from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DB Connection String
SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc:://sa:pho@dbsa25@TGL-IT-OFFICER\\SQLEXPRESS/AirlineDB"
    "?driver=ODBC+Driver+18+SQL+Server"
)

# The engine manages the connection pool and connects to the database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# This is like a 'staging area' for the database transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# the base class for defining SQL tables/models/entities as python classes
Base = declarative_base()


# creates a session for each request and closes it when done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
