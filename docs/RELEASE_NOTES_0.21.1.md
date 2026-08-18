# Release Notes · v0.21.1

发布日期：2026-08-18
上游基线：`v0.21`（Zotero 活动引用在 Word 中可正常 Refresh 的验证版本）

## 本次变更主题
把「Zotero 活动引用」从一次性的修复脚本，升级为 **Lark-Formatter 的默认功能与内置模板资源**。

## 新增能力

### 1. 排版流水线默认修复 Zotero 域（默认开启）
新增模块 `src/docx_io/zotero_fields.py`，在保存成品 `*_new.docx` 之后自动执行：

| 修复项 | 说明 |
| :--- | :--- |
| `citationItem.uris` 补齐 | Zotero 9 回退到内嵌 `itemData` 时会读 `uris.length`，缺键会抛出「Zotero 在更新文档时出错」 |
| `fldSimple` → 复杂域 | 插件只识别 `begin/separate/end` 复杂域 |
| `ZOTERO_PREF_1/2/...` | 文档首选项必须写入 Word 自定义文档属性（`docProps/custom.xml`，每段 255 字符），不能放正文域 |
| 引用 id 字符串化 | 数字 id 会与用户本地库条目撞车导致刷新报错 |
| 清理无效 `customXml` 部件 | 早期手写的 `customXml/item2.xml` 会干扰插件 |

特性：
- 文档中**不含** Zotero 域时自动跳过，不改动任何字节；
- 重复执行结果字节一致（幂等）；
- 执行结果写入变更记录（报告中的 `zotero_live_citation` 条目）；
- 异常被吞掉并记录，不会影响排版主流程。

### 2. 场景模板新增 `zotero` 配置段
`src/scene/presets/default_format.json`（默认格式模板）新增：

```json
"zotero": {
  "enabled": true,
  "style_id": "http://www.zotero.org/styles/china-national-standard-gb-t-7714-2015-numeric",
  "locale": "zh-CN",
  "store_references": true,
  "write_document_prefs": true,
  "overwrite_document_prefs": false
}
```

同时新增能力位 `capabilities.zotero_live_citation`。自定义/克隆模板未写该段时按默认值（开启）处理。

### 3. 界面：实验室 → Zotero 活动引用兼容
- 复选框「Zotero 活动引用兼容」（默认勾选）；
- 子选项「强制写入 GB/T 7714 引用样式」（覆盖文档中已有的引用样式设置，默认关闭）；
- 按钮「导出 Zotero 模板与样式...」：把内置资源一键导出到任意目录；
- 「!」使用须知说明。

### 4. 内置资源 `src/resources/zotero/`
随程序（及 PyInstaller 封包）分发：

- `鲁东大学学术学位论文_Zotero联动模板.docx`（可直接 Refresh 的活动引用模板）
- `china-national-standard-gb-t-7714-2015-numeric.csl`
- `Ludong_Thesis_Zotero_library.json` / `.ris`（示例文献库）

打包 spec 已加入 `("src/resources", "src/resources")`。

## 变更文件
- 新增：`src/docx_io/zotero_fields.py`、`src/resources/__init__.py`、`src/resources/zotero/*`、`tests/test_zotero_compat.py`
- 修改：`src/engine/pipeline.py`、`src/scene/schema.py`、`src/scene/manager.py`、
  `src/scene/presets/default_format.json`、`src/ui/main_window.py`、
  `scripts/repair_zotero_word_fields.py`（改为复用共享模块，输出与 v0.21 字节一致）、
  `Lark-Formatter_v0.20_LTS.spec`、`src/utils/app_meta.py`、`README.md`、`README_Zotero_and_Template.md`

## 验证
- `python -m unittest tests.test_zotero_compat tests.test_zotero_word_fields`（7 项全通过）
- 端到端：用默认模板对 `鲁东大学学术学位论文_Zotero活动引用版.docx` 跑完整流水线，成品仍保留 5 处活动引用域、
  `uris` 均为数组、`ZOTERO_PREF` 文档首选项完好。

## 使用提醒
Word 端刷新前仍需：先在 Zotero 中安装 GB/T 7714-2015 CSL 样式 → 先启动 Zotero 再打开 Word → 点击 `Zotero → Refresh`。
