CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT, grade TEXT, phone TEXT);
CREATE TABLE categories (category_id TEXT PRIMARY KEY, name TEXT, parent_id TEXT, returnable INTEGER);
CREATE TABLE products (product_id TEXT PRIMARY KEY, name TEXT, category_id TEXT, brand TEXT);
CREATE TABLE skus (sku_id TEXT PRIMARY KEY, product_id TEXT, size TEXT, color TEXT, price REAL, stock INTEGER,
                   material TEXT, season TEXT);
CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT, ordered_at TEXT, status TEXT);
CREATE TABLE order_items (item_id TEXT PRIMARY KEY, order_id TEXT, sku_id TEXT, quantity INTEGER,
                          unit_price REAL, delivered_at TEXT, item_status TEXT,
                          gift_wrap INTEGER DEFAULT 0);
CREATE TABLE claims (claim_id TEXT PRIMARY KEY, item_id TEXT, kind TEXT, reason TEXT, claimed_at TEXT,
                     claim_status TEXT);
CREATE TABLE wishlists (customer_id TEXT, product_id TEXT);
CREATE TABLE price_changes (change_id TEXT PRIMARY KEY, sku_id TEXT, changed_at TEXT, price REAL);
CREATE TABLE return_cases (case_id TEXT PRIMARY KEY, item_id TEXT, decided_at TEXT, days_after_delivery INTEGER,
                           status_then TEXT, returnable_then INTEGER, grade_then TEXT, approved INTEGER);

INSERT INTO customers VALUES ('C001', '김하늘', 'VIP', '010-5550-0101'), ('C002', '이도윤', 'BASIC', '010-5550-0102'),
                             ('C003', '박서연', 'SILVER', '010-5550-0103');
INSERT INTO categories VALUES ('K1', '의류', NULL, 1), ('K2', '상의', 'K1', 1), ('K3', '니트', 'K2', 1),
                              ('K4', '속옷', 'K1', 0);
INSERT INTO products VALUES ('P1', '울 니트 스웨터', 'K3', '하늘섬유'), ('P2', '면 티셔츠', 'K2', '하늘섬유'),
                            ('P3', '기본 속옷 세트', 'K4', '바람직물');
INSERT INTO skus VALUES ('S1', 'P1', 'M', '네이비', 59000, 3, '울', 'FW'), ('S2', 'P1', 'L', '네이비', 59000, 12, '울', 'FW'),
                        ('S3', 'P2', 'M', '화이트', 19000, 2, '면', 'ALL'), ('S4', 'P3', 'L', '블랙', 15000, 40, '면', 'ALL');
INSERT INTO orders VALUES ('O1', 'C001', '2026-10-20T10:00:00', 'DELIVERED'),
                          ('O2', 'C001', '2026-10-27T09:30:00', 'SHIPPED'),
                          ('O3', 'C002', '2026-10-15T14:00:00', 'DELIVERED'),
                          ('O4', 'C002', '2026-10-28T11:00:00', 'CANCELLED');
INSERT INTO order_items (item_id, order_id, sku_id, quantity, unit_price, delivered_at, item_status) VALUES
  ('I1001', 'O1', 'S1', 1, 59000, '2026-10-25T15:00:00', 'NORMAL'),
  ('I1002', 'O1', 'S3', 2, 19000, '2026-10-25T15:00:00', 'RETURN_REQUESTED'),
  ('I1003', 'O3', 'S2', 1, 59000, '2026-10-18T10:00:00', 'NORMAL'),
  ('I1004', 'O3', 'S4', 1, 15000, '2026-10-18T10:00:00', 'NORMAL'),
  ('I1005', 'O2', 'S2', 1, 59000, NULL, 'NORMAL'),
  ('I1006', 'O4', 'S3', 1, 19000, NULL, 'NORMAL');
UPDATE order_items SET gift_wrap = 1 WHERE item_id = 'I1001';
INSERT INTO claims VALUES ('CL1', 'I1002', 'RETURN', '사이즈가 맞지 않음', '2026-10-26T09:00:00', 'OPEN');
INSERT INTO wishlists VALUES ('C001', 'P2'), ('C001', 'P3'), ('C002', 'P1');
INSERT INTO price_changes VALUES ('PC1', 'S1', '2026-09-01T00:00:00', 69000), ('PC2', 'S1', '2026-10-01T00:00:00', 59000),
                                 ('PC3', 'S2', '2026-09-01T00:00:00', 69000), ('PC4', 'S2', '2026-10-01T00:00:00', 59000),
                                 ('PC5', 'S3', '2026-08-15T00:00:00', 19000);
INSERT INTO return_cases VALUES
  ('RC01', 'I0901', '2026-09-03T10:00:00', 2, 'NORMAL', 1, 'BASIC', 1),
  ('RC02', 'I0902', '2026-09-05T10:00:00', 10, 'NORMAL', 1, 'BASIC', 0),
  ('RC03', 'I0903', '2026-09-08T10:00:00', 3, 'NORMAL', 0, 'VIP', 0),
  ('RC04', 'I0904', '2026-09-10T10:00:00', 12, 'NORMAL', 1, 'VIP', 1),
  ('RC05', 'I0905', '2026-09-12T10:00:00', 5, 'RETURN_REQUESTED', 1, 'BASIC', 0),
  ('RC06', 'I0906', '2026-09-15T10:00:00', NULL, 'NORMAL', 1, 'SILVER', 0),
  ('RC07', 'I0907', '2026-09-18T10:00:00', 7, 'NORMAL', 1, 'SILVER', 1),
  ('RC08', 'I0908', '2026-09-20T10:00:00', 8, 'NORMAL', 1, 'SILVER', 1),
  ('RC09', 'I0909', '2026-09-25T10:00:00', 1, 'NORMAL', 1, 'BASIC', 1),
  ('RC10', 'I0910', '2026-09-28T10:00:00', 20, 'NORMAL', 1, 'VIP', 0);
