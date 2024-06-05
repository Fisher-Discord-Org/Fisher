from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class BaseEngine(ABC):
    def __init__(self, cog_name: str, url: str):
        self.cog_name = cog_name
        self.db_engine = create_async_engine(url, pool_pre_ping=True)
        self.Session = async_sessionmaker(self.db_engine, expire_on_commit=False)

    @abstractmethod
    async def init_models(self, base_cls: type[DeclarativeBase]) -> None:
        raise NotImplementedError


class SQLiteEngine(BaseEngine):
    def __init__(self, cog_name: str, url: str):
        super().__init__(cog_name=cog_name, url=url)

    async def init_models(self, base_cls: type[DeclarativeBase]) -> None:
        async with self.db_engine.begin() as conn:
            await conn.run_sync(base_cls.metadata.create_all)
