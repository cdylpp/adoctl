# Generation Workflow

Use this sequence for every decomposition task.

## Steps

1. Read sprint goal inputs from the user.
2. Read `contracts/bundle.schema.json`.
3. Read `contracts/agent_contract.yaml`.
4. Read `contracts/planning_context.yaml`.
5. Build Features aligned to goals.
6. Build UserStories under Features with `relations.parent_local_id`.
7. Populate canonical `fields` using only allowed canonical keys.
8. Apply defaults from planning context:
   - team work defaults to `project\\team` backlog paths
   - project-level work defaults to project backlog paths
9. Validate output against the checklist below.
10. Return JSON only.

## Pre-Output Checklist

1. `bundle_id` exists and matches sprint context.
2. All `local_id` values are unique.
3. Every parent link references a valid parent local ID or known external parent ID supplied in inputs.
4. All required canonical fields for each type are present.
5. No field keys appear that are absent from contract mappings.
6. Acceptance criteria are concrete and testable.

## Fail-Safe Reminder

When uncertain, block and ask for missing inputs. Do not infer unsupported values.
