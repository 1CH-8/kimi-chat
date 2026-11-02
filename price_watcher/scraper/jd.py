"""京东爬虫."""
from __future__ import annotations

from datetime import datetime
from typing import List

from .base import BaseScraper, Product, make_mock_product


class JDScraper(BaseScraper):
    platform = "jd"
    platform_name = "京东"

    SEARCH_URL = "https://search.jd.com/Search?keyword={keyword}&page={page}"

    def _build_url(self, keyword: str, max_items: int) -> str:
        page = 1
        return self.SEARCH_URL.format(keyword=keyword, page=page)

    def _parse(self, html: str) -> list:
        """使用 BeautifulSoup 解析京东搜索页."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        return soup.select("li.gl-item") or soup.select(".J_goodsList li") or soup.select("li[class*='gl-item']")

    def _extract_fields(self, raw_items: list, keyword: str) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        products = []
        for node in raw_items:
            try:
                # 名称
                name_tag = node.select_one(".p-name a") or node.select_one("a.p-name")
                name = name_tag.get_text(strip=True) if name_tag else ""

                # 价格（京东常见渲染方式：class="p-price"）
                price_tag = node.select_one(".p-price strong i") or node.select_one(".p-price .price")
                price = self._to_float(price_tag.get_text(strip=True)) if price_tag else None

                # 店铺
                shop_tag = node.select_one(".p-shop a") or node.select_one(".J_im_icon a")
                shop_name = shop_tag.get_text(strip=True) if shop_tag else ""

                # 链接
                url = ""
                if name_tag and name_tag.has_attr("href"):
                    url = name_tag["href"]
                    if url.startswith("//"):
                        url = "https:" + url

                # 商品ID
                product_id = node.get("data-sku", "") or node.get("data-pid", "")

                # 销量（京东常以"已售X+"或评价数出现）
                sales_tag = node.select_one(".p-commit a") or node.select_one(".comment")
                sales_text = sales_tag.get_text(strip=True) if sales_tag else ""
                sales = self._to_int(sales_text)

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
                        product_id=product_id,
                        collected_at=now,
                    ))
            except Exception:
                continue
        return products

    def _mock_search(self, keyword: str, max_items: int) -> List[Product]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import random as _r
        _r.seed(hash(f"jd-{keyword}") % 2**32)
        price_range = _r.choice([(100, 800), (200, 1500), (500, 3000), (50, 300)])
        return [
            make_mock_product(self.platform, keyword, i, price_range=price_range, now=now)
            for i in range(max_items)
        ]
