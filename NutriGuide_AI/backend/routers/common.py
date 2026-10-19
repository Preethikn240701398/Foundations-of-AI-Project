from seed import all_serialized


async def load_meals() -> list[dict]:
    return await all_serialized("meals")


async def load_foods() -> list[dict]:
    return await all_serialized("foods")


def find_item(name: str | None, *pools: list[dict]) -> dict | None:
    """Fuzzy lookup of a meal/food by name (exact, then contains, then token match)."""
    if not name:
        return None
    q = name.strip().lower()
    universe = [x for pool in pools for x in pool]
    for x in universe:
        if str(x.get("name", "")).lower() == q:
            return x
    for x in universe:
        if q in str(x.get("name", "")).lower():
            return x
    tokens = [t for t in q.replace(",", " ").split() if len(t) > 2]
    best, best_hits = None, 0
    for x in universe:
        hay = str(x.get("name", "")).lower()
        hits = sum(1 for t in tokens if t in hay)
        if hits > best_hits:
            best, best_hits = x, hits
    return best if best_hits else None


def find_in_text(text: str, *pools: list[dict]) -> dict | None:
    """Find a catalogue item whose name (or a key word of it) appears inside a sentence."""
    t = text.lower()
    universe = [x for pool in pools for x in pool]
    named = [x for x in universe if str(x.get("name", "")).lower() in t]
    if named:
        return max(named, key=lambda x: len(x["name"]))
    stop = {"with", "and", "the", "for", "can", "eat", "have", "is", "are", "good", "bad", "safe", "okay", "ok",
            "should", "what", "about", "this", "that", "meal", "food", "diet", "fried", "fry"}
    words = [w.strip("?.,!") for w in t.split()]
    words = [w for w in words if len(w) > 3 and w not in stop]
    best, best_hits = None, 0
    for x in universe:
        name_words = set(str(x.get("name", "")).lower().replace("&", " ").replace("(", " ").replace(")", " ").split())
        hits = sum(1 for w in words if w in name_words or (w.endswith("s") and w[:-1] in name_words))
        if hits > best_hits:
            best, best_hits = x, hits
    return best if best_hits else None
