from __future__ import annotations

from crisp.v3.ci_guards import EXPLORATORY_JOB_NAME_PREFIX, load_workflow_yaml

WORKFLOW_PATH = ".github/workflows/v3-keep-path-rc-exploratory.yml"


def test_keep_path_rc_exploratory_workflow_stays_exploratory_only() -> None:
    workflow = load_workflow_yaml(WORKFLOW_PATH)

    assert workflow["name"] == "v3 Keep-Path RC Exploratory"
    jobs = workflow["jobs"]
    assert set(jobs) == {"keep-path-rc-contracts", "keep-path-rc-bundle"}
    assert all(
        str(job_payload["name"]).startswith(EXPLORATORY_JOB_NAME_PREFIX)
        for job_payload in jobs.values()
    )
    assert all(str(job_payload["runs-on"]) == "windows-latest" for job_payload in jobs.values())


def test_keep_path_rc_exploratory_workflow_uses_fixed_fixture_and_fixed_evidence() -> None:
    workflow = load_workflow_yaml(WORKFLOW_PATH)
    bundle_job = workflow["jobs"]["keep-path-rc-bundle"]
    body_text = "\n".join(
        str(step.get("run", "")) + "\n" + str(step.get("uses", ""))
        for step in bundle_job["steps"]
    )

    assert "scripts/run_keep_path_rc_gate.py" in body_text
    assert "scripts/run_keep_path_rc_campaign.py" in body_text
    assert "scripts/run_keep_path_rc_release_packet_smoke.py" not in body_text
    assert "scripts/run_keep_path_release_packet_smoke.py" in body_text
    assert "tests/v3/fixtures/keep_path_rc_ci/runs" in body_text
    assert "docs/release/evidence/keep_path_rc/2026-04-09" in body_text
    assert "release_packet_smoke_snapshot.json" in body_text
    assert "actions/upload-artifact@v4" in body_text


def test_keep_path_rc_exploratory_workflow_does_not_claim_required_or_full_verdict_semantics() -> None:
    workflow = load_workflow_yaml(WORKFLOW_PATH)
    body_text = "\n".join(
        str(step.get("run", "")) + "\n" + str(step.get("uses", ""))
        for job_payload in workflow["jobs"].values()
        for step in job_payload["steps"]
    )

    assert "required / " not in body_text
    assert "v29-required-matrix.yml" not in body_text
    assert "verdict_match_rate: `1/" not in body_text
    assert "verdict_match_rate: `0/" not in body_text
    assert "--snapshot-path docs/release/evidence/keep_path_rc/2026-04-09/release_packet_smoke_snapshot.json" in body_text
