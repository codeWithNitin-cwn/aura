# gateway/app.py
import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASR_URL    = "http://localhost:5001/transcribe"
NLP_URL    = "http://localhost:5002/parse"
TOOL_URL = "http://localhost:5003/execute"
TTS_URL    = "http://localhost:5004/speak"
VISION_URL = "http://localhost:5005"

VISION_TOOLS = {"read_screen", "click_icon", "describe_screen", "desktop_icons", "find_text"}
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(BASE_DIR, path)

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

def run_pipeline(text, use_tts=True):

    """Shared pipeline: text → NLP → Tool/Vision → TTS"""

    # Step 1: NLP
    nlp_resp    = requests.post(NLP_URL, json={"text": text})
    intent_data = nlp_resp.json()
    print(f"[NLP] Intent: {intent_data}")

    tool   = intent_data.get("tool", "general")
    params = intent_data.get("params", {})

    # Step 2: Route to Vision or Tool service
    if tool in VISION_TOOLS:
        endpoint_map = {
            "read_screen":     f"{VISION_URL}/read_screen",
            "click_icon":      f"{VISION_URL}/click_icon",
            "describe_screen": f"{VISION_URL}/describe",
            "desktop_icons":   f"{VISION_URL}/desktop_icons",
            "find_text":       f"{VISION_URL}/find_text",
        }
        if tool == "desktop_icons":
            resp = requests.get(endpoint_map[tool])
        else:
            resp = requests.post(endpoint_map[tool], json=params)
        result = resp.json().get("result", "Done.")
    else:
        resp   = requests.post(TOOL_URL, json=intent_data)
        result = resp.json()["result"]

    print(f"[RESULT] {str(result)[:150]}")

    # Step 3: TTS
    audio_url = None

    if use_tts:
        requests.post(TTS_URL, json={"text": str(result)[:500]})
        audio_url = "http://localhost:5004/audio"

    

    return result, audio_url

# ── VOICE route (existing) ──────────────────────────────────
@app.route("/process", methods=["POST"])
def process():
    try:
        audio = request.files.get("audio")

        # ASR
        asr_resp = requests.post(ASR_URL, files={"audio": (audio.filename, audio.read(), "audio/webm")})
        text = asr_resp.json()["text"]
        print(f"[ASR] User said: {text}")

        result, audio_url = run_pipeline(text)

        return jsonify({
            "user_said": text,
            "response":  result,
            "audio_url": audio_url
        })
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e), "user_said": "", "response": "Something went wrong!"}), 500

# ── TEXT route (new) ────────────────────────────────────────
@app.route("/process_text", methods=["POST"])
def process_text():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No text provided"}), 400
        print(f"[TEXT] User typed: {text}")
        result, audio_url = run_pipeline(text, use_tts=False)


        return jsonify({
            "user_said": text,
            "response":  result,
            "audio_url": audio_url
        })
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e), "response": "Something went wrong!"}), 500

if __name__ == "__main__":
    print("Gateway running on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)