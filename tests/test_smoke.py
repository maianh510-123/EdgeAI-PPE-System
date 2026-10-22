import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from edgeai_ppe.constants import PPE_CLASSES, CLASS_STATUS
from edgeai_ppe.config import AppConfig, load_config
from edgeai_ppe.detection.result import Detection
from edgeai_ppe.detection.detector import DemoDetector
from edgeai_ppe.compliance.evaluator import evaluate_status
from edgeai_ppe.communication.payload import create_event, PPEEvent
from edgeai_ppe.communication.interface import ConsoleClient
from edgeai_ppe.pipeline.ppe_pipeline import PPEPipeline

class SmokeTests(unittest.TestCase):
    def test_all_classes_and_payload_roundtrip(self):
        expected = dict(zip(PPE_CLASSES, ("detected", "compliant", "compliant", "violation", "violation")))
        self.assertEqual(dict(CLASS_STATUS), expected)
        for label in PPE_CLASSES:
            event = create_event(Detection(label, 0.8), "edge", "cam", is_demo=True)
            decoded = json.loads(event.to_json())
            self.assertEqual(decoded["status"], expected[label])
            self.assertEqual(PPEEvent(**decoded), event)
        self.assertNotEqual(create_event(Detection("person", 1), "e", "c", is_demo=True).message_id,
                            create_event(Detection("person", 1), "e", "c", is_demo=True).message_id)

    def test_invalid_detection_and_status(self):
        for label, score in (("unknown", .5), ("person", -1), ("person", float("nan")), ("person", True)):
            with self.assertRaises(ValueError):
                Detection(label, score)
        with self.assertRaises(ValueError):
            evaluate_status("unknown")
        event = create_event(Detection("no_helmet", .9), "e", "c", is_demo=True).to_dict()
        event["status"] = "compliant"
        with self.assertRaises(ValueError):
            PPEEvent(**event)

    def test_demo_and_threshold(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            summary = PPEPipeline(AppConfig(), DemoDetector(), ConsoleClient(), is_demo=True).run_once()
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual((summary.accepted, summary.sent, summary.failed), (2, 2, 0))
        self.assertTrue(all(event["is_demo"] for event in events))
        with contextlib.redirect_stdout(io.StringIO()):
            summary = PPEPipeline(AppConfig(confidence_threshold=.95), DemoDetector(), ConsoleClient(), is_demo=True).run_once()
        self.assertEqual(summary.sent, 1)

    def test_send_failure_continues(self):
        class FailingClient:
            calls = 0
            def send(self, event):
                self.calls += 1
                if self.calls == 1:
                    raise OSError("test failure")
        client = FailingClient()
        with self.assertLogs(level="ERROR"):
            result = PPEPipeline(AppConfig(), DemoDetector(), client, is_demo=True).run_once()
        self.assertEqual((result.sent, result.failed, client.calls), (1, 1, 2))

    def test_config_validation_and_environment(self):
        with patch.dict(os.environ, {"EDGEAI_DEVICE_ID": "test-edge", "EDGEAI_CAMERA_ID": "test-cam"}):
            config = load_config(ROOT / "configs/default.yaml")
            self.assertEqual((config.device_id, config.camera_id), ("test-edge", "test-cam"))
        with self.assertRaises(ValueError):
            AppConfig(transport="mqtt")
        with self.assertRaises(ValueError):
            AppConfig(confidence_threshold=2)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "config.yaml"
            for text in ('[]', '{"unknown": 1}', 'bad yaml'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_cli_from_other_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--config",
                                     str(ROOT / "configs/default.yaml")], cwd=temp,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([json.loads(line) for line in result.stdout.splitlines()]), 2)
        failed = subprocess.run([sys.executable, str(ROOT / "main.py"), "--config",
                                 str(ROOT / "missing-config.yaml")], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)

if __name__ == "__main__":
    unittest.main()
