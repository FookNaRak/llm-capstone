"""Build a searchable index over the curated manufacturer catalog."""

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"
TOKEN = re.compile(r"[a-z0-9]+|[\u0e00-\u0e7f]+|[^\W\d_]+")
ASCII_MODEL = re.compile(r"[a-z0-9]+\Z")
SUPPORT_QUERY = re.compile(r"\bbios\b|\bfirmware\b|\bsupport list\b|ไบออส|เฟิร์มแวร์")
SPEC_QUERY = re.compile(r"\b(ddr[45]?|socket|memory|ram|chipset)\b|แรม|ซ็อกเก็ต")


def tokens(value):
    return TOKEN.findall(unicodedata.normalize("NFKC", value).casefold())


def normalized_name(value):
    return "".join(tokens(value))


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


class Catalog:
    """Keep part resolution separate from fuzzy evidence retrieval."""

    def __init__(self, path=CATALOG_PATH):
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        self.parts = {}
        self._names = defaultdict(set)
        self._documents = []
        self._by_part = defaultdict(list)
        for group, kind in (("boards", "board"), ("cpus", "cpu"), ("memory", "memory")):
            for entry in data[group]:
                part = dict(entry, kind=kind)
                part_id = part["id"]
                if part_id in self.parts:
                    raise ValueError(f"Duplicate catalog part ID: {part_id}")
                self.parts[part_id] = part
                for name in (part_id, part["name"], *part.get("aliases", [])):
                    self._names[normalized_name(name)].add(part_id)

        for part in self.parts.values():
            self._add_documents(part)

        # Keep the baseline over the same documents as the hybrid retriever.
        text_rows = [f"{doc['title']} {doc['text']}" for doc in self._documents]
        self._word_counts = [Counter(tokens(row)) for row in text_rows]
        self._lengths = [sum(row.values()) for row in self._word_counts]
        self._avg_length = sum(self._lengths) / max(1, len(self._lengths))
        self._word_df = Counter(word for row in self._word_counts for word in row)

        # Include identifier aliases in the hybrid index to handle variant spellings.
        vector_rows = [
            ngrams(" ".join((row, *self.parts[doc["part_id"]].get("aliases", []))))
            for row, doc in zip(text_rows, self._documents)
        ]
        self._feature_df = Counter(feature for row in vector_rows for feature in row)
        self._vectors = [self._unit_vector(row) for row in vector_rows]
        self._longest_alias = max(map(len, self._names), default=0)

    def _add(self, part, document_id, title, text, url):
        document = {
            "id": document_id,
            "part_id": part["id"],
            "kind": part["kind"],
            "title": title,
            "text": text,
            "url": url,
        }
        self._documents.append(document)
        self._by_part[part["id"]].append(document)

    def _add_documents(self, part):
        name = part["name"]
        kind = part["kind"]
        if kind == "board":
            specs = f"Motherboard CPU socket {part['socket']}. Memory type {part['ddr']}."
        elif kind == "cpu":
            specs = f"Processor CPU socket {part['socket']}."
        else:
            specs = f"Memory RAM type {part['ddr']}."
        self._add(part, part["id"], name, specs, part["source_url"])

        if kind == "board" and part.get("support_url"):
            lines = []
            for cpu_id, minimum_bios in part["cpu_support"].items():
                cpu = self.parts[cpu_id]["name"]
                bios = "all listed BIOS versions" if minimum_bios is None else f"BIOS {minimum_bios} or newer"
                lines.append(f"{cpu}: {bios}.")
            summary = "CPU Support List (curated subset). " + " ".join(lines)
            self._add(part, f"support:{part['id']}", f"{name} CPU Support", summary, part["support_url"])

    def _unit_vector(self, counts):
        size = len(self._documents)
        vector = {
            feature: (1 + math.log(count)) * (1 + math.log((size + 1) / (self._feature_df[feature] + 1)))
            for feature, count in counts.items()
            if feature in self._feature_df
        }
        magnitude = math.sqrt(sum(value * value for value in vector.values()))
        return {key: value / magnitude for key, value in vector.items()}

    def _bm25(self, query_words, index):
        word_counts = self._word_counts[index]
        length_factor = 1.2 * (0.25 + 0.75 * self._lengths[index] / self._avg_length)
        score = 0.0
        for word in sorted(query_words & word_counts.keys()):
            df = self._word_df[word]
            weight = math.log1p((len(self._documents) - df + 0.5) / (df + 0.5))
            frequency = word_counts[word]
            score += weight * frequency * 2.2 / (frequency + length_factor)
        return score

    def _mentioned_parts(self, query_words):
        matches = []
        for start, word in enumerate(query_words):
            if not ASCII_MODEL.fullmatch(word):
                continue
            name = ""
            for end in range(start, len(query_words)):
                word = query_words[end]
                if not ASCII_MODEL.fullmatch(word):
                    break
                name += word
                if len(name) > self._longest_alias:
                    break
                if name in self._names:
                    matches.append((start, end, self._names[name]))
        return {
            part_id
            for start, end, part_ids in matches
            if not any(
                other_start <= start and end <= other_end and (start, end) != (other_start, other_end)
                for other_start, other_end, _ in matches
            )
            for part_id in part_ids
        }

    def resolve(self, value, kind):
        """Return all exact identifier/alias matches, or an empty list."""
        # IDs supplied by a caller are already canonical. Ambiguous human aliases
        # still return all matches for the agent to clarify.
        direct = self.parts.get(value.strip().casefold())
        if direct and direct["kind"] == kind:
            return [direct]
        matches = self._names.get(normalized_name(value), ())
        return [self.parts[key] for key in sorted(matches) if self.parts[key]["kind"] == kind]

    def mentioned_parts(self, query):
        """Return IDs identified by explicit catalog names or curated aliases."""
        return self._mentioned_parts(tokens(query))

    def sources_for(self, part_id):
        """Return source documents in spec-first order for known part IDs."""
        return [dict(doc) for doc in self._by_part.get(part_id, ())]

    def search(self, query, k=5, mode="hybrid", kind=None):
        """Return cited BM25 or hybrid results ranked by decreasing score."""
        if mode not in {"keyword", "hybrid"}:
            raise ValueError("Search mode must be 'keyword' or 'hybrid'.")
        if k <= 0:
            return []
        query_words = tokens(query)
        terms = set(query_words)
        candidates = [
            (index, doc, self._bm25(terms, index))
            for index, doc in enumerate(self._documents)
            if kind is None or doc["kind"] == kind
        ]
        if mode == "keyword":
            return self._rank((doc, score) for _, doc, score in candidates)[:k]

        query_vector = self._unit_vector(ngrams(query))
        best_bm25 = max((score for _, _, score in candidates), default=0) or 1.0
        mentions = self._mentioned_parts(query_words)
        asks_support = bool(SUPPORT_QUERY.search(query.casefold()))
        asks_specs = bool(SPEC_QUERY.search(query.casefold()))
        ranked = []
        for index, doc, bm25 in candidates:
            similarity = sum(value * self._vectors[index].get(key, 0) for key, value in query_vector.items())
            score = 0.35 * bm25 / best_bm25 + 0.65 * similarity
            if doc["part_id"] in mentions:
                score += 0.75
                if doc["kind"] == "board":
                    is_support = doc["id"].startswith("support:")
                    if (asks_support and is_support) or (asks_specs and not is_support):
                        score += 0.3
            ranked.append((doc, score))
        return self._rank(ranked)[:k]

    @staticmethod
    def _rank(scored):
        ordered = sorted(scored, key=lambda item: (-item[1], item[0]["id"]))
        return [dict(doc, score=round(score, 6)) for doc, score in ordered if score > 0]
