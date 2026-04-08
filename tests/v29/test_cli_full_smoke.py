from __future__ import annotations

from crisp.v29.cli import run_integrated_v29
from tests.v29_smoke_helpers import (
    assert_outputs_exist,
    create_minimal_full_mode_fixture_bundle,
    make_stub_core_bridge,
    required_full_smoke_outputs,
)


def test_run_integrated_v29_full_with_stubbed_core(tmp_path, monkeypatch) -> None:
    bundle = create_minimal_full_mode_fixture_bundle(tmp_path)

    monkeypatch.setattr(
        'crisp.v29.cli.run_core_bridge',
        make_stub_core_bridge(
            library_path=bundle['library_path'],
            target_id='tgt',
        ),
    )
    out_dir = bundle['repo_root'] / 'out'
    result = run_integrated_v29(
        repo_root=bundle['repo_root'],
        config_path=bundle['config_path'],
        library_path=bundle['library_path'],
        stageplan_path=bundle['stageplan_path'],
        out_dir=out_dir,
        run_mode='full',
        caps_path=bundle['caps_path'],
        assays_path=bundle['assays_path'],
    )
    assert result['run_mode_complete'] is True
    assert_outputs_exist(out_dir, required_full_smoke_outputs())
