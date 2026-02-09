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
