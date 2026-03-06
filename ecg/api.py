from pydantic import BaseModel
import requests
import json


URL = "http://localhost:5001"
# URL = "https://trauma-back.msailab.com"


class LoginRequest(BaseModel):
    username: str
    password: str


class ArrayData(BaseModel):
    data: dict
    file_name: str


def getTokenForRequest():
    payload_data = LoginRequest(
        username="admin@marvasti.com", password="traumaprojectdemo"
    )

    response = requests.post(
        f"{URL}/auth/login", json=payload_data.model_dump())

    try:
        return json.loads(response.text)["access_token"]
    except:
        return ""


def resetOldVisualization(token: str):
    requests.delete(f'{URL}/data/reset_all',
                    headers={"Authorization": f'Bearer {token}'},)


def sendData(payload_data: ArrayData, token: str, chunk_seconds: int, part_number: int):
    try:
        response = requests.post(
            f'{URL}/data/save_array',
            json=payload_data.model_dump(),
            headers={"Authorization": f'Bearer {token}'},
            timeout=10
        )
        response.raise_for_status()
        print(
            f"✅ Sent {chunk_seconds}s chunk (Part {part_number}) successfully")
    except Exception as e:
        print(f"❌ Failed to send Part {part_number}: {e}")
