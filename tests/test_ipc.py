import os
import sys
import time
import socket
import json
import unittest

AEGIS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AEGIS_ROOT not in sys.path:
    sys.path.insert(0, AEGIS_ROOT)

from aegis.ipc import IPCServer, IPCClient, IPCError, SOCKET_PATH
from aegis.config import load_config

class TestAegisIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = IPCServer()
        cls.server.start()
        time.sleep(0.2)
        cls.client = IPCClient()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        time.sleep(0.2)

    def test_01_socket_exists_and_permissions(self):
        self.assertTrue(os.path.exists(SOCKET_PATH), f"Socket path {SOCKET_PATH} should exist")
        mode = os.stat(SOCKET_PATH).st_mode & 0o777
        self.assertEqual(mode, 0o600, f"Socket permissions should be 0600, got {oct(mode)}")

    def test_02_get_status(self):
        status = self.client.get_status()
        self.assertIn("health", status)
        self.assertIn("state", status)
        self.assertIn("cpu", status)
        self.assertIn("memory", status)
        self.assertIn("used", status["memory"])
        self.assertIn("total", status["memory"])
        self.assertIn("percent", status["memory"])

    def test_03_get_processes(self):
        procs = self.client.get_processes()
        self.assertIsInstance(procs, list)
        if len(procs) > 0:
            p = procs[0]
            self.assertIn("pid", p)
            self.assertIn("name", p)
            self.assertIn("cpu", p)
            self.assertIn("rss", p)
            self.assertIn("score", p)
            self.assertIn("protected", p)

    def test_04_get_events(self):
        events = self.client.get_events(limit=5)
        self.assertIsInstance(events, list)

    def test_05_get_config(self):
        cfg = self.client.get_config()
        self.assertIn("protect", cfg)
        self.assertIn("memory", cfg)
        self.assertIn("soft_pct", cfg["memory"])

    def test_06_protect_unprotect_process(self):
        res = self.client.protect_process("test_app_123")
        self.assertTrue(res.get("protected"))
        cfg = self.client.get_config()
        self.assertIn("test_app_123", cfg["protect"])

        res2 = self.client.unprotect_process("test_app_123")
        self.assertTrue(res2.get("unprotected"))
        cfg2 = self.client.get_config()
        self.assertNotIn("test_app_123", cfg2["protect"])

    def test_07_mark_expendable(self):
        res = self.client.mark_expendable("test_steam_game")
        self.assertTrue(res.get("expendable"))
        cfg = self.client.get_config()
        self.assertIn("test_steam_game", cfg["expendable"])

        res2 = self.client.unmark_expendable("test_steam_game")
        self.assertTrue(res2.get("unmarked_expendable"))
        cfg2 = self.client.get_config()
        self.assertNotIn("test_steam_game", cfg2["expendable"])

    def test_07b_oom_protect_process(self):
        res = self.client.oom_protect_process(name="test_app_123")
        self.assertTrue(res.get("oom_protected"))
        cfg = self.client.get_config()
        self.assertIn("test_app_123", cfg["protect"])

    def test_07c_protection_conflicts_and_get_protection(self):
        # Test get_protection RPC
        prot = self.client.get_protection()
        self.assertIn("protected", prot)
        self.assertIn("expendable", prot)

        # Protect app
        self.client.protect_process("conflict_app")

        # Marking protected app as expendable without force should raise PROTECTION_CONFLICT
        with self.assertRaises(IPCError) as ctx:
            self.client.mark_expendable("conflict_app", force=False)
        self.assertEqual(ctx.exception.code, "PROTECTION_CONFLICT")

        # Marking with force=True should succeed and remove from protected list
        res = self.client.mark_expendable("conflict_app", force=True)
        self.assertTrue(res.get("expendable"))

        prot2 = self.client.get_protection()
        self.assertIn("conflict_app", prot2["expendable"])
        self.assertNotIn("conflict_app", prot2["protected"])

        # Clean up
        self.client.unmark_expendable("conflict_app")

    def test_08_update_config(self):
        res = self.client.update_config({
            "memory": {"soft_pct": 88.0, "hard_pct": 94.0, "max_pct": 98.0},
            "temperature": {"warning": 80.0, "critical": 92.0, "action": "kill"},
            "kill": {"weights": {"rss": 0.5, "cpu": 0.4, "runtime": 0.1}}
        })
        self.assertTrue(res.get("updated"))
        cfg = self.client.get_config()
        self.assertEqual(cfg["memory"]["soft_pct"], 88.0)
        self.assertEqual(cfg["memory"]["hard_pct"], 94.0)
        self.assertEqual(cfg["temperature"]["warning"], 80.0)
        self.assertEqual(cfg["kill"]["weights"]["rss"], 0.5)

    def test_08b_update_config_invalid_memory(self):
        # soft >= hard should be rejected
        with self.assertRaises(IPCError) as ctx:
            self.client.update_config({"memory": {"soft_pct": 95.0, "hard_pct": 90.0}})
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

        # hard >= max should be rejected
        with self.assertRaises(IPCError) as ctx:
            self.client.update_config({"memory": {"soft_pct": 80.0, "hard_pct": 98.0, "max_pct": 95.0}})
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

        # out of bounds > 100 should be rejected
        with self.assertRaises(IPCError) as ctx:
            self.client.update_config({"memory": {"soft_pct": 105.0}})
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

    def test_08c_update_config_invalid_temperature(self):
        # warning >= critical should be rejected
        with self.assertRaises(IPCError) as ctx:
            self.client.update_config({"temperature": {"warning": 95.0, "critical": 90.0}})
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

    def test_08d_update_config_invalid_weights(self):
        # weights sum to 1.3 != 1.0 should be rejected
        with self.assertRaises(IPCError) as ctx:
            self.client.update_config({"kill": {"weights": {"rss": 0.7, "cpu": 0.4, "runtime": 0.2}}})
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

    def test_08e_config_change_event(self):
        self.client.update_config({"cpu": {"alert_pct": 85.0}})
        events = self.client.get_events(limit=10, source="config")
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0]["source"], "config")

    def test_08f_validate_config_dict_unit(self):
        from aegis.config import validate_config_dict, get_default_config, save_config, CONFIG_PATH
        # Valid dict should not raise
        validate_config_dict({"memory": {"soft_pct": 80.0, "hard_pct": 90.0, "max_pct": 95.0}})
        
        # Default config
        def_cfg = get_default_config()
        self.assertEqual(def_cfg.memory.soft_pct, 90.0)

        # Save config atomic check
        def_cfg.memory.soft_pct = 85.0
        save_config(def_cfg)
        self.assertTrue(os.path.exists(CONFIG_PATH))

    def test_09_invalid_requests(self):
        # 1. Unknown method
        with self.assertRaises(IPCError) as ctx:
            self.client._call("invalid_unknown_method")
        self.assertEqual(ctx.exception.code, "METHOD_NOT_FOUND")

        # 2. Invalid PID for terminate_process
        with self.assertRaises(IPCError) as ctx:
            self.client.terminate_process(99999999)
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

        # 3. Protected process termination attempt
        with self.assertRaises(IPCError) as ctx:
            self.client.terminate_process(1)  # PID 1 init is protected
        self.assertEqual(ctx.exception.code, "INVALID_PARAMS")

    def test_10_raw_malformed_json(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(SOCKET_PATH)
        sock.sendall(b"{bad_json_string\n")
        rfile = sock.makefile("r", encoding="utf-8")
        resp_str = rfile.readline()
        sock.close()

        resp = json.loads(resp_str)
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "PARSE_ERROR")

if __name__ == "__main__":
    unittest.main()
