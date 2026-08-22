"""Training entry point.

Refuses to run until the Phase 6 gate is open. Running this script does not
train anything — by design. When the gate passes, this file is where training
starts, with dataset + model version captured in models/registry.json.
"""

from __future__ import annotations

import sys

from ml.gate import MIN_SPAN_DAYS, MIN_VERIFIED_OBSERVATIONS, check_gate


def main() -> int:
    report = check_gate()
    print(
        f"Gate: verified={report.verified_observations}, "
        f"span={report.span_days:.1f}d "
        f"(need {MIN_VERIFIED_OBSERVATIONS} verified over {MIN_SPAN_DAYS}d)"
    )
    if not report.open:
        print(f"TRAINING REFUSED — gate closed: {report.reason}")
        return 3
    print("Gate open — training would proceed here (nothing trained in this build).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
