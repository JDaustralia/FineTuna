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

``