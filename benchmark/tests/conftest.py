"""Use inherited permissions for temporary test directories on Windows."""
from pathlib import Path
import shutil
import uuid
import pytest
from typing import Iterator

@pytest.fixture
def tmp_path() -> Iterator[Path]:
    path = Path(__file__).parent / ('.tmp-' + uuid.uuid4().hex)
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path)
