"""
StadiumPulse AI — GenAI-enabled Smart Stadium & Tournament Operations platform
Built for PromptWars [Challenge 4] Smart Stadiums & Tournament Operations — FIFA World Cup 2026

Two front doors:
  /            Fan Portal   — multilingual AI concierge, wayfinding, live zone status
  /ops         Command View — operations staff dashboard with AI-generated briefings

GenAI is used for:
  1. Multilingual fan assistant (translation + grounded Q&A)
  2. Turn-by-step, accessibility-aware wayfinding narration
  3. Real-time operational briefings synthesized from live crowd + incident data
  4. Sustainability nudges personalised to fan behaviour

The app runs fully standalone with a rule-based fallback so it can be demoed
without any API key. Set ANTHROPIC_API_KEY to switch on live GenAI responses.
"""

import os
import random
import time
import uuid
import logging
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=16*1024
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Anthropic client (optional — app degrades gracefully without a key)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_client = None
if ANTHROPIC_API_KEY:
    try:
        import anthropic

        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        _client = None


def ask_claude(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Call Claude if configured, otherwise return a clearly-labelled fallback."""
    if _client is None:
        return None
    try:
        resp = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        return "\n".join(parts).strip()
    except Exception as exc:  # noqa: BLE001 — surface any API failure as a soft fallback
        app.logger.warning("Claude call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Stadium digital twin (mock live data — swap for real IoT/turnstile feeds)
# ---------------------------------------------------------------------------
ZONES = [
    {"id": "GA", "name": "Gate A — East Concourse", "capacity": 4200},
    {"id": "GB", "name": "Gate B — West Concourse", "capacity": 4200},
    {"id": "GC", "name": "Gate C — North Plaza", "capacity": 3000},
    {"id": "GD", "name": "Gate D — South Plaza (Accessible)", "capacity": 2200},
    {"id": "CF", "name": "Fan Fest Concourse", "capacity": 6000},
    {"id": "TR", "name": "Transit Hub / Shuttle Bay", "capacity": 3500},
]

VENUE_FACTS = """
Venue: FIFA World Cup 2026 Host Stadium (68,500 seats)
Gates: A (East), B (West), C (North), D (South — step-free, accessible seating routed here)
Transit: Shuttle Bay behind Gate D; Metro Blue Line exits at North Plaza (Gate C)
Amenities: First aid at every gate + Section 114 & Section 220; prayer/quiet rooms behind Gate C;
family restrooms every 40m on the concourse ring; refill stations every 25m (reusable-cup only, no
single-use plastics inside the bowl — part of the tournament's zero-waste pledge)
Kickoff: Gates open 3 hours before kickoff. Bag policy: clear bags under A4 size only.
Multilingual staff (English, Spanish, Portuguese, French, Arabic) stationed at every gate info desk.
"""

_incident_log = []


def simulate_zone_state():
    """Pseudo-live crowd figures — deterministic-ish drift so the dashboard feels alive."""
    t = int(time.time() // 6)  # shifts every 6s
    state = []
    for i, z in enumerate(ZONES):
        random.seed(t * 13 + i)
        base = 0.35 + 0.5 * abs(((t + i * 7) % 40) - 20) / 20
        noise = random.uniform(-0.05, 0.08)
        occ = max(0.05, min(0.99, base + noise))
        count = int(occ * z["capacity"])
        state.append(
            {
                **z,
                "occupancy_pct": round(occ * 100, 1),
                "count": count,
                "status": "critical" if occ > 0.85 else "busy" if occ > 0.6 else "normal",
                "wait_min": max(1, int(occ * 22)),
            }
        )
    return state


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------
@app.route("/")
def fan_portal():
    return render_template("index.html", ai_live=_client is not None)


@app.route("/ops")
def ops_dashboard():
    return render_template("ops.html", ai_live=_client is not None)


# ---------------------------------------------------------------------------
# API — live digital twin
# ---------------------------------------------------------------------------
@app.route("/api/crowd-status")
def crowd_status():
    return jsonify({"zones": simulate_zone_state(), "ts": datetime.utcnow().isoformat()})


@app.route("/api/incidents", methods=["GET", "POST"])
def incidents():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        entry = {
            "id": str(uuid.uuid4())[:8],
            "zone": data.get("zone", "GA"),
            "type": data.get("type", "General"),
            "note": data.get("note", ""),
            "ts": datetime.utcnow().isoformat(),
        }
        _incident_log.insert(0, entry)
        return jsonify(entry), 201
    return jsonify(_incident_log[:20])


# ---------------------------------------------------------------------------
# API — GenAI features
# ---------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    """Multilingual fan concierge — navigation, accessibility, amenities, transport."""
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    language = data.get("language", "auto-detect the language and reply in the same language")
    if not message:
        return jsonify({"reply": "Ask me anything about gates, seating, transport, or accessibility."})

    system = (
        "You are the on-site AI concierge for a FIFA World Cup 2026 host stadium. "
        "Answer ONLY using the venue facts provided. Be concise (max 4 sentences), warm, and "
        f"practical. Respond in: {language}. If asked something outside the venue facts, say so "
        "and offer to connect the fan with a human steward.\n\nVenue facts:\n" + VENUE_FACTS
    )
    reply = ask_claude(system, message)
    if reply is None:
        reply = _fallback_chat(message)
    return jsonify({"reply": reply, "ai_live": _client is not None})


@app.route("/api/navigate", methods=["POST"])
def navigate():
    """Turn-by-step, accessibility-aware wayfinding narration."""
    data = request.get_json(force=True) or {}
    origin = data.get("origin", "Main entrance")
    destination = data.get("destination", "Section 114")
    accessible = bool(data.get("accessible"))
    language = data.get("language", "English")

    system = (
        "You generate short, clear step-by-step walking directions inside a football stadium. "
        "Use 3-5 numbered steps, each under 15 words. If accessibility is requested, route via "
        "step-free paths and lifts and mention it explicitly.\n\nVenue facts:\n" + VENUE_FACTS
    )
    prompt = (
        f"From: {origin}\nTo: {destination}\nAccessible route needed: {accessible}\n"
        f"Reply in: {language}"
    )
    reply = ask_claude(system, prompt, max_tokens=300)
    if reply is None:
        reply = _fallback_navigate(origin, destination, accessible)
    return jsonify({"directions": reply, "ai_live": _client is not None})


@app.route("/api/ops-brief", methods=["POST"])
def ops_brief():
    """Real-time decision support: synthesize crowd + incident data into staff actions."""
    zones = simulate_zone_state()
    hot = [z for z in zones if z["status"] != "normal"]
    system = (
        "You are an operations-intelligence assistant for stadium event control. Given live zone "
        "occupancy and recent incidents, write a crisp briefing for the shift supervisor: "
        "1) top risk, 2) recommended action, 3) one sustainability or accessibility note if relevant. "
        "Max 80 words, no preamble."
    )
    prompt = f"Zones needing attention: {hot}\nRecent incidents: {_incident_log[:5]}"
    reply = ask_claude(system, prompt, max_tokens=250)
    if reply is None:
        reply = _fallback_brief(hot)
    return jsonify({"brief": reply, "hot_zones": hot, "ai_live": _client is not None})


@app.route("/api/sustainability-tip")
def sustainability_tip():
    tips = [
        "Refill stations are 25m apart on every concourse — skip single-use bottles entirely.",
        "Metro Blue Line at Gate C cuts your post-match exit time vs. rideshare pickup.",
        "Return your reusable cup at any refill point for the deposit — it's reused, not recycled.",
        "Walking to Gate D? You'll also pass the quietest exit route after the final whistle.",
    ]
    return jsonify({"tip": random.choice(tips)})


# ---------------------------------------------------------------------------
# Rule-based fallbacks (used only when no ANTHROPIC_API_KEY is configured)
# ---------------------------------------------------------------------------
def _fallback_chat(message: str) -> str:
    m = message.lower()
    if "accessib" in m or "wheelchair" in m:
        return ("[offline mode] Gate D is our step-free entrance with accessible seating and lifts "
                "to every tier. Staff can meet you there — ask any steward to radio ahead.")
    if "transport" in m or "shuttle" in m or "metro" in m or "bus" in m:
        return ("[offline mode] Shuttle Bay is directly behind Gate D. Metro Blue Line exits at "
                "North Plaza, Gate C — about a 5 minute walk to the bowl.")
    if "bag" in m:
        return "[offline mode] Only clear bags under A4 size are allowed inside the venue."
    if "food" in m or "water" in m or "refill" in m:
        return ("[offline mode] Refill stations sit every 25m on the concourse — it's a reusable-cup, "
                "zero-single-use-plastic venue.")
    return ("[offline mode — connect ANTHROPIC_API_KEY for full AI answers] I can help with gates, "
            "seating, transport, accessibility, or amenities — what do you need?")


def _fallback_navigate(origin, destination, accessible):
    route = "via the step-free ring and Gate D lifts" if accessible else "via the shortest concourse route"
    return (
        f"[offline mode]\n1. Exit {origin} toward the outer concourse.\n"
        f"2. Follow signage {route}.\n"
        f"3. Continue to the section nearest {destination}.\n"
        f"4. A steward at the tier entrance will confirm your seat block."
    )


def _fallback_brief(hot_zones):
    if not hot_zones:
        return "[offline mode] All zones nominal. No action required — recommend routine patrol cadence."
    worst = max(hot_zones, key=lambda z: z["occupancy_pct"])
    return (
        f"[offline mode] Top risk: {worst['name']} at {worst['occupancy_pct']}% capacity, "
        f"~{worst['wait_min']} min wait. Action: open overflow lane / redirect arrivals via next-"
        f"quietest gate. Note: prioritise Gate D accessible flow during redirection."
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    return response
