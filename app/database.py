import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()


# 2. Pull values from environment variables
DB_DRIVER = os.getenv("DB_DRIVER")
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# This handles the special symbols in your password perfectly
params = quote_plus(
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
)
# DB Connection String
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"


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
