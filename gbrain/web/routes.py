"""
GBrain Web 路由
"""

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

from gbrain.plugins.training.service import get_training_service
from gbrain.plugins.training.learning_agent import LearningAgent
from gbrain.database import Database

# 会话管理
learning_sessions: dict[str, LearningAgent] = {}

# 状态映射常量
STATUS_TEXT_MAP = {"draft": "草稿", "published": "已发布", "archived": "已归档"}


def _clean_lecture_content(content: str) -> str:
    """过滤讲义内容，移除生成元数据"""
    if not content:
        return content
    import re

    # 先移除所有 think 标记块 (<think>...</think>)
    # 分步移除，避免字符串解析问题
    start_marker = '<think>'
    end_marker = '</think>'
    while start_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if end_idx != -1:
            content = content[:start_idx] + content[end_idx + len(end_marker):]
        else:
            break

    lines = content.split('\n')
    result = []

    # 跳过整个章节的模式（包括其下属内容）
    skip_section_patterns = [
        r'^## 基本信息',
        r'^## 开篇',
        r'^## 学习目标',
        r'^## 准备工作',
        r'^## 培训目标',
        r'^## 培训场景',
        r'^## 培训目的',
        r'^## 模块总结',
        r'^## 本章小结',
        r'^## 行动计划',
    ]

    # 跳过单个子章节（### 开头）的模式
    skip_subsection_patterns = [
        r'^### 培训场景',
        r'^### 培训目标',
        r'^### 培训目的',
        r'^### 需求',
        r'^### 思考',
        r'^### 分析',
        r'^### 案例分析',
        r'^### 学习目标',
        r'^### 准备工作',
    ]

    # 跳过多行内容的关键词（正则表达式匹配）
    skip_line_patterns = [
        r'^通过本培训，您将掌握',
        r'^本章将介绍.*相关知识和技能',
        r'^这就是商务礼仪的力量',
        r'^它不是刻板的条条框框',
        r'^而是在每一个细节中传递价值',
        r'^本次培训时长约',
        r'^将帮助大家',
        r'^- \*\*理解\*\*',  # 匹配列表项 "- **理解**..."
        r'^- \*\*掌握\*\*',
        r'^- \*\*学会\*\*',
        r'^- \*\*运用\*\*',
        r'^- \*\*提升\*\*',
    ]

    skip_until_h2 = False

    for line in lines:
        trimmed = line.strip()

        # 遇到 ## 或 ### 标题，重置跳过状态
        if re.match(r'^#{1,3}\s', trimmed):
            skip_until_h2 = False

        # 检查是否需要跳过整个 ## 章节
        if any(re.match(p, trimmed) for p in skip_section_patterns):
            skip_until_h2 = True
            continue

        if skip_until_h2:
            continue

        # 检查是否需要跳过 ### 子章节
        if any(re.match(p, trimmed) for p in skip_subsection_patterns):
            skip_until_h2 = True
            continue

        # 检查是否匹配整行关键词（任意位置）
        if any(re.search(p, trimmed) for p in skip_line_patterns):
            continue

        result.append(line)

    return '\n'.join(result)


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
                    "status_text": STATUS_TEXT_MAP.get(t.status.value, t.status.value)
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
                    "status_text": STATUS_TEXT_MAP.get(t.status.value, t.status.value)
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
                "content": _clean_lecture_content(task.content),
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
            "content": _clean_lecture_content(task.content),
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

        # 过滤讲义内容，移除生成元数据
        clean_content = _clean_lecture_content(task.content)

        return JSONResponse({
            "progress_id": task_id,  # 用task_id作为progress_id演示
            "task_title": task.title,
            "content": clean_content,
            "quiz_items": [
                {
                    "id": q.id,
                    "question": q.question,
                    "options": q.options
                }
                for q in task.quiz_items
            ]
        })

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
            import sys
            sys.stderr.write(f"[API] topic={data.get('topic', '')}, desc={str(data.get('description', ''))[:50]}, content_source={data.get('content_source', [])}\n")
            sys.stderr.flush()

            user_prompt = data.get('user_prompt', '')
            file_contents = data.get('file_contents', [])
            training_type = data.get('training_type', 'product')
            output_format = data.get('output_format', 'lecture')

            # 验证 training_type
            valid_training_types = {'product', 'compliance', 'sales_skill', 'business_etiquette'}
            if training_type not in valid_training_types:
                training_type = 'product'

            # 兼容简单格式：自动构建 Markdown prompt
            if not user_prompt:
                topic = data.get('topic', '')
                description = data.get('description', '')
                num_chapters = data.get('num_chapters', 4)
                content_source = data.get('content_source', [])

                if not topic:
                    return JSONResponse({"success": False, "error": "培训主题不能为空"}, status_code=400)

                # 如果有选择知识库文件，获取内容
                kb_raw_contents = []
                kb_load_warnings = []
                invalid_file_ids = []
                if content_source and not file_contents:
                    db = Database()
                    found_count = 0
                    for page_id in content_source:
                        page = db.get_page(page_id)
                        if page:
                            kb_content = page.get('content', '')
                            kb_raw_contents.append(kb_content)
                            file_contents.append(kb_content)
                            found_count += 1
                            logger.info(f"成功读取 KB page: {page_id}, title={page.get('title','')}, content_len={len(kb_content)}")
                        else:
                            invalid_file_ids.append(page_id)
                            kb_load_warnings.append(f"知识库文件 {page_id} 未找到")
                            logger.warning(f"KB page 未找到: {page_id}")
                    if invalid_file_ids:
                        logger.warning(f"无效的知识库文件 IDs: {invalid_file_ids}")
                    logger.info(f"Loaded {found_count}/{len(content_source)} KB pages, content_source={content_source}")
                    if found_count == 0 and content_source:
                        return JSONResponse({
                            "success": False,
                            "error": f"选定的知识库文件均未找到，请重新选择有效的文件。无效的文件ID: {invalid_file_ids}"
                        }, status_code=400)

                # 构建章节结构：根据用户描述生成，优先使用描述中的关键词
                import re

                # 从描述中提取关键词/功能点作为章节
                def extract_keywords_from_description(desc: str) -> list[str]:
                    """从描述中智能提取关键词作为章节，兼容所有常见格式"""
                    if not desc:
                        return []

                    all_keywords = []
                    seen = set()

                    def add_keyword(kw):
                        kw = kw.strip()
                        kw = re.sub(r'^(熟悉|掌握|了解|学习|学会|包含|包括)\s*', '', kw)
                        if kw and len(kw) >= 2 and kw not in seen:
                            seen.add(kw)
                            all_keywords.append(kw)

                    # 按行处理，匹配各种编号前缀
                    prefix_patterns = [
                        r'^[\u2460-\u2473]\s*',           # 圆圈编号
                        r'^\d+[、.]\s*',                  # 数字+顿号/点
                        r'^[一二三四五六七八九十]+[、.]\s*', # 中文数字+顿号/点
                        r'^[\uff08(][一二三四五六七八九十]+[\uff09)]\s*', # 括号中文数字
                    ]

                    for line in desc.split('\n'):
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue
                        matched = False
                        for pattern in prefix_patterns:
                            match_obj = re.match(pattern, line_stripped)
                            if match_obj:
                                content_after = line_stripped[match_obj.end():].strip()
                                if content_after:
                                    add_keyword(content_after)
                                    matched = True
                                break
                        # 如果没匹配到编号，尝试顿号分隔
                        if not matched and '、' in line_stripped and 5 <= len(line_stripped) <= 80:
                            parts = line_stripped.split('、')
                            if 2 <= len(parts) <= 10:
                                for part in parts:
                                    add_keyword(part.strip())

                    # 如果没有提取到，尝试整段顿号分隔
                    if not all_keywords and '、' in desc:
                        parts = desc.split('、')
                        if 3 <= len(parts) <= 15:
                            for part in parts:
                                add_keyword(part)

                    # 如果还是没有，尝试逗号分隔
                    if not all_keywords and ('，' in desc or ',' in desc):
                        parts = re.split(r'[，,]', desc)
                        if 3 <= len(parts) <= 20:
                            for part in parts:
                                add_keyword(part)

                    return all_keywords


                # 从知识库内容中提取章节标题（作为备选）
                def extract_chapters_from_kb(kb_contents):
                    """从知识库内容中智能提取章节"""
                    all_lines = []
                    for kb_content in kb_contents:
                        all_lines.extend(kb_content.split('\n'))

                    chapters = []
                    for line in all_lines:
                        stripped = line.strip()
                        # 识别章节标题特征
                        if re.match(r'^#{2,3}\s+', stripped):
                            title = re.sub(r'^#+\s+', '', stripped).strip()
                            title = re.sub(r'^[\d\.\、．]+[\s\、\.]+', '', title)
                            title = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]+[\s\、\.]+', '', title)
                            if len(title) >= 2 and len(title) <= 40:
                                chapters.append(title)
                        elif re.match(r'^第[一二三四五六七八九十百零\d]+[章节部]', stripped):
                            chapters.append(stripped)

                    seen = set()
                    unique_chapters = []
                    for c in chapters:
                        if c not in seen:
                            seen.add(c)
                            unique_chapters.append(c)
                    return unique_chapters

                # 提取描述中的关键词作为章节
                desc_keywords = extract_keywords_from_description(description)
                logger.info(f"从描述提取的关键词: {desc_keywords}")

                # 提取知识库中的章节
                kb_chapters = extract_chapters_from_kb(kb_raw_contents) if kb_raw_contents else []

                # 决定章节结构：描述关键词 > 知识库章节 > 默认生成
                if desc_keywords:
                    # 优先使用描述中的关键词
                    modules_md = '\n'.join([f'#### 模块{i+1}：{name}' for i, name in enumerate(desc_keywords[:num_chapters])])
                    logger.info(f"使用描述关键词生成 {len(desc_keywords[:num_chapters])} 个模块")
                elif kb_chapters:
                    # 其次使用知识库的章节
                    modules_md = '\n'.join([f'#### 模块{i+1}：{name}' for i, name in enumerate(kb_chapters[:num_chapters])])
                    logger.info(f"使用知识库章节生成 {len(kb_chapters[:num_chapters])} 个模块")
                else:
                    # 最后按数量生成空模块
                    modules_md = '\n'.join([f'#### 模块{i+1}' for i in range(num_chapters)])
                    logger.info("使用默认空模块")

                user_prompt = f"""## 基本信息
- 培训主题：{topic}
- 培训受众：通用员工
- 目标岗位：通用岗位
- 所属行业：通用行业
- 时长：约 {num_chapters * 15} 分钟
- 风格：专业严谨

## 大纲结构
### 模块拆解层
{modules_md}
"""

            builder = LectureGenerationBuilder()

            # 自动检测培训类型（仅在简单格式时需要）
            training_type_auto = training_type
            if not user_prompt:
                topic_lower = topic.lower()
                desc_lower = description.lower()
                combined = topic_lower + ' ' + desc_lower

                if any(kw in combined for kw in ['礼仪', '礼仪培训', '商务礼仪', '职场礼仪']):
                    training_type_auto = 'business_etiquette'
                elif any(kw in combined for kw in ['销售', '话术', '客户']):
                    training_type_auto = 'sales_skill'
                elif any(kw in combined for kw in ['合规', '法规', '制度']):
                    training_type_auto = 'compliance'

            with open('/tmp/api_debug2.txt', 'a') as f:
                f.write(f"[API] file_contents={len(file_contents)} items\n")
                if file_contents:
                    f.write(f"[API] file_contents[0][:200]={file_contents[0][:200]}\n")
                else:
                    f.write("[API] file_contents is EMPTY\n")

            result = builder.build(user_prompt, file_contents, training_type_auto, output_format)

            with open('/tmp/api_debug2.txt', 'a') as f:
                f.write(f"[API] result[:200]={result['content'][:200]}\n")

            return JSONResponse({
                "success": True,
                "content": result['content']
            })
        except Exception as e:
            logger.exception("Course generation failed")
            return JSONResponse({"success": False, "error": "生成失败，请重试"}, status_code=500)

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
                output_format = data.get('output_format', 'lecture')
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
                result = builder.build(user_prompt, [], 'product', output_format)
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
                logger.info(f"上传文件: {file.filename}, page_id={page_id}, content长度={len(markdown_content)}")
                insert_result = db.insert_page(
                    page_id=page_id,
                    title=title,
                    content=markdown_content,
                    category="培训资料",
                    tags=["上传文档", ext.replace('.', '')],
                    links=[]
                )
                logger.info(f"insert_page 结果: {insert_result}, title={title}")

                if not insert_result:
                    raise Exception(f"数据库保存失败: page_id={page_id}, title={title}")

                results.append({
                    "filename": file.filename,
                    "success": True,
                    "page_id": page_id,
                    "title": title,
                    "preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
                })
                logger.info(f"上传成功: {file.filename} -> page_id={page_id}")

            except Exception as e:
                logger.error(f"上传失败: {file.filename}, error={str(e)}")
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

    @app.delete("/api/training/admin/task/{task_id}")
    async def api_delete_task(task_id: str):
        """删除任务"""
        service = get_training_service()
        success = service.delete_task(task_id)
        return JSONResponse({"success": success})

    @app.post("/api/training/admin/task/{task_id}/regenerate")
    async def api_regenerate_task(task_id: str, request: Request):
        """重新生成任务内容"""
        service = get_training_service()
        task = service.get_task(task_id)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        try:
            body = await request.body()
            data = json.loads(body)
            new_content = data.get('content', '')
            if new_content:
                success = service.update_task(task_id, content=new_content)
                return JSONResponse({"success": success})
            return JSONResponse({"error": "Content is required"}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

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
        SSE 流式对话接口（场景驱动学习）

        action:
          - start: 初始化学习会话，生成场景链，返回 welcome 消息和进度
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

            # 清理讲义内容
            clean_content = _clean_lecture_content(task.content or "")

            # 检查是否有已存在的会话
            if task_id in learning_sessions:
                agent = learning_sessions[task_id]
                # 如果是重新开始学习，重置会话
                if agent.stage in ["completed", "failed"]:
                    agent.scene_engine.reset()
                    agent.set_stage("learning")
            else:
                # 尝试从数据库加载场景链
                db = Database()
                saved_chain = db.get_scene_chain(task_id)

                if saved_chain and saved_chain.get('scenes'):
                    # 使用数据库中的场景链
                    scene_chain = saved_chain['scenes']
                else:
                    # 生成新场景链并保存到数据库
                    from gbrain.plugins.training.scene_generator import generate_scene_chain as gen_chain
                    chain_obj = gen_chain(clean_content, num_scenes=4, task_id=task_id)
                    scene_chain = [s.__dict__ for s in chain_obj.scenes] if chain_obj else []

                    # 保存到数据库
                    if scene_chain:
                        import uuid
                        db.insert_scene_chain({
                            'id': str(uuid.uuid4()),
                            'task_id': task_id,
                            'scenes': scene_chain,
                            'weak_points': []
                        })

                # 创建学习会话
                learning_sessions[task_id] = LearningAgent(
                    task_id=task_id,
                    content=clean_content,
                    task_title=task.title,
                    progress_id=task_id,
                    scene_chain=scene_chain
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
