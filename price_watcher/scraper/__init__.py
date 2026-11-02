"""爬虫模块."""
from .base import BaseScraper
from .jd import JDScraper
from .taobao import TaobaoScraper
from .pdd import PDDScraper

__all__ = ["BaseScraper", "JDScraper", "TaobaoScraper", "PDDScraper"]
