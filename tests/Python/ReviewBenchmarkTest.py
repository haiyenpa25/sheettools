import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'workers'))
from evaluation.review_benchmark import benchmark
from omr_checks.book_profile import BookProfile

class ReviewBenchmarkTest(unittest.TestCase):
    def test_no_truth_cannot_claim_accuracy(self):
        r=benchmark({'measures':[{'id':'a','decision':'accept'}]},None,[])
        self.assertIsNone(r['accept_precision']); self.assertFalse(r['accuracy_available'])
    def test_thresholds_and_dataset_gate_are_distinct(self):
        rows=[{'id':str(i),'decision':'accept' if i<9 else 'review'} for i in range(10)]
        truth={'verified':True,'measures':[{'id':str(i),'correct':i<9} for i in range(10)]}
        result=benchmark({'measures':rows},truth,[])
        self.assertTrue(result['performance_targets_met'])
        self.assertFalse(result['auto_repair_eligible'])
        self.assertFalse(result['targets_achieved'])
    def test_truth_for_another_source_is_rejected(self):
        ledger={'source_sha256':'a'*64,'measures':[{'id':'a','decision':'accept'}]}
        truth={'source_sha256':'b'*64,'verified':True,'measures':[{'id':'a','correct':True}]}
        self.assertFalse(benchmark(ledger,truth,[])['accuracy_available'])
    def test_metrics_and_partial_labels(self):
        ledger={'measures':[{'id':'a','decision':'accept'},{'id':'b','decision':'review'},{'id':'c','decision':'review'}]}
        truth={'verified':True,'measures':[{'id':'a','correct':True},{'id':'b','correct':False},{'id':'c','correct':True}]}
        r=benchmark(ledger,truth,[{'seconds':3},{'seconds':4}]); self.assertEqual(1,r['accept_precision']); self.assertEqual(1,r['error_coverage']); self.assertEqual(7,r['human_seconds']); self.assertTrue(r['complete_labels'])
        truth['measures'].pop(); self.assertFalse(benchmark(ledger,truth,[])['complete_labels'])
    def test_profile_needs_three_unique_human_events_and_context(self):
        with tempfile.TemporaryDirectory() as root:
            p=BookProfile(root,'book')
            for event in ('a','b'): p.confirm('NĂM','NẮM','ĐẤNG _ GIỮ',event)
            self.assertEqual('ĐẤNG NĂM GIỮ',p.apply_text('ĐẤNG NĂM GIỮ')['text'])
            p.confirm('NĂM','NẮM','ĐẤNG _ GIỮ','b'); self.assertEqual(2,p.data['ocr_confusions'][0]['confirmations'])
            p.confirm('NĂM','NẮM','ĐẤNG _ GIỮ','c')
            self.assertEqual('ĐẤNG NẮM GIỮ',p.apply_text('ĐẤNG NĂM GIỮ')['text'])
            self.assertEqual('NĂM MỚI',p.apply_text('NĂM MỚI')['text'])
            with self.assertRaises(ValueError): BookProfile(root,'../raw')
if __name__=='__main__': unittest.main()
