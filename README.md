# AcademicReviewer

学术竞赛论文智能评审系统 —— 基于多 Agent 协作的自动化论文评审工具，支持 ISEF、STS、John Locke、HiMCM 等主流学术竞赛。

## 功能概览

- **多维度评审** —— 评审标准解析、结构逻辑、论证证据、语言风格、学术诚信 5 个 Agent 并行协作
- **多竞赛适配** —— 内置 10+ 竞赛评审规则与标准（ISEF / STS / John Locke / HiMCM / NHD 等）
- **多格式解析** —— 支持 TXT / PDF / DOCX 文档上传
- **Web 界面** —— Gradio 图形界面，一键提交评审、查看历史记录
- **校准引擎** —— 对比获奖/非获奖文章，自动提取特征差异，生成规则优化建议
- **多 LLM 支持** —— DeepSeek / OpenAI / Gemini / GLM 可切换

## 环境要求

- **Python** >= 3.10
- 至少一个 LLM API Key（DeepSeek / OpenAI / Gemini / GLM 任一）

## 安装与启动

### Windows

```bash
# 1. Clone 仓库
git clone https://github.com/gzhuai/AcademicReviewer.git
cd AcademicReviewer

# 2. 一键安装（自动创建虚拟环境并安装依赖）
scripts\install.bat

# 3. 编辑 .env 文件，填入 API Key
notepad .env

# 4. 启动系统
scripts\start_all.bat
```

### macOS / Linux

```bash
# 1. Clone 仓库
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

## 配置说明

复制 `.env.example` 为 `.env`，填入至少一个 LLM API Key：

```env
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
GLM_API_KEY=xxx
LLM_PROVIDER=deepseek
```

## 使用指南

详细使用说明请参阅：[docs/使用指南.html](docs/使用指南.html)

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
