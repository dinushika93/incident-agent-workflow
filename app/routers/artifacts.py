from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from ..dependancies.tools import Tools

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    responses={404: {"description": "Not found"}},
)


def fetch_tools(request: Request) -> Tools:
    return request.app.state.tools


@router.get("/{artifact_url:path}", response_class=PlainTextResponse)
async def get_artifact(artifact_url: str, tools: Tools = Depends(fetch_tools)):
    try:
        stream = await tools.fetch_artifact(artifact_url)
        content = await stream.readall()
        log_content = content.decode("utf-8") if isinstance(content, bytes) else content
        if not log_content:
            raise HTTPException(status_code=404, detail="Log file does not contain any data")
        return log_content
    except HTTPException:
        raise

