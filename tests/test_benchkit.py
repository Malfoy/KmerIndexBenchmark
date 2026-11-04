import contextlib,gzip,io,json,os,shutil,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchkit import adapters,data,runner
from benchkit.common import ROOT,TOOLS,extract,load,threads
from benchkit.cli import main
from benchkit.verification import verify

class ProtocolTests(unittest.TestCase):
 def test_frozen_collections_and_profiles(self):verify()
 def test_every_profile_uses_all_threads_and_no_findere(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);rows=[dict(color=0,path='/tmp/first.fa.gz'),dict(color=1,path='/tmp/second.fa.gz')]
   for bits in [4,8,16]:
    for mode in ['dense','minimizers']:
     for tool in TOOLS:
      case=root/f'{bits}-{mode}-{tool}';case.mkdir();commands,files=adapters.construction(tool,case,root,rows,load(ROOT/f'configs/{bits}bit.json'),mode,'refseq')
      self.assertTrue(files)
      for cmd in commands:
       flag='--threads' if '--threads' in cmd else '-T' if tool=='cobs' else '-p' if tool=='metagraph' else '--n-threads' if tool=='themisto' else '-t'
       self.assertEqual(cmd[cmd.index(flag)+1],str(threads()));self.assertNotIn('--findere',cmd)
 def test_native_raptor_only_historical_atb8(self):
  self.assertTrue(adapters.uses_native_minimizers('raptor','atb',8));self.assertFalse(adapters.uses_native_minimizers('raptor','refseq',8));self.assertFalse(adapters.uses_native_minimizers('raptor','atb',16))
 def test_refseq_large_queries_reuse_exact16k(self):
  a=data.workloads('refseq',16384);b=data.workloads('refseq',131072)
  self.assertEqual(a,b)
 def test_install_defaults_all_eight_without_launching(self):
  with patch('benchkit.install.install') as install:self.assertEqual(main(['install']),0);self.assertEqual(set(install.call_args.args[1]),set(TOOLS))
 def test_dry_run_order_sizes_before_doubling(self):
  with tempfile.TemporaryDirectory() as t,contextlib.redirect_stdout(io.StringIO()) as out:
   runner.run(Path(t),'refseq',[128,64],[8],['dense','minimizers'],['zindex','cobs'],dry_run=True)
   rows=out.getvalue().splitlines();self.assertEqual(len(rows),8);self.assertTrue(all('n=64' in r for r in rows[:4]));self.assertTrue(all('n=128' in r for r in rows[4:]));self.assertFalse(list(Path(t).glob('results')))
 def test_tar_rejects_escape(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);archive=t/'bad.tar'
   with tarfile.open(archive,'w') as f:
    info=tarfile.TarInfo('../escape');info.size=1;f.addfile(info,io.BytesIO(b'x'))
   with self.assertRaises(ValueError):extract(archive,t/'out')
 def test_cobs_native_temporary_file_is_counted_as_scratch(self):
  from benchkit.measure import disk
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'index.cobs_compact.tmp').write_bytes(b'abc')
   d=disk(root);self.assertEqual(d['index_allocated_bytes'],0);self.assertGreater(d['temp_allocated_bytes'],0)
 def test_prepared_cleanup_preserves_all_preparation_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   work=Path(t);root=work/'data/prepared/refseq/64/simd';root.mkdir(parents=True)
   (root/'COMPLETE.json').write_text('{"count":123}')
   (root/'preparation.log').write_text('extraction evidence')
   (root/'derived.fasta.gz').write_bytes(b'fixture')
   runner.cleanup_prepared(work,'refseq',64)
   self.assertFalse(root.exists());self.assertEqual(load(work/'reports/preparation/refseq/64/simd/COMPLETE.json')['count'],123)
   self.assertTrue((work/'reports/preparation/refseq/64/simd/preparation.log').exists())
 def test_no_machine_specific_paths_in_text_metadata(self):
  for root in ['configs','benchkit','docs','paper']:
   for p in (ROOT/root).rglob('*'):
    if p.suffix in ['.py','.json','.md']:self.assertNotIn('/home/nadine',p.read_text(),str(p))

@unittest.skipUnless(shutil.which('pigz') and Path('/usr/bin/time').exists(),'integration fixtures need GNU time and pigz')
class WorkflowTests(unittest.TestCase):
 def test_all_eight_tools_dense_and_minimizers_with_fake_indexers(self):
  with tempfile.TemporaryDirectory() as t:
   work=Path(t);bins=work/'tools/bin';bins.mkdir(parents=True)
   for tool in [*TOOLS,'minimizer-fasta','kmtricks']:
    p=bins/tool;shutil.copy2(ROOT/'tests/fake_tool.py',p);p.chmod(0o755)
   source=work/'input.fasta.gz'
   with gzip.open(source,'wt') as out:out.write('>g0\n'+'A'*1100+'\n')
   second=work/'second.fasta.gz'
   with gzip.open(second,'wt') as out:out.write('>g1\n'+'G'*1100+'\n')
   rows=[dict(color=i,accession=f'GCF_TEST{i}',bases=1100,path=str(path)) for i,path in enumerate([source,second])]
   queries={}
   for label,base in [('positive','A'),('negative','C')]:
    p=work/(label+'.fasta.gz')
    with gzip.open(p,'wt') as out:out.write('>q0\n'+base*1000+'\n>q1\n'+base*1000+'\n')
    queries[label]=dict(path=str(p),sha256='fixture')
   metadata=dict(count=2,length=1000,source_metadata=[dict(query_id='q0',source_color=0),dict(query_id='q1',source_color=0)],workloads=queries)
   real_sha=runner.sha
   def case_sha(p):return 'fixture-accessions' if 'data/accessions/' in str(p) else real_sha(p)
   with patch.object(data,'samples',return_value=rows),patch.object(data,'workloads',return_value=metadata),patch.object(runner,'sha',side_effect=case_sha):
    for mode in ['dense','minimizers']:
     for tool in TOOLS:
      with self.subTest(mode=mode,tool=tool):
       result=runner.run_case(work,'refseq',2,8,mode,tool,False,48,0)
       self.assertEqual(result['status'],'complete',result.get('reason'))
       self.assertEqual(result['queries']['positive']['validation']['source_misses'],0)
       self.assertFalse(list((work/f'results/refseq/8bit/{mode}/n2/{tool}').glob('index*')))
       self.assertTrue(load(work/f'results/refseq/8bit/{mode}/n2/{tool}/cleanup.json')['removed'])
       with patch.object(runner,'measure',side_effect=AssertionError('Completed case must not rerun')):self.assertEqual(runner.run_case(work,'refseq',2,8,mode,tool,False,48,0)['status'],'complete')
    old=runner.run_case(work,'refseq',2,16,'dense','fulgor',False,48,0);self.assertTrue(old['reused_exact_measurement'])
   self.assertTrue(source.exists())
 def test_failed_native_stage_preserved_and_not_retried(self):
  with tempfile.TemporaryDirectory() as t:
   work=Path(t);case=work/'results/refseq/8bit/dense/n64/zindex';case.mkdir(parents=True);(case/'FAILED.json').write_text('{"reason":"fixture"}')
   with patch.object(runner,'measure',side_effect=AssertionError('must not rerun')):
    r=runner.run_case(work,'refseq',64,8,'dense','zindex',False,48,0);self.assertEqual(r['status'],'failed_retained');self.assertTrue((case/'FAILED.json').exists())


class DownloadTests(unittest.TestCase):
 def test_multiple_versioned_components_stay_compressed_and_resume(self):
  import hashlib
  with tempfile.TemporaryDirectory() as t:
   work=Path(t);payloads={'https://archive.example/part1':b'>a\nAAA\n','https://archive.example/part2':gzip.compress(b'>b\nCCC\n')}
   row=dict(accession='GCF_TEST.1',urls=json.dumps(list(payloads)),bases=6)
   with patch.object(data,'manifest',return_value=[row]),patch('urllib.request.urlopen',side_effect=lambda req,timeout:io.BytesIO(payloads[req.full_url])):
    data.download(work,'refseq',1)
    output=data.genome_path(work,'refseq',row['accession']);self.assertEqual(output.read_bytes()[:2],b'\x1f\x8b')
    from benchkit.common import fasta
    self.assertEqual(list(fasta(output)),[('a','AAA'),('b','CCC')])
   with patch.object(data,'manifest',return_value=[row]),patch('urllib.request.urlopen',side_effect=AssertionError('Completed download must be reused')):data.download(work,'refseq',1)

if __name__=='__main__':unittest.main()
