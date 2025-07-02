from fastapi import APIRouter, Depends, HTTPException
from app.schemas import CreateTable, JoinRoom
from database.models import Chatroom, RoomMembers, User
from app.database import get_db
from sqlalchemy.orm import Session
from app.utils import get_current_user, check_user_inroom, hash_password, verify_password

router = APIRouter()

@router.post("/creategroup")
def create_table(tableinfo: CreateTable, db: Session = Depends(get_db), user : User = Depends(get_current_user)):

    if tableinfo.is_private and not tableinfo.password:
        raise HTTPException(status_code=400, detail="Password required for private room")
    
    hashed_password = (
        hash_password(tableinfo.password) if tableinfo.is_private else None
    )
    # Step 1: Create chatroom
    new_room = Chatroom(
        roomname=tableinfo.room_name,
        is_private=tableinfo.is_private,
        is_deleted=False,
        created_by= user.id,
        password=hashed_password
        
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    # Step 2: Add creator as member
    room_member = RoomMembers(
        user_id= user.id,
        room_id=new_room.id,
        is_admin=True
    )
    db.add(room_member)
    db.commit()

    return {"message": "Chatroom created successfully", "room_id": new_room.id}

@router.get("/getgroups")
def get_room(db: Session = Depends(get_db)):
    chat_room_names = db.query(Chatroom.roomname).all()
    room_list = [room[0] for room in chat_room_names]  # Extract values from tuples
    return {"chatrooms": room_list}

@router.post("/joingroup")
def join_room(members: JoinRoom, db: Session = Depends(get_db), user : User = Depends(get_current_user)):
    room = db.query(Chatroom).filter(Chatroom.id == members.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    user_exist = check_user_inroom(user.id,members.room_id,db)
    if user_exist:
        return {"message" : "Already in chat"}
    
    if room.is_private:
        if not members.password:
            raise HTTPException(status_code=401, detail="Password required to join this room")
        if not verify_password(members.password, room.password):
            raise HTTPException(status_code=403, detail="Incorrect password")

    new_member = RoomMembers(
        user_id=user.id,
        room_id=members.room_id,
        is_admin=False
    )
    db.add(new_member)
    db.commit()
    return {"message": f"Joined chat room '{room.roomname}' successfully"}

