"""CSV export and paper-style EPS dashboards; Matplotlib is optional until plotting."""
import csv,importlib.util,json
from pathlib import Path
from .common import ROOT,atomic,load,now
FIELDS=['collection','bits','genomes','tool','representation','status','index_bytes','build_wall_s','build_cpu_s','build_rss_bytes','peak_temp_bytes','peak_index_plus_temp_bytes','positive_wall_s','negative_wall_s','positive_rss_bytes','negative_rss_bytes','positive_seq_s','negative_seq_s']
def export_results(work):
 rows=[]
 paths=sorted((work/'results').glob('*/*bit/*/n*/*/result.json'))
 paths+=sorted(p for p in (work/'results').glob('*/*bit/*/n*/*/FAILED.json') if not (p.parent/'result.json').exists())
 for p in paths:
  d=load(p)
  if p.name=='FAILED.json' and (p.parent/'construction-result.json').exists():d=dict(load(p.parent/'construction-result.json'),**{k:v for k,v in d.items() if k!='queries'})
  r={k:d.get(k) for k in FIELDS}
  for label,v in d.get('queries',{}).items():r.update({label+'_wall_s':v['wall_s'],label+'_rss_bytes':v['rss_bytes'],label+'_seq_s':v['seq_s']})
  rows.append(r)
 (work/'reports').mkdir(exist_ok=True)
 with (work/'reports/results.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
 atomic(work/'reports/results.json',dict(updated_utc=now(),measurements=rows))
 return rows

def module():
 try:
  import matplotlib
 except ImportError as e:raise ValueError('Plotting needs Matplotlib: python3 -m pip install -r requirements-plot.txt') from e
 p=ROOT/'paper/plot.py';spec=importlib.util.spec_from_file_location('paper_figures',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def plot(work,output,paper=False):
 m=module();output.mkdir(parents=True,exist_ok=True)
 if paper:
  records=m.main_scaling(output)
  for family in m.DATA['families']:
   if family['rows']:records.append(m.dashboard(output,family))
  records.extend([m.seeds(output),m.parameters(output)])
  atomic(output/'figures.json',dict(source='Bundled original paper data',figures=records))
 else:
  rows=export_results(work);records=[]
  for collection,bits in sorted({(r['collection'],r['bits']) for r in rows if r['status']=='complete'}):
   family=dict(dataset=collection,bits=bits,rows=[dict(r,representation='kmers' if r['representation']=='dense' else 'minimizers') for r in rows if r['collection']==collection and r['bits']==bits and r['status']=='complete'])
   records.append(m.dashboard(output,family))
  atomic(output/'figures.json',dict(source=str(work/'reports/results.csv'),figures=records))
 print('Figures written to',output)
