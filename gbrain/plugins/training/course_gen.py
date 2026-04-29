"""
课件生成器 - AI 从 gbrain 知识库提取内容生成培训课件
"""

import json
import math
import struct
import uuid
import re
from typing import Optional

from gbrain.database import Database
from gbrain.plugins.training.models import QuizItem


def get_embedding(text: str):
    """获取文本 embedding"""
    import requests
    from gbrain.config import QWEN_API_KEY, QWEN_EMBEDDING_URL, EMBEDDING_MODEL

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": EMBEDDING_MODEL,
        "input": {"texts": [text[:8192]]}
    }

    try:
        response = requests.post(
            QWEN_EMBEDDING_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return None
        result = response.json()
        return result.get("data", [{}])[0].get("embedding")
    except Exception:
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """混合搜索：向量 + BM25 + RRF"""
    from gbrain.config import RRF_K

    db = Database()

    # 获取 query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []

    # 向量搜索
    vector_results = []
    try:
        cursor = db.conn.execute("SELECT page_id, embedding FROM page_vectors")
        for row in cursor.fetchall():
            page_id = row[0]
            embedding_bytes = row[1]
            if embedding_bytes:
                embedding = struct.unpack(f'{len(embedding_bytes)//4}f', embedding_bytes)
                score = cosine_similarity(query_embedding, list(embedding))
                vector_results.append({'page_id': page_id, 'score': score})
        vector_results.sort(key=lambda x: x['score'], reverse=True)
        vector_results = vector_results[:top_k]
    except Exception:
        vector_results = []

    # BM25 搜索（简化版）
    bm25_results = []
    all_pages = db.get_all_pages()
    keywords = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 1]
    for page in all_pages:
        content_lower = (page.get('title', '') + ' ' + page.get('content', '')).lower()
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            bm25_results.append({
                'page_id': page['id'],
                'title': page.get('title', ''),
                'snippet': page.get('content', '')[:200],
                'score': score
            })
    bm25_results.sort(key=lambda x: x['score'], reverse=True)
    bm25_results = bm25_results[:top_k]

    # RRF 融合
    scores = {}
    for rank, result in enumerate(vector_results):
        page_id = result['page_id']
        rrf_score = 1.0 / (RRF_K + rank + 1)
        if page_id in scores:
            scores[page_id]['rrf_score'] += rrf_score
        else:
            scores[page_id] = {
                'page_id': page_id,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'rrf_score': rrf_score
            }

    for rank, result in enumerate(bm25_results):
        page_id = result['page_id']
        rrf_score = 1.0 / (RRF_K + rank + 1)
        if page_id in scores:
            scores[page_id]['rrf_score'] += rrf_score
        else:
            scores[page_id] = {
                'page_id': page_id,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'rrf_score': rrf_score
            }

    sorted_results = sorted(scores.values(), key=lambda x: x['rrf_score'], reverse=True)[:top_k]
    return [
        {'page_id': r['page_id'], 'title': r['title'], 'snippet': r['snippet'], 'score': r['rrf_score']}
        for r in sorted_results
    ]


def call_llm(prompt: str, system_prompt: str = "") -> str:
    """调用 MiniMax API 生成内容（同步版本）"""
    import requests
    from gbrain.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MODEL_NAME

    api_key = MINIMAX_API_KEY

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{MINIMAX_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        if response.status_code != 200:
            raise Exception(f"API 错误: {response.status_code}")
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM 调用失败: {str(e)}")


async def call_llm_async(prompt: str, system_prompt: str = "") -> str:
    """调用 MiniMax API 生成内容（异步版本，使用线程池避免阻塞）"""
    import asyncio
    return await asyncio.to_thread(call_llm, prompt, system_prompt)


class CourseGenerator:
    """课件生成器"""

    def __init__(self):
        self.db = Database()

    def generate_course(
        self,
        topic: str,
        description: str,
        num_chapters: int = 4,
        num_quiz: int = 3,
        content_source: list = None
    ) -> dict:
        """
        生成培训课件

        Args:
            topic: 培训主题
            description: HR 描述的需求
            num_chapters: 章节数量
            num_quiz: 测验题数量
            content_source: 指定的知识库页面 ID 列表

        Returns:
            dict: 包含 content 和 quiz_items
        """
        # 1. 根据 content_source 获取指定内容，或搜索全部知识库
        search_results = []
        context_parts = []

        if content_source:
            # 精确获取指定页面内容（获取完整内容）
            db = Database()
            for page_id in content_source:
                page = db.get_page(page_id)
                if page:
                    full_content = page.get('content', '')
                    # 截取前 3000 字符，保留关键信息
                    snippet = full_content[:3000] if len(full_content) > 3000 else full_content
                    context_parts.append(f"【参考资料】{page.get('title', '')}\n{snippet}")
                    search_results.append({'page_id': page_id, 'title': page.get('title', '')})
        else:
            # 搜索全部知识库
            print(f"检索知识库相关内容: {topic}")
            search_results = hybrid_search(f"{topic} {description}", top_k=5)
            for i, result in enumerate(search_results):
                page = self.db.get_page(result['page_id'])
                if page:
                    context_parts.append(f"【参考资料{i+1}】{page.get('title', '')}\n{page.get('content', '')[:500]}")
                    result['title'] = page.get('title', '')

        context = "\n\n".join(context_parts)

        # 3. 同时生成课件内容和测验题目（合并为一次调用提速）
        print(f"生成课件内容和测验题目...")
        combined_system = """你是一个专业的企业培训课件生成专家。根据客户的需求描述和提供的参考资料，生成符合企业实际培训需要的课件。

核心原则：
1. 课件内容必须紧密围绕用户的需求描述，根据需求复杂度确定模块数量（1-5个）
2. 充分利用参考知识库中的真实内容，不要凭空编造
3. 语言专业、简洁、易懂，符合成人学习规律
4. 只输出讲义内容，不包含需求描述、思考过程、分析推理

推荐课件结构：
## 模块N：核心要点名称
   ### 要点（1-2个核心概念定义）
   ### 实践方法（具体做法/步骤）
   ### 应用场景（1-2句话，不展开案例）
   ### 自检清单（3-5个检查项，学完自测用）

## 总结
   - 3-5条核心要点

禁止生成的内容：
- 不要生成"开篇"、"培训目标"、"培训场景"、"学习目标"等章节
- 不要生成"需求"、"思考"、"分析"、"行动计划"等章节
- 不要生成"研究表明..."、"让我们思考..."、"问题分析..."等引导性内容
- 不要生成大段案例分析
- 不要生成生成过程中的推理说明

测验题目要求：
1. 每道题为单选题，测试学员对关键知识点的理解
2. 选项要有区分度，干扰项要合理
3. 必须明确标注正确答案（correct_index: 0=A, 1=B, 2=C, 3=D）
4. 输出 JSON 数组格式"""

        # 构建强调用户需求的 prompt
        knowledge_context = f"\n\n{'='*50}\n".join(context_parts) if context_parts else "（无参考知识库内容）"

        combined_prompt = f"""## 培训需求

【培训主题】{topic}
【需求描述】{description}
【模块数量】由 AI 根据需求复杂度自行决定（1-5个）
【测验题数量】{num_quiz} 道

## 参考知识库内容
{knowledge_context}

## 输出要求

请严格按照【需求描述】生成课件：
1. 根据需求复杂度决定模块数量（简单主题1-2个，复杂主题3-5个）
2. 模块数量要匹配需求的实际内容，不要为凑数而拆分
3. 结合参考知识库中的真实内容，不要凭空编造
4. 提供可操作的实践方法，不要空泛的理论描述

输出格式（JSON）：
{{
  "content": "课件的Markdown内容，结构参考【推荐课件结构】",
  "quiz_items": [
    {{
      "id": "q1",
      "question": "题目内容",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "correct_index": 0,
      "explanation": "题解"
    }}
  ]
}}

请直接输出JSON，JSON块外不得有任何其他内容（包括思考过程、说明文字等）："""

        try:
            combined_response = call_llm(combined_prompt, combined_system)
            combined_json = self._extract_json(combined_response)
            if combined_json:
                course_content = combined_json.get('content', f"# {topic}\n\n{description}")
                quiz_json = combined_json.get('quiz_items', [])
                quiz_items = []
                if quiz_json:
                    for q in quiz_json[:num_quiz]:
                        # 处理 LLM 返回的不同格式：correct_index 或 answer
                        correct_idx = q.get('correct_index', 0)
                        answer_str = q.get('answer', '')
                        if answer_str and isinstance(answer_str, str):
                            # 转换 "A"/"B"/"C"/"D" 为索引 0/1/2/3
                            answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'a': 0, 'b': 1, 'c': 2, 'd': 3}
                            correct_idx = answer_map.get(answer_str.upper(), correct_idx)
                        quiz_items.append(QuizItem(
                            id=q.get('id', f"q{len(quiz_items)+1}"),
                            question=q.get('question', ''),
                            options=q.get('options', []),
                            correct_index=correct_idx,
                            explanation=q.get('explanation', '')
                        ))
            else:
                course_content = f"# {topic}\n\n{description}"
                quiz_items = []
        except Exception as e:
            print(f"生成失败: {e}")
            course_content = f"# {topic}\n\n{description}"
            quiz_items = []

        return {
            'content': course_content,
            'quiz_items': quiz_items,
            'search_results': search_results,
            'topic': topic,
            'description': description
        }

    def _extract_json(self, text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        if not text:
            return None

        # 清理思考过程标记（外层）
        text = re.sub(r'<think>[\s\S]*?</think>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()

        # 尝试直接解析
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                # 清理 content 字段中的思考过程标记
                if 'content' in result and isinstance(result['content'], str):
                    result['content'] = self._clean_thinking_markers(result['content'])
                return result
        except:
            pass

        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, dict):
                    # 清理 content 字段中的思考过程标记
                    if 'content' in result and isinstance(result['content'], str):
                        result['content'] = self._clean_thinking_markers(result['content'])
                    return result
            except:
                pass

        # 尝试提取 ``` ... ``` 块
        for block_match in re.finditer(r'```\s*([\s\S]*?)\s*```', text):
            try:
                result = json.loads(block_match.group(1).strip())
                if isinstance(result, dict):
                    # 清理 content 字段中的思考过程标记
                    if 'content' in result and isinstance(result['content'], str):
                        result['content'] = self._clean_thinking_markers(result['content'])
                    return result
            except:
                pass

        # 尝试找到 JSON 对象 - 找所有可能的 { ... } 块
        start = text.find('{')
        if start == -1:
            return None

        # 从后往前找最后一个 }
        for end in range(len(text) - 1, start - 1, -1):
            if text[end] == '}':
                try:
                    result = json.loads(text[start:end + 1])
                    if isinstance(result, dict):
                        # 清理 content 字段中的思考过程标记
                        if 'content' in result and isinstance(result['content'], str):
                            result['content'] = self._clean_thinking_markers(result['content'])
                        return result
                except:
                    continue

        return None

    
    def _clean_thinking_markers(self, text: str) -> str:
        """清理文本中的思考过程标记"""
        if not text:
            return text
        # 分步移除 <think>...</think> 块
        import re
        # 用变量避免字符串解析问题
        think_start = '<think>'
        think_end = '</think>'
        # 移除 <think>...</think> 块
        text = re.sub(think_start + r'[\s\S]*?' + think_end, '', text)
        # 移除 XML 标签
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()


def get_course_generator() -> CourseGenerator:
    global _generator
    if _generator is None:
        _generator = CourseGenerator()
    return _generator
