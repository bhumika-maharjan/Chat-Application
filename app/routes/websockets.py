from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.database import get_db,SessionLocal
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.models import ConnectionManager
from database.models import Message, User, RoomMembers
from app.validations import check_user_inroom

router = APIRouter()

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

            ws = new WebSocket(`ws://localhost:8000/user/?userid =${userid}&roomid=${roomid}&token=${token}`);

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

@router.get("/homepage")
def display_home():
    return HTMLResponse(html)

def verify_token(token: str):
    return token == "mystr"

manager = ConnectionManager()

@router.websocket("/user/")
async def websocket_endpoint(websocket: WebSocket, userid: str):
    roomid = websocket.query_params.get("roomid")
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

@router.post('user/leftchat')
async def left_chat(userid: int, chatid: int, db: Session = Depends(get_db)):
    userinfo = db.query(User.first_name, User.last_name).filter_by(id=userid).first()

    if not userinfo:
        return {"error": "User not found"}

    membership = check_user_inroom(userid, chatid, db)
    if membership:
        full_name = f"{userinfo.first_name} {userinfo.last_name}"
        msg_text = f"{full_name} has left the chat."
        stored_msg = store_and_return_message(userid, chatid, msg_text)

        db.query(RoomMembers).filter_by(user_id=userid, room_id=chatid).delete()
        db.commit()

        await manager.brodcast(f"{stored_msg['message']}", chatid)

        return {"message": "Leave message stored and broadcasted"}
    else:
        return {"message": "No user in this room"}