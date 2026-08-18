"""内置资源定位（源码运行 / PyInstaller 打包均可用）。

``src/resources/zotero`` 里放的是 Zotero 联动的“开箱即用”素材：

- ``鲁东大学学术学位论文_Zotero联动模板.docx``：带活动引用域、可直接 Refresh 的论文模板；
- ``china-national-standard-gb-t-7714-2015-numeric.csl``：GB/T 7714-2015 顺序编码制样式；
- ``Ludong_Thesis_Zotero_library.json`` / ``.ris``：示例文献库，导入 Zotero 即可试用。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

__all__ = [
    "resources_dir",
    "zotero_dir",
    "zotero_assets",
    "export_zotero_assets",
    "ZOTERO_TEMPLATE_NAME",
    "ZOTERO_CSL_NAME",
]

ZOTERO_TEMPLATE_NAME = "鲁东大学学术学位论文_Zotero联动模板.docx"
ZOTERO_CSL_NAME = "china-national-standard-gb-t-7714-2015-numeric.csl"
_ZOTERO_LIBRARY_NAMES = (
    "Ludong_Thesis_Zotero_library.json",
    "Ludong_Thesis_Zotero_library.ris",
)


def _candidate_dirs() -> list[Path]:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        base = Path(meipass)
        candidates += [base / "src" / "resources", base / "resources"]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates += [
            exe_dir / "_internal" / "src" / "resources",
            exe_dir / "src" / "resources",
            exe_dir / "resources",
        ]
    candidates.append(Path(__file__).resolve().parent)
    # 源码目录（开发态）作为最后兜底
    candidates.append(Path(__file__).resolve().parents[2] / "src" / "resources")
    return candidates


def resources_dir() -> Path:
    """返回可用的内置资源目录。"""
    for candidate in _candidate_dirs():
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parent


def zotero_dir() -> Path:
    return resources_dir() / "zotero"


def zotero_assets() -> dict[str, Path]:
    """返回 {逻辑名: 路径}，只包含实际存在的文件。"""
    base = zotero_dir()
    mapping = {
        "template": base / ZOTERO_TEMPLATE_NAME,
        "csl": base / ZOTERO_CSL_NAME,
    }
    for index, name in enumerate(_ZOTERO_LIBRARY_NAMES):
        mapping[f"library_{index}"] = base / name
    return {key: path for key, path in mapping.items() if path.is_file()}


def export_zotero_assets(target_dir: str | Path) -> list[Path]:
    """把内置 Zotero 素材复制到用户选择的目录，返回复制后的文件列表。"""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in zotero_assets().values():
        destination = target / source.name
        shutil.copyfile(source, destination)
        copied.append(destination)
    return copied
