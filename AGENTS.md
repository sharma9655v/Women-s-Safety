# Agent Instructions

## Non-negotiable
1. Never guarantee safety.
2. Never invent data, APIs, datasets, model accuracy or scores.
3. Never treat stale data as current.
4. Preserve evidence history.
5. Show uncertainty when evidence is weak.
6. Do not expose reporter identity.
7. Keep ML separate from UI and routing.
8. Add tests for safety-scoring logic.
9. Version datasets and models.

## Before coding
Read:
README.md
resources.md
design.md
architecture.md
data-model.md
research-spec.md

## Coding order
1. deterministic map/routing
2. evidence engine
3. tests
4. reports
5. ML
6. research experiments

## Definition of done
API validation + errors + tests + privacy review + traceable model/data version + uncertainty-aware UI.
