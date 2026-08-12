"""Simple sync test for queue creation"""
import os
from dotenv import load_dotenv
from azure.storage.queue import QueueClient

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
QUEUE_NAME = "incident-queue"

try:
    # Use synchronous client for simpler testing
    queue_client = QueueClient.from_connection_string(
        conn_str=AZURE_STORAGE_CONNECTION_STRING,
        queue_name=QUEUE_NAME
    )
    
    # Create queue
    queue_client.create_queue()
    print(f"✅ Queue '{QUEUE_NAME}' created successfully")
    
    # Send a test message
    import json
    messages = [
        {"incident_id": "incident_123", "artifact_path": "logs/incident_123.log"},
        {"incident_id": "incident_124", "artifact_path": "logs/incident_124.log"},
    ]
    for message in messages:
        queue_client.send_message(json.dumps(message))
        print(f"✅ Message sent: {message['incident_id']}")
    
    # Check properties
    properties = queue_client.get_queue_properties()
    print(f"📊 Queue has {properties.approximate_message_count} message(s)")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
