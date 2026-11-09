"""Reproduce the tax benchmark. Add --live to grade the configured model."""

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

from tax_app.proxy import MODEL, ProxyConfigurationError, _proxy_client
from tax_app.agent import ask
from tax_app.calculator import TaxInput, calculate_tax
from tax_app.retrieval import TaxRules


def evaluate(rules, cases):
    results = {}
    for mode in ("keyword", "hybrid"):
        matches = []
        for case in cases["rules"]:
            hits = [rule["id"] for rule in rules.search(case["query"], mode)]
            relevant = set(case["ids"])
            matches.append({"query": case["query"], "expected": case["ids"], "hits": hits,
                            "recall": len(relevant.intersection(hits)) / len(relevant)})
        results[mode] = {"recall_at_3": sum(case["recall"] for case in matches) / len(matches),
                         "cases": matches}
    checks = []
    for case in cases["calculations"]:
        actual = calculate_tax(TaxInput(tax_year=2568, **case["input"]))
        expected = {key: value for key, value in case.items() if key != "input"}
        correct = all(Decimal(actual[key]) == Decimal(value) for key, value in expected.items()
                      if key != "allowed")
        correct &= all(Decimal(actual["allowed"][key]) == Decimal(value)
                       for key, value in expected.get("allowed", {}).items())
        checks.append({"input": case["input"], "expected": expected, "actual": actual,
                       "correct": correct})
    results["calculator"] = {"correct": sum(case["correct"] for case in checks), "cases": checks}
    return results


def evaluate_live(rules, cases):
    client = _proxy_client()
    labels = {
        "annual_income": "gross annual employment income including bonus",
        "life_premium": "confirmed eligible own life insurance premium",
        "health_premium": "confirmed eligible own health insurance premium",
        "receipt_general": "confirmed eligible ordinary Easy E-Receipt expenses",
        "receipt_special": "confirmed eligible special-group Easy E-Receipt expenses",
        "withheld": "tax withheld",
    }
    records = []
    for case in cases["calculations"]:
        facts = ", ".join(f"{labels[key]} {value} baht" for key, value in case["input"].items())
        prompt = ("For Thai tax year 2568, I file individually, have employment income only, "
                  "and have no special exemptions. I have " + facts +
                  ". Other optional deductions are zero. Return the final tax before withholding "
                  "as TAX=<number in baht>. Keep the visible answer to one line.")
        row = {"input": case["input"], "expected": case["tax"]}
        try:
            response = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}],
                temperature=0, max_tokens=1800,
            )
            row["baseline_finish_reason"] = response.choices[0].finish_reason
            row["baseline_text"] = response.choices[0].message.content or ""
            match = re.search(r"TAX\s*=\s*([0-9,]+(?:\.[0-9]+)?)",
                              row["baseline_text"], re.I)
            row["baseline"] = match[1].replace(",", "") if match else None
        except Exception as error:
            row["baseline_error"] = type(error).__name__
        try:
            response = ask(rules, prompt, client=client)
            row["agent"] = (response["result"] or {}).get("tax")
        except Exception as error:
            row["agent_error"] = type(error).__name__
        records.append(row)
    return {
        method: sum(row.get(method) is not None and Decimal(row[method]) == Decimal(row["expected"])
                    for row in records)
        for method in ("baseline", "agent")
    } | {"cases": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("gold.json").read_text(encoding="utf-8"))
    rules = TaxRules()
    results = evaluate(rules, cases)
    for mode in ("keyword", "hybrid"):
        print(f"{mode}: Recall@3 = {results[mode]['recall_at_3']:.4f}")
    print(f"Direct calculator: {results['calculator']['correct']}/{len(cases['calculations'])}")
    if args.live:
        try:
            results["live"] = evaluate_live(rules, cases)
        except ProxyConfigurationError:
            parser.exit(2, "Configure the course proxy in .env first.\n")
        print(f"Live model-only: {results['live']['baseline']}/{len(cases['calculations'])}")
        print(f"Live agent: {results['live']['agent']}/{len(cases['calculations'])}")
    if args.output:
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")


if __name__ == "__main__":
    main()
