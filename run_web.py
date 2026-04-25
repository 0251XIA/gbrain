#!/usr/bin/env python3
"""
GBrain Web 服务器启动脚本
"""

import sys
import uvicorn

# 添加项目路径
sys.path.insert(0, "/Users/forxia/gbrain")


if __name__ == "__main__":
    uvicorn.run(
        "gbrain.web.app:create_app",
        host="0.0.0.0",
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8080,
        reload=True
    )
