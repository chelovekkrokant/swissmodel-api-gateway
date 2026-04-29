import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File

from app.utils import create_temp_dir

api_router = APIRouter()

@api_router.post("/predict")
async def predict(
        fasta: UploadFile = File(...),
        template: Optional[UploadFile] = File(None),
):
    template_path = "none"
    temp_dir = create_temp_dir()

    fasta_path = os.path.join(temp_dir, fasta.filename)

    with open(fasta_path, "wb") as f:
        f.write(await fasta.read())

    if template is not None:
        template_path = os.path.join(temp_dir, template.filename)
        with open(template_path, "wb") as f:
            f.write(await template.read())

    return {"temp_dir": temp_dir, "fasta_path": fasta_path, "template_path": template_path}