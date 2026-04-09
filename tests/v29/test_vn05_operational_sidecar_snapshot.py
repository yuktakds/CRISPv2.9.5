from __future__ import annotations

from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from tests.v29_smoke_helpers import (
    create_minimal_full_mode_fixture_bundle,
    make_stub_core_bridge,
)


def test_run_integrated_v29_passes_core_compounds_path_to_sidecar_snapshot(tmp_path: Path, monkeypatch) -> None:
    fixture = create_minimal_full_mode_fixture_bundle(tmp_path / "bundle")
    integrated_path = fixture["repo_root"] / "integrated.yaml"
    integrated_path.write_text(
        "\n".join(
            [
                "v3_sidecar:",
                "  enabled: true",
                "  channels:",
                "    catalytic:",
                "      enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=fixture["library_path"], target_id="tgt"),
    )
    captured: dict[str, object] = {}

    def _fake_run_sidecar(*, snapshot, options, comparator_options=None):
        captured["core_compounds_path"] = snapshot.core_compounds_path
        captured["cap_pair_features_path"] = snapshot.cap_pair_features_path
        return None

    monkeypatch.setattr("crisp.v29.cli.run_sidecar", _fake_run_sidecar)

    run_integrated_v29(
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
        library_path=fixture["library_path"],
        stageplan_path=fixture["stageplan_path"],
        out_dir=tmp_path / "run",
        integrated_config_path=integrated_path,
        run_mode="full",
        caps_path=fixture["caps_path"],
        assays_path=fixture["assays_path"],
    )

    assert isinstance(captured["core_compounds_path"], str)
    assert str(captured["core_compounds_path"]).endswith("core_compounds.parquet")
