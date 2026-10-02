#!/usr/bin/env python3
"""Run on the Pi as a normal user. Keeps one receiver process across both phases."""
import argparse,base64,csv,datetime as dt,json,math,signal,statistics as st,subprocess,time
from pathlib import Path

def summarize(rows):
    bins=[10*math.log10(st.mean(10**(v[i]/10) for v in rows)) for i in range(len(rows[0]))]
    power=st.mean(10*math.log10(st.mean(10**(v/10) for v in row)) for row in rows)
    return bins,power

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path.home()/'auracam-captures')
    parser.add_argument('--render-only',type=Path,help='Existing capture.json; no radio acquisition')
    args=parser.parse_args()
    if args.render_only:
        folder=args.render_only.resolve().parent;record=json.loads(args.render_only.read_text())
    else:
        folder=args.output/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True)
        windows={};proc=None
        def wait(label,seconds):
            print('SAY:'+label,flush=True)
            for remaining in range(seconds,0,-1):
                if proc is not None and proc.poll() is not None:raise RuntimeError('Receiver stopped; check receiver.log')
                print(f'{remaining} seconds',flush=True);time.sleep(1)
        try:
            wait('Leave the room. Empty baseline starts after warmup.',20)
            with (folder/'receiver.log').open('w') as log:
                proc=subprocess.Popen(['rtl_power','-f','88M:90.5M:25k','-g','20.7','-i','1',str(folder/'spectrum.csv')],stdout=log,stderr=log)
                wait('Warming receiver; stay outside.',10)
                windows['empty']=[dt.datetime.now().isoformat()];wait('Recording empty baseline. Stay outside.',12);windows['empty'].append(dt.datetime.now().isoformat())
                wait('ENTER NOW. Stand on your marked spot.',10)
                capture_unix=int(time.time());windows['person']=[dt.datetime.now().isoformat()];wait('Hold still. Capturing RF.',8);windows['person'].append(dt.datetime.now().isoformat())
        finally:
            if proc is not None and proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            (folder/'windows.json').write_text(json.dumps({'windows':windows,'clock':str(dt.datetime.now().astimezone().tzinfo)},indent=2))
    # Reconstruct the baseline from saved raw measurements, including older sessions.
    windows=json.loads((folder/'windows.json').read_text())['windows']
    groups={k:[] for k in windows}
    for r in csv.reader((folder/'spectrum.csv').open()):
        t=dt.datetime.fromisoformat(r[0].strip()+'T'+r[1].strip());lo,hi,step=map(float,r[2:5])
        v=[float(z) for i,z in enumerate(r[6:]) if 89150000<=lo+i*step<89450000]
        for name,(a,b) in windows.items():
            if dt.datetime.fromisoformat(a)+dt.timedelta(seconds=2)<=t<=dt.datetime.fromisoformat(b)-dt.timedelta(seconds=2):groups[name].append(v)
    if any(len(v)<3 for v in groups.values()):raise RuntimeError('Insufficient valid readings; inspect raw recording')
    empty,ep=summarize(groups['empty']);person,pp=summarize(groups['person'])
    if not args.render_only:
        record={'trial':1,'condition':'person','capture_unix':capture_unix,'effect_db':pp-ep,'delta':[p-e for p,e in zip(person,empty)],'method':'preceding empty baseline; no following empty phase','frequency_hz':[88000000,90500000],'analysis_hz':[89150000,89450000]}
        (folder/'capture.json').write_text(json.dumps(record,indent=2))
    # Transfer the known person epoch to the earlier baseline without guessing timezone.
    elapsed=(dt.datetime.fromisoformat(windows['person'][0])-dt.datetime.fromisoformat(windows['empty'][0])).total_seconds()
    center=st.mean(empty);spread=max(max(abs(v-center) for v in empty),1e-9)
    baseline={**record,'condition':'control','capture_unix':round(record['capture_unix']-elapsed),'effect_db':0,
              'delta':[(v-center)/spread*.15 for v in empty], 'power_bins_db':empty,
              'method':'empty spectrum centered and normalized to +/-0.15 for subtle artistic shape; zero change relative to itself'}
    (folder/'baseline.json').write_text(json.dumps(baseline,indent=2))
    print('SAY:Capture complete. Rendering your baseline and presence images.',flush=True)
    # Same Canvas function as the interactive app; no screenshot/UI scaling.
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    options=webdriver.ChromeOptions();options.binary_location='/usr/bin/chromium'
    options.add_argument('--headless=new');options.add_argument('--disable-dev-shm-usage')
    with webdriver.Chrome(service=Service('/usr/bin/chromedriver'),options=options) as browser:
        browser.get((Path(__file__).resolve().parent/'index.html').as_uri())
        for label,item in [('baseline',baseline),('presence',record)]:
            for style in ['ribbons','terrain','twist']:
                url=browser.execute_script('return window.renderAuraPNG(arguments[0],arguments[1]);',item,{'style':style,'dark':True,'size':[1080,1350]})
                (folder/f'{label}-{style}-1080x1350.png').write_bytes(base64.b64decode(url.split(',',1)[1]))
    print('SAY:All six images are ready.',flush=True)
    print('RESULT:'+str(folder),flush=True)
if __name__=='__main__':main()
