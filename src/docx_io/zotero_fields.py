"""Zotero 活动引用（Live Citation）兼容层。

Word 版 Zotero 插件对 DOCX 的要求非常挑剔，下面三点任意一条不满足，
点击 Word 功能区的 ``Zotero → Refresh`` 就会卡在 “Refreshing...” 或直接
弹出 “Zotero 在更新文档时出错”：

1. 文档首选项必须写在 **Word 自定义文档属性** ``ZOTERO_PREF_1/2/...``
   （``docProps/custom.xml``，每段 255 字符），而不是正文域或自造的
   ``customXml`` 部件；
2. 每个 ``ADDIN ZOTERO_ITEM CSL_CITATION`` 域里的每个 citationItem 都必须带
   ``uris`` 数组。Zotero 9 在回退到内嵌 ``itemData`` 时会读
   ``citationItem.uris.length``，缺键直接抛异常；
3. 引用域必须是 **复杂域**（begin/separate/end），``w:fldSimple`` 形式的
   Zotero 域插件识别不了。

本模块把这些修复做成可复用能力：既被排版流水线在保存成品 DOCX 后自动调用
（场景配置 ``zotero.enabled``，默认开启），也被 ``scripts/repair_zotero_word_fields.py``
与命令行 ``python -m src.docx_io.zotero_fields <文件>`` 复用。
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, unescape

__all__ = [
    "ZoteroCompatConfigLike",
    "ZoteroRepairReport",
    "DEFAULT_STYLE_ID",
    "DEFAULT_LOCALE",
    "docx_has_zotero_fields",
    "build_document_prefs",
    "normalize_document_xml",
    "repair_docx",
]

DEFAULT_STYLE_ID = (
    "http://www.zotero.org/styles/china-national-standard-gb-t-7714-2015-numeric"
)
DEFAULT_LOCALE = "zh-CN"
DEFAULT_SESSION_ID = "LarkFmt01"
CSL_SCHEMA = "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
MAX_PROPERTY_LENGTH = 255

CUSTOM_PROPS_PART = "docProps/custom.xml"
CUSTOM_PROPS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.custom-properties+xml"
)
CUSTOM_PROPS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
)
_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

_NS = {
    "cp": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
    "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
}

_FLD_SIMPLE_RE = re.compile(
    r'<w:fldSimple\b[^>]*w:instr="(?P<instr>[^"]*ADDIN ZOTERO_[^"]*)"[^>]*>'
    r"(?P<body>.*?)</w:fldSimple>",
    re.DOTALL,
)
_INSTR_RE = re.compile(r"(<w:instrText[^>]*>)(.*?)(</w:instrText>)", re.DOTALL)
_PREF_PARAGRAPH_RE = re.compile(
    r"<w:p\b(?:(?!</w:p>).)*ZOTERO_PREF(?:(?!</w:p>).)*</w:p>", re.DOTALL
)


class ZoteroCompatConfigLike:
    """鸭子类型说明：任何带下列属性的对象都可以传给 :func:`repair_docx`。"""

    enabled: bool = True
    style_id: str = DEFAULT_STYLE_ID
    locale: str = DEFAULT_LOCALE
    store_references: bool = True
    write_document_prefs: bool = True
    overwrite_document_prefs: bool = False


@dataclass
class ZoteroRepairReport:
    """一次修复的结果摘要。"""

    path: str = ""
    has_fields: bool = False
    changed: bool = False
    citations: int = 0
    citation_items_fixed: int = 0
    field_simple_converted: int = 0
    prefs_written: bool = False
    prefs_present: bool = False
    dropped_parts: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.has_fields:
            return "未检测到 Zotero 活动引用域，已跳过"
        bits = [f"引用域 {self.citations} 处"]
        if self.citation_items_fixed:
            bits.append(f"补齐 uris {self.citation_items_fixed} 项")
        if self.field_simple_converted:
            bits.append(f"fldSimple 转复杂域 {self.field_simple_converted} 处")
        if self.prefs_written:
            bits.append("已写入 ZOTERO_PREF 文档首选项")
        elif self.prefs_present:
            bits.append("保留原有文档首选项")
        if self.dropped_parts:
            bits.append(f"清理无效部件 {len(self.dropped_parts)} 个")
        return "，".join(bits)


# --------------------------------------------------------------------------
# 文档首选项（ZOTERO_PREF_n）
# --------------------------------------------------------------------------
def build_document_prefs(
    *,
    style_id: str = DEFAULT_STYLE_ID,
    locale: str = DEFAULT_LOCALE,
    store_references: bool = True,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:
    """生成 Zotero 文档首选项串。

    Zotero 9 会先尝试 ``JSON.parse()``，JSON 还能避开 Word 对
    ``<data ...>`` 的实体转义问题，因此这里统一输出 JSON。
    """
    return json.dumps(
        {
            "style": {
                "styleID": style_id,
                "locale": locale,
                "hasBibliography": True,
                "bibliographyStyleHasBeenSet": True,
            },
            "prefs": {
                "fieldType": "Field",
                "storeReferences": bool(store_references),
                "automaticJournalAbbreviations": True,
                "noteType": 0,
            },
            "sessionID": session_id,
            "zoteroVersion": "9.0.0",
            "dataVersion": 3,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _existing_custom_properties(raw: bytes | None) -> tuple[list[tuple[str, str]], str]:
    """返回 (非 Zotero 属性的 [name, value] 列表, 已存在的 ZOTERO_PREF 拼接串)。"""
    if not raw:
        return [], ""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return [], ""
    others: list[tuple[str, str]] = []
    pref_chunks: list[tuple[int, str]] = []
    for prop in root.findall("cp:property", _NS):
        name = prop.get("name") or ""
        value = prop.findtext("vt:lpwstr", default="", namespaces=_NS) or ""
        if name.startswith("ZOTERO_PREF_"):
            try:
                index = int(name.rsplit("_", 1)[1])
            except ValueError:
                index = len(pref_chunks) + 1
            pref_chunks.append((index, value))
        elif name:
            others.append((name, value))
    joined = "".join(text for _, text in sorted(pref_chunks))
    return others, joined


def custom_properties_xml(
    prefs: str, *, keep_properties: list[tuple[str, str]] | None = None
) -> str:
    """把首选项串按 255 字符切片写成 ZOTERO_PREF_n 自定义文档属性。"""
    properties: list[str] = []
    pid = 2  # pid 1 由规范保留
    for name, value in keep_properties or []:
        properties.append(
            f'<property fmtid="{_FMTID}" pid="{pid}" name="{escape(name)}">'
            f"<vt:lpwstr>{escape(value)}</vt:lpwstr></property>"
        )
        pid += 1
    chunks = [
        prefs[i : i + MAX_PROPERTY_LENGTH]
        for i in range(0, len(prefs), MAX_PROPERTY_LENGTH)
    ] or [""]
    for index, chunk in enumerate(chunks, start=1):
        properties.append(
            f'<property fmtid="{_FMTID}" pid="{pid}" name="ZOTERO_PREF_{index}">'
            f"<vt:lpwstr>{escape(chunk)}</vt:lpwstr></property>"
        )
        pid += 1
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        + "".join(properties)
        + "</Properties>\n"
    )


def _patch_content_types(xml: str) -> str:
    xml = re.sub(r'<Override PartName="/customXml/itemProps\d+\.xml"[^>]*/>\s*', "", xml)
    if f'PartName="/{CUSTOM_PROPS_PART}"' not in xml:
        override = (
            f'<Override PartName="/{CUSTOM_PROPS_PART}" '
            f'ContentType="{CUSTOM_PROPS_CONTENT_TYPE}"/>'
        )
        xml = xml.replace("</Types>", override + "</Types>", 1)
    return xml


def _patch_package_rels(xml: str) -> str:
    if CUSTOM_PROPS_REL_TYPE in xml:
        return xml
    rel = (
        '<Relationship Id="rIdZoteroPref" '
        f'Type="{CUSTOM_PROPS_REL_TYPE}" Target="{CUSTOM_PROPS_PART}"/>'
    )
    return xml.replace("</Relationships>", rel + "</Relationships>", 1)


def _drop_stale_customxml_rels(xml: str, targets: set[str]) -> str:
    for target in targets:
        xml = re.sub(
            r'<Relationship[^>]*Target="[^"]*'
            + re.escape(Path(target).name)
            + r'"[^>]*/>',
            "",
            xml,
        )
    return xml


# --------------------------------------------------------------------------
# 正文域
# --------------------------------------------------------------------------
def docx_has_zotero_fields(path: str | Path) -> bool:
    """快速判断一个 DOCX 是否含 Zotero 活动引用域。"""
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", "ignore")
    except (KeyError, OSError, zipfile.BadZipFile):
        return False
    return "ZOTERO_ITEM" in xml or "ZOTERO_BIBL" in xml


def _complex_field_xml(code: str, body: str) -> str:
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> {escape(code.strip())} </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f"{body}"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def _fix_citation_payload(payload: dict) -> int:
    """就地补齐 Zotero 9 必需的字段，返回修复的 citationItem 数量。"""
    fixed = 0
    props = payload.get("properties")
    if isinstance(props, dict):
        props.pop("style", None)
        if not isinstance(props.get("noteIndex"), int):
            props["noteIndex"] = 0
    else:
        payload["properties"] = {"noteIndex": 0}
    payload.setdefault("schema", CSL_SCHEMA)

    items = payload.get("citationItems")
    if not isinstance(items, list):
        return fixed
    for item in items:
        if not isinstance(item, dict):
            continue
        touched = False
        uris = item.get("uris")
        if not isinstance(uris, list):
            item["uris"] = []
            touched = True
        item_data = item.get("itemData")
        if isinstance(item_data, dict):
            # id 必须是字符串，且与 itemData.id 一致，否则会与用户库里的
            # 数字 id 撞车，Refresh 报“更新文档时出错”。
            raw_id = item.get("id", item_data.get("id"))
            if raw_id is not None and not isinstance(raw_id, str):
                raw_id = str(raw_id)
                touched = True
            if raw_id is not None:
                if item.get("id") != raw_id:
                    item["id"] = raw_id
                    touched = True
                if item_data.get("id") != raw_id:
                    item_data["id"] = raw_id
                    touched = True
        if touched:
            fixed += 1
    return fixed


def normalize_document_xml(xml: str) -> tuple[str, dict]:
    """规范化 ``word/document.xml``，返回 (新 XML, 统计信息)。"""
    stats = {"citations": 0, "citation_items_fixed": 0, "field_simple_converted": 0,
             "pref_paragraphs_removed": 0}

    def _convert_simple(match: re.Match[str]) -> str:
        stats["field_simple_converted"] += 1
        code = unescape(match.group("instr"), {"&quot;": '"', "&apos;": "'"})
        return _complex_field_xml(code, match.group("body"))

    xml = _FLD_SIMPLE_RE.sub(_convert_simple, xml)

    def _fix_instr(match: re.Match[str]) -> str:
        head, body, tail = match.groups()
        raw = unescape(body)
        if "CSL_CITATION" not in raw:
            return match.group(0)
        stats["citations"] += 1
        start = raw.find("{")
        if start < 0:
            return match.group(0)
        prefix = raw[:start]
        try:
            payload = json.loads(raw[start:])
        except json.JSONDecodeError:
            return match.group(0)
        stats["citation_items_fixed"] += _fix_citation_payload(payload)
        rebuilt = prefix.strip() + " " + json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )
        return f'{head}{escape(" " + rebuilt.strip() + " ")}{tail}'

    xml = _INSTR_RE.sub(_fix_instr, xml)

    # 正文里的 ZOTERO_PREF 域是早期误写，插件从不读取，留着反而干扰。
    xml, removed = _PREF_PARAGRAPH_RE.subn("", xml)
    stats["pref_paragraphs_removed"] = removed
    return xml, stats


# --------------------------------------------------------------------------
# 对外主入口
# --------------------------------------------------------------------------
def repair_docx(
    path: str | Path,
    *,
    style_id: str = DEFAULT_STYLE_ID,
    locale: str = DEFAULT_LOCALE,
    store_references: bool = True,
    session_id: str = DEFAULT_SESSION_ID,
    write_document_prefs: bool = True,
    overwrite_document_prefs: bool = False,
    only_if_zotero_fields: bool = True,
) -> ZoteroRepairReport:
    """让 DOCX 里的 Zotero 活动引用在 Word 中可以正常 Refresh。

    默认只在文档确实含 Zotero 域时才动手（``only_if_zotero_fields``），
    因此可以安全地挂在排版流水线末尾对所有文档调用。
    """
    docx_path = Path(path)
    report = ZoteroRepairReport(path=str(docx_path))
    if not docx_path.is_file():
        report.messages.append("文件不存在")
        return report

    try:
        with zipfile.ZipFile(docx_path, "r") as zin:
            infos = list(zin.infolist())
            parts = {info.filename: zin.read(info.filename) for info in infos}
    except (OSError, zipfile.BadZipFile) as exc:
        report.messages.append(f"无法读取 DOCX：{exc}")
        return report

    if "word/document.xml" not in parts:
        report.messages.append("缺少 word/document.xml")
        return report

    document_xml = parts["word/document.xml"].decode("utf-8")
    report.has_fields = "ZOTERO_ITEM" in document_xml or "ZOTERO_BIBL" in document_xml
    if only_if_zotero_fields and not report.has_fields:
        return report

    new_document_xml, stats = normalize_document_xml(document_xml)
    report.citations = stats["citations"]
    report.citation_items_fixed = stats["citation_items_fixed"]
    report.field_simple_converted = stats["field_simple_converted"]

    others, existing_prefs = _existing_custom_properties(parts.get(CUSTOM_PROPS_PART))
    report.prefs_present = bool(existing_prefs.strip())
    prefs = existing_prefs
    need_prefs = write_document_prefs and (
        overwrite_document_prefs or not report.prefs_present
    )
    if need_prefs:
        prefs = build_document_prefs(
            style_id=style_id,
            locale=locale,
            store_references=store_references,
            session_id=session_id,
        )

    new_custom_xml = custom_properties_xml(prefs, keep_properties=others).encode("utf-8")
    prefs_changed = parts.get(CUSTOM_PROPS_PART) != new_custom_xml
    report.prefs_written = need_prefs and prefs_changed

    # Zotero 从不读取这些自造的 customXml 部件，旧文档里残留会让 Word 报错。
    drop = {
        name
        for name in parts
        if name.startswith("customXml/")
        and b"ZOTERO" in parts[name].upper()
    }
    for name in list(drop):
        rels = f"customXml/_rels/{Path(name).name}.rels"
        if rels in parts:
            drop.add(rels)
    report.dropped_parts = sorted(drop)

    content_types = parts.get("[Content_Types].xml", b"").decode("utf-8")
    new_content_types = _patch_content_types(content_types) if content_types else ""
    package_rels = parts.get("_rels/.rels", b"").decode("utf-8")
    new_package_rels = _patch_package_rels(package_rels) if package_rels else ""
    doc_rels = parts.get("word/_rels/document.xml.rels", b"").decode("utf-8")
    new_doc_rels = _drop_stale_customxml_rels(doc_rels, drop) if doc_rels else ""

    changed = (
        new_document_xml != document_xml
        or prefs_changed
        or bool(drop)
        or new_content_types != content_types
        or new_package_rels != package_rels
        or new_doc_rels != doc_rels
    )
    report.changed = changed
    if not changed:
        return report

    parts["word/document.xml"] = new_document_xml.encode("utf-8")
    parts[CUSTOM_PROPS_PART] = new_custom_xml
    if content_types:
        parts["[Content_Types].xml"] = new_content_types.encode("utf-8")
    if package_rels:
        parts["_rels/.rels"] = new_package_rels.encode("utf-8")
    if doc_rels:
        parts["word/_rels/document.xml.rels"] = new_doc_rels.encode("utf-8")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        written: set[str] = set()
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
    docx_path.write_bytes(buffer.getvalue())
    return report


def repair_docx_with_config(path: str | Path, config) -> ZoteroRepairReport:
    """按场景配置（``SceneConfig.zotero``）执行修复。"""
    if config is None or not bool(getattr(config, "enabled", False)):
        return ZoteroRepairReport(path=str(path), messages=["Zotero 兼容功能未启用"])
    return repair_docx(
        path,
        style_id=str(getattr(config, "style_id", "") or DEFAULT_STYLE_ID),
        locale=str(getattr(config, "locale", "") or DEFAULT_LOCALE),
        store_references=bool(getattr(config, "store_references", True)),
        write_document_prefs=bool(getattr(config, "write_document_prefs", True)),
        overwrite_document_prefs=bool(
            getattr(config, "overwrite_document_prefs", False)
        ),
    )


def _cli(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="修复 DOCX 中的 Zotero 活动引用域，使 Word 可以正常 Refresh。"
    )
    parser.add_argument("files", nargs="+", help="要修复的 .docx 文件")
    parser.add_argument("--style-id", default=DEFAULT_STYLE_ID)
    parser.add_argument("--locale", default=DEFAULT_LOCALE)
    parser.add_argument(
        "--force-prefs",
        action="store_true",
        help="覆盖文档中已有的 Zotero 文档首选项（切换引用样式时使用）",
    )
    args = parser.parse_args(argv)

    exit_code = 0
    for name in args.files:
        report = repair_docx(
            name,
            style_id=args.style_id,
            locale=args.locale,
            overwrite_document_prefs=args.force_prefs,
        )
        print(f"{name}: {report.summary()}")
        if report.messages:
            exit_code = 1
            for message in report.messages:
                print(f"  ! {message}")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(_cli(sys.argv[1:]))
