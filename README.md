# Validator Uptime & Slashing Attestation Oracle

A standalone GenLayer Intelligent Contract primitive submitted for the **Standalone Contracts** track.

## Purpose

Lets a validator operator (or anyone) submit an uptime / SLA claim about a validator on
some external network (*"we ran 99.9% uptime on Cosmos Hub over the last 30 days"*),
backed by a public evidence URL (a block explorer, a chain's REST API, a status
dashboard, etc). GenLayer's AI-validator consensus independently reads that evidence
and confirms or rejects the claim, producing an on-chain, disputable attestation that
other contracts or off-chain systems can rely on without trusting the claimant or a
single centralized oracle.

Real-world use cases:

- **Staking-as-a-service marketplaces** — trust-minimized SLA verification between an
  operator and a delegator.
- **Slashing-insurance / cover products** — a neutral, disputable source of truth about
  whether a claimed uptime figure is accurate.
- **Validator reputation systems** — aggregating verified (not self-reported) uptime.

## Design

### Two-step lifecycle

`submit_attestation` records a claim as `pending`. `verify_attestation` runs a separate
consensus round that reads the evidence and moves it to `confirmed` or `rejected`.
Already-processed attestations cannot be verified again.

### Consensus (Equivalence Principle, independent comparison)

```
leader_fn():
    web_data = gl.nondet.web.get(evidence_url)
    ask LLM for {claim_supported, measured_uptime_bps, reasoning}
    return _validate_result(parsed JSON)          # strict, see below

validator_fn(leader_result):
    leader_data    = _validate_result(leader_result)   # reject malformed leader output
    validator_data = leader_fn()                       # independently re-fetch + re-derive
    accept only if:
        claim_supported matches exactly, AND
        |measured_uptime_bps difference| <= 50 bps (0.5%)
```

Free-text `reasoning` is stored for transparency but never compared, since two LLM runs
will always phrase it differently.

### Strict result validation before any state write

LLM output is untrusted. `_validate_result` is applied at three points: in the leader,
in the validator (to both the leader's result and its own), and once more immediately
before state is written. A result is accepted only if:

| Field | Requirement |
|---|---|
| `claim_supported` | a real JSON boolean — the string `"false"` (truthy in Python) is rejected |
| `measured_uptime_bps` | an `int` (not `bool`, not `float`, not a string) in `0..10000` |
| `reasoning` | a string (stored truncated to 500 characters) |

Malformed results make validators disagree, so they can never be finalized into state,
and can never fail halfway through persistence. `submit_attestation` additionally
validates `claimed_uptime_bps` (0..10000) and requires an `https://` evidence URL.

These rules are covered by offline tests (`tests/test_result_validation.py`) that load
the helper functions straight from the contract source, so they always test exactly the
code that is deployed:

```
python3 tests/test_result_validation.py
```

## Deployed contract

The source in this repository is byte-for-byte the source that was deployed.

| Field | Value |
|---|---|
| Network | GenLayer Studio (Studionet) |
| Deployed address | `0xd4662F40ef362DEcFA9c7af7844E5E5968ab24F5` |
| Explorer | `https://explorer-studio.genlayer.com/address/0xd4662F40ef362DEcFA9c7af7844E5E5968ab24F5` |
| Source | [`validator_uptime_oracle.py`](./validator_uptime_oracle.py) |

## Live test evidence

Two consensus rounds against real, public, unauthenticated data sources: one claim the
evidence does **not** support, and one it does.

### Scenario 1 — rejected claim (unsupported by evidence)

| Field | Value |
|---|---|
| `network` | `ethereum` |
| `claimed_uptime_bps` | `9990` (99.90%) |
| `evidence_url` | `https://beaconcha.in/api/v1/validator/1` |
| Result | `claim_supported: false` → `status: rejected` |
| Tx (`verify_attestation`) | `0x7fcae48c39c1d62413cf3327331f4c8c5e9fa87dda01fda5e5a1f636f4bb88b7` |

### Scenario 2 — confirmed claim (supported by evidence)

| Field | Value |
|---|---|
| `network` | `cosmos-hub` |
| `validator_address` | `cosmosvalcons1p2x4mv97rjta5sd69snn5ftya5zekwvvp9jjxu` |
| `claimed_uptime_bps` | `10000` (100%) |
| `evidence_url` | `https://cosmos-rest.publicnode.com/cosmos/slashing/v1beta1/signing_infos` |
| Ground truth | `missed_blocks_counter: "0"` for this validator |
| Result | `claim_supported: true`, `measured_uptime_bps: 10000` → `status: confirmed` |
| Tx (`verify_attestation`) | `0x4b4c3eff3855c751f79f81c2d483ca17703f49a567ffcf549c7d57a118535538` |

In the Scenario 2 run the first leader's proposal was rejected by the majority of validators (leader rotation); the second round reached consensus and was accepted.

## Reproducing

1. Open [GenLayer Studio](https://studio.genlayer.com) and deploy `validator_uptime_oracle.py`
   (constructor takes no arguments).
2. `submit_attestation(validator_address, network, claimed_uptime_bps, evidence_url)`
   with the values from a scenario above; note the returned id.
3. `verify_attestation(id)`.
4. `get_attestation(id)` to read back `status`, `confirmed_uptime_bps`, `reasoning`.

## Files

- [`validator_uptime_oracle.py`](./validator_uptime_oracle.py) — contract source
- [`tests/test_result_validation.py`](./tests/test_result_validation.py) — offline validation tests
- [`LICENSE`](./LICENSE) — MIT
