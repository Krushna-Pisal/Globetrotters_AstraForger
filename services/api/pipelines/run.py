"""Pipeline CLI (docs/03 §3).

    python -m pipelines.run --dataset thar1_demo_2024 --steps all
    python -m pipelines.run --dataset thar1_demo_2024 --steps expected,detect
    python -m pipelines.run --command fetch-weather

Each step runs in its own transaction and is idempotent (delete-and-insert per dataset). An explicitly requested
step that is not implemented yet exits 2 and names its milestone. `--steps all` runs every implemented step in
order and lists the pending ones on stderr, so no target silently pretends to have run.
"""

import argparse
import sys
from collections.abc import Callable

from sqlalchemy import Connection

PIPELINE_STEPS: dict[str, str] = {
    "quality": "M2",
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
IMPLEMENTED: dict[str, Callable[[argparse.Namespace], None]] = {}
STEPS: dict[str, Callable[[Connection, str], None]] = {}


def _register() -> None:
    from pipelines import kaggle, thar1

    IMPLEMENTED["ingest-kaggle"] = kaggle.run
    IMPLEMENTED["fetch-weather"] = thar1.fetch_weather
    IMPLEMENTED["scenario"] = thar1.scenario
    STEPS["quality"] = thar1.step_quality
    STEPS["expected"] = thar1.step_expected
    STEPS["detect"] = thar1.step_detect
    try:
        from pipelines import m3
    except ImportError:
        return
    IMPLEMENTED["baseline"] = m3.build_baseline
    IMPLEMENTED["approve-baseline"] = m3.approve_baseline
    STEPS.update(m3.STEPS)


def run_steps(dataset_id: str, names: list[str]) -> None:
    from app.core.db import get_engine

    for name in names:
        with get_engine().begin() as conn:
            STEPS[name](conn, dataset_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.run")
    parser.add_argument("--dataset")
    parser.add_argument("--steps", default="all")
    parser.add_argument("--from", dest="period_from")
    parser.add_argument("--to", dest="period_to")
    parser.add_argument("--command", choices=sorted(COMMANDS))
    args = parser.parse_args(argv)
    _register()

    if args.command:
        if args.command not in IMPLEMENTED:
            print(f"step '{args.command}' is not implemented yet (milestone {COMMANDS[args.command]})", file=sys.stderr)
            return 2
        IMPLEMENTED[args.command](args)
        return 0

    if not args.dataset:
        parser.error("--dataset is required for pipeline steps")
    if args.steps == "all":
        names = [s for s in PIPELINE_STEPS if s in STEPS]
        pending = [f"{s} ({PIPELINE_STEPS[s]})" for s in PIPELINE_STEPS if s not in STEPS]
    else:
        names = args.steps.split(",")
        for name in names:
            if name not in PIPELINE_STEPS:
                parser.error(f"unknown step {name!r}")
            if name not in STEPS:
                print(f"step '{name}' is not implemented yet (milestone {PIPELINE_STEPS[name]})", file=sys.stderr)
                return 2
        pending = []
    run_steps(args.dataset, names)
    if pending:
        print(f"pending steps not run: {', '.join(pending)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
