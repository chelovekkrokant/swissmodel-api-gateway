import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.swissmodel_client import (
    submit_automodel,
    submit_user_template,
    fetch_results,
    download_pdb,
    logger,
    request_id_var,
)
from app.utils import create_temp_dir, save_upload_file, parse_fasta, validate_files

api_router = APIRouter()

@api_router.post("/predict", status_code=200)
async def predict(
        fasta: Optional[UploadFile] = File(None),
        template: Optional[UploadFile] = File(None),
):
    # Уникальный id для этого запроса, изолирован в asyncio-task, не виден другим запросам
    request_id_var.set(uuid.uuid4().hex[:8])

    if fasta is None:
        raise HTTPException(status_code=400, detail="fasta file required")

    logger.info(f"Received request: fasta={fasta.filename}, template={template.filename if template else None}")

    validate_files(fasta, template)
    temp_dir = create_temp_dir()

    # finally гарантирует удаление temp_dir даже при любом исключении внутри
    try:
        try:
            fasta_path = await save_upload_file(fasta, temp_dir)
            template_path = None
            if template is not None:
                template_path = await save_upload_file(template, temp_dir)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        try:
            sequences = parse_fasta(fasta_path)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

        try:
            if template is not None:
                # Режим B: шаблон задаётся пользователем, API принимает только одну последовательность
                if len(sequences) > 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Template mode requires a single sequence in FASTA",
                    )
                with open(template_path) as f:
                    template_pdb = f.read()
                logger.info("Mode B (user template): sequences=1")
                project_id = await submit_user_template(sequences[0], template_pdb)
            else:
                # Режим A: SWISS-MODEL сам подберёт шаблон по базе данных
                logger.info(f"Mode A (automodel): sequences={len(sequences)}")
                project_id = await submit_automodel(sequences)

            results = await fetch_results(project_id)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=str(e))

        # None означает FAILED от SWISS-MODEL, код ошибки зависит от режима
        if results is None:
            if template is None:
                raise HTTPException(status_code=404, detail="No suitable templates found")
            raise HTTPException(status_code=500, detail="Job failed for user template")

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

        logger.info(f"Returning PDB for project_id={project_id}: size={len(pdb_bytes)} bytes")
        return Response(
            content=pdb_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="result.pdb"'},
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
