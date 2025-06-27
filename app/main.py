from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from datetime import datetime,timedelta, timezone


from app.database import SessionLocal, engine
from app.models import Base, User
from app.schemas import UserCreate, UserLogin, UserResponse
from app.utils import hash_password, verify_password
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.route import chats, communication
from app.database import get_db

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(chats.router)
app.include_router(communication.router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
