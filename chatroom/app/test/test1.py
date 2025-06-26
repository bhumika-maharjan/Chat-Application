from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import User,Chatroom,RoomMembers
from app.test.validation import check_user_inroom

# Initialize FastAPI app
app = FastAPI()

# SQLAlchemy setup
engine = create_engine("postgresql://postgres:admin@localhost:5432/chatapp", echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class CreateTable(BaseModel):
    room_name: str
    is_private: bool
    created_by: int

class JoinRoom(BaseModel):
    user_id: int
    room_id: int

# Create chatroom endpoint
@app.post("/createtable")
def create_table(tableinfo: CreateTable, db: Session = Depends(get_db)):
    # Step 1: Create chatroom
    new_room = Chatroom(
        roomname=tableinfo.room_name,
        is_private=tableinfo.is_private,
        is_deleted=False,
        created_by=tableinfo.created_by
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    # Step 2: Add creator as member
    room_member = RoomMembers(
        user_id=tableinfo.created_by,
        room_id=new_room.id,
        is_admin=True
    )
    db.add(room_member)
    db.commit()

    return {"message": "Chatroom created successfully", "room_id": new_room.id}



@app.get("/getroom")
def get_room(db: Session = Depends(get_db)):
    chat_room_names = db.query(Chatroom.roomname).all()
    room_list = [room[0] for room in chat_room_names]  # Extract values from tuples
    return {"chatrooms": room_list}

@app.post("/joingroup")
def join_room(members: JoinRoom, db: Session = Depends(get_db)):
    room = db.query(Chatroom).filter(Chatroom.id == members.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    user_exist = check_user_inroom(members.user_id,members.room_id,db)
    if user_exist:
        return {"message" : "Already in chat"}
    else:
        new_member = RoomMembers(
            user_id=members.user_id,
            room_id=members.room_id,
            is_admin=False
        )
        db.add(new_member)
        db.commit()

        return {"message": f"Joined chat room '{room.roomname}' successfully"}