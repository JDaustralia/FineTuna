# Multi-Model Orchestration Policy (v1)

Purpose. Provide deterministic, machine readable guidance so an Orchestrator LLM can select the best model per task, with first/second/third choices, fallbacks, formatting rules, and safety rails for code/JSON patching.

0) Model Registry (Canonical IDs)
Use these exact model_ids in routing and logs.

models:
  # -------- safetensors (run via vLLM / Transformers) --------
  - id: gpt-oss-120b           # Open-weight generalist + reasoning knob
    family: safetensors
  - id: llama-3.1-8b-base
    family: safetensors
  - id: llama-3.1-8b-it
    family: safetensors

  # -------- NVFP4 (run via vLLM; keep lane for FP4) --------
  - id: intellect-3
    family: nvfp4
  - id: mistral-small-119b-a6b
    family: nvfp4
  - id: llama-3.3-70b-it
    family: nvfp4
  - id: llama-3.1-8b-it-nvfp4
    family: nvfp4
  - id: nemotron-nano-9b-v2
    family: nvfp4
  - id: phi-4-reason-plus
    family: nvfp4

  # -------- GGUF (run via llama.cpp / Ollama) --------
  - id: mixtral-8x22b-iq4_xs
    family: gguf
  - id: nemotron-super-49b-q6_k
    family: gguf
  - id: llama-3.3-70b-it-uqq6_k_xl
    family: gguf
  - id: devstral-2-123b-q4_k_m
    family: gguf
  - id: phind-codellama-34b-v2-q8_0
    family: gguf
  - id: gemma-3-27b-it-bf16
    family: gguf
  - id: gemma-3-27b-it-q4
    family: gguf
  - id: llama-3.1-8b-it-f16
    family: gguf
  - id: phi-4-q8
    family: gguf
  - id: phi-4-mini-it-q8
    family: gguf


Runtime lanes (assumed):
•	vLLM lane → safetensors, nvfp4 (planner/reasoner/generalist).
•	llama.cpp lane → gguf (agentic coding, grammar constrained outputs).
•	Ollama helper lane → small gguf helpers (summarizers, evaluators) when convenience > control.
1) Global Routing Principles
1.	Choose the smallest model that reliably solves the task (latency, cost, KV headroom).
2.	Prefer NVFP4 / FP16 over integer quant when quality is critical (esp. planning, long code).
3.	For code/patch/JSON, run on llama.cpp GGUF with grammar constraints enabled.
4.	Always define a secondary and tertiary model for diversity and failover.
5.	When KV/VRAM pressure rises, invoke a Summarizer to compress state before continuing.

2) Task → Model Mapping (Priorities & Fallbacks)
The orchestrator should select the highest priority available model that fits the context/VRAM envelope and latency target. If the result is low confidence or tool execution fails, escalate to the next priority.
2.1 Planning / Research / Analysis (non code)
•	Goal: long context briefs, structured plans, pros/cons, comparisons.
•	First: gpt-oss-120b (safetensors; reasoning knob; robust planning)
•	Second: mistral-small-119b-a6b (nvfp4; hybrid instruct+reasoning)
•	Third: llama-3.3-70b-it (nvfp4)
•	Lightweight alt (short briefs): llama-3.1-8b-it-nvfp4 or llama-3.1-8b-it-f16
Format hints: Ask for outline → bullets → risks → next actions.
When KV ≥ 70%: hand off to Summarizer (see §3.4).

2.2 Agentic Coding — Repo Orchestration (plan→patch→test→retry)
•	Goal: multi file edits, tool calling, deterministic patches.
•	First: devstral-2-123b-q4_k_m (gguf, llama.cpp; agentic SWE; use grammars)
•	Second: phind-codellama-34b-v2-q8_0 (gguf; precise implementer)
•	Third: nemotron-super-49b-q6_k (gguf; strong general reasoning flavor)
Run time rules:
•	Always enforce GBNF/JSON schema for diffs/patches.
•	Sampling: temperature=0.15, min_p=0.01, top_p=0.9, top_k=50.
•	Stop conditions: tests green; diff size within policy; no regressions.

2.3 Code Completion / Unit Test Authoring (single file or small scope)
•	First: phind-codellama-34b-v2-q8_0
•	Second: llama-3.3-70b-it-uqq6_k_xl
•	Third: gemma-3-27b-it-bf16
Notes: Keep low temperature, prefer functional tests and property based tests.

2.4 Long Form Explanations / Documentation Drafting
•	First: mistral-small-119b-a6b (nvfp4)
•	Second: gpt-oss-120b (safetensors)
•	Third: llama-3.3-70b-it (nvfp4)
Style: “Explain like I’m experienced; include short code snippets and caveats.”

2.5 Summarization / State Card Maintenance (always on helper)
•	First: phi-4-mini-it-q8
•	Second: phi-4-q8
•	Third: llama-3.1-8b-it-f16
Duties:
•	Compress tool logs, test traces, and diffs into a state card.
•	Maintain hypothesis, changed_files, failing_tests, last_cmds.
•	Trigger when KV ≥ 70% or after N tool invocations.

2.6 JSON / Structured Output / Tool Arguments
•	First (llama.cpp grammar): whichever task model is selected but with grammar activated.
•	If grammar is unavailable: prefer models in gguf lane; else fall back to short spans and post validation.
2.7 Creative Brainstorming / Naming / Ideation
•	First: gpt-oss-120b
•	Second: mistral-small-119b-a6b
•	Third: llama-3.3-70b-it

2.8 Quick Q&A / Low latency General Help
•	First: llama-3.1-8b-it-nvfp4 (or llama-3.1-8b-it-f16)
•	Second: phi-4-mini-it-q8
•	Third: gemma-3-27b-it-q4 (when a bit more capacity is needed)

2.9 Math / Reasoning heavy Short Problems
•	First: gpt-oss-120b
•	Second: mistral-small-119b-a6b
•	Third: nemotron-super-49b-q6_k or mixtral-8x22b-iq4_xs (diversity check)

3) Orchestrator Execution Rules
3.1 Selection Algorithm (pseudocode)

Given: task_type, context_tokens_est, latency_target, must_have_grammar?

1) Candidate set = priorities[task_type]
2) Filter by runtime availability and max context support
3) If must_have_grammar? → prefer gguf/llama.cpp lane
4) Pick smallest model that satisfies quality tier:
     - Tier A: nvfp4/safetensors large (planner-grade)
     - Tier B: gguf high-precision (Q8_0 / Q6_K / special L variants)
     - Tier C: gguf balanced (Q4_K_M) or small helpers
5) If KV utilization > threshold or response drifts:
     - Invoke Summarizer → update state card → trim conversation
6) If tool-run fails twice or confidence < threshold:
     - Escalate to next model (2nd, then 3rd priority)
7) Persist: model_id, tokens_in/out, latency, verdict, confidence

3.2 Confidence & Escalation
confidence_policy:
low: escalate_one # try 2nd priority with same prompt + short critique
very_low: replan_and_escalate # regenerate plan on 2nd model
mismatch: cross_check_with
Rubric for dueling: correctness, constraints adherence, testability, minimal diff size.

3.3 Code / Patch Guardrails (llama.cpp lane)
code_guardrails:
structured_outputs: grammar_required
grammars:
- json_object
- json_array
- unified_diff # if available; else JSON patch schema
sampling:
temperature: 0.15
min_p: 0.01
top_p: 0.9
top_k: 50
stop_on:
- malformed_json
- unbalanced_delimiters
retry:
max_attempts: 2
on_retry: lower_temperature_by: 0.
Show more lines

3.4 Summarizer Protocol (KV Management)
summarizer:
when:
- kv_utilization_pct >= 70
- steps_since_last_summary >= 6
model_order: [phi-4-mini-it-q8, phi-4-q8, llama-3.1-8b-it-f16]
state_card:
fields: [hypothesis, changed_files, failing_tests, last_cmds, open_questions]
max_tokens: 800
compress

3.5 Sampling Defaults (non code)
defaults:
planning:
temperature: 0.3
top_p: 0.9
summarization:
temperature: 0.2
creative:
temperature: 0.7
top_p:

4) Task Templates (for Orchestrator Prompts)
Use these templated messages to prime each lane consistently.
4.1 Planning (generalist / nvfp4 or safetensors)
Plain Text
System: You are a senior planner. Produce a 5–8 step plan with risks and mitigations.
User:
Goal: {goal}
Constraints: {constraints}
Deliver: JSON with keys {"steps":[], "risks":[], "mitigations":[], "next_actions
4.2 Repo Agent (gguf / llama.cpp + grammar)
Plain Text
System: You are a repo-scale coding agent. Propose plan then atomic diffs. Follow JSON schema strictly.
User:
Issue: {issue}
RepoSummary: {repo_summary}
Deliver
4.3 Summarizer (always-on)
Plain Text
System: Summarize to maintain a compact state card.
User:
Logs: {logs}
Deliver: {"hypothesis":"...", "changed_files":[...], "failing_tests":[...], "last_cmds":[...]}

5) Policy by Model (Strengths & Notes)
Keep descriptions short, non normative, and orchestration relevant.
model_notes:
gpt-oss-120b:
role: planner/generalist
strengths: long plans, reasoning diversity, robust tool instructions
cautions: higher latency; summarize on long threads
mistral-small-119b-a6b:
role: hybrid instruct+reasoning
strengths: structured planning, agent patterns
llama-3.3-70b-it:
role: secondary planner; strong general writing
llama-3.1-8b-it-nvfp4:
role: quick helper; short plans and rewrites

devstral-2-123b-q4_k_m:
role: primary repo agent
strengths: multi-file edits, retries, tool orchestration
run_on: llama.cpp with grammar

phind-codellama-34b-v2-q8_0:
role: implementer / unit tests
strengths: code precision, smaller diffs
nemotron-super-49b-q6_k:
role: alternative implementer
strengths: reasoning flavor; good second opinion

mixtral-8x22b-iq4_xs:
role: diversity check for reasoning
gemma-3-27b-it-bf16:
role: strong single-file code/doc drafts
gemma-3-27b-it-q4:
role: economical helper
llama-3.1-8b-it-f16:
role: low-latency helper
phi-4-q8:
role: summarizer backup
phi-4-mini-it-q8:
role: primary summar
Show more lines

6) Failure Handling & Safety
YAML
failure_policy:
tool_error:
first: retry_same_model
second: escalate_next_model
low_confidence:
action: cross_check_secondary
formatting_violation (json/diff):
action: reject_and_retry
note: reduce temperature; re-emit with grammar

7) Telemetry & Learning Loop
•	Log per call: task_type, model_id, tokens_in/out, latency_ms, confidence, retries, result_ok.
•	Nightly ranking update:
•	If a 2nd choice model outperforms 1st on ≥ 3 recent tasks of a type → swap priorities temporarily and A/B for next 3 tasks.
•	Maintain per task success scores to auto tune priority lists over time.

8) Implementation Notes (for the Orchestrator Engineer)
•	Route by lane: large safetensors/NVFP4 → vLLM; GGUF → llama.cpp; small GGUF helpers → llama.cpp or Ollama.
•	Enable grammars for any code/JSON/diff output.
•	Keep temperatures low for code; higher for creativity.
•	Monitor KV/cuda memory; trigger summarizer when thresholds are crossed.
•	Record outcomes to refine priority lists over time.

Minimal API Contract 
request:
  task_type: planning | coding_agent | code_completion | summarization | creative | qna | math
  input:
    text: "<user/problem>"
    repo_context?: "<optional summary>"
    constraints?: ["..."]
  perf:
    latency_target_ms: 3000
    max_context_tokens: 32000
  must_have_grammar?: true|false

response:
  chosen_model: "<model_id>"
  lane: vllm | llamacpp | ollama
  parameters: {temperature, top_p, top_k, min_p, grammar?: name}
  result:
    text?: "<answer>"
    json?: {...}
    patches?: [{"file":"...", "unified_diff":"..."}]
  meta:
    tokens_in: 0
    tokens_out: 0
    latency_ms: 0
    confidence: 0.0
    fallback_used: false

