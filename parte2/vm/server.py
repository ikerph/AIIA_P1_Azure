from flask import Flask, request
import cv2
import numpy as np
from ultralytics import YOLO
import time
import csv
import os
import psutil
from datetime import datetime

# Folder served by Apache
web_folder = "/var/www/html"
csv_filename = os.path.join(web_folder, "database.csv")

yolo_net = YOLO("yolov8n.pt")  # load a pretrained model

app = Flask(__name__)

# Write the CSV header
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Timestamp", "Person_Count", "Inference_ms", "CPU_percent", "RAM_MB"])


# Receives a JPG frame from the local machine
@app.route("/upload", methods=["POST"])
def upload():
    # Decode the JPG image received
    image_data = np.frombuffer(request.data, np.uint8)
    frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    if frame is None:
        return {"error": "image not decoded"}, 400

    # Perform person detection using YOLOv8
    start = time.time()
    detections = yolo_net.predict(source=frame, verbose=False)
    inference_ms = (time.time() - start) * 1000

    person_count = 0
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
            cv2.rectangle(img=frame, pt1=p1, pt2=p2, color=(0, 255, 0), thickness=2)
            person_count = person_count + 1

    # Get the current date and time with seconds precision
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CPU and RAM of the VM => Task 2.5
    cpu_percent = psutil.cpu_percent()
    ram_mb = psutil.virtual_memory().used / (1024 * 1024)

    # Create or open the CSV file for writing
    with open(csv_filename, mode='a', newline='') as csv_file:
        fieldnames = ["Timestamp", "Person_Count", "Inference_ms", "CPU_percent", "RAM_MB"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        # Write the timestamp and person count to the CSV file
        writer.writerow({"Timestamp": timestamp, "Person_Count": person_count, "Inference_ms": round(inference_ms, 1),
                         "CPU_percent": cpu_percent, "RAM_MB": round(ram_mb)})

    print(timestamp, "->", person_count, "people", "(" + str(round(inference_ms)) + " ms)")

    # Save the frame with detected persons for the web page
    cv2.imwrite(os.path.join(web_folder, 'processed_frame.jpg'), frame)

    # Answer to the local machine with the result
    return {"person_count": person_count, "inference_ms": round(inference_ms, 1)}


# threaded=False: frames are processed one by one
app.run(host="0.0.0.0", port=5000, threaded=False)
