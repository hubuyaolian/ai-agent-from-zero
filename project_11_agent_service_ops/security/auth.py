"""API Key 鉴权教学实现。"""

from __future__ import annotations

from dataclasses import dataclass

from project_11_agent_service_ops.config import (
    DEFAULT_API_KEYS,
    DEFAULT_TENANT_ID,
    DEFAULT_USER_ID,
)


class AuthenticationError(RuntimeError):
    """认证失败。"""


@dataclass(frozen=True)
class AuthContext:
    """通过鉴权后得到的调用方上下文。"""

    user_id: str
    tenant_id: str
    api_key_id: str
    scopes: frozenset[str]


class APIKeyAuthenticator:
    """最小 API Key 鉴权器。

    生产系统应接入密钥管理系统，并存储 hash 后的 key。这里保留明文 key
    是为了让课程脚本可以开箱运行。
    """

    def __init__(self, key_map: dict[str, AuthContext]) -> None:
        self._key_map = key_map

    @classmethod
    def from_config(cls) -> "APIKeyAuthenticator":
        """从环境变量构造本地教学鉴权器。"""
        key_map = {
            api_key: AuthContext(
                user_id=DEFAULT_USER_ID,
                tenant_id=DEFAULT_TENANT_ID,
                api_key_id=f"local-key-{index}",
                scopes=frozenset({"chat", "stream", "metrics", "eval"}),
            )
            for index, api_key in enumerate(DEFAULT_API_KEYS, start=1)
        }
        return cls(key_map)

    def authenticate(self, api_key: str | None) -> AuthContext:
        """校验 API Key 并返回调用方上下文。"""
        if not api_key:
            raise AuthenticationError("缺少 X-API-Key 请求头")
        context = self._key_map.get(api_key)
        if context is None:
            raise AuthenticationError("API Key 无效")
        return context

    @staticmethod
    def require_scope(context: AuthContext, scope: str) -> None:
        """检查调用方是否具备某个权限。"""
        if scope not in context.scopes:
            raise AuthenticationError(f"缺少权限: {scope}")
