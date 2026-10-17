"""ARRIVAL-001 synthetic acceptance and adversarial safety controls."""
import importlib.util
import unittest

class ArrivalTests(unittest.TestCase):
    def controller(self):
        self.assertIsNotNone(importlib.util.find_spec('engine.arrival_controller'),
                             'Arrival lifecycle capability must exist')
        from engine.arrival_controller import ArrivalController
        return ArrivalController()

    def test_two_reliable_observations_required(self):
        c=self.controller();c.begin((1.001,1),route_length_m=223,now_ms=0)
        kwargs=dict(context_revision=c.revision,position=(1.001,1),accuracy_m=5,reliable=True,on_route=True,remaining_m=0)
        self.assertEqual(c.observe(timestamp_ms=1000,now_ms=1000,**kwargs),'CANDIDATE')
        self.assertFalse(c.arrived)
        self.assertEqual(c.observe(timestamp_ms=2000,now_ms=2000,**kwargs),'ARRIVED')
        self.assertTrue(c.arrived)

    def test_frozen_twenty_cases(self):
        self.controller()
        from benchmarks.arrival_lifecycle_trial import run_dmn
        r=run_dmn()
        self.assertEqual(len(r['cases']),20)
        self.assertEqual([(c['case_id'],c['outcome']) for c in r['cases']],
                         [(c['case_id'],'PASS') for c in r['cases']])

    def started(self):
        c=self.controller();token=c.begin((1.001,1),route_length_m=223,now_ms=0)
        fields=dict(context_revision=token,position=(1.001,1),accuracy_m=5,reliable=True,on_route=True,remaining_m=0)
        return c,fields

    def test_invalid_position_clears_candidate(self):
        for position in ((float('nan'),1),(1,float('inf')),(91,1),(1,181),(True,1),'bad',None):
            with self.subTest(position=position):
                c,f=self.started()
                self.assertEqual(c.observe(timestamp_ms=1000,now_ms=1000,**f),'CANDIDATE')
                self.assertEqual(c.observe(timestamp_ms=2000,now_ms=2000,**(f|dict(position=position))),'WITHHELD')
                self.assertEqual(c.observe(timestamp_ms=3000,now_ms=3000,**f),'CANDIDATE')

    def test_invalid_progress_and_accuracy_clear_candidate(self):
        for key,value in (('remaining_m',float('nan')),('remaining_m',float('inf')),('remaining_m',True),('remaining_m',224),('accuracy_m',-1),('accuracy_m',float('nan')),('accuracy_m',True)):
            with self.subTest(key=key,value=value):
                c,f=self.started();c.observe(timestamp_ms=1000,now_ms=1000,**f)
                self.assertEqual(c.observe(timestamp_ms=2000,now_ms=2000,**(f|{key:value})),'WITHHELD')
                self.assertEqual(c.observe(timestamp_ms=3000,now_ms=3000,**f),'CANDIDATE')

    def test_old_context_cannot_complete_arrival(self):
        c,f=self.started();old=f['context_revision']
        c.observe(timestamp_ms=1000,now_ms=1000,**f)
        new=c.begin((1.001,1),route_length_m=223,now_ms=1500)
        self.assertNotEqual(old,new)
        self.assertEqual(c.observe(timestamp_ms=2000,now_ms=2000,**f),'REJECTED')
        self.assertFalse(c.arrived)
        self.assertEqual(c.observe(timestamp_ms=3000,now_ms=3000,**(f|dict(context_revision=new))),'CANDIDATE')

    def test_pre_context_sample_rejected(self):
        c,f=self.started();f['context_revision']=c.begin((1.001,1),route_length_m=223,now_ms=2000)
        self.assertEqual(c.observe(timestamp_ms=1000,now_ms=3000,**f),'REJECTED')

    def test_longitude_wrap_proximity(self):
        c=self.controller();token=c.begin((0,179.99995),route_length_m=100,now_ms=0)
        f=dict(context_revision=token,position=(0,-179.99995),accuracy_m=5,reliable=True,on_route=True,remaining_m=0)
        self.assertEqual(c.observe(timestamp_ms=1000,now_ms=1000,**f),'CANDIDATE')
        self.assertEqual(c.observe(timestamp_ms=2000,now_ms=2000,**f),'ARRIVED')

    def test_exact_age_boundary_can_corroborate(self):
        c,f=self.started()
        self.assertEqual(c.observe(timestamp_ms=0,now_ms=0,**f),'CANDIDATE')
        self.assertEqual(c.observe(timestamp_ms=1000,now_ms=10000,**f),'ARRIVED')

    def test_backward_clock_rejected(self):
        c,f=self.started();c.observe(timestamp_ms=2000,now_ms=2000,**f)
        with self.assertRaises(ValueError):c.observe(timestamp_ms=1000,now_ms=1000,**f)
        self.assertFalse(c.arrived)

    def test_invalid_configuration(self):
        from engine.arrival_controller import ArrivalController
        for kwargs in (dict(radius_m=float('nan')),dict(max_remaining_m=-1),dict(max_accuracy_m=True),dict(minimum_sample_gap_ms=0),dict(max_observation_age_ms=True),dict(minimum_sample_gap_ms=10001)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):ArrivalController(**kwargs)

    def test_invalid_begin_is_atomic(self):
        c,f=self.started();revision=c.revision
        for dest,length in (((91,1),223),((1,1),float('inf')),((1,1),True)):
            with self.subTest(dest=dest,length=length),self.assertRaises(ValueError):c.begin(dest,route_length_m=length,now_ms=1000)
            self.assertEqual(c.revision,revision)
        self.assertEqual(c.observe(timestamp_ms=1000,now_ms=1000,**f),'CANDIDATE')

    def test_scorecard_includes_all_families_and_rejects_partial(self):
        from benchmarks.arrival_lifecycle_trial import coverage,run_dmn
        r=run_dmn();rows=coverage(r)['rows']
        self.assertEqual(len(rows),13)
        self.assertEqual(rows[0]['score_out_of_ten'],10)
        self.assertTrue(all(x['rank'] is None for x in rows[1:]))
        self.assertEqual(sum(x['cases'][0]['outcome']=='UNSUPPORTED' for x in rows),5)
        r['cases'].pop()
        with self.assertRaises(ValueError):coverage(r)
