import asyncio
import logging
import os
import json
import httpx
from pydantic import BaseModel, ValidationError

# Azure SDK Async namespaces
from azure.storage.queue.aio import QueueClient
from azure.storage.queue import BinaryBase64DecodePolicy, BinaryBase64EncodePolicy, TextBase64DecodePolicy

# Agent requirements
from app.agents import InputDependancies, agent

# Setup logging
logging.basicConfig(
    filename="app.log",
    filemode="w",
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FASTAPI_BASEURL = os.getenv("FASTAPI_URL")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
QUEUE_NAME = os.getenv("QUEUE_NAME", "")

class IncidentMessage(BaseModel):
    incident_id: str
    artifact_path: str

async def process_message(client: httpx.AsyncClient, message: IncidentMessage) -> bool:
    path = f"{FASTAPI_BASEURL}/artifacts/{message.artifact_path}"

    try:
        logger.info(f"Calling the Artifact (Fast API) Endpoint for {message.incident_id}")
        response = await client.get(path)
        logger.info("FastAPI returned %s for %s",response.status_code, message.incident_id)


        response.raise_for_status() # Raise error for bad HTTP statuses (4xx, 5xx)
        
        # Run the agent
        deps = InputDependancies(
            incident_id=message.incident_id,
            system_config_path="app_config.json"
        )
        result = await agent.run(response.text, deps=deps)
        logger.info(f"Successfully returned a response from the agent: {result.output}")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"FastAPI returned error {e.response.status_code} for ID {message.incident_id} : {e}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to FastAPI for ID {message.incident_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to get a valid response from the agent: {e}")
        return False

async def main():
    MIN_BACKOFF = 1
    MAX_BACKOFF = 60
    BACKOFF_FACTOR = 2
    
    # 1. Initialize Async Service Client with Base64 decode rules
    queue_client = QueueClient.from_connection_string(
        conn_str = AZURE_STORAGE_CONNECTION_STRING,
        queue_name = QUEUE_NAME,
        message_input_policy= BinaryBase64DecodePolicy()
    )
    current_backoff = MIN_BACKOFF

    # 2. Managed context setup across both service connection and client
    async with httpx.AsyncClient() as http_client, queue_client:
        logger.info("Worker loop started successfully. Waiting for messages...")
        
        while True:
            try:
                # 💡 FIX: Added 'await' here so it evaluates the async pager stream
                messages =  queue_client.receive_messages(max_messages=1, visibility_timeout=30)
                
                
                has_messages = False
                async for message in messages:
                    has_messages = True
                    current_backoff = MIN_BACKOFF # Reset backoff timer on successful read
                    content = message.content

                    logger.info(f"Received message {message.id} with content: {content}")
                    
                    try:
                        # --- Parse and Validate Payload ---
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        payload = json.loads(content)
                        incident = IncidentMessage(**payload)
                        
                        # Process the structured object
                        success = await process_message(http_client, incident)
                        
                        if success:
                            await queue_client.delete_message(message)
                            logger.info(f"Deleted message {message.id} from queue.")
                        else:
                            logger.warning(f"Retrying incident {incident.incident_id} later (kept in queue).")
                            
                    except (json.JSONDecodeError, ValidationError) as parse_err:
                        # Poison message safeguard handling
                        logger.error(f"Error parsing the message format: {parse_err}. Removing bad message payload...")
                        await queue_client.delete_message(message)

                # --- Backoff Idling Strategy ---
                if has_messages:
                    current_backoff = MIN_BACKOFF
                else:
                    logger.info(f"No message found. Polling the queue again in {current_backoff} seconds...")
                    await asyncio.sleep(current_backoff)
                    current_backoff = min(current_backoff * BACKOFF_FACTOR, MAX_BACKOFF)

            except Exception:
                logger.exception("Unexpected worker exception occurred in loop execution context")
                await asyncio.sleep(MIN_BACKOFF)

if __name__ == "__main__":
    asyncio.run(main())