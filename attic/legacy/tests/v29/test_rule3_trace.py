from __future__ import annotations

from crisp.v29.rule3_trace import build_rule3_trace_summary, summarize_proposal_trace


def test_summarize_proposal_trace_distinguishes_selected_pruned_and_exhausted() -> None:
    summary = summarize_proposal_trace(
        {
            "anchor_candidate_atoms": [5, 7, 5, 9],
            "anchor_candidate_sources": [
                {"atom_index": 5, "source": "struct_conn"},
                {"atom_index": 7, "source": "smarts_union"},
                {"atom_index": 5, "source": "near_band"},
                {"atom_index": 9, "source": "near_band"},
            ],
            "candidate_order_hash": "sha256:h1",
            "proposal_policy_version": "v29.trace-only.noop",
            "semantic_mode": "trace-only-noop",
            "struct_conn_status": "present",
            "near_band_triggered": True,
        },
        molecule_id="mol-1",
        top_n_limit=2,
    )

    assert summary["ordering_label"] == "struct_conn>smarts_union>struct_conn>near_band"
    assert summary["proposal_handling_counts"] == {
        "exhausted_top_n_window": 1,
        "pruned_duplicate_atom": 1,
        "selected_top_n": 2,
    }
    assert [item["handling_status"] for item in summary["proposal_handling_trace"]] == [
        "selected_top_n",
        "selected_top_n",
        "pruned_duplicate_atom",
        "exhausted_top_n_window",
    ]
    assert [item["handling_reason"] for item in summary["top_n_proposals"]] == [
        "selected_by_struct_conn_priority",
        "selected_by_smarts_union_order",
    ]


def test_build_rule3_trace_summary_reports_run_level_ordering_distribution() -> None:
    payload = build_rule3_trace_summary(
        [
            {
                "molecule_id": "mol-1",
                "target_id": "tgt",
                "proposal_trace_json": {
                    "anchor_candidate_atoms": [5, 7, 5, 9],
                    "anchor_candidate_sources": [
                        {"atom_index": 5, "source": "struct_conn"},
                        {"atom_index": 7, "source": "smarts_union"},
                        {"atom_index": 5, "source": "near_band"},
                        {"atom_index": 9, "source": "near_band"},
                    ],
                    "candidate_order_hash": "sha256:h1",
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "struct_conn_status": "present",
                    "near_band_triggered": True,
                },
            },
            {
                "molecule_id": "mol-2",
                "target_id": "tgt",
                "proposal_trace_json": {
                    "anchor_candidate_atoms": [],
                    "anchor_candidate_sources": [],
                    "candidate_order_hash": "sha256:h2",
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "struct_conn_status": "absent",
                    "near_band_triggered": False,
                },
            },
        ],
        top_n_limit=2,
    )

    assert payload["summary_version"] == "rule3_trace_summary/v1"
    assert payload["record_count"] == 2
    assert payload["run_summary"]["ordering_distribution"] == [
        {"ordering_label": "none", "count": 1},
        {"ordering_label": "struct_conn>smarts_union>struct_conn>near_band", "count": 1},
    ]
    assert payload["run_summary"]["proposal_handling_totals"] == {
        "exhausted_top_n_window": 1,
        "pruned_duplicate_atom": 1,
        "selected_top_n": 2,
        "skip_no_candidates": 1,
    }
    assert all("core_verdict" not in summary for summary in payload["compound_summaries"])
