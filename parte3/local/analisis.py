import pandas as pd
import matplotlib.pyplot as plt
import requests

# Task 3.6 => performance of the serverless application
# - upload_times.csv
# - database.csv: written by the Azure Function
web_csv_url = "https://aiiastoragep3iker.z43.web.core.windows.net/database.csv"

with open("database_function.csv", "w", newline="") as f:
    f.write(requests.get(web_csv_url).text)

local = pd.read_csv("upload_times.csv", parse_dates=["Timestamp"])
func = pd.read_csv("database_function.csv", parse_dates=["Timestamp"])

# Only the frames of this test
start_time = local["Timestamp"].min().floor("s")
end_time = local["Timestamp"].max().ceil("s")
func = func[(func["Timestamp"] >= start_time) & (func["Timestamp"] <= end_time)]

# Price of Azure AI Vision (France Central)
vision_price = 0.88 / 1000   # EUR per image

# Cold start is the slowest execution
cold_start = func["Function_ms"].max()

print("Frames uploaded:", len(local), "| Frames processed by the function:", len(func))
duration = (local["Timestamp"].max() - local["Timestamp"].min()).total_seconds()
print("Real rate: %.2f frames per second (target: 2)" % (len(local) / duration))
print()
print("Response time: mean %.0f ms | median %.0f ms | max %.0f ms" % (func["Response_ms"].mean(), func["Response_ms"].median(), func["Response_ms"].max()))
print("Upload: mean %.0f ms" % local["Upload_ms"].mean())
print("Function: mean %.0f ms | max %.0f ms (cold start)" % (func["Function_ms"].mean(), cold_start))
print("Azure AI Vision: mean %.0f ms" % func["Vision_ms"].mean())
print("Frame size: mean %.1f KB" % local["Frame_KB"].mean())
print()
# Every uploaded frame triggers one call to Azure AI Vision
print("Cost: %.5f EUR per frame | %.2f EUR this test | %.2f EUR per hour at 2 frames/s" % (vision_price, len(local) * vision_price, 7200 * vision_price))

# Graph of the response time of each frame
func = func.sort_values("Timestamp")
plt.figure(figsize=(10, 4))
plt.plot(func["Timestamp"], func["Response_ms"], label="Total response time")
plt.plot(func["Timestamp"], func["Function_ms"], label="Function execution time")
plt.plot(func["Timestamp"], func["Vision_ms"], label="Azure AI Vision time")
plt.xlabel("Time")
plt.ylabel("ms")
plt.title("Response time of the serverless application")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("response_time_p3.png", dpi=150)
