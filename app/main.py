from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import aircrafts, airports, bookings, flights, users

# creates all the tables in the database (Only run if you haven't run the SQL scripts)
# database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Airline Booking System API", version="1.0")

# CORS Middleware

origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All flight related endpoints
app.include_router(flights.router, prefix="/api/v1/flights", tags=["Flights"])
app.include_router(
    users.router, prefix="/api/v1/users", tags=["Users and Authentication"]
)
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
app.include_router(aircrafts.router, prefix="/api/v1/aircrafts", tags=["Aircrafts"])
app.include_router(airports.router, prefix="/api/v1/airports", tags=["Airports"])


@app.get("/api/v1/health")
def read_root():
    return {"status": "ok", "message": "API is running"}
