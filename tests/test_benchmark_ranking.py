import unittest
from benchmarks.benchmark_ranking import judge,markdown
class RankingTests(unittest.TestCase):
    def example(self):
        cases=[
         {'case':'legal','expected_ways':[1],'results':{'DriveMate':'pass','Engine':'fail','Absent':'not tested'}},
         {'case':'no_entry','expected_ways':None,'results':{'DriveMate':'pass','Engine':'fail','Absent':'not tested'}}]
        s=lambda p,f,u,n:dict(passed=p,failed=f,unknown=u,not_tested=n,test_cases=2)
        return {'cases':cases,'summaries':{'DriveMate':s(2,0,0,0),'Engine':s(0,2,0,0),'Absent':s(0,0,0,2)}}
    def test_critical_failure_and_exclusion(self):
        report=judge(self.example())
        self.assertEqual([(e['engine'],e['rank']) for e in report['rankings']],[('DriveMate',1),('Engine',2)])
        self.assertEqual(report['rankings'][1]['safety_failures'],1)
        self.assertIn('CRITICAL',markdown(report))
        self.assertNotIn('| Absent |',markdown(report))
    def test_ties_are_not_broken_arbitrarily(self):
        data=self.example()
        for row in data['cases']:row['results']['Engine']='pass'
        data['summaries']['Engine']=dict(data['summaries']['DriveMate'])
        self.assertEqual([e['rank'] for e in judge(data)['rankings']],[1,1])
    def test_unknown_not_labeled_as_actual_failure(self):
        data=self.example()
        data['cases'][0]['results']['Engine']='unknown'
        data['summaries']['Engine']=dict(passed=0,failed=1,unknown=1,not_tested=0,test_cases=2)
        report=judge(data)
        self.assertEqual(report['rankings'][1]['score'],0)
        self.assertEqual(sum(e['status']=='unknown' for e in report['failures']),1)
    def test_bad_aggregate_never_ranked(self):
        data=self.example();data['summaries']['DriveMate']['passed']=3
        with self.assertRaises(ValueError):judge(data)
if __name__=='__main__':unittest.main()
