# app/routers/flights.py

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

# Import the SQLAlchemy Models and Pydantic Schemas
from .. import models, schemas
from ..database import get_db

router = APIRouter()

# --- Endpoint 1: Search Flights ---


# This endpoint handles the main customer search query.
# It uses query parameters for search criteria.
@router.get("/search", response_model=List[schemas.FlightRead])
def search_flights(
    # Query parameters for the search
    origin_iata: str = Query(
        ..., min_length=3, max_length=3, description="Origin IATA Code (e.g., LHR)"
    ),
    destination_iata: str = Query(
        ..., min_length=3, max_length=3, description="Destination IATA Code (e.g., JFK)"
    ),
    departure_date: date = Query(..., description="The date of departure (YYYY-MM-DD)"),
    passengers: int = Query(1, gt=0, description="Number of passengers"),
    db: Session = Depends(get_db),
):
    """
    Allows users to search for available flights based on origin, destination, and date.

    The search logic involves filtering by date and checking inventory for available seats.
    """

    # --- 1. Find Airport IDs from IATA Codes ---
    # Convert IATA codes to IDs for use in the Flights table query

    origin_airport = (
        db.query(models.Airport).filter(models.Airport.IATACode == origin_iata).first()
    )
    destination_airport = (
        db.query(models.Airport)
        .filter(models.Airport.IATACode == destination_iata)
        .first()
    )

    if not origin_airport or not destination_airport:
        raise HTTPException(
            status_code=404, detail="One or both airport codes are invalid."
        )

    origin_id = origin_airport.AirportID
    destination_id = destination_airport.AirportID

    # --- 2. Build the Core Flight Query ---
    # Filter for the correct route and date.
    # SQLAlchemy's date comparison handles the DATETIMEOFFSET column accurately when comparing to a date object.

    flights_query = db.query(models.Flight).filter(
        models.Flight.DepartureAirportID == origin_id,
        models.Flight.ArrivalAirportID == destination_id,
        # Check if the departure date matches the date part of the DATETIMEOFFSET
        models.Flight.DepartureDateTime >= departure_date,
        models.Flight.DepartureDateTime < departure_date + timedelta(days=1),
    )

    # --- 3. Filter by Inventory/Availability ---
    # We join the Flights table with the Inventory table and check if any inventory class
    # has enough available seats for the requested number of passengers.

    available_flights = (
        flights_query.join(models.FlightInventory)
        .filter(
            (models.FlightInventory.TotalSeats - models.FlightInventory.SeatsBooked)
            >= passengers
        )
        .distinct()
        .all()
    )

    # --- 4. Return the Results ---
    # The `response_model=List[schemas.FlightRead]` automatically validates the data
    # and includes the nested airport and aircraft details, thanks to the relationships
    # defined in `models.py` and `schemas.py`'s `orm_mode=True`.

    return available_flights


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
