import unittest
from benchmarks.category_audit import category,rank_per_category,tally,ROUTES
class CategoryAuditTests(unittest.TestCase):
    def test_category_denominator_real_and_ineligible_missing(self):
        c=category('rings','Ring',(ROUTES[-2],ROUTES[-1]),
            {'DriveMate':{ROUTES[-2]:'pass',ROUTES[-1]:'fail'},
             'GraphHopper':{ROUTES[-2]:'pass',ROUTES[-1]:'pass'}},'source')
        self.assertEqual(c['counts']['DriveMate']['passed'],1)
        self.assertEqual(c['counts']['DriveMate']['failed'],1)
        self.assertEqual(c['counts']['RoutingKit CH']['not_tested'],2)
        self.assertEqual(rank_per_category(c),{'GraphHopper':1,'DriveMate':2})
    def test_untested_and_unknown_never_promoted(self):
        self.assertEqual(tally(['pass','unknown','fail','not tested']),
                         {'passed':1,'failed':1,'unknown':1,'not_tested':1,'total':4})
        with self.assertRaises(ValueError):tally(['unavailable-as-a-pass'])
    def test_tied_engines_get_same_rank(self):
        c=category('r','route',('a','b'),{'DriveMate':{'a':'pass','b':'pass'},
            'GraphHopper':{'a':'pass','b':'pass'}},'source')
        self.assertEqual(rank_per_category(c)['DriveMate'],1)
        self.assertEqual(rank_per_category(c)['GraphHopper'],1)
if __name__=='__main__':unittest.main()
