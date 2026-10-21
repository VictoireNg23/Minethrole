#!/usr/bin/env python3
"""Extract the patch constants verbatim; --check detects drift without rewriting."""
from pathlib import Path
import argparse, csv, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
patch=(ROOT/'patches/v8.patch').read_text()
profiles=['coinhive','cryptoloot','unknown_algorithm_1','unknown_algorithm_2']
stored=[];active=[]
for mode,profile in enumerate(profiles):
 m=re.search(r'baseline_key_'+profile+r'\[[^=]+?=\s*(.*?);',patch,re.S)
 groups=re.findall(r'\{([^{}]+)\}',m.group(1).replace('\n+','\n'))
 for row,g in enumerate(groups):
  w=row+1 if mode==0 else row*2+1 if mode<3 else 5
  for rank,key in enumerate(map(int,re.findall(r'\d+',g))):
   v=key;ops=[]
   for _ in range(w):v,d=divmod(v,123);ops.append(d+0x45)
   assert v==0
   item={'profile':profile,'window':w,'rank':rank,'key':key,'opcodes':ops[::-1]}
   stored.append(item)
   if w==5 and rank<3:active.append(dict(item,counter=3*mode+rank))
def matrix(name):
 text=re.search(name+r'\[4\]\[3\]\s*=\s*(.*?);',patch,re.S).group(1)
 return [[float(x) for x in re.findall(r'\d+(?:\.\d+)?',g)] for g in re.findall(r'\{([^{}]+)\}',text)]
config={'id':'original-v8-patch','patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'window_size':5,'stored':stored,'active':active,'means':matrix('baseline_value'),'stddev':matrix('baseline_stddev'),'normalized':matrix('baseline_normalized'),'interval_cpu_ms':500,'cosine_threshold':0.99,'sigma_threshold':3.0,'original_defensive_default':False,'sleep_seconds':10,'timer_wall_ms':50}
out=ROOT/'config/original.json';expected=json.dumps(config,indent=2)+'\n'
assert len(stored)==193 and len(active)==12 and len({x['key'] for x in active})==12
if args.check:
 assert out.read_text()==expected,'config/original.json differs from patch extraction'
 rows=list(csv.DictReader((ROOT/'docs/signatures-originales.csv').open()))
 assert [(x['profile'],x['window'],x['rank'],x['key']) for x in stored]==[(x['profile'],int(x['window']),int(x['rank'])-1,int(x['key_decimal'])) for x in rows]
 print('PASS: 193 stored / 12 active keys, opcode decoding, profiles and CSV match the original patch')
else:out.write_text(expected)
