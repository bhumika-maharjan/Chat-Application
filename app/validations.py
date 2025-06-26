from sqlalchemy.orm import Session
from database.models import RoomMembers

def check_user_inroom(userid: int, roomid: int, db: Session):
    membership = db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).first()
    return membership is not None