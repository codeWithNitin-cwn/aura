# AURA - Autonomous Universal Response Assistant

AURA is a voice-controlled AI assistant I built as a personal project. You speak a command, it figures out what you want, does it, and talks back. Everything runs locally on your machine.

---

## How it works

When you speak into the browser, the audio gets sent to a Whisper model that converts it to text. That text goes to Gemini which figures out what you're asking for and which tool to use. The tool runs, and the result gets read back to you using gTTS.

The whole thing is split into 5 separate Flask services that talk to each other:

```
Browser  ->  Gateway (5000)  ->  ASR (5001)  ->  NLP (5002)  ->  Tools (5003)  ->  TTS (5004)
```

There's also a Vision service (5005) for screen reading and clicking.

---

## What it can do

- Voice and text input
- Web search
- Calendar events
- Email
- File operations (create, read, edit, find)
- Screen reading and UI control
- Open and close applications
- System info like RAM usage, current time, etc.

---

## Stack

- Python and Flask for all the backend services
- Whisper for speech recognition, runs offline
- Gemini API for understanding commands
- gTTS for the voice responses
- Vanilla HTML, CSS and JS for the frontend

---

## Running it locally

Clone the repo and install dependencies:

```bash
git clone https://github.com/codeWithNitin-cwn/aura.git
cd aura
pip install -r requirements.txt
```

You'll also need ffmpeg installed and added to PATH. Download it from ffmpeg.org.

Create a .env file in the root folder with your Gemini API key:

```
GEMINI_API_KEY=your_key_here
```

You can get a free key from aistudio.google.com.

Then start everything:

```bash
python start/run_all.py
```

On Windows you can also just double-click start_aura.bat. Once it's running open localhost:5000 in your browser.

---

## Project structure

```
aura/
  asr/          Whisper speech to text service
  gateway/      Main entry point, routing, and frontend
  nlp/          Gemini intent parsing
  tools/        Tool execution (search, calendar, files, etc.)
  tts/          Text to speech
  vision/       Screen reading and UI control
  start/        Scripts to launch all services at once
```

---

## Notes

Whisper downloads a model around 140MB the first time it runs so you need internet for that first launch. After that it works completely offline. The .env file is not included in the repo so you'll need to create your own with your API key.

This is a prototype. Facial recognition and a few other planned features are not built yet.

---

Built by Nitin
github.com/codeWithNitin-cwn
