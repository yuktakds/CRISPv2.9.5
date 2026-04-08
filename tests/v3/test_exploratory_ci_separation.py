from __future__ import annotations

from crisp.v3.ci_guards import (
    EXPLORATORY_JOB_NAME_PREFIX,
    EXPLORATORY_WORKFLOW_PATHS,
    REQUIRED_WORKFLOW_PATH,
    audit_exploratory_ci_separation,
    load_workflow_yaml,
)


def test_repo_workflows_preserve_exploratory_v3_ci_separation() -> None:
    findings = audit_exploratory_ci_separation(
        required_workflow=load_workflow_yaml(REQUIRED_WORKFLOW_PATH),
        exploratory_workflows={
            workflow_path: load_workflow_yaml(workflow_path)
            for workflow_path in EXPLORATORY_WORKFLOW_PATHS
        },
    )

    assert findings == ()


def test_ci_separation_rejects_promoted_v3_operator_job() -> None:
    required_workflow = {
        "jobs": {
            "v3-report-guards": {
                "name": "required / v3-report-guards",
            }
        }
    }
    exploratory_workflows = {
        ".github/workflows/v3-readiness-exploratory.yml": {
            "name": "v3 Readiness Exploratory",
            "jobs": {
                "report-guards": {
                    "name": f"{EXPLORATORY_JOB_NAME_PREFIX}v3-report-guards",
                }
            },
        }
    }

    findings = audit_exploratory_ci_separation(
        required_workflow=required_workflow,
        exploratory_workflows=exploratory_workflows,
    )

    assert "unexpected required v3 job: required / v3-report-guards" in findings


def test_ci_separation_rejects_non_exploratory_v3_job_name() -> None:
    findings = audit_exploratory_ci_separation(
        required_workflow={
            "jobs": {
                "v3-sidecar-determinism": {
                    "name": "required / v3-sidecar-determinism",
                }
            }
        },
        exploratory_workflows={
            ".github/workflows/v3-bridge-comparator-exploratory.yml": {
                "name": "v3 Bridge Comparator Exploratory",
                "jobs": {
                    "bridge-comparator": {
                        "name": "required / v3-bridge-comparator",
                    }
                },
            }
        },
    )

    assert (
        ".github/workflows/v3-bridge-comparator-exploratory.yml:bridge-comparator is not exploratory"
        in findings
    )
