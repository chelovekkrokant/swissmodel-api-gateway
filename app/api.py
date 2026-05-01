from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from starlette import status

from app.swissmodel_client import submit_automodel, fetch_results, download_pdb, logger
from app.utils import create_temp_dir, save_upload_file, parse_fasta, validate_files

api_router = APIRouter()

@api_router.post("/predict", status_code=200)
async def predict(
        fasta: Optional[UploadFile] = File(None),
        template: Optional[UploadFile] = File(None),
):
    if fasta is None:
        raise HTTPException(status_code=400, detail="fasta file required")

    logger.info(f"Received request: fasta={fasta.filename}, template={template.filename if template else None}")

    validate_files(fasta, template)
    temp_dir = create_temp_dir()

    try:
        fasta_path = await save_upload_file(fasta, temp_dir)
        if template is not None:
            template_path = await save_upload_file(template, temp_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        sequence = parse_fasta(fasta_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    try:
        project_id = await submit_automodel(sequence)
        results = await fetch_results(project_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))

    models = results.get("models", [])
    if not models:
        raise HTTPException(status_code=404, detail="No models found")

    coordinates_url = models[0].get("coordinates_url")
    if not coordinates_url:
        raise HTTPException(status_code=500, detail="No coordinates_url in model response")

    try:
        pdb_bytes = await download_pdb(coordinates_url)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Returning PDB for project_id={project_id}")
    return Response(
        status_code=status.HTTP_200_OK,
        content=pdb_bytes,
        headers={"Content-Disposition": "attachment; filename=result.pdb"},
    )