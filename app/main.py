from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.routes import communication,chats,auth

from app.database import engine
from app.models import Base
from fastapi.staticfiles import StaticFiles


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/login")
