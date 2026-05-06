import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.swissmodel_client import init_client, close_client, request_id_var


# Filter добавляет request_id в каждую запись лога — так id попадает в format-строку
class _RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s [req=%(request_id)s] %(name)s: %(message)s",
)
# addFilter навешиваем на все хэндлеры root-логгера после basicConfig
for _h in logging.getLogger().handlers:
    _h.addFilter(_RequestIdFilter())

logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_client()
    yield
    await close_client()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
