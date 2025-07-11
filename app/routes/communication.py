from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from typing import Dict, Tuple
from app.database import get_db, SessionLocal
from app.connection_manager import ConnectionManager
from database.models import RoomMembers, Message, User, Chatroom, PrivateMessage
from app.utils import get_current_user, check_user_inroom, verify_token, verify_password, decode_token
from sqlalchemy.orm import Session
import json
import base64
import uuid
import os

router = APIRouter()

@router.get("/chatroom/{roomid}")
def get_chatroom_info(
    roomid: int,
    token: str = Header(...), 
):
    db = SessionLocal()
    print("checking")
    user = verify_token(token, db)  
    room = db.query(Chatroom).filter(Chatroom.id == roomid).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    creator = db.query(User).filter(User.id == room.created_by).first()
    return {
        "user" : f"{user.first_name} {user.last_name}",
        "roomname": room.roomname,
        "creator": f"{creator.first_name} {creator.last_name}", # type: ignore
        "created_at": room.created_at.isoformat()
    }


html = """
<!DOCTYPE html>
<html>
    <head><title>Chat</title></head>
    <body>
        <form onsubmit="CreateConnection(event)">
            <input id="roomid" placeholder="Enter room id"/>
            <input id="token" placeholder="Enter token" />
            <input id="roompassword" placeholder="Enter room password (if private)" />
            <button>Connect</button>
        </form>
        <hr>
        <div id="room-info" style="display:none;">
            <p><strong>Logged in User:</strong> <span id="user"></span></p>
            <p><strong>Room:</strong> <span id="roomname"></span></p>
            <p><strong>Creator:</strong> <span id="creator"></span></p>
        </div>
        <form onsubmit="SendMsg(event)">
            <input id="message" placeholder="Enter Message"/>
            <input type="file" id="fileInput" />
            <button>Send Msg</button>
        </form>
        <ul id="messages"></ul>
    </body>
    <script>
        var ws = null;

        function CreateConnection(event){
            event.preventDefault(); 

            if (ws !== null && ws.readyState === WebSocket.OPEN) {
                alert("Already connected!");
                return;
            }

            const roomid = document.getElementById("roomid").value;
            const token = document.getElementById("token").value;
            const password = document.getElementById("roompassword").value;

            fetch(`http://localhost:8000/chatroom/${roomid}`, {
                headers: {
                    "token": token
                }
            })
            .then(response => {
                console.log("Fetching");
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById("user").innerText = data.user;
                document.getElementById("roomname").innerText = data.roomname;
                document.getElementById("creator").innerText = data.creator;
                document.getElementById("room-info").style.display = "block";
            })
            .catch(error => {
                console.error("Fetch failed:", error);
                alert("Failed to fetch chatroom details.");
            });

        
            ws = new WebSocket(`ws://localhost:8000/chat/${roomid}?token=${token}&password=${encodeURIComponent(password)}`);

            ws.onmessage = (event) => {
                const message = document.createElement("li");
                const text = event.data;

                if (text.includes("/uploads/")) {
                    const parts = text.split(" ");
                    const fileUrl = parts.find(p => p.includes("/uploads/"));
                    const ext = fileUrl.split('.').pop().toLowerCase();

                    const labelText = text.replace(fileUrl, "").trim();
                    const lines = labelText.split('\\n');
                    lines.forEach((line, index) => {
                        const p = document.createElement("p");
                        if (index === 0 && line.startsWith("Timestamp")) {
                            p.style.fontWeight = "bold";
                        }
                        p.textContent = line;
                        message.appendChild(p);
                    });

                    if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) {
                        const img = document.createElement("img");
                        img.src = fileUrl;
                        img.style.maxWidth = "200px";
                        img.style.border = "1px solid #ccc";
                        img.style.marginTop = "5px";
                        message.appendChild(img);
                    } else if (["mp4", "webm"].includes(ext)) {
                        const video = document.createElement("video");
                        video.src = fileUrl;
                        video.controls = true;
                        video.style.maxWidth = "300px";
                        video.style.border = "1px solid #ccc";
                        video.style.marginTop = "5px";
                        message.appendChild(video);
                    } else {
                        const link = document.createElement("a");
                        link.href = encodeURI(fileUrl);
                        link.textContent = "Download file";
                        link.download = "";
                        link.target = "_blank";
                        message.appendChild(link);
                    }

                } else {
                    const lines = text.split('\\n');
                    lines.forEach((line, index) => {
                        const p = document.createElement("p");
                        if (index === 0 && line.startsWith("Timestamp")) {
                            p.style.fontWeight = "bold";
                        }
                        p.textContent = line;
                        message.appendChild(p);
                    });
                }

                document.getElementById('messages').appendChild(message);
            };


            ws.onclose = () => {
                ws = null;
                document.getElementById("messages").innerHTML = "";
                document.getElementById("room-info").style.display = "none";
            };
        }

        function SendMsg(event){
            event.preventDefault(); 
            const msg = document.getElementById("message").value;
            const fileInput =  document.getElementById("fileInput");
            const file = fileInput.files[0];

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
                document.getElementById("message").value = "";
                document.getElementById("fileInput").value = "";
            }
        }
    </script>
</html>
"""

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/home")
def display_home():
    return HTMLResponse(html)

manager = ConnectionManager()

@router.websocket("/chat/{roomid}")
async def websocket_endpoint(websocket: WebSocket, roomid : str, db: Session = Depends(get_db)):
    token =  websocket.query_params.get("token")
    password = websocket.query_params.get("password", "")
    userinfo = decode_token(token, db) # type: ignore
    userid = int(userinfo.id) # type: ignore
    roomid = int(roomid) # type: ignore

    room = db.query(Chatroom).filter(Chatroom.id == roomid).first()
    if not room:
        await websocket.close(code=1008)
        return

    is_member = check_user_inroom(userid, roomid, db) # type: ignore
    if not is_member:
        await websocket.close(code=1008)
        return

    if bool(room.is_private):
        if not password or not verify_password(password, room.password): # type: ignore
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, roomid) # type: ignore
    await send_past_messages_to_user(websocket, roomid) # type: ignore
    await manager.brodcast(f"{userinfo.first_name} {userinfo.last_name} is online.", roomid) # type: ignore

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)

                if data["type"] == "text":
                    stored_msg = store_and_return_message(userid, roomid, data["text"]) # type: ignore
                    await manager.brodcast(
                        f"Timestamp: {stored_msg['sent_at']}\n{stored_msg['user']}: {stored_msg['message']}",
                        roomid # type: ignore
                    ) 
                elif data["type"] == "file":
                    header, base64_data =  data["data"].split(",",1)
                    file_data =  base64.b64decode(base64_data)
                    filename = f"{uuid.uuid4()}_{data['filename'].replace(' ', '_')}"
                    filepath = os.path.join(UPLOAD_DIR,filename)

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    file_url = f"/{UPLOAD_DIR}/{filename}"

                    stored_msg =  store_and_return_message(
                        userid,
                        roomid, # type: ignore
                        content = data.get("text"),
                        file_url = file_url,
                        file_type = data["mimetype"]
                    )

                    await manager.brodcast(
                        f"Timestamp: {stored_msg['sent_at']}\n{stored_msg['user']} sent a file: {file_url}",
                        roomid # type: ignore
                    )
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format.")
                continue  # Don't exit the loop


    except WebSocketDisconnect:
        manager.disconnect(websocket, roomid) # type: ignore
        await manager.brodcast(f"{userinfo.first_name} {userinfo.last_name} is offline", roomid) # type: ignore


async def send_past_messages_to_user(websocket: WebSocket, roomid: int):
    db = SessionLocal()
    try:
        results = (
            db.query(
                Message.content,
                Message.file_url,
                Message.file_type,
                User.first_name,
                User.last_name,
                Message.sent_at)
            .join(User, Message.sender_id == User.id)
            .filter(Message.room_id == roomid)
            .order_by(Message.sent_at)
            .all()
        )

        for content,file_url, file_type, first_name, last_name, time in results:
            if file_url:
                if content:
                    message_text = f"Timestamp: {time}\n{first_name} {last_name} sent a file: {content} {file_url}"
                else:
                    message_text = f"Timestamp: {time}\n{first_name} {last_name} sent a file: {file_url}"
            else:
                message_text = f"Timestamp: {time}\n{first_name} {last_name}: {content}"
            await websocket.send_text(message_text)
    finally:
        db.close()

def store_and_return_message(userid: int, room_id: int, content: str, file_url :str = None, file_type: str = None) -> dict:
    db = SessionLocal()
    try:
        print("working")
        new_message = Message(
            content= content,
            sender_id= userid,
            room_id= room_id,
            file_url =  file_url,
            file_type = file_type
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        print("data sent")

        user = db.query(User).filter(User.id == userid).first()

        return {
            "user": user.first_name + user.last_name, #type: ignore
            "message": new_message.content or "",
            "file_url": new_message.file_url,
            "file_type": new_message.file_type,
            "sent_at" : new_message.sent_at

        }
    finally:
        db.close()

@router.get('/leftchat/{roomid}')
async def left_chat( roomid: int, db: Session = Depends(get_db), user : User = Depends(get_current_user)):
    userid =  user.id
    userinfo = db.query(User.first_name, User.last_name).filter_by(id= userid).first()

    if not userinfo:
        return {"error": "User not found"}

    membership = check_user_inroom( userid, roomid, db) #type: ignore
    if membership:
        full_name = f"{userinfo.first_name} {userinfo.last_name}"
        msg_text = f"{full_name} has left the chat."
        stored_msg = store_and_return_message( userid , roomid, msg_text) #type: ignore

        db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).delete()
        db.commit()

        await manager.brodcast(f"{stored_msg['message']}", roomid)

        return {"message": "Leave message stored and broadcasted"}
    else:
        return {"message": "No user in this room"}
    
private_chat_html = """
<!DOCTYPE html>
<html>
<head><title>Private Chat</title></head>
<body>
    <h2>Private Chat Test</h2>
    <label>Your Token:</label><br>
    <input type="text" id="token" style="width: 400px"/><br><br>

    <label>Receiver User ID:</label><br>
    <input type="text" id="receiver_id"/><br><br>

    <button onclick="connectChat()">Connect</button>
    <hr>

    <input type="text" id="message" placeholder="Type your message"/>
    <button onclick="sendMessage()">Send</button>

    <ul id="chatbox"></ul>

<script>
    let socket = null;

    function connectChat() {
        const receiverId = document.getElementById("receiver_id").value;
        const token = document.getElementById("token").value;

        socket = new WebSocket(`ws://localhost:8000/privatechat/${receiverId}?token=${token}`);

        socket.onopen = () => {
            console.log("Connected to private chat.");
        };

        socket.onmessage = (event) => {
            const msg = document.createElement("li");
            msg.textContent = event.data;
            document.getElementById("chatbox").appendChild(msg);
        };

        socket.onclose = () => {
            alert("Connection closed.");
        };
    }

    function sendMessage() {
        const msg = document.getElementById("message").value;
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(msg);
            document.getElementById("message").value = "";
        } else {
            alert("Socket is not connected.");
        }
    }
</script>
</body>
</html>
"""


@router.get("/private")
def private_chat_page():
    return HTMLResponse(private_chat_html)


# Store active WebSocket connections per user
private_connections: Dict[int, WebSocket] = {}

async def send_private_message_history(websocket: WebSocket, user1_id: int, user2_id: int):
    db = SessionLocal()
    try:
        # Query messages where (sender=user1 and receiver=user2) OR (sender=user2 and receiver=user1)
        messages = (
            db.query(PrivateMessage)
            .filter(
                ((PrivateMessage.sender_id == user1_id) & (PrivateMessage.receiver_id == user2_id)) |
                ((PrivateMessage.sender_id == user2_id) & (PrivateMessage.receiver_id == user1_id))
            )
            .order_by(PrivateMessage.sent_at)
            .all()
        )
        
        for msg in messages:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            text = f"Timestamp: {msg.sent_at}\n{sender.first_name} {sender.last_name}: {msg.content}"
            await websocket.send_text(text)
    finally:
        db.close()


@router.websocket("/privatechat/{receiver_id}")
async def private_chat(websocket: WebSocket, receiver_id: int, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        print("Missing token")
        await websocket.close(code=1008)
        return

    try:
        user = decode_token(token, db)
    except ValueError as e:
        print("TOKEN ERROR:", str(e))
        await websocket.close(code=1008)
        return

    await websocket.accept()  # Only after token is valid

    sender_id = user.id

    await send_private_message_history(websocket, sender_id, receiver_id) 
    private_connections[sender_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            msg = store_private_message(sender_id, receiver_id, data)
            response_text = f"Timestamp: {msg['sent_at']}\n{msg['sender']}: {msg['message']}"

            receiver_ws = private_connections.get(receiver_id)
            if receiver_ws:
                await receiver_ws.send_text(response_text)

            await websocket.send_text(response_text)

    except WebSocketDisconnect:
        del private_connections[sender_id]


def store_private_message(sender_id: int, receiver_id: int,  content: str, file_url: str = None, file_type: str = None):
    db = SessionLocal()
    try:
        message = PrivateMessage(
            sender_id=sender_id,
            receiver_id= receiver_id,
            content=content,
            file_url=file_url,
            file_type=file_type
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        sender = db.query(User).filter_by(id=sender_id).first()
        return {
            "sender": f"{sender.first_name} {sender.last_name}",
            "message": message.content,
            "sent_at": message.sent_at
        }
    finally:
        db.close()