"""Phase 7 research experiments for Map for Women.

Runs are reproducible and recorded: every script writes versioned JSON +
Markdown artifacts under research/artifacts/ with the evidence/risk model
versions embedded. No number in a report exists unless this harness produced
it (research-spec.md integrity rule).

Run (from this directory):
    uv run python -m research.baselines
    uv run python -m research.stress
    uv run python -m research.lifecycle
"""

__version__ = "0.1.0"
