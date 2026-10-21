#!/usr/bin/env python3
"""Inspect section metadata without executing Wasm; run from any directory."""
import os
from pathlib import Path
import csv,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
class R:
 def __init__(self,b): self.b=b;self.i=0
 def byte(self):
  if self.i>=len(self.b): raise ValueError('EOF')
  x=self.b[self.i];self.i+=1;return x
 def u(self):
  n=0
  for k in range(5):
   x=self.byte();n|=(x&127)<<(7*k)
   if not x&128:return n
  raise ValueError('LEB overflow')
 def name(self):
  n=self.u();b=self.b[self.i:self.i+n];self.i+=n;return b.decode('utf-8')
 def limits(self):
  f=self.u();lo=self.u();hi=self.u() if f&1 else None
  return {'flags':f,'min':lo,'max':hi}
def inspect(p):
 b=p.read_bytes();r=R(b);r.i=8
 sections={}
 while r.i<len(b):
  kind=r.byte();n=r.u();end=r.i+n
  if end>len(b):raise ValueError('section truncated')
  if kind: sections[kind]=b[r.i:end]
  r.i=end
 types=[]
 if 1 in sections:
  q=R(sections[1])
  for _ in range(q.u()):
   if q.byte()!=0x60:raise ValueError('non function type')
   args=[q.byte() for _ in range(q.u())];rets=[q.byte() for _ in range(q.u())]
   types.append({'params':[hex(x) for x in args],'results':[hex(x) for x in rets]})
 imports=[];ft=[];mem=[]
 if 2 in sections:
  q=R(sections[2])
  for _ in range(q.u()):
   mod,name,k=q.name(),q.name(),q.byte();d={'module':mod,'name':name,'kind':k}
   if k==0:
    t=q.u();d['type']=types[t];ft.append(t)
   elif k==1:d['element_type']=q.byte();d['limits']=q.limits()
   elif k==2:d['limits']=q.limits();mem.append(d['limits'])
   elif k==3:d['value_type']=q.byte();d['mutable']=q.byte()
   elif k==4:d['attribute']=q.byte();d['type_index']=q.u()
   else:raise ValueError('import kind')
   imports.append(d)
 if 3 in sections:
  q=R(sections[3]);ft.extend(q.u() for _ in range(q.u()))
 if 5 in sections:
  q=R(sections[5]);mem.extend(q.limits() for _ in range(q.u()))
 exports=[]
 if 7 in sections:
  q=R(sections[7])
  for _ in range(q.u()):
   name,k,idx=q.name(),q.byte(),q.u();d={'name':name,'kind':k,'index':idx}
   if k==0:d['type']=types[ft[idx]]
   exports.append(d)
 start=R(sections[8]).u() if 8 in sections else None
 return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'imports':imports,'exports':exports,'start':start,'memories':mem}
rows=[inspect(p) for p in sorted(Path('Dataset/Dataset1_S').rglob('*.wasm'))]
out=Path('docs/dataset1_s-inventaire.csv')
with out.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
 for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
for label in ['Benign','Malware']:
 rs=[r for r in rows if '/'+label+'/' in r['path']]
 print(label,'modules',len(rs),'no_imports',sum(not r['imports'] for r in rs),'start',sum(r['start'] is not None for r in rs),'exported_functions',sum(any(e['kind']==0 for e in r['exports']) for r in rs),'shared_memory',sum(any(m['flags']&2 for m in r['memories']) for r in rs))
 print('import_modules',collections.Counter(i['module'] for r in rs for i in r['imports']))
 print('common_imports',collections.Counter((i['module'],i['name']) for r in rs for i in r['imports']).most_common(16))
 print('common_function_exports',collections.Counter(e['name'] for r in rs for e in r['exports'] if e['kind']==0).most_common(16))
 print('no_import_examples',[(r['path'],[e['name'] for e in r['exports'] if e['kind']==0][:8]) for r in rs if not r['imports']][:8])
print('Parsed',len(rows),'module envelopes; this is not full Wasm validation.')
