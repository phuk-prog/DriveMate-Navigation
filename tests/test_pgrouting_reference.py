import unittest
from benchmarks.pgrouting_reference import sql_for_query
from benchmarks.whole_drive import prepared

class PgRoutingAdapterTests(unittest.TestCase):
    def test_only_synthetic_numbers_are_sent_as_pgsql(self):
        sql,labels=sql_for_query(prepared(),'osm:20','osm:24')
        self.assertIn('pgr_dijkstra',sql)
        self.assertIn('CREATE TEMP TABLE',sql)
        self.assertIn('reverse_cost',sql)
        self.assertTrue(labels)
        self.assertNotIn('https:',sql)
        self.assertNotIn('user',sql)
    def test_directionality_is_preserved(self):
        sql,labels=sql_for_query(prepared(),'osm:4','osm:1')
        self.assertIn('pgr_dijkstra',sql)
        self.assertTrue('WHERE edge>0' in sql)
if __name__=='__main__':unittest.main()
