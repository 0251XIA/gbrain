"""
培训插件入口
"""

from gbrain.plugins import Plugin, PluginMetadata


class TrainingPlugin(Plugin):
    """培训插件"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="training",
            version="0.1.0",
            description="岗位培训 Agent 插件 - 课件生成、学习引导、考核输出",
            author="GBrain Team"
        )

    def on_load(self) -> bool:
        super().on_load()
        # TODO: 初始化各子模块
        # - EventBus 订阅
        # - 数据库表初始化
        # - 企微客户端初始化
        return True

    def on_unload(self):
        # TODO: 清理资源
        super().on_unload()
