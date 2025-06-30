from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.connection_manager import ConnectionManager
from database.models import RoomMembers, Message, User
from app.utils import get_current_user, check_user_inroom, verify_token
import os
import json
import base64
import uuid

router = APIRouter()

# HTML frontend
html = """
<!DOCTYPE html>
<html>
    <head><title>Chat</title></head>
    <body>
        <form onsubmit="CreateConnection(event)">
            <input id="roomid" placeholder="Enter room id"/>
            <input id="token" placeholder="Enter token" />
            <button>Connect</button>
        </form>
        <hr>
        <form onsubmit="SendMsg(event)">
            <input id="message" placeholder="Enter Message"/>
            <input type="file" id="fileInput"/>
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

            ws = new WebSocket(`ws://localhost:8000/chat/${roomid}?token=${token}`);

            ws.onmessage = (event) => {
    const message = document.createElement("li");
    const text = event.data;

    // If it includes an uploaded file link (our server prefixes "/uploads/")
    if (text.includes("/uploads/")) {
        const parts = text.split(" ");
        const fileUrl = parts.find(p => p.includes("/uploads/"));
        const ext = fileUrl.split('.').pop().toLowerCase();

        const label = document.createElement("p");
        label.textContent = text.replace(fileUrl, "").trim();

        message.appendChild(label);

        if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) {
            const img = document.createElement("img");
            img.src = fileUrl;
            img.style.maxWidth = "200px";
            img.style.border = "1px solid #ccc";
            img.style.marginTop = "5px";
            message.appendChild(img);
        } else {
            // For other file types, create a download link
            const link = document.createElement("a");
            link.href = fileUrl;
            link.textContent = "Download file";
            link.download = "";
            link.target = "_blank";
            message.appendChild(link);
        }

    } else {
        // Regular text message
        message.textContent = text;
    }

    document.getElementById('messages').appendChild(message);
};


            ws.onclose = () => {
                ws = null;
            };
        }

        function SendMsg(event){
            event.preventDefault(); 
            const msg = document.getElementById("message").value;
            const fileInput = document.getElementById("fileInput");
            const file = fileInput.files[0];

            if (file){
                const reader = new FileReader();
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
                };
                reader.readAsDataURL(file);
            } else{
                ws.send(JSON.stringify({
                    type: "text",
                    text: msg
                }));
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
async def websocket_endpoint(websocket: WebSocket, roomid: str, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    userinfo = verify_token(token, db)
    userid = int(userinfo.id)
    roomid = int(roomid)

    await manager.connect(websocket, roomid)
    await send_past_messages_to_user(websocket, roomid)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)

                if data["type"] == "text":
                    stored_msg = store_and_return_message(userid, roomid, data["text"])
                    await manager.brodcast(
                        f"{stored_msg['user']}: {stored_msg['message']} \t Timestamp:{stored_msg['sent_at']}",
                        roomid
                    )

                elif data["type"] == "file":
                    header, base64_data = data["data"].split(",", 1)
                    file_data = base64.b64decode(base64_data)
                    filename = f"{uuid.uuid4()}_{data['filename']}"
                    filepath = os.path.join(UPLOAD_DIR, filename)

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    file_url = f"/{UPLOAD_DIR}/{filename}"

                    stored_msg = store_and_return_message(
                        userid,
                        roomid,
                        content=data.get("text"),
                        file_url=file_url,
                        file_type=data["mimetype"]
                    )

                    await manager.brodcast(
                        f"{stored_msg['user']} sent a file: {file_url} \t Timestamp:{stored_msg['sent_at']}",
                        roomid
                    )

            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON format.")
                continue  # Don't exit the loop

    except WebSocketDisconnect:
        manager.disconnect(websocket, roomid)
        await manager.brodcast(f"{userid} disconnected", roomid)


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
                Message.sent_at
            )
            .join(User, Message.sender_id == User.id)
            .filter(Message.room_id == roomid)
            .order_by(Message.sent_at)
            .all()
        )

        for content, file_url, file_type, first_name, last_name, time in results:
            if file_url:
                # This is a file message (could have optional text)
                message_text = f"{first_name} {last_name} sent a file: {file_url} \t Timestamp:{time}"
            else:
                # Regular text message
                message_text = f"{first_name} {last_name}: {content} \t TimeStamp:{time}"

            await websocket.send_text(message_text)

    finally:
        db.close()


def store_and_return_message(userid: int, room_id: int, content: str = None, file_url: str = None, file_type: str = None) -> dict:
    db = SessionLocal()
    try:
        new_message = Message(
            content=content,
            sender_id=userid,
            room_id=room_id,
            file_url=file_url,
            file_type=file_type
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        user = db.query(User).filter(User.id == userid).first()

        return {
            "user": user.first_name + user.last_name,
            "message": new_message.content or "",
            "file_url": new_message.file_url,
            "file_type": new_message.file_type,
            "sent_at": new_message.sent_at
        }
    finally:
        db.close()


@router.get('/leftchat/{roomid}')
async def left_chat(roomid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    userid = user.id
    userinfo = db.query(User.first_name, User.last_name).filter_by(id=userid).first()

    if not userinfo:
        return {"error": "User not found"}

    membership = check_user_inroom(userid, roomid, db)
    if membership:
        full_name = f"{userinfo.first_name} {userinfo.last_name}"
        msg_text = f"{full_name} has left the chat."
        stored_msg = store_and_return_message(userid, roomid, msg_text)

        db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).delete()
        db.commit()

        await manager.brodcast(f"{stored_msg['message']}", roomid)
        return {"message": "Leave message stored and broadcasted"}
    else:
        return {"message": "No user in this room"}
