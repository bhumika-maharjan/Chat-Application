from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = FastAPI()
engine = create_engine("postgresql://postgres:admin@localhost:5432/chatapp")

class CreateTable(BaseModel):
    room_name : str
    is_private : bool
    created_by : int

class JoinRoom(BaseModel):
    user_id : int
    room_id : int

@app.post("/createtable")
def create_table(tableinfo: CreateTable):
    with engine.connect() as conn:
        # Step 1: Insert into chatroom
        insert_query = text("""
            INSERT INTO chatroom (roomname, is_private, is_deleted, created_by)
            VALUES (:roomname, :is_private, false, :created_by)
        """)
        conn.execute(insert_query, {
            "roomname": tableinfo.room_name,
            "is_private": tableinfo.is_private,
            "created_by": tableinfo.created_by
        })
        conn.commit()

        # Step 2: Get the new chatroom's ID
        select_query = text("""
            SELECT id FROM chatroom
            WHERE roomname = :roomname AND created_by = :created_by AND is_private = :is_private
            ORDER BY id DESC LIMIT 1
        """)
        result = conn.execute(select_query, {
            "roomname": tableinfo.room_name,
            "created_by": tableinfo.created_by,
            "is_private": tableinfo.is_private
        }).fetchone()

        if not result:
            return {"error": "Failed to retrieve room ID"}

        room_id = result[0]

        # Step 3: Insert creator as admin in room_members
        member_query = text("""
            INSERT INTO room_members (user_id, room_id, is_admin)
            VALUES (:user_id, :room_id, true)
        """)
        conn.execute(member_query, {
            "user_id": tableinfo.created_by,
            "room_id": room_id
        })
        conn.commit()

    return {"message": "Chatroom created successfully", "room_id": room_id}


@app.get("/getroom")
def get_room():
    with engine.connect() as conn:
        query = text("SELECT roomname FROM chatroom")
        result = conn.execute(query)
        rooms = [row._mapping["roomname"] for row in result] 
    return {"chatrooms": rooms}

@app.post("/joingroup")
def join_room(members : JoinRoom):
    with engine.connect() as conn:
        member_query = text("""
            INSERT INTO room_members (user_id, room_id, is_admin)
            VALUES (:user_id, :room_id, false)
        """)
        conn.execute(member_query, {
            "user_id": members.user_id,
            "room_id": members.room_id
        })
        conn.commit()

        select_query = text("""
                SELECT roomname FROM chatroom
                WHERE id = :room_id
            """)
        result = conn.execute(select_query, {
            "room_id": members.room_id
        }).fetchone()

        if not result:
            return {"error": "Chatroom not found"}

        roomname = result[0]

    return {"message": f"Joined chat room '{roomname}' successfully"}