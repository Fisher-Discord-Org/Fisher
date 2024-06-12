from __future__ import annotations

from typing import Self
from weakref import WeakValueDictionary


class SingletonMeta(type):
    _instances: WeakValueDictionary[type, SingletonMeta] = WeakValueDictionary()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Singleton(metaclass=SingletonMeta):
    @classmethod
    def get_instance(cls: type[Self]) -> Self | None:
        return cls._instances.get(cls, None)
