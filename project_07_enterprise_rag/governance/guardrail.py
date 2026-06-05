"""安全与隐私治理：Prompt 注入防御与 PII 数据掩码。"""

from __future__ import annotations

import re

from langchain_core.documents import Document


class GuardrailManager:
    """输入与输出安全防护栏。"""

    def __init__(self):
        # 常见敏感 Prompt 注入模式特征
        self.injection_patterns = [
            r"ignore\s+(?:the\s+)?above\s+instructions",
            r"忽略(?:以上|前面)的?指令",
            r"system\s+prompt",
            r"你现在是",
            r"你被设定为",
            r"bypass\s+safety",
        ]
        self.email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        self.phone_pattern = r"(?<!\d)(?:\+86)?1[3-9]\d{9}(?!\d)"

    def mask_pii(self, text: str) -> str:
        """纯粹的 PII 脱敏过滤。"""
        if not text:
            return ""
        masked = text
        masked = re.sub(self.email_pattern, "[EMAIL_MASKED]", masked)
        masked = re.sub(self.phone_pattern, "[PHONE_MASKED]", masked)
        return masked

    def mask_value(self, value):
        """递归脱敏任意可序列化结构中的字符串值。"""
        if isinstance(value, str):
            return self.mask_pii(value)
        if isinstance(value, dict):
            return {key: self.mask_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.mask_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.mask_value(item) for item in value)
        return value

    def mask_document(self, doc: Document) -> Document:
        """脱敏 Document 正文和 metadata，避免原始 PII 进入 State/checkpoint。"""
        return Document(
            page_content=self.mask_pii(doc.page_content),
            metadata=self.mask_value(dict(doc.metadata or {})),
        )

    def detect_injection(self, text: str) -> tuple[bool, str]:
        """专门用于在图内部针对脱敏后的安全文本检测注入。"""
        if not text:
            return True, ""
        for pattern in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "检测到潜在的 Prompt 注入攻击。"
        return True, ""
