from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from .routers import artifacts
from .dependancies.tools import Tools

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    tools = Tools()
    await tools.initialize()
    app.state.tools = tools
    try:
        yield
    finally:
        await tools.close()


app = FastAPI(lifespan=lifespan)
app.include_router(artifacts.router)

@app.get("/")
async def root():
    return "hello root"