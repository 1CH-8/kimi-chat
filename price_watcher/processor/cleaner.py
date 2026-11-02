"""数据清洗与去重."""
from __future__ import annotations

import re
from typing import List

from ..scraper.base import Product


def _normalize_name(name: str) -> str:
    """名称归一化：去除多余空格、特殊符号、版本尾缀等."""
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)
    # 去掉常见营销尾缀
    name = re.sub(r"(正品|旗舰|尊享|青春|标准版|pro|max|ultra|lite|plus)", "", name, flags=re.I)
    name = re.sub(r"[\(\)\[\]【】（）《》]", "", name)
    return name


def clean_and_deduplicate(products: List[Product], name_threshold: float = 0.85) -> List[Product]:
    """清洗脏数据 + 基于名称相似度去重.

    规则:
      1. 价格缺失 / <= 0 的剔除
      2. 名称过短（< 3 字）剔除
      3. 同名 + 价格差 < 5% 视为重复，保留评分高/销量大的那条
    """
    # Step 1: 基础过滤
    cleaned: List[Product] = []
    for p in products:
        if not p.name or len(p.name.strip()) < 3:
            continue
        if p.price is None or p.price <= 0:
            continue
        cleaned.append(p)

    # Step 2: 精确去重（同 product_id 或 完全相同 name）
    seen: dict[str, Product] = {}
    for p in cleaned:
        key = f"{p.platform}|{_normalize_name(p.name)}"
        if key not in seen:
            seen[key] = p
        else:
            existing = seen[key]
            # 保留数据更完整的那条
            def _score(pp: Product) -> float:
                return (
                    (pp.shop_score or 0) * 100
                    + pp.sales
                    + (10 if pp.shop_name else 0)
                    + (5 if pp.url else 0)
                )
            if _score(p) > _score(existing):
                seen[key] = p

    # Step 3: 跨平台近似去重（名称相似 + 价格接近）
    final: List[Product] = []
    for p in seen.values():
        is_dup = False
        norm = _normalize_name(p.name)
        for f in final:
            f_norm = _normalize_name(f.name)
            if norm != f_norm and not _names_similar(norm, f_norm, threshold=name_threshold):
                continue
            # 价格差 < 8% 视为同款
            base = min(p.price, f.price)
            if base > 0 and abs(p.price - f.price) / base < 0.08:
                # 保留更便宜的
                winner = p if p.price < f.price else f
                final.remove(f)
                final.append(winner)
                is_dup = True
                break
        if not is_dup:
            final.append(p)

    return final


def _names_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    """简易相似度：计算最长公共子序列占长度的比例.

    避免引入额外依赖，够用即可.
    """
    if not a or not b:
        return False
    m, n = len(a), len(b)
    # LCS
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs_len = dp[m][n]
    return lcs_len / min(m, n) >= threshold
