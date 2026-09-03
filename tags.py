"""
The tag vocabulary, and how the world's words map onto it.

The app's Reads carry a small set of plain topic words (see Tools/seed.py).
Everything the pulse hears — a holiday's name, an anniversary's title, a
launch, a page people are looking up — is folded onto that same vocabulary
here, so a signal can only ever say something a Read can answer.

Keep the vocabulary small and boring. "moon", not "lunar-exploration".
"""

# keyword (lowercase, matched as a substring of the lowercased text) -> tags
KEYWORDS = {
    # sky and space
    "moon": ["moon"], "lunar": ["moon"], "artemis": ["moon", "launch"], "apollo": ["moon", "space"],
    "eclipse": ["sun", "moon", "astronomy"], "solar": ["sun"], "sunrise": ["dawn", "morning"],
    "mars": ["mars", "space"], "rocket": ["launch", "space"], "launch": ["launch", "space"],
    "spacecraft": ["space"], "astronaut": ["space"], "orbit": ["space"], "telescope": ["astronomy", "telescope"],
    "comet": ["astronomy"], "meteor": ["astronomy"], "planet": ["astronomy", "space"], "galaxy": ["astronomy"],
    "nebula": ["astronomy"], "star": ["astronomy"], "aurora": ["astronomy", "light"],
    # science and discovery
    "nobel": ["science", "discovery"], "physics": ["physics", "science"], "chemistry": ["science"],
    "medicine": ["health", "medicine"], "vaccine": ["health", "disease"], "pandemic": ["plague", "disease"],
    "epidemic": ["plague", "disease"], "virus": ["disease"], "hospital": ["health"], "doctor": ["doctor", "health"],
    "darwin": ["evolution"], "evolution": ["evolution"], "fossil": ["evolution", "deep-time"], "dinosaur": ["deep-time"],
    "einstein": ["relativity", "physics"], "relativity": ["relativity"], "atom": ["atoms", "physics"],
    "radium": ["radiation"], "radiation": ["radiation"], "curie": ["radiation"], "galileo": ["astronomy", "moon"],
    "microscope": ["microscope", "science"], "bacteria": ["bacteria", "disease"], "genome": ["evolution", "science"],
    "heart": ["heart", "health"], "blood": ["blood", "health"], "invention": ["discovery", "technology"],
    # machines and minds
    "robot": ["robots", "machines"], "artificial intelligence": ["ai", "machines"], "openai": ["ai"], "chatgpt": ["ai"],
    " ai ": ["ai"], "automation": ["automation", "work"], "computer": ["technology", "machines"],
    "internet": ["internet", "network"], "algorithm": ["ai", "technology"],
    # power and the public
    "election": ["election", "democracy"], "vote": ["election", "democracy"], "ballot": ["election"],
    "parliament": ["democracy", "politics"], "congress": ["democracy", "politics"], "senate": ["politics"],
    "president": ["politics", "leadership", "power"], "prime minister": ["politics", "leadership"],
    "democracy": ["democracy"], "republic": ["democracy"], "independence": ["democracy", "freedom"],
    "constitution": ["law", "democracy"], "revolution": ["revolution"], "empire": ["empire", "power"],
    "treaty": ["negotiation", "peace"], "peace": ["peace"], "protest": ["politics", "revolution"],
    "inflation": ["money", "economy"], "recession": ["economy", "money", "collapse"], "bankrupt": ["money", "ruin"],
    "stock market": ["money", "economy"], "budget": ["money"], "tax": ["money"],
    # the natural year
    "spring": ["spring"], "summer": ["summer"], "autumn": ["autumn"], "fall ": ["autumn"], "winter": ["winter"],
    "equinox": ["spring", "autumn"], "solstice": ["summer", "winter"], "harvest": ["autumn"],
    "snow": ["winter", "cold"], "frost": ["cold", "winter"], "heat": ["summer"], "storm": ["storm"],
    "hurricane": ["storm"], "flood": ["water", "storm"], "wildfire": ["fire"], "fire": ["fire"],
    "drought": ["climate"], "climate": ["climate"], "earth day": ["nature", "earth"],
    # the sea and the road
    "ocean": ["sea", "ocean"], " sea": ["sea"], "voyage": ["voyage", "travel"], "ship": ["sea", "travel"],
    "island": ["islands"], "expedition": ["explorers", "discovery"], "explorer": ["explorers"],
    # letters and art
    "poet": ["poetry"], "poetry": ["poetry"], "novel": ["books"], "book": ["books"], "library": ["books"],
    "shakespeare": ["love", "poetry"], "theatre": ["art"], "museum": ["art"], "painting": ["art"],
    # days of the heart
    "valentine": ["love"], "wedding": ["love", "marriage"], "marriage": ["marriage", "love"],
    "mother": ["family"], "father": ["family"], "family": ["family"], "children": ["children"],
    "new year": ["beginnings"], "birthday": ["birth"], "thanksgiving": ["family", "gratitude"],
    "christmas": ["christmas", "december"], "halloween": ["fear", "night"], "memorial": ["memory"],
    "labor day": ["work"], "labour day": ["work"], "workers": ["work"],
    # the city
    "london": ["london", "city"], "city": ["city"], "walk": ["walking"],
}

# An anniversary is only worth a line if the thing itself is one of these.
# "Royal Exchange, London (1666)" is a fact and not a reason to read anything.
STRONG = [
    "moon", "lunar", "apollo", "eclipse", "telescope", "mars", "rocket", "launch", "spacecraft", "astronaut",
    "comet", "nobel", "vaccine", "darwin", "evolution", "einstein", "relativity", "radium", "galileo",
    "robot", "computer", "internet", "election", "independence", "constitution", "revolution", "democracy",
    "poet", "shakespeare", "library", "equinox", "solstice", "voyage", "expedition", "microscope", "atom",
    "invention", "observatory", "planet", "galaxy", "origin of species", "great fire",
]


# Anything that mentions these never becomes a signal, whatever else it says.
# The app is for a good two minutes; the day's horrors are not its subject.
BLOCKLIST = [
    "war", "battle", "killed", "kill", "massacre", "attack", "bomb", "murder", "shooting", "shot",
    "terror", "genocide", "holocaust", "coup", "assassin", "execut", "crash", "collision", "dies", "died",
    "death", "deaths", "dead", "slave", "slavery", "lynch", "riot", "hostage", "kidnap", "invasion",
    "nuclear test", "missile", "troops", "military", "army", "navy", "airstrike", "torture", "abuse",
    "rape", "suicide", "disaster", "earthquake", "tsunami", "explosion", "sinking", "wreck", "famine",
    "siege", "hijack", "assault", "violence", "prison", "arrest", "uprising", "conflict", "crisis",
    "killing", "killings", "stabbing", "poison", "victim", "victims", "abduction", "disappearance",
    "scandal", "impeach", "resign", "fraud", "cartel", "gang", "drug",
]


import re


def _has(key: str, text: str) -> bool:
    """Whole words only: "evolution" must not hear "revolution", and "war"
    must not hear "awarded"."""
    return re.search(r"\b" + re.escape(key.strip()) + r"\b", text, re.IGNORECASE) is not None


def tags_for(text: str) -> list[str]:
    """Every tag the vocabulary hears in a piece of text, in first-seen order."""
    seen: list[str] = []
    for key, tags in KEYWORDS.items():
        if _has(key, text):
            for t in tags:
                if t not in seen:
                    seen.append(t)
    return seen


def blocked(text: str) -> bool:
    return any(_has(b, text) for b in BLOCKLIST)


def strong(text: str) -> bool:
    return any(_has(k, text) for k in STRONG)


def bare(title: str) -> bool:
    """A page that is just the topic — "Mars", "Moon" — is a subject, not an
    event, and makes a silly anniversary."""
    return title.strip().lower() in KEYWORDS


# Who counts, for a birthday, when they aren't one of the catalogue's authors.
CALLINGS = ["poet", "novelist", "playwright", "physicist", "astronomer", "naturalist", "chemist",
            "mathematician", "philosopher", "historian", "inventor", "explorer", "biologist"]
