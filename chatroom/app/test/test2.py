from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import User, Message, RoomMembers

app = FastAPI()

DATABASE_URL = "postgresql://postgres:admin@localhost:5432/chatapp"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

html = """
<!DOCTYPE html>
<html>
    <head><title>Chat</title></head>
    <body>
        <form onsubmit="CreateConnection(event)">
            <input id="userid" placeholder="Enter user id"/>
            <input id="roomid" placeholder="Enter room id"/>
            <input id="token" placeholder="Enter token" />
            <button>Connect</button>
        </form>
        <hr>
        <form onsubmit="SendMsg(event)">
            <input id="message" placeholder="Enter Message"/>
            <button>Send Msg</button>
        </form>
        <ul id="messages"></ul>
    </body>
    <script>
        var ws = null;

        function CreateConnection(event){
            event.preventDefault(); 
            const userid = document.getElementById("userid").value;
            const roomid = document.getElementById("roomid").value;
            const token = document.getElementById("token").value;

            ws = new WebSocket(`ws://localhost:8000/users/${userid}/?q=${roomid}&token=${token}`);

            ws.onmessage = (event) => {
                const message = document.createElement("li");
                const content = document.createTextNode(event.data);
                message.appendChild(content);
                document.getElementById('messages').appendChild(message);
            };
        }

        function SendMsg(event){
            event.preventDefault(); 
            const msg = document.getElementById("message").value;
            ws.send(msg);
        }
    </script>
</html>
"""

@app.get("/home")
def display_home():
    return HTMLResponse(html)

def verify_token(token: str):
    return token == "mystr"

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

manager = ConnectionManager()

@app.websocket("/users/{userid}/")
async def websocket_endpoint(websocket: WebSocket, userid: str):
    roomid = websocket.query_params.get("q")
    token = websocket.query_params.get("token")

    if not verify_token(token):
        await websocket.close(code=1008)
        return

    userid = int(userid)
    roomid = int(roomid)

    await manager.connect(websocket, roomid)

    await send_past_messages_to_user(websocket, roomid)

    try:
        while True:
            data = await websocket.receive_text()
            stored_msg = store_and_return_message(userid, roomid, data)

            await manager.brodcast(f"{stored_msg['user']}: {stored_msg['message']}", roomid)

    except WebSocketDisconnect:
        manager.disconnect(websocket, roomid)
        await manager.brodcast(f"{userid} disconnected", roomid)

async def send_past_messages_to_user(websocket: WebSocket, roomid: int):
    db = SessionLocal()
    try:
        results = (
            db.query(Message.content, User.first_name,User.last_name)
            .join(User, Message.sender_id == User.id)
            .filter(Message.room_id == roomid)
            .order_by(Message.sent_at)
            .all()
        )

        for content, first_name, last_name in results:
            await websocket.send_text(f"{first_name} {last_name}: {content}")
    finally:
        db.close()

def store_and_return_message(userid: int, room_id: int, content: str) -> dict:
    db = SessionLocal()
    try:
        new_message = Message(
            content=content,
            sender_id=userid,
            room_id=room_id
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        user = db.query(User).filter(User.id == userid).first()

        return {
            "user": user.first_name + user.last_name,
            "message": new_message.content
        }
    finally:
        db.close()

@app.post('/leftchat')
async def left_chat(userid: int, chatid: int, db: Session = Depends(get_db)):
    userinfo = db.query(User.first_name, User.last_name).filter_by(id=userid).first()

    if not userinfo:
        return {"error": "User not found"}

    full_name = f"{userinfo.first_name} {userinfo.last_name}"
    msg_text = f"{full_name} has left the chat."
    stored_msg = store_and_return_message(userid, chatid, msg_text)

    db.query(RoomMembers).filter_by(user_id=userid, room_id=chatid).delete()
    db.commit()
    # Step 4: Broadcast to all users in room
    await manager.brodcast(f"{stored_msg['message']}",chatid)

    return {"message": "Leave message stored and broadcasted"}