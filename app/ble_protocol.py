"""Transport-independent, bounded BLE RPC. No radio dependencies; unit-testable."""
import hashlib,json
from urllib.request import Request,urlopen
from urllib.parse import quote

CHUNK=480
MAX_RESPONSE=16*1024*1024
class Protocol:
    def __init__(self,base='http://127.0.0.1:8080',fetch=None):
        self.base=base;self.fetch=fetch or self.http;self.payload=b'';self.reply=b''
    def http(self,path,body=None):
        request=Request(self.base+path,data=body,headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=10) as r:
            value=r.read(MAX_RESPONSE+1)
            if len(value)>MAX_RESPONSE:raise ValueError('Image exceeds transfer limit')
            return value
    def command(self,raw):
        try:
            req=json.loads(raw);op=req['op']
            if op=='read':
                offset=req['offset']
                if not isinstance(offset,int) or not 0<=offset<=len(self.payload):raise ValueError('Invalid offset')
                self.reply=self.payload[offset:offset+CHUNK];return
            if op=='library':value=self.fetch('/api/library')
            elif op=='state':value=self.fetch('/api/state')
            elif op=='action':
                body=req['body']
                if body.get('action') not in ['survey','tune','baseline','lock','capture','settings','name','delete']:raise ValueError('Unknown action')
                value=self.fetch('/api/action',json.dumps(body).encode())
            elif op=='image':
                path=req['path']
                # Only paths listed by the current session are exposed over BLE.
                current=json.loads(self.fetch('/api/state'))
                if path not in current.get('gallery',[]):
                    catalog=json.loads(self.fetch('/api/library'))
                    if not any(path in entry['images'] for entry in catalog):raise ValueError('Image is not in capture library')
                value=self.fetch(quote(path,safe='/'))
            else:raise ValueError('Unknown operation')
            if len(value)>MAX_RESPONSE:raise ValueError('Transfer too large')
            self.payload=value
            self.reply=json.dumps({'length':len(value),'sha256':hashlib.sha256(value).hexdigest()}).encode()
        except Exception as e:
            self.payload=b'';self.reply=json.dumps({'error':str(e)[:220]}).encode()
