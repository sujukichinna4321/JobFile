import json, os, re, sys
from datetime import datetime, timedelta, timezone
import requests
import pytz

# বাংলাদেশ টাইমজোন
BD = pytz.timezone("Asia/Dhaka")
NOW_BD = datetime.now(BD)
TODAY_BD = NOW_BD.date()

DEFAULT_IMAGE = os.environ.get("DEFAULT_IMAGE", "https://raw.githubusercontent.com/samnite2290/img/gh-pages/HOME/HOME-LIVE-EVENT.png")
SUBTITLE_SUFFIX = os.environ.get("SUBTITLE_SUFFIX", " | Select 🅻🅸🆅🅴 🆂🅿🅾🆁🆃🆂 Button, Share Our Apps With Your Friends & Family.")

FOOTBALL_LEAGUES = {
    "premier league":   ("🏆 ENGLISH ⚽ PREMIER LEAGUE 2026/27", "TNT 1"),
    "la liga":          ("🏆 SPANISH ⚽ LA LIGA 2026/27",       "SonyLiv"),
    "bundesliga":       ("🏆 GERMAN ⚽ BUNDESLIGA 2026/27",      "SonyLiv"),
    "serie a":          ("🏆 ITALIAN ⚽ SERIE A 2026/27",        "SonyLiv"),
    "ligue 1":          ("🏆 FRENCH ⚽ LIGUE 1 2026/27",         "SonyLiv"),
    "champions league": ("🏆 UEFA ⚽ CHAMPIONS LEAGUE 2026/27",  "SonyLiv"),
    "europa league":    ("🏆 UEFA ⚽ EUROPA LEAGUE 2026/27",     "SonyLiv"),
    "nations league":   ("🏆 Friendly Match ⚽ NATIONS LEAGUE 2026/27", "SonyLiv"),
    "fifa world cup":   ("🏆 FIFA ⚽ WORLD CUP 2026",            "T Sports"),
    "friendly":         ("🏆 Friendly Match ⚽ 2026",            "T Sports"),
}

CRICKET_LEAGUES = {
    "t20i":      ("🏏 T20I CRICKET 2026",              "Fancode"),
    "t20":       ("🏏 T20 CRICKET 2026",               "Fancode"),
    "t10":       ("🏏 T10 CRICKET 2026",               "Fancode"),
    "odi":       ("🏏 ODI CRICKET 2026",               "Fancode"),
    "test":      ("🏏 TEST CRICKET 2026",              "Fancode"),
    "world cup": ("🏆 ICC 🏏 MEN'S T20 WORLD CUP 2026", "Willow"),
    "ipl":       ("🏏 INDIAN PREMIER LEAGUE 2026",     "SonyLiv"),
    "bbl":       ("🏏 BIG BASH LEAGUE 2026",           "SonyLiv"),
    "psl":       ("🏏 PSL 2026",                       "Tapmad"),
    "bpl":       ("🏏 BPL 2026",                       "T Sports"),
}

SOURCES = [
    ("fancode", "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json", "Fancode"),
    ("sonyliv", "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json",   "SonyLiv"),
    ("tapmad",  "https://gist.githubusercontent.com/albatr0ssss/3cff7a26be49b1d352c15f615067e7cd/raw/tapmad_bd.json", "Tapmad"),
]

def fetch_json(url):
    try:
        print(f"Fetching: {url}", flush=True)
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"Successfully fetched {len(data) if isinstance(data, list) else 'dict'} items from {url}", flush=True)
        return data
    except Exception as e:
        print(f"[ERROR] fetch failed {url}: {e}", flush=True)
        return []

def _iter_events(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ("events", "data", "matches", "items", "results"):
            v = data.get(k)
            if isinstance(v, list): return v
    return []

def parse_start(ev):
    keys = ("startTime", "start_time", "startAt", "startDate", "beginAt", "matchTime", "date", "datetime", "utcStartTime", "start")
    for k in keys:
        v = ev.get(k)
        if not v: continue
        if isinstance(v, (int, float)):
            try: return datetime.fromtimestamp(v, tz=timezone.utc).astimezone(BD)
            except: pass
        if isinstance(v, str):
            s = v.strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(BD)
            except: pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M"):
                try:
                    dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
                    return dt.astimezone(BD)
                except: continue
    return None

def _name(x):
    if isinstance(x, dict): return x.get("name") or x.get("title") or x.get("shortName") or ""
    return str(x or "")

def extract_teams(ev):
    t1 = ev.get("team1") or ev.get("homeTeam") or ev.get("home") or ev.get("teamA") or ""
    t2 = ev.get("team2") or ev.get("awayTeam") or ev.get("away") or ev.get("teamB") or ""
    t1, t2 = _name(t1).strip(), _name(t2).strip()
    if not t1 or not t2:
        title = ev.get("title") or ev.get("name") or ev.get("eventName") or ""
        parts = re.split(r"\s+(?:vs\.?|v\.?|🆚|-)\s+", title, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            t1, t2 = parts[0].strip(), parts[1].strip()
    return t1, t2

def extract_competition(ev):
    for k in ("competition", "league", "tournament", "series", "event", "category", "sport"):
        v = _name(ev.get(k))
        if v: return v
    return ""

def extract_image(ev):
    for k in ("image", "poster", "thumbnail", "banner", "imageUrl", "image_url", "logo"):
        v = ev.get(k)
        if isinstance(v, str) and v.startswith("http"): return v
        if isinstance(v, dict):
            u = v.get("url") or v.get("src")
            if isinstance(u, str) and u.startswith("http"): return u
    return ""

def detect_sport(ev, comp):
    s = (ev.get("sport") or ev.get("sportType") or "").lower()
    c = (comp or "").lower()
    if "cricket" in s or any(x in c for x in ("cricket", "t20", "t10", "odi", "test", "ipl", "bbl", "psl", "bpl", "icc")):
        return "cricket"
    return "football"

def guess_format(comp):
    c = (comp or "").lower()
    if "t10" in c: return "T10"
    if "t20" in c: return "T20"
    if "odi" in c or "one day" in c: return "ODI"
    if "test" in c: return "Test"
    return "T20"

def league_meta(sport, comp):
    c = (comp or "").lower()
    table = CRICKET_LEAGUES if sport == "cricket" else FOOTBALL_LEAGUES
    for key, val in table.items():
        if key in c: return val
    return ("🏏 CRICKET 2026" if sport == "cricket" else "⚽ FOOTBALL 2026", "Fancode" if sport == "cricket" else "T Sports")

def bst_str(dt):
    return dt.strftime("%d-%m-%Y-%I:%M 00 %p").lower()

def compute_multiple(sport, fmt, start_bd):
    if sport == "football": return start_bd + timedelta(minutes=60)
    if fmt == "T20": return start_bd + timedelta(minutes=105)
    if fmt == "T10": return start_bd + timedelta(minutes=55)
    if fmt == "ODI": return start_bd + timedelta(minutes=225)
    if fmt == "Test": return start_bd + timedelta(minutes=150)
    return None

def build_entry(ev, platform_tag):
    start = parse_start(ev)
    if not start: return None
    
    # আপনার রিকোয়ারমেন্ট অনুযায়ী আজকের ম্যাচ ফিল্টার
    if start.date() != TODAY_BD: 
        return None 
        
    t1, t2 = extract_teams(ev)
    if not t1 or not t2: return None

    comp = extract_competition(ev)
    sport = detect_sport(ev, comp)
    sub_name, channel = league_meta(sport, comp)
    fmt = guess_format(comp) if sport == "cricket" else ""

    title    = f"{t1} 🆚 {t2} । Watch on {channel}"
    subtitle = f"{sub_name}{SUBTITLE_SUFFIX}"
    image    = extract_image(ev) or DEFAULT_IMAGE
    date_time = bst_str(start - timedelta(minutes=5))

    multiple_on = sport == "football" or fmt in ("T20", "T10", "ODI", "Test")
    multiple_time = ""
    if multiple_on:
        mt = compute_multiple(sport, fmt, start)
        if mt:
            multiple_time = f"({bst_str(mt)})"
        else:
            multiple_on = False

    return {
        "Date & Time": date_time,
        "multipleTimeRun": "On" if multiple_on else "Off",
        "multipleTime": multiple_time,
        "Title": title,
        "Subtitle": subtitle,
        "Image": image,
    }

def _sort_key(x):
    s = x["Date & Time"]
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})-(\d{2}):(\d{2})\s+00\s+([ap]m)", s)
    if not m: return datetime.max
    dd, mm, yy, hh, mi, ap = m.groups()
    hh = int(hh) % 12
    if ap == "pm": hh += 12
    return datetime(int(yy), int(mm), int(dd), hh, int(mi))

def main():
    results, seen = [], set()
    for name, url, tag in SOURCES:
        data = fetch_json(url)
        events = _iter_events(data)
        print(f"Processing {len(events)} events from {name}", flush=True)
        
        for ev in events:
            try:
                entry = build_entry(ev, tag)
            except Exception as e:
                continue
            if not entry: continue
            key = (entry["Title"], entry["Date & Time"])
            if key in seen: continue
            seen.add(key)
            results.append(entry)

    results.sort(key=_sort_key)

    # আজ কোনো ম্যাচ না পেলে ডামি ডেটা দিয়ে ফাইল তৈরি হবে
    if not results:
        print("[WARN] No matches found for today. Creating dummy file.", flush=True)
        results.append({
            "Date & Time": bst_str(NOW_BD),
            "multipleTimeRun": "Off",
            "multipleTime": "",
            "Title": "No Matches Found Today",
            "Subtitle": "Check back later or verify the source URLs.",
            "Image": DEFAULT_IMAGE
        })

    with open("notifications.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Generated notifications.json with {len(results)} entries.", flush=True)

if __name__ == "__main__":
    main()
