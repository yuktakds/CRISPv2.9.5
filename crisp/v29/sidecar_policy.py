from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SidecarArtifactPolicy:
    artifact_name: str
    policy_class: str
    activation_condition: str
    inventory_treatment: str
    replay_handling: str
    validator_handling: str
    completion_blocking: bool = False


SIDECAR_POLICIES: dict[str, SidecarArtifactPolicy] = {
    "core_bridge_diagnostics.json": SidecarArtifactPolicy(
        artifact_name="core_bridge_diagnostics.json",
        policy_class="conditional",
        activation_condition="written when the core bridge materializes",
        inventory_treatment="generated_outputs_only",
        replay_handling="observe_only",
        validator_handling="non_blocking",
    ),
    "legacy_phase1_evidence_alias.json": SidecarArtifactPolicy(
        artifact_name="legacy_phase1_evidence_alias.json",
        policy_class="optional",
        activation_condition="written by the integrated shell for legacy evidence traceability",
        inventory_treatment="generated_outputs_only",
        replay_handling="observe_only",
        validator_handling="non_blocking",
    ),
    "rule3_trace_summary.json": SidecarArtifactPolicy(
        artifact_name="rule3_trace_summary.json",
        policy_class="conditional",
        activation_condition="written when the core branch emits proposal_trace_json rows",
        inventory_treatment="generated_outputs_only",
        replay_handling="observe_only",
        validator_handling="non_blocking",
    ),
    "theta_rule1_resolution.json": SidecarArtifactPolicy(
        artifact_name="theta_rule1_resolution.json",
        policy_class="conditional",
        activation_condition="written for rule1-capable runs or when a theta table is explicitly supplied",
        inventory_treatment="generated_outputs_only",
        replay_handling="required_for_rule1_replay",
        validator_handling="required_managed_fail_fast_or_warn_fallback",
    ),
    "rule1_branch_diagnostics.json": SidecarArtifactPolicy(
        artifact_name="rule1_branch_diagnostics.json",
        policy_class="conditional",
        activation_condition="written when the rule1 branch executes",
        inventory_treatment="generated_outputs_only",
        replay_handling="observe_only",
        validator_handling="non_blocking",
    ),
}


def sidecar_policy_rows() -> list[dict[str, object]]:
    return [
        asdict(policy)
        for _name, policy in sorted(SIDECAR_POLICIES.items())
    ]
