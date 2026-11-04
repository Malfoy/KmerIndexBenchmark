"""Frozen nested accession lists, compressed downloads and exact paper workloads."""
import concurrent.futures,csv,gzip,json,os,re,shutil,subprocess,time,urllib.request,urllib.error
from pathlib import Path
from .common import ROOT,atomic,fasta,load,native_env,now,sha,threads

def manifest(collection,n):
 listfile=ROOT/f'data/accessions/{collection}/{n}.txt'
 if not listfile.exists():raise ValueError(f'No frozen {collection} collection of {n} genomes; use ./bench datasets')
 identifiers=listfile.read_text().splitlines()
 with gzip.open(ROOT/f'data/manifests/{collection}.tsv.gz','rt') as f:
  rows=[]
  for row in csv.DictReader(f,delimiter='\t'):
   if len(rows)==n:break
   row.update(color=int(row['color']),bases=int(row['bases']));rows.append(row)
 assert [r['accession'] for r in rows]==identifiers
 return rows

def genome_path(work,collection,accession):return work/f'data/genomes/{collection}/{accession}.fasta.gz'

def download(work,collection,n):
 rows=manifest(collection,n);directory=work/f'data/genomes/{collection}';directory.mkdir(parents=True,exist_ok=True)
 failures=[];done=0
 def fetch(row):
  output=genome_path(work,collection,row['accession']);receipt=output.with_suffix('.json')
  if receipt.exists():
   saved=load(receipt)
   if output.is_file() and output.stat().st_size==saved['compressed_bytes'] and saved['accession']==row['accession']:return
   raise ValueError('Download cache changed: '+str(output))
  if output.exists():
   bases=records=0
   for _,seq in fasta(output):bases+=len(seq);records+=1
   if bases!=row['bases'] or not records:raise ValueError('Incomplete existing file (receipt missing): '+str(output))
   digest=sha(output);urls=json.loads(row['urls'])
   if row.get('compressed_sha256') and all('ftp.ncbi.nlm.nih.gov/' in u for u in urls) and digest!=row['compressed_sha256']:raise ValueError('Existing file checksum mismatch: '+str(output))
   atomic(receipt,dict(accession=row['accession'],urls=urls,bases=bases,records=records,compressed_bytes=output.stat().st_size,sha256=digest,validated_interrupted_download_adopted=True,downloaded_utc=now()))
   return
  part=output.with_name(output.name+'.partial');urls=json.loads(row['urls'])
  for attempt in range(5):
   try:
    with part.open('wb') as out:
     for url in urls:
      request=urllib.request.Request(url)
      with urllib.request.urlopen(request,timeout=180) as inp:
       first=inp.read(2)
       if first==b'\x1f\x8b':out.write(first);shutil.copyfileobj(inp,out)
       elif first.startswith(b'>'):
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,compresslevel=1,mtime=0) as zipped:zipped.write(first);shutil.copyfileobj(inp,zipped)
       else:raise ValueError('Expected FASTA content, got another format: '+url)
    break
   except (urllib.error.URLError,ConnectionError,TimeoutError) as exc:
    if isinstance(exc,urllib.error.HTTPError) and exc.code<500 and exc.code!=429:raise
    if attempt==4:raise
    time.sleep(min(60,2**attempt))
  # All concatenated gzip members must be readable and retain complete genomes.
  bases=records=0
  for _,seq in fasta(part):
   records+=1;bases+=len(seq)
  if bases!=row['bases'] or not records:raise ValueError(f'{row["accession"]}: expected {row["bases"]} bases, got {bases}')
  digest=sha(part)
  if row.get('compressed_sha256') and all('ftp.ncbi.nlm.nih.gov/' in u for u in urls) and digest!=row['compressed_sha256']:raise ValueError('Compressed checksum mismatch: '+row['accession'])
  part.replace(output);atomic(receipt,dict(accession=row['accession'],urls=urls,bases=bases,records=records,compressed_bytes=output.stat().st_size,sha256=digest,downloaded_utc=now()))
 with concurrent.futures.ThreadPoolExecutor(max_workers=threads()) as pool:
  futures={pool.submit(fetch,row):row for row in rows}
  for future in concurrent.futures.as_completed(futures):
   row=futures[future]
   try:future.result();done+=1
   except Exception as exc:failures.append(dict(accession=row['accession'],reason=str(exc)))
   if (done+len(failures))%100==0:print(f'{collection}: {done}/{n} available, {len(failures)} errors',flush=True)
 atomic(work/f'reports/download-{collection}-{n}.json',dict(completed_utc=now(),available=done,requested=n,failures=failures))
 if failures:raise ValueError(f'{len(failures)} accessions unavailable; details in {work}/reports/download-{collection}-{n}.json. No substitutions were made; rerun downloads to retry only missing genomes.')
 print(f'{collection}: {n} compressed genomes ready',flush=True)

def samples(work,collection,n):
 rows=manifest(collection,n)
 for row in rows:
  row['path']=str(genome_path(work,collection,row['accession']).resolve())
  if not Path(row['path']).is_file():raise ValueError(f'Missing {row["accession"]}. Run: ./bench download {collection} --size {n}')
 return rows

def workloads(collection,n):
 index=load(ROOT/'data/queries/index.json');key=f'{collection}/{n}'
 while 'reuse' in index[key]:key=index[key]['reuse']
 with gzip.open(ROOT/index[key]['metadata'],'rt') as f:meta=json.load(f)
 for value in meta['workloads'].values():
  value['path']=str((ROOT/value['path']).resolve())
  if sha(value['path'])!=value['sha256']:raise ValueError('Bundled workload checksum mismatch')
 return meta

def prepare_simd(work,collection,n,rows,queries):
 directory=work/f'data/prepared/{collection}/{n}/simd';proof=directory/'COMPLETE.json'
 if proof.exists():return load(proof)
 if directory.exists():raise ValueError('Interrupted minimizer preparation; inspect/remove only this derived directory: '+str(directory))
 directory.mkdir(parents=True);fof=directory/'inputs.fof';fof.write_text(''.join(f'{r["color"]:08d}\t{r["path"]}\n' for r in rows))
 binary=work/'tools/bin/minimizer-fasta'
 if not binary.exists():raise ValueError('Install zindex to obtain the pinned SIMD minimizer helper: ./bench install zindex')
 env=native_env(binary.parent);started=time.monotonic()
 commands=[[str(binary),'--fof',str(fof),'--output-dir',str(directory/'genomes'),'--k','31','--window','19','--threads',str(threads()),'--minimizer-scheme','simd','--gzip']]
 with (directory/'preparation.log').open('w') as log:
  for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  prepared=[]
  for row,line in zip(rows,(directory/'genomes/minimizers.fof').read_text().splitlines()):
   name,path=line.split('\t');assert int(name)==row['color'];prepared.append(dict(row,path=path))
  assert len(prepared)==len(rows)
  q={}
  for label,value in queries['workloads'].items():
   raw=directory/f'{label}.raw.fasta.gz';output=directory/f'{label}.fasta.gz'
   command=[str(binary),value['path'],str(raw),'--k','31','--window','19','--threads',str(threads()),'--minimizer-scheme','simd','--gzip'];commands.append(command)
   subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   counts=[0]*queries['count'];total=0
   with gzip.open(output,'wt',compresslevel=1) as out:
    for name,sequence in fasta(raw):
     match=re.fullmatch(r'r(\d+)_p\d+',name)
     if not match or len(sequence)!=31:raise ValueError('Unexpected minimizer output header or seed length')
     parent=int(match[1])-1;counts[parent]+=1;out.write(f'>q{total}\n{sequence}\n');total+=1
   raw.unlink();q[label]=dict(path=str(output),counts=counts,count=total,sha256=sha(output))
 result=dict(samples=prepared,workloads=q,commands=commands,k=31,window=19,canonical=True,external_preparation_wall_s=time.monotonic()-started,native_build_timing_excludes_preparation=True)
 atomic(proof,result);return result
