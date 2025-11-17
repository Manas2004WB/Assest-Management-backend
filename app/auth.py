from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

# Secret key (keep it safe!)
SECRET_KEY = "your_super_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- PASSWORD HELPERS ----------
def hash_password(password: str):
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes.decode("utf-8"))


def verify_password(plain_password: str, hashed_password: str):
    plain_password_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_password_bytes.decode("utf-8"), hashed_password)


# ---------- JWT CREATION ----------
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ---------- COOKIE LOGIN ----------
def login_user_response(username: str):
    """Returns response with JWT stored inside HttpOnly cookie"""

    token = create_access_token({"sub": username})

    response = JSONResponse({"message": "Login successful"})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="none",
        secure=False,
        max_age=60*60,
        path="/"
    )

    return response


# ---------- COOKIE LOGOUT ----------
def logout_user_response():
    response = JSONResponse({"message": "Logged out successfully"})
    response.delete_cookie("access_token", path="/")
    return response


# ---------- GET CURRENT USER ----------
def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/token"))):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
