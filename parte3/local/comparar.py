import os

# Allow OpenCV to connect youtube lives
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "extension_picky;0"

import cv2
import time
import numpy as np
import yt_dlp
from ultralytics import YOLO
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

# Task 3.6 => same frames with YOLOv8 and Azure AI Vision

# Keys and Endpoint of the Computer Vision resource
endpoint = "https://aiiavisionp3iker.cognitiveservices.azure.com/"
#key = "VISION_KEY"

num_frames = 5      # 1 call to Azure AI Vision per frame
interval = 10       # seconds between frames

yolo_net = YOLO("yolov8n.pt")
client = ImageAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

youtube_url = "https://www.youtube.com/watch?v=DjdUEyjx8GM"
with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
    url = ydl.extract_info(youtube_url, download=False)["url"]

cap = cv2.VideoCapture()
cap.open(url)
if not cap.isOpened():
    exit(1)

os.makedirs("comparison", exist_ok=True)
last_time = 0
saved = 0

print("Frame | YOLOv8 | Azure AI Vision")
while saved < num_frames:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    # Only one frame each 10s
    if time.time() - last_time < interval:
        continue
    last_time = time.time()

    # YOLOv8
    yolo_frame = frame.copy()
    yolo_count = 0
    detections = yolo_net.predict(source=frame, verbose=False)
    for detection in detections[0]:
        class_id = detection.boxes.cls.item()
        confidence = detection.boxes.conf.item()

        # Check if the detected object is a person (class_id 0)
        if class_id == 0 and confidence > 0.5:
            # Extract bounding box coordinates
            center_x, center_y, width, height = detection.boxes.xywh[0].tolist()
            x, y = (int(center_x - width / 2), int(center_y - height / 2))
            p1 = (x, y)
            p2=(int(x + width), int(y + height))

            # Draw a bounding box around the person
            cv2.rectangle(img=yolo_frame, pt1=p1, pt2=p2, color=(0, 255, 0), thickness=2)
            yolo_count = yolo_count + 1

    # Azure AI Vision
    vision_frame = frame.copy()
    vision_count = 0
    ret, jpg = cv2.imencode(".jpg", frame)
    result = client.analyze(
        image_data=jpg.tobytes(),
        visual_features=[VisualFeatures.PEOPLE],
        language="en"
    )
    if result.people is not None:
        for person in result.people.list:
            if person.confidence > 0.5:
                # Draw a bounding box around the person
                box = person.bounding_box
                p1 = (box.x, box.y)
                p2 = (box.x + box.width, box.y + box.height)
                cv2.rectangle(img=vision_frame, pt1=p1, pt2=p2, color=(0, 255, 0), thickness=2)
                vision_count = vision_count + 1

    # Save both results side by side
    cv2.putText(yolo_frame, "YOLOv8: " + str(yolo_count), (20, 700), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.putText(vision_frame, "Azure AI Vision: " + str(vision_count), (20, 700), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    saved = saved + 1
    cv2.imwrite("comparison/frame_" + str(saved) + ".jpg", np.hstack([yolo_frame, vision_frame]))
    print("  ", saved, " | ", yolo_count, " | ", vision_count)

cap.release()
print("Images saved in the folder comparison/")
