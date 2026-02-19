from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import os

app = Flask(__name__)

# Always save next to this script — no more "file not found" on Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_PATH = os.path.join(BASE_DIR, "response.mp3")

@app.route('/speak', methods=['POST'])
def speak():
    data = request.get_json()
    text = data.get('text', 'No response.')
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(AUDIO_PATH)
        print(f"[TTS] Saved audio to {AUDIO_PATH}")
        return jsonify({"status": "ok", "message": "Audio ready."})
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def get_audio():
    if not os.path.exists(AUDIO_PATH):
        return jsonify({"error": "No audio file found. Call /speak first."}), 404
    return send_file(AUDIO_PATH, mimetype="audio/mpeg")

if __name__ == '__main__':
    app.run(port=5004, debug=True)