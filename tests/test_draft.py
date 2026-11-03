import io

import pytest

from xgen_data_studio.backends.sql import SqliteBackend
from xgen_data_studio.draft import ReadError, draft, infer_type, load_sqlite, read_csv, read_file, romanize, studio_from
from xgen_data_studio.modules import compose

from .conftest import EXAMPLE

FILES = EXAMPLE.parent / "files"


def _files() -> list:
    tables = []
    for p in sorted(FILES.iterdir()):
        tables += read_file(p.read_bytes(), p.name)
    return tables


def test_a_database_with_primary_keys_and_no_foreign_keys_gets_the_relations_a_person_wrote(source):
    pytest.importorskip("rdflib")
    d = draft(source, name="shop")
    keys = {o.table: (o.key, o.key_why) for o in d.objects}
    assert keys["orders"] == ("order_id", "primary_key") and "wishlists" not in keys
    found = {(lk.source, lk.target, lk.cardinality) for lk in d.links}
    # the nine relations of the hand-written commerce ontology, found from names and values alone
    assert found == {("Order", "Customer", "many_to_one"), ("OrderItem", "Order", "many_to_one"),
                     ("OrderItem", "Skus", "many_to_one"), ("Skus", "Product", "many_to_one"),
                     ("Product", "Category", "many_to_one"), ("Category", "Category", "many_to_one"),
                     ("Claim", "OrderItem", "many_to_one"), ("Customer", "Product", "many_to_many"),
                     ("PriceChange", "Skus", "many_to_one")}
    wish = next(lk for lk in d.links if lk.via)
    assert wish.via == ("wishlists", "customer_id", "product_id")
    order = next(o for o in d.objects if o.name == "Order")
    assert order.prop_of("ordered_at").type == "datetime"  # SQLite keeps dates as ISO text
    assert compose(d.modules()).issues == []
    st = studio_from(d, source)
    assert st.check_bindings().ok and st.conformance().passed


def test_files_become_a_studio_that_answers_the_same_on_every_backend():
    pytest.importorskip("rdflib")
    b = SqliteBackend()
    loaded = load_sqlite(_files(), b)
    assert next(lo for lo in loaded if lo.table == "도서저자").row_key == "row_no"
    d = draft(b, name="my-data", label="내 데이터", loaded=loaded, lang="ko")
    objs = {o.table: o for o in d.objects}
    assert set(objs) == {"회원", "도서", "저자", "대출", "대출상태이력"}  # 도서저자 is the many-to-many of 도서 and 저자
    book = objs["도서"]
    assert book.name == "Doseo" and book.key == "doseobeonho" and book.title == "doseomyeong"
    assert book.prop_of("정가").type == "integer"  # "14,800"
    assert book.prop_of("출간일").type == "date"
    assert book.prop_of("분류").values == ["경제", "과학", "소설", "에세이", "역사"]
    assert objs["대출"].prop_of("대출일시").type == "datetime"
    assert {(lk.source, lk.target, lk.why) for lk in d.links} == {
        ("Daechul", "Hoewon", "values_included"), ("Daechul", "Doseo", "values_included"),
        ("Doseo", "Jeoja", "values_included"), ("Daechulsangtaeiryeok", "Daechul", "values_included")}
    assert [s["id"] for s in d.steps()] == ["read", "objects", "properties", "links", "queries", "rules", "bindings"]
    st = studio_from(d, b)
    assert st.check_bindings().ok
    rep = st.conformance()
    assert rep.passed and rep.summary()["queries"] == 12
    assert st.run("daechulPerHoewon").columns == ["hoewonbeonho", "ireum", "n"]


def test_the_review_leaves_out_and_renames():
    b = SqliteBackend()
    d = draft(b, loaded=load_sqlite(_files(), b), lang="ko")
    r = d.revise(drop=["object:Jeoja"], labels={"object:Daechul": "대출 기록"})
    assert {o.name for o in r.objects} == {"Daechul", "Doseo", "Hoewon", "Daechulsangtaeiryeok"}
    assert all("Jeoja" not in (lk.source, lk.target) for lk in r.links)
    assert next(o for o in r.objects if o.name == "Daechul").label == "대출 기록"
    assert r.queries()["daechulPerHoewon"]["label"] == "회원별 대출 기록 수"
    assert {o.name for o in d.objects} == {"Daechul", "Doseo", "Hoewon", "Jeoja", "Daechulsangtaeiryeok"}  # kept


def test_reading_files():
    t = read_csv("코드,금액,메모\n00123,\"1,200\",가\n00124,300,\n".encode("cp949"), "표.csv")
    assert t.name == "표" and t.columns == ["코드", "금액", "메모"] and t.rows[1] == ["00124", "300", None]
    assert infer_type(["00123", "00124"]) == "string" and infer_type(["1,200", "300"]) == "integer"
    assert infer_type(["2026-10-01 09:30", "2026/10/02"]) == "datetime"
    assert infer_type(["2026-02-30"]) == "string"
    t = read_csv(b"a;b\n1;2\n3;4\n", "x.csv", max_rows=1)
    assert t.columns == ["a", "b"] and t.truncated and len(t.rows) == 1
    with pytest.raises(ReadError):
        read_file(b"", "x.pdf")
    assert romanize("회원번호") == "hoewonbeonho"


def test_reading_a_workbook():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "members"
    ws.append(["member_id", "joined"])
    ws.append(["M1", 1.0])
    other = wb.create_sheet("empty")
    other.append([None])
    buf = io.BytesIO()
    wb.save(buf)
    tables = read_file(buf.getvalue(), "book.xlsx")
    assert [(t.name, t.rows) for t in tables] == [("members", [["M1", "1"]])]
    with pytest.raises(ReadError):
        read_file(b"not a zip", "x.xlsx")


def test_a_table_with_no_key_is_left_out_of_a_database_it_cannot_change():
    b = SqliteBackend()
    b.script("CREATE TABLE logs (msg TEXT, level TEXT); INSERT INTO logs VALUES ('a', 'x'), ('a', 'x');"
             "CREATE TABLE things (id INTEGER PRIMARY KEY, id_ref INTEGER);"
             "CREATE TABLE other (id INTEGER PRIMARY KEY); INSERT INTO other VALUES (1), (2);"
             "INSERT INTO things VALUES (1, 1), (2, 2);")
    d = draft(b)
    assert d.skipped == [{"table": "logs", "why": "no_key"}]
    assert not d.links  # 'id' is every table's key name, so the name alone does not make a relation


def test_the_command_writes_a_studio_folder_that_serves_as_it_is(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_data_studio.cli import main
    from xgen_data_studio.config import load_studio

    files = [str(p) for p in sorted(FILES.iterdir())]
    assert main(["draft", *files, "--name", "lib", "--drop", "object:Jeoja", "-o", str(tmp_path)]) == 0
    st = load_studio(tmp_path / "studio.yaml")
    assert set(st.onto.objects) == {"Daechul", "Doseo", "Hoewon", "Daechulsangtaeiryeok"} and st.conformance().passed
    with pytest.raises(SystemExit):
        main(["draft", *files, "-o", str(tmp_path)])  # an existing studio folder is not overwritten
    assert main(["draft", "--sqlite", str(tmp_path / "data.sqlite"), "--name", "again"]) == 0
    assert main(["draft", *files, "--rules", '{"infer_links": false}', "-o", str(tmp_path / "flat")]) == 0
    assert not load_studio(tmp_path / "flat" / "studio.yaml").onto.links


def test_the_rules_are_settings_a_person_can_change():
    from xgen_data_studio.draft import DraftRules

    def run(**rules):
        b = SqliteBackend()
        r = DraftRules.from_dict(rules)
        return draft(b, loaded=load_sqlite(_files(), b, row_keys=r.row_keys), lang="ko", rules=r)

    base = run()
    assert sum(p.type == "enum" for o in base.objects for p in o.properties) == 4
    assert not [p for o in run(enum_max=3).objects for p in o.properties if p.column == "분류" and p.type == "enum"]
    assert not run(infer_links=False).links
    flat = run(link_tables=False)
    assert "도서저자" in {o.table for o in flat.objects}  # numbered rows key it
    assert {s["table"] for s in run(link_tables=False, row_keys=False).skipped} == {"도서저자"}
    assert set(run(queries=["list"]).queries()) == {"listDaechul", "listDoseo", "listJeoja", "listHoewon",
                                                "listDaechulsangtaeiryeok"}
    assert DraftRules.from_dict({"title_hints": "nm, 이름"}).title_hints == ["nm", "이름"]


def test_every_step_takes_a_persons_edit():
    pytest.importorskip("rdflib")
    b = SqliteBackend()
    tables = _files()
    d = draft(b, loaded=load_sqlite(tables, b), lang="ko")
    r = d.revise(keys={"Hoewon": "ireum"}, types={"Doseo.chulganil": "string", "Hoewon.gaipil": "enum"},
                 values={"Hoewon.gaipil": ["2024-03-02"]}, drop=["property:Daechul.doseobeonho", "query:listJeoja"],
                 labels={"property:Doseo.jeongga": "판매가", "link:hoewon": "대출 회원"},
                 cardinality={"doseojeoja": "many_to_many"},
                 add_links=[{"source": "Daechul", "property": "hoewonbeonho", "target": "Hoewon", "label": "담당"}])
    objs = {o.name: o for o in r.objects}
    assert objs["Hoewon"].key == "ireum" and objs["Doseo"].prop_of("출간일").type == "string"
    assert objs["Hoewon"].prop_of("가입일").values == ["2024-03-02"]
    assert "doseobeonho" not in {p.name for p in objs["Daechul"].properties}
    assert "doseo" not in {lk.name for lk in r.links}  # it was joined on the property left out
    added = next(lk for lk in r.links if lk.why == "manual")
    assert added.on == ("hoewonbeonho", "ireum") and added.label == "담당"
    assert "listJeoja" not in r.queries() and "listJeoja" in r.queries(dropped=True)
    assert next(s for s in r.steps() if s["id"] == "queries")["items"]
    with pytest.raises(ValueError):
        d.revise(types={"Doseo.jeongga": "money"})
    with pytest.raises(ValueError):
        d.revise(keys={"Doseo": "nothing"})
    assert compose(d.revise(types={"Doseo.bunryu": "enum"}, values={"Doseo.bunryu": []}).modules()).issues


def test_a_type_chosen_by_a_person_is_how_the_values_are_stored():
    b = SqliteBackend()
    t = read_csv("code,flag\n001,Y\n002,N\n".encode(), "t.csv")
    load_sqlite([t], b, types={"t": {"code": "integer", "flag": "boolean"}})
    assert b.fetch("SELECT code, flag FROM t ORDER BY code") == [(1, 1), (2, 0)]
    with pytest.raises(ReadError) as e:
        load_sqlite([read_csv(b"code\nA1\n", "u.csv")], SqliteBackend(), types={"u": {"code": "integer"}})
    assert e.value.reason == "convert" and e.value.info["value"] == "A1"
