from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm

from router.utils.auth import create_access_token, verify_password, hash_password

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Fake user (can be replaced with DB)
fake_user = {
    "email": "admin@marvasti.com",
    "password": hash_password("traumaprojectdemo")
}


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(request: LoginRequest):
    if request.username != fake_user["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, fake_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token
    token = create_access_token({"sub": request.username})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
async def login(request: OAuth2PasswordRequestForm = Depends()):
    if request.username != fake_user["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, fake_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": request.username})

    return {"access_token": token, "token_type": "bearer"}
