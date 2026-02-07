
# TODO

## AGENT Tasks

- [X] Add menu options for CLI to select team
- [X] Store selected team in config files
- [X] Load team upon starting the CLI
- [X] Display the "home" screen for the CLI as the first them: show ORG, PROJECT, TEAM, and CURRENT ITERATION. If these are not added to the config files, add them. Allow the user to change these variables at anytime when using the CLI. 
- [X] The welcome screen should be user friendly in the sense that it should be very clear, neat and easy to read.
- [X] With the extracted work item types along with their fields. Create a yaml config for each work item type. The goal of this is the same as `sync` however, we have extracted the data for you. These yaml files will be supplied to any agent tasked with creating work items in the future. These are the core contracts that must be upheld by any agent.
- [X] Develop agent instruction file which is a single, portable, and shareable file that is passed to any agent before prompting the agent for work decomposition. This file should be easily shared with any agent. This file should detail every instruction that is required for the agent to start taking sprint goals and translating them into canonical json. It is input that this instruction set can be injested, ported to a wide variety of agents.
- [X] Add a policy-owned mapping file, for example: `config/policy/field_map.yaml`; Maps canonical keys (e.g., `story_points`) to ADO reference names (e.g., `Microsoft.VSTS.Scheduling.StoryPoints`).
- [X] Add `config/policy/wit_map.yaml`, mapping canonical type -> ADO work item type name:
  - `Feature -> Feature`
  - `UserStory -> User Story` (or `Product Backlog Item`)
  - Validation uses `wit_map.yaml` to check existence and to drive writer endpoints.
- [X] Current gap: `field_policy.yaml` is not yet wired into `adoctl contract export`, so updating it will not yet show up in `agent_contract.yaml` automatically. This is important so the user can modifiy the policy yml and the changes will propagate throughout the system. Here is the order of importance. (1) Anything **required** by `wit_contract.yaml` takes precedence over `field_policy.yaml`. For example, if a work item has a required field in wit contract and field does not list it as required, update the `field_policy.yaml` so that it matches wit contract. However, if wit_contract does not specify that a field is required, then field_policy can make this tighter by saying it is required. The backward modification is not required.
- [X] Given the descriptions and context work item in `./docs`, update the yaml files in `./policy` to match what is specified in `./docs`. More explicitly, update `field_policy.yaml` based on the following specifications: `Blockers`, `Critical-Business-Decisions`, `Features`, `Iterations`, `Key-Results`, `Linking`, `Risks`, `User-Stories`, and `Work-Items` in `./docs`. 

## Implementation Plan (Phased Milestones)

### Milestone 1: Contract + Config Composition (offline-ready)

- [X] Define `wit_map.yaml` and `field_map.yaml` policy files (skeleton + examples).
- [X] Implement config loaders that validate structure and provide typed accessors.
- [X] Implement `adoctl contract export` to produce a single agent-consumable contract snapshot.
- [X] Add examples showing how an agent uses the exported contract to create valid bundle JSON.

Exit criteria:

- You can generate a contract snapshot from `config/policy/*` + `config/generated/*`.
- The contract snapshot changes deterministically with policy/ADO metadata updates.

### Milestone 2: Outbox Validate (schema → policy → metadata)

- Implement `adoctl outbox validate`:
  - JSON Schema validation using `schema/bundle.schema.json`
  - Policy checks:
    - only parent-child
    - no double nesting
    - max depth 2
    - required tags (if configured)
    - user story title format rule
    - bundle-local uniqueness of `local_id`
  - Metadata checks:
    - canonical types map to valid ADO WIT names
    - canonical fields map to known ADO fields for that WIT
    - area/iteration exists in generated paths
- Emit `outbox/failed/<bundle>.report.yaml` describing failures.

Exit criteria:

- A “bad” bundle never reaches `outbox/validated/`.
- The report is unambiguous and actionable.

### Milestone 3: Write Engine + Audit (dry-run first)

- Implement ADO writer:
  - `--dry-run` prints resolved plan (no network writes)
  - Real write:
    - create Features first
    - create User Stories next, link to parent via hierarchy link
  - Strictly use reference names from generated metadata and mappings (no guessing).
- Audit:
  - record request payloads (redacted) + response IDs
  - record local_id → ado_id mapping
  - record failure reason and stop

Exit criteria:

- Writes stop on first failure.
- Audit exists for every run.
- Linking uses parent-child only.

### Milestone 4: “Sprint Goals” UX and Iteration Resilience

- Introduce optional `goals` file format + loader.
- Add ability to resolve “current iteration” for a team via ADO REST:
  - store the resolved iteration in local context + in audit for traceability
- Add validation rule: bundle’s iteration/area defaults must be resolvable without guessing.

Exit criteria:

- Operator can declare goals once, then generate many bundles consistently.
- Iteration changes don’t break the pipeline (explicit resolution step).

### Milestone 5: Hardening (change management, CI, safety)

- Schema versioning policy:
  - bump when bundle or contract shape changes
  - keep compatibility logic explicit (no silent coercion)
- Test suite:
  - golden bundles (valid/invalid)
  - policy violations
  - metadata violations
  - writer dry-run plan snapshots
- Logging + redaction:
  - ensure PAT never appears in logs/audits
- Add `adoctl doctor` command to verify prerequisites:
  - generated configs present
  - policy files present
  - contract export up to date

Exit criteria:

- CI runs unit tests and catches regressions.
- Operator gets clear diagnostics for missing/stale config.

## Open Questions (Need Decisions Before Writer Is “Production Safe”)

- Exact process template: confirm the ADO WIT names for “Feature” and “User Story” equivalents.
- Field ownership: decide which canonical fields you allow (`field_map.yaml`) and which are required (`field_policy.yaml`).
- Tagging conventions: require `bundle_id` tag? KR tags? sprint tag?
- Auth constraints: PAT-only for MVP is assumed; confirm storage policy (env var only recommended).
- Rollback policy: if partial writes occur, is cleanup allowed or do we only stop and audit?

## Efficiency Notes (Pragmatic)

- Cache metadata in `config/generated` and treat it as the source for validation.
- Sync only what you need (already supported via sections); add iteration/teamsettings endpoints only when required.
- Keep exported agent contract small and stable; avoid pushing huge ADO metadata into the agent surface area.

## Definition of Done (End-to-End)

- A user can define sprint goals once.
- An agent can reliably produce a canonical bundle that passes validation using the exported contract snapshot.
- `adoctl outbox validate` enforces schema/policy/metadata deterministically and never writes on failure.
- `adoctl write --dry-run` is accurate and `adoctl write` creates correct WITs/paths/links with complete audits.
