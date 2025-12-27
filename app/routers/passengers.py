from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import dependencies, models, schemas
from ..database import get_db

router = APIRouter()


@router.put("/{passenger_id}", response_model=schemas.PassengerRead)
def update_passenger(
    passenger_id: int, data: schemas.PassengerUpdate, db: Session = Depends(get_db)
):
    passenger = db.query(models.Passenger).filter_by(PassengerID=passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    passenger.FirstName = data.FirstName
    passenger.LastName = data.LastName
    passenger.PassportNumber = data.PassportNumber
    passenger.DateOfBirth = data.DateOfBirth

    db.commit()
    return passenger
