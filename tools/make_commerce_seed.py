"""Write the example shop: examples/library/seed_operations.sql and the raw files in examples/files.

    python tools/make_commerce_seed.py

Everything here is invented by this script from a fixed seed. It builds on examples/commerce/seed.sql, whose rows the
gold questions read, so it leaves customers C001 to C003 and the wool SKUs alone.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = random.Random(20261106)
NOW = datetime(2026, 10, 30, 12, 0)

SURNAMES = "김이박최정강조윤장임한오서신권황안송류홍"
GIVEN = ["민재", "서윤", "지호", "하린", "도현", "수아", "예준", "지유", "시우", "채원", "주원", "유나", "건우", "소율", "현우",
         "다인", "준서", "가은", "태윤", "나연"]
GRADES = ["BASIC"] * 6 + ["SILVER"] * 3 + ["VIP"]
CATEGORIES = [("K5", "잡화", None, 1), ("K6", "가방", "K5", 1), ("K7", "신발", "K5", 1), ("K8", "뷰티", None, 1),
              ("K9", "스킨케어", "K8", 0), ("K10", "리빙", None, 1), ("K11", "주방용품", "K10", 1), ("K12", "침구", "K10", 1)]
SELLERS = [("SL01", "하늘섬유 공식몰", "010-5550-0901", 0.08), ("SL02", "바람직물 스토어", "010-5550-0902", 0.09),
           ("SL03", "들녘가죽", "010-5550-0903", 0.11), ("SL04", "솔빛코스메틱", "010-5550-0904", 0.12),
           ("SL05", "나무결리빙", "010-5550-0905", 0.10)]
PRODUCTS = [("P4", "데일리 토트백", "K6", "들녘가죽", "SL03", 89000), ("P5", "미니 크로스백", "K6", "들녘가죽", "SL03", 69000),
            ("P6", "러닝 스니커즈", "K7", "바람직물", "SL02", 79000), ("P7", "슬립온 로퍼", "K7", "들녘가죽", "SL03", 99000),
            ("P8", "수분 크림", "K9", "솔빛코스메틱", "SL04", 32000), ("P9", "진정 토너", "K9", "솔빛코스메틱", "SL04", 24000),
            ("P10", "무쇠 프라이팬", "K11", "나무결리빙", "SL05", 45000), ("P11", "유리 밀폐용기 세트", "K11", "나무결리빙", "SL05", 38000),
            ("P12", "순면 이불 커버", "K12", "나무결리빙", "SL05", 59000), ("P13", "메모리폼 베개", "K12", "나무결리빙", "SL05", 42000)]
OLD_PRODUCT_SELLERS = [("P1", "SL01"), ("P2", "SL01"), ("P3", "SL02")]
CARRIERS = [("CR1", "하늘택배"), ("CR2", "바람로지스"), ("CR3", "들녘물류")]
COUPONS = [("CP10", "신규 회원 10%", 0.10, 30000, "2026-12-31T23:59:59"), ("CP05", "재구매 5%", 0.05, 20000, "2026-11-30T23:59:59"),
           ("CP15", "가을 기획전 15%", 0.15, 50000, "2026-10-31T23:59:59")]
METHODS = ["CARD"] * 6 + ["EASY_PAY"] * 3 + ["BANK_TRANSFER"] * 2 + ["VIRTUAL_ACCOUNT"]
REASONS = ["사이즈가 맞지 않음", "단순 변심", "상품 불량", "오배송", "색상이 다름"]
REVIEWS = {5: "만족합니다", 4: "배송이 빠르고 좋아요", 3: "무난합니다", 2: "기대보다 아쉽습니다", 1: "다시 구매하지 않겠습니다"}


def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert(table: str, rows: list[tuple], columns: str = "") -> str:
    if not rows:
        return ""
    body = ",\n".join("  (" + ", ".join(q(v) for v in r) + ")" for r in rows)
    return f"INSERT INTO {table}{columns} VALUES\n{body};\n"


def stamp(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S")


# the rows ------------------------------------------------------------------------------------------------------------

customers = []
for i in range(4, 28):
    name = R.choice(SURNAMES) + GIVEN[(i * 7) % len(GIVEN)]
    customers.append((f"C{i:03}", name, R.choice(GRADES), f"010-5550-{100 + i:04}"))

skus = []
sizes = {"K6": ["FREE"], "K7": ["250", "260", "270"], "K9": ["50ml"], "K11": ["기본"], "K12": ["Q", "K"]}
for pid, _, cat, _, _, price in PRODUCTS:
    for size in sizes[cat]:
        skus.append((f"S{len(skus) + 5}", pid, size, R.choice(["블랙", "아이보리", "그레이", "브라운"]), price, R.randint(0, 80),
                     {"K6": "가죽", "K7": "합성", "K9": "화장품", "K11": "유리", "K12": "면"}[cat], "ALL"))

orders, items, claims, history = [], [], [], []
payments, shipments, refunds, order_coupons, reviews = [], [], [], [], []


def pay_and_ship(oid: str, at: datetime, status: str, total: int, delivered: datetime | None) -> None:
    pay_id = f"PY{len(payments) + 1:03}"
    if status == "ORDERED":
        payments.append((pay_id, oid, "VIRTUAL_ACCOUNT", total, None, "PENDING"))
        return
    paid = at + timedelta(minutes=R.randint(1, 50))
    payments.append((pay_id, oid, R.choice(METHODS), total, stamp(paid), "CANCELLED" if status == "CANCELLED" else "APPROVED"))
    if status in ("SHIPPED", "DELIVERED"):
        out = paid + timedelta(hours=R.randint(6, 30))
        carrier = R.choice(CARRIERS)[0]
        shipments.append((f"SH{len(shipments) + 1:03}", oid, carrier, f"70{R.randint(10_000_000, 99_999_999)}", stamp(out),
                          stamp(delivered) if delivered else None, "DELIVERED" if delivered else "IN_TRANSIT"))


# the orders the gold questions read get their payment and shipment too
base = {"O1": ("2026-10-20T10:00:00", "DELIVERED", 97000, "2026-10-25T15:00:00"), "O2": ("2026-10-27T09:30:00", "SHIPPED", 59000, None),
        "O3": ("2026-10-15T14:00:00", "DELIVERED", 74000, "2026-10-18T10:00:00"), "O4": ("2026-10-28T11:00:00", "CANCELLED", 19000, None)}
for oid, (at, status, total, delivered) in base.items():
    pay_and_ship(oid, datetime.fromisoformat(at), status, total, datetime.fromisoformat(delivered) if delivered else None)

price_of = {s[0]: s[4] for s in skus}
item_no, claim_no, day = 2000, 1, 0
for n in range(5, 71):
    oid, who = f"O{n}", R.choice(customers)[0]
    at = datetime(2026, 8, 1, 9) + timedelta(days=(n - 5) * 89.6 / 65, minutes=R.randint(0, 300))
    age = (NOW - at).days
    if age > 8:
        status = R.choices(["DELIVERED", "CANCELLED"], [92, 8])[0]
    elif age > 2:
        status = R.choices(["DELIVERED", "SHIPPED", "CANCELLED"], [45, 45, 10])[0]
    else:
        status = R.choices(["SHIPPED", "PAID", "ORDERED"], [30, 45, 25])[0]
    delivered = at + timedelta(days=R.randint(2, 4), hours=R.randint(1, 9)) if status == "DELIVERED" else None
    orders.append((oid, who, stamp(at), status))
    steps = {"ORDERED": ["ORDERED"], "PAID": ["ORDERED", "PAID"], "SHIPPED": ["ORDERED", "PAID", "SHIPPED"],
             "DELIVERED": ["ORDERED", "PAID", "SHIPPED", "DELIVERED"],
             "CANCELLED": ["ORDERED", "CANCELLED"] if R.random() < .5 else ["ORDERED", "PAID", "CANCELLED"]}[status]
    for i, (a, b) in enumerate(zip(steps, steps[1:])):
        history.append((f"H{len(history) + 1:04}", oid, a, b, stamp(at + timedelta(hours=(i + 1) * 9))))
    total = 0
    for _ in range(R.choice([1, 1, 1, 2, 2, 3])):
        item_no += 1
        sku = R.choice(skus)[0]
        qty = R.choice([1, 1, 1, 2])
        total += price_of[sku] * qty
        state = "NORMAL"
        if status == "DELIVERED":
            state = R.choices(["NORMAL", "RETURN_REQUESTED", "RETURNED"], [84, 6, 10])[0]
            if state == "RETURN_REQUESTED" and age > 18:  # a request this old has been settled
                state = "RETURNED"
        iid = f"I{item_no}"
        items.append((iid, oid, sku, qty, price_of[sku], stamp(delivered) if delivered else None, state))
        if state != "NORMAL":
            claim_no += 1
            at_claim = delivered + timedelta(days=R.randint(1, 6))
            done = state == "RETURNED"
            cid = f"CL{claim_no}"
            claims.append((cid, iid, R.choices(["RETURN", "EXCHANGE"], [8, 2])[0], R.choice(REASONS), stamp(at_claim), "CLOSED" if done else "OPEN"))
            refunds_at = at_claim + timedelta(days=R.randint(1, 3))
            refunds.append([cid, oid, price_of[sku] * qty, stamp(refunds_at), "DONE" if done else "REQUESTED"])
    pay_and_ship(oid, at, status, total, delivered)
    if total >= 30000 and R.random() < .3:
        order_coupons.append((oid, R.choice(COUPONS)[0]))
    if delivered and R.random() < .55:
        pid = next(s[1] for s in skus if s[0] == items[-1][2])
        star = R.choices([5, 4, 3, 2, 1], [46, 30, 14, 7, 3])[0]
        reviews.append((f"RV{len(reviews) + 1:03}", who, pid, star, stamp(delivered + timedelta(days=R.randint(1, 7))), REVIEWS[star]))

pay_of = {p[1]: p[0] for p in payments}
refund_rows = [(f"RF{i + 1:03}", c, pay_of[o], amount, at, st) for i, (c, o, amount, at, st) in enumerate(refunds)]

sql = """-- The example shop's operations. Invented by tools/make_commerce_seed.py; do not edit by hand.
CREATE TABLE sellers (seller_id TEXT PRIMARY KEY, name TEXT, phone TEXT, commission_rate REAL);
CREATE TABLE product_sellers (product_id TEXT, seller_id TEXT);
CREATE TABLE payments (payment_id TEXT PRIMARY KEY, order_id TEXT, method TEXT, amount REAL, paid_at TEXT, pay_status TEXT);
CREATE TABLE refunds (refund_id TEXT PRIMARY KEY, claim_id TEXT, payment_id TEXT, amount REAL, requested_at TEXT, refund_status TEXT);
CREATE TABLE carriers (carrier_id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE shipments (shipment_id TEXT PRIMARY KEY, order_id TEXT, carrier_id TEXT, tracking_no TEXT, shipped_at TEXT,
                        delivered_at TEXT, ship_status TEXT);
CREATE TABLE coupons (coupon_id TEXT PRIMARY KEY, name TEXT, discount_rate REAL, min_amount REAL, expires_at TEXT);
CREATE TABLE order_coupons (order_id TEXT, coupon_id TEXT);
CREATE TABLE reviews (review_id TEXT PRIMARY KEY, customer_id TEXT, product_id TEXT, rating INTEGER, written_at TEXT, body TEXT);

"""
sql += insert("customers", customers) + insert("categories", CATEGORIES)
sql += insert("products", [(p[0], p[1], p[2], p[3]) for p in PRODUCTS]) + insert("skus", skus)
sql += insert("orders", orders)
sql += insert("order_items", items, " (item_id, order_id, sku_id, quantity, unit_price, delivered_at, item_status)")
sql += insert("claims", claims) + insert("sellers", SELLERS)
sql += insert("product_sellers", OLD_PRODUCT_SELLERS + [(p[0], p[4]) for p in PRODUCTS])
sql += insert("payments", payments) + insert("refunds", refund_rows) + insert("carriers", CARRIERS)
sql += insert("shipments", shipments) + insert("coupons", COUPONS) + insert("order_coupons", order_coupons)
sql += insert("reviews", reviews)
(ROOT / "examples" / "library" / "seed_operations.sql").write_text(sql, encoding="utf-8", newline="\n")


def table(name: str, head: list[str], rows: list[tuple]) -> None:
    with (ROOT / "examples" / "files" / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)


(ROOT / "examples" / "files").mkdir(exist_ok=True)
table("회원.csv", ["회원번호", "이름", "등급", "연락처"], customers)
table("상품.csv", ["상품번호", "상품명", "카테고리", "브랜드", "판매자번호", "판매가"],
      [(p[0], p[1], next(c[1] for c in CATEGORIES if c[0] == p[2]), p[3], p[4], p[5]) for p in PRODUCTS])
table("판매자.csv", ["판매자번호", "판매자명", "수수료율"], [(s[0], s[1], s[3]) for s in SELLERS])
table("주문.csv", ["주문번호", "회원번호", "주문일시", "주문상태"], orders)
table("주문상품.csv", ["주문상품번호", "주문번호", "상품번호", "수량", "결제단가", "배송완료일시", "주문상품상태"],
      [(i[0], i[1], next(s[1] for s in skus if s[0] == i[2]), i[3], i[4], i[5], i[6]) for i in items])
table("주문상태이력.csv", ["이력번호", "주문번호", "이전상태", "이후상태", "변경일시"], history)
table("결제.csv", ["결제번호", "주문번호", "결제수단", "결제금액", "결제일시", "결제상태"], [p for p in payments if p[1] not in base])
table("배송.csv", ["배송번호", "주문번호", "택배사", "운송장번호", "출고일시", "배송완료일시", "배송상태"],
      [(s[0], s[1], next(c[1] for c in CARRIERS if c[0] == s[2]), s[3], s[4], s[5], s[6]) for s in shipments if s[1] not in base])

print("customers", len(customers) + 3, "products", len(PRODUCTS) + 3, "skus", len(skus) + 4, "orders", len(orders) + 4,
      "items", len(items) + 6, "claims", len(claims) + 1, "payments", len(payments), "refunds", len(refund_rows),
      "shipments", len(shipments), "coupon uses", len(order_coupons), "reviews", len(reviews), "history", len(history))
print("in transit", sum(s[6] == "IN_TRANSIT" for s in shipments), "pending refunds", sum(r[5] == "REQUESTED" for r in refund_rows),
      "methods", len({p[2] for p in payments}), "pending pay", sum(p[5] == "PENDING" for p in payments))
