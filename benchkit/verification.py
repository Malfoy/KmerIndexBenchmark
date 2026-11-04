"""Checks that make an exported reproduction kit independently auditable."""
import csv,gzip,json,re
from pathlib import Path
from .common import ROOT,load,sha

def verify(queries=False):
 report=load(ROOT/'data/provenance.json');checked=0
 for family,info in report['collections'].items():
  with gzip.open(ROOT/f'data/manifests/{family}.tsv.gz','rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
  assert len(rows)==info['genomes']
  ids=[r['accession'] for r in rows];assert len(ids)==len(set(ids))
  assert [int(r['color']) for r in rows]==list(range(len(rows)))
  for n in info['sizes']:
   actual=(ROOT/f'data/accessions/{family}/{n}.txt').read_text().splitlines();assert actual==ids[:n]
   checked+=1
  pattern=r'GCF_\d+\.\d+' if family=='refseq' else r'SAM[END][A-Z]?\d+'
  assert all(re.fullmatch(pattern,r['accession']) for r in rows)
  assert all(json.loads(r['urls']) and all(u.startswith('https://') for u in json.loads(r['urls'])) for r in rows)
 seed_ids=(ROOT/'data/accessions/seed-study-32.txt').read_text().splitlines();assert len(seed_ids)==32 and len(set(seed_ids))==32
 reference=load(ROOT/'data/reference/identity.json');assert sha(ROOT/reference['file'])==reference['compressed_sha256']
 lock=load(ROOT/'configs/tools.lock.json');z=lock['zindex'];assert sha(ROOT/z['source_archive'])==z['sha256']
 for entry in lock['kaminari']['patches']:assert sha(ROOT/entry['file'])==entry['sha256']
 for bits in [4,8,16]:
  p=load(ROOT/f'configs/{bits}bit.json');assert p['target_fpr']==2**-bits
  for rep in ['dense','minimizers']:
   z=p['parameters'][rep]['zindex'];assert z['fingerprint_bits']==bits and z['hashes']==(8 if bits==8 else 4)
 if queries:
  index=load(ROOT/'data/queries/index.json');seen=set()
  for key,v in index.items():
   if 'reuse' in v:assert v['reuse'] in index;continue
   with gzip.open(ROOT/v['metadata'],'rt') as f:meta=json.load(f)
   assert len(meta['source_metadata'])==meta['count'] and meta['length']==1000
   for item in meta['workloads'].values():
    if item['path'] not in seen:assert sha(ROOT/item['path'])==item['sha256'];seen.add(item['path'])
  print(f'{len(seen)} exact compressed query workloads verified')
 print(f'{checked} nested accession lists, both complete manifests, source pin and fixed precision profiles verified')
