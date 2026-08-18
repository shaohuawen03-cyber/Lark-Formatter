# 鲁东大学研究生学位论文排版与 Zotero 参考文献管理指南

本文档汇总了本次为您定制的学位论文排版模板及与 Zotero 联动的完整交付成果。

---

## 一、交付文件清单

| 文件名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **`鲁东大学学术硕士学位论文_标准定稿版.docx`** | DOCX (静态定稿版) | **推荐使用**。封面含官方校名图徽、校徽圆形印章，所有个人及导师信息完整填入，全要素符合学校写作规范（A4、页边距上3下2.5左3右3、第X章/1.1/1.1.1/1.1.1.1编号、三线表、22磅目录行距）。 |
| **`鲁东大学学术学位论文_Zotero活动引用版.docx`** | DOCX (Zotero活动版) | 内置 Zotero CSL 活动引用字段，可在 Word 中直接与 Zotero 软件联动，一键刷新或切换引用样式。 |
| **`Ludong_Thesis_Zotero_library.json`** | CSL-JSON | **Zotero 文献库导入文件（推荐）**。包含学校规范中全部示例参考文献（专著[M]、期刊[J]、学位论文[D]、会议[C]、标准[S]、专利[P]、报纸[N]等）的完整结构化元数据。 |
| **`Ludong_Thesis_Zotero_library.ris`** | RIS | RIS 格式文献库，备用导入文件。 |
| **`Ludong_Thesis_Zotero_library.bib`** | BibTeX | BibTeX 格式文献库，备用导入文件。 |
| **`assets/ludong_logo_text.jpeg`** | 图片 | 从官方 PDF 中提取的“鲁东大学”书法校名矢量位图。 |
| **`assets/ludong_emblem.jpeg`** | 图片 | 从官方 PDF 中提取的鲁东大学圆形校徽图徽。 |

---

## 二、Zotero 参考文献联动使用流程

### 1. 将文献库导入到 Zotero
1. 打开 Zotero 客户端；
2. 点击菜单栏 **文件 (File) → 导入 (Import...)**；
3. 选择 **`Ludong_Thesis_Zotero_library.json`**（或 `Ludong_Thesis_Zotero_library.ris`）；
4. 导入后，您的 Zotero 中会建立一个名为 `Ludong_Thesis_Zotero_library` 的分类，包含全部示例文献。

### 2. 先安装学校引用样式，再打开活动文档
Zotero 刷新文档时必须能在本地找到 CSL 样式。如果样式未安装，插件会尝试在线下载并弹出隐藏对话框，Word 功能区就会一直停在 **Refreshing...**。

1. 打开 Zotero 客户端（不要只开 Word）；
2. 菜单 **编辑 → 设置 → 引用 → 样式**，点击 `+`，选择仓库中的 `china-national-standard-gb-t-7714-2015-numeric.csl`；
3. 确认列表中已出现 **China National Standard GB/T 7714-2015 (numeric, 中文)**；
4. 打开 Word（确保已安装 Zotero Word 插件），再打开 **`鲁东大学学术学位论文_Zotero活动引用版.docx`**；
5. 在 Word 顶部功能区点击 **Zotero → Refresh**。正文引用会保持 `[1]`、`[2]` 上标，文末参考文献由活动域重新生成。

文档已把 Zotero 文档数据写进 Word 自定义属性 `ZOTERO_PREF_1`（Windows 插件真正读取的位置），引用域里带完整 `itemData` 和空的 `uris: []`。缺少 `uris` 时 Zotero 9 会在刷新时直接崩溃。

若仍要手动确认样式：点击 **Document Preferences（文档首选项）**，选择 **`China National Standard GB/T 7714-2015 (numeric, 中文)`**。

### 3. 日常写作与多处引用操作
- **常规插入引用**：在 Word 中需要引用的位置按 `Zotero → Add/Edit Citation`，搜索作者名或题目回车即可；
- **同一文献多处引用标注页码（如 `[13]59-60`）**：在 Zotero 引用框中点击文献气泡，在 `Page`（页码）栏填入 `59-60`，系统将自动生成标准格式；
- **定稿提交（移除活动字段）**：在论文最终提交送审前，可点击 `Zotero → Unlink Citations`，将活动字段固化为纯文本。

### 4. 若 Refresh 一直转圈
按下面顺序排查，几乎都能一次恢复：

1. **先完全退出 Word**（任务栏里也不要留着旧文档），再 `git pull` 打开仓库里的新文件。失败过一次的旧窗口不要保存。
2. **先启动 Zotero 再开 Word**。插件在 Word 里点 Refresh 时要连本地 Zotero。
3. **确认已安装上面的 CSL 文件**。不要让 Zotero 去 `zotero.org` 临时下载样式。
4. 如果同时装了 EndNote，先关掉 EndNote 再 Refresh，两个插件抢同一篇文档会报“更新文档时出错”。
5. 如果对话框被 Word 挡住，用 Alt+Tab 切到 Zotero。

---

## 三、Lark-Formatter 本地运行与一键排版

在您的 PowerShell 中执行以下命令即可同步最新文件并启动软件：

```powershell
# 1. 同步最新更新
git pull origin arena/01a00f8c-lark-formatter --no-rebase

# 2. 激活环境并启动软件
conda activate lark
python main.py
```
