"""Deterministic compatibility checks for the curated catalog."""

import re


def check_compatibility(catalog, motherboard=None, cpu=None, memory=None, bios=None):
    checks = []
    parts = {}
    citations = {}

    def add(rule, status, detail, **evidence):
        checks.append(dict(rule=rule, status=status, detail=detail, **evidence))

    for kind, value in (("board", motherboard), ("cpu", cpu), ("memory", memory)):
        if not value:
            continue
        matches = catalog.resolve(value, kind)
        if len(matches) == 1:
            part = matches[0]
            parts[kind] = part
            for source in catalog.sources_for(part["id"]):
                citations[source["id"]] = source
        else:
            add("identify_" + kind, "unknown", "Ambiguous name." if matches else
                "Part not found in the catalog.", input=value,
                candidates=[part["name"] for part in matches])

    board = parts.get("board")
    processor = parts.get("cpu")
    ram = parts.get("memory")
    if not motherboard or not (cpu or memory):
        add("required_parts", "unknown", "Specify a motherboard and a CPU or memory.")

    if board and processor:
        socket_match = board["socket"] == processor["socket"]
        add("socket", "compatible" if socket_match else "incompatible",
            f"Motherboard socket: {board['socket']}. CPU socket: {processor['socket']}.")
        if socket_match:
            support = board["cpu_support"]
            cpu_id = processor["id"]
            if cpu_id not in support:
                add("cpu_support", "unknown",
                    "No verified entry for this pairing in the catalog snapshot.")
            else:
                minimum = support[cpu_id]
                if minimum is None:
                    add("cpu_support", "compatible",
                        "The manufacturer lists this CPU for all BIOS versions.")
                elif bios is None or not re.fullmatch(r"[0-9]{1,12}", bios.strip()):
                    add("bios", "conditional", f"Verify BIOS version {minimum} or newer.",
                        minimum_bios=minimum)
                elif int(bios) < int(minimum):
                    add("bios", "conditional",
                        f"BIOS {bios} is below the listed minimum {minimum}. Update required.",
                        minimum_bios=minimum)
                else:
                    add("bios", "compatible",
                        f"BIOS {bios} meets the listed minimum {minimum}.",
                        minimum_bios=minimum)

    if board and ram:
        ddr_match = board["ddr"] == ram["ddr"]
        add("memory_generation", "compatible" if ddr_match else "incompatible",
            f"Motherboard: {board['ddr']}. Memory kit: {ram['ddr']}. "
            "This check covers DDR generation only.")

    states = {check["status"] for check in checks}
    status = next((state for state in ("incompatible", "unknown", "conditional")
                   if state in states), "compatible" if checks else "unknown")
    return {
        "status": status,
        "parts": {kind: part["name"] for kind, part in parts.items()},
        "checks": checks,
        "citations": list(citations.values()),
    }
