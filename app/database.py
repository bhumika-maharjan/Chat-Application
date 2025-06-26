from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = FastAPI()
engine = create_engine("postgresql://postgres:admin@localhost:5432/chatapp", echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()