import subprocess

services = [
    "gateway/app.py",
    "asr/asr_service.py",
    "nlp/nlp_service.py",
    "tools/tool_service.py",
    "tts/tts_service.py",
    "vision/vision_service.py",
]

for service in services:
    subprocess.Popen(["python", service])

print("All AURA services started.")
