from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.database import engine
from app.routes import auth, chats, communication, home, profile
from database.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI()
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
app.include_router(profile.router)

app.mount(
    "/profile_images",
    StaticFiles(directory=UPLOAD_DIR),  # app/uploads/profile_pics/
    name="profile_images",
)

app.include_router(home.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
