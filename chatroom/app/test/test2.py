from fastapi import WebSocket, WebSocketDisconnect, FastAPI
from sqlalchemy import create_engine
from fastapi.responses import HTMLResponse
from typing import Optional

app = FastAPI()
engine = create_engine("postgresql://postgres:admin@localhost:5432/chatapp")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <form action="" onsubmit="CreateConnection(event)">
            <input id="userid" placeholder="Enter user id"/>
            <input id="roomid" placeholder="Enter room id"/>
            <input id="token" placeholder="Enter token" />
            <button>Find chat</button>
        </form>

        <hr>
        
        <form action="" onsubmit="SendMsg(event)">
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
                console.log("Received:", event.data);
                var message = document.createElement("li")
                var content =  document.createTextNode(event.data);
                message.appendChild(content);
                document.getElementById('messages').appendChild(message)
            };
        }

        function SendMsg(event){
            event.preventDefault(); 
            msg = document.getElementById("message").value
            ws.send(msg)
        }
    </script>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.rooms_active_user : dict[int,list[WebSocket]] = {}

    async def connect(self, websocket : WebSocket, roomid: int):
        await websocket.accept()
        if roomid not in self.rooms_active_user:
            self.rooms_active_user[roomid] = []
        self.rooms_active_user[roomid].append(websocket)
    
    async def brodcast(self, msg : str,roomid : int):
        if roomid in self.rooms_active_user:
            for user in self.rooms_active_user[roomid]:
                await user.send_text(msg)

    def disconnect(self, websocket : WebSocket, roomid: int):
        if roomid in self.rooms_active_user:
            self.rooms_active_user[roomid].remove(websocket)
            if not self.rooms_active_user[roomid]:
                del self.rooms_active_user[roomid]



manager = ConnectionManager()

@app.get('/home')
def displayhomepage():
    return HTMLResponse(html)

def verify_token(token : str):
    if token == "mystr":
        return True
    return False


@app.websocket("/users/{userid}/")
async def websocket_endpoint(websocket: WebSocket, userid: str):
    roomid = websocket.query_params.get("q")
    token = websocket.query_params.get("token")
    verifytoken = verify_token(token)
    if verifytoken:
        await manager.connect(websocket,int(roomid))
        try:
            while True:
                data = await websocket.receive_text()
                await manager.brodcast(f"From:{userid} Msg:{data}",int(roomid))
        except WebSocketDisconnect:
            manager.disconnect(websocket,int(roomid))
            await manager.brodcast(f"{userid} diconnected",int(roomid))
    else:
        await websocket.close(code=1008)
        return
