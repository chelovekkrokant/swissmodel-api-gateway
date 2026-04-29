import tempfile


def create_temp_dir():
    return tempfile.mkdtemp(prefix="tmp")
