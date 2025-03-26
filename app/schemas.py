from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    items: List[Item] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# New schemas for documents
class DocumentBase(BaseModel):
    file_id: str
    name: str
    mime_type: str

class DocumentCreate(DocumentBase):
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class Document(DocumentBase):
    id: int
    owner_id: int
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    last_synced: Optional[datetime]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True

class DocumentEmbeddingBase(BaseModel):
    chunk_index: int
    chunk_text: str
    embedding_vector: List[float]

class DocumentEmbeddingCreate(DocumentEmbeddingBase):
    document_id: int

class DocumentEmbedding(DocumentEmbeddingBase):
    id: int
    document_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for Google Drive authentication
class GoogleCredentials(BaseModel):
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: List[str]

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str 