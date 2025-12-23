from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_admin_user

# Import the SQLAlchemy Models and Pydantic Schemas
from .. import models, schemas
from ..database import get_db

router = APIRouter()


# --- Endpoint 1: Search Flights ---
@router.get("", response_model=List[schemas.AirportRead])
def get_airports(
    db: Session = Depends(get_db), admin_user: models.User = Depends(get_admin_user)
):
    return db.query(models.Airport).all()
