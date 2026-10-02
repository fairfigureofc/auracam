#!/usr/bin/env python3
"""Local-network AuraCam controller. One serialized hardware job at a time."""
import argparse,base64,csv,datetime as dt,json,math,statistics as st,subprocess,threading,time,uuid,shutil,secrets
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,unquote
from pi_capture import summarize

ROOT=Path(__file__).resolve().parent
state={'stage':'idle','busy':False,'message':'Start a session with the antenna fixed in place.','candidates':[],'gallery':[]}
lock=threading.Lock();receiver=None;session=None;baseline=None;selected=None
render_settings={'dark':True,'chroma':0,'size':[1080,1350],'gains':{'ribbons':1.1,'terrain':1.4,'twist':1.0}}
state['render_settings']=dict(render_settings)

def save():
    if session:
        p=session/'session.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));tmp.replace(p)
def status(message,stage=None):
    with lock:
        state['message']=message
        if stage:state['stage']=stage
        save()
def stop_receiver():
    global receiver
    if receiver and receiver.poll() is None:
        receiver.terminate()
        try:receiver.wait(timeout=5)
        except subprocess.TimeoutExpired:receiver.kill();receiver.wait()
    receiver=None

def rows(path,low,high,start=0):
    result=[]
    if not path.exists():return result
    for row in csv.reader(path.open()):
        try:
            stamp=dt.datetime.fromisoformat(row[0].strip()+'T'+row[1].strip()).timestamp()
            if stamp<start:continue
            lo,hi,step=map(float,row[2:5]);v=[float(z) for i,z in enumerate(row[6:]) if low<=lo+i*step<min(high,hi)]
            if len(v)>=3 and all(math.isfinite(x) for x in v):result.append((stamp,v))
        except (ValueError,IndexError):continue # Ignore an incomplete last write.
    return result

def countdown(message,seconds):
    status(message)
    for n in range(seconds,0,-1):
        with lock:state['remaining']=n
        if receiver is not None and receiver.poll() is not None:raise RuntimeError('Receiver stopped. Check receiver.log.')
        time.sleep(1)
    with lock:state['remaining']=0

def render(record,folder,prefix):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    options=webdriver.ChromeOptions();options.binary_location='/usr/bin/chromium'
    options.add_argument('--headless=new');options.add_argument('--disable-dev-shm-usage')
    files=[]
    with webdriver.Chrome(service=Service('/usr/bin/chromedriver'),options=options) as browser:
        browser.set_page_load_timeout(30);browser.set_script_timeout(30)
        browser.get((ROOT/'index.html').as_uri())
        for style in ['ribbons','terrain','twist']:
            name=f'{prefix}-{style}.png'
            uri=browser.execute_script('return window.renderAuraPNG(arguments[0],arguments[1]);',record,{'style':style,**render_settings,'gain':0.2 if record['condition']=='control' else render_settings['gains'][style]})
            (folder/name).write_bytes(base64.b64decode(uri.split(',',1)[1]));optimize_png(folder/name);files.append('/files/'+str((folder/name).relative_to(DATA)))
    return files

def optimize_png(path):
    # Work on a copy: timeout/failure must never damage the original.
    if not shutil.which('optipng'):return
    candidate=path.with_name(path.stem+'.optimizing.png')
    shutil.copyfile(path,candidate)
    try:
        subprocess.run(['optipng','-quiet','-o2',str(candidate)],check=True,timeout=20)
        before=path.stat().st_size;after=candidate.stat().st_size
        if after<before:candidate.replace(path)
        print(f'PNG {path.name}: {before} -> {min(before,after)} bytes',flush=True)
    except (subprocess.SubprocessError,OSError) as error:
        print(f'PNG optimization skipped: {error}',flush=True)
    finally:candidate.unlink(missing_ok=True)

def random_name():
    return secrets.choice(['Lunar','Velvet','Silver','Astral','Quiet','Phantom'])+' '+secrets.choice(['Echo','Orbit','Signal','Mirage','Comet','Horizon'])+' '+uuid.uuid4().hex[:4].upper()

def name_capture(payload):
    if not session or not state.get('capture_id') or payload.get('capture_id')!=state['capture_id']:
        raise ValueError('Select the current capture before naming it')
    value=payload.get('name','')
    if not isinstance(value,str) or len(value)>80:raise ValueError('Name must be 80 characters or fewer')
    value=' '.join(value.split()) or state.get('capture_name') or random_name()
    path=session/state['capture_id']/'capture.json'
    record=json.loads(path.read_text());record['capture_name']=value
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(record,indent=2));temp.replace(path)
    with lock:state['capture_name']=value
    status('Capture name saved.')

def survey():
    global session,baseline,selected
    stop_receiver();baseline=None;selected=None
    session=DATA/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]);session.mkdir(parents=True)
    with lock:state.update(candidates=[],gallery=[],baseline=None,center_hz=None,session_id=session.name,capture_id=None,capture_name=None)
    status('Surveying 88–108 MHz. Keep the capture area empty.','surveying')
    with (session/'survey.log').open('w') as log:
        subprocess.run(['rtl_power','-f','88M:108M:100k','-g','20.7','-i','5','-e','20s',str(session/'survey.csv')],stdout=log,stderr=log,check=True,timeout=40)
    # Integrate across 300 kHz neighborhoods. These are candidate bands, not station IDs.
    tracks={}
    for r in csv.reader((session/'survey.csv').open()):
        lo,hi,step=map(float,r[2:5]);stamp=r[0]+r[1]
        for i,z in enumerate(r[6:]):
            f=lo+i*step
            if f>=hi:continue
            center=round(f/300000)*300000
            tracks.setdefault(center,{}).setdefault(stamp,[]).append(float(z))
    candidates=[]
    for f,times in tracks.items():
        if not 88300000<=f<=107700000:continue
        values=[10*math.log10(st.mean(10**(z/10) for z in v)) for v in times.values()]
        if len(values)<3:continue
        mean=st.mean(values);sd=st.stdev(values)
        candidates.append({'center_hz':f,'power_db':round(mean,2),'variation_db':round(sd,3),'score':mean-3*sd})
    chosen=[]
    for c in sorted(candidates,key=lambda c:c['score'],reverse=True):
        if all(abs(c['center_hz']-x['center_hz'])>=600000 for x in chosen):chosen.append(c)
        if len(chosen)==5:break
    if not chosen:raise RuntimeError('No usable survey candidates; check antenna and survey.log.')
    with lock:state['candidates']=chosen
    status('Select a candidate band. Ranking uses strength and stability, not proven presence sensitivity.','choose')

def tune(center):
    global receiver,selected,baseline
    if center not in [c['center_hz'] for c in state['candidates']]:raise ValueError('Choose a surveyed candidate')
    stop_receiver();baseline=None;selected=center
    low=center-1250000;high=center+1250000
    with lock:state.update(baseline=None,gallery=[],center_hz=center)
    log=(session/'receiver.log').open('a')
    receiver=subprocess.Popen(['rtl_power','-f',f'{low}:{high}:25000','-g','20.7','-i','1',str(session/'stream.csv')],stdout=log,stderr=log);log.close()
    status('Warming receiver. Frequency and gain are now fixed.')
    time.sleep(10)
    status('Receiver ready. Clear the capture area, then measure a baseline.','ready')

def measure():
    start=time.time();time.sleep(8);end=time.time();time.sleep(2)
    if receiver is None or receiver.poll() is not None:raise RuntimeError('Receiver is not running. Select frequency again.')
    data=[v for t,v in rows(session/'stream.csv',selected-150000,selected+150000,start+2) if t<=end-1]
    if len(data)<3 or len({len(v) for v in data})!=1:raise RuntimeError('Insufficient consistent RF readings. Try again.')
    bins,power=summarize(data);powers=[10*math.log10(st.mean(10**(z/10) for z in v)) for v in data]
    return {'bins':bins,'power':power,'sd':st.stdev(powers),'capture_unix':int(start),'samples':len(data)}

def calibrate(immediate=False):
    global baseline
    if not selected:raise ValueError('Select frequency first')
    baseline=None
    with lock:state['baseline']=None;state['gallery']=[];state['capture_id']=None;state['capture_name']=None
    if not immediate:countdown('Empty baseline begins in 3 seconds.',3)
    status('Measuring empty baseline. Stay outside.','calibrating');b=measure()
    center=st.mean(b['bins']);spread=max(max(abs(x-center) for x in b['bins']),1e-9)
    b['record']={'trial':0,'condition':'control','capture_unix':b['capture_unix'],'effect_db':0,'delta':[(x-center)/spread*.15 for x in b['bins']], 'frequency_hz':[selected-1250000,selected+1250000],'analysis_hz':[selected-150000,selected+150000]}
    b['id']=uuid.uuid4().hex[:10];folder=session/('baseline-'+b['id']);folder.mkdir();(folder/'baseline.json').write_text(json.dumps(b,indent=2))
    status('Rendering baseline previews. You may return.');b['images']=render(b['record'],folder,'baseline');baseline=b
    with lock:state['baseline']={'id':b['id'],'variation_db':round(b['sd'],3),'samples':b['samples']};state['gallery']=b['images']
    status('Review the baseline and its variation. Lock it or rescan.','baseline_review')

def capture(immediate=False):
    if not baseline or state['stage'] not in ['locked','gallery']:raise ValueError('Lock a baseline first')
    if not immediate:countdown('Capture begins in 3 seconds.',3)
    status('Hold still. Capturing radio measurements.','capturing');p=measure()
    if len(p['bins'])!=len(baseline['bins']):raise ValueError('Frequency bins changed; recalibrate')
    folder=session/('guest-'+uuid.uuid4().hex[:10]);folder.mkdir()
    record={**baseline['record'],'trial':1,'condition':'person','capture_unix':p['capture_unix'],'effect_db':p['power']-baseline['power'],'delta':[a-b for a,b in zip(p['bins'],baseline['bins'])],'baseline_id':baseline['id'],'gain_db':20.7,'render_settings':{'gains':{'ribbons':1.1,'terrain':1.4,'twist':1},**render_settings},'session_id':session.name}
    record['capture_name']=random_name()
    (folder/'capture.json').write_text(json.dumps(record,indent=2));status('Capture complete. Rendering on the Pi. You may leave the spot.')
    # Render the empty partner with the same settings as this guest.
    empty_images=render(baseline['record'],folder,'baseline')
    images=render(record,folder,'presence')
    with lock:state['gallery']=empty_images+images;state['capture_id']=folder.name;state['capture_name']=record['capture_name']
    status('Six images ready. Download an image or capture the next guest.','gallery')

def update_settings(payload):
    dark=payload.get('dark');chroma=payload.get('chroma');size=payload.get('size')
    if type(dark) is not bool or type(chroma) not in (int,float) or not math.isfinite(chroma) or not 0<=chroma<=1 or size not in [[1080,1350],[1080,1080],[1080,1920]]:
        raise ValueError('Invalid render settings')
    gains=payload.get('gains',render_settings['gains'])
    if not isinstance(gains,dict) or set(gains)!={'ribbons','terrain','twist'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0.2<=v<=2 for v in gains.values()):
        raise ValueError('Invalid amplitude settings')
    render_settings.update(dark=dark,chroma=chroma,size=size,gains=gains)
    with lock:state['render_settings']=dict(render_settings)
    status('Render settings saved for the next baseline or guest.')

def capture_library():
    entries=[]
    for record_path in DATA.glob('*/guest-*/capture.json'):
        folder=record_path.parent
        if folder.is_symlink() or record_path.is_symlink() or not folder.resolve().is_relative_to(DATA.resolve()):continue
        try:
            record=json.loads(record_path.read_text())
            images=[folder/f'{phase}-{style}.png' for phase in ['baseline','presence'] for style in ['ribbons','terrain','twist']]
            if not all(p.is_file() and not p.is_symlink() for p in images):continue
            entries.append({'id':str(folder.relative_to(DATA)), 'name':record.get('capture_name') or folder.name,
                'timestamp':record.get('capture_unix',int(record_path.stat().st_mtime)),
                'images':['/files/'+str(p.relative_to(DATA)) for p in images]})
        except (ValueError,OSError):continue
    return sorted(entries,key=lambda x:(x['timestamp'],x['id']),reverse=True)

def delete_capture(identifier):
    entry=next((e for e in capture_library() if e['id']==identifier),None)
    if not entry:raise ValueError('Capture not found')
    folder=DATA/entry['id']
    # Exact catalog IDs only. Never accept a path supplied directly by the client.
    shutil.rmtree(folder)
    if session and folder.parent==session and folder.name==state.get('capture_id'):
        state.update(capture_id=None,capture_name=None,gallery=baseline['images'] if baseline else [],stage='locked' if baseline else 'idle')
    state['message']='Capture deleted from Pi. iPhone copies are unchanged.'
    save()

def run(action,payload):
    try:
        if action=='settings':update_settings(payload)
        elif action=='survey':survey()
        elif action=='tune':tune(int(payload['center_hz']))
        elif action=='baseline':calibrate(payload.get('countdown_done') is True)
        elif action=='lock':
            if not baseline or state['stage']!='baseline_review':raise ValueError('Measure baseline first')
            status('Baseline locked. Ready for a guest.','locked')
        elif action=='capture':capture(payload.get('countdown_done') is True)
        elif action=='name':name_capture(payload)
        else:raise ValueError('Unknown action')
    except Exception as e:status(str(e),'error')
    finally:
        with lock:state['busy']=False;state['remaining']=0;save()

class Handler(BaseHTTPRequestHandler):
    def reply(self,code,body,kind='application/json'):
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path=='/api/library':
            with lock:body=json.dumps(capture_library()).encode()
            return self.reply(200,body)
        if path=='/api/state':
            with lock:body=json.dumps(state).encode()
            return self.reply(200,body)
        if path=='/':return self.reply(200,(ROOT/'session.html').read_bytes(),'text/html; charset=utf-8')
        if path.startswith('/files/'):
            p=(DATA/path[7:]).resolve()
            if p.is_relative_to(DATA.resolve()) and p.is_file() and p.suffix=='.png':return self.reply(200,p.read_bytes(),'image/png')
        self.reply(404,b'{}')
    def do_POST(self):
        if urlparse(self.path).path!='/api/action':return self.reply(404,b'{}')
        # Local UI only: reject cross-origin browser mutations.
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.reply(403,b'{}')
        if self.headers.get('Content-Type')!='application/json':return self.reply(415,b'{}')
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<4096:raise ValueError()
            body=json.loads(self.rfile.read(n));action=body['action']
            if action not in ['survey','tune','baseline','lock','capture','settings','name','delete']:raise ValueError()
        except (ValueError,KeyError):return self.reply(400,b'{}')
        with lock:
            if state['busy']:return self.reply(409,b'{"error":"A job is already running"}')
            if action=='delete':
                try:delete_capture(body.get('id'));return self.reply(200,b'{}')
                except ValueError as error:return self.reply(404,json.dumps({'error':str(error)}).encode())
            state['busy']=True
        threading.Thread(target=run,args=(action,body),daemon=True).start();self.reply(202,b'{}')
    def log_message(self,*args):pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8080);parser.add_argument('--data',type=Path,default=Path.home()/'auracam-sessions');args=parser.parse_args();DATA=args.data.resolve();DATA.mkdir(parents=True,exist_ok=True)
    print(f'Open http://radiopi.local:{args.port} on your local network. No public internet exposure or authentication is configured.',flush=True)
    try:ThreadingHTTPServer(('0.0.0.0',args.port),Handler).serve_forever()
    finally:stop_receiver()
