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

class DeletedNodeTree(BaseModel):
    node_id: int
    node_name: str
    parent_id: Optional[int] = None
    children: List["DeletedNodeTree"] = []

# Fix forward reference for Pydantic v1.x
DeletedNodeTree.update_forward_refs()

class NodeTreeResponse(BaseModel):
    node_id: int
    node_name: str
    parent_id: Optional[int] = None
    children_count: int
    is_deleted: bool
    children: List["NodeTreeResponse"] = []

    class Config:
        orm_mode = True

# Fix forward reference for Pydantic v1.x
NodeTreeResponse.update_forward_refs()

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

