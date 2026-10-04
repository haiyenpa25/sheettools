import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'workers'))
from omr_checks.repair import image_proposal, reconcile_tuplet
import xml.etree.ElementTree as ET

class RepairEvidenceTest(unittest.TestCase):
    def test_crop_pitch_and_image_bracket_can_reconcile_timing(self):
        m={'interline':20,'staff_lines':[80,100,120,140,160],
            'evidence':{'omr':{'expected_beats':4,'fifths':-2},'image':{'components':[
                {'x':100,'y':140,'hollow':True},{'x':200,'y':120,'hollow':False},
                {'x':250,'y':130,'hollow':False},{'x':300,'y':140,'hollow':False}],
                'tuplet_marks':[{'number':3,'bracket_span':[180,320]}]}}}
        candidate=ET.fromstring('<measure>'+''.join(f'<note><pitch><step>{s}</step>{"<alter>-1</alter>" if s=="B" else ""}<octave>4</octave></pitch><duration>{d}</duration><type>{t}</type></note>' for s,d,t in [('G',12,'half'),('B',6,'quarter'),('A',6,'quarter'),('G',6,'quarter')])+'</measure>')
        self.assertTrue(reconcile_tuplet(m,candidate,6))
        self.assertEqual(['12','4','4','4'],[n.findtext('duration') for n in candidate.findall('note')])
        self.assertEqual(3,len(candidate.findall('note/time-modification')))
        candidate.find('note/pitch/step').text='F'
        self.assertFalse(reconcile_tuplet(m,candidate,6),'Pitch disagreement cannot be silently repaired')
    def test_only_propose_from_three_heads_and_tuplet_evidence(self):
        m={'id':'m','part_id':'P1','measure_number':3,'staff_lines':[80,100,120,140,160],'interline':20,
            'evidence':{'omr':{'expected_beats':4,'beats':4,'fifths':-2},'lyrics':{'1':4},
                'image':{'components':[{'x':100,'y':140,'hollow':True},{'x':200,'y':120,'hollow':False},
                    {'x':250,'y':130,'hollow':False},{'x':300,'y':140,'hollow':False}],
                    'tuplet_marks':[{'number':3,'bracket_span':[180,320]}]}}}
        proposal=image_proposal(m)
        self.assertEqual(4,len(proposal['notes'])); self.assertEqual('2/3',proposal['notes'][-1]['quarters'])
        self.assertFalse(proposal['verified'],'CV timing alone may never be auto-applied')
        m['evidence']['image']['tuplet_marks']=[]; self.assertIsNone(image_proposal(m))
if __name__=='__main__': unittest.main()
