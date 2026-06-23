# AcademicReviewer

学术竞赛论文智能评审系统 —— 基于多 Agent 协作的自动化论文评审工具，支持 ISEF、STS、John Locke、HiMCM 等主流学术竞赛。

## 功能概览

- **多维度评审** —— 评审标准解析、结构逻辑、论证证据、语言风格、学术诚信 5 个 Agent 并行协作
- **多竞赛适配** —— 内置 11 个竞赛评审规则，**按类型差异化适配**：科研型重证据权重、思辨型重结构权重、商科型重框架应用
- **教练型反馈** —— 缺→问→改三步法，逐段标注原文，给出可操作的改写方案
- **多格式解析** —— 支持 TXT / PDF / DOCX 文档上传
- **Web 界面** —— Gradio 图形界面，7 个功能 Tab（评审/历史/状态/校准/看板/赛事管理/教师审核）
- **Word 批注导出** —— 评审结果一键导出为 .docx，原文 + Word 批注 + 内联语法修正
- **校准引擎** —— 对比获奖/非获奖文章，自动提取特征差异，**按竞赛类型切换特征集**（科研 21 特征/思辨 15 特征）
- **多 LLM 支持** —— DeepSeek / OpenAI / Gemini / GLM 可切换
- **团队协作** —— 多实例上报 → 中央服务器汇总 → 管理看板
- **安全加固** —— Bearer Token 认证（可选）、文件大小/类型限制、隐私声明

## 环境要求

| 项目 | 最低要求 | 说明 |
|------|---------|------|
| **操作系统** | Windows 10+ / macOS 12+ / Ubuntu 22.04+ | 推荐 Windows 11 或 macOS 14+ |
| **Python** | >= 3.10（推荐 3.11/3.12） | [python.org/downloads](https://www.python.org/downloads/) |
| **磁盘空间** | >= 2 GB 可用 | venv ~800MB + 其他文件 |
| **网络** | 需要 | pip install 首次下载依赖 + LLM API 调用 |
| **LLM API Key** | 至少一个 | DeepSeek（推荐，最便宜）/ OpenAI / Gemini / GLM |
| **Git / 压缩包** | 任一 | clone 或直接下载 ZIP |

> 无需 GPU、Docker、或外部数据库。所有数据存本地 SQLite + ChromaDB。

### ⚠️ 首次安装前必读

**如果你是竞赛指导老师（非技术背景），以下是同事常卡住的几个点：**

1. **装 Python 时一定要勾选 "Add Python to PATH"**（安装界面的一个复选框）—— 不勾选会导致系统找不到 `python` 命令，安装脚本报错。

2. **验证 Python 是否装好**：打开终端（Windows 按 `Win+R`，输入 `cmd`，回车），输入 `python --version`，应该显示 `Python 3.x.x`。如果显示"不是内部或外部命令"，说明没勾选 PATH，需要重装或手动添加环境变量。

3. **pip 安装依赖需要网络**：首次安装会从 PyPI 下载约 400MB 的包。如果你在公司网络、有防火墙或代理，可能需要先配置代理：
   ```bash
   set HTTPS_PROXY=http://你的代理地址:端口  # Windows CMD
   $env:HTTPS_PROXY="http://你的代理地址:端口"  # PowerShell
   ```

4. **API Key 是必填项**：系统依赖 LLM 进行评审，没有 API Key（如 DeepSeek 的 `sk-xxx` 格式 Key）系统能启动但无法运行评审。至少配置一个服务商。

## 安装与启动

### Windows

```bash
# 1. 获取代码（二选一）
git clone https://github.com/gzhuai/AcademicReviewer.git   # 命令行
# 或访问 GitHub 页面 → Code → Download ZIP → 解压       # 无需 Git

# 2. 进入项目目录
cd AcademicReviewer

# 3. 一键安装（双击 scripts\install.bat 或在终端运行）
scripts\install.bat
# 安装过程：检测 Python → 创建虚拟环境 → 安装依赖(~5分钟) → 复制配置文件 → 创建数据目录
# 安装完成后会询问是否编辑 .env，输入 y 打开记事本

# 4. 编辑 .env 文件，填入 API Key（如果安装时跳过了）
notepad .env

# 5. 启动系统（双击 scripts\start_all.bat）
scripts\start_all.bat
```

### macOS / Linux

```bash
# 1. 获取代码
git clone https://github.com/gzhuai/AcademicReviewer.git
cd AcademicReviewer

# 2. 一键安装
bash scripts/install.sh

# 3. 编辑 .env 文件，填入 API Key
nano .env

# 4. 启动系统
bash scripts/start_all.sh
```

启动后浏览器访问 **http://127.0.0.1:7860** 即可使用。

### 手动安装（如果一键脚本失败）

```bash
# Windows
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env
python run.py                    # 终端 1：后端
python app/gradio_app.py         # 终端 2：前端

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py                    # 终端 1：后端
python app/gradio_app.py         # 终端 2：前端

启动后浏览器访问 **http://127.0.0.1:7860** 即可使用。

## 配置说明

复制 `.env.example` 为 `.env`，填入至少一个 LLM API Key：

```env
# 必填项（至少一个）→ 获取地址见 .env.example 中的注释
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
GLM_API_KEY=xxx

# 使用哪个模型（默认 deepseek，推荐性价比最高）
LLM_PROVIDER=deepseek
```

> **如何获取 API Key？** DeepSeek 最便宜且国内可直接注册（[platform.deepseek.com](https://platform.deepseek.com)）。其他选项：OpenAI 需海外信用卡、Gemini 免费额度较低、GLM 国内可注册。

## 常见安装问题

| 症状 | 原因 | 解决 |
|------|------|------|
| `'python' 不是内部或外部命令` | Python 未安装或未勾选 PATH | 重装 Python，**勾选 "Add Python to PATH"** |
| `powershell: command not found` | Windows 精简版系统 | 手动安装步骤见上方「手动安装」 |
| `pip install` 报网络错误 | 代理/防火墙拦截 PyPI | 配置代理（见上方首次安装前必读） |
| `No module named 'venv'` | Python 安装不完整 | 重装 Python，确保勾选 pip 和 venv |
| 依赖安装一半失败 | C 盘空间不足 | 清理空间，需要 ~2GB |
| `start_all.sh` 无反应 | SSH/远程服务器（无 GUI） | 已自动回退到后台进程模式 |
| 启动后访问 7860 无响应 | 后端未就绪 | 等 5-10 秒刷新，或查看终端日志 |

## 使用指南

- **教师用户**: [docs/教师使用指南.md](docs/教师使用指南.md) — 从零到评审的完整教程
- **图文版**: [docs/使用指南.html](docs/使用指南.html) — 含 UI 界面说明
- **开发者**: [AI_HANDOFF.md](AI_HANDOFF.md) + [CONTRIBUTING.md](CONTRIBUTING.md)

## 团队协作：数据集中汇总

系统支持「本地运行 + 中央汇总」架构，让所有同事的使用数据和校准结果自动归集到你这里。

### 架构说明

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│ 同事 A    │   │ 同事 B    │   │ 同事 C    │
│ 本地运行  │   │ 本地运行  │   │ 本地运行  │
└────┬─────┘   └────┬─────┘   └────┬─────┘
     │  自动上报     │  自动上报     │  自动上报
     └───────────────┼───────────────┘
                     ▼
            ┌────────────────┐
            │  中央服务器      │
            │  (你部署的实例)  │
            │  管理看板 → 汇总  │
            └────────────────┘
```

### 部署步骤

**1. 你（管理员）部署中央服务器**

找一台云服务器或有公网 IP 的机器，安装并启动系统。在 `.env` 中保持 `SYNC_SERVER_URL=` 为空（这是中央服务器本身），设置 `HOST=0.0.0.0` 使其对外可访问。

**2. 同事配置本地实例**

在同事的 `.env` 中添加：

```env
SYNC_SERVER_URL=http://你的服务器IP:8000
INSTANCE_NAME=张三
```

**3. 开启后自动生效**

同事每次提交评审或运行校准，结果会自动上报到你的中央服务器。打开浏览器访问 `http://你的服务器IP:7860` → **「管理看板」** 即可查看所有汇总数据，无需同事做任何额外操作。

### 赛事别名系统

同事在提交评审时可能会用不同方式称呼同一个赛事（如 `John Locke` / `john locke` / `约翰洛克` / `JL`）。系统内置了**别名归一化引擎**，会自动将各种称呼映射为标准名称。你可以在**「赛事管理」**页面添加/编辑别名。

### 赛事管理（图形界面）

在 Gradio 界面的 **「赛事管理」** 标签页中，你可以：
- 📋 查看当前所有已注册的赛事
- ➕ 添加新赛事（填写名称、选择类型和配置模板、设置别名）
- ✏️ 编辑已有赛事（输入已存在的赛事名称即为编辑）
- 🗑️ 删除不再需要的赛事

修改立即生效，旧配置自动备份到 `competition_registry.json.bak`。无需手动编辑 JSON 文件。

### 安全说明

- **认证**：可选 Bearer Token 认证。在 `.env` 中设置 `API_TOKEN=your-secret` 启用。不设则跳过（向后兼容）。
- **文件限制**：上传文件限制 50MB，仅允许 .txt/.md/.pdf/.docx 格式。
- **隐私声明**：提交的论文全文将发送到您选择的 LLM 提供商（DeepSeek / OpenAI / Gemini / GLM）的 API 进行评审处理。请勿上传包含身份证号、联系方式等个人敏感信息的学生作品。评审结果仅在本地 SQLite 数据库存储，不上传至第三方。团队协作模式下，评审数据经内网同步到中央服务器，传输内容与上述相同。

## 项目结构

```
AcademicReviewer/
├── app/                # 核心应用
│   ├── agents/         # 5 个评审 Agent
│   ├── calibration/    # 校准引擎（特征提取、效应量分析）
│   ├── llm/            # LLM 适配器（DeepSeek/OpenAI/Gemini/GLM）
│   ├── models/         # 数据库模型
│   └── utils/          # 工具（文档解析、引文检查、向量检索）
├── cli/                # 命令行入口
├── configs/            # 竞赛规则、评分标准、样式指南
├── prompts/            # Agent 提示词模板
├── scripts/            # 安装与启动脚本
├── tests/              # 测试用例
└── docs/               # 架构文档与使用指南
```

## License

MIT

## 开发者文档

面向 AI 编程助手（Claude Code / Codex / Copilot 等）的接手指南，含完整模块地图、API 参考、编码规范和常见陷阱：[AI_HANDOFF.md](AI_HANDOFF.md)
