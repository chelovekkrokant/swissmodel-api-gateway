from typing import Optional

from fastapi import APIRouter, UploadFile, File

api_router = APIRouter()

@api_router.post("/predict")
def predict(
        fasta: UploadFile = File(...),
        template: Optional[UploadFile] = File(...),
):
    return {"message": "endpoint todo", "fasta": fasta.filename}