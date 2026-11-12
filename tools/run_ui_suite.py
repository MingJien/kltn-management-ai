"""Run each UI spec in a fresh owned schema, avoiding cross-spec state leaks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specs",nargs="*")
    parser.add_argument("--report",default="local/ui-suite-results.json")
    parser.add_argument("--trace",action="store_true",help="Keep synthetic traces only on failure under local/ or tmp/")
    args=parser.parse_args()
    specs=args.specs or sorted(p.name for p in (ROOT/"frontend/e2e").glob("*.spec.ts"))
    report=(ROOT/args.report).resolve()
    if not report.is_relative_to(ROOT/"local") and not report.is_relative_to(ROOT/"tmp"):
        parser.error("Keep detailed UI logs under ignored local/ or tmp/")
    report.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    for name in specs:
        if Path(name).name!=name or not (ROOT/"frontend/e2e"/name).is_file():
            parser.error("Spec must be a filename in frontend/e2e")
        started=time.monotonic()
        log=report.parent/(name+".log")
        with log.open("w",encoding="utf-8") as output:
            result=subprocess.run([sys.executable,"-m","tools.run_e2e","e2e/"+name,*(["--trace=retain-on-failure"] if args.trace else [])],cwd=ROOT,
                env={**os.environ,"KLTN_E2E_ALLOW_ISOLATED_SCHEMA":"true","PYTHONIOENCODING":"utf-8"},
                stdout=output,stderr=subprocess.STDOUT)
        row=dict(spec=name,passed=result.returncode==0,seconds=round(time.monotonic()-started,1),log=str(log.relative_to(ROOT)))
        results.append(row)
        report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"{'PASS' if row['passed'] else 'FAIL'} {name} ({row['seconds']}s)",flush=True)
    print(f"{sum(r['passed'] for r in results)}/{len(results)} specs passed",flush=True)
    return 0 if all(r["passed"] for r in results) else 1


if __name__=="__main__":
    raise SystemExit(main())
