"""GNU time and sampled construction disk/RSS accounting, with explicit limits."""
import json,os,resource,shutil,signal,subprocess,threading,time
from pathlib import Path
from .common import atomic,load,native_env,now,size,threads
from .adapters import KM_TEMP

def disk(work):
 index=temp=0
 for p in work.iterdir():
  if p.name.startswith('index') and (p.name.endswith('.tmp') or '.tmp.' in p.name):temp+=size(p,True)
  elif p.name.startswith('index'):
   n=size(p,True);index+=n
   if p.is_dir():
    for name in KM_TEMP:v=size(p/'atb'/name,True);temp+=v;index-=v
  elif p.name=='tmp':temp+=size(p,True)
  elif p.name.startswith('.zor-pow2-building-'):
   for part in p.iterdir():
    if part.name in ['features','cells','abandoned']:temp+=size(part,True)
    else:index+=size(part,True)
 return dict(index_allocated_bytes=index,temp_allocated_bytes=temp)
def measure(command,work,label,bin_dir,stdout=None,construction=False,max_ram_gb=48,disk_reserve_gb=2):
 marker=work/(label+'.command.json')
 if marker.exists():raise ValueError('Native stage already attempted; no automatic retry: '+str(marker))
 if shutil.disk_usage(work).free<disk_reserve_gb*1e9:raise ValueError('Disk reserve insufficient before native launch')
 atomic(marker,list(map(str,command)));(work/'tmp').mkdir(exist_ok=True)
 soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(min(524288,hard) if hard!=-1 else 524288,hard))
 timed=['/usr/bin/time','-f','%e\t%U\t%S\t%M\t%x','-o',str(work/(label+'.time.tsv')),*map(str,command)]
 snapshots=[];guards=[];sampling_errors=[];done=threading.Event();child=None;observed_rss=0
 def record_disk():
  try:snapshots.append(disk(work))
  except FileNotFoundError:pass
  except Exception as e:sampling_errors.append(str(e))
 def sample():
  nonlocal observed_rss
  last=time.monotonic()
  while not done.wait(.25):
   if construction and time.monotonic()-last>=30:record_disk();last=time.monotonic()
   if child is None:continue
   rss=0;pending=[child.pid]
   while pending:
    pid=pending.pop();p=Path(f'/proc/{pid}')
    try:
     for line in (p/'status').read_text().splitlines():
      if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
     pending.extend(map(int,(p/'task'/str(pid)/'children').read_text().split()))
    except (FileNotFoundError,ProcessLookupError):pass
   observed_rss=max(observed_rss,rss)
   free=shutil.disk_usage(work).free
   if not guards and ((max_ram_gb and rss>max_ram_gb*1e9) or free<disk_reserve_gb*1e9):
    guards.append(dict(measured_native_tree_rss_bytes=rss,ram_limit_gb=max_ram_gb,free_disk_bytes=free,disk_reserve_gb=disk_reserve_gb,utc=now()))
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
 if construction:record_disk()
 thread=threading.Thread(target=sample,daemon=True);thread.start();started=now()
 try:
  with Path(stdout or work/(label+'.stdout.log')).open('w') as out,(work/(label+'.stderr.log')).open('w') as err:
   child=subprocess.Popen(timed,cwd=work,env=native_env(bin_dir),stdout=out,stderr=err,start_new_session=True)
   atomic(work/'active-native.json',dict(pid=child.pid,command=list(map(str,command)),stage=label,started_utc=started))
   code=child.wait()
 finally:
  done.set();thread.join()
  if construction:record_disk()
  (work/'active-native.json').unlink(missing_ok=True)
 values=(work/(label+'.time.tsv')).read_text().splitlines();fields=values[-1].split('\t') if values else []
 result=dict(exit_code=code,threads=threads(),started_utc=started,finished_utc=now(),guards=guards,sampled_native_tree_peak_rss_bytes=observed_rss)
 if len(fields)==5:
  wall,user,system,rss,exit_code=fields;result.update(wall_seconds=float(wall),user_seconds=float(user),system_seconds=float(system),peak_rss_bytes=int(rss)*1024)
 if construction:result.update(sampled_peak_temp_bytes=max((x['temp_allocated_bytes'] for x in snapshots),default=0),sampled_peak_index_plus_temp_bytes=max((sum(x.values()) for x in snapshots),default=0),disk_sampling_interval_seconds=30,disk_sampling_note='Sampled lower bound, gzip inputs and query outputs excluded; output staging separated from native scratch',disk_sampling_errors=sampling_errors)
 atomic(work/(label+'.metrics.json'),result)
 if code or guards or len(fields)!=5:raise RuntimeError(f'{label} exited {code}; retained logs and metrics in {work}')
 return result
