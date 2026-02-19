# vision/vision_service.py
# Gives AURA eyes — it can SEE your screen and click on things

from flask import Flask, request, jsonify
from groq import Groq
from PIL import ImageGrab, Image
import pyautogui
import base64, io, os, json, time
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SCREENSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen.png")

# ── Take a screenshot and return as base64 ──────────────────
def take_screenshot(region=None):
    """Captures screen, saves it, returns base64 string."""
    try:
        img = ImageGrab.grab(bbox=region)  # None = full screen
        img = img.resize((1280, 720), Image.LANCZOS)  # resize to save tokens
        img.save(SCREENSHOT_PATH)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"[VISION] Screenshot failed: {e}")
        return None

# ── Ask Groq Vision what's on screen ────────────────────────
def ask_vision(b64_image, question):
    """Send screenshot to Groq vision model and ask a question."""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Groq vision model
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": question
                        }
                    ]
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return None

# ── Find the pixel location of an icon by name ──────────────
def find_icon_location(b64_image, icon_name):
    """Ask vision model to return the x,y coordinates of an icon."""
    question = f"""Look at this screenshot carefully.
Find the icon or element named '{icon_name}' on screen.
Return ONLY a JSON object like this: {{"found": true, "x": 123, "y": 456, "description": "what you see"}}
If not found: {{"found": false, "x": 0, "y": 0, "description": "not found"}}
Return ONLY the JSON. Nothing else."""

    result = ask_vision(b64_image, question)
    if not result:
        return {"found": False, "x": 0, "y": 0, "description": "Vision failed"}
    try:
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except:
        return {"found": False, "x": 0, "y": 0, "description": result}

# ════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════

# 1. READ SCREEN — tell AURA what's on screen
@app.route('/read_screen', methods=['POST'])
def read_screen():
    """Take screenshot and describe what's visible."""
    data     = request.get_json() or {}
    question = data.get('question', 'What applications, icons, and folders do you see on the desktop? List everything visible.')
    print(f"[VISION] Reading screen...")
    b64 = take_screenshot()
    if not b64:
        return jsonify({"result": "Could not take screenshot."}), 500
    answer = ask_vision(b64, question)
    print(f"[VISION] Screen says: {str(answer)[:150]}")
    return jsonify({"result": answer or "Could not read screen."})

# 2. CLICK ICON — find and click something by name
@app.route('/click_icon', methods=['POST'])
def click_icon():
    """Find an icon/app/folder by name and click it."""
    data   = request.get_json() or {}
    target = data.get('target', '')
    action = data.get('action', 'double_click')  # single_click or double_click

    print(f"[VISION] Looking for '{target}' on screen...")
    b64  = take_screenshot()
    if not b64:
        return jsonify({"result": "Could not take screenshot."}), 500

    loc = find_icon_location(b64, target)
    print(f"[VISION] Found: {loc}")

    if not loc.get('found'):
        return jsonify({"result": f"I couldn't find '{target}' on your screen. {loc.get('description','')}"})

    x, y = int(loc['x']), int(loc['y'])

    # Scale coordinates back to actual screen resolution
    screen_w, screen_h = pyautogui.size()
    x = int(x * screen_w / 1280)
    y = int(y * screen_h / 720)

    pyautogui.moveTo(x, y, duration=0.4)
    time.sleep(0.2)
    if action == 'double_click':
        pyautogui.doubleClick(x, y)
    else:
        pyautogui.click(x, y)

    return jsonify({"result": f"Found '{target}' and clicked it. {loc.get('description', '')}"})

# 3. DESCRIBE SCREEN — what is AURA currently looking at
@app.route('/describe', methods=['POST'])
def describe():
    """Full description of current screen state."""
    b64 = take_screenshot()
    if not b64:
        return jsonify({"result": "Could not take screenshot."}), 500
    answer = ask_vision(b64, "Describe exactly what is on this screen in detail. List all visible icons, windows, folders, text, and taskbar items.")
    return jsonify({"result": answer or "Could not describe screen."})

# 4. FIND TEXT ON SCREEN
@app.route('/find_text', methods=['POST'])
def find_text():
    """Find specific text visible on screen."""
    data = request.get_json() or {}
    text = data.get('text', '')
    b64  = take_screenshot()
    if not b64:
        return jsonify({"result": "Could not take screenshot."}), 500
    answer = ask_vision(b64, f"Is the text '{text}' visible anywhere on this screen? If yes, describe where it is and return its approximate x,y coordinates as JSON. If no, say not found.")
    return jsonify({"result": answer or "Could not search screen."})

# 5. GET DESKTOP ICONS — list all icons on desktop
@app.route('/desktop_icons', methods=['GET'])
def desktop_icons():
    """List all icons visible on desktop + from filesystem."""
    # Method 1: Read from filesystem (reliable)
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    try:
        items = os.listdir(desktop_path)
        files   = [i for i in items if os.path.isfile(os.path.join(desktop_path, i))]
        folders = [i for i in items if os.path.isdir(os.path.join(desktop_path, i))]
        fs_result = f"Desktop folders: {', '.join(folders) or 'none'}\nDesktop files: {', '.join(files) or 'none'}"
    except Exception as e:
        fs_result = f"Could not read desktop folder: {e}"

    # Method 2: Visual scan (what AI sees on screen)
    b64    = take_screenshot()
    visual = ask_vision(b64, "List ALL icons you can see on the desktop. Include their approximate positions (left/center/right, top/middle/bottom of screen).") if b64 else "Screenshot failed."

    return jsonify({
        "filesystem": fs_result,
        "visual":     visual or "Could not scan visually.",
        "result":     fs_result  # used by gateway
    })

if __name__ == '__main__':
    print("[VISION] Screen vision service running on port 5005...")
    app.run(port=5005, debug=False)