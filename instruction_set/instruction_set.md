# Portable Agent Instruction Set

This document is machine-assembled by `adoctl instruction-set export` and is intended to be shared as a single, complete instruction payload for external agents.

When earlier sections reference `contracts/agent_contract.yaml`, `contracts/bundle.schema.json`, or `contracts/planning_context.yaml`, use sections 06, 07, and 08 in this document.

## 01 Required Inputs

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
   - if `owner` is used, provide assignable owner values from `planning_context.yaml`
   - default org policy uses `display_name` for owner identity values (`System.AssignedTo`)

## If Inputs Are Missing

The agent must not guess. It must return a blocked JSON response (see `examples/blocked_response_template.json`) listing missing inputs.

## 02 Contracts And Rules

# Contracts And Rules

This system has two mandatory contracts.

## 1) Structural Contract

Source: `contracts/bundle.schema.json`

Required top-level keys:

1. `schema_version`
2. `bundle_id`
3. `source`
4. `context`
5. `work_items`

Required per-work-item keys:

1. `local_id`
2. `type`
3. `title`
4. `description`
5. `acceptance_criteria`
6. `relations.parent_local_id`

Allowed `type` values:

1. `Feature`
2. `UserStory`

## 2) Semantic Contract

Source: `contracts/agent_contract.yaml`

The agent must obey:

1. Supported canonical types (`canonical.supported_types`)
2. Canonical field mappings (`canonical.field_mappings`)
3. Link policy (`rules.link_policy`)
4. Standards (`rules.standards.work_item_standards`)
5. Field policy (`field_policy.allowed_fields`, `field_policy.required_fields`)

## Hard Rules

1. Parent-child links only (`relations.parent_local_id`)
2. No Feature to Feature nesting
3. No UserStory to UserStory nesting
4. No unknown canonical field keys
5. No invented ADO field names or work item types
6. Every `local_id` must be unique within the bundle

## 03 Output Expectations

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
   - markdown/plain-text description is acceptable; writer converts it to ADO-compatible HTML

## Blocked Response Rules

If valid output is impossible due to missing inputs, return JSON-only blocked output using `examples/blocked_response_template.json`.

## 04 Generation Workflow

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

## 05 Efficiency Notes

# Efficiency Notes

These are the operational efficiency constraints that keep the system stable.

## Core Efficiency Rules

1. Treat `config/generated` metadata as the source for validation.
2. Sync only necessary metadata sections unless full refresh is required.
3. Keep the exported agent contract compact and stable.
4. Sync planning context (`--planning-only`) to refresh team-scoped paths and Objective/Key Result context without pulling unrelated metadata.
5. Use `python -m adoctl instruction-set export ...` to refresh all instruction-set contracts in one step instead of manual copy operations.

## Practical Guidance For External Agents

1. Do not request full ADO metadata payloads when `agent_contract.yaml` already provides the needed canonical surface area.
2. Prefer minimal canonical fields that still satisfy required field policy.
3. Avoid adding optional fields unless explicitly requested by sprint goals.

## Quality And Performance

1. Smaller, contract-compliant bundles validate faster.
2. Deterministic parent linking reduces rewrite/rework.
3. Fewer non-essential fields reduces policy drift and mapping breakage.

## 06 Agent Contract

```yaml
# MACHINE-GENERATED FILE. DO NOT EDIT BY HAND.
# Generated by `adoctl contract export`.
# Edit config/policy/*.yaml (and refresh config/generated/wit_contract.yaml) to change this contract.

schema_version: '1.0'
generated_at_utc: '2026-02-10T18:03:52.641286+00:00'
canonical:
  supported_types:
  - Feature
  - UserStory
  field_mappings:
  - canonical_key: acceptance_criteria
    reference_name: Microsoft.VSTS.Common.AcceptanceCriteria
    applies_to:
    - UserStory
    description: Specific requirements that define done for this user story.
  - canonical_key: area_path
    reference_name: System.AreaPath
    applies_to:
    - Feature
    - UserStory
    description: The area of the product with which this feature is associated.
  - canonical_key: description
    reference_name: System.Description
    applies_to:
    - Feature
    - UserStory
    description: Primary narrative body for the work item.
  - canonical_key: iteration_path
    reference_name: System.IterationPath
    applies_to:
    - Feature
    - UserStory
    description: Iteration path that plans the work item.
  - canonical_key: owner
    reference_name: System.AssignedTo
    applies_to:
    - Feature
    - UserStory
    description: Person currently accountable for the work item.
  - canonical_key: priority
    reference_name: Microsoft.VSTS.Common.Priority
    applies_to:
    - Feature
    - UserStory
    description: Business priority ordering. Integer value 1 - 5
  - canonical_key: risk
    reference_name: Microsoft.VSTS.Common.Risk
    applies_to:
    - Feature
    description: Risk classification for Feature work.
  - canonical_key: state
    reference_name: System.State
    applies_to:
    - Feature
    - UserStory
    description: Workflow state value.
  - canonical_key: story_points
    reference_name: Microsoft.VSTS.Scheduling.StoryPoints
    applies_to:
    - UserStory
    description: Relative size estimate. Use the fibonacci series 1 - 8.
  - canonical_key: title
    reference_name: System.Title
    applies_to:
    - Feature
    - UserStory
    description: Work item title. Clear, concise encapsulation of the work.
  - canonical_key: value_area
    reference_name: Microsoft.VSTS.Common.ValueArea
    applies_to:
    - Feature
    - UserStory
    description: Value area classification (Business or Architectural).
rules:
  link_policy:
    allowed_link_types:
    - parent-child
    max_depth: 2
    forbid_double_nesting:
    - KeyResult
    - Feature
    - UserStory
  standards:
    required_tags: []
    work_item_standards:
      Feature:
        area_path:
          preferred_format: Black Lagoon\[Team]\[FunctionalArea]\[ProductName]
          rule: Set area path relative to the execution team. If the product is not
            defined yet, then set it to default format.
        definition_of_done:
          required: true
          rule: Definition of done must be explicit in description content.
        dependencies:
          code_format: dependency:N#
          rule: Track dependencies in description using dependency code.
        description:
          template: As a <persona>, I need <capability>, so that <outcome>.
        iteration_path:
          preferred_format: Black Lagoon\[Team]
          rule: If iteration is known, assign the specific iteration; otherwise assign
            the team backlog iteration.
        links:
          constraints:
          - Use parent-child hierarchy.
          - Do not nest Feature under Feature.
          required_parent_type: Key Result
        planning_horizon:
          maximum: 1 quarter
          minimum: 2 sprints
        release_plan:
          allowed_values:
          - NOW
          - NEAR
          - FAR
          mapping:
            FAR: Quarter month 3
            NEAR: Quarter month 2
            NOW: Quarter month 1
          required: true
        title:
          rule: Concise, action-oriented title; keep simple and de-duplicate data.
      UserStory:
        acceptance_criteria:
          format: (AC N). Given / When / Then
          required: true
          rule: Specific, testable definition of done.
        description:
          template: As a <persona>, I need <capability>, so that <outcome>.
        links:
          chain_requirement: Parent Feature should aggregate to a Key Result.
          required_parent_type: Feature
        owner:
          required: false
          rule: Assign an accountable individual.
        story_points:
          allowed_values:
          - 1
          - 2
          - 3
          - 5
          - 8
          guidance: Estimate complexity/effort, not time.
          method: Fibonacci
          required: true
          t_shirt_map:
            '1': small
            '2': medium
            '3': large
            '5': XL
            '8': XXL
        title:
          rule: Clear, meaningful title containing the action to be completed.
mapping:
  wit_map:
    Feature: Feature
    UserStory: User Story
  field_map:
    acceptance_criteria: Microsoft.VSTS.Common.AcceptanceCriteria
    area_path: System.AreaPath
    description: System.Description
    iteration_path: System.IterationPath
    owner: System.AssignedTo
    priority: Microsoft.VSTS.Common.Priority
    risk: Microsoft.VSTS.Common.Risk
    state: System.State
    story_points: Microsoft.VSTS.Scheduling.StoryPoints
    title: System.Title
    value_area: Microsoft.VSTS.Common.ValueArea
ado_capabilities:
  Feature:
    ado_work_item_type: Feature
    available_fields:
    - Microsoft.VSTS.Build.IntegrationBuild
    - Microsoft.VSTS.Common.ActivatedBy
    - Microsoft.VSTS.Common.ActivatedDate
    - Microsoft.VSTS.Common.BusinessValue
    - Microsoft.VSTS.Common.ClosedBy
    - Microsoft.VSTS.Common.ClosedDate
    - Microsoft.VSTS.Common.Priority
    - Microsoft.VSTS.Common.ResolvedBy
    - Microsoft.VSTS.Common.ResolvedDate
    - Microsoft.VSTS.Common.ResolvedReason
    - Microsoft.VSTS.Common.Risk
    - Microsoft.VSTS.Common.StackRank
    - Microsoft.VSTS.Common.StateChangeDate
    - Microsoft.VSTS.Common.TimeCriticality
    - Microsoft.VSTS.Common.ValueArea
    - Microsoft.VSTS.Scheduling.Effort
    - Microsoft.VSTS.Scheduling.StartDate
    - Microsoft.VSTS.Scheduling.TargetDate
    - System.AreaId
    - System.AreaLevel1
    - System.AreaLevel2
    - System.AreaLevel3
    - System.AreaLevel4
    - System.AreaLevel5
    - System.AreaLevel6
    - System.AreaLevel7
    - System.AreaPath
    - System.AssignedTo
    - System.AttachedFileCount
    - System.AuthorizedAs
    - System.AuthorizedDate
    - System.BoardColumn
    - System.BoardColumnDone
    - System.BoardLane
    - System.ChangedBy
    - System.ChangedDate
    - System.CommentCount
    - System.CreatedBy
    - System.CreatedDate
    - System.Description
    - System.ExternalLinkCount
    - System.History
    - System.HyperLinkCount
    - System.Id
    - System.IterationId
    - System.IterationLevel1
    - System.IterationLevel2
    - System.IterationLevel3
    - System.IterationLevel4
    - System.IterationLevel5
    - System.IterationLevel6
    - System.IterationLevel7
    - System.IterationPath
    - System.NodeName
    - System.Parent
    - System.Reason
    - System.RelatedLinkCount
    - System.RemoteLinkCount
    - System.Rev
    - System.RevisedDate
    - System.State
    - System.Tags
    - System.TeamProject
    - System.Title
    - System.Watermark
    - System.WorkItemType
    required_fields:
    - Microsoft.VSTS.Common.Priority
    - Microsoft.VSTS.Common.ValueArea
    - System.AreaId
    - System.IterationId
    - System.State
    - System.Title
  UserStory:
    ado_work_item_type: User Story
    available_fields:
    - Custom.CRQ#
    - Microsoft.VSTS.Build.IntegrationBuild
    - Microsoft.VSTS.Common.AcceptanceCriteria
    - Microsoft.VSTS.Common.ActivatedBy
    - Microsoft.VSTS.Common.ActivatedDate
    - Microsoft.VSTS.Common.ClosedBy
    - Microsoft.VSTS.Common.ClosedDate
    - Microsoft.VSTS.Common.Priority
    - Microsoft.VSTS.Common.ResolvedBy
    - Microsoft.VSTS.Common.ResolvedDate
    - Microsoft.VSTS.Common.ResolvedReason
    - Microsoft.VSTS.Common.Risk
    - Microsoft.VSTS.Common.StackRank
    - Microsoft.VSTS.Common.StateChangeDate
    - Microsoft.VSTS.Common.ValueArea
    - Microsoft.VSTS.Scheduling.FinishDate
    - Microsoft.VSTS.Scheduling.StartDate
    - Microsoft.VSTS.Scheduling.StoryPoints
    - System.AreaId
    - System.AreaLevel1
    - System.AreaLevel2
    - System.AreaLevel3
    - System.AreaLevel4
    - System.AreaLevel5
    - System.AreaLevel6
    - System.AreaLevel7
    - System.AreaPath
    - System.AssignedTo
    - System.AttachedFileCount
    - System.AuthorizedAs
    - System.AuthorizedDate
    - System.BoardColumn
    - System.BoardColumnDone
    - System.BoardLane
    - System.ChangedBy
    - System.ChangedDate
    - System.CommentCount
    - System.CreatedBy
    - System.CreatedDate
    - System.Description
    - System.ExternalLinkCount
    - System.History
    - System.HyperLinkCount
    - System.Id
    - System.IterationId
    - System.IterationLevel1
    - System.IterationLevel2
    - System.IterationLevel3
    - System.IterationLevel4
    - System.IterationLevel5
    - System.IterationLevel6
    - System.IterationLevel7
    - System.IterationPath
    - System.NodeName
    - System.Parent
    - System.Reason
    - System.RelatedLinkCount
    - System.RemoteLinkCount
    - System.Rev
    - System.RevisedDate
    - System.State
    - System.Tags
    - System.TeamProject
    - System.Title
    - System.Watermark
    - System.WorkItemType
    required_fields:
    - Microsoft.VSTS.Common.ValueArea
    - System.AreaId
    - System.IterationId
    - System.State
    - System.Title
planning:
  available: true
  source_path: config/generated/planning_context.yaml
  project: Black Lagoon
  core_team: Black Lagoon
  project_backlog_defaults:
    iteration_path: Black Lagoon
    area_path: Black Lagoon
  teams:
  - id: 737dd9ec-a9fa-41ff-8723-70c60f3c5736
    name: Data Science and Analytics
    default_iteration_path: Black Lagoon\Data Science and Analytics
    default_area_path: Black Lagoon\Data Science and Analytics
    allowed_iteration_paths:
    - Black Lagoon\DSA\25-00
    - Black Lagoon\DSA\25-01
    - Black Lagoon\DSA\25-02
    - Black Lagoon\DSA\25-03
    - Black Lagoon\DSA\25-04
    - Black Lagoon\DSA\25-05
    - Black Lagoon\DSA\26-00
    - Black Lagoon\DSA\26-Q1-01
    - Black Lagoon\DSA\26-Q1-02
    - Black Lagoon\DSA\26-Q1-03
    - Black Lagoon\DSA\26-Q1-04
    - Black Lagoon\DSA\26-Q1-05
    - Black Lagoon\DSA\26-Q1-06
    - Black Lagoon\DSA\FY26-Q2-01
    - Black Lagoon\DSA\FY26-Q2-02
    - Black Lagoon\DSA\FY26-Q2-03
    - Black Lagoon\DSA\FY26-Q2-04
    - Black Lagoon\DSA\FY26-Q2-05
    - Black Lagoon\DSA\FY26-Q2-06
    - Black Lagoon\DSA\FY26-Q3-01
    - Black Lagoon\DSA\FY26-Q3-02
    - Black Lagoon\DSA\FY26-Q3-03
    - Black Lagoon\DSA\FY26-Q3-04
    - Black Lagoon\DSA\FY26-Q3-05
    - Black Lagoon\DSA\FY26-Q3-06
    - Black Lagoon\Data Science and Analytics
    allowed_area_paths:
    - Black Lagoon\Data Science and Analytics
    team_settings_iteration_paths:
    - Black Lagoon\DSA\25-00
    - Black Lagoon\DSA\25-01
    - Black Lagoon\DSA\25-02
    - Black Lagoon\DSA\25-03
    - Black Lagoon\DSA\25-04
    - Black Lagoon\DSA\25-05
    - Black Lagoon\DSA\26-00
    - Black Lagoon\DSA\26-Q1-01
    - Black Lagoon\DSA\26-Q1-02
    - Black Lagoon\DSA\26-Q1-03
    - Black Lagoon\DSA\26-Q1-04
    - Black Lagoon\DSA\26-Q1-05
    - Black Lagoon\DSA\26-Q1-06
    - Black Lagoon\DSA\FY26-Q2-01
    - Black Lagoon\DSA\FY26-Q2-02
    - Black Lagoon\DSA\FY26-Q2-03
    - Black Lagoon\DSA\FY26-Q2-04
    - Black Lagoon\DSA\FY26-Q2-05
    - Black Lagoon\DSA\FY26-Q2-06
    - Black Lagoon\DSA\FY26-Q3-01
    - Black Lagoon\DSA\FY26-Q3-02
    - Black Lagoon\DSA\FY26-Q3-03
    - Black Lagoon\DSA\FY26-Q3-04
    - Black Lagoon\DSA\FY26-Q3-05
    - Black Lagoon\DSA\FY26-Q3-06
    team_settings_area_paths: []
  - id: 154af80d-9194-484b-8b47-bde168a596f0
    name: Digital Transformation
    default_iteration_path: Black Lagoon\Digital Transformation
    default_area_path: Black Lagoon\Digital Transformation
    allowed_iteration_paths:
    - Black Lagoon\DT\FY26-Q2-01
    - Black Lagoon\DT\FY26-Q2-02
    - Black Lagoon\DT\FY26-Q2-03
    - Black Lagoon\DT\Sprint 69
    - Black Lagoon\DT\Sprint 70
    - Black Lagoon\DT\Sprint 71
    - Black Lagoon\DT\Sprint 72
    - Black Lagoon\DT\Sprint 73
    - Black Lagoon\DT\Sprint 74
    - Black Lagoon\DT\Sprint 75
    - Black Lagoon\Digital Transformation
    allowed_area_paths:
    - Black Lagoon\Digital Transformation
    team_settings_iteration_paths:
    - Black Lagoon\DT\FY26-Q2-01
    - Black Lagoon\DT\FY26-Q2-02
    - Black Lagoon\DT\FY26-Q2-03
    - Black Lagoon\DT\Sprint 69
    - Black Lagoon\DT\Sprint 70
    - Black Lagoon\DT\Sprint 71
    - Black Lagoon\DT\Sprint 72
    - Black Lagoon\DT\Sprint 73
    - Black Lagoon\DT\Sprint 74
    - Black Lagoon\DT\Sprint 75
    team_settings_area_paths: []
  - id: c3484290-7096-457a-8735-4efc433a427f
    name: KM
    default_iteration_path: Black Lagoon\KM
    default_area_path: Black Lagoon\KM
    allowed_iteration_paths:
    - Black Lagoon\KM
    - Black Lagoon\KM\FY26-Q2-01
    - Black Lagoon\KM\FY26-Q2-02
    - Black Lagoon\KM\FY26-Q2-03
    - Black Lagoon\KM\FY26-Q2-04
    - Black Lagoon\KM\FY26-Q2-05
    - Black Lagoon\KM\FY26-Q2-06
    - Black Lagoon\KM\FY26-Q3-01
    - Black Lagoon\KM\FY26-Q3-02
    - Black Lagoon\KM\FY26-Q3-03
    - Black Lagoon\KM\FY26-Q3-04
    - Black Lagoon\KM\FY26-Q3-05
    - Black Lagoon\KM\FY26-Q3-06
    - Black Lagoon\KM\FY26-Q4-01
    - Black Lagoon\KM\FY26-Q4-02
    - Black Lagoon\KM\FY26-Q4-03
    - Black Lagoon\KM\FY26-Q4-04
    - Black Lagoon\KM\FY26-Q4-05
    - Black Lagoon\KM\FY26-Q4-06
    - Black Lagoon\KM\KM Sprint 2
    - Black Lagoon\KM\KM Sprint 3
    - Black Lagoon\KM\Sprint 0
    - Black Lagoon\KM\Sprint 1
    allowed_area_paths:
    - Black Lagoon\KM
    team_settings_iteration_paths:
    - Black Lagoon\KM\FY26-Q2-01
    - Black Lagoon\KM\FY26-Q2-02
    - Black Lagoon\KM\FY26-Q2-03
    - Black Lagoon\KM\FY26-Q2-04
    - Black Lagoon\KM\FY26-Q2-05
    - Black Lagoon\KM\FY26-Q2-06
    - Black Lagoon\KM\FY26-Q3-01
    - Black Lagoon\KM\FY26-Q3-02
    - Black Lagoon\KM\FY26-Q3-03
    - Black Lagoon\KM\FY26-Q3-04
    - Black Lagoon\KM\FY26-Q3-05
    - Black Lagoon\KM\FY26-Q3-06
    - Black Lagoon\KM\FY26-Q4-01
    - Black Lagoon\KM\FY26-Q4-02
    - Black Lagoon\KM\FY26-Q4-03
    - Black Lagoon\KM\FY26-Q4-04
    - Black Lagoon\KM\FY26-Q4-05
    - Black Lagoon\KM\FY26-Q4-06
    - Black Lagoon\KM\KM Sprint 2
    - Black Lagoon\KM\KM Sprint 3
    - Black Lagoon\KM\Sprint 0
    - Black Lagoon\KM\Sprint 1
    team_settings_area_paths: []
  objectives:
  - id: 10140
    title: 'Train / Organize '
    state: New
    work_item_type: Objective
    area_path: Black Lagoon
    iteration_path: Black Lagoon
    assigned_to: null
    parent_id: null
  - id: 10141
    title: Equip
    state: New
    work_item_type: Objective
    area_path: Black Lagoon
    iteration_path: Black Lagoon
    assigned_to: null
    parent_id: null
  - id: 10213
    title: Man
    state: New
    work_item_type: Objective
    area_path: Black Lagoon
    iteration_path: Black Lagoon
    assigned_to: null
    parent_id: null
  - id: 10214
    title: Modernize
    state: New
    work_item_type: Objective
    area_path: Black Lagoon
    iteration_path: Black Lagoon
    assigned_to: null
    parent_id: null
  - id: 10215
    title: Sustain
    state: New
    work_item_type: Objective
    area_path: Black Lagoon
    iteration_path: Black Lagoon
    assigned_to: null
    parent_id: null
  key_results: []
  orphan_key_results: []
field_policy:
  allowed_fields:
    Feature:
    - area_path
    - description
    - iteration_path
    - owner
    - priority
    - risk
    - state
    - title
    - value_area
    UserStory:
    - acceptance_criteria
    - area_path
    - description
    - iteration_path
    - owner
    - priority
    - state
    - story_points
    - title
    - value_area
  required_fields:
    Feature:
    - area_path
    - description
    - iteration_path
    - priority
    - state
    - title
    - value_area
    UserStory:
    - acceptance_criteria
    - area_path
    - description
    - iteration_path
    - priority
    - state
    - story_points
    - title
    - value_area
  description_required_sections:
    Feature:
    - definition of done
    - dependencies
    - release plan
    UserStory: []
  description_optional_sections:
    Feature: []
    UserStory: []
  generated_required_fields:
    Feature:
    - priority
    - state
    - title
    - value_area
    UserStory:
    - state
    - title
    - value_area
  effective_required_fields:
    Feature:
    - area_path
    - description
    - iteration_path
    - priority
    - state
    - title
    - value_area
    UserStory:
    - acceptance_criteria
    - area_path
    - description
    - iteration_path
    - priority
    - state
    - story_points
    - title
    - value_area
  export_work_item_types:
  - Feature
  - UserStory
  owner_identity_format: display_name
validation:
  mapping_coverage_issues: []
  strict_ready: true
```

## 07 Bundle Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ADO Decomposition Bundle",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "bundle_id", "source", "context", "work_items"],
  "properties": {
    "schema_version": { "type": "string" },
    "bundle_id": { "type": "string" },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": ["agent_name", "prompt_id", "generated_at"],
      "properties": {
        "agent_name": { "type": "string" },
        "prompt_id": { "type": "string" },
        "generated_at": { "type": "string" }
      }
    },
    "context": {
      "type": "object",
      "additionalProperties": true
    },
    "work_items": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["local_id", "type", "title", "description", "acceptance_criteria", "relations"],
        "properties": {
          "local_id": { "type": "string" },
          "type": { "type": "string", "enum": ["Feature", "UserStory"] },
          "title": { "type": "string" },
          "description": { "type": "string" },
          "acceptance_criteria": {
            "type": "array",
            "items": { "type": "string" }
          },
          "fields": {
            "type": "object",
            "additionalProperties": true
          },
          "relations": {
            "type": "object",
            "additionalProperties": false,
            "required": ["parent_local_id"],
            "properties": {
              "parent_local_id": { "type": "string", "minLength": 1 }
            }
          }
        }
      }
    }
  }
}
```

## 08 Planning Context

```yaml
# MACHINE-GENERATED FILE. DO NOT EDIT BY HAND.
# Generated by `adoctl sync`.
# User-managed policy files live under config/policy/*.yaml.

schema_version: '1.0'
generated_at_utc: '2026-02-09T19:26:45.568978+00:00'
project: Black Lagoon
core_team: Black Lagoon
project_backlog_defaults:
  iteration_path: Black Lagoon
  area_path: Black Lagoon
teams:
- id: 737dd9ec-a9fa-41ff-8723-70c60f3c5736
  name: Data Science and Analytics
  default_iteration_path: Black Lagoon\Data Science and Analytics
  default_area_path: Black Lagoon\Data Science and Analytics
  allowed_iteration_paths:
  - Black Lagoon\DSA\25-00
  - Black Lagoon\DSA\25-01
  - Black Lagoon\DSA\25-02
  - Black Lagoon\DSA\25-03
  - Black Lagoon\DSA\25-04
  - Black Lagoon\DSA\25-05
  - Black Lagoon\DSA\26-00
  - Black Lagoon\DSA\26-Q1-01
  - Black Lagoon\DSA\26-Q1-02
  - Black Lagoon\DSA\26-Q1-03
  - Black Lagoon\DSA\26-Q1-04
  - Black Lagoon\DSA\26-Q1-05
  - Black Lagoon\DSA\26-Q1-06
  - Black Lagoon\DSA\FY26-Q2-01
  - Black Lagoon\DSA\FY26-Q2-02
  - Black Lagoon\DSA\FY26-Q2-03
  - Black Lagoon\DSA\FY26-Q2-04
  - Black Lagoon\DSA\FY26-Q2-05
  - Black Lagoon\DSA\FY26-Q2-06
  - Black Lagoon\DSA\FY26-Q3-01
  - Black Lagoon\DSA\FY26-Q3-02
  - Black Lagoon\DSA\FY26-Q3-03
  - Black Lagoon\DSA\FY26-Q3-04
  - Black Lagoon\DSA\FY26-Q3-05
  - Black Lagoon\DSA\FY26-Q3-06
  - Black Lagoon\Data Science and Analytics
  allowed_area_paths:
  - Black Lagoon\Data Science and Analytics
  team_settings_iteration_paths:
  - Black Lagoon\DSA\25-00
  - Black Lagoon\DSA\25-01
  - Black Lagoon\DSA\25-02
  - Black Lagoon\DSA\25-03
  - Black Lagoon\DSA\25-04
  - Black Lagoon\DSA\25-05
  - Black Lagoon\DSA\26-00
  - Black Lagoon\DSA\26-Q1-01
  - Black Lagoon\DSA\26-Q1-02
  - Black Lagoon\DSA\26-Q1-03
  - Black Lagoon\DSA\26-Q1-04
  - Black Lagoon\DSA\26-Q1-05
  - Black Lagoon\DSA\26-Q1-06
  - Black Lagoon\DSA\FY26-Q2-01
  - Black Lagoon\DSA\FY26-Q2-02
  - Black Lagoon\DSA\FY26-Q2-03
  - Black Lagoon\DSA\FY26-Q2-04
  - Black Lagoon\DSA\FY26-Q2-05
  - Black Lagoon\DSA\FY26-Q2-06
  - Black Lagoon\DSA\FY26-Q3-01
  - Black Lagoon\DSA\FY26-Q3-02
  - Black Lagoon\DSA\FY26-Q3-03
  - Black Lagoon\DSA\FY26-Q3-04
  - Black Lagoon\DSA\FY26-Q3-05
  - Black Lagoon\DSA\FY26-Q3-06
  team_settings_area_paths: []
- id: 154af80d-9194-484b-8b47-bde168a596f0
  name: Digital Transformation
  default_iteration_path: Black Lagoon\Digital Transformation
  default_area_path: Black Lagoon\Digital Transformation
  allowed_iteration_paths:
  - Black Lagoon\DT\FY26-Q2-01
  - Black Lagoon\DT\FY26-Q2-02
  - Black Lagoon\DT\FY26-Q2-03
  - Black Lagoon\DT\Sprint 69
  - Black Lagoon\DT\Sprint 70
  - Black Lagoon\DT\Sprint 71
  - Black Lagoon\DT\Sprint 72
  - Black Lagoon\DT\Sprint 73
  - Black Lagoon\DT\Sprint 74
  - Black Lagoon\DT\Sprint 75
  - Black Lagoon\Digital Transformation
  allowed_area_paths:
  - Black Lagoon\Digital Transformation
  team_settings_iteration_paths:
  - Black Lagoon\DT\FY26-Q2-01
  - Black Lagoon\DT\FY26-Q2-02
  - Black Lagoon\DT\FY26-Q2-03
  - Black Lagoon\DT\Sprint 69
  - Black Lagoon\DT\Sprint 70
  - Black Lagoon\DT\Sprint 71
  - Black Lagoon\DT\Sprint 72
  - Black Lagoon\DT\Sprint 73
  - Black Lagoon\DT\Sprint 74
  - Black Lagoon\DT\Sprint 75
  team_settings_area_paths: []
- id: c3484290-7096-457a-8735-4efc433a427f
  name: KM
  default_iteration_path: Black Lagoon\KM
  default_area_path: Black Lagoon\KM
  allowed_iteration_paths:
  - Black Lagoon\KM
  - Black Lagoon\KM\FY26-Q2-01
  - Black Lagoon\KM\FY26-Q2-02
  - Black Lagoon\KM\FY26-Q2-03
  - Black Lagoon\KM\FY26-Q2-04
  - Black Lagoon\KM\FY26-Q2-05
  - Black Lagoon\KM\FY26-Q2-06
  - Black Lagoon\KM\FY26-Q3-01
  - Black Lagoon\KM\FY26-Q3-02
  - Black Lagoon\KM\FY26-Q3-03
  - Black Lagoon\KM\FY26-Q3-04
  - Black Lagoon\KM\FY26-Q3-05
  - Black Lagoon\KM\FY26-Q3-06
  - Black Lagoon\KM\FY26-Q4-01
  - Black Lagoon\KM\FY26-Q4-02
  - Black Lagoon\KM\FY26-Q4-03
  - Black Lagoon\KM\FY26-Q4-04
  - Black Lagoon\KM\FY26-Q4-05
  - Black Lagoon\KM\FY26-Q4-06
  - Black Lagoon\KM\KM Sprint 2
  - Black Lagoon\KM\KM Sprint 3
  - Black Lagoon\KM\Sprint 0
  - Black Lagoon\KM\Sprint 1
  allowed_area_paths:
  - Black Lagoon\KM
  team_settings_iteration_paths:
  - Black Lagoon\KM\FY26-Q2-01
  - Black Lagoon\KM\FY26-Q2-02
  - Black Lagoon\KM\FY26-Q2-03
  - Black Lagoon\KM\FY26-Q2-04
  - Black Lagoon\KM\FY26-Q2-05
  - Black Lagoon\KM\FY26-Q2-06
  - Black Lagoon\KM\FY26-Q3-01
  - Black Lagoon\KM\FY26-Q3-02
  - Black Lagoon\KM\FY26-Q3-03
  - Black Lagoon\KM\FY26-Q3-04
  - Black Lagoon\KM\FY26-Q3-05
  - Black Lagoon\KM\FY26-Q3-06
  - Black Lagoon\KM\FY26-Q4-01
  - Black Lagoon\KM\FY26-Q4-02
  - Black Lagoon\KM\FY26-Q4-03
  - Black Lagoon\KM\FY26-Q4-04
  - Black Lagoon\KM\FY26-Q4-05
  - Black Lagoon\KM\FY26-Q4-06
  - Black Lagoon\KM\KM Sprint 2
  - Black Lagoon\KM\KM Sprint 3
  - Black Lagoon\KM\Sprint 0
  - Black Lagoon\KM\Sprint 1
  team_settings_area_paths: []
objectives:
- id: 10140
  title: 'Train / Organize '
  state: New
  work_item_type: Objective
  area_path: Black Lagoon
  iteration_path: Black Lagoon
  assigned_to: null
  parent_id: null
- id: 10141
  title: Equip
  state: New
  work_item_type: Objective
  area_path: Black Lagoon
  iteration_path: Black Lagoon
  assigned_to: null
  parent_id: null
- id: 10213
  title: Man
  state: New
  work_item_type: Objective
  area_path: Black Lagoon
  iteration_path: Black Lagoon
  assigned_to: null
  parent_id: null
- id: 10214
  title: Modernize
  state: New
  work_item_type: Objective
  area_path: Black Lagoon
  iteration_path: Black Lagoon
  assigned_to: null
  parent_id: null
- id: 10215
  title: Sustain
  state: New
  work_item_type: Objective
  area_path: Black Lagoon
  iteration_path: Black Lagoon
  assigned_to: null
  parent_id: null
key_results: []
orphan_key_results: []
```
