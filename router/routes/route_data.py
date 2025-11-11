import os
import json
from fastapi import APIRouter
from pydantic import BaseModel
from queue import Queue, Empty
from datetime import datetime

router = APIRouter()

# Queue to hold incoming arrays
array_queue = Queue(maxsize=0)

# Folder and file setup
folder_path = os.path.join(os.getcwd(), "signal_data_json_files")
os.makedirs(folder_path, exist_ok=True)
file_name = "array.json"
file_path = os.path.join(folder_path, file_name)

# Pydantic model for validation
class ArrayData(BaseModel):
    data: dict
    file_name: str = file_name  # optional, default to "array.json"

# Route 1: Save multidimensional array to queue
@router.post("/save_array")
async def save_array(payload: ArrayData):
    array_entry = {
        "data": payload.data,
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        array_queue.put_nowait(array_entry)
    except:
        return {"status": "queue_full"}, 429

    return {"status": "queued", "queue_size": array_queue.qsize()}

# Route 2: Get the next array from queue (frontend)
@router.get("/get_array")
async def get_array():
    try:
        array_entry = array_queue.get_nowait()  # pop from queue
    except Empty:
        return {"message": "no new array data"}

    print(array_queue.qsize())
    # Save consumed array to file
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            all_data = json.load(f)
    else:
        all_data = []

    all_data.append(array_entry)

    with open(file_path, "w") as f:
        json.dump(all_data, f)

    return array_entry
