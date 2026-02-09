# Efficiency Notes

These are the operational efficiency constraints that keep the system stable.

## Core Efficiency Rules

1. Treat `config/generated` metadata as the source for validation.
2. Sync only necessary metadata sections unless full refresh is required.
3. Keep the exported agent contract compact and stable.

## Practical Guidance For External Agents

1. Do not request full ADO metadata payloads when `agent_contract.yaml` already provides the needed canonical surface area.
2. Prefer minimal canonical fields that still satisfy required field policy.
3. Avoid adding optional fields unless explicitly requested by sprint goals.

## Quality And Performance

1. Smaller, contract-compliant bundles validate faster.
2. Deterministic parent linking reduces rewrite/rework.
3. Fewer non-essential fields reduces policy drift and mapping breakage.
