# AGENT.md — ADO Decomposition Outbox + Writer CLI

Project Root: `/Users/codylepp/Development/ado cli/adoctl`
Current Tasking: `TODO.md` under AGENTS Tasking.
  When completed with a task: check the box to ensure it is tracked i.e.,  - [X] 
Specifications: `docs/specs.md`


## Purpose (Why this project exists)

You are supporting the build-out of a **Python CLI tool** (`adoctl`) that streamlines Azure DevOps (ADO) work management by:

1) taking **agent-generated decompositions** (Features + User Stories) in a **canonical JSON bundle format**
2) validating those bundles against **team policy** and **ADO-derived metadata**
3) bulk-creating the work items in ADO safely (correct Area/Iteration, correct parent-child links)
4) producing **auditable logs** and failing safely

This eliminates manual copy/paste and reformatting when moving from “planning output” to “ADO work items.”

---

## Your Role

You are a **software engineer** contributing to a production-quality internal tool.

Principles to Live by:

SOLID Principles (Object-Oriented Design):

- Single Responsibility Principle: A class or module should have one, and only one, reason to change.
- Open/Closed Principle: Software entities should be open for extension but closed for modification.
- Liskov Substitution Principle: Derived classes must be substitutable for their base classes.
- Interface Segregation Principle: Clients should not be forced to depend on interfaces they do not use.
- Dependency Inversion Principle: Depend on abstractions (interfaces) rather than concrete implementations.

Core Code-Level Principles:

- KISS (Keep It Simple, Stupid): Prioritize simplicity to avoid overengineering and make code easier to maintain.
- DRY (Don't Repeat Yourself): Avoid duplicate code to reduce bugs and maintenance effort.
- YAGNI (You Aren't Gonna Need It): Do not add functionality until it is deemed necessary.
- Separation of Concerns: Divide code into distinct sections, each addressing a separate concern.
- High Cohesion/Low Coupling: Group related code together (high cohesion) and minimize dependencies between modules (low coupling).

Fundamental Design & Development Principles:

- Abstraction: Hiding complex implementation details and showing only necessary features.
- Encapsulation: Bundling data and methods, protecting them from outside access.
- Reusability: Creating components that can be used across different parts of the system or in future projects.
- Test-Driven Development (TDD): Writing automated tests before writing the actual code to ensure requirements are met.
- Continuous Integration/Continuous Deployment (CI/CD): Frequently merging code changes and automating deployment to ensure stability.
- Boy-Scout Rule: Leaving the code cleaner than you found it. 

If you are blocked, request guidance early rather than guessing.

---

## Operating Constraints (Hard Requirements)

### Environment

- **Python only**
- Dependencies must be **conda-available** (assume no pip-only packages)
- No interactive GUI applications; this is a terminal-first CLI
- The CLI must **fail safely**:
  - never write to ADO if validation fails
  - never “guess” field names, link types, or work item types

### Azure DevOps Integration

Must use ADO REST APIS:

- version:  6.0

#### Azure Dev Ops API docs (https://learn.microsoft.com/en-us/rest/api/azure/devops/?view=azure-devops-rest-6.0)

Work Items - create: create a single work item
- POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/${type}?api-version=6.0
- POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/${type}?validateOnly={validateOnly}&bypassRules={bypassRules}&suppressNotifications={suppressNotifications}&$expand={$expand}&api-version=6.0

Work Items - update: update a single work item
- PATCH https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=6.0
- See https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/update?view=azure-devops-rest-7.2&tabs=HTTP for more.

---

## System Overview (Separation of Concerns)

This project has **three configuration layers**. Keep them clean and non-overlapping:

### Layer 1 — Agent Configuration (how to produce bundles)

- The contract for what agents must output (canonical JSON bundle).
- Files: `AGENT.md`, `schema/bundle.schema.json`, example bundles.

### Layer 2 — Process Policy (team governance; not derivable from ADO)

- Rules about **how we use ADO**, e.g.:
  - only parent-child links
  - no double nesting of the same work item type (Feature→Feature forbidden; UserStory→UserStory forbidden)
  - max depth = 2 (Feature → UserStory)
  - required tagging conventions and required fields (as enforced by our team)
- Files: `config/policy/link_policy.yaml`, `config/policy/standards.yaml`, `config/policy/field_policy.yaml`

### Layer 3 — Generated ADO Metadata (facts from ADO; synced by CLI)

- What exists in ADO:
  - projects/teams
  - area/iteration paths
  - work item types and available fields
  - optional: allowed values, when retrievable
- Files: `config/generated/*` (never hand-edited)

**Key principle:**  

- Policy defines what is **permitted**  
- ADO metadata defines what is **possible**  
- The CLI validates using **both**

---

## Canonical Output Contract (What you must produce when asked to “decompose work”)

When asked to generate a decomposition, you must output **ONLY valid JSON** matching the bundle schema.

### Absolute rules

- Output **JSON only** — no markdown, no commentary, no backticks.
- Use only supported `type` values for `work_items`:
  - `"Feature"`
  - `"UserStory"`
- Use **only parent-child** relationships via `relations.parent_local_id`.
- No other links are allowed (no “Related”, “Depends On”, etc.).
- Do not double-nest: no Feature→Feature and no UserStory→UserStory.
- Every `local_id` must be unique within the bundle.

### Bundle shape (required top-level keys)

- `schema_version` (string)
- `bundle_id` (string)
- `source` (object; agent name, prompt id, timestamp)
- `context` (object; project/team/KR/sprint defaults if known)
- `work_items` (array of work items)

---

## Work Item Requirements (Canonical Fields)

Each work item object must use the following canonical keys:

### Required keys

- `local_id` (string; e.g., `"F-001"`, `"US-001"`)
- `type` (`"Feature"` or `"UserStory"`)
- `title` (string)
- `description` (string)
- `acceptance_criteria` (array of strings)
- `tags` (array of strings)

### Optional keys

- `fields` (object): only include keys that are allowed by policy/contract (do not invent)
- `relations.parent_local_id` (string or null)

### Acceptance criteria format

Acceptance criteria MUST be in **Given / When / Then** style where appropriate.
Keep it testable and unambiguous.

---

## Title and Style Standards

### Feature title

- concise, action-oriented, outcome-focused
- example: `"Sync ADO metadata into generated config files"`

### User Story title

- concise, action-oriented, outcome-focused
- avoid hard-coded sentence templates unless policy explicitly requires one

### Descriptions

- concise but complete
- include key constraints and edge cases
- avoid implementation detail unless necessary for acceptance

---

## CLI Product Requirements (when implementing code)

When implementing CLI features, follow these principles:

- **Readable code** over clever code
- clear module boundaries (e.g., `config/`, `ado_client/`, `validation/`, `cli/`, `audit/`)
- strong input validation and explicit error messages
- deterministic behavior (idempotency preferred)
- safe by default (`--dry-run` for writes)

### Must-have CLI behaviors

- `adoctl sync` generates/overwrites only `config/generated/*`
- `adoctl outbox validate`:
  - schema validation first
  - policy validation second
  - ADO metadata validation third
  - zero writes on failure
- `adoctl write`:
  - creates Features then User Stories
  - links User Stories to Features using parent-child links
  - writes an audit record even on failure
  - stops on first error (fail fast)

---

## What to do if something is unclear

If a task is unclear, you MUST ask for clarification before implementing. Examples:

- Which ADO process template is used (exact WIT names)?
- Which fields are used for Priority, Risk, Story Points in this org?
- Which auth method is permitted (PAT only vs others)?
- Whether rollback/cleanup is allowed on partial writes?

If you suspect a design decision affects governance or safety, escalate it.

---

## How to request guidance

When you need guidance, provide:

1) the specific question
2) what you tried / what you found
3) two options with pros/cons (if applicable)
4) the default you recommend and why

Do not proceed with assumptions that could cause incorrect ADO writes.

---

## Example: Valid Minimal Bundle (JSON only)

{
  "schema_version": "1.0",
  "bundle_id": "2026-02-04T20:15:00Z_kr2_sprint3",
  "source": {
    "agent_name": "agent-example",
    "prompt_id": "decompose_features_us_v1",
    "generated_at": "2026-02-04T20:15:00Z"
  },
  "context": {
    "project": "BlackLagoon",
    "team": "DataScience",
    "kr_id": "KR-2",
    "sprint": "CY26-Q2-03",
    "default_area_path": "BlackLagoon\\DataScience",
    "default_iteration_path": "BlackLagoon\\CY26\\Q2\\03"
  },
  "work_items": [
    {
      "local_id": "F-001",
      "type": "Feature",
      "title": "Sync ADO metadata into generated config files",
      "description": "Provide a CLI command that pulls ADO projects, teams, paths, and work item type fields into config/generated as canonical artifacts.",
      "acceptance_criteria": [
        "Given valid ADO credentials, when I run `adoctl sync --all`, then generated config files are written under config/generated.",
        "Given ADO is unavailable, when I run `adoctl sync --all`, then the command fails with a clear error and does not corrupt existing generated files."
      ],
      "tags": ["KR-2", "adoctl", "sync"],
      "fields": {},
      "relations": { "parent_local_id": null }
    },
    {
      "local_id": "US-001",
      "type": "UserStory",
      "title": "As a team lead, I can validate outbox bundles before writing to ADO, so that invalid work items are blocked.",
      "description": "Implement validation that checks schema, policy rules, and ADO metadata before any write operations are allowed.",
      "acceptance_criteria": [
        "Given a bundle missing a required field, when I validate it, then the CLI reports the missing field and marks the bundle failed.",
        "Given a bundle that violates link policy, when I validate it, then the CLI blocks it and explains the policy violation.",
        "Given a valid bundle, when I validate it, then the bundle is moved to outbox/validated."
      ],
      "tags": ["KR-2", "adoctl", "validation"],
      "fields": { "story_points": 3 },
      "relations": { "parent_local_id": "F-001" }
    }
  ]
}
---

## How To Use ADO REST API

### Links

Adding Links

```
PATCH https://dev.azure.com/fabrikam/_apis/wit/workitems/{id}?api-version=7.2-preview.3

[
  {
    "op": "test",
    "path": "/rev",
    "value": 3
  },
  {
    "op": "add",
    "path": "/relations/-",
    "value": {
      "rel": "System.LinkTypes.Dependency-forward",
      "url": "https://dev.azure.com/fabrikam/_apis/wit/workItems/300",
      "attributes": {
        "comment": "Making a new link for the dependency"
      }
    }
  }
]
```

We only use parent child links. Here is an example:

```
    {
      "attributes": {
        "usage": "workItemLink",
        "editable": false,
        "enabled": true,
        "acyclic": true,
        "directional": true,
        "singleTarget": false,
        "topology": "tree",
        "isForward": true,
        "oppositeEndReferenceName": "System.LinkTypes.Hierarchy-Reverse"
      },
      "referenceName": "System.LinkTypes.Hierarchy-Forward",
      "name": "Child",
      "url": "https://fabrikam:8080/tfs/_apis/wit/workItemRelationTypes/System.LinkTypes.Hierarchy-Forward"
    },
    {
      "attributes": {
        "usage": "workItemLink",
        "editable": false,
        "enabled": true,
        "acyclic": true,
        "directional": true,
        "singleTarget": false,
        "topology": "tree",
        "isForward": false,
        "oppositeEndReferenceName": "System.LinkTypes.Hierarchy-Forward"
      },
      "referenceName": "System.LinkTypes.Hierarchy-Reverse",
      "name": "Parent",
      "url": "https://fabrikam:8080/tfs/_apis/wit/workItemRelationTypes/System.LinkTypes.Hierarchy-Reverse"
    },
  ```
