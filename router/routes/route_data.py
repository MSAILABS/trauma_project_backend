import os
import json
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from router.utils.jwt_dependency import get_current_user
from ecg.ecg_decompress_v4 import process_and_send_er3_data

router = APIRouter()

# Queue to hold incoming arrays
array_queue = Queue(maxsize=0)

# State for ER3 background processing thread
er3_thread_lock = threading.Lock()
current_er3_thread = None
current_er3_stop_event = None
current_er3_pause_event = None

# Track last time /get_array was called
last_get_array_time = datetime.utcnow()


def _queue_cleaner_loop():
    """
    Background loop that clears the queue if /get_array has not been
    called for more than 10 minutes and the queue is not empty.
    """
    global last_get_array_time
    while True:
        try:
            now = datetime.utcnow()
            idle_seconds = (now - last_get_array_time).total_seconds()
            if idle_seconds > 300 and not array_queue.empty():
                cleared = 0
                while True:
                    try:
                        array_queue.get_nowait()
                        cleared += 1
                    except Empty:
                        break
                # Optional: log to stdout for debugging
                print(f"🧹 Cleared {cleared} items from array_queue after {idle_seconds} seconds idle.")
        except Exception:
            # Never let the cleaner thread crash
            pass
        time.sleep(60)


# Start the background queue cleaner thread
_queue_cleaner_thread = threading.Thread(target=_queue_cleaner_loop, daemon=True)
_queue_cleaner_thread.start()

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
# 1b. Trigger ER3 processing in background (cancellable)
# ------------------------------
@router.post("/process_er3")
async def process_er3(
    model_type: str = "rf",
    current_user=Depends(get_current_user),
):
    """
    Starts background processing of the ER3 ECG file that is already
    present on the backend (no file upload from frontend).

    If a previous processing job is still running, it will be asked to
    stop before a new one is started.
    """
    base_dir = Path(__file__).resolve().parents[2]  # project root
    er3_file_path = base_dir / "ecg" / "W20251223095205"

    if not er3_file_path.exists():
        return JSONResponse(
            {"error": f"ER3 file not found at {er3_file_path}"},
            status_code=404,
        )

    raw_data = er3_file_path.read_bytes()

    # Match defaults used in ecg_decompress_v4.main, except model_type which
    # is now provided by the frontend.
    sampling_rate = 250
    description = er3_file_path.name

    global current_er3_thread, current_er3_stop_event, current_er3_pause_event

    with er3_thread_lock:
        # If there is an existing processing thread, signal it to stop
        if current_er3_thread is not None and current_er3_thread.is_alive():
            if current_er3_stop_event is not None:
                current_er3_stop_event.set()

        # Create a new stop/pause event and worker thread
        stop_event = threading.Event()
        pause_event = threading.Event()

        def worker():
            try:
                process_and_send_er3_data(
                    raw_data=raw_data,
                    sampling_rate=sampling_rate,
                    description=description,
                    model_type=model_type,
                    stop_event=stop_event,
                    pause_event=pause_event,
                )
            finally:
                # When done, clear the global references if this is still the active thread
                global current_er3_thread, current_er3_stop_event, current_er3_pause_event
                with er3_thread_lock:
                    if current_er3_thread is threading.current_thread():
                        current_er3_thread = None
                        current_er3_stop_event = None
                        current_er3_pause_event = None

        thread = threading.Thread(target=worker, daemon=True)
        current_er3_thread = thread
        current_er3_stop_event = stop_event
        current_er3_pause_event = pause_event
        thread.start()

    return {
        "status": "processing_started",
        "description": description,
        "model_type": model_type,
        "sampling_rate": sampling_rate,
        "file_path": str(er3_file_path),
    }


# ------------------------------
# 1c. Reset/stop ER3 processing if running
# ------------------------------
@router.post("/reset_er3")
async def reset_er3(current_user=Depends(get_current_user)):
    """
    If an ER3 processing job is currently running in the background,
    request it to stop. Does not start a new job.
    """
    global current_er3_thread, current_er3_stop_event, current_er3_pause_event

    # Clear the queue
    cleared_count = 0
    while True:
        try:
            array_queue.get_nowait()
            cleared_count += 1
        except Empty:
            break

    with er3_thread_lock:
        if current_er3_thread is not None and current_er3_thread.is_alive():
            if current_er3_stop_event is not None:
                current_er3_stop_event.set()
            if current_er3_pause_event is not None:
                current_er3_pause_event.clear()

            return {
                "status": "stop_requested",
                "cleared_queue_items": cleared_count,
            }
        else:
            current_er3_thread = None
            current_er3_stop_event = None
            current_er3_pause_event = None
            return {
                "status": "no_active_job",
                "cleared_queue_items": cleared_count,
            }


# ------------------------------
# 1d. Pause ER3 processing if running
# ------------------------------
@router.post("/pause_er3")
async def pause_er3(current_user=Depends(get_current_user)):
    """
    Pause the ER3 processing job if it is currently running and not already paused.
    """
    global current_er3_thread, current_er3_pause_event

    with er3_thread_lock:
        if current_er3_thread is not None and current_er3_thread.is_alive():
            if current_er3_pause_event is None:
                return {"status": "no_pause_handle"}
            if not current_er3_pause_event.is_set():
                current_er3_pause_event.set()
                return {"status": "paused"}
            else:
                return {"status": "already_paused"}
        else:
            return {"status": "no_active_job"}


# ------------------------------
# 1e. Unpause ER3 processing if paused
# ------------------------------
@router.post("/unpause_er3")
async def unpause_er3(current_user=Depends(get_current_user)):
    """
    Unpause the ER3 processing job if it is currently paused.
    """
    global current_er3_thread, current_er3_pause_event

    with er3_thread_lock:
        if current_er3_thread is not None and current_er3_thread.is_alive():
            if current_er3_pause_event is None:
                return {"status": "no_pause_handle"}
            if current_er3_pause_event.is_set():
                current_er3_pause_event.clear()
                return {"status": "unpaused"}
            else:
                return {"status": "not_paused"}
        else:
            return {"status": "no_active_job"}


# ------------------------------
# 2. Pop next array from queue
# ------------------------------
@router.get("/get_array")
async def get_array(current_user=Depends(get_current_user)):
    global last_get_array_time
    last_get_array_time = datetime.utcnow()

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
