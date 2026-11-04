"""Small shared helpers; benchmark execution requires only Python's standard library."""
import contextlib,csv,datetime,gzip,hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOLS=('zindex','cobs','raptor','kmindex','kaminari','fulgor','metagraph','themisto')
def threads():return len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.partial');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while chunk:=f.read(4*2**20):h.update(chunk)
 return h.hexdigest()
def load(path):return json.loads(Path(path).read_text())
def fasta(path):
 opener=gzip.open if (str(path).endswith('.gz') or str(path).endswith('.gz.partial')) else open
 with opener(path,'rt') as f:
  name=None;pieces=[]
  for line in f:
   if line.startswith('>'):
    if name is not None:yield name,''.join(pieces).upper()
    name=line[1:].split()[0];pieces=[]
   else:pieces.append(line.strip())
  if name is not None:yield name,''.join(pieces).upper()
def size(path,allocated=False):
 path=Path(path)
 if not path.exists() or path.is_symlink():return 0
 if path.is_file():s=path.stat();return s.st_blocks*512 if allocated else s.st_size
 total=0
 for base,dirs,files in os.walk(path,followlinks=False):
  dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink()]
  for name in files:
   p=Path(base)/name
   try:
    if not p.is_symlink():s=p.stat();total+=s.st_blocks*512 if allocated else s.st_size
   except FileNotFoundError:pass
 return total
def remove_owned(path,parent):
 path=Path(path);parent=Path(parent).resolve()
 if path.parent.resolve()!=parent:raise ValueError('Cleanup must stay in its owning case')
 if path.is_symlink():path.unlink()
 elif path.is_dir():shutil.rmtree(path)
 elif path.exists():path.unlink()
def extract(archive,dest):
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   target=(dest/m.name).resolve()
   if not target.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive entry: '+m.name)
   if m.issym() or m.islnk():
    link=((target.parent if m.issym() else dest)/m.linkname).resolve()
    if not link.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive link: '+m.name)
  t.extractall(dest,filter='data')
def native_env(bin_dir):
 return dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],OMP_NUM_THREADS=str(threads()),RAYON_NUM_THREADS=str(threads()),CARGO_BUILD_JOBS=str(threads()),SHARG_NO_VERSION_CHECK='1',LC_ALL='C')
