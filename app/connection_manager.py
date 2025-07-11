from fastapi import WebSocket
from typing import Dict, Tuple, List, Union
import json

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

class UserConnectionManager:
    def __init__(self):
        # user_id -> list of (receiver_id, websocket) connections
        self.active_user: Dict[int, List[Tuple[int, WebSocket]]] = {}
    
    async def connect(self,sender_id : int, receiver_id : int, websocket: WebSocket):
        await websocket.accept()
        if sender_id not in self.active_user:
            self.active_user[sender_id] = []
        self.active_user[sender_id].append((receiver_id, websocket))

    async def send_msg(self, sender_id: int, receiver_id: int, msg: Union[str, dict]):
        if isinstance(msg, dict):
            msg = json.dumps(msg)  # convert dict to JSON string

        # Send to receiver if connected
        if receiver_id in self.active_user:
            for receiver, websocket in self.active_user[receiver_id]:
                if receiver == sender_id:
                    await websocket.send_text(msg)

        # Optionally: also send to sender if connected (e.g., for delivery status)
        if sender_id in self.active_user:
            for receiver, websocket in self.active_user[sender_id]:
                if receiver == receiver_id:
                    await websocket.send_text(msg)

    async def disconnect(self, sender_id: int, receiver_id: int, websocket: WebSocket):
        if sender_id in self.active_user:
            # Filter out the exact (receiver_id, websocket) pair
            self.active_user[sender_id] = [
                (rid, ws) for (rid, ws) in self.active_user[sender_id]
                if not (rid == receiver_id and ws == websocket)
            ]

            # If sender has no more connections, remove the sender
            if not self.active_user[sender_id]:
                del self.active_user[sender_id]
