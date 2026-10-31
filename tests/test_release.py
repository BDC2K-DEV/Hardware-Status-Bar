import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

metrics=module('metrics',ROOT/'extension/metrics.py')
installer=module('installer',ROOT/'scripts/install.py')

class ReleaseTests(unittest.TestCase):
    def test_compatibility(self):
        self.assertTrue(installer.supported('GNOME Shell 50.1'))
        for version in ['GNOME Shell 49.5','GNOME Shell 51.0','Plasma 6.5']:
            self.assertFalse(installer.supported(version))

    def test_archive_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.zip'
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('../outside','bad')
            with self.assertRaises(ValueError):installer.validate_archive(path)

    def test_package(self):
        subprocess.run(['python3',str(ROOT/'scripts/build.py')],check=True,capture_output=True)
        installer.validate_archive(ROOT/'dist/hardware-status-bar.extension.zip')
        with zipfile.ZipFile(ROOT/'dist/hardware-status-bar-linux.zip') as archive:
            self.assertEqual(set(archive.namelist()),{'install.sh','install.py','hardware-status-bar.extension.zip','README.md','LICENSE','CONTRIBUTING.md','SECURITY.md','CHANGELOG.md','docs/compatibility.md','docs/images/bar.png','docs/images/menu.png'})

    def test_descendants(self):
        ps={10:{'ppid':1},11:{'ppid':10},12:{'ppid':11},20:{'ppid':1}}
        self.assertEqual(metrics.descendants([10],ps),{10,11,12})

    def test_disposable_process_kill_and_stale_identity(self):
        proc=subprocess.Popen(['sleep','60'])
        try:
            rows=metrics.apps([{'id':'test','pids':[proc.pid]}])
            self.assertEqual(rows[0]['count'],1)
            self.assertEqual(metrics.kill([[proc.pid,'not-its-start-time']])['killed'],0)
            self.assertIsNone(proc.poll())
            self.assertEqual(metrics.kill(rows[0]['tokens'])['killed'],1)
            proc.wait(timeout=5)
            self.assertEqual(proc.returncode,-9)
            self.assertEqual(metrics.kill(rows[0]['tokens'])['killed'],0)
        finally:
            if proc.poll() is None:proc.kill();proc.wait()


class InstallLifecycleTests(unittest.TestCase):
    def test_install_check_duplicate_and_remove_in_isolated_home(self):
        import os
        import shutil
        import sys
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copy(ROOT/'dist/hardware-status-bar.extension.zip',root/'hardware-status-bar.extension.zip')
            enabled=[]
            def fake_run(*args):
                if args==('gnome-shell','--version'):return 'GNOME Shell 50.1'
                if args[:2]==('gsettings','get'):return repr(enabled)
                if args[:2]==('gsettings','set'):
                    enabled[:]=__import__('ast').literal_eval(args[-1]);return ''
                raise AssertionError(args)
            with patch.object(installer,'__file__',str(root/'install.py')),patch.dict(os.environ,{'XDG_DATA_HOME':str(root/'data')}),patch.object(installer,'run',side_effect=fake_run),patch.object(installer.shutil,'which',return_value='/usr/bin/fake'),patch.object(installer.os,'geteuid',return_value=1000),patch.object(installer.subprocess,'run'):
                with patch.object(sys,'argv',['install.py','--check']):installer.main()
                self.assertFalse((root/'data').exists())
                with patch.object(sys,'argv',['install.py']):installer.main()
                target=root/'data/gnome-shell/extensions'/installer.UUID
                self.assertEqual({p.name for p in target.iterdir()},installer.FILES)
                self.assertIn(installer.UUID,enabled)
                with patch.object(sys,'argv',['install.py']):
                    with self.assertRaises(RuntimeError):installer.main()
                with patch.object(sys,'argv',['install.py','--uninstall']):installer.main()
                self.assertFalse(target.exists());self.assertNotIn(installer.UUID,enabled)

if __name__=='__main__':unittest.main()
