"""
Setup test artifact (log file) in Azure Blob Storage (Azurite)
"""
import asyncio
import os
from azure.storage.blob.aio import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
CONTAINER_NAME = "artifacts"

# Sample log content that matches the agent's use case
SAMPLE_LOG = """[2026-06-24 09:40:01.102] [INFO] [Thread-14] [InventoryService.Controllers] Ingesting batch request: POST /api/v1/inventory/cache/sync - Items count: 450
[2026-06-24 09:41:15.420] [INFO] [Thread-19] [InventoryService.Security] Token validation successful for client identity: svc-order-processor-prod
[2026-06-24 09:42:00.891] [WARN] [Thread-32] [StackExchange.Redis.ConnectionMultiplexer] Redis connection pool utilization warning: 88% capacity reached (44/50 active multiplexer sockets allocated).
[2026-06-24 09:42:03.115] [WARN] [Thread-08] [StackExchange.Redis.ConnectionMultiplexer] Redis connection pool utilization warning: 98% capacity reached (49/50 active multiplexer sockets allocated).
[2026-06-24 09:42:05.002] [FATAL] [Thread-41] [Company.Infrastructure.Cache.RedisProvider] SocketException: No connections were available to service this operation. Hard limit of 50 connections thoroughly exhausted. Connection pool saturation at 100%.
[2026-06-24 09:42:05.005] [ERROR] [Thread-41] [Company.Services.InventoryService] RedisTimeoutException: Timeout performing EXISTS inventory:cache:items. (Threshold constraint limit of 250ms exceeded waiting for an open socket connection slot).
  at StackExchange.Redis.ConnectionMultiplexer.ExecuteSyncImpl[T](Message message, ResultProcessor`1 processor, ServerEndPoint server) in C:\\\\projects\\redis\\StackExchange.Redis\\ConnectionMultiplexer.cs:line 1201
  at Company.Infrastructure.Cache.RedisProvider.Exists(String key) in /src/Infrastructure/Cache/RedisProvider.cs:line 42
  at Company.Services.InventoryService.GetStockCount(Guid itemId) in /src/Services/InventoryService.cs:line 108
  at Company.Api.Controllers.InventoryController.CheckStock(Guid id) in /src/Api/Controllers/InventoryController.cs:line 29
[2026-06-24 09:42:05.012] [ERROR] [Thread-11] [InventoryService.Middleware] GlobalExceptionHandler caught unhandled exception. Bubbling up HTTP Status Code 503 (Service Unavailable) to API Gateway caller."""

LOG_BLOBS = {
    "logs/incident_123.log": SAMPLE_LOG,
    "logs/incident_124.log": """[2026-06-24 10:15:00.001] [INFO] [Thread-07] [OrderProcessingService] Starting order reconciliation batch: batch-88421
[2026-06-24 10:15:01.287] [ERROR] [Thread-07] [OrderProcessingService.Database] SqlException: Database integrity check failed. Error 824: SQL Server detected a logical consistency-based I/O error while reading page (1:245) in database 'Orders'.
[2026-06-24 10:15:01.290] [FATAL] [Thread-07] [OrderProcessingService] Reconciliation aborted. The affected database page is corrupt and requires database recovery or manual restore.
[2026-06-24 10:15:01.294] [ERROR] [Thread-12] [OrderProcessingService.Middleware] GlobalExceptionHandler caught unhandled exception. Bubbling up HTTP Status Code 503 (Service Unavailable) to API Gateway caller.""",
    "logs/incident_125.log": """[2026-06-24 11:30:00.100] [INFO] [Thread-21] [PaymentService] Starting payment settlement batch: settlement-55109
[2026-06-24 11:30:02.443] [WARN] [Thread-21] [PaymentService.Gateway] Payment gateway response latency exceeded 2 seconds.
[2026-06-24 11:30:05.712] [ERROR] [Thread-21] [PaymentService.Gateway] HttpRequestException: The upstream payment gateway returned HTTP Status Code 502 (Bad Gateway).
[2026-06-24 11:30:05.715] [ERROR] [Thread-21] [PaymentService] Settlement batch settlement-55109 failed after 3 attempts. 127 payments were not settled.
[2026-06-24 11:30:05.718] [FATAL] [Thread-04] [PaymentService.Middleware] GlobalExceptionHandler caught unhandled exception. Bubbling up HTTP Status Code 502 (Bad Gateway) to API Gateway caller.""",
}

async def setup_test_blob():
    """Upload a test log file to Azurite blob storage"""
    
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    
    async with blob_service_client:
        # Get container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Create container if it doesn't exist
        try:
            await container_client.create_container()
            print(f"✅ Container '{CONTAINER_NAME}' created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Container '{CONTAINER_NAME}' already exists")
            else:
                print(f"❌ Error creating container: {e}")
                return
        
        # Upload the blob
        try:
            for blob_name, log_content in LOG_BLOBS.items():
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(log_content, overwrite=True)
                print(f"✅ Test log uploaded: {CONTAINER_NAME}/{blob_name} ({len(log_content)} bytes)")
            
            # Also upload the config file needed by the agent
            config_container = blob_service_client.get_container_client("infrastructure-settings")
            try:
                await config_container.create_container()
                print(f"✅ Container 'infrastructure-settings' created successfully")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️  Container 'infrastructure-settings' already exists")
            
            # Read and upload app_config.json
            config_path = "mock_infrasettings_storage/app_config.json"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = f.read()
                config_blob = config_container.get_blob_client("app_config.json")
                await config_blob.upload_blob(config_data, overwrite=True)
                print(f"✅ Config file 'app_config.json' uploaded successfully")
            else:
                print(f"⚠️  Config file not found at {config_path}")
            
        except Exception as e:
            print(f"❌ Error uploading blob: {e}")

if __name__ == "__main__":
    print("🚀 Setting up test artifacts in Azurite Blob Storage\n")
    asyncio.run(setup_test_blob())
