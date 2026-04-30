import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def submit_automodel(sequences):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=settings.project_create_url,
            headers={"Authorization": f"Token {settings.swissmodel_api_key}"},
            json={"target_sequences": sequences},
        )
    if not str(response.status_code).startswith("2"):
        raise RuntimeError(f"Submission failed: {response.status_code} {response.text}")
    data = response.json()
    project_id = data.get("project_id")
    if not project_id:
        raise RuntimeError(f"No project_id in response: {data}")
    logger.info(f"Submitted automodel, status_code={response.status_code}, project_id={project_id} data={data}")
    return project_id


async def fetch_results(project_id: str) -> dict:
    max_attempts = settings.max_wait_time // settings.poll_interval
    url = settings.project_status_url.format(project_id=project_id)

    async with httpx.AsyncClient() as client:
        for attempt in range(max_attempts):
            await asyncio.sleep(settings.poll_interval)

            response = await client.get(
                url=url,
                headers={"Authorization": f"Token {settings.swissmodel_api_key}"},
            )

            if not str(response.status_code).startswith('2'):
                raise RuntimeError(f"Polling failed: status={response.status_code}, body={response.text}")

            data = response.json()
            status = data.get("status")
            logger.info(f"Job status (attempt {attempt + 1}/{max_attempts}): {status}")

            if status == "COMPLETED":
                return data
            if status == "FAILED":
                raise RuntimeError(f"Job failed: {data}")
            if status is None:
                raise RuntimeError(f"No status field in response: {data}")

    raise TimeoutError(f"Job did not complete in {settings.max_wait_time}s")