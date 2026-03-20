# pi‑mono — Multi‑Model Orchestration Policy (v2)

> **Purpose.** This document is designed for ingestion by the pi‑mono Orchestrator and for human review (HiTL).  
> It defines the control‑plane blueprint, model registry, routing priorities, guardrails, runtime defaults, **and how to feed these artifacts to the orchestrator**.

---

## (0) Orchestrator Blueprint — Updated

### Control‑Plane (Always‑On)
- **Primary Router / Orchestrator:** `llama-3.1-8b-it-nvfp4`  
  Duties: intent classification → task typing → lane selection → parameterization (sampling, grammar) → scheduling.  
  Keep turns short; escalate only when routing requires deeper reasoning.

- **Executive Orchestrator (on‑demand):** `gpt-oss-120b`  
  Duties: arbitrate duels, re‑plan complex multi‑stage jobs, synthesize cross‑model answers when confidence is low.

- **State Steward / Summarizer (always hot):** `phi-4-mini-it-q8`  
  Duties: KV‑relief and conversation hygiene. Maintain a compact **state card**:  
  `hypothesis`, `changed_files`, `failing_tests`, `last_cmds`, `open_questions`.

### Coding Lane (Key Agents)
- **Primary Repo Agent (heavy):** `devstral-2-123b-q4_k_m`  
- **Fast‑Small Repo Agent:** `devstral-small-2-24b-it-ud_q4_k_xl` (NEW)  
- **Implementer / Tests:** `phind-codellama-34b-v2-q8_0`

**Why this design?**  
A small, always‑on router keeps latency/VRAM steady while still having a powerful executive (120B) for adjudication and re‑planning. A permanent summarizer ensures KV stays in check during long, tool‑heavy sessions. For coding, the heavy 123B agent is complemented by a fast‑small 24B Devstral for quick repo work.

---

## 1) Model Registry (canonical IDs)
See `policy/orchestrator_policy.yaml`.

---

## 2) Global Routing Principles

1. Pick the **smallest model** that reliably solves the task.  
2. For **code/JSON/diffs**, prefer **llama.cpp GGUF** with **grammar constraints**.  
3. Always define **2nd/3rd** choices for diversity/failover.  
4. Use the **Executive** (120B) only on low confidence or complex re‑planning.  
5. Trigger **Summarizer** early; keep working contexts modest.

---

## 3) Task → Model Mapping (priorities)

**Planning/Research:** gpt‑oss‑120b → mistral‑small‑119b‑a6b → llama‑3.3‑70b‑it  
**Repo Agentic Coding:** devstral‑2‑123b‑q4_k_m → devstral‑small‑2‑24b‑it‑ud_q4_k_xl → phind‑34b‑v2‑q8_0  
**Code Completion/Tests:** phind‑34b‑v2‑q8_0 → llama‑3.3‑70b‑it‑uqq6_k_xl → gemma‑3‑27b‑it‑bf16  
**Long‑Form Docs:** mistral‑small‑119b‑a6b → gpt‑oss‑120b → llama‑3.3‑70b‑it  
**Summarization/State:** phi‑4‑mini‑it‑q8 → phi‑4‑q8 → llama‑3.1‑8b‑it‑nvfp4  
**Creative:** gpt‑oss‑120b → mistral‑small‑119b‑a6b → llama‑3.3‑70b‑it  
**Quick Q&A:** llama‑3.1‑8b‑it‑nvfp4 → phi‑4‑mini‑it‑q8 → gemma‑3‑27b‑it‑q4  
**Short Math/Reasoning:** gpt‑oss‑120b → mistral‑small‑119b‑a6b → nemotron‑super‑49b‑q6_k

---

## 4) Selection Algorithm (pseudo‑flow)

0. Router (8B NVFP4) classifies task → candidate list.
1. Filter by lane availability and max context.
2. If structured output required → prioritize GGUF/llama.cpp candidates with grammar.
3. Pick smallest candidate meeting quality tier; run; compute confidence.
4. If low confidence or tool failure:
* Summarize if KV is high or transcript long.
* Adjudicate with gpt-oss-120b or escalate to next candidate.
5. Persist: model_id, tokens_in/out, latency, confidence, verdict.

---

## 5) **How to Feed This to the Orchestrator (Ingestion Guide)**

### A. Files and Roles
- **`orchestrator_policy.yaml`** → **Machine routing configuration** (**source of truth**). Parsed at startup; all routing decisions use it.  
- **`orchestration_overview.md`** → **Human + LLM meta‑reference**. Load **only on demand** (adjudication, re‑planning). Do **not** parse every turn.  
- **`session_state.json`** → **Runtime memory**. Continuously updated by Summarizer.

### B. Storage Layout

/policy/orchestrator_policy.yaml
/policy/orchestration_overview.md
/state/session_state.json

### C. Boot Sequence
1. Load YAML; cache priorities, params, guardrails, KV triggers.  
2. Start router (`llama‑3.1‑8b‑it‑nvfp4`), summarizer (`phi‑4‑mini‑it‑q8`), and lazy‑init the Executive (`gpt‑oss‑120b`).  
3. Load or create `/state/session_state.json`.  
4. Enter event loop.

### D. Runtime Calls
- Router receives:
{ task_type, input_text, repo_context?, constraints?, perf?, must_have_grammar? }
- - Router picks model from YAML; applies parameters.  
- If low confidence → summarize → adjudicate (120B) or escalate to next candidate.  
- Persist telemetry.

---

## 6) Guardrails & Formatting

- **Grammars required** for code/JSON/diff tasks (llama.cpp GBNF / JSON schema).  
- **Sampling defaults**: Code → `temp=0.15, min_p=0.01, top_p=0.9, top_k=50`; Planning → `temp=0.3, top_p=0.9`.  
- **Fail policy**: 1 retry on tool error → escalate; format violations → retry with lower temperature (max 2).

---

## 7) Telemetry & Online Learning

- Log: `timestamp, task_type, model_id, lane, tokens_in, tokens_out, latency_ms, confidence, retries, result_ok`.  
- If a 2nd‑choice model wins ≥3 recent tasks of same type, **A/B swap** priorities temporarily.

---
