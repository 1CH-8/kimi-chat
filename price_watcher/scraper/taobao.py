"""淘宝爬虫."""
from __future__ import annotations

from datetime import datetime
from typing import List

from .base import BaseScraper, Product, make_mock_product


class TaobaoScraper(BaseScraper):
    platform = "taobao"
    platform_name = "淘宝"

    SEARCH_URL = "https://s.taobao.com/search?q={keyword}&sort=price-asc"

    def _build_url(self, keyword: str, max_items: int) -> str:
        return self.SEARCH_URL.format(keyword=keyword)

    def _parse(self, html: str) -> list:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        return (
            soup.select(".ContentItem-content")
            or soup.select("[class*='ContentItem']")
            or soup.select("div.items .item")
        )

    def _extract_fields(self, raw_items: list, keyword: str) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        products = []
        for node in raw_items:
            try:
                name_tag = node.select_one(".ContentItem-title a") or node.select_one("a.tb-link")
                name = name_tag.get_text(strip=True) if name_tag else ""

                price_tag = node.select_one(".Price--priceInt") or node.select_one(".price")
                price = self._to_float(price_tag.get_text(strip=True)) if price_tag else None

                shop_tag = node.select_one(".shopname") or node.select_one(".ShopInfo--shopName")
                shop_name = shop_tag.get_text(strip=True) if shop_tag else ""

                url = ""
                if name_tag and name_tag.has_attr("href"):
                    url = name_tag["href"]
                    if url.startswith("//"):
                        url = "https:" + url

                sales_tag = node.select_one(".Price--realSales") or node.select_one(".sold")
                sales = self._to_int(sales_tag.get_text(strip=True)) if sales_tag else 0

                score_tag = node.select_one(".ShopHeader--shopScore") or node.select_one(".rate")
                score = self._to_score(score_tag.get_text(strip=True)) if score_tag else None

                if name and price is not None:
                    products.append(Product(
                        platform=self.platform,
                        name=name,
                        price=price,
                        original_price=None,
                        sales=sales,
                        shop_name=shop_name,
                        shop_score=score,
                        url=url,
                        product_id="",
                        collected_at=now,
                    ))
            except Exception:
                continue
        return products

    def _mock_search(self, keyword: str, max_items: int) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import random as _r
        _r.seed(hash(f"taobao-{keyword}") % 2**32)
        price_range = _r.choice([(50, 500), (100, 1000), (30, 200), (200, 2000)])
        return [
            make_mock_product(self.platform, keyword, i, price_range=price_range, now=now)
            for i in range(max_items)
        ]
