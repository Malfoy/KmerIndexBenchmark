"""Native paper commands. All thread counts follow the process CPU affinity."""
from pathlib import Path
from .common import threads
KM_TEMP={'fpr','filters','howde_index','merge_infos','counts','histograms','partition_infos','superkmers','minimizers'}

def params(profile,rep,tool):return profile['parameters'][rep].get(tool,{})
def uses_native_minimizers(tool,collection,bits):return tool=='zindex' or (tool=='raptor' and collection=='atb' and bits==8)
def construction(tool,work,bin_dir,samples,profile,rep,collection):
 b=str(bin_dir/tool);t=str(threads());p=params(profile,rep,tool);idx=work/'index';tmp=work/'tmp';tmp.mkdir(exist_ok=True)
 fof=work/'inputs.fof';fof.write_text(''.join(r['path']+'\n' for r in samples));target=profile['target_fpr'];commands=[]
 if tool=='zindex':
  fof.write_text(''.join(f'{r["color"]:08d}\t{r["path"]}\n' for r in samples))
  command=[b,'--threads',t,'build','--fof',str(fof),'--output',str(idx),'--k','49' if rep=='minimizers' else '31','--index-mode','minimizers' if rep=='minimizers' else 'kmers','--technical-layout','flat','--stack-compression','none','--power-of-two-merge','--build-jobs',t,'--skip-oversized-documents=false']
  for key,value in p.items():
   command.append('--'+key.replace('_','-')+('='+str(value).lower() if isinstance(value,bool) else ''))
   if not isinstance(value,bool):command.append(str(value))
  if rep=='minimizers':command+=['--minimizer-size','31','--minimizer-scheme','open-closed-mod']
  commands=[command];artifacts=[idx]
 elif tool=='cobs':
  aliases=tmp/'inputs';aliases.mkdir();paths=[]
  for row in samples:
   alias=aliases/f'color{row["color"]:08d}.fna.gz';alias.symlink_to(row['path']);paths.append(alias)
  fof.write_text(''.join(str(p)+'\n' for p in paths))
  commands=[[b,'compact-construct','--file-type','list',str(fof),str(work/'index.cobs_compact'),'-k','31','-T',t,'-m',str((8 if profile['bits']==8 else 32)*2**30),'--false-positive-rate',str(p.get('native_target_fpr',p.get('bloom_fpr',target))),'--num-hashes',str(p.get('hashes',p.get('cobs_hashes',profile['bits'])))]];artifacts=[work/'index.cobs_compact']
 elif tool=='raptor':
  native=rep=='minimizers' and uses_native_minimizers(tool,collection,profile['bits'])
  if native:
   prepared=tmp/'prepared';commands.append([b,'prepare','--input',str(fof),'--output',str(prepared),'--kmer','31','--window','49','--kmer-count-cutoff','1','--threads',t]);layout_input=prepared/'minimiser.list'
  else:layout_input=fof
  commands.extend([[b,'layout','--input-file',str(layout_input),'--output-filename',str(tmp/'layout.tsv'),'--kmer-size','31','--false-positive-rate',str(p.get('native_target_fpr',p.get('bloom_fpr',target))),'--num-hash-functions',str(p.get('hashes',p.get('raptor_hashes',min(5,profile['bits'])))),'--threads',t],[b,'build','--input',str(tmp/'layout.tsv'),'--output',str(idx),* ([] if native else ['--window','31']),'--threads',t]])
  artifacts=[idx]
 elif tool=='kaminari':
  commands=[[b,'build','-i',str(fof),'-o',str(idx),'-k','31','-m',str(p.get('kaminari_m',30)),'-b',str(p.get('kaminari_bits',profile['bits'])),'-a','-g','8192','-t',t,*(['-s','42','-c','4'] if profile['bits']!=8 else [])]];artifacts=[idx]
 elif tool=='fulgor':commands=[[b,'build','-l',str(fof),'-o',str(idx),'-k','31','-m','19','-g','8','-t',t,'-d',str(tmp)]];artifacts=[Path(str(idx)+'.fur')]
 elif tool=='metagraph':
  files=[r['path'] for r in samples]
  commands=[[b,'build','-k','31','--mode','canonical','--mem-cap-gb','8','-p',t,'-o',str(idx),*files],[b,'annotate','-i',str(idx)+'.dbg','--anno-filename','--anno-type','column','-p',t,'-o',str(idx),*files]];artifacts=[Path(str(idx)+'.dbg'),Path(str(idx)+'.column.annodbg')]
 elif tool=='themisto':commands=[[b,'build','-k','31','-i',str(fof),'--index-prefix',str(idx),'--temp-dir',str(tmp),'--mem-gigas','8','--n-threads',t,'--file-colors']];artifacts=[Path(str(idx)+'.tdbg'),Path(str(idx)+'.tcolors')]
 elif tool=='kmindex':
  bits=p.get('bits',p.get('kmindex_bits'));assert bits
  fof.write_text(''.join(f'color{r["color"]:08d}: {r["path"]}\n' for r in samples))
  commands=[[b,'build','--fof',str(fof),'--index',str(idx),'--run-dir','@inplace','--register-as','atb','--hard-min','1','--kmer-size','31','--bloom-size',str(bits),'--nb-partitions',t,'--threads',t,'--km-path',str(bin_dir/'kmtricks')]];artifacts=[idx]
 else:raise ValueError(tool)
 return commands,artifacts

def compression(work,bin_dir):return [str(bin_dir/'kmindex'),'compress','--global-index',str(work/'index'),'--name','atb','--block-size','8','--cpr-level','6','--threads',str(threads()),'--delete','--check']
def query(tool,work,bin_dir,source,output,length,ratio):
 b=str(bin_dir/tool);idx=work/'index';t=str(threads())
 if tool=='zindex':return [b,'--threads',t,'query','--index',str(idx),'--query',str(source),'--min-ratio',str(ratio),'--records','--record-batch-size','4096','--query-memory','subindex'],output,output
 if tool=='cobs':return [b,'query','-i',str(work/'index.cobs_compact'),'-f',str(source),'-t',str(ratio),'-T',t],output,output
 if tool=='raptor':return [b,'search','--index',str(idx),'--query',str(source),'--output',str(output),'--threads',t,'--query_length',str(length),'--threshold',str(ratio)],None,output
 if tool=='kaminari':return [b,'query','-x',str(idx),'-i',str(source),'-o',str(output),'-r',str(ratio),'-t',t],None,output
 if tool=='fulgor':return [b,'pseudoalign','-i',str(idx)+'.fur','-q',str(source),'-o',str(output),'-r',str(ratio),'-t',t],None,output
 if tool=='metagraph':return [b,'query','-i',str(idx)+'.dbg','-a',str(idx)+'.column.annodbg','--query-mode','labels','--min-kmers-fraction-label',str(ratio),'-p',t,'--batch-size','10000000',str(source)],output,output
 if tool=='themisto':return [b,'pseudoalign','--query-file',str(source),'--index-prefix',str(idx),'--temp-dir',str(work/'tmp'),'--out-file',str(output),'--n-threads',t,'--threshold',str(ratio),'--include-unknown-kmers'],None,output
 directory=output.with_suffix('.d');return [b,'query','--index',str(idx),'--fastx',str(source),'--zvalue','0','--threshold',str(ratio),'--format','json','--aggregate','--output',str(directory),'--threads',t,'--batch-size','1000'],None,directory
