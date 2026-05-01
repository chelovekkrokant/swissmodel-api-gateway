import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.swissmodel_client import init_client, close_client

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_client()
    yield
    await close_client()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)