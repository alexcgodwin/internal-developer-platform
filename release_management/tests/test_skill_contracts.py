import re
import unittest
from pathlib import Path


class SkillContracts(unittest.TestCase):
    def test_skills_have_required_metadata_and_referenced_command(self):
        repo = Path(__file__).resolve().parents[2]
        for name in ("release-readiness", "release-inventory", "release-incident-evidence"):
            path = repo / ".claude" / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertTrue(text.startswith("---\nname: " + name + "\n"))
                self.assertRegex(text, r"(?m)^description: .{20,}$")
                self.assertIn("python -m release_management", text)
                self.assertIn("---\n", text[5:])


if __name__ == "__main__":
    unittest.main()
