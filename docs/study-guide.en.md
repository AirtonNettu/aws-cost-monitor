<p align="right"><a href="study-guide.md">Português</a> · <strong>English</strong></p>

# Study Guide — AWS Cost Monitor

> A technical document meant for **study**. It uses the project's real code as
> teaching material to explain the **FinOps**, **AWS integration**, and
> **software design** concepts behind the tool. Read it alongside the code and
> you should understand not only *what* the project does, but *why* it is built
> this way.

## Table of contents

1. [The problem: why monitor cloud costs](#1-the-problem-why-monitor-cloud-costs)
2. [FinOps in one sentence](#2-finops-in-one-sentence)
3. [The core rule: Python computes, AI interprets](#3-the-core-rule-python-computes-ai-interprets)
4. [How we talk to AWS (Cost Explorer + boto3)](#4-how-we-talk-to-aws-cost-explorer--boto3)
5. [The deterministic calculation layer](#5-the-deterministic-calculation-layer)
6. [FinOps rules as code](#6-finops-rules-as-code)
7. [The decoupled AI layer](#7-the-decoupled-ai-layer)
8. [Error handling as a design decision](#8-error-handling-as-a-design-decision)
9. [Testing without touching the cloud](#9-testing-without-touching-the-cloud)
10. [Configuration and secrets](#10-configuration-and-secrets)
11. [Exercises to reinforce](#11-exercises-to-reinforce)
12. [Glossary](#12-glossary)

---

## 1. The problem: why monitor cloud costs

In the cloud, anyone on a team can create cost-generating resources (instances,
databases, storage) with no purchasing process. Great for speed, but it means
spend grows diffusely: dozens of services, several accounts, daily changes.

Without visibility, two problems appear:

- **Silent waste** — forgotten resources left running, test environments nobody
  shut down, old storage piling up.
- **Bill shock** — the cost is only noticed when the invoice arrives, too late
  to react.

The answer isn't "spend less at any cost," it's **seeing the spend in time to
decide**. That's where FinOps comes in.

## 2. FinOps in one sentence

> **FinOps** is the practice of bringing financial accountability to the variable
> spend model of the cloud, uniting engineering, finance, and business teams to
> make decisions based on cost data.

In practice, FinOps revolves around a cycle:

1. **Inform** — collect and organize costs (how much, where, why).
2. **Optimize** — identify waste and opportunities.
3. **Operate** — act and repeat continuously.

This project focuses on the **Inform** phase (collection and analysis) and takes
first steps into **Optimize** (the FinOps rules that raise alerts). The
**Operate** phase is on the roadmap (notifications, scheduling).

## 3. The core rule: Python computes, AI interprets

This is the project's most important design decision, and it's worth
understanding well because it shows up in almost every file.

**The problem it solves:** a language model (LLM) is great at producing text,
but it is non-deterministic and can "hallucinate" — invent a plausible-looking
number. For financial data, that's unacceptable: `$1,234.56` must not become
`$1,243.65` because the model slipped.

**The solution:** physically separate the two responsibilities.

| Responsibility | Where it lives | Property |
|---|---|---|
| Compute values | `src/analysis/` (pure Python) | Deterministic, auditable, testable |
| Interpret values | `src/ai/` (LLM) | Creative, swappable, optional |

The AI **never** receives raw AWS data to add up. It receives ready-made numbers
and only writes the natural-language reading. See `_build_prompt` in
`llama_client.py`: values go in already formatted (e.g. `f"{total:.2f} USD"`) and
the prompt explicitly instructs it *not to invent values*.

**Why this is good design, beyond accuracy:**

- **Testability** — you can test all the calculation without network or AI.
- **Vendor swap** — you can replace Llama with OpenAI, Claude, or Bedrock
  without touching the calculation logic.
- **Graceful degradation** — if the AI goes down, the number stays correct;
  only the interpretation is missing.

> **Transferable concept:** isolate what must be correct and predictable from
> what must be flexible. True for AI, but also for external integrations, caching,
> feature flags, etc.

## 4. How we talk to AWS (Cost Explorer + boto3)

All conversation with AWS lives in **a single file**: `src/aws/cost_explorer.py`.
It's the only part of the code that imports `boto3`. That's intentional — it
concentrates the external dependency in one place.

**The pieces involved:**

- **boto3** — AWS's official Python SDK. It doesn't read credentials from the
  code: it automatically looks in local credentials (AWS CLI, environment
  variables, roles). That's why the project *never* loads keys in code.
- **AWS Cost Explorer** — the AWS service that exposes costs. The API used is
  `get_cost_and_usage`.
- **AWS STS** — identity service. `get_caller_identity` answers "who am I in this
  account?" and is used to validate that credentials work (`src/test_aws.py`).

**The query, conceptually:**

```python
client = boto3.client("ce", region_name=config.AWS_REGION)
client.get_cost_and_usage(
    TimePeriod={"Start": start, "End": end},   # last N days up to today
    Granularity=config.COST_GRANULARITY,       # MONTHLY
    Metrics=[config.COST_METRIC],              # UnblendedCost
    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],  # group by service
)
```

Three cost concepts worth knowing:

- **UnblendedCost** — the "raw" cost of each item, without averaging across
  accounts. The most direct metric for analyzing what each service cost.
- **Granularity** — the time resolution: `MONTHLY`, `DAILY`, or `HOURLY`. The
  project uses monthly (cheaper to query and enough for the overview).
- **GroupBy SERVICE** — asks AWS to break the cost down per service (EC2, S3,
  Lambda...) instead of a single total.

**Least privilege:** the identity only needs `ce:GetCostAndUsage` and
`sts:GetCallerIdentity`. Granting only what's necessary is a security principle —
if the credential leaks, the damage is limited.

## 5. The deterministic calculation layer

It lives in `src/analysis/cost_analyzer.py`. Two main functions, both pure (same
input → same output, no side effects).

### `analyze_costs(costs)`

Turns the AWS response into a structured summary. In order:

1. Accumulates the value per service by summing all periods.
2. Sums the grand total.
3. Filters only services with positive cost (ignores zeros and credits).
4. Computes each service's percentage — **only if the total is positive**.
5. Finds the highest-cost service.

The return is a dictionary (`services`, `total_cost`, `percentages`,
`largest_service`...). Returning **structured data** instead of text is what lets
the next step (AI, report, tests) consume the result without parsing strings.

### `compare_periods(costs)` and division by zero

Compares the two most recent periods to find the percentage variation. The
teaching detail is here:

```python
if previous_total != 0:
    variation = ((current_total - previous_total) / previous_total) * 100
else:
    variation = None
```

If the previous period cost zero, a percentage variation **does not exist**
(dividing by zero has no result). Instead of letting the program crash or invent
a number, the code returns `None` and the report shows "unavailable."

> **Transferable concept:** handle the impossible case explicitly. An honest
> `None` beats a wrong number or a crash.

## 6. FinOps rules as code

`src/analysis/finops_rules.py` takes the already-computed numbers and applies
heuristics a FinOps analyst would apply "by hand." It is **deterministic** — no
AI, no network. The `generate_alerts` function produces three alert types:

- **Growth** — the total cost rose more than `FINOPS_GROWTH_THRESHOLD`
  (default 20%) versus the previous period. Flags a jump to investigate.
- **Concentration** — a single service represents more than
  `FINOPS_CONCENTRATION_THRESHOLD` (default 50%) of the total. Concentration
  isn't necessarily bad, but it's a risk to be aware of.
- **Top N** — ranking of the `FINOPS_TOP_N` (default 5) largest services. Pure
  "where the money is going."

Each alert is a dictionary with `type`, `severity`, and `message`. Note that the
financial "intelligence" is **Python**, not AI. The AI later only *interprets*
these alerts in prose. The thresholds are configurable via environment variables,
so FinOps policy becomes configuration, not hard-coded logic.

## 7. The decoupled AI layer

`src/ai/llama_client.py` talks to a **local Llama** (Ollama-compatible server) over
HTTP. The flow:

1. `_build_prompt(analysis, comparison, alerts)` assembles the text, injecting
   the ready-made numbers and the instruction not to invent values.
2. `interpret(...)` does a `POST` to `{LLAMA_BASE_URL}/api/generate` with the
   model, the prompt, and `stream=False`, respecting `LLAMA_TIMEOUT`.
3. Reads `data["response"]` and returns the interpretation.

**The design point is in the failure handling.** Anything that goes wrong —
refused connection, timeout, HTTP error, invalid JSON, empty response — becomes a
single `LlamaUnavailableError` with a clear message. The orchestrator
(`src/main.py`) catches that error and **carries on without the AI**: the report
comes out with correct numbers and a note explaining why the interpretation is
missing.

> **Transferable concept:** an optional dependency should fail in a
> *non-blocking* way. Always ask: "if this goes down, what can the user still do?"

## 8. Error handling as a design decision

The project doesn't use a generic `try/except` that swallows everything. It
converts low-level errors into **domain-specific exceptions**:

- boto3/botocore errors (missing credential, access denied) become
  `CostExplorerError` with a message that tells the user what to do.
- AI failures become `LlamaUnavailableError`.

And the orchestrator decides what each error means for the *process*:

- `CostExplorerError` → exits with code `1` (real failure, can't continue without
  data).
- No data in the period → code `0` with a warning (not an error, just nothing to
  show).
- AI unavailable → carries on, report without the AI section.

> **Transferable concept:** the exit code and the exception type communicate
> intent. A credential error and a "nothing to report" are different situations
> and deserve different responses.

## 9. Testing without touching the cloud

The suite in `tests/` uses `pytest` and **mocks**: it never calls real AWS or
Llama. That's possible precisely because the calculation is deterministic and the
external dependencies are isolated.

What the tests cover:

- Total cost sum, grouping (including accumulation across periods).
- Percentages and identifying the largest service.
- Period comparison and the **previous-period-zero** case (division by zero).
- Empty data and negative values/adjustments.
- The three FinOps rules (growth, concentration, top N).
- The AI client: refused connection, timeout, empty response.
- Report generation in all three formats (txt, JSON, Markdown).

Run:

```bash
uv run pytest -v
```

> **Transferable concept:** testable code and decoupled code are the same thing
> seen from different angles. If it's hard to test without the network, it's
> probably too coupled.

## 10. Configuration and secrets

`src/config.py` centralizes all parameterization. It reads environment variables
(via `python-dotenv`, optionally from a `.env`) and exposes each parameter with a
**safe default** — so the app runs with no configuration at all.

Security golden rules applied in the project:

- AWS credentials **never** in code or in Git — they come from the AWS CLI.
- `.env`, `reports/`, and `data/` stay out of version control (`.gitignore`).
- Least-privilege IAM.

## 11. Exercises to reinforce

Try these, using the code as your base:

1. **Trace a value.** Take the "Total cost" from the report and follow where it
   came from: which function computed it? From which field of the AWS response?
2. **Break it on purpose.** Disable the AI (`AI_ENABLED=false`) and run. What
   changes in the report? Now leave the AI enabled with Llama down. Same result?
   Why?
3. **Change a policy.** Lower `FINOPS_CONCENTRATION_THRESHOLD` to `10`. What new
   alerts appear? Where in the code is that threshold read?
4. **Think about the test.** If you added a rule "service X alone grew more than
   Y%", how would you test it without calling AWS?
5. **Swap the format.** Run with `REPORT_FORMAT=json` and then `markdown`. Do the
   numbers change? Does the structure? Where is the function that picks the
   format?

## 12. Glossary

- **FinOps** — cloud financial management discipline; uniting engineering and
  finance to decide based on cost data.
- **Cost Explorer** — AWS service that exposes cost and usage data.
- **boto3** — AWS's official Python SDK.
- **STS** — Security Token Service; `get_caller_identity` validates the identity.
- **UnblendedCost** — raw cost of each item, without averaging across accounts.
- **Granularity** — time resolution of the cost query (monthly, daily).
- **IAM / least privilege** — access control granting only the needed permission.
- **Deterministic** — the same input always produces the same output.
- **LLM** — Large Language Model (e.g. Llama); generates text, non-deterministic.
- **Graceful degradation** — the system stays useful even when an optional part
  fails.
- **Mock** — a fake object that simulates an external dependency in tests.

---

> For the file-by-file breakdown, see the other documents in [`docs/`](README.md):
> `architecture.md`, `code-structure.md`, `data-flow.md`, `configuration.md`,
> `aws-permissions.md`, `ai-integration.md`, `reports.md`, `error-handling.md`,
> `testing.md`.
