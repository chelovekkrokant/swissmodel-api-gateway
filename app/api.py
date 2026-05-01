from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.swissmodel_client import submit_automodel, fetch_results, logger
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
    except (RuntimeError, TimeoutError) as e:
        raise HTTPException(status_code=500, detail=str(e))

    return results