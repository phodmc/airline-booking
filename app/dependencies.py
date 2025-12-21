import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

# Import the SQLAlchemy Models, Pydantic Schemas, and DB utilities
from . import models
from .database import get_db

# this tells fastapi where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

load_dotenv()
# These should ideally go in your .env later!
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("TOKEN_EXPIRY")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        decoded_jwt = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = decoded_jwt.get("sub")
        if user_email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    db_user = db.query(models.User).filter(models.User.Email == user_email).first()
    if db_user is None:
        raise credentials_exception

    return db_user


def get_admin_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.IsAdmin:
        raise HTTPException(status_code=403, detail="You do not have admin privileges")

    return current_user
