import os, json

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Pydantic model for validation
class ArrayData(BaseModel):
    data: dict
    file_name: str

# Route 1: Save multidimensional array to file
@router.post("/save_array")
async def save_array(payload: ArrayData):
    data = []

    file_name = f"array.json"
    file_path = os.path.join(os.getcwd(), "signal_data_json_files", file_name)

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data: list = json.loads(f.read())

    data.append(payload.data)

    with open(file_path, "w") as f:
        json.dump(data, f)


    return {"message": "Array saved successfully"}

# Route 2: Get the last saved multidimensional array
@router.get("/get_array/{segment_num}")
async def get_array(segment_num: int):
    try:
        file_name = f"array.json"
        file_path = os.path.join(os.getcwd(), "signal_data_json_files", file_name)

        if not os.path.exists(file_path):
            return {"error": "No array saved yet"}
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        print(len(data),segment_num)
        res_data = data[segment_num + 1] if len(data) > 0 else {}
        return res_data
    except Exception as e:
        print(e)
        raise e