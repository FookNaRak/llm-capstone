"""Compare lexical overlap with a sparse character-vector retriever."""

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

MANUAL = "https://www.rd.go.th/fileadmin/tax_pdf/pit/2568/Ins91_241268.pdf"
FORM = "https://www.rd.go.th/fileadmin/tax_pdf/pit/2568/241268PIT91.pdf"


TOKEN = re.compile(r"[a-z0-9]+|[\u0e00-\u0e7f]+|[^\W\d_]+")


def tokens(value):
    return TOKEN.findall(unicodedata.normalize("NFKC", value).casefold())


def ngrams(value):
    """Sparse character embedding features, including adjacent model tokens."""
    words = tokens(value)
    text = f" {' '.join(words)} "
    compact = "".join(words)
    return Counter(
        sample[start : start + size]
        for sample in (text, compact)
        for size in (3, 4)
        for start in range(len(sample) - size + 1)
    )


class TaxRules:
    def __init__(self):
        records = json.loads(Path(__file__).with_name("rules.json").read_text(encoding="utf-8"))
        self.rules = {}
        for rule in records:
            document = FORM if rule.get("document") == "form" else MANUAL
            self.rules[rule["id"]] = dict(rule, url=f"{document}#page={rule['page']}")
        rows = {key: f"{rule['title']} {rule['text']}" for key, rule in self.rules.items()}
        self.words = {key: set(tokens(row)) for key, row in rows.items()}
        counts = {key: ngrams(row + " " + self.rules[key]["terms"])
                  for key, row in rows.items()}
        self.df = Counter(feature for row in counts.values() for feature in row)
        self.vectors = {key: self.vector(row) for key, row in counts.items()}

    def vector(self, counts):
        weights = {key: (1 + math.log(count)) *
                   (1 + math.log((1 + len(self.rules)) / (1 + self.df[key])))
                   for key, count in counts.items() if key in self.df}
        norm = math.sqrt(sum(weight ** 2 for weight in weights.values()))
        return {key: weight / norm for key, weight in weights.items()}

    def search(self, query, mode="hybrid", limit=3):
        words = set(tokens(query))
        vector = self.vector(ngrams(query))
        ranked = []
        for key, rule in self.rules.items():
            overlap = len(words & self.words[key]) / max(1, len(words))
            similarity = sum(weight * self.vectors[key].get(feature, 0)
                             for feature, weight in vector.items())
            score = overlap if mode == "keyword" else 0.2 * overlap + 0.8 * similarity
            floor = 0 if mode == "keyword" else 0.035
            if score > floor:
                ranked.append((score, key, rule))
        return [rule for _, _, rule in sorted(ranked, key=lambda row: (-row[0], row[1]))[:limit]]

    def calculation_sources(self, profile):
        ids = ["expense", "personal", "brackets"]
        if profile.life_premium or profile.health_premium:
            ids.extend(("life", "health"))
        if profile.receipt_general or profile.receipt_special:
            ids.extend(("receipt-period", "receipt-cap"))
        if profile.withheld is not None:
            ids.append("withholding")
        return [self.rules[key] for key in ids]
