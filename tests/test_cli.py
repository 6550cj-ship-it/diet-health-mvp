"""从仓库根直接运行的命令行行为。"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ["plan", "--sex", "female", "--age", "28", "--height-cm", "168",
        "--weight-kg", "65", "--activity", "low_active", "--goal", "maintain"]


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "diet_mvp", *args], cwd=ROOT,
                              text=True, capture_output=True, timeout=30)

    def test_json_demo_is_machine_readable(self):
        result = self.run_cli(*DEMO, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["bmi"]["bmi"], 23.0)
        self.assertEqual(payload["bmi"]["category"], "normal")
        self.assertEqual(len(payload["plan"]["meals"]), 4)
        self.assertTrue(payload["plan"]["constraints_met"])

    def test_chinese_demo(self):
        result = self.run_cli(*DEMO)
        self.assertEqual(result.returncode, 0, result.stderr)
        for term in ("BMI", "正常", "日目标", "早餐", "午餐", "晚餐", "加餐", "合计"):
            self.assertIn(term, result.stdout)

    def test_help_and_bad_input(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertEqual(self.run_cli("plan", "--help").returncode, 0)
        result = self.run_cli(*DEMO, "--age", "12")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("13", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
