"""
架空の注文データを CSV に生成するスクリプト。
Faker を使って、ECサイトの注文データをダミーで作る。
"""

import csv
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("ja_JP")

PRODUCTS = [
    {"product_id": "P001", "product_name": "ワイヤレスイヤホン", "unit_price": 8800},
    {"product_id": "P002", "product_name": "スマートウォッチ",   "unit_price": 24800},
    {"product_id": "P003", "product_name": "モバイルバッテリー", "unit_price": 3980},
    {"product_id": "P004", "product_name": "USBハブ",           "unit_price": 2480},
    {"product_id": "P005", "product_name": "Webカメラ",         "unit_price": 6800},
]

STATUSES = ["completed", "pending", "cancelled"]


def generate_orders(num_orders: int, output_path: str) -> None:
    base_date = datetime(2024, 1, 1)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order_id", "customer_id", "customer_name",
            "product_id", "product_name", "quantity",
            "unit_price", "order_date", "status",
        ])
        writer.writeheader()

        for i in range(1, num_orders + 1):
            product = random.choice(PRODUCTS)
            order_date = base_date + timedelta(days=random.randint(0, 364))

            writer.writerow({
                "order_id":      f"ORD-{i:05d}",
                "customer_id":   f"C-{random.randint(1, 200):04d}",
                "customer_name": fake.name(),
                "product_id":    product["product_id"],
                "product_name":  product["product_name"],
                "quantity":      random.randint(1, 5),
                "unit_price":    product["unit_price"],
                "order_date":    order_date.strftime("%Y-%m-%d"),
                "status":        random.choice(STATUSES),
            })

    print(f"{num_orders} 件の注文データを {output_path} に生成しました。")


if __name__ == "__main__":
    generate_orders(num_orders=1000, output_path="data/orders.csv")
