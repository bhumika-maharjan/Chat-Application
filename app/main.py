from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.routes import communication,chats,auth, profile

from app.database import engine
from app.models import Base
from fastapi.staticfiles import StaticFiles
from database.database import engine
from database.models import Base


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(chats.router)
app.include_router(communication.router)
app.include_router(auth.router)
<<<<<<< HEAD
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

=======
app.include_router(profile.router)
>>>>>>> 350c42eee861b6be1479764616a1489415c75f1b

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/login")
