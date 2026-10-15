import os

# Allow OpenCV to connect youtube lives
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "extension_picky;0"

import cv2
import sys
import time
import threading
import requests
import pandas as pd
import yt_dlp
from datetime import datetime

# Task 4.2 => N cameras to the VM
# Usage: python multi_vm.py 8

vm_url = "http://70.156.165.2:5000/upload"
vm_csv_url = "http://70.156.165.2/database.csv"

# Public cameras (Task 4.1)
cameras = [
    "https://www.youtube.com/watch?v=DjdUEyjx8GM",   # Tokyo, Kabukicho
    "https://www.youtube.com/watch?v=gFRtAAmiFbE",   # Tokyo, Kabukicho II
    "https://www.youtube.com/watch?v=i2PpmC1IeKk",   # Osaka, Dotonbori
    "https://www.youtube.com/watch?v=fvOgXk09PFY",   # Davao (Philippines)
    "https://www.youtube.com/watch?v=Gyn8efd2Jv8",   # Sapporo, Tanukikoji
    "https://www.youtube.com/watch?v=bMhaK0-DVMg",   # Tokyo, Adachi
]

num_cameras = int(sys.argv[1])
duration = 120      # test seconds
interval = 5        # seconds between frames
vm_price = 0.018    # money per hour in euros

frames = {}         # last frame of each camera
results = []        # response time and size of each frame
running = True


# Read one camera and its last frame
def read_camera(youtube_url):
    with yt_dlp.YoutubeDL({"format": "bestvideo[height<=720]", "quiet": True}) as ydl:
        url = ydl.extract_info(youtube_url, download=False)["url"]
    cap = cv2.VideoCapture(url)
    while running:
        ret, frame = cap.read()
        if ret:
            frames[youtube_url] = frame


# Send one frame every 5 seconds to the VM (repeat if N > 6)
def send_camera(camera_id):
    youtube_url = cameras[camera_id % len(cameras)]
    time.sleep(camera_id * interval / num_cameras)   # do not send all at the same time
    while running:
        start = time.time()
        ret, jpg = cv2.imencode(".jpg", frames[youtube_url])
        try:
            requests.post(vm_url, data=jpg.tobytes(), headers={"Content-Type": "image/jpeg"}, timeout=60)
            results.append({"Response_ms": (time.time() - start) * 1000, "Frame_KB": len(jpg) / 1024})
        except requests.exceptions.RequestException:
            print("VM did not answer")
        time.sleep(max(0, interval - (time.time() - start)))


for youtube_url in cameras[:num_cameras]:
    threading.Thread(target=read_camera, args=(youtube_url,), daemon=True).start()
while len(frames) < min(num_cameras, len(cameras)):
    time.sleep(1)

print("Sending", num_cameras, "cameras to the VM during", duration, "seconds...")
start_test = datetime.now()
for camera_id in range(num_cameras):
    threading.Thread(target=send_camera, args=(camera_id,), daemon=True).start()
time.sleep(duration)
running = False
end_test = datetime.now()

# Response time and bandwidth 
data = pd.DataFrame(results)
# CPU and RAM of the VM 
vm = pd.read_csv(vm_csv_url, parse_dates=["Timestamp"])
vm = vm[(vm["Timestamp"] >= start_test.replace(microsecond=0)) & (vm["Timestamp"] <= end_test)]

print("Cameras:", num_cameras, "| Frames processed:", len(data), "of", num_cameras * duration // interval)
print("Response time: mean %.0f ms | max %.0f ms" % (data["Response_ms"].mean(), data["Response_ms"].max()))
print("CPU of the VM: mean %.1f %% | max %.1f %%" % (vm["CPU_percent"].mean(), vm["CPU_percent"].max()))
print("Memory of the VM: max %.0f MB of 843 MB" % vm["RAM_MB"].max())
print("Bandwidth: %.2f Mbit/s" % (data["Frame_KB"].sum() * 8 / 1024 / duration))
print("Cost: %.4f EUR per hour per camera" % (vm_price / num_cameras))
