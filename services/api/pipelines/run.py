"""Pipeline CLI (docs/03 §3).

    python -m pipelines.run --dataset thar1_demo_2024 --steps all --from 2024-01 --to 2024-12
    python -m pipelines.run --command fetch-weather

Steps are registered as their milestones land. An unregistered step exits non-zero and names its milestone,
so no make target silently pretends to have run.
"""

import argparse
import sys
from collections.abc import Callable

PIPELINE_STEPS: dict[str, str] = {
    "expected": "M2",
    "detect": "M2",
    "accounting": "M3",
    "settlement": "M3",
    "om": "M3",
    "finance": "M3",
    "attribution": "M4",
    "metrics": "M4",
    "reconcile": "M4",
}
COMMANDS: dict[str, str] = {
    "fetch-weather": "M2",
    "ingest-kaggle": "M1",
    "baseline": "M3",
    "approve-baseline": "M3",
    "scenario": "M2",
}
IMPLEMENTED: dict[str, Callable[[argparse.Namespace], None]] = {}  # filled by later milestones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.run")
    parser.add_argument("--dataset")
    parser.add_argument("--steps", default="all")
    parser.add_argument("--from", dest="period_from")
    parser.add_argument("--to", dest="period_to")
    parser.add_argument("--command", choices=sorted(COMMANDS))
    args = parser.parse_args(argv)

    if args.command:
        names = [args.command]
        milestones = COMMANDS
    else:
        if not args.dataset:
            parser.error("--dataset is required for pipeline steps")
        names = list(PIPELINE_STEPS) if args.steps == "all" else args.steps.split(",")
        milestones = PIPELINE_STEPS

    for name in names:
        if name not in milestones:
            parser.error(f"unknown step {name!r}")
        if name not in IMPLEMENTED:
            print(f"step '{name}' is not implemented yet (milestone {milestones[name]})", file=sys.stderr)
            return 2
    for name in names:
        IMPLEMENTED[name](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
