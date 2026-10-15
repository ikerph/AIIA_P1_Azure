import os

# Allow OpenCV to connect youtube live
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "extension_picky;0"

import cv2
import requests
import time
import csv
from datetime import datetime
import yt_dlp

# Public IP of the Azure VM and port of the Flask server
vm_url = "http://70.156.165.2:5000/upload"

# Local CSV with the response times measured from the local machine => Task 2.5
csv_filename = "response_times.csv"

# URL of the Youtube video stream
youtube_url = "https://www.youtube.com/watch?v=DjdUEyjx8GM"

# yt-dlp to get the url of the live stream
def get_stream_url():
    with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
        return ydl.extract_info(youtube_url, download=False)["url"]

# Create a VideoCapture object to read frames from the stream
cap = cv2.VideoCapture()

# Set the VideoCapture object to use the HLS stream
cap.open(get_stream_url())

# Check if the stream is opened successfully
if not cap.isOpened():
    exit(1)

# Write the CSV header
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Timestamp", "Person_Count", "Inference_ms", "Response_ms", "Frame_KB"])

interval = 5  # seconds between frames sent
last_time = 0

while True:
    # Read a frame from the stream
    ret, frame = cap.read()

    # Reopen if stream is down
    if not ret:
        print("Reopening the stream...")
        cap.release()
        time.sleep(2)
        cap.open(get_stream_url())
        continue

    # Only one frame each 5s
    if time.time() - last_time < interval:
        continue
    last_time = time.time()

    # Encode  frame as JPG to send it
    ret, jpg = cv2.imencode(".jpg", frame)
    image_data = jpg.tobytes()
    frame_kb = len(image_data) / 1024

    # Send the frame to the VM and wait for the result
    start = time.time()
    try:
        response = requests.post(vm_url, data=image_data, headers={"Content-Type": "image/jpeg"}, timeout=30)
        result = response.json()
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        continue
    response_ms = (time.time() - start) * 1000

    # Get the current date and time with seconds precision
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create or open the CSV file for writing
    with open(csv_filename, mode='a', newline='') as csv_file:
        fieldnames = ["Timestamp", "Person_Count", "Inference_ms", "Response_ms", "Frame_KB"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writerow({"Timestamp": timestamp, "Person_Count": result["person_count"],
                         "Inference_ms": result["inference_ms"], "Response_ms": round(response_ms, 1),
                         "Frame_KB": round(frame_kb, 1)})

    print(timestamp, "->", result["person_count"], "people",
          "| inference", round(result["inference_ms"]), "ms",
          "| response", round(response_ms), "ms",
          "| frame", round(frame_kb), "KB")


# Release the VideoCapture
cap.release()
