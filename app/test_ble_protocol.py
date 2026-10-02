import hashlib,json,unittest
from ble_protocol import Protocol,CHUNK
class TransferTests(unittest.TestCase):
    def setUp(self):
        self.image=b'\x89PNG\r\n\x1a\n'+bytes(range(256))*4096
        self.calls=[]
        def fetch(path,body=None):
            self.calls.append((path,body))
            if path=='/api/state':return json.dumps({'gallery':['/files/session/guest/presence.png']}).encode()
            if path=='/api/action':return b'{}'
            return self.image
        self.p=Protocol(fetch=fetch)
    def command(self,obj):self.p.command(json.dumps(obj).encode());return self.p.reply
    def test_chunked_image_hash_and_retry(self):
        meta=json.loads(self.command({'op':'image','path':'/files/session/guest/presence.png'}));data=b''
        for offset in range(0,meta['length'],CHUNK):
            part=self.command({'op':'read','offset':offset})
            self.assertEqual(part,self.command({'op':'read','offset':offset}))
            self.assertLessEqual(len(part),CHUNK);data+=part
        self.assertEqual(data,self.image);self.assertEqual(hashlib.sha256(data).hexdigest(),meta['sha256'])
    def test_unknown_paths_and_invalid_offsets(self):
        self.assertIn('error',json.loads(self.command({'op':'image','path':'/files/../../etc/passwd'})))
        self.assertIn('error',json.loads(self.command({'op':'read','offset':-1})))
    def test_command_allowlist(self):
        self.assertIn('error',json.loads(self.command({'op':'action','body':{'action':'exec'}})))
        self.command({'op':'action','body':{'action':'capture'}})
        self.assertEqual(json.loads(self.calls[-1][1]),{'action':'capture'})
    def test_settings_validation(self):
        import session_server as s
        with self.assertRaises(ValueError):s.update_settings({'dark':True,'chroma':float('nan'),'size':[1080,1350]})
        s.update_settings({'dark':False,'chroma':0.5,'size':[1080,1920]})
        self.assertEqual(s.state['render_settings']['size'],[1080,1920])
        self.assertFalse(s.state['render_settings']['dark'])
if __name__=='__main__':unittest.main()
