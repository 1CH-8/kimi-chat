"""性价比推荐算法.

综合考量:
  - 价格越低越优 (40%)
  - 销量越高越优 (30%)
  - 店铺评分越高越优 (20%)
  - 折扣力度（划线价 vs 现价）越大越优 (10%)

使用归一化 + 加权综合得分.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..scraper.base import Product


def _normalize(values: List[float], higher_better: bool = True) -> List[float]:
    """Min-Max 归一化. higher_better=False 表示值越小越好."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    if higher_better:
        return [(v - lo) / (hi - lo) for v in values]
    return [(hi - v) / (hi - lo) for v in values]


def score_products(products: List[Product]) -> List[Tuple[Product, float, Dict[str, float]]]:
    """为每个商品打综合分，返回 (product, 综合分, 分项分) 列表."""
    if not products:
        return []

    prices = [p.price for p in products]
    sales = [float(p.sales) for p in products]
    scores = [float(p.shop_score or 0) for p in products]
    discounts = [
        (p.original_price - p.price) / p.original_price if p.original_price and p.original_price > 0 else 0.0
        for p in products
    ]

    n_price = _normalize(prices, higher_better=False)   # 价格越低越好
    n_sales = _normalize(sales, higher_better=True)
    n_score = _normalize(scores, higher_better=True)
    n_disc = _normalize(discounts, higher_better=True)

    result: List[Tuple[Product, float, Dict[str, float]]] = []
    weights = {"price": 0.40, "sales": 0.30, "score": 0.20, "discount": 0.10}
    for i, p in enumerate(products):
        component_scores = {
            "price": round(n_price[i], 4),
            "sales": round(n_sales[i], 4),
            "score": round(n_score[i], 4),
            "discount": round(n_disc[i], 4),
        }
        total = (
            component_scores["price"] * weights["price"]
            + component_scores["sales"] * weights["sales"]
            + component_scores["score"] * weights["score"]
            + component_scores["discount"] * weights["discount"]
        )
        result.append((p, round(total, 4), component_scores))
    return result


def recommend_best(products: List[Product], top_n: int = 5) -> List[Dict]:
    """返回性价比最高的 top_n 商品，附带推荐理由标签."""
    scored = score_products(products)
    scored.sort(key=lambda x: x[1], reverse=True)

    # 各维度冠军
    if scored:
        cheapest = min(scored, key=lambda x: x[0].price)
        best_score = max(scored, key=lambda x: x[0].shop_score or 0)
        best_sales = max(scored, key=lambda x: x[0].sales)
    else:
        cheapest = best_score = best_sales = None

    ranked = []
    for rank, (p, total, comp) in enumerate(scored[:top_n], start=1):
        tags = []
        if rank == 1:
            tags.append("🏆 综合最推荐")
        if cheapest and cheapest[0] is p:
            tags.append("💰 全网最低价")
        if best_score and best_score[0] is p:
            tags.append("⭐ 店铺评分最高")
        if best_sales and best_sales[0] is p:
            tags.append("🔥 销量冠军")
        if p.original_price and (p.original_price - p.price) / p.original_price > 0.2:
            tags.append("🎁 高折扣")
        ranked.append({
            "rank": rank,
            "product": p.to_dict(),
            "score": total,
            "components": comp,
            "tags": tags,
        })
    return ranked
