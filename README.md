# Batch Labeling

Batch Labeling is a FastAPI-based service for uploading images, running object detection using a TorchScript model, and returning bounding boxes in COCO format. It integrates with MinIO (S3-compatible) storage for input/output image management.

## Features
- Upload multiple images via API
- Only allows jpg, jpeg, png files
- Runs inference using a TorchScript model
- Returns bounding boxes in COCO format ([x, y, width, height])
- Stores input and output images in S3 buckets

## Setup

### 1. Clone the repository
```bash
git clone <repo-url>
cd batch_labeling
```

### 2. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file with the following keys:
```
ACCESS_KEY_ID=your_access_key
SECRET_ACCESS_KEY=your_secret_key
ENDPOINT_URL=http://api.url
BUCKET_NAME=your-input-bucket
OUTPUT_BUCKET_NAME=your-output-bucket
NO_LABEL_BUCKET_NAME=your-no-label-bucket
MODEL_BUCKET=your-model-bucket
MODEL=model.pt
LOCAL_MODEL_PATH=./model/model.pt
```

### 4. Run the API
```bash
uvicorn main:app --reload
```

### 5. Docker
Build and run the container:
```bash
docker build -t image_name:tag .
docker run --env-file .env -p 8000:8000 image_name:tag
```

## API Usage

### Upload Images
**Endpoint:** `POST /upload`

**Request:**
- `files`: List of image files (jpg, jpeg, png)

**Response:**
```json
{
	"results": [
		{
			"filename": "image1.jpg",
			"coco_bboxes": [[x, y, width, height], ...]
		},
		{
			"filename": "image2.png",
			"coco_bboxes": [[x, y, width, height], ...]
		}
	]
}
```

## COCO Format
Bounding boxes are returned as `[x, y, width, height]` for each detected object.

# Folder Structure
- `main.py` - FastAPI app and endpoints
- `utils.py` - Model loading, prediction, COCO conversion
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container setup
- `class_mapping.json` - Class index to name mapping
- `model/` - TorchScript model file
- `deployments/` - Kubernetes manifests for deploying the app:
	- `deployment.yaml`: Deployment resource for running the API server
	- `secrets.yaml`: Kubernetes secrets for environment variables and credentials

## Model Storage and Download

The TorchScript model file (`model.pt`) is stored in object storage (e.g., MinIO or S3) rather than bundled in the Docker image or repository. On application startup, the model is automatically downloaded to the container if it is not already present locally.

**Reason:**
- This approach allows you to update or swap the model file in object storage without rebuilding or redeploying the application container.
- It keeps the Docker image lightweight and decouples model management from application code.
- It supports secure, centralized, and versioned model storage, which is important for production ML workflows.

The download logic is handled in the FastAPI startup event (`main.py`), using the MinIO/S3 client and environment variables for credentials and bucket names.

## Workflow

1. **User uploads images** via the `/upload` API endpoint (supports multiple jpg/jpeg/png files).
2. **Files are validated** for allowed types and extensions.
3. **Original images are uploaded** to the input MinIO/S3 bucket.
4. **Model inference runs** on each image using the TorchScript model.
5. **Bounding boxes are predicted** and converted to COCO format (`[x, y, width, height]`).
6. **Images with predictions** are saved and uploaded to the output bucket.
7. **Images with no predictions** above the confidence threshold are uploaded to the no-label bucket.
8. **API response** returns the filenames and COCO-format bounding boxes for each image.

## CI/CD Workflow

This project uses GitHub Actions for continuous integration and deployment:

- **Run Tests** (`.github/workflows/runtest.yaml`):
	- Triggers on every push or pull request to the `main` branch.
	- Sets up Python 3.12.4 and installs all dependencies (including torch and torchvision CPU wheels).
	- Runs all tests in the `test/` directory using pytest.

- **Build and Push Docker Image** (`.github/workflows/docker.yaml`):
	- Triggers automatically after a successful test workflow.
	- Builds a Docker image from the repository.
	- Pushes the image to Docker Hub using credentials stored in repository secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `CONTAINER_NAME`).

This ensures that only code that passes all tests is built and deployed as a Docker image.

## Kubernetes Deployment

The `deployments/` folder contains manifests for deploying this application to a Kubernetes cluster:

- **Namespace**: Creates a dedicated namespace for the deployment.
- **Secrets**: `secrets.yaml` defines a Kubernetes Secret containing all required environment variables and credentials (such as S3 keys, bucket names, and endpoints). These are injected into the container as environment variables.
- **Deployment**: `deployment.yaml` defines a Deployment resource that:
  - Runs the FastAPI app in a container
  - Injects secrets as environment variables
  - Exposes port
- **Service**: Exposes the app internally as a service.
- **Ingress**: Configures external access via an Ingress resource with TLS and routing for the domain `fish.kk11.com.np`.

Ensure your cluster has an Ingress controller (e.g., Traefik) and cert-manager for TLS if using the provided ingress config.

This setup provides a secure, production-ready deployment for the batch labeling API on Kubernetes.

## Continuous Delivery with ArgoCD

This project supports GitOps-based continuous delivery using [ArgoCD]. ArgoCD automatically syncs the Kubernetes manifests in the `deployments/` folder from this repository to your Kubernetes cluster.

**Benefits:**
- Ensures your cluster state always matches the desired state in Git
- Enables automated, auditable, and version-controlled deployments
- Makes rollbacks and environment management easy

**How it works:**
- When you push changes to the manifests in the `deployments/` folder (such as updating the Docker image tag), ArgoCD detects the change and applies it to the cluster.
- This enables safe, automated, and repeatable deployments without manual `kubectl` commands.

## License
MIT