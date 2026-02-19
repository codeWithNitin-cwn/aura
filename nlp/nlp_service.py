from flask import Flask, request, jsonify
from groq import Groq
import os, json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an intent parser for a desktop AI assistant called AURA.
Given the user's spoken command, return ONLY a raw JSON object. No markdown, no code fences, no explanation.

IMPORTANT for file operations: The user will just say a filename like "demo.txt" or "notes.txt".
You do NOT need the full path. Just pass the filename as-is. AURA will find it automatically.

Available tools:

web_search   → {"intent":"search",       "tool":"web_search",   "params":{"query":"..."}}
calendar     → {"intent":"calendar",     "tool":"calendar",     "params":{"action":"add","title":"...","datetime":"..."}}
email        → {"intent":"email",        "tool":"email",        "params":{"to":"...","subject":"...","body":"..."}}
open_app     → {"intent":"open_app",     "tool":"open_app",     "params":{"target":"chrome|notepad|calculator|spotify|vs code|explorer|cmd|word|excel|powerpoint"}}
close_app    → {"intent":"close_app",    "tool":"close_app",    "params":{"target":"chrome|notepad|..."}}
read_file    → {"intent":"read_file",    "tool":"read_file",    "params":{"path":"demo.txt"}}
create_file  → {"intent":"create_file",  "tool":"create_file",  "params":{"path":"demo.txt","content":"..."}}
edit_file    → {"intent":"edit_file",    "tool":"edit_file",    "params":{"path":"demo.txt","content":"new content","mode":"overwrite|append"}}
delete_file  → {"intent":"delete_file",  "tool":"delete_file",  "params":{"path":"demo.txt"}}
list_files   → {"intent":"list_files",   "tool":"list_files",   "params":{"path":"desktop|downloads|documents|pictures"}}
find_file    → {"intent":"find_file",    "tool":"find_file",    "params":{"name":"demo.txt"}}
mouse        → {"intent":"mouse",        "tool":"mouse",        "params":{"action":"click|move|scroll_up|scroll_down|right_click|double_click","x":100,"y":200}}
keyboard     → {"intent":"keyboard",     "tool":"keyboard",     "params":{"action":"type|hotkey|press|screenshot","text":"...","keys":"ctrl+c","key":"enter"}}
volume       → {"intent":"volume",       "tool":"volume",       "params":{"action":"up|down|mute","amount":5}}
system_info  → {"intent":"system_info",  "tool":"system_info",  "params":{"query":"all|cpu|ram|disk|battery|system"}}
window       → {"intent":"window",       "tool":"window",       "params":{"action":"list|focus|minimize|maximize","target":"..."}}
read_screen  → {"intent":"read_screen",  "tool":"read_screen",  "params":{"question":"what do you see?"}}
click_icon   → {"intent":"click_icon",   "tool":"click_icon",   "params":{"target":"Chrome|Recycle Bin|...","action":"double_click"}}
desktop_icons→ {"intent":"desktop_icons","tool":"desktop_icons","params":{}}
general      → {"intent":"general",      "tool":"general",      "params":{"response":"..."}}

Examples:
"Delete demo.txt"              → {"intent":"delete_file","tool":"delete_file","params":{"path":"demo.txt"}}
"Read notes.txt"               → {"intent":"read_file","tool":"read_file","params":{"path":"notes.txt"}}
"Edit demo.txt add hello"      → {"intent":"edit_file","tool":"edit_file","params":{"path":"demo.txt","content":"hello","mode":"append"}}
"Create test.txt"              → {"intent":"create_file","tool":"create_file","params":{"path":"test.txt","content":""}}
"Find report.pdf"              → {"intent":"find_file","tool":"find_file","params":{"name":"report.pdf"}}
"Show desktop files"           → {"intent":"list_files","tool":"list_files","params":{"path":"desktop"}}
"Show downloads"               → {"intent":"list_files","tool":"list_files","params":{"path":"downloads"}}
"Open Chrome"                  → {"intent":"open_app","tool":"open_app","params":{"target":"chrome"}}
"What is my RAM?"              → {"intent":"system_info","tool":"system_info","params":{"query":"ram"}}
"Take a screenshot"            → {"intent":"keyboard","tool":"keyboard","params":{"action":"screenshot"}}
"Turn up volume"               → {"intent":"volume","tool":"volume","params":{"action":"up","amount":5}}
"Press Ctrl S"                 → {"intent":"keyboard","tool":"keyboard","params":{"action":"hotkey","keys":"ctrl+s"}}
"What's on my screen?"         → {"intent":"read_screen","tool":"read_screen","params":{"question":"what do you see?"}}
"Show desktop icons"           → {"intent":"desktop_icons","tool":"desktop_icons","params":{}}

Return ONLY raw JSON. Nothing else."""

def call_groq(text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f'User said: "{text}"'}
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[NLP ERROR] {e}")
        return {"intent":"general","tool":"general","params":{"response":"Sorry, I didn't understand that."}}

@app.route('/parse', methods=['POST'])
def parse():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400
    result = call_groq(text)
    print(f"[NLP] '{text}' → {result}")
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5002, debug=False)