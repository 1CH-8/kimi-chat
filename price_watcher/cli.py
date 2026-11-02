"""命令行工具入口.

用法示例:
    python -m price_watcher.cli search "iPhone 15" -p jd taobao -n 10
    python -m price_watcher.cli search "耳机" --no-mock
    python -m price_watcher.cli history "耳机" --days 7
    python -m price_watcher.cli platforms
    python -m price_watcher.cli demo "机械键盘"
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from . import config
from .pipeline import run_pipeline, save_result
from .scraper.factory import ScraperFactory
from .storage.history import PriceHistory


def _print_result(result: dict):
    """终端友好输出."""
    print("\n" + "=" * 70)
    print(f" 🔍  关键词: {result['keyword']}    采集时间: {result['collected_at']}")
    print(f" 📊  原始 {result['raw_count']} 条 → 清洗后 {result['cleaned_count']} 条")
    print("=" * 70)

    # 平台统计
    print("\n📦 平台统计")
    print("-" * 70)
    print(f"{'平台':<8}{'商品数':>6}{'最低价':>10}{'最高价':>10}{'均价':>10}{'总销量':>10}")
    print("-" * 70)
    for plat, s in result["platform_stats"].items():
        print(f"{plat:<8}{s['count']:>6}{s['min_price']:>10.2f}{s['max_price']:>10.2f}"
              f"{s['avg_price']:>10.2f}{s['total_sales']:>10,}")

    # 性价比推荐
    print("\n🏆 性价比推荐 TOP 5")
    print("-" * 70)
    for rec in result["recommendations"]:
        p = rec["product"]
        tags = " ".join(rec["tags"])
        print(f" #{rec['rank']}  [综合分 {rec['score']:.2f}] {tags}")
        print(f"    {p['platform'].upper()} | ¥{p['price']} | 销量 {p['sales']} | "
              f"店铺 {p['shop_name']} (评分 {p['shop_score']})")
        print(f"    {p['name'][:50]}")
        print()

    # 全量商品表（前 15）
    print("💰 全量商品价格排序（前 15 条，低 → 高）")
    print("-" * 70)
    print(f"{'#':<4}{'平台':<8}{'价格':>10}{'销量':>10}{'评分':>6}{'商品名'}")
    print("-" * 70)
    for i, p in enumerate(result["products"][:15], start=1):
        score_str = f"{p['shop_score']:.1f}" if p["shop_score"] else "-"
        print(f"{i:<4}{p['platform']:<8}{p['price']:>10.2f}{p['sales']:>10,}{score_str:>6}  "
              f"{p['name'][:45]}")


def cmd_search(args):
    result = run_pipeline(
        keyword=args.keyword,
        platforms=args.platforms,
        max_items_per_platform=args.num,
        use_mock=not args.no_mock,
        save_history=not args.no_history,
    )
    _print_result(result)
    if args.save_json:
        path = save_result(result)
        print(f"\n💾 已保存 JSON: {path}")


def cmd_history(args):
    ph = PriceHistory()
    trend = ph.get_trend_data(args.keyword, days=args.days)
    history_list = ph.get_history(args.keyword, days=args.days)
    if not history_list:
        print(f"⚠️  没有找到 '{args.keyword}' 的历史记录")
        return
    print(f"\n📈 '{args.keyword}' 最近 {args.days} 天共 {len(history_list)} 条快照")
    print("-" * 60)
    for s in history_list:
        print(f"  {s['timestamp']} | 总商品 {s['summary']['total_items']} 条 | "
              + " | ".join(f"{p}最低¥{v['min']}" for p, v in s["platforms"].items()))


def cmd_platforms(args):
    print("可用平台:", ", ".join(ScraperFactory.available_platforms()))


def cmd_demo(args):
    """演示模式：跑一次并生成 JSON 示例."""
    keyword = args.keyword or "机械键盘"
    print(f"🎬 演示模式: 关键词 '{keyword}'")
    result = run_pipeline(keyword=keyword, use_mock=True)
    _print_result(result)
    path = save_result(result)
    print(f"\n✅ 演示数据已保存到: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="price-watcher",
        description="电商商品价格自动化采集与对比工具",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="采集并对比指定关键词")
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument("-p", "--platforms", nargs="+", default=config.PLATFORMS,
                          choices=config.PLATFORMS, help="要采集的平台")
    p_search.add_argument("-n", "--num", type=int, default=20, help="每个平台最多采集条数")
    p_search.add_argument("--no-mock", action="store_true", help="尝试真实采集（忽略反爬失败会回退）")
    p_search.add_argument("--no-history", action="store_true", help="不写入价格历史")
    p_search.add_argument("--save-json", action="store_true", help="保存结果到 JSON 文件")
    p_search.set_defaults(func=cmd_search)

    # history
    p_hist = sub.add_parser("history", help="查看价格历史")
    p_hist.add_argument("keyword", help="关键词")
    p_hist.add_argument("--days", type=int, default=30, help="最近 N 天")
    p_hist.set_defaults(func=cmd_history)

    # platforms
    p_plat = sub.add_parser("platforms", help="列出可用平台")
    p_plat.set_defaults(func=cmd_platforms)

    # demo
    p_demo = sub.add_parser("demo", help="演示模式（快速跑通全流程，用模拟数据）")
    p_demo.add_argument("keyword", nargs="?", default="机械键盘", help="示例关键词")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    args.func(args)


if __name__ == "__main__":
    main()
