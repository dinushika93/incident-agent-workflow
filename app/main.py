from fastapi import FastAPI
from dotenv import load_dotenv

from .routers import artifacts

load_dotenv()

app = FastAPI()
app.include_router(artifacts.router)

@app.get("/")
async def root():
    return "hello root"