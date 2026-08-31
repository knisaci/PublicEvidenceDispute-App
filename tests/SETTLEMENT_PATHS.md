# PublicEvidenceDispute settlement paths

Contract: 0x4A7050418a9dFe41709400FbC85F8C8A1f593aE6
Network: Testnet Bradbury
Transfers: emit_transfer
Value methods: add_stake, join_as_defendant (@gl.public.write.payable)

## Path A — funded resolve
1. Creator add_stake with value
2. Defendant join_as_defendant with value
3. status becomes funded
4. resolve() — validators fetch evidence_url
5. matching verdict + confidence
6. winner paid via emit_transfer, or unknown refunds both stakes
7. settle() retries if needed

## Path B — defendant never joins
1. status open
2. creator calls cancel_open
3. creator recorded stake returned
4. status cancelled

## Path C — mutual cancel
1. status open or funded, unresolved
2. both parties request_cancel
3. each recorded stake returned

## Path D — expiry
1. after expires_unix
2. either party cancel_expired
3. recorded stakes returned

## Frontend
https:// (set after Vercel)
