import io
import os
import sys
from fastapi.testclient import TestClient

# Ensure root folder is in Python path so "main" can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # assuming FastAPI app is in main.py

client = TestClient(app)


def test_upload_invalid_file_type():
    """Ensure that uploading a non-image file returns an error."""
    response = client.post(
        "/upload",
        files={"files": ("test.txt", io.BytesIO(b"fake content"), "text/plain")},
    )
    assert response.status_code == 200
    json_resp = response.json()
    assert "error" in json_resp["results"][0]
    assert "File type not allowed" in json_resp["results"][0]["error"]
