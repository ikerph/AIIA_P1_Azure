import os
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import azure.functions as func
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

app = func.FunctionApp()


# Keys are read from the environment variables of the Function App.
# Clients are created in the first execution (not when the file is loaded)
vision_client = None
web_container = None


def get_clients():
    global vision_client, web_container
    if vision_client is None:
        vision_client = ImageAnalysisClient(
            endpoint=os.environ["VISION_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["VISION_KEY"])
        )
        # Container of the static website, where the results are written
        blob_service = BlobServiceClient.from_connection_string(os.environ["RawStorage"])
        web_container = blob_service.get_container_client("$web")
    return vision_client, web_container


# Runs every time an image is uploaded to "raw" (Event Grid)
@app.blob_trigger(arg_name="myblob", path="raw/{name}", connection="RawStorage",
                  source=func.BlobSource.EVENT_GRID)
def process_image(myblob: func.InputStream):
    start = time.time()
    vision_client, web_container = get_clients()
    blob_name = myblob.name.split("/")[-1]   # frame_20261002_121530_250.jpg
    image_data = myblob.read()

    # Analyze image with PEOPLE feature (Azure AI Vision)
    vision_start = time.time()
    result = vision_client.analyze(
        image_data=image_data,
        visual_features=[VisualFeatures.PEOPLE],
        language="en"
    )
    vision_ms = (time.time() - vision_start) * 1000

    # Decode the image to draw the boxes
    frame = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)

    person_count = 0
    if result.people is not None:
        for person in result.people.list:
            if person.confidence > 0.5:
                # Draw a bounding box around the person
                box = person.bounding_box
                p1 = (box.x, box.y)
                p2 = (box.x + box.width, box.y + box.height)
                cv2.rectangle(img=frame, pt1=p1, pt2=p2, color=(0, 255, 0), thickness=2)
                person_count = person_count + 1

    # Upload the processed frame to the web container
    ret, jpg = cv2.imencode(".jpg", frame)
    web_container.upload_blob("processed_frame.jpg", jpg.tobytes(), overwrite=True,
                              content_settings=ContentSettings(content_type="image/jpeg", cache_control="no-cache"))

    # Response time = now - capture time
    capture_time = datetime.strptime(blob_name, "frame_%Y%m%d_%H%M%S_%f.jpg")
    now = datetime.now(ZoneInfo("Europe/Madrid")).replace(tzinfo=None)
    response_ms = (now - capture_time).total_seconds() * 1000
    function_ms = (time.time() - start) * 1000

    # Append blob: several executions can write at the same time
    csv_blob = web_container.get_blob_client("database.csv")
    if not csv_blob.exists():
        csv_blob.create_append_blob(content_settings=ContentSettings(content_type="text/csv", cache_control="no-cache"))
        csv_blob.append_block("Timestamp,Person_Count,Vision_ms,Response_ms,Function_ms\n")

    timestamp = capture_time.strftime("%Y-%m-%d %H:%M:%S")
    csv_blob.append_block(f"{timestamp},{person_count},{vision_ms:.1f},{response_ms:.1f},{function_ms:.1f}\n")

    logging.info(f"{blob_name} -> {person_count} people | vision {vision_ms:.0f} ms | response {response_ms:.0f} ms")
