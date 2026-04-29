# GBrain 企业培训智能助手

> 基于 AI 的企业培训管理平台，支持智能课件生成、场景化学习、多模式考核

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 定位

GBrain 是一款面向企业的 **AI 培训管理平台**，帮助企业实现：
- 智能化学课件生成
- 场景驱动的互动学习
- 多维度考核评估
- 员工学习进度追踪

## 核心功能

### 1. 智能课件生成
- 支持 PDF、DOCX、PPTX、TXT、MD 格式文档上传
- 自动转换为 Markdown 格式
- 基于知识库内容 AI 生成培训课件
- 智能提取课程大纲和知识点

### 2. 三大学习模式

| 模式 | 说明 |
|------|------|
| **探索模式** | 自由问答，解答培训相关疑问 |
| **场景学习** | 工作场景驱动的互动学习 |
| **考核模式** | 单选/判断/简答题测验 |

### 3. 学习助手
- 引导式学习流程
- 实时反馈与评分
- 薄弱点智能识别
- 学习进度追踪

### 4. 管理后台
- 培训任务创建与管理
- 员工学习进度看板
- 考核成绩统计
- 知识库管理

## 快速开始

### 环境要求
- Python 3.10+
- MiniMax API Key（用于 AI 生成）
- 千问 API Key（用于 Embedding）

### 安装依赖

```bash
cd /Users/forxia/gbrain
source .venv/bin/activate
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件：

```env
MINIMAX_API_KEY=your_minimax_api_key
QWEN_API_KEY=your_qwen_api_key
```

### 启动服务

```bash
python run_web.py
```

访问 http://localhost:8080/training

## 项目结构

```
gbrain/
├── gbrain/
│   ├── plugins/training/           # 培训插件
│   │   ├── learning_agent.py      # 学习助手核心
│   │   ├── chat_engine.py        # 对话引擎
│   │   ├── doc_converter.py      # 文档转换器
│   │   ├── course_gen.py         # 课件生成器
│   │   ├── service.py            # 培训服务
│   │   └── skills/              # 学习技能
│   │       ├── exploration/      # 探索模式
│   │       ├── scene_learning/    # 场景学习
│   │       └── quiz/             # 考核模式
│   └── web/                      # Web 服务
│       ├── app.py               # FastAPI 应用
│       ├── routes.py            # 路由定义
│       └── templates/           # HTML 模板
├── data/                         # 数据存储
│   ├── gbrain.db               # SQLite 数据库
│   └── uploads/                # 上传文件
└── run_web.py                   # 启动脚本
```

## 架构设计

### 学习流程

```
文档上传 → 转换为 Markdown → AI 生成课件 → 知识库存储
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
              探索模式          场景学习            考核模式
                    ↓                 ↓                 ↓
              自由问答         场景互动学习      测验评分
                    └─────────────────┴─────────────────┘
                                      ↓
                               学习进度追踪
```

### 考核评分机制

- 学习得分占 30%（场景学习表现）
- 考核得分占 70%（测验成绩）
- 70 分为及格线

## API 接口

### Web 页面
- `GET /training` - 培训首页
- `GET /training/tasks` - 任务列表
- `GET /training/task/{id}` - 任务详情
- `GET /training/learn/{progress_id}` - 学习页面
- `GET /training/dashboard` - 数据看板
- `GET /training/admin` - 管理后台

### API 端点
- `POST /api/training/admin/course/generate` - AI 生成课件
- `POST /api/training/admin/upload` - 上传文档
- `POST /api/training/admin/task` - 创建任务
- `POST /api/training/learn/{task_id}/chat` - 学习对话（SSE 流式）

## 技术栈

- **Web 框架:** FastAPI + Uvicorn
- **模板引擎:** Jinja2
- **数据库:** SQLite
- **AI 模型:** MiniMax API
- **向量搜索:** 千问 Embedding API
- **文档处理:** pdfplumber, python-docx, python-pptx

## 适用场景

✅ **适合:**
- 企业内部培训管理
- 新员工入职培训
- 技能提升培训
- 合规与制度培训

❌ **不适合:**
- 实时视频培训
- 多人协作编辑
- 复杂权限管理
