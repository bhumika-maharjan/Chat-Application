from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.routes import communication,chats,auth
from routes.auth import router


from app.database import SessionLocal, engine
from app.models import Base


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/login")
