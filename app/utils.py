import os
import tempfile
from typing import Optional

from fastapi import UploadFile, File, HTTPException


def create_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="tmp")


async def save_upload_file(upload_file: UploadFile, directory: str) -> str:
    path = os.path.join(directory, upload_file.filename)
    with open(path, "wb") as f:
        f.write(await upload_file.read())
    return path


def parse_fasta(path: str) -> list[str]:
    sequences = []
    current: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current:
                    sequences.append("".join(current))
                    current = []
            elif line:
                current.append(line)
    if current:
        sequences.append("".join(current))
    if not len(sequences):
        raise OSError("Sequences not found")
    return sequences

def validate_files(fasta: File, template: Optional[File] = None):
    if not fasta.filename.endswith(".fasta"):
        raise HTTPException(status_code=400, detail="fasta file must have .fasta extension")
    if template is not None and not template.filename.endswith(".pdb"):
        raise HTTPException(status_code=400, detail="template file must have .pdb extension")