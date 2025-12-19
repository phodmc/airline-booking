# app/routers/flights.py
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, cast
from sqlalchemy.orm import Session, aliased, joinedload

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
