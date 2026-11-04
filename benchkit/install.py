"""Pinned, prefix-local installation. No sudo and no changes to global configuration."""
import os,platform,shutil,subprocess,urllib.request
from pathlib import Path
from .common import ROOT,TOOLS,atomic,extract,load,native_env,now,sha,threads

def transfer(url,dest):
 dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
 part=dest.with_name(dest.name+'.partial')
 with urllib.request.urlopen(urllib.request.Request(url),timeout=120) as inp,part.open('wb') as out:shutil.copyfileobj(inp,out)
 part.replace(dest)
def unpack(archive,source):
 source=Path(source)
 if source.exists():return
 staged=source.with_name('.'+source.name+'.extracting')
 if staged.exists():shutil.rmtree(staged)
 extract(archive,staged);staged.rename(source)

def install(work,selected):
 if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('The pinned release assets require Linux x86_64. Source builds can be adapted in benchkit/install.py.')
 prefix=work/'tools';bin_dir=prefix/'bin';bin_dir.mkdir(parents=True,exist_ok=True);(work/'logs/install').mkdir(parents=True,exist_ok=True)
 lock=load(ROOT/'configs/tools.lock.json');selection=list(dict.fromkeys([*selected,*(['kmtricks'] if 'kmindex' in selected else [])]))
 for name in selection:
  spec=lock[name];source=prefix/'src'/name;stamp=prefix/f'{name}.json'
  if stamp.exists():
   info=load(stamp)
   if info['pin']!=spec or not (bin_dir/name).exists() or sha(bin_dir/name)!=info['binary_sha256']:raise ValueError(f'Installed {name} changed; inspect {stamp}, do not overwrite it silently')
   for helper,digest in info.get('helpers',{}).items():
    if not (bin_dir/helper).exists() or sha(bin_dir/helper)!=digest:raise ValueError('Installed helper changed or missing: '+helper)
   print(f'{name}: already installed',flush=True);continue
  print(f'Installing {name}; log: {work}/logs/install/{name}.log',flush=True)
  env=native_env(bin_dir)
  with (work/f'logs/install/{name}.log').open('a') as log:
   def run(cmd,cwd=None):
    log.write('$ '+repr(list(map(str,cmd)))+'\n');log.flush();subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   if name=='zindex':
    archive=ROOT/spec['source_archive'];assert sha(archive)==spec['sha256']
    if not (source/'Cargo.toml').exists():unpack(archive,source)
    env['CARGO_TARGET_DIR']=str(prefix/'build/zindex')
    # Build the production CLI and external SIMD helper from the same frozen source.
    run(['cargo','build','--locked','--release','-j',threads(),'-p','zorindex','--bin','zorindex'],source)
    run(['cargo','build','--locked','--release','-j',threads(),'-p','minimizer-fasta'],source)
    binary=prefix/'build/zindex/release/zorindex'
    helper=prefix/'build/zindex/release/minimizer-fasta';target_helper=bin_dir/'minimizer-fasta'
    if target_helper.exists() and sha(target_helper)!=sha(helper):raise ValueError('Refusing to replace a different installed minimizer helper')
    if not target_helper.exists():shutil.copy2(helper,target_helper)
   elif 'repo' in spec:
    if not (source/'.git').exists():run(['git','clone','--no-checkout',spec['repo'],source])
    run(['git','fetch','origin',spec['commit']],source);run(['git','checkout','--detach',spec['commit']],source);run(['git','submodule','update','--init','--recursive'],source)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==spec['commit']
    if name=='kaminari':
     patch=ROOT/'patches/kaminari-minimizers-single-merge.patch';assert sha(patch)==spec['patches'][0]['sha256']
     sub=source/'bundled/Minimizers'
     check=subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=sub,capture_output=True)
     if check.returncode:run(['git','apply',patch],sub)
     arg=prefix/'src/argparse'
     if not arg.exists():run(['git','clone','https://github.com/yhhshb/argparse.git',arg])
     run(['git','checkout','--detach',spec['argparse_commit']],arg)
    if name=='raptor':
     seqan=source/'lib/seqan3/include/seqan3'
     for f in ['alignment/matrix/detail/trace_directions.hpp','alphabet/views/translate.hpp','io/sam_file/sam_flag.hpp','core/detail/strong_type.hpp','core/debug_stream/debug_stream_type.hpp']:
      p=seqan/f;p.write_text(p.read_text().replace('\nconstexpr bool add_enum_bitwise_operators<','\ninline constexpr bool add_enum_bitwise_operators<'))
    build=prefix/'build'/name
    cmd=['cmake','-S',source,'-B',build,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_POLICY_VERSION_MINIMUM=3.5']
    if name=='kaminari':cmd+=['-DFETCHCONTENT_SOURCE_DIR_ARGPARSE='+str(arg)]
    if name=='raptor':cmd+=['-DCMAKE_CXX_FLAGS=-include cstdint','-DRAPTOR_USE_CCACHE=OFF']
    run(cmd);run(['cmake','--build',build,'--target',name,'--parallel',threads()])
    candidates=[p for p in build.rglob(name) if p.is_file() and os.access(p,os.X_OK)];assert len(candidates)==1,candidates;binary=candidates[0]
   else:
    asset=prefix/'downloads'/spec['url'].split('/')[-1]
    if not asset.exists():transfer(spec['url'],asset)
    if sha(asset)!=spec['sha256']:raise ValueError('Release asset checksum mismatch: '+str(asset))
    if name=='metagraph':binary=asset;binary.chmod(0o755)
    else:
     if not source.exists():unpack(asset,source)
     if name=='cobs':
      candidates=list(source.glob('CMakeLists.txt')) or list(source.glob('*/CMakeLists.txt'));assert len(candidates)==1
      build=prefix/'build/cobs';run(['cmake','-S',candidates[0].parent,'-B',build,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_POLICY_VERSION_MINIMUM=3.5','-DCMAKE_CXX_FLAGS=-include stdint.h']);run(['cmake','--build',build,'--target','cobs','--parallel',threads()]);binary=build/'src/cobs'
     else:
      candidates=[p for p in source.rglob(name) if p.is_file() and os.access(p,os.X_OK)];assert len(candidates)==1,candidates;binary=candidates[0]
   target=bin_dir/name
   if target.exists() or target.is_symlink():
    if target.resolve()!=binary.resolve() or not target.exists() or sha(target)!=sha(binary):raise ValueError('Refusing to replace existing binary '+str(target))
   else:target.symlink_to(os.path.relpath(binary,target.parent))
   atomic(stamp,dict(tool=name,installed_utc=now(),binary_sha256=sha(target),pin=spec,threads=threads(),helpers={'minimizer-fasta':sha(bin_dir/'minimizer-fasta')} if name=='zindex' else {}))
 print('Tools installed in',bin_dir)
