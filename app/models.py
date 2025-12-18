# models.py

from sqlalchemy import (
    CHAR,
    DECIMAL,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.mssql import DATETIMEOFFSET
from sqlalchemy.orm import relationship

from .database import Base


# --- 1. Airports Model ---
class Airport(Base):
    __tablename__ = "Airports"

    AirportID = Column(Integer, primary_key=True, index=True)
    IATACode = Column(CHAR(3), unique=True, nullable=False)
    Name = Column(String(100), nullable=False)
    City = Column(String(50), nullable=False)
    Country = Column(String(50), nullable=False)
    TimeZone = Column(String(50))

    # Relationships
    # Define relationships to Flight table for both departure and arrival
    departures = relationship(
        "Flight",
        foreign_keys="[Flight.DepartureAirportID]",
        back_populates="departure_airport",
    )
    arrivals = relationship(
        "Flight",
        foreign_keys="[Flight.ArrivalAirportID]",
        back_populates="arrival_airport",
    )


# --- 2. Aircraft Model ---
class Aircraft(Base):
    __tablename__ = "Aircraft"

    AircraftID = Column(Integer, primary_key=True, index=True)
    ModelCode = Column(CHAR(4), unique=True, nullable=False)
    Manufacturer = Column(String(50))
    TotalSeats = Column(Integer, nullable=False)  # Use Integer for SMALLINT
    Range_km = Column(Integer)

    # Relationship to Flights
    flights = relationship("Flight", back_populates="aircraft")


# --- 3. Flights Model ---
class Flight(Base):
    __tablename__ = "Flights"

    FlightID = Column(Integer, primary_key=True, index=True)
    FlightNumber = Column(String(10), nullable=False)
    DepartureAirportID = Column(
        Integer, ForeignKey("Airports.AirportID"), nullable=False
    )
    ArrivalAirportID = Column(Integer, ForeignKey("Airports.AirportID"), nullable=False)
    AircraftID = Column(Integer, ForeignKey("Aircraft.AircraftID"), nullable=False)
    # Use DATETIMEOFFSET for time zone aware storage
    DepartureDateTime = Column(DATETIMEOFFSET, nullable=False)
    ArrivalDateTime = Column(DATETIMEOFFSET, nullable=False)
    BasePrice = Column(DECIMAL(10, 2), nullable=False)
    Status = Column(String(20), default="Scheduled", nullable=False)

    # Relationships (Allows joining between tables easily)
    departure_airport = relationship(
        "Airport", foreign_keys=[DepartureAirportID], back_populates="departures"
    )
    arrival_airport = relationship(
        "Airport", foreign_keys=[ArrivalAirportID], back_populates="arrivals"
    )
    aircraft = relationship("Aircraft", back_populates="flights")
    inventory_items = relationship("FlightInventory", back_populates="flight")
    bookings = relationship("Booking", back_populates="flight")


# --- 4. FlightInventory Model ---
class FlightInventory(Base):
    __tablename__ = "FlightInventory"

    InventoryID = Column(Integer, primary_key=True, index=True)
    FlightID = Column(Integer, ForeignKey("Flights.FlightID"), nullable=False)
    ClassCode = Column(CHAR(1), nullable=False)
    BaseFare = Column(DECIMAL(10, 2), nullable=False)
    TotalSeats = Column(Integer, nullable=False)
    SeatsBooked = Column(Integer, default=0, nullable=False)
    IsRefundable = Column(Boolean, default=True, nullable=False)

    # Relationship to Flight and Passengers
    flight = relationship("Flight", back_populates="inventory_items")
    passengers = relationship("Passenger", back_populates="inventory_item")


# --- 5. Users Model ---
class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, index=True)
    Email = Column(String(100), unique=True, nullable=False)
    HashedPassword = Column(CHAR(60), nullable=False)
    FirstName = Column(String(50), nullable=False)
    LastName = Column(String(50), nullable=False)
    PhoneNumber = Column(String(20))
    DateOfBirth = Column(Date)
    CreatedDate = Column(
        DateTime, nullable=False
    )  # DATETIME2 equivalent in SQLAlchemy is DateTime

    # Relationship to Bookings
    bookings = relationship("Booking", back_populates="user")


# --- 6. Bookings Model ---
class Booking(Base):
    __tablename__ = "Bookings"

    BookingID = Column(Integer, primary_key=True, index=True)
    PNR = Column(CHAR(6), unique=True, nullable=False)
    UserID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    FlightID = Column(Integer, ForeignKey("Flights.FlightID"), nullable=False)
    BookingDate = Column(DateTime, nullable=False)
    TotalAmount = Column(DECIMAL(10, 2), nullable=False)
    PaymentStatus = Column(String(20), nullable=False)
    BookingStatus = Column(String(20), nullable=False)

    # Relationships
    user = relationship("User", back_populates="bookings")
    passengers = relationship("Passenger", back_populates="booking")
    flight = relationship("Flight", back_populates="bookings")


# --- 7. Passengers Model ---
class Passenger(Base):
    __tablename__ = "Passengers"

    PassengerID = Column(Integer, primary_key=True, index=True)
    BookingID = Column(Integer, ForeignKey("Bookings.BookingID"), nullable=False)
    InventoryID = Column(
        Integer, ForeignKey("FlightInventory.InventoryID"), nullable=False
    )
    FirstName = Column(String(50), nullable=False)
    LastName = Column(String(50), nullable=False)
    DateOfBirth = Column(Date, nullable=False)
    PassportNumber = Column(String(30), unique=True)
    SeatNumber = Column(String(5))

    # Relationships
    booking = relationship("Booking", back_populates="passengers")
    inventory_item = relationship("FlightInventory", back_populates="passengers")
