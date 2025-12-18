from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

# Import the SQLAlchemy Models, Pydantic Schemas, and DB utilities
from . import models
from .database import get_db

# this tells fastapi where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

# These should ideally go in your .env later!
SECRET_KEY = "a-very-secret-string-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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
