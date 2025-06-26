from fastapi import FastAPI
from app.routes import chats,websockets

app =  FastAPI()

app.include_router(chats.router)
app.include_router(websockets.router)