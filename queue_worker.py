import pika
import json
import os

def callback(ch, method, properties, body):
    message = json.loads(body)
    data = message["data"]
    file_name = "array.json"

    file_path = os.path.join(os.getcwd(), "signal_data_json_files", file_name)

    # Read existing file
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content: list = json.loads(f.read())
    else:
        content = []

    content.append(data)

    # Write back
    with open(file_path, "w") as f:
        json.dump(content, f)

    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_worker():
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        channel = connection.channel()
        channel.queue_declare(queue="signal_data_queue", durable=True)
        channel.basic_consume(queue="signal_data_queue", on_message_callback=callback)
        print("🚀 Worker is listening for messages...")
        channel.start_consuming()

