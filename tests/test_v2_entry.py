"""The screens outside an ontology: the ontologies there are to choose from with what each holds, one made from another,
and the person's list of what waits, what happened and what was settled."""
import json
from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.web import library_entry, routes
from ontlas.web.api import StudioSession
from ontlas.web.team import NEEDS

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"

FARM = {
    "library/farm/0.2.0.yaml": {
        "module": "farm", "version": "0.2.0", "kind": "domain", "label": "농장 표준", "description": "밭과 작물을 정의합니다",
        "namespace": "https://example.org/farm#",
        "areas": {"Field": {"label": "밭"}},
        "objects": {"Crop": {"label": "작물", "area": "Field", "key": "crop_id",
                             "properties": {"crop_id": {"type": "string"}, "name": {"type": "string", "label": "이름"}}},
                    "Plot": {"label": "구획", "area": "Field", "key": "plot_id", "properties": {"plot_id": {"type": "string"}}}},
    },
    "studio.yaml": {"library": "library", "name": "farm-studio", "label": "농장", "description": "농장 온톨로지",
                    "namespace": "https://example.org/farm#", "modules": ["farm"]},
}


def call(method: str, route: str):
    fn = routes.find(method, route)
    assert fn is not None, route
    return fn


@pytest.fixture()
def session(tmp_path):
    yaml = pytest.importorskip("yaml")
    routes.load()
    for name, body in FARM.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(body, allow_unicode=True, sort_keys=False), encoding="utf-8")
    first = load_studio(SHOP)
    s = StudioSession(first)
    farm = tmp_path / "studio.yaml"
    s.libraries = [library_entry("l1", SHOP, first), library_entry("l2", farm, load_studio(farm))]
    return s


def by_id(out: dict) -> dict:
    return {o["id"]: o for o in out["ontologies"]}


def test_every_ontology_is_listed_with_what_it_holds_and_how_far_it_has_come(session):
    out = call("GET", "entry/ontologies")(session, {}, None)
    json.dumps(out)  # what goes to the page is plain
    assert out["current"] == "l1" and out["made"] == 0 and out["made_max"] >= 1
    shop = by_id(out)["l1"]
    assert shop["current"] and shop["held"] and shop["source"] == "sqlite" and not shop["made"]
    assert shop["counts"]["objects"] == len(session.studio.onto.areas) and shop["counts"]["entities"] == len(session.studio.onto.objects)
    assert shop["version"] == "1.0.0" and shop["maturity"]["unit"] == "Object" and shop["maturity"]["all"] == shop["counts"]["objects"]
    on = {m["name"] for m in shop["modules"] if m["on"]}
    assert {"core", "commerce"} <= on and "food" not in on and "workspace" not in {m["name"] for m in shop["modules"]}
    assert next(m for m in shop["modules"] if m["name"] == "commerce")["requires"] == ["core"]
    assert next(m for m in shop["modules"] if m["name"] == "commerce")["counts"]["areas"] > 0


def test_an_ontology_not_opened_yet_is_read_from_its_files_without_opening_it(session):
    farm = by_id(call("GET", "entry/ontologies")(session, {}, None))["l2"]
    assert not farm["current"] and not farm["held"] and "l2" not in session._library_held
    assert farm["description"] == "농장 온톨로지" and farm["version"] == "0.2.0"
    assert farm["counts"]["objects"] == 1 and farm["counts"]["entities"] == 2
    # Crop has a property past its key, Plot has none: the Object is as far as its least defined Entity
    assert farm["maturity"] == {"low": 0, "at": 1, "done": 0, "all": 1, "unit": "Object", "full": False}
    assert [m["name"] for m in farm["modules"]] == ["farm"] and farm["modules"][0]["on"]
    assert session.library_id == "l1"


def test_an_ontology_whose_file_no_longer_reads_keeps_its_row(session):
    Path(session.libraries[1]["path"]).write_text("modules: [gone]\nlibrary: library\n", encoding="utf-8")
    farm = by_id(call("GET", "entry/ontologies")(session, {}, None))["l2"]
    assert farm["label"] == "농장 표준" and farm["counts"] is None and farm["modules"] == [] and farm["maturity"] is None


def test_an_ontology_is_made_from_the_modules_picked_of_another_ones_library(session):
    out = call("POST", "entry/ontology/new")(session, {"label": "의류 몰", "key": "apparel", "start": "pack", "base": "l1",
                                                       "modules": ["commerce", "fashion"], "description": "의류  고객사"}, None)
    assert out["id"] == "s1" and session.library_id == "s1"
    made = by_id(call("GET", "entry/ontologies")(session, {}, None))["s1"]
    assert made["made"] and made["current"] and made["base"] == session.libraries[0]["label"] and made["description"] == "의류 고객사"
    on = {m["name"] for m in made["modules"] if m["on"]}
    assert on == {"core", "commerce", "fashion"}  # what the picked ones stand on came along; the rest stayed out


def test_an_ontology_is_made_on_another_one_that_is_not_open(session):
    out = call("POST", "entry/ontology/new")(session, {"label": "둘째 농장", "start": "base", "base": "l2"}, None)
    assert session.library_id == out["id"] and "Crop" in session.studio.onto.objects
    rows = by_id(call("GET", "entry/ontologies")(session, {}, None))
    assert rows[out["id"]]["base"] == "농장 표준" and rows["l2"]["held"]  # the base was opened on the way and is held now


def test_nothing_is_made_and_the_person_stays_where_they_were_when_it_fails(session):
    new = call("POST", "entry/ontology/new")
    with pytest.raises(ValueError):
        new(session, {"label": "", "start": "base", "base": "l2"}, None)
    assert session.library_id == "l1" and len(session.libraries) == 2
    for body in ({"label": "x", "start": "pack", "base": "l1", "modules": []}, {"label": "x", "start": "pack", "base": "none", "modules": ["core"]},
                 {"label": "x", "start": "later"}, {"label": "x", "start": "files"}):
        with pytest.raises(ValueError):
            new(session, body, None)
    assert session.library_id == "l1" and len(session.libraries) == 2


def test_an_empty_ontology_is_made_and_only_an_admin_may_make_one(session):
    out = call("POST", "entry/ontology/new")(session, {"label": "빈 것", "start": "empty"}, None)
    made = by_id(call("GET", "entry/ontologies")(session, {}, None))[out["id"]]
    assert made["counts"]["entities"] == 0 and made["maturity"] is None and made["modules"] == []
    assert NEEDS["entry/ontology/new"] == "admin"


def test_the_persons_list_holds_what_waits_what_happened_and_what_was_settled(session):
    out = call("GET", "entry/inbox")(session, {}, None)
    json.dumps(out)
    assert out["box"]["counts"]["all"] == len(out["box"]["items"]) and out["notes"] == [] and out["done"] == []
    session.manage_edit("update_object", {"name": "Customer", "label": "손님"})
    res = session.manage_propose()  # one visitor is both sides: the change is approved and applied at once
    assert res["ok"] and not res["pending"]
    out = call("GET", "entry/inbox")(session, {}, None)
    assert [n["kind"] for n in out["notes"]][:1] == ["change"] and out["notes"][0]["at"]
    done = out["done"][0]
    assert done["kind"] == "change" and done["status"] == "approved" and done["id"] == res["change"]["id"] and done["at"]


def test_a_person_changes_their_own_password_and_every_sign_in_of_theirs_ends(session, tmp_path):
    from ontlas.web.areas import entry
    from ontlas.web.team import Logins, Users

    users = Users.load(tmp_path / "users.yaml")
    users.add("kim", "first-password-1", name="김", roles=["editor"])
    users.add("lee", "other-password-1", name="이", roles=["viewer"])
    logins = Logins(users)
    token, kim = logins.sign_in("kim", "first-password-1")
    other, _ = logins.sign_in("lee", "other-password-1")
    kept = dict(routes.SERVER)
    routes.SERVER.clear()
    routes.SERVER.update(logins=logins, limits={"idle": 3600})
    entry._wrong.clear()
    try:
        said = call("GET", "entry/me")(session, {}, kim)
        assert said == {"team": True, "hours": 12, "idle_minutes": None, "password_min": 10, "can_change_password": True}
        change = call("POST", "entry/password")
        for body in ({"current": "wrong-password-1", "new": "second-password-2"}, {"current": "first-password-1", "new": "short"},
                     {"current": "first-password-1", "new": "first-password-1"}):
            with pytest.raises(ValueError):
                change(session, body, kim)
        assert logins.user(token) is not None  # nothing changed, nobody signed out
        assert change(session, {"current": "first-password-1", "new": "second-password-2"}, kim) == {"ok": True}
        assert logins.user(token) is None and logins.user(other) is not None
        assert logins.sign_in("kim", "first-password-1") is None and logins.sign_in("kim", "second-password-2") is not None
        again = Users.load(tmp_path / "users.yaml")  # the file holds it, with the name and the roles as they were
        assert again.verify("kim", "second-password-2").roles == ["editor"] and again.users["kim"].name == "김"
        # guessing the current one is slowed down
        kim = logins.users.users["kim"]
        for _ in range(entry.WRONG_PER_MINUTE):
            with pytest.raises(ValueError):
                change(session, {"current": "guess-guess-guess", "new": "third-password-3"}, kim)
        with pytest.raises(ValueError, match="1분 뒤"):
            change(session, {"current": "second-password-2", "new": "third-password-3"}, kim)
        # where nobody signs in there is no password, and the session's keeping is said instead
        routes.SERVER.clear()
        routes.SERVER.update(logins=None, limits={"idle": 1800})
        assert call("GET", "entry/me")(session, {}, None) == {"team": False, "hours": None, "idle_minutes": 30, "password_min": 10,
                                                              "can_change_password": False}
        with pytest.raises(ValueError):
            change(session, {"current": "x", "new": "second-password-2"}, None)
        assert NEEDS["entry/password"] == "viewer"
    finally:
        routes.SERVER.clear()
        routes.SERVER.update(kept)
        entry._wrong.clear()
