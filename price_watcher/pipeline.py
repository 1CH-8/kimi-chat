"""主流程编排：把采集 → 清洗 → 排序 → 推荐 → 存储 串起来."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Dict, List

from . import config
from .processor.cleaner import clean_and_deduplicate
from .processor.recommender import recommend_best
from .processor.sorter import sort_by_price
from .scraper.base import Product
from .scraper.factory import ScraperFactory
from .storage.history import PriceHistory

logger = logging.getLogger(__name__)


def run_pipeline(
    keyword: str,
    platforms: List[str] | None = None,
    max_items_per_platform: int = 20,
    use_mock: bool = True,
    save_history: bool = True,
) -> Dict:
    """执行一次完整的采集 + 处理流水线，返回结果字典."""
    platforms = platforms or config.PLATFORMS

    # 1) 采集
    raw_products = ScraperFactory.search_all(
        keyword=keyword,
        platforms=platforms,
        max_items_per_platform=max_items_per_platform,
        use_mock=use_mock,
    )

    # 2) 清洗去重
    cleaned = clean_and_deduplicate(raw_products)

    # 3) 按价格升序
    sorted_products = sort_by_price(cleaned, ascending=True)

    # 4) 性价比推荐
    recommendations = recommend_best(sorted_products, top_n=5)

    # 5) 存储历史
    if save_history:
        ph = PriceHistory()
        ph.record(keyword, cleaned)

    # 6) 汇总统计
    platform_stats = _platform_stats(cleaned)

    return {
        "keyword": keyword,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_count": len(raw_products),
        "cleaned_count": len(cleaned),
        "platform_stats": platform_stats,
        "products": [p.to_dict() for p in sorted_products],
        "recommendations": recommendations,
    }


def _platform_stats(products: List[Product]) -> Dict[str, Dict]:
    stats: Dict[str, List[Product]] = {}
    for p in products:
        stats.setdefault(p.platform, []).append(p)
    summary = {}
    for plat, items in stats.items():
        prices = [p.price for p in items]
        summary[plat] = {
            "count": len(items),
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": round(sum(prices) / len(prices), 2),
            "total_sales": sum(p.sales for p in items),
        }
    return summary


def save_result(result: Dict, out_path: str | None = None) -> str:
    """把结果存成 JSON，返回实际路径."""
    out_path = out_path or os.path.join(
        config.JSON_OUTPUT_DIR,
        f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return out_path
