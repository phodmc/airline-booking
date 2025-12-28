import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from .. import dependencies, models, schemas
from ..database import get_db

router = APIRouter()


# seat number generator
# def gen_seat_label(index):
#     row = (index // 6) + 1
#     letter = ["A", "B", "C", "D", "E", "F"][index % 6]
#     return f"{row}{letter}"


@router.post("", response_model=schemas.BookingRead)
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),  # The Padlock!
):
    try:
        inventory_id = booking_in.passengers[0].InventoryID
        passenger_count = len(booking_in.passengers)

        # Quick lookup to get the FlightID needed for the procedure
        inventory_item = db.query(models.FlightInventory).filter_by(InventoryID=inventory_id).first()
        if not inventory_item:
            raise HTTPException(status_code=404, detail="Inventory not found")

        # 1. EXECUTE PROCEDURE #5: sp_CreateBooking
        # This procedure uses fn_GeneratePNR and fn_CalculateTotalAmount internally
        # and returns the NewBookingID and the PNR.
        booking_result = db.execute(
            text(
                "EXEC sp_CreateBooking @UserID=:uid, @FlightID=:fid, @InventoryID=:iid, @PassengerCount=:pc"
            ),
            {
                "uid": current_user.UserID,
                "fid": inventory_item.FlightID,
                "iid": inventory_id,
                "pc": passenger_count,
            },
        ).fetchone()

        new_booking_id = booking_result["NewBookingID"]
        assigned_pnr = booking_result.["AssignedPNR"]

        # 2. EXECUTE PROCEDURE #3: sp_CreatePassenger
        # This loop runs the passenger procedure for each person
        # It uses fn_GenerateSeatLabel internally.
        for p_data in booking_in.passengers:
            db.execute(
                text("""
                    EXEC sp_CreatePassenger
                    @BookingID=:bid, @InventoryID=:iid, @FirstName=:fn,
                    @LastName=:ln, @DateOfBirth=:dob, @PassportNumber=:pn
                """),
                {
                    "bid": new_booking_id,
                    "iid": p_data.InventoryID,
                    "fn": p_data.FirstName,
                    "ln": p_data.LastName,
                    "dob": p_data.DateOfBirth,
                    "pn": p_data.PassportNumber,
                },
            )

        db.commit()

        # 3. Fetch the final record using our View (Optional but cool) or standard Query
        # We fetch it back so FastAPI can return the full object to the frontend
        final_booking = (
            db.query(models.Booking)
            .options(joinedload(models.Booking.passengers), joinedload(models.Booking.flight))
            .filter(models.Booking.BookingID == new_booking_id)
            .first()
        )
        return final_booking

    except Exception as e:
        db.rollback()  # If ANYTHING fails, undo all database changes!
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")


# get all bookings for a user
# __________________________
@router.get("/me", response_model=List[schemas.BookingRead])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    # fetch all bookings for the logged-in user
    # Query the VIEW we created
    # This automatically includes FlightNumber, Times, and PassengerCount
    query = text("SELECT * FROM vw_MyBookings WHERE UserID = :uid")
    result = db.execute(query, {"uid": current_user.UserID})

    return result.mappings().all()


# get single booking by PNR
# ___________________________
@router.get("/{pnr}", response_model=schemas.BookingRead)
def get_booking_by_pnr(
    pnr: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    # find bookings that belong to current user and matches pnr
    booking = (
        db.query(models.Booking)
        .options(
            joinedload(models.Booking.flight).joinedload(
                models.Flight.departure_airport
            ),
            joinedload(models.Booking.flight).joinedload(models.Flight.arrival_airport),
            joinedload(models.Booking.passengers),
        )
        .filter(
            models.Booking.PNR == pnr.upper(),
            models.Booking.UserID == current_user.UserID,
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404, detail=f"Booking with PNR {pnr} not found or access denied"
        )

    return booking


# get booking by pnr and last name
# _______________________________


@router.get("/pnr/{pnr}/{last_name}", response_model=schemas.BookingRead)
def get_trip_by_pnr_and_name(pnr: str, last_name: str, db: Session = Depends(get_db)):
    # find bookings that belong to matches pnr and last name
    booking = (
        db.query(models.Booking)
        .options(
            joinedload(models.Booking.flight).joinedload(
                models.Flight.departure_airport
            ),
            joinedload(models.Booking.flight).joinedload(models.Flight.arrival_airport),
            joinedload(models.Booking.passengers),
        )
        .filter(
            models.Booking.PNR == pnr.upper(),
            models.Passenger.LastName.ilike(last_name),
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail=f"Booking with PNR {pnr} not found or unknown last name",
        )

    return booking


#


# flight/booking cancellation
#  ____________________________
@router.put("/{pnr}/cancel", response_model=schemas.BookingRead)
def cancel_booking(
    pnr: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    try:
        # 1. Use the Stored Procedure to handle the cancellation
        # The trigger 'trig_RestoreInventoryOnCancel' will automatically free the seats!
        db.execute(text("EXEC sp_CancelBooking @PNR = :pnr"), {"pnr": pnr.upper()})
        db.commit()

        # fetch booking and ensure ownership of current user
        booking = (
            db.query(models.Booking)
            .filter(
                models.Booking.PNR == pnr.upper(),
                models.Booking.UserID == current_user.UserID,
            )
            .first()
        )

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        db.refresh(booking)
        return booking

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {str(e)}")
