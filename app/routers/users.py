# app/routers/users.py
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm  # Used for login form
from jose import jwt

# Security dependencies
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import the SQLAlchemy Models, Pydantic Schemas, and DB utilities
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

# These should ideally go in your .env later!
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-string-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()

# Initialize Password Context for Hashing/Verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Security Utility Functions ---


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """Checks a plain password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # this generates the long, encrypted string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Endpoint 1: User Registration ---


@router.post(
    "/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED
)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user account with hashed password storage.
    """
    # Check if the email already exists
    db_user = db.query(models.User).filter(models.User.Email == user_data.Email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash the password for secure storage
    hashed_password = get_password_hash(user_data.Password)

    try:
        # Use the Stored Procedure for the actual insert
        db.execute(
            text(
                "EXEC sp_CreateUser @Email=:email, @HashedPassword=:hp, @FirstName=:fn, @LastName=:ln, @PhoneNumber=:ph, @DateOfBirth=:dob"
            ),
            {
                "email": user_data.Email,
                "hp": hashed_password,
                "fn": user_data.FirstName,
                "ln": user_data.LastName,
                "ph": user_data.PhoneNumber,
                "dob": user_data.DateOfBirth,
            },
        )
        db.commit()

        # Fetch the newly created user to return
        return (
            db.query(models.User).filter(models.User.Email == user_data.Email).first()
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed.")


# --- Endpoint 2: User Login (Get Token) ---


@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),  # FastAPI standard for username/password login
    db: Session = Depends(get_db),
):
    """
    Authenticates user and returns an access token (we'll implement the token generation later).
    """
    user = db.query(models.User).filter(models.User.Email == form_data.username).first()

    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # create and respond with access token
    access_token = create_access_token(data={"sub": user.Email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Endpoint 3: Get Current User (To verify login) ---


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Retrieves the details of the currently logged-in user.
    """

    return current_user
