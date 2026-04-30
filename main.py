import logging

from fastapi import FastAPI

from app.api import api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.include_router(api_router)