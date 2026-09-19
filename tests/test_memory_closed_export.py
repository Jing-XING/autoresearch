import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile,ZIP_DEFLATED
from scripts.archive_memory_test40_v1 import BATCH,WORKERS,export
from scripts.unpack_memory_test40_v1 import unpack


class ClosedExportTest(unittest.TestCase):
    def test_closed_byte_roundtrip_missing_simulation_and_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/'source';root.mkdir()
            workers=[]
            for t,c,m,s in sorted(WORKERS):
                workers.append(dict(tie_order=t,condition=c,model=m,shard=s,exit_code=0))
                folder=root/t/c/m/f'shard-{s}';folder.mkdir(parents=True)
                for name in ['manifest.json','config.json','summary.json']:
                    (folder/name).write_bytes(b'{"fixture":true}\r\n')
                for i in range(20):
                    for suffix in ('-status','-model-audit',''):
                        if i==0 and suffix=='':continue # Export does not invent missing simulations.
                        (folder/f'case-{i:03}{suffix}.json').write_bytes(b'{"synthetic":true}\n')
            grid=dict(batch=BATCH,status='running',registered_episodes=560,workers=workers)
            gp=root/'grid_manifest.json';gp.write_text(json.dumps(grid))
            with self.assertRaisesRegex(ValueError,'unfinished'):export(root,base/'early.zip')
            self.assertFalse((base/'early.zip').exists())
            grid['status']='complete';gp.write_text(json.dumps(grid))
            receipt=export(root,base/'full.zip');self.assertEqual(receipt['simulation_files'],532)
            result=unpack(base/'full.zip',receipt['archive_sha256'],base/'restored')
            self.assertFalse(result['scientific_analysis_executed'])
            for p in root.rglob('*.json'):
                self.assertEqual(p.read_bytes(),(Path(result['root'])/p.relative_to(root)).read_bytes())
            with self.assertRaises(FileExistsError):unpack(base/'full.zip',receipt['archive_sha256'],base/'restored')
            with self.assertRaisesRegex(ValueError,'archive differs'):unpack(base/'full.zip','0'*64,base/'bad')
            (root/'unregistered.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Extra or missing'):export(root,base/'extra.zip')
            # Corruption with a freshly computed outer hash must still fail per-member verification.
            with ZipFile(base/'full.zip') as z, ZipFile(base/'forged.zip','x',ZIP_DEFLATED) as out:
                target=next(n for n in z.namelist() if n.endswith('/case-001-status.json'))
                for n in z.namelist():out.writestr(n,b'{}' if n==target else z.read(n))
            forged_sha=hashlib.sha256((base/'forged.zip').read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'Size differs|hash differs'):
                unpack(base/'forged.zip',forged_sha,base/'forged-out')
            self.assertFalse((base/'forged-out').exists())


if __name__=='__main__':unittest.main()
