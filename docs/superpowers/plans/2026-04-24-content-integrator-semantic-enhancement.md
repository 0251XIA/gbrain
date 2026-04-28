# ContentIntegrator 语义增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强 ContentIntegrator 的内容分配逻辑，实现多模块分配、fallback池、完整案例提取和同义词扩展

**Architecture:** 在现有 `_distribute_content` 方法基础上增加多模块分配和 fallback 机制；新增同义词映射配置；改进案例提取逻辑去除字符限制

**Tech Stack:** Python, pytest, regex

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `gbrain/plugins/training/skills/lecture_generation/content_integrator.py` | 核心逻辑修改 |
| `gbrain/plugins/training/skills/lecture_generation/models.py` | 新增同义词配置 |
| `tests/plugins/training/skills/lecture_generation/test_content_integrator.py` | 新增测试用例 |

---

## Task 1: 同义词映射配置

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/models.py:53`

- [ ] **Step 1: 在 models.py 添加 SYNONYM_MAP 配置**

在文件末尾添加：

```python
# 领域同义词映射表
SYNONYM_MAP: dict[str, list[str]] = {
    "电话": ["话术", "沟通技巧", "通话", "语音"],
    "销售": ["营销", "推销", "商务", "售卖"],
    "客户": ["顾客", "用户", "采购方", "买家"],
    "合同": ["合约", "协议", "契约"],
    "签署": ["签名", "签字", "签订", "签章"],
    "产品": ["商品", "服务", "解决方案"],
    "培训": ["训练", "学习", "教学"],
    "系统": ["平台", "软件", "工具"],
    "流程": ["步骤", "过程", "工序"],
    "规范": ["标准", "准则", "规程"],
}
```

- [ ] **Step 2: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/models.py
git commit -m "feat: add SYNONYM_MAP for keyword expansion"
```

---

## Task 2: 多模块分配逻辑

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/content_integrator.py:40-68`
- Test: `tests/plugins/training/skills/lecture_generation/test_content_integrator.py`

- [ ] **Step 1: 编写多模块分配的失败测试**

在 `test_content_integrator.py` 添加：

```python
def test_distribute_content_multi_module():
    """同一条内容应分配给多个相关模块"""
    integrator = ContentIntegrator()

    parsed = ParsedPrompt(
        topic="销售培训",
        audience="销售团队",
        position="销售代表",
        industry="企业服务",
        duration="60分钟",
        style="实操导向",
        objectives=["掌握话术", "了解产品"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=2,
        outline_structure={"模块拆解层": ["模块1-电话话术", "模块2-产品知识"]}
    )

    file_contents = ["销售电话沟通技巧，包含与客户的话术对话"]

    result = integrator.integrate(parsed, file_contents)

    # 内容应同时分配给两个模块
    assert len(result.module_contents["模块1-电话话术"]) >= 1
    assert len(result.module_contents["模块2-产品知识"]) >= 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_distribute_content_multi_module -v
```
Expected: FAIL - 内容只分配给了一个模块

- [ ] **Step 3: 实现多模块分配**

将 `_distribute_content` 方法替换为：

```python
def _distribute_content(self, content: str, module_contents: dict[str, list[str]], modules: list[str]):
    """将内容分配到对应模块，使用关键词匹配避免误匹配"""
    # 构建每个模块的关键词集合（含同义词扩展）
    module_keywords: dict[str, list[str]] = {}
    for module in modules:
        keywords = re.findall(r'[\w]+', module)
        stopwords = {'模块', '章节', '第', '一', '二', '三', '四', '五', '的', '和'}
        keywords = [k for k in keywords if k not in stopwords and len(k) > 1]
        # 同义词扩展
        from .models import SYNONYM_MAP
        expanded = set(keywords)
        for kw in keywords:
            if kw in SYNONYM_MAP:
                expanded.update(SYNONYM_MAP[kw])
        module_keywords[module] = list(expanded)

    # 计算每个模块的匹配分数
    module_scores: dict[str, int] = {}
    for module in modules:
        score = 0
        for keyword in module_keywords[module]:
            if re.search(rf'\b{re.escape(keyword)}\b', content):
                score += 1
        module_scores[module] = score

    # 多模块分配：分配给所有分数超过阈值(0.3*最高分)的模块
    max_score = max(module_scores.values()) if module_scores else 0
    threshold = max_score * 0.3

    for module, score in module_scores.items():
        if score >= threshold and score > 0:
            module_contents[module].append(content)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_distribute_content_multi_module -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/content_integrator.py tests/plugins/training/skills/lecture_generation/test_content_integrator.py
git commit -m "feat: implement multi-module content distribution"
```

---

## Task 3: Fallback 池机制

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/content_integrator.py:6-31`
- Test: `tests/plugins/training/skills/lecture_generation/test_content_integrator.py`

- [ ] **Step 1: 编写 fallback 池的失败测试**

在 `test_content_integrator.py` 添加：

```python
def test_distribute_content_fallback_pool():
    """未匹配内容应进入 fallback 池重新分配"""
    integrator = ContentIntegrator()

    parsed = ParsedPrompt(
        topic="产品培训",
        audience="全员",
        position="员工",
        industry="通用",
        duration="60分钟",
        style="专业严谨",
        objectives=["了解企业文化", "掌握产品知识"],
        special_requirements=[],
        forbidden_content=[],
        num_modules=2,
        outline_structure={"模块拆解层": ["模块1-企业文化", "模块2-产品知识"]}
    )

    # 内容与模块无关键词匹配
    file_contents = ["这是一段通用的公司介绍内容，与具体模块无直接关联"]

    result = integrator.integrate(parsed, file_contents)

    # 内容应至少分配到一个模块（fallback 到第一个）
    total = sum(len(v) for v in result.module_contents.values())
    assert total >= 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_distribute_content_fallback_pool -v
```
Expected: FAIL - 内容被丢弃

- [ ] **Step 3: 修改 integrate 方法添加 fallback 逻辑**

将 `integrate` 方法修改为：

```python
def integrate(self, parsed: ParsedPrompt, file_contents: list[str]) -> IntegratedContent:
    """按大纲结构分配内容，碎片化内容结构化整合"""
    module_contents: dict[str, list[str]] = {}

    # 获取模块列表
    modules = self._get_modules_from_outline(parsed.outline_structure)

    # 初始化模块内容
    for module in modules:
        module_contents[module] = []

    # 收集未分配的内容
    fallback_pool: list[str] = []

    # 分配文件内容到模块
    for content in file_contents:
        distributed = self._distribute_content(content, module_contents, modules)
        if not distributed:
            fallback_pool.append(content)

    # Fallback 池处理：按学习目标关键词重新匹配
    if fallback_pool and parsed.objectives:
        self._process_fallback_pool(fallback_pool, module_contents, modules, parsed.objectives)

    # 提取案例库
    case_library = self._extract_cases(file_contents)

    # 提取配套材料
    supplementary = self._extract_supplementary(file_contents)

    return IntegratedContent(
        module_contents=module_contents,
        case_library=case_library,
        supplementary_materials=supplementary
    )
```

- [ ] **Step 4: 修改 _distribute_content 返回分配状态**

将 `_distribute_content` 方法的返回类型改为 bool：

```python
def _distribute_content(self, content: str, module_contents: dict[str, list[str]], modules: list[str]) -> bool:
    """将内容分配到对应模块，返回是否分配成功"""
    # ... 现有逻辑 ...

    # 多模块分配
    max_score = max(module_scores.values()) if module_scores else 0
    threshold = max_score * 0.3

    distributed = False
    for module, score in module_scores.items():
        if score >= threshold and score > 0:
            module_contents[module].append(content)
            distributed = True

    return distributed
```

- [ ] **Step 5: 添加 _process_fallback_pool 方法**

在 `_get_modules_from_outline` 方法后添加：

```python
def _process_fallback_pool(self, fallback_pool: list[str], module_contents: dict[str, list[str]], modules: list[str], objectives: list[str]):
    """将未分配内容按学习目标关键词重新分配"""
    # 提取学习目标关键词
    objective_keywords: list[str] = []
    for obj in objectives:
        keywords = re.findall(r'[\w]+', obj)
        objective_keywords.extend([k for k in keywords if len(k) > 1])

    # 尝试用学习目标关键词匹配
    for content in fallback_pool:
        best_module = None
        best_score = 0
        for module in modules:
            score = sum(1 for kw in objective_keywords if re.search(rf'\b{re.escape(kw)}\b', content))
            if score > best_score:
                best_score = score
                best_module = module

        if best_module and best_score > 0:
            module_contents[best_module].append(content)
        elif modules:
            # 仍有剩余则分配给第一个模块
            module_contents[modules[0]].append(content)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_distribute_content_fallback_pool -v
```
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/content_integrator.py tests/plugins/training/skills/lecture_generation/test_content_integrator.py
git commit -m "feat: add fallback pool for unmatched content"
```

---

## Task 4: 案例提取升级（去除500字符限制）

**Files:**
- Modify: `gbrain/plugins/training/skills/lecture_generation/content_integrator.py:70-112`
- Test: `tests/plugins/training/skills/lecture_generation/test_content_integrator.py`

- [ ] **Step 1: 编写案例完整提取的失败测试**

在 `test_content_integrator.py` 添加：

```python
def test_extract_cases_no_truncation():
    """案例提取不应有500字符限制"""
    integrator = ContentIntegrator()

    # 创建一个超过500字符的案例内容
    long_case = "案例一：这是一个非常长的客户成功案例。" + "这是详细描述。" * 100

    file_contents = [f"销售培训内容包括：\n\n{long_case}"]

    result = integrator.integrate(
        ParsedPrompt(
            topic="销售培训",
            audience="销售",
            position="销售",
            industry="通用",
            duration="60分钟",
            style="专业严谨",
            objectives=["掌握销售技巧"],
            special_requirements=[],
            forbidden_content=[],
            num_modules=1,
            outline_structure={"模块拆解层": ["模块1"]}
        ),
        file_contents
    )

    if result.case_library:
        # 案例内容应接近原始长度（允许句号分割差异）
        assert len(result.case_library[0]["content"]) > 500
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_extract_cases_no_truncation -v
```
Expected: FAIL - 案例被截断到500字符

- [ ] **Step 3: 修改 _extract_cases 方法去除字符限制**

将 `_extract_cases` 方法修改为：

```python
def _extract_cases(self, file_contents: list[str]) -> list[dict]:
    """从文件内容中提取案例，使用多种模式匹配"""
    cases = []
    # 案例模式：匹配"案例"或"case"开头的独立段落或章节
    case_patterns = [
        # 模式1: "案例N：" 或 "案例N：" 后面跟内容（完整段落）
        re.compile(r'案例\s*[\d零一二三四五六七八九十百]+[：:]\s*(.{20,})?(?=\n\n|\n案例|\Z)', re.DOTALL),
        # 模式2: "案例：" 后面跟内容（完整段落）
        re.compile(r'案例\s*：[：:]\s*(.{20,})?(?=\n\n|\Z)', re.DOTALL),
        # 模式3: 独立的案例标题行后面跟内容段落
        re.compile(r'^#{1,3}\s*案例[^\n]*\n+(.{20,})?(?=\n#{1,3}\s|\Z)', re.DOTALL | re.MULTILINE),
        # 模式4: "CASE" 或 "Case" 开头的内容块
        re.compile(r'(?:^|\n)(CASE|case|Case)[^\n]*\n+(.{20,})?(?=\n(?:CASE|case|Case)|\Z)', re.DOTALL | re.MULTILINE),
    ]

    for content in file_contents:
        matched_cases: set[str] = set()
        for pattern in case_patterns:
            for match in pattern.finditer(content):
                case_content = match.group(1).strip() if match.group(1) else ""
                if case_content and case_content not in matched_cases:
                    matched_cases.add(case_content)
                    # 按自然段落分割，最多保留3段
                    paragraphs = re.split(r'(?<=[。！？\n])', case_content)
                    case_text = ''.join(paragraphs[:3])
                    cases.append({
                        "content": case_text,
                        "type": "case"
                    })

        # 如果没有通过模式匹配到，但文件包含"案例"关键词，
        # 则尝试提取包含关键词的完整段落（不截断）
        if not matched_cases and ('案例' in content or re.search(r'\bcase\b', content, re.I)):
            sentences = re.split(r'[\n。]+', content)
            for sentence in sentences:
                if '案例' in sentence or re.search(r'\bcase\b', sentence, re.I):
                    case_text = sentence.strip()
                    if case_text and len(case_text) > 10:
                        cases.append({
                            "content": case_text,
                            "type": "case"
                        })
                    break

    return cases
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py::test_extract_cases_no_truncation -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add gbrain/plugins/training/skills/lecture_generation/content_integrator.py tests/plugins/training/skills/lecture_generation/test_content_integrator.py
git commit -m "feat: remove 500-char limit in case extraction"
```

---

## Task 5: 完整测试验证

- [ ] **Step 1: 运行所有测试**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m pytest tests/plugins/training/skills/lecture_generation/test_content_integrator.py -v
```
Expected: 全部 PASS

- [ ] **Step 2: 运行 lint 检查**

```bash
cd /Users/forxia/GBRAIN-AGENT && python -m ruff check gbrain/plugins/training/skills/lecture_generation/content_integrator.py gbrain/plugins/training/skills/lecture_generation/models.py
```

- [ ] **Step 3: 提交最终变更**

```bash
git add -A && git commit -m "feat: implement ContentIntegrator semantic enhancement

- Multi-module content distribution (0.3 * max_score threshold)
- Fallback pool for unmatched content
- Case extraction without 500-char limit
- Synonym expansion for keyword matching

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验证指标

| 指标 | 预期 |
|------|------|
| 多模块分配 | 同一内容可分配给 2+ 模块 |
| Fallback 池 | 未匹配内容不再丢弃 |
| 案例完整性 | 案例可超过 500 字符 |
| 同义词扩展 | "电话" 可匹配 "话术" |
| 现有测试 | 全部通过 |
