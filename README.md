# PDF 批量下载器

一个基于 **wxPython** 的桌面小工具：输入任意含 PDF 链接的页面，批量抓取、过滤、下载，并按试卷类型自动归档。

专为 CAIE / Edexcel 等试卷站点（如 papacambridge）优化，也可用于任意含 PDF 链接的网页。

---

## 目录

- [功能特性](#功能特性)
- [截图](#截图)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [目录结构](#目录结构)
- [在 VS Code 中开发](#在-vs-code-中开发)
  - [打开项目与选择解释器](#打开项目与选择解释器)
  - [运行](#运行)
  - [调试](#调试)
- [打包为可执行文件](#打包为可执行文件)
- [上传到 GitHub](#上传到-github)
- [常见问题](#常见问题)
- [免责声明](#免责声明)
- [致谢](#致谢)
- [License](#license)

---

## 功能特性

- 🔍 **双策略抓取**：BeautifulSoup 扫描 `<a href>` + 正则兜底，覆盖 JS 内嵌与纯文本链接
- 🔗 **中转链接解析**：自动把 `download_file.php?files=<url>.pdf` 解成内层 pdf 直链（papacambridge 已实测）
- 🎯 **文件名白名单**：默认只下载文件名分段含 `er` / `gt` / `ms` / `qp` 的文件，`ci` 等自动跳过
- 📥 **健壮下载**：超时、3 次指数退避重试、已存在非空文件跳过、`.part` 原子写入防止半截文件
- 🧵 **后台线程**：下载全程 UI 可交互，不假死
- 📊 **日志 + 进度条**：每个文件的成功 / 失败 / 跳过都有记录
- 🗂️ **一键归档**：按文件名倒数第二段把 PDF 分到 `ms/` `qp` 子目录
- 💾 **不污染工作目录**：全程使用绝对路径，不 `chdir`

---

## 截图

> 建议放一张程序界面截图到 `docs/screenshot.png`，然后取消下一行注释。
>
> `![screenshot](docs/screenshot.png)`

---

## 环境要求

- **Python** 3.9 及以上
- 操作系统：Windows / macOS / Linux
- 依赖见 `requirements.txt`：

```
requests>=2.28
beautifulsoup4>=4.11
wxPython>=4.2
```

> **Windows**：`pip install wxPython` 若失败，去 <https://wxpython.org/pages/downloads/> 下载对应 Python 版本的 wheel 手动安装。
> **Linux**：需先装 GTK 开发库，例如 Debian/Ubuntu：`sudo apt install libgtk-3-dev libwebkit2gtk-4.1-dev`。
> **macOS**：`pip install wxPython` 一般可直接装好，必要时用 `--no-binary` 从源码编译。

---

## 安装

```bash
git clone https://github.com/<你的用户名>/pdf-downloader.git
cd pdf-downloader
pip install -r requirements.txt
```

推荐使用虚拟环境：

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## 快速开始

```bash
python main.py
```

操作流程：

1. **粘贴网址**：在"页面网址"输入框填入含 PDF 链接的页面，例如：
   `https://pastpapers.papacambridge.com/papers/caie/as-and-a-level-physics-9702-2026-march`
2. **扫描链接**：点 **扫描链接**，日志区会列出所有命中白名单的 PDF 直链
3. **选择目录**：点目录选择器，指定保存位置
4. **一键下载**：进度条与日志实时更新
5. **（可选）一键分类文件**：把已下载的 PDF 按 `ms` / `qp` 归档到子目录

示例输出：

```
扫描页面: https://pastpapers.papacambridge.com/papers/caie/as-and-a-level-physics-9702-2026-march
共发现 12 个 PDF 链接
  https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/9702_m26_er.pdf
  https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/9702_m26_gt.pdf
  https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/9702_m26_ms_12.pdf
  ...
开始下载到: C:\Users\xxx\Desktop\test
下载完成: 9702_m26_er.pdf
下载完成: 9702_m26_gt.pdf
...
完成: 成功 12，失败 0
```

---

## 配置说明

所有可调项集中在 `config.py`：

```python
# 只下载文件名分段里包含这些关键词的文件（大小写不敏感）
# 例如 9702_m26_er.pdf -> ['9702','m26','er'] -> 命中
#      9702_m26_ci_33.pdf -> ['9702','m26','ci','33'] -> 不命中，跳过
ALLOWED_KEYWORDS = ("er", "gt", "ms", "qp")

# 归档的子目录名
ARCHIVE_KINDS = ("ms", "qp")

# 网络参数
REQUEST_TIMEOUT = 30      # 单次请求超时（秒）
MAX_RETRIES = 3           # 失败重试次数
RETRY_BACKOFF = 1.0       # 第 n 次重试等待 n*BACKOFF 秒
DOWNLOAD_DELAY = 0.5      # 每个文件之间的节流（秒）

# papacambridge 对 Referer 敏感
PAPACAMBRIDGE_REFERER = "https://pastpapers.papacambridge.com/"

# 默认下载目录
DEFAULT_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
```

常用调整示例：

```python
ALLOWED_KEYWORDS = ("qp", "ms")   # 只要试卷 + 评分标准
ALLOWED_KEYWORDS = ("qp",)        # 只要试卷
ALLOWED_KEYWORDS = ()             # 不过滤，全部下载
```

> 若站点文件名用 `-` 而不是 `_` 分隔（如 `9702-m26-er.pdf`），把 `core/fetcher.py` 里 `_stem_parts` 的 `split("_")` 改成 `re.split(r"[_\-]", stem)` 即可。

---

## 目录结构

```
pdf_downloader/
├── main.py                 # 入口
├── config.py               # 全局配置（UA/超时/白名单/归档规则）
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── core/
│   ├── __init__.py
│   ├── fetcher.py          # 抓链接 + 链接归一化 + 白名单过滤
│   ├── downloader.py       # 下载（重试/去重/文件名净化/原子写入）
│   └── organizer.py        # 按试卷类型归档
└── gui/
    ├── __init__.py
    └── main_frame.py       # 主窗口（BoxSizer 布局 + 线程 + 日志 + 进度）
```

---

## 在 VS Code 中开发

### 打开项目与选择解释器

1. **以文件夹形式打开项目**：不要只打开单个 `.py` 文件。在终端执行 `cd 项目目录` 然后 `code .`，或通过 VS Code 菜单 `文件 > 打开文件夹` 打开整个 `pdf_downloader` 目录。
2. **选择 Python 解释器**：按 `Ctrl+Shift+P`，输入 `Python: Select Interpreter`，选择你为项目创建的虚拟环境（推荐 venv），避免依赖冲突。
3. **安装依赖**：在 VS Code 集成终端（``Ctrl+` ``）中确认虚拟环境已激活，然后执行 `pip install -r requirements.txt`。

### 运行

打开入口文件 `main.py`，三种运行方式：

- **终端命令（最稳）**：在集成终端执行 `python main.py`
- **右上角绿色三角**：适合快速测试，但对复杂项目结构支持有限
- **快捷键 `Ctrl+F5`**：不调试直接运行当前文件

### 调试

调试能设置断点、查看变量，对 GUI 事件处理流程排查非常有帮助。

1. 点击左侧活动栏的 **"运行与调试"** 图标，或按 `Ctrl+Shift+D`
2. 点击 **"创建 launch.json 文件"**，选择 **Python Debugger** → **Python File**
3. 在 `.vscode/launch.json` 中把 `program` 指向入口文件，并加上 `"console": "integratedTerminal"`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "运行 PDF 下载器",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

配置好后按 `F5` 启动调试，在代码行号旁点击设置断点。

---

## 打包为可执行文件

想让程序在没有 Python 环境的电脑上运行，用 **PyInstaller** 打包：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PDF下载器 main.py
```

- `--onefile`：打包成单个可执行文件
- `--windowed`（或 `-w`）：**GUI 程序必须加**，运行时不显示黑色命令行窗口
- `--name`：指定生成的应用名称

生成的可执行文件在 **`dist/`** 目录下。若运行时提示找不到 wx 模块，改用：

```bash
pyinstaller --onefile --windowed --collect-all wx --name PDF下载器 main.py
```

| 目的 | 推荐方式 | 关键操作 |
|---|---|---|
| 快速运行测试 | 终端 `python main.py` | 最直接，环境变量和相对路径最明确 |
| 排查 Bug | `launch.json` 调试（F5） | 可设断点、看调用栈，`console` 设为 `integratedTerminal` |
| 发给别人用 | PyInstaller 打包 | `--onefile --windowed`，GUI 必备 `--windowed` |

---

## 上传到 GitHub

### 1. 上传前清理

```bash
# 在项目根目录执行
rm -rf __pycache__ core/__pycache__ gui/__pycache__
rm -rf downloads          # 下载的 PDF 不要提交
rm -f  *.part *.log       # 下载临时文件和日志
```

> ⚠️ 如果任何文件里写过 Dropbox token、API key，**务必先删除**。Git 一旦提交，历史里会永久留存，届时需要 `git filter-repo` 才能彻底清掉。

### 2. 补齐三个元文件

**`.gitignore`**：

```gitignore
# ---- Python ----
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/

# ---- 虚拟环境 ----
venv/
.venv/
env/

# ---- 编辑器 ----
.vscode/
.idea/
*.swp

# ---- 本项目产物 ----
downloads/
*.pdf
*.part
*.log

# ---- 系统 ----
.DS_Store
Thumbs.db
```

**`LICENSE`**（MIT）：

```
MIT License

Copyright (c) 2026 赵三金

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 常见问题

**Q：扫描到 0 个链接？**
A：页面可能是 JS 动态渲染，`requests` 拿不到真实 DOM。可先用浏览器打开页面 → F12 → Network → 确认 PDF 链接出现在初始 HTML 中；若没有，需要改用 Selenium / Playwright 方案。

**Q：某些链接 404？**
A：papacambridge 的 `download_file.php?files=...` 常返回 404，本项目已自动解析成内层直链，正常下载。若仍 404，说明源站本身文件缺失。

**Q：文件名出现 `%20` 或非法字符？**
A：`downloader.filename_from_url()` 已做 `unquote` + 非法字符替换，Windows 上也能正常保存。

**Q：想暂停 / 并发下载？**
A：当前为单线程顺序下载（每文件间隔 `DOWNLOAD_DELAY` 秒，避免被封）。如需并发，可把 `download_many` 改为 `concurrent.futures.ThreadPoolExecutor`，但请控制并发数并对站点友好。

**Q：`ALLOWED_KEYWORDS` 怎么调？**
A：见 [配置说明](#配置说明)。留空元组 `()` 表示不过滤全部下载。

**Q：为什么程序里没有 `papacambridge` 专用按钮？**
A：抓取层已对 `download_file.php?files=...` 做通用解析，任何含此类链接的页面都能处理，无需专用入口。

---

## 免责声明

本项目仅供**个人学习与离线备份**使用。请遵守目标网站的 `robots.txt` 与服务条款，控制请求频率。下载内容的版权归原机构所有，请勿用于商业传播。因使用本工具产生的任何法律问题，作者不承担责任。

---

## 致谢

- 界面基于 [wxPython](https://wxpython.org/)
- 解析基于 [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) 与 [Requests](https://requests.readthedocs.io/)

---

## License

[MIT](LICENSE)