import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def submit_automodel(sequences):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.base_url}/automodel",
            headers={"Authorization": f"Token {settings.api_key}"},
            json={"target_sequences": sequences},
        )
    project_id = response.json()["project_id"]
    logger.info(f"Submitted automodel, status_code={response.status_code}, project_id={project_id}")
    return project_id


async def fetch_results(project_id: str):
    async with httpx.AsyncClient() as client:
        while True:
            time.sleep(10)

            response = await client.get(
                f"{settings.base_url}/project/{project_id}/models/summary/",
                headers={"Authorization": f"Token {settings.api_key}"}
            )
            status = response.json()["status"]
            logger.info(f"Job status: {status}")
            if status in ["COMPLETED", "FAILED"]:
                break
    return response.json()