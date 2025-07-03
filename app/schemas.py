from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Optional, Annotated
from fastapi import WebSocket
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        orm_mode = True

class UserOut(BaseModel):
    id: int
    username: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None

class ChangePassword(BaseModel):
   old_password: Annotated[str, StringConstraints(min_length=6)]
   new_password: Annotated[str, StringConstraints(min_length=6)]

class CreateTable(BaseModel):
    room_name: str
    password: Optional[str] = None

class JoinRoom(BaseModel):
    room_id: int
    password: Optional[str] = None