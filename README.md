# StadiumPulse AI

**PromptWars — [Challenge 4] Smart Stadiums & Tournament Operations — FIFA World Cup 2026**

A GenAI-enabled platform with two views:

- **Fan Portal** (`/`) — a multilingual AI concierge, an accessibility-aware wayfinder, live
  zone crowd status, and personalised sustainability nudges.
- **Command View** (`/ops`) — a staff dashboard that turns live crowd + incident data into
  a plain-language AI briefing with a recommended next action.

## Problem → Solution mapping

| Challenge ask | What StadiumPulse AI does |
|---|---|
| Navigation | AI-generated, step-by-step wayfinding between any two points in the venue |
| Crowd management | Live occupancy per gate/zone with automatic normal/busy/critical status |
| Accessibility | Step-free routing toggle; Gate D modelled as the accessible entrance throughout |
| Transportation | Shuttle/metro guidance surfaced in both chat and wayfinder |
| Sustainability | Reusable-cup / zero-plastic nudges, tied to real fan behaviour (e.g. exit routing) |
| Multilingual assistance | Chat replies in the fan's chosen language (or auto-detected) |
| Operational intelligence | AI briefing synthesizes zone + incident data for the shift supervisor |
| Real-time decision support | Briefing includes a concrete recommended action, refreshable on demand |

## How GenAI is used (not bolted on)

Every AI call is **grounded** — it's given the venue facts and/or live sensor data as context,
so it can't hallucinate gate numbers or amenities:

1. `/api/chat` — Claude answers fan questions using a fixed venue fact-sheet, in the requested
   language.
2. `/api/navigate` — Claude turns an origin/destination pair into 3–5 numbered steps, routing
   via step-free paths when accessibility is requested.
3. `/api/ops-brief` — Claude reads the current hot zones and last 5 incidents and returns a
   sub-80-word briefing: top risk → recommended action → one accessibility/sustainability note.

The app runs **without any API key** in a clearly-labelled offline fallback mode (rule-based
responses), so judges can run it instantly. Set `ANTHROPIC_API_KEY` to switch on live Claude
responses — no code changes needed.

## Architecture

```
Flask app (app.py)
 ├─ digital twin: 6 zones, simulated live occupancy (swap for real turnstile/IoT feed)
 ├─ incident log: in-memory (swap for a real DB, e.g. Postgres, for production)
 └─ GenAI layer: ask_claude() wraps the Anthropic Messages API, with a rule-based
    fallback so every feature still works offline.

Frontend: server-rendered Jinja templates + vanilla JS (fetch + 6s polling), no build step.
```

## Run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional — omit to run in offline demo mode
python app.py
```
Visit `http://localhost:5000` (Fan Portal) and `http://localhost:5000/ops` (Command View).

## Deploy (free tier, ~5 minutes)

**Render.com**
1. Push this repo to GitHub.
2. New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `gunicorn app:app`
4. Add environment variable `ANTHROPIC_API_KEY` (optional).
5. Deploy — Render gives you a public URL for the submission form's "Deployed Link".

**Railway.app** works the same way with `gunicorn app:app` as the start command.

## What's simulated vs. production-ready

- Crowd occupancy is a seeded pseudo-live simulation standing in for real turnstile/camera
  counts — the API shape (`/api/crowd-status`) is designed to be a drop-in swap for a real feed.
- Incident log is in-memory for demo purposes; swap for a persistent store in production.
- Everything else (chat, wayfinding, briefing generation, Flask routes, UI) is real, working code.

## Roadmap

- Real IoT/turnstile integration for zone occupancy
- Push notifications to fans in a zone that's about to go critical
- Voice input for the concierge (hands-free at the gate)
- Post-match: AI-generated ops retro from the full incident + crowd history
