"""
GBrain 插件系统

插件目录结构：
gbrain/plugins/
├── __init__.py          # 插件基类 + 插件管理器
├── training/            # 培训模块插件
│   ├── __init__.py
│   ├── __plugin__.py   # 插件入口（必须）
│   ├── models.py       # 数据模型
│   ├── events.py       # 事件总线
│   ├── course_gen.py   # 课件生成器
│   ├── state_machine.py# 学习状态机
│   ├── quiz_engine.py  # 考核引擎
│   ├── task_pusher.py  # 任务推送器
│   └── dashboard.py    # 数据看板
└── ...                 # 其他插件目录

插件开发规范：
1. 每个插件目录下必须有 __plugin__.py 作为入口
2. 插件类必须继承 Plugin 基类
3. 插件通过 PluginManager 自动发现和加载
4. 插件间通过 EventBus 通信
"""

import os
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class PluginHook(Enum):
    """插件生命周期钩子"""
    BEFORE_LOAD = "before_load"
    AFTER_LOAD = "after_load"
    BEFORE_UNLOAD = "before_unload"
    AFTER_UNLOAD = "after_unload"


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: list[str] = field(default_factory=list)


class Plugin(ABC):
    """插件基类"""

    def __init__(self):
        self._enabled = False
        self._metadata: Optional[PluginMetadata] = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass

    @property
    def enabled(self) -> bool:
        return self._enabled

    def on_load(self) -> bool:
        """插件加载时调用，返回 True 表示加载成功"""
        self._enabled = True
        return True

    def on_unload(self):
        """插件卸载时调用"""
        self._enabled = False

    def on_event(self, event: 'Event'):
        """处理事件（由 EventBus 调用）"""
        pass


@dataclass
class Event:
    """事件对象"""
    id: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    source: str = ""  # employee_id | system | hr_action
    payload: dict = field(default_factory=dict)
    consumed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "consumed": self.consumed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        data = dict(data)
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EventBus:
    """事件总线 - 插件间通信中枢"""

    _instance: Optional['EventBus'] = None

    @classmethod
    def get_instance(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._event_log: list[Event] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event):
        """发布事件"""
        self._event_log.append(event)
        event.consumed = False

        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
                event.consumed = True
            except Exception as e:
                print(f"事件处理错误 [{event.event_type}]: {e}")

    def get_history(self, event_type: str = None, limit: int = 100) -> list[Event]:
        """获取事件历史"""
        if event_type:
            return [e for e in self._event_log if e.event_type == event_type][-limit:]
        return self._event_log[-limit:]

    def clear_history(self):
        """清空事件历史"""
        self._event_log.clear()


class PluginManager:
    """插件管理器"""

    def __init__(self, plugins_dir: str = None):
        if plugins_dir is None:
            from gbrain.config import BASE_PATH
            plugins_dir = BASE_PATH / "gbrain" / "plugins"
        self.plugins_dir = plugins_dir
        self._plugins: dict[str, Plugin] = {}
        self._event_bus = EventBus.get_instance()

    def discover_plugins(self) -> list[str]:
        """发现所有插件"""
        if not self.plugins_dir.exists():
            return []

        plugins = []
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "__plugin__.py").exists():
                plugins.append(item.name)
        return plugins

    def load_plugin(self, name: str) -> bool:
        """加载指定插件"""
        if name in self._plugins:
            return True  # 已加载

        plugin_path = self.plugins_dir / name / "__plugin__.py"
        if not plugin_path.exists():
            print(f"插件不存在: {name}")
            return False

        try:
            # 动态导入插件模块
            module_name = f"gbrain.plugins.{name}.__plugin__"
            module = importlib.import_module(module_name)

            # 查找插件类（必须继承 Plugin）
            plugin_class = None
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                    plugin_class = obj
                    break

            if plugin_class is None:
                print(f"插件 {name} 未找到 Plugin 子类")
                return False

            plugin_instance = plugin_class()
            if plugin_instance.on_load():
                self._plugins[name] = plugin_instance
                print(f"插件已加载: {name} v{plugin_instance.metadata.version}")
                return True

        except Exception as e:
            print(f"插件加载失败 [{name}]: {e}")
            return False

        return False

    def unload_plugin(self, name: str):
        """卸载指定插件"""
        if name not in self._plugins:
            return

        plugin = self._plugins[name]
        plugin.on_unload()
        del self._plugins[name]
        print(f"插件已卸载: {name}")

    def load_all(self):
        """加载所有发现的插件"""
        for name in self.discover_plugins():
            self.load_plugin(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """列出所有已加载插件"""
        return [
            {
                "name": p.metadata.name,
                "version": p.metadata.version,
                "description": p.metadata.description,
                "enabled": p.enabled
            }
            for p in self._plugins.values()
        ]


# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def get_event_bus() -> EventBus:
    return EventBus.get_instance()
