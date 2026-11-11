"""English names on a draft: the queries made from a renamed object keep their answers and what the review left out,
and a name two tables would share is offered to neither."""
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    s = StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))
    s.use_samples()
    s.make_draft("가상 쇼핑몰")
    return s


def test_renamed_objects_keep_their_queries_answers_and_drops(session):
    d0 = session.pending[0]
    names = {k: v["name"] for k, v in session._draft_view()["names"].items() if v["name"]}
    assert len(names) >= 2  # one object's name holds another's (주문, 주문상품), the case a text replace gets wrong
    renamed = session._edit(d0, {"names": names})
    assert len(renamed.questions()) == len(d0.questions()) > 0
    assert set(renamed.answers) <= set(renamed.queries())
    inner = next(o for o in d0.objects if any(p.name != o.name and o.name.startswith(p.name) for p in d0.objects))
    old = f"list{inner.name}"
    by_old = dict(zip(d0.queries(dropped=True), renamed.queries(dropped=True)))
    dropped = session._edit(d0, {"names": names, "drop": [f"query:{old}"]})
    assert by_old[old] not in dropped.queries() and dropped.no_queries == [by_old[old]]
    again = session._edit(d0, {"names": names, "drop": [f"query:{by_old[old]}"]})  # the page may send the new name
    assert again.no_queries == [by_old[old]]


def test_a_name_two_tables_would_share_is_offered_to_neither(tmp_path, session):
    from ontlas.config import open_backend
    from ontlas.draft import draft

    db = tmp_path / "shop.db"
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE "주문내역" ("내역번호" TEXT PRIMARY KEY, "금액" INTEGER)')
    con.execute('CREATE TABLE "주문상세" ("상세번호" TEXT PRIMARY KEY, "수량" INTEGER)')
    con.executemany('INSERT INTO "주문내역" VALUES (?,?)', [("A1", 10), ("A2", 20)])
    con.executemany('INSERT INTO "주문상세" VALUES (?,?)', [("B1", 1), ("B2", 2)])
    con.commit()
    con.close()
    d = draft(open_backend({"kind": "sqlite", "path": str(db)}, tmp_path), name="shop", label="가상", lang="ko")
    got = session._english(d)
    assert len(got) == 2 and all(v["name"] == "" for v in got.values())
    d.revise(names={k: v["name"] for k, v in got.items() if v["name"]})


def test_a_decision_is_drawn_from_history_on_a_draft_with_english_names():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.modules import compose
    from ontlas.web import DataOptions, StudioSession

    s = StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions())
    rows = ["사건번호,등급,구매금액,반품사유,처리결과"]
    for i in range(60):
        grade, amount = ["VIP", "일반"][i % 2], (i % 5) * 20000
        rows.append(f"R{i:03},{grade},{amount},{['변심', '불량'][i % 3 == 0]},{'승인' if grade == 'VIP' or amount >= 60000 else '반려'}")
    s.catalog_upload("반품기록.csv", ("\n".join(rows) + "\n").encode("utf-8"))
    s.make_draft("반품 판정")
    d0 = s.pending[0]
    names = {k: v["name"] for k, v in s._draft_view()["names"].items() if v["name"]}
    obj = d0.objects[0]
    assert obj.name in names  # 반품기록 reads as an English name, which the page sends with every edit
    col = {p.column: p.name for p in obj.properties}
    got = s.induce_decision(f"{obj.name}.{col['처리결과']}", [col["등급"], col["구매금액"], col["반품사유"]],
                            edits={"names": names})  # the target and inputs as the draft found them
    assert got["ok"], got.get("error")
    d = s._edit(d0, {"names": names})
    assert compose(d.modules(), name=d.name).ontology.decisions[got["name"]].target == names[obj.name]
