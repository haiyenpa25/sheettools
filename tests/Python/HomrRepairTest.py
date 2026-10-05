import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'workers'))
from omr_checks.repair import homr_candidate


class HomrRepairTest(unittest.TestCase):
    def test_candidate_requires_matching_page_and_image_pitch_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary); (project/'pages').mkdir(); page=project/'pages/page-001.png'; page.write_bytes(b'image')
            (project/'musicxml').mkdir(); (project/'omr_out').mkdir()
            current='<score-partwise><part id="P1"><measure number="3"><attributes><divisions>6</divisions></attributes></measure></part></score-partwise>'
            (project/'musicxml/current.musicxml').write_text(current)
            notes=''.join(f'<note><pitch><step>{s}</step>{"<alter>-1</alter>" if s=="B" else ""}<octave>4</octave></pitch><duration>{d}</duration><type>{t}</type></note>' for s,d,t in [('G',12,'half'),('B',4,'quarter'),('A',4,'quarter'),('G',4,'quarter')])
            notes=notes.replace('<type>quarter</type>','<voice>1</voice><type>quarter</type>',1)
            notes=notes.replace('<duration>4</duration><voice>1</voice><type>quarter</type>','<duration>4</duration><voice>1</voice><type>quarter</type><notations><tuplet type="start"/></notations>',1)
            base=project/'omr_comparisons/run/page_0001'; base.mkdir(parents=True)
            (base/'page.musicxml').write_text('<score-partwise><part id="P1"><measure number="1"><attributes><divisions>6</divisions></attributes>'+notes+'</measure></part></score-partwise>')
            positions=[{'id':f'P1:1:{i+1}','position':[x,y]} for i,(x,y) in enumerate([(100,140),(200,120),(250,130),(300,140)])]
            (base/'note_positions.json').write_text(json.dumps({'positions':positions}))
            status={'engine':'homr','status':'completed','pages':[{'page':1,'xml':'page.musicxml','source_sha256':hashlib.sha256(b'image').hexdigest()}]}
            (base.parent/'status.json').write_text(json.dumps(status))
            words=[{'text':text,'x':x,'staff_index':0,'verse_number':1} for x,text in zip([100,200,250,300],['Tôi','với','mỗi','ngày'])]
            (project/'omr_out/lyrics.json').write_text(json.dumps({'words':words}))
            entry={'id':'m3','page':1,'part_id':'P1','measure_number':3,'staff_index':0,'box':[50,60,350,250],
                   'staff_lines':[80,100,120,140,160],'interline':20,'evidence':{'omr':{'expected_beats':4,'fifths':-2},
                   'image':{'heads':4,'components':[{'x':x,'y':y,'hollow':i==0} for i,(x,y) in enumerate([(100,140),(200,120),(250,130),(300,140)])],
                            'tuplet_marks':[{'number':3,'bracket_span':[180,320]}]},'lyrics':{'1':4}}}
            candidate=homr_candidate(project,entry)
            self.assertTrue(candidate['verified']); self.assertIn('Tôi',candidate['measure_xml'])
            self.assertEqual(2,len(ET.fromstring(candidate['measure_xml']).findall('note/notations/tuplet')),'Tuplet markers cannot be duplicated')
            self.assertEqual(current,(project/'musicxml/current.musicxml').read_text())
            entry['evidence']['image']['components'][0]['y']=160
            self.assertFalse(homr_candidate(project,entry)['verified'],'Image pitch conflict blocks application')
            page.write_bytes(b'other-image')
            self.assertIsNone(homr_candidate(project,entry),'Stale page recognition must be rejected')

if __name__=='__main__': unittest.main()
