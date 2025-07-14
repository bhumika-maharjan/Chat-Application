from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from database.models import Chatroom, RoomMembers, User

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/users")
def search_users(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return db.query(User).filter(User.username.ilike(f"{query}%")).limit(10).all()


@router.get("/rooms")
def search_rooms(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return (
        db.query(Chatroom).filter(Chatroom.roomname.ilike(f"{query}%")).limit(10).all()
    )


@router.get("/users-in-room")
def search_users_in_room(
    room_id: int, query: str = Query(..., min_length=1), db: Session = Depends(get_db)
):
    return (
        db.query(User)
        .join(RoomMembers)
        .filter(RoomMembers.room_id == room_id, User.username.ilike(f"{query}%"))
        .limit(10)
        .all()
    )
