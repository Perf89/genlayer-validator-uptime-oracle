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

Real-world use cases this primitive is meant to unlock:

- **Staking-as-a-service marketplaces** — trust-minimized SLA verification between an
  operator and a delegator, without either side running a centralized reputation
  service.
- **Slashing-insurance / cover products** — an underwriter needs a neutral, disputable
  source of truth about whether a claimed incident/uptime figure is accurate.
- **Validator reputation systems** — aggregating verified (not self-reported) uptime
  history across networks.

## Why this is a real primitive, not a demo

- It is **standalone and reusable**: any contract or frontend can call
  `submit_attestation` / `verify_attestation` against any evidence URL and any claimed
  metric — it is not wired to one specific dataset or network.
- **State design** separates the claim (`submit_attestation`) from its verification
  (`verify_attestation`) as two distinct consensus rounds, so a claim can sit pending,
  be disputed, or be re-submitted without re-running evidence collection every time.
- **Equivalence Principle is used for real, not as a format check.** The validator does
  not just check that the leader returned valid JSON — it independently re-fetches the
  same evidence URL and re-derives the verdict, then the two are compared on the
  decision fields only (`claim_supported` exact match, `measured_uptime_bps` within
  ±50 bps / ±0.5% tolerance). This is exactly the "independent comparison" pattern the
  docs recommend over leader-output-only validation.

## Consensus design

```
leader_fn():
    web_data = gl.nondet.web.get(evidence_url)
    ask LLM to extract measured_uptime_bps + claim_supported from web_data
    return structured JSON

validator_fn(leader_result):
    re-fetch the same evidence_url
    re-run the same extraction independently
    accept only if:
        - claim_supported matches exactly, AND
        - measured_uptime_bps is within ±50 bps of the leader's value
```

Free-text `reasoning` is stored on-chain for transparency but is **never** compared
between validators, since two independent LLM runs will always phrase their reasoning
differently — only the decision fields need to agree.

## Deployed contract

| Field | Value |
|---|---|
| Network | GenLayer Studio (Studionet) |
| Contract | `Validator uptime oracle.py` |
| Deployed address | `0x4E...8229` *(copy full address from Studio → contract header)* |
| Source | [`validator_uptime_oracle.py`](./validator_uptime_oracle.py) |

> Replace the address above with the full value from the Studio contract panel
> (click the copy icon next to "Deployed at").

## Live test evidence

Two independent consensus rounds were run against real, public, unauthenticated data
sources — one that does **not** support the claim, and one that does — to demonstrate
that the contract genuinely discriminates between supported and unsupported claims
rather than rubber-stamping every submission.

### Scenario 1 — Rejected claim (unsupported by evidence)

| Field | Value |
|---|---|
| `attestation_id` | `1` |
| `network` | `ethereum` |
| `claimed_uptime_bps` | `9990` (99.90%) |
| `evidence_url` | `https://beaconcha.in/api/v1/validator/1` |
| Result | `claim_supported: false`, `measured_uptime_bps: 0` |
| Tx (`verify_attestation`) | `0x8712471f883b3fc7192edfbb9d5b9b71e440f142985c7c9f0626009ebec03fe` |
| Validator votes | 4/5 Agree that the claim is **unsupported** |

The AI validators independently read the evidence URL, found nothing that supported
the claimed uptime figure, and rejected the claim — the correct outcome for unverifiable
evidence.

### Scenario 2 — Confirmed claim (supported by evidence)

| Field | Value |
|---|---|
| `attestation_id` | `5` |
| `network` | `cosmos-hub` |
| `claimed_uptime_bps` | `10000` (100%) |
| `validator_address` | `cosmosvalcons1p2x4mv97rjta5sd69snn5ftya5zekwvvp9jjxu` |
| `evidence_url` | `https://cosmos-rest.publicnode.com/cosmos/slashing/v1beta1/signing_infos` |
| Ground truth | `missed_blocks_counter: "0"` for this validator in the public Cosmos Hub REST API |
| Result | `claim_supported: true`, `measured_uptime_bps: 10000` |
| Tx (`verify_attestation`) | `0x02e1d90b222d49023e8b3cdc389affcba9973b90ab90e7b8d8957e799a5b1a9c` |
| Validator votes | 3/5 Agree, 2/5 Disagree (`claude-sonnet-4.6`, `deepseek` disagreed) — majority accepted |

This round is the strongest evidence of genuine Equivalence Principle behavior: five
different LLM providers (GPT-5.4, Gemini, Grok, Claude Sonnet 4.6, DeepSeek)
independently parsed the same raw JSON evidence (a 600+ entry validator list) and did
**not** all agree — three found and confirmed the specific validator's zero missed-block
count, two did not. The protocol's majority rule resolved the disagreement correctly.
This is real, disputable consensus over evidence — not a formality.

## Reproducing these tests

1. Open [GenLayer Studio](https://studio.genlayer.com), get testnet GEN from the 💧
   faucet.
2. Upload `validator_uptime_oracle.py` and deploy (constructor takes no arguments).
3. Call `submit_attestation(validator_address, network, claimed_uptime_bps, evidence_url)`
   with the values from either scenario above.
4. Call `verify_attestation(attestation_id)` using the id returned by step 3.
5. Call `get_attestation(attestation_id)` to read back the final `status`,
   `confirmed_uptime_bps`, and `reasoning`.

## Files

- [`validator_uptime_oracle.py`](./validator_uptime_oracle.py) — full contract source,
  with an in-file docstring covering purpose and consensus design.
- [`LICENSE`](./LICENSE) — MIT.

## License

MIT — see [`LICENSE`](./LICENSE). Fill in your name/handle as copyright holder before
publishing.
