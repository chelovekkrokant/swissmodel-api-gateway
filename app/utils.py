import os
import tempfile

from fastapi import UploadFile


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
