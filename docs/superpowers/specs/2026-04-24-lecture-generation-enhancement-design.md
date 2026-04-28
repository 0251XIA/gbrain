# 课件生成能力增强设计方案

**日期：** 2026-04-24
**分支：** feat/enhance-lecture-generation
**状态：** 已批准

---

## 1. 背景与目标

当前 ContentIntegrator 的内容分配逻辑存在以下问题：
1. 每条内容仅分配给单一最高分模块，其余内容丢弃
2. 未匹配内容无 fallback 机制
3. 案例提取限制 500 字符，导致内容不完整
4. 关键词匹配缺乏同义词扩展

**目标：** 提升知识库内容的利用率和语义匹配精度

---

## 2. 改进方案（语义增强）

### 2.1 多模块分配

**问题：** 当前 `_distribute_content()` 仅分配给单一模块

**改进：**
- 计算每条内容与所有模块的匹配分数
- 分配给所有分数超过 `0.3 * 最高分` 的模块
- 保留内容副本到多个相关模块

```python
# 分配阈值 = 0.3 * max_score
threshold = max_score * 0.3
for module_name, score in module_scores.items():
    if score >= threshold and score > 0:
        module_contents[module_name].append(content)
```

### 2.2 未匹配内容 Fallback 池

**问题：** 最佳分数为 0 的内容被直接丢弃

**改进：**
- 收集所有未匹配内容到 fallback_pool
- 按学习目标关键词二次匹配
- 仍有剩余则分配给第一个模块

```python
# 第一轮：多模块分配
# 第二轮：fallback 重新匹配
for content in fallback_pool:
    best_module, best_score = self._find_best_module(content, module_keywords)
    if best_module:
        module_contents[best_module].append(content)
```

### 2.3 案例提取升级

**问题：** `case = content[:500]` 截断案例内容

**改进：**
- 使用正则提取完整自然段落
- 按句号、换行等自然分隔符判断段落边界
- 不设字符数硬限制

```python
paragraphs = re.split(r'(?<=[。！？\n])', content)
case = ''.join(paragraphs[:3])  # 最多3个自然段
```

### 2.4 同义词扩展

**问题：** 关键词匹配缺乏语义等价词

**改进：**
- 建立领域同义词映射表
- 匹配时同时检查原词和同义词

```python
SYNONYM_MAP = {
    "电话": ["话术", "沟通技巧", "通话"],
    "销售": ["营销", "推销", "商务"],
    "客户": ["顾客", "用户", "采购方"],
}

def _expand_keywords(self, keywords):
    expanded = set(keywords)
    for word in keywords:
        if word in SYNONYM_MAP:
            expanded.update(SYNONYM_MAP[word])
    return expanded
```

---

## 3. 文件变更

| 文件 | 变更类型 |
|------|----------|
| `gbrain/plugins/training/skills/lecture_generation/content_integrator.py` | 核心修改 |
| `gbrain/plugins/training/skills/lecture_generation/models.py` | 新增同义词配置 |

---

## 4. 验证指标

- 知识库内容利用率提升（丢弃率 < 10%）
- 内容分配覆盖模块数增加（从平均 1.2 → 2.0+）
- 案例完整性提升（无截断案例）

---

## 5. 测试计划

1. 单元测试：多模块分配逻辑
2. 单元测试：fallback 池内容重新分配
3. 集成测试：完整流程输出验证
