# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

class AIConstitutionalDAO(gl.Contract):
    constitution: str
    active_proposal: str
    proposal_status: str
    votes_for: u256
    votes_against: u256
    voters_json: str  # تخزين القائمة كـ JSON String لتجاوز قيود GenVM وضمان التطابق الدقيق

    def __init__(self, constitution: str):
        self.constitution = constitution
        self.active_proposal = ""
        self.proposal_status = "NONE"
        self.votes_for = u256(0)
        self.votes_against = u256(0)
        self.voters_json = "[]"

    @gl.public.write
    def submit_proposal(self, proposal_text: str) -> str:
        if self.proposal_status == "ACTIVE":
            raise gl.vm.UserError("An active proposal is already awaiting resolution. Resolve it first.")

        dao_rules = self.constitution

        def evaluate_constitutionality() -> dict:
            task = f"""
            You are the strict AI guardian of a DAO.
            Immutable constitution: "{dao_rules}"
            Proposed action: "{proposal_text}"
            
            Does this proposal violate any rules or the core spirit of the constitution?
            
            Respond using ONLY the following JSON format:
            {{
                "is_constitutional": bool,
                "reason": "short explanation"
            }}
            """
            try:
                result_str = gl.nondet.exec_prompt(task).replace("```json", "").replace("```", "")
                parsed = json.loads(result_str)
                if "is_constitutional" not in parsed:
                    return {"is_constitutional": False, "error": True, "reason": "Invalid LLM JSON format."}
                parsed["error"] = False
                return parsed
            except Exception:
                return {"is_constitutional": False, "error": True, "reason": "LLM execution or parsing failed."}

        consensus_result = gl.eq_principle.strict_eq(evaluate_constitutionality)

        if consensus_result.get("error"):
            raise gl.vm.UserError(f"Proposal evaluation failed: {consensus_result.get('reason')}")

        self.active_proposal = proposal_text
        self.votes_for = u256(0)
        self.votes_against = u256(0)
        self.voters_json = "[]"

        if consensus_result["is_constitutional"]:
            self.proposal_status = "ACTIVE"
            return f"Proposal ACCEPTED for voting. Reason: {consensus_result.get('reason')}"
        else:
            self.proposal_status = "REJECTED_BY_AI"
            return f"Proposal REJECTED by AI Guardian. Reason: {consensus_result.get('reason')}"

    # إزالة إدخال العنوان يدوياً والاعتماد على gl.message.sender
    @gl.public.write
    def cast_vote(self, support: bool) -> str:
        if self.proposal_status != "ACTIVE":
            raise gl.vm.UserError("No active proposal to vote on.")
            
        # 1. Verifiable Caller Identity
        caller = gl.message.sender
        
        # 2. Exact Membership Semantics
        voters_list = json.loads(self.voters_json)
        if caller in voters_list:
            raise gl.vm.UserError("Voter has already cast a vote.")
            
        voters_list.append(caller)
        self.voters_json = json.dumps(voters_list)
        
        if support:
            self.votes_for += u256(1)
        else:
            self.votes_against += u256(1)
            
        return f"Vote cast successfully by {caller}."

    @gl.public.write
    def resolve_proposal(self) -> str:
        if self.proposal_status != "ACTIVE":
            raise gl.vm.UserError("No active proposal to resolve.")
            
        total_votes = self.votes_for + self.votes_against
        if total_votes == u256(0):
            self.proposal_status = "REJECTED_BY_VOTERS"
            return "Proposal rejected due to lack of votes."
            
        if self.votes_for > self.votes_against:
            self.proposal_status = "PASSED"
            return "Proposal passed by majority vote."
        else:
            self.proposal_status = "REJECTED_BY_VOTERS"
            return "Proposal rejected by majority vote."

    @gl.public.view
    def get_proposal_status(self) -> dict:
        return {
            "proposal": self.active_proposal,
            "status": self.proposal_status
        }