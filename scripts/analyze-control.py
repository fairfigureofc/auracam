import csv,json,math,statistics as st,itertools,argparse
from datetime import datetime,timedelta
from pathlib import Path
parser=argparse.ArgumentParser(description='Analyze an AuraCam randomized recording with the prespecified band and phase windows.')
parser.add_argument('recording', type=Path)
parser.add_argument('--output', type=Path, help='Optional JSON result path')
args=parser.parse_args()
p=args.recording
m=json.loads((p/'phases.json').read_text());rows=[]
for r in csv.reader((p/'spectrum.csv').open()):
 t=datetime.fromisoformat(r[0].strip()+'T'+r[1].strip());lo,hi,step=map(float,r[2:5]);v=list(map(float,r[6:]))[:round((hi-lo)/step)]
 vals=[z for i,z in enumerate(v) if 89150000<=lo+i*step<89450000]
 power=10*math.log10(st.mean(10**(z/10) for z in vals))
 rows.append((t,power))
g={}
for ph in m['phases']:
 start=datetime.fromisoformat(ph['start'])+timedelta(seconds=2);end=datetime.fromisoformat(ph['end'])-timedelta(seconds=2)
 v=[z for t,z in rows if start<=t<=end]
 if v:g[ph['phase']]={'n':len(v),'mean':st.mean(v),'sd':st.stdev(v)}
out=[]
for i,c in enumerate(m['trial_order'],1):
 before=g['empty_control_b' if i==1 else f'trial_{i-1}_empty'];during=g[f'trial_{i}_{c}'];after=g[f'trial_{i}_empty']
 out.append({'trial':i,'condition':c,'effect_db':during['mean']-(before['mean']+after['mean'])/2,'before':before,'during':during,'after':after})
print('rows',len(rows),'gaps',[(str(a[0]),(b[0]-a[0]).total_seconds()) for a,b in zip(rows,rows[1:]) if (b[0]-a[0]).total_seconds()!=1])
for x in out: print(x['trial'],x['condition'],'effect',round(x['effect_db'],4),'before/during/after',*[round(x[k]['mean'],4) for k in ['before','during','after']],'n',x['during']['n'])
person=[x['effect_db'] for x in out if x['condition']=='person'];control=[x['effect_db'] for x in out if x['condition']=='control'];obs=st.mean(person)-st.mean(control)
print('person mean',st.mean(person),'control mean',st.mean(control),'difference',obs)
# Enumerate only assignments permitted by randomized blocks (2 of 4 per block).
null=[]
for a in itertools.combinations(range(4),2):
 for b in itertools.combinations(range(4,8),2):
  ids=set(a+b);null.append(st.mean(out[i]['effect_db'] for i in ids)-st.mean(out[i]['effect_db'] for i in range(8) if i not in ids))
print('two-sided randomization p',sum(abs(v)>=abs(obs)-1e-12 for v in null)/len(null),'assignments',len(null))
if args.output: args.output.write_text(json.dumps({'trials':out,'person_mean_db':st.mean(person),'control_mean_db':st.mean(control),'difference_db':obs},indent=2))
