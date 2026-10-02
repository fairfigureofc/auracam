import json,tempfile,unittest
from pathlib import Path
import session_server as s
class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();s.DATA=Path(self.tmp.name);s.session=None
    def tearDown(self):self.tmp.cleanup()
    def capture(self,identifier,name,stamp):
        folder=s.DATA/'session'/identifier;folder.mkdir(parents=True)
        (folder/'capture.json').write_text(json.dumps({'capture_name':name,'capture_unix':stamp}))
        for phase in ['baseline','presence']:
            for style in ['ribbons','terrain','twist']:(folder/f'{phase}-{style}.png').write_bytes(b'image')
        return folder
    def test_order_and_names(self):
        self.capture('guest-a','Sample Person',10);self.capture('guest-b','Lunar Echo',20)
        entries=s.capture_library();self.assertEqual([e['name'] for e in entries],['Lunar Echo','Sample Person']);self.assertEqual(len(entries[0]['images']),6)
    def test_delete_exact_capture_only(self):
        a=self.capture('guest-a','A',1);b=self.capture('guest-b','B',2)
        s.delete_capture('session/guest-a');self.assertFalse(a.exists());self.assertTrue(b.exists())
        for bad in ['../','session','session/guest-b/..','/etc']:
            with self.assertRaises(ValueError):s.delete_capture(bad)
        self.assertTrue(b.exists())
    def test_partial_capture_hidden(self):
        folder=self.capture('guest-a','A',1);(folder/'presence-twist.png').unlink();self.assertEqual(s.capture_library(),[])
    def test_delete_active_keeps_baseline(self):
        folder=self.capture('guest-a','A',1);s.session=folder.parent;s.baseline={'images':['/files/baseline.png']}
        s.state.update(capture_id=folder.name,stage='gallery')
        s.delete_capture('session/guest-a');self.assertEqual(s.state['stage'],'locked');self.assertIsNone(s.state['capture_id']);self.assertEqual(s.state['gallery'],['/files/baseline.png'])
if __name__=='__main__':unittest.main()
