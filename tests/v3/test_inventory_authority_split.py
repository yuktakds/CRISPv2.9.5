from __future__ import annotations

from crisp.v3.readiness.consistency import (
    audit_inventory_authority_split,
    build_inventory_authority_payload,
)


def test_inventory_authority_split_accepts_sidecar_manifest_and_rc2_output_inventory() -> None:
    findings = audit_inventory_authority_split(
        readiness={
            "inventory_authority": build_inventory_authority_payload(
                rc2_output_inventory_mutated=False,
            )
        },
        output_inventory={"generated_outputs": ["run_manifest.json", "output_inventory.json"]},
    )

    assert findings == ()


def test_inventory_authority_split_rejects_sidecar_outputs_in_rc2_inventory() -> None:
    findings = audit_inventory_authority_split(
        readiness={
            "inventory_authority": build_inventory_authority_payload(
                rc2_output_inventory_mutated=False,
            )
        },
        output_inventory={
            "generated_outputs": [
                "run_manifest.json",
                "output_inventory.json",
                "v3_sidecar/preconditions_readiness.json",
            ]
        },
    )

    assert findings == (
        "output_inventory enumerates sidecar artifact: v3_sidecar/preconditions_readiness.json",
    )


def test_inventory_authority_split_rejects_mismatched_sidecar_authority() -> None:
    readiness = {
        "inventory_authority": build_inventory_authority_payload(
            rc2_output_inventory_mutated=False,
        )
    }
    readiness["inventory_authority"]["sidecar_inventory_source"] = "output_inventory.json"
    findings = audit_inventory_authority_split(
        readiness=readiness,
        output_inventory={"generated_outputs": ["run_manifest.json", "output_inventory.json"]},
    )

    assert findings == ("inventory_authority sidecar_inventory_source mismatch",)
