"""
Test script to populate the queue with a sample incident message
"""
import asyncio
import json
import os
from azure.storage.queue.aio import QueueClient
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
QUEUE_NAME = os.getenv("QUEUE_NAME", "incident-queue")

async def create_test_message():
    """Create a test incident message in the queue"""
    
    # Sample incident message
    messages = [
        {"incident_id": "incident_123", "artifact_path": "logs/incident_123.log"},
        {"incident_id": "incident_124", "artifact_path": "logs/incident_124.log"},
    ]
    
    # Create queue client
    queue_client = QueueClient.from_connection_string(
        conn_str=AZURE_STORAGE_CONNECTION_STRING,
        queue_name=QUEUE_NAME,
        message_encode_policy=None,
        message_decode_policy=None
    )
    
    async with queue_client:
        # Create the queue if it doesn't exist
        try:
            await queue_client.create_queue()
            print(f"✅ Queue '{QUEUE_NAME}' created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Queue '{QUEUE_NAME}' already exists")
            else:
                print(f"❌ Error creating queue: {e}")
                return
        
        # Send the message
        try:
            for message in messages:
                await queue_client.send_message(json.dumps(message))
                print(f"✅ Message sent: {message['incident_id']} -> {message['artifact_path']}")
            
            # Check queue properties
            properties = await queue_client.get_queue_properties()
            print(f"\n📊 Queue stats: {properties.approximate_message_count} message(s) in queue")
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")

if __name__ == "__main__":
    print("🚀 Testing Azure Queue Storage with Azurite\n")
    asyncio.run(create_test_message())
