"""An offline evidence verifier must reject corrupt and incomplete packages."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

spec=importlib.util.spec_from_file_location('paper3_verifier',Path(__file__).resolve().parents[1]/'scripts/verify_paper3_offline_artifact.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class IntegrityTests(unittest.TestCase):
    def package(self,path,*,member=b'unchanged',missing=False,extra=None,alias=None):
        manifest={'format':'paper3-offline-v1','files':{'data.json':{'bytes':9,'sha256':module.sha(b'unchanged')}},'original_path_aliases':alias or {}}
        with ZipFile(path,'w') as z:
            z.writestr('artifact_manifest.json',json.dumps(manifest))
            if not missing:z.writestr('data.json',member)
            if extra:z.writestr(extra,b'payload')

    def test_changed_record_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,member=b'tampered!')
            with self.assertRaisesRegex(ValueError,'Member mismatch'):module.Artifact(p)

    def test_omitted_record_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,missing=True)
            with self.assertRaisesRegex(ValueError,'Incomplete or extra'):module.Artifact(p)

    def test_parent_path_rejected_without_extraction(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,extra='../outside.txt')
            with self.assertRaisesRegex(ValueError,'Unsafe ZIP'):module.Artifact(p)
            self.assertFalse((Path(d).parent/'outside.txt').exists())

    def test_absolute_path_is_only_a_declared_alias(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,alias={'C:\\original\\data.json':'data.json'})
            a=module.Artifact(p)
            try:
                self.assertEqual(a.read('C:\\original\\data.json'),b'unchanged')
                with self.assertRaisesRegex(ValueError,'Unregistered member'):a.read('C:\\original\\unlisted.json')
            finally:a.zip.close()


if __name__=='__main__':unittest.main()
