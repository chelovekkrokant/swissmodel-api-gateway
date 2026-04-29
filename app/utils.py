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
