# AI 学习引导助手实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 AI 学习引导助手，支持通过对话引导员工学习课件内容，包含主动导览、智能问答、学习测验功能。

**Architecture:** 基于现有 gbrain 培训模块，新增 LearningAgent 类处理对话逻辑，使用 SSE 实现流式响应，前端新增 AI 对话面板。

**Tech Stack:** Python 3.10+, FastAPI, SSE, MiniMax API (复用 course_gen.py 的 call_llm)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `gbrain/plugins/training/learning_agent.py` | 新建 | LearningAgent 主类，状态机控制 |
| `gbrain/plugins/training/chat_engine.py` | 新建 | 对话引擎，处理各阶段对话逻辑 |
| `gbrain/plugins/training/__init__.py` | 修改 | 导出 LearningAgent |
| `gbrain/web/routes.py` | 修改 | 新增 SSE 对话接口 |
| `gbrain/web/templates/training/learn.html` | 修改 | AI 对话 UI |

---

## Task 1: 创建 ChatEngine 对话引擎

**Files:**
- Create: `gbrain/plugins/training/chat_engine.py`
- Test: (手动测试)

- [ ] **Step 1: 创建 chat_engine.py 基础结构**

```python
"""
对话引擎 - 处理 AI 学习引导的各阶段对话逻辑
"""

from typing import Optional
import json


class ChatEngine:
    """对话引擎基类"""

    SYSTEM_PROMPT = """你是一个友善的学习教练，风格特点：
    - 鼓励式引导，语气温暖友善
    - 穿插案例和实践建议
    - 轻松氛围，不给压力
    - 用"咱们"、"我们"等人称
    - 适当使用 emoji 增加亲和力

    课件内容：
    {content}

    当前阶段：{stage}
    """

    def __init__(self, content: str, stage: str = "tour"):
        self.content = content
        self.stage = stage
        self.messages = []

    def build_system_prompt(self) -> str:
        """构建系统提示词"""
        return self.SYSTEM_PROMPT.format(content=self.content[:8000], stage=self.stage)

    def add_message(self, role: str, content: str):
        """添加对话历史"""
        self.messages.append({"role": role, "content": content})

    async def chat(self, user_message: str) -> str:
        """处理用户消息，返回 AI 回复"""
        raise NotImplementedError


class TourEngine(ChatEngine):
    """导览引擎 - 引导学习课件"""

    def __init__(self, content: str):
        super().__init__(content, "tour")
        self.current_section = 0
        self.sections = self._split_content(content)

    def _split_content(self, content: str) -> list:
        """将课件内容分段"""
        import re
        # 按 ## 标题分割章节
        parts = re.split(r'^##\s+', content, flags=re.MULTILINE)
        sections = []
        for i, part in enumerate(parts[1:], 1):  # 跳过第一个空部分
            lines = part.strip().split('\n', 1)
            title = lines[0].strip() if lines else f"第{i}章"
            body = lines[1] if len(lines) > 1 else ""
            sections.append({"title": title, "body": body[:500]})
        return sections if sections else [{"title": "课件内容", "body": content[:500]}]

    def get_section_intro(self) -> str:
        """获取当前章节的介绍"""
        if self.current_section >= len(self.sections):
            return None
        s = self.sections[self.current_section]
        return f"咱们来看看【{s['title']}】：{s['body'][:200]}..."

    def advance_section(self) -> bool:
        """推进到下一章节"""
        self.current_section += 1
        return self.current_section < len(self.sections)

    async def chat(self, user_message: str) -> str:
        """处理导览阶段的对话"""
        from gbrain.plugins.training.course_gen import call_llm

        self.add_message("user", user_message)

        # 判断员工是否理解当前内容
        check_prompt = f"""请判断员工的下述回答是否体现了对当前章节内容的理解：

        章节：{self.sections[self.current_section]['title']}
        员工回答：{user_message}

        请用 JSON 格式回复：
        {{"understood": true/false, "feedback": "简短评价（1-2句话）"}}
        """

        check_resp = call_llm(check_prompt, "")
        try:
            result = json.loads(check_resp)
            feedback = result.get("feedback", "")
        except:
            feedback = "好的，我听到了你的想法！"

        # 推进章节或进入问答
        if self.advance_section():
            next_intro = self.get_section_intro()
            reply = f"{feedback}\n\n太棒了！{next_intro}\n\n学完之后，可以跟我说说你的理解哦~"
        else:
            reply = f"{feedback}\n\n哇，你已经学完整个课件了！有什么想问的，或者想说"开始测验"吗？"
            self.stage = "q_and_a"

        self.add_message("assistant", reply)
        return reply


class QAEngine(ChatEngine):
    """问答引擎 - 回答员工问题"""

    def __init__(self, content: str):
        super().__init__(content, "q_and_a")

    async def chat(self, user_message: str) -> str:
        """处理问答"""
        from gbrain.plugins.training.course_gen import call_llm

        self.add_message("user", user_message)

        qa_prompt = f"""基于以下课件内容，回答员工的问题。用友善教练的风格。

        课件内容：
        {self.content[:8000]}

        员工问题：{user_message}

        回答要求：
        - 结合课件内容具体回答
        - 适当举例说明
        - 鼓励式语气
        - 1-3句话即可
        """

        reply = call_llm(qa_prompt, self.build_system_prompt())
        self.add_message("assistant", reply)
        return reply


class QuizEngine(ChatEngine):
    """测验引擎 - 生成测验题目"""

    def __init__(self, content: str, num_quiz: int = 3):
        super().__init__(content, "quiz")
        self.num_quiz = num_quiz
        self.current_quiz = 0
        self.answers = []
        self.quiz_items = self._generate_quiz_items()

    def _generate_quiz_items(self) -> list:
        """生成测验题"""
        from gbrain.plugins.training.course_gen import call_llm

        prompt = f"""基于以下课件内容，生成 {self.num_quiz} 道开放式测验题：

        课件内容：
        {self.content[:6000]}

        要求：
        - 每道题考察一个核心知识点
        - 题目开放性，让员工自由发挥
        - 3-5句话一道题

        输出 JSON 数组格式：
        [
          {{"id": "q1", "question": "题目内容"}},
          ...
        ]
        """

        resp = call_llm(prompt, "")
        # 解析 JSON
        try:
            items = json.loads(resp)
        except:
            items = [{"id": f"q{i+1}", "question": f"请说明你对第{i+1}个知识点的理解"} for i in range(self.num_quiz)]

        return items[:self.num_quiz]

    def get_current_question(self) -> dict:
        """获取当前题目"""
        if self.current_quiz >= len(self.quiz_items):
            return None
        return self.quiz_items[self.current_quiz]

    async def chat(self, user_message: str) -> str:
        """处理测验回答"""
        from gbrain.plugins.training.course_gen import call_llm

        self.add_message("user", user_message)

        # 评估回答
        current_q = self.get_current_question()
        eval_prompt = f"""评估员工对这道题的回答：

        题目：{current_q['question']}
        员工回答：{user_message}

        请用 JSON 格式回复：
        {{"quality": "good/ok/poor", "feedback": "1句话点评"}}
        """

        eval_resp = call_llm(eval_prompt, "")
        try:
            result = json.loads(eval_resp)
            feedback = result.get("feedback", "回答得很好！")
        except:
            feedback = "好的，我听到了！"

        self.answers.append(user_message)
        self.current_quiz += 1

        # 是否还有下一题
        next_q = self.get_current_question()
        if next_q:
            return f"{feedback}\n\n现在来第 {self.current_quiz + 1} 题：\n\n{next_q['question']}"
        else:
            self.stage = "summary"
            return f"{feedback}\n\n测验完成！你回答得很棒。现在我来帮你总结一下今天的学习~"
```

- [ ] **Step 2: Commit**

```bash
git add gbrain/plugins/training/chat_engine.py
git commit -m "feat: add chat engine with TourEngine, QAEngine, QuizEngine"
```

---

## Task 2: 创建 LearningAgent 主类

**Files:**
- Create: `gbrain/plugins/training/learning_agent.py`
- Modify: `gbrain/plugins/training/__init__.py`
- Test: (手动测试)

- [ ] **Step 1: 创建 learning_agent.py**

```python
"""
Learning Agent - AI 学习引导助手主类
"""

from typing import Optional, AsyncIterator
from .chat_engine import TourEngine, QAEngine, QuizEngine


class LearningAgent:
    """
    学习引导 Agent

    状态机：
    tour -> q_and_a -> quiz -> summary -> completed

    tour: 导览阶段，AI 分段引导学习
    q_and_a: 问答阶段，员工自由提问
    quiz: 测验阶段，AI 出题检验
    summary: 总结阶段，AI 回顾要点
    completed: 完成
    """

    STAGES = ["tour", "q_and_a", "quiz", "summary", "completed"]

    def __init__(self, task_id: str, content: str, task_title: str = ""):
        self.task_id = task_id
        self.content = content
        self.task_title = task_title
        self.stage = "tour"
        self.context = []

        # 初始化各阶段引擎
        self.tour_engine = TourEngine(content)
        self.qa_engine = QAEngine(content)
        self.quiz_engine = QuizEngine(content, num_quiz=3)

        # 当前引擎
        self._engine = self.tour_engine

    def set_stage(self, stage: str):
        """切换阶段"""
        if stage not in self.STAGES:
            return
        self.stage = stage
        if stage == "tour":
            self._engine = self.tour_engine
        elif stage == "q_and_a":
            self._engine = self.qa_engine
        elif stage in ("quiz", "summary"):
            self._engine = self.quiz_engine

    async def chat(self, message: str) -> AsyncIterator[dict]:
        """
        处理对话，返回流式响应
        """
        # 处理特殊指令
        if message.strip() in ("开始测验", "我想测验", "测验"):
            if self.stage in ("tour", "q_and_a"):
                self.set_stage("quiz")
                first_q = self.quiz_engine.get_current_question()
                yield {
                    "type": "quiz",
                    "content": f"好的！咱们开始测验吧~\n\n第1题：{first_q['question']}",
                    "metadata": {"stage": self.stage, "question_id": first_q['id']}
                }
                return

        # 正常对话
        reply = await self._engine.chat(message)

        # 构建响应
        response = {
            "type": "message",
            "content": reply,
            "metadata": {
                "stage": self.stage,
                "engine": self._engine.__class__.__name__
            }
        }

        # 检查阶段变化
        if self.stage == "tour" and self.tour_engine.stage == "q_and_a":
            self.set_stage("q_and_a")
            response["type"] = "tour_end"
            response["metadata"]["next_stage"] = "q_and_a"

        if self.stage == "quiz" and self.quiz_engine.stage == "summary":
            self.set_stage("summary")
            response["type"] = "quiz_end"

        yield response

    def get_welcome_message(self) -> str:
        """获取欢迎消息"""
        return f"""👋 你好！我是你的学习助手！

欢迎学习《{self.task_title}》，咱们开始吧~

我会带你一步步了解课程内容，有任何问题随时问我。准备好了吗？"""

    def get_progress(self) -> dict:
        """获取学习进度"""
        return {
            "stage": self.stage,
            "task_id": self.task_id,
            "quiz_count": self.quiz_engine.current_quiz,
            "quiz_total": len(self.quiz_engine.quiz_items)
        }
```

- [ ] **Step 2: 修改 __init__.py 导出**

```python
from .learning_agent import LearningAgent
from .chat_engine import TourEngine, QAEngine, QuizEngine

__all__ = ["LearningAgent", "TourEngine", "QAEngine", "QuizEngine"]
```

- [ ] **Step 3: Commit**

```bash
git add gbrain/plugins/training/learning_agent.py gbrain/plugins/training/__init__.py
git commit -m "feat: add LearningAgent class for guided learning"
```

---

## Task 3: 添加 SSE 对话接口

**Files:**
- Modify: `gbrain/web/routes.py`

- [ ] **Step 1: 添加 SSE 路由**

在 routes.py 新增：

```python
from gbrain.plugins.training.learning_agent import LearningAgent

# 存储当前学习会话
learning_sessions = {}

@app.post("/api/training/learn/{task_id}/chat")
async def chat(task_id: str, request: Request):
    """SSE 流式对话接口"""
    try:
        body = await request.body()
        data = json.loads(body)
        message = data.get("message", "")
        action = data.get("action", "chat")  # chat | start | status
    except:
        message = ""
        action = "chat"

    service = get_training_service()

    # start: 初始化学习会话
    if action == "start" or task_id not in learning_sessions:
        task = service.get_task(task_id)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        agent = LearningAgent(
            task_id=task_id,
            content=task.content,
            task_title=task.title
        )
        learning_sessions[task_id] = agent

        return JSONResponse({
            "type": "start",
            "welcome": agent.get_welcome_message(),
            "progress": agent.get_progress()
        })

    # status: 获取当前进度
    if action == "status":
        agent = learning_sessions.get(task_id)
        if not agent:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        return JSONResponse(agent.get_progress())

    # chat: 处理对话
    agent = learning_sessions.get(task_id)
    if not agent:
        return JSONResponse({"error": "Session not found, please start first"}, status_code=400)

    # 流式返回
    async def event_generator():
        try:
            async for response in agent.chat(message):
                yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

注意：需要在 routes.py 顶部添加 StreamingResponse 导入：
```python
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
```

- [ ] **Step 2: Commit**

```bash
git add gbrain/web/routes.py
git commit -m "feat: add SSE chat endpoint for learning agent"
```

---

## Task 4: 前端 AI 对话 UI

**Files:**
- Modify: `gbrain/web/templates/training/learn.html`

- [ ] **Step 1: 修改 learn.html 布局**

将现有 learn.html 改造为双栏布局，左侧课件，右侧 AI 对话：

```html
{% block extra_style %}
{{ super() }}
<style>
.learn-layout {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
}
@media (max-width: 1024px) {
    .learn-layout {
        grid-template-columns: 1fr;
    }
}
.course-main {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chat-panel {
    background: white;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
    position: sticky;
    top: 1rem;
}
.chat-header {
    padding: 1rem;
    border-bottom: 1px solid #eee;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}
.chat-message {
    margin-bottom: 1rem;
    animation: fadeIn 0.3s ease;
}
.chat-message.ai {
    text-align: left;
}
.chat-message.user {
    text-align: right;
}
.chat-message .bubble {
    display: inline-block;
    padding: 0.75rem 1rem;
    border-radius: 12px;
    max-width: 85%;
    line-height: 1.5;
}
.chat-message.ai .bubble {
    background: #f8f9fa;
    border-bottom-left-radius: 4px;
}
.chat-message.user .bubble {
    background: #4361ee;
    color: white;
    border-bottom-right-radius: 4px;
}
.chat-input-area {
    padding: 1rem;
    border-top: 1px solid #eee;
    display: flex;
    gap: 0.5rem;
}
.chat-input {
    flex: 1;
    padding: 0.75rem 1rem;
    border: 1px solid #ddd;
    border-radius: 24px;
    outline: none;
}
.chat-input:focus {
    border-color: #4361ee;
}
.chat-send {
    padding: 0.5rem 1rem;
    background: #4361ee;
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
}
.stage-indicator {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: #e8f4fd;
    color: #4361ee;
    border-radius: 12px;
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
{% endblock %}
```

- [ ] **Step 2: 修改 HTML 结构**

```html
{% block content %}
<div class="learn-layout">
    <div class="course-main">
        <div class="learn-progress" style="margin-bottom: 1rem;">
            <div>
                <div class="title" id="task-title">加载中...</div>
                <span class="stage-indicator" id="stage-indicator">导览阶段</span>
            </div>
        </div>
        <div class="course-body" id="course-content">
            <p style="color: #999;">加载课件内容...</p>
        </div>
    </div>

    <div class="chat-panel">
        <div class="chat-header">
            <span>🧑‍🏫</span>
            <span>学习助手</span>
        </div>
        <div class="chat-messages" id="chat-messages">
            <div class="chat-message ai">
                <div class="bubble" id="welcome-message">正在连接学习助手...</div>
            </div>
        </div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chat-input" placeholder="输入你的问题或回答..." disabled>
            <button class="chat-send" id="chat-send" onclick="sendMessage()" disabled>发送</button>
        </div>
    </div>
</div>
```

- [ ] **Step 3: 修改 JavaScript**

```html
{% block extra_script %}
{{ super() }}
<script>
const taskId = "{{ progress_id }}";
let chatConnected = false;
let chatInput = document.getElementById('chat-input');
let chatSend = document.getElementById('chat-send');

// 连接聊天
async function connectChat() {
    try {
        const res = await fetch(`/api/training/learn/${taskId}/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action: 'start'})
        });
        const data = await res.json();

        if (data.welcome) {
            document.getElementById('welcome-message').textContent = data.welcome;
        }

        // 加载课件
        loadCourseContent();

        chatConnected = true;
        chatInput.disabled = false;
        chatSend.disabled = false;
        chatInput.focus();
    } catch (e) {
        document.getElementById('welcome-message').textContent = '连接失败，请刷新页面重试';
    }
}

function loadCourseContent() {
    // 加载课件内容显示在左侧
    fetch(`/api/training/learn-by-task/${taskId}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('task-title').textContent = data.task_title || '培训任务';
            const rendered = marked.parse(data.content || '');
            document.getElementById('course-content').innerHTML = `<div class="markdown-body">${rendered}</div>`;
        });
}

function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg || !chatConnected) return;

    // 显示用户消息
    appendMessage('user', msg);
    chatInput.value = '';

    // 发送并接收回复
    fetch(`/api/training/learn/${taskId}/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
    }).then(r => r.json())
      .then(data => {
          if (data.content) {
              appendMessage('ai', data.content);
          }
      })
      .catch(e => appendMessage('ai', '抱歉，出现了一点问题，请重试。'));
}

function appendMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.innerHTML = `<div class="bubble">${escapeHtml(content)}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 回车发送
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// 初始化连接
connectChat();
</script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add gbrain/web/templates/training/learn.html
git commit -m "feat: add AI chat panel UI to learning page"
```

---

## Task 5: 集成测试

**Files:**
- (手动测试)

- [ ] **Step 1: 启动服务测试**

```bash
source .venv/bin/activate
python run_web.py
```

- [ ] **Step 2: 访问学习页面**

打开浏览器访问 `/training/task/{task_id}/learn`，验证：
1. 左侧显示课件内容
2. 右侧显示 AI 对话面板
3. AI 发送欢迎消息
4. 输入消息能得到 AI 回复

---

## 汇总

| Task | 文件 | 状态 |
|------|------|------|
| 1 | chat_engine.py | 新建 |
| 2 | learning_agent.py | 新建 |
| 3 | routes.py | 修改 |
| 4 | learn.html | 修改 |
| 5 | 集成测试 | 手动 |

---

**Plan complete.** 建议使用 Subagent-Driven 模式执行，每个 Task 由独立 subagent 完成。
