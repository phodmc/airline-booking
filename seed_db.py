from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_data():
    db = SessionLocal()
    try:
        # 1. Clear existing data (Double check!)
        db.query(models.Booking).delete()
        db.query(models.Flight).delete()
        db.query(models.User).delete()
        db.query(models.Airport).delete()

        # 2. Create Airports
        jfk = models.Airport(
            Name="John F. Kennedy International",
            City="New York",
            Country="USA",
            IATACode="JFK",
        )
        lhr = models.Airport(
            Name="London Heathrow", City="London", Country="UK", IATACode="LHR"
        )
        dxb = models.Airport(
            Name="Dubai International", City="Dubai", Country="UAE", IATACode="DXB"
        )
        db.add_all([jfk, lhr, dxb])
        db.commit()

        # 3. Create a Test User
        hashed_pw = pwd_context.hash("password123")
        test_user = models.User(
            Email="traveler@example.com",
            HashedPassword=hashed_pw,
            FirstName="John",
            LastName="Doe",
        )
        db.add(test_user)
        db.commit()

        # 4. Create Flights
        flight1 = models.Flight(
            FlightNumber="AA101",
            DepartureAirportID=jfk.AirportID,
            ArrivalAirportID=lhr.AirportID,
            DepartureTime=datetime.utcnow() + timedelta(days=1),
            ArrivalTime=datetime.utcnow() + timedelta(days=1, hours=7),
            Price=550.00,
        )

        flight2 = models.Flight(
            FlightNumber="EK202",
            DepartureAirportID=lhr.AirportID,
            ArrivalAirportID=dxb.AirportID,
            DepartureTime=datetime.utcnow() + timedelta(days=2),
            ArrivalTime=datetime.utcnow() + timedelta(days=2, hours=7),
            Price=850.00,
        )
        db.add_all([flight1, flight2])
        db.commit()

        print("✅ Database seeded successfully!")
        print(f"User: traveler@example.com | Password: password123")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
