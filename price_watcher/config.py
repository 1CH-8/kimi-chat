"""全局配置."""
import os

# 请求相关
REQUEST_TIMEOUT = 15          # 秒
REQUEST_INTERVAL = (1, 3)     # 请求间隔随机范围
MAX_RETRIES = 3               # 重试次数

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORY_DB = os.path.join(OUTPUT_DIR, "price_history.json")
DEMO_DB = os.path.join(OUTPUT_DIR, "demo_history.json")
JSON_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "json")

# 确保目录存在
for _d in [OUTPUT_DIR, JSON_OUTPUT_DIR]:
    os.makedirs(_d, exist_ok=True)

# 平台列表
PLATFORMS = ["jd", "taobao", "pdd"]
