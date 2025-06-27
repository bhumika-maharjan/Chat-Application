from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi import WebSocket

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

class CreateTable(BaseModel):
    room_name: str
    is_private: bool

class JoinRoom(BaseModel):
    room_id: int

class ConnectionManager:
    def __init__(self):
        self.rooms_active_user: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, roomid: int):
        await websocket.accept()
        if roomid not in self.rooms_active_user:
            self.rooms_active_user[roomid] = []
        self.rooms_active_user[roomid].append(websocket)

    async def brodcast(self, msg: str, roomid: int):
        if roomid in self.rooms_active_user:
            for user in self.rooms_active_user[roomid]:
                await user.send_text(msg)

    def disconnect(self, websocket: WebSocket, roomid: int):
        if roomid in self.rooms_active_user:
            self.rooms_active_user[roomid].remove(websocket)
            if not self.rooms_active_user[roomid]:
                del self.rooms_active_user[roomid]