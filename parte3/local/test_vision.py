import os
import cv2
import time
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

# Task 3.4 => test of Azure AI Vision

# Keys and Endpoint of the resource
endpoint = "https://aiiavisionp3iker.cognitiveservices.azure.com/"
#key = "VISION_KEY"

# Create an Image Analysis client
client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

# Load image to analyze into a 'bytes' object
with open("frame.jpg", "rb") as f:
    image_data = f.read()

# Analyze image with PEOPLE feature
start = time.time()
result = client.analyze(
    image_data=image_data,
    visual_features=[VisualFeatures.PEOPLE],
    language="en"
)
analysis_ms = (time.time() - start) * 1000

frame = cv2.imread("frame.jpg")
person_count = 0

if result.people is not None:
    for person in result.people.list:
        confidence = person.confidence
        if confidence > 0.5:
            bounding_box = person.bounding_box
            print("Confidence:", round(confidence, 2), "| Bounding Box:", bounding_box)

            # Draw a box around the person
            p1 = (bounding_box.x, bounding_box.y)
            p2 = (bounding_box.x + bounding_box.width, bounding_box.y + bounding_box.height)
            cv2.rectangle(img=frame, pt1=p1, pt2=p2, color=(0, 255, 0), thickness=2)
            person_count = person_count + 1
else:
    print("Analysis failed.")

print()
print("People detected:", person_count, "| Azure AI Vision time:", round(analysis_ms), "ms")

cv2.imwrite("frame_vision.jpg", frame)
