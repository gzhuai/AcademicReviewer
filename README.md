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
