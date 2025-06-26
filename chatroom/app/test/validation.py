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

def check_user_inroom(userid: int, roomid: int, db: Session):
    membership = db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).first()
    return membership is not None