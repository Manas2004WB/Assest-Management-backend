from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NodeCreate(BaseModel):
    parent_id: Optional[int] = None
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
