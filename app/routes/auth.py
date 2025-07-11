from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from datetime import datetime, timedelta, timezone
from typing import List

from database.models import User
from app.schemas import UserCreate, UserLogin, UserResponse
from app.utils import hash_password, verify_password
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_pw = hash_password(user.password)
    db_user = User(
        username=user.username,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        email=user.email,
        password=hashed_pw    
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password): #type: ignore
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(db_user.id),
        "exp": expire
    }
    access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM) #type: ignore

    return {"access token": f"bearer {access_token}"}

    # return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users