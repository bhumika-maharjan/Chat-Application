from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from routes.auth import router


from app.database import SessionLocal, engine
from app.models import Base


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()