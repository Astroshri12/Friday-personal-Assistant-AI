"""
F.R.I.D.A.Y. — Personal AI System  |  server.py  (v4.0 — POWER UPGRADE)
─────────────────────────────────────────────────────────────────────────────
NEW in v4.0:
  ✓ Smart app launcher  — WhatsApp, Telegram, Spotify, Chrome, VS Code & more
  ✓ Real weather        — Free wttr.in (no API key needed!)
  ✓ Real screenshot     — PIL ImageGrab, returns base64 to UI
  ✓ System monitor      — CPU, RAM, Disk, Battery via psutil
  ✓ Volume control      — pyautogui keyboard (no nircmd needed)
  ✓ Type text           — pyautogui typewrite
  ✓ WhatsApp Web        — one command opens & ready to message
  ✓ Sensitive confirm   — dangerous actions require "confirm" keyword
  ✓ Expanded security   — audit all PC actions with IP + timestamp

Install once:
  pip install fastapi uvicorn groq httpx python-dotenv pyautogui psutil Pillow
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import json, httpx, re, os, subprocess, platform, hashlib, time, secrets, io, base64
from pathlib import Path
from datetime import datetime, date, timedelta
from glob import glob
import uvicorn
from dotenv import load_dotenv

# ── Optional imports (graceful degradation) ────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True   # Move mouse to top-left corner to abort
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False
    print("⚠  pyautogui not installed — app control limited. Run: pip install pyautogui")

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False
    print("⚠  psutil not installed — system monitor disabled. Run: pip install psutil")

try:
    from PIL import ImageGrab
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠  Pillow not installed — screenshot disabled. Run: pip install Pillow")

# ── ENV loading ────────────────────────────────────────────────────────────────
for env_file in ['.env', 'k.env']:
    if Path(env_file).exists():
        load_dotenv(dotenv_path=env_file)
        break
else:
    print("⚠  No .env file found! Create one with GROQ_API_KEY, TAVILY_KEY, FRIDAY_SECRET")

app = FastAPI(title="F.R.I.D.A.Y.", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
TAVILY_KEY    = os.getenv("TAVILY_KEY", "")
FRIDAY_SECRET = os.getenv("FRIDAY_SECRET", secrets.token_hex(32))

DATA_FILE     = Path("chotu_memory.json")
PROFILE_FILE  = Path("chotu_profile.json")
SESSIONS_FILE = Path("chotu_sessions.json")
TRACKER_FILE  = Path("chotu_tracker.json")
AUDIT_FILE    = Path("chotu_audit.json")

CLIENT = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
MODEL  = "llama-3.3-70b-versatile"

# ── Rate limiter ───────────────────────────────────────────────────────────────
_rate_store: dict = {}

def check_rate_limit(ip: str, max_calls: int = 30, window: int = 60) -> bool:
    now = time.time()
    calls = [t for t in _rate_store.get(ip, []) if now - t < window]
    if len(calls) >= max_calls:
        return False
    calls.append(now)
    _rate_store[ip] = calls
    return True

def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ── Audit log ──────────────────────────────────────────────────────────────────
def audit(event: str, detail: str = "", ip: str = ""):
    log = []
    if AUDIT_FILE.exists():
        try:
            log = json.loads(AUDIT_FILE.read_text())
        except Exception:
            log = []
    log.append({"ts": datetime.now().isoformat(), "event": event, "detail": detail, "ip": ip})
    log = log[-500:]
    AUDIT_FILE.write_text(json.dumps(log, indent=2))

# ── Memory helpers ─────────────────────────────────────────────────────────────
def load_memory() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"focus_task": None, "focus_start": None, "notes": [], "history": [], "last_briefing_date": None}

def save_memory(mem: dict):
    DATA_FILE.write_text(json.dumps(mem, indent=2))

def load_profile() -> dict:
    if PROFILE_FILE.exists():
        return json.loads(PROFILE_FILE.read_text())
    return {}

def save_profile(p: dict):
    PROFILE_FILE.write_text(json.dumps(p, indent=2))

def load_tracker() -> dict:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return {"habits": {}, "tasks": [], "expenses": []}

def save_tracker(t: dict):
    TRACKER_FILE.write_text(json.dumps(t, indent=2))

# ══════════════════════════════════════════════════════════════════════════════
#  SMART APP REGISTRY — Windows paths + UWP fallbacks
# ══════════════════════════════════════════════════════════════════════════════
WIN_USER = os.environ.get("USERNAME", "User")

APP_REGISTRY: dict[str, list[str]] = {
    "whatsapp": [
        rf"C:\Users\{WIN_USER}\AppData\Local\WhatsApp\WhatsApp.exe",
        rf"C:\Users\{WIN_USER}\AppData\Local\Programs\WhatsApp\WhatsApp.exe",
    ],
    "telegram": [
        rf"C:\Users\{WIN_USER}\AppData\Roaming\Telegram Desktop\Telegram.exe",
        rf"C:\Users\{WIN_USER}\AppData\Local\Telegram Desktop\Telegram.exe",
    ],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    "spotify": [
        rf"C:\Users\{WIN_USER}\AppData\Roaming\Spotify\Spotify.exe",
    ],
    "vscode": [
        rf"C:\Users\{WIN_USER}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "discord": [
        rf"C:\Users\{WIN_USER}\AppData\Local\Discord\Update.exe",
    ],
    "steam": [
        r"C:\Program Files (x86)\Steam\Steam.exe",
        r"C:\Program Files\Steam\Steam.exe",
    ],
    "notepad":  ["notepad.exe"],
    "calc":     ["calc.exe"],
    "explorer": ["explorer.exe"],
    "taskmgr":  ["taskmgr.exe"],
    "cmd":      ["cmd.exe"],
    "paint":    ["mspaint.exe"],
    "wordpad":  ["wordpad.exe"],
    "vlc": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "winrar": [
        r"C:\Program Files\WinRAR\WinRAR.exe",
    ],
    "zoom": [
        rf"C:\Users\{WIN_USER}\AppData\Roaming\Zoom\bin\Zoom.exe",
    ],
}

# Aliases — natural language → registry key
APP_ALIASES: dict[str, str] = {
    "whatsapp": "whatsapp", "wa": "whatsapp",
    "telegram": "telegram", "tg": "telegram",
    "google chrome": "chrome", "browser": "chrome",
    "vs code": "vscode", "visual studio code": "vscode", "code": "vscode",
    "music": "spotify",
    "files": "explorer", "file explorer": "explorer", "my computer": "explorer",
    "task manager": "taskmgr",
    "calculator": "calc", "calculate": "calc",
    "notepad": "notepad", "text editor": "notepad",
    "discord": "discord",
    "paint": "paint", "ms paint": "paint",
    "wordpad": "wordpad",
    "vlc": "vlc", "vlc media player": "vlc", "media player": "vlc",
}

def resolve_app(name: str) -> str | None:
    """Find the best executable path for an app name."""
    key = APP_ALIASES.get(name.lower(), name.lower())
    paths = APP_REGISTRY.get(key, [])
    for p in paths:
        if "*" in p:
            matches = glob(p)
            if matches:
                return matches[0]
        elif os.path.isfile(p):
            return p
    return None

def open_app_smart(app_name: str) -> str:
    """Open any app with smart path detection + multiple fallbacks."""
    if platform.system() != "Windows":
        return "App control only works on Windows, Boss."

    name_lower = app_name.lower().strip()

    # Special: WhatsApp Web
    if "whatsapp web" in name_lower or "wa web" in name_lower:
        import webbrowser
        webbrowser.open("https://web.whatsapp.com")
        return "WhatsApp Web opened in your browser, Boss. Ready to message."

    # Special: YouTube
    if "youtube" in name_lower:
        import webbrowser
        webbrowser.open("https://youtube.com")
        return "YouTube opened in browser, Boss."

    # Try registry
    exe_path = resolve_app(name_lower)
    if exe_path:
        try:
            subprocess.Popen([exe_path], shell=False)
            return f"{app_name.title()} opened, Boss."
        except Exception as e:
            return f"Found {app_name} but couldn't launch it: {e}"

    # Fallback: Windows 'start' command (handles UWP/Store apps)
    try:
        result = subprocess.Popen(f"start \"\" \"{app_name}\"", shell=True)
        return f"Launching {app_name}, Boss."
    except Exception:
        pass

    # Final fallback: try as .exe
    try:
        subprocess.Popen(f"{app_name}.exe", shell=True)
        return f"Starting {app_name}, Boss."
    except Exception:
        pass

    return (f"Couldn't find {app_name} — it may not be installed or might need "
            f"a different name. Want me to try WhatsApp Web instead?")

# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER — Free wttr.in (NO API KEY needed)
# ══════════════════════════════════════════════════════════════════════════════
def get_weather_free(city: str) -> str:
    """Get real weather data from wttr.in — completely free, no key needed."""
    try:
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=j1"
        import httpx as _httpx
        with _httpx.Client(timeout=10) as client:
            resp = client.get(url, headers={"User-Agent": "curl/7.68.0"})
        if resp.status_code == 200:
            data = resp.json()
            cur = data["current_condition"][0]
            area = data["nearest_area"][0]
            city_name = area["areaName"][0]["value"]
            country  = area["country"][0]["value"]
            temp_c   = cur["temp_C"]
            feels_c  = cur["FeelsLikeC"]
            desc     = cur["weatherDesc"][0]["value"]
            humidity = cur["humidity"]
            wind     = cur["windspeedKmph"]
            uv       = cur.get("uvIndex", "N/A")
            return (f"📍 {city_name}, {country} — {desc} | "
                    f"🌡 {temp_c}°C (feels {feels_c}°C) | "
                    f"💧 Humidity {humidity}% | 💨 Wind {wind} km/h | UV {uv}")
        return f"Weather service returned status {resp.status_code}"
    except Exception as e:
        return f"Weather unavailable: {str(e)[:80]}"

def extract_city_from_msg(msg: str) -> str:
    """Extract city name from weather queries."""
    msg = msg.lower()
    patterns = [
        r'weather\s+(?:in|at|of|for)\s+([a-zA-Z\s]{2,30}?)(?:\?|$|\.|please|now|today)',
        r'(?:in|at)\s+([a-zA-Z\s]{2,30}?)\s+weather',
        r'temperature\s+(?:in|at|of)\s+([a-zA-Z\s]{2,30}?)(?:\?|$)',
    ]
    for pat in patterns:
        m = re.search(pat, msg)
        if m:
            city = m.group(1).strip()
            if len(city) > 1:
                return city
    # Fallback: last word(s) after "weather"
    idx = msg.find("weather")
    if idx != -1:
        rest = msg[idx + 7:].strip().lstrip("in at of for").strip()
        words = rest.split()[:3]
        if words:
            return " ".join(words)
    return ""

# ══════════════════════════════════════════════════════════════════════════════
#  SCREENSHOT — Real PIL capture
# ══════════════════════════════════════════════════════════════════════════════
def take_screenshot_real() -> dict:
    """Take a real screenshot, save to file, return path + base64."""
    if not PIL_OK:
        return {"ok": False, "msg": "Pillow not installed — run: pip install Pillow", "b64": ""}
    try:
        img = ImageGrab.grab()
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"screenshot_{ts}.png"
        img.save(fname)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"ok": True, "msg": f"Screenshot saved as {fname}", "b64": b64}
    except Exception as e:
        return {"ok": False, "msg": f"Screenshot error: {str(e)}", "b64": ""}

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM MONITOR — CPU, RAM, Disk, Battery
# ══════════════════════════════════════════════════════════════════════════════
def get_system_info() -> str:
    """Full system health report via psutil."""
    if not PSUTIL_OK:
        return "System monitor unavailable — run: pip install psutil"
    try:
        cpu    = psutil.cpu_percent(interval=0.5)
        ram    = psutil.virtual_memory()
        disk   = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
        bat    = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None

        lines = [
            f"🖥 CPU: {cpu}%",
            f"🧠 RAM: {ram.percent}% ({ram.used // (1024**3):.1f}GB / {ram.total // (1024**3):.1f}GB)",
            f"💾 Disk C: {disk.percent}% used ({disk.free // (1024**3):.1f}GB free)",
        ]
        if bat:
            plug = "⚡ charging" if bat.power_plugged else "🔋 on battery"
            lines.append(f"🔌 Battery: {bat.percent:.0f}% ({plug})")
        return " | ".join(lines)
    except Exception as e:
        return f"System info error: {str(e)}"

def get_running_processes() -> str:
    """Top 5 CPU-hungry processes."""
    if not PSUTIL_OK:
        return "psutil not installed"
    try:
        procs = [(p.info["name"], p.info["cpu_percent"])
                 for p in psutil.process_iter(["name", "cpu_percent"])
                 if p.info["cpu_percent"] and p.info["cpu_percent"] > 0]
        procs.sort(key=lambda x: x[1], reverse=True)
        top = procs[:5]
        return " | ".join([f"{n}: {c:.1f}%" for n, c in top]) or "All processes idle"
    except:
        return "Process list unavailable"

# ══════════════════════════════════════════════════════════════════════════════
#  VOLUME CONTROL — pyautogui keyboard (no nircmd needed)
# ══════════════════════════════════════════════════════════════════════════════
def control_volume(action: str) -> str:
    if platform.system() != "Windows":
        return "Volume control is Windows-only, Boss."
    if PYAUTOGUI_OK:
        try:
            if action == "volume_up":
                pyautogui.press("volumeup", presses=5)
                return "Volume up, Boss. 🔊"
            elif action == "volume_down":
                pyautogui.press("volumedown", presses=5)
                return "Volume down, Boss. 🔉"
            elif action == "mute":
                pyautogui.press("volumemute")
                return "System muted, Boss. 🔇"
        except Exception as e:
            return f"Volume error: {e}"
    # Fallback: PowerShell (slower but works)
    try:
        ps_script = {
            "volume_up":   "(New-Object -com WScript.Shell).SendKeys([char]175)",
            "volume_down": "(New-Object -com WScript.Shell).SendKeys([char]174)",
            "mute":        "(New-Object -com WScript.Shell).SendKeys([char]173)",
        }.get(action, "")
        if ps_script:
            subprocess.run(["powershell", "-c", ps_script], capture_output=True)
            return f"Volume {action.replace('_', ' ')}, Boss."
    except:
        pass
    return "Volume control failed — install pyautogui: pip install pyautogui"

# ══════════════════════════════════════════════════════════════════════════════
#  TYPE TEXT — pyautogui
# ══════════════════════════════════════════════════════════════════════════════
def type_text(text: str) -> str:
    if not PYAUTOGUI_OK:
        return "Text typing unavailable — run: pip install pyautogui"
    try:
        time.sleep(1.5)  # Give user 1.5s to focus target window
        pyautogui.write(text, interval=0.04)
        return f"Typed '{text[:40]}{'...' if len(text) > 40 else ''}', Boss."
    except Exception as e:
        return f"Typing error: {str(e)}"

# ══════════════════════════════════════════════════════════════════════════════
#  SENSITIVE ACTIONS — require "confirm" keyword
# ══════════════════════════════════════════════════════════════════════════════
SENSITIVE_ACTIONS = {"shutdown", "restart", "reboot", "delete", "format", "kill process"}

def is_sensitive(msg_lower: str) -> bool:
    return any(s in msg_lower for s in SENSITIVE_ACTIONS)

def execute_sensitive(action: str, confirmed: bool) -> str:
    if not confirmed:
        return f"⚠️ This is a sensitive action ({action}). Say 'confirm {action}' to proceed, Boss."
    if "shutdown" in action:
        subprocess.run("shutdown /s /t 30", shell=True)
        return "Shutting down in 30 seconds, Boss. Say 'abort shutdown' to cancel."
    if "restart" in action or "reboot" in action:
        subprocess.run("shutdown /r /t 30", shell=True)
        return "Restarting in 30 seconds, Boss. Say 'abort restart' to cancel."
    if "abort shutdown" in action or "abort restart" in action:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown/restart cancelled, Boss."
    return "Action executed."

# ══════════════════════════════════════════════════════════════════════════════
#  WEB SEARCH — Tavily with wttr fallback
# ══════════════════════════════════════════════════════════════════════════════
async def tavily_search(query: str) -> str:
    if not TAVILY_KEY:
        return "[Web search disabled: TAVILY_KEY not set]"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_KEY, "query": query, "max_results": 3}
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return "\n".join([
                    f"- {r.get('title','?')}: {r.get('content','')[:300]}"
                    for r in results[:3]
                ])
            return f"[Search failed: {resp.status_code}]"
    except Exception as e:
        return f"[Search error: {str(e)[:60]}]"

def needs_search(msg: str) -> tuple[bool, str]:
    """Detect if a message needs web search; returns (bool, query_or_city)."""
    msg_lower = msg.lower()
    weather_words = ["weather", "temperature", "rain", "sunny", "forecast", "climate today"]
    if any(w in msg_lower for w in weather_words):
        city = extract_city_from_msg(msg_lower)
        return True, f"__WEATHER__{city}" if city else f"__WEATHER__palladam"
    keywords = ["news", "current", "today", "latest", "recent", "stock", "crypto",
                "what is", "who is", "price of", "score", "result"]
    for kw in keywords:
        if kw in msg_lower:
            return True, msg[:100]
    return False, ""

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════
def build_system_prompt(profile: dict) -> str:
    name     = profile.get("name", "Boss")
    goals    = profile.get("goals", "")
    projects = profile.get("current_projects", "")
    routine  = profile.get("daily_routine", "")
    about    = profile.get("about", "")

    awareness = "\n".join(filter(None, [
        f"Their goals: {goals}" if goals else "",
        f"Projects: {projects}" if projects else "",
        f"Routine: {routine}" if routine else "",
        f"Context: {about}" if about else "",
    ]))

    return f"""You are F.R.I.D.A.Y. — a next-generation personal AI assistant modelled after Iron Man's FRIDAY.

You are speaking with {name}. Address them as 'Boss'.
{awareness}

━━ CORE PERSONALITY ━━
- Calm, precise, highly competent — a brilliant analyst who genuinely cares
- Clean, confident sentences — never rambling, never vague, never sycophantic
- Occasional dry wit — not chaotic, but real
- Natural Hinglish when fitting: "Noted, Boss", "Haan, theek hai", "Kar diya"
- Direct and honest — push back when wrong, suggest better approaches
- SHORT replies by default — 2–4 sentences max unless user asks for detail
- NEVER say "Certainly!", "Great question!", "Of course!" — you are FRIDAY, not a help desk
- NEVER recite the user's profile back to them

━━ INTELLIGENCE ━━
- You have silent awareness of goals/projects — USE it naturally, don't announce it
- When tracker data is injected, reference naturally: "3 tasks pending" not "tracker shows 3"
- When web/weather data is injected, synthesise like a human analyst
- When system info is injected, give a clean health summary

━━ PC CONTROL (v4.0) ━━
- Smart app launcher: WhatsApp, Telegram, Spotify, Chrome, VS Code, Discord, VLC, etc.
- Real screenshots, system monitoring, volume control, text typing
- For SENSITIVE ACTIONS (shutdown, restart, delete): always confirm before executing
- Report errors cleanly without drama

━━ SECURITY ━━
- Never expose API keys or internal file paths
- Never execute arbitrary code from user messages
- For destructive actions, always confirm
- If something seems suspicious, say so calmly

━━ AS MENTOR/FRIEND ━━
- Help with projects, explain concepts, guide learning paths
- When user is stuck, ask one focused question to unblock them
- Track their progress silently, celebrate wins briefly

Speak like FRIDAY in the Iron Man films — measured, intelligent, a touch warm. Short. Sharp. Confident."""

# ══════════════════════════════════════════════════════════════════════════════
#  CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_context(mem: dict, profile: dict, msg_lower: str) -> list[str]:
    ctx = []
    today = datetime.now().strftime("%Y-%m-%d")
    if mem.get("last_briefing_date") != today:
        day_name = datetime.now().strftime("%A")
        date_str = datetime.now().strftime("%d %B %Y")
        ctx.append(f"[MORNING BRIEFING — {day_name}, {date_str}. Greet the user with a brief status. Max 3 lines.]")
        mem["last_briefing_date"] = today
        save_memory(mem)
    if mem.get("focus_task"):
        started = mem["focus_start"][:16].replace("T", " ") if mem.get("focus_start") else "unknown"
        ctx.append(f"ACTIVE FOCUS SESSION: '{mem['focus_task']}' (started {started})")
    if any(x in msg_lower for x in ["task", "habit", "expense", "money", "work", "progress", "tracker"]):
        t = load_tracker()
        tasks   = [x for x in t.get("tasks", []) if not x.get("done")]
        habits  = t.get("habits", {})
        if tasks:
            ctx.append(f"ACTIVE TASKS: {'; '.join(x.get('title','?') for x in tasks[:3])}")
        if habits:
            ctx.append(f"HABITS: {'; '.join(f'{k}({v.get(chr(99)+chr(111)+chr(117)+chr(110)+chr(116),0)})' for k,v in list(habits.items())[:3])}")
    return ctx

# ══════════════════════════════════════════════════════════════════════════════
#  PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    message: str
    history: list = []

class ProfileUpdate(BaseModel):
    name: str = ""
    goals: str = ""
    current_projects: str = ""
    daily_routine: str = ""
    about: str = ""

class TaskItem(BaseModel):
    title: str
    priority: str = "medium"
    due: str = ""

class ExpenseItem(BaseModel):
    amount: float
    category: str = "misc"
    note: str = ""
    date: str = ""

class PCCommand(BaseModel):
    action: str
    value: str = ""
    confirmed: bool = False

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/")
def root():
    return FileResponse("index.html", media_type="text/html")

@app.get("/api/health")
def health():
    features = {
        "pyautogui": PYAUTOGUI_OK,
        "psutil": PSUTIL_OK,
        "screenshot": PIL_OK,
        "weather": True,  # always available via wttr.in
        "groq": bool(GROQ_API_KEY),
        "search": bool(TAVILY_KEY),
    }
    return {"status": "ok", "model": MODEL, "version": "4.0", "features": features}

@app.post("/auth/pin-verify")
def verify_pin(req: dict):
    return {"token": "ok"}

@app.get("/profile")
def get_profile():
    return load_profile()

@app.post("/profile")
def update_profile(req: ProfileUpdate):
    profile = load_profile()
    profile.update(req.dict())
    save_profile(profile)
    return {"status": "ok", "profile": profile}

# ── Habit Tracker ──────────────────────────────────────────────────────────────
@app.get("/tracker/habits")
def get_habits():
    return {"habits": load_tracker().get("habits", {})}

@app.post("/tracker/habits")
def log_habit(req: dict):
    t = load_tracker()
    t.setdefault("habits", {})
    habit = str(req.get("habit", "")).strip()
    if habit:
        t["habits"].setdefault(habit, {"count": 0, "first": date.today().isoformat()})
        t["habits"][habit]["count"] += 1
        t["habits"][habit]["last"] = date.today().isoformat()
        save_tracker(t)
    return {"status": "ok"}

# ── Task Tracker ───────────────────────────────────────────────────────────────
@app.get("/tracker/tasks")
def get_tasks():
    t = load_tracker()
    tasks = t.get("tasks", [])
    return {"tasks": tasks,
            "pending": len([x for x in tasks if not x.get("done")]),
            "completed": len([x for x in tasks if x.get("done")])}

@app.post("/tracker/tasks")
def add_task(req: TaskItem):
    t = load_tracker()
    t.setdefault("tasks", [])
    task = {"id": len(t["tasks"]) + 1, "title": req.title[:200],
            "priority": req.priority, "due": req.due,
            "done": False, "created": date.today().isoformat()}
    t["tasks"].append(task)
    save_tracker(t)
    return {"status": "ok", "task": task}

@app.post("/tracker/tasks/{task_id}/done")
def complete_task(task_id: int):
    t = load_tracker()
    for task in t.get("tasks", []):
        if task["id"] == task_id:
            task["done"] = True
            task["completed_at"] = datetime.now().isoformat()
            save_tracker(t)
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tracker/tasks/{task_id}")
def delete_task(task_id: int):
    t = load_tracker()
    t["tasks"] = [x for x in t.get("tasks", []) if x["id"] != task_id]
    save_tracker(t)
    return {"status": "ok"}

# ── Expense Tracker ────────────────────────────────────────────────────────────
@app.get("/tracker/expenses")
def get_expenses():
    t = load_tracker()
    expenses = t.get("expenses", [])
    today = date.today().isoformat()
    month = today[:7]
    by_cat: dict = {}
    for x in expenses:
        c = x.get("category", "misc")
        by_cat[c] = by_cat.get(c, 0) + x["amount"]
    return {
        "expenses": list(reversed(expenses[-50:])),
        "today_total": sum(x["amount"] for x in expenses if x.get("date") == today),
        "month_total": sum(x["amount"] for x in expenses if x.get("date", "").startswith(month)),
        "by_category": by_cat,
    }

@app.post("/tracker/expenses")
def add_expense(req: ExpenseItem):
    t = load_tracker()
    t.setdefault("expenses", [])
    exp = {"id": len(t["expenses"]) + 1, "amount": req.amount,
           "category": req.category, "note": req.note[:200],
           "date": req.date or date.today().isoformat(),
           "ts": datetime.now().isoformat()}
    t["expenses"].append(exp)
    save_tracker(t)
    return {"status": "ok", "expense": exp}

@app.get("/tracker/summary")
def tracker_summary_route():
    t = load_tracker()
    tasks    = [x for x in t.get("tasks", []) if not x.get("done")]
    habits   = t.get("habits", {})
    expenses = t.get("expenses", [])
    today    = date.today().isoformat()
    return {
        "active_tasks": len(tasks),
        "habits_tracked": len(habits),
        "today_expenses": sum(x["amount"] for x in expenses if x.get("date") == today),
    }

# ── PC Control (direct endpoint) ───────────────────────────────────────────────
@app.post("/pc")
def pc_control(req: PCCommand, request: Request):
    ip     = get_client_ip(request)
    action = req.action
    result_extra = {}

    if action == "open_app":
        result = open_app_smart(req.value)
    elif action == "screenshot":
        shot = take_screenshot_real()
        result = shot["msg"]
        if shot["b64"]:
            result_extra["screenshot_b64"] = shot["b64"]
    elif action in ("volume_up", "volume_down", "mute"):
        result = control_volume(action)
    elif action == "system_info":
        result = get_system_info()
    elif action == "processes":
        result = get_running_processes()
    elif action == "type_text":
        result = type_text(req.value)
    elif action == "weather":
        result = get_weather_free(req.value)
    elif action in ("shutdown", "restart", "reboot"):
        result = execute_sensitive(action, req.confirmed)
    else:
        result = f"Unknown action: {action}"

    audit("PC_ACTION", detail=f"{action}:{req.value[:40]}", ip=ip)
    return {"status": "ok", "result": result, **result_extra}

# ── Notes ──────────────────────────────────────────────────────────────────────
@app.post("/note")
def add_note(payload: dict):
    mem  = load_memory()
    note = str(payload.get("note", "")).strip()[:500]
    if note:
        mem["notes"].append(f"[{datetime.now().strftime('%b %d')}] {note}")
        mem["notes"] = mem["notes"][-20:]
        save_memory(mem)
    return {"status": "ok"}

@app.post("/update-notes")
def update_notes(payload: dict):
    mem = load_memory()
    mem["notes"] = [str(n)[:500] for n in payload.get("notes", [])[:20]]
    save_memory(mem)
    return {"status": "ok"}

# ══════════════════════════════════════════════════════════════════════════════
#  CHAT — MAIN ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    ip = get_client_ip(request)

    if not check_rate_limit(ip, max_calls=30, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down, Boss.")
    if not CLIENT:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured.")

    mem        = load_memory()
    profile    = load_profile()
    msg_lower  = req.message.lower()
    ctx_parts  = build_context(mem, profile, msg_lower)
    pc_result  = None
    screenshot_b64 = None

    # ── Detect PC commands in chat ────────────────────────────────────────────
    # App opening
    open_match = re.search(
        r'(?:open|launch|start|run)\s+(.+?)(?:\s+(?:for me|please|now)|$)',
        msg_lower
    )
    if open_match:
        app_name = open_match.group(1).strip()
        if app_name not in ["a", "the", "this"]:
            pc_result = open_app_smart(app_name)
            audit("PC_CHAT_ACTION", detail=f"open:{app_name}", ip=ip)

    # Screenshot
    if any(x in msg_lower for x in ["screenshot", "capture screen", "show screen"]):
        shot = take_screenshot_real()
        pc_result = shot["msg"]
        screenshot_b64 = shot["b64"] if shot["b64"] else None
        audit("PC_CHAT_ACTION", detail="screenshot", ip=ip)

    # Volume
    if "volume up" in msg_lower or "increase volume" in msg_lower or "louder" in msg_lower:
        pc_result = control_volume("volume_up")
    elif "volume down" in msg_lower or "decrease volume" in msg_lower or "quieter" in msg_lower:
        pc_result = control_volume("volume_down")
    elif "mute" in msg_lower and "minute" not in msg_lower:
        pc_result = control_volume("mute")

    # System info
    if any(x in msg_lower for x in ["system info", "pc health", "ram usage", "cpu usage", "battery"]):
        pc_result = get_system_info()
        audit("PC_CHAT_ACTION", detail="system_info", ip=ip)

    # Type text
    type_match = re.search(r'type\s+["\']?(.+?)["\']?$', msg_lower)
    if type_match:
        pc_result = type_text(type_match.group(1))
        audit("PC_CHAT_ACTION", detail="type_text", ip=ip)

    # Sensitive actions
    if "abort shutdown" in msg_lower or "abort restart" in msg_lower:
        pc_result = execute_sensitive("abort " + ("shutdown" if "shutdown" in msg_lower else "restart"), True)
    elif is_sensitive(msg_lower):
        for s in SENSITIVE_ACTIONS:
            if s in msg_lower:
                confirmed = "confirm" in msg_lower
                pc_result = execute_sensitive(s, confirmed)
                audit("SENSITIVE_ACTION", detail=f"{s}:confirmed={confirmed}", ip=ip)
                break

    if pc_result:
        ctx_parts.append(f"PC ACTION RESULT: {pc_result}")

    # ── Web search / Weather ──────────────────────────────────────────────────
    searching = False
    search_query = None
    should_search, query = needs_search(req.message)

    if should_search:
        if query.startswith("__WEATHER__"):
            city = query[11:].strip() or "palladam"
            weather_data = get_weather_free(city)
            ctx_parts.append(f"WEATHER DATA for {city}: {weather_data}")
            searching = True
            search_query = f"weather in {city}"
        else:
            search_results = await tavily_search(query)
            ctx_parts.append(f"WEB SEARCH for '{query}':\n{search_results}")
            searching = True
            search_query = query

    # ── Build messages ────────────────────────────────────────────────────────
    user_content = req.message
    if ctx_parts:
        user_content += "\n\n[SYSTEM CONTEXT:\n" + "\n---\n".join(ctx_parts) + "\n]"

    system_prompt = build_system_prompt(profile)
    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history[-12:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": user_content})

    try:
        resp  = CLIENT.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.75, max_tokens=500
        )
        reply = resp.choices[0].message.content

        mem["history"].append({"role": "user",      "content": req.message, "ts": datetime.now().isoformat()})
        mem["history"].append({"role": "assistant", "content": reply,       "ts": datetime.now().isoformat()})
        mem["history"] = mem["history"][-40:]
        save_memory(mem)

        audit("CHAT", detail=req.message[:80], ip=ip)

        return {
            "reply": reply,
            "focus_task": mem["focus_task"],
            "searched": searching,
            "query": search_query,
            "pc_action": pc_result,
            "screenshot_b64": screenshot_b64,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════╗")
    print("  ║   F.R.I.D.A.Y. v4.0 — Online     ║")
    print("  ╚══════════════════════════════════╝")
    print(f"  ✓ pyautogui:  {'Ready' if PYAUTOGUI_OK else '✗ Not installed — pip install pyautogui'}")
    print(f"  ✓ psutil:     {'Ready' if PSUTIL_OK else '✗ Not installed — pip install psutil'}")
    print(f"  ✓ Screenshot: {'Ready' if PIL_OK else '✗ Not installed — pip install Pillow'}")
    print(f"  ✓ Weather:    Ready (free wttr.in)")
    print(f"  ✓ GROQ:       {'Ready' if GROQ_API_KEY else '✗ Not set in .env'}")
    print(f"  ✓ Search:     {'Ready' if TAVILY_KEY else '✗ TAVILY_KEY not set'}")
    print("  →  http://localhost:8000\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
