# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from datetime import datetime, timezone
import json


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass
    class Write:
        pass


class PublicEvidenceDispute(gl.Contract):
    creator: Address
    defendant: Address
    topic: str
    expires_unix: u256

    creator_claim: str
    creator_evidence_url: str
    creator_committed: bool

    defendant_claim: str
    defendant_evidence_url: str
    defendant_committed: bool

    creator_stake: u256
    defendant_stake: u256
    pot: u256

    status: str
    has_resolved: bool
    is_paid: bool
    is_refunded: bool

    verdict: str
    confidence: str
    note: str
    winner: Address

    creator_cancel: bool
    defendant_cancel: bool

    def __init__(self, defendant: str, topic: str, creator_claim: str, creator_evidence_url: str, expires_unix: int):
        self.creator = gl.message.sender_address
        self.defendant = Address(defendant)
        self.topic = topic
        self.expires_unix = u256(expires_unix)
        self.creator_claim = creator_claim
        self.creator_evidence_url = creator_evidence_url
        self.creator_committed = True
        self.defendant_claim = ""
        self.defendant_evidence_url = ""
        self.defendant_committed = False
        self.creator_stake = gl.message.value
        self.defendant_stake = u256(0)
        self.pot = gl.message.value
        self.status = "open"
        self.has_resolved = False
        self.is_paid = False
        self.is_refunded = False
        self.verdict = ""
        self.confidence = ""
        self.note = ""
        self.winner = Address("0x0000000000000000000000000000000000000000")
        self.creator_cancel = False
        self.defendant_cancel = False

    def _unresolved(self) -> bool:
        return (not self.has_resolved) and (not self.is_paid) and (not self.is_refunded)

    def _both_committed(self) -> bool:
        return self.creator_committed and self.defendant_committed

    def _refund_stakes(self) -> dict:
        if self.creator_stake > u256(0):
            _Recipient(self.creator).emit_transfer(value=self.creator_stake)
        if self.defendant_stake > u256(0):
            _Recipient(self.defendant).emit_transfer(value=self.defendant_stake)
        self.pot = u256(0)
        self.creator_stake = u256(0)
        self.defendant_stake = u256(0)
        self.is_refunded = True
        self.status = "cancelled"
        return {"ok": True, "status": self.status}

    @gl.public.view
    def get_dispute(self) -> dict:
        return {
            "creator": str(self.creator),
            "defendant": str(self.defendant),
            "topic": self.topic,
            "expires_unix": int(self.expires_unix),
            "creator_claim": self.creator_claim,
            "creator_evidence_url": self.creator_evidence_url,
            "creator_committed": self.creator_committed,
            "defendant_claim": self.defendant_claim,
            "defendant_evidence_url": self.defendant_evidence_url,
            "defendant_committed": self.defendant_committed,
            "creator_stake": int(self.creator_stake),
            "defendant_stake": int(self.defendant_stake),
            "pot": int(self.pot),
            "status": self.status,
            "has_resolved": self.has_resolved,
            "is_paid": self.is_paid,
            "is_refunded": self.is_refunded,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "note": self.note,
            "winner": str(self.winner),
            "creator_cancel": self.creator_cancel,
            "defendant_cancel": self.defendant_cancel,
        }

    @gl.public.write
    def commit_defense(self, defendant_claim: str, defendant_evidence_url: str) -> dict:
        require(gl.message.sender_address == self.defendant, "Only defendant")
        require(self._unresolved(), "Settled")
        require(not self.defendant_committed, "Defense already committed")
        require(len(defendant_claim) > 0, "Claim required")
        require(len(defendant_evidence_url) > 8, "Evidence required")
        self.defendant_claim = defendant_claim
        self.defendant_evidence_url = defendant_evidence_url
        self.defendant_committed = True
        if self.status == "funded":
            self.status = "ready"
        return {"ok": True, "defendant_committed": True, "status": self.status}

    @gl.public.write.payable
    def join_as_defendant(self) -> dict:
        require(gl.message.sender_address == self.defendant, "Only defendant")
        require(self.defendant_stake == u256(0), "Already joined")
        amount = gl.message.value
        require(amount > u256(0), "Must send GEN")
        self.defendant_stake = amount
        self.pot += amount
        if self.creator_stake > u256(0) and self.defendant_stake > u256(0):
            self.status = "ready" if self._both_committed() else "funded"
        return {"ok": True, "status": self.status}

    @gl.public.write.payable
    def add_stake(self) -> dict:
        require(self._unresolved(), "Settled")
        amount = gl.message.value
        require(amount > u256(0), "Must send GEN")
        sender = gl.message.sender_address
        require(sender == self.creator or sender == self.defendant, "Not a party")
        if sender == self.creator:
            self.creator_stake += amount
        else:
            self.defendant_stake += amount
        self.pot += amount
        if self.creator_stake > u256(0) and self.defendant_stake > u256(0):
            self.status = "ready" if self._both_committed() else "funded"
        return {"ok": True, "status": self.status}

    @gl.public.write
    def cancel_open(self) -> dict:
        require(gl.message.sender_address == self.creator, "Only creator")
        require(self._unresolved(), "Already settled")
        require(self.defendant_stake == u256(0), "Defendant already funded")
        return self._refund_stakes()

    @gl.public.write
    def request_cancel(self) -> dict:
        require(self._unresolved(), "Already settled")
        sender = gl.message.sender_address
        require(sender == self.creator or sender == self.defendant, "Not a party")
        if sender == self.creator:
            self.creator_cancel = True
        else:
            self.defendant_cancel = True
        if self.creator_cancel and self.defendant_cancel:
            return self._refund_stakes()
        return {"ok": True, "creator_cancel": self.creator_cancel, "defendant_cancel": self.defendant_cancel}

    @gl.public.write
    def cancel_expired(self) -> dict:
        require(self._unresolved(), "Already settled")
        sender = gl.message.sender_address
        require(sender == self.creator or sender == self.defendant, "Not a party")
        now_s = int(datetime.now(timezone.utc).timestamp())
        require(now_s >= int(self.expires_unix) or int(self.expires_unix) == 0, "Not expired")
        return self._refund_stakes()

    def _settle(self) -> dict:
        if self.is_paid or self.is_refunded:
            return {"ok": True, "status": self.status}
        if self.status == "resolved_unknown":
            if self.creator_stake > u256(0):
                _Recipient(self.creator).emit_transfer(value=self.creator_stake)
            if self.defendant_stake > u256(0):
                _Recipient(self.defendant).emit_transfer(value=self.defendant_stake)
            self.pot = u256(0)
            self.is_refunded = True
            self.status = "refunded"
            return {"ok": True, "status": self.status}
        if self.pot == u256(0):
            return {"ok": False, "message": "Empty pot"}
        _Recipient(self.winner).emit_transfer(value=self.pot)
        self.pot = u256(0)
        self.is_paid = True
        self.status = "paid"
        return {"ok": True, "status": self.status}

    @gl.public.write
    def resolve(self) -> dict:
        require(self._both_committed(), "Both must commit first")
        require(self.creator_stake > u256(0) and self.defendant_stake > u256(0), "Both must stake")
        if self.has_resolved:
            return self._settle()
        topic = self.topic
        creator_claim = self.creator_claim
        defendant_claim = self.defendant_claim
        creator_url = self.creator_evidence_url
        defendant_url = self.defendant_evidence_url

        def leader_fn() -> dict:
            creator_page = gl.nondet.web.render(creator_url, mode="text")
            defendant_page = gl.nondet.web.render(defendant_url, mode="text")
            prompt = f"""
Adjudicate a two-party dispute. Claims and evidence were committed before this vote.
Topic: {topic}
Creator claim: {creator_claim}
Creator evidence: {creator_page[:6000]}
Defendant claim: {defendant_claim}
Defendant evidence: {defendant_page[:6000]}
JSON only:
{{"verdict":"creator"|"defendant"|"unknown","confidence":"low"|"medium"|"high","note":"<one sentence>"}}
"""
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(raw, dict):
                raw = json.loads(str(raw).replace("```json", "").replace("```", "").strip())
            verdict = str(raw.get("verdict", "unknown")).lower().strip()
            if verdict not in ("creator", "defendant", "unknown"):
                verdict = "unknown"
            confidence = str(raw.get("confidence", "low")).lower().strip()
            if confidence not in ("low", "medium", "high"):
                confidence = "low"
            return {"verdict": verdict, "confidence": confidence, "note": str(raw.get("note", ""))[:300]}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader = leader_result.calldata
            if not isinstance(leader, dict):
                return False
            mine = leader_fn()
            return mine["verdict"] == leader.get("verdict") and mine["confidence"] == leader.get("confidence")

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.has_resolved = True
        self.verdict = str(result["verdict"])
        self.confidence = str(result["confidence"])
        self.note = str(result.get("note", ""))[:300]
        if self.verdict == "creator":
            self.winner = self.creator
            self.status = "resolved_creator"
        elif self.verdict == "defendant":
            self.winner = self.defendant
            self.status = "resolved_defendant"
        else:
            self.winner = Address("0x0000000000000000000000000000000000000000")
            self.status = "resolved_unknown"
        return self._settle()

    @gl.public.write
    def settle(self) -> dict:
        require(self.has_resolved, "Not resolved")
        return self._settle()
