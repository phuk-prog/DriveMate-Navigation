"""Record every executed unittest under its navigation subsystem.

Run as: python -m tools.unittest_evidence. Produces case-level machine-readable
evidence rather than treating one 400+ method suite as a single green check.
"""
import json,sys,traceback,unittest
from collections import Counter,defaultdict
from pathlib import Path

def category(identifier):
    name=identifier.split(".",1)[0].removeprefix("test_").lower()
    if any(token in name for token in ("gps_recovery","recovery")):return "GPS signal-loss/recovery"
    if any(token in name for token in ("gps_matching","gps_0101","gps_")):return "GPS positioning and matching"
    if "roundabout" in name:return "Roundabouts and exit guidance"
    if "lane" in name:return "Lane indications and connectivity"
    if "instruction" in name:return "Instruction timing and delivery"
    if any(x in name for x in ("timed_journey","journey","whole_drive")):return "Complete journeys and rerouting"
    if any(x in name for x in ("osm","import","map","public_uk","road_restriction")):return "Map data and restrictions"
    if any(x in name for x in ("route","routing","junction","restriction")):return "Routing and legal junctions"
    if any(x in name for x in ("native","core","endpoint","http")):return "Native routing and backend reliability"
    if any(x in name for x in ("score","compare","cloud","head_to_head","reference","provider","adversarial","benchmark")):return "Benchmark and evidence validation"
    if any(x in name for x in ("privacy","security")):return "Security and privacy"
    return "Other core reliability checks"

class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.records={}
    def startTest(self,test):
        super().startTest(test)
        self.records[test.id()]={'test':test.id(),'category':category(test.id()),'status':'running'}
    def addSuccess(self,test):
        super().addSuccess(test);self.records[test.id()]['status']='pass'
    def addSkip(self,test,reason):
        super().addSkip(test,reason)
        self.records[test.id()].update(status='skipped',reason=reason)
    def addFailure(self,test,error):
        super().addFailure(test,error)
        self.records[test.id()].update(status='fail',detail=self._exc_info_to_string(error,test)[-5000:])
    def addError(self,test,error):
        super().addError(test,error)
        self.records[test.id()].update(status='error',detail=self._exc_info_to_string(error,test)[-5000:])
    def addExpectedFailure(self,test,error):
        super().addExpectedFailure(test,error)
        self.records[test.id()].update(status='expected_failure',reason=self._exc_info_to_string(error,test)[-2000:])
    def addUnexpectedSuccess(self,test):
        super().addUnexpectedSuccess(test);self.records[test.id()]['status']='unexpected_success'

def summarise(records):
    bycategory=defaultdict(Counter)
    for row in records:
        if row['status']=='running':raise ValueError('Unfinished recorded test '+row['test'])
        bycategory[row['category']][row['status']]+=1
    result={}
    for name,counts in sorted(bycategory.items()):
        executed=sum(counts.values())
        result[name]={'passed':counts['pass'],'failed':counts['fail']+counts['error']+counts['unexpected_success'],
                      'skipped':counts['skipped'],'expected_failure':counts['expected_failure'],
                      'total_discovered':executed}
    return result

def main():
    suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py')
    r=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(suite)
    rows=sorted(r.records.values(),key=lambda x:x['test'])
    report={'system':'DriveMate research','scope':'test methods (not synthetic observations or competitor executions)',
            'tests':rows,'categories':summarise(rows),'total_discovered':len(rows),
            'ok':r.wasSuccessful()}
    root=Path('results/unittest');root.mkdir(parents=True,exist_ok=True)
    (root/'per_test.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'methods_recorded':len(rows),'categories':len(report['categories']),
                      'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)}))
    return 0 if r.wasSuccessful() else 1

if __name__=='__main__':sys.exit(main())
