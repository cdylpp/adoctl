
# TODO

## AGENT Tasks

- [X] Add menu options for CLI to select team
- [X] Store selected team in config files
- [X] Load team upon starting the CLI
- [X] Display the "home" screen for the CLI as the first them: show ORG, PROJECT, TEAM, and CURRENT ITERATION. If these are not added to the config files, add them. Allow the user to change these variables at anytime when using the CLI. 
- [X] The welcome screen should be user friendly in the sense that it should be very clear, neat and easy to read.

## Product Owner / Process Owner (you / team lead)

- Define and lock:
- allowed link rules (already: parent-child only, no double nesting)
- required fields per WIT (what you enforce)
- naming/tagging standards
- Provide initial KR taxonomy file (kr_taxonomy.yaml)
- Decide supported auth method (PAT vs other) for MVP

## ADO SME / Admin (or whoever knows your process template)

- Confirm work item type names used by your ADO process:
- “Feature” vs “Product Backlog Item” vs custom
- “User Story” vs other
- Confirm which ADO fields your org uses for priority/risk/story points
- Confirm path conventions and project/team boundaries

## CLI Engineer

- Implement:
- config loader + layer composition
- sync command and serializers for generated config
- validation engine (schema + policy + metadata)
- ADO writer (create + link + audit + safe failure)
- clean CLI UX and logging

## Agent Prompt/Contract Author

- Draft AGENT.md using:
- canonical JSON bundle schema
- effective contract exports (what fields/types are allowed)
- Provide example prompts and sample outputs (good/bad)

## QA / Tester

- Build test bundles:
- valid feature/story bundle
- invalid nesting, invalid link, missing fields, unknown area/iteration
- Verify:
- validation stops writes
- audit/log output is complete and readable
- idempotency behavior (if implemented)

## Security / Compliance (as applicable)

- Approve secrets handling:
- PAT storage (env var only recommended)
- logging redaction policy
- location of audit artifacts
