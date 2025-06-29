from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from app import  schemas
from database import models
from app.validations import get_current_user
from app.utils import verify_password, hash_password

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)

@router.get("/", response_model= schemas.UserOut)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.put("/update", response_model=schemas.UserOut)
def update_profile(updated:  schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    for field, value in updated.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/change-password")
def change_password(payload: schemas.ChangePassword, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(status_code=400, detail = "old password is incorrect")
    current_user.password = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}    