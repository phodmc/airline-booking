# schemas.py

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.fields import computed_field


# --- 1. Airport Schemas ---
class AirportBase(BaseModel):
    IATACode: str = Field(..., max_length=3)
    Name: str = Field(..., max_length=100)
    City: str = Field(..., max_length=50)
    Country: str = Field(..., max_length=50)
    TimeZone: Optional[str] = Field(None, max_length=50)


class AirportRead(AirportBase):
    AirportID: int

    class Config:
        from_attributes = (
            True  # Essential for Pydantic to read data directly from SQLAlchemy models
        )


# --- 2. Aircraft Schemas ---
class AircraftBase(BaseModel):
    ModelCode: str = Field(..., max_length=4)
    Manufacturer: Optional[str] = Field(None, max_length=50)
    TotalSeats: int = Field(..., gt=0)
    Range_km: Optional[int] = None


class AircraftRead(AircraftBase):
    AircraftID: int

    class Config:
        from_attributes = True


# --- 4. Inventory Schemas ---
class InventoryBase(BaseModel):
    ClassCode: str = Field(..., max_length=1)  # Y, J, F
    BaseFare: Decimal = Field(..., ge=0)
    TotalSeats: int = Field(..., gt=0)
    IsRefundable: bool = True


class InventoryRead(InventoryBase):
    InventoryID: int
    FlightID: int
    SeatsBooked: int

    # Property to show available seats
    @computed_field
    def SeatsAvailable(self) -> int:
        return self.TotalSeats - self.SeatsBooked

    class Config:
        from_attributes = True


# --- 3. Flight Schemas (for Searching and Creation) ---
class FlightBase(BaseModel):
    FlightNumber: str = Field(..., max_length=10)
    DepartureAirportID: int
    ArrivalAirportID: int
    AircraftID: int
    DepartureDateTime: datetime  # Pydantic will handle time-zone-aware datetime
    ArrivalDateTime: datetime
    BasePrice: Decimal = Field(..., ge=0)
    Status: str = "Scheduled"


class FlightRead(FlightBase):
    FlightID: int

    # Nested schemas to return related object data (e.g., airport names)
    departure_airport: AirportRead
    arrival_airport: AirportRead
    aircraft: AircraftRead
    inventory_items: List[InventoryRead]

    class Config:
        from_attributes = True


# --- 5. User Schemas ---
class UserCreate(BaseModel):
    Email: str = Field(..., max_length=100)
    Password: str = Field(
        ..., min_length=8, max_length=72
    )  # The raw password before hashing
    FirstName: str = Field(..., max_length=50)
    LastName: str = Field(..., max_length=50)
    PhoneNumber: Optional[str] = Field(None, max_length=20)
    DateOfBirth: Optional[date] = None


class UserRead(BaseModel):
    UserID: int
    Email: str
    FirstName: str
    LastName: str
    CreatedDate: datetime
    IsAdmin: bool

    class Config:
        from_attributes = True


# --- 6. Booking and Passenger Schemas (Simplified) ---
class PassengerBase(BaseModel):
    FirstName: str = Field(..., max_length=50)
    LastName: str = Field(..., max_length=50)
    DateOfBirth: date
    PassportNumber: Optional[str] = Field(None, max_length=30)
    SeatNumber: Optional[str] = Field(None, max_length=5)
    # The InventoryID for the specific class purchased must be provided during booking
    InventoryID: int


class BookingCreate(BaseModel):
    # This is what the user sends to the API
    passengers: List[PassengerBase]


class BookingRead(BaseModel):
    BookingID: int
    PNR: str
    UserID: int
    BookingDate: datetime
    TotalAmount: Decimal
    PaymentStatus: str
    BookingStatus: str

    flight: Optional[FlightRead]
    passengers: List["PassengerRead"]  # Forward reference needed for recursive schemas

    class Config:
        from_attributes = True


# Define PassengerRead after BookingRead uses a forward reference
class PassengerRead(PassengerBase):
    PassengerID: int
    BookingID: int

    class Config:
        from_attributes = True


# Final configuration for recursive schemas (BookingRead uses PassengerRead)
BookingRead.model_rebuild()
