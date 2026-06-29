"""
ベンチマーク用大量データ生成スクリプト。

通常の orders.csv（数百件）とは別に data/orders_large.csv を生成する。
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

FAKE = Faker("ja_JP")
RANDOM = random.Random(42)  # 再現性のためシードを固定

PRODUCTS = [
    ("P001", "ワイヤレスイヤホン",  8800),
    ("P002", "スマートウォッチ",   24800),
    ("P003", "モバイルバッテリー",  3980),
    ("P004", "USBハブ",           2480),
    ("P005", "Webカメラ",         6800),
    ("P006", "キーボード",         9800),
    ("P007", "マウス",             3200),
    ("P008", "ヘッドセット",       12800),
    ("P009", "外付けSSD",         14800),
    ("P010", "ノートPC スタンド",  4500),
]

STATUSES = ["completed", "completed", "completed", "pending", "cancelled"]

START_DATE = date(2020, 1, 1)
END_DATE   = date(2024, 12, 31)
DATE_RANGE = (END_DATE - START_DATE).days


def random_date() -> date:
    return START_DATE + timedelta(days=RANDOM.randint(0, DATE_RANGE))


def generate_rows(n: int):
    customer_pool = [
        (f"C-{i:04d}", FAKE.name())
        for i in range(1, 1001)  # 1000 人の顧客プール
    ]
    for i in range(1, n + 1):
        customer_id, customer_name = RANDOM.choice(customer_pool)
        product_id, product_name, unit_price = RANDOM.choice(PRODUCTS)
        quantity = RANDOM.randint(1, 5)
        yield {
            "order_id":      f"ORD-{i:06d}",
            "customer_id":   customer_id,
            "customer_name": customer_name,
            "product_id":    product_id,
            "product_name":  product_name,
            "quantity":      quantity,
            "unit_price":    unit_price,
            "order_date":    random_date().isoformat(),
            "status":        RANDOM.choice(STATUSES),
        }


def main(n: int = 100_000) -> None:
    output_path = Path(__file__).parent.parent / "data" / "orders_large.csv"
    output_path.parent.mkdir(exist_ok=True)

    fieldnames = [
        "order_id", "customer_id", "customer_name",
        "product_id", "product_name", "quantity",
        "unit_price", "order_date", "status",
    ]

    print(f"{n:,} 件を生成中... → {output_path}")
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(generate_rows(n))

    size_kb = output_path.stat().st_size // 1024
    print(f"完了: {n:,} 件、{size_kb:,} KB")


if __name__ == "__main__":
    main()
