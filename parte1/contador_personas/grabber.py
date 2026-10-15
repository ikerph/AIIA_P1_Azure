import cv2
from ultralytics import YOLO
import time
import csv
import os
from datetime import datetime
import yt_dlp

csv_filename = "database.csv"

yolo_net = YOLO("yolov8n.pt")  # load a pretrained model

# URL of the Youtube video stream
youtube_url = "https://www.youtube.com/watch?v=DjdUEyjx8GM"

# yt-dlp to get the url of the live stream
with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
    url = ydl.extract_info(youtube_url, download=False)["url"]

# Create a VideoCapture object to read frames from the stream
cap = cv2.VideoCapture()

# Set the VideoCapture object to use the stream
cap.open(url)

# Check if the stream is opened successfully
if not cap.isOpened():
    exit(1)

# Write CSV header
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Timestamp", "Person_Count", "Inference_ms"])

interval = 5  # seconds between processed frames
last_time = 0

while True:
    # Read a frame
    ret, frame = cap.read()

    # Check if frame succesfully read
    if not ret:
        break

    # Only one frame each 5s (due to buffer overflow)
    if time.time() - last_time < interval:
        continue
    last_time = time.time()

    # Perform person detection using YOLO
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

    # Create or open the CSV file for writing
    with open(csv_filename, mode='a', newline='') as csv_file:
        fieldnames = ["Timestamp", "Person_Count", "Inference_ms"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        # Write the timestamp and person count to the CSV file
        writer.writerow({"Timestamp": timestamp, "Person_Count": person_count, "Inference_ms": round(inference_ms, 1)})

    print(timestamp, "->", person_count, "people", "(" + str(round(inference_ms)) + " ms)")

    # Display the frame with detected persons
    cv2.imwrite('processed_frame.jpg', frame)

    # Press 'q' to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


# Release the VideoCapture and close the window
cap.release()
cv2.destroyAllWindows()
