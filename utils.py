import os
import cv2
import json
import torch
import torchvision
import numpy as np
from PIL import Image
import tempfile
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import io

# Load env vars
load_dotenv()

# Setup device and model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_model(model_path):
    """Load the TorchScript model from the given path into global variable."""
    global model
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    print(f"Loading model from {model_path}...")
    model = torch.jit.load(model_path).to(device)
    print("Model loaded successfully.")

# Load class mapping
def load_class_mapping(json_path):
    with open(json_path, 'r') as f:
        mappings = json.load(f)
    return {item['model_idx']: item['class_name'] for item in mappings}

# Predict + draw boxes and save to output_path
def predict_and_draw_from_array(image_np, class_mappings, output_path):
    image_tensor = torch.from_numpy(image_np).permute(2, 0, 1).float().unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(image_tensor)[0]
        print(f'Ouptut scores is {output["scores"]}')

        # Apply confidence threshold
        conf_thresh = 0.85
        conf_mask = output['scores'] > conf_thresh

        if conf_mask.sum() == 0:
            print("No detections above 85% confidence.")
            return output_path, []

        # Optionally apply NMS to high-confidence boxes
        else:
            boxes_conf = output['pred_boxes'][conf_mask]
            scores_conf = output['scores'][conf_mask]
            classes_conf = output['pred_classes'][conf_mask]

            # Apply NMS to the filtered boxes
            to_keep = torchvision.ops.nms(boxes_conf, scores_conf, iou_threshold=0.5)

            # Final filtered predictions
            boxes = boxes_conf[to_keep].cpu().numpy().astype(int)
            coco_bboxes = convert_to_coco_format(boxes)
            classes = classes_conf[to_keep].cpu().numpy()
            scores = scores_conf[to_keep].cpu().numpy()

            print(output)
            print("High-confidence boxes:", boxes)            

        for bbox, label, score in zip(boxes, classes, scores):
            x1, y1, x2, y2 = bbox
            class_name = class_mappings.get(label, f'class_{label}')
            cv2.rectangle(image_np, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(image_np, f'{class_name}: {score:.2f}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        # Save result
        cv2.imwrite(output_path, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
        return output_path, coco_bboxes

# Download image from S3, process, and return local output path
def run_prediction_from_s3(s3_client, bucket_name, key, output_bucket, no_label_bucket, class_mapping_path):
    class_mappings = load_class_mapping(class_mapping_path)

    # Prepare variables for cleanup
    temp_path = None
    output_path = None

    try:
        # Download from S3 to temp file (keep extension)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(key)[-1]) as temp_file:
            s3_client.download_fileobj(bucket_name, key, temp_file)
            temp_path = temp_file.name

        # Open image and convert to RGB
        image = Image.open(temp_path).convert("RGB")
        image_np = np.array(image)

        # Prepare output path in temp directory
        output_file = f"pred_{os.path.basename(key)}"
        output_path = os.path.join(tempfile.gettempdir(), output_file)

        # Run prediction and draw bounding boxes
        output_path, coco_bboxes = predict_and_draw_from_array(image_np, class_mappings, output_path)

        # Handle case: no detections found
        if not coco_bboxes:
            print("No detections above confidence threshold.")
            with open(temp_path, "rb") as f:
                s3_client.put_object(Bucket=no_label_bucket, Key=key, Body=f)
            return None, []

        # Upload the resulting image back to S3 output bucket
        with open(output_path, "rb") as f:
            s3_client.put_object(Bucket=output_bucket, Key=output_file, Body=f)

        return output_path, coco_bboxes

    finally:
        # Cleanup temp files if they were created
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

def convert_to_coco_format(boxes):
    """
    Convert bounding boxes from [x1, y1, x2, y2] format to [x, y, width, height] (COCO format).
    
    Args:
        boxes (list or np.ndarray): List of bounding boxes in [x1, y1, x2, y2] format.

    Returns:
        list: Bounding boxes in [x, y, width, height] format.
    """
    boxes_coco = []
    print(type(boxes))
    for box in boxes:
        print(f'Box is {box}')
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        print(f'Box coordinates: {x1}, {y1}, {x2}, {y2}')
        print(type(x1), type(y1), type(x2), type(y2))
        width = x2 - x1
        height = y2 - y1
        boxes_coco.append([x1, y1, width, height])
    print(f'Boxes in COCO format: {boxes_coco}')
    return boxes_coco
