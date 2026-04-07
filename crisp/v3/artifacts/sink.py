from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_bytes
from crisp.utils.jsonx import canonical_json_bytes
from crisp.v3.contracts import ArtifactDescriptor, GeneratorManifest
from crisp.v3.policy import GENERATOR_MANIFEST_SCHEMA_VERSION, expected_output_digest_payload


class ArtifactSink:
    def __init__(self, output_root: str | Path, *, semantic_policy_version: str) -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.semantic_policy_version = semantic_policy_version
        self._outputs: list[ArtifactDescriptor] = []

    def write_json(self, logical_name: str, payload: Any, *, layer: str) -> Path:
        data = canonical_json_bytes(payload)
        return self._write_bytes(
            logical_name=logical_name,
            data=data,
            layer=layer,
            content_type="application/json",
        )

    def write_jsonl(self, logical_name: str, rows: list[dict[str, Any]], *, layer: str) -> Path:
        if rows:
            data = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
        else:
            data = b""
        return self._write_bytes(
            logical_name=logical_name,
            data=data,
            layer=layer,
            content_type="application/jsonl",
        )

    def write_text(
        self,
        logical_name: str,
        payload: str,
        *,
        layer: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> Path:
        return self._write_bytes(
            logical_name=logical_name,
            data=payload.encode("utf-8"),
            layer=layer,
            content_type=content_type,
        )

    def _write_bytes(
        self,
        *,
        logical_name: str,
        data: bytes,
        layer: str,
        content_type: str,
    ) -> Path:
        path = self.output_root / logical_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        descriptor = ArtifactDescriptor(
            logical_name=logical_name,
            relative_path=logical_name,
            layer=layer,
            content_type=content_type,
            sha256=sha256_bytes(data),
            byte_count=len(data),
        )
        self._outputs.append(descriptor)
        return path

    def materialized_outputs(self) -> list[str]:
        return [descriptor.relative_path for descriptor in self._outputs]

    def manifest_payload(self, *, run_id: str) -> GeneratorManifest:
        outputs_payload = [asdict(descriptor) for descriptor in self._outputs]
        expected_output_digest = expected_output_digest_payload(outputs_payload)
        return GeneratorManifest(
            schema_version=GENERATOR_MANIFEST_SCHEMA_VERSION,
            run_id=run_id,
            output_root=str(self.output_root),
            semantic_policy_version=self.semantic_policy_version,
            expected_output_digest=expected_output_digest,
            outputs=list(self._outputs),
        )

    def write_generator_manifest(self, *, run_id: str, logical_name: str = "generator_manifest.json") -> tuple[Path, str]:
        manifest = self.manifest_payload(run_id=run_id)
        path = self.output_root / logical_name
        path.write_bytes(canonical_json_bytes(asdict(manifest)))
        return path, manifest.expected_output_digest
