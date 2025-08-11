import os
import boto3
from typing import List
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from fastapi import FastAPI, UploadFile, File
from utils import run_prediction_from_s3
from typing import List
from fastapi import UploadFile, File
from utils import load_model

# Load env vars
load_dotenv()

# ENV variables
AWS_ACCESS_KEY = os.getenv("ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("SECRET_ACCESS_KEY")
S3_ENDPOINT_URL = os.getenv("ENDPOINT_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
OUTPUT_BUCKET_NAME = os.getenv("OUTPUT_BUCKET_NAME")
NO_LABEL_BUCKET_NAME = os.getenv("NO_LABEL_BUCKET_NAME")
MODEL_BUCKET = os.getenv("MODEL_BUCKET")
MODEL= os.getenv("MODEL")
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "./model/model.pt")


# Initialize FastAPI
app = FastAPI(title="Batch Labeling")

# Initialize boto3 client for MinIO
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)
def download_model():
    """Download the model from S3 if not already available locally."""
    os.makedirs(os.path.dirname(LOCAL_MODEL_PATH), exist_ok=True)
    if not os.path.exists(LOCAL_MODEL_PATH):
        print(f"Downloading model: {MODEL} from MinIO...")
        s3.download_file(MODEL_BUCKET, MODEL, LOCAL_MODEL_PATH)
        print("Model downloaded successfully.")
    else:
        print("Model already exists locally. Skipping download.")


@app.on_event("startup")
def startup_event():
    """Run on FastAPI startup."""
    download_model()
    load_model(LOCAL_MODEL_PATH)

@app.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    allowed_types = ["image/jpeg", "image/png"]
    allowed_exts = [".jpg", ".jpeg", ".png"]

    results = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if file.content_type not in allowed_types or ext not in allowed_exts:
            results.append({
                "filename": file.filename,
                "error": "File type not allowed. Only jpg, jpeg, png files are accepted."
            })
            continue

        # Upload original image to input bucket
        data = await file.read()
        s3.put_object(Bucket=BUCKET_NAME, Key=file.filename, Body=data)

        # Run prediction and upload output to output bucket
        pred_filename, coco_bboxes = run_prediction_from_s3(
            s3_client=s3,
            bucket_name=BUCKET_NAME,
            key=file.filename,
            output_bucket=OUTPUT_BUCKET_NAME,
            no_label_bucket=NO_LABEL_BUCKET_NAME,
            class_mapping_path='class_mapping.json'
        )

        # input_url = f"{S3_ENDPOINT_URL}/{BUCKET_NAME}/{file.filename}"
        # output_url = f"{S3_ENDPOINT_URL}/{OUTPUT_BUCKET_NAME}/" 

        results.append({
            "filename": file.filename,
            # "input_url": input_url,
            # "output_url": output_url,
            "coco_bboxes": coco_bboxes,
            # "status": "prediction complete and uploaded"
        })

    return {"results": results}
