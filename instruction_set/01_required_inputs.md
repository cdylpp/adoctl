# Required Inputs For Any Agent

An agent must receive all of the following before generating work-item bundles.

## Expected Inputs

1. Sprint goals and outcomes:
   - high-level objective text
   - KR references, these must be in the form of a title or a KR id. You may assume the KR id exists despite explicit knowledge of this fact.
   - scope boundaries. These may also be inferred by the agent based on high-level objectives and agent understanding of project/task breakdown.
2. Delivery context:
   - `sprint` or iteration reference
3. Constraints (Optional):
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
   - provide area/iteration values that exist in ADO metadata. Use `planning_context.yaml` as source of truth for path names.
   - team-scoped work should use team defaults from `planning_context.yaml`
   - non-team work (Objectives, project-level requests, and applicable Key Results) should use project backlog defaults from `planning_context.yaml`
3. No ambiguous ownership:
   - if `owner` is used, provide assignable owner values from `planning_context.yaml`
   - default org policy uses `display_name` for owner identity values (`System.AssignedTo`)

## If Inputs Are Missing

The agent must not guess. It must return a blocked JSON response (see `examples/blocked_response_template.json`) listing missing inputs.
