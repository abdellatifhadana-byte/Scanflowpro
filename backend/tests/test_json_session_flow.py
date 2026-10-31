import asyncio
import tempfile
import unittest
from pathlib import Path

from managers.json_session_manager import JSONSessionManager
from managers.smart_session_manager import SmartSessionManager


class JSONSessionFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_keyword_create_returns_string_and_supports_upload_path(self):
        with tempfile.TemporaryDirectory() as temp:
            json_manager = JSONSessionManager(Path(temp))
            smart = SmartSessionManager.__new__(SmartSessionManager)
            smart.manager = json_manager
            smart.storage_type = "json"

            session_id = await smart.create_session(
                batch_name="Acceptance batch",
                settings={"document_type": "printed"},
            )
            self.assertIsInstance(session_id, str)
            self.assertTrue(session_id)

            session = await smart.get_session(session_id)
            self.assertEqual(session["batch_name"], "Acceptance batch")

            upload_dir = smart.get_session_path(session_id, "uploads")
            self.assertTrue(upload_dir.is_dir())
            uploaded = upload_dir / "sample.pdf"
            uploaded.write_bytes(b"%PDF-test")
            self.assertTrue(uploaded.exists())

            self.assertTrue(await smart.update_session(session_id, {
                "files": [{"filename": "sample.pdf", "path": str(uploaded)}],
                "status": "files_uploaded",
            }))
            saved = await smart.get_session(session_id)
            self.assertEqual(saved["status"], "files_uploaded")
            self.assertEqual(saved["files"][0]["filename"], "sample.pdf")

            self.assertTrue(await smart.update_session(session_id, {
                "status": "completed",
                "pages": [{"page_id": "p1"}],
                "results": [{"code": "A123"}],
            }))
            results = await smart.get_session(session_id)
            self.assertEqual(results["status"], "completed")
            self.assertEqual(results["results"][0]["code"], "A123")


if __name__ == "__main__":
    unittest.main()
