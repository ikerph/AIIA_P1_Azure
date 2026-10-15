import os

# Allow OpenCV to connect youtube lives
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "extension_picky;0"

import cv2
import time
import csv
from datetime import datetime
import yt_dlp
from azure.storage.blob import BlobServiceClient, ContentSettings

# Connection string of the storage account (Access keys), not written in the code
# RawStorage = "DefaultEndpointsProtocol=https;AccountName=aiiastoragep3iker;AccountKey=..."
#connection_string = "CONNECTION_STRING"

# Container for the raw images
container_name = "raw"

# Local CSV with the upload times => Task 3.6
csv_filename = "upload_times.csv"

interval = 0.5      # seconds between frames uploaded
max_frames = 600   # 5 minutes, to limit the cost

# URL of the Youtube video stream
youtube_url = "https://www.youtube.com/watch?v=DjdUEyjx8GM"

# yt-dlp to get the url of the live stream
def get_stream_url():
    with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
        return ydl.extract_info(youtube_url, download=False)["url"]

# Connect to the container of the storage account
blob_service = BlobServiceClient.from_connection_string(connection_string)
container = blob_service.get_container_client(container_name)

# Create a VideoCapture object to read frames from the stream
cap = cv2.VideoCapture()

# Set the VideoCapture object to use the HLS stream
cap.open(get_stream_url())

# Check if the stream is opened successfully
if not cap.isOpened():
    print("Error: Could not open the stream.")
    exit(1)

# Write the CSV header
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Timestamp", "Blob_name", "Upload_ms", "Frame_KB"])

last_time = 0
uploaded = 0

while uploaded < max_frames:
    # Read a frame from the stream
    ret, frame = cap.read()

    # If the stream is cut, reopen it with a new url
    if not ret:
        print("Reopening the stream...")
        cap.release()
        time.sleep(2)
        cap.open(get_stream_url())
        continue

    # Only one frame each 0.5s
    if time.time() - last_time < interval:
        continue
    last_time = time.time()

    # Encode the frame as JPG to upload it
    ret, jpg = cv2.imencode(".jpg", frame)
    image_data = jpg.tobytes()
    frame_kb = len(image_data) / 1024

    # Capture time in the name => response time
    capture_time = datetime.now()
    blob_name = capture_time.strftime("frame_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"

    # Upload the frame to the raw container
    start = time.time()
    try:
        container.upload_blob(blob_name, image_data, overwrite=True,
                              content_settings=ContentSettings(content_type="image/jpeg"))
    except Exception as e:
        print("Error: Could not upload the frame.", e)
        continue
    upload_ms = (time.time() - start) * 1000
    uploaded = uploaded + 1

    # Create or open the CSV file for writing
    with open(csv_filename, mode='a', newline='') as csv_file:
        fieldnames = ["Timestamp", "Blob_name", "Upload_ms", "Frame_KB"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writerow({"Timestamp": capture_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "Blob_name": blob_name,
                         "Upload_ms": round(upload_ms, 1), "Frame_KB": round(frame_kb, 1)})

    print("[" + str(uploaded) + "/" + str(max_frames) + "]", blob_name,
          "| upload", round(upload_ms), "ms", "| frame", round(frame_kb), "KB")


# Release the VideoCapture
cap.release()
