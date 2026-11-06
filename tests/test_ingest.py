"""Anything in, one JSON out: every format reads into the canonical object, and an upload cannot do harm on the way."""
import io
import json
import struct
import sys
import time
import tracemalloc
import zipfile
from collections.abc import Iterator
from itertools import accumulate

import pytest

from xgen_space import ingest as ingest_module
from xgen_space.cli import main
from xgen_space.definitions import Definitions, from_sheets, schema_backend
from xgen_space.draft import Table, draft
from xgen_space.ingest import IngestError, adapter_paths, ingest, is_sheet, load_adapters, register

from .conftest import EXAMPLE, LIB

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def _zip(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def _reason(data: bytes, source: str) -> str:
    with pytest.raises(IngestError) as e:
        ingest(data, source)
    return e.value.reason


# ---- SQL DDL -------------------------------------------------------------------------------------------------

POSTGRES = """
-- a dump, with what a dump holds around the tables
SET statement_timeout = 0;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE FUNCTION public.touch() RETURNS trigger AS $$
BEGIN
  NEW.note := 'CREATE TABLE fake (id int);';
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TYPE public.mood AS ENUM ('calm', 'busy');
CREATE TEMP TABLE scratch (a int);
CREATE GLOBAL TEMPORARY TABLE scratch2 (a int);
CREATE TABLE IF NOT EXISTS public.orders (
    order_no character varying(20) NOT NULL,
    mood public.mood,
    placed_at timestamp(6) without time zone DEFAULT now(),
    total numeric(10,2),
    tags text[],
    status character varying(10),
    CONSTRAINT ck_status CHECK (((status)::text = ANY ((ARRAY['OPEN'::character varying, 'DONE'::character varying])::text[])))
);
CREATE TABLE public.order_lines (
    order_no varchar(20) NOT NULL REFERENCES public.orders (order_no) ON DELETE CASCADE,
    line_no integer NOT NULL,
    kind char(1) CHECK (kind IN ('A', 'B')),
    state char(1) CHECK (state NOT IN ('X')),
    PRIMARY KEY (order_no, line_no)
);
CREATE TABLE public.shipments (
    ship_no serial PRIMARY KEY,
    order_no varchar(20),
    line_no integer
);
ALTER TABLE ONLY public.orders ADD CONSTRAINT pk_orders PRIMARY KEY (order_no);
ALTER TABLE ONLY public.shipments
    ADD CONSTRAINT fk_line FOREIGN KEY (order_no, line_no) REFERENCES public.order_lines(order_no, line_no);
COMMENT ON TABLE public.orders IS '주문
주문 한 건의 머리 정보';
COMMENT ON COLUMN public.orders.order_no IS '주문번호';
COMMENT ON INDEX public.orders_idx IS 'ignored';
CREATE VIEW public.v AS SELECT * FROM public.orders;
CREATE INDEX orders_idx ON public.orders (placed_at);
INSERT INTO public.orders VALUES ('O1', now(), 10, '{}', 'OPEN; CREATE TABLE nope (id int)');
"""

MYSQL = """
/*!40101 SET NAMES utf8 */;
DROP TABLE IF EXISTS `member`;
CREATE TABLE `member` (
  `member_no` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '회원번호',
  `grade` enum('GOLD','SILVER') NOT NULL DEFAULT 'SILVER' COMMENT '등급',
  `key` varchar(10) DEFAULT NULL,
  `note` varchar(100) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT 'it\\'s; fine',
  `active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`member_no`),
  UNIQUE KEY `uk_key` (`key`),
  KEY `idx_grade` (`grade`) USING BTREE,
  CONSTRAINT `ck_active` CHECK ((`active` in (0,1)))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COMMENT='회원';
CREATE TABLE `coupon` (
  `coupon_no` int NOT NULL,
  `member_no` bigint unsigned,
  PRIMARY KEY (`coupon_no`),
  CONSTRAINT `fk_member` FOREIGN KEY (`member_no`) REFERENCES `member` (`member_no`) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT 'it\\'s a coupon';
DELIMITER $$
CREATE PROCEDURE p() BEGIN CREATE TABLE t1 (a int); END$$
DELIMITER ;
DELIMITER ;;
CREATE PROCEDURE q() BEGIN
  CREATE TEMPORARY TABLE t2 (a int);
END ;;
DELIMITER ;
INSERT INTO `member` VALUES (1,'GOLD','k','it\\'s; CREATE TABLE fake (a int)',1);
ALTER TABLE `coupon` ADD COLUMN `extra` int, ADD CONSTRAINT `fk2` FOREIGN KEY (`coupon_no`) REFERENCES `member` (`member_no`);
"""

ORACLE = """
CREATE TABLE "SHOP"."TB_GOODS"
   (    "GOODS_NO" VARCHAR2(20 BYTE) NOT NULL ENABLE,
        "PRICE" NUMBER(10,2) DEFAULT 0,
        "NAME" NVARCHAR2(100),
        "ANY_LEN" NUMBER(*,0),
        "SOLD_YN" CHAR(1 CHAR),
         CONSTRAINT "PK_GOODS" PRIMARY KEY ("GOODS_NO")
  USING INDEX PCTFREE 10 INITRANS 2 STORAGE(INITIAL 65536 NEXT 1048576) TABLESPACE "USERS"  ENABLE,
         SUPPLEMENTAL LOG GROUP "G1" ("NAME") ALWAYS
   ) SEGMENT CREATION IMMEDIATE TABLESPACE "USERS";
/
CREATE TABLE "SHOP"."TB_REVIEW" ("REVIEW_NO" NUMBER(10), "GOODS_NO" VARCHAR2(20 BYTE));
/
ALTER TABLE "SHOP"."TB_REVIEW" ADD (CONSTRAINT "PK_REVIEW" PRIMARY KEY ("REVIEW_NO"),
  CONSTRAINT "FK_GOODS" FOREIGN KEY ("GOODS_NO") REFERENCES "SHOP"."TB_GOODS" ("GOODS_NO") ENABLE);
ALTER TABLE "SHOP"."TB_GOODS" ADD CONSTRAINT "CK_SOLD" CHECK ("SOLD_YN" IN ('Y','N')) ENABLE;
COMMENT ON TABLE "SHOP"."TB_GOODS" IS '상품';
COMMENT ON COLUMN "SHOP"."TB_GOODS"."GOODS_NO" IS '상품번호';
"""

SQLSERVER = """
USE [shop]
GO
SET ANSI_NULLS ON
GO
CREATE TABLE [dbo].[Customer](
	[CustomerId] [int] IDENTITY(1,1) NOT NULL,
	[Name] [nvarchar](100) COLLATE Korean_Wansung_CI_AS NOT NULL,
	[Memo] [nvarchar](max) NULL,
	[Level] [varchar](10) NULL,
	[Go] [int] NULL,
	[Total] AS ([CustomerId]*(2)),
 CONSTRAINT [PK_Customer] PRIMARY KEY CLUSTERED ([CustomerId] ASC)
 WITH (PAD_INDEX = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
CREATE TABLE [dbo].[Visit](
	[VisitId] [bigint] NOT NULL,
	[CustomerId] [int] NOT NULL
)
GO
ALTER TABLE [dbo].[Visit]  WITH CHECK ADD  CONSTRAINT [FK_Visit] FOREIGN KEY([CustomerId])
REFERENCES [dbo].[Customer] ([CustomerId])
GO
ALTER TABLE [dbo].[Customer]  WITH CHECK ADD  CONSTRAINT [CK_Level] CHECK  (([Level]='GOLD' OR [Level]='BASIC'))
GO
EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'고객명', @level0type=N'SCHEMA', @level0name=N'dbo',
  @level1type=N'TABLE', @level1name=N'Customer', @level2type=N'COLUMN', @level2name=N'Name'
GO
EXEC sp_addextendedproperty 'MS_Description', '고객', 'SCHEMA', 'dbo', 'TABLE', 'Customer'
GO
"""

SQLITE = """
CREATE TABLE author (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, bare, key TEXT);
CREATE TABLE book (
  id INTEGER PRIMARY KEY,
  author_id INTEGER REFERENCES author,
  state TEXT CHECK(state IN ('NEW','OLD')),
  FOREIGN KEY (id) REFERENCES author(id)
) WITHOUT ROWID;
CREATE TABLE copy_of AS SELECT * FROM book;
CREATE VIRTUAL TABLE docs USING fts5(body);
"""


def test_postgres_dump():
    d = ingest(POSTGRES.encode(), "pg.sql")
    assert sorted(d.tables) == ["order_lines", "orders", "shipments"]
    o = d.table("orders")
    assert (o.label, o.description) == ("주문", "주문 한 건의 머리 정보")
    assert o.primary_key == ["order_no"] and o.column("order_no").pk and o.column("order_no").label == "주문번호"
    assert (o.column("order_no").type, o.column("order_no").length) == ("character varying", 20)
    assert o.column("placed_at").type == "timestamp without time zone"
    assert (o.column("total").type, o.column("total").length) == ("numeric", 10) and o.column("tags").type == "text[]"
    assert [v["code"] for v in d.code_of(o.column("status")).values] == ["OPEN", "DONE"]  # IN, as a dump prints it
    assert o.column("mood").code == "mood" and [v["code"] for v in d.codes["mood"].values] == ["calm", "busy"]
    lines = d.table("order_lines")
    assert lines.primary_key == ["order_no", "line_no"]  # a composite key stays whole
    assert lines.references == [{"columns": ["order_no"], "table": "orders", "ref_columns": ["order_no"]}]
    assert [v["code"] for v in d.code_of(lines.column("kind")).values] == ["A", "B"]
    assert d.code_of(lines.column("state")) is None  # NOT IN lists what is refused
    assert d.table("shipments").references == [{"columns": ["order_no", "line_no"], "table": "order_lines",
                                                "ref_columns": ["order_no", "line_no"]}]


def test_mysql_dump():
    d = ingest(MYSQL.encode(), "my.sql")
    assert sorted(d.tables) == ["coupon", "member"]
    m = d.table("member")
    assert m.label == "회원" and m.primary_key == ["member_no"]
    no = m.column("member_no")
    assert (no.type, no.length, no.label, no.required) == ("bigint unsigned", 20, "회원번호", True)
    grade = m.column("grade")
    assert grade.type == "enum" and grade.label == "등급"
    assert d.code_of(grade).label == "등급" and [v["code"] for v in d.code_of(grade).values] == ["GOLD", "SILVER"]
    assert m.column("key").type == "varchar" and m.column("note").length == 100  # a column may be called key
    assert [c.name for c in m.columns] == ["member_no", "grade", "key", "note", "active"]
    assert [v["code"] for v in d.code_of(m.column("active")).values] == ["0", "1"]
    c = d.table("coupon")
    assert c.label == "it's a coupon"
    assert c.references[0] == {"columns": ["member_no"], "table": "member", "ref_columns": ["member_no"]}
    assert c.references[1]["columns"] == ["coupon_no"]


def test_oracle_export():
    d = ingest(ORACLE.encode(), "ora.sql")
    g = d.table("TB_GOODS")
    assert sorted(d.tables) == ["TB_GOODS", "TB_REVIEW"] and g.label == "상품" and g.primary_key == ["GOODS_NO"]
    assert [c.name for c in g.columns] == ["GOODS_NO", "PRICE", "NAME", "ANY_LEN", "SOLD_YN"]
    assert (g.column("GOODS_NO").type, g.column("GOODS_NO").length) == ("VARCHAR2", 20)
    assert (g.column("PRICE").type, g.column("PRICE").length) == ("NUMBER", 10)
    assert g.column("GOODS_NO").label == "상품번호" and g.column("GOODS_NO").required
    assert [v["code"] for v in d.code_of(g.column("SOLD_YN")).values] == ["Y", "N"]
    r = d.table("TB_REVIEW")
    assert r.primary_key == ["REVIEW_NO"]
    assert r.references == [{"columns": ["GOODS_NO"], "table": "TB_GOODS", "ref_columns": ["GOODS_NO"]}]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "cp949"])
def test_sql_server_script_in_the_encodings_it_is_saved_in(encoding):
    d = ingest(SQLSERVER.encode(encoding), "ms.sql")
    c = d.table("Customer")
    assert sorted(d.tables) == ["Customer", "Visit"] and c.primary_key == ["CustomerId"]
    assert [x.name for x in c.columns] == ["CustomerId", "Name", "Memo", "Level", "Go", "Total"]
    assert (c.column("Name").type, c.column("Name").length, c.column("Name").required) == ("nvarchar", 100, True)
    assert (c.column("Memo").type, c.column("Memo").length) == ("nvarchar", 0)
    assert c.label == "고객" and c.column("Name").label == "고객명"
    assert [v["code"] for v in d.code_of(c.column("Level")).values] == ["GOLD", "BASIC"]  # IN, as SQL Server prints it
    assert d.table("Visit").references == [{"columns": ["CustomerId"], "table": "Customer",
                                            "ref_columns": ["CustomerId"]}]


def test_sqlite_schema():
    d = ingest(SQLITE.encode(), "lite.sql")
    assert sorted(d.tables) == ["author", "book"]  # no columns of its own in the other two
    a = d.table("author")
    assert a.primary_key == ["id"] and a.column("bare").type == "" and a.column("key").type == "TEXT"
    b = d.table("book")
    assert {"columns": ["author_id"], "table": "author", "ref_columns": []} in b.references
    assert {"columns": ["id"], "table": "author", "ref_columns": ["id"]} in b.references
    assert [v["code"] for v in d.code_of(b.column("state")).values] == ["NEW", "OLD"]


def test_a_script_without_terminators_and_a_broken_statement_do_not_stop_the_rest():
    d = ingest(b"CREATE TABLE a (id int)\nCREATE TABLE b (id int, x int\n;\nCREATE TABLE c (id int);\nnonsense here;",
               "x.sql")
    assert sorted(d.tables) == ["a", "b", "c"] and [c.name for c in d.table("b").columns] == ["id", "x"]
    assert _reason(b"SELECT 1; DROP VIEW v;", "x.sql") == "empty"


def test_open_quotes_and_comments_end_with_the_file_and_stay_fast():
    assert sorted(ingest(b"CREATE TABLE a (id int); /* never closed", "x.sql").tables) == ["a"]
    assert sorted(ingest(b"CREATE TABLE a (id int); SELECT 'never closed", "x.sql").tables) == ["a"]
    assert sorted(ingest(b"CREATE TABLE a (id int);" + b"/*/*" * 200_000, "x.sql").tables) == ["a"]


def test_a_definition_from_sql_drafts_the_way_a_sheet_does():
    pytest.importorskip("yaml")
    d = ingest(ORACLE.encode(), "ora.sql")
    dr = draft(schema_backend(d), name="shop", lang="ko", definitions=d)
    objs = {o.name: o for o in dr.objects}
    assert set(objs) == {"Good", "Review"} and objs["Good"].label == "상품"  # the draft names objects in the singular
    assert objs["Good"].prop_of("SOLD_YN").values == ["Y", "N"]
    assert [(lk.source, lk.target) for lk in dr.links] == [("Review", "Good")]


# ---- ERD formats ---------------------------------------------------------------------------------------------

DBML = """
Project shop { database_type: 'PostgreSQL'  Note: 'Table not_a_table { id int }' }
// a comment
Enum core.order_status as OS {
  open [note: '접수']
  "in progress"
  done
}
TablePartial stamped [headerColor: #ff0000] {
  created_at timestamp [not null]
  memo text [note: 'from the partial']
}
Table core.users as U [headercolor: #3498DB, note: '회원'] {
  id integer [pk, increment]
  name "varchar(40)" [not null, unique, note: '이름']
  memo varchar(10)
  tags text[] [note: '태그']
  ~stamped
}
Table orders {
  id int
  country varchar(2)
  user_id int [ref: > U.id, not null]
  status OS
  price decimal(10, 2) [default: 0]
  Note: '''
    주문
    주문 한 건 \\'끝\\''''
  indexes {
    (id, country) [pk]
    (user_id, status) [unique]
    `id*2`
    status [name: 'ix_status']
  }
  checks {
    `price >= 0` [name: 'chk']
  }
}
Table order_items {
  order_id int
  order_country varchar(2)
  sku varchar(20)
  profile_id int [ref: - profiles.id]
  note { 'long form note' }
  records (order_id) { 1 }
}
Table profiles { id int [pk] }
Table user_infos { user_id int }
Table authors { id int [pk] }
Table books { id int [pk] }
Ref fk_item: order_items.(order_id, order_country) > orders.(id, country) [delete: cascade]
Ref { U.id < orders.user_id }
Ref: U.id - user_infos.user_id
Ref: order_items.sku >? books.id
Ref: authors.id <> books.id
TableGroup g { orders order_items }
records core.users(id) { 1 }
"""


def test_dbml():
    d = ingest(DBML.encode(), "shop.dbml")
    assert "not_a_table" not in d.tables and "stamped" not in d.tables
    assert sorted(d.tables) == ["authors", "books", "order_items", "orders", "profiles", "user_infos", "users"]
    u = d.table("users")
    assert u.label == "회원" and u.primary_key == ["id"] and u.column("id").pk
    assert (u.column("name").type, u.column("name").required, u.column("name").label) == ("varchar(40)", True, "이름")
    assert u.column("tags").type == "text[]" and u.column("tags").label == "태그"
    assert [c.name for c in u.columns] == ["created_at", "id", "name", "memo", "tags"]  # the partial's, then its own
    assert u.column("memo").type == "varchar" and u.column("created_at").required  # the table's own column wins
    o = d.table("orders")
    assert o.primary_key == ["id", "country"] and o.column("id").pk and o.column("country").required
    assert (o.label, o.description) == ("주문", "주문 한 건 '끝'") and o.column("price").length == 10
    assert o.references == [{"columns": ["user_id"], "table": "users", "ref_columns": ["id"]}] * 2  # inline and long
    assert o.column("status").code == "order_status"
    g = d.codes["order_status"]
    assert [(v["code"], v["name"]) for v in g.values] == [("open", "접수"), ("in progress", ""), ("done", "")]
    i = d.table("order_items")
    assert {"columns": ["order_id", "order_country"], "table": "orders",
            "ref_columns": ["id", "country"]} in i.references
    assert {"columns": ["sku"], "table": "books", "ref_columns": ["id"]} in i.references  # the ? only says optional
    assert {"columns": ["profile_id"], "table": "profiles", "ref_columns": ["id"]} in i.references  # the column with it
    assert i.label == "long form note"
    assert d.table("user_infos").references == [{"columns": ["user_id"], "table": "users", "ref_columns": ["id"]}]
    assert d.table("authors").references == [] and d.table("books").references == []  # many to many has no key


PDM = """<?xml version="1.0" encoding="UTF-8"?>
<?PowerDesigner AppLocale="UTF16" Name="shop" Target="ORACLE Version 11g" signature="PDM_DATA_MODEL_XML" version="16.5.0"?>
<!-- do not edit this file -->
<Model xmlns:a="attribute" xmlns:c="collection" xmlns:o="object">
<o:RootObject Id="o1"><c:Children><o:Model Id="o2">
<a:Name>shop</a:Name><a:Code>SHOP</a:Code>
<c:Tables>
<o:Table Id="o10"><a:Name>주문</a:Name><a:Code>TB_ORDER</a:Code><a:Comment>주문 머리</a:Comment>
 <c:Columns>
  <o:Column Id="o11"><a:Name>주문번호</a:Name><a:Code>ORDER_NO</a:Code><a:DataType>VARCHAR2(20)</a:DataType>
   <a:Length>20</a:Length><a:Column.Mandatory>1</a:Column.Mandatory></o:Column>
  <o:Column Id="o12"><a:Name>순번</a:Name><a:Code>SEQ</a:Code><a:DataType>NUMBER(5,0)</a:DataType>
   <a:Mandatory>1</a:Mandatory></o:Column>
  <o:Column Id="o13"><a:Name>상태</a:Name><a:Code>STAT_CD</a:Code><a:DataType>CHAR(2)</a:DataType>
   <a:ListOfValues>10&#9;접수&#10;20&#9;완료</a:ListOfValues></o:Column>
 </c:Columns>
 <c:Keys><o:Key Id="o14"><a:Name>PK</a:Name><a:Code>PK_ORDER</a:Code>
  <c:Key.Columns><o:Column Ref="o11"/><o:Column Ref="o12"/></c:Key.Columns></o:Key></c:Keys>
 <c:PrimaryKey><o:Key Ref="o14"/></c:PrimaryKey>
</o:Table>
<o:Table Id="o20"><a:Name>배송</a:Name><a:Code>TB_DELIVERY</a:Code>
 <c:Columns>
  <o:Column Id="o21"><a:Name>배송번호</a:Name><a:Code>DELI_NO</a:Code><a:DataType>VARCHAR2(20)</a:DataType></o:Column>
  <o:Column Id="o22"><a:Name>주문번호</a:Name><a:Code>ORDER_NO</a:Code><a:DataType>VARCHAR2(20)</a:DataType></o:Column>
  <o:Column Id="o23"><a:Name>순번</a:Name><a:Code>ORDER_SEQ</a:Code><a:DataType>NUMBER(5,0)</a:DataType></o:Column>
  <o:Column Id="o24"><a:Name>창고</a:Name><a:Code>WH_NO</a:Code><a:DataType>VARCHAR2(20)</a:DataType></o:Column>
 </c:Columns>
</o:Table>
<o:Shortcut Id="o30"><a:Name>창고</a:Name><a:Code>TB_WAREHOUSE</a:Code></o:Shortcut>
</c:Tables>
<c:References>
<o:Reference Id="o40"><a:Name>r</a:Name><a:Code>FK_DELI</a:Code>
 <c:ParentTable><o:Table Ref="o10"/></c:ParentTable><c:ChildTable><o:Table Ref="o20"/></c:ChildTable>
 <c:Joins>
  <o:ReferenceJoin Id="o41"><c:Object1><o:Column Ref="o11"/></c:Object1><c:Object2><o:Column Ref="o22"/></c:Object2></o:ReferenceJoin>
  <o:ReferenceJoin Id="o42"><c:Object1><o:Column Ref="o12"/></c:Object1><c:Object2><o:Column Ref="o23"/></c:Object2></o:ReferenceJoin>
 </c:Joins>
</o:Reference>
<o:Reference Id="o43"><a:Code>FK_WH</a:Code>
 <c:ParentTable><o:Shortcut Ref="o30"/></c:ParentTable><c:ChildTable><o:Table Ref="o20"/></c:ChildTable>
 <c:Joins><o:ReferenceJoin Id="o44"><c:Object2><o:Column Ref="o24"/></c:Object2></o:ReferenceJoin></c:Joins>
</o:Reference>
</c:References>
<c:DefaultDiagram><o:PhysicalDiagram Ref="o50"/></c:DefaultDiagram>
<c:PhysicalDiagrams><o:PhysicalDiagram Id="o50"><c:Symbols><o:TableSymbol Id="o51">
 <c:Object><o:Table Ref="o10"/></c:Object></o:TableSymbol></c:Symbols></o:PhysicalDiagram></c:PhysicalDiagrams>
</o:Model></c:Children></o:RootObject></Model>"""


def test_power_designer_model():
    d = ingest(PDM.encode(), "shop.pdm")
    assert sorted(d.tables) == ["TB_DELIVERY", "TB_ORDER"]
    o = d.table("TB_ORDER")
    assert (o.label, o.description) == ("주문", "주문 머리") and o.primary_key == ["ORDER_NO", "SEQ"]
    c = o.column("ORDER_NO")
    assert (c.label, c.type, c.length, c.required, c.pk) == ("주문번호", "VARCHAR2", 20, True, True)
    assert o.column("SEQ").required and o.column("SEQ").type == "NUMBER"  # the older name of the flag
    assert [(v["code"], v["name"]) for v in d.code_of(o.column("STAT_CD")).values] == [("10", "접수"), ("20", "완료")]
    assert d.code_of(o.column("STAT_CD")).label == "상태"
    assert d.table("TB_DELIVERY").references == [
        {"columns": ["ORDER_NO", "ORDER_SEQ"], "table": "TB_ORDER", "ref_columns": ["ORDER_NO", "SEQ"]},
        {"columns": ["WH_NO"], "table": "TB_WAREHOUSE", "ref_columns": [""]}]


def test_a_binary_power_designer_model_says_to_save_it_as_xml():
    with pytest.raises(IngestError) as e:
        ingest(b"\x01\x02 binary model", "shop.pdm")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "XML"


def _value(kind: str, key: str, text: str) -> str:
    return f'<value type="{kind}" key="{key}">{text}</value>'


def _mwb_column(id_: str, name: str, type_: str, *, not_null: int = 0, length: int = -1, comment: str = "",
                params: str = "") -> str:
    return (f'<value type="object" struct-name="db.mysql.Column" id="{id_}">{_value("string", "name", name)}'
            f'{_value("int", "isNotNull", not_null)}{_value("int", "length", length)}{_value("int", "precision", -1)}'
            f'{_value("string", "comment", comment)}{_value("string", "datatypeExplicitParams", params)}'
            f'<link type="object" struct-name="db.SimpleDatatype" key="simpleType">'
            f'com.mysql.rdbms.mysql.datatype.{type_}</link></value>')


def _mwb_index(id_: str, cols: list[str]) -> str:
    items = "".join(f'<value type="object" struct-name="db.mysql.IndexColumn" id="{id_}{c}">'
                    f'<link type="object" struct-name="db.Column" key="referencedColumn">{c}</link></value>'
                    for c in cols)
    return (f'<value type="object" struct-name="db.mysql.Index" id="{id_}">{_value("int", "isPrimary", 1)}'
            f'{_value("string", "indexType", "PRIMARY")}'
            f'<value type="list" content-type="object" key="columns">{items}</value></value>')


MWB = f"""<?xml version="1.0"?>
<data grt_format="2.0" document_type="MySQL Workbench Model" version="1.4.4">
<value type="object" struct-name="workbench.Document" id="d1">
<value type="list" content-type="object" key="physicalModels">
<value type="object" struct-name="workbench.physical.Model" id="m1">
<value type="object" struct-name="db.mysql.Catalog" id="c1" key="catalog">
<value type="list" content-type="object" key="schemata">
<value type="object" struct-name="db.mysql.Schema" id="s1">{_value("string", "name", "shop")}
<value type="list" content-type="object" content-struct-name="db.mysql.Table" key="tables">
<value type="object" struct-name="db.mysql.Table" id="t1">{_value("string", "name", "film")}
{_value("string", "comment", "영화")}
<value type="list" content-type="object" key="columns">
{_mwb_column("a1", "film_id", "int", not_null=1, comment="영화번호")}
{_mwb_column("a2", "lang", "varchar", length=20)}
{_mwb_column("a3", "rating", "enum", params="('G','PG')")}
</value>
<value type="list" content-type="object" key="indices">{_mwb_index("i1", ["a1", "a2"])}</value>
</value>
<value type="object" struct-name="db.mysql.Table" id="t2">{_value("string", "name", "actor_film")}
<value type="list" content-type="object" key="columns">
{_mwb_column("b1", "film_id", "int", not_null=1)}
{_mwb_column("b2", "lang", "varchar", length=20)}
</value>
<value type="list" content-type="object" key="foreignKeys">
<value type="object" struct-name="db.mysql.ForeignKey" id="f1">{_value("string", "name", "fk")}
<link type="object" struct-name="db.mysql.Table" key="referencedTable">t1</link>
<value type="list" content-type="object" key="columns"><link type="object">b1</link><link type="object">b2</link></value>
<value type="list" content-type="object" key="referencedColumns"><link type="object">a1</link><link type="object">a2</link></value>
</value></value>
</value>
</value></value></value></value></value></value>
<value type="object" struct-name="workbench.physical.TableFigure" id="tf1">
<link type="object" struct-name="db.Table" key="table">t1</link></value>
</value></data>"""


def test_mysql_workbench_model():
    d = ingest(_zip({"document.mwb.xml": MWB, "lock": ""}), "shop.mwb")
    assert sorted(d.tables) == ["actor_film", "film"]
    f = d.table("film")
    assert f.label == "영화" and f.primary_key == ["film_id", "lang"]
    c = f.column("film_id")
    assert (c.type, c.required, c.pk, c.label) == ("INT", True, True, "영화번호")
    assert (f.column("lang").type, f.column("lang").length) == ("VARCHAR", 20)
    assert [v["code"] for v in d.code_of(f.column("rating")).values] == ["G", "PG"]
    assert d.table("actor_film").references == [{"columns": ["film_id", "lang"], "table": "film",
                                                 "ref_columns": ["film_id", "lang"]}]


# ---- documents -----------------------------------------------------------------------------------------------


def _para(text: str, style: str = "", numbered: bool = False) -> str:
    props = f'<w:pStyle w:val="{style}"/>' if style else ""
    props += '<w:numPr><w:numId w:val="1"/></w:numPr>' if numbered else ""
    return f'<w:p><w:pPr>{props}</w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{text}</w:t></w:r></w:p>'


DOCX = {
    "word/styles.xml": f"""<?xml version="1.0"?><w:styles {W}>
      <w:style w:type="paragraph" w:styleId="1"><w:name w:val="heading 1"/></w:style>
      <w:style w:type="paragraph" w:styleId="a0"><w:name w:val="Normal"/></w:style></w:styles>""",
    "word/document.xml": f"""<?xml version="1.0"?><w:document {W}><w:body>
      {_para("머리말")}
      {_para("1. 교환", "1")}
      {_para("7일 이내 교환할 수 있습니다.")}
      {_para("미개봉 상품", numbered=True)}
      <w:tbl><w:tblPr/><w:tr><w:tc><w:p><w:r><w:t>구분</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>기간</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>의류</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>7일</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      {_para("2. 반품", "Heading2")}
      <w:p><w:r><w:t>왕복 배송비는</w:t></w:r><w:r><w:tab/><w:t xml:space="preserve"> 고객 부담입니다.</w:t></w:r>
        <w:del><w:r><w:delText>지운 말</w:delText></w:r></w:del>
        <mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
          <mc:Choice Requires="wps"><w:r><w:t> 본문</w:t></w:r></mc:Choice>
          <mc:Fallback><w:r><w:t> 사본</w:t></w:r></mc:Fallback></mc:AlternateContent></w:p>
      <w:sdt><w:sdtContent>{_para("불가 조건은 금지 규정을 따릅니다.")}</w:sdtContent></w:sdt>
      <w:sectPr/></w:body></w:document>"""}


def test_word_document():
    d = ingest(_zip(DOCX), "교환정책서.docx")
    doc = d.documents[0]
    assert doc["name"] == "교환정책서" and doc["kind"] == "policy" and d.sources == ["교환정책서.docx"]
    assert [s["title"] for s in doc["sections"]] == ["", "1. 교환", "2. 반품"]  # style 1 is Heading 1 in Korean Word
    assert doc["sections"][1]["text"].splitlines() == ["7일 이내 교환할 수 있습니다.", "- 미개봉 상품", "구분 | 기간",
                                                       "의류 | 7일"]
    assert doc["sections"][2]["text"].splitlines()[0] == "왕복 배송비는\t 고객 부담입니다. 본문"
    assert "지운 말" not in doc["text"] and "사본" not in doc["text"]
    assert doc["text"].startswith("머리말\n1. 교환\n")


def _slide(title: str, body: str, table: list[list[str]] | None = None) -> str:
    cell = "<a:tc><a:txBody><a:p><a:r><a:t>{}</a:t></a:r></a:p></a:txBody></a:tc>"
    rows = "".join("<a:tr>" + "".join(cell.format(c) for c in r) + "</a:tr>" for r in table or [])
    frame = ("<p:graphicFrame><a:graphic><a:graphicData>"
             f"<a:tbl>{rows}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>")
    head = ('<p:sp><p:nvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r>'
            f'<a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp>') if title else ""
    return (f'<p:sld {P} {A}><p:cSld><p:spTree>{head}<p:grpSp><p:sp><p:txBody><a:p><a:r><a:t>{body}</a:t></a:r>'
            f'<a:r><a:t> 끝</a:t></a:r></a:p></p:txBody></p:sp></p:grpSp>'
            f'{frame if table else ""}</p:spTree></p:cSld></p:sld>')


def test_powerpoint_deck_in_the_order_it_shows():
    rels = ('<Relationships xmlns="r"><Relationship Id="rId1" Target="slides/slide1.xml"/>'
            '<Relationship Id="rId2" Target="/ppt/slides/slide10.xml"/></Relationships>')
    deck = {"ppt/presentation.xml": f'<p:presentation {P} {R}><p:sldIdLst><p:sldId id="256" r:id="rId2"/>'
                                    f'<p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>',
            "ppt/_rels/presentation.xml.rels": rels,
            "ppt/slides/slide1.xml": _slide("주문 목록", "검색 조건", [["항목", "설명"], ["주문번호", "20자리"]]),
            "ppt/slides/slide10.xml": _slide("", "표지")}
    doc = ingest(_zip(deck), "주문화면.pptx").documents[0]
    assert doc["kind"] == "screen"
    assert [s["title"] for s in doc["sections"]] == ["Slide 1", "주문 목록"]
    assert doc["sections"][0]["text"] == "표지 끝"
    assert doc["sections"][1]["text"].splitlines() == ["검색 조건 끝", "항목 | 설명", "주문번호 | 20자리"]


def test_hancom_document():
    hp = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    hs = 'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    hh = 'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'

    def p(text, style="0", extra=""):
        return f'<hp:p styleIDRef="{style}"><hp:run charPrIDRef="1">{extra}<hp:t>{text}</hp:t></hp:run></hp:p>'

    table = ('<hp:tbl><hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>등급</hp:t></hp:run></hp:p></hp:subList></hp:tc>'
             '<hp:tc><hp:subList><hp:p><hp:run><hp:t>혜택</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl>')
    inner = "<hp:subList><hp:p><hp:run><hp:t>{}</hp:t></hp:run></hp:p></hp:subList>"
    box = (f'<hp:p styleIDRef="0"><hp:run><hp:rect><hp:drawText>{inner.format("글상자")}</hp:drawText></hp:rect>'
           f'<hp:ctrl><hp:footNote>{inner.format("각주")}</hp:footNote></hp:ctrl></hp:run></hp:p>')
    doc = ingest(_zip({
        "mimetype": "application/hwp+zip",
        "Contents/header.xml": f'<hh:head {hh}><hh:styles><hh:style id="0" name="바탕글"/>'
                               f'<hh:style id="2" name="개요 1" engName="Outline 1"/></hh:styles></hh:head>',
        "Contents/section1.xml": f'<hs:sec {hs} {hp}>{p("둘째 구역")}</hs:sec>',
        "Contents/section0.xml": f'<hs:sec {hs} {hp}><hp:p styleIDRef="0"><hp:run><hp:secPr/></hp:run></hp:p>'
                                 f'{p("회원 등급", "2")}{p("앞<hp:tab/>뒤<hp:lineBreak/>끝")}'
                                 f'{p("제1조 (목적)")}<hp:p styleIDRef="0"><hp:run>{table}</hp:run></hp:p>'
                                 f'{box}</hs:sec>'}),
        "회원규정.hwpx").documents[0]
    assert [s["title"] for s in doc["sections"]] == ["회원 등급", "제1조 (목적)"]
    assert doc["sections"][0]["text"].splitlines() == ["앞\t뒤", "끝"]
    assert doc["sections"][1]["text"].splitlines() == ["등급 | 혜택", "글상자", "각주", "둘째 구역"]


def test_html_leaves_out_what_is_not_read():
    doc = ingest("""<html><head><title>창 제목</title><style>h1 { color: red }</style></head><body>
      <script>document.write("CREATE TABLE fake (id int)")</script>
      <h1>배송 &amp; 반품</h1><p>당일 <b>출고</b>합니다.<br>주말 제외</p>
      <ul><li>산간 지역</li><li>도서 지역</li></ul>
      <table><tr><th>지역</th><th>비용</th></tr><tr><td>산간<td>3,000원</tr></table>
      <h2>예외</h2><noscript>스크립트 없음</noscript><div>없음</div></body></html>""".encode(), "안내.html").documents[0]
    assert [s["title"] for s in doc["sections"]] == ["배송 & 반품", "예외"]
    assert doc["sections"][0]["text"].splitlines() == ["당일 출고합니다. 주말 제외", "- 산간 지역", "- 도서 지역",
                                                       "지역 | 비용", "산간 | 3,000원"]
    assert doc["sections"][1]["text"] == "없음"
    assert not any(x in doc["text"] for x in ("fake", "color", "창 제목", "스크립트"))


def test_markdown_and_text():
    doc = ingest(b"intro\n# One\nbody\n```\n# not a heading\n```\n## Two ##\nmore\n", "a.md").documents[0]
    assert [s["title"] for s in doc["sections"]] == ["", "One", "Two"]
    assert "# not a heading" in doc["sections"][1]["text"]
    text = "제1조 (목적)\n이 규정은 정한다.\n1.2 반품\n1. 고객은 7일 이내 반품할 수 있다.\n2024.01.15 작성\n3.14\n"
    doc = ingest(text.encode("cp949"), "규정.txt").documents[0]
    assert [s["title"] for s in doc["sections"]] == ["제1조 (목적)", "1.2 반품"]
    assert doc["sections"][1]["text"].splitlines() == ["1. 고객은 7일 이내 반품할 수 있다.", "2024.01.15 작성", "3.14"]


def test_a_document_says_what_kind_it_is():
    assert ingest(b"nothing much here at all", "a.txt").documents[0]["kind"] == "other"
    rules = "제1조 반품 정책. 고객은 교환할 수 있다. 환불은 불가하다."
    assert ingest(rules.encode(), "a.txt").documents[0]["kind"] == "policy"


def _pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               b"/Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % x for x in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)


def test_pdf_with_its_extra():
    pytest.importorskip("pypdf")
    doc = ingest(_pdf("Returns within seven days"), "policy.pdf").documents[0]
    assert doc["name"] == "policy" and "Returns within seven days" in doc["text"]
    assert ingest(_pdf("sniffed"), "no-extension").documents[0]["text"] == "sniffed"
    assert _reason(_pdf(""), "blank.pdf") == "empty"
    assert _reason(b"%PDF-1.4 not really", "broken.pdf") == "format"


def test_pdf_without_its_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", None)  # the import fails, as it does when the extra is not installed
    with pytest.raises(IngestError, match="xgen-space.pdf") as e:
        ingest(b"%PDF-1.4", "a.pdf")
    assert e.value.reason == "needs_extra"


# ---- sheets and JSON -----------------------------------------------------------------------------------------


def test_a_glossary_sheet_with_korean_or_english_headers():
    sheet = Table("g", ["표준 용어", "유의어", "혼용 금지", "정의", "영문명", "약어", "컬럼", "비고"], [
        ["주문내역", "주문상세, 주문 품목;오더라인/구매내역·주문줄", "주문리스트", "한 주문의 상품", "Order Detail",
         "ORD_DTL", "ORD_DTL_NO", "x"],
        ["", "빈 줄", "", "", "", "", "", ""]])
    t = from_sheets([sheet]).terms
    assert t == [{"term": "주문내역", "synonyms": ["주문상세", "주문 품목", "오더라인", "구매내역", "주문줄"],
                  "avoid": ["주문리스트"], "definition": "한 주문의 상품", "english": "Order Detail",
                  "abbreviation": "ORD_DTL", "column": "ORD_DTL_NO"}]
    sheet = Table("g", ["Term", "Synonyms", "Avoid", "Definition"], [["order", "purchase", "buy", "a sale"]])
    assert from_sheets([sheet]).terms[0]["avoid"] == ["buy"]
    assert from_sheets([Table("g", ["용어"], [["주문"]])]) is None  # a list of words defines nothing


def test_a_glossary_known_by_qualified_headers_keeps_related_terms_apart_from_synonyms():
    sheet = Table("g", ["출처", "용어명 (국문)", "용어 구분 (선택)", "관련 용어 (선택)"],
                  [["주문", "1차 할인", "파생어", "2차 할인"]])
    assert from_sheets([sheet]).terms == [{"term": "1차 할인", "synonyms": [], "avoid": [], "definition": "",
                                           "english": "", "abbreviation": "", "column": ""}]
    t = from_sheets([Table("t", ["테이블명 (물리)", "컬럼명 (물리)"], [["T", "A"]])])
    assert t.table("T").columns[0].name == "A"


def test_a_message_sheet():
    sheet = Table("m", ["메시지코드", "메시지 내용", "구분", "화면"],
                  [["MSG-001", "주문이 완료되었습니다.", "안내", "주문완료"], ["MSG-002", "재고가 없습니다.", "오류", ""],
                   ["주문관리", "", "", ""]])
    d = from_sheets([sheet])
    assert [m["code"] for m in d.messages] == ["MSG-001", "MSG-002"]  # the row that only labels a section is left out
    assert d.messages[0] == {"code": "MSG-001", "text": "주문이 완료되었습니다.", "kind": "안내", "screen": "주문완료"}
    d = from_sheets([Table("m", ["메시지코드", "메시지", "화면코드"], [["E1", "실패", "ORD-01"]])])
    assert d.messages[0]["screen"] == "ORD-01"
    d = from_sheets([Table("m", ["메시지ID", "문구"], [["E1", "실패"]]),
                     Table("n", ["code", "message"], [["E2", "fail"]])])
    assert [m["code"] for m in d.messages] == ["E1", "E2"]


def test_a_log_with_code_and_message_columns_stays_data():
    log = Table("log", ["at", "code", "message"], [[str(i), "E1", "timeout"] for i in range(10)])
    assert from_sheets([log]) is None


def test_the_four_sheets_of_a_workbook_read_together():
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    wb = Workbook()
    wb.active.append(["테이블명", "컬럼명", "PK"])
    wb.active.append(["TB_A", "A_NO", "Y"])
    for rows in ([["코드그룹", "코드", "코드명"], ["G1", "1", "하나"]], [["용어", "정의"], ["가", "나"]],
                 [["메시지코드", "메시지"], ["M1", "다"]], [["번호", "값"], ["1", "2"]]):
        ws = wb.create_sheet()
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    d = ingest(buf.getvalue(), "all.xlsx")
    assert d.counts() == {"tables": 1, "columns": 1, "references": 0, "codes": 1, "code_values": 1, "terms": 1,
                          "messages": 1}
    assert ingest(buf.getvalue(), "no-extension").counts() == d.counts()  # a workbook is known by what it holds


CANONICAL = {
    "tables": [{"name": "T", "columns": [{"name": "A", "pk": True, "required": True},
                                         {"name": "B", "pk": True, "required": True}],
                "primary_key": ["A", "B"],
                "references": [{"columns": ["A", "B"], "table": "U", "ref_columns": ["X", "Y"]}]}],
    "codes": {"G": {"label": "그룹", "values": [{"code": "1", "name": "하나", "use": True}]}},
    "terms": [{"term": "주문내역", "synonyms": ["주문상세"], "avoid": [], "definition": "", "english": "",
               "abbreviation": "", "column": ""}],
    "messages": [{"code": "MSG-001", "text": "완료", "kind": "", "screen": ""}],
    "documents": [{"name": "교환정책서", "kind": "policy", "text": "반품",
                   "sections": [{"title": "1.2 반품", "text": "반품"}]}]}


def test_the_canonical_json_passes_through_unchanged():
    d = ingest(json.dumps(CANONICAL).encode(), "bundle.json")
    assert d.to_dict() == CANONICAL
    assert d.counts() == {"tables": 1, "columns": 2, "references": 1, "codes": 1, "code_values": 1, "terms": 1,
                          "messages": 1, "documents": 1}
    assert ingest(json.dumps({"terms": CANONICAL["terms"]}).encode(), "t.json").terms == CANONICAL["terms"]


def test_json_takes_the_usual_synonyms_and_refuses_what_is_not_a_bundle():
    d = Definitions.from_dict({"terms": [{"name": "a", "aliases": "b, c"}, {"synonyms": ["no term"]}],
                               "messages": [{"id": "M", "message": "t", "type": "오류"}],
                               "documents": [{"title": "d", "kind": "memo", "text": "x"}]})
    assert d.terms[0]["synonyms"] == ["b", "c"] and len(d.terms) == 1 and d.messages[0]["kind"] == "오류"
    assert d.documents[0] == {"name": "d", "kind": "other", "text": "x", "sections": []}
    for bad in (b'{"other": 1}', b"[1]", b"{broken", b'{"tables": 5}', b'{"terms": [1]}', b"[" * 200_000):
        assert _reason(bad, "x.json") == "format"


def test_merging_keeps_everything_and_the_later_source_wins():
    a = Definitions.from_dict({"terms": [{"term": "x", "definition": "a"}, {"term": "x", "definition": "b"},
                                         {"term": "y"}],
                               "messages": [{"code": "M", "text": "old"}], "documents": [{"name": "d", "text": "old"}]},
                              "a")
    b = Definitions.from_dict({"terms": [{"term": "y", "definition": "new"}],
                               "messages": [{"code": "M", "text": "new"}],
                               "documents": [{"name": "e", "text": "e"}]}, "b")
    m = a.merge(b)
    assert [(t["term"], t["definition"]) for t in m.terms] == [("x", "a"), ("x", "b"), ("y", "new")]
    assert [x["text"] for x in m.messages] == ["new"] and [x["name"] for x in m.documents] == ["d", "e"]
    assert m.sources == ["a", "b"] and len(a.terms) == 3 and a.messages[0]["text"] == "old"


# ---- choosing an adapter -------------------------------------------------------------------------------------


@pytest.mark.parametrize("data,kind", [
    (b"create  table t (id int);", "tables"), (b"Table t {\n id int\n}\n", "tables"), (PDM.encode(), "tables"),
    (b"<!doctype html><p>hello</p>", "documents"), (b'{"terms": [{"term": "a"}]}', "terms"),
    (b"just some words", "documents"), (_zip(DOCX), "documents"), (_zip({"document.mwb.xml": MWB}), "tables"),
])
def test_a_file_without_a_known_extension_is_known_by_its_content(data, kind):
    assert getattr(ingest(data, "export.dat"), kind)


@pytest.mark.parametrize("source,to", [("a.doc", "DOCX"), ("a.hwp", "HWPX"), ("a.ppt", "PPTX"), ("a.xls", "XLSX"),
                                       ("a.erwin", "SQL, XLSX, PDF"), ("a", "SQL, XLSX, PDF")])
def test_a_binary_format_says_what_to_export_to(source, to):
    with pytest.raises(IngestError, match=to) as e:
        ingest(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\0\0\0\0", source)
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == to


@pytest.mark.parametrize("source,to", [("a.hwpx", "HWPX"), ("locked.docx", "DOCX"), ("a.pptx", "PPTX")])
def test_an_older_binary_under_a_newer_name_says_the_same(source, to):
    with pytest.raises(IngestError, match=to) as e:
        ingest(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\0\0", source)
    assert e.value.reason == "export_needed"


def test_a_zip_or_xml_of_nothing_known_says_the_same():
    assert _reason(_zip({"content.xml": "<a/>"}), "a.odt") == "export_needed"
    assert _reason(b'<?xml version="1.0"?><other/>', "a.xml") == "export_needed"


def test_empty_and_malformed_files_get_a_reason():
    assert _reason(b"", "a.sql") == "empty"
    assert _reason(b"   \n", "a.md") == "empty"
    assert _reason(b"not a zip", "a.docx") == "format"
    assert _reason(_zip({"other.xml": "<a/>"}), "a.docx") == "format"
    assert _reason(_zip({"word/document.xml": "<broken"}), "a.docx") == "format"
    assert _reason(b"<other/>", "a.pdm") == "format"
    assert _reason(b"\xff\x00", "a.sql") == "format"
    assert _reason(b"a,b\n1,2\n", "data.csv") == "format"  # rows, and no definitions in them


def test_a_csv_definition_sheet_still_reads():
    d = ingest((EXAMPLE.parent / "definitions" / "테이블정의서.csv").read_bytes(), "테이블정의서.csv")
    assert d.counts()["tables"] == 3


def test_a_text_file_is_rows_or_prose():
    assert is_sheet(b"a,b\n1,2\n3,4\n", "x.txt") and is_sheet(b"", "x.csv") and is_sheet(b"", "x.xlsx")
    assert not is_sheet("첫 문장입니다.\n둘째 문장, 쉼표 하나.\n".encode(), "x.txt") and not is_sheet(b"", "x.sql")
    assert ingest("테이블명\t컬럼명\nT\tA\nT\tB\n".encode(), "x.txt").counts()["columns"] == 2


@pytest.fixture
def adapters(monkeypatch):
    monkeypatch.setattr(ingest_module, "ADAPTERS", dict(ingest_module.ADAPTERS))


PLUGIN = """
from xgen_space.definitions import Definitions, TableDef
from xgen_space.ingest import register


def read(data, source):
    return Definitions({"T": TableDef("T", data.decode())}, sources=[source])

register([".Foo", "bar"], read)
"""


def test_a_format_of_your_own(adapters, tmp_path):
    f = tmp_path / "foo_adapter.py"
    f.write_text(PLUGIN, encoding="utf-8")
    load_adapters([str(f)])
    assert ingest(b"hello", "x.foo").table("T").label == "hello" and ingest(b"hi", "x.BAR").table("T").label == "hi"
    register("baz", lambda data, source: None)
    assert _reason(b"x", "a.baz") == "format"
    register("boom", lambda data, source: 1 / 0)
    assert _reason(b"x", "a.boom") == "format"
    with pytest.raises(IngestError):
        load_adapters([str(tmp_path / "missing.py")])


def test_adapters_from_the_environment(adapters, tmp_path, monkeypatch):
    f = tmp_path / "foo_adapter.py"
    f.write_text(PLUGIN, encoding="utf-8")
    monkeypatch.setenv("XSPACE_ADAPTERS", str(f))
    monkeypatch.setattr(ingest_module, "_env_loaded", False)
    assert ingest(b"hello", "x.foo").table("T").label == "hello"


def test_adapter_paths_split_on_both_separators_and_keep_a_drive():
    assert adapter_paths(r"D:\a\b.py;c.py") == [r"D:\a\b.py", "c.py"]
    assert adapter_paths(r"D:\a.py:E:/b.py") == [r"D:\a.py", "E:/b.py"]
    assert adapter_paths("/a/b.py:/c/d.py;e.py") == ["/a/b.py", "/c/d.py", "e.py"]
    assert adapter_paths("") == []


# ---- what an upload cannot do --------------------------------------------------------------------------------

BOMB = {".docx": "word/document.xml", ".pptx": "ppt/slides/slide1.xml", ".hwpx": "Contents/section0.xml",
        ".mwb": "document.mwb.xml"}


@pytest.mark.parametrize("ext,member", BOMB.items())
def test_every_zip_format_refuses_what_unpacks_past_the_cap(ext, member, monkeypatch):
    monkeypatch.setattr(ingest_module, "UNPACKED_MAX", 1 << 16)
    bomb = _zip({member: b" " * (1 << 17)})
    assert len(bomb) < 1 << 12 and _reason(bomb, f"a{ext}") == "too_large"
    assert _reason(bomb, "no-extension") in ("too_large", "export_needed")


def test_the_cap_counts_every_entry_together(monkeypatch):
    monkeypatch.setattr(ingest_module, "UNPACKED_MAX", 1 << 16)
    assert _reason(_zip({f"word/{i}.xml": b" " * (1 << 14) for i in range(8)}), "a.docx") == "too_large"


@pytest.fixture(scope="module")
def real_bomb() -> bytes:
    return b" " * (ingest_module.UNPACKED_MAX + 1)


@pytest.mark.parametrize("ext,member", [*BOMB.items(), (".xlsx", "xl/workbook.xml")])
def test_a_small_upload_that_inflates_past_64mb(ext, member, real_bomb):
    bomb = _zip({member: real_bomb})
    assert len(bomb) < 1 << 20 and _reason(bomb, f"a{ext}") == "too_large"


def _lying(member: str, real: int, declared: int) -> bytes:
    """A zip whose headers declare far less than its entry inflates to."""
    data = bytearray(_zip({member: b" " * real}))
    for sig, at in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        i = data.find(sig)
        assert struct.unpack_from("<I", data, i + at)[0] == real
        struct.pack_into("<I", data, i + at, declared)
    return bytes(data)


def test_a_zip_that_lies_about_its_size_is_stopped_while_reading(monkeypatch):
    monkeypatch.setattr(ingest_module, "UNPACKED_MAX", 1 << 16)
    lie = _lying("word/document.xml", 1 << 20, 100)
    with zipfile.ZipFile(io.BytesIO(lie)) as z:
        assert sum(i.file_size for i in z.infolist()) == 100  # the declared check alone would let it through
    assert _reason(lie, "a.docx") == "format"  # read no further than declared, then the checksum fails


def test_reading_stops_at_the_cap_whatever_the_entry_declares(monkeypatch):
    z = ingest_module._Archive(_zip({"a": b"x" * 100, "b": b"y" * 100}), "a.zip")
    monkeypatch.setattr(z, "left", 150)
    assert len(z.read("a")) == 100
    with pytest.raises(IngestError) as e:
        z.read("b")
    assert e.value.reason == "too_large"


def test_deep_nesting_ends_in_an_answer():
    deep = b"<a>" * 200_000 + b"</a>" * 200_000
    assert _reason(_zip({"Contents/section0.xml": deep}), "a.hwpx") == "format"
    assert _reason(_zip({"word/document.xml": deep}), "a.docx") == "empty"


def test_a_plugin_that_gives_no_format_to_export_to_still_gets_an_answer(session, adapters):
    def refuse(data, source):
        raise IngestError("export it", "export_needed")

    register("own", refuse)
    with pytest.raises(ValueError, match="SQL, XLSX, PDF 파일로 내보내"):
        session.upload("a.own", b"x")


@pytest.mark.parametrize("data,source", [
    (b"\n" * 2_000_000 + b"x", "a.dat"),  # by content: what looks for a heading word at each line
    (b"# a" + b" " * 2_000_000 + b"b", "a.md"),
    (b"/*" * 1_000_000, "a.sql"),
    (b"'" * 2_000_001, "a.sql"),
    (b"(" * 2_000_000, "a.dbml"),
])
def test_text_made_to_be_slow_is_read_in_linear_time(data, source):
    start = time.perf_counter()
    try:
        ingest(data, source)
    except IngestError:
        pass
    assert time.perf_counter() - start < 10


def test_a_header_made_to_be_slow_is_matched_in_linear_time():
    start = time.perf_counter()
    assert from_sheets([Table("x", ["(" * 1_000_000, "b"], [["1", "2"]])]) is None
    assert time.perf_counter() - start < 5


XXE = '<!DOCTYPE m [<!ENTITY x SYSTEM "file:///etc/hostname">]>'
LAUGHS = ('<!DOCTYPE m [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">'
          '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;">]>')


@pytest.mark.parametrize("doctype", [XXE, LAUGHS, '<!DOCTYPE m SYSTEM "http://example.org/m.dtd">'])
def test_xml_that_declares_a_document_type_is_refused(doctype):
    body = '<?xml version="1.0"?>' + doctype + '<Model xmlns:a="attribute"><a:Name>&x;</a:Name></Model>'
    assert _reason(body.encode(), "a.pdm") == "format"
    assert _reason(_zip({"word/document.xml": body}), "a.docx") == "format"
    assert _reason(_zip({"document.mwb.xml": body}), "a.mwb") == "format"
    assert _reason(_zip({"Contents/section0.xml": body}), "a.hwpx") == "format"
    deck = {"ppt/slides/slide1.xml": body}
    assert _reason(_zip(deck), "a.pptx") == "format"


def test_an_entry_named_outside_the_archive_is_never_written_anywhere(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    body = f"<w:document {W}><w:body>{_para('본문')}</w:body></w:document>"
    data = _zip({"../../evil.txt": "x", "word/document.xml": body})
    assert ingest(data, "a.docx").documents[0]["text"] == "본문"
    assert list(tmp_path.iterdir()) == []


def test_nothing_in_a_file_is_run(tmp_path):
    mark = tmp_path / "ran"
    code = f"open({str(mark)!r}, 'w').close()\n"
    for name in ("adapter.py", "x.txt", "x.md"):
        assert ingest(code.encode(), name).documents
    assert not mark.exists()


# ---- wiring --------------------------------------------------------------------------------------------------


def test_xspace_ingest_writes_one_json_and_counts_it(tmp_path, capsys):
    sql, md = tmp_path / "shop.sql", tmp_path / "정책.md"
    sql.write_bytes(ORACLE.encode())
    md.write_text("# 반품\n내용\n", encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    assert main(["ingest", str(sql), str(md), "-o", str(bundle)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["tables"] == 2 and printed["documents"] == 1 and printed["written"] == str(bundle)
    data = json.loads(bundle.read_text(encoding="utf-8"))
    assert set(data) == {"tables", "codes", "terms", "messages", "documents"} and data["documents"][0]["name"] == "정책"
    assert main(["ingest", str(bundle)]) == 0  # the JSON goes back in as it came out
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data and json.loads(captured.err)["tables"] == 2


def test_xspace_ingest_takes_an_adapter_and_says_what_it_cannot_read(adapters, tmp_path, capsys):
    plugin, f = tmp_path / "foo_adapter.py", tmp_path / "x.foo"
    plugin.write_text(PLUGIN, encoding="utf-8")
    f.write_bytes(b"hello")
    assert main(["ingest", str(f), "--adapter", str(plugin)]) == 0
    assert json.loads(capsys.readouterr().out)["tables"][0]["label"] == "hello"
    blob = tmp_path / "x.hwp"
    blob.write_bytes(b"\xd0\xcf\x11\xe0\0\0")
    with pytest.raises(SystemExit, match="HWPX"):
        main(["ingest", str(blob)])


def test_xspace_draft_takes_definitions_of_any_format(tmp_path, capsys):
    pytest.importorskip("yaml")
    sql = tmp_path / "shop.sql"
    sql.write_bytes(ORACLE.encode())
    assert main(["draft", "--definitions", str(sql), "--lang", "ko"]) == 0
    assert "상품" in capsys.readouterr().out
    md = tmp_path / "a.md"
    md.write_text("text", encoding="utf-8")
    with pytest.raises(SystemExit, match="no tables"):
        main(["draft", "--definitions", str(md)])
    blob = tmp_path / "x.doc"
    blob.write_bytes(b"\xd0\xcf\x11\xe0\0\0")
    with pytest.raises(SystemExit, match="DOCX"):
        main(["draft", "--definitions", str(blob)])


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"))


def test_the_page_takes_every_format_and_lists_it_without_the_full_text(session):
    long = "반품 규정입니다. " * 500
    session.upload("용어.csv", "용어,유의어,정의\n주문내역,주문상세,상품 목록\n".encode())
    session.upload("메시지.csv", "메시지코드,메시지 내용\nM1,완료\n".encode())
    session.upload("정책.md", f"# 반품\n{long}\n".encode())
    st = session.upload("shop.sql", ORACLE.encode())
    assert st["files"] == []
    by = {x["source"]: x for x in st["definitions"]}
    assert by["용어.csv"]["terms"] == 1 and by["용어.csv"]["term_list"] == [{"term": "주문내역", "synonyms": 1}]
    assert by["메시지.csv"]["messages"] == 1 and by["메시지.csv"]["message_list"] == [{"code": "M1", "chars": 2}]
    doc = by["정책.md"]["document_list"][0]
    assert by["정책.md"]["documents"] == 1 and doc["name"] == "정책" and doc["sections"] == 1 and doc["chars"] > 4000
    assert by["shop.sql"]["tables"][0]["key"] == ["GOODS_NO"] and by["shop.sql"]["terms"] == 0
    assert long.strip() not in json.dumps(st, ensure_ascii=False)
    st = session.make_draft("쇼핑몰")
    assert st["pending"]["origin"]["kind"] == "definitions" and st["pending"]["counts"]["objects"] == 2
    assert session.remove_file("정책.md")["pending"] is None


def test_a_prose_text_file_is_a_document_and_a_delimited_one_stays_data(session):
    st = session.upload("메모.txt", "첫 문장입니다.\n둘째 문장입니다.\n".encode())
    assert st["files"] == [] and st["definitions"][0]["documents"] == 1
    st = session.upload("rows.txt", b"a,b\n1,2\n3,4\n")
    assert [f["source"] for f in st["files"]] == ["rows.txt"]


def test_a_document_alone_does_not_make_a_draft(session):
    session.upload("정책.md", "# 반품\n내용\n".encode())
    with pytest.raises(ValueError, match="테이블 정의가 없어 초안을 생성하지 못했습니다"):
        session.make_draft("x")


@pytest.mark.parametrize("name,data,text", [
    ("a.hwp", b"\xd0\xcf\x11\xe0\0\0", "HWPX 파일로 내보내 다시 업로드해 주세요."),
    ("a.erwin", b"\0\0\0\0", "SQL, XLSX, PDF 파일로 내보내 다시 업로드해 주세요."),
    ("a.sql", b"SELECT 1;", "읽을 수 있는 정의나 본문이 없어 정의서를 만들지 못했습니다."),
    ("a.docx", b"not a zip", "파일 내용을 해석할 수 없어 읽지 못했습니다."),
    ("a.docx", _zip({"word/document.xml": b" " * (65 << 20)}),
     "압축 해제 크기가 64MB 한도를 초과해 파일을 열지 못했습니다."),
])
def test_the_page_answers_each_reason_in_korean(session, name, data, text):
    with pytest.raises(ValueError, match=text.replace(".", r"\.")):
        session.upload(name, data)
    assert session.files_state()["definitions"] == []


def test_the_page_says_when_a_reader_is_not_installed(session, monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", None)
    with pytest.raises(ValueError, match="문서 읽기 모듈이 설치되지 않아 파일을 처리하지 못했습니다"):
        session.upload("a.pdf", b"%PDF-1.4")


def test_a_sqlite_file_gives_its_tables_keys_and_references(tmp_path):
    import sqlite3

    f = tmp_path / "x.db"
    c = sqlite3.connect(f)
    c.executescript("CREATE TABLE a (x TEXT, y INT, PRIMARY KEY (x, y)); CREATE TABLE b (id TEXT PRIMARY KEY, x TEXT, "
                    "y INT, FOREIGN KEY (x, y) REFERENCES a (x, y));")
    c.close()
    d = ingest(f.read_bytes(), "x.db")
    assert d.table("a").primary_key == ["x", "y"]
    assert d.table("b").references == [{"columns": ["x", "y"], "table": "a", "ref_columns": ["x", "y"]}]
    assert ingest(f.read_bytes(), "no-extension").counts()["tables"] == 2


def _book(path, sheets):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    wb.save(path)
    return path.read_bytes()


def test_a_project_workbook_has_a_cover_a_title_and_group_rows(tmp_path):
    data = _book(tmp_path / "codes.xlsx", {
        "표지": [[None], ["코드정의서"], ["Ver 1.0"]],
        "코드정의서": [["코드정의서"], [None], [None],
                  ["대분류코드", "중분류코드", "코드명", "코드설명", "사용여부", "정렬순서", "참조1", "참조2"],
                  ["주문(OD)"],
                  ["OD01", "*", "주문상태코드", None, None, None, None, None],
                  ["OD01", "10", "접수", None, "Y", 1, None, None],
                  ["OD01", "90", "취소", None, "N", 2, None, None],
                  ["AC01", "*", "가능업무코드", None, None, None, "OD01(주문상태코드)", "최대 일수"],
                  ["AC01", "11", "주문취소", None, "Y", 1, "10,20", "7"]],
        "다국어": [["대분류코드", "중분류코드", "언어코드", "코드명"], ["OD01", "10", "en", "Received"]],
    })
    d = ingest(data, "codes.xlsx")
    assert set(d.codes) == {"OD01", "AC01"} and d.codes["OD01"].label == "주문상태코드"
    assert [v["code"] for v in d.codes["OD01"].values] == ["10", "90"] and d.codes["OD01"].values[1]["use"] is False
    assert d.codes["AC01"].refs == {"ref1": "OD01(주문상태코드)", "ref2": "최대 일수"}
    assert d.codes["AC01"].values[0]["refs"] == {"ref1": "10,20", "ref2": "7"}
    back = Definitions.from_dict(d.to_dict())
    assert back.codes["AC01"].refs == d.codes["AC01"].refs and back.codes["AC01"].values[0]["refs"]["ref1"] == "10,20"


def test_an_index_sheet_gives_the_keys_and_merges_with_the_model(tmp_path):
    data = _book(tmp_path / "idx.xlsx", {"인덱스정의서": [
        [None], ["인덱스명", "테이블(물리)", "테이블(논리)", "컬럼", "유니크여부", "프라이머리여부"],
        ["pk_ord_line", "ord_line", "주문상세", "{ord_no,line_seq}", "Y", "Y"],
        ["ix_ord_line", "ord_line", "주문상세", "{status}", "N", "N"]]})
    idx = ingest(data, "idx.xlsx")
    assert idx.table("ORD_LINE").primary_key == ["ord_no", "line_seq"]
    model = Definitions.from_dict({"tables": [{"name": "ORD_LINE", "label": "주문상세", "columns": [{"name": "ORD_NO"}]}]})
    both = model.merge(idx)
    assert list(both.tables) == ["ORD_LINE"] and both.table("ord_line").primary_key == ["ord_no", "line_seq"]
    assert [c.name for c in both.table("ord_line").columns] == ["ORD_NO"]


def test_codes_hold_decision_tables_of_both_shapes():
    from xgen_space.definitions import schema_backend
    from xgen_space.draft import draft, studio_from

    pytest.importorskip("yaml")
    defs = Definitions.from_dict({
        "tables": [{"name": "LINE", "columns": [{"name": "LINE_NO", "pk": True}, {"name": "STAT_CD", "code": "OD01"},
                                                {"name": "KIND_CD", "code": "OD02"}, {"name": "REASON_CD", "code": "RS01"}]}],
        "codes": {
            "OD01": {"label": "상태", "values": [{"code": "10", "name": "접수"}, {"code": "20", "name": "완료"}]},
            "OD02": {"label": "구분", "values": [{"code": "1", "name": "일반"}]},
            "AC01": {"label": "가능 업무", "refs": {"ref1": "OD01(상태)", "ref2": "OD02(구분)"}, "values": [
                {"code": "11", "name": "취소", "refs": {"ref1": "10", "ref2": "1"}},
                {"code": "12", "name": "반품", "refs": {"ref1": "10,20", "ref2": "1"}},
                {"code": "13", "name": "폐기", "use": "N", "refs": {"ref1": "10"}}]},
            "RS01": {"label": "사유", "refs": {"ref1": "OD02(구분)", "ref2": "귀책"}, "values": [
                {"code": "100", "name": "단순변심", "refs": {"ref2": "고객"}},
                {"code": "200", "name": "상품불량", "refs": {"ref2": "당사"}}]}}})
    b = schema_backend(defs)
    d = draft(b, name="t", lang="ko", definitions=defs)
    assert {"codes_ac01", "codes_rs01"} <= set(d.decisions)
    assert d.decisions["codes_ac01"]["hit_policy"] == "collect" and d.decisions["codes_rs01"]["hit_policy"] == "first"
    st = studio_from(d, b, graph=False)
    b.script("INSERT INTO LINE VALUES ('L1', '20', '1', '200'); INSERT INTO LINE VALUES ('L2', '10', '1', '100');")
    assert [x["name"] for x in st.decide("codes_ac01", "L1").outputs] == ["반품"]
    assert [x["name"] for x in st.decide("codes_ac01", "L2").outputs] == ["취소", "반품"]  # 폐기 is not in use
    assert st.decide("codes_rs01", "L1").outputs["ref2"] == "당사"
    assert st.decide("codes_rs01", "L1").matched == ["c200"]


def test_an_uploaded_document_feeds_the_policy_draft_by_section_and_a_code_shows_its_message():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    s = StudioSession(load_studio(LIB / "studio.yaml"))
    s.upload("규정.md", "# 반품\n\n7일 이내 반품합니다.\n\n# 교환\n\n14일 이내 교환합니다.\n".encode())
    got = s.document_text("규정")
    assert got["ok"] and got["sections"] == ["반품", "교환"] and "14일" in got["text"]
    part = s.document_text("규정", "교환")
    assert "14일" in part["text"] and "7일" not in part["text"]
    assert not s.document_text("없는 문서")["ok"]
    s.studio.composition.messages = [{"code": "MSG-1", "text": "기간이 지났습니다."}]
    assert s._said({"reason": "MSG-1", "ok": True}) == [{"code": "MSG-1", "text": "기간이 지났습니다."}]


def _hwp_record(tag: int, payload: bytes) -> bytes:
    import struct

    return struct.pack("<I", tag | (len(payload) << 20)) + payload


def _hwp_paragraph(text: str) -> bytes:
    tab = (9).to_bytes(2, "little") * 8  # a control of eight units, as a tab is
    return _hwp_record(67, tab + text.encode("utf-16-le") + (13).to_bytes(2, "little"))


def _hwp_file(lines, *, flags=1, fat_loop=False) -> bytes:
    """The smallest .hwp: a compound file with a header and one compressed section, all in the mini stream."""
    import struct
    import zlib

    pack = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = b"".join(_hwp_paragraph(x) for x in lines)
    section = pack.compress(body) + pack.flush() if flags & 1 else body
    header = b"HWP Document File".ljust(32, b"\0") + b"\0\0\0\5" + struct.pack("<I", flags)
    header = header.ljust(256, b"\0")
    mini = header + section.ljust((len(section) + 63) // 64 * 64, b"\0")
    blocks = len(mini) // 64
    mini_fat = [i + 1 for i in range(blocks - 1)] + [0xFFFFFFFE]
    mini_fat[3] = 0xFFFFFFFE  # the header takes four blocks, the section the rest
    sectors = (len(mini) + 511) // 512

    def entry(name, kind, *, left=0xFFFFFFFF, right=0xFFFFFFFF, child=0xFFFFFFFF, start=0, size=0):
        raw = name.encode("utf-16-le") + b"\0\0"
        return (raw.ljust(64, b"\0") + struct.pack("<HBB", len(raw), kind, 1) + struct.pack("<III", left, right, child)
                + b"\0" * 36 + struct.pack("<IQ", start, size))

    directory = (entry("Root Entry", 5, child=1, start=3, size=len(mini)) + entry("FileHeader", 2, right=2, start=0, size=256)
                 + entry("BodyText", 1, child=3) + entry("Section0", 2, start=4, size=len(section)))
    fat = [0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFE] + [3 + i + 1 for i in range(sectors - 1)] + [0xFFFFFFFE]
    if fat_loop:
        fat[3] = 3
    head = bytearray(512)
    head[:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<HH", head, 30, 9, 6)
    struct.pack_into("<I", head, 44, 1)
    struct.pack_into("<I", head, 48, 1)
    struct.pack_into("<IIII", head, 56, 4096, 2, 1, 0xFFFFFFFE)
    struct.pack_into("<I", head, 72, 0)
    struct.pack_into("<109I", head, 76, 0, *([0xFFFFFFFF] * 108))
    pad = lambda b: b.ljust((len(b) + 511) // 512 * 512, b"\xff")  # noqa: E731
    return (bytes(head) + pad(struct.pack(f"<{len(fat)}I", *fat)) + pad(directory)
            + pad(struct.pack(f"<{len(mini_fat)}I", *mini_fat)) + mini.ljust(sectors * 512, b"\0"))


def test_a_hwp_file_gives_its_text_by_section():
    d = ingest(_hwp_file(["1. 반품 기간", "배송 완료 후 7일 이내 반품할 수 있습니다.", "2. 교환", "교환은 1회만 가능합니다."]), "규정.hwp")
    doc = d.documents[0]
    assert doc["name"] == "규정" and [s["title"] for s in doc["sections"]] == ["1. 반품 기간", "2. 교환"]
    assert "교환은 1회만 가능합니다." in doc["text"]


def test_a_hwp_file_stored_without_compression_reads_too():
    assert "본문" in ingest(_hwp_file(["본문입니다."], flags=0), "a.hwp").documents[0]["text"]


@pytest.mark.parametrize("flags", [1 | 2, 1 | 4])
def test_a_hwp_file_with_a_password_or_for_viewing_is_refused_with_what_to_do(flags):
    with pytest.raises(IngestError) as e:
        ingest(_hwp_file(["내용"], flags=flags), "a.hwp")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "HWPX"


def test_a_malformed_hwp_ends_in_an_answer():
    with pytest.raises(IngestError):
        ingest(_hwp_file(["내용"], fat_loop=True), "a.hwp")
    with pytest.raises(IngestError):
        ingest(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\xff" * 600, "a.hwp")
    with pytest.raises(IngestError):
        ingest(_hwp_file(["내용"])[:700], "a.hwp")


# ---- older Office files --------------------------------------------------------------------------------------

END, FREE = 0xFFFFFFFE, 0xFFFFFFFF
MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _ole(streams: dict[str, bytes]) -> bytes:
    """A compound file of these streams in sectors of their own: a cutoff of 0 keeps them out of the mini stream, which
    the .hwp tests cover."""
    names = list(streams)
    blobs = [streams[n].ljust((len(streams[n]) + 511) // 512 * 512, b"\0") for n in names]
    n_dir = (len(names) + 4) // 4
    n_fat = 1
    while n_fat * 128 < n_fat + n_dir + sum(len(b) // 512 for b in blobs):
        n_fat += 1
    fat = [0xFFFFFFFD] * n_fat

    def link(count: int) -> int:
        start = len(fat)
        fat.extend(range(start + 1, start + count))
        if count:
            fat.append(END)
        return start if count else END

    def entry(name: str, kind: int, *, right=FREE, child=FREE, start=END, size=0) -> bytes:
        raw = name.encode("utf-16-le") + b"\0\0"
        return (raw.ljust(64, b"\0") + struct.pack("<HBB", len(raw), kind, 1) + struct.pack("<III", FREE, right, child)
                + b"\0" * 36 + struct.pack("<IQ", start, size))

    directory_at = link(n_dir)
    entries = [entry("Root Entry", 5, child=1 if names else FREE)]
    for i, (n, b) in enumerate(zip(names, blobs)):
        entries.append(entry(n, 2, right=i + 2 if i + 1 < len(names) else FREE, start=link(len(b) // 512),
                             size=len(streams[n])))
    directory = b"".join(entries).ljust(n_dir * 512, b"\0")
    head = bytearray(512)
    head[:8] = MAGIC
    struct.pack_into("<HH", head, 30, 9, 6)
    struct.pack_into("<II", head, 44, n_fat, directory_at)
    struct.pack_into("<IIIII", head, 56, 0, END, 0, END, 0)
    struct.pack_into("<109I", head, 76, *range(n_fat), *[FREE] * (109 - n_fat))
    table = struct.pack(f"<{n_fat * 128}I", *fat, *[FREE] * (n_fat * 128 - len(fat)))
    return bytes(head) + table + directory + b"".join(blobs)


IN_TABLE, ROW_END = b"\x16\x24\x01", b"\x17\x24\x01"  # sprmPFInTable, sprmPFTtp


def _word(pieces: list[str], props: list[tuple[int, bytes]], *, flags=0x0200, ident=0xA5EC, text_length=None,
          cps=None, stream="1Table", again=1) -> bytes:
    """A .doc: pieces of text, one byte a character where ASCII holds them and two elsewhere, and for each mark that
    ends a paragraph or a cell its (style, properties). Styles 1 to 4 are Heading 1, Heading 2, Title and one of a
    user's own. `again` names the same pieces that many times over in the piece table."""
    start = 1536
    body, marks, places = bytearray(), [], []
    for piece in pieces:
        narrow = piece.isascii()
        places.append((start + len(body)) * 2 | 0x40000000 if narrow else start + len(body))
        for ch in piece:
            body += ch.encode("ascii" if narrow else "utf-16-le")
            if ch in "\r\x07":
                marks.append(start + len(body))
    runs = len(marks)
    assert runs == len(props) and runs < 30
    page = bytearray(512)
    struct.pack_into(f"<{runs + 1}I", page, 0, start, *marks)
    page[511] = runs
    top = 510
    for i, (style, sprms) in enumerate(props):
        blob = struct.pack("<H", style) + sprms
        head = bytes([(len(blob) + 1) // 2]) if len(blob) % 2 else bytes([0, len(blob) // 2])
        top = (top - len(head) - len(blob)) // 2 * 2
        page[top:top + len(head) + len(blob)] = head + blob
        page[4 * (runs + 1) + 13 * i] = top // 2
    page_at = (start + len(body) + 511) // 512
    word = bytearray(page_at * 512 + 512)
    word[start:start + len(body)] = body
    word[page_at * 512:] = page
    lengths = [len(p.encode("utf-16-le")) // 2 for p in pieces]
    cps = cps if cps is not None else [0, *accumulate(lengths * again)]
    pcds = b"".join(struct.pack("<HIH", 0, fc, 0) for fc in places) * again
    plc = struct.pack(f"<{len(cps)}I", *cps) + pcds
    clx = b"\x01" + struct.pack("<H", 3) + b"abc" + b"\x02" + struct.pack("<I", len(plc)) + plc
    styles = b"".join(struct.pack("<HH", 10, sti) + b"\0" * 8 for sti in (0, 1, 2, 62, 0xFFE))
    stsh = struct.pack("<HH", 18, 5) + b"\0" * 16 + styles
    bte = struct.pack("<III", start, marks[-1] if marks else start, page_at)
    table = stsh + bte + clx
    struct.pack_into("<HH", word, 0, ident, 0xC1)
    struct.pack_into("<H", word, 0x0A, flags)
    struct.pack_into("<I", word, 76, sum(lengths) * again if text_length is None else text_length)
    struct.pack_into("<II", word, 0xA2, 0, len(stsh))
    struct.pack_into("<II", word, 0x102, len(stsh), len(bte))
    struct.pack_into("<II", word, 0x1A2, len(stsh) + len(bte), len(clx))
    return _ole({"WordDocument": bytes(word), stream: table})


def test_a_doc_gives_its_sections_by_heading_style_and_by_number():
    d = ingest(_word(["반품 규정\r", "First body line.\r", "기간\r", "가까운 설명입니다.\r",
                      "1. Scope\r", "Own style text\r"],
                     [(3, b""), (0, b""), (1, b""), (0, b""), (0, b""), (4, b"")]), "규정.doc").documents[0]
    assert d["name"] == "규정" and d["kind"] == "other"
    assert [s["title"] for s in d["sections"]] == ["반품 규정", "기간", "1. Scope"]
    assert d["sections"][0]["text"] == "First body line."
    assert d["sections"][2]["text"] == "Own style text"


def test_a_doc_reads_a_paragraph_across_pieces_of_both_widths():
    d = ingest(_word(["Mixed ", "한글 ", "end\r"], [(0, b"")]), "a.doc").documents[0]
    assert d["text"] == "Mixed 한글 end"


def test_a_doc_finds_a_heading_past_characters_of_two_units():
    # a pair of surrogates is one character in Python and two in the file, and styles are found by file position
    # one piece, or the count starts afresh; enough of them to reach back past the heading's own paragraph
    d = ingest(_word(["😀😀😀😀😀 앞줄\r제목\r본문\r"], [(0, b""), (1, b""), (0, b"")]), "a.doc").documents[0]
    assert [s["title"] for s in d["sections"]] == ["", "제목"]


def test_a_doc_keeps_a_table_as_rows():
    cells = [(0, IN_TABLE)] * 2 + [(0, IN_TABLE + ROW_END)]
    d = ingest(_word(["Before\r", "A\x07B\x07\x07", "줄 하나\r둘\x07\x07\x07", "After\r"],
                     [(0, b""), *cells, (0, IN_TABLE), *cells, (0, b"")]), "a.doc").documents[0]
    assert d["text"].split("\n") == ["Before", "A | B", "줄 하나 둘 |", "After"]


def test_a_doc_shows_what_a_field_shows_and_not_its_instruction():
    link = '\x13 HYPERLINK "http://example.org" \x14Our site\x15'
    nested = "\x13 IF \x13 MERGEFIELD a \x14x\x15 = 1 \x14shown\x15"
    d = ingest(_word([f"See {link} and {nested}.\r"], [(0, b"")]), "a.doc").documents[0]
    assert d["text"] == "See Our site and shown."


def test_a_doc_drops_what_is_not_text():
    d = ingest(_word(["a\x01b\x0bc\x1ed\x1fe\tf\r"], [(0, b"")]), "a.doc").documents[0]
    assert d["text"] == "ab\nc-de\tf"


def test_a_doc_reads_the_table_stream_its_header_names():
    assert ingest(_word(["Text\r"], [(0, b"")], flags=0, stream="0Table"), "a.doc").documents
    assert _reason(_word(["Text\r"], [(0, b"")], flags=0), "a.doc") == "format"  # says 0Table, holds 1Table


@pytest.mark.parametrize("flags", [0x0200 | 0x0100, 0x0200 | 0x0100 | 0x8000])
def test_a_doc_with_a_password_is_refused_with_what_to_do(flags):
    with pytest.raises(IngestError, match="password") as e:
        ingest(_word(["Secret\r"], [(0, b"")], flags=flags), "a.doc")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "DOCX"


def test_a_doc_from_word_95_says_what_to_export_to():
    with pytest.raises(IngestError) as e:
        ingest(_word(["Old\r"], [(0, b"")], ident=0xA5DC), "a.doc")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "DOCX"


def test_a_malformed_doc_ends_in_an_answer():
    assert _reason(_word(["Text\r"], [(0, b"")], cps=[5, 0]), "a.doc") == "format"
    assert _reason(_word(["Text\r"], [(0, b"")], text_length=(1 << 26) + 1), "a.doc") == "too_large"
    assert _reason(_word(["Text\r"], [(0, b"")], text_length=0), "a.doc") == "empty"
    assert _reason(_ole({"WordDocument": b"\xec\xa5"}), "a.doc") == "format"


def test_pieces_cannot_give_more_text_than_the_file_says_it_has():
    # one long piece named a thousand times, in a text said to be one short line
    data = _word(["x" * 4000 + "\r"], [(0, b"")], again=1000, text_length=10)
    assert ingest(data, "a.doc").documents[0]["text"] == "x" * 10


def test_fields_that_never_close_stay_linear():
    start = time.perf_counter()
    assert _reason(_word(["\x13" * 600_000 + "\r"], [(0, b"")]), "a.doc") == "empty"
    assert time.perf_counter() - start < 10


def test_paragraph_properties_made_to_be_slow_end():
    # two paragraphs with long lists of properties, taken in turn four hundred thousand times over
    long = b"\x00\x24\x00" * 70
    data = _word(["x\r", "y\r"], [(0, long), (0, long)], again=200_000)
    start = time.perf_counter()
    assert _reason(data, "a.doc") == "format"
    assert time.perf_counter() - start < 5


def _rec(kind: int, body: bytes = b"", *, instance: int = 0) -> bytes:
    return struct.pack("<HHI", instance << 4, kind, len(body)) + body


def _box(kind: int, *children: bytes, instance: int = 0) -> bytes:
    body = b"".join(children)
    return struct.pack("<HHI", 0xF | instance << 4, kind, len(body)) + body


def _atoms(text: str, text_type: int) -> bytes:
    atom = (_rec(0x0FA8, text.encode("latin-1")) if text.isascii() else _rec(0x0FA0, text.encode("utf-16-le")))
    return _rec(0x0F9F, struct.pack("<I", text_type)) + atom


def _shape(text: str, text_type: int = 4) -> bytes:
    """A shape's text, as deep in a slide's drawing as PowerPoint keeps it."""
    return _box(0xF004, _box(0xF00D, _atoms(text, text_type)))


def _slide_record(*shapes: bytes) -> bytes:
    return _box(0x03EE, _box(0x040C, _box(0xF002, _box(0xF003, *shapes))))


def _persist(places: dict[int, int]) -> bytes:
    return _rec(0x1772, b"".join(struct.pack("<II", 1 << 20 | k, v) for k, v in places.items()))


def _edit(last: int, directory: int, document: int = 1) -> bytes:
    return _rec(0x0FF5, struct.pack("<IHBBIIII", 0, 0, 0, 3, last, directory, document, 0) + b"\0" * 4)


def _ppt_file(raw: bytes, edit: int, *, token: int = 0xE391C05F, extra: dict | None = None) -> bytes:
    user = _rec(0x0FF6, struct.pack("<IIIHH", 0x14, token, edit, 0, 0x03F4) + b"\0" * 12)
    return _ole({"PowerPoint Document": raw, "Current User": user, **(extra or {})})


def _deck(slides: list[tuple[list[bytes], bytes]], **kw) -> bytes:
    """A deck of (what the slide list holds, the slide's own shapes): a slide id starts at 2, the document is 1."""
    raw = b""
    places = {}
    for i, (_, shapes) in enumerate(slides):
        places[2 + i] = len(raw)
        raw += _slide_record(shapes)
    listed = b"".join(_rec(0x03F3, struct.pack("<IIIII", 2 + i, 0, 0, 0, 0)) + b"".join(texts)
                      for i, (texts, _) in enumerate(slides))
    places[1] = len(raw)
    raw += _box(0x03E8, _box(0x0FF0, _rec(0x03F3, b"\0" * 20), _atoms("마스터 글자", 0), instance=1),
                _box(0x0FF0, listed), _box(0x0FF0, _rec(0x03F3, b"\0" * 20), _atoms("발표자 노트", 2), instance=2))
    directory = len(raw)
    raw += _persist(places)
    edit = len(raw)
    return _ppt_file(raw + _edit(0, directory), edit, **kw)


def test_a_ppt_gives_a_section_to_a_slide_in_its_order():
    d = ingest(_deck([([_atoms("첫 화면", 0), _atoms("첫줄\r둘째\x0bsame paragraph", 1)], _shape("글상자")),
                      ([_atoms("Ascii title", 6)], b""),
                      ([], _shape("목록만 있는 화면"))]), "화면.ppt").documents[0]
    assert d["name"] == "화면" and d["kind"] == "screen"
    assert [s["title"] for s in d["sections"]] == ["첫 화면", "Ascii title", "Slide 3"]
    assert d["sections"][0]["text"].split("\n") == ["첫줄", "둘째", "same paragraph", "글상자"]
    assert d["sections"][2]["text"] == "목록만 있는 화면"


def test_a_ppt_leaves_out_masters_notes_and_slides_with_nothing_on_them():
    d = ingest(_deck([([_atoms("제목", 0)], b""), ([], b"")]), "a.ppt").documents[0]
    assert len(d["sections"]) == 1 and "마스터" not in d["text"] and "노트" not in d["text"]


def test_a_ppt_finds_a_title_in_a_shape_as_it_does_in_the_slide_list():
    d = ingest(_deck([([], _shape("도형 제목", 0) + _shape("도형 본문"))]), "a.ppt").documents[0]
    assert d["sections"] == [{"title": "도형 제목", "text": "도형 본문"}]


def test_a_ppt_says_a_line_once_when_a_writer_keeps_it_in_both_places():
    d = ingest(_deck([([_atoms("제목", 0), _atoms("본문", 1)], _shape("제목", 0) + _shape("본문"))]), "a.ppt").documents[0]
    assert d["sections"] == [{"title": "제목", "text": "본문"}]


def test_a_ppt_shows_the_newest_edit_and_not_what_it_replaced():
    # a fast save appends: the older slide is still in the stream, and only the edit chain says it is gone
    old = _slide_record(_shape("지난 판"))
    doc_at = len(old)
    doc = _box(0x03E8, _box(0x0FF0, _rec(0x03F3, struct.pack("<IIIII", 2, 0, 0, 0, 0))))
    first_dir = doc_at + len(doc)
    raw = old + doc + _persist({1: doc_at, 2: 0})
    first_edit = len(raw)
    raw += _edit(0, first_dir)
    new_at = len(raw)
    raw += _slide_record(_shape("새 판"))
    second_dir = len(raw)
    raw += _persist({2: new_at})
    second_edit = len(raw)
    raw += _edit(first_edit, second_dir)
    d = ingest(_ppt_file(raw, second_edit), "a.ppt").documents[0]
    assert "새 판" in d["text"] and "지난" not in d["text"]


@pytest.mark.parametrize("kw", [{"token": 0xF3D1C4DF}, {"extra": {"EncryptedSummary": b"\0" * 64}}])
def test_a_ppt_with_a_password_is_refused_with_what_to_do(kw):
    with pytest.raises(IngestError, match="password") as e:
        ingest(_deck([([_atoms("제목", 0)], b"")], **kw), "a.ppt")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "PPTX"


def test_a_ppt_from_before_97_says_what_to_export_to():
    data = _ole({"PowerPoint Document": b"\0" * 64, "Current User": b"\0" * 8})
    assert _reason(data, "a.ppt") == "export_needed"


def test_a_malformed_ppt_ends_in_an_answer():
    assert _reason(_ppt_file(b"\0" * 64, 0), "a.ppt") == "format"  # no edit at all
    assert _reason(_ppt_file(_rec(0x1234, _rec(0x1234, b"\0" * 64)), 8), "a.ppt") == "format"  # lands on something else
    loop = _persist({1: 0})  # an edit that follows itself, and a document that is no document
    assert _reason(_ppt_file(loop + _edit(len(loop), 0), len(loop)), "a.ppt") == "format"


def test_slides_that_all_point_at_one_long_record_end():
    many = b"".join(_rec(0x0FA8, b"x") for _ in range(20_000))
    slide = _box(0x03EE, many)
    ids = {2 + i: 0 for i in range(3000)}
    listed = b"".join(_rec(0x03F3, struct.pack("<IIIII", k, 0, 0, 0, 0)) for k in ids)
    doc = _box(0x03E8, _box(0x0FF0, listed))
    directory = len(slide) + len(doc)
    raw = slide + doc + _persist({1: len(slide), **ids})
    start = time.perf_counter()
    assert _reason(_ppt_file(raw + _edit(0, directory), len(raw)), "a.ppt") == "format"
    assert time.perf_counter() - start < 5


def test_one_long_text_named_by_many_slides_is_not_read_again_and_again():
    slide = _box(0x03EE, _rec(0x0FA8, b"x" * 200_000))
    ids = {2 + i: 0 for i in range(300)}
    doc = _box(0x03E8, _box(0x0FF0, b"".join(_rec(0x03F3, struct.pack("<IIIII", k, 0, 0, 0, 0)) for k in ids)))
    directory = len(slide) + len(doc)
    raw = slide + doc + _persist({1: len(slide), **ids})
    assert _reason(_ppt_file(raw + _edit(0, directory), len(raw)), "a.ppt") == "format"


def _biff(rid: int, body: bytes = b"") -> bytes:
    return struct.pack("<HH", rid, len(body)) + body


def _bof(kind: int, version: int = 0x0600) -> bytes:
    return _biff(0x0809, struct.pack("<HHHHII", version, kind, 0, 0, 0, 0))


def _label(text: str, length: int = 2) -> bytes:
    return len(text).to_bytes(length, "little") + b"\x01" + text.encode("utf-16-le")


def _strings(items: list[str]) -> bytes:
    return struct.pack("<II", len(items), len(items)) + b"".join(_label(x) for x in items)


def _number(r: int, c: int, v: float, xf: int = 0) -> bytes:
    return _biff(0x0203, struct.pack("<HHHd", r, c, xf, v))


def _shared(r: int, c: int, i: int) -> bytes:
    return _biff(0x00FD, struct.pack("<HHHI", r, c, 0, i))


def _workbook(sheets: dict[str, bytes], *, head: bytes = b"", sst: bytes = b"", version: int = 0x0600,
          stream: str = "Workbook", kinds: dict[str, int] | None = None) -> bytes:
    """A workbook of sheets given as their cell records; `head` goes into the globals, before the sheet list."""
    def globals_(places: list[int]) -> bytes:
        bound = b"".join(_biff(0x0085, struct.pack("<IBB", at, 0, (kinds or {}).get(n, 0)) + _label(n, 1))
                         for n, at in zip(sheets, places))
        return _bof(5, version) + head + bound + sst + _biff(0x000A)

    size = len(globals_([0] * len(sheets)))
    places, body = [], b""
    for cells in sheets.values():
        places.append(size + len(body))
        body += _bof(0x10, version) + cells + _biff(0x000A)
    return _ole({stream: globals_(places) + body})


def _table_of(rows: list[list]) -> tuple[bytes, bytes]:
    """The cell records of rows and the shared strings they use."""
    strings: list[str] = []
    cells = b""
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if isinstance(v, str):
                strings.append(v)
                cells += _shared(r, c, len(strings) - 1)
            elif v is not None:
                cells += _number(r, c, v)
    return cells, _biff(0x00FC, _strings(strings))


DEFINITION_ROWS = [["테이블 정의서"], ["테이블명", "테이블한글명", "컬럼명", "컬럼한글명", "데이터타입", "길이", "PK"],
                   ["TB_ORDER", "주문", "ORDER_NO", "주문번호", "VARCHAR", 20, "Y"],
                   ["TB_ORDER", "주문", "AMOUNT", "금액", "NUMBER", 12, None]]
CODE_ROWS = [["코드그룹", "코드그룹명", "코드", "코드명", "사용여부"], ["OD01", "주문상태", "10", "접수", "Y"], ["OD01", "주문상태", "20", "완료", "N"]]
DATA_ROWS = [["id", "이름", "금액"], [1, "회원", 1000.5], [2, "손님", 3]]


def _two_sheets(first: list[list], second: list[list]) -> bytes:
    a, _ = _table_of(first)
    strings = [v for row in first + second for v in row if isinstance(v, str)]
    cells, n = b"", len([v for row in first for v in row if isinstance(v, str)])
    for r, row in enumerate(second):
        for c, v in enumerate(row):
            if isinstance(v, str):
                cells += _shared(r, c, n)
                n += 1
            elif v is not None:
                cells += _number(r, c, v)
    return _workbook({"정의서": a, "코드": cells}, sst=_biff(0x00FC, _strings(strings)))


def test_a_definition_workbook_reads_as_its_xlsx_does():
    d = ingest(_two_sheets(DEFINITION_ROWS, CODE_ROWS), "정의.xls")
    assert list(d.tables) == ["TB_ORDER"] and d.tables["TB_ORDER"].primary_key == ["ORDER_NO"]
    assert d.tables["TB_ORDER"].label == "주문" and d.tables["TB_ORDER"].columns[0].length == 20
    assert [v["code"] for v in d.codes["OD01"].values] == ["10", "20"] and d.sources == ["정의.xls"]


def test_xls_and_xlsx_give_the_same_definitions_and_the_same_rows():
    pytest.importorskip("openpyxl")
    from datetime import datetime

    from openpyxl import Workbook

    from xgen_space.draft import read_file

    wb = Workbook()
    wb.active.title = "정의서"
    codes = wb.create_sheet("코드")
    for row in DEFINITION_ROWS:
        wb.active.append(row)
    for row in CODE_ROWS:
        codes.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    ours = ingest(_two_sheets(DEFINITION_ROWS, CODE_ROWS), "a.xls")
    assert ours.to_dict() == ingest(buf.getvalue(), "a.xlsx").to_dict()

    wb = Workbook()
    ws = wb.active
    ws.append(["id", "이름", "가입일"])
    ws.append([1, "회원", datetime(2024, 3, 1)])
    ws.append([2.5, None, datetime(2024, 3, 1, 13, 5, 7)])
    buf = io.BytesIO()
    wb.save(buf)
    cells, sst = _table_of([["id", "이름", "가입일"], [1, "회원", None], [2.5, None, None]])
    cells += _number(1, 2, 45352, xf=1) + _number(2, 2, 45352 + (13 * 3600 + 5 * 60 + 7) / 86400, xf=1)
    formats = _biff(0x00E0, b"\0" * 20) + _biff(0x00E0, struct.pack("<HH", 0, 14) + b"\0" * 16)
    data = _workbook({"Sheet": cells}, head=formats, sst=sst)
    ours, theirs = ingest_module.read_xls(data, "a.xls")[0], read_file(buf.getvalue(), "a.xlsx")[0]
    assert (ours.name, ours.columns, ours.rows) == (theirs.name, theirs.columns, theirs.rows)


def test_a_data_sheet_gives_its_rows_and_comes_in_as_text_as_in_a_newer_workbook():
    cells, sst = _table_of(DATA_ROWS)
    doc = ingest(_workbook({"Sheet1": cells}, sst=sst), "회원.xls").documents[0]
    assert doc["name"] == "회원" and doc["kind"] == "other" and "회원 | 1000.5" in doc["text"]
    t = ingest_module.read_xls(_workbook({"Sheet1": cells}, sst=sst), "회원.xls")[0]
    assert t.name == "회원" and t.columns == ["id", "이름", "금액"]
    assert t.rows == [["1", "회원", "1000.5"], ["2", "손님", "3"]]


def test_a_workbook_of_several_sheets_is_named_by_them_and_leaves_out_what_has_no_rows():
    cells, sst = _table_of(DATA_ROWS)
    out = ingest_module.read_xls(_workbook({"일반": cells, "빈 시트": b"", "차트": b"", "끝": cells}, sst=sst,
                                       kinds={"차트": 2}), "a.xls")
    assert [t.name for t in out] == ["일반", "끝"] and out[0].source == "a.xls · 일반"


def test_a_chart_sheet_is_no_sheet_of_the_workbook():
    cells, sst = _table_of(DATA_ROWS)
    data = _workbook({"데이터": cells, "차트": _number(0, 0, 1)}, sst=sst, kinds={"차트": 2})
    assert [t.name for t in ingest_module.read_xls(data, "회원.xls")] == ["회원"]  # one worksheet, named after the file


def _rk_int(v: int, hundredths: bool = False) -> int:
    return (v << 2 & 0xFFFFFFFF) | 2 | int(hundredths)


def _rk_double(v: float, hundredths: bool = False) -> int:
    return struct.unpack("<II", struct.pack("<d", v))[1] & 0xFFFFFFFC | int(hundredths)


def test_every_kind_of_cell_a_workbook_holds():
    rks = b"".join(struct.pack("<HI", 0, rk) for rk in (_rk_int(7), _rk_int(150, True)))
    multi = struct.pack("<HH", 2, 1) + rks + b"\x02\0"
    cells = b"".join([
        _biff(0x0204, struct.pack("<HHH", 0, 0, 0) + _label("a")),
        _biff(0x0204, struct.pack("<HHH", 0, 1, 0) + b"\x02\0\0bc"),
        _biff(0x00D6, struct.pack("<HHH", 0, 2, 0) + _label("한") + b"\0\0"),
        _biff(0x00FD, struct.pack("<HHHI", 0, 3, 0, 0)),
        _biff(0x027E, struct.pack("<HHHI", 1, 0, 0, _rk_int(-5))),
        _biff(0x027E, struct.pack("<HHHI", 1, 1, 0, _rk_double(2.5))),
        _biff(0x027E, struct.pack("<HHHI", 1, 2, 0, _rk_int(1234, True))),
        _biff(0x027E, struct.pack("<HHHI", 1, 3, 0, _rk_double(1000.0, True))),
        _biff(0x00BD, multi),
        _number(2, 3, 0.25),
        _biff(0x0205, struct.pack("<HHHBB", 2, 0, 0, 1, 0)),  # a boolean
        _biff(0x0205, struct.pack("<HHHBB", 3, 0, 0, 7, 1)),  # an error value stays blank
        _biff(0x0006, struct.pack("<HHH", 3, 1, 0) + struct.pack("<d", 42) + b"\0" * 8),
        _biff(0x0006, struct.pack("<HHH", 3, 2, 0) + b"\0\0\0\0\0\0\xff\xff" + b"\0" * 8),
        _biff(0x0207, _label("결과")),
        _biff(0x0006, struct.pack("<HHH", 3, 3, 0) + b"\x01\0\x01\0\0\0\xff\xff" + b"\0" * 8),
    ])
    t = ingest_module.read_xls(_workbook({"s": cells}, sst=_biff(0x00FC, _strings(["공유"]))), "a.xls")[0]
    assert t.columns == ["a", "bc", "한", "공유"]
    assert t.rows == [["-5", "2.5", "12.34", "10"], ["true", "7", "1.5", "0.25"], [None, "42", "결과", "true"]]


def test_a_chart_inside_a_sheet_gives_no_cells():
    chart = _bof(0x20) + _number(5, 0, 99) + _biff(0x000A)
    cells, sst = _table_of(DATA_ROWS)
    assert len(ingest_module.read_xls(_workbook({"s": cells + chart + _number(3, 0, 3)}, sst=sst), "a.xls")[0].rows) == 3


@pytest.mark.parametrize("formats,xf,serial,epoch,text", [
    (b"", 14, 45352, b"", "2024-03-01"),
    (b"", 22, 45352.5, b"", "2024-03-01T12:00:00"),
    (b"", 20, 0.5, b"", "12:00:00"),
    (b"", 14, 44, b"", "1900-02-13"),  # before the leap day Excel takes 1900 to have
    (b"", 14, 43890, b"\x01\0", "2024-03-01"),  # counted from 1904
    (_biff(0x041E, struct.pack("<H", 164) + _label('yyyy"년" mm"월"')), 164, 45352, b"", "2024-03-01"),
    (_biff(0x041E, struct.pack("<H", 165) + _label('#,##0"일"')), 165, 45352, b"", "45352"),  # a word in quotes is no date
    (_biff(0x041E, struct.pack("<H", 166) + _label(r"0.0\d;[Red]0.0")), 166, 1.5, b"", "1.5"),
    (b"", 14, 1e300, b"", str(int(1e300))),  # no calendar holds it
])
def test_a_number_is_a_date_when_its_format_says_so(formats, xf, serial, epoch, text):
    head = formats + _biff(0x00E0, struct.pack("<HH", 0, xf) + b"\0" * 16) + (_biff(0x0022, epoch) if epoch else b"")
    t = ingest_module.read_xls(_workbook({"s": _shared(0, 0, 0) + _number(1, 0, serial)}, head=head,
                                     sst=_biff(0x00FC, _strings(["h"]))), "a.xls")[0]
    assert t.rows == [[text]]


def _columns(cells: bytes, sst: bytes) -> list[str]:
    return ingest_module.read_xls(_workbook({"s": cells}, sst=sst), "a.xls")[0].columns


def test_shared_strings_run_on_across_records_and_change_width_there():
    three = _shared(0, 0, 0) + _shared(0, 1, 1) + _shared(0, 2, 2)
    head = struct.pack("<II", 3, 3)
    wide = struct.pack("<HB", 6, 1) + "가나다".encode("utf-16-le")
    rest = "라마바".encode("utf-16-le")
    after = struct.pack("<HB", 4, 0) + b"abcd"
    last = struct.pack("<HB", 1, 0) + b"z"
    sst = _biff(0x00FC, head + wide) + _biff(0x003C, b"\x01" + rest + after[:1]) + _biff(0x003C, after[1:] + last)
    assert _columns(three, sst) == ["가나다라마바", "abcd", "z"]
    sst = _biff(0x00FC, head + wide) + _biff(0x003C, b"\x00def" + after + last)  # the rest fits one byte a character
    assert _columns(three, sst) == ["가나다def", "abcd", "z"]
    narrow = struct.pack("<II", 1, 1) + struct.pack("<HB", 4, 0) + b"ab"
    sst = _biff(0x00FC, narrow) + _biff(0x003C, b"\x01" + "한글".encode("utf-16-le"))
    assert _columns(_shared(0, 0, 0), sst) == ["ab한글"]


def test_a_string_that_starts_a_record_needs_no_flag_and_one_cut_at_its_start_does():
    first = struct.pack("<II", 2, 2) + struct.pack("<HB", 1, 0) + b"a"
    second = struct.pack("<HB", 1, 0) + b"b"
    two = _shared(0, 0, 0) + _shared(0, 1, 1)
    assert _columns(two, _biff(0x00FC, first) + _biff(0x003C, second)) == ["a", "b"]
    sst = _biff(0x00FC, first + second[:3]) + _biff(0x003C, b"\x00" + second[3:])  # the head ends the record
    assert _columns(two, sst) == ["a", "b"]


def test_shared_strings_skip_their_rich_text_and_phonetic_parts():
    rich = struct.pack("<HBH", 2, 8, 2) + b"ab" + b"\xee" * 8
    phonetic = struct.pack("<HBi", 2, 4, 6) + b"cd" + b"\xee" * 6
    both = struct.pack("<HBHi", 2, 12, 1, 3) + b"ef" + b"\xee" * 4 + b"\xee" * 3
    sst = _biff(0x00FC, struct.pack("<II", 3, 3) + rich + phonetic + both)
    assert _columns(_shared(0, 0, 0) + _shared(0, 1, 1) + _shared(0, 2, 2), sst) == ["ab", "cd", "ef"]


def test_a_workbook_with_a_password_is_refused_with_what_to_do():
    cells, sst = _table_of(DATA_ROWS)
    with pytest.raises(IngestError, match="password") as e:
        ingest(_workbook({"s": cells}, head=_biff(0x002F, b"\x01\0" + b"\0" * 52), sst=sst), "a.xls")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "XLSX"


@pytest.mark.parametrize("kw", [{"version": 0x0500}, {"stream": "Book"}])
def test_a_workbook_from_excel_95_says_what_to_export_to(kw):
    cells, sst = _table_of(DATA_ROWS)
    with pytest.raises(IngestError) as e:
        ingest(_workbook({"s": cells}, sst=sst, **kw), "a.xls")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "XLSX"


def test_a_malformed_workbook_ends_in_an_answer():
    assert _reason(_ole({"Workbook": b"\x09\x08"}), "a.xls") == "export_needed"  # not even a whole record
    assert _reason(_workbook({}), "a.xls") == "empty"
    assert _reason(_workbook({"s": b""}), "a.xls") == "empty"
    assert _reason(_workbook({"s": _biff(0x0203, b"\0\0")}), "a.xls") == "format"  # a cell cut short
    past = _workbook({"s": _shared(0, 0, 9) + _number(0, 1, 1)}, sst=_biff(0x00FC, _strings(["a"])))
    assert ingest_module.read_xls(past, "a.xls")[0].columns == ["column1", "1"]  # a string past the end is a blank


def test_shared_strings_that_lie_about_their_number_and_length_end():
    sst = _biff(0x00FC, struct.pack("<II", 0xFFFFFFFF, 0xFFFFFFFF) + struct.pack("<HB", 0xFFFF, 1) + b"ab")
    assert _columns(_shared(0, 0, 0), sst) == ["扡"]


def test_a_cell_past_the_last_column_spreads_nothing():
    cells, sst = _table_of(DATA_ROWS)
    t = ingest_module.read_xls(_workbook({"s": cells + _number(0, 60000, 1)}, sst=sst), "a.xls")[0]
    assert len(t.columns) == 3


def test_a_workbook_that_spreads_past_the_limit_is_refused(monkeypatch):
    monkeypatch.setattr(ingest_module, "_XLS_CELLS", 1000)
    far = b"".join(_number(r, 200, 1) for r in range(20))  # twenty cells, four thousand places
    assert _reason(_workbook({"s": far}), "a.xls") == "too_large"
    again = _number(0, 0, 1) * 2000  # counted as they are read, so memory is held before anything is laid out
    assert _reason(_workbook({"s": again}), "a.xls") == "too_large"


def test_old_office_files_are_known_by_what_they_hold():
    cells, sst = _table_of(DATA_ROWS)
    assert ingest(_word(["본문\r"], [(0, b"")]), "export.dat").documents
    assert ingest(_deck([([_atoms("제목", 0)], b"")]), "a.pot").documents[0]["kind"] == "screen"
    assert ingest(_workbook({"s": cells}, sst=sst), "a.xlt").documents
    assert ingest(_workbook({"s": cells}, sst=sst), "wrong.doc").documents[0]["name"] == "wrong"
    assert "본문" in ingest(_hwp_file(["본문입니다."]), "export.dat").documents[0]["text"]


def test_a_newer_file_or_a_web_page_saved_under_the_old_name_still_reads():
    assert ingest(_zip(DOCX), "a.doc").documents
    assert ingest(b"<html><body><p>hello</p></body></html>", "a.xls").documents
    assert ingest(b"a\tb\n1\t2\n3\t4\n", "a.xls").documents


def test_a_compound_file_of_nothing_known_says_what_to_export_to():
    assert _reason(_ole({"Contents": b"\0" * 64}), "a.doc") == "export_needed"
    assert _reason(_ole({"Contents": b"\0" * 64}), "a.dat") == "export_needed"


def test_a_newer_file_with_a_password_says_so():
    with pytest.raises(IngestError, match="password") as e:
        ingest(_ole({"EncryptionInfo": b"\0" * 64, "EncryptedPackage": b"\0" * 64}), "a.xls")
    assert e.value.reason == "export_needed" and e.value.info["export_to"] == "XLSX"


def test_stream_names_may_be_in_another_case():
    cells, sst = _table_of(DATA_ROWS)
    assert ingest(_workbook({"s": cells}, sst=sst, stream="WORKBOOK"), "a.xls").documents


def test_the_high_half_of_a_stream_size_is_ignored_in_a_small_sector_file():
    raw = bytearray(_ole({"Workbook": b"\0" * 64}))
    at = 512 * 2 + 128 + 124  # the second directory entry's size, its high half
    raw[at:at + 4] = b"\xff\xff\xff\xff"
    assert _reason(bytes(raw), "a.xls") == "export_needed"  # read as 64 bytes, not as far past the limit


def test_a_sector_list_that_runs_in_a_circle_ends_quickly():
    # each list sector names sector 1 for a FAT 127 times and itself as next: a megabyte would build a billion entries
    size = 1 << 20
    data = bytearray(size)
    data[:8] = MAGIC
    struct.pack_into("<HH", data, 30, 9, 6)
    struct.pack_into("<II", data, 44, 109, 0)
    struct.pack_into("<IIIII", data, 56, 4096, END, 0, 1, size // 512)
    struct.pack_into("<109I", data, 76, *[1] * 109)
    struct.pack_into("<128I", data, 1024, *[1] * 127, 1)
    start = time.perf_counter()
    assert _reason(bytes(data), "a.doc") == "export_needed"
    assert time.perf_counter() - start < 5


def test_a_sector_of_a_size_no_compound_file_has_builds_no_fat():
    # with sectors as long as the file, the header's 109 places would make a FAT of many times the file
    size = 1 << 18
    data = bytearray(size)
    data[:8] = MAGIC
    struct.pack_into("<HH", data, 30, 16, 6)
    struct.pack_into("<II", data, 44, 109, 0)
    struct.pack_into("<IIIII", data, 56, 4096, END, 0, END, 0)
    struct.pack_into("<109I", data, 76, *[0] * 109)
    data[1 << 16:] = b"\x01\x02\x03\x04" * ((size - (1 << 16)) // 4)
    tracemalloc.start()
    try:
        assert _reason(bytes(data), "a.doc") == "export_needed"
        assert tracemalloc.get_traced_memory()[1] < 4 * size
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize("at,shift", [(30, 7), (32, 3)])
def test_a_size_no_compound_file_has_is_refused(at, shift):
    data = bytearray(_ole({"Workbook": b"\0" * 64}))
    struct.pack_into("<H", data, at, shift)
    assert _reason(bytes(data), "a.xls") == "export_needed"


def _mutations(data: bytes, seed: int, count: int) -> Iterator[bytes]:
    import random

    rnd = random.Random(seed)
    for _ in range(count):
        raw = bytearray(data)
        for _ in range(rnd.choice((1, 4, 32))):
            at = rnd.randrange(512, len(raw))
            raw[at] = rnd.choice((0, 1, 0x7F, 0xFF, rnd.randrange(256)))
        yield bytes(raw)


def _samples() -> list[tuple[str, bytes]]:
    cells, sst = _table_of(DEFINITION_ROWS)
    return [("a.doc", _word(["제목\r", "A\x07", "\x07", "\x13 F \x14x\x15\r"],
                            [(1, b""), (0, IN_TABLE), (0, IN_TABLE + ROW_END), (0, b"")])),
            ("a.ppt", _deck([([_atoms("제목", 0)], _shape("글상자"))])),
            ("a.xls", _workbook({"s": cells}, sst=sst))]


@pytest.mark.parametrize("source,data", _samples(), ids=lambda x: x if isinstance(x, str) else "")
def test_a_damaged_file_reads_or_ends_in_an_answer_and_never_in_anything_else(source, data):
    for raw in _mutations(data, 96, 400):
        try:
            assert isinstance(ingest(raw, source), Definitions)
        except IngestError:
            pass


def test_the_page_takes_an_old_workbook_of_definitions_and_says_what_a_password_needs(session):
    st = session.upload("정의.xls", _two_sheets(DEFINITION_ROWS, CODE_ROWS))
    assert st["files"] == [] and st["definitions"][0]["tables"][0]["key"] == ["ORDER_NO"]
    st = session.upload("규정.doc", _word(["본문입니다.\r"], [(0, b"")]))
    assert any(x["documents"] == 1 for x in st["definitions"])
    with pytest.raises(ValueError, match="암호를 해제하거나 PPTX 파일로 내보내"):
        session.upload("a.ppt", _deck([([_atoms("제목", 0)], b"")], token=0xF3D1C4DF))


# ---- the same table name in two schemas ----------------------------------------------------------------------

SCHEMAS = """
CREATE TABLE sales.customer (id INT PRIMARY KEY, name VARCHAR(50));
CREATE TABLE hr.customer (id INT PRIMARY KEY, dept VARCHAR(20), status VARCHAR(1) CHECK (status IN ('A','B')));
CREATE TABLE sales.orders (id INT PRIMARY KEY, customer_id INT REFERENCES customer(id), staff_id INT,
                           FOREIGN KEY (staff_id) REFERENCES hr.customer(id));
CREATE TABLE sales.note (id INT PRIMARY KEY, customer_id INT, order_id INT);
ALTER TABLE sales.note ADD CONSTRAINT fk1 FOREIGN KEY (customer_id) REFERENCES hr.customer (id);
ALTER TABLE sales.note ADD CONSTRAINT fk2 FOREIGN KEY (order_id) REFERENCES orders (id);
ALTER TABLE hr.customer ADD CONSTRAINT fk3 FOREIGN KEY (id) REFERENCES sales.customer (id);
COMMENT ON TABLE hr.customer IS 'staff';
COMMENT ON COLUMN sales.customer.name IS 'shopper name';
"""


def test_tables_of_one_name_in_two_schemas_are_both_kept():
    d = ingest(SCHEMAS.encode(), "two.sql")
    assert set(d.tables) == {"sales.customer", "hr.customer", "orders", "note"}
    assert [c.name for c in d.tables["sales.customer"].columns] == ["id", "name"]
    assert [c.name for c in d.tables["hr.customer"].columns] == ["id", "dept", "status"]
    assert d.tables["hr.customer"].label == "staff" and d.tables["sales.customer"].column("name").label == "shopper name"
    assert d.tables["hr.customer"].column("status").code == "hr.customer.status"


def test_a_reference_finds_the_table_of_its_schema_and_stays_plain_elsewhere():
    d = ingest(SCHEMAS.encode(), "two.sql")
    assert d.tables["orders"].references == [
        {"columns": ["customer_id"], "table": "sales.customer", "ref_columns": ["id"]},
        {"columns": ["staff_id"], "table": "hr.customer", "ref_columns": ["id"]}]
    assert [r["table"] for r in d.tables["note"].references] == ["hr.customer", "orders"]
    assert [r["table"] for r in d.tables["hr.customer"].references] == ["sales.customer"]
    assert d.tables["sales.customer"].references == []


def test_two_schemas_draft_as_two_objects():
    pytest.importorskip("yaml")
    d = ingest(SCHEMAS.encode(), "two.sql")
    dr = draft(schema_backend(d), name="shop", definitions=d)
    assert {"SalesCustomer", "HrCustomer"} <= {o.name for o in dr.objects}
    assert {(lk.source, lk.target) for lk in dr.links} >= {("Order", "SalesCustomer"), ("Order", "HrCustomer")}


def test_one_schema_keeps_plain_names_and_a_later_definition_still_wins():
    d = ingest(b"CREATE TABLE dbo.t (a INT);\nCREATE TABLE dbo.t (b INT);\n"
               b"CREATE TABLE dbo.u (c INT REFERENCES dbo.t(b));", "a.sql")
    assert set(d.tables) == {"t", "u"} and [c.name for c in d.tables["t"].columns] == ["b"]
    assert d.tables["u"].references == [{"columns": ["c"], "table": "t", "ref_columns": ["b"]}]


def test_schemas_that_differ_only_by_case_are_one_schema():
    d = ingest(b"CREATE TABLE App.t (a INT);\nCREATE TABLE app.t (b INT);", "a.sql")
    assert set(d.tables) == {"t"} and [c.name for c in d.tables["t"].columns] == ["b"]


def test_a_table_with_no_schema_and_its_namesake_in_one_are_both_kept():
    d = ingest(b"CREATE TABLE t (a INT);\nCREATE TABLE hr.t (b INT);\nCREATE TABLE u (c INT REFERENCES t(a));", "a.sql")
    assert set(d.tables) == {"t", "hr.t", "u"} and d.tables["u"].references[0]["table"] == "t"


def test_sql_server_comments_find_the_table_of_their_schema():
    d = ingest("""CREATE TABLE [sales].[t] (a INT);
CREATE TABLE [hr].[t] (b INT);
EXEC sp_addextendedproperty N'MS_Description', N'staff', N'SCHEMA', N'hr', N'TABLE', N't';
""".encode(), "a.sql")
    assert d.tables["hr.t"].label == "staff" and d.tables["sales.t"].label == ""
