from __future__ import annotations

from collections import Counter
from typing import Any

DEFAULT_RULE3_TRACE_TOP_N = 3
RULE3_TRACE_SUMMARY_VERSION = "rule3_trace_summary/v1"


def _normalize_atom_list(values: Any) -> list[int]:
    if not isinstance(values, list | tuple):
        return []
    atoms: list[int] = []
    for value in values:
        try:
            atoms.append(int(value))
        except (TypeError, ValueError):
            continue
    return atoms


def _normalize_candidate_rows(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in values:
        if not isinstance(raw, dict):
            continue
        atom_index = raw.get("atom_index")
        try:
            normalized_atom_index = int(atom_index)
        except (TypeError, ValueError):
            continue
        rows.append({
            "atom_index": normalized_atom_index,
            "source": str(raw.get("source", "unknown")),
        })
    return rows


def _selected_reason_for_source(source: str) -> str:
    if source == "struct_conn":
        return "selected_by_struct_conn_priority"
    if source == "smarts_union":
        return "selected_by_smarts_union_order"
    if source == "near_band":
        return "selected_by_near_band_order"
    return "selected_by_unknown_source_order"


def _source_ordering_label(ordering_sources: list[str]) -> str:
    return ">".join(ordering_sources) if ordering_sources else "none"


def summarize_proposal_trace(
    trace: dict[str, Any] | None,
    *,
    molecule_id: str | None = None,
    target_id: str | None = None,
    top_n_limit: int = DEFAULT_RULE3_TRACE_TOP_N,
) -> dict[str, Any]:
    payload = trace if isinstance(trace, dict) else {}
    ordered_atoms = _normalize_atom_list(payload.get("anchor_candidate_atoms"))
    candidate_rows = _normalize_candidate_rows(payload.get("anchor_candidate_sources"))
    candidate_sources_by_atom: dict[int, list[str]] = {}
    source_count_by_type: Counter[str] = Counter()
    for row in candidate_rows:
        atom_index = int(row["atom_index"])
        source = str(row["source"])
        candidate_sources_by_atom.setdefault(atom_index, []).append(source)
        source_count_by_type[source] += 1

    seen_atoms: set[int] = set()
    selected_count = 0
    proposal_handling_trace: list[dict[str, Any]] = []
    top_n_proposals: list[dict[str, Any]] = []
    proposal_handling_counts: Counter[str] = Counter()
    ordering_sources: list[str] = []

    for ordering_index, atom_index in enumerate(ordered_atoms):
        available_sources = list(candidate_sources_by_atom.get(atom_index, []))
        source = available_sources[0] if available_sources else "unknown"
        ordering_sources.append(source)
        if atom_index in seen_atoms:
            handling_status = "pruned_duplicate_atom"
            handling_reason = "duplicate_atom_after_selection"
        elif selected_count < top_n_limit:
            handling_status = "selected_top_n"
            handling_reason = _selected_reason_for_source(source)
            selected_count += 1
            seen_atoms.add(atom_index)
        else:
            handling_status = "exhausted_top_n_window"
            handling_reason = "top_n_window_exhausted"
            seen_atoms.add(atom_index)

        item = {
            "ordering_index": ordering_index,
            "atom_index": atom_index,
            "source": source,
            "available_sources": available_sources,
            "handling_status": handling_status,
            "handling_reason": handling_reason,
        }
        proposal_handling_trace.append(item)
        proposal_handling_counts[handling_status] += 1
        if handling_status == "selected_top_n":
            top_n_proposals.append(item)

    if not proposal_handling_trace:
        proposal_handling_counts["skip_no_candidates"] += 1

    return {
        "molecule_id": molecule_id,
        "target_id": target_id,
        "candidate_order_hash": payload.get("candidate_order_hash"),
        "proposal_policy_version": payload.get("proposal_policy_version"),
        "semantic_mode": payload.get("semantic_mode"),
        "struct_conn_status": payload.get("struct_conn_status"),
        "near_band_triggered": bool(payload.get("near_band_triggered", False)),
        "candidate_count": len(ordered_atoms),
        "unique_candidate_count": len(set(ordered_atoms)),
        "top_n_limit": int(top_n_limit),
        "ordering_sources": ordering_sources,
        "ordering_label": _source_ordering_label(ordering_sources),
        "source_count_by_type": dict(sorted(source_count_by_type.items())),
        "proposal_handling_counts": dict(sorted(proposal_handling_counts.items())),
        "top_n_proposals": top_n_proposals,
        "proposal_handling_trace": proposal_handling_trace,
    }


def build_rule3_trace_summary(
    evidence_rows: list[dict[str, Any]],
    *,
    top_n_limit: int = DEFAULT_RULE3_TRACE_TOP_N,
) -> dict[str, Any]:
    ordering_distribution: Counter[str] = Counter()
    candidate_order_hash_distribution: Counter[str] = Counter()
    proposal_handling_totals: Counter[str] = Counter()
    semantic_mode_counts: Counter[str] = Counter()
    proposal_policy_version_counts: Counter[str] = Counter()
    source_presence_counts: Counter[str] = Counter()
    compound_summaries: list[dict[str, Any]] = []

    for row in evidence_rows:
        trace_summary = summarize_proposal_trace(
            row.get("proposal_trace_json"),
            molecule_id=None if row.get("molecule_id") is None else str(row.get("molecule_id")),
            target_id=None if row.get("target_id") is None else str(row.get("target_id")),
            top_n_limit=top_n_limit,
        )
        compound_summaries.append(trace_summary)
        ordering_distribution[trace_summary["ordering_label"]] += 1
        candidate_order_hash_distribution[str(trace_summary.get("candidate_order_hash") or "missing")] += 1
        semantic_mode_counts[str(trace_summary.get("semantic_mode") or "missing")] += 1
        proposal_policy_version_counts[str(trace_summary.get("proposal_policy_version") or "missing")] += 1
        for status, count in trace_summary["proposal_handling_counts"].items():
            proposal_handling_totals[str(status)] += int(count)
        for source in trace_summary["source_count_by_type"]:
            source_presence_counts[str(source)] += 1

    return {
        "summary_version": RULE3_TRACE_SUMMARY_VERSION,
        "top_n_limit": int(top_n_limit),
        "record_count": len(compound_summaries),
        "run_summary": {
            "ordering_distribution": [
                {"ordering_label": label, "count": count}
                for label, count in sorted(ordering_distribution.items(), key=lambda item: (-item[1], item[0]))
            ],
            "candidate_order_hash_distribution": [
                {"candidate_order_hash": key, "count": count}
                for key, count in sorted(candidate_order_hash_distribution.items(), key=lambda item: (-item[1], item[0]))
            ],
            "proposal_handling_totals": dict(sorted(proposal_handling_totals.items())),
            "semantic_mode_counts": dict(sorted(semantic_mode_counts.items())),
            "proposal_policy_version_counts": dict(sorted(proposal_policy_version_counts.items())),
            "source_presence_counts": dict(sorted(source_presence_counts.items())),
        },
        "compound_summaries": compound_summaries,
    }


def format_rule3_run_summary(summary: dict[str, Any]) -> str:
    run_summary = summary.get("run_summary")
    if not isinstance(run_summary, dict):
        return "trace-summary=unavailable"

    ordering_distribution = run_summary.get("ordering_distribution")
    if not isinstance(ordering_distribution, list):
        ordering_distribution = []
    handling_totals = run_summary.get("proposal_handling_totals")
    if not isinstance(handling_totals, dict):
        handling_totals = {}

    ordering_preview = ",".join(
        f"{str(item.get('ordering_label'))}:{int(item.get('count', 0))}"
        for item in ordering_distribution[:3]
        if isinstance(item, dict)
    ) or "none"
    handling_preview = ",".join(
        f"{str(status)}:{int(count)}"
        for status, count in sorted(handling_totals.items())
    ) or "none"
    return (
        f"records={int(summary.get('record_count', 0))} "
        f"top-n={int(summary.get('top_n_limit', DEFAULT_RULE3_TRACE_TOP_N))} "
        f"orderings={ordering_preview} "
        f"handling={handling_preview}"
    )
