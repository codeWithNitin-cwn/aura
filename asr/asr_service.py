import whisper
import tempfile
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
model = whisper.load_model("base")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files["audio"]
    tmp_path = tempfile.mktemp(suffix=".webm")
    audio_file.save(tmp_path)

    try:
        result = model.transcribe(tmp_path, language="en")
        text = result["text"].strip()
        print(f"[ASR] Transcribed: {text}")
    except Exception as e:
        print(f"[ASR ERROR] {e}")
        text = "sorry I could not hear that"

    try:
        os.remove(tmp_path)
    except:
        pass

    return jsonify({"text": text})

if __name__ == "__main__":
    print("ASR Service running on port 5001...")
    app.run(port=5001, debug=False)