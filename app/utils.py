from passlib.context import CryptContext
from fastapi import WebSocket
from fastapi import Header, HTTPException, Depends,Query
from database.models import User, RoomMembers
from app.config import SECRET_KEY,ALGORITHM
import jwt
from app.database import get_db
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password:str, hashed_password: str)->bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(authorization: str | None = Header(...), db: Session = Depends(get_db)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token scheme")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        user_id = payload.get("sub")
        user = db.query(User).filter_by(id=user_id).first()
        print(user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
def verify_token(obtained_token: str = Query(...), db : Session = Depends(get_db)):
    try:
        # scheme, token = obtained_token.split()
        # if scheme.lower() != "bearer":
        #     raise HTTPException(status_code=401, detail="Invalid token scheme")
        if obtained_token.lower().startswith("bearer "):
            token = obtained_token[7:]  # strip first 7 chars (bearer + space)
        else:
            token = obtained_token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        print(f"user_id from token: {user_id}")
        user = db.query(User).filter_by(id = user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
def check_user_inroom(userid: int, roomid: int, db: Session):
    membership = db.query(RoomMembers).filter_by(user_id=userid, room_id=roomid).first()
    return membership is not None