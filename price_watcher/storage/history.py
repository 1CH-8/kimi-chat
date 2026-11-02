"""价格历史存储：基于 JSON 文件的轻量实现, 可用于画价格趋势图."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from .. import config
from ..scraper.base import Product


class PriceHistory:
    """按关键词记录历史价格快照."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.HISTORY_DB
        self._data: Dict[str, List[dict]] = self._load()

    # -------- 内部 --------
    def _load(self) -> Dict[str, List[dict]]:
        if not os.path.exists(self.db_path):
            return {}
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # -------- 对外 --------
    def record(self, keyword: str, products: List[Product]):
        """保存一次快照：记录每个平台的最低/平均/最高价格."""
        stats = defaultdict(list)
        for p in products:
            stats[p.platform].append(p.price)

        snapshot = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platforms": {},
            "summary": {
                "total_items": len(products),
            },
        }
        for plat, prices in stats.items():
            snapshot["platforms"][plat] = {
                "min": min(prices),
                "max": max(prices),
                "avg": round(sum(prices) / len(prices), 2),
                "count": len(prices),
            }
            snapshot["summary"][f"{plat}_min"] = min(prices)

        self._data.setdefault(keyword, []).append(snapshot)
        self._save()

    def get_history(self, keyword: str, days: int = 30) -> List[dict]:
        """取最近 N 天的历史快照."""
        snapshots = self._data.get(keyword, [])
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        return [s for s in snapshots if s["timestamp"] >= cutoff]

    def get_trend_data(self, keyword: str, days: int = 30) -> Dict[str, List]:
        """返回 ECharts 可用的趋势数据."""
        history = self.get_history(keyword, days)
        result = {"timestamps": [], "min_prices": [], "avg_prices": [], "platform_min": {}}
        for s in history:
            result["timestamps"].append(s["timestamp"][:16].replace(" ", "\n"))
            result["min_prices"].append(s["summary"].get("total_min", None) or min(
                [v["min"] for v in s["platforms"].values()], default=None
            ))
            all_avgs = [v["avg"] for v in s["platforms"].values()]
            result["avg_prices"].append(round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else None)
            for plat, v in s["platforms"].items():
                result["platform_min"].setdefault(plat, []).append(v["min"])
        return result

    def clear(self, keyword: str | None = None):
        if keyword is None:
            self._data.clear()
        else:
            self._data.pop(keyword, None)
        self._save()
