import os

# Allow OpenCV to connect youtube lives
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "extension_picky;0"

import cv2
import sys
import time
import threading
import pandas as pd
import yt_dlp
from datetime import datetime
from azure.storage.blob import BlobServiceClient

# Task 4.3 => N cameras to the serverless application
# How to use: python multi_func.py 8

# Connection string of the storage account 
#connection_string = "CONNECTION STRING"
web_csv_url = "https://aiiastoragep3iker.z43.web.core.windows.net/database.csv"

# Public cameras =>Task 4.1
cameras = [
    "https://www.youtube.com/watch?v=DjdUEyjx8GM",   # Tokyo, Kabukicho
    "https://www.youtube.com/watch?v=gFRtAAmiFbE",   # Tokyo, Kabukicho II
    "https://www.youtube.com/watch?v=i2PpmC1IeKk",   # Osaka, Dotonbori
    "https://www.youtube.com/watch?v=fvOgXk09PFY",   # Davao (Philippines)
    "https://www.youtube.com/watch?v=Gyn8efd2Jv8",   # Sapporo, Tanukikoji
    "https://www.youtube.com/watch?v=bMhaK0-DVMg",   # Tokyo, Adachi
]

num_cameras = int(sys.argv[1])
duration = 120          # seconds of the test
interval = 5            # seconds between frames of the same camera
vision_price = 0.00088  # EUR per image (Azure AI Vision)

container = BlobServiceClient.from_connection_string(connection_string).get_container_client("raw")

frames = {}         # last frame of each camera
results = []        # upload time and size of each frame
running = True


# Read one camera continuously and keep only its last frame
def read_camera(youtube_url):
    with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
        url = ydl.extract_info(youtube_url, download=False)["url"]
    cap = cv2.VideoCapture(url)
    while running:
        ret, frame = cap.read()
        if ret:
            frames[youtube_url] = frame


# Upload one frame every 5 seconds to "raw"
def send_camera(camera_id):
    youtube_url = cameras[camera_id % len(cameras)]
    time.sleep(camera_id * interval / num_cameras)   # do not send all at the same time
    while running:
        start = time.time()
        ret, jpg = cv2.imencode(".jpg", frames[youtube_url])
        blob_name = "cam" + str(camera_id) + "/" + datetime.now().strftime("frame_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"
        try:
            container.upload_blob(blob_name, jpg.tobytes(), overwrite=True)
            results.append({"Upload_ms": (time.time() - start) * 1000, "Frame_KB": len(jpg) / 1024})
        except Exception:
            print("Error: the frame could not be uploaded")
        time.sleep(max(0, interval - (time.time() - start)))


for youtube_url in cameras[:num_cameras]:
    threading.Thread(target=read_camera, args=(youtube_url,), daemon=True).start()
while len(frames) < min(num_cameras, len(cameras)):
    time.sleep(1)

print("Sending", num_cameras, "cameras to the cloud application", duration, "s")
start_test = datetime.now()
for camera_id in range(num_cameras):
    threading.Thread(target=send_camera, args=(camera_id,), daemon=True).start()
time.sleep(duration)
running = False
end_test = datetime.now()

print("Waiting 30 seconds for processing everything...")
time.sleep(30)

# Results 
data = pd.DataFrame(results)
func = pd.read_csv(web_csv_url, parse_dates=["Timestamp"])
func = func[(func["Timestamp"] >= start_test.replace(microsecond=0)) & (func["Timestamp"] <= end_test)]

print()
print("Cameras:", num_cameras, "| Frames uploaded:", len(data), "of", num_cameras * duration // interval,
      "| Frames processed:", len(func))
print("Response time: mean %.0f ms | max %.0f ms" % (func["Response_ms"].mean(), func["Response_ms"].max()))
print("People per frame (Azure AI Vision): mean %.1f" % func["Person_Count"].mean())
print("Bandwidth: %.2f Mbit/s" % (data["Frame_KB"].sum() * 8 / 1024 / duration))
print("Cost: %.2f EUR per hour per camera | %.2f EUR this test" % (
    3600 / interval * vision_price, len(func) * vision_price))
