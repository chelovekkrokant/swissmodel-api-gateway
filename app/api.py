from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.utils import create_temp_dir, save_upload_file

api_router = APIRouter()

@api_router.post("/predict", status_code=200)
async def predict(
        fasta: UploadFile = File(...),
        template: Optional[UploadFile] = File(None),
):
    if not fasta.filename.endswith(".fasta"):
        raise HTTPException(status_code=400, detail="fasta file must have .fasta extension")
    if template is not None and not template.filename.endswith(".pdb"):
        raise HTTPException(status_code=400, detail="template file must have .pdb extension")

    template_path = "none"
    temp_dir = create_temp_dir()

    try:
        fasta_path = await save_upload_file(fasta, temp_dir)
        if template is not None:
            template_path = await save_upload_file(template, temp_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return {"temp_dir": temp_dir, "fasta_path": fasta_path, "template_path": template_path}