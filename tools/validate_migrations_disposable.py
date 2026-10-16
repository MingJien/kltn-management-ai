"""Deprecated migration checker; retained so an old command cannot target kltn_dev.

Use ``python -m tools.run_e2e``. That test harness applies the official
migration in an owned random schema inside kltn_management and removes only
that schema when the run finishes.
"""


def main() -> int:
    print("Deprecated: use `python -m tools.run_e2e` for the official schema.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
