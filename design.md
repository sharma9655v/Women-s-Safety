# Design Specification

## Goals
- Safety-aware, not safety-guaranteeing
- Dynamic and honest about freshness
- Explainable
- Privacy-preserving
- GIS-first
- ML only when data supports it
- Graceful degradation in data-sparse areas

## User flow
Origin → destination → travel mode → safety preference
→ generate candidate routes
→ map-match segments
→ retrieve evidence
→ apply freshness/reliability
→ predict risk
→ calculate uncertainty
→ rank
→ explain

Outputs:
1. Safety Priority
2. Balanced
3. Time Priority

## Route card
Show:
- estimated safety
- confidence
- distance
- ETA
- reasons
- data freshness
- warnings
- alternative

Use wording such as:
“Estimated safety: 84/100”
“Confidence: 89%”
Never “Safe: 84/100”.

## Evidence states
VERIFIED
REPORTED
CORROBORATED
CONFLICTING
EXPIRED
REJECTED

Never overwrite old evidence.

## Freshness
Baseline:
freshness = exp(-lambda * age)

Use data-type-specific decay rates. Do not use one universal decay rate in final research.

## Risk model
Initial baseline: deterministic rules.
ML later: XGBoost/LightGBM.

Features:
- incident count/recency
- lighting evidence
- lighting confidence
- emergency-facility distance
- public transport accessibility
- activity proxy
- road infrastructure
- time/day
- weather
- recent reports
- evidence age
- evidence conflict

Output:
risk_probability + calibrated confidence/uncertainty.

## Routing
C(segment) =
alpha*distance + beta*time + gamma*risk + delta*uncertainty

Safety preference changes weights.

## Failure states
Sparse data → “Limited safety data” + low confidence.
Conflicting evidence → “Conflicting recent evidence” + higher uncertainty.
Routing failure → explicit error, never fake route.
ML unavailable → deterministic fallback.

## Privacy
- No continuous location history by default.
- Pseudonymous reports.
- Strip unnecessary image metadata.
- Encrypt sensitive fields.
- Explicit opt-in for live sharing.
