"""Web 演示后端：Flask 提供 API + 静态页面.

启动: python /workspace/web/app.py
访问: http://127.0.0.1:5000
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

# 让 `price_watcher` 包可被导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request

from price_watcher import config
from price_watcher.pipeline import run_pipeline

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# ---------- 内置演示数据（用于页面首次加载展示示例） ----------
DEMO_KEYWORD = "机械键盘"


def _build_demo_result():
    """生成一份固定的演示结果，页面初始化时直接展示."""
    import random as _r
    _r.seed(42)
    return run_pipeline(
        keyword=DEMO_KEYWORD,
        platforms=config.PLATFORMS,
        max_items_per_platform=15,
        use_mock=True,
        save_history=True,
    )


DEMO_RESULT = _build_demo_result()


# ---------- 路由 ----------
@app.route("/")
def index():
    """首页：渲染演示页面."""
    demo_json = json.dumps(DEMO_RESULT, ensure_ascii=False)
    return render_template("index.html", demo_json=demo_json, demo_keyword=DEMO_KEYWORD)


@app.route("/api/search")
def api_search():
    """实时搜索 API.

    查询参数:
      - keyword: 关键词 (必填)
      - platforms: 逗号分隔的平台列表，默认 jd,taobao,pdd
      - num: 每平台条数，默认 15
      - no_mock: 1=尝试真实采集
    """
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "缺少关键词 keyword"}), 400

    platforms_param = request.args.get("platforms", "jd,taobao,pdd")
    platforms = [p.strip() for p in platforms_param.split(",") if p.strip()]
    num = int(request.args.get("num", 15))
    use_mock = request.args.get("no_mock") != "1"

    start = time.time()
    try:
        result = run_pipeline(
            keyword=keyword,
            platforms=platforms,
            max_items_per_platform=num,
            use_mock=use_mock,
            save_history=True,
        )
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500

    elapsed = round(time.time() - start, 2)
    result["elapsed_seconds"] = elapsed
    return jsonify(result)


@app.route("/api/demo")
def api_demo():
    """返回内置演示数据."""
    return jsonify(DEMO_RESULT)


# ---------- 启动 ----------
if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Price Watcher Web Demo 启动中 → http://127.0.0.1:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)
