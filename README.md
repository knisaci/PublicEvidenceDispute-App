# PublicEvidenceDispute-App

Full GenLayer Project: two-party dispute settled from a public evidence URL via AI consensus.

## Live
https://public-evidence-dispute-app.vercel.app

## Contract
0x4A7050418a9dFe41709400FbC85F8C8A1f593aE6
Network: Testnet Bradbury
Explorer: https://explorer-bradbury.genlayer.com/address/0x4A7050418a9dFe41709400FbC85F8C8A1f593aE6
Source in this repo: PublicEvidenceDispute.py

## What it does
Creator and defendant lock GEN. resolve() fetches the evidence page. Validators accept only when verdict and confidence match. Winner is paid with emit_transfer. Unknown refunds both stakes.

Unresolved funds are not stuck:
- cancel_open if defendant never funds
- request_cancel when both parties agree
- cancel_expired after expires_unix

## Frontend
React + genlayer-js. Connect wallet, send value, call the full lifecycle.

## Tests
python3 tests/test_settlement_state_machine.py
See tests/SETTLEMENT_PATHS.md

## License
MIT
