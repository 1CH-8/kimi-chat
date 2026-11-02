"""爬虫工厂 —— 根据平台名创建对应爬虫，并支持并发采集."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List

from .base import BaseScraper, Product
from .jd import JDScraper
from .taobao import TaobaoScraper
from .pdd import PDDScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    _registry = {
        "jd": JDScraper,
        "taobao": TaobaoScraper,
        "pdd": PDDScraper,
    }

    @classmethod
    def create(cls, platform: str, use_mock: bool = True) -> BaseScraper:
        platform = platform.lower()
        if platform not in cls._registry:
            raise ValueError(f"未知平台: {platform}, 可选: {list(cls._registry.keys())}")
        return cls._registry[platform](use_mock=use_mock)

    @classmethod
    def available_platforms(cls) -> List[str]:
        return list(cls._registry.keys())

    @classmethod
    def search_all(
        cls,
        keyword: str,
        platforms: Iterable[str] = ("jd", "taobao", "pdd"),
        max_items_per_platform: int = 20,
        use_mock: bool = True,
        max_workers: int = 3,
    ) -> List[Product]:
        """多平台并发采集."""
        platforms = list(platforms)
        results: List[Product] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(cls.create(p, use_mock=use_mock).search, keyword, max_items_per_platform): p
                for p in platforms
            }
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    results.extend(future.result())
                except Exception as exc:
                    logger.error(f"[{platform}] 采集异常: {exc}")
        return results
