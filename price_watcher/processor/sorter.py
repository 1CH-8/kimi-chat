"""排序：按价格从低到高，或按综合性价比排序."""
from __future__ import annotations

from typing import List, Literal

from ..scraper.base import Product

SortKey = Literal["price_asc", "price_desc", "sales", "score"]


def sort_by_price(products: List[Product], ascending: bool = True) -> List[Product]:
    """按价格升/降序."""
    return sorted(products, key=lambda p: p.price, reverse=not ascending)


def sort_by(products: List[Product], key: SortKey = "price_asc") -> List[Product]:
    if key == "price_asc":
        return sort_by_price(products, ascending=True)
    if key == "price_desc":
        return sort_by_price(products, ascending=False)
    if key == "sales":
        return sorted(products, key=lambda p: p.sales, reverse=True)
    if key == "score":
        return sorted(products, key=lambda p: p.shop_score or 0, reverse=True)
    raise ValueError(f"未知排序: {key}")
