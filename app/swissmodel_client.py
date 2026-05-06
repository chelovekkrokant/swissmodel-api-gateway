import asyncio
import gzip
import logging
from contextvars import ContextVar

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_client: httpx.AsyncClient | None = None


def init_client():
    global _client
    _client = httpx.AsyncClient(
        headers={"Authorization": f"Token {settings.swissmodel_api_key}"},
        timeout=httpx.Timeout(60.0, connect=10.0),
    )


async def close_client():
    if _client:
        await _client.aclose()


async def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(settings.rate_limit_max_retries + 1):
        wait_hint: str | None = None
        try:
            response = await _client.request(method, url, **kwargs)
        except httpx.RequestError as e:
            last_exc = e
        else:
            if response.status_code != 429:
                return response
            wait_hint = response.headers.get("Retry-After")
            last_exc = None

        if attempt >= settings.rate_limit_max_retries:
            if last_exc is not None:
                raise RuntimeError(f"Network error on {method} {url}: {last_exc}") from last_exc
            raise RuntimeError(
                f"Rate limit exceeded after {settings.rate_limit_max_retries} retries on {method} {url}"
            )

        try:
            delay = float(wait_hint) if wait_hint is not None else settings.rate_limit_base_delay * (2 ** attempt)
        except ValueError:
            delay = settings.rate_limit_base_delay * (2 ** attempt)
        delay = min(delay, settings.rate_limit_max_delay)

        reason = repr(last_exc) if last_exc is not None else "429"
        logger.warning(
            f"Retrying {method} {url} in {delay:.1f}s "
            f"(attempt {attempt + 1}/{settings.rate_limit_max_retries}): {reason}"
        )
        await asyncio.sleep(delay)

    raise RuntimeError(f"Unreachable retry path for {method} {url}")


async def submit_automodel(sequences: list[str]) -> str:
    response = await _request_with_retry(
        "POST",
        settings.project_create_url,
        json={"target_sequences": sequences},
    )
    if not str(response.status_code).startswith("2"):
        raise RuntimeError(f"Submission failed: {response.status_code} {response.text}")
    data = response.json()
    project_id = data.get("project_id")
    if not project_id:
        raise RuntimeError(f"No project_id in response: {data}")
    logger.info(f"  Submitted automodel: status_code={response.status_code}, project_id={project_id}")
    return project_id


async def submit_user_template(sequence: str, template_pdb: str) -> str:
    response = await _request_with_retry(
        "POST",
        settings.template_upload_url,
        json={
            "target_sequences": sequence,
            "template_coordinates": template_pdb,
            "project_title": "predict-service user template",
        },
    )
    if not str(response.status_code).startswith("2"):
        raise RuntimeError(f"Submission failed: {response.status_code} {response.text}")
    data = response.json()
    project_id = data.get("project_id")
    if not project_id:
        raise RuntimeError(f"No project_id in response: {data}")
    logger.info(f"  Submitted user template: status_code={response.status_code}, project_id={project_id}")
    return project_id


async def fetch_results(project_id: str) -> dict | None:
    max_attempts = settings.max_wait_time // settings.poll_interval
    url = settings.project_status_url.format(project_id=project_id)

    for attempt in range(max_attempts):
        response = await _request_with_retry("GET", url)

        if not str(response.status_code).startswith("2"):
            raise RuntimeError(f"Polling failed: status={response.status_code}, body={response.text}")

        data = response.json()
        status = data.get("status")
        logger.info(f"  Job status (attempt {attempt + 1}/{max_attempts}): {status}")

        if status == "COMPLETED":
            return data
        if status == "FAILED":
            logger.info(f"  Job FAILED: {data}")
            return None
        if status is None:
            raise RuntimeError(f"No status field in response: {data}")

        await asyncio.sleep(settings.poll_interval)

    raise TimeoutError(f"Job did not complete in {settings.max_wait_time}s")

async def download_pdb(coordinates_url: str) -> bytes:
    response = await _request_with_retry("GET", coordinates_url)
    if not str(response.status_code).startswith("2"):
        raise RuntimeError(f"Failed to download PDB: status={response.status_code}")
    pdb_bytes = gzip.decompress(response.content)
    logger.info(f"Downloaded PDB from {coordinates_url}: size={len(pdb_bytes)} bytes")
    return pdb_bytes
