"""
GBrain 内容分类器
"""

import re
from typing import Tuple

CATEGORY_RULES = {
    "销售": [
        (r"销售|客户开发|演示|报价|谈判|促成|成交", 3.0),
        (r"续费|续期|合同签署|签单", 3.0),
        (r"销售漏斗|销售过程|销售经验|销售技巧", 3.0),
        (r"客户.*画像|客户分类|A类客户|B类客户|C类客户", 2.5),
        (r"客户.*维护|客户.*跟进|客户.*意向|客户.*需求", 2.5),
        (r"逼单|促成|促单|关单", 2.5),
        (r"商务报价|套餐|代金券|优惠|折扣", 2.0),
        (r"友商|竞争对手|竞品|对比", 1.5),
    ],
    "服务": [
        (r"服务|售后|客服|技术支持", 2.5),
        (r"问题.*解决|问题.*解答|问题.*沟通", 2.5),
        (r"客户.*服务|客户服务|服务.*客户", 2.0),
        (r"服务.*流程|处理.*流程|服务.*标准", 2.0),
        (r"服务.*质量|服务.*体验|服务.*满意", 2.0),
        (r"快速.*响应|及时.*处理|工单|问题.*反馈", 2.0),
    ],
    "技术": [
        (r"技术|功能|产品功能|系统架构", 2.5),
        (r"API|接口|开发|SDK", 2.5),
        (r"电子签章|数字签名|身份认证|印章.*管理", 2.0),
        (r"嵌入.*签|页面.*签|移动.*签|H5.*签", 2.0),
        (r"签.*验|验.*签|签.*名|盖章", 1.5),
        (r"私有化|本地部署|云.*部署", 1.5),
        (r"安全|加密|合规|法律效力", 1.5),
    ],
}

DEFAULT_CATEGORY = "通用"


class Classifier:
    """内容分类器"""

    def classify(self, content: str, title: str = "") -> Tuple[str, float]:
        """对内容进行分类"""
        text = (title + " " + content).lower()
        scores = {}

        for category, rules in CATEGORY_RULES.items():
            score = 0.0
            for pattern, weight in rules:
                if re.search(pattern, text):
                    score += weight
            scores[category] = score

        if not scores or max(scores.values()) == 0:
            return DEFAULT_CATEGORY, 0.0

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        confidence = min(best_score / 5.0, 1.0) if best_score > 0 else 0.0

        return best_category, confidence
