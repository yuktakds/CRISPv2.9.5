from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

EXPLORATORY_JOB_NAME_PREFIX = "exploratory / "
ALLOWED_REQUIRED_V3_JOB_NAMES = ("required / v3-sidecar-determinism",)
EXPLORATORY_WORKFLOW_PATHS = (
    ".github/workflows/v3-readiness-exploratory.yml",
    ".github/workflows/v3-bridge-comparator-exploratory.yml",
    ".github/workflows/v3-cap-sidecar-exploratory.yml",
    ".github/workflows/v3-catalytic-sidecar-exploratory.yml",
)
REQUIRED_WORKFLOW_PATH = ".github/workflows/v29-required-matrix.yml"
REQUIRED_PROMOTION_BLOCKED_REASON = (
    "path_only_partial comparator is not fully comparable; v3 lanes remain exploratory"
)


def build_ci_separation_payload(*, v3_lanes_required: bool) -> dict[str, Any]:
    return {
        "v3_lanes_required": v3_lanes_required,
        "required_promotion_blocked": not v3_lanes_required,
        "required_promotion_blocked_reason": REQUIRED_PROMOTION_BLOCKED_REASON,
        "allowed_required_v3_job_names": list(ALLOWED_REQUIRED_V3_JOB_NAMES),
        "exploratory_job_name_prefix": EXPLORATORY_JOB_NAME_PREFIX,
        "exploratory_workflow_paths": list(EXPLORATORY_WORKFLOW_PATHS),
        "required_workflow_path": REQUIRED_WORKFLOW_PATH,
        "rc2_frozen_suite_untouched": True,
    }


def load_workflow_yaml(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {} if payload is None else dict(payload)


def audit_exploratory_ci_separation(
    *,
    required_workflow: Mapping[str, Any],
    exploratory_workflows: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    findings: list[str] = []
    required_jobs = required_workflow.get("jobs", {})
    required_job_names = {
        str(job_payload.get("name", ""))
        for job_payload in required_jobs.values()
        if isinstance(job_payload, Mapping)
    }
    for required_name in ALLOWED_REQUIRED_V3_JOB_NAMES:
        if required_name not in required_job_names:
            findings.append(f"required v3 boundary job missing: {required_name}")
    for job_name in sorted(required_job_names):
        if "/ v3-" in job_name and job_name not in ALLOWED_REQUIRED_V3_JOB_NAMES:
            findings.append(f"unexpected required v3 job: {job_name}")

    for workflow_path, workflow_payload in exploratory_workflows.items():
        workflow_name = str(workflow_payload.get("name", ""))
        if "Exploratory" not in workflow_name:
            findings.append(f"{workflow_path} workflow name must carry Exploratory marker")
        jobs = workflow_payload.get("jobs", {})
        if not isinstance(jobs, Mapping) or not jobs:
            findings.append(f"{workflow_path} has no jobs")
            continue
        for job_id, job_payload in jobs.items():
            if not isinstance(job_payload, Mapping):
                findings.append(f"{workflow_path}:{job_id} payload is not a mapping")
                continue
            job_name = str(job_payload.get("name", ""))
            if not job_name.startswith(EXPLORATORY_JOB_NAME_PREFIX):
                findings.append(f"{workflow_path}:{job_id} is not exploratory")
            if job_name in required_job_names:
                findings.append(f"{workflow_path}:{job_id} duplicates required job name")
            if job_name.startswith("required / "):
                findings.append(f"{workflow_path}:{job_id} must not be required")
    return tuple(findings)
