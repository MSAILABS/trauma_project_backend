import os
import json
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from queue import Queue, Empty
from datetime import datetime

from router.utils.jwt_dependency import get_current_user

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


# ------------------------------
# 1. Save multidimensional array
# ------------------------------
@router.post("/save_array")
async def save_array(payload: ArrayData, current_user=Depends(get_current_user)):
    array_entry = {
        "data": payload.data,
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        array_queue.put_nowait(array_entry)
    except:
        return {"status": "queue_full"}, 429

    return {"status": "queued", "queue_size": array_queue.qsize()}


# ------------------------------
# 2. Pop next array from queue
# ------------------------------
@router.get("/get_array")
async def get_array(current_user=Depends(get_current_user)):
    try:
        array_entry = array_queue.get_nowait()  # pop from queue
    except Empty:
        return {"message": "no new array data"}

    # Load existing file
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            all_data = json.load(f)
    else:
        all_data = []

    # Append new array to file
    all_data.append(array_entry)

    with open(file_path, "w") as f:
        json.dump(all_data, f)

    return array_entry


# ------------------------------
# 3. Download array.json file
# ------------------------------
@router.get("/download_array")
async def download_array(current_user=Depends(get_current_user)):
    if not os.path.exists(file_path):
        return JSONResponse({"error": "array.json file not found"}, status_code=404)

    return FileResponse(
        path=file_path,
        filename="array.json",
        media_type="application/json"
    )


# ------------------------------
# 4. Delete array.json file
# ------------------------------
@router.delete("/delete_array")
async def delete_array(current_user=Depends(get_current_user)):
    if not os.path.exists(file_path):
        return JSONResponse({"message": "file not found"}, status_code=404)

    os.remove(file_path)
    return {"message": "array.json deleted successfully"}


# ------------------------------
# 5. Get all data from array.json
# ------------------------------
@router.get("/get_all_arrays")
async def get_all_arrays(current_user=Depends(get_current_user)):
    if not os.path.exists(file_path):
        return {"message": "array.json file does not exist", "data": []}

    with open(file_path, "r") as f:
        try:
            all_data = json.load(f)
        except json.JSONDecodeError:
            all_data = []

    return {"data": all_data}


# ------------------------------
# 6. Clear only the queue
# ------------------------------
@router.delete("/clear_queue")
async def clear_queue(current_user=Depends(get_current_user)):
    cleared_count = 0

    while True:
        try:
            array_queue.get_nowait()
            cleared_count += 1
        except Empty:
            break

    return {
        "message": "queue cleared",
        "cleared_items": cleared_count,
        "queue_size": array_queue.qsize()
    }


# ------------------------------
# 7. Reset both the queue and array.json file
# ------------------------------
@router.delete("/reset_all")
async def reset_all(current_user=Depends(get_current_user)):
    # Clear queue
    while True:
        try:
            array_queue.get_nowait()
        except Empty:
            break

    # Remove file if exists
    if os.path.exists(file_path):
        os.remove(file_path)
        file_status = "array.json deleted"
    else:
        file_status = "array.json not found"

    return {
        "message": "queue + file reset successful",
        "file_status": file_status,
        "queue_size": array_queue.qsize()
    }
