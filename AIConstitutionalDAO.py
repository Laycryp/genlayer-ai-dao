# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

class AIConstitutionalDAO(gl.Contract):
    constitution: str
    owner: str
    active_proposal: str
    proposal_status: str
    proposer: str

    def __init__(self, constitution: str):
        # 1. Precommitted Rules: تحديد الدستور عند النشر ولا يمكن تغييره
        self.constitution = constitution
        self.owner = gl.message.sender
        self.active_proposal = ""
        self.proposal_status = "NONE"
        self.proposer = ""

    @gl.public.write
    def submit_proposal(self, proposal_text: str) -> str:
        # 2. Access/State Control: منع إغراق العقد بمقترحات جديدة إذا كان هناك مقترح نشط
        if self.proposal_status == "ACTIVE":
            raise gl.vm.UserError("An active proposal is already awaiting manual voting.")

        caller = gl.message.sender
        dao_rules = self.constitution

        # 3. Non-deterministic block with Explicit Failure Handling
        def evaluate_constitutionality() -> dict:
            task = f"""
            You are the strict AI guardian of a Decentralized Autonomous Organization (DAO).
            The DAO's immutable constitution is: "{dao_rules}"
            
            A member has submitted the following proposal: "{proposal_text}"
            
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

        # 4. Strict Consensus
        consensus_result = gl.eq_principle.strict_eq(evaluate_constitutionality)

        if consensus_result.get("error"):
            raise gl.vm.UserError(f"Proposal evaluation failed: {consensus_result.get('reason')}")

        # تحديث حالة العقد وتوثيق عنوان مقدم المقترح
        self.proposer = caller
        self.active_proposal = proposal_text

        if consensus_result["is_constitutional"]:
            self.proposal_status = "ACTIVE"
            return f"Proposal ACCEPTED for voting. Reason: {consensus_result.get('reason')}"
        else:
            self.proposal_status = "REJECTED"
            return f"Proposal REJECTED by AI Guardian. Reason: {consensus_result.get('reason')}"

    @gl.public.view
    def get_proposal_status(self) -> str:
        return self.proposal_status