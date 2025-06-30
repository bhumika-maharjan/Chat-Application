from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.routes import communication,chats,auth, profile
from fastapi.staticfiles import StaticFiles
from app.database import engine
from database.models import Base


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
app.include_router(profile.router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
