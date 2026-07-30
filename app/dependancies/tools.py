import datetime
import json
from logging import exception
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, field_validator
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient

load_dotenv()


class Patch(BaseModel):
    patch_id: int
    created_date: str
    data: str

    @field_validator('created_date')
    @classmethod
    def validate_datetime_format(cls,v: str) -> str:
        try:
            # Enforces validation matching: dd-mm-yyyy_HH-mm-ss
            print(f"datetime issssssssss: {v}")
            datetime.datetime.strptime(v, "%d-%m-%Y_%H-%M-%S")
            return v
        except ValueError:
            raise ValueError("datetime must be in the format 'dd-mm-yyyy_HH-mm-ss'")

class Tools:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    artifact_container = "artifacts"
    config_container = "infrastructure-settings"
    patch_container = "patches"
    mock_patches_dir = os.path.join(project_root, "mock_patches")

    def __init__(self):
        if not self.connection_string:
            raise HTTPException(status_code=500, detail="AZURE_STORAGE_CONNECTION_STRING is not configured")
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

    async def get_blob_client(self, container_name: str, blob_name: str):
        container_client = self.blob_service_client.get_container_client(container_name)
        try:
        # 💡 Explicitly await the async create_container call
            await container_client.create_container()
        except ResourceExistsError:
            pass
        return container_client.get_blob_client(blob_name)

    async def fetch_artifact(self, artifact_path: str):
        if not artifact_path:
            raise HTTPException(status_code=400, detail="Artifact path is required")

        blob_client = await self.get_blob_client(self.artifact_container, artifact_path)
        try:
            return blob_client.download_blob()

        except ResourceNotFoundError:
            raise HTTPException(status_code=404, 
                                detail=f"Blob artifact not found: {artifact_path}")

    async def fetch_infrastructure_settings(self, system_config_path: str):
        if not system_config_path:
            raise HTTPException(status_code=400, detail="System configuration path is required")

        blob_client = await self.get_blob_client(self.config_container, system_config_path)
        try:
            stream = await blob_client.download_blob()
            content = await stream.readall()
            return json.loads(content)
        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail=f"Configuration blob not found: {system_config_path}")


    async def post_patch(self, patch: Patch) -> str:
        try:
                os.makedirs(self.mock_patches_dir, exist_ok=True)

                json_dict = json.loads(patch.data)
                file_name = f"patch_{patch.patch_id}_{patch.created_date}.json"
                file_path = os.path.join(self.mock_patches_dir, file_name)
                print(f"patch file path: {file_path}")

                #for debugging, write the patch to a local file first
                with open(file_path, "w") as file:
                    json.dump(json_dict, file, indent=4)

                blob_client = await self.get_blob_client(self.patch_container, file_name)
                # Upload directly from bytes in memory
                json_bytes = json.dumps(json_dict).encode("utf-8")
                blob_client.upload_blob(json_bytes, overwrite=True)

                return f"{self.patch_container}/{file_name}"

  
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error occurred while posting patch: {str(e)}")

