from __future__ import annotations

import json
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "鲁东大学学术学位论文_Zotero活动引用版.docx"
TEMPLATE = ROOT / "鲁东大学学术学位论文_Zotero联动模板.docx"
VALID_OBJECT_KEY = re.compile(r"^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$")
FAKE_URI = re.compile(r"zotero\.org/users/[^\"\\]+/items/([^\"\\]+)")


def _document_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _archive_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def _instr_texts(xml: str) -> list[str]:
    return re.findall(r"<w:instrText[^>]*>(.*?)</w:instrText>", xml, flags=re.DOTALL)


def _json_payloads(xml: str) -> list[dict]:
    payloads = []
    for text in _instr_texts(xml):
        if "CSL_CITATION" not in text:
            continue
        start = text.find("{")
        payloads.append(json.loads(text[start:]))
    return payloads


class ZoteroWordFieldTests(unittest.TestCase):
    def test_active_document_can_refresh(self) -> None:
        self._assert_refreshable(ACTIVE, min_citations=5)

    def test_template_document_can_refresh(self) -> None:
        self._assert_refreshable(TEMPLATE, min_citations=6)

    def _assert_refreshable(self, path: Path, min_citations: int) -> None:
        self.assertTrue(path.is_file(), path)
        xml = _document_xml(path)
        names = _archive_names(path)

        self.assertNotIn("fldSimple", xml)
        self.assertIn("ZOTERO_PREF", xml)
        self.assertIn("ZOTERO_BIBL", xml)
        self.assertIn("customXml/item2.xml", names)
        self.assertGreaterEqual(xml.count("ZOTERO_ITEM"), min_citations)
        self.assertNotIn("ITEM-1", xml)

        for match in FAKE_URI.finditer(xml):
            self.assertRegex(match.group(1), VALID_OBJECT_KEY, match.group(0))

        payloads = _json_payloads(xml)
        self.assertGreaterEqual(len(payloads), min_citations)
        citation_ids = [item["citationID"] for item in payloads]
        self.assertEqual(len(citation_ids), len(set(citation_ids)))

        for payload in payloads:
            self.assertNotIn("style", payload["properties"])
            self.assertEqual(payload["properties"]["noteIndex"], 0)
            for cited in payload["citationItems"]:
                self.assertNotIn("uris", cited)
                self.assertTrue(cited["itemData"]["title"])
                self.assertEqual(cited["id"], cited["itemData"]["id"])

        self.assertEqual(xml.count("[1] 陈登原"), 1)
        self.assertEqual(xml.count("[5] 冯西桥"), 1)
        bibl_start = xml.index("ZOTERO_BIBL")
        bibl_end = xml.index("附录A", bibl_start)
        bibl_xml = xml[bibl_start:bibl_end]
        self.assertGreaterEqual(bibl_xml.count("<w:p>"), 4)
        self.assertNotIn("\n袁训来", bibl_xml)


if __name__ == "__main__":
    unittest.main()
