"""Pinned model integrity: bad caches cannot be blessed by a new manifest."""
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts import download_models


class ModelSetupTests(unittest.TestCase):
    def fixture(self,root,content=b"official pinned task model"):
        name="fixture.task"
        model_dir=root/"models"
        model_dir.mkdir()
        expected={"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()}
        stack=ExitStack()
        stack.enter_context(patch.object(download_models,"ROOT",root))
        stack.enter_context(patch.object(download_models,"MODELS",{name:"https://example.invalid/model"}))
        stack.enter_context(patch.object(download_models,"EXPECTED",{name:expected}))
        self.addCleanup(stack.close)
        return model_dir/name,expected

    def test_valid_cache_does_not_download_and_manifest_uses_pinned_values(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            path,expected=self.fixture(root)
            path.write_bytes(b"official pinned task model")
            path.with_suffix(".part").write_bytes(b"stale interrupted download")
            with patch.object(download_models,"urlopen") as fetch:
                download_models.download()
            fetch.assert_not_called()
            manifest=json.loads((root/"models/manifest.json").read_text())
            self.assertEqual(manifest[path.name]["sha256"],expected["sha256"])
            self.assertEqual(manifest[path.name]["bytes"],expected["bytes"])
            self.assertFalse(list((root/"models").glob("*.part")))

    def test_corrupt_cache_is_repaired_only_after_verified_download(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            path,expected=self.fixture(root)
            path.write_bytes(b"broken cached task")
            with patch.object(download_models,"urlopen",return_value=io.BytesIO(b"official pinned task model")) as fetch:
                download_models.download()
            fetch.assert_called_once()
            self.assertTrue(download_models.verified(path,expected))
            self.assertFalse(list((root/"models").glob("*.part")))

    def test_wrong_download_preserves_cache_and_existing_manifest(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            path,expected=self.fixture(root)
            corrupt=b"old corrupt cached file"
            path.write_bytes(corrupt)
            old_manifest=b'{"previous": "manifest must not bless a failed download"}'
            (root/"models/manifest.json").write_bytes(old_manifest)
            # Match the expected byte count but fail the SHA256 check.
            with patch.object(download_models,"urlopen",return_value=io.BytesIO(b"x"*expected["bytes"])):
                with self.assertRaisesRegex(RuntimeError,"Checksum verification failed"):
                    download_models.download()
            self.assertEqual(path.read_bytes(),corrupt)
            self.assertEqual((root/"models/manifest.json").read_bytes(),old_manifest)
            self.assertFalse(list((root/"models").glob("*.part")))


if __name__=="__main__":
    unittest.main()
