
from fastapi import APIRouter, Depends, HTTPException, Query, Request, requests
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app.models import NodeData
from app.schemas import NodeCreate, NodeResponse, NodeTreeResponse, DeletedNodeTree
from app.crud import get_descendants
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List
from urllib.parse import unquote_plus
from sqlalchemy import text, bindparam
from fastapi import Depends
from app.auth import get_current_user
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/nodes", response_model=List[NodeResponse])
def get_nodes(db: Session = Depends(get_db)):
    query = text("SELECT * FROM node_data;")
    result = db.execute(query)
    nodes = result.fetchall()
    return [dict(row._mapping) for row in nodes]


@router.get("/nodes/tree", response_model=List[NodeTreeResponse])
def get_nodes_tree(db: Session = Depends(get_db),current_user: str = Depends(get_current_user)):
    query = text("SELECT * FROM node_data WHERE is_deleted = 0;")
    result = db.execute(query)
    nodes = [dict(row._mapping) for row in result.fetchall()]
    node_map = {n["node_id"]: {**n, "children": [],
                               "children_count": 0} for n in nodes}
    tree = []

    for n in node_map.values():
        parent_id = n.get("parent_id")
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(n)
        else:
            tree.append(n)

    def count_children(node):
        if not node["children"]:
            node["children_count"] = 0
            return 0

        total = 0
        for child in node["children"]:
            total += 1 + count_children(child)
        node["children_count"] = total
        return total

    for root in tree:
        count_children(root)

    return tree


# @router.get("/nodes/tree-withDeleted", response_model=List[NodeTreeResponse])
# def get_nodes_tree(db: Session = Depends(get_db)):
#     query = text("SELECT * FROM node_data")
#     result = db.execute(query)
#     nodes = [dict(row._mapping) for row in result.fetchall()]
#     node_map = {n["node_id"]: {**n, "children": [], "children_count": 0} for n in nodes}
#     tree = []
#     for n in node_map.values():
#         parent_id = n.get("parent_id")
#         if parent_id and parent_id in node_map:
#             node_map[parent_id]["children"].append(n)
#             node_map[parent_id]["children_count"] += 1
#         else:
#             tree.append(n)
#     return tree

@router.post("/nodes", response_model=NodeResponse)
def create_node(node: NodeCreate, 
                db: Session = Depends(get_db), 
                current_user: str = Depends(get_current_user)
                ):
    parent_query = text("""
        SELECT node_id 
        FROM node_data 
        WHERE node_name = :parent_name AND is_deleted = 0
    """)
    parent_result = db.execute(
        parent_query, {"parent_name": node.parent_name}).first()

    if not parent_result:
        raise HTTPException(
            status_code=404,
            detail=f"Parent node '{node.parent_name}' not found."
        )
    parent_id = parent_result.node_id
    insert_query = text("""
        INSERT INTO node_data (parent_id, node_name, is_deleted)
        OUTPUT INSERTED.*
        VALUES (:parent_id, :node_name, :is_deleted)
    """)

    result = db.execute(insert_query, {
        "parent_id": parent_id,
        "node_name": node.node_name,
        "is_deleted": False
    })

    new_node = result.fetchone()
    db.commit()
    return dict(new_node._mapping)


@router.put("/nodes/{node_id}", response_model=NodeResponse)
def update_node(node_id: int, node: NodeCreate, db: Session = Depends(get_db)):
    update_query = text(""" 
        UPDATE node_data 
        SET parent_id = :parent_id,
            node_name = :node_name
        OUTPUT INSERTED.*
        WHERE node_id = :node_id""")
    try:
        result = db.execute(update_query, {
            "node_id": node_id,
            "parent_id": node.parent_id,
            "node_name": node.node_name
        })
        updated_node = result.fetchone()
        if not updated_node:
            raise HTTPException(status_code=404, detail="Node not found")
        db.commit()
        return dict(updated_node._mapping)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/restore/{node_id}", response_model=NodeResponse)
def restore_node(node_id: int, db: Session = Depends(get_db)):
    try:
        node_query = text("""
            SELECT node_id, parent_id, is_deleted
            FROM node_data
            WHERE node_id = :node_id
        """)
        node = db.execute(node_query, {"node_id": node_id}).fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        restore_chain = []
        current_parent_id = node.parent_id

        while current_parent_id:
            parent = db.execute(text("""
                SELECT node_id, parent_id, is_deleted
                FROM node_data
                WHERE node_id = :parent_id
            """), {"parent_id": current_parent_id}).fetchone()

            if not parent:
                break

            if parent.is_deleted == 1:
                restore_chain.append(parent.node_id)
                current_parent_id = parent.parent_id
            else:
                break

        ids_to_restore = [node.node_id] + restore_chain

        update_query = text(
            "UPDATE node_data SET is_deleted = 0 WHERE node_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))

        db.execute(update_query, {"ids": ids_to_restore})
        db.commit()

        restored = db.execute(
            text("SELECT * FROM node_data WHERE node_id = :id"),
            {"id": node.node_id}
        ).fetchone()

        return dict(restored._mapping)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db)):
    node_query = text(
        "SELECT node_id, parent_id FROM node_data WHERE node_id = :node_id")
    node = db.execute(node_query, {"node_id": node_id}).fetchone()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.parent_id == 0:
        raise HTTPException(
            status_code=400, detail="Root node cannot be deleted")

    child_nodes = get_descendants(db, node_id, return_objects=True)
    try:
        if child_nodes:
            child_ids = [child.node_id for child in child_nodes]
            placeholders = ", ".join(map(str, child_ids))
            update_children_query = text(
                f"UPDATE node_data SET is_deleted = 1 WHERE node_id IN ({placeholders})"
            )
            db.execute(update_children_query)

        update_node_query = text(
            "UPDATE node_data SET is_deleted = 1 WHERE node_id = :node_id"
        )
        db.execute(update_node_query, {"node_id": node_id})

        db.commit()

        return {
            "message": f"Node {node_id} and its {len(child_nodes)} child nodes marked as deleted successfully"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/hard-nodes/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db)):
    node_query = text(
        "SELECT node_id, parent_id FROM node_data WHERE node_id = :node_id")
    node = db.execute(node_query, {"node_id": node_id}).fetchone()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.parent_id == 0:
        raise HTTPException(
            status_code=400, detail="Root node cannot be deleted")

    child_ids = get_descendants(db, node_id, return_objects=False)

    try:
        if child_ids:
            delete_children_query = text(
                "DELETE FROM node_data WHERE node_id IN :child_ids"
            )
            db.execute(delete_children_query, {"child_ids": tuple(child_ids)})

        delete_node_query = text(
            "DELETE FROM node_data WHERE node_id = :node_id")
        db.execute(delete_node_query, {"node_id": node_id})

        db.commit()
        return {
            "message": f"Node {node_id} and its {len(child_ids)} child nodes deleted successfully"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/search")
def search_nodes(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    decoded_q = unquote_plus(q)
    query = text("""
    SELECT node_id, node_name
    FROM node_data
    WHERE node_name LIKE :pattern
      AND is_deleted = 0
    ORDER BY node_name
    OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY
""")
    result = db.execute(query, {"pattern": f"%{decoded_q}%"})

    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/nodes/deleted-trees", response_model=List[DeletedNodeTree])
def get_deleted_trees(db: Session = Depends(get_db)):
    all_deleted = db.execute(text("""
        SELECT node_id, node_name, parent_id
        FROM node_data
        WHERE is_deleted = 1
    """)).mappings().all()

    if not all_deleted:
        return []

    deleted_nodes = [dict(row) for row in all_deleted]

    deleted_ids = {n["node_id"] for n in deleted_nodes}
    deleted_roots = [
        n for n in deleted_nodes if not n["parent_id"] or n["parent_id"] not in deleted_ids
    ]
    node_map = {n["node_id"]: {**n, "children": []} for n in deleted_nodes}
    for n in node_map.values():
        pid = n.get("parent_id")
        if pid and pid in node_map:
            node_map[pid]["children"].append(n)
    deleted_trees = [node_map[r["node_id"]] for r in deleted_roots]

    return deleted_trees
