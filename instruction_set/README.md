# External Agent Instruction Set

This folder is the portable packet to send to any external agent that does not have repository access.

Use this packet for one job only: convert sprint goals into a canonical JSON bundle that can pass `adoctl outbox validate`.

## Packet Contents

1. `01_required_inputs.md`
2. `02_contracts_and_rules.md`
3. `03_output_expectations.md`
4. `04_generation_workflow.md`
5. `05_efficiency_notes.md`
6. `contracts/bundle.schema.json`
7. `contracts/agent_contract.yaml`
8. `contracts/planning_context.yaml`
9. `examples/minimal_bundle_template.json`
10. `examples/blocked_response_template.json`

## How To Use This Packet

1. Provide this entire folder to the agent.
2. Provide sprint-goal-specific input using `01_required_inputs.md`.
3. Require output to follow `03_output_expectations.md`.
4. Validate generated output with:
   - `python -m adoctl outbox validate <bundle>.json`

## Refresh Process (Before Sending To Agents)

Run these commands, then resend this folder:

1. `python -m adoctl sync --org-url "https://dev.azure.com/<ORG>" --project "<PROJECT>" --planning-only`
2. `python -m adoctl instruction-set export --out-dir instruction_set --policy-dir config/policy --generated-dir config/generated --schema schema/bundle.schema.json`
