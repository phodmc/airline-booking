# app/routers/users.py
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm  # Used for login form
from jose import JWTError, jwt

# Security dependencies
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# Import the SQLAlchemy Models, Pydantic Schemas, and DB utilities
from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["Users and Authentication"])

# Initialize Password Context for Hashing/Verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Security Utility Functions ---


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """Checks a plain password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# These should ideally go in your .env later!
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-string-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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

    # Create the new user object
    new_user = models.User(
        Email=user_data.Email,
        HashedPassword=hashed_password,
        FirstName=user_data.FirstName,
        LastName=user_data.LastName,
        PhoneNumber=user_data.PhoneNumber,
        DateOfBirth=user_data.DateOfBirth,
        CreatedDate=datetime.now(),
    )

    # Commit to the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


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

    # --- TEMPORARY SUCCESS RESPONSE ---
    # create and respond with access token
    access_token = create_access_token(data={"sub": user.Email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Endpoint 3: Get Current User (To verify login) ---


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(
    # This dependency will eventually require a valid token
    # For now, we manually look up the user using the temporary token structure
    temp_token: str = Query(
        ..., description="The temporary token returned from /token"
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieves the details of the currently logged-in user.
    """
    try:
        # Extract UserID from the temporary token
        user_id = int(temp_token.split("-")[-1])
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format"
        )

    user = db.query(models.User).filter(models.User.UserID == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
