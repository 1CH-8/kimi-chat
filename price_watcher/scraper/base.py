"""爬虫基类 —— 定义统一的采集接口与通用工具."""
from __future__ import annotations

import logging
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .. import config

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """统一的商品数据结构（平台无关）."""
    platform: str           # 平台标识 jd/taobao/pdd
    name: str               # 商品名称
    price: float            # 当前价格（元）
    original_price: Optional[float] = None  # 划线价
    sales: int = 0          # 销量（件/月销）
    shop_name: str = ""     # 店铺名
    shop_score: Optional[float] = None  # 店铺评分（0-5）
    url: str = ""           # 商品链接
    product_id: str = ""    # 平台内部商品ID
    image_url: str = ""     # 商品主图
    collected_at: str = ""  # 采集时间戳

    def to_dict(self) -> dict:
        return asdict(self)


class BaseScraper(ABC):
    """所有平台爬虫的父类.

    子类只需实现 ``_build_url`` / ``_parse`` / ``_extract_fields`` 三个方法.
    """

    platform: str = "base"
    platform_name: str = "通用"

    def __init__(self, use_mock: bool = True):
        self.session = requests.Session()
        self.session.headers.update(config.DEFAULT_HEADERS)
        self.use_mock = use_mock

    # -------- 对外接口 --------
    def search(self, keyword: str, max_items: int = 20) -> List[Product]:
        """按关键词搜索商品并返回结构化列表."""
        logger.info(f"[{self.platform_name}] 搜索: {keyword} (最多 {max_items} 条)")

        if self.use_mock:
            results = self._mock_search(keyword, max_items)
            logger.info(f"[{self.platform_name}] 返回模拟数据 {len(results)} 条")
            return results

        try:
            url = self._build_url(keyword, max_items)
            html = self._fetch(url)
            raw_items = self._parse(html)
            products = self._extract_fields(raw_items, keyword)[:max_items]
            logger.info(f"[{self.platform_name}] 成功采集 {len(products)} 条")
            return products
        except Exception as exc:
            logger.warning(f"[{self.platform_name}] 真实采集失败: {exc}, 回退到模拟数据")
            return self._mock_search(keyword, max_items)

    # -------- 抽象方法 --------
    @abstractmethod
    def _build_url(self, keyword: str, max_items: int) -> str: ...

    @abstractmethod
    def _parse(self, html: str) -> list: ...

    @abstractmethod
    def _extract_fields(self, raw_items: list, keyword: str) -> List[Product]: ...

    @abstractmethod
    def _mock_search(self, keyword: str, max_items: int) -> List[Product]:
        """模拟数据生成（用于演示或反爬拦截时的回退）."""
        ...

    # -------- 工具方法 --------
    def _fetch(self, url: str) -> str:
        """带重试、UA 随机化、间隔控制的 GET 请求."""
        last_exc = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self.session.headers["User-Agent"] = random.choice(self._user_agents())
                time.sleep(random.uniform(*config.REQUEST_INTERVAL))
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except requests.RequestException as exc:
                last_exc = exc
                logger.debug(f"请求失败 ({attempt}/{config.MAX_RETRIES}): {url} -> {exc}")
                time.sleep(2 * attempt)
        raise RuntimeError(f"请求 {url} 最终失败: {last_exc}")

    @staticmethod
    def _user_agents() -> List[str]:
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 "
            "Mobile/15E148 Safari/604.1",
        ]

    @staticmethod
    def _to_float(text: str) -> Optional[float]:
        if not text:
            return None
        matched = re.search(r"[\d.]+", text.replace(",", ""))
        return float(matched.group()) if matched else None

    @staticmethod
    def _to_int(text: str) -> int:
        if not text:
            return 0
        text = text.replace(",", "").replace("+", "").strip()
        # 处理 "1.2万+" 之类
        if "万" in text:
            num = BaseScraper._to_float(text.replace("万", ""))
            return int((num or 0) * 10000)
        if "千" in text:
            num = BaseScraper._to_float(text.replace("千", ""))
            return int((num or 0) * 1000)
        matched = re.search(r"\d+", text)
        return int(matched.group()) if matched else 0

    @staticmethod
    def _to_score(text: str) -> Optional[float]:
        score = BaseScraper._to_float(text)
        if score is None:
            return None
        # 某些平台满分是 100，归一化到 5 分制
        if score > 10:
            score = round(score / 20, 1)
        return score


def make_mock_product(
    platform: str,
    keyword: str,
    index: int,
    price_range: tuple = (50, 2000),
    now: str = "",
) -> Product:
    """辅助函数：生成一条模拟商品数据."""
    import random as _r
    brand_suffix = ["旗舰版", "尊享版", "青春版", "标准版", "Pro", "Max", "Ultra", "Lite"]
    brand = _r.choice(["精选", "优品", "好物", "臻选", "品质", "正品"])
    suffix = _r.choice(brand_suffix)
    pmin, pmax = price_range
    base_price = round(_r.uniform(pmin, pmax), 2)
    original_price = round(base_price * _r.uniform(1.1, 1.6), 2)
    sales = _r.choice([_r.randint(50, 2000), _r.randint(2000, 10000), _r.randint(10000, 80000)])
    shop_score = round(_r.uniform(3.8, 5.0), 1)
    shop_name = f"{_r.choice(['优品', '臻选', '好物', '优选', '精选'])}{keyword[:2]}专营店"
    return Product(
        platform=platform,
        name=f"{keyword} {brand}{suffix} {index+1}号".strip(),
        price=base_price,
        original_price=original_price,
        sales=sales,
        shop_name=shop_name,
        shop_score=shop_score,
        url=f"https://{platform}.example.com/item/{index+100000+index}",
        product_id=f"{platform}_{index+100000+index}",
        image_url="",
        collected_at=now,
    )
