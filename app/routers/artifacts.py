from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from ..dependancies.tools import Tools

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    responses={404: {"description": "Not found"}},
)


def fetch_tools():
    return Tools()


@router.get("/{artifact_url}", response_class=PlainTextResponse)
async def get_artifact(artifact_url: str, tools: Tools = Depends(fetch_tools)):
    try:
        log_content = tools.fetch_artifact(artifact_url)
        if not log_content:
            raise HTTPException(status_code=404, detail="Log file does not contain any data")
        return log_content
    except HTTPException:
        raise

