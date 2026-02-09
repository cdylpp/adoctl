# Output Expectations

## Required Output Mode

Return JSON only.

Do not return:

1. markdown
2. commentary
3. code fences

## Canonical Bundle Expectations

1. Bundle is one JSON object.
2. `work_items` contains only `Feature` and `UserStory`.
3. `relations.parent_local_id` is present for every work item.
4. `acceptance_criteria` is an array of testable statements.
5. Use canonical field keys only.

## Writing Standards

1. Feature title:
   - concise, action-oriented, outcome-focused
2. User story title:
   - concise, action-oriented, outcome-focused
3. Descriptions:
   - include constraints and relevant edge cases
   - avoid implementation-level detail unless needed for acceptance

## Blocked Response Rules

If valid output is impossible due to missing inputs, return JSON-only blocked output using `examples/blocked_response_template.json`.
