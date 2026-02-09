# Roadmap: Resilient Sprint Goals -> Agent Bundle -> Valid ADO Work Items

## Why This Exists

The end-state goal (per `specs.md`) is a safe, repeatable pipeline:

1. A user defines sprint goals and context (project/team/iteration).
2. An agent produces a canonical JSON bundle (Features + User Stories).
3. `adoctl` validates the bundle against:
   - schema (structure),
   - policy (team governance),
   - ADO-generated metadata (what is possible).
4. `adoctl` writes work items to ADO (dry-run first), links via parent-child, and emits audits.

The architecture must be:

- Resilient under change (ADO fields/WITs evolve, policies change, agent prompts evolve).
- Correct (no guessing, explicit mappings, deterministic validation).
- Efficient (cache metadata locally, incremental sync, fail fast).
- Safe by default (no writes unless validation passes, support `--dry-run`, audit always).

## Current State (Codebase Snapshot)

- ADO metadata sync exists: `adoctl sync` writes `config/generated/*` (`projects`, `paths`, `teams`, `wit_contract`, `_sync_state`).
- Offline bootstrap for WIT contracts exists from extracted JSON: `adoctl bootstrap-wit-contracts` writes:
  - `config/generated/wit_contract.yaml` (aggregate)
  - `config/generated/wit_contracts/*.yaml` (per-type)
- Home/context UX exists (local operator context): `config/local/context.yaml`.
- Outbox validation and ADO writing are not implemented yet.

## Target Workflow (Operator + Agent + CLI)

### A) Operator defines sprint goals (human-authored)

Introduce a small, explicit sprint planning input file (human-owned, versionable):

- `outbox/goals/2026-02-sprint03.yaml` (example name)
- Contains:
  - `org_url`, `project`, `team`
  - `iteration_path` (or a reference to “current iteration” resolution)
  - optional `area_path`
  - goal statements / KR references / constraints
  - required tags conventions (e.g., `KR-2`, `bundle_id`, program tag)

Key design rule: this file is NOT derived from ADO; it is a “what we intend to do” input and should be stable and reviewable.

### B) Agent generates canonical bundle (machine-authored)

Agent output must be:

- JSON-only, conforming to `schema/bundle.schema.json`.
- Uses canonical types (currently `Feature` and `UserStory`) and `relations.parent_local_id`.
- Uses only allowed canonical `fields` keys exported by `adoctl` (no guessing).

### C) `adoctl outbox validate` produces a deterministic report

Validation order (fail-fast, zero writes on any failure):

1. Schema validation (JSON Schema).
   1. Must provide feedback on proper validation if this fails.
   2. Still continues on the rest of the work items.
2. Policy validation (link rules, required tags/fields, local id uniqueness).
   1. If fails: should provide instructions on what to fix.
3. Metadata validation (ADO feasibility):
   - work item types exist
   - required ADO fields exist
   - field values match expected types/allowed values when known
   - area/iteration paths exist

Output:

- `outbox/validated/<bundle>.json` on success
- `outbox/failed/<bundle>.json` + a machine-readable report on failure

### D) `adoctl write` performs safe creation and linking

Write plan:

- Resolve effective context (iteration/area defaults + per-item overrides).
- Create parent work items first (Features), then children (User Stories).
- Link via parent-child relation only.
- Emit audit artifact on success or failure.
- Stop on first error (fail fast).

Idempotency strategy (recommended):

- Require a unique `bundle_id` tag to be applied to every created item (policy).
- Write emits a mapping of `local_id -> ado_id` in audit.
- A second run can be “detect-only” unless explicitly permitted to update.

## Key Architectural Decisions for Resilience

### 1) Separate “Canonical Fields” from “ADO Fields”

The bundle `fields` object should be treated as canonical keys (team-defined), not raw ADO reference names.

Why:

- ADO reference names vary by process/template and custom fields.
- Canonical keys let you keep the agent contract stable while mapping changes in one place.

Implementation:

- Add a policy-owned mapping file, for example:
  - `config/policy/field_map.yaml`
  - Maps canonical keys (e.g., `story_points`) to ADO reference names (e.g., `Microsoft.VSTS.Scheduling.StoryPoints`).
- Validation enforces:
  - Bundle `fields` keys MUST exist in `field_map.yaml` (no guessing).
  - The mapped ADO field MUST exist in the generated WIT metadata.

### 2) Make WIT name mapping explicit and configurable

The bundle type enum is currently `Feature`/`UserStory`, but ADO might use different WIT names (e.g., `Product Backlog Item`).

Implementation:

- Add `config/policy/wit_map.yaml`, mapping canonical type -> ADO work item type name:
  - `Feature -> Feature`
  - `UserStory -> User Story` (or `Product Backlog Item`)
- Validation uses `wit_map.yaml` to check existence and to drive writer endpoints.

### 3) Generate an “Effective Agent Contract” snapshot

Agents should not read internal ADO metadata and policy directly; they should consume a single exported contract snapshot that is stable and self-contained.

Add a CLI command:

- `adoctl contract export`
- Output:
  - JSON (or YAML) file containing:
    - supported canonical `type` values
    - allowed canonical `fields` keys + descriptions
    - required tags conventions
    - link rules (parent-child only)
    - semantic writing standards from policy
    - optionally: a minimal subset of WIT required fields (Title, Description, Acceptance Criteria, etc.)

This enables “resilience under change”:

- When ADO metadata changes, `adoctl sync` + `adoctl contract export` updates the agent contract.
- Agents follow the exported contract; the bundle stays valid by construction.

### 4) Treat `config/generated/*` as cache with schema versions

Generated config should be:

- Overwritten only by `adoctl sync` (or `bootstrap-wit-contracts` as initial seed).
- Self-describing with `schema_version`, `generated_at_utc`, `source`.
- Validated by `adoctl` before use.

Add internal validation for generated files:

- On `adoctl outbox validate`, confirm `config/generated/wit_contract.yaml` and `paths_*` exist and match expected schema.
- Fail clearly if generated config is missing or stale.

### 5) Prefer ADO-derived field types when available

`data.json` bootstrap extract does not include field types; `adoctl sync` does.

Recommendation:

- Keep bootstrap as “seed only”.
- Prefer `adoctl sync --wit-only` to refresh field types/read-only/required flags from ADO when credentials are available.
- Validation can run in two modes:
  - “strict”: requires typed WIT metadata (preferred)
  - “best-effort”: uses bootstrap metadata (required/default/help) when types are unknown

## Concrete Module Boundaries (So It Stays Maintainable)

Proposed packages:

- `adoctl/config/`
  - Load policy layer (`config/policy/*`)
  - Load generated layer (`config/generated/*`)
  - Compose effective contract view models
- `adoctl/validation/`
  - `schema_validate(bundle)`
  - `policy_validate(bundle, policy)`
  - `metadata_validate(bundle, generated)`
  - Emits a structured report object (serializable)
- `adoctl/outbox/`
  - Move files between `ready/validated/failed/archived`
  - Write validation reports next to bundles
- `adoctl/ado_client/`
  - HTTP primitives + a small typed client layer for:
    - create work item
    - update work item (add relation)
    - resolve current iteration for team (optional enhancement)
- `adoctl/audit/`
  - Append-only audit artifacts for every write attempt
  - Redaction utilities

Key rule: validation must not depend on writer; writer must depend on validation outputs.
