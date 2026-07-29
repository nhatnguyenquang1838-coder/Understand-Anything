import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "power_help.py"


class PowerHelpTests(unittest.TestCase):
    def test_json_contract_lists_understand_options(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["id"], "ua")
        self.assertIn("--full", data["options"])
        self.assertIn("--exclude <patterns>", data["options"])

    def test_help_is_available_without_scanning(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("read-only Understand Anything", result.stdout)


if __name__ == "__main__":
    unittest.main()
