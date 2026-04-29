#!/usr/bin/env python3
"""
GBrain Web 服务器启动脚本
"""

import sys
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, "/Users/forxia/gbrain")


if __name__ == "__main__":
    uvicorn.run(
        "gbrain.web.app:create_app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        timeout_keep_alive=300  # 5分钟超时
    )