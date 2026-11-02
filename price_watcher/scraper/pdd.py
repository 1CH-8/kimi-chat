"""拼多多爬虫."""
from __future__ import annotations

from datetime import datetime
from typing import List

from .base import BaseScraper, Product, make_mock_product


class PDDScraper(BaseScraper):
    platform = "pdd"
    platform_name = "拼多多"

    SEARCH_URL = "https://mobile.yangkeduo.com/search_result.html?search_key={keyword}"

    def _build_url(self, keyword: str, max_items: int) -> str:
        return self.SEARCH_URL.format(keyword=keyword)

    def _parse(self, html: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        return (
            soup.select("[class*='goods-item']")
            or soup.select(".goods-list .item")
            or soup.select("div[data-goods-id]")
        )

    def _extract_fields(self, raw_items: list, keyword: str) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        products = []
        for node in raw_items:
            try:
                name_tag = node.select_one(".goods-title") or node.select_one("[class*='title']")
                name = name_tag.get_text(strip=True) if name_tag else ""

                price_tag = node.select_one(".price") or node.select_one("[class*='price']")
                price = self._to_float(price_tag.get_text(strip=True)) if price_tag else None

                shop_tag = node.select_one(".shop-name") or node.select_one("[class*='mallName']")
                shop_name = shop_tag.get_text(strip=True) if shop_tag else ""

                url = ""
                a_tag = node.select_one("a")
                if a_tag and a_tag.has_attr("href"):
                    url = a_tag["href"]
                    if url.startswith("//"):
                        url = "https:" + url
                if not url:
                    gid = node.get("data-goods-id", "")
                    if gid:
                        url = f"https://mobile.yangkeduo.com/goods.html?goods_id={gid}"

                sales_tag = node.select_one(".sales") or node.select_one("[class*='sales']")
                sales = self._to_int(sales_tag.get_text(strip=True)) if sales_tag else 0

                if name and price is not None:
                    products.append(Product(
                        platform=self.platform,
                        name=name,
                        price=price,
                        original_price=None,
                        sales=sales,
                        shop_name=shop_name,
                        shop_score=None,
                        url=url,
                        product_id=node.get("data-goods-id", ""),
                        collected_at=now,
                    ))
            except Exception:
                continue
        return products

    def _mock_search(self, keyword: str, max_items: int) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import random as _r
        _r.seed(hash(f"pdd-{keyword}") % 2**32)
        # 拼多多价格倾向于更低
        price_range = _r.choice([(30, 300), (50, 500), (20, 150), (100, 800)])
        return [
            make_mock_product(self.platform, keyword, i, price_range=price_range, now=now)
            for i in range(max_items)
        ]
