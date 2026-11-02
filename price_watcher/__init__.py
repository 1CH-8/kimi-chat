"""电商价格自动化采集与对比工具包."""
from .scraper.factory import ScraperFactory
from .processor.cleaner import clean_and_deduplicate
from .processor.sorter import sort_by_price
from .processor.recommender import recommend_best

__all__ = ["ScraperFactory", "clean_and_deduplicate", "sort_by_price", "recommend_best"]
