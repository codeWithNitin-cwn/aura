from flask import Flask, request, jsonify
from ddgs import DDGS
import csv, os, time, subprocess, psutil, platform, shutil, glob
from datetime import datetime
import pyautogui
import pygetwindow as gw

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pyautogui.FAILSAFE = True

# ════════════════════════════════════════════
# UNIVERSAL FILE FINDER
# Searches everywhere on the PC for a filename
# ════════════════════════════════════════════
SEARCH_LOCATIONS = [
    os.path.expanduser('~\\Desktop'),
    os.path.expanduser('~\\Documents'),
    os.path.expanduser('~\\Downloads'),
    os.path.expanduser('~\\Pictures'),
    os.path.expanduser('~\\Videos'),
    os.path.expanduser('~\\Music'),
    os.path.expanduser('~'),
    'C:\\Users\\Nitin',
    'C:\\',
]

def find_file_everywhere(filename):
    """Search for a file by name across all common locations. Returns list of full paths."""
    found = []
    if os.path.exists(filename):
        return [filename]

    name = os.path.basename(filename) if os.path.sep in filename else filename

    for location in SEARCH_LOCATIONS:
        if not os.path.exists(location):
            continue
        try:
            matches = glob.glob(os.path.join(location, '**', name), recursive=True)
            for m in matches:
                if m not in found:
                    found.append(m)
            if found:
                break
        except Exception:
            continue
    return found

def resolve_path(path):
    path = os.path.expandvars(os.path.expanduser(path.strip()))
    if os.path.exists(path):
        return path, None
    results = find_file_everywhere(path)
    if results:
        return results[0], None
    if os.path.sep in path or ':' in path:
        return path, None
    desktop = os.path.expanduser('~\\Desktop')
    return os.path.join(desktop, path), None


# ════════════════════════════════════════════
# 1. WEB SEARCH
# ════════════════════════════════════════════
def tool_web_search(params):
    query = params.get('query', '')
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3, backend="lite"))
        if not results:
            return f"No results found for '{query}'."
        lines = [f"Here's what I found about '{query}':"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}: {r['body'][:200]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"

# ════════════════════════════════════════════
# 2. CALENDAR
# ════════════════════════════════════════════
def tool_calendar(params):
    action = params.get('action', 'add')
    title  = params.get('title', 'Untitled Event')
    dt     = params.get('datetime', 'unspecified time')
    log    = os.path.join(BASE_DIR, "calendar.csv")
    with open(log, 'a', newline='') as f:
        csv.writer(f).writerow([datetime.now().isoformat(), action, title, dt])
    return f"Added '{title}' to your calendar at {dt}."

# ════════════════════════════════════════════
# 3. EMAIL
# ════════════════════════════════════════════
def tool_email(params):
    import webbrowser, urllib.parse
    to      = params.get('to', '')
    subject = params.get('subject', 'No Subject')
    body    = params.get('body', '')

    if not to:
        return "No recipient specified. Please say who to send it to."

    url = (
        "https://mail.google.com/mail/?view=cm"
        f"&to={urllib.parse.quote(to)}"
        f"&su={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
    )
    webbrowser.open(url)
    return f"Gmail opened — composing email to {to} with subject '{subject}'. Just hit Send."

# ════════════════════════════════════════════
# 4. OPEN APP
# ════════════════════════════════════════════
APP_MAP = {
    'chrome':        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'google chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'notepad':       'notepad.exe',
    'calculator':    'calc.exe',
    'paint':         'mspaint.exe',
    'file explorer': 'explorer.exe',
    'explorer':      'explorer.exe',
    'vs code':       'code',
    'vscode':        'code',
    'spotify':       r'C:\Users\Nitin\AppData\Roaming\Spotify\Spotify.exe',
    'task manager':  'taskmgr.exe',
    'cmd':           'cmd.exe',
    'terminal':      'cmd.exe',
    'word':          r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE',
    'excel':         r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE',
    'powerpoint':    r'C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE',
}

def tool_open_app(params):
    target = params.get('target', '').lower()
    path   = APP_MAP.get(target)

    try:
        if path:
            subprocess.Popen(path, shell=True)
        else:
            subprocess.Popen(f'start "" "{target}"', shell=True)
        return f"Opening {target}."
    except Exception as e:
        return f"Could not open {target}: {e}"

# ════════════════════════════════════════════
# 4b. OPEN FOLDER — searches everywhere, opens in Explorer
# ════════════════════════════════════════════
FOLDER_SHORTCUTS = {
    'desktop':   os.path.expanduser('~\\Desktop'),
    'documents': os.path.expanduser('~\\Documents'),
    'downloads': os.path.expanduser('~\\Downloads'),
    'pictures':  os.path.expanduser('~\\Pictures'),
    'music':     os.path.expanduser('~\\Music'),
    'videos':    os.path.expanduser('~\\Videos'),
    'home':      os.path.expanduser('~'),
    'c drive':   'C:\\',
    'c:':        'C:\\',
}

def tool_open_folder(params):
    name = params.get('name', '').strip()
    if not name:
        subprocess.Popen('explorer.exe')
        return "Opened File Explorer."

    # Check shortcut names first
    shortcut = FOLDER_SHORTCUTS.get(name.lower())
    if shortcut:
        subprocess.Popen(f'explorer "{shortcut}"')
        return f"Opened {name} folder."

    # Check if it's already a full path
    if os.path.isdir(name):
        subprocess.Popen(f'explorer "{name}"')
        return f"Opened folder: {name}"

    # Search in all common locations recursively
    search_roots = [
        os.path.expanduser('~\\Desktop'),
        os.path.expanduser('~\\Documents'),
        os.path.expanduser('~\\Downloads'),
        os.path.expanduser('~'),
        'C:\\Users\\Nitin',
    ]

    found = None
    for root in search_roots:
        if not os.path.exists(root):
            continue
        try:
            for dirpath, dirnames, _ in os.walk(root):
                for d in dirnames:
                    if d.lower() == name.lower():
                        found = os.path.join(dirpath, d)
                        break
                if found:
                    break
        except Exception:
            continue
        if found:
            break

    if found:
        subprocess.Popen(f'explorer "{found}"')
        return f"Found and opened folder: {found}"

    # Last resort: open Explorer with Windows search
    subprocess.Popen(
        f'explorer "search-ms:displayname=Search Results&query={name}"',
        shell=True
    )
    return f"Could not find '{name}' directly. Opened File Explorer search for it."

# ════════════════════════════════════════════
# 5. CLOSE APP
# ════════════════════════════════════════════
def tool_close_app(params):
    target = params.get('target', '').lower()
    killed = []
    for proc in psutil.process_iter(['name']):
        if target in proc.info['name'].lower():
            try:
                proc.kill()
                killed.append(proc.info['name'])
            except:
                pass
    return f"Closed: {', '.join(set(killed))}." if killed else f"No process found for '{target}'."

# ════════════════════════════════════════════
# 6. READ FILE — searches everywhere
# ════════════════════════════════════════════
def tool_read_file(params):
    raw_path = params.get('path', '')
    try:
        path, err = resolve_path(raw_path)
        if not os.path.exists(path):
            results = find_file_everywhere(raw_path)
            if not results:
                return f"Could not find '{raw_path}' anywhere on your PC."
            path = results[0]

        size = os.path.getsize(path)
        if size > 50000:
            return f"File too large to read ({size} bytes)."
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(2000)
        return f"Contents of {path}:\n{content}{'...(truncated)' if size > 2000 else ''}"
    except Exception as e:
        return f"Could not read file: {e}"

# ════════════════════════════════════════════
# 7. CREATE FILE — defaults to Desktop
# ════════════════════════════════════════════
def tool_create_file(params):
    raw_path = params.get('path', '')
    content  = params.get('content', '')
    try:
        path, _ = resolve_path(raw_path)
        dir_ = os.path.dirname(path)
        if dir_:
            os.makedirs(dir_, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File created at {path}."
    except Exception as e:
        return f"Could not create file: {e}"

# ════════════════════════════════════════════
# 8. EDIT / APPEND FILE — searches everywhere
# ════════════════════════════════════════════
def tool_edit_file(params):
    raw_path = params.get('path', '')
    content  = params.get('content', '')
    mode     = params.get('mode', 'overwrite')
    try:
        path, _ = resolve_path(raw_path)
        if not os.path.exists(path):
            results = find_file_everywhere(raw_path)
            if not results:
                return f"Could not find '{raw_path}' anywhere. Use create_file to make it first."
            path = results[0]

        write_mode = 'a' if mode == 'append' else 'w'
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(('\n' if mode == 'append' else '') + content)
        action = "Appended to" if mode == 'append' else "Overwrote"
        return f"{action} {path} successfully."
    except Exception as e:
        return f"Could not edit file: {e}"

# ════════════════════════════════════════════
# 9. SCREEN VISION
# ════════════════════════════════════════════
import requests as _requests
VISION_URL = "http://localhost:5005"

def tool_read_screen(params):
    question = params.get('question', 'What do you see on screen?')
    try:
        r = _requests.post(f"{VISION_URL}/read_screen", json={"question": question}, timeout=20)
        return r.json().get("result", "Could not read screen.")
    except Exception as e:
        return f"Vision service error: {e}"

def tool_click_icon(params):
    target = params.get('target', '')
    action = params.get('action', 'double_click')
    try:
        r = _requests.post(f"{VISION_URL}/click_icon", json={"target": target, "action": action}, timeout=20)
        return r.json().get("result", "Could not click icon.")
    except Exception as e:
        return f"Vision service error: {e}"

def tool_desktop_icons(params):
    try:
        r = _requests.get(f"{VISION_URL}/desktop_icons", timeout=15)
        return r.json().get("result", "Could not list icons.")
    except Exception as e:
        return f"Vision service error: {e}"

# ════════════════════════════════════════════
# 10. DELETE FILE — searches everywhere
# ════════════════════════════════════════════
def tool_delete_file(params):
    raw_path = params.get('path', '')
    try:
        path, _ = resolve_path(raw_path)

        if os.path.isfile(path):
            os.remove(path)
            return f"Deleted file: {path}"
        if os.path.isdir(path):
            shutil.rmtree(path)
            return f"Deleted folder: {path}"

        name    = os.path.basename(raw_path) or raw_path
        results = find_file_everywhere(name)
        if not results:
            return f"Could not find '{name}' anywhere on your PC."

        deleted = []
        for r in results:
            try:
                if os.path.isfile(r):
                    os.remove(r)
                elif os.path.isdir(r):
                    shutil.rmtree(r)
                deleted.append(r)
            except Exception:
                pass

        if deleted:
            return f"Found and deleted {len(deleted)} item(s):\n" + "\n".join(deleted)
        return f"Found '{name}' but could not delete it (permission denied?)."
    except Exception as e:
        return f"Could not delete: {e}"

# ════════════════════════════════════════════
# 11. LIST FILES
# ════════════════════════════════════════════
def tool_list_files(params):
    raw_path = params.get('path', '~\\Desktop')
    try:
        path = os.path.expandvars(os.path.expanduser(raw_path))
        if not os.path.exists(path):
            guesses = {
                'desktop':   os.path.expanduser('~\\Desktop'),
                'downloads': os.path.expanduser('~\\Downloads'),
                'documents': os.path.expanduser('~\\Documents'),
                'pictures':  os.path.expanduser('~\\Pictures'),
                'music':     os.path.expanduser('~\\Music'),
                'videos':    os.path.expanduser('~\\Videos'),
            }
            matched = guesses.get(raw_path.lower().strip())
            if matched:
                path = matched
            else:
                return f"Folder not found: {raw_path}"

        items   = os.listdir(path)
        files   = [i for i in items if os.path.isfile(os.path.join(path, i))]
        folders = [i for i in items if os.path.isdir(os.path.join(path, i))]
        return f"In {path}:\nFolders ({len(folders)}): {', '.join(folders[:15]) or 'none'}\nFiles ({len(files)}): {', '.join(files[:15]) or 'none'}"
    except Exception as e:
        return f"Could not list files: {e}"

# ════════════════════════════════════════════
# 12. FIND FILE — search by name
# ════════════════════════════════════════════
def tool_find_file(params):
    name = params.get('name', '')
    try:
        results = find_file_everywhere(name)
        if not results:
            return f"Could not find '{name}' anywhere on your PC."
        return f"Found '{name}' in {len(results)} location(s):\n" + "\n".join(results[:10])
    except Exception as e:
        return f"Search failed: {e}"

# ════════════════════════════════════════════
# 13. MOUSE CONTROL
# ════════════════════════════════════════════
def tool_mouse(params):
    action = params.get('action', '')
    try:
        if action == 'click':
            x, y = params.get('x'), params.get('y')
            if x and y:
                pyautogui.click(int(x), int(y))
                return f"Clicked at ({x}, {y})."
            pyautogui.click()
            return "Clicked."
        elif action == 'move':
            pyautogui.moveTo(int(params.get('x',500)), int(params.get('y',500)), duration=0.5)
            return "Moved mouse."
        elif action == 'scroll_up':
            pyautogui.scroll(int(params.get('amount', 3)))
            return "Scrolled up."
        elif action == 'scroll_down':
            pyautogui.scroll(-int(params.get('amount', 3)))
            return "Scrolled down."
        elif action == 'right_click':
            pyautogui.rightClick(); return "Right clicked."
        elif action == 'double_click':
            pyautogui.doubleClick(); return "Double clicked."
        elif action == 'position':
            x, y = pyautogui.position(); return f"Mouse at ({x}, {y})."
        return f"Unknown mouse action: {action}"
    except Exception as e:
        return f"Mouse failed: {e}"

# ════════════════════════════════════════════
# 14. KEYBOARD CONTROL
# ════════════════════════════════════════════
def tool_keyboard(params):
    action = params.get('action', '')
    try:
        if action == 'type':
            pyautogui.typewrite(params.get('text',''), interval=0.04)
            return f"Typed: {params.get('text','')}"
        elif action == 'hotkey':
            pyautogui.hotkey(*[k.strip() for k in params.get('keys','').split('+')])
            return f"Pressed: {params.get('keys','')}"
        elif action == 'press':
            pyautogui.press(params.get('key',''))
            return f"Pressed: {params.get('key','')}"
        elif action == 'screenshot':
            path = os.path.join(os.path.expanduser('~\\Desktop'), f'screenshot_{int(time.time())}.png')
            pyautogui.screenshot(path)
            return "Screenshot saved to Desktop."
        return f"Unknown keyboard action: {action}"
    except Exception as e:
        return f"Keyboard failed: {e}"

# ════════════════════════════════════════════
# 15. VOLUME
# ════════════════════════════════════════════
def tool_volume(params):
    action = params.get('action','')
    amount = int(params.get('amount', 5))
    try:
        if action == 'up':
            for _ in range(amount): pyautogui.press('volumeup')
            return f"Volume up by {amount}."
        elif action == 'down':
            for _ in range(amount): pyautogui.press('volumedown')
            return f"Volume down by {amount}."
        elif action == 'mute':
            pyautogui.press('volumemute'); return "Muted."
        return "Say volume up, down, or mute."
    except Exception as e:
        return f"Volume failed: {e}"

# ════════════════════════════════════════════
# 16. SYSTEM INFO
# ════════════════════════════════════════════
def tool_system_info(params):
    query = params.get('query','all').lower()
    try:
        info = {}
        if query in ('all','cpu'):
            info['CPU Usage'] = f"{psutil.cpu_percent(interval=1)}%"
            info['CPU Cores'] = psutil.cpu_count()
        if query in ('all','memory','ram'):
            mem = psutil.virtual_memory()
            info['RAM Total']     = f"{mem.total//(1024**3)} GB"
            info['RAM Used']      = f"{mem.used//(1024**3)} GB"
            info['RAM Available'] = f"{mem.available//(1024**3)} GB"
            info['RAM %']         = f"{mem.percent}%"
        if query in ('all','disk'):
            disk = psutil.disk_usage('C:\\')
            info['Disk Total'] = f"{disk.total//(1024**3)} GB"
            info['Disk Free']  = f"{disk.free//(1024**3)} GB"
        if query in ('all','system','os'):
            info['OS']       = platform.system()+' '+platform.release()
            info['Hostname'] = platform.node()
        if query in ('all','battery'):
            b = psutil.sensors_battery()
            if b: info['Battery'] = f"{b.percent}% {'(charging)' if b.power_plugged else ''}"
        return "\n".join(f"{k}: {v}" for k,v in info.items()) or "No info."
    except Exception as e:
        return f"System info failed: {e}"

# ════════════════════════════════════════════
# 17. WINDOW CONTROL
# ════════════════════════════════════════════
def tool_window(params):
    action = params.get('action','')
    target = params.get('target','').lower()
    try:
        if action == 'list':
            wins = [w.title for w in gw.getAllWindows() if w.title.strip()]
            return f"Open windows: {', '.join(wins[:15])}"
        wins = [w for w in gw.getAllWindows() if target in w.title.lower()]
        if not wins: return f"No window matching '{target}'."
        if action == 'focus':    wins[0].activate();  return f"Focused: {wins[0].title}"
        if action == 'minimize': wins[0].minimize();  return f"Minimized: {wins[0].title}"
        if action == 'maximize': wins[0].maximize();  return f"Maximized: {wins[0].title}"
        return f"Unknown window action: {action}"
    except Exception as e:
        return f"Window control failed: {e}"

# ════════════════════════════════════════════
# 18. GET TIME / DATE
# ════════════════════════════════════════════
def tool_get_time(params):
    now = datetime.now()
    return f"The current time is {now.strftime('%I:%M %p')} and today is {now.strftime('%A, %d %B %Y')}."

# ════════════════════════════════════════════
# 19. GENERAL FALLBACK
# ════════════════════════════════════════════
def tool_general(params):
    return params.get('response', "I'm AURA. How can I help?")

# ════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════
TOOLS = {
    'web_search':    tool_web_search,
    'calendar':      tool_calendar,
    'email':         tool_email,
    'open_app':      tool_open_app,
    'open_folder':   tool_open_folder,   # ← NEW
    'search_folder': tool_open_folder,   # ← NEW (alias)
    'close_app':     tool_close_app,
    'read_file':     tool_read_file,
    'create_file':   tool_create_file,
    'edit_file':     tool_edit_file,
    'get_time':      tool_get_time,
    'delete_file':   tool_delete_file,
    'list_files':    tool_list_files,
    'find_file':     tool_find_file,
    'mouse':         tool_mouse,
    'keyboard':      tool_keyboard,
    'volume':        tool_volume,
    'system_info':   tool_system_info,
    'window':        tool_window,
    'general':       tool_general,
    'read_screen':   tool_read_screen,
    'click_icon':    tool_click_icon,
    'desktop_icons': tool_desktop_icons,
}

@app.route('/execute', methods=['POST'])
def execute():
    data   = request.get_json()
    tool   = data.get('tool', 'general')
    params = data.get('params', {})
    print(f"[TOOL] Running: {tool} with {params}")
    fn     = TOOLS.get(tool, tool_general)
    result = fn(params)
    print(f"[TOOL] Result: {str(result)[:120]}")
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(port=5003, debug=False)
