
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
- [X] During Milestone 3, we ran into a design issue regarding local ids for work items created vs ADO generated work item ids. We want to resolve this issue with this update. Our goal is to keep ADO work item ids for all work items with such an id. That means, as soon as a work item is written to ADO and a work item is received, we want to store that work item id locally with the newly created work item. This will resolve the constant work to remap local to ADO. Another feature of this would be that all locally stored work items have either a local id or a ADO wit id. If they have a local id that means they have not been written to ADO yet and these would be the ones to process first. Additionally, with work item ids stored, linking will be much easier.
- [X] We know to improve the sync scripts from ADO to our semantics in the tool. Lets build out sync scripts for Teams, Iteration Paths, Area Paths, Key Results, and Objectives. The goal of these scripts should first query ADO to return all items of either Teams, Iteration Paths, Area Paths, Key Results, or Objectives and return a json object that dumps metadata from ADO. The sync scripts take the json dump from ADO and transform it into yaml semantics used by the tool. The tool will use these semantics to show the possible KRs, the allowed Area Paths for each Team and the allowed Iteration paths. These will be replicated in the instruction set so the agent has the minimum required context to successfully perform their duties.


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

- [X] Implement `adoctl outbox validate`:
  - [X] JSON Schema validation using `schema/bundle.schema.json`
  - [X] Policy checks:
    - [X] only parent-child
    - [X] no double nesting
    - [X] max depth 2
    - [X] required tags (if configured)
    - [X] bundle-local uniqueness of `local_id`
  - [X] Metadata checks:
    - [X] canonical types map to valid ADO WIT names
    - [X] canonical fields map to known ADO fields for that WIT
    - [X] area/iteration exists in generated paths
- [X] Emit `outbox/failed/<bundle>.report.yaml` describing failures.

Exit criteria:

- [X] A “bad” bundle never reaches `outbox/validated/`.
- [X] The report is unambiguous and actionable.

### Milestone 3: Write Engine + Audit (dry-run first)

- [X] Implement ADO writer:
  - [X] `--dry-run` prints resolved plan (no network writes). The resolved plan includes a structured output of each url called with each method to ensure the API endpoints are being called correctly. This has to be validated before moving to testing the real write.  
  - [X] Real write:
    - [X] create Features first.
    - [X] create User Stories next, link to parent via hierarchy link.
  - [X] Strictly use reference names from generated metadata and mappings (no guessing).
- [X] Audit:
  - [X] record request payloads (redacted) + response IDs
  - [X] record local_id → ado_id mapping
  - [X] record failure reason and stop

Exit criteria:

- [X] Writes stop on first failure.
- [X] Audit exists for every run.
- [X] Linking uses parent-child only.

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

- [X] Exact process template: located in `config/generated/wit_contracts/feature.yaml` and `config/generated/wit_contracts/user_story.yaml`, respecitvely.
- [X] Field ownership: decide which canonical fields you allow (`field_map.yaml`) and which are required (`field_policy.yaml`).
- [X] Tagging conventions: not required.
- [X] Auth constraints: PAT-only for MVP is assumed; storage policy env var only.
- [ ] Rollback policy: if partial writes occur, is cleanup allowed or do we only stop and audit?

## Efficiency Notes (Pragmatic)

- Cache metadata in `config/generated` and treat it as the source for validation.
- Sync only what you need (already supported via sections); add iteration/teamsettings endpoints only when required.
- Keep exported agent contract small and stable; avoid pushing huge ADO metadata into the agent surface area.

## Definition of Done (End-to-End)

- A user can define sprint goals once.
- An agent can reliably produce a canonical bundle that passes validation using the exported contract snapshot.
- `adoctl outbox validate` enforces schema/policy/metadata deterministically and never writes on failure.
- `adoctl write --dry-run` is accurate and `adoctl write` creates correct WITs/paths/links with complete audits.
