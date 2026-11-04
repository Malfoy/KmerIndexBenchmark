"""One entry point for installation, data, benchmarks, results and plots."""
import argparse,json,os,platform,shutil,sys
from pathlib import Path
from .common import ROOT,TOOLS,atomic,load,threads

def doctor(work):
 required={'python3':(3,11),'git':None,'cmake':None,'c++':None,'make':None,'cargo':None,'rustc':None,'pigz':None,'/usr/bin/time':None}
 missing=[]
 print(f'Platform: {platform.system()} {platform.machine()} | available CPUs: {threads()} | work directory: {work}')
 for name in required:
  present=shutil.which(name);print(f'{"OK     " if present else "MISSING"} {name}'+(f' ({present})' if present else ''))
  if not present:missing.append(name)
 print('Native tools are pinned in configs/tools.lock.json. Rust>=1.89 is required to compile the frozen Zindex source.')
 return int(bool(missing) or sys.version_info<(3,11,8))
def main(argv=None):
 parser=argparse.ArgumentParser(prog='./bench',description='Install and reproduce the Zindex paper bacterial benchmarks.')
 parser.add_argument('--workdir',type=Path,default=Path(os.environ.get('BENCH_WORKDIR',ROOT/'work')),help='Downloads, installed tools, logs and results (default: ./work). Put this on a large disk.')
 sub=parser.add_subparsers(dest='command',required=True)
 sub.add_parser('doctor',help='Check installation prerequisites and available CPUs')
 sub.add_parser('datasets',help='Show frozen collections and available sizes')
 p=sub.add_parser('install',help='Install all tools, or only the named tools, under the work directory');p.add_argument('tools',nargs='*',choices=[*TOOLS,'kmtricks'])
 p=sub.add_parser('download',help='Download only missing genomes; preserve compression and accession order');p.add_argument('collection',choices=['refseq','atb']);p.add_argument('--size',type=int,default=64)
 p=sub.add_parser('run',help='Run every selected tool at each size before growing; preserve results and clean indexes');p.add_argument('collection',choices=['refseq','atb']);p.add_argument('--sizes',type=int,nargs='+',default=[64]);p.add_argument('--bits',type=int,nargs='+',choices=[4,8,16],default=[8]);p.add_argument('--mode',choices=['dense','minimizers','both'],default='both');p.add_argument('--tools',nargs='+',choices=TOOLS,default=list(TOOLS));p.add_argument('--keep-indexes',action='store_true');p.add_argument('--keep-prepared',action='store_true',help='Retain externally computed minimizer FASTAs after each collection size');p.add_argument('--max-ram-gb',type=float,default=48,help='Explicit sampled native RSS budget, decimal GB; 0 disables this guard (recorded)');p.add_argument('--disk-reserve-gb',type=float,default=2);p.add_argument('--planner',choices=['streaming','full','naive'],help='Optional Zindex construction comparison; use separate --workdir values');p.add_argument('--dry-run',action='store_true',help='Print the queue without installing, downloading or running tools')
 p=sub.add_parser('results',help='Show measured results without rerunning');p.add_argument('--paper',action='store_true')
 p=sub.add_parser('plot',help='Generate EPS/PDF/PNG dashboards');p.add_argument('--paper',action='store_true',help='Use bundled paper measurements instead of your own results');p.add_argument('--output',type=Path,default=Path('plots'))
 p=sub.add_parser('verify',help='Verify accession nesting, pinned source and bundled query checksums');p.add_argument('--queries',action='store_true',help='Also hash every compressed workload (about168MB)')
 args=parser.parse_args(argv);work=args.workdir.expanduser().resolve()
 try:
  if args.command=='doctor':return doctor(work)
  if args.command=='datasets':
   for name,d in load(ROOT/'data/provenance.json')['collections'].items():print(name+': '+', '.join(map(str,d['sizes']))+' genomes; '+d['accession_type'])
   return 0
  if args.command=='install':
   from .install import install
   install(work,args.tools or list(TOOLS));return 0
  if args.command=='download':
   from .data import download
   download(work,args.collection,args.size);return 0
  if args.command=='run':
   from .data import manifest
   for n in args.sizes:manifest(args.collection,n)
   if args.max_ram_gb<0 or args.disk_reserve_gb<0:raise ValueError('Resource budgets cannot be negative')
   from .runner import run
   run(work,args.collection,args.sizes,args.bits,['dense','minimizers'] if args.mode=='both' else [args.mode],args.tools,args.keep_indexes,args.max_ram_gb,args.disk_reserve_gb,args.keep_prepared,args.planner,args.dry_run)
   if args.dry_run:return 0
   status=load(work/'status.json');return 1 if status['failed'] else 0
  if args.command=='results':
   from .plot import export_results
   values=load(ROOT/'paper/results.json')['families'] if args.paper else None
   rows=[dict(r,collection=f['dataset'],bits=f['bits']) for f in values for r in f['rows']] if values else export_results(work)
   print('Collection\tbits\tgenomes\ttool\tmode\tstatus\tindexGB\tbuild_s\tpositive_s\tnegative_s')
   for r in rows:print('\t'.join(str(r.get(k,'')) for k in ['collection','bits','genomes','tool','representation','status'])+'\t'+str(round(r['index_bytes']/1e9,3) if r.get('index_bytes') is not None else '')+'\t'+'\t'.join(str(r.get(k,'')) for k in ['build_wall_s','positive_wall_s','negative_wall_s']))
   return 0
  if args.command=='plot':
   from .plot import plot
   plot(work,args.output.resolve(),args.paper);return 0
  if args.command=='verify':
   from .verification import verify
   verify(args.queries);return 0
 except Exception as exc:
  print('Error:',str(exc) or repr(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
