# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
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
    evidence_url: str
    question: str
    expires_unix: u256

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

    def __init__(self, defendant: str, evidence_url: str, question: str, expires_unix: int):
        self.creator = gl.message.sender_address
        self.defendant = Address(defendant)
        self.evidence_url = evidence_url
        self.question = question
        self.expires_unix = u256(expires_unix)
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
            "evidence_url": self.evidence_url,
            "question": self.question,
            "expires_unix": int(self.expires_unix),
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

    @gl.public.write.payable
    def join_as_defendant(self) -> dict:
        require(gl.message.sender_address == self.defendant, "Only defendant")
        require(self.status == "open", "Not open")
        require(self.defendant_stake == u256(0), "Already joined")
        amount = gl.message.value
        require(amount > u256(0), "Must send GEN")
        self.defendant_stake = amount
        self.pot += amount
        if self.creator_stake > u256(0) and self.defendant_stake > u256(0):
            self.status = "funded"
        return {"ok": True, "status": self.status, "pot": int(self.pot)}

    @gl.public.write.payable
    def add_stake(self) -> dict:
        require(self._unresolved(), "Settled")
        require(self.status in ("open", "funded"), "Wrong state")
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
            self.status = "funded"
        return {"ok": True, "pot": int(self.pot), "status": self.status}

    @gl.public.write
    def cancel_open(self) -> dict:
        require(gl.message.sender_address == self.creator, "Only creator")
        require(self._unresolved(), "Already settled")
        require(self.status == "open", "Not open")
        return self._refund_stakes()

    @gl.public.write
    def request_cancel(self) -> dict:
        require(self._unresolved(), "Already settled")
        require(self.status in ("open", "funded"), "Wrong state")
        sender = gl.message.sender_address
        require(sender == self.creator or sender == self.defendant, "Not a party")
        if sender == self.creator:
            self.creator_cancel = True
        else:
            self.defendant_cancel = True
        if self.creator_cancel and self.defendant_cancel:
            return self._refund_stakes()
        return {"ok": True, "status": self.status, "creator_cancel": self.creator_cancel, "defendant_cancel": self.defendant_cancel}

    @gl.public.write
    def cancel_expired(self) -> dict:
        require(self._unresolved(), "Already settled")
        require(self.status in ("open", "funded"), "Wrong state")
        sender = gl.message.sender_address
        require(sender == self.creator or sender == self.defendant, "Not a party")
        now_s = 0
        raw = gl.message_raw.get("datetime", "")
        try:
            from datetime import date
            ds = str(raw).replace("Z", "+00:00")
            date_part = ds.split("T")[0]
            y, m, d = [int(x) for x in date_part.split("-")]
            now_s = int((date(y, m, d) - date(1970, 1, 1)).days) * 86400
        except Exception:
            now_s = 0
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
            return {"ok": False, "message": "Empty pot", "status": self.status}
        _Recipient(self.winner).emit_transfer(value=self.pot)
        self.pot = u256(0)
        self.is_paid = True
        self.status = "paid"
        return {"ok": True, "status": self.status, "verdict": self.verdict, "winner": str(self.winner)}

    @gl.public.write
    def resolve(self) -> dict:
        require(self.creator_stake > u256(0) and self.defendant_stake > u256(0), "Both must stake")
        if self.has_resolved and self.status in ("paid", "refunded", "cancelled"):
            return {"ok": False, "message": "Already settled", "status": self.status}
        if self.has_resolved:
            return self._settle()
        evidence_url = self.evidence_url
        question = self.question

        def leader_fn() -> dict:
            page = gl.nondet.web.render(evidence_url, mode="text")
            prompt = f"""
You are an impartial adjudicator deciding a two-party dispute from public evidence.
Question:
{question}
Evidence page content:
{page[:12000]}
Respond with valid JSON only:
{{
  "verdict": "creator" | "defendant" | "unknown",
  "confidence": "low" | "medium" | "high",
  "note": "<one short sentence of evidence-based reasoning>"
}}
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
            note = str(raw.get("note", ""))[:300]
            return {"verdict": verdict, "confidence": confidence, "note": note}

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader = leader_result.calldata
            if not isinstance(leader, dict):
                return False
            mine = leader_fn()
            if mine["verdict"] != leader.get("verdict"):
                return False
            if mine["confidence"] != leader.get("confidence"):
                return False
            return True

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
        require(not self.is_paid and not self.is_refunded, "Already settled")
        return self._settle()
