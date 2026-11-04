"""Serial all-tools-per-size runner; successful measurements are never repeated."""
import fcntl,gzip,json,math,os,shutil,time,traceback
from pathlib import Path
from .common import ROOT,TOOLS,atomic,load,native_env,now,remove_owned,sha,size,threads
from . import adapters,data
from .measure import measure
from .query_cache import cached_query
from .validate import validate

def cleanup(work):
 removed=[]
 for p in work.iterdir():
  if p.name=='tmp' or p.name.startswith('index') or p.name.startswith('.zor-pow2-building-'):
   removed.append(dict(path=p.name,apparent_bytes=size(p)));remove_owned(p,work)
 atomic(work/'cleanup.json',dict(completed_utc=now(),removed=removed,inputs_and_results_preserved=True))
def archive_output(path):
 path=Path(path)
 if path.is_file():
  # Pigz uses all affinity CPUs; raw output is removed only after successful gzip validation.
  import subprocess
  output=path.with_name(path.name+'.gz');part=output.with_name(output.name+'.partial')
  with part.open('wb') as out:subprocess.run(['pigz','-p',str(threads()),'-1','-c',str(path)],stdout=out,check=True)
  subprocess.run(['pigz','-t',str(part)],check=True);part.replace(output);path.unlink()
 elif path.is_dir():
  for p in sorted(path.rglob('*')):
   if p.is_file():archive_output(p)

def admission(work,tool,rows,p,rep,reserve):
 required=reserve*1e9
 if tool=='kmindex':
  bits=p.get('bits',p.get('kmindex_bits'));matrix=math.ceil(bits/8)*math.ceil(len(rows)/8)*8
  occurrences=[r['bases']*(.1 if rep=='minimizers' else 1) for r in rows]
  required+=math.ceil(1.15*matrix+12*sum(bits*-math.expm1(-n/bits) for n in occurrences))
 free=shutil.disk_usage(work).free
 return dict(required_disk_bytes=int(required),available_disk_bytes=free,estimate_not_measurement=True,admitted=free>=required,native_attempted=False)
def run_case(work,collection,n,bits,rep,tool,keep_indexes,max_ram_gb,disk_reserve_gb,planner=None):
 result=work/f'results/{collection}/{bits}bit/{rep}/n{n}/{tool}';done=result/'result.json';failed=result/'FAILED.json'
 if done.exists():
  saved=load(done)
  if saved.get('status')!='resource_blocked' or shutil.disk_usage(work).free<saved['required_disk_bytes']:return saved
  assert not list(result.glob('*.command.json')), 'Only pre-native deferrals can be reconsidered'
  atomic(work/f'reports/reconsidered-{collection}-{bits}-{rep}-{n}-{tool}.json',saved)
  done.unlink();(result/'admission.json').unlink(missing_ok=True)
 if failed.exists():return dict(status='failed_retained',source=str(failed),tool=tool,genomes=n,bits=bits,collection=collection,representation=rep)
 if result.exists() and any(result.iterdir()):raise ValueError('Interrupted case; inspect without overwriting or rerunning: '+str(result))
 result.mkdir(parents=True,exist_ok=True);profile=load(ROOT/f'configs/{bits}bit.json')
 if planner:profile['parameters'][rep]['zindex']['merge_planner']=planner
 if max_ram_gb:profile['parameters'][rep]['zindex']['max_ram_gb']=max_ram_gb
 else:profile['parameters'][rep]['zindex'].pop('max_ram_gb',None)
 rows=data.samples(work,collection,n);q=data.workloads(collection,n);bin_dir=work/'tools/bin'
 if not (bin_dir/tool).exists():raise ValueError(f'{tool} is not installed. Run ./bench install {tool}')
 identity=dict(collection=collection,genomes=n,bits=bits,representation=rep,tool=tool,parameters=adapters.params(profile,rep,tool),threads=threads(),binary_sha256=sha(bin_dir/tool),input_accessions_sha256=sha(ROOT/f'data/accessions/{collection}/{n}.txt'),queries={k:v['sha256'] for k,v in q['workloads'].items()},query_runs=1,query_ratio=.8,max_ram_gb=max_ram_gb,minimum_disk_reserve_gb=disk_reserve_gb)
 if tool in ('fulgor','metagraph','themisto') and not keep_indexes:
  for previous in (work/f'results/{collection}').glob(f'*bit/{rep}/n{n}/{tool}/result.json'):
   old=load(previous)
   keys=['collection','genomes','representation','tool','parameters','threads','binary_sha256','input_accessions_sha256','queries','max_ram_gb','minimum_disk_reserve_gb']
   # Completed result queries contain metrics, so compare workload SHA identities separately.
   if old.get('status')=='complete' and all(old.get(k)==identity.get(k) for k in keys if k!='queries') and load(previous.parent/'identity.json')['queries']==identity['queries']:
    value=dict(old,bits=bits,reused_exact_measurement=True,reused_from=str(previous),index_retained=False)
    atomic(result/'identity.json',identity);atomic(done,value);return value
 if identity['parameters'].get('analytic_not_empirically_frozen'):
  value=dict(identity,status='not_calibrated_in_paper',native_attempted=False,reason='Only an analytical matrix size is available; the paper profile does not claim an empirically frozen comparison.')
  atomic(done,value);print(f'{tool}: no calibrated paper configuration for {bits}bit {rep}; not launched',flush=True);return value
 check=admission(work,tool,rows,identity['parameters'],rep,disk_reserve_gb);atomic(result/'admission.json',check)
 if not check['admitted']:
  value=dict(identity,status='resource_blocked',**check);atomic(result/'result.json',value);print(f'{tool}: skipped before launch (disk estimate exceeds free space)',flush=True);return value
 atomic(result/'identity.json',identity);stage='prepare_inputs'
 try:
  simd=None;counts=None;extraction='all canonical31mers'
  if rep=='minimizers':
   if adapters.uses_native_minimizers(tool,collection,bits):extraction='native OCM31/window49' if tool=='zindex' else'native Raptor31/window49'
   else:
    simd=data.prepare_simd(work,collection,n,rows,q);rows=simd['samples'];extraction='external canonical SIMD31/w19 FASTA representatives'
  commands,artifacts=adapters.construction(tool,result,bin_dir,rows,profile,rep,collection);metrics=[]
  state_path=work/'status.json'
  for i,command in enumerate(commands,1):
   stage=f'build-{i}';atomic(state_path,dict(status='constructing',case=identity,stage=stage,updated_utc=now()));metrics.append(measure(command,result,stage,bin_dir,construction=True,max_ram_gb=max_ram_gb,disk_reserve_gb=disk_reserve_gb))
  if tool=='kmindex':
   for name in adapters.KM_TEMP:
    p=result/'index/atb'/name
    if p.exists():remove_owned(p,p.parent)
   stage='build-compression';metrics.append(measure(adapters.compression(result,bin_dir),result,stage,bin_dir,construction=True,max_ram_gb=max_ram_gb,disk_reserve_gb=disk_reserve_gb))
   if not (result/'index/atb/compression.cfg').exists() or list((result/'index/atb/matrices').glob('*.cmbf')):raise ValueError('kmindex compression did not publish a compressed index')
  if not all(p.exists() for p in artifacts):raise ValueError('Construction exited successfully but final index files are missing')
  if tool=='zindex':
   manifest=load(result/'index/manifest.json');assert len(manifest['colors'])==n and not manifest.get('skipped_documents');atomic(result/'native-manifest.json',manifest)
  if tool=='raptor' and rep=='minimizers' and adapters.uses_native_minimizers(tool,collection,bits):
   paths=(result/'tmp/prepared/minimiser.list').read_text().splitlines();assert len(paths)==len(rows)
   rows=[dict(row,raptor_path=path) for row,path in zip(rows,paths)]
  measured=dict(identity,status='construction_complete',feature_policy=extraction,build=metrics,index_bytes=sum(size(p) for p in artifacts),build_wall_s=sum(m['wall_seconds'] for m in metrics),build_cpu_s=sum(m['user_seconds']+m['system_seconds'] for m in metrics),build_rss_bytes=max(m['peak_rss_bytes'] for m in metrics),peak_temp_bytes=max(m['sampled_peak_temp_bytes'] for m in metrics),peak_index_plus_temp_bytes=max(m['sampled_peak_index_plus_temp_bytes'] for m in metrics),queries={},accuracy=profile['accuracy'][rep].get(tool),accuracy_scope='Frozen standalone5Mb evaluation only, no collection-level key FPR claim',external_preparation=None if simd is None else {'wall_s':simd['external_preparation_wall_s'],'shared_across_tools':True,'excluded_from_native_build_timing':True})
  atomic(result/'construction-result.json',measured)
  for label,item in q['workloads'].items():
   stage='query-'+label;external=simd['workloads'][label] if simd else None
   source=Path(external['path'] if external else item['path']);counts=external['counts'] if external else None;length=31 if external else 1000
   output=result/f'{stage}.tsv.raw';command,stdout,native_output=adapters.query(tool,result,bin_dir,source,output,length,.8)
   atomic(state_path,dict(status='querying_once',case=identity,stage=stage,updated_utc=now()))
   with cached_query(source) as cache:
    atomic(result/(stage+'.cache.json'),cache);metric=measure(command,result,stage,bin_dir,stdout,max_ram_gb=max_ram_gb,disk_reserve_gb=disk_reserve_gb)
   validation=validate(tool,native_output,rows,q['source_metadata'],label,counts,.8)
   atomic(result/(stage+'.validation.json'),validation)
   measured['queries'][label]=dict(metric=metric,validation=validation,cache=cache,original_reads=q['count'],length=1000,wall_s=metric['wall_seconds'],cpu_s=metric['user_seconds']+metric['system_seconds'],rss_bytes=metric['peak_rss_bytes'],seq_s=q['count']/metric['wall_seconds'],bases_s=1000*q['count']/metric['wall_seconds'])
   atomic(result/'partial-result.json',measured);archive_output(native_output)
  if not keep_indexes:cleanup(result)
  measured.update(status='complete',completed_utc=now(),index_retained=keep_indexes);atomic(done,measured)
  print(f'{collection} {bits}bit {rep} n={n} {tool}: complete ({measured["index_bytes"]/1e9:.3f}GB, {measured["build_wall_s"]:.2f}s build)',flush=True)
  return measured
 except Exception as exc:
  failure=dict(identity,status='failed',stage=stage,reason=str(exc),traceback=traceback.format_exc(),created_utc=now(),automatic_native_retry=False)
  atomic(failed,failure);print(f'{tool}: failed at {stage}; details: {failed}',flush=True);return failure
 finally:
  if not keep_indexes and not (result/'cleanup.json').exists():cleanup(result)

def cleanup_prepared(work,collection,n):
 prepared=work/f'data/prepared/{collection}/{n}'
 if not prepared.exists():return
 archive=work/f'reports/preparation/{collection}/{n}'
 for p in prepared.rglob('*'):
  if p.is_file() and p.suffix in ['.json','.log','.fof']:
   target=archive/p.relative_to(prepared);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 shutil.rmtree(prepared)
 atomic(work/f'reports/prepared-cleanup-{collection}-{n}.json',dict(derived_minimizer_inputs_removed=True,preparation_reports_logs_counts_manifests_retained=str(archive),primary_genomes_queries_and_all_results_preserved=True,completed_utc=now()))

def run(work,collection,sizes,bits,modes,tools,keep_indexes=False,max_ram_gb=48,disk_reserve_gb=2,keep_prepared=False,planner=None,dry_run=False):
 work.mkdir(parents=True,exist_ok=True)
 if dry_run:
  for n in sorted(sizes):
   for width in bits:
    for rep in modes:
     for tool in tools:print(f'{collection}\tn={n}\t{width}bit\t{rep}\t{tool}\tthreads={threads()}')
  return
 for tool in set(tools):
  if not (work/'tools/bin'/tool).exists():raise ValueError(f'Missing {tool}; install first: ./bench install {tool}')
 atomic(work/'reports/machine.json',dict(recorded_utc=now(),os=os.uname().sysname,os_release=os.uname().release,cpu_affinity=sorted(os.sched_getaffinity(0)),cpu_model=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),meminfo=Path('/proc/meminfo').read_text(),threads=threads()))
 if 'minimizers' in modes and any(not adapters.uses_native_minimizers(t,collection,b) for t in tools for b in bits) and not (work/'tools/bin/minimizer-fasta').exists():raise ValueError('External minimizer input needs the pinned helper: ./bench install zindex')
 with (work/'.benchmark.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  outcomes=[]
  for n in sorted(sizes):
   data.samples(work,collection,n)
   for width in bits:
    for rep in modes:
     for tool in tools:outcomes.append(run_case(work,collection,n,width,rep,tool,keep_indexes,max_ram_gb,disk_reserve_gb,planner))
   from .plot import export_results
   export_results(work)
   if not keep_prepared:cleanup_prepared(work,collection,n)
  atomic(work/'summary.json',dict(completed_utc=now(),cases=outcomes,completed=sum(r.get('status')=='complete' for r in outcomes),threads=threads()))
  atomic(work/'status.json',dict(status='finished',updated_utc=now(),complete=sum(r.get('status')=='complete' for r in outcomes),failed=sum(r.get('status') in ['failed','failed_retained'] for r in outcomes),resource_blocked=sum(r.get('status')=='resource_blocked' for r in outcomes)))
