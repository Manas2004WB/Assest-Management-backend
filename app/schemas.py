from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

class NodeCreate(BaseModel):
    parent_name: str
    node_name: str

class NodeResponse(BaseModel):
    node_id: int
    parent_id: Optional[int]
    node_name: str
    is_deleted: Optional[bool]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
        

class NodeTreeResponse(BaseModel):
    node_id: int
    node_name: str
    parent_id: Optional[int] = None
    children_count : int
    children: List["NodeTreeResponse"] = []

    class Config:
        orm_mode = True

# Fix forward reference (important!)
NodeTreeResponse.model_rebuild()
