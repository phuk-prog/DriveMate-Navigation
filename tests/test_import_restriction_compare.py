import unittest
from benchmarks.import_restriction_compare import decode_response
class RealResponseContract(unittest.TestCase):
    def test_success_metadata_hints_is_a_dictionary(self):
        response={'paths':[{'details':{'osm_way_id':[[0,1,10],[1,2,20],[2,3,20]]}}],
                  'hints':{'visited_nodes.sum':4}}
        self.assertEqual(decode_response(response),([10,20],False))
    def test_only_explicit_connection_failure_counts_as_unreachable(self):
        self.assertEqual(decode_response({'hints':[{'details':'com.graphhopper.util.exceptions.ConnectionNotFoundException'}]}),(None,True))
        self.assertEqual(decode_response({'message':'invalid profile','hints':[]}),(None,False))
