# app/routers/flights.py
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, cast
from sqlalchemy.orm import Session, aliased, joinedload
from starlette.types import HTTPExceptionHandler

from app.dependencies import get_admin_user

# Import the SQLAlchemy Models and Pydantic Schemas
from .. import models, schemas
from ..database import get_db

router = APIRouter()


# --- Endpoint 1: Search Flights ---
@router.get("", response_model=List[schemas.FlightRead])
def search_flights(
    origin_code: Optional[str] = Query(None),
    destination_code: Optional[str] = Query(None),
    travel_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    # 1. Create Aliases for the Airport table
    DepartureAirport = aliased(models.Airport)
    ArrivalAirport = aliased(models.Airport)

    # 2. Start the query using joinedload for the response objects
    query = db.query(models.Flight).options(
        joinedload(models.Flight.departure_airport),
        joinedload(models.Flight.arrival_airport),
        joinedload(models.Flight.aircraft),
        joinedload(models.Flight.inventory_items),
    )

    # 3. Filter by Origin using the Alias
    if origin_code:
        query = query.join(
            DepartureAirport,
            models.Flight.DepartureAirportID == DepartureAirport.AirportID,
        ).filter(DepartureAirport.IATACode == origin_code.upper())

    # 4. Filter by Destination using the Alias
    if destination_code:
        query = query.join(
            ArrivalAirport, models.Flight.ArrivalAirportID == ArrivalAirport.AirportID
        ).filter(ArrivalAirport.IATACode == destination_code.upper())

    # 5. Filter by Date
    if travel_date:
        query = query.filter(cast(models.Flight.DepartureDateTime, Date) == travel_date)

    return query.all()


# --- Endpoint 2: Get Flight Details (including Inventory) ---


@router.get("/{flight_id}", response_model=schemas.FlightRead)
def get_flight_details(flight_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the full details of a single flight, including airport, aircraft, and inventory.
    """
    flight = db.query(models.Flight).filter(models.Flight.FlightID == flight_id).first()

    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")

    # To include the inventory details in the response, we need to explicitly load them.
    # The FlightRead schema doesn't yet include the InventoryRead list, but we can
    # create a detailed schema later that does. For now, let's just return the core FlightRead data.
    return flight


# Create flights by user with admin privileges
@router.post("", response_model=schemas.FlightRead)
def create_flight(
    flight_in: schemas.FlightCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user),
):
    try:
        new_flight = models.Flight(
            FlightNumber=flight_in.FlightNumber,
            DepartureAirportID=flight_in.DepartureAirportID,
            ArrivalAirportID=flight_in.ArrivalAirportID,
            AircraftID=flight_in.AircraftID,
            DepartureDateTime=flight_in.DepartureDateTime,
            ArrivalDateTime=flight_in.ArrivalDateTime,
            BasePrice=flight_in.BasePrice,
            Status=flight_in.Status,
        )

        db.add(new_flight)
        db.flush()  # send record to db, generates id but data not commited

        for item in flight_in.inventory_items:
            inventory = models.FlightInventory(
                FlightID=new_flight.FlightID,
                ClassCode=item.ClassCode,
                BaseFare=item.BaseFare,
                TotalSeats=item.TotalSeats,
            )

            db.add(inventory)

        # save all db transactions permanently
        db.commit()

        db.refresh(new_flight)
        return new_flight

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create flight: {str(e)}"
        )


# update flights route


@router.put("/{flight_id}", response_model=schemas.FlightRead)
def update_flight(
    flight_id: int,
    flight_in: schemas.FlightUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user),
):
    flight = db.query(models.Flight).filter(models.Flight.FlightID == flight_id).first()

    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")

    update_data = flight_in.dict(exclude_unset=True)  # converts schema to dictionary

    try:
        for key, item in update_data.items():
            setattr(flight, key, item)

        db.commit()
        db.refresh(flight)
        return flight

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Update failed. Check your data. Error: {str(e)}"
        )
