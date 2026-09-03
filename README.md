# The pulse service

One script, once a day, one file. `pulse.py` asks a handful of open sources
what today is about, folds the answers onto the catalogue's tag vocabulary,
filters out anything the app would never show, and writes `pulse.json`:

```json
{ "date": "2026-09-03",
  "signals": [ { "tag": "launch", "line": "A rocket launches today: …", "source": "launchlibrary", "weight": 3 } ] }
```

The app fetches the committed file from GitHub's raw host on launch, keeps
the last good copy, and ships with a bundled copy so a phone with no signal
still has a day. `.github/workflows/pulse.yml` runs it at 05:17 UTC and
commits the result. No server. (Set `NASA_API_KEY` as a repository secret to
lift the demo-key rate limit; `PULSE_COUNTRY` picks the holiday calendar.)

```
python3 Service/pulse/pulse.py              # today
python3 Service/pulse/pulse.py 2026-07-20   # any date, to see what it would say
```

## Sources, and what they're allowed to be used for

| Source | What it gives | Licence | How it's used |
|---|---|---|---|
| Arithmetic | equinoxes, solstices, the Moon's phase, the month | — | The floor: every day has a season and a sky. Always emitted. |
| [Nager.Date](https://date.nager.at) | public holidays by country | MIT | `It's Labor Day.` — weight 5, the day's loudest fact. |
| [Nobel Prize API](https://api.nobelprize.org) | every prize, dated to the day | CC0 | `On this day in 1911, Marie Curie was awarded the Nobel Prize in Chemistry.` Science's best friend. |
| [Wikimedia On This Day](https://api.wikimedia.org/wiki/Feed_API) | anniversaries and births | CC BY-SA 4.0 | Used to *find* the tag only. The line is built from the linked page's **title and year**, which are facts, never from the event text. An event counts only if its own title is one of the strong topics (`STRONG` in `tags.py`); the oldest wins a tag. A birth counts if the person is one of the catalogue's authors — their Read leads that day, weight 4 — or a poet, physicist, astronomer and the like born by 1930. |
| [NASA APOD](https://api.nasa.gov) | tonight's sky, with a title | Public domain (US government) | `Tonight's sky, from NASA: The Eclipse and the Stork.` |
| [Launch Library 2](https://thespacedevs.com) | the launch schedule | Free tier, attribution | `A rocket launches this week: Falcon 9 carrying …` — the `launch`/`space`/`moon` tags. |
| [Wikimedia pageviews](https://wikimedia.org/api/rest_v1/) | what people looked up yesterday | CC0 | Low weight. Only when a title lands on the vocabulary. |

Not used, deliberately: any news API. The reader never sees a headline; the
pulse carries topics, and the Read is the content.

## The filter

`tags.py` is two lists. `KEYWORDS` maps the world's words to the catalogue's
tags (`moon`, `election`, `fire`), and a signal is only emitted if some Read
carries the tag — so a day can only ever point at something the app can
answer. `BLOCKLIST` drops anything that mentions war, killing, disaster and
their relatives, wherever it comes from. The app is for a good two minutes.

## Weights

Holiday 5 · season turning-point 4 · Nobel, launch, full Moon 3 ·
anniversary, sky, new Moon 2 · month, curiosity 1. In the app a pulse signal
outranks the almanac, and within the pulse the weight breaks ties. Eight
signals a day at most, one per tag, the computed ones always kept.
