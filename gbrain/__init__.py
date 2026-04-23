"""
GBrain - AI Agent 记忆与知识管理系统
"""

from .mcp_server import GBrainMCP, run_stdio_server, run_http_server

# 兼容旧接口
class GBrain(GBrainMCP):
    """GBrain 主类（兼容性别名）"""
    pass


__all__ = ['GBrain', 'GBrainMCP', 'run_stdio_server', 'run_http_server']
__version__ = '0.1.0'
