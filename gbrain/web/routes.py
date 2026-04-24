"""
GBrain Web 路由
"""

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
import os

from gbrain.plugins.training.service import get_training_service
from gbrain.plugins.training.learning_agent import LearningAgent
from gbrain.database import Database

# 会话管理
learning_sessions: dict[str, LearningAgent] = {}


def register_routes(app: FastAPI, templates: Jinja2Templates):
    """注册所有路由"""

    @app.get("/", response_class=HTMLResponse)
    async def home():
        """首页 - 重定向到培训平台"""
        return RedirectResponse(url="/training")

    @app.get("/training", response_class=HTMLResponse)
    async def training_home(request: Request):
        """培训首页"""
        return templates.TemplateResponse(
            "training/home.html",
            {"request": request, "title": "培训平台"}
        )

    @app.get("/training/tasks", response_class=HTMLResponse)
    async def task_list(request: Request):
        """任务列表"""
        return templates.TemplateResponse(
            "training/tasks.html",
            {"request": request, "title": "培训任务"}
        )

    @app.get("/training/task/{task_id}", response_class=HTMLResponse)
    async def task_detail(request: Request, task_id: str):
        """任务详情/学习页面"""
        return templates.TemplateResponse(
            "training/task_detail.html",
            {"request": request, "title": "学习任务", "task_id": task_id}
        )

    @app.get("/training/learn/{progress_id}", response_class=HTMLResponse)
    async def learn_page(request: Request, progress_id: str):
        """学习页面"""
        return templates.TemplateResponse(
            "training/learn.html",
            {"request": request, "title": "学习中", "progress_id": progress_id}
        )

    @app.get("/training/task/{task_id}/learn", response_class=HTMLResponse)
    async def task_learn_page(request: Request, task_id: str):
        """通过任务ID进入学习页面"""
        return templates.TemplateResponse(
            "training/learn.html",
            {"request": request, "title": "学习中", "progress_id": task_id, "is_task_learn": True}
        )

    @app.post("/training/quiz/{progress_id}")
    async def submit_quiz(progress_id: str, answers: str = Form(...)):
        """提交测验"""
        # 解析答案并重定向到结果页
        return RedirectResponse(url=f"/training/quiz/result/{progress_id}")

    @app.get("/training/quiz/result/{progress_id}", response_class=HTMLResponse)
    async def quiz_result(request: Request, progress_id: str):
        """测验结果页面"""
        return templates.TemplateResponse(
            "training/quiz_result.html",
            {"request": request, "title": "测验结果", "progress_id": progress_id}
        )

    @app.get("/training/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """数据看板"""
        return templates.TemplateResponse(
            "training/dashboard.html",
            {"request": request, "title": "数据看板"}
        )

    @app.get("/training/admin", response_class=HTMLResponse)
    async def admin_panel(request: Request):
        """管理后台"""
        return templates.TemplateResponse(
            "training/admin.html",
            {"request": request, "title": "管理后台"}
        )

    # ========== API 端点 ==========

    @app.get("/api/training/tasks")
    async def api_task_list():
        """任务列表 API（仅返回已发布的）"""
        service = get_training_service()
        tasks = service.get_all_tasks(status='published')
        return JSONResponse({
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "task_type": t.task_type.value,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "status": t.status.value,
                    "status_text": {"draft": "草稿", "published": "已发布", "archived": "已归档"}.get(t.status.value, t.status.value)
                }
                for t in tasks
            ]
        })

    @app.get("/api/training/admin/tasks")
    async def api_admin_task_list():
        """管理后台任务列表 API（返回所有状态）"""
        service = get_training_service()
        tasks = service.get_all_tasks()  # 不筛选，返回所有
        return JSONResponse({
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "task_type": t.task_type.value,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "status": t.status.value,
                    "status_text": {"draft": "草稿", "published": "已发布", "archived": "已归档"}.get(t.status.value, t.status.value)
                }
                for t in tasks
            ]
        })

    @app.get("/api/training/task/{task_id}")
    async def api_task_detail(task_id: str):
        """任务详情 API"""
        service = get_training_service()
        task = service.get_task(task_id)
        if not task:
            return JSONResponse({"task": None}, status_code=404)

        return JSONResponse({
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type.value,
                "content": task.content,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "status": task.status.value,
                "quiz_items": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "options": q.options
                    }
                    for q in task.quiz_items
                ]
            }
        })

    @app.get("/api/training/learn/{progress_id}")
    async def api_learn_page(progress_id: str):
        """学习页面 API"""
        service = get_training_service()
        progress = service.get_progress(progress_id)
        if not progress:
            return JSONResponse({"error": "Progress not found"}, status_code=404)

        # 开始学习
        if progress.state.value == "not_started":
            service.start_learning(progress_id)

        task = service.get_task(progress.task_id)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        return JSONResponse({
            "progress_id": progress_id,
            "task_title": task.title,
            "content": task.content,
            "quiz_items": [
                {
                    "id": q.id,
                    "question": q.question,
                    "options": q.options
                }
                for q in task.quiz_items
            ]
        })

    @app.get("/api/training/learn-by-task/{task_id}")
    async def api_learn_by_task(task_id: str):
        """通过任务ID直接进入学习（用于演示）"""
        service = get_training_service()
        task = service.get_task(task_id)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        return JSONResponse({
            "progress_id": task_id,  # 用task_id作为progress_id演示
            "task_title": task.title,
            "content": task.content,
            "quiz_items": [
                {
                    "id": q.id,
                    "question": q.question,
                    "options": q.options
                }
                for q in task.quiz_items
            ]
        })

    @app.post("/api/training/quiz/{progress_id}")
    async def api_submit_quiz(progress_id: str):
        """提交测验 API"""
        # 获取原始请求体
        body = await api_submit_quiz.__code__
        return JSONResponse({"success": True, "redirect": f"/training/quiz/result/{progress_id}"})

    @app.post("/api/training/quiz/{progress_id}/submit")
    async def api_quiz_submit(progress_id: str, request: Request):
        """提交测验 API（JSON）"""
        service = get_training_service()
        try:
            body = await request.body()
            data = json.loads(body)
            answers = data.get('answers', [])
            result = service.submit_quiz(progress_id, answers)
            return JSONResponse({
                "success": True,
                "score": result.score,
                "passed": result.passed,
                "redirect": f"/training/quiz/result/{progress_id}"
            })
        except ValueError as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    @app.get("/api/training/quiz/result/{progress_id}")
    async def api_quiz_result(progress_id: str):
        """测验结果 API"""
        service = get_training_service()
        progress = service.get_progress(progress_id)
        if not progress:
            return JSONResponse({"error": "Progress not found"}, status_code=404)

        # 计算剩余补考次数
        attempts_left = max(0, 2 - progress.quiz_attempts)

        return JSONResponse({
            "score": progress.quiz_score,
            "passed": progress.state.value in ('completed', 'mastered'),
            "attempts_left": attempts_left,
            "state": progress.state.value
        })

    @app.get("/api/training/progress/{employee_id}")
    async def api_progress(employee_id: str):
        """员工学习进度 API"""
        service = get_training_service()
        progress_list = service.get_employee_progress(employee_id)
        return JSONResponse({
            "progress": [
                {
                    "id": p.id,
                    "task_id": p.task_id,
                    "state": p.state.value,
                    "quiz_score": p.quiz_score,
                    "quiz_attempts": p.quiz_attempts
                }
                for p in progress_list
            ]
        })

    @app.get("/api/training/admin/tasks/{task_id}/progress")
    async def api_task_progress(task_id: str):
        """获取任务的员工学习进度"""
        service = get_training_service()
        progress_list = service.get_task_progress(task_id)
        return JSONResponse({
            "progress": [
                {
                    "id": p.id,
                    "employee_id": p.employee_id,
                    "state": p.state.value,
                    "quiz_score": p.quiz_score,
                    "quiz_attempts": p.quiz_attempts
                }
                for p in progress_list
            ]
        })

    @app.get("/api/training/employees")
    async def api_employees():
        """员工列表 API"""
        service = get_training_service()
        employees = service.get_all_employees()
        return JSONResponse({
            "employees": [
                {
                    "id": e.id,
                    "name": e.name,
                    "department": e.department,
                    "position": e.position,
                    "role": e.role.value
                }
                for e in employees
            ]
        })

    @app.get("/api/training/dashboard/stats")
    async def api_dashboard_stats():
        """看板统计数据 API"""
        service = get_training_service()
        stats = service.get_dashboard_stats()
        task_stats = service.get_task_stats()
        incomplete = service.get_incomplete_employees()

        return JSONResponse({
            "total_employees": stats.get('total_employees', 0),
            "completed_count": stats.get('completed_count', 0),
            "completion_rate": stats.get('completion_rate', 0.0),
            "avg_quiz_score": stats.get('avg_quiz_score', 0.0),
            "task_stats": task_stats,
            "incomplete_employees": incomplete
        })

    @app.post("/api/training/admin/course/generate")
    async def api_generate_course(request: Request):
        """AI 生成讲义 API（基于 Skill）

        支持两种输入格式：
        1. 简单格式：{ topic, description, num_chapters, training_type, content_source }
        2. Markdown 格式：{ user_prompt, file_contents, training_type }
        """
        from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder
        try:
            body = await request.body()
            data = json.loads(body)

            user_prompt = data.get('user_prompt', '')
            file_contents = data.get('file_contents', [])
            training_type = data.get('training_type', 'product')

            # 兼容简单格式：自动构建 Markdown prompt
            if not user_prompt:
                topic = data.get('topic', '')
                description = data.get('description', '')
                num_chapters = data.get('num_chapters', 4)
                content_source = data.get('content_source', [])

                if not topic:
                    return JSONResponse({"success": False, "error": "培训主题不能为空"}, status_code=400)

                # 如果有选择知识库文件，获取内容
                if content_source and not file_contents:
                    db = Database()
                    for page_id in content_source:
                        page = db.get_page(page_id)
                        if page:
                            file_contents.append(page.get('content', ''))

                # 构建 Markdown 格式 prompt（包含描述）
                modules_md = '\n'.join([f"#### 模块{i+1}" for i in range(num_chapters)])
                user_prompt = f"""## 基本信息
- 培训主题：{topic}
- 培训受众：通用员工
- 目标岗位：通用岗位
- 所属行业：通用行业
- 时长：约 {num_chapters * 15} 分钟
- 风格：专业严谨

## 需求描述
{description}

## 学习目标
1. 理解{topic}的核心概念
2. 掌握{topic}的关键方法
3. 能够应用{topic}解决实际问题

## 大纲结构
### 模块拆解层
{modules_md}
"""

            builder = LectureGenerationBuilder()
            result = builder.build(user_prompt, file_contents, training_type)

            return JSONResponse({
                "success": True,
                "content": result['content'],
                "user_prompt_params": result['user_prompt_params'],
                "outline": result['outline'],
                "validation_report": result['validation_report'],
                "knowledge_points": result['knowledge_points'],
                "case_library": result.get('case_library', []),
                "supplementary_materials": result.get('supplementary_materials', {}),
                "metadata": result['metadata']
            })
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    @app.post("/api/training/admin/task")
    async def api_create_task(request: Request):
        """创建任务 API"""
        service = get_training_service()
        try:
            body = await request.body()
            data = json.loads(body)

            # 如果提供了 auto_generate，则使用 AI 生成讲义（Skill）
            if data.get('auto_generate'):
                from gbrain.plugins.training.skills.lecture_generation.builder import LectureGenerationBuilder
                builder = LectureGenerationBuilder()
                topic = data['title']
                num_chapters = data.get('num_chapters', 4)
                modules_md = '\n'.join([f"#### 模块{i+1}" for i in range(num_chapters)])
                user_prompt = f"""## 基本信息
- 培训主题：{topic}
- 培训受众：通用员工
- 目标岗位：通用岗位
- 所属行业：通用行业
- 时长：约 {num_chapters * 15} 分钟
- 风格：专业严谨

## 学习目标
1. 理解{topic}的核心概念
2. 掌握{topic}的关键方法
3. 能够应用{topic}解决实际问题

## 大纲结构
### 模块拆解层
{modules_md}
"""
                result = builder.build(user_prompt, [], 'product')
                data['content'] = result['content']
                data['quiz_items'] = []  # Skill 版本暂不生成 quiz_items

            task = service.create_task(
                title=data['title'],
                description=data.get('description', ''),
                task_type=data.get('task_type', 'onboarding'),
                content_source=data.get('content_source', []),
                deadline=data.get('deadline'),
                priority=data.get('priority', 2),
                content=data.get('content', ''),
                quiz_items=data.get('quiz_items', [])
            )

            return JSONResponse({"success": True, "task_id": task.id})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    @app.post("/api/training/admin/upload")
    async def api_upload_documents(files: list[UploadFile] = File(...)):
        """上传文档并转换为 Markdown"""
        from gbrain.plugins.training.doc_converter import get_document_converter
        from gbrain.database import Database
        import uuid

        converter = get_document_converter()
        db = Database()
        results = []

        for file in files:
            try:
                # 检查文件格式
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in converter.SUPPORTED_FORMATS:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"不支持的格式: {ext}，支持: {', '.join(converter.SUPPORTED_FORMATS)}"
                    })
                    continue

                # 读取文件内容
                content = await file.read()

                # 保存文件
                file_path = await converter.save_file(file.filename, content)

                # 转换为 Markdown
                markdown_content = converter.convert_to_markdown(file_path)

                # 提取标题
                title = converter.extract_title_from_content(markdown_content)
                if not title:
                    title = file.filename.replace(ext, '')

                # 存入知识库
                page_id = str(uuid.uuid4())
                db.insert_page(
                    page_id=page_id,
                    title=title,
                    content=markdown_content,
                    category="培训资料",
                    tags=["上传文档", ext.replace('.', '')],
                    links=[]
                )

                results.append({
                    "filename": file.filename,
                    "success": True,
                    "page_id": page_id,
                    "title": title,
                    "preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
                })

            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })

        return JSONResponse({
            "success": True,
            "results": results
        })

    @app.post("/api/training/admin/task/{task_id}/publish")
    async def api_publish_task(task_id: str):
        """发布任务"""
        service = get_training_service()
        success = service.publish_task(task_id)
        return JSONResponse({"success": success})

    @app.post("/api/training/admin/task/{task_id}/archive")
    async def api_archive_task(task_id: str):
        """归档任务"""
        service = get_training_service()
        success = service.archive_task(task_id)
        return JSONResponse({"success": success})

    @app.get("/api/training/knowledge/pages")
    async def api_knowledge_pages():
        """获取知识库所有页面（用于选择来源）"""
        db = Database()
        pages = db.get_all_pages()
        return JSONResponse({
            "pages": [
                {
                    "id": p['id'],
                    "title": p.get('title', ''),
                    "category": p.get('category', ''),
                    "updated_at": p.get('updated_at', '')
                }
                for p in pages
            ]
        })

    @app.post("/api/training/admin/employee")
    async def api_create_employee(request: Request):
        """创建员工 API"""
        service = get_training_service()
        try:
            body = await request.body()
            data = json.loads(body)

            employee = service.create_employee(
                name=data['name'],
                department=data['department'],
                position=data['position'],
                role=data.get('role', 'employee'),
                join_date=data.get('join_date')
            )

            return JSONResponse({"success": True, "employee_id": employee.id})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    # ========== SSE 对话接口 ==========

    @app.post("/api/training/learn/{task_id}/chat")
    async def api_learning_chat(task_id: str, request: Request):
        """
        SSE 流式对话接口

        action:
          - start: 初始化学习会话，返回 welcome 消息和进度
          - status: 获取当前进度
          - chat: 处理对话，流式返回
        """
        body = await request.body()
        data = json.loads(body)
        action = data.get('action', 'chat')

        if action == 'start':
            # 初始化学习会话
            service = get_training_service()
            task = service.get_task(task_id)
            if not task:
                return JSONResponse({"error": "Task not found"}, status_code=404)

            # 创建或获取会话
            if task_id not in learning_sessions:
                learning_sessions[task_id] = LearningAgent(
                    task_id=task_id,
                    content=task.content or "",
                    task_title=task.title
                )

            agent = learning_sessions[task_id]
            welcome = agent.get_welcome_message()
            progress = agent.get_progress()

            async def event_stream():
                yield f"data: {json.dumps(welcome, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'progress', **progress}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        elif action == 'status':
            # 获取当前进度
            if task_id not in learning_sessions:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            agent = learning_sessions[task_id]
            return JSONResponse(agent.get_progress())

        elif action == 'chat':
            # 处理对话
            if task_id not in learning_sessions:
                return JSONResponse({"error": "Session not found. Use action=start first."}, status_code=404)

            message = data.get('message', '')
            agent = learning_sessions[task_id]

            async def event_stream():
                response = await agent.chat(message)
                yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        else:
            return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
