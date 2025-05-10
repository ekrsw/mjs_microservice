from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr