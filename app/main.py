from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.routes import communication,chats,auth, profile
from fastapi.staticfiles import StaticFiles
from app.database import engine
from database.models import Base
from fastapi.middleware.cors import CORSMiddleware


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
    allow_methods=["*"],    # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
app.include_router(profile.router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
