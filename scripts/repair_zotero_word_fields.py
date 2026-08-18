#!/usr/bin/env python3
"""Make the thesis Zotero documents refreshable in Word for Windows.

The Windows plugin does NOT read a body-level ZOTERO_PREF field or a
hand-rolled customXml part.  It concatenates Word custom document
properties named ZOTERO_PREF_1, ZOTERO_PREF_2, ... (255 chars each)
from docProps/custom.xml.

Numeric citation item ids such as 1/2/3 also collide with real items
in the user's Zotero library and make Refresh throw
"Zotero 在更新文档时出错".
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.docx_io.zotero_fields import (  # noqa: E402
    build_document_prefs,
    custom_properties_xml as shared_custom_properties_xml,
)

ROOT = Path(__file__).resolve().parents[1]
STYLE_ID = "http://www.zotero.org/styles/china-national-standard-gb-t-7714-2015-numeric"
SCHEMA = "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
SESSION_ID = "LdThsZ01"

LIBRARY_PATH = ROOT / "Ludong_Thesis_Zotero_library.json"
ACTIVE_DOC = ROOT / "鲁东大学学术学位论文_Zotero活动引用版.docx"
TEMPLATE_DOC = ROOT / "鲁东大学学术学位论文_Zotero联动模板.docx"

BIBL_ENTRIES = [
    "[1] 陈登原. 国史旧闻：第1卷[M]. 北京：中华书局，2000：29.",
    "[2] 袁训来，陈哲，肖书海. 蓝田生物群：一个认识多细胞生物起源和早期演化的新窗口[J]. 科学通报，2012，55(34)：3219.",
    "[3] 哈里森，沃尔德伦. 经济数学与金融数学[M]. 谢远涛，译. 北京：中国人民大学出版社，2012：235-236.",
    "[4] 马克思. 政治经济学批判[M]//马克思，恩格斯. 马克思恩格斯全集：第35卷. 北京：人民出版社，2013：302.",
    "[5] 冯西桥. 核反应堆压力管道与压力容器的LBB分析[R]. 北京：清华大学核能技术设计研究院，1997.",
]

CITATION_SPECS = {
    "[1]": ("chen_dengyuan_2000", None, "cCiteA01"),
    "[2]": ("yuan_xunlai_2012", None, "cCiteA02"),
    "[3]": ("harrison_waldron_2012", None, "cCiteA03"),
    "[4]": ("marx_2013", None, "cCiteA04"),
    "[5]": ("feng_xiqiao_1997", None, "cCiteA05"),
    "[1]59-60": ("chen_dengyuan_2000", "59-60", "cCiteA06"),
}


def load_library() -> dict[str, dict]:
    items = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in items}


def document_data_xml() -> str:
    """文档首选项串（与 :mod:`src.docx_io.zotero_fields` 共用同一实现）。"""
    return build_document_prefs(
        style_id=STYLE_ID, locale="zh-CN", session_id=SESSION_ID
    )


def _clean_names(people: list[dict] | None) -> list[dict] | None:
    if not people:
        return people
    cleaned = []
    for person in people:
        entry = {key: value for key, value in person.items() if value not in ("", None)}
        if entry:
            cleaned.append(entry)
    return cleaned or people


def citation_payload(library: dict[str, dict], display: str) -> dict:
    item_id, locator, citation_id = CITATION_SPECS[display]
    item = deepcopy(library[item_id])
    for key in ("author", "translator", "editor", "container-author"):
        if key in item:
            item[key] = _clean_names(item[key])
    # uris MUST be an array. Zotero 9 does citationItem.uris.length when
    # falling back to embedded itemData; a missing key throws and Word
    # shows "Zotero 在更新文档时出错".
    citation_item: dict = {"id": item_id, "uris": [], "itemData": item}
    if locator:
        citation_item["locator"] = locator
        citation_item["label"] = "page"
    return {
        "citationID": citation_id,
        "properties": {
            "formattedCitation": display,
            "plainCitation": display,
            "noteIndex": 0,
        },
        "citationItems": [citation_item],
        "schema": SCHEMA,
    }


def field_code_xml(code: str) -> str:
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> {escape(code)} </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    )


def citation_field_xml(library: dict[str, dict], display: str) -> str:
    payload = citation_payload(library, display)
    code = "ADDIN ZOTERO_ITEM CSL_CITATION " + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )
    result = (
        "<w:r>"
        "<w:rPr>"
        '<w:vertAlign w:val="superscript"/>'
        '<w:rFonts w:ascii="Times New Roman" w:eastAsia="宋体" w:hAnsi="Times New Roman"/>'
        "</w:rPr>"
        f"<w:t>{escape(display)}</w:t>"
        "</w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )
    return field_code_xml(code) + result


def bibliography_field_xml() -> str:
    code = 'ADDIN ZOTERO_BIBL {"uncited":[],"omitted":[],"custom":[]} CSL_BIBLIOGRAPHY'
    font = (
        "<w:rPr>"
        '<w:rFonts w:ascii="Times New Roman" w:eastAsia="宋体" w:hAnsi="Times New Roman"/>'
        "</w:rPr>"
    )
    paragraphs: list[str] = []
    for index, entry in enumerate(BIBL_ENTRIES):
        runs = ""
        if index == 0:
            runs += field_code_xml(code)
        runs += f'<w:r>{font}<w:t xml:space="preserve">{escape(entry)}</w:t></w:r>'
        if index == len(BIBL_ENTRIES) - 1:
            runs += '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        paragraphs.append(f"<w:p>{runs}</w:p>")
    return "".join(paragraphs)


def replace_citations(xml: str, library: dict[str, dict], expected: int) -> str:
    patterns = [
        re.compile(
            r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            r'<w:r><w:instrText[^>]*> ADDIN ZOTERO_ITEM CSL_CITATION .*?</w:instrText></w:r>'
            r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            r"<w:r>(?:<w:rPr>.*?</w:rPr>)?<w:t>([^<]+)</w:t></w:r>"
            r'<w:r><w:fldChar w:fldCharType="end"/></w:r>',
            re.DOTALL,
        ),
        re.compile(
            r'<w:fldSimple w:instr="ADDIN ZOTERO_ITEM CSL_CITATION .*?">'
            r"<w:r><w:rPr>.*?</w:rPr><w:t>([^<]+)</w:t></w:r>"
            r"</w:fldSimple>",
            re.DOTALL,
        ),
    ]

    def _repl(match: re.Match[str]) -> str:
        display = match.group(1)
        if display not in CITATION_SPECS:
            raise RuntimeError(f"Unexpected citation display text: {display}")
        return citation_field_xml(library, display)

    total = 0
    updated = xml
    for pattern in patterns:
        updated, count = pattern.subn(_repl, updated)
        total += count
    if total != expected:
        raise RuntimeError(f"Expected {expected} citation fields, replaced {total}")
    return updated


def replace_bibliography(xml: str) -> str:
    token = "ADDIN ZOTERO_BIBL"
    idx = xml.find(token)
    if idx >= 0:
        para_start = xml.rfind("<w:p>", 0, idx)
        end = xml.find('<w:fldChar w:fldCharType="end"/>', idx)
        if para_start < 0 or end < 0:
            raise RuntimeError("Failed to locate existing bibliography field bounds")
        end = xml.find("</w:p>", end)
        if end < 0:
            raise RuntimeError("Bibliography field is missing a closing paragraph")
        end += len("</w:p>")
        return xml[:para_start] + bibliography_field_xml() + xml[end:]

    old = (
        "<w:p><w:r><w:t>[1] 陈登原. 国史旧闻：第1卷[M]. 北京：中华书局，2000：29.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>[2] 袁训来，陈哲，肖书海，等. 蓝田生物群：一个认识多细胞生物起源和早期演化的新窗口[J]. 科学通报，2012，55(34)：3219.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>[3] 哈里森，沃尔德伦. 经济数学与金融数学[M]. 谢远涛，译. 北京：中国人民大学出版社，2012：235-236.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>[4] 马克思. 政治经济学批判[M]//马克思，恩格斯. 马克思恩格斯全集：第35卷. 北京：人民出版社，2013：302.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>[5] 冯西桥. 核反应堆压力管道与压力容器的LBB分析[R]. 北京：清华大学核能技术设计研究院，1997.</w:t></w:r></w:p>"
    )
    if old not in xml:
        raise RuntimeError("Neither a Zotero bibliography field nor the static block was found")
    return xml.replace(old, bibliography_field_xml(), 1)


def strip_pref_field(xml: str) -> str:
    """Remove the unused body-level ZOTERO_PREF field from earlier repairs."""
    pattern = re.compile(
        r"<w:p>(?:(?!</w:p>).)*ZOTERO_PREF(?:(?!</w:p>).)*</w:p>",
        re.DOTALL,
    )
    return pattern.sub("", xml, count=1)


def custom_properties_xml() -> str:
    return shared_custom_properties_xml(document_data_xml())


def patch_package_rels(xml: str) -> str:
    rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
    if rel_type in xml:
        return xml
    extra = (
        '<Relationship Id="rIdZoteroPref" '
        f'Type="{rel_type}" '
        'Target="docProps/custom.xml"/>'
    )
    return xml.replace("</Relationships>", extra + "</Relationships>", 1)


def patch_content_types(xml: str) -> str:
    xml = re.sub(
        r'<Override PartName="/customXml/itemProps2.xml"[^/]*/>',
        "",
        xml,
    )
    if 'PartName="/docProps/custom.xml"' not in xml:
        extra = (
            '<Override PartName="/docProps/custom.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>'
        )
        xml = xml.replace("</Types>", extra + "</Types>", 1)
    return xml


def patch_document_rels(xml: str) -> str:
    return xml.replace(
        '<Relationship Id="rIdZoteroData" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" '
        'Target="../customXml/item2.xml"/>',
        "",
    )


def rewrite_docx(path: Path, mutate_document_xml) -> None:
    with zipfile.ZipFile(path, "r") as zin:
        parts = {info.filename: zin.read(info.filename) for info in zin.infolist()}
        infos = list(zin.infolist())

    document_xml = parts["word/document.xml"].decode("utf-8")
    document_xml = mutate_document_xml(document_xml)
    document_xml = strip_pref_field(document_xml)
    parts["word/document.xml"] = document_xml.encode("utf-8")

    parts["[Content_Types].xml"] = patch_content_types(
        parts["[Content_Types].xml"].decode("utf-8")
    ).encode("utf-8")
    parts["_rels/.rels"] = patch_package_rels(
        parts["_rels/.rels"].decode("utf-8")
    ).encode("utf-8")
    parts["word/_rels/document.xml.rels"] = patch_document_rels(
        parts["word/_rels/document.xml.rels"].decode("utf-8")
    ).encode("utf-8")
    parts["docProps/custom.xml"] = custom_properties_xml().encode("utf-8")

    drop = {
        "customXml/item2.xml",
        "customXml/itemProps2.xml",
        "customXml/_rels/item2.xml.rels",
    }

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        written = set()
        for info in infos:
            if info.filename in drop:
                continue
            new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
            new_info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(new_info, parts[info.filename])
            written.add(info.filename)
        for name, content in parts.items():
            if name in written or name in drop:
                continue
            zout.writestr(name, content)
    path.write_bytes(buffer.getvalue())


def main() -> None:
    library = load_library()

    def mutate_active(xml: str) -> str:
        xml = replace_citations(xml, library, expected=5)
        return replace_bibliography(xml)

    def mutate_template(xml: str) -> str:
        xml = replace_citations(xml, library, expected=6)
        return replace_bibliography(xml)

    rewrite_docx(ACTIVE_DOC, mutate_active)
    rewrite_docx(TEMPLATE_DOC, mutate_template)
    print(f"repaired {ACTIVE_DOC.name}")
    print(f"repaired {TEMPLATE_DOC.name}")


if __name__ == "__main__":
    main()
