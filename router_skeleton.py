import os, json, time, yaml
from typing import Dict, Any, List

POLICY_PATH = os.environ.get("PI_MONO_POLICY", "policy/orchestrator_policy.yaml")
STATE_PATH = os.environ.get("PI_MONO_STATE", "state/session_state.json")


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"hypothesis": "", "changed_files": [], "failing_tests": [],
                "last_cmds": [], "open_questions": [], "last_summary_ts": None, "kv_utilization_pct": 0}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


class Router:
    def __init__(self, policy: Dict[str, Any], state: Dict[str, Any]):
        self.policy = policy
        self.state = state
        self.router_id = policy["router"]["control_plane"]["primary"]
        self.exec_id = policy["router"]["adjudicator"]["on_low_confidence"]

    def select_order(self, task_type: str) -> List[str]:
        return self.policy["routing"][task_type]["order"]

    def params_for(self, task_type: str) -> Dict[str, Any]:
        return self.policy["routing"][task_type].get("params", {})

    def grammar_required(self, task_type: str) -> bool:
        req_for = self.policy["guards"]["structured_outputs"]["grammar_required_for"]
        return task_type in req_for

    def summarize_if_needed(self):
        trig = self.policy["kv_management"]["trigger"]
        if (self.state.get("kv_utilization_pct", 0) >= trig["kv_utilization_pct"]):
            self.call_summarizer()

    def call_summarizer(self):
        # Pseudocode stub: call phi-4-mini-it-q8 with a compact prompt to rewrite logs → state card.
        self.state["last_summary_ts"] = time.time()
        save_state(STATE_PATH, self.state)

    def call_model(self, model_id: str, prompt: str, params: Dict[str, Any], use_grammar: bool) -> Dict[str, Any]:
        # Pseudocode stub: dispatch to vLLM or llama.cpp based on 'lane' in policy['models'] list
        # Return { text, tokens_in, tokens_out, latency_ms, confidence }
        return {"text": "…", "tokens_in": 0, "tokens_out": 0, "latency_ms": 0, "confidence": 0.85}

    def adjudicate(self, prompt: str, candidate_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Pseudocode stub: call gpt-oss-120b with the policy excerpt and candidate outputs to choose best
        return max(candidate_outputs, key=lambda r: r["confidence"])

    def handle(self, task_type: str, prompt: str, must_have_grammar: bool = False) -> Dict[str, Any]:
        self.summarize_if_needed()
        order = self.select_order(task_type)
        params = self.params_for(task_type)
        need_grammar = must_have_grammar or self.grammar_required(task_type)

        attempts = []
        for model_id in order:
            res = self.call_model(model_id, prompt, params, use_grammar=need_grammar)
            attempts.append({"model_id": model_id, **res})
            if res["confidence"] >= 0.8:
                return attempts[-1]

            # tool or format errors would be handled here; on failures, continue to next model
        # Adjudicate among attempts if all low-confidence:
        best = self.adjudicate(prompt, attempts)
        return best


if __name__ == "__main__":
    policy = load_yaml(POLICY_PATH)
    state = load_state(STATE_PATH)
    router = Router(policy, state)

    # Example call
    out = router.handle(
        task_type="repo_agentic_coding",
        prompt="Fix failing tests in auth module; add unit tests for token expiry.",
        must_have_grammar=True
    )
    print(json.dumps(out, indent=2))
#  Copyright (c) 2026. Copyright asserted and retained by James Dick himself.
