# Required Inputs For Any Agent

An agent must receive all of the following before generating work-item bundles.

## Mandatory Inputs

1. Sprint goals and outcomes:
   - objective text
   - KR references
   - scope boundaries
2. Delivery context:
   - `project`
   - `team`
   - `sprint` or iteration reference
   - `default_area_path`
   - `default_iteration_path`
3. Constraints:
   - dependencies
   - compliance or governance restrictions
   - explicit exclusions
4. Contracts:
   - `contracts/bundle.schema.json`
   - `contracts/agent_contract.yaml`
   - `contracts/planning_context.yaml`

## Input Quality Requirements

1. Parent context must be explicit:
   - if features must map to known KR/parent IDs, provide those IDs directly
2. Paths must be valid:
   - provide area/iteration values that exist in ADO metadata
   - team-scoped work should use team defaults from `planning_context.yaml`
   - non-team work (Objectives, project-level requests, and applicable Key Results) should use project backlog defaults from `planning_context.yaml`
3. No ambiguous ownership:
   - if `owner` is required by contract/policy, provide assignable owner values

## If Inputs Are Missing

The agent must not guess. It must return a blocked JSON response (see `examples/blocked_response_template.json`) listing missing inputs.
