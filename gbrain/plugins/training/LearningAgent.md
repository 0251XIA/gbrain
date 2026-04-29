# LearningAgent 学习助手体系

## 一、架构概览

```
LearningAgent（总协调器）
├── ExplorationEngine（探索引擎）
├── SceneLearningEngine（场景学习引擎）
└── QuizEngine（考核引擎）
```

## 二、三种模式

| 模式 | 引擎 | 特点 | 触发词 |
|------|------|------|--------|
| **探索模式** | ExplorationEngine | 自由问答，不限制问题格式，基于课件内容智能回答 | 探索、问答、提问、探索模式 |
| **学习模式** | SceneLearningEngine | 场景链引导式学习，AI评估回答，4个场景循序渐进 | 学习、场景学习、开始学习、学习模式 |
| **考核模式** | QuizEngine | 选择/判断/简答题测验，实时评分，不可重考 | 考核、考试、测验、考核模式 |

## 三、状态流转

```
exploration ←→ learning —→ ready_to_quiz —→ quiz —→ completed
                                        ↓
                                      failed
```

**6个阶段**：`exploration` | `learning` | `ready_to_quiz` | `quiz` | `completed` | `failed`

## 四、学习模式流程

1. 展示工作场景（从场景链读取）
2. 学员思考并输入回答
3. AI评估回答，给出反馈和正确答案
4. 记录薄弱知识点
5. 进入下一场景（重复4个场景）
6. 学习完成 → 进入 `ready_to_quiz` 阶段

## 五、考核模式

- **题目来源**：基于场景学习薄弱点 + 场景链自动生成7道考核题
- **题型**：选择题、判断题、简答题
- **评分**：学习得分(70%) + 考核得分(30%)，70分及格
- **特点**：考核只有一次机会，未通过需重新学习

## 六、API 接口

```
POST /api/training/learn/{task_id}/chat
  ├── action=start      → 初始化会话，返回欢迎消息+进度
  ├── action=status    → 获取当前进度
  └── action=chat       → 处理对话消息（SSE流式返回）
```

## 七、关键设计

- **默认进入学习模式**，每次 action=start 重置状态
- 模式切换：检测到关键词（探索/学习/考核）立即切换，不做问题回答
- 探索模式切换时：如果带了问题内容则回答问题，否则只显示欢迎消息
- SSE流式响应，支持实时反馈
