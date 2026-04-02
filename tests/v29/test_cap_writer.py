from __future__ import annotations

from pathlib import Path
import json

import pytest

from crisp.v29.contracts import CapBatchEval
from crisp.v29.writers import write_cap_batch_eval, write_eval_report


def test_cap_batch_eval_is_truth_source(tmp_path: Path) -> None:
    path = tmp_path / "cap_batch_eval.json"
    write_cap_batch_eval(path, CapBatchEval(run_id="r1", status="SKIPPED", cap_batch_verdict=None, cap_batch_reason_code=None))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["source_of_truth"] is True


def test_eval_report_rejects_verdict_keys(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_eval_report(tmp_path / "eval_report.json", {"cap_batch_verdict": "PASS"})
