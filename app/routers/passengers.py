from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import dependencies, models, schemas
from ..database import get_db

router = APIRouter()


@router.put("/{passenger_id}", response_model=schemas.PassengerRead)
def update_passenger(
    passenger_id: int, data: schemas.PassengerUpdate, db: Session = Depends(get_db)
):
    # check if passenger exists
    passenger = db.query(models.Passenger).filter_by(PassengerID=passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    try:
        # 2. Use the Stored Procedure to perform the update
        db.execute(
            text("""
                    EXEC sp_UpdatePassengerDetails
                    @PassengerID = :pid,
                    @FirstName = :fn,
                    @LastName = :ln,
                    @PassportNumber = :pn
                """),
            {
                "pid": passenger_id,
                "fn": data.FirstName,
                "ln": data.LastName,
                "pn": data.PassportNumber,
            },
        )
        db.commit()

        # 3. Refresh the object to get the updated data back from the DB
        db.refresh(passenger)
        return passenger

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
