from passlib.context import CryptContext
from fastapi import WebSocket

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password:str, hashed_password: str)->bool:
    return pwd_context.verify(plain_password, hashed_password)


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