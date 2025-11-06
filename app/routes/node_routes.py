from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app.models import NodeData
from app.schemas import NodeCreate, NodeResponse
from app.crud import get_descendants
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List

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


@router.post("/nodes", response_model=NodeResponse)
def create_node(node: NodeCreate, db: Session = Depends(get_db)):
    insert_query = text("""
        INSERT INTO node_data (parent_id, node_name, is_deleted)
        OUTPUT INSERTED.*
        VALUES (:parent_id, :node_name, :is_deleted)
    """)
    if node.parent_id == 0:
        raise HTTPException(
            status_code=400, detail="Root node cannot be created by user")
    result = db.execute(insert_query, {
        "parent_id": node.parent_id,
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
            child_ids = tuple(child.node_id for child in child_nodes)
            update_children_query = text(
                "UPDATE node_data SET is_deleted = 1 WHERE node_id IN :child_ids"
            )
            db.execute(update_children_query, {"child_ids": child_ids})

        update_node_query = text(
            "UPDATE node_data SET is_deleted = 1 WHERE node_id = :node_id")
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
