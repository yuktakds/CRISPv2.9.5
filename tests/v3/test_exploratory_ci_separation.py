from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from crisp.v3.ci_guards import (
    EXPLORATORY_JOB_NAME_PREFIX,
    REQUIRED_WORKFLOW_PATH,
    audit_exploratory_ci_separation,
    discover_workflow_paths,
    load_repo_workflows,
)


def test_repo_workflows_preserve_exploratory_v3_ci_separation() -> None:
    findings = audit_exploratory_ci_separation(workflows=load_repo_workflows())

    assert findings == ()


def test_ci_separation_rejects_required_job_body_that_references_v3_paths() -> None:
    findings = audit_exploratory_ci_separation(
        workflows={
            REQUIRED_WORKFLOW_PATH: {
                "name": "v2.9.5 Required Matrix",
                "jobs": {
                    "v3-report-guards": {
                        "name": "required / replay-inventory-crosscheck",
                        "steps": [
                            {"run": "uv run pytest -q tests/v3/test_report_guards.py"},
                        ],
                    },
                    "v3-sidecar-determinism": {
                        "name": "required / v3-sidecar-determinism",
                        "steps": [
                            {"run": "uv run pytest -q tests/v3/test_sidecar_invariants.py"},
                        ],
                    },
                },
            }
        }
    )

    assert (
        ".github/workflows/v29-required-matrix.yml:v3-report-guards required workflow job body references v3 paths: tests/v3/"
        in findings
    )


def test_ci_separation_rejects_non_exploratory_job_label_for_v3_commands() -> None:
    findings = audit_exploratory_ci_separation(
        workflows={
            REQUIRED_WORKFLOW_PATH: {
                "name": "v2.9.5 Required Matrix",
                "jobs": {
                    "v3-sidecar-determinism": {
                        "name": "required / v3-sidecar-determinism",
                        "steps": [{"run": "uv run pytest -q tests/v3/test_sidecar_invariants.py"}],
                    }
                },
            },
            ".github/workflows/v3-reporting-exploratory.yml": {
                "name": "v3 Reporting Exploratory",
                "jobs": {
                    "operator-safety": {
                        "name": "reporting checks",
                        "steps": [{"run": "uv run pytest -q tests/v3/test_report_guards.py"}],
                    }
                },
            },
        }
    )

    assert (
        ".github/workflows/v3-reporting-exploratory.yml:operator-safety references v3 paths without exploratory job label: tests/v3/"
        in findings
    )


def test_ci_separation_discovers_new_workflows_from_repo_enumeration(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "v29-required-matrix.yml").write_text(
        dedent(
            """
            name: v2.9.5 Required Matrix
            jobs:
              v3-sidecar-determinism:
                name: required / v3-sidecar-determinism
                steps:
                  - run: uv run pytest -q tests/v3/test_sidecar_invariants.py
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (workflow_dir / "v3-new-exploratory.yml").write_text(
        dedent(
            f"""
            name: v3 New Exploratory
            jobs:
              new-job:
                name: {EXPLORATORY_JOB_NAME_PREFIX}v3-new-job
                steps:
                  - run: uv run pytest -q tests/v3/test_report_guards.py
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    workflow_paths = discover_workflow_paths(repo_root=tmp_path)
    findings = audit_exploratory_ci_separation(
        workflows=load_repo_workflows(repo_root=tmp_path)
    )

    assert workflow_paths == (
        ".github/workflows/v29-required-matrix.yml",
        ".github/workflows/v3-new-exploratory.yml",
    )
    assert findings == ()
