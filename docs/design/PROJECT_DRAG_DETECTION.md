# Project Drag Detection

## 1. Founder-Approved Capability

Vidurai should detect and explain when AI agents appear to be unnecessarily extending a project through redundant tests, repeated approvals, duplicated reviews, invented edge cases, scope expansion, excessive handoffs, or rising effort without a newly discovered risk.

Vidurai must distinguish:

### Genuine assurance
* security
* migrations
* destructive operations
* data integrity
* production changes
* release gates
* shared contract changes
* newly discovered concrete defects

### Avoidable project drag
* repeating unchanged tests
* requesting approval for routine reversible work
* adding tests with no approved acceptance criterion
* repeatedly reviewing already accepted behaviour
* introducing edge cases unrelated to current risk
* expanding scope after contract freeze
* repeated agent handoffs without ownership
* increasing ETA without new evidence
* reporting completion without executing required work
* contradictory reports that create avoidable review cycles

## 2. Counsellor Behaviour

Vidurai must remain advisory.

It should:
```
observe
→ compare work against approved acceptance criteria
→ detect possible drag
→ explain the evidence
→ propose the fastest safe path
→ estimate effort saved
→ state residual risk
→ let the human decide
```

It must not:
* silently cancel tests
* block agents without an explicit human rule
* override the founder
* treat all additional testing as waste
* suppress genuine security or data-integrity work
* optimise speed at the expense of correctness

## 3. Candidate Drag Assessment Output

```json
{
  "status": "possible_drag",
  "confidence": 0.86,
  "evidence": [
    "The same test suite was run three times without relevant code changes.",
    "Nine proposed checks do not map to approved acceptance criteria."
  ],
  "necessary_steps": [
    "Run the migration rollback test.",
    "Compile the modified VS Code extension."
  ],
  "possibly_redundant_steps": [
    "Repeat the unchanged packaging suite.",
    "Run a second broad architecture review."
  ],
  "fastest_safe_path": [
    "Run the two acceptance-mapped checks.",
    "Fix only observed failures.",
    "Proceed to the commit gate."
  ],
  "estimated_effort_saved": "2–4 hours",
  "residual_risk": "Low",
  "human_decision_required": true
}
```

*Note: This is a candidate internal contract, not a locked public API.*

## 4. Minimum Signals Required

Candidate inputs for detecting drag:
* approved scope
* acceptance criteria
* changed files
* test commands and results
* code-change timestamps
* approval requests
* agent handoffs
* estimated effort changes
* unresolved defects
* current task owner
* completed versus proposed tasks

Vidurai should not infer drag only from elapsed time.
It must use evidence such as:
```
additional proposed work
without:
- relevant code change
- new risk
- failed acceptance criterion
- new founder requirement
```

## 5. Initial Detection Rules

Candidate rules:

### Repeated test rule
Flag when the same test is proposed again while:
* relevant files have not changed
* the previous run passed
* no environment or dependency changed

### Approval-loop rule
Flag when an agent requests approval for routine reversible actions already covered by an approved package.

### Scope-growth rule
Flag when new tasks are introduced after scope freeze without:
* a new defect
* a new requirement
* a security or data-integrity reason

### Handoff-churn rule
Flag when work moves repeatedly between agents without:
* a clear owner
* a completed output
* a meaningful capability reason

### ETA-growth rule
Flag when effort estimates increase materially without corresponding new evidence or scope.

### Contradictory-report rule
Flag when an agent states:
* tests passed while command output shows failures
* working tree is clean while uncommitted changes exist
* implementation is complete while required output is absent

## 6. Trust and Restraint

Apply the approved Vidurai doctrine:
* minimum sufficient truth
* counsel without control
* evidence, interpretation, and recommendation remain separate
* decisions are inspectable and reversible
* direct Human–AI communication remains possible

Every drag warning should separate:
```
Evidence:
What happened.

Interpretation:
Why it may represent unnecessary drag.

Counsel:
The faster safe path.

Decision:
Human approval or rejection.
```
