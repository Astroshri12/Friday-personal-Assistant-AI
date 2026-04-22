# F.R.I.D.A.Y. — Personal AI System

> *"A next-generation personal AI assistant modelled after Iron Man's F.R.I.D.A.Y."*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LLM](https://img.shields.io/badge/LLM-Llama%203.3%2070B%20(Groq)-orange)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows)](https://www.microsoft.com/windows)

F.R.I.D.A.Y. is a locally-hosted, AI-powered personal assistant that runs entirely on your machine. Chat with it in natural language, control your PC, track tasks and habits, get real-time weather, search the web — all through a clean browser UI, powered by Llama 3.3 70B via Groq.

No cloud subscriptions. No telemetry. Your data stays on your disk.

---

## Screenshots

> *Boot screen → PIN lock → Chat interface with PC control panel*

*(Add your own screenshots here once running)*

---

## Features

### 🤖 AI Chat
- Powered by **Llama 3.3 70B** via [Groq](https://groq.com) (free tier available)
- Remembers context across messages with a rolling conversation history
- Personalized to your profile — name, goals, projects, daily routine
- Daily morning briefing on first message of the day
- Iron Man–style FRIDAY personality: calm, sharp, occasional Hinglish

### 🖥️ PC Control
| Command | What it does |
|---|---|
| `open spotify` | Launches Spotify (smart path detection) |
| `open whatsapp` | Opens WhatsApp desktop app |
| `open whatsapp web` | Opens WhatsApp Web in browser |
| `open youtube` | Opens YouTube in browser |
| `take a screenshot` | Captures screen, saves PNG, shows in chat |
| `volume up / down / mute` | Controls system volume |
| `tell me about battery` | CPU, RAM, disk, battery status |
| `type "hello world"` | Types text into the focused window |
| `restart now` | Restarts PC (requires "confirm" keyword) |
| `shutdown` | Shuts down PC (requires "confirm" keyword) |

Supported apps out of the box: WhatsApp, Telegram, Spotify, Chrome, Firefox, Edge, VS Code, Discord, Steam, VLC, Zoom, Notepad, Calculator, Paint, WordPad, Task Manager, File Explorer, WinRAR.

### 🌦️ Real-Time Weather
- Powered by [wttr.in](https://wttr.in) — **no API key needed**
- Ask in plain English: *"What's the weather in Chennai?"*
- Returns temperature, feels-like, humidity, wind speed, UV index

### 🔍 Web Search
- Powered by [Tavily](https://tavily.com) (free tier available)
- Automatically triggered for news, current events, prices, "who is", "what is" queries
- Results synthesized by the LLM — you get answers, not links

### ✅ Task Tracker
- Add tasks with priority (low / medium / high) and due dates
- Mark tasks done, delete tasks
- Active tasks are silently injected into the AI's context so it can reference them naturally

### 📊 Habit Tracker
- Log habits by name (e.g., *"meditation"*, *"workout"*)
- Tracks count and streak dates

### 💸 Expense Tracker
- Log expenses with amount, category, and note
- Daily and monthly totals, breakdown by category

### 🔐 Security
- **PIN lock screen** on startup (6-digit PIN, stored hashed in browser localStorage)
- **Audit log** — every chat message and PC action logged with timestamp and IP to `chotu_audit.json`
- **Rate limiting** — 30 requests/minute per IP
- **Sensitive action confirmation** — shutdown, restart, delete require an explicit `confirm` keyword
- No API keys ever sent to the frontend; all secrets stay server-side in `.env`

### 🎨 UI
- Retro-futuristic dark interface with animated boot sequence
- Responsive chat with message history
- PC control quick-action buttons
- Profile editor, notes panel, tracker panels — all in one tab

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · Uvicorn |
| LLM | Groq API (Llama 3.3 70B Versatile) |
| Web Search | Tavily API |
| Weather | wttr.in (free, no key) |
| PC Control | pyautogui · subprocess |
| System Monitor | psutil |
| Screenshots | Pillow (PIL) · ImageGrab |
| Frontend | Vanilla HTML/CSS/JS (single file) |
| Storage | Local JSON files |

---

## Quick Start

### Prerequisites
- Windows 10 or 11
- Python 3.10 or newer ([download](https://python.org/downloads/) — check **"Add Python to PATH"** during install)
- A free [Groq API key](https://console.groq.com)
- A free [Tavily API key](https://tavily.com) *(optional — only needed for web search)*

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/friday-ai.git
cd friday-ai
```

### 2. Create your `.env` file

Create a file named `.env` in the project folder:

```env
GROQ_API_KEY=gsk_your_groq_key_here
TAVILY_KEY=tvly_your_tavily_key_here
FRIDAY_SECRET=any_random_string_here
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn groq httpx python-dotenv pyautogui psutil Pillow
```

Or simply double-click **`START_FRIDAY.bat`** — it installs everything automatically and launches the server.

### 4. Run

```bash
python server.py
```

Or double-click `START_FRIDAY.bat`.

### 5. Open in browser

```
http://localhost:8000
```

Set a 6-digit PIN on first launch, then start chatting.

---

## Project Structure

```
friday-ai/
├── server.py             # FastAPI backend — all AI, PC control, APIs
├── index.html            # Frontend UI — single file, no build step
├── START_FRIDAY.bat      # One-click Windows launcher
├── SETUP_GUIDE.txt       # Detailed setup guide
├── .env                  # Your API keys (create this, never commit it)
│
├── chotu_profile.json    # Your profile (name, goals, routine) — auto-created
├── chotu_memory.json     # Conversation history & notes — auto-created
├── chotu_tracker.json    # Tasks, habits, expenses — auto-created
└── chotu_audit.json      # Security audit log — auto-created
```

> The JSON files are created automatically on first run. To reset everything, just delete them and restart.

---

## Configuration

All configuration lives in `.env`:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Your Groq API key — get it at [console.groq.com](https://console.groq.com) |
| `TAVILY_KEY` | No | Tavily search key — get it at [tavily.com](https://tavily.com). Without this, web search is disabled but everything else works. |
| `FRIDAY_SECRET` | Yes | Any random string — used for session signing. Just make it long and random. |

---

## API Reference

F.R.I.D.A.Y. exposes a REST API at `http://localhost:8000`. Useful if you want to build integrations:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Main chat endpoint |
| `GET` | `/profile` | Get user profile |
| `POST` | `/profile` | Update user profile |
| `GET` | `/tracker/tasks` | List tasks |
| `POST` | `/tracker/tasks` | Add a task |
| `POST` | `/tracker/tasks/{id}/done` | Mark task complete |
| `DELETE` | `/tracker/tasks/{id}` | Delete a task |
| `GET` | `/tracker/habits` | List habits |
| `POST` | `/tracker/habits` | Log a habit |
| `GET` | `/tracker/expenses` | List expenses |
| `POST` | `/tracker/expenses` | Add an expense |
| `POST` | `/pc` | Direct PC control action |
| `GET` | `/api/health` | Feature status check |

---

## Customising FRIDAY's Personality

The AI system prompt is in `server.py` inside `build_system_prompt()`. You can edit:
- The name it calls itself
- How it addresses you (default: "Boss")
- Language style, tone, length of replies
- What context it receives automatically

The model is `llama-3.3-70b-versatile` by default. To change it, edit the `MODEL` variable near the top of `server.py`.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `python: command not found` | Reinstall Python and check "Add Python to PATH" |
| `ModuleNotFoundError` | Run `pip install fastapi uvicorn groq httpx python-dotenv pyautogui psutil Pillow` |
| `FileNotFoundError: index.html` | Make sure `server.py` and `index.html` are in the **same folder** |
| `Port 8000 already in use` | Change the port on the last line of `server.py` to `port=8001`, then open `localhost:8001` |
| `GROQ_API_KEY not configured` | Check that your `.env` file is in the same folder as `server.py` and restart the server |
| `Connection refused` | The server isn't running — check your terminal for errors |
| App won't open | The app may be installed in a different path. Check `APP_REGISTRY` in `server.py` and add your path |

---

## Roadmap

- [ ] Voice input (Whisper / browser Web Speech API)
- [ ] Voice output (TTS)
- [ ] Linux and macOS support
- [ ] Proactive reminders and scheduled tasks
- [ ] Email integration
- [ ] Mobile-friendly UI
- [ ] Docker container for easy deployment
- [ ] Plugin system for custom skills

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [Groq](https://groq.com) — blazing fast LLM inference
- [Meta](https://ai.meta.com) — Llama 3.3 model
- [Tavily](https://tavily.com) — search API
- [wttr.in](https://wttr.in) — free weather API
- [FastAPI](https://fastapi.tiangolo.com) — the backbone
- Tony Stark, for the original FRIDAY concept ✊

---

*Built by [Shri Sanjay I S](https://github.com/YOUR_USERNAME) · Mechanical Engineering student · PSG College of Technology*
