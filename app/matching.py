"""Match competitor listings to our products by name.

Brand must match, numbers that define the product (20W, 2m, 10000mAh, iPhone 15) must agree,
and the remaining words are compared. Returns a 0-1 score: >= 0.8 High, >= 0.55 Medium.
"""
from __future__ import annotations

import re

REPLACE = [(r"\btype[\s-]?c\b", "usb-c"), (r"\bpowerbank\b", "power bank"), (r"\btws\b", ""), (r"\boriginal\b", ""),
           (r"\b\d+\s*year warranty\b", ""), (r"\bwarranty\b", ""), (r"\b(black|white|blue|red|green|grey|gray|pink)\b", ""),
           (r"\bwith\b|\bfor\b|\band\b|\bthe\b", " "), (r"(\d)\s+(mah|w|m|mm|l|cu)\b", r"\1\2"), (r"\bpcs\b|\bpack\b", "pack")]
UNITS = re.compile(r"^\d+(\.\d+)?(w|m|mm|mah|l|p|gb|tb|inch|in)?$")


def normalize(name: str) -> list[str]:
    s = name.lower()
    s = re.sub(r"[|()\[\],/]", " ", s)
    s = re.sub(r"\s-\s", " ", s)
    for pat, rep in REPLACE:
        s = re.sub(pat, rep, s)
    return [t for t in re.split(r"\s+", s) if t and t != "-"]


def score(ours: str, theirs: str) -> float:
    a, b = normalize(ours), normalize(theirs)
    if not a or not b:
        return 0.0
    if a[0] != b[0]:  # brand
        return 0.0
    nums_a = {t for t in a if UNITS.match(t) or re.search(r"\d", t)}
    nums_b = {t for t in b if UNITS.match(t) or re.search(r"\d", t)}
    if nums_a != nums_b:
        overlap = len(nums_a & nums_b) / max(1, len(nums_a | nums_b))
        if overlap < 1:
            return round(0.3 * overlap, 3)  # different wattage / length / model = different product
    words_a, words_b = set(a) - nums_a, set(b) - nums_b
    j = len(words_a & words_b) / max(1, len(words_a | words_b))
    contain = len(words_a & words_b) / max(1, min(len(words_a), len(words_b)))
    return round(0.45 * j + 0.55 * contain, 3)


def label(s: float) -> str:
    return "High" if s >= 0.8 else "Medium" if s >= 0.55 else "Low"


def best_match(title: str, products: list[dict]):
    best, best_s = None, 0.0
    for p in products:
        s = score(p["name"], title)
        if s > best_s:
            best, best_s = p, s
    return best, best_s
