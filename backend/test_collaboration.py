from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from host import Host
from security import (
    generate_session_code,
    safe_resolve,
    session_registry,
    validate_ip,
    validate_session_code,
)


class TestPeerCodeSecurity(unittest.TestCase):
    def test_random_session_code(self):
        code = generate_session_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(validate_session_code(code))
        for char in code:
            self.assertNotIn(char, "O0I1L")

    def test_validate_ip(self):
        self.assertTrue(validate_ip("192.168.1.1"))
        self.assertFalse(validate_ip("999.1.1.1"))
        self.assertFalse(validate_ip("not-an-ip"))

    def test_session_registry(self):
        info = session_registry.create("192.168.1.10", 45123)
        self.assertEqual(len(info.code), 6)
        self.assertEqual(len(info.key), 64)
        self.assertTrue(session_registry.validate_key(info.code, info.key))
        self.assertFalse(session_registry.validate_key(info.code, "wrong"))
        session_registry.remove(info.session_id)

    def test_path_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            real_tmp = os.path.realpath(tmpdir)

            safe_path = safe_resolve(real_tmp, "src/main.py")
            self.assertEqual(safe_path, os.path.realpath(os.path.join(real_tmp, "src/main.py")))

            with self.assertRaises(PermissionError):
                safe_resolve(real_tmp, "../outside.py")

            with self.assertRaises(PermissionError):
                safe_resolve(real_tmp, "C:/Windows/System32")


class TestPeerCodeCollaboration(unittest.TestCase):
    def setUp(self):
        self.project_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.project_dir)

    def test_host_saving_conflict(self):
        host = Host(self.project_dir, "TestHost")

        rel_path = "test.py"
        host.create_node(rel_path, is_dir=False)

        res = host.read_file(rel_path)
        self.assertEqual(res["version"], 1)
        self.assertEqual(res["content"], "")

        save_res = host.save_file(rel_path, "print('hello')", 1)
        self.assertEqual(save_res["status"], "ok")
        self.assertEqual(save_res["version"], 2)

        conflict_res = host.save_file(rel_path, "print('conflict')", 1)
        self.assertEqual(conflict_res["status"], "conflict")
        self.assertEqual(conflict_res["server_version"], 2)

        save_res2 = host.save_file(rel_path, "print('resolved')", 2)
        self.assertEqual(save_res2["status"], "ok")
        self.assertEqual(save_res2["version"], 3)

    def test_incremental_text_edit(self):
        host = Host(self.project_dir, "TestHost")
        rel_path = "edit.py"
        host.create_node(rel_path, is_dir=False)
        host.read_file(rel_path)

        host.apply_text_edit(rel_path, {"op": "insert", "index": 0, "text": "hello"})
        self.assertEqual(host.opened_files[rel_path]["content"], "hello")

        host.apply_text_edit(rel_path, {"op": "insert", "index": 5, "text": " world"})
        self.assertEqual(host.opened_files[rel_path]["content"], "hello world")


if __name__ == "__main__":
    unittest.main()
