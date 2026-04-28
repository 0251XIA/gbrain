#!/usr/bin/env python3
"""
初始化培训模块示例数据
"""

import sys
sys.path.insert(0, "/Users/forxia/gbrain")

from gbrain.plugins.training.service import get_training_service
from gbrain.plugins.training.models import QuizItem


def init_sample_data():
    service = get_training_service()

    # 创建示例员工
    print("创建员工...")
    emp1 = service.create_employee(
        name="张三",
        department="销售部",
        position="销售经理",
        role="employee"
    )
    emp2 = service.create_employee(
        name="李四",
        department="技术部",
        position="后端开发",
        role="employee"
    )
    emp3 = service.create_employee(
        name="王五",
        department="人力资源",
        position="HR主管",
        role="hr"
    )
    print(f"创建员工: {emp1.name}, {emp2.name}, {emp3.name}")

    # 创建入职培训任务
    print("\n创建入职培训任务...")
    onboarding_task = service.create_task(
        title="新员工入职培训",
        description="帮助新员工快速了解公司制度、流程、文化",
        task_type="onboarding",
        deadline="2026-05-15",
        priority=1,
        content="""# 新员工入职培训

## 第一章 公司简介
欢迎加入我们的公司！我们是一家专注于企业知识管理的高科技公司。

## 第二章 公司制度
1. 工作时间：周一至周五 9:00-18:00
2. 考勤制度：请使用企业微信打卡
3. 请假流程：提前3天申请，部门经理审批

## 第三章 财务制度
1. 报销标准：差旅费按级别区分
2. 报销流程：OA系统提交，财务审核
3. 发票要求：必须为增值税普通发票

## 第四章 企业文化
我们的核心价值观：创新、专业、协作、诚信
""",
        quiz_items=[
            QuizItem(
                id="q1",
                question="公司的工作时间是什么？",
                options=["9:00-18:00", "10:00-19:00", "8:00-17:00", "弹性时间"],
                correct_index=0,
                explanation="公司标准工作时间为周一至周五 9:00-18:00"
            ),
            QuizItem(
                id="q2",
                question="请假需要提前多少天申请？",
                options=["1天", "3天", "7天", "14天"],
                correct_index=1,
                explanation="请假需要提前3天申请，需部门经理审批"
            ),
            QuizItem(
                id="q3",
                question="公司核心价值观不包括以下哪一项？",
                options=["创新", "专业", "加班", "诚信"],
                correct_index=2,
                explanation="核心价值观是：创新、专业、协作、诚信"
            )
        ]
    )
    print(f"创建任务: {onboarding_task.title}")

    # 创建技能培训任务
    print("\n创建技能培训任务...")
    skill_task = service.create_task(
        title="销售技巧提升培训",
        description="提升销售团队的专业能力和成交率",
        task_type="skill",
        deadline="2026-05-20",
        priority=2,
        content="""# 销售技巧提升培训

## 第一模块：客户需求分析
1. 倾听客户需求
2. 开放式问题引导
3. 需求确认技巧

## 第二模块：产品介绍
1. FAB法则（特征-优势-利益）
2. 竞品对比分析
3. 解决客户异议

## 第三模块：成交技巧
1. 成交信号识别
2. 促成成交的方法
3. 售后服务承诺

## 第四模块：客户维护
1. 客户分类管理
2. 定期回访计划
3. 二次开发机会
""",
        quiz_items=[
            QuizItem(
                id="sq1",
                question="FAB法则中的B代表什么？",
                options=["特征", "优势", "利益", "需求"],
                correct_index=2,
                explanation="FAB = Feature(特征) + Advantage(优势) + Benefit(利益)"
            ),
            QuizItem(
                id="sq2",
                question="促成成交的最佳时机是什么？",
                options=["客户刚进门时", "客户表达购买信号时", "无论如何都要主动", "等客户主动提出"],
                correct_index=1,
                explanation="当客户表达购买信号时是促成成交的最佳时机"
            )
        ]
    )
    print(f"创建任务: {skill_task.title}")

    # 发布任务
    print("\n发布任务...")
    service.publish_task(onboarding_task.id)
    service.publish_task(skill_task.id)

    # 分配任务给员工
    print("\n分配任务...")
    p1 = service.assign_task_to_employee(onboarding_task.id, emp1.id)
    p2 = service.assign_task_to_employee(skill_task.id, emp1.id)
    p3 = service.assign_task_to_employee(onboarding_task.id, emp2.id)
    print(f"分配任务: 张三-入职培训, 张三-销售技巧, 李四-入职培训")

    print("\n✅ 示例数据初始化完成！")
    print(f"入职培训任务ID: {onboarding_task.id}")
    print(f"技能培训任务ID: {skill_task.id}")
    print(f"张三员工ID: {emp1.id}")
    print(f"李四员工ID: {emp2.id}")
    print(f"王五（HR）员工ID: {emp3.id}")


if __name__ == "__main__":
    init_sample_data()
