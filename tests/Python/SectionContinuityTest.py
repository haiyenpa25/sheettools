import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'workers'))
from omr_checks.section_continuity import connect_sections


class ContinuityTest(unittest.TestCase):
    def test_chorus_prefix_in_middle_verse_row_and_next_page(self):
        def word(text,x,y,verse,kind='verse'):
            return {'text':text,'x':x,'y':y,'box':[x-10,y-10,x+10,y+10], 'system_id':'system_001',
                'verse_number':verse,'section_type':kind,'lyric_name':'ĐK' if kind=='chorus' else f'Lời {verse}'}
        pages=[{'words':[word('đường',100,100,1),word('hoài',100,130,2),word('lành',100,160,3),
            word('Tương',200,130,2),word('lai',250,130,2),word('tôi',300,130,1,'chorus')]},
            {'words':[word('điều',100,100,1),word('tôi',200,100,1)]}]
        connect_sections(pages)
        for w in pages[0]['words'][3:]+pages[1]['words']:
            self.assertEqual('ĐK',w['lyric_name']); self.assertEqual(1,w['verse_number'])
        self.assertEqual('Lời 2',pages[0]['words'][1]['lyric_name'])

    def test_explicit_new_verse_does_not_inherit_chorus(self):
        pages=[{'words':[{'section_type':'chorus','lyric_name':'ĐK','system_id':'s','x':1,'y':1,'box':[0,0,2,2]}]},
               {'words':[{'section_type':'verse','explicit_verse':True,'verse_number':2,'system_id':'s','x':1,'y':1,'box':[0,0,2,2]}]}]
        connect_sections(pages)
        self.assertEqual('verse',pages[1]['words'][0]['section_type'])

if __name__=='__main__': unittest.main()
