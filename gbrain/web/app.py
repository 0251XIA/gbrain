"""
GBrain Web 应用 - FastAPI 入口
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from gbrain.config import BASE_PATH


def create_app() -> FastAPI:
    app = FastAPI(
        title="GBrain Training",
        description="岗位培训 Agent - Web 学习平台",
        version="0.1.0"
    )

    # 静态文件和模板
    static_dir = BASE_PATH / "gbrain" / "web" / "static"
    templates_dir = BASE_PATH / "gbrain" / "web" / "templates"

    static_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(templates_dir))

    # 注册路由
    from .routes import register_routes
    register_routes(app, templates)

    return app
