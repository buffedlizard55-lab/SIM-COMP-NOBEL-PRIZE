"""Family-level research analysis with predeclared verdict rules.

Everything here is computed from the simulated ledgers of one build. Nothing is
a Kalshi fill and nothing is a forecast. The rules are fixed in code and printed
on the site so that a verdict can be re-derived by hand from research.json.

Verdict per (family, settled universe)
--------------------------------------
REFERENCE             the family is a null, control, or placebo; it is a yardstick.
NOT TESTED            no variant of the family filled a single order.
INCONCLUSIVE-LOW-POWER the family's fills touched fewer than MIN_EVENTS settled
                      events, or those events contain no YES outcome, or fewer
                      than MIN_TRADED_VARIANTS variants of the family traded.
                      With so few independent outcomes no ranking is evidence.
SUPPORTED-ON-SNAPSHOT all of: family median ending equity > null p95; the family
                      median > its matched placebo median (when one exists); and
                      the worst leave-one-event-out family median > null median.
NOT SUPPORTED         family median ending equity <= null median.
INCONCLUSIVE          anything in between.
UNSETTLED             forward universe: open positions are marked at the closing
                      bid, no outcome exists yet, so no verdict is possible.

"Supported on snapshot" is deliberately weak language: variants inside a family
share signals and markets, so they are not independent trials; the binomial
p-value reported next to the share above the null p95 assumes independence and
therefore overstates the evidence. research.json reports how many (family,
universe) tests reached a verdict and how many would clear a 5% bar by chance (Harvey, Liu & Zhu 2016; Bailey & Lopez de Prado 2014).
"""

from __future__ import annotations

import math
from decimal import Decimal

from simcomp.research_cards import CHANNELS, card_for
from simcomp.research_sources import SOURCES, VERIFIED_ON

MIN_EVENTS = 3
MIN_TRADED_VARIANTS = 3
STARTING_CASH = 10000.0
SETTLED_UNIVERSES = ("nobel_settled", "panel_settled")

RULES = {
    "REFERENCE": "Null, control, or placebo family; used as a yardstick, not tested itself.",
    "NOT TESTED": "No variant filled an order in this universe.",
    "INCONCLUSIVE-LOW-POWER": (f"Fills touched fewer than {MIN_EVENTS} settled events, or none of those events had a YES outcome, "
                               f"or fewer than {MIN_TRADED_VARIANTS} variants of the family traded."),
    "SUPPORTED-ON-SNAPSHOT": ("Median ending equity of the variants that traded > null p95 (and > $10,000) AND > the matched "
                              "placebo's traded median (if any) AND worst leave-one-event-out median > null median."),
    "NOT SUPPORTED": "Median ending equity of the variants that traded <= null (batch-001) median.",
    "INCONCLUSIVE": "Between the two: above the null median but failing at least one support condition.",
    "UNSETTLED": "Forward universe; positions are marked at the closing bid and no outcome exists yet.",
}


def _pct(ordered, p):
    if not ordered:
        return None
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _median(values):
    return _pct(sorted(values), 0.5)


def binom_tail(k: int, n: int, p: float = 0.05) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Assumes independent variants (they are not)."""
    if n <= 0:
        return 1.0
    return float(sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1)))


def _r(x, digits=2):
    return None if x is None else round(float(x), digits)


def analyse(universe_results: dict, variants: list) -> dict:
    by_pid = {v.username: v for v in variants}
    families: dict[str, dict] = {}
    for v in variants:
        entry = families.setdefault(v.family, {"family": v.family, "batches": set(), "variants": 0})
        entry["batches"].add(v.batch)
        entry["variants"] += 1

    universes_out = {}
    for universe, result in universe_results.items():
        board = result["leaderboard"]
        eq = {row["p"]: float(row["eq"]) for row in board}
        fills = {row["p"]: int(row["n"]) for row in board}
        null_eq = sorted(eq[p] for p in eq if by_pid[p].family == "null_model")
        null = {"n": len(null_eq), "p05": _pct(null_eq, 0.05), "median": _pct(null_eq, 0.5), "p95": _pct(null_eq, 0.95)}
        outcomes = result.get("event_outcomes", {})
        ranked = sorted(eq.values(), reverse=True)
        top_decile_cut = ranked[max(len(ranked) // 10 - 1, 0)] if ranked else None
        universes_out[universe] = {
            "participants": len(board),
            "events": len(outcomes),
            "settled_events": sum(1 for o in outcomes.values() if o["settled"]),
            "events_with_yes": sum(1 for o in outcomes.values() if o["yes"]),
            "markets": sum(o["markets"] for o in outcomes.values()),
            "null": {k: _r(v) if k != "n" else v for k, v in null.items()},
            "top_decile_cut": _r(top_decile_cut),
        }
        event_pnl = result.get("event_pnl", {})
        clips = result.get("clips", {})
        by_family: dict[str, list] = {}
        for pid in eq:
            by_family.setdefault(by_pid[pid].family, []).append(pid)
        # Tests use variants that filled at least one order. A variant that never
        # trades ends at exactly $10,000, which sits above the null median only
        # because the null pays fees and spread; counting it would reward inaction.
        medians = {fam: _median([eq[p] for p in pids if fills[p] > 0]) for fam, pids in by_family.items()}
        for family, pids in by_family.items():
            card = card_for(family)
            all_values = sorted(eq[p] for p in pids)
            entered = [p for p in pids if fills[p] > 0]
            values = sorted(eq[p] for p in entered)
            median = _pct(values, 0.5)
            above = sum(1 for x in values if null["p95"] is not None and x > null["p95"])
            # Events this family's fills touched, and concentration of its P&L.
            touched: dict[str, float] = {}
            for p in pids:
                for event, pnl in event_pnl.get(p, {}).items():
                    touched[event] = touched.get(event, 0.0) + abs(float(pnl))
            total_abs = sum(touched.values())
            top_event = max(touched, key=lambda e: (touched[e], e)) if touched else None
            settled_touched = [e for e in touched if outcomes.get(e, {}).get("settled")]
            yes_touched = [e for e in settled_touched if outcomes.get(e, {}).get("yes")]
            # Worst leave-one-event-out family median.
            loo_worst, loo_event = None, None
            for event in sorted(touched):
                adjusted = sorted(eq[p] - float(event_pnl.get(p, {}).get(event, Decimal(0))) for p in entered)
                m = _pct(adjusted, 0.5)
                if loo_worst is None or m < loo_worst:
                    loo_worst, loo_event = m, event
            placebo_family = f"placebo_{family}"
            placebo_median = medians.get(placebo_family)
            n_fills = sum(fills[p] for p in pids)
            n_clips = sum(clips.get(p, 0) for p in pids)
            stats = {
                "n": len(all_values),
                "entered": len(entered),
                "median_eq": _r(median),
                "median_eq_all_variants": _r(_pct(all_values, 0.5)),
                "vs_cash": _r(median - STARTING_CASH) if median is not None else None,
                "p05_eq": _r(_pct(values, 0.05)),
                "p95_eq": _r(_pct(values, 0.95)),
                "vs_null_median": _r(median - null["median"]) if (median is not None and null["median"] is not None) else None,
                "share_above_null_p95": round(above / len(values), 4) if values else 0,
                "binom_p_indep": round(binom_tail(above, len(values)), 6),
                "p_top_decile": round(sum(1 for x in all_values if top_decile_cut is not None and x >= top_decile_cut) / len(all_values), 4),
                "placebo_family": placebo_family if placebo_median is not None else None,
                "placebo_median_eq": _r(placebo_median),
                "vs_placebo": _r(median - placebo_median) if (placebo_median is not None and median is not None) else None,
                "events_touched": len(touched),
                "settled_events_touched": len(settled_touched),
                "yes_events_touched": len(yes_touched),
                "top_event": top_event,
                "top_event_share": round(touched[top_event] / total_abs, 4) if top_event and total_abs else None,
                "loo_worst_median_eq": _r(loo_worst),
                "loo_worst_event": loo_event,
                "fills": n_fills,
                "clip_rate": round(n_clips / n_fills, 4) if n_fills else 0,
            }
            stats["verdict"], stats["why"] = _verdict(universe, card, stats, null)
            families[family].setdefault("universes", {})[universe] = stats

    out_families = []
    for family, entry in sorted(families.items(), key=lambda item: (min(item[1]["batches"]), item[0])):
        card = card_for(family)
        settled_verdicts = [entry.get("universes", {}).get(u, {}).get("verdict") for u in SETTLED_UNIVERSES]
        out_families.append({
            "family": family,
            "batches": sorted(entry["batches"]),
            "variants": entry["variants"],
            "card": card,
            "universes": entry.get("universes", {}),
            "overall": _overall(card, settled_verdicts),
            "consistency": _consistency(entry.get("universes", {})),
        })
    counts: dict[str, int] = {}
    for fam in out_families:
        counts[fam["overall"]] = counts.get(fam["overall"], 0) + 1
    tested = sum(1 for fam in out_families for u in SETTLED_UNIVERSES
                 if fam["universes"].get(u, {}).get("verdict") in ("SUPPORTED-ON-SNAPSHOT", "NOT SUPPORTED", "INCONCLUSIVE"))
    return {
        "simulated": True,
        "rules": RULES,
        "min_events": MIN_EVENTS,
        "channels": CHANNELS,
        "sources": SOURCES,
        "sources_verified_on": VERIFIED_ON,
        "universes": universes_out,
        "families": out_families,
        "overall_counts": counts,
        "multiple_testing": {
            "family_universe_tests": tested,
            "expected_false_passes_at_5pct": round(0.05 * tested, 1),
            "note": (
                "Each (family, settled universe) pair that reached a verdict is one test. At a 5% bar about "
                "this many would pass by luck alone, before accounting for correlated variants and markets."
            ),
        },
    }


def _verdict(universe: str, card: dict, s: dict, null: dict) -> tuple[str, str]:
    if universe not in SETTLED_UNIVERSES:
        return "UNSETTLED", "forward universe: marked at the closing bid, no outcome yet"
    if card["kind"] in ("null", "control", "placebo"):
        return "REFERENCE", f"{card['kind']} family"
    if s["entered"] == 0:
        return "NOT TESTED", "no fills"
    if s["entered"] < MIN_TRADED_VARIANTS:
        return "INCONCLUSIVE-LOW-POWER", (
            f"only {s['entered']} variant(s) of the family traded; need >= {MIN_TRADED_VARIANTS} for a family median"
        )
    if s["settled_events_touched"] < MIN_EVENTS or s["yes_events_touched"] == 0:
        return "INCONCLUSIVE-LOW-POWER", (
            f"fills touched {s['settled_events_touched']} settled events ({s['yes_events_touched']} with a YES outcome); "
            f"need >= {MIN_EVENTS} and >= 1"
        )
    median, p50, p95 = s["median_eq"], null["median"], null["p95"]
    if median <= p50:
        return "NOT SUPPORTED", f"median {median:.2f} <= null median {p50:.2f}"
    checks = [median > p95 and median > STARTING_CASH]
    why = [f"median {median:.2f} {'>' if median > p95 else '<='} null p95 {p95:.2f}"]
    if s["placebo_median_eq"] is not None:
        checks.append(median > s["placebo_median_eq"])
        why.append(f"placebo {s['placebo_median_eq']:.2f}")
    loo = s["loo_worst_median_eq"]
    checks.append(loo is not None and loo > p50)
    why.append(f"worst leave-one-event-out median {loo:.2f} (drop {s['loo_worst_event']})" if loo is not None else "no LOO")
    if all(checks):
        return "SUPPORTED-ON-SNAPSHOT", "; ".join(why)
    return "INCONCLUSIVE", "; ".join(why)


def _consistency(universes: dict) -> str:
    """Direction of the traded median vs the null median in each settled universe."""
    signs = []
    for u in SETTLED_UNIVERSES:
        s = universes.get(u) or {}
        if s.get("vs_null_median") is None or s.get("entered", 0) == 0:
            signs.append("n/a")
        else:
            signs.append("above" if s["vs_null_median"] > 0 else "below")
    if signs == ["above", "above"]:
        return "above null in both settled universes"
    if signs == ["below", "below"]:
        return "below null in both settled universes"
    if "n/a" in signs:
        return "only one settled universe traded"
    return "mixed direction across settled universes"


def _overall(card: dict, verdicts: list) -> str:
    if card["kind"] in ("null", "control", "placebo"):
        return "REFERENCE"
    present = [v for v in verdicts if v]
    if "SUPPORTED-ON-SNAPSHOT" in present and "NOT SUPPORTED" in present:
        return "MIXED"
    if "SUPPORTED-ON-SNAPSHOT" in present:
        return "SUPPORTED-ON-SNAPSHOT"
    if "NOT SUPPORTED" in present:
        return "NOT SUPPORTED"
    if "INCONCLUSIVE" in present:
        return "INCONCLUSIVE"
    if "INCONCLUSIVE-LOW-POWER" in present:
        return "INCONCLUSIVE-LOW-POWER"
    return "NOT TESTED"


def data_quality_flags(grouped: dict, universe_results: dict) -> list[dict]:
    """Research-relevant data limits, computed where possible, stated where not."""
    flags = [
        {"code": "close_time_excluded", "severity": "warning",
         "message": ("Settled Nobel markets carry a close_time written after the announcement (e.g. KXNOBELECON-25 "
                     "closes 2025-10-17 with sub-second precision). No strategy reads close_time; the schedule channel "
                     "uses only whole-minute event strike_date values, which Nobel events do not publish.")},
        {"code": "panel_selection_by_lifetime_volume", "severity": "warning",
         "message": ("The settled panel keeps the top 25 markets per series by lifetime volume, chosen at fetch time. "
                     "That is post-selected: a strategy cannot have known at decision time which markets would be kept.")},
        {"code": "cash_not_recycled", "severity": "info",
         "message": ("Settlement is applied after the whole decision loop, so settled cash never funds later trades "
                     "inside a run. Sizing rules can only size down; the $300 per-market cap and 500-contract clip bind.")},
    ]
    # Nobel series that trade forward but have no settled event in the snapshot.
    forward_series = sorted({m.series_ticker for m in grouped.get("nobel_forward", []) if m.series_ticker})
    settled_series = {m.series_ticker for m in grouped.get("nobel_settled", []) if m.series_ticker}
    missing = [series for series in forward_series if series not in settled_series]
    if missing:
        flags.append({"code": "nobel_subjects_without_settled_history", "severity": "warning",
                      "message": (f"{', '.join(missing)} trade in the forward universe but have no settled event in the "
                                  "snapshot, so no settled-universe result says anything about those subjects.")})
    for universe in SETTLED_UNIVERSES:
        outcomes = universe_results.get(universe, {}).get("event_outcomes", {})
        for event, o in sorted(outcomes.items()):
            if o["settled"] and o["yes"] == 0 and o["markets"] >= 3:
                flags.append({"code": "event_field_incomplete", "severity": "warning", "event_ticker": event,
                              "message": (f"{event}: {o['markets']} stored contracts all settled NO. The winning contract "
                                          "(if any) is not in the snapshot, so event-structure rules see a partial field.")})
    return flags


def render_markdown(research: dict, manifest: dict) -> str:
    """docs/RESEARCH.md, generated from research.json and the program manifest."""
    lines = [
        "# Research findings (generated)",
        "",
        "> Generated by `simcomp/analysis.py` from `data/sim/program/research.json` on "
        f"{manifest.get('generated_at', '')}. Do not edit by hand; rerun `python3 scripts/refresh.py --skip-collect`.",
        "> Every participant, trade and P&L figure here is **simulated** on stored public Kalshi candles. "
        "No figure is a Kalshi fill, a real account, or a forecast.",
        "",
        f"- Participants: **{manifest.get('participants')}** in {len(manifest.get('batches', []))} batches; "
        f"ledger rows: **{manifest.get('trade_rows_total')}**; replay of {', '.join(research.get('replay', {}).get('batches', []))}: "
        f"**{research.get('replay', {}).get('status')}**.",
        f"- Families with research cards: **{len(research['families'])}**. Sources verified on {research['sources_verified_on']}.",
        f"- Family × settled-universe tests that reached a verdict: **{research['multiple_testing']['family_universe_tests']}**; "
        f"about **{research['multiple_testing']['expected_false_passes_at_5pct']}** would pass a 5% bar by luck alone.",
        "",
        "## Verdict rules (fixed before results were read)",
        "",
    ]
    for key, text in research["rules"].items():
        lines.append(f"- **{key}** — {text}")
    lines += ["", "## Power: what each universe can and cannot show", "",
              "| Universe | Markets | Events | Settled events | Events with a YES | Null p05 / median / p95 |",
              "|---|---:|---:|---:|---:|---|"]
    for universe, u in research["universes"].items():
        n = u["null"]
        lines.append(f"| {universe} | {u['markets']} | {u['events']} | {u['settled_events']} | {u['events_with_yes']} | "
                     f"{n.get('p05')} / {n.get('median')} / {n.get('p95')} |")
    lines += ["", "Few independent outcomes means most families cannot be distinguished from luck. "
              "The Nobel settled universe has only a handful of events with a YES outcome.", "",
              "## Overall verdicts", ""]
    for key, value in sorted(research["overall_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Family table", "",
              "Median ending equity from $10,000 per participant. `vs null` is the family median minus the batch-001 null median. "
              "P(top 10%) is the share of the family's variants that finished in the top decile of that universe's board.", "",
              "| Batch | Family | Kind | Nobel settled: median (vs null) · verdict | Panel settled: median (vs null) · verdict | P(top 10%) N/P | Overall |",
              "|---|---|---|---|---|---|---|"]
    for fam in research["families"]:
        cells = []
        tops = []
        for universe in SETTLED_UNIVERSES:
            s = fam["universes"].get(universe)
            if not s:
                cells.append("—")
                tops.append("—")
                continue
            vs = s["vs_null_median"]
            cells.append(f"{s['median_eq']} ({'+' if vs is not None and vs >= 0 else ''}{vs}) · {s['verdict']}")
            tops.append(f"{s['p_top_decile']:.2f}")
        lines.append(f"| {fam['batches'][0][-3:]} | `{fam['family']}` | {fam['card']['kind']} | {cells[0]} | {cells[1]} | "
                     f"{' / '.join(tops)} | **{fam['overall']}** |")
    lines += ["", "## Research cards", "",
              "Each card was written with the rule, before its result was read. Sources are ids in "
              "`simcomp/research_sources.py`; see the Sources table below.", ""]
    for fam in research["families"]:
        card = fam["card"]
        lines += [f"### `{fam['family']}` ({', '.join(fam['batches'])}, {fam['variants']} variants)", "",
                  f"- **Question:** {card['question']}",
                  f"- **Mechanism:** {card['mechanism']}",
                  f"- **Predicts:** {card['predicts']}",
                  f"- **Falsified if:** {card['falsified_if']}",
                  f"- **Reads:** {', '.join(card['channels'])}",
                  f"- **Sources:** {', '.join(card['sources'])}",
                  f"- **Overall:** {fam['overall']}", ""]
        for universe in SETTLED_UNIVERSES:
            s = fam["universes"].get(universe)
            if s:
                lines.append(f"  - {universe}: {s['verdict']} — {s['why']}. Entered {s['entered']}/{s['n']}, "
                             f"events {s['settled_events_touched']} settled ({s['yes_events_touched']} YES), "
                             f"top event {s['top_event']} share {s['top_event_share']}, clip rate {s['clip_rate']}.")
        lines.append("")
    lines += ["## Data-quality flags", ""]
    for flag in research.get("data_quality", []):
        lines.append(f"- **{flag['code']}** ({flag['severity']}): {flag['message']}")
    lines += ["", "## Sources", "", "| id | citation | link |", "|---|---|---|"]
    for key, src in research["sources"].items():
        lines.append(f"| `{key}` | {src['citation']} | {src.get('url') or '—'} |")
    lines.append("")
    return "\n".join(lines)
