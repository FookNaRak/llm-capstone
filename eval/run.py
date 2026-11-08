"""Run the checked-in gold cases against the same search and rules as the app."""

import argparse
import json
from pathlib import Path
from statistics import mean

from app.agent import ProxyConfigurationError, run_agent
from app.catalog import Catalog
from app.checker import check_compatibility


CASES_PATH = Path(__file__).with_name("gold.json")
K = 3


def retrieval_scores(rows, mode):
    """Macro-average document Recall@3 and reciprocal rank, with unjudged cases omitted."""
    judged = [row for row in rows if row["relevant"]]
    recalls = []
    reciprocal_ranks = []
    for row in judged:
        relevant = set(row["relevant"])
        retrieved = row[mode]
        recalls.append(len(relevant.intersection(retrieved)) / len(relevant))
        first_hit = next((rank for rank, doc in enumerate(retrieved, 1) if doc in relevant), None)
        reciprocal_ranks.append(1 / first_hit if first_hit else 0.0)
    return {
        "cases": len(judged),
        "recall_at_3": round(mean(recalls), 4),
        "mrr_at_3": round(mean(reciprocal_ranks), 4),
    }


def run(catalog, cases, live=False):
    rows = []
    for case in cases:
        row = {"id": case["id"], "query": case["query"], "relevant": case["relevant"]}
        for mode in ("keyword", "hybrid"):
            row[mode] = [doc["id"] for doc in catalog.search(case["query"], k=K, mode=mode)]
        if "check" in case:
            row["expected_status"] = case["status"]
            row["rule_status"] = check_compatibility(catalog, **case["check"])["status"]
            if live:
                response = run_agent(catalog, case["query"])
                row["live_status"] = (response["result"] or {}).get("status")
                row["live_tools"] = [event.get("name") for event in response["trace"]]
        rows.append(row)

    checked = [row for row in rows if "expected_status" in row]
    scores = {mode: retrieval_scores(rows, mode) for mode in ("keyword", "hybrid")}
    for status_key in ("rule_status", "live_status") if live else ("rule_status",):
        matches = sum(row[status_key] == row["expected_status"] for row in checked)
        scores[status_key] = {"correct": matches, "cases": len(checked), "accuracy": round(matches / len(checked), 4)}
    return {"scores": scores, "cases": rows}


def print_summary(report):
    scores = report["scores"]
    print("Search                Cases  Recall@3  MRR@3")
    for mode in ("keyword", "hybrid"):
        result = scores[mode]
        print(f"{mode:<20} {result['cases']:>5}  {result['recall_at_3']:>8.4f}  {result['mrr_at_3']:>5.4f}")

    for key, name in (("rule_status", "Direct rule checker"), ("live_status", "Live agent")):
        if key in scores:
            result = scores[key]
            print(f"{name} status accuracy: {result['correct']}/{result['cases']} ({result['accuracy']:.1%})")

    for row in report["cases"]:
        missing = sorted(set(row["relevant"]) - set(row["hybrid"]))
        if missing:
            print(f"{row['id']} hybrid retrieval missed: {', '.join(missing)}")
        for key in ("rule_status", "live_status"):
            if key in row and row[key] != row["expected_status"]:
                print(f"{row['id']} {key}: expected {row['expected_status']}, got {row[key]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also grade the configured class-proxy agent's compatibility verdicts")
    parser.add_argument("--output", type=Path, help="Write per-case results and aggregate metrics as JSON")
    args = parser.parse_args()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    try:
        report = run(Catalog(), cases, live=args.live)
    except ProxyConfigurationError as error:
        parser.exit(2, f"Live evaluation needs class proxy credentials. {error}\n")
    print_summary(report)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
