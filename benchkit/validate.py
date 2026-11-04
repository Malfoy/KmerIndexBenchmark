"""Validate native output IDs and original-read source recovery, without FPR claims."""
import bisect,hashlib,math,re
from pathlib import Path
from .kmindex_scores import stream_scores

def hits(tool,path,samples,ratio):
 if tool=='kmindex':
  for qid,scores in stream_scores(path/'atb.json'):yield int(qid.removeprefix('q')),{int(k.removeprefix('color')) for k,v in scores.items() if v>=ratio}
  return
 by_path={str(Path(value).resolve()):s['color'] for s in samples for value in [s['path'],s.get('raptor_path',s['path'])]};mapping={}
 with path.open() as f:
  if tool=='zindex':assert next(f).strip()=='query_id\tvalid_kmers\thits'
  if tool=='raptor':
   for line in f:
    if line=='#QUERY_NAME\tUSER_BINS\n':break
    if line.startswith('#') and line[1:2].isdigit():
     number,value=line[1:].rstrip('\n').split('\t',1);mapping[int(number)]=by_path[str(Path(value).resolve())]
   assert len(mapping)==len(samples)
  for line in f:
   if tool=='zindex':
    q,n,text=line.rstrip('\n').split('\t');n=int(n)
    yield int(q.removeprefix('q')),{int(a) for a,b in (v.split(':') for v in text.split(',') if v) if int(b)>=n*ratio} if n else set()
   elif tool=='cobs':
    q,n=line.rstrip('\n').split('\t');values=set()
    for _ in range(int(n)):
     name,score=next(f).rstrip('\n').split('\t');values.add(int(Path(name).name.split('.',1)[0].removeprefix('color')))
    yield int(q.removeprefix('*q')),values
   elif tool=='raptor':q,text=line.rstrip('\n').split('\t');yield int(q.removeprefix('q')),{mapping[int(x)] for x in text.split(',') if x}
   elif tool=='kaminari':
    fields=line.rstrip('\n').split('\t');values={int(x) for x in re.findall(r'\((\d+),\d+\)',line)};assert int(fields[1])==len(values);yield int(fields[0].removeprefix('q')),values
   elif tool in ('fulgor','themisto'):
    values=list(map(int,line.split()));yield values[0],set(values[2:] if tool=='fulgor' else values[1:])
   else:
    fields=line.rstrip('\n').split('\t');yield int(fields[1].removeprefix('q')),{by_path[str(Path(x).resolve())] for field in fields[2:] for x in field.split(':') if x}

def validate(tool,path,samples,metadata,label,counts=None,ratio=.8):
 count=len(metadata);counts=counts or [1]*count;cumulative=[];total=0
 for n in counts:total+=n;cumulative.append(total)
 seen=bytearray(total);found=[0]*count;any_hits=0;xor=0
 for qid,values in hits(tool,path,samples,ratio):
  if not 0<=qid<total or seen[qid] or any(not 0<=v<len(samples) for v in values):raise ValueError('Duplicate or invalid native result ID')
  seen[qid]=1;parent=bisect.bisect_right(cumulative,qid);any_hits+=bool(values)
  if label=='positive':found[parent]+=int(int(metadata[parent]['source_color']) in values)
  xor^=int.from_bytes(hashlib.sha256(f'{qid}:{sorted(values)}'.encode()).digest(),'big')
 if sum(seen)!=total:raise ValueError(f'Native output has {sum(seen)}/{total} records')
 return dict(native_records=total,original_reads=count,source_misses=sum(v<math.ceil(ratio*n) for v,n in zip(found,counts)) if label=='positive' else None,records_with_hits=any_hits,semantic_sha256_xor=f'{xor:064x}',accuracy_scope='Original-read source recovery only; not an individual-key FPR or FNR measurement')
