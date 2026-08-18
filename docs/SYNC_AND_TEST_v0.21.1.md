# v0.21.1 同步与测试速查

## 一、同步代码（PowerShell）

```powershell
cd D:\你的路径\Lark-Formatter          # 换成你的仓库目录

git fetch origin --tags
git checkout arena/01a013c1-lark-formatter
git pull origin arena/01a013c1-lark-formatter --no-rebase

git log --oneline -3
# 应看到：
# e7aedb9 chore: 随包分发内置 Zotero 联动模板 docx
# 04c2cf2 feat: 把 Zotero 活动引用兼容并入默认模板与默认功能
# b604d34 fix: add empty uris arrays so Zotero 9 Refresh does not crash

git tag            # 应看到 v0.21 和 v0.21.1
```

> 注意：`v0.21.1` 这个 tag 我重新指过一次（补上内置模板 docx）。
> 如果你之前已经 fetch 过旧的 v0.21.1，用 `git fetch origin --tags --force` 覆盖本地 tag。

想回到“验证成功那一版”：`git checkout v0.21`（只读查看），回到最新：`git checkout arena/01a013c1-lark-formatter`。

## 二、模板到底更新了什么

| 对象 | 是否变化 |
| :--- | :--- |
| `src/scene/presets/default_format.json`（内置默认模板） | ✅ 新增 `zotero` 配置段 + `capabilities.zotero_live_citation` |
| `src/resources/zotero/*`（新增内置资源） | ✅ 联动模板 docx、GB/T 7714 CSL、示例文献库 |
| 根目录 4 个论文 docx（含 Zotero 活动引用版/联动模板） | ⏸ 内容零变化（重构后重跑脚本，产物字节一致） |
| 你本机的 `templates\default_format.json`（用户可写模板） | ⚠️ **git pull 不会覆盖它**（设计如此，保护你的自定义） |

最后一条不影响功能：模板 JSON 里缺 `zotero` 段时，程序按内置默认值处理（= 开启）。
如果你想让“格式配置”里也能看到这一段，删掉用户模板让它重新播种即可：

```powershell
copy templates\default_format.json templates\default_format.json.bak
del templates\default_format.json
python main.py        # 启动时会用新的内置模板重新生成
```

## 三、测试命令

> 最简验收：只用之前那份测试文档跑第 3、4 步（端到端 + 体检）通过，就说明功能正常。
> `tests/` 目录被 `.gitignore` 整体忽略，`tests/test_zotero_compat.py` 已在提交 `411e382` 中强制加入，
> 若提示“file or directory not found”，`git pull` 一次即可。


```powershell
conda activate lark
cd D:\你的路径\Lark-Formatter
```

### 1) 单元测试（最快的验收）
```powershell
python -m pytest -q tests\test_zotero_compat.py tests\test_zotero_word_fields.py
# 期望：7 passed
```

### 2) 确认默认模板已带 Zotero 配置
```powershell
python -c "from pathlib import Path; from src.scene.manager import load_scene; c=load_scene(Path('src/scene/presets/default_format.json')); print(c.zotero); print(c.capabilities['zotero_live_citation'])"
```

### 3) 命令行修复任意 docx（含强制切换引用样式）
```powershell
python -m src.docx_io.zotero_fields "鲁东大学学术学位论文_Zotero活动引用版.docx"
python -m src.docx_io.zotero_fields "论文_new.docx" --force-prefs
```

### 4) 端到端：用新默认模板跑一遍排版，检查 Zotero 域是否完好
```powershell
copy "鲁东大学学术学位论文_Zotero活动引用版.docx" test_zotero_run.docx

python -c "from pathlib import Path; from src.scene.manager import load_scene; from src.engine.pipeline import Pipeline; cfg=load_scene(Path('src/scene/presets/default_format.json')); r=Pipeline(cfg).run('test_zotero_run.docx'); print(r.success, r.output_paths.get('final')); [print('ZOTERO:', x.change_type, x.after) for x in r.tracker.records if x.target=='zotero_live_citation']"
```
期望输出里有：`ZOTERO: repair Zotero 活动引用：引用域 5 处…`

再体检成品文件：
```powershell
python -c "import json,re,zipfile; z=zipfile.ZipFile('test_zotero_run_new.docx'); x=z.read('word/document.xml').decode(); p=[json.loads(t[t.find('{'):]) for t in re.findall(r'<w:instrText[^>]*>(.*?)</w:instrText>',x,re.S) if 'CSL_CITATION' in t]; print('引用域', len(p), '| fldSimple', 'fldSimple' in x, '| uris ok', all(i.get('uris')==[] for q in p for i in q['citationItems']), '| prefs', 'docProps/custom.xml' in z.namelist())"
```
期望：`引用域 5 | fldSimple False | uris ok True | prefs True`

### 5) 界面验收
```powershell
python main.py
```
- 「实验室」面板底部应出现 **Zotero 活动引用兼容**（默认勾选）、**强制写入 GB/T 7714 引用样式**、**导出 Zotero 模板与样式...**、以及 `!` 说明按钮；
- 点导出按钮选个文件夹，应导出 4 个文件（联动模板 docx / CSL / json / ris）；
- 选一篇带 Zotero 引用的论文点“开始排版”，日志里应出现 `Zotero 活动引用兼容: 开启（…）`。

### 6) Word 端最终验收
1. 先在 Zotero：编辑 → 设置 → 引用 → 样式 → `+` → 选导出的 `.csl`；
2. 先开 Zotero，再用 Word 打开 `xxx_new.docx`；
3. 点 `Zotero → Refresh`，正文 `[1]` 上标与文末参考文献应正常重建，不再报错。

---

## 四、GUI（`python main.py`）按老测试文档跑通的步骤

沙箱里已用无头 Qt 完整走过一遍，结论：界面构建、导出按钮、开始排版、Zotero 修复全部正常。
你在本机按下面顺序点一遍即可复现：

```powershell
conda activate lark
cd E:\0writing\Lark-Formatter
python main.py
```

1. **模板**：`场景/模板` 选择 **默认格式**（若之前删过 `templates\default_format.json`，
   启动时会自动用新的内置模板重新播种，里面已带 `zotero` 段）。
2. **文档**：`浏览...` 选之前那份测试文档，例如
   `鲁东大学学术学位论文_Zotero活动引用版.docx`（建议先复制一份 `test_zotero_run.docx` 再选）。
3. **实验室面板**：确认底部出现 **Zotero 活动引用兼容**，默认已勾选；
   「强制写入 GB/T 7714 引用样式」保持不勾（除非要强制换样式）。
4. **可选**：点 **导出 Zotero 模板与样式...**，选一个空文件夹，应导出 4 个文件：
   `鲁东大学学术学位论文_Zotero联动模板.docx`、`china-national-standard-gb-t-7714-2015-numeric.csl`、
   `Ludong_Thesis_Zotero_library.json`、`.ris`。日志出现 `已导出 Zotero 模板与样式到：…`。
5. **点「开始排版」**，日志里应依次看到：
   ```
   Zotero 活动引用兼容: 开启（强制写入 GB/T 7714 样式=否）
   开始排版...
   ...
   排版完成/部分成功! 共 N 项修改
   ```
6. **检查成品** `xxx_new.docx`：
   ```powershell
   python -c "import json,re,zipfile; z=zipfile.ZipFile('test_zotero_run_new.docx'); x=z.read('word/document.xml').decode(); p=[json.loads(t[t.find('{'):]) for t in re.findall(r'<w:instrText[^>]*>(.*?)</w:instrText>',x,re.S) if 'CSL_CITATION' in t]; print('引用域', len(p), '| fldSimple', 'fldSimple' in x, '| uris ok', all(i.get('uris')==[] for q in p for i in q['citationItems']), '| prefs', 'docProps/custom.xml' in z.namelist())"
   ```
   期望：`引用域 5 | fldSimple False | uris ok True | prefs True`
   （JSON 报告 `xxx_排版附件\xxx_报告.json` 里也会有一条 `zotero_live_citation` 记录。）
7. **Word 端**：先开 Zotero（确认已安装 GB/T 7714-2015 numeric 样式）→ 再用 Word 打开成品 →
   `Zotero → Refresh`，正文 `[1]`–`[5]` 上标与文末参考文献正常重建即为全流程通过。
