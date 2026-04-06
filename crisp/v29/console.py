from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO
import sys

from crisp.v29.runtime_contract import IntegratedRunContract

_PREFIXES = {
    "progress": "[progress]",
    "warn": "[warn]",
    "skip": "[skip]",
    "fail_fast": "[fail-fast]",
    "summary": "[summary]",
    "artifact": "[artifact]",
}


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


@dataclass(slots=True)
class ConsoleReporter:
    stream: TextIO = field(default_factory=lambda: sys.stdout)

    def _emit(self, prefix: str, message: str) -> None:
        print(f"{_PREFIXES[prefix]} {message}", file=self.stream)

    def banner(self, contract: IntegratedRunContract, *, out_dir: str | Path) -> None:
        self.progress(
            "banner "
            f"role={contract.config_role} "
            f"comparison={contract.comparison_type} "
            f"comparison-source={contract.comparison_type_source} "
            f"truth-source={contract.truth_source} "
            f"core-frozen={_bool_text(contract.core_frozen)} "
            f"run-mode={contract.run_mode_resolved} "
            f"out={Path(out_dir).resolve()}"
        )

    def progress(self, message: str) -> None:
        self._emit("progress", message)

    def warn(self, message: str) -> None:
        self._emit("warn", message)

    def skip(self, message: str) -> None:
        self._emit("skip", message)

    def fail_fast(self, message: str) -> None:
        self._emit("fail_fast", message)

    def summary(self, message: str) -> None:
        self._emit("summary", message)

    def artifact(self, path: str | Path) -> None:
        self._emit("artifact", str(Path(path).resolve()))
