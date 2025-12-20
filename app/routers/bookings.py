import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import dependencies, models, schemas
from ..database import get_db

router = APIRouter()


@router.post("", response_model=schemas.BookingRead)
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),  # The Padlock!
):
    # Look up the fare from the Inventory table
    # We'll use the InventoryID from the first passenger to get the price

    # single flight validation: ensures all passengers are on the same flight
    inventory_ids = {p.InventoryID for p in booking_in.passengers}
    if len(inventory_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail="All passengers in a single booking must be on the same flight/class",
        )

    try:
        inventory_id = booking_in.passengers[0].InventoryID
        inventory_item = (
            db.query(models.FlightInventory)
            .filter(models.FlightInventory.InventoryID == inventory_id)
            .first()
        )

        if not inventory_item:
            raise HTTPException(
                status_code=404, detail="FlightInventory/Class not found"
            )

        # Calculate Total (Price * Number of Passengers)
        calculated_total = inventory_item.BaseFare * len(booking_in.passengers)

        # 1. Generate a unique PNR
        pnr = str(uuid.uuid4()).upper()[:6]

        # 2. Create the main Booking record
        # Note: We calculate TotalAmount based on your business logic later,
        # for now we'll use the one from the request or fetch from Flight
        new_booking = models.Booking(
            PNR=pnr,
            UserID=current_user.UserID,
            FlightID=inventory_item.FlightID,
            BookingDate=datetime.utcnow(),
            TotalAmount=calculated_total,
            BookingStatus="Confirmed",
            PaymentStatus="Pending",
        )

        # update seats booked
        inventory_item.SeatsBooked += len(booking_in.passengers)

        db.add(new_booking)
        db.flush()  # This gets us the new_booking.BookingID without committing yet

        # 3. Add the Passengers
        for p_data in booking_in.passengers:
            new_passenger = models.Passenger(
                BookingID=new_booking.BookingID,
                FirstName=p_data.FirstName,
                LastName=p_data.LastName,
                DateOfBirth=p_data.DateOfBirth,
                PassportNumber=p_data.PassportNumber,
                InventoryID=p_data.InventoryID,
            )
            db.add(new_passenger)

        db.commit()
        db.refresh(new_booking)
        return new_booking

    except Exception as e:
        db.rollback()  # If ANYTHING fails, undo all database changes!
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")


#
@router.get("/me", response_model=List[schemas.BookingRead])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    # fetch all bookings for the logged-in user
    bookings = (
        db.query(models.Booking)
        .options(
            joinedload(models.Booking.flight).joinedload(
                models.Flight.departure_airport
            ),
            joinedload(models.Booking.flight).joinedload(models.Flight.arrival_airport),
            joinedload(models.Booking.passengers),
        )
        .filter(models.Booking.UserID == current_user.UserID)
        .all()
    )

    return bookings


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
