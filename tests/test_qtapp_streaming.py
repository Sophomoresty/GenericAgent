import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("GA_LANG", "zh")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

import frontends.qtapp as qtapp


class TestQtAppStreamingRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_streaming_row_skips_markdown_reparse_until_finished(self):
        markdown_calls = []
        real_md_to_html = qtapp._md_to_html

        def counted_md_to_html(text):
            markdown_calls.append(text)
            return real_md_to_html(text)

        with patch.object(qtapp, "_md_to_html", side_effect=counted_md_to_html):
            row = qtapp._MsgRow("▌", "assistant")
            self.assertEqual(len(markdown_calls), 1)

            row.set_finished(False)
            row.set_text("**hello**\n\n```python\nprint(1)\n```")

            self.assertEqual(len(markdown_calls), 1)
            self.assertIn("**hello**", row._label.toPlainText())
            self.assertIn("print(1)", row._label.toPlainText())

    def test_finished_row_renders_markdown_after_streaming(self):
        markdown_calls = []
        real_md_to_html = qtapp._md_to_html

        def counted_md_to_html(text):
            markdown_calls.append(text)
            return real_md_to_html(text)

        with patch.object(qtapp, "_md_to_html", side_effect=counted_md_to_html):
            row = qtapp._MsgRow("▌", "assistant")
            row.set_finished(False)
            row.set_text("**done**")
            self.assertEqual(len(markdown_calls), 1)

            row.set_finished(True)

            self.assertGreaterEqual(len(markdown_calls), 2)
            self.assertEqual(row._label.toPlainText().strip(), "done")


if __name__ == "__main__":
    unittest.main()
