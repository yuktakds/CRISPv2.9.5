from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crisp.config.models import TargetConfig
from crisp.repro.hashing import sha256_file
from crisp.v29.contracts import TableWriteResult
from crisp.v29.tableio import read_records_table, write_records_table

DEFAULT_THETA_RULE1: float = 1.0
THETA_RULE1_TABLE_SCHEMA_VERSION = "theta_rule1_table/v1"
THETA_RULE1_RUNTIME_CONTRACT = "crisp.v29.theta_rule1.runtime/v1"
THETA_RULE1_ACTIVE_STATUS = "active"
_THETA_RULE1_METADATA_KEYS = (
    "table_schema_version",
    "runtime_contract",
    "table_version",
    "table_source",
    "table_status",
    "benchmark_config_path",
    "benchmark_config_role",
    "benchmark_config_hash",
    "calibration_seed",
    "calibration_cohort",
    "calibrated_by",
)
_THETA_RULE1_REQUIRED_KEYS = (
    "lookup_key",
    "theta_rule1",
    *_THETA_RULE1_METADATA_KEYS,
)


class ThetaRule1RuntimeError(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ThetaRule1RuntimeTable:
    lookup_table: dict[str, float]
    table_id: str
    table_version: str | None
    table_digest: str | None
    table_source: str | None
    runtime_contract: str | None
    schema_version: str | None
    table_status: str | None
    calibration_metadata: dict[str, Any] = field(default_factory=dict)


def build_theta_rule1_calibration_rows(
    values_by_key: dict[str, float],
    *,
    table_version: str,
    table_source: str,
    benchmark_config_path: str,
    benchmark_config_hash: str,
    calibration_seed: int,
    calibration_cohort: str,
    calibrated_by: str,
    benchmark_config_role: str = "benchmark",
    table_status: str = THETA_RULE1_ACTIVE_STATUS,
) -> list[dict[str, Any]]:
    if not values_by_key:
        raise ValueError("THETA_RULE1_CALIBRATION_VALUES_EMPTY")
    if benchmark_config_role != "benchmark":
        raise ValueError("THETA_RULE1_CALIBRATION_REQUIRES_BENCHMARK_CONFIG")
    if not table_version.strip():
        raise ValueError("THETA_RULE1_TABLE_VERSION_EMPTY")
    if not table_source.strip():
        raise ValueError("THETA_RULE1_TABLE_SOURCE_EMPTY")
    if not benchmark_config_path.strip():
        raise ValueError("THETA_RULE1_BENCHMARK_CONFIG_PATH_EMPTY")
    if not benchmark_config_hash.strip():
        raise ValueError("THETA_RULE1_BENCHMARK_CONFIG_HASH_EMPTY")
    if not calibration_cohort.strip():
        raise ValueError("THETA_RULE1_CALIBRATION_COHORT_EMPTY")
    if not calibrated_by.strip():
        raise ValueError("THETA_RULE1_CALIBRATED_BY_EMPTY")

    rows: list[dict[str, Any]] = []
    for lookup_key, theta_value in sorted(values_by_key.items()):
        rows.append({
            "lookup_key": str(lookup_key),
            "theta_rule1": float(theta_value),
            "table_schema_version": THETA_RULE1_TABLE_SCHEMA_VERSION,
            "runtime_contract": THETA_RULE1_RUNTIME_CONTRACT,
            "table_version": table_version,
            "table_source": table_source,
            "table_status": table_status,
            "benchmark_config_path": benchmark_config_path,
            "benchmark_config_role": benchmark_config_role,
            "benchmark_config_hash": benchmark_config_hash,
            "calibration_seed": int(calibration_seed),
            "calibration_cohort": calibration_cohort,
            "calibrated_by": calibrated_by,
        })
    return rows


def write_theta_rule1_calibration_table(
    path: str | Path,
    *,
    values_by_key: dict[str, float],
    table_version: str,
    table_source: str,
    benchmark_config_path: str,
    benchmark_config_hash: str,
    calibration_seed: int,
    calibration_cohort: str,
    calibrated_by: str,
    benchmark_config_role: str = "benchmark",
    table_status: str = THETA_RULE1_ACTIVE_STATUS,
) -> TableWriteResult:
    out = Path(path)
    if out.suffix.lower() != ".parquet":
        raise ValueError("THETA_RULE1_TABLE_MUST_BE_PARQUET")
    rows = build_theta_rule1_calibration_rows(
        values_by_key,
        table_version=table_version,
        table_source=table_source,
        benchmark_config_path=benchmark_config_path,
        benchmark_config_hash=benchmark_config_hash,
        calibration_seed=calibration_seed,
        calibration_cohort=calibration_cohort,
        calibrated_by=calibrated_by,
        benchmark_config_role=benchmark_config_role,
        table_status=table_status,
    )
    result = write_records_table(out, rows)
    if result.format != "parquet":
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_NOT_PARQUET",
            message=(
                "managed theta_rule1 table must materialize as parquet "
                f"(got {result.format})"
            ),
        )
    return result


def _builtin_theta_rule1_runtime_table() -> ThetaRule1RuntimeTable:
    return ThetaRule1RuntimeTable(
        lookup_table={},
        table_id="builtin:none",
        table_version=None,
        table_digest=None,
        table_source="builtin:none",
        runtime_contract=None,
        schema_version=None,
        table_status=None,
        calibration_metadata={},
    )


def _validate_theta_rule1_rows(rows: list[dict[str, Any]], *, path: Path) -> dict[str, Any]:
    if not rows:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_EMPTY",
            message=f"{path} has no rows",
        )

    first = rows[0]
    missing_keys = [key for key in _THETA_RULE1_REQUIRED_KEYS if key not in first]
    if missing_keys:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_MISSING_COLUMNS",
            message=f"missing columns: {missing_keys}",
        )

    metadata = {key: first.get(key) for key in _THETA_RULE1_METADATA_KEYS}
    for row in rows[1:]:
        for key in _THETA_RULE1_METADATA_KEYS:
            if row.get(key) != metadata[key]:
                raise ThetaRule1RuntimeError(
                    code="THETA_RULE1_TABLE_METADATA_DRIFT",
                    message=f"{key} must be constant across rows",
                )

    schema_version = str(metadata["table_schema_version"])
    if schema_version != THETA_RULE1_TABLE_SCHEMA_VERSION:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_INCOMPATIBLE_SCHEMA",
            message=f"{schema_version!r} != {THETA_RULE1_TABLE_SCHEMA_VERSION!r}",
        )
    runtime_contract = str(metadata["runtime_contract"])
    if runtime_contract != THETA_RULE1_RUNTIME_CONTRACT:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_INCOMPATIBLE_RUNTIME",
            message=f"{runtime_contract!r} != {THETA_RULE1_RUNTIME_CONTRACT!r}",
        )

    table_status = str(metadata["table_status"])
    if table_status != THETA_RULE1_ACTIVE_STATUS:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_STALE",
            message=f"table_status={table_status!r}",
        )

    benchmark_role = str(metadata["benchmark_config_role"])
    if benchmark_role != "benchmark":
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_REQUIRES_BENCHMARK",
            message=f"benchmark_config_role={benchmark_role!r}",
        )

    for required_text_key in (
        "table_version",
        "table_source",
        "benchmark_config_path",
        "benchmark_config_hash",
        "calibration_cohort",
        "calibrated_by",
    ):
        raw_value = metadata.get(required_text_key)
        if raw_value is None or not str(raw_value).strip():
            raise ThetaRule1RuntimeError(
                code="THETA_RULE1_TABLE_METADATA_EMPTY",
                message=f"{required_text_key} is empty",
            )

    try:
        metadata["calibration_seed"] = int(metadata["calibration_seed"])
    except (TypeError, ValueError) as exc:
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_INVALID_SEED",
            message=str(exc),
        ) from exc

    return metadata


def load_theta_rule1_runtime_table(
    path: str | Path | None,
    *,
    require_managed: bool = False,
) -> ThetaRule1RuntimeTable:
    if path is None:
        if require_managed:
            raise ThetaRule1RuntimeError(
                code="THETA_RULE1_TABLE_MISSING",
                message="theta_rule1_table is required for managed runtime",
            )
        return _builtin_theta_rule1_runtime_table()

    table_path = Path(path)
    if table_path.suffix.lower() != ".parquet":
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_MUST_BE_PARQUET",
            message=f"{table_path} must end with .parquet",
        )
    if not table_path.exists():
        raise ThetaRule1RuntimeError(
            code="THETA_RULE1_TABLE_MISSING",
            message=f"{table_path} not found",
        )

    rows = read_records_table(table_path)
    metadata = _validate_theta_rule1_rows(rows, path=table_path)

    lookup_table: dict[str, float] = {}
    for row in rows:
        lookup_key = str(row.get("lookup_key") or "").strip()
        if not lookup_key:
            raise ThetaRule1RuntimeError(
                code="THETA_RULE1_TABLE_LOOKUP_KEY_EMPTY",
                message="lookup_key must be non-empty",
            )
        if lookup_key in lookup_table:
            raise ThetaRule1RuntimeError(
                code="THETA_RULE1_TABLE_DUPLICATE_LOOKUP_KEY",
                message=f"duplicate lookup_key={lookup_key!r}",
            )
        try:
            lookup_table[lookup_key] = float(row["theta_rule1"])
        except (TypeError, ValueError) as exc:
            raise ThetaRule1RuntimeError(
                code="THETA_RULE1_TABLE_INVALID_VALUE",
                message=f"lookup_key={lookup_key!r}: {exc}",
            ) from exc

    return ThetaRule1RuntimeTable(
        lookup_table=lookup_table,
        table_id=f"table:{table_path.resolve()}",
        table_version=str(metadata["table_version"]),
        table_digest=sha256_file(table_path),
        table_source=str(metadata["table_source"]),
        runtime_contract=str(metadata["runtime_contract"]),
        schema_version=str(metadata["table_schema_version"]),
        table_status=str(metadata["table_status"]),
        calibration_metadata={
            "benchmark_config_path": str(metadata["benchmark_config_path"]),
            "benchmark_config_role": str(metadata["benchmark_config_role"]),
            "benchmark_config_hash": str(metadata["benchmark_config_hash"]),
            "calibration_seed": int(metadata["calibration_seed"]),
            "calibration_cohort": str(metadata["calibration_cohort"]),
            "calibrated_by": str(metadata["calibrated_by"]),
        },
    )


def resolve_theta_rule1(
    runtime_table: ThetaRule1RuntimeTable,
    *,
    config: TargetConfig,
) -> float:
    for key in (config.target_name, config.pathway, "default"):
        if key and key in runtime_table.lookup_table:
            return float(runtime_table.lookup_table[key])
    return DEFAULT_THETA_RULE1
