from fastapi import WebSocket, APIRouter, Depends, WebSocketDisconnect
from app.database import get_db, SessionLocal
from sqlalchemy.orm import Session
from app.utils import verify_token, verify_user
from app.connection_manager import UserConnectionManager
from fastapi.responses import HTMLResponse
from database.models import Message, User
from sqlalchemy import or_, and_
from datetime import datetime
import base64
import uuid
import json
import os

router =  APIRouter()

html = """
<!DOCTYPE html>
<html>
    <head><title>User Chat</title></head>
    <body>
        <form onSubmit="CreateConnection(event)">
            <input id="receiver" placeholder="Enter id you want to send msg"/>
            <input id="token" placeholder="Enter token" />
            <button>Connect</button>
        </form>

        <hr>

        <form onSubmit="SendMsg(event)">
            <input id="message" placeholder="Enter the msg"/>
            <input type="file" id="fileInput" />
            <button>Send</button>
        </form>

        <ul id="messages"></ul>

        <script>
            var ws = null;

            function CreateConnection(event){
                event.preventDefault();
                if (ws !== null && ws.readyState === WebSocket.OPEN) {
                    alert("Already connected!");
                    return;
                }

                const receiverid = document.getElementById("receiver").value;
                const token = document.getElementById("token").value;

                ws = new WebSocket(`ws://localhost:8000/userchat/${receiverid}?token=${token}`);

                ws.onmessage = (event) => {
                    const msgList = document.getElementById("messages");
                    const li = document.createElement("li");
                    li.textContent = event.data;
                    msgList.appendChild(li);
                };
            }

            function SendMsg(event){
                event.preventDefault(); 
                const msg = document.getElementById("message").value;
                const fileInput =  document.getElementById("fileInput");
                const file = fileInput.files[0];
                status =  "sending"
                if (ws && ws.readyState === WebSocket.OPEN) {
                    if(file){
                        const reader= new FileReader();
                        reader.onload = () => {
                            const base64 = reader.result;
                            const payload = {
                                type: "file",
                                filename: file.name,
                                mimetype: file.type,
                                data: base64,
                                text: msg
                            };
                            ws.send(JSON.stringify(payload));
                            document.getElementById("message").value = "";
                            document.getElementById("fileInput").value = "";
                        };
                        reader.readAsDataURL(file);
                    } else{
                        ws.send(JSON.stringify({
                            type: "text",
                            text: msg
                        }));
                    }
                    // Optional: show your own sent message in the list
                    const msgList = document.getElementById("messages");
                    const li = document.createElement("li");
                    li.textContent = "Timestamp :"+getCurrentTimestamp() +"You: " + msg + " Status:" + status;
                    msgList.appendChild(li);
                } else {
                    alert("WebSocket not connected.");
                }
            }
            function getCurrentTimestamp() {
                const now = new Date();
                
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are zero-based
                const day = String(now.getDate()).padStart(2, '0');
                
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            }
        </script>
    </body>
</html>

"""

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

usermanager = UserConnectionManager()

@router.get("/")
def display():
    return HTMLResponse(html)

@router.websocket("/userchat/{receiverid}")
async def user_websocket_endpoint(websocket: WebSocket, receiverid : str, db: Session = Depends(get_db)):
    token =  websocket.query_params.get("token")
    userinfo =  verify_token(token, db)

    sender_id = int(userinfo.id)
    receiver_id = int(receiverid)

    receiver_exist = verify_user(receiver_id, db)
    if not receiver_exist:
        await websocket.close(code=1008)
        return
    
    await usermanager.connect(sender_id, receiver_id, websocket)
    await send_past_message(websocket , sender_id, receiver_id)

    try:
        while True:
            raw_data =  await websocket.receive_text()
            try:
                data = json.loads(raw_data)

                if data["type"] == "text":
                    stored_msg =  store_and_return_msg(data["text"], sender_id, receiver_id)
                    # Notify both parties
                    await usermanager.send_msg(sender_id, receiver_id, {
                        "type": "status_update",
                        "message_id": stored_msg["id"],
                        "timestamp": stored_msg["timestamp"],
                        "sender": stored_msg["sender"],
                        "content": stored_msg["content"],
                        "file_url": stored_msg["file_url"],
                        "status": "sent"
                    })

                    update_status("delivered",stored_msg["id"])

                    await websocket.send_text(json.dumps({
                        "type": "status_update",
                        "message_id": stored_msg["id"],
                        "timestamp": stored_msg["timestamp"],
                        "sender": stored_msg["sender"],
                        "content": stored_msg["content"],
                        "file_url": stored_msg["file_url"],
                        "status": "delivered"
                    }))

                elif data["type"] == "file":
                    header, base64_data =  data["data"].split(",",1)
                    file_data =  base64.b64decode(base64_data)
                    filename = f"{uuid.uuid4()}_{data['filename'].replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR,filename)

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    file_url = f"/{UPLOAD_DIR}/{filename}"

                    stored_msg = store_and_return_msg(
                        content=data.get("text"),
                        sender_id=sender_id,
                        receiver_id=receiver_id,
                        file_url=file_url,
                        file_type=data["mimetype"]
                    )

                    await usermanager.send_msg(sender_id, receiver_id, {
                        "type": "status_update",
                        "message_id": stored_msg["id"],
                        "timestamp": stored_msg["timestamp"],
                        "sender": stored_msg["sender"],
                        "content": stored_msg["content"],
                        "file_url": stored_msg["file_url"],
                        "status": "sent"
                    })

                    update_status("delivered", stored_msg["id"])

                    await websocket.send_text(json.dumps({
                        "type": "status_update",
                        "message_id": stored_msg["id"],
                        "timestamp": stored_msg["timestamp"],
                        "sender": stored_msg["sender"],
                        "content": stored_msg["content"],
                        "file_url": stored_msg["file_url"],
                        "status": "delivered"
                    }))

                elif data["type"] == "read":
                    message_id = data["message_id"]
                    msg = db.query(Message).filter(Message.id == message_id).first()
                    if msg and msg.receiver_id == sender_id:
                        update_status("read", message_id)
                        sender = db.query(User).filter(User.id == msg.sender_id).first()
                        await websocket.send_text(json.dumps({
                            "type": "status_update",
                            "message_id": message_id,
                            "timestamp": msg.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "sender": sender.first_name + " " + sender.last_name,
                            "content": msg.content,
                            "file_url": msg.file_url,
                            "status": "read"
                        }))
                        # Optionally, notify the sender via usermanager (if connected)
                        await usermanager.send_msg(msg.sender_id, msg.receiver_id, {
                            "type": "status_update",
                            "message_id": message_id,
                            "timestamp": msg.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "sender": sender.first_name + " " + sender.last_name,
                            "content": msg.content,
                            "file_url": msg.file_url,
                            "status": "read"
                        })

            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format.")
                continue 
    except WebSocketDisconnect:
        await usermanager.disconnect(sender_id, receiver_id, websocket)
        print(userinfo.first_name,"disconnected")


async def send_past_message(websocket : WebSocket, sender_id : int, receiver_id : int):
    db = SessionLocal()
    try:
        chat_history = (
            db.query(
                Message.id,
                Message.content,
                Message.file_url,
                Message.file_type,
                Message.sent_at,
                Message.sender_id,
                Message.status,
                User.first_name,
                User.last_name
            )
            .join(User, Message.sender_id == User.id)
            .filter(
                or_(
                    and_(Message.sender_id == sender_id, Message.receiver_id == receiver_id),
                    and_(Message.sender_id == receiver_id, Message.receiver_id == sender_id)
                )
            )
            .order_by(Message.sent_at)
            .all()
        )
        for id,content, file_url, file_type, sent_at, sender_id,status, first_name, last_name in chat_history:
            timestamp = sent_at.strftime("%Y-%m-%d %H:%M:%S")

            if file_url:
                if content:
                    await websocket.send_text(json.dumps({
                        "type" : "message_history",
                        "message_id" : id,
                        "timestamp" : timestamp,
                        "sender" : first_name + last_name,
                        "content" : content,
                        "fileurl" : file_url,
                        "status" : status
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        "type" : "message_history",
                        "message_id" : id,
                        "timestamp" : timestamp,
                        "sender" : first_name + last_name,
                        "content" : None,
                        "fileurl" : file_url,
                        "status" : status
                    }))
            else:
                await websocket.send_text(json.dumps({
                    "type" : "message_history",
                    "message_id" : id,
                    "timestamp" : timestamp,
                    "sender" : first_name + last_name,
                    "content" : content,
                    "file_url" : None,
                    "status" : status
                }))
    finally:
        db.close()

def store_and_return_msg(content: str, sender_id: int, receiver_id: int, file_url: str = None, file_type: str = None) -> dict:
    db = SessionLocal()
    try:
        new_message = Message(
            content=content,
            sender_id=sender_id,
            file_url=file_url,
            file_type=file_type,
            receiver_id=receiver_id,
            status="sent"
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        user = db.query(User).filter(User.id == sender_id).first()
        timestamp = new_message.sent_at.strftime("%Y-%m-%d %H:%M:%S")

        if new_message.file_url:
            if new_message.content:
                return{
                    "id": new_message.id,
                    "timestamp" : timestamp,
                    "sender" : user.first_name + " " + user.last_name,
                    "content" : new_message.content,
                    "file_url" : new_message.file_url,
                    "status" : new_message.status 
                }
            else:
                return{
                    "id": new_message.id,
                    "timestamp" : timestamp,
                    "sender" : user.first_name + " " + user.last_name,
                    "content" : None,
                    "file_url" : new_message.file_url,
                    "status" : new_message.status 
                }
        else:
                return{
                    "id": new_message.id,
                    "timestamp" : timestamp,
                    "sender" : user.first_name + " " + user.last_name,
                    "content" : new_message.content,
                    "file_url" : None,
                    "status" : new_message.status 
                }
    finally:
        db.close()


def update_status(status: str, id: int):
    db = SessionLocal()
    try:
        msg = db.query(Message).filter(Message.id == id).first()
        if msg:
            msg.status = status
            db.commit()
            return True
        return False
    finally:
        db.close()

@router.websocket("/readstatus")
async def readstatus(messageid: int, receivertoken: str, websocket:WebSocket, db: Session = Depends(get_db)):
    userinfo = verify_token(receivertoken, db)

    msg = db.query(Message).filter(Message.id == messageid).first()
    if not msg:
        return {"error": "Message not found"}
    if userinfo.id != msg.receiver_id:
        return {"error": "Unauthorized"}

    update_status("read", messageid)

    sender_id = msg.sender_id
    receiver_id = msg.receiver_id
    timestamp = msg.sent_at.strftime("%Y-%m-%d %H:%M:%S")
    sender = db.query(User).filter(User.id == sender_id).first()
    await websocket.send_text(json.dumps({
        "type": "status_update",
        "message_id": messageid,
        "timestamp": timestamp,
        "sender": sender.first_name + " " + sender.last_name,
        "content": msg.content,
        "file_url": msg.file_url,
        "status": "read"
    }))

    return {"message": "Status updated to read"}
