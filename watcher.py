import os, json, requests
from bs4 import BeautifulSoup

TG_TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
BASE = "https://egy.voxcinemas.com"
SHOWTIME_URL = BASE + "/movies/dune-part-one-re-release"
WHATSON_URL = BASE + "/movies/whatson"
TARGETS = ["dune: part one (re-release)", "dune: part two (re-release)"]
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
STATE = "alerted.json"

def notify(m):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": m})

def get_text(url):
    r = requests.get(url, headers=H, timeout=60)
    return BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)

state = {"alerted": [], "whatson_seen": None}
if os.path.exists(STATE):
    old = json.load(open(STATE))
    if isinstance(old, list):
        state["alerted"] = old
    else:
        state.update(old)
else:
    notify("Dune cloud watcher is running")

errors = []

# Check 1: re-releases appear in the showtimes movie list
try:
    text = get_text(SHOWTIME_URL)
    a = text.find("Select Your Movie(s)")
    b = text.find("Find Times and Book")
    if a == -1 or b == -1:
        raise RuntimeError("showtimes list markup changed")
    block = text[a:b].lower()
    for t in TARGETS:
        if t in block and t not in state["alerted"]:
            state["alerted"].append(t)
            notify(f"TICKETS LIVE: {t}\n{BASE}/movies/whatson")
except Exception as e:
    errors.append(f"showtimes check: {e}")

# Check 2: any new Dune title on the What's On page
try:
    text = get_text(WHATSON_URL)
    lines = {l.strip() for l in text.split("\n")
             if "dune" in l.lower() and len(l) < 80}
    if state["whatson_seen"] is None:
        state["whatson_seen"] = sorted(lines)
        notify("What's On check is set up. Dune titles listed right now: "
               + (", ".join(sorted(lines)) or "none found"))
    else:
        for l in sorted(lines - set(state["whatson_seen"])):
            notify(f"NEW on What's On: {l}\n{WHATSON_URL}")
        state["whatson_seen"] = sorted(set(state["whatson_seen"]) | lines)
except Exception as e:
    errors.append(f"whatson check: {e}")

json.dump(state, open(STATE, "w"))
if errors:
    raise RuntimeError("; ".join(errors))
