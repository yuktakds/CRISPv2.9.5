# 9KR6 smoke config semantic drift audit

This audit compares the only local baseline artifact available in-repo,
`configs/9kr6_cys328.yaml`, against `configs/9kr6_cys328.smoke.yaml`.
No separate historical Phase1 config artifact was found under `configs/`,
so the conclusions below are explicitly limited to semantic drift caused by
the current smoke sampling profile versus the original low-sampling baseline.

## Mechanical config diff

- `sampling.alpha`: `0.5` -> `0.35`
- `sampling.n_conformers`: `1` -> `8`
- `sampling.n_rotations`: `1` -> `64`
- `sampling.n_translations`: `1` -> `32`

## Fixed sample selection

Samples are deterministic: the script ranks `(compound_name, smiles)` pairs by
SHA256, takes the first `100` rows, then restores original library order.

- `facr2240` sample: `D:\CRISPv2.9.5\outputs\audit-inputs\facr2240-sample100.smi`
- `cys3200` sample: `D:\CRISPv2.9.5\outputs\audit-inputs\cys3200-sample100.smi`

## Comparative findings

### facr2240

- Baseline summary: PASS 0, FAIL 100, UNCLEAR 0
- Smoke summary: PASS 92, FAIL 8, UNCLEAR 0
- Baseline reasons: `{"FAIL_NO_FEASIBLE": 100}`
- Smoke reasons: `{"FAIL_ANCHORING_DISTANCE": 8, "PASS": 92}`
- Baseline core reasons: `{"UNCLEAR_INSUFFICIENT_FEASIBLE_POSES": 100}`
- Smoke core reasons: `{"FAIL_ANCHORING_DISTANCE": 8, "PASS": 92}`
- Baseline v_core counts: `{"UNCLEAR": 100}`
- Smoke v_core counts: `{"FAIL": 8, "PASS": 92}`
- Transition counts: `{"FAIL:FAIL_NO_FEASIBLE -> FAIL:FAIL_ANCHORING_DISTANCE": 8, "FAIL:FAIL_NO_FEASIBLE -> PASS:PASS": 92}`
- Changed records: `100` / `100`
- Baseline feasible_count stats: `{"count": 100, "max": 0, "median": 0.0, "min": 0}`
- Smoke feasible_count stats: `{"count": 100, "max": 661, "median": 212.0, "min": 50}`
- Baseline offtarget verdicts: `{"PASS": 100}`
- Smoke offtarget verdicts: `{"PASS": 100}`
- Baseline offtarget reasons: `{"OFFTARGET_SAFE": 100}`
- Smoke offtarget reasons: `{"OFFTARGET_SAFE": 100}`
- Baseline early_stop reasons: `{"NONE": 100}`
- Smoke early_stop reasons: `{"NONE": 100}`
- Baseline stage_id_found counts: `{"None": 100}`
- Smoke stage_id_found counts: `{"1": 99, "2": 1}`
- Example record flips:
  `Z2517218485`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `98`
  `Z2522603416`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `661`
  `Z3488636154`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `301`
  `Z2738284576`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `283`
  `Z2738285854`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `188`
  `Z3325092106`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `283`
  `Z3490366121`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `70`
  `Z3672062297`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `149`

### cys3200

- Baseline summary: PASS 0, FAIL 100, UNCLEAR 0
- Smoke summary: PASS 98, FAIL 2, UNCLEAR 0
- Baseline reasons: `{"FAIL_NO_FEASIBLE": 100}`
- Smoke reasons: `{"FAIL_ANCHORING_DISTANCE": 2, "PASS": 98}`
- Baseline core reasons: `{"UNCLEAR_INSUFFICIENT_FEASIBLE_POSES": 100}`
- Smoke core reasons: `{"FAIL_ANCHORING_DISTANCE": 2, "PASS": 98}`
- Baseline v_core counts: `{"UNCLEAR": 100}`
- Smoke v_core counts: `{"FAIL": 2, "PASS": 98}`
- Transition counts: `{"FAIL:FAIL_NO_FEASIBLE -> FAIL:FAIL_ANCHORING_DISTANCE": 2, "FAIL:FAIL_NO_FEASIBLE -> PASS:PASS": 98}`
- Changed records: `100` / `100`
- Baseline feasible_count stats: `{"count": 100, "max": 0, "median": 0.0, "min": 0}`
- Smoke feasible_count stats: `{"count": 100, "max": 891, "median": 162.0, "min": 55}`
- Baseline offtarget verdicts: `{"PASS": 100}`
- Smoke offtarget verdicts: `{"PASS": 100}`
- Baseline offtarget reasons: `{"OFFTARGET_SAFE": 100}`
- Smoke offtarget reasons: `{"OFFTARGET_SAFE": 100}`
- Baseline early_stop reasons: `{"NONE": 100}`
- Smoke early_stop reasons: `{"NONE": 100}`
- Baseline stage_id_found counts: `{"None": 100}`
- Smoke stage_id_found counts: `{"1": 98, "2": 2}`
- Example record flips:
  `Z3952172754`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `144`
  `Z3952174239`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `100`
  `Z3952174637`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `132`
  `Z4147934981`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `114`
  `Z3952172037`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `115`
  `Z3952173919`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `171`
  `Z3952174591`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `164`
  `Z3952172177`: `FAIL:FAIL_NO_FEASIBLE` -> `PASS:PASS`, feasible `0` -> `66`

## CXSMILES parser impact

- CXSMILES rows audited in `fACR2240.smiles`: `66`
- Name changes: `66`
- SMILES tokenization changes: `66`
- Input hash changes: `66`
- Canonical SMILES changes after RDKit parse: `0`
- Verdict changes in the old invalid run vs `-cxfix` run: `0`
- Reason changes in the old invalid run vs `-cxfix` run: `0`

## Conclusion

The CXSMILES parser fix corrects identifier and input-hash corruption for CX rows,
but it does not explain the current Phase1 pass-heavy distribution. The reproducible
drift seen here is dominated by the smoke sampling profile: the baseline config
collapses to `FAIL_NO_FEASIBLE`, while the smoke config converts most of the same
sample into `PASS` and pushes the residual failures almost entirely into
`FAIL_ANCHORING_DISTANCE` without activating any additional offtarget taxonomy.
