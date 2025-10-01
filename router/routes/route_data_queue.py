import pika
import json
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ArrayData(BaseModel):
    data: dict
    file_name: str

def publish_to_queue(message: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="localhost")  # Change if RabbitMQ is remote
    )
    channel = connection.channel()
    channel.queue_declare(queue="signal_data_queue", durable=True)

    channel.basic_publish(
        exchange="",
        routing_key="signal_data_queue",
        body=json.dumps(message),
    )
    connection.close()


@router.post("/save_array")
async def save_array(payload: ArrayData):
    publish_to_queue(payload.model_dump())
    return {"message": "Array sent to queue"}
