import httpx
from app.config import settings


async def submit_automodel(sequences):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.automodel_url,
            headers={"Authorization": f"Token {settings.api_key}"},
            json={"target_sequences": sequences},
        )
    return response.json()