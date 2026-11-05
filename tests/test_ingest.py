"""Anything in, one JSON out: every format reads into the canonical object, and an upload cannot do harm on the way."""
import io
import json
import struct
import sys
import time
import zipfile

import pytest

from xgen_data_studio import ingest as ingest_module
from xgen_data_studio.cli import main
from xgen_data_studio.definitions import Definitions, from_sheets, schema_backend
from xgen_data_studio.draft import Table, draft
from xgen_data_studio.ingest import IngestError, adapter_paths, ingest, is_sheet, load_adapters, register

from .conftest import EXAMPLE

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
    with pytest.raises(IngestError, match="xgen-data-studio.pdf") as e:
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
from xgen_data_studio.definitions import Definitions, TableDef
from xgen_data_studio.ingest import register

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
    monkeypatch.setenv("XDS_ADAPTERS", str(f))
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


def test_xds_ingest_writes_one_json_and_counts_it(tmp_path, capsys):
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


def test_xds_ingest_takes_an_adapter_and_says_what_it_cannot_read(adapters, tmp_path, capsys):
    plugin, f = tmp_path / "foo_adapter.py", tmp_path / "x.foo"
    plugin.write_text(PLUGIN, encoding="utf-8")
    f.write_bytes(b"hello")
    assert main(["ingest", str(f), "--adapter", str(plugin)]) == 0
    assert json.loads(capsys.readouterr().out)["tables"][0]["label"] == "hello"
    blob = tmp_path / "x.hwp"
    blob.write_bytes(b"\xd0\xcf\x11\xe0\0\0")
    with pytest.raises(SystemExit, match="HWPX"):
        main(["ingest", str(blob)])


def test_xds_draft_takes_definitions_of_any_format(tmp_path, capsys):
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
    from xgen_data_studio.config import load_studio
    from xgen_data_studio.web.api import StudioSession

    return StudioSession(load_studio(EXAMPLE.parent / "library" / "studio.yaml"))


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
    from xgen_data_studio.definitions import schema_backend
    from xgen_data_studio.draft import draft, studio_from

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
