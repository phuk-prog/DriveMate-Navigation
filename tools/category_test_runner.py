"""Run all existing unittest files once, in isolated, separately labelled categories.

These are UNIT CONTRACT checks, not real-world navigation quality or competitor
rankings. Missing implemented cases remain NOT_RUN.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from io import StringIO

ROOT=Path(__file__).resolve().parents[1]
TESTS=ROOT/"tests"
REGISTRY=ROOT/"config/dmn-separated-category-tests.json"

def validate(data):
    if data.get("schema_version")!=1: raise ValueError("Unsupported registry")
    categories=data.get("categories")
    if not isinstance(categories,list) or len(categories)<14:
        raise ValueError("Missing navigation categories")
    ids=[c["id"] for c in categories]
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate category")
    # Old app-adoption tests remain archived but are outside engine scope.
    excluded={"test_app_readiness.py"}
    actual={p.name for p in TESTS.glob("test_*.py")} - excluded
    if any(not (TESTS / name).exists() for name in excluded):
        raise ValueError("Explicit engine-only exclusions changed")
    claimed=[]
    for c in categories:
        if c.get("engine_rank") is not None or c.get("navigation_score") is not None:
            raise ValueError("Unit contract cannot predeclare navigation score")
        names=c["test_files"]
        if not isinstance(names,list) or len(names)!=len(set(names)):
            raise ValueError("Duplicate test file in category")
        claimed.extend(names)
    if len(claimed)!=len(set(claimed)) or set(claimed)!=actual:
        raise ValueError("Each test_*.py file must belong to exactly one category; missing="
                         +repr(sorted(actual-set(claimed)))+" extra="+
                         repr(sorted(set(claimed)-actual)))
    required={"map_data","legal_routing","gps_matching","gps_loss_recovery",
              "route_computation","route_quality","route_calculation_speed",
              "junctions","roundabouts","lanes","route_line_adherence",
              "rerouting","instruction_timing","live_traffic","speed_limits",
              "arrival","offline_reliability","failure_handling",
              "performance_resources","integrated_end_to_end",
              "reference_adapters"}
    if set(ids)!=required:raise ValueError("Owner-approved category list drift")
    return {"category_count":len(categories),"unit_test_files":len(actual)}

class Cases(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.details=[]
    def addSuccess(self,test):
        super().addSuccess(test)
        self.details.append({"id":test.id(),"result":"PASS"})
    def addFailure(self,test,err):
        super().addFailure(test,err)
        self.details.append({"id":test.id(),"result":"FAIL",
                             "detail":self._exc_info_to_string(err,test)[-1600:]})
    def addError(self,test,err):
        super().addError(test,err)
        self.details.append({"id":test.id(),"result":"ERROR",
                             "detail":self._exc_info_to_string(err,test)[-1600:]})
    def addSkip(self,test,reason):
        super().addSkip(test,reason)
        self.details.append({"id":test.id(),"result":"SKIP","detail":reason})

def run_one(category,dirpath):
    start=time.perf_counter()
    files=category["test_files"]
    if not files:
        report={"category":category["id"],"label":category["label"],"scope":category["scope"],
                "status":"NOT_RUN","reason":"No implemented test module belongs to this category",
                "unit_total":0,"passed":0,"failed":0,"errors":0,"skipped":0,"cases":[]}
        code=0
    else:
        loader=unittest.TestLoader()
        suite=unittest.TestSuite()
        for filename in files:
            suite.addTests(loader.discover(start_dir=str(TESTS),pattern=filename))
        output=StringIO()
        result=unittest.TextTestRunner(stream=output,verbosity=1,resultclass=Cases).run(suite)
        passed=sum(c["result"]=="PASS" for c in result.details)
        errors=len(result.errors)
        failed=len(result.failures)
        skipped=len(result.skipped)
        status="UNIT_PASS" if result.wasSuccessful() and result.testsRun>0 else "UNIT_FAIL"
        report={"category":category["id"],"label":category["label"],"scope":category["scope"],
                "status":status,"unit_total":result.testsRun,"passed":passed,
                "failed":failed,"errors":errors,"skipped":skipped,"cases":result.details,
                "test_files":files,"debug_tail":output.getvalue()[-1400:]}
        code=0 if status=="UNIT_PASS" else 1
    report.update({"elapsed_s":round(time.perf_counter()-start,3),
                   "classification":"UNIT_CONTRACT_ONLY",
                   "external_engine_comparison":"NOT_EXECUTED_BY_THIS_SUITE",
                   "engine_rank":None,"navigation_score":None,
                   "independent_real_road_truth":False,
                   "commit":os.getenv("GITHUB_HEAD_SHA") or os.getenv("GITHUB_SHA")})
    dirpath.mkdir(parents=True,exist_ok=True)
    (dirpath/(category["id"]+".json")).write_text(json.dumps(report,indent=2)+"\n")
    print(category["id"]+" "+report["status"]+" "+str(report["passed"])+"/"+
          str(report["unit_total"]),flush=True)
    return code

def run_all(categories,target):
    target.mkdir(parents=True,exist_ok=True)
    rows=[]
    for c in categories:
        cmd=[sys.executable,"-m","tools.category_test_runner","--category",
             c["id"],"--output-dir",str(target)]
        path=target/(c["id"]+".json")
        try:
            completed=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=150)
            if not path.exists() or completed.returncode not in (0,1):
                raise RuntimeError((completed.stdout+completed.stderr)[-1800:])
            result=json.loads(path.read_text())
            if result["category"]!=c["id"]: raise RuntimeError("Mismatched category output")
        except (subprocess.TimeoutExpired,RuntimeError,ValueError) as exc:
            result={"category":c["id"],"label":c["label"],"status":"INFRA_FAILURE",
                    "unit_total":0,"passed":0,"failed":0,"errors":1,"skipped":0,
                    "reason":str(exc)[-1800:],"engine_rank":None,"navigation_score":None}
            path.write_text(json.dumps(result,indent=2)+"\n")
        rows.append(result)
        print(c["id"]+": "+result["status"]+" "+str(result.get("passed",0))+"/"+
              str(result.get("unit_total",0)),flush=True)
    failures=[x for x in rows if x["status"] not in ("UNIT_PASS","NOT_RUN")]
    summary={"classification":"Per-category unittest executions; NOT navigation engine competition",
             "category_count":len(rows),
             "categories_with_unit_tests":sum(x["unit_total"]>0 for x in rows),
             "categories_not_run":sum(x["status"]=="NOT_RUN" for x in rows),
             "unit_total":sum(x["unit_total"] for x in rows),
             "unit_passed":sum(x["passed"] for x in rows),
             "unit_failed_or_errored":sum(x["failed"]+x["errors"] for x in rows),
             "failures":[x["category"] for x in failures],
             "engine_ranking":None,"independent_real_road_truth":False,
             "results":[{"category":x["category"],"label":x["label"],
                        "status":x["status"],"unit_total":x["unit_total"],
                        "passed":x["passed"],"failed":x["failed"],"errors":x["errors"],
                        "skipped":x["skipped"]} for x in rows]}
    (target/"index.json").write_text(json.dumps(summary,indent=2)+"\n")
    table=["# Individual DMN category unit-test execution","",
           "These results are *unit contracts*, NOT comparable engine rankings "
           "or independent real-road navigation proof.","",
           "| Category | Status | Passed/unit total | Fails/errors |",
           "|---|---|---:|---:|"]
    for x in rows:
        table.append("| "+x["label"]+" | "+x["status"]+" | "+
                     str(x["passed"])+"/"+str(x["unit_total"])+" | "+
                     str(x["failed"]+x["errors"])+" |")
    table.append("\nSee each category JSON for individual case verdicts. Absent categories are NOT_RUN.")
    (target/"summary.md").write_text("\n".join(table)+"\n")
    print("Completed "+str(len(rows))+" independent categories; "+
          str(summary["unit_passed"])+"/"+str(summary["unit_total"])+
          " passed; "+str(summary["categories_not_run"])+" categories NOT_RUN",flush=True)
    return 1 if failures else 0

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--all",action="store_true")
    p.add_argument("--category",type=str)
    p.add_argument("--output-dir",type=Path,default=ROOT/"results/category-checks")
    args=p.parse_args()
    if args.all==bool(args.category):p.error("Select exactly --all or --category")
    data=json.loads(REGISTRY.read_text())
    validate(data)
    return run_all(data["categories"],args.output_dir) if args.all else run_one(
        next(c for c in data["categories"] if c["id"]==args.category),args.output_dir)

if __name__=="__main__":
    raise SystemExit(main())
