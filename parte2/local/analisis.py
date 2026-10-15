import pandas as pd
import matplotlib.pyplot as plt
import requests

#  Task 2.5 => performance data of the Virtual Machine
# - response_times.csv
# - database.csv: measured on the VM by server.py
vm_csv_url = "http://70.156.165.2/database.csv"

with open("database_vm.csv", "w", newline="") as f:
    f.write(requests.get(vm_csv_url).text)

local = pd.read_csv("response_times.csv", parse_dates=["Timestamp"])
vm = pd.read_csv("database_vm.csv", parse_dates=["Timestamp"])

print("Frames removed (warm-up):", (local["Inference_ms"] > 1000).sum())
local = local[local["Inference_ms"] <= 1000]
vm = vm[vm["Inference_ms"] <= 1000]

# Network time = total response time - inference time on the VM
local["Network_ms"] = local["Response_ms"] - local["Inference_ms"]

# One frame every 5 seconds
interval = 5
frame_kb = local["Frame_KB"].mean()

print("Frames analysed:", len(local))
print("Response time: mean %.0f ms, median %.0f ms" % (local["Response_ms"].mean(), local["Response_ms"].median()))
print("Inference time: mean %.0f ms" % local["Inference_ms"].mean())
print("Network time: mean %.0f ms" % local["Network_ms"].mean())
print("CPU: mean %.1f %%, max %.1f %%" % (vm["CPU_percent"].mean(), vm["CPU_percent"].max()))
print("RAM: mean %.0f MB, max %.0f MB" % (vm["RAM_MB"].mean(), vm["RAM_MB"].max()))
print("Frame size: %.1f KB" % frame_kb)
print("Upload: %.1f MB per minute, %.1f MB per hour" % (frame_kb * 60 / interval / 1024, frame_kb * 3600 / interval / 1024))

# Graph of the response time over time
plt.figure(figsize=(10, 4))
plt.plot(local["Timestamp"], local["Response_ms"], label="Total response time")
plt.plot(local["Timestamp"], local["Inference_ms"], label="Inference time (VM)")
plt.xlabel("Time")
plt.ylabel("ms")
plt.title("Response time of the Azure VM")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("response_time.png", dpi=150)