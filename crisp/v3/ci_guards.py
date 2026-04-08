from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

EXPLORATORY_JOB_NAME_PREFIX = "exploratory / "
EXPLORATORY_WORKFLOW_NAME_MARKER = "Exploratory"
ALLOWED_REQUIRED_V3_JOB_NAMES = ("required / v3-sidecar-determinism",)
REQUIRED_WORKFLOW_PATH = ".github/workflows/v29-required-matrix.yml"
REQUIRED_PROMOTION_BLOCKED_REASON = (
    "path_only_partial comparator is not fully comparable; v3 lanes remain exploratory"
)
V3_JOB_BODY_MARKERS = (
    "tests/v3/",
    "tests\\v3\\",
    "crisp/v3/",
    "crisp\\v3\\",
    "v3_sidecar",
)
REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ".github/workflows"


def _normalize_relpath(path: Path, *, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def discover_workflow_paths(*, repo_root: str | Path | None = None) -> tuple[str, ...]:
    root = REPO_ROOT if repo_root is None else Path(repo_root)
    workflow_dir = root / WORKFLOWS_DIR
    return tuple(
        sorted(
            _normalize_relpath(path, repo_root=root)
            for path in workflow_dir.glob("*.yml")
            if path.is_file()
        )
    )


def load_workflow_yaml(path: str | Path, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = REPO_ROOT if repo_root is None else Path(repo_root)
    workflow_path = Path(path)
    if not workflow_path.is_absolute():
        workflow_path = root / workflow_path
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    return {} if payload is None else dict(payload)


def load_repo_workflows(*, repo_root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    root = REPO_ROOT if repo_root is None else Path(repo_root)
    return {
        workflow_path: load_workflow_yaml(workflow_path, repo_root=root)
        for workflow_path in discover_workflow_paths(repo_root=root)
    }


def _job_name(job_id: str, job_payload: Mapping[str, Any]) -> str:
    return str(job_payload.get("name", job_id))


def _job_steps(job_payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    steps = job_payload.get("steps", ())
    if not isinstance(steps, list):
        return ()
    return tuple(step for step in steps if isinstance(step, Mapping))


def _job_body_text(job_payload: Mapping[str, Any]) -> str:
    fragments: list[str] = []
    for step in _job_steps(job_payload):
        run_text = step.get("run")
        uses_text = step.get("uses")
        working_dir = step.get("working-directory")
        if run_text:
            fragments.append(str(run_text))
        if uses_text:
            fragments.append(str(uses_text))
        if working_dir:
            fragments.append(str(working_dir))
    return "\n".join(fragments)


def _v3_job_body_markers(job_payload: Mapping[str, Any]) -> tuple[str, ...]:
    body_text = _job_body_text(job_payload)
    return tuple(marker for marker in V3_JOB_BODY_MARKERS if marker in body_text)


def classify_workflow_paths(
    workflows: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    exploratory_paths: list[str] = []
    required_paths: list[str] = []
    for workflow_path, workflow_payload in workflows.items():
        jobs = workflow_payload.get("jobs", {})
        if not isinstance(jobs, Mapping):
            continue
        job_names = [
            _job_name(job_id, job_payload)
            for job_id, job_payload in jobs.items()
            if isinstance(job_payload, Mapping)
        ]
        has_required_jobs = any(job_name.startswith("required / ") for job_name in job_names)
        has_exploratory_jobs = any(job_name.startswith(EXPLORATORY_JOB_NAME_PREFIX) for job_name in job_names)
        has_v3_job_bodies = any(
            _v3_job_body_markers(job_payload)
            for job_payload in jobs.values()
            if isinstance(job_payload, Mapping)
        )
        if workflow_path == REQUIRED_WORKFLOW_PATH or has_required_jobs:
            required_paths.append(workflow_path)
        if has_exploratory_jobs or (has_v3_job_bodies and workflow_path != REQUIRED_WORKFLOW_PATH):
            exploratory_paths.append(workflow_path)
    return {
        "exploratory": tuple(sorted(set(exploratory_paths))),
        "required": tuple(sorted(set(required_paths))),
    }


def build_ci_separation_payload(
    *,
    v3_lanes_required: bool,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    workflows = load_repo_workflows(repo_root=repo_root)
    classified = classify_workflow_paths(workflows)
    return {
        "v3_lanes_required": v3_lanes_required,
        "required_promotion_blocked": not v3_lanes_required,
        "required_promotion_blocked_reason": REQUIRED_PROMOTION_BLOCKED_REASON,
        "allowed_required_v3_job_names": list(ALLOWED_REQUIRED_V3_JOB_NAMES),
        "exploratory_job_name_prefix": EXPLORATORY_JOB_NAME_PREFIX,
        "exploratory_workflow_name_marker": EXPLORATORY_WORKFLOW_NAME_MARKER,
        "workflow_paths": list(sorted(workflows)),
        "exploratory_workflow_paths": list(classified["exploratory"]),
        "required_workflow_paths": list(classified["required"]),
        "required_workflow_path": REQUIRED_WORKFLOW_PATH,
        "v3_job_body_markers": list(V3_JOB_BODY_MARKERS),
        "rc2_frozen_suite_untouched": True,
    }


def audit_exploratory_ci_separation(
    *,
    workflows: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    findings: list[str] = []
    classified = classify_workflow_paths(workflows)
    required_paths = set(classified["required"])
    allowlisted_required_names = set(ALLOWED_REQUIRED_V3_JOB_NAMES)
    seen_allowlisted_required_names: set[str] = set()
    required_job_names: set[str] = set()

    if REQUIRED_WORKFLOW_PATH not in workflows:
        findings.append(f"required workflow missing: {REQUIRED_WORKFLOW_PATH}")

    for workflow_path, workflow_payload in workflows.items():
        workflow_name = str(workflow_payload.get("name", ""))
        jobs = workflow_payload.get("jobs", {})
        if not isinstance(jobs, Mapping) or not jobs:
            findings.append(f"{workflow_path} has no jobs")
            continue

        workflow_has_exploratory_jobs = False
        workflow_has_required_jobs = False
        workflow_has_v3_bodies = False

        for job_id, job_payload in jobs.items():
            if not isinstance(job_payload, Mapping):
                findings.append(f"{workflow_path}:{job_id} payload is not a mapping")
                continue

            job_name = _job_name(job_id, job_payload)
            markers = _v3_job_body_markers(job_payload)
            is_required_job = job_name.startswith("required / ")
            is_exploratory_job = job_name.startswith(EXPLORATORY_JOB_NAME_PREFIX)

            workflow_has_required_jobs = workflow_has_required_jobs or is_required_job
            workflow_has_exploratory_jobs = workflow_has_exploratory_jobs or is_exploratory_job
            workflow_has_v3_bodies = workflow_has_v3_bodies or bool(markers)

            if is_required_job:
                required_job_names.add(job_name)
                if workflow_path != REQUIRED_WORKFLOW_PATH:
                    findings.append(
                        f"{workflow_path}:{job_id} required job must live in {REQUIRED_WORKFLOW_PATH}"
                    )
            if is_exploratory_job and workflow_path == REQUIRED_WORKFLOW_PATH:
                findings.append(f"{workflow_path}:{job_id} exploratory job must not live in required workflow")

            if markers:
                marker_list = ", ".join(markers)
                if workflow_path in required_paths:
                    if job_name not in allowlisted_required_names:
                        findings.append(
                            f"{workflow_path}:{job_id} required workflow job body references v3 paths: {marker_list}"
                        )
                    else:
                        seen_allowlisted_required_names.add(job_name)
                else:
                    if not is_exploratory_job:
                        findings.append(
                            f"{workflow_path}:{job_id} references v3 paths without exploratory job label: {marker_list}"
                        )
                    if EXPLORATORY_WORKFLOW_NAME_MARKER not in workflow_name:
                        findings.append(f"{workflow_path} workflow name must carry Exploratory marker")
                    if is_required_job:
                        findings.append(
                            f"{workflow_path}:{job_id} must not be required when referencing v3 paths"
                        )

        if workflow_has_exploratory_jobs and EXPLORATORY_WORKFLOW_NAME_MARKER not in workflow_name:
            findings.append(f"{workflow_path} workflow name must carry Exploratory marker")
        if workflow_has_exploratory_jobs and workflow_has_required_jobs:
            findings.append(f"{workflow_path} mixes required and exploratory job labels")
        if workflow_has_v3_bodies and workflow_path != REQUIRED_WORKFLOW_PATH and not workflow_has_exploratory_jobs:
            findings.append(f"{workflow_path} references v3 paths without exploratory jobs")

    for required_name in allowlisted_required_names:
        if required_name not in required_job_names:
            findings.append(f"required v3 boundary job missing: {required_name}")
        if required_name not in seen_allowlisted_required_names:
            findings.append(f"required v3 boundary job missing v3 command markers: {required_name}")

    return tuple(findings)
