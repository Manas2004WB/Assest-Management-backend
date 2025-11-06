from sqlalchemy.orm import Session
from app.models import NodeData
from sqlalchemy import text

def get_descendants(db: Session, parent_id: int, return_objects=True):
    if return_objects:
        children = db.query(NodeData).filter(NodeData.parent_id == parent_id).all()
        all_children = []
        for child in children:
            all_children.append(child)
            all_children.extend(get_descendants(db, child.node_id, return_objects=True))
        return all_children
    else:
        query = text("SELECT node_id FROM node_data WHERE parent_id = :parent_id")
        children = db.execute(query, {"parent_id": parent_id}).fetchall()
        all_ids = []
        for child in children:
            child_id = child[0]
            all_ids.append(child_id)
            all_ids.extend(get_descendants(db, child_id, return_objects=False))
        return all_ids
