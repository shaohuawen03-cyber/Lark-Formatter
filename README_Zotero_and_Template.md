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
2. 点击菜单栏 **文件 (File) $\rightarrow$ 导入 (Import...)**；
3. 选择 **`Ludong_Thesis_Zotero_library.json`**（或 `Ludong_Thesis_Zotero_library.ris`）；
4. 导入后，您的 Zotero 中会建立一个名为 `Ludong_Thesis_Zotero_library` 的分类，包含全部 12 条经过校对的规范文献。

### 2. 在 Word 中设置学校官方引用样式
1. 打开 Word（确保已安装 Zotero Word 插件）；
2. 在 Word 顶部功能区点击 **Zotero** 标签页；
3. 点击 **Document Preferences（文档首选项）**；
4. 选择样式为：
   - **`China National Standard GB/T 7714-2015 (numeric, 中文)`**（国家标准顺序编码制）
   - *(如果列表中没有该样式，点击“管理样式” $\rightarrow$ “获取更多样式”，搜索 `GB/T 7714` 即可一键安装)*；
5. 点击 **Refresh（刷新）**，正文引用将自动呈现为 `[1]`、`[2]` 上标，文末自动生成规范的参考文献列表！

### 3. 日常写作与多处引用操作
- **常规插入引用**：在 Word 中需要引用的位置按 `Zotero $\rightarrow$ Add/Edit Citation`，搜索作者名或题目回车即可；
- **同一文献多处引用标注页码（如 `[13]59-60`）**：在 Zotero 引用框中点击文献气泡，在 `Page`（页码）栏填入 `59-60`，系统将自动生成标准格式；
- **定稿提交（移除活动字段）**：在论文最终提交送审前，可点击 `Zotero $\rightarrow$ Unlink Citations`，将活动字段固化为纯文本。

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
