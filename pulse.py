#!/usr/bin/env python3
"""
The pulse: what today is about, as tags and one line each.

Runs once a day, anywhere Python runs, and writes pulse.json. The app fetches
that file; it never fetches the sources. Nothing here is a headline — every
source is either computed (the season, the Moon), a public archive with an
open licence, or a schedule. See README.md for the sources and their terms.

    python3 Service/pulse/pulse.py                # today, writes pulse.json
    python3 Service/pulse/pulse.py 2026-07-20     # any date
    python3 Service/pulse/pulse.py --out path.json

The rule the whole file serves: a signal is only emitted if some Read in the
catalogue carries its tag. A day with nothing to say says nothing.
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tags import tags_for, blocked, strong, bare, CALLINGS, _has  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
READS = os.path.join(HERE, "..", "..", "Read4Life", "Resources", "reads.json")
# The public feed repo has no Reads, only the vocabulary exported from them
# (`python3 Tools/export-vocabulary.py`): tags and author names, nothing else.
VOCAB = os.path.join(HERE, "vocabulary.json")
UA = "Read4Life-pulse/0.1 (daily reading app; contact via repository)"
COUNTRY = os.environ.get("PULSE_COUNTRY", "US")
# "Today" is the reader's today, not the runner's: GitHub's machines are on
# UTC and would date the file tomorrow for the whole American evening.
TZ = ZoneInfo(os.environ.get("PULSE_TZ", "America/New_York"))
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ------------------------------------------------------------------ signals

class Signal:
    def __init__(self, tag, line, source, weight):
        self.tag, self.line, self.source, self.weight = tag, line, source, weight

    def json(self):
        return {"tag": self.tag, "line": self.line, "source": self.source, "weight": self.weight}


def emit(out, tags, line, source, weight, known):
    """One signal per tag the catalogue can answer; the line is shared."""
    if blocked(line):
        return
    for tag in tags:
        if tag in known:
            out.append(Signal(tag, line, source, weight))


# --- computed: the natural year -------------------------------------------

def sky(day, out, known):
    """The season's turning points and the Moon, from arithmetic alone."""
    md = (day.month, day.day)
    turning = {(3, 20): ("spring", "Today is the spring equinox."), (6, 21): ("summer", "Today is the summer solstice."),
               (9, 22): ("autumn", "Today is the autumn equinox."), (12, 21): ("winter", "Today is the winter solstice.")}
    for (m, d), (tag, line) in turning.items():
        near = abs((day - dt.date(day.year, m, d)).days) <= 1
        if near:
            emit(out, [tag], line, "computed", 4, known)

    # Synodic month from a known new Moon (2000-01-06 18:14 UTC).
    ref = dt.datetime(2000, 1, 6, 18, 14)
    age = ((dt.datetime(day.year, day.month, day.day, 12) - ref).total_seconds() / 86400) % 29.530588853
    if abs(age - 14.77) < 0.6:
        emit(out, ["moon", "night"], "Tonight's Moon is full.", "computed", 3, known)
    elif age < 0.6 or age > 28.9:
        emit(out, ["moon", "night"], "Tonight is a new Moon — the darkest sky of the month.", "computed", 2, known)

    seasons = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
               6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
    month_tag = {4: "april", 6: "june", 11: "november", 12: "december"}.get(day.month)
    emit(out, [seasons[day.month]] + ([month_tag] if month_tag else []),
         f"It's {day.strftime('%B')}.", "computed", 1, known)


# --- public holidays (Nager.Date, MIT) -------------------------------------

def holidays(day, out, known):
    try:
        data = get(f"https://date.nager.at/api/v3/PublicHolidays/{day.year}/{COUNTRY}")
    except Exception as e:
        print("holidays:", e, file=sys.stderr); return
    for h in data:
        if h["date"] == day.isoformat():
            name = h.get("localName") or h.get("name")
            emit(out, tags_for(name), f"It's {name}.", "nager", 5, known)


# --- anniversaries (Wikimedia On This Day; titles and years only) ----------

def slug(name):
    return "author:" + "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").strip().replace(" ", "-")


def anniversaries(day, out, known, authors=()):
    """Wikipedia's 'on this day'. The event text is CC BY-SA, so it is used
    only to find the tag; the line is built from the page title and year,
    which are facts."""
    for kind in ("events", "births"):
        try:
            data = get(f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/{kind}/{day.month:02d}/{day.day:02d}")
        except Exception as e:
            print(f"onthisday {kind}:", e, file=sys.stderr); continue
        # Oldest first: a 1969 anniversary outranks a 2019 one on the same
        # tag, and the app's whole taste runs that way.
        items = sorted(data.get(kind, []), key=lambda i: i.get("year", 9999))
        for item in items:
            text = item.get("text", "")
            if kind == "events" and blocked(text):
                continue
            year = item.get("year")
            if kind == "births":
                pages = item.get("pages") or []
                title = pages[0].get("titles", {}).get("normalized", "") if pages else ""
                if not title or blocked(title):
                    continue
                # One of the catalogue's own authors: their Read leads today.
                if title in authors:
                    emit(out, [slug(title)], f"{title} was born on this day in {year}.", "wikimedia", 4, known | {slug(title)})
                    continue
                description = pages[0].get("description", "") if pages else ""
                if any(_has(c, description) for c in CALLINGS) and year <= 1930:
                    emit(out, tags_for(description), f"{title} was born on this day in {year}.", "wikimedia", 2, known)
                continue
            # An event: pick the linked page whose own title says what it is.
            for page in item.get("pages") or []:
                title = page.get("titles", {}).get("normalized", "").replace("_", " ")
                tags = tags_for(title)
                if title.startswith("Nobel Prize") or bare(title):
                    continue
                if tags and strong(title) and not blocked(title) and not blocked(page.get("description", "")):
                    emit(out, tags, f"Today is the anniversary of {title} ({year}).", "wikimedia", 2, known)
                    break


# --- Nobel Prizes (api.nobelprize.org, CC0) --------------------------------

def nobel(day, out, known):
    """Prizes awarded on this day of the year, any year. Curie's 1911
    Chemistry prize is dated 7 November; the archive knows."""
    prizes = []
    offset = 0
    try:
        while True:
            data = get(f"https://api.nobelprize.org/2.1/nobelPrizes?limit=100&offset={offset}&sort=asc")
            page = data.get("nobelPrizes", [])
            prizes += page
            offset += len(page)
            if not page or offset >= data.get("meta", {}).get("count", 0):
                break
    except Exception as e:
        print("nobel:", e, file=sys.stderr)
    data = {"nobelPrizes": prizes}
    field = {"Physics": ["physics", "science"], "Chemistry": ["science", "discovery"],
             "Physiology or Medicine": ["health", "medicine", "science"], "Literature": ["books", "poetry"],
             "Peace": ["peace"], "Economic Sciences": ["economy", "money"]}
    for p in data.get("nobelPrizes", []):
        awarded = p.get("dateAwarded", "")
        if awarded[5:] != day.strftime("%m-%d"):
            continue
        names = [l.get("knownName", {}).get("en") or l.get("orgName", {}).get("en", "") for l in p.get("laureates", [])]
        names = [n for n in names if n]
        if not names:
            continue
        cat = p["category"]["en"]
        who = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
        line = f"On this day in {p['awardYear']}, {who} {'was' if len(names) == 1 else 'were'} awarded the Nobel Prize in {cat}."
        emit(out, field.get(cat, ["science"]) + tags_for(who), line, "nobel", 3, known)


# --- the sky tonight (NASA APOD, public domain) ----------------------------

def apod(day, out, known):
    """Today's picture, or yesterday's if today's isn't posted yet — NASA
    publishes it in the small hours, US time."""
    data = None
    for when in (day, day - dt.timedelta(days=1)):
        try:
            data = get(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={when.isoformat()}")
            break
        except Exception as e:
            print(f"apod {when}:", e, file=sys.stderr)
    if not data:
        return
    title = data.get("title", "")
    tags = tags_for(title + " " + data.get("explanation", "")[:400])
    if tags:
        emit(out, tags, f"Tonight's sky, from NASA: {title}.", "nasa", 2, known)


# --- launches this week (Launch Library 2, attribution) --------------------

def launches(day, out, known):
    try:
        data = get("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=12&mode=list")
    except Exception as e:
        print("launches:", e, file=sys.stderr); return
    for l in data.get("results", []):
        when = dt.date.fromisoformat(l["net"][:10])
        if not (0 <= (when - day).days <= 4):
            continue
        name = l.get("name", "")
        rocket, _, payload = [x.strip() for x in name.partition("|")]
        tags = ["launch", "space"] + tags_for(name)
        dayword = "today" if when == day else "this week"
        what = f"{rocket} carrying {payload}" if payload else rocket
        emit(out, tags, f"A rocket launches {dayword}: {what}.", "launchlibrary", 3, known)
        break  # one is enough; the tag is the point


# --- what people are looking up (Wikimedia pageviews, CC0) -----------------

def curiosity(day, out, known):
    """Yesterday's most-viewed pages, folded onto the vocabulary. Low weight:
    this is what people are curious about, and it is mostly not our subject."""
    y = day - dt.timedelta(days=1)
    try:
        data = get(f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{y.year}/{y.month:02d}/{y.day:02d}")
    except Exception as e:
        print("pageviews:", e, file=sys.stderr); return
    seen = 0
    for a in data["items"][0]["articles"][:60]:
        title = a["article"].replace("_", " ")
        if title.startswith(("Main Page", "Special:", "Wikipedia:", "Deaths in", "Portal:")):
            continue
        tags = tags_for(title)
        if tags and strong(title) and not blocked(title):
            emit(out, tags, f"People are looking up {title} today.", "pageviews", 1, known)
            seen += 1
        if seen >= 3:
            break


# -------------------------------------------------------------------- build

def build(day):
    if os.path.exists(READS):
        with open(READS, encoding="utf-8") as f:
            reads = json.load(f)
        known = {t for r in reads for t in r["tags"]}
        authors = {r["author"] for r in reads}
    else:
        with open(VOCAB, encoding="utf-8") as f:
            vocab = json.load(f)
        known, authors = set(vocab["tags"]), set(vocab["authors"])
    out: list[Signal] = []
    for source in (sky, holidays, nobel, anniversaries, apod, launches, curiosity):
        try:
            if source is anniversaries:
                source(day, out, known, authors)
            else:
                source(day, out, known)
        except Exception as e:
            print(f"{source.__name__}: {e}", file=sys.stderr)

    # One line per tag, the heaviest wins; at most eight, heaviest first.
    best: dict[str, Signal] = {}
    for s in out:
        if s.tag not in best or s.weight > best[s.tag].weight:
            best[s.tag] = s
    computed = [s for s in best.values() if s.source == "computed"]
    rest = sorted((s for s in best.values() if s.source != "computed"), key=lambda s: -s.weight)
    signals = computed + rest[:max(0, 8 - len(computed))]
    return {
        "date": day.isoformat(),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "signals": [s.json() for s in signals],
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = dt.date.fromisoformat(args[0]) if args else dt.datetime.now(TZ).date()
    out_path = os.path.join(HERE, "pulse.json")
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    doc = build(day)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{day}: {len(doc['signals'])} signals -> {os.path.relpath(out_path)}")
    for s in doc["signals"]:
        print(f"  [{s['weight']}] {s['tag']:<12} {s['line']}  ({s['source']})")
