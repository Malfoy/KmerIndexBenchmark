#!/usr/bin/env python3
"""Deterministic test double; never constructs a biological index."""
import gzip,json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name;args=sys.argv[1:]
if args[:1]==['--threads']:args=args[2:]
def arg(k,default=None):return args[args.index(k)+1] if k in args else default
def fasta(p):
 with gzip.open(p,'rt') as f:
  while header:=f.readline():yield header[1:].strip(),f.readline().strip()
def touch(p,text='fixture'):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
if name=='minimizer-fasta':
 if '--fof' in args:
  out=Path(arg('--output-dir'));out.mkdir(parents=True);lines=[]
  for i,line in enumerate(Path(arg('--fof')).read_text().splitlines()):
   color,path=line.split('\t');dest=out/f'{i}.fasta.gz'
   with gzip.open(dest,'wt') as f:
    for j,(_,seq) in enumerate(fasta(path),1):f.write(f'>r{j}_p0\n{seq[:31]}\n')
   lines.append(f'{color}\t{dest}\n')
  (out/'minimizers.fof').write_text(''.join(lines))
 else:
  with gzip.open(args[1],'wt') as f:
   for i,(_,seq) in enumerate(fasta(args[0]),1):f.write(f'>r{i}_p0\n{seq[:31]}\n')
 sys.exit(0)
cmd=args[0]
if cmd=='build' or cmd=='compact-construct':
 if name in ['zindex','kaminari']:
  index=Path(arg('--output') or arg('-o'));index.mkdir(parents=True)
  rows=Path(arg('--fof') or arg('-i')).read_text().splitlines();touch(index/'manifest.json',json.dumps(dict(colors=[{} for _ in rows],hashes=8,fingerprint_bits=8)))
 elif name=='cobs':touch(args[args.index('--file-type')+3])
 elif name=='raptor':touch(arg('--output'),Path(arg('--input')).read_text())
 elif name=='fulgor':touch(arg('-o')+'.fur')
 elif name=='metagraph':touch(arg('-o')+'.dbg')
 elif name=='themisto':touch(arg('--index-prefix')+'.tdbg');touch(arg('--index-prefix')+'.tcolors')
 elif name=='kmindex':touch(Path(arg('--index'))/'atb/matrices/matrix.cmbf')
 sys.exit(0)
if cmd=='annotate':touch(arg('-o')+'.column.annodbg');sys.exit(0)
if cmd=='layout':touch(arg('--output-filename'),Path(arg('--input-file')).read_text());sys.exit(0)
if cmd=='compress':
 touch(Path(arg('--global-index'))/'atb/compression.cfg')
 for p in (Path(arg('--global-index'))/'atb/matrices').glob('*.cmbf'):p.unlink()
 sys.exit(0)
source=arg('--query') or arg('-f') or arg('-i') if name=='kaminari' else None
if name=='zindex':source=arg('--query')
elif name=='cobs':source=arg('-f')
elif name=='raptor':source=arg('--query')
elif name=='kaminari':source=arg('-i')
elif name=='fulgor':source=arg('-q')
elif name=='metagraph':source=args[-1]
elif name=='themisto':source=arg('--query-file')
elif name=='kmindex':source=arg('--fastx')
reads=list(fasta(source));out=[];mapping=Path.cwd()/'inputs.fof';inputs=mapping.read_text().splitlines()
if name=='zindex':out=['query_id\tvalid_kmers\thits\n']
if name=='raptor':out=[f'#{i}\t{p}\n' for i,p in enumerate(inputs)]+['#QUERY_NAME\tUSER_BINS\n']
km={}
for i,(qid,seq) in enumerate(reads):
 hit=seq[0] in 'AT'
 if name=='zindex':out.append(f'{qid}\t1\t'+('0:1' if hit else '')+'\n')
 elif name=='cobs':out.append(f'*{qid}\t{int(hit)}\n'+('color00000000.fna.gz\t1\n' if hit else ''))
 elif name=='raptor':out.append(f'{qid}\t'+('0' if hit else '')+'\n')
 elif name=='kaminari':out.append(f'{qid}\t{int(hit)}\t'+('(0,1)' if hit else '')+'\n')
 elif name=='fulgor':out.append(f'{i} {int(hit)}'+(' 0' if hit else '')+'\n')
 elif name=='themisto':out.append(str(i)+(' 0' if hit else '')+'\n')
 elif name=='metagraph':out.append(f'{i}\t{qid}'+('\t'+inputs[0] if hit else '')+'\n')
 else:km[qid]={'color00000000':1.0} if hit else {}
text=''.join(out)
if name in ['zindex','cobs','metagraph']:sys.stdout.write(text)
elif name=='kmindex':touch(Path(arg('--output'))/'atb.json',json.dumps({'atb':km}))
else:touch(arg('--output') or arg('-o') or arg('--out-file'),text)
