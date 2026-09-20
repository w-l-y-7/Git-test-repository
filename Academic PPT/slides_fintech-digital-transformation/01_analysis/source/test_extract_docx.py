# -*- coding: utf-8 -*-
"""extract_docx.py 的单元测试。

这个脚本一被导入就会读 sys.argv 里的输入/输出路径并跑完整个流程，
所以测试时先造一个"最小的 docx"（本质是个 zip），再按脚本的方式加载它。
全过程只用标准库，不碰真实文档。
"""
import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
SRC = Path(__file__).with_name("extract_docx.py")


def make_docx(path, body_xml):
    """把一段 body 内容打包成 docx（zip 里放 word/document.xml）。"""
    xml = (
        f'<w:document xmlns:w="{W}" xmlns:m="{M}">'
        f"<w:body>{body_xml}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)


def load_module(docx_path, out_path, name):
    """按脚本的用法（命令行参数）加载一次模块。"""
    old = sys.argv
    sys.argv = ["extract_docx.py", str(docx_path), str(out_path)]
    try:
        spec = importlib.util.spec_from_file_location(name, SRC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.argv = old


def P(inner):
    return ET.fromstring(f'<w:p xmlns:w="{W}" xmlns:m="{M}">{inner}</w:p>')


class TestParaText(unittest.TestCase):
    """段落的取字逻辑。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        make_docx(d / "a.docx", "<w:p><w:r><w:t>x</w:t></w:r></w:p>")
        cls.mod = load_module(d / "a.docx", d / "a.txt", "extract_docx_fn")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_joins_runs(self):
        p = P('<w:r><w:t>hello</w:t></w:r><w:r><w:t> world</w:t></w:r>')
        self.assertEqual(self.mod.para_text(p), "hello world")

    def test_formula_placeholder(self):
        self.assertEqual(self.mod.para_text(P("<m:oMath/>")), "[公式]")

    def test_break_becomes_newline(self):
        p = P('<w:r><w:t>a</w:t></w:r><w:br/><w:r><w:t>b</w:t></w:r>')
        self.assertEqual(self.mod.para_text(p), "a\nb")

    def test_empty_paragraph(self):
        # 边界：空段落
        self.assertEqual(self.mod.para_text(P("")), "")

    def test_text_is_stripped(self):
        p = P('<w:r><w:t>  padded  </w:t></w:r>')
        self.assertEqual(self.mod.para_text(p), "padded")


class TestParaStyle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        make_docx(d / "a.docx", "<w:p><w:r><w:t>x</w:t></w:r></w:p>")
        cls.mod = load_module(d / "a.docx", d / "a.txt", "extract_docx_style")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reads_pstyle(self):
        p = P('<w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>x</w:t></w:r>')
        self.assertEqual(self.mod.para_style(p), "Heading2")

    def test_no_pPr(self):
        # 边界：没有段落属性
        self.assertEqual(self.mod.para_style(P('<w:r><w:t>x</w:t></w:r>')), "")

    def test_pPr_without_pStyle(self):
        p = P('<w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:t>x</w:t></w:r>')
        self.assertEqual(self.mod.para_style(p), "")


class TestFullPipeline(unittest.TestCase):
    """整条流程：docx → 纯文本。"""

    def _run(self, body_xml):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        docx = d / "in.docx"
        out = d / "out.txt"
        make_docx(docx, body_xml)
        load_module(docx, out, f"extract_docx_pipe_{id(body_xml)}")
        return out.read_text(encoding="utf-8").split("\n")

    def test_headings_body_formula_table(self):
        body = (
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>标题</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>第一段</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>含公式</w:t></w:r><m:oMath/></w:p>'
            '<w:p/>'
            '<w:tbl>'
            '<w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc></w:tr>'
            '<w:tr><w:tc><w:p><w:r><w:t>C</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>D</w:t></w:r></w:p></w:tc></w:tr>'
            "</w:tbl>"
        )
        lines = self._run(body)
        self.assertIn("# 标题", lines)
        self.assertIn("第一段", lines)
        self.assertIn("含公式 [公式]", lines)
        self.assertIn("【表格】", lines)
        self.assertIn("| A | B |", lines)
        self.assertIn("| C | D |", lines)

    def test_heading_level_number(self):
        body = '<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>小标题</w:t></w:r></w:p>'
        self.assertIn("### 小标题", self._run(body))

    def test_heading_without_number_defaults_to_one(self):
        # 边界：样式名叫 Heading 但没带数字 → 按一级标题
        body = '<w:p><w:pPr><w:pStyle w:val="Heading"/></w:pPr><w:r><w:t>无编号标题</w:t></w:r></w:p>'
        self.assertIn("# 无编号标题", self._run(body))

    def test_title_style(self):
        body = '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>大标题</w:t></w:r></w:p>'
        self.assertIn("# 大标题", self._run(body))

    def test_empty_paragraph_skipped(self):
        body = '<w:p/><w:p><w:r><w:t>只有这段</w:t></w:r></w:p>'
        lines = [l for l in self._run(body) if l]
        self.assertEqual(lines, ["只有这段"])

    def test_table_row_count(self):
        body = (
            "<w:tbl>"
            '<w:tr><w:tc><w:p><w:r><w:t>x</w:t></w:r></w:p></w:tc></w:tr>'
            '<w:tr><w:tc><w:p><w:r><w:t>y</w:t></w:r></w:p></w:tc></w:tr>'
            "</w:tbl>"
        )
        lines = self._run(body)
        self.assertEqual(lines.count("| x |"), 1)
        self.assertEqual(lines.count("| y |"), 1)


class TestBadInput(unittest.TestCase):
    """异常情况。"""

    def test_zip_without_document_xml_raises(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        bad = d / "bad.docx"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("other.txt", "not a real docx")
        with self.assertRaises(KeyError):
            load_module(bad, d / "out.txt", "extract_docx_bad")


if __name__ == "__main__":
    unittest.main()
