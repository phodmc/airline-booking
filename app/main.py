from fastapi import FastAPI

from .routers import bookings, flights, users

# creates all the tables in the database (Only run if you haven't run the SQL scripts)
# database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Airline Booking System API", version="1.0")

# All flight related endpoints
app.include_router(flights.router, prefix="/api/v1/flights", tags=["Flights"])
app.include_router(
    users.router, prefix="/api/v1/users", tags=["Users and Authentication"]
)
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])


@app.get("/api/v1/health")
def read_root():
    return {"status": "ok", "message": "API is running"}
