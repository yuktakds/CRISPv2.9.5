from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def build_donor_plan(
    pair_plan_rows: list[dict[str, Any]],
    shuffle_universe_scope: str,
    shuffle_seed: int,
) -> dict[str, Any]:
    native_caps = sorted({str(r['native_cap_id']) for r in pair_plan_rows if r['pairing_role'] == 'native'})
    donor_caps = sorted({str(r['cap_id']) for r in pair_plan_rows if r['pairing_role'] == 'matched_falsification'})
    payload = {
        'shuffle_universe_scope': shuffle_universe_scope,
        'shuffle_seed': int(shuffle_seed),
        'native_caps': native_caps,
        'donor_caps': donor_caps,
    }
    payload['shuffle_donor_pool_hash'] = 'sha256:' + sha256(json.dumps(donor_caps, sort_keys=True).encode('utf-8')).hexdigest()
    payload['donor_plan_hash'] = 'sha256:' + sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
    return payload
