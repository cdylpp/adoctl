# Specification: ADO Decomposition Outbox + Writer CLI (Centralized, Layered Config)

## 1. Purpose

Create a streamlined workflow that turns an agent-generated decomposition (Features + User Stories) into validated, bulk-created Azure DevOps (ADO) work items—without manual reformatting or copy/paste.

Core flow:

1. Agent produces canonical JSON bundle (no prose)
2. Bundle is placed in an outbox on the work device
3. CLI validates against policy + ADO metadata
4. CLI writes work items to ADO with correct Area/Iteration + parent-child links
5. CLI records audits/logs and fails safely

## 2. System Components

### A) Agent Output Contract (producer side)

- Agents output only canonical JSON (bundle format).
- Agents do not “decide” ADO field/link rules; they follow the exported contract.

Deliverables:

- AGENT.md (instructions + contract summary)
- JSON bundle schema (schema/bundle.schema.json)
- Example bundles (valid/invalid)

### B) CLI Tool (consumer/enforcer side)

A Python CLI (adoctl) that:

- loads config layers
- syncs ADO metadata into generated config
- validates bundles (schema → policy → ADO metadata)
- writes work items (dry-run + real)
- generates audits + logs

### C) Configuration Layering (separation of concerns)

To keep this centralized and non-redundant, configuration is split into three layers:

Layer 1 — Agent Configuration (behavior + output contract)
What it is: Guidance for agents on how to produce bundles.
Source of truth: your repo files (human-authored) + exported contract snapshot.

Files:

- AGENT.md (agent-facing)
- schema/bundle.schema.json (machine-facing, used by CLI)
- config/policy/kr_taxonomy.yaml (agent references KR ids, tags, etc.)

Layer 2 — Process Configuration (governance rules not derivable from ADO)
What it is: Rules about how your team uses ADO.
Source of truth: human-authored policy configs.

Examples:

- Only parent-child links
- No double nesting (Feature→Feature forbidden; UserStory→UserStory forbidden)
- Max hierarchy depth = 2 (Feature→UserStory)
- Required tagging conventions
- Enforced required fields beyond what ADO exposes

Files:

- config/policy/link_policy.yaml
- config/policy/standards.yaml
- config/policy/field_policy.yaml (what you require/allow, not what ADO has)

Layer 3 — Generated ADO Configuration (facts synced from ADO)
What it is: The “what exists” layer pulled from ADO:

- projects/teams
- area/iteration paths
- work item type definitions (fields + reference names + data types)
- (optional/best-effort) allowed values

Source of truth: ADO (synced by CLI).
Never manually edited.

Files:

- config/generated/projects.yaml
- config/generated/teams.yaml
- config/generated/paths_area.yaml
- config/generated/paths_iteration.yaml
- config/generated/wit_contract.yaml
- config/generated/_sync_state.yaml

Key principle:

- Layer 2 decides what is permitted
- Layer 3 decides what is possible
- Validation requires both

⸻

## 3. Canonical Bundle Format (Agent → Outbox)

- One JSON file per request (“bundle”).
- Contains: schema_version, bundle_id, context, work_items[]
- Work items use canonical keys: type, title, description, acceptance_criteria, tags, fields, relations.parent_local_id
- Only relationship supported in bundle: parent_local_id

Outbox layout:

- `outbox/ready/` agent drops files here
- `outbox/validated/` passed validation
- `outbox/failed/` failed validation (with report)
- `outbox/archived/` successfully written (with audit reference)

⸻

## 4. CLI Responsibilities (adoctl)

4.1 Sync (ADO → generated config)
Command: `adoctl sync [--all|--projects|--paths|--wit]`

- Pull metadata from ADO
- Generate/overwrite files in config/generated/
- Record _sync_state.yaml (timestamps, org/project, versions)

4.2 Validate (bundle → pass/fail + report)
Command: `adoctl outbox validate <bundle|--all>`
Validation order:

1. JSON schema validation (structure)
2. Process policy validation (link rules, required fields, naming, tag rules)
3. ADO metadata validation (paths exist, fields exist/type match)

Failure: move to outbox/failed/ + write validation report
Success: move to outbox/validated/

4.3 Write (validated bundle → ADO)
Command: `adoctl write <bundle|--all-validated> [--dry-run] [--area X] [--iteration Y]`
Write behavior:

- dry-run prints plan and resolved overrides
- real write creates Features first, then User Stories
- links stories to feature parents
- fails safe: stop on first failure, audit everything

4.4 Audit + Logging

- `audit/<timestamp>_write.yaml|json` per run
- structured logs in `logs/adoctl.log`
- redaction of secrets always

⸻

## 5. “Centralized” Truth Model (No Redundancy)

- ADO-derived facts live only in `config/generated/*`
- Team process rules live only in `config/policy/*`
- Agent behavior rules live only in AGENT.md + schema
- CLI composes them at runtime:
- effective contract = policy ∩ generated capabilities

⸻

## 6. Definition of Done

- An agent can produce a valid JSON bundle with no reformatting.
- `adoctl sync` produces generated configs.
- `adoctl outbox validate` enforces policy + ADO constraints.
- `adoctl write --dry-run` shows plan and catches issues early.
- `adoctl` write creates correct WITs, correct paths, correct parent-child links.
- Every run creates an audit record and fails safely.