"""What the studio page asks for, answered from one studio as plain dicts."""
from __future__ import annotations

import ast
import copy
import json
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from xgen_space.actions import Actor
from xgen_space.check import all_props, column_of, find_prop
from xgen_space.compile.base import CompileError, compiler_for
from xgen_space.conformance import normalize_rows
from xgen_space.ir import Column, Query, Ref
from xgen_space.library import OverlayLibrary
from xgen_space.modules import Module, ModuleError, Requirement, compose
from xgen_space.preview import MODULE_COLOR, MODULE_KIND, TARGETS, _highlight, _ir_text
from xgen_space.repository import Repositories, clean_path, is_litter
from xgen_space.roles import apply_role
from xgen_space.studio import Studio
from xgen_space.web.pages_api import PagesMixin
from xgen_space.web.space_api import SpaceMixin, attach

KIND_ORDER = list(MODULE_KIND)
CHECK_LABEL = {"role": "역할 권한", "parameters": "Parameter", "target": "대상 확인", "state": "상태 전이",
               "states": "허용 상태", "call": "외부 호출"}
_NO_COLUMN = re.compile(r"no such column: (\S+)|column \W?([\w.]+)\W? does not exist|Unknown column '([^']+)'", re.I)
_NO_TABLE = re.compile(r"no such table: (\S+)|relation \W?([\w.]+)\W? does not exist|Table '([^']+)' doesn't exist", re.I)


def said(e: Exception | str) -> str:
    """An engine's or a database's error as the page says it: what is missing, then where to look. The original stays at
    the end, for whoever fixes the source."""
    text = str(e) if isinstance(e, str) else f"{type(e).__name__}: {e}"
    m = _NO_COLUMN.search(text)
    if m:
        name = next(g for g in m.groups() if g)
        return f"원천 DB에 {name} 컬럼이 없어 실행하지 못했습니다. DB 대조에서 정의와 원천 DB를 확인해 주세요. ({text})"
    m = _NO_TABLE.search(text)
    if m:
        name = next(g for g in m.groups() if g)
        return f"원천 DB에 {name} 테이블이 없어 실행하지 못했습니다. DB 대조에서 정의와 원천 DB를 확인해 주세요. ({text})"
    return text


STATUS_WORD = {"pending": "승인 대기", "stale": "실행 전 재검사 실패", "rejected": "반려", "executed": "실행",
               "failed": "외부 호출 실패", "rolled_back": "되돌림"}
EVENT_LABEL = {"requested": "요청", "rejected": "반려", "approved": "승인", "executed": "원천 반영",
               "written": "원천 기록", "called": "외부 호출", "call_failed": "외부 호출 실패 · 원천 복원",
               "rolled_back": "되돌림", "auto_approved": "자동 승인 기준 충족", "stale": "실행 전 재검사 실패",
               "decided": "판정 조회", "answered": "질문 답변", "function_ran": "함수 실행"}
GATE_LABEL = {("bind", "max_errors"): "DB 대조 오류 최대", ("bind", "max_warnings"): "DB 대조 경고 최대",
              ("index", "min_found"): "문서 검색 적중률 최소",
              ("query", "min_agree"): "Backend 결과 일치율 최소", ("decide", "min_agreement"): "판정 일치율 최소",
              ("check", "min_accuracy"): "검증 질문 정답률 최소", ("check", "min_grounded"): "근거 제시율 최소",
              ("check", "max_value_errors"): "거래 값 오류 최대"}
STAGE_LABEL = {"source": "원천 데이터", "define": "온톨로지 정의", "bind": "DB 대조", "project": "그래프 저장소 반영", "index": "문서 · 벡터 색인",
               "query": "질의", "decide": "판정 · 처리", "check": "검증"}
CHANGE_STATUS = {"pending": "승인 대기", "approved": "승인 · 적용", "rejected": "반려"}
READ_ERROR = {
    "encoding": "파일 인코딩을 확인할 수 없어 읽지 못했습니다. UTF-8 또는 CP949로 저장해 다시 업로드해 주세요.",
    "empty": "데이터 행이 없어 테이블을 만들지 못했습니다. 첫 행에 컬럼 이름이 있는지 확인해 주세요.",
    "workbook": "XLSX 형식이 아니어서 파일을 열지 못했습니다. XLSX로 저장해 다시 업로드해 주세요.",
    "workbook_size": "압축 해제 크기가 64MB 한도를 초과해 파일을 열지 못했습니다. 시트를 나누어 다시 업로드해 주세요.",
    "openpyxl": "Excel 읽기 모듈이 설치되지 않아 XLSX 파일을 처리하지 못했습니다. CSV로 저장해 업로드해 주세요.",
}
INGEST_ERROR = {
    "format": "파일 내용을 해석할 수 없어 읽지 못했습니다. 파일 형식을 확인해 다시 업로드해 주세요.",
    "empty": "읽을 수 있는 정의나 본문이 없어 정의서를 만들지 못했습니다. 내용이 있는 파일을 업로드해 주세요.",
    "too_large": "압축 해제 크기가 64MB 한도를 초과해 파일을 열지 못했습니다. 파일을 나누어 다시 업로드해 주세요.",
    "needs_extra": "문서 읽기 모듈이 설치되지 않아 파일을 처리하지 못했습니다. DOCX 또는 TXT로 저장해 업로드해 주세요.",
    "export_needed": "암호가 걸렸거나 지원하지 않는 형식이라 내용을 읽지 못했습니다. 암호를 해제하거나 {export_to} 파일로 내보내 다시 업로드해 주세요.",
}
MODULE_TEXT_MAX = 48 * 1024
ASK_RETRY_WITHIN = 45.0  # seconds into a natural-language question after which no further attempt starts
DRAFT_RETRY_WITHIN = 100.0  # the same for a policy draft, which no page request waits on: at most 5 minutes in all
POLICY_MAX = 12000  # characters of policy text a draft reads
JSON_PREVIEW = 40_000  # characters of the one JSON the page shows; the download has it all
RAW_FILES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg", ".ico", ".mp4", ".mov", ".avi",
             ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".zip", ".7z", ".rar", ".tar", ".gz", ".exe", ".dll", ".bin"}
MONITOR_EVERY = 20.0  # seconds between measurements of the pipeline while the board is open
PIPELINES_MAX = 5  # applied pipelines a visitor keeps to switch between
WORKSPACE = "workspace"  # the module the management screens' edits are filed as (manage.NAME)
SAMPLE_ROWS = 3  # rows of a table the draft review shows beside it
IMPACT_KINDS = {"질의": "queries", "결정": "decisions", "검증 질문": "questions", "액션": "actions", "역할": "roles",
                "함수": "functions", "계산 속성": "computed"}  # what _readers says each reader is
PERSONAL = re.compile(r"연락처|전화|휴대|핸드폰|이메일|메일|주소|주민|생년|생일|계좌|카드번호|phone|mobile|tel|e?mail|address|birth|"
                      r"ssn|account|card_?no", re.I)  # columns a draft suggests hiding
EDIT_TEXT = [
    (r"^query '(.+)' already exists$", r"질의 '\1'이(가) 이미 있어 저장하지 못했습니다. 다른 영문 이름을 입력해 주세요."),
    (r"^query name '(.*)' must be .*$", r"질의 영문 이름 '\1'은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있어 저장하지 못했습니다."),
    (r"^hit policy priority needs a priority on every rule; (.+) have none$", r"우선순위 방식은 규칙마다 우선순위가 있어야 합니다. \1에 우선순위를 먼저 정해 주세요."),
    (r"^hit policy '(.+)' is not one of .*$", r"적용 방식 '\1'은 쓸 수 없습니다."),
    (r"^type '(.+)' is not one of .*$", r"자료형 '\1'은 쓸 수 없습니다. 문자열, 정수, 소수, 참 · 거짓, 날짜, 일시, 허용값 중에서 골라 주세요."),
    (r"^rule id '(.*)' must be letters, digits, _ and - starting with a letter$", r"규칙 번호 '\1'은 영문자로 시작하고 영문자 · 숫자 · _ · - 만 쓸 수 있어 저장하지 못했습니다."),
    (r"^rule '(.+)' already exists in (\S+)$", r"규칙 '\1'이 이미 있어 추가하지 못했습니다. 다른 번호를 입력해 주세요."),
    (r"^rule '(.+)' is unknown in (\S+)$", r"규칙 '\1'을 찾지 못했습니다. 화면을 새로고침해 주세요."),
    (r"^decision (\S+) needs at least one rule$", r"결정표에 규칙이 하나는 있어야 하므로 제외하지 못했습니다."),
    (r"^decision (\S+) has no (?:input|output) '(.+)'$", r"결정표에 '\2' 항목이 없어 저장하지 못했습니다."),
    (r"^decision '(.+)' (?:is unknown|already exists)$", r"결정표 '\1'을 처리하지 못했습니다. 이름을 확인해 주세요."),
    (r"^(?:decision|action|role) name '(.*)' must be letters, digits and _ starting with a letter$", r"이름 '\1'은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있어 만들지 못했습니다."),
    (r"^give at least one input$", r"입력값이 없어 결정표를 만들지 못했습니다. 입력값을 선택해 주세요."),
    (r"^(\S+): '(.+)' is not a literal; quote text as .*$", r"\1 조건의 값 '\2'을 읽지 못했습니다. 값을 확인해 주세요."),
    (r"^(\S+) takes a (\S+)$", r"기준값 \1의 값 형식이 맞지 않아 저장하지 못했습니다."),
    (r"^(.+) must be at least (\S+)$", r"\1 값은 \2 이상이어야 하므로 저장하지 못했습니다."),
    (r"^(.+) must be at most (\S+)$", r"\1 값은 \2 이하여야 하므로 저장하지 못했습니다."),
    (r"^a state machine has at least two states$", r"상태 값이 두 개 이상 있어야 하므로 저장하지 못했습니다."),
    (r"^a transition goes between states: (\S*) to (\S*)$", r"전이의 상태 값 \1, \2이 상태 목록에 없어 저장하지 못했습니다."),
    (r"^unknown edit '(.+)'$", r"지원하지 않는 편집(\1)이라 적용하지 못했습니다."),
    (r"^(object|property|link) name '(.*)' must be letters, digits and _ starting with a letter$",
     r"이름 '\2'은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있어 만들지 못했습니다."),
    (r"^object type '(.+)' already exists$", r"객체 '\1'이 이미 있어 추가하지 못했습니다. 다른 이름을 입력해 주세요."),
    (r"^give the key and the key property$", "키 속성을 정하지 않아 객체를 추가하지 못했습니다. 키와 키 속성을 입력해 주세요."),
    (r"^object type '(.+)' is unknown$", r"객체 '\1'을 찾지 못했습니다. 화면을 새로고침해 주세요."),
    (r"^key '(.+)' is not a property of (.+)$", r"'\1'은 \2의 속성이 아니어서 키로 정하지 못했습니다."),
    (r"^the key of (.+) is set where it is defined; change it there$",
     r"\1의 키는 표준 모듈에서 정해져 있어 여기서 바꾸지 못했습니다. 해당 모듈에서 바꿔 주세요."),
    (r"^(.+) already has '(.+)'$", r"\1에 속성 '\2'이 이미 있어 추가하지 못했습니다."),
    (r"^(\w+)\.(\w+) is unknown$", r"속성 \1.\2을 찾지 못했습니다. 화면을 새로고침해 주세요."),
    (r"^the type of (.+) comes from its standard; it cannot be changed here$",
     r"\1의 자료형은 표준 모듈에서 정해져 있어 바꾸지 못했습니다. 새 속성을 추가해 주세요."),
    (r"^'(.+)' is the key of (.+); delete the object instead$",
     r"'\1'은 \2의 키라서 지우지 못했습니다. 객체를 지워 주세요."),
    (r"^'(.+)' comes from (.+), which (.+) specialises; delete it on (.+)$",
     r"'\1'은 상위 객체 \2에서 상속 속성이라 \3에서 지우지 못했습니다. \2에서 지워 주세요."),
    (r"^link '(.+)' already exists$", r"관계 '\1'이 이미 있어 추가하지 못했습니다. 다른 이름을 입력해 주세요."),
    (r"^link '(.+)' is unknown$", r"관계 '\1'을 찾지 못했습니다. 화면을 새로고침해 주세요."),
    (r"^the endpoints of (.+) come from its standard; add a new link instead$",
     r"\1의 양 끝 객체는 표준 모듈에서 정해져 있어 바꾸지 못했습니다. 새 관계를 추가해 주세요."),
    (r"^question id '(.*)' is empty or already used$",
     r"질문 번호 '\1'이 비어 있거나 이미 있어 추가하지 못했습니다. 다른 번호를 입력해 주세요."),
    (r"^question '(.+)' is unknown$", r"검증 질문 '\1'을 찾지 못했습니다. 화면을 새로고침해 주세요."),
]
GAP_TEXT = [(r"^no rule matched$", "적용된 규칙 없음"), (r"^rule (\S+) has no cite$", r"규칙 \1 출처 없음"),
            (r"^(\S+) has no source column$", r"\1 원천 컬럼 없음"), (r"^no version$", "판본 없음"),
            (r"^no answer$", "답 없음")]


ISSUE_TEXT = [
    (r"^no version of '(.+?)' satisfies .*$", r"의존 모듈 '\1'을 찾지 못했습니다. requires 항목의 모듈 이름을 확인해 주세요."),
    (r"^cannot read requirement '(.+?)'.*$", r"requires 값 '\1'을 읽지 못했습니다. name 또는 name>=1.0 형식으로 입력해 주세요."),
    (r"^(\S+) requires '(.+?)', which is not attached$", r"\1에 필요한 '\2' 모듈이 적용되어 있지 않습니다. '\2' 모듈을 먼저 적용해 주세요."),
    (r"^(\S+) requires '(.+?)', but (\S+) is attached$", r"\1에 필요한 '\2' 버전과 적용된 \3 버전이 맞지 않습니다. 버전을 확인해 주세요."),
    (r"^modules require each other in a cycle: (.+)$", r"모듈 의존 관계가 순환합니다. \1. requires 항목을 확인해 주세요."),
    (r"^module (\S*): kind must be one of .*$", r"모듈 \1의 kind 값이 올바르지 않습니다. core, domain, industry, customer, binding, quality, method 중에서 지정해 주세요."),
    (r"^(\w+)\.(\w+): type '(.+?)' is not one of .*$", r"\1.\2의 타입 '\3'은 사용할 수 없습니다. string, integer, decimal, boolean, date, datetime, enum 중에서 지정해 주세요."),
    (r"^(\w+)\.(\w+): expected .*$", r"\1.\2의 계산식을 해석하지 못했습니다. 식을 확인해 주세요."),
    (r"^decision (\S+): target '(.+?)' is unknown$", r"결정 \1의 대상 객체 '\2'를 찾지 못했습니다. target 항목을 확인해 주세요."),
    (r"^link (\S+): endpoints (\S+) -> (\S+) must be object types$", r"관계 \1의 객체 \2 또는 \3을 찾지 못했습니다. 출발 객체와 도착 객체를 확인해 주세요."),
    (r"^(\S+) extends (?:object type|link|decision|role) '(.+?)', which no attached module defines$", r"확장 대상 '\2'를 정의한 모듈이 적용되어 있지 않습니다. 대상 이름과 requires 항목을 확인해 주세요."),
    (r"^(\S+) changes the type of (\S+) from (\S+) to (\S+)$", r"\2의 타입은 변경할 수 없습니다. \3에서 \4로 바꾸려면 새 속성을 추가해 주세요."),
    (r"^(\S+) binds (\S+), which is not a property of (\S+)$", r"\2는 \3의 속성이 아니어서 연결하지 못했습니다. 속성 이름을 확인해 주세요."),
    (r"^(\S+) removes (.+), which is not there$", r"제거 대상 \2를 찾지 못했습니다. 이름을 확인해 주세요."),
    (r"^(\S+) defines (\S+) '(.+?)', already defined by (\S+?);.*$", r"'\3'은 \4에 이미 정의되어 있습니다. 다른 이름을 사용하거나 확장으로 지정해 주세요."),
    (r"^module '(.+?)' is not attached$", r"'\1' 모듈이 적용되어 있지 않습니다."),
    # a query a person typed
    (r"^unknown label '(.+?)'$", r"'\1' 객체를 찾지 못했습니다. 객체 이름을 확인해 주세요."),
    (r"^give '(.+?)' a label on first use$", r"변수 \1에 객체 이름을 지정해 주세요. 예: (\1:Customer)"),
    (r"^(.+) is outside the ontology namespace (.+)$", r"\1은 온톨로지 네임스페이스 \2에 없는 주소입니다."),
    (r"^'return' lists at least one column$", "return 항목에 컬럼을 하나 이상 지정해 주세요."),
    (r"^a query is an object$", "질의는 JSON 객체로 입력해 주세요."),
    (r"^Expecting .* line \d+ column \d+ .*$", "JSON 형식이 올바르지 않습니다."),
    (r"^Expected \{.*$", "SELECT, CONSTRUCT, DESCRIBE, ASK 중 하나로 시작해 주세요."),
    # a decision table drawn from past cases
    (r"^pick at least one input$", "입력을 하나 이상 선택해 주세요."),
    (r"^(\d+) past cases with a result; at least (\d+) are needed$", r"결과가 있는 지난 처리 기록이 \1건입니다. \2건 이상 필요합니다."),
    (r"^(\S+): inputs reach one relation away at most$", r"\1: 입력은 관계 한 단계까지만 지정할 수 있습니다."),
    (r"^(\S+): '(.+?)' reaches many (\S+); pick a relation to one$", r"\1: 여러 \3로 이어지는 관계입니다. 하나로 이어지는 관계를 선택해 주세요."),
    (r"^(\S+) is (\S+); inputs are allowed values, true/false or numbers$", r"\1은 \2 타입입니다. 입력에는 허용값, 참 · 거짓, 숫자만 사용할 수 있습니다."),
    (r"^(\S+) is the result itself$", r"\1은 결과 컬럼이어서 입력으로 사용할 수 없습니다."),
    (r"^(\S+) is (\S+); the result has to be an allowed-value or true/false property$", r"\1은 \2 타입입니다. 결과는 허용값 또는 참 · 거짓 속성이어야 합니다."),
    (r"^'(.+?)' is not Type\.property$", r"결과 컬럼 '\1'을 찾지 못했습니다. 다시 선택해 주세요."),
]


def _issue_text(msg: str) -> str:
    """A check's finding, as the page says it; one not listed here keeps its own words."""
    for pattern, text in ISSUE_TEXT:
        if re.match(pattern, msg):
            return re.sub(pattern, text, msg)
    return msg


def mine_label(o, name: str) -> str:
    t = o.objects.get(name)
    return (t.label or name) if t is not None else name


def _edit_text(msg: str) -> str:
    """A management edit's refusal, as the page says it; checks the definition raises keep their own words."""
    for pattern, text in EDIT_TEXT:
        if re.match(pattern, msg):
            return re.sub(pattern, text, msg)
    return f"정의 검사를 통과하지 못해 적용하지 않았습니다. {_issue_text(msg)}"


def _gap_text(gap: str) -> str:
    """What a question's answer lacks of its grounds, as the page says it."""
    for pattern, text in GAP_TEXT:
        if re.match(pattern, gap):
            return re.sub(pattern, text, gap)
    return gap


def plain(v: Any) -> Any:
    """A value the page can show as JSON."""
    if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else v
    if isinstance(v, Decimal):
        return plain(float(v))
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [plain(x) for x in v]
    return str(v)


def principal_keys(node: Any) -> list[str]:
    """The principal attributes a role's row filters ask for, e.g. ['customer_id']."""
    found: list[str] = []
    if isinstance(node, dict):
        if isinstance(node.get("principal"), str):
            found.append(node["principal"])
        for v in node.values():
            found += principal_keys(v)
    elif isinstance(node, list):
        for v in node:
            found += principal_keys(v)
    return list(dict.fromkeys(found))


@dataclass
class DataOptions:
    """What a visitor may bring in: files within these limits, the bundled samples, and (off unless asked) a database."""

    file_bytes: int = 1 << 20
    total_bytes: int = 4 << 20
    files: int = 30
    rows: int = 10_000
    columns: int = 80
    samples: Path | None = None
    allow_connect: bool = False
    policies: Path | None = None  # example policy texts (.md, .txt) for drafting rules
    repositories: Path | None = None  # where repositories outlive the server; otherwise they end with the visitor
    embedder: dict | None = None  # the model every visitor's documents are embedded with, over what the studio file says
    rest: bool = False  # /v1 is on: the page says so, and how to reach it


class StudioSession(SpaceMixin, PagesMixin):
    """One visitor's studio: modules plugged in and out, queries, decisions and approvals, kept apart from others."""

    def __init__(self, studio: Studio, *, llm: Callable[[str, str], str] | None = None,
                 data: DataOptions | None = None, origin: dict | None = None,
                 repositories: Repositories | None = None):
        self.studio = studio
        self.llm = llm
        self._llm_last: dict | None = None  # how the model's last call went, for the sidebar
        self.data = data or DataOptions()
        self.origin = origin or {"kind": "config"}
        self.lock = threading.RLock()
        self.log: list[dict] = []
        self._measured: dict = {}  # what the last look at the flow found, item by item
        self._issue_open: dict | None = None  # issue id -> when it opened and what it was called
        self.used = time.time()
        if studio.library is not None and not isinstance(studio.library, OverlayLibrary):
            studio.library = OverlayLibrary(studio.library, [])  # a visitor's edited modules are kept here
        self._library_rows = studio.library.list() if studio.library is not None else []
        self.repositories = repositories or Repositories()
        self.repo = next(iter(self.repositories.items))  # the repository this visitor is looking at
        self.uploads: dict[str, list] = {}  # file path -> the tables read from it, for files going into a draft
        self.definitions: dict = {}  # file path -> the table and code definitions read from it (definitions.py)
        self.sizes: dict[str, int] = {}
        self._held: dict[str, str] = {}  # file path -> the hash of what uploads and definitions hold for it
        self.events: deque = deque(maxlen=30)  # what happened here, newest first, for the control board
        self._watch: dict | None = None  # the last measurement of the pipeline
        self.pending = None  # (draft, the database it was drawn from, the tables loaded into it, the rules)
        self.who = "방문자"  # the person behind the requests; a team studio sets it from the login
        self.self_approve = True  # one visitor is both sides of a change; a team studio turns this off
        self.store = None  # a library folder approved changes are written to (xspace serve --library-write)
        self.workspace = None  # the management screens' pending edits (manage.Workspace), until filed
        self._ws_sig: tuple = ()
        self._draft: dict | None = None  # the policy draft running or last finished, for the page to collect
        self._reading: dict | None = None  # the relation reading running or last finished, for the page to collect
        self._adopt(studio)
        self.pipeline = "p1"  # the one on screen; every applied draft stays here to switch back to
        self.pipelines: list[dict] = [{"id": "p1", "label": "기본 파이프라인", "studio": studio, "origin": self.origin,
                                       "rows": self._library_rows, "log": self.log}]
        self.load_pipelines()
        self.load_relations()

    def _adopt(self, studio: Studio) -> None:
        """Make a studio this session's: its change requests follow the session's approval and storage."""
        self.studio = studio
        studio.changes.self_approve = self.self_approve
        studio.actions.self_approve = self.self_approve
        studio.changes.store = self.store
        attach(self)

    # ---- helpers -------------------------------------------------------------------------------------------

    def _note(self, kind: str, text: str, **detail) -> None:
        self.log.insert(0, {"kind": kind, "text": text, "at": datetime.now().isoformat(timespec="seconds"), **plain(detail)})
        del self.log[30:]
        self.event(kind, text)

    def event(self, kind: str, text: str) -> None:
        self.events.appendleft({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": text})

    def _reproject(self) -> dict:
        graphs = [n for n, b in self.studio.backends.items() if b.capabilities.load]
        if not graphs:
            return {}
        try:
            return plain(self.studio.project(into=graphs))
        except Exception as e:  # a composition without bindings has nothing to project
            return {"error": f"{type(e).__name__}: {e}"}

    def _label(self, module: str) -> str:
        row = next((r for r in self._library_rows if r["name"] == module), None)
        if row:
            return row["label"] or module
        comp = self.studio.composition
        return next((m.label or m.name for m in (comp.modules if comp else []) if m.name == module), module)

    def _obj_label(self, name: str) -> str:
        o = self.studio.onto
        return o.objects[name].label or name if name in o.objects else name

    # ---- the whole page ------------------------------------------------------------------------------------

    def state(self) -> dict:
        st, o = self.studio, self.studio.onto
        comp = st.composition
        on = [m.name for m in comp.modules] if comp else [o.name]
        rows = [dict(r) for r in self._library_rows] if self._library_rows else [
            {"name": m.name, "label": m.label, "kind": m.kind, "latest": m.version, "versions": [m.version],
             "requires": [str(r) for r in m.requires], "counts": m.counts(), "description": m.description}
            for m in (comp.modules if comp else [])]
        for r in rows:
            r["on"] = r["name"] in on
            r["kind_label"] = MODULE_KIND.get(r["kind"], r["kind"])
            r["color"] = MODULE_COLOR.get(r["kind"], "#8a96a5")
            r["version"] = next((m.version for m in comp.modules if m.name == r["name"]), r["latest"]) if comp \
                else r["latest"]
        rows.sort(key=lambda r: (KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 99, r["name"]))
        layers = []
        if comp:
            for k in KIND_ORDER:
                ms = [{"name": m.name, "label": m.label or m.name, "version": m.version}
                      for m in comp.modules if m.kind == k]
                if ms:
                    layers.append({"kind": k, "kind_label": MODULE_KIND[k], "color": MODULE_COLOR[k], "modules": ms})
        roles = [{"name": r.name, "label": r.label or r.name,
                  "principal": principal_keys({k: v for k, v in r.row_filters.items()})}
                 for r in o.roles.values()]
        domains = [m.label or m.name for m in comp.modules if m.kind == "domain"] if comp else [o.label or o.name]
        registered = st.registered()
        return plain({
            "title": " · ".join(domains),
            "modules_on": len(on),
            "library": rows,
            "layers": layers,
            "graph": self.graph(),
            "stats": {"objects": len(o.objects), "links": len(o.links),
                      "properties": sum(len(t.properties) for t in o.objects.values()),
                      "decisions": len(o.decisions), "actions": len(o.actions), "queries": len(o.queries),
                      "questions": len(o.questions)},
            "queries": [{"name": q.name, "label": q.label or q.name, "params": q.params,
                         "example": registered.get(q.name, (None, {}))[1]} for q in o.queries.values()],
            "questions": [{"id": q.id, "text": q.text, "decision": q.decision, "key": q.key, "query": q.query,
                           "params": q.params} for q in o.questions],
            "decisions": [{"name": d.name, "label": d.label or d.name, "target": d.target,
                           "target_label": self._obj_label(d.target)} for d in o.decisions.values()],
            "actions": [{"name": a.name, "label": a.label or a.name, "target": a.target, "parameters": a.parameters,
                         "decisions": [c.decision for c in a.criteria if c.decision], "approval": a.approval}
                        for a in o.actions.values()],
            "roles": roles,
            "targets": [{"id": t, "label": lbl} for t, lbl in TARGETS],
            "ask": self.llm is not None,
            "zen": _has_zen(),
            "log": self.log,
            "origin": self.origin,
            "repository": self._repository_row(),
            "repositories": self.repositories.rows(),
            "pipelines": [{"id": p["id"], "label": p["label"]} for p in self.pipelines],
            "pipeline": self.pipeline,
            "data": {"samples": bool(self._sample_files()), "connect": self.data.allow_connect,
                     "kept": self.repositories.persistent,
                     "files": sum(r["files"] for r in self.repositories.rows() if r["id"] == self.repo),
                     "policy_sample": bool(self._policy_files())},
            "identities": [{"name": i.name, "label": i.label or i.name} for i in o.identities.values()],
            "who": self.who, "self_approve": self.self_approve,
            "changes": sum(c.status == "pending" for c in st.changes.requests.values()),
        })

    def graph(self) -> dict:
        st, o = self.studio, self.studio.onto
        comp = st.composition
        nodes, clusters = [], {}
        for t in o.objects.values():
            owner = comp.owner(f"object:{t.name}") if comp else o.name
            clusters.setdefault(owner, self._label(owner))
            nodes.append({"id": t.name, "label": t.label or t.name, "table": t.table, "abstract": t.abstract,
                          "key": t.key, "module": owner})
        edges = [{"id": lk.name, "source": lk.source, "target": lk.target, "label": lk.label or lk.name,
                  "subtype": False} for lk in o.links.values()]
        edges += [{"source": t.name, "target": t.parent, "label": "하위 유형", "subtype": True}
                  for t in o.objects.values() if t.parent in o.objects]
        return {"nodes": nodes, "edges": edges, "clusters": [{"id": k, "label": v} for k, v in clusters.items()]}

    def object(self, name: str) -> dict:
        st, o = self.studio, self.studio.onto
        t = o.obj(name)
        comp = st.composition
        props = []
        for p in all_props(o, name):
            prop = find_prop(o, name, p)
            inherited = p not in t.properties
            owner = comp.owner(f"property:{name}.{p}") if comp and not inherited else ""
            props.append({"name": p, "label": prop.label or p, "type": prop.type, "unit": prop.unit,
                          "values": prop.values, "labels": prop.labels, "required": prop.required, "cite": prop.cite,
                          "column": column_of(o, name, p) if t.table and not prop.expr else "", "key": p == t.key,
                          "module": owner, "module_label": self._label(owner) if owner else "",
                          "inherited": inherited, "expr": prop.expr, "mask": prop.mask,
                          "description": prop.description})
        links = []
        for lk in o.links.values():
            if name in (lk.source, lk.target):
                out = lk.source == name
                other = lk.target if out else lk.source
                links.append({"name": lk.name if out else (lk.inverse or lk.name), "label": lk.label or lk.name,
                              "other": other, "other_label": self._obj_label(other), "out": out,
                              "cardinality": lk.cardinality})
        children = [c.name for c in o.objects.values() if c.parent == name]
        owner = comp.owner(f"object:{name}") if comp else ""
        return plain({
            "name": name, "label": t.label or name, "description": t.description, "key": t.key, "table": t.table,
            "abstract": t.abstract, "parent": t.parent, "parent_label": self._obj_label(t.parent) if t.parent else "",
            "children": [{"name": c, "label": self._obj_label(c)} for c in children],
            "aligned": t.aligned, "cite": t.cite, "module": owner, "module_label": self._label(owner) if owner else "",
            "touched": [self._label(m) for m in (comp.touched.get(f"object:{name}", []) if comp else [])],
            "states": {"property": t.states.property, "states": t.states.states, "initial": t.states.initial,
                       "transitions": [{"from": x.source, "to": x.target} for x in t.states.transitions]}
            if t.states else None,
            "series": dict(t.series), "identity": name in o.identities,
            "properties": props, "links": links, "documents": self._mentions(name),
        })

    # ---- modules ---------------------------------------------------------------------------------------------

    def impact(self, name: str, cascade: bool = False) -> dict:
        imp = self.studio.detach_impact(name, cascade=cascade)
        d = imp.to_dict()
        d["label"] = self._label(name)
        d["cascade"] = cascade
        d["dependents_labels"] = [self._label(x) for x in imp.dependents]
        return d

    def detach(self, name: str, cascade: bool = False) -> dict:
        try:
            imp = self.studio.detach(name, cascade=cascade)
        except ModuleError as e:
            imp = getattr(e, "impact", None)
            return {"ok": False, "error": str(e), "impact": imp.to_dict() if imp else None}
        gone = [name, *imp.dependents] if cascade else [name]
        proj = self._reproject()
        warning = _projection_warning(proj)
        self._keep_applied()
        self._note("detach", f"{', '.join(self._label(x) for x in gone)} 모듈을 해제했습니다. "
                   f"항목 {len(imp.removed)}개가 제거되었습니다. {warning}".strip(), removed=imp.removed[:12])
        return {"ok": True, "impact": imp.to_dict(), "projection": proj, "warning": warning}

    def _keep_applied(self) -> None:
        """What is on stays on across a restart, when approved changes are written to a library folder."""
        comp = self.studio.composition
        if self.store is not None and comp is not None:
            self.store.keep_applied([m.name for m in comp.modules])

    def object_rows(self, name: str, limit: int = 20) -> dict:
        """The data under a definition: rows as the source holds them, in the object's own words."""
        st = self.studio
        t = st.onto.obj(name)
        if not t.table:
            return {"ok": False, "error": "개념 객체라 연결된 데이터가 없습니다."}
        props = [p for p in all_props(st.onto, name) if not find_prop(st.onto, name, p).expr][:12]
        q = {"match": {"x": name}, "return": [f"x.{p}" for p in props], "limit": max(1, min(int(limit), 100))}
        res = st.run(q)
        return plain({"ok": True, "name": name, "label": t.label or name, "columns": res.columns,
                      "labels": {p: find_prop(st.onto, name, p).label or p for p in props}, "rows": [list(r) for r in res.rows]})

    def attach(self, name: str) -> dict:
        before = {m.name for m in self.studio.composition.modules} if self.studio.composition else set()
        try:
            comp = self.studio.attach(name)
        except ModuleError as e:
            return {"ok": False, "error": str(e)}
        added = [m.name for m in comp.modules if m.name not in before]
        self._keep_applied()
        proj = self._reproject()
        warning = _projection_warning(proj)
        self._note("attach", f"{', '.join(self._label(x) for x in added)} 모듈을 적용했습니다. {warning}".strip(),
                   added=added)
        return {"ok": True, "added": added, "projection": proj, "warning": warning}

    def export_owl(self) -> str:
        from xgen_space.exchange.owl import to_owl

        comp = self.studio.composition
        ttl, _ = to_owl(self.studio.onto, origin=comp.origin if comp else None)
        return ttl

    # ---- queries ---------------------------------------------------------------------------------------------

    def run_query(self, query: str | dict | Query, params: dict | None = None, *, role: str = "",
                  principal: dict | None = None) -> dict:
        st = self.studio
        name = query if isinstance(query, str) else ""
        q = st.query(query)
        values = dict(params or {})
        shown, extra = q, {}
        if role:
            if name and not st.onto.roles[role].can("run", name):
                return {"ok": False, "error": f"{st.onto.roles[role].label or role} 역할에 실행 권한이 없어 질의를 실행하지 못했습니다."}
            shown, extra = apply_role(st.onto, q, role, principal)
        bound = {**values, **extra}
        translations = []
        for target, label in TARGETS:
            try:
                c = st.translate(shown, target)
                text = c.preview(bound) if set(c.params) <= set(bound) | set(c.literals) else c.text
                translations.append({"target": target, "label": label, "ok": True, "text": text,
                                     "html": _highlight(text, target), "params": c.params})
            except CompileError as e:
                translations.append({"target": target, "label": label, "ok": False, "error": str(e)})
        results, first, agree = [], None, True
        for bname, b in st.backends.items():
            try:
                res = st.run(q, values, backend=bname, role=role or None, principal=principal)
                rows = normalize_rows(res.rows, res.columns, res.compiled.column_types)
                if first is None:
                    first = rows
                elif sorted(map(repr, rows)) != sorted(map(repr, first)):
                    agree = False
                results.append({"backend": bname, "language": b.capabilities.language,
                                "dialect": b.capabilities.dialect, "columns": res.columns, "rows": plain(rows),
                                "ok": True, "masked": res.masked})
            except Exception as e:
                agree = False
                results.append({"backend": bname, "language": b.capabilities.language,
                                "dialect": b.capabilities.dialect, "ok": False, "error": f"{type(e).__name__}: {e}"})
        source = {"ir": _ir_text(q.to_dict())}
        for lang in ("sparql", "cypher"):  # what a person would write: computed properties by their names
            try:
                comp = compiler_for(st.onto, lang)
                comp.by_name = True
                c = comp.compile(q)
                source[lang] = c.preview(values) if set(c.params) <= set(values) | set(c.literals) else c.text
            except CompileError:
                pass
        return plain({"ok": True, "name": name, "label": st.onto.queries[name].label if name else "",
                      "ir": _ir_text(shown.to_dict()), "params": bound, "translations": translations,
                      "results": results, "agree": agree and len(results) > 1, "source": source})

    def run_text(self, language: str, text: str, *, role: str = "", principal: dict | None = None) -> dict:
        if len(text) > 8000:
            return {"ok": False, "error": "쿼리 길이가 8,000자 한도를 초과해 실행하지 못했습니다. 쿼리를 줄여 다시 입력해 주세요."}
        try:
            if language == "sparql":
                from xgen_space.parse.sparql import parse_sparql

                q = parse_sparql(text, self.studio.onto)
            elif language == "cypher":
                from xgen_space.parse.cypher import parse_cypher

                q = parse_cypher(text, self.studio.onto)
            else:
                q = Query.from_dict(json.loads(text))
        except Exception as e:
            return {"ok": False, "error": f"쿼리 문법을 해석하지 못했습니다. {_issue_text(str(e).split(chr(10))[0])}"}
        return self.run_query(q, role=role, principal=principal)

    def ask(self, question: str, *, role: str = "", principal: dict | None = None, model: Callable[[str, str], str] | None = None) -> dict:
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 자연어 질문을 처리하지 못했습니다."}
        from xgen_space.nl import IRGenerator, probe

        llm, tries = self._budgeted(model)
        gen = IRGenerator(self.studio.onto, llm, role=role or None, terms=self._terms(),
                          runner=probe(self.studio, role=role or None, principal=principal)).generate(question[:500])
        if not gen.ok:
            return {"ok": False, "error": "질문을 질의로 변환하지 못했습니다. " + self._failed(gen.attempts, tries)
                                          + " 질문을 바꿔 다시 입력해 주세요."}
        out = self.run_query(gen.registered or gen.query, gen.params, role=role, principal=principal)
        out["attempts"] = len(gen.attempts)
        return out

    def _budgeted(self, model: Callable[[str, str], str] | None = None, within: float | None = None
                  ) -> tuple[Callable[[str, str], str], list]:
        """The model for one page request, and the calls it has made. A proxy in front of the page may give up on
        a request (Cloudflare at 100 s) and a model that reasons first takes 20 to 40 s: another attempt starts only
        early enough to end in time."""
        started, tries, model = time.monotonic(), [], model or self.llm
        within = ASK_RETRY_WITHIN if within is None else within

        def llm(system: str, user: str) -> str:
            if tries and time.monotonic() - started > within:
                raise TimeoutError("no time left for another attempt")
            tries.append(1)
            try:
                out = model(system, user)
            except Exception as e:
                self._llm_last = {"ok": False, "at": datetime.now().isoformat(timespec="seconds"), "error": said(e)}
                raise
            self._llm_last = {"ok": True, "at": datetime.now().isoformat(timespec="seconds")}
            return out

        return llm, tries

    @staticmethod
    def _failed(attempts: list, tries: list) -> str:
        """Why the model's attempts came to nothing: what it last said wrong, or that it never finished an answer."""
        answered = [a for a in attempts if a.raw]  # what the model last said, not the attempt time stopped
        if not answered:
            return "언어 모델이 답변을 끝내지 못했습니다."
        late = " 응답 시간 한도로 다시 시도하지 못했습니다." if len(tries) < len(attempts) else ""
        return " / ".join(answered[-1].issues[:3]) + late

    def _policy_files(self) -> list[Path]:
        d = self.data.policies
        if not d or not Path(d).is_dir():
            return []
        return sorted(p for p in Path(d).iterdir() if p.suffix.lower() in (".md", ".txt"))

    def policy_sample(self) -> dict:
        found = self._policy_files()
        if not found:
            return {"ok": False, "error": "예시 정책서가 설정되지 않아 불러오지 못했습니다."}
        return {"ok": True, "name": found[0].name, "text": found[0].read_text(encoding="utf-8")[:POLICY_MAX]}

    def document_text(self, name: str, section: str = "") -> dict:
        """The text of an uploaded document, or of one of its sections, for the policy draft."""
        for d in self.definitions.values():
            for doc in getattr(d, "documents", None) or []:
                if doc.get("name") == name:
                    part = next((s for s in doc.get("sections") or [] if s.get("title") == section), None)
                    text = part["text"] if part else doc.get("text", "")
                    return {"ok": True, "name": name, "text": text[:POLICY_MAX], "cut": len(text) > POLICY_MAX,
                            "sections": [s.get("title") for s in doc.get("sections") or [] if s.get("text", "").strip()]}
        return {"ok": False, "error": "업로드한 문서에 없어 불러오지 못했습니다. 데이터 카탈로그에서 문서를 업로드해 주세요."}

    def policy_start(self, text: str, target: str = "", name: str = "") -> dict:
        """Start a draft and return at once: the model takes a minute or more, longer than a proxy in front of the
        page waits, and the visitor's other requests must not stand behind it. The page collects it by policy_result."""
        if self._draft and self._draft["out"] is None:
            return {"ok": True, "job": self._draft["id"]}
        job: dict = {"id": uuid.uuid4().hex, "out": None}
        self._draft = job

        def run() -> None:
            try:
                job["out"] = self.policy_draft(text, target, name)
            except ValueError as e:
                job["out"] = {"ok": False, "error": str(e)}
            except Exception:  # a thread has no caller to report to: the page must still end its wait
                job["out"] = {"ok": False, "error": "정책서 규칙 초안을 만들지 못했습니다. 다시 시도해 주세요."}

        threading.Thread(target=run, name="policy-draft", daemon=True).start()
        return {"ok": True, "job": job["id"]}

    def policy_result(self, job: str) -> dict:
        if not self._draft or self._draft["id"] != job:
            return {"ok": False, "error": "진행 중인 규칙 초안을 찾지 못했습니다. 초안을 다시 생성해 주세요."}
        return self._draft["out"] or {"ok": True, "running": True}

    def policy_draft(self, text: str, target: str = "", name: str = "") -> dict:
        """A decision table drafted from policy text by the model and checked by the engine, as module text for
        the editor; a person files it as a change request (see policy.py)."""
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 정책서 규칙 초안을 만들지 못했습니다."}
        text = str(text or "").strip()[:POLICY_MAX]
        if not text:
            raise ValueError("정책서 내용이 없어 규칙 초안을 만들지 못했습니다. 정책서 조항을 입력해 주세요.")
        comp = self.studio.composition
        if comp is None:
            return {"ok": False, "error": "모듈로 구성된 스페이스가 아니어서 규칙 초안을 모듈로 만들지 못했습니다."}
        if target and target not in self.studio.onto.objects:
            raise ValueError(f"대상 객체 {target} 이(가) 정의에 없어 규칙 초안을 만들지 못했습니다. 대상을 다시 선택해 주세요.")
        import yaml

        from xgen_space.policy import CALL_SECONDS, CALL_TOKENS, PolicyDrafter

        roomier = getattr(self.llm, "roomier", None)
        llm, tries = self._budgeted(roomier(CALL_TOKENS, CALL_SECONDS) if roomier else self.llm, DRAFT_RETRY_WITHIN)
        d = PolicyDrafter(list(comp.modules), llm, compose_kw=self.studio._compose_kw).draft(
            text, target=target, name=str(name or ""))
        late = len(tries) < len(d.attempts)
        if d.module is None:
            return {"ok": False, "error": "정책서를 결정표로 바꾸지 못했습니다. " + self._failed(d.attempts, tries)
                                          + " 정책서 내용을 줄이거나 대상을 바꿔 다시 시도해 주세요."}
        (dname, table), = d.module.body["decisions"].items()
        return plain({
            "ok": True, "module": d.module.name, "label": d.module.label, "decision": dname, "target": table["target"],
            "yaml": yaml.safe_dump(d.module.to_dict(), allow_unicode=True, sort_keys=False, default_flow_style=None,
                                   width=110),
            "inputs": [{"name": k, **v} for k, v in (table.get("inputs") or {}).items()],
            "rules": [{"id": r.get("id"), "when": r.get("when") or {}, "then": r.get("then") or {},
                       "cite": r.get("cite", "")} for r in table.get("rules") or []],
            "issues": d.issues, "attempts": len(d.attempts), "late": late})

    # ---- decisions and actions -------------------------------------------------------------------------------

    def keys(self, type_name: str) -> list[dict]:
        o = self.studio.onto
        t = o.obj(type_name)
        names = all_props(o, type_name)
        show = [t.key] + [p for p in [t.title, t.states.property if t.states else ""] if p and p != t.key]
        show += [p for p in names if find_prop(o, type_name, p).type in ("datetime", "date") and p not in show][:1]
        show += [p for p in names if p.endswith("_id") and p not in show][:1]
        q = Query(nodes={"x": type_name}, columns=[Column(Ref("x", p), p) for p in show])
        rows = self.studio.run(q).rows
        out = [{"key": str(r[0]), "fields": {p: plain(v) for p, v in zip(show[1:], r[1:])}} for r in rows]
        return sorted(out, key=lambda x: x["key"])

    def _said(self, outs: dict) -> list[dict]:
        """A decision that answers with a message code shows the message a dictionary module holds for it."""
        comp = self.studio.composition
        by_code = {m.get("code"): m for m in (comp.messages if comp else [])}
        return [by_code[v] for v in outs.values() if isinstance(v, str) and v in by_code]

    def decide(self, name: str, key: str) -> dict:
        from xgen_space.decide.words import cell_words, input_label, labels_of, unit_of, verdict

        st = self.studio
        table = st.onto.decisions[name]
        res = st.decide(name, key)
        outs = res.outputs if isinstance(res.outputs, dict) else {"result": res.outputs}
        collected = table.hit_policy == "collect"  # every rule that applies: the list is the answer
        picked = res.outputs if isinstance(res.outputs, list) else []
        zen = None
        if _has_zen():
            try:
                from xgen_space.decide.zen import evaluate_zen

                z = evaluate_zen(table, res.inputs)
                zen = {"outputs": plain(z), "same": plain(z) == plain(res.outputs)}
            except Exception as e:
                zen = {"error": f"{type(e).__name__}: {e}"}
        first = next(iter(table.outputs), "")
        named = table.named
        words = {i: {"unit": unit_of(st.onto, table, i), "labels": labels_of(st.onto, table, i)} for i in table.inputs}
        rules = [{"id": r.id, "when": r.when, "then": r.then, "cite": r.cite, "hit": r.id in res.matched,
                  "said": {i: cell_words(r.when.get(i, "-"), named, **words[i]) for i in table.inputs}}
                 for r in table.rules]
        comp = st.composition
        touched = comp.touched.get(f"decision:{name}", []) if comp else []
        evidence = []
        for e in res.evidence:
            prop = find_prop(st.onto, e.object_type, e.property) if e.object_type and e.property else None
            evidence.append({"input": e.input, "value": e.value, "object": e.object_type,
                             "object_label": self._obj_label(e.object_type), "key": e.key, "property": e.property,
                             "property_label": prop.label if prop else "", "source": e.source})
        actions = [a.name for a in st.onto.actions.values() if any(c.decision == name for c in a.criteria)]
        return plain({
            "name": name, "label": table.label or name, "target": table.target,
            "target_label": self._obj_label(table.target), "key": key, "hit_policy": table.hit_policy,
            "inputs": list(table.inputs), "outputs": list(table.outputs), "result": outs,
            "input_labels": {i: input_label(st.onto, table, i) for i in table.inputs},
            "overridden": res.overridden, "parameters": res.parameters, "conflicts": res.conflicts,
            "yes": bool(picked) if collected else (verdict(table, outs)[1] if first else False),
            "verdict": ("가능" if picked else "불가") if collected else verdict(table, outs)[0],
            "reason": " · ".join(str(x.get("name") or x.get("code") or x) if isinstance(x, dict) else str(x) for x in picked)
            if collected else next((v for v in outs.values() if isinstance(v, str)), ""),
            "matched": res.matched, "rules": rules, "values": res.inputs, "evidence": evidence,
            "messages": self._said(outs),
            "engine": res.engine, "zen": zen, "notes": res.notes,
            "touched": [self._label(m) for m in touched], "actions": actions,
        })

    def _proposal(self, p) -> dict:
        st = self.studio
        a = st.onto.actions.get(p.action)
        checks = []
        for c in p.checks:
            detail = c.detail
            if c.name.startswith("decision:"):
                d = st.onto.decisions.get(c.name.split(":", 1)[1])
                title = f"판정 · {d.label if d else c.name}"
                try:  # the outputs as they were when the request was checked
                    res = ast.literal_eval(c.detail)
                except (ValueError, SyntaxError):
                    res = None
                detail = ", ".join(f"{k} {_word(v)}" for k, v in res.items()) if isinstance(res, dict) else c.detail
            elif c.name == "role":
                labels = [st.onto.roles[r].label or r for r in p.requested_by.roles if r in st.onto.roles]
                detail = ", ".join(labels) if c.passed else f"{', '.join(labels) or '역할 없음'} 역할에 요청 권한이 없습니다"
                title = CHECK_LABEL[c.name]
            elif c.name == "target":
                detail = f"{self._obj_label(p.target)} {p.key}"
                title = CHECK_LABEL[c.name]
            elif c.name == "parameters":
                detail = ", ".join(f"{k} {v}" for k, v in p.params.items()) if c.passed else c.detail
                title = CHECK_LABEL[c.name]
            else:
                detail = c.detail.replace("->", "→")
                title = CHECK_LABEL.get(c.name, c.name)
            checks.append({"name": c.name, "title": title, "passed": c.passed, "detail": detail})
        labels = {k: (v.get("label") if isinstance(v, dict) else "") or k for k, v in (a.parameters if a else {}).items()}
        target = st.onto.objects.get(p.target)
        labels.update({k: x.label for k, x in (target.properties if target else {}).items() if x.label and k in p.changes})
        inside = bool(p.limits) and all(x["within"] for x in p.limits)
        waits = ""  # why a request inside its limits still waits for a person
        if p.status == "pending" and inside and a is not None:
            waits = "agent" if p.requested_by.kind != "human" and not a.auto_agents else "right"
        return plain({"id": p.id, "action": p.action, "label": a.label if a else p.action, "target": p.target, "labels": labels,
                      "waits": waits,
                      "target_label": self._obj_label(p.target), "key": p.key, "params": p.params,
                      "requested_by": p.requested_by.id, "requested_kind": p.requested_by.kind, "status": p.status, "checks": checks,
                      "changes": p.changes, "before": p.before, "approved_by": p.approved_by, "call": p.call,
                      "limits": p.limits, "rolled_back_by": p.rolled_back_by, "can_roll_back": p.status == "executed" and (
                          not (a and a.call) or bool(a and a.undo))})

    def request(self, action: str, key: str, params: dict, role: str, principal: dict | None = None, *,
                kind: str = "agent") -> dict:
        """A request from this page, as an agent under a role or as the person signed in, acting in that role."""
        label = self.studio.onto.roles[role].label or role if role else "Agent"
        who = label if kind == "agent" else self.who
        actor = Actor(who, kind, [role] if role else [], principal=principal or {})
        p = self.studio.actions.request(action, key, params, actor=actor)
        if p.status == "executed":  # inside its limits it ran at once
            self._reproject()
        state = {"pending": "승인 대기 중입니다.", "executed": "자동 승인 기준을 충족해 실행했습니다."}.get(p.status, "검사를 통과하지 못해 반려되었습니다.")
        self._note("request", f"요청 접수: {actor.id}, {self._obj_label(p.target)} {key} {self._proposal(p)['label']}. "
                   f"{state}")
        return {"ok": True, "proposal": self._proposal(p)}

    def _approver(self) -> Actor:
        approver_role = next((r.name for r in self.studio.onto.roles.values()
                              if any(r.can("execute", a) for a in self.studio.onto.actions)), "")
        return Actor(self.who if self.who != "방문자" else "운영자", "human", [approver_role] if approver_role else [])

    def rollback(self, proposal_id: str) -> dict:
        from xgen_space.actions import ActionError

        try:
            p = self.studio.actions.rollback(proposal_id, actor=self._approver(), reason="화면에서 되돌림")
        except (ActionError, PermissionError) as e:
            return {"ok": False, "error": f"되돌릴 수 없는 상태라 되돌리지 못했습니다. {e}"}
        proj = self._reproject()
        self._note("approve", f"요청 {p.id}: 실행 전 값으로 되돌렸습니다.", projection=proj)
        return {"ok": True, "proposal": self._proposal(p), "projection": proj}

    def pending_actions(self) -> dict:
        """Requests waiting for a person, whoever asked: this page, another person, a platform or an agent; and the
        latest that ran, so one can still be rolled back after the page that approved it is gone."""
        props = list(self.studio.actions.proposals.values())
        ran = [p for p in props if p.status in ("executed", "rolled_back", "failed")][-10:]
        return {"pending": [self._proposal(p) for p in props if p.status == "pending"],
                "done": [self._proposal(p) for p in reversed(ran)]}

    def approve(self, proposal_id: str, approve: bool) -> dict:
        from xgen_space.actions import Refused, Settled

        approver = self._approver()
        acts = self.studio.actions
        verb = "승인" if approve else "반려"
        try:
            p = acts.approve(proposal_id, approver=approver) if approve else \
                acts.reject(proposal_id, approver=approver, reason="운영자 반려")
        except Refused as e:
            why = {"self": f"요청한 사람은 자기 요청을 {verb}할 수 없어 처리하지 못했습니다. 다른 승인 권한자에게 {verb}을 요청해 주세요.",
                   "right": f"실행 권한이 있는 역할이 없어 {verb}하지 못했습니다. 권한 관리에서 이 액션의 실행 권한을 확인해 주세요.",
                   "scope": f"대상 행이 승인자의 조회 범위 밖이라 {verb}하지 못했습니다. 이 행을 조회할 수 있는 승인자에게 요청해 주세요."}
            return {"ok": False, "error": why.get(e.code, f"{verb} 권한이 없어 처리하지 못했습니다. {e}")}
        except Settled as e:
            if e.code == "ran":
                return {"ok": False, "error": "이미 실행된 요청이라 반려하지 못했습니다. 되돌리기로 실행 전 값으로 복원해 주세요."}
            word = STATUS_WORD.get(e.code, e.code)
            return {"ok": False, "error": f"이미 {word} 상태인 요청이라 {verb}하지 못했습니다. 화면을 새로 고쳐 현재 상태를 확인해 주세요."}
        except KeyError:
            return {"ok": False, "error": "요청을 찾을 수 없어 처리하지 못했습니다. 화면을 새로 고쳐 다시 시도해 주세요."}
        except (PermissionError, ValueError, RuntimeError) as e:
            return {"ok": False, "error": str(e)}
        proj = self._reproject() if p.status == "executed" else {}
        verb = {"executed": "승인 후 원천 DB에 반영했습니다", "failed": "외부 호출이 실패해 원천 DB를 실행 전 값으로 복원했습니다"
                }.get(p.status, "반려했습니다")
        self._note("approve", f"요청 {p.id}: {verb}.", projection=proj)
        return {"ok": True, "proposal": self._proposal(p), "projection": proj}

    def function_run(self, name: str, key: str, params: dict) -> dict:
        """Try a function on one object. A draft runs here and nowhere else. An input left empty takes its default."""
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        f = self.studio.onto.functions.get(name)
        if f is not None and f.target and key and self.studio.fetch(f.target, key) is None:
            return {"ok": False, "error": f"{self._obj_label(f.target)} {key}을(를) 찾을 수 없어 실행하지 못했습니다. 번호를 확인해 주세요."}
        try:
            return {"ok": True, **plain(self.studio.function(name, key or None, params, by=self.who, trial=True))}
        except (ValueError, KeyError, PermissionError, OSError) as e:  # the page says it where the result would be
            return {"ok": False, "error": said(e)}

    def function_log(self) -> dict:
        return {"log": plain(list(reversed(self.studio.function_log)))}

    def value_state(self) -> dict:
        """What the ontology answers against what the transaction system shows, with the condition it is held to."""
        specs = self.studio.flow.values
        if not specs:
            return {"ok": True, "configured": False, "items": []}
        try:
            out = self.studio.value_accuracy(specs)
        except Exception as e:  # a query that no longer runs or a service that does not answer: what the page should say
            return {"ok": False, "configured": True, "error": said(e), "items": []}
        return {"ok": True, "configured": True, "limit": (self.studio.flow.gates.get("check") or {}).get("max_value_errors"), **plain(out)}

    def audit(self) -> list[dict]:
        return [{"at": a.at, "actor": a.actor, "kind": a.actor_kind, "event": EVENT_LABEL.get(a.event, a.event),
                 "proposal": a.proposal, "key": a.key, "target": a.target, "action": a.action, "detail": plain(a.detail),
                 "versions": a.versions}
                for a in reversed(self.studio.actions.audit)]

    # ---- data in: files or a database, drafted into modules, plugged in ---------------------------------------

    def _sample_files(self) -> list[Path]:
        d = self.data.samples
        if d is None or not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix.lower() in (".csv", ".tsv", ".xlsx"))

    def files_state(self) -> dict:
        self._hold()
        lim = self.data
        files = [{"source": src, "bytes": self.sizes.get(src, 0),
                  "tables": [{"name": t.name, "sheet": t.source, "rows": len(t.rows), "columns": t.columns,
                              "truncated": t.truncated, "preview": t.rows[:5]} for t in ts]}
                 for src, ts in self.uploads.items()]
        defs = [{"source": src, "bytes": self.sizes.get(src, 0), **d.counts(),
                 "tables": [{"name": t.name, "label": t.label, "columns": len(t.columns), "key": t.primary_key}
                            for t in list(d.tables.values())[:600]],
                 "groups": [{"name": g.name, "label": g.label, "values": len(g.values)}
                            for g in list(d.codes.values())[:600]],
                 "terms": len(d.terms), "messages": len(d.messages), "documents": len(d.documents),
                 "term_list": [{"term": t["term"], "synonyms": len(t["synonyms"])} for t in d.terms[:600]],
                 "message_list": [{"code": m["code"], "chars": len(m["text"])} for m in d.messages[:600]],
                 "document_list": [{"name": x["name"], "kind": x["kind"], "sections": len(x["sections"]),
                                    "chars": len(x["text"])} for x in d.documents[:600]]}
                for src, d in self.definitions.items()]
        from xgen_space.draft import DraftRules

        base = DraftRules.from_dict(self._method_rules())  # an attached method module's rules, or the defaults
        rules = self.pending[3] if self.pending else base
        comp = self.studio.composition
        return plain({"files": files, "definitions": defs, "pending": self._draft_view() if self.pending else None,
                      "rules": rules.to_dict(), "defaults": base.to_dict(),
                      "rules_by": [self._label(m) for m in (comp.rules_by if comp else [])],
                      "limits": {"file_bytes": lim.file_bytes, "total_bytes": lim.total_bytes, "files": lim.files,
                                 "rows": lim.rows, "columns": lim.columns},
                      "samples": [p.name for p in self._sample_files()], "connect": lim.allow_connect})

    def _read(self, source: str, data: bytes) -> tuple[list, Any]:
        """What a file holds: its tables, or its definitions. ValueError says why it could not be read."""
        from xgen_space.draft import ReadError, read_file

        lim = self.data
        from xgen_space.definitions import from_sheets, header_row
        from xgen_space.ingest import EXPORT_ANY, IngestError, ingest, is_sheet

        if not is_sheet(data, source):  # everything but rows rolls up into the one definitions object
            try:
                return [], ingest(data, source)
            except IngestError as e:
                if e.reason == "format" and source.lower().endswith(".json"):
                    raise ValueError(f"{source}: tables 또는 codes 항목이 없어 정의서로 읽지 못했습니다. "
                                     "테이블 정의서 · 코드 정의서 JSON 인지 확인해 주세요.") from None
                text = INGEST_ERROR.get(e.reason, INGEST_ERROR["format"])
                raise ValueError(f"{source}: " + text.format(export_to=e.info.get("export_to", EXPORT_ANY))) from None
        try:
            tables = read_file(data, source, max_rows=lim.rows, header=header_row)
        except ReadError as e:
            raise ValueError(f"{source}: " + READ_ERROR.get(
                e.reason, "파일을 테이블로 읽지 못했습니다. 파일 형식을 확인해 주세요.")) from None
        sheets = [t for t in tables if from_sheets([t]) is not None]  # definition sheets, not data
        if sheets:  # a definition workbook's cover and revision sheets are not data
            return [], from_sheets(sheets, source)
        wide = [t.name for t in tables if len(t.columns) > lim.columns]
        if wide:
            raise ValueError(f"{', '.join(wide)}: 컬럼 수가 {lim.columns}개 한도를 초과해 업로드하지 못했습니다. "
                             "컬럼을 줄여 다시 업로드해 주세요.")
        return tables, None

    def _room(self, path: str, size: int) -> None:
        """Refuse a file past the limits; a file replacing one at the same path takes that one's place."""
        lim = self.data
        name = path.rsplit("/", 1)[-1]
        if size > lim.file_bytes:
            raise ValueError(f"{name}: 파일 크기가 {_size(lim.file_bytes)} 한도를 초과해 업로드하지 못했습니다. "
                             "파일을 나누어 다시 업로드해 주세요.")
        files, total = self.repositories.usage()
        before = self.repositories.files(self.repo).get(path)
        if before is None and files >= lim.files:
            raise ValueError(f"업로드 파일 수가 {lim.files}개 한도에 도달해 추가하지 못했습니다. "
                             "파일을 삭제하고 휴지통을 비운 뒤 다시 업로드해 주세요.")
        if total - (before["bytes"] if before else 0) + size > lim.total_bytes:
            raise ValueError(f"전체 업로드 용량이 {_size(lim.total_bytes)} 한도를 초과해 업로드하지 못했습니다. "
                             "파일을 삭제하고 휴지통을 비운 뒤 다시 업로드해 주세요.")

    def _keep(self, path: str, data: bytes, tables: list, defs: Any, error: str = "") -> None:
        """A file goes into the repository, and what was read from it into the next draft."""
        f = self.repositories.put(self.repo, path, data, facts=_facts(tables, defs), error=error)
        self._release(path)
        if f["included"] and not error:
            self._take(path, f, tables, defs)
        self.pending = None

    def _take(self, path: str, f: dict, tables: list, defs: Any) -> None:
        if tables:
            self.uploads[path] = tables
        if defs is not None:
            self.definitions[path] = defs
        self.sizes[path] = f["bytes"]
        self._held[path] = f["sha256"]

    def _release(self, path: str) -> None:
        self.uploads.pop(path, None)
        self.definitions.pop(path, None)
        self.sizes.pop(path, None)
        self._held.pop(path, None)

    def _hold(self) -> None:
        """Bring what the next draft reads in line with the files going into it: after a switch of repository, a file
        left out or taken back, or a server started on repositories it kept."""
        wanted = {p: f for p, f in self.repositories.files(self.repo).items()
                  if f["included"] and not f.get("error") and (f.get("facts") or {}).get("kind") != "raw"}
        stale = [p for p, sha in self._held.items() if p not in wanted or wanted[p]["sha256"] != sha]
        fresh = [p for p in wanted if p not in self._held or p in stale]
        for p in stale:
            self._release(p)
        for p in fresh:
            f = wanted[p]
            try:
                tables, defs = self._read(p.rsplit("/", 1)[-1], self.repositories.read(self.repo, p))
            except ValueError:  # a limit that came down since: the row still says what the file is
                continue
            self._take(p, f, tables, defs)
        if stale or fresh:
            self.pending = None

    def upload(self, source: str, data: bytes) -> dict:
        """A file into the top of the repository, which must be readable; the page brings files by catalog_upload."""
        name = Path(source.replace("\\", "/")).name[:120] or "file.csv"
        self._room(name, len(data))
        tables, defs = self._read(name, data)
        self._keep(name, data, tables, defs)
        return self.files_state()

    def use_samples(self) -> dict:
        files = self._sample_files()
        if not files:
            raise ValueError("샘플 데이터가 설정되지 않아 불러오지 못했습니다.")
        for p in files:
            self.upload(p.name, p.read_bytes())
        return self.files_state()

    def remove_file(self, source: str) -> dict:
        self.catalog_remove([source])
        return self.files_state()

    # ---- pipelines: each applied draft kept beside the ones before it -----------------------------------------

    def _stash(self) -> None:
        """Write what the current pipeline has come to back to its entry."""
        cur = next(p for p in self.pipelines if p["id"] == self.pipeline)
        cur.update(studio=self.studio, origin=self.origin, rows=self._library_rows, log=self.log)

    def _make_room(self, label: str) -> None:
        if len(self.pipelines) >= PIPELINES_MAX and not any(p["label"] == label for p in self.pipelines[1:]):
            raise ValueError(f"파이프라인 수가 {PIPELINES_MAX}개 한도에 도달해 적용하지 못했습니다. "
                             "파이프라인을 삭제한 뒤 다시 적용해 주세요.")

    def _new_pipeline(self, label: str) -> None:
        """What was just applied becomes a pipeline; applied again under its name, it takes that one's place."""
        same = next((p for p in self.pipelines[1:] if p["label"] == label), None)
        pid = same["id"] if same else f"p{1 + max(int(p['id'][1:]) for p in self.pipelines)}"
        entry = {"id": pid, "label": label, "studio": self.studio, "origin": self.origin, "rows": self._library_rows,
                 "log": self.log}
        if same:
            self.pipelines[self.pipelines.index(same)] = entry
        else:
            self.pipelines.append(entry)
        self.pipeline = pid
        self.save_pipelines()

    def pipeline_use(self, pid: str) -> dict:
        target = next((p for p in self.pipelines if p["id"] == pid), None)
        if target is None:
            raise LookupError(f"파이프라인 {pid}")
        self._stash()
        self._adopt(target["studio"])
        self.origin, self._library_rows, self.log = target["origin"], target["rows"], target["log"]
        self.pipeline, self.pending, self.workspace, self._ws_sig = pid, None, None, ()
        self.event("pipeline", f"{target['label']}(으)로 전환")
        return {"ok": True}

    def pipeline_delete(self, pid: str) -> dict:
        if pid == "p1":
            raise ValueError("기본 파이프라인은 삭제할 수 없습니다.")
        if pid == self.pipeline:
            self.pipeline_use("p1")
        self.pipelines = [p for p in self.pipelines if p["id"] != pid]
        self.save_pipelines()
        return {"ok": True}

    # ---- the control board: the pipeline measured, floor by floor ---------------------------------------------

    def _monitor_sig(self) -> tuple:
        """What has to change for the board to measure again before its time."""
        st = self.studio
        comp = st.composition
        return (id(st), tuple((m.name, m.version) for m in comp.modules) if comp else (), self.repo,
                tuple(f["sha256"] for f in self.repositories.files(self.repo).values()), tuple(self.space.stores),
                id(self.log[0]) if self.log else 0, sum(c.status == "pending" for c in st.changes.requests.values()))

    def _watched(self) -> tuple[dict, bool]:
        """The last measurement, taken again when something changed or a while has passed; whether it is new."""
        from xgen_space.web.monitor import failed

        sig, now = self._monitor_sig(), time.time()
        w = self._watch
        fresh = w is None or w["sig"] != sig or now - w["at"] >= MONITOR_EVERY
        if fresh:
            started = time.perf_counter()
            flow = self.flow()
            bind = next(s for s in flow["steps"] if s["id"] == "bind")
            findings = self.bindings()["findings"] if failed(bind) else []
            took = round((time.perf_counter() - started) * 1000)
            w = self._watch = {"sig": sig, "at": now, "flow": flow, "findings": findings, "took": took, "measured": self._measured,
                               "stamp": datetime.now().isoformat(timespec="seconds")}
            gates = [g for s in flow["steps"] for g in s["gates"]]
            self.event("measure", f"파이프라인 점검 완료 · 통과 조건 {sum(g['passed'] for g in gates)} / {len(gates)} 충족")
        return w, fresh

    def _issues(self, w: dict, *, changes: int, actions: int, dirty: bool) -> list[dict]:
        """What is wrong as things stand: built once per measurement, with what waits on a person read every time."""
        from xgen_space.web import issues

        if "built" not in w:
            w["built"] = plain(issues.build(self, w))
        out = [*w["built"], *plain(issues.waiting(self, dirty=dirty, changes=changes, actions=actions))]
        self._track_issues(out)
        return sorted(out, key=lambda x: (x["level"] != "bad", not x["members"]))

    def _track_issues(self, issues: list[dict]) -> None:
        """When each issue opened and closed, in the journal so a restart still knows how long it has been open."""
        journal = self.studio.changes.journal
        if self._issue_open is None:
            self._issue_open = {}
            for r in journal.read() if journal is not None else []:
                if r.get("kind") == "issue" and r.get("event") == "open":
                    self._issue_open[r["id"]] = {"at": r.get("at", ""), "title": r.get("title", "")}
                elif r.get("kind") == "issue":
                    self._issue_open.pop(r.get("id"), None)
        now = datetime.now().isoformat(timespec="seconds")
        here = {x["id"] for x in issues if not x["direct"]}
        for x in issues:
            if x["direct"]:
                continue
            if x["id"] not in self._issue_open:
                self._issue_open[x["id"]] = {"at": now, "title": x["title"]}
                if journal is not None:
                    journal.write("issue", {"event": "open", "id": x["id"], "at": now, "title": x["title"], "level": x["level"]})
            x["since"] = self._issue_open[x["id"]]["at"]
        for gone in [k for k in self._issue_open if k not in here]:
            if journal is not None:
                journal.write("issue", {"event": "resolved", "id": gone, "at": now, "title": self._issue_open[gone]["title"]})
            self.event("issue", f"해결됨 · {self._issue_open[gone]['title']}")
            del self._issue_open[gone]

    def issues(self) -> dict:
        """What is wrong right now and how to fix it, for every page that says so."""
        st = self.studio
        w, _ = self._watched()
        gates = [g for s in w["flow"]["steps"] for g in s["gates"]]
        return plain({"issues": self._issues(w, changes=sum(c.status == "pending" for c in st.changes.requests.values()),
                                             actions=sum(p.status == "pending" for p in st.actions.proposals.values()),
                                             dirty=bool(self.workspace and self.workspace.dirty)),
                      "measured_at": w["stamp"], "gates": {"met": sum(g["passed"] for g in gates), "all": len(gates)}})

    def module_preview(self, name: str) -> dict:
        """What taking a module off would do, tried on a copy before it is done."""
        from xgen_space.review import gates, measure, trial

        st = self.studio
        imp = st.detach_impact(name)
        out = {"module": name, "label": self._label(name), "impact": imp.to_dict(), "removed": [self._element_label(x) for x in imp.removed]}
        if imp.ok and st.composition is not None:
            try:
                copy = trial(st, [m for m in st.composition.modules if m.name != name], st.flow)
                results = gates(measure(copy, copy.flow), copy.flow)
                out["gates"] = {"met": sum(g.passed for g in results), "all": len(results), "failed": [g.condition for g in results if not g.passed]}
            except Exception as e:  # a copy that cannot be measured: the page says what would be removed and no more
                out["error"] = str(e)
        return plain(out)

    def monitor(self) -> dict:
        """The board: measured when something changed or a while has passed, and read at every look."""
        from xgen_space.web.monitor import board

        w, fresh = self._watched()
        st = self.studio
        comp = st.composition
        on = {m.name for m in comp.modules} if comp else set()
        faults = [{"label": str(f.get("label", "")), "module": str(f.get("attach", "")), "on": f.get("attach") in on}
                  for f in (getattr(st, "settings", {}).get("monitor") or {}).get("faults") or []
                  if any(r["name"] == f.get("attach") for r in self._library_rows)]

        def owner(element: str) -> str:
            return self._label(comp.owner(element)) if comp else ""

        changes = sum(c.status == "pending" for c in st.changes.requests.values())
        actions = sum(p.status == "pending" for p in st.actions.proposals.values())
        dirty = bool(self.workspace and self.workspace.dirty)
        out = board(w["flow"], files=self.repositories.files(self.repo), onto=st.onto, owner_label=owner,
                    reasoners=[r.name for r in st.reasoners.values()], graphs=[{"name": n, "language": b.capabilities.language}
                                                                                for n, b in st.backends.items() if b.capabilities.load],
                    modules=[], findings=w["findings"], faults=faults, changes=changes, actions=actions, dirty=dirty)
        out["issues"] = [x for x in self._issues(w, changes=changes, actions=actions, dirty=dirty) if x["alert"]]
        return plain({**out, "now": datetime.now().isoformat(timespec="seconds"), "measured_at": w["stamp"],
                      "measured": fresh, "took": w["took"], "events": list(self.events)[:12],
                      "repository": self._repository_row()["label"], "notice": self.origin.get("notice", "")})

    # ---- the catalog: repositories, folders and files, each with what it turned out to be ---------------------

    def _repository_row(self) -> dict:
        return next(r for r in self.repositories.rows() if r["id"] == self.repo)

    def catalog_state(self, folder: str = "") -> dict:
        folder = clean_path(folder)
        folders, files = self.repositories.listing(self.repo, folder)
        lim = self.data
        count, total = self.repositories.usage()
        everything = self.repositories.files(self.repo)
        index = self._index_of()
        return plain({"repository": self._repository_row(), "repositories": self.repositories.rows(), "folder": folder,
                      "folders": folders, "files": [{**f, "ext": Path(f["name"]).suffix.lower().lstrip("."), "index": index.get(f["path"])}
                                                    for f in files],
                      "included": sum(1 for f in everything.values() if f["included"] and not f.get("error")
                                      and (f.get("facts") or {}).get("kind") != "raw"),
                      "unread": sum(1 for f in everything.values() if f.get("error")),
                      "limits": {"file_bytes": lim.file_bytes, "total_bytes": lim.total_bytes, "files": lim.files,
                                 "used_files": count, "used_bytes": total},
                      "samples": bool(self._sample_files()), "server_paths": lim.allow_connect,
                      "persistent": self.repositories.persistent})

    def catalog_upload(self, path: str, data: bytes) -> dict:
        """A file into its folder. One that cannot be read is kept too, with the reason, as raw material is."""
        path = clean_path(path)
        if not path:
            raise ValueError("파일 이름이 없어 업로드하지 못했습니다. 파일을 다시 선택해 주세요.")
        if is_litter(path):
            return {"ok": True, "skipped": True}
        self._room(path, len(data))
        name = path.rsplit("/", 1)[-1]
        if Path(name).suffix.lower() in RAW_FILES:  # kept as it is: nothing to read into a draft
            self.repositories.put(self.repo, path, data, facts={"kind": "raw"}, error="")
            self._release(path)
            self.event("upload", f"파일 업로드 · {name}")
            return {"ok": True, "skipped": False}
        try:
            tables, defs = self._read(name, data)
            self._keep(path, data, tables, defs)
        except ValueError as e:
            self._keep(path, data, [], None, str(e).removeprefix(name + ": "))
        self.event("upload", f"파일 업로드 · {name}")
        return {"ok": True, "skipped": False}

    def catalog_folder(self, path: str) -> dict:
        path = clean_path(path)
        if not path:
            raise ValueError("이름이 없어 폴더를 만들지 못했습니다. 폴더 이름을 입력해 주세요.")
        self.repositories.folder(self.repo, path)
        return {"ok": True}

    def catalog_remove(self, paths: list) -> dict:
        gone = self.repositories.remove(self.repo, [clean_path(p) for p in paths])
        for p in gone:
            if p in self._held:
                self.pending = None
            self._release(p)
        return {"ok": True, "removed": len(gone)}

    def catalog_rename(self, path: str, name: str) -> dict:
        path, name = clean_path(path), clean_path(name)
        if not name or "/" in name:
            raise ValueError("이름을 확인할 수 없어 바꾸지 못했습니다. 슬래시 없이 이름을 입력해 주세요.")
        folder = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
        self.repositories.move(self.repo, path, folder + name)
        self._hold()  # a table takes its name from its file: what was read under the old path is read again
        return {"ok": True}

    def catalog_include(self, paths: list, on: bool) -> dict:
        self.repositories.include(self.repo, [clean_path(p) for p in paths], on)
        self._hold()
        return {"ok": True}

    def catalog_embed(self, paths: list, on: bool) -> dict:
        """Embed the documents of files, or of everything in folders, into the vector stores, or take them out. They stay in
        the draft and in the document ontology either way."""
        self.repositories.embed(self.repo, [clean_path(p) for p in paths], on)
        self._sync_space()
        r = self.space.index()
        if r.get("embed_error"):
            raise ValueError(f"문서를 임베딩하지 못했습니다. {r['embed_error']}")
        return {"ok": True}

    def _index_of(self) -> dict[str, dict]:
        """Each file's documents as the vector stores hold them: embedded, off, waiting or failed, with passage counts."""
        self._sync_space()
        self.space.index()
        rows = {r["name"]: r for r in self.space.document_rows()}
        out = {}
        for path, defs in self.definitions.items():
            mine = [rows[d["name"]] for d in (getattr(defs, "documents", None) or [])
                    if d["name"] in rows and rows[d["name"]]["path"] == path and rows[d["name"]]["state"] != "none"]
            if not mine:
                continue
            states = {r["state"] for r in mine}
            state = "off" if states == {"off"} else next((s for s in ("failed", "pending") if s in states), "embedded")
            out[path] = {"state": state, "chunks": sum(r["indexed"] for r in mine), "passages": sum(r["passages"] for r in mine)}
        return out

    def catalog_move(self, paths: list, folder: str) -> dict:
        """Files and folders into another folder of the repository, keeping their names."""
        folder = clean_path(folder)
        for p in [clean_path(p) for p in paths]:
            name = p.rsplit("/", 1)[-1]
            if p != (folder + "/" if folder else "") + name:
                self.repositories.move(self.repo, p, (folder + "/" if folder else "") + name)
        self._hold()
        return {"ok": True}

    def catalog_trash(self) -> dict:
        return {"items": self.repositories.trash(self.repo)}

    def catalog_trash_op(self, op: str, ids: list) -> dict:
        """Put trashed items back, or delete them for good; without ids, the whole trash goes."""
        ids = [str(i) for i in ids or []]
        if op == "restore":
            items = sum(t["id"] in ids for t in self.repositories.trash(self.repo))
            back = self.repositories.restore(self.repo, ids)
            self._hold()  # what came back goes into the next draft as it did before
            return {"ok": True, "restored": len(back), "items": items}
        if op == "purge":
            return {"ok": True, "purged": self.repositories.purge(self.repo, ids or None)}
        raise ValueError("요청 형식이 올바르지 않아 처리하지 못했습니다.")

    def catalog_history(self) -> dict:
        return {"items": self.repositories.history(self.repo)}

    def catalog_repository(self, op: str, repo: str = "", label: str = "") -> dict:
        if op == "create":
            self.repo = self.repositories.create(label)
        elif op == "use":
            self.repositories.files(repo)  # a repository that went from under this visitor says so
            self.repo = repo
        elif op == "rename":
            self.repositories.rename_repo(repo or self.repo, label)
        elif op == "delete":
            self.repositories.delete_repo(repo or self.repo)
            if self.repo == (repo or self.repo):
                self.repo = next(iter(self.repositories.items))
        else:
            raise ValueError("요청 형식이 올바르지 않아 처리하지 못했습니다.")
        self._hold()
        return {"ok": True}

    def catalog_file(self, path: str) -> dict:
        """One file: what is known of it, its first rows or its sections, and its share of the one JSON."""
        path = clean_path(path)
        f = self.repositories.entry(self.repo, path)
        name = path.rsplit("/", 1)[-1]
        out = {"path": path, "name": name, **f, "tables": [], "sections": [], "json": ""}
        if f.get("error") or (f.get("facts") or {}).get("kind") == "raw":
            return plain(out)
        tables, defs = self._read(name, self.repositories.read(self.repo, path))
        out["tables"] = [{"name": t.name, "sheet": t.source, "rows": len(t.rows), "columns": t.columns,
                          "preview": t.rows[:8]} for t in tables]
        docs = defs.documents if defs is not None else []
        out["sections"] = [{"document": d["name"], "title": x.get("title", ""), "chars": len(x.get("text", ""))}
                           for d in docs for x in d.get("sections") or []][:200]
        out["json"] = _json_text(_as_definitions(name, tables, defs).to_dict())[:JSON_PREVIEW]
        return plain(out)

    def _one_definitions(self):
        """Everything going into a draft as the one definitions object."""
        self._hold()
        out = None
        for path in self._held:
            d = _as_definitions(path, self.uploads.get(path, []), self.definitions.get(path))
            out = d if out is None else out.merge(d)
        return out

    def catalog_convert(self) -> dict:
        """What the files came to: a row for each, and the one JSON they roll up into."""
        files = self.repositories.files(self.repo)
        one = self._one_definitions()
        text = _json_text(one.to_dict()) if one is not None else ""
        return plain({"repository": self._repository_row(), "bytes": len(text.encode("utf-8")),
                      "rows": [{"path": p, "bytes": f["bytes"], "included": f["included"], "facts": f.get("facts") or {},
                                "error": f.get("error", "")} for p, f in files.items()],
                      "counts": one.counts() if one is not None else {}, "json": text[:JSON_PREVIEW],
                      "cut": len(text) > JSON_PREVIEW})

    def catalog_download(self, path: str) -> tuple:
        path = clean_path(path)
        return 200, self.repositories.read(self.repo, path), "application/octet-stream", path.rsplit("/", 1)[-1]

    def catalog_json(self) -> tuple:
        one = self._one_definitions()
        if one is None:
            raise ValueError("초안에 포함한 파일이 없어 JSON을 만들지 못했습니다. 파일을 업로드해 주세요.")
        name = self._repository_row()["label"]
        return 200, _json_text(one.to_dict()).encode("utf-8"), "application/json; charset=utf-8", f"{name}.json"

    def catalog_import(self, path: str, folder: str = "") -> dict:
        """A folder or a file on the server, its structure kept, for installs that allow the server's disk."""
        if not self.data.allow_connect:
            raise PermissionError("공개 데모에서는 서버 경로 가져오기가 비활성화되어 있어 처리하지 못했습니다. 파일 업로드를 이용해 주세요.")
        typed = str(path).strip().strip('"')
        if not typed:
            raise ValueError("경로가 없어 가져오지 못했습니다. 서버에 있는 파일 또는 폴더 경로를 입력해 주세요.")
        src, folder = Path(typed), clean_path(folder)
        if not src.exists():
            raise ValueError("경로를 찾을 수 없어 가져오지 못했습니다. 서버에 있는 파일 또는 폴더 경로를 입력해 주세요.")
        found = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        done = 0
        for p in found:
            rel = p.name if src.is_file() else f"{src.name}/{p.relative_to(src).as_posix()}"
            target = f"{folder}/{rel}" if folder else rel
            if not self.catalog_upload(target, p.read_bytes())["skipped"]:
                done += 1
        return {"ok": True, "imported": done}

    def _method_rules(self) -> dict:
        comp = self.studio.composition
        return dict(comp.draft_rules) if comp else {}

    def _rules(self, rules: dict | None):
        from xgen_space.draft import DraftRules

        try:  # what the visitor set, over an attached method module's rules
            return DraftRules.from_dict({**self._method_rules(), **(rules if isinstance(rules, dict) else {})})
        except (TypeError, ValueError):
            raise ValueError("생성 설정 값을 확인할 수 없어 초안을 생성하지 못했습니다. 숫자 항목을 확인해 주세요.") from None

    def _defs(self):
        """The uploaded definitions as one, or None."""
        out = None
        for d in self.definitions.values():
            out = d if out is None else out.merge(d)
        return out

    def make_draft(self, label: str = "", rules: dict | None = None, tables: list | None = None) -> dict:
        from xgen_space.backends.sql import SqliteBackend
        from xgen_space.draft import draft, load_sqlite

        self._hold()
        all_tables = [t for ts in self.uploads.values() for t in ts]
        defs = self._defs()
        wanted = {str(x) for x in tables} if tables else None
        if not all_tables and defs is not None and defs.tables:  # the schema alone: an empty database, keys and refs
            from xgen_space.definitions import schema_backend

            names = [t for t in defs.tables if wanted is None or t in wanted]
            if not names:
                raise ValueError("선택된 테이블이 없어 초안을 생성하지 못했습니다. 테이블을 하나 이상 선택해 주세요.")
            r = self._rules(rules)
            b = schema_backend(defs, names)
            d = draft(b, name="my-schema", label=(label or "정의서 초안")[:40], lang="ko", rules=r, definitions=defs,
                      origin={"kind": "definitions", "files": list(self.definitions),
                              "detail": f"정의서 {len(self.definitions)}개 · 테이블 {len(names)}개(행 없음)"})
            self.pending = (d, b, [], r)
            return self.files_state()
        if not all_tables and defs is not None:
            raise ValueError("테이블 정의가 없어 초안을 생성하지 못했습니다. 테이블 정의서 또는 데이터 파일을 업로드해 주세요.")
        if not all_tables:
            raise ValueError("업로드한 파일이 없어 초안을 생성하지 못했습니다. 파일을 업로드해 주세요.")
        chosen = [t for t in all_tables if wanted is None or t.name in wanted]
        if not chosen:
            raise ValueError("선택된 테이블이 없어 초안을 생성하지 못했습니다. 테이블을 하나 이상 선택해 주세요.")
        r = self._rules(rules)
        b = SqliteBackend()
        loaded = load_sqlite(chosen, b, row_keys=r.row_keys)
        d = draft(b, name="my-data", label=(label or "업로드 데이터")[:40], loaded=loaded, lang="ko", rules=r,
                  definitions=defs, origin={"kind": "files", "files": list(self.uploads), "detail": f"업로드 파일 {len(self.uploads)}개"})
        self.pending = (d, b, chosen, r)
        return self.files_state()

    def connect(self, dsn: str, label: str = "", rules: dict | None = None) -> dict:
        if not self.data.allow_connect:
            raise PermissionError("공개 데모에서는 DB 연결이 비활성화되어 있어 연결하지 못했습니다. 파일 업로드를 이용해 주세요.")

        from xgen_space.config import open_backend
        from xgen_space.draft import draft

        dsn = dsn.strip()
        u = urlparse(dsn)
        if u.scheme in ("postgres", "postgresql", "mysql", "oracle", "mssql", "sqlserver"):
            kind = {"postgresql": "postgres", "sqlserver": "mssql"}.get(u.scheme, u.scheme)
            try:  # a / ? or # in the password ends the host early, and the rest would come back as a bad port or host
                u.port  # noqa: B018
                cut = "@" in dsn[len(u.scheme) + 3 + len(u.netloc):]
            except ValueError:
                cut = True
            if cut:
                raise ValueError("연결 주소의 사용자 정보를 확인할 수 없어 연결하지 못했습니다. 비밀번호의 /, ?, #, @ 는 "
                                 "%2F 처럼 인코딩해 입력해 주세요.")
            word = {"mysql": "MySQL", "oracle": "Oracle", "postgres": "PostgreSQL", "mssql": "SQL Server"}[kind]
            where = f"{word} {u.hostname or 'localhost'}{u.path}"  # never the user or the password
            try:
                b = open_backend({"kind": kind, "dsn": dsn}, Path("."))
            except ImportError:
                raise ValueError(f"{word} 드라이버가 설치되어 있지 않아 연결하지 못했습니다. 서버에 드라이버를 설치해 주세요.") from None
            except Exception:  # what a driver says may carry the address and the password
                raise ValueError(f"{where}에 연결하지 못했습니다. 주소, 계정, 네트워크를 확인해 주세요.") from None
        else:
            path = dsn[len("sqlite:///"):] if dsn.startswith("sqlite:///") else dsn
            if not Path(path).is_file():
                raise ValueError("연결 주소를 확인할 수 없어 연결하지 못했습니다. postgresql://, mysql://, oracle://, mssql:// "
                                 "주소 또는 SQLite 파일 경로를 입력해 주세요.")
            b = open_backend({"kind": "sqlite", "path": str(Path(path).resolve())}, Path("."))
            where = f"SQLite {Path(path).name}"
        r = self._rules(rules)
        d = draft(b, name="my-db", label=(label or "연결 데이터베이스")[:40], lang="ko", rules=r,
                  definitions=self._defs(), origin={"kind": "database", "detail": where})
        self.pending = (d, b, [], r)
        return self.files_state()

    def _draft_view(self) -> dict:
        d = self.pending[0]
        return {"label": d.label, "origin": d.origin, "steps": d.steps(), "names": self._english(d), **self._revised(d)}

    def _english(self, d) -> dict:
        """An English name for each object the draft named by romanizing it: from the library's words and the
        glossaries, or nothing when a part of its name is not a known word."""
        from xgen_space.naming import english, vocabulary

        ontos = [self.studio.onto]
        names = [r["name"] for r in self.standards()["standards"]]
        if names:
            try:
                ontos.append(self._standard(names)[1])
            except ValueError:  # standards that do not compose together still leave the space's own words
                pass
        words = vocabulary(ontos, [*self._terms(), *(d.terms or [])])
        out = {}
        for o in d.objects:
            got = english(o.label, words) or english(o.table, words)
            out[o.name] = {"name": got[0], "parts": got[1]} if got else {"name": "", "parts": []}
        # 주문내역 and 주문상세 both read OrderDetail: a name two objects would share is offered to neither
        final = [out[o.name]["name"] or o.name for o in d.objects]
        for o in d.objects:
            if out[o.name]["name"] and final.count(out[o.name]["name"]) > 1:
                out[o.name] = {"name": "", "parts": []}
        return out

    def draft_table(self, table: str) -> dict:
        """One table of the draft as a person checks it: a few rows, how unique its key is, what each column holds,
        and the columns that look personal enough to hide."""
        if not self.pending:
            raise ValueError("생성된 초안이 없어 테이블을 보여 주지 못했습니다. 초안을 먼저 생성해 주세요.")
        d, b = self.pending[0], self.pending[1]
        prof = next((t for t in d.tables if t.name == table), None)
        if prof is None:
            raise LookupError(table)
        from xgen_space.compile.sql import qi

        cols = [c.name for c in prof.columns]
        pick = ", ".join(qi(c) for c in cols)
        dialect = b.capabilities.dialect
        sql = (f"SELECT TOP {SAMPLE_ROWS} {pick} FROM {qi(table)}" if dialect == "tsql" else
               f"SELECT {pick} FROM {qi(table)} FETCH FIRST {SAMPLE_ROWS} ROWS ONLY" if dialect == "oracle" else
               f"SELECT {pick} FROM {qi(table)} LIMIT {SAMPLE_ROWS}")
        try:
            rows = [list(r) for r in b.fetch(sql)]
        except Exception:  # a source that will not show rows still has its profile
            rows = []
        o = next((x for x in d.objects if x.table == table), None)
        key_col = next((p.column for p in o.properties if p.name == o.key), "") if o else ""
        kp = next((c for c in prof.columns if c.name == key_col), None)
        return plain({"table": table, "rows": prof.rows, "columns": cols, "sample": rows,
                      "key": {"column": key_col, "distinct": kp.distinct if kp else 0, "nulls": kp.nulls if kp else 0,
                              "why": o.key_why if o else ""},
                      "profile": [{"name": c.name, "type": c.type, "distinct": c.distinct, "nulls": c.nulls,
                                   "values": len(c.values)} for c in prof.columns],
                      "personal": [c for c in cols if PERSONAL.search(c)]})

    @staticmethod
    def _revised(d) -> dict:
        """What a draft would plug in: the graph, the two module files, and the checks it does not pass."""
        import yaml

        modules = d.modules()
        comp = compose(modules, name=d.name)
        graph = StudioSession(Studio.from_modules(modules, name=d.name)).graph() if not comp.issues else None
        return {"graph": graph, "issues": list(comp.issues), "queries": list(d.queries()),
                "query_items": [{"element": f"query:{k}", "label": v["label"], "on": k not in d.no_queries}
                                for k, v in d.queries(dropped=True).items()],
                "counts": {"objects": len(d.objects), "links": len(d.links),
                           "properties": sum(len(o.properties) for o in d.objects), "queries": len(d.queries()),
                           "states": len(d.states), "actions": len(d.actions()), "roles": len(d.roles()),
                           "questions": len(d.questions()), "decisions": len(d.decisions)},
                "modules": [{"name": m.name, "kind": m.kind, "label": m.label,
                             "yaml": yaml.safe_dump(m.to_dict(), allow_unicode=True, sort_keys=False)}
                            for m in modules]}

    @staticmethod
    def _edit(d, edits: dict | None):
        """The page's edits as revise() takes them."""
        e = edits if isinstance(edits, dict) else {}

        def pairs(k: str) -> dict:
            v = e.get(k)
            return {str(a): str(b) for a, b in v.items()} if isinstance(v, dict) else {}

        values = {}
        for k, v in (e.get("values") or {}).items():
            items = v.split(",") if isinstance(v, str) else v if isinstance(v, list) else []
            values[str(k)] = [str(x).strip() for x in items if str(x).strip()]
        return d.revise(drop=[str(x) for x in e.get("drop") or []],
                        labels={k: v[:60] for k, v in pairs("labels").items() if v.strip()},
                        keys=pairs("keys"), types=pairs("types"), values=values, cardinality=pairs("cardinality"),
                        add_links=[x for x in e.get("add_links") or [] if isinstance(x, dict)],
                        names={k: v.strip() for k, v in pairs("names").items() if v.strip()})

    # ---- a decision table from past outcomes, and bindings onto a standard ----------------------------------------

    def induce_decision(self, target: str, inputs: list, label: str = "", edits: dict | None = None) -> dict:
        from xgen_space.induce import InduceError, induce

        if not self.pending:
            raise ValueError("생성된 초안이 없어 판정 표를 만들지 못했습니다. 초안을 먼저 생성해 주세요.")
        d0, b, _, _ = self.pending
        try:  # the page names the target and inputs as the draft found them; new names come last, when it is applied
            d = self._edit(d0, {k: v for k, v in (edits or {}).items() if k != "names"})
            onto = compose(d.modules(), name=d.name).ontology
            out = induce(b, onto, str(target), [str(x) for x in inputs or []], label=label[:60])
        except (InduceError, ValueError) as e:
            return {"ok": False, "error": f"판정 표를 만들지 못했습니다. {_issue_text(str(e))}"}
        d0.decisions[out["name"]] = {**out["decision"], "report": out["report"]}
        self._note("draft", f"{out['decision']['label']}: 지난 {out['report']['cases']}건으로 규칙 "
                            f"{out['report']['rules']}개를 만들었습니다.")
        return plain({"ok": True, **out})

    def drop_decision(self, name: str) -> dict:
        if self.pending:
            self.pending[0].decisions.pop(name, None)
        return {"ok": True}

    def standards(self) -> dict:
        lib = self.studio.library
        rows = lib.list() if lib is not None else []
        return {"standards": [{"name": r["name"], "label": r["label"] or r["name"], "kind": r["kind"],
                               "kind_label": MODULE_KIND.get(r["kind"], r["kind"])}
                              for r in rows if r["kind"] in ("domain", "industry")]}

    def _standard(self, names: list) -> tuple[list[Module], Any]:
        lib = self.studio.library
        if lib is None:
            raise ValueError("라이브러리가 없어 표준에 연결하지 못했습니다.")
        names = [str(n) for n in names or []]
        if not names:
            raise ValueError("연결할 표준 모듈을 선택하지 않아 제안을 만들지 못했습니다. 표준 모듈을 선택해 주세요.")
        try:
            mods = lib.resolve(names)
            onto = compose(mods, **self.studio._compose_kw).ontology
        except ModuleError as e:
            raise ValueError(f"표준 모듈을 구성하지 못했습니다. {e}") from None
        return mods, onto

    def _terms(self) -> list[dict]:
        """The words a system uses: from the uploaded glossaries and the attached dictionary modules."""
        comp, defs = self.studio.composition, self._defs()
        return list(comp.terms if comp else []) + list(getattr(defs, "terms", None) or [])

    def suggest_mapping(self, standard: list, edits: dict | None = None, tables: dict | None = None) -> dict:
        from xgen_space.mapping import retarget, suggest

        if not self.pending:
            raise ValueError("생성된 초안이 없어 연결을 제안하지 못했습니다. 초안을 먼저 생성해 주세요.")
        mods, onto = self._standard(standard)
        d = self._edit(self.pending[0], edits)
        s = suggest(d, onto, [str(x) for x in standard], self._terms())
        if tables:
            s = retarget(s, d, onto, {str(k): str(v) for k, v in tables.items() if v}, self._terms())
        owner = {o: m.label or m.name for m in mods for o in (m.body.get("objects") or {})}
        objs = []
        for m in s.objects:
            o = onto.objects[m.object]
            objs.append({**m.__dict__, "label": o.label or m.object, "module_label": owner.get(m.object, ""),
                         "columns": [{**c.__dict__, "label": (find_prop(onto, m.object, c.property).label
                                                              or c.property)} for c in m.columns],
                         "missing": [{"property": p, "label": find_prop(onto, m.object, p).label or p}
                                     for p in m.missing]})
        tables = [{"table": o.table, "columns": [p.column for p in o.properties],
                   "names": {p.column: ", ".join(p.columns) for p in o.properties if p.columns}} for o in d.objects]
        return plain({"ok": True, "objects": objs, "links": s.links, "unmatched_tables": s.unmatched_tables,
                      "unbound_objects": [{"name": t, "label": onto.objects[t].label or t} for t in s.unbound_objects],
                      "tables": tables, "standard": [str(x) for x in standard]})

    def apply_review(self, standard: list, edits: dict | None = None, choices: dict | None = None,
                     mapping: dict | None = None) -> dict:
        """The draft as its review left it, table by table: a table a person bound to the standard becomes a binding
        of the standard's object, the others new objects beside the standard, joined to it where the draft found the
        tables joined."""
        if not self.pending:
            raise ValueError("생성된 초안이 없어 적용하지 못했습니다. 초안을 먼저 생성해 주세요.")
        if not any(c == "standard" for c in (choices or {}).values()):
            return self.apply_draft(edits)
        objects, extra = self._review_plan(standard, edits, choices)
        return self.apply_mapping(standard, edits, {**(mapping or {}), "objects": objects}, extra=extra)

    def _review_plan(self, standard: list, edits: dict | None, choices: dict | None) -> tuple[dict, list[Module]]:
        """Which standard object each bound table binds, and the modules of the tables kept as new objects."""
        from xgen_space.mapping import suggest

        bound = {str(t) for t, c in (choices or {}).items() if c == "standard"}
        _, onto = self._standard(standard)
        d = self._edit(self.pending[0], edits)
        s = suggest(d, onto, [str(x) for x in standard], self._terms())
        to_std = {m.table: m for m in s.objects if m.table in bound}
        objects = {m.object: (m.table if m.table in to_std else None) for m in s.objects}
        kept = [o for o in d.objects if o.table not in to_std]
        return objects, (self._beside(d, kept, to_std, onto, [str(x) for x in standard]) if kept else [])

    def review_preview(self, standard: list, edits: dict | None = None, choices: dict | None = None) -> dict:
        """What applying the review would plug in, before it does: the module files and the checks they fail."""
        import yaml

        from xgen_space.mapping import binding, suggest

        if not self.pending:
            raise ValueError("생성된 초안이 없어 미리 보지 못했습니다. 초안을 먼저 생성해 주세요.")
        if not any(c == "standard" for c in (choices or {}).values()):
            return self.preview_draft(edits)
        try:
            objects, extra = self._review_plan(standard, edits, choices)
            mods, onto = self._standard(standard)
            d = self._edit(self.pending[0], edits)
            m = binding(suggest(d, onto, [str(x) for x in standard], self._terms()), onto, name=f"{d.name}-standard",
                        label=f"{d.label} 표준 연결", edits={"objects": objects}, draft=d, terms=self._terms(), base=mods)
        except ValueError as e:
            return {"ok": False, "issues": [str(e)]}
        comp = compose([*mods, m, *extra], **self.studio._compose_kw)
        return plain({"ok": True, "issues": list(comp.issues),
                      "modules": [{"name": x.name, "kind": x.kind, "label": x.label,
                                   "yaml": yaml.safe_dump(x.to_dict(), allow_unicode=True, sort_keys=False)}
                                  for x in [m, *extra]]})

    @staticmethod
    def _beside(d, kept, to_std: dict, onto, standard: list[str]) -> list[Module]:
        """The draft's other tables as modules over the standard: their objects, and the relations the draft found
        between them and the tables bound to the standard, now on the standard's objects."""
        clash = sorted(o.name for o in kept if o.name in onto.objects)
        if clash:
            raise ValueError(f"새 객체 {', '.join(clash)}의 이름이 표준 객체와 같아 적용하지 못했습니다. API 이름을 바꾸거나 "
                             "표준에 연결해 주세요.")
        names = {o.name for o in kept}
        by_name = {o.name: o for o in d.objects}
        rest = d.revise(drop=[f"object:{o.name}" for o in d.objects if o.name not in names])
        mods = rest.modules()
        dom, bind = mods[0], mods[1]
        dom.requires = [*dom.requires, *[Requirement(n) for n in standard]]
        for lk in d.links:
            out_, in_ = lk.source in names, lk.target in names
            if out_ == in_ or lk.via or not lk.on:
                continue
            std = to_std.get(by_name[lk.target if out_ else lk.source].table)
            if std is None:
                continue
            so = onto.objects[std.object]
            if out_:  # a new object refers to a bound one: by the standard's key, if it reads the same column
                key_col = next((c.column for c in std.columns if c.property == so.key), "")
                target_key = next((p.column for p in by_name[lk.target].properties if p.name == lk.on[1]), "")
                if not key_col or key_col != target_key:
                    continue
                spec, on = {"from": lk.source, "to": std.object}, {lk.on[0]: so.key}
            else:  # a bound object refers to a new one: on the standard property its column is bound to
                prop = next((c.property for c in std.columns if c.column == lk.column), None)
                if prop is None:
                    continue
                spec, on = {"from": std.object, "to": lk.target}, {prop: lk.on[1]}
            name = lk.name if lk.name not in onto.links else f"{lk.name}Link"
            dom.body["links"][name] = {**spec, "cardinality": lk.cardinality, "label": lk.label}
            bind.extend.setdefault("links", {})[name] = {"on": on}
        return mods

    def apply_mapping(self, standard: list, edits: dict | None = None, mapping: dict | None = None,
                      extra: list[Module] | None = None) -> dict:
        from xgen_space.backends.rdf import RdflibBackend
        from xgen_space.draft import LABELS
        from xgen_space.mapping import binding, suggest

        if not self.pending:
            raise ValueError("생성된 초안이 없어 표준에 연결하지 못했습니다. 초안을 먼저 생성해 주세요.")
        mods, onto = self._standard(standard)
        d = self._edit(self.pending[0], edits)
        s = suggest(d, onto, [str(x) for x in standard], self._terms())
        m = binding(s, onto, name=f"{d.name}-standard", label=f"{d.label} 표준 연결", edits=mapping or {}, draft=d,
                    terms=self._terms(), base=mods)
        m.terms, m.messages = list(d.terms), list(d.messages)  # the system's words go with its binding
        extra = list(extra or [])
        comp = compose([*mods, m, *extra], **self.studio._compose_kw)
        if comp.issues:
            raise ValueError("정의 검사에서 오류가 발견되어 연결하지 못했습니다. " + "; ".join(comp.issues[:5]))

        def build() -> Studio:
            st = Studio.from_modules([*mods, m, *extra], library=OverlayLibrary(self.studio.library, [m, *extra]),
                                     use_zen=self.studio.use_zen, **self.studio._compose_kw)
            st.add_backend("source", self.pending[1], source=True)
            st.add_backend("graph", RdflibBackend())
            st.project()
            return st

        st = build()
        # the standard's questions were answered on its own example data. On these tables a question on a query with
        # parameters is asked again with the answer the tables give now (it also gives the query the values the
        # backends are compared with); one on a decision goes. Each kept query without parameters is asked its row
        # count now, as a draft does.
        words = LABELS.get(d.lang, LABELS["en"])["question"]
        asked, wrong, renewed = [], [], 0
        for name, rq in st.onto.queries.items():
            if not rq.params:
                asked.append({"id": f"{m.name}-q{len(asked) + 1}", "text": words.format(q=rq.label or name),
                              "query": name, "expect": {"rows": len(st.run(name, {}, backend="source").rows)}})
        failed = {r.id for r in st.questions(backend="source").results if not r.passed}
        for qs in [q for q in st.onto.questions if q.id in failed]:
            wrong.append(qs.id)
            if qs.query and st.onto.queries[qs.query].params:
                try:
                    rows = len(st.run(qs.query, qs.params, backend="source").rows)
                except Exception:  # a question the tables cannot answer goes
                    continue
                asked.append({"id": f"{m.name}-{qs.id}", "text": qs.text, "query": qs.query,
                              "params": dict(qs.params), "expect": {"rows": rows}})
                renewed += 1
        if wrong or asked:
            if wrong:
                m.remove["questions"] = [*m.remove.get("questions", []), *wrong]
            m.body["questions"] = asked
            st = build()
        self._make_room(d.label)
        self._stash()
        self._adopt(st)
        self._library_rows = st.library.list()
        self.origin = {**d.origin, "label": d.label, "standard": [str(x) for x in standard]}
        self.pending, self.log = None, []
        self._new_pipeline(d.label)
        removed = sum(len(v) for v in (m.remove.get("properties") or {}).values())
        uses = [f"{word} {len(m.remove[k])}개" for k, word in (("states", "상태 전이"), ("decisions", "결정"),
                                                              ("actions", "Action")) if m.remove.get(k)]
        news = len(extra[0].body.get("objects") or {}) if extra else 0
        self._note("draft", f"{d.label} 테이블을 표준 {', '.join(map(str, standard))} 에 연결했습니다. 객체 "
                            f"{len(m.extend.get('objects') or {})}개, 관계 {len(m.extend.get('links') or {})}개, "
                            + (f"새 객체 {news}개, " if news else "")
                            + f"테이블에 없는 속성 {removed}개 제외"
                            + (f"(이 속성을 사용하는 {', '.join(uses)} 제외)" if uses else "")
                            + (f", 예시 데이터 기준 표준 검증 질문 {renewed}개는 업로드 데이터의 답으로 다시 등록" if renewed else "")
                            + (f", 업로드 데이터로 답할 수 없는 표준 검증 질문 {len(wrong) - renewed}개 제외"
                               if len(wrong) > renewed else ""))
        return plain({"ok": True, "module": m.to_dict()})

    def preview_draft(self, edits: dict | None = None) -> dict:
        if not self.pending:
            raise ValueError("생성된 초안이 없어 미리 보지 못했습니다. 초안을 먼저 생성해 주세요.")
        try:
            r = self._edit(self.pending[0], edits)
        except ValueError as e:
            return {"ok": False, "issues": [str(e)]}
        return plain({"ok": True, **self._revised(r)})

    def apply_draft(self, edits: dict | None = None) -> dict:
        from xgen_space.backends.sql import SqliteBackend
        from xgen_space.draft import ReadError, load_sqlite, studio_from

        if not self.pending:
            raise ValueError("생성된 초안이 없어 적용하지 못했습니다. 초안을 먼저 생성해 주세요.")
        d0, b, tables, rules = self.pending
        try:
            d = self._edit(d0, edits)
        except ValueError as e:
            raise ValueError(f"편집 내용을 확인할 수 없어 적용하지 못했습니다. {e}") from None
        if not d.objects:
            raise ValueError("선택된 객체가 없어 적용하지 못했습니다. 객체를 하나 이상 선택해 주세요.")
        self._make_room(d.label)
        if d.origin.get("kind") == "files":  # a type the person chose is how the values are stored
            was = {(o.table, p.column): p.type for o in d0.objects for p in o.properties}
            original = {lo.table: t.name for t, lo in zip(tables, d0.loaded)}
            asked: dict[str, dict[str, str]] = {}
            for o in d.objects:
                for p in o.properties:
                    if was.get((o.table, p.column)) != p.type:
                        asked.setdefault(original.get(o.table, o.table), {})[p.column] = p.type
            if asked:
                b = SqliteBackend()
                try:
                    load_sqlite(tables, b, row_keys=rules.row_keys, types=asked)
                except ReadError as e:
                    i = e.info
                    raise ValueError(f"{i.get('table')}.{i.get('column')} 값 {i.get('value')!r} 을(를) "
                                     f"{i.get('type')} 타입으로 변환하지 못해 적용하지 못했습니다. 타입을 다시 선택해 "
                                     "주세요.") from None
        self._stash()
        try:
            self._adopt(studio_from(d, b, library=self.studio.library, use_zen=self.studio.use_zen))
        except ModuleError as e:
            raise ValueError(f"정의 검사에서 오류가 발견되어 적용하지 못했습니다. {e}") from None
        self._library_rows = self.studio.library.list()
        self.origin = {**d.origin, "label": d.label}
        self.pending, self.log = None, []
        self._new_pipeline(d.label)
        self._note("draft", f"{d.label} 온톨로지를 적용했습니다. 객체 {len(d.objects)}개, 관계 {len(d.links)}개")
        return {"ok": True}

    # ---- module files: read, check, save into this visitor's library, plug in ---------------------------------

    def _module(self, name: str) -> Module:
        comp = self.studio.composition
        for m in comp.modules if comp else []:
            if m.name == name:
                return m
        if self.studio.library is None:
            raise LookupError(name)
        try:
            return self.studio.library.get(name)
        except ModuleError:
            raise LookupError(name) from None

    def module_source(self, name: str, version: str = "") -> dict:
        import yaml

        lib = self.studio.library
        versions = list(lib.versions(name)) if lib is not None and name in lib.names() else []
        m = lib.get(name, version) if version and version in versions else self._module(name)
        comp = self.studio.composition
        return {"name": m.name, "label": m.label or m.name, "kind": m.kind, "version": m.version, "versions": versions,
                "applied": bool(comp) and m.name in {x.name for x in comp.modules},
                "yaml": yaml.safe_dump(m.to_dict(), allow_unicode=True, sort_keys=False)}

    @staticmethod
    def _parse_module(text: str) -> Module:
        import yaml

        if len(text.encode("utf-8")) > MODULE_TEXT_MAX:
            raise ValueError("정의 파일 크기가 48KB 한도를 초과해 읽지 못했습니다. 모듈을 나누어 저장해 주세요.")
        try:
            d = yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f"{mark.line + 1}행의 " if mark is not None else ""
            raise ValueError(f"{where}YAML 형식이 올바르지 않아 읽지 못했습니다. 들여쓰기와 따옴표를 확인해 주세요.") from None
        if not isinstance(d, dict) or not d.get("module"):
            raise ValueError("module 이름이 없어 읽지 못했습니다. 첫 줄에 module: 이름을 입력해 주세요.")
        try:
            return Module.from_dict(d)
        except KeyError as e:
            raise ValueError(f"{e} 항목이 없어 모듈을 읽지 못했습니다. 항목을 추가해 주세요.") from None
        except (ModuleError, TypeError, ValueError, AttributeError) as e:
            raise ValueError(f"모듈 형식이 올바르지 않아 읽지 못했습니다. {_issue_text(str(e))}") from None

    def _module_issues(self, m: Module) -> list[str]:
        from xgen_space.library import OverlayLibrary

        comp = self.studio.composition
        current = list(comp.modules) if comp else []
        names = {x.name for x in current}
        if m.name in names:
            mods = [m if x.name == m.name else x for x in current]
        else:
            try:
                picked = OverlayLibrary(self.studio.library, [m]).resolve([*names, m.name])
            except ModuleError as e:
                return [_issue_text(str(e))]
            mods = current + [x for x in picked if x.name not in names]
        try:
            return [_issue_text(str(x)) for x in compose(mods, **self.studio._compose_kw).issues]
        except ModuleError as e:
            return [_issue_text(str(e))]
        except KeyError as e:  # an object without its key, a link without its ends
            return [f"{e} 항목이 없어 정의를 읽지 못했습니다. 항목을 추가해 주세요."]

    def check_module(self, text: str) -> dict:
        m = self._parse_module(text)
        comp = self.studio.composition
        issues = self._module_issues(m)
        return plain({"ok": not issues, "issues": issues, "name": m.name, "version": m.version, "kind": m.kind,
                      "counts": m.counts(), "applied": bool(comp) and m.name in {x.name for x in comp.modules}})

    def save_module(self, text: str, apply: bool = False) -> dict:
        """Propose and, where this visitor may approve their own change, approve it in one step."""
        comp = self.studio.composition
        res = self.propose_module(text, attach=apply)
        change = res["change"]
        applied = bool(comp) and change["module"] in {x.name for x in comp.modules}
        if not self.studio.changes.self_approve:
            return {"ok": True, "applied": False, "pending": True, "change": change, "warning": ""}
        out = self.decide_change(change["id"], True)
        if not out["ok"]:
            raise ValueError(out["error"])
        warning = _projection_warning(out.get("projection") or {})
        return {"ok": True, "applied": applied or apply, "warning": warning, "change": out["change"],
                "bumped": res["bumped"]}

    def export_module(self, name: str) -> str:
        return self.module_source(name)["yaml"]

    # ---- definition changes: a module version is proposed, reviewed on a copy, approved by a person ------------

    def _change_label(self, cr) -> str:
        """A change's module by its name for people: the library's, else the label its own file gives."""
        import yaml

        label = self._label(cr.module)
        if label != cr.module:
            return label
        try:
            return str((yaml.safe_load(cr.text) or {}).get("label") or cr.module)
        except yaml.YAMLError:
            return cr.module

    def _change(self, cr) -> dict:
        rv = cr.review
        gates = [{**g, "label": GATE_LABEL.get((g["stage"], g["condition"]), g["condition"]),
                  "stage_label": STAGE_LABEL.get(g["stage"], g["stage"])} for g in rv.get("gates") or []]
        m = rv.get("measured") or {}
        return plain({
            "id": cr.id, "module": cr.module, "module_label": self._change_label(cr), "version": cr.version,
            "base_version": rv.get("base_version", ""), "mode": rv.get("mode", ""), "status": cr.status,
            "status_label": CHANGE_STATUS.get(cr.status, cr.status), "requested_by": cr.requested_by,
            "decided_by": cr.decided_by, "reason": cr.reason, "at": cr.at, "passed": rv.get("passed"),
            "issues": rv.get("issues") or [], "diff": rv.get("diff") or {}, "gates": gates,
            "measured": {"bind": {k: v for k, v in (m.get("bind") or {}).items() if k != "findings"},
                         "findings": (m.get("bind") or {}).get("findings", [])[:20],
                         "query": m.get("query"), "check": m.get("check"),
                         "decide": {k: v for k, v in (m.get("decide") or {}).items() if k != "mismatches"},
                         "mismatches": (m.get("decide") or {}).get("mismatches", [])[:20]}})

    def propose_module(self, text: str, attach: bool = False) -> dict:
        m = self._parse_module(text)
        issues = self._module_issues(m)
        if issues:
            raise ValueError("정의 검사에서 오류가 발견되어 변경을 요청하지 못했습니다. " + "; ".join(issues[:5]))
        lib = self.studio.changes.store or self.studio.library
        bumped = ""
        if m.version in lib.versions(m.name):
            if {**lib.get(m.name).to_dict(), "version": ""} == {**m.to_dict(), "version": ""}:  # an earlier version is a change from the latest
                raise ValueError("바뀐 내용이 없어 변경을 요청하지 못했습니다. 정의를 수정한 뒤 다시 요청해 주세요.")
            bumped, m.version = m.version, _next_version(lib.versions(m.name))
        cr = self.studio.changes.propose(m, by=self.who, attach=attach)
        extra = f" 버전 {bumped} 이(가) 이미 있어 {m.version} (으)로 올렸습니다." if bumped else ""
        state = "흐름 통과 조건을 모두 충족합니다" if cr.review.get("passed") else "흐름 통과 조건을 충족하지 못했습니다"
        self._note("change", f"{m.label or m.name} {m.version} 변경을 요청했습니다. {state}.{extra}")
        return {"ok": True, "change": self._change(cr), "bumped": bumped}

    def changes_state(self) -> dict:
        ch = self.studio.changes
        return {"changes": [self._change(c) for c in reversed(list(ch.requests.values()))], "who": self.who,
                "self_approve": ch.self_approve, "writes_folder": ch.store is not None}

    def decide_change(self, change_id: str, approve: bool, reason: str = "") -> dict:
        from xgen_space.review import ChangeError

        ch = self.studio.changes
        held = ch.requests.get(change_id)
        sent_back = [self._element_label(e) for e, v in (held.marks if held else {}).items() if v == "fix"]
        if approve and sent_back:
            return {"ok": False, "error": f"수정을 요청한 항목({', '.join(sent_back)})이 있어 승인하지 못했습니다. "
                                          "작성자가 고친 뒤 다시 검토해 주세요.", "change": self._change(held)}
        try:
            cr = ch.approve(change_id, by=self.who) if approve else                 ch.reject(change_id, by=self.who, reason=reason or "검토 후 반려")
        except PermissionError:
            return {"ok": False, "error": "변경을 요청한 사람은 같은 변경을 승인할 수 없어 승인하지 못했습니다. "
                                          "다른 승인자가 승인해 주세요."}
        except (ChangeError, ModuleError) as e:
            cr = ch.requests.get(change_id)
            failed = [g["label"] for g in (self._change(cr)["gates"] if cr else []) if not g["passed"]]
            why = ", ".join(failed) if failed else str(e)
            return {"ok": False, "error": f"흐름 통과 조건({why})을 충족하지 못해 승인하지 못했습니다. "
                                          "정의를 수정해 다시 요청해 주세요.",
                    "change": self._change(cr) if cr else None}
        proj = {}
        if cr.status == "approved":
            proj = self._reproject()
            self._library_rows = self.studio.library.list()
            if cr.module == WORKSPACE:
                self.workspace = None  # the edits are in the studio now; the next ones start from there
        verb = "승인하고 적용했습니다" if cr.status == "approved" else "반려했습니다"
        self._note("change", f"{self._label(cr.module)} {cr.version} 변경을 {verb}.", projection=proj)
        return {"ok": True, "change": self._change(cr), "projection": proj}

    # ---- management: objects, properties, relations, questions as one pending overlay module --------------------

    def _ws(self):
        from xgen_space.manage import Workspace

        comp = self.studio.composition
        if comp is None:
            raise ValueError("모듈로 구성된 스페이스가 아니어서 정의를 관리하지 못했습니다.")
        sig = tuple(m.key for m in comp.modules)
        if self.workspace is None or self._ws_sig != sig:
            current = next((m for m in comp.modules if m.name == WORKSPACE), None)
            old = self.workspace
            ws = Workspace(list(comp.modules), current, compose_kw=self.studio._compose_kw)
            if old is not None and old.dirty:  # unsent edits carry over to the new modules; they are checked again
                ws.module, ws.edits, ws._before, ws._undone = old.module, old.edits, old._before, old._undone
            self.workspace, self._ws_sig = ws, sig
        return self.workspace

    def manage_state(self) -> dict:
        """The definition as the pending edits would leave it, and what the source holds, for the management screens."""
        from xgen_space.draft import _catalog
        from xgen_space.functions import describe as describe_function
        from xgen_space.manage import _lineage, row_rule
        from xgen_space.review import element_diff

        ws = self._ws()
        issues: list[str] = []
        try:
            comp = ws.composed()
        except ModuleError as e:  # the modules changed under unsent edits and they no longer hold
            comp, issues = self.studio.composition, [str(e)]
        o, base = comp.ontology, self.studio.onto
        issues += list(comp.issues)
        mine = ws.module
        pending_check = []
        if ws.dirty and self.studio.source and not comp.issues:  # whether the unsent edits already mend what the source lacks
            try:
                from xgen_space.bindings import check_bindings

                pending_check = [asdict(f) for f in check_bindings(o, self.studio.backends[self.studio.source], data=False).findings]
            except Exception:  # the source could not be read: the page goes by the last measurement
                pending_check = []
        diff = element_diff(base, o) if ws.dirty else {"added": [], "removed": [], "changed": []}
        touched = set(diff["changed"])  # what the unsent edits change; what they add is marked new

        def owner(element: str) -> dict:
            m = comp.owner(element)
            return {"module": m, "module_label": mine.label if m == WORKSPACE else (self._label(m) if m else "")}

        src = self.studio.backends.get(self.studio.source) if self.studio.source else None
        catalog, rows = self._source_catalog(src, _catalog)
        bound: dict[str, list[str]] = {}
        for t in o.objects.values():
            if t.table:
                bound.setdefault(t.table, []).append(t.name)
        linked = {lk.source for lk in o.links.values()} | {lk.target for lk in o.links.values()}
        kinds = {m.name: m.kind for m in comp.modules}
        objects = []
        for t in o.objects.values():
            props = all_props(o, t.name)
            objects.append({
                "name": t.name, "label": t.label or t.name, "description": t.description, "table": t.table,
                "key": t.key, "parent": t.parent, "concept": not t.table, "properties": len(props),
                "computed": sum(1 for p in props if find_prop(o, t.name, p).expr),
                "links": sum(1 for lk in o.links.values() if t.name in (lk.source, lk.target)),
                "rows": rows.get(t.table) if t.table else None, "states": bool(t.states), "series": bool(t.series),
                "extended_by": [mine.label if x == WORKSPACE else self._label(x) for x in comp.touched.get(f"object:{t.name}", [])
                                if x != comp.owner(f"object:{t.name}") and kinds.get(x) != "binding"],  # a binding only places it
                "pending": f"object:{t.name}" in touched, "new": t.name not in base.objects, **owner(f"object:{t.name}")})
        from xgen_space.model import RAW_SUFFIX

        properties = []
        for t in o.objects.values():
            for pname in all_props(o, t.name):
                if pname.endswith(RAW_SUFFIX):  # the stored value behind a transform is the property's, not one of its own
                    continue
                p = find_prop(o, t.name, pname)
                from_type = t.name if pname in t.properties else next(
                    (x for x in _lineage(o, t.name) if pname in o.objects[x].properties), t.name)
                properties.append({
                    "object": t.name, "name": pname, "label": p.label, "type": p.type, "column": p.col if not p.expr or p.transform else "",
                    "values": p.values, "labels": p.labels, "columns": p.columns, "required": p.required,
                    "mask": p.mask, "expr": "" if p.transform else p.expr, "transform": p.transform, "source_type": p.source_type,
                    "unit": p.unit,
                    "description": p.description, "key": pname == t.key, "inherited": from_type if from_type != t.name else "",
                    "pending": f"property:{t.name}.{pname}" in touched,
                    "extended_by": [mine.label if x == WORKSPACE else self._label(x) for x in comp.touched.get(f"property:{from_type}.{pname}", [])
                                    if x != comp.owner(f"property:{from_type}.{pname}") and kinds.get(x) != "binding"],
                    "new": t.name not in base.objects or pname not in all_props(base, t.name),
                    **owner(f"property:{from_type}.{pname}")})
        links = [{"name": lk.name, "label": lk.label, "source": lk.source, "target": lk.target,
                  "on": list(lk.on) if lk.on else None,
                  "via": {"table": lk.via.table, "source": lk.via.source_column, "target": lk.via.target_column}
                  if lk.via else None, "cardinality": lk.cardinality, "inverse": lk.inverse, "required": lk.required,
                  "pending": f"link:{lk.name}" in touched, "new": lk.name not in base.links, **owner(f"link:{lk.name}")}
                 for lk in o.links.values()]
        questions = [{"id": q.id, "text": q.text, "decision": q.decision, "key": q.key, "query": q.query,
                      "params": q.params, "expect": q.expect, "pending": f"question:{q.id}" in diff["added"],
                      **owner(f"question:{q.id}")} for q in o.questions]
        via: dict[str, list[str]] = {}
        for lk in o.links.values():
            if lk.via:
                via.setdefault(lk.via.table, []).append(lk.name)
        tables = [{"table": t, "columns": [{"name": c, "type": ty} for c, ty in cols], "key": pk,
                   "fks": [{"column": c, "table": rt, "ref": rc} for c, rt, rc in fks], "rows": rows.get(t),
                   "objects": bound.get(t, []), "links": via.get(t, [])} for t, cols, pk, fks in catalog]
        import yaml

        from xgen_space.answer import rule_owner
        from xgen_space.decide.words import cell_parts, cell_words, input_label, labels_of, reads, unit_of

        decisions = []
        for t in o.decisions.values():
            spec = [{"name": i, "label": input_label(o, t, i), "type": v.type, "unit": unit_of(o, t, i).strip(),
                     "values": list((find_prop(o, *reads(o, t, i)).values if all(reads(o, t, i)) and find_prop(o, *reads(o, t, i)) else []) or []),
                     "labels": labels_of(o, t, i)} for i, v in t.inputs.items()]
            decisions.append({
                "name": t.name, "label": t.label or t.name, "target": t.target, "target_label": t.target and mine_label(o, t.target),
                "hit_policy": t.hit_policy, "inputs": spec, "outputs": [{"name": k, "type": v} for k, v in t.outputs.items()],
                "pending": f"decision:{t.name}" in touched, "new": t.name not in base.decisions, **owner(f"decision:{t.name}"),
                "rules": [{"id": r.id, "cite": r.cite, "then": r.then, "module": rule_owner(comp, t.name, r.id),
                           "when": {i["name"]: cell_parts(r.when.get(i["name"], "-")) for i in spec},
                           "said": {i["name"]: cell_words(r.when.get(i["name"], "-"), t.named, unit=unit_of(o, t, i["name"]), labels=i["labels"]) for i in spec}}
                          for r in t.rules]})
        def readers(name: str) -> list[str]:
            """What reads a named value, so a person changing it sees what moves with it."""
            at = re.compile(rf"@{re.escape(name)}\b")
            out = [f"{d.label or d.name} · {r.id}" for d in o.decisions.values() for r in d.rules
                   if at.search(f"{r.when} {r.then}")]
            out += [f"{mine_label(o, t.name)} · {x.label or x.name}" for t in o.objects.values() for x in t.properties.values()
                    if x.expr and at.search(x.expr)]
            out += [f"{a.label or a.name}" for a in o.actions.values() if at.search(str(a.auto_within))]
            out += [f"{f.label or f.name}" for f in o.functions.values() if at.search(f"{f.expr} {f.inputs}")]
            return out

        parameters = [{"name": p.name, "label": p.label or p.name, "value": p.value, "type": p.type, "unit": p.unit, "min": p.min, "max": p.max,
                       "description": p.description, "cite": p.cite, "pending": f"parameter:{p.name}" in touched, "readers": readers(p.name),
                       **owner(f"parameter:{p.name}")}
                      for p in o.parameters.values()]
        actions = [{"name": a.name, "label": a.label or a.name, "target": a.target, "target_label": mine_label(o, a.target),
                    "parameters": [{"name": k, "label": (v.get("label") if isinstance(v, dict) else "") or k, "type": (v.get("type") if isinstance(v, dict) else v) or "string"}
                                   for k, v in a.parameters.items()],
                    "criteria": [{"decision": c.decision, "expect": c.expect, "states": c.states, "function": c.function} for c in a.criteria],
                    "transition_to": a.transition_to, "approval": a.approval, "cite": a.cite, "set": a.set,
                    "auto_within": a.auto_within, "auto_agents": a.auto_agents, "call": a.call, "undo": a.undo,
                    "pending": f"action:{a.name}" in touched, "new": a.name not in base.actions, **owner(f"action:{a.name}")}
                   for a in o.actions.values()]
        roles = [{"name": r.name, "label": r.label or r.name, "read": r.read, "run": r.run, "request": r.request, "execute": r.execute,
                  "mask": r.mask, "unmask": r.unmask, "filters": sorted(r.row_filters), "pending": f"role:{r.name}" in touched,
                  "rows": [row_rule(t, s) for t, s in r.row_filters.items()], "scope": r.scope, "documents": r.documents,
                  "new": r.name not in base.roles, **owner(f"role:{r.name}")} for r in o.roles.values()]
        metrics = [{"name": x.name, "label": x.label or x.name, "description": x.description, "unit": x.unit, "owner": x.owner,
                    "scale": x.scale, "cite": x.cite, "formula": x.formula, "denominator": x.denominator, "time": x.time,
                    "pending": f"metric:{x.name}" in touched, "new": x.name not in base.metrics, **owner(f"metric:{x.name}")}
                   for x in o.metrics.values()]
        identities = [{"name": i.name, "label": i.label or i.name, "table": i.table,
                       "members": {m.type: m.fields for m in i.members.values()},
                       "rules": [{"id": r.id, "match": r.match, "normalize": r.normalize} for r in i.rules],
                       "new": i.name not in base.identities, **owner(f"identity:{i.name}")} for i in o.identities.values()]
        functions = [{**describe_function(o, f), "pending": f"function:{f.name}" in touched, "new": f.name not in base.functions,
                      **owner(f"function:{f.name}")} for f in o.functions.values()]
        states = [{"object": t.name, "label": t.label or t.name, "property": t.states.property, "states": t.states.states,
                   "initial": t.states.initial, "pending": f"object:{t.name}" in touched, **owner(f"object:{t.name}"),
                   "transitions": [{"from": m.source, "to": m.target, "action": m.action} for m in t.states.transitions]}
                  for t in o.objects.values() if t.states]

        return plain({
            "objects": objects, "properties": properties, "links": links, "questions": questions,
            "decisions": decisions, "parameters": parameters, "actions": actions, "roles": roles, "states": states,
            "metrics": metrics, "identities": identities, "functions": functions,
            "queries": [{"name": n, "label": q.label or n} for n, q in o.queries.items()],
            "documents": sorted(self.studio.space.documents()) if self.studio.space is not None else [],
            "folders": self.studio.space.folders() if self.studio.space is not None else [],
            "unlinked": [x["name"] for x in objects if not x["concept"] and x["name"] not in linked],
            "unread": [x["name"] for x in objects if not x["concept"] and not self._readers(f"object:{x['name']}")],
            "comments": {k: len(v) for k, v in self._notes().items() if v},
            "sources": {"source": {"name": self.studio.source, "dialect": src.capabilities.dialect if src else "",
                                   "tables": tables,
                                   "unbound": [x["table"] for x in tables if not x["objects"] and not x["links"]]},
                        "graphs": [{"name": n, "language": b.capabilities.language}
                                   for n, b in self.studio.backends.items() if n != self.studio.source]},
            "workspace": {"dirty": ws.dirty, "module": WORKSPACE, "label": mine.label,
                          "version": ws.current.version if ws.current else "",
                          "edits": [{"op": e.op, "target": e.target, "took_out": e.took_out} for e in ws.edits], "redo": len(ws._undone),
                          "issues": issues, "diff": diff, "impact": self._impact(diff), "findings": pending_check,
                          "yaml": yaml.safe_dump(mine.to_dict(), allow_unicode=True, sort_keys=False)},
        })

    def _impact(self, diff: dict) -> dict:
        """How many queries, decisions, questions, actions and roles read what the pending edits change or take out."""
        seen: set[str] = set()
        for el in [*diff.get("changed", []), *diff.get("removed", [])]:
            if el.split(":", 1)[0] in ("object", "property", "link", "decision", "rule", "query"):
                seen.update(self._readers(el))
        out: dict[str, int] = {}
        for r in seen:
            kind = next((w for w in IMPACT_KINDS if r.startswith(w)), "")
            if kind:
                out[IMPACT_KINDS[kind]] = out.get(IMPACT_KINDS[kind], 0) + 1
        return out

    def manage_undo(self) -> dict:
        from xgen_space.manage import UNDO_DEPTH, TooFarBack

        ws = self._ws()
        try:
            if ws.undo() is None:
                raise ValueError("되돌릴 변경이 없습니다.")
        except TooFarBack:
            raise ValueError(f"최근 {UNDO_DEPTH}개보다 앞선 변경은 하나씩 되돌리지 못합니다. 모두 취소한 뒤 다시 바꿔 주세요.") from None
        return {"ok": True, **self.manage_state()}

    def manage_redo(self) -> dict:
        from xgen_space.manage import EditError

        try:
            if self._ws().redo() is None:
                raise ValueError("다시 실행할 변경이 없습니다.")
        except (EditError, ModuleError) as e:
            raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, **self.manage_state()}

    def manage_revert(self, index: int) -> dict:
        """One pending edit taken back, the ones after it kept."""
        from xgen_space.manage import UNDO_DEPTH, EditError, TooFarBack

        try:
            self._ws().revert(int(index))
        except TooFarBack:
            raise ValueError(f"최근 {UNDO_DEPTH}개보다 앞선 변경은 하나씩 되돌리지 못합니다. 모두 취소한 뒤 다시 바꿔 주세요.") from None
        except EditError as e:
            raise ValueError(f"뒤에 있는 변경({e})이 이 변경에 기대고 있어 되돌리지 못했습니다. 그 변경을 먼저 되돌려 주세요.") from None
        return {"ok": True, **self.manage_state()}

    def link_suggest(self, source: str, target: str) -> dict:
        """How two objects would join, from the names and references the source shows, and how many rows would meet."""
        from xgen_space.check import columns_of
        from xgen_space.compile.sql import qi

        o, _ = self._pending_onto()
        if source not in o.objects or target not in o.objects:
            raise ValueError("객체를 찾지 못해 관계를 제안하지 못했습니다. 카드를 다시 선택해 주세요.")
        a, b = o.objects[source], o.objects[target]
        pa, pb = all_props(o, source), all_props(o, target)
        fields = {p: find_prop(o, source, p) for p in pa}, {p: find_prop(o, target, p) for p in pb}
        same = lambda p, x: p in x and not fields[x is pb][p].expr  # noqa: E731
        options: list[tuple[str, str, str]] = []
        if same(b.key, pa):
            options.append((b.key, b.key, "many_to_one"))
        if same(a.key, pb) and (a.key, a.key, "one_to_many") not in options:
            options.append((a.key, a.key, "one_to_many"))
        for p in pa:  # a column named for the other table's key: order_no for an Order keyed by no, buyer_id for Buyer
            if (p == f"{target.lower()}_{b.key}" or p == f"{target.lower()}_id") and p != b.key and same(b.key, pb):
                options.append((p, b.key, "many_to_one"))
        src = self.studio.backends.get(self.studio.source) if self.studio.source else None
        met = []
        for sp, tp, card in options[:4]:
            row = {"sp": sp, "tp": tp, "cardinality": card, "ratio": None, "matched": None, "total": None}
            if src is not None and a.table and b.table:
                try:
                    s, t = columns_of(o, source, sp)[0], columns_of(o, target, tp)[0]
                    many, m_col, one, o_col = (a.table, s, b.table, t) if card == "many_to_one" else (b.table, t, a.table, s)  # counted from the side that points
                    got = src.fetch(f"SELECT COUNT(m.{qi(m_col)}), COUNT(u.{qi(o_col)}) FROM {qi(many)} m LEFT JOIN {qi(one)} u ON m.{qi(m_col)} = u.{qi(o_col)} "
                                    f"WHERE m.{qi(m_col)} IS NOT NULL")[0]
                    row.update({"total": got[0], "matched": got[1], "ratio": got[1] / got[0] if got[0] else None})
                except Exception:  # columns that cannot be joined have no ratio to show
                    row["ratio"] = None
            met.append(row)
        met.sort(key=lambda r: -(r["ratio"] or 0))
        taken = {lk.name for lk in o.links.values()} | {lk.inverse for lk in o.links.values() if lk.inverse}
        first = target[:1].lower() + target[1:]
        name = first if first not in taken else f"{source[:1].lower()}{source[1:]}{target}"
        return plain({"source": source, "target": target, "name": name, "label": b.label or target, "options": met,
                      "props": {"source": [{"name": p, "label": f.label or p} for p, f in fields[0].items() if not f.expr],
                                "target": [{"name": p, "label": f.label or p} for p, f in fields[1].items() if not f.expr]}})

    def object_profile(self, name: str) -> dict:
        """A few rows of an object as the source holds them, and for each column how full and how varied it is."""
        from xgen_space.check import columns_of
        from xgen_space.compile.sql import qi

        o, _ = self._pending_onto()
        t = o.objects.get(name)
        if t is None or not t.table:
            return {"ok": False, "error": "개념 객체라 연결된 데이터가 없습니다."}
        src = self.studio.backends.get(self.studio.source) if self.studio.source else None
        if src is None:
            return {"ok": False, "error": "원천 DB가 연결되어 있지 않아 데이터를 읽지 못했습니다."}
        have = src.columns(t.table) or {}
        props = [p for p in all_props(o, name) if not find_prop(o, name, p).expr
                 and len(columns_of(o, name, p)) == 1 and columns_of(o, name, p)[0].lower() in have][:14]
        if not props:
            return {"ok": False, "error": f"{t.table} 테이블에서 읽을 수 있는 컬럼이 없습니다."}
        cols = [columns_of(o, name, p)[0] for p in props]
        dialect = src.capabilities.dialect
        top, first = ("TOP 6 " if dialect == "tsql" else ""), {"oracle": " FETCH FIRST 6 ROWS ONLY", "tsql": ""}.get(dialect, " LIMIT 6")
        rows = src.fetch(f"SELECT {top}{', '.join(qi(c) for c in cols)} FROM {qi(t.table)}{first}")
        counts = src.fetch(f"SELECT COUNT(*), {', '.join(f'COUNT({qi(c)}), COUNT(DISTINCT {qi(c)})' for c in cols)} FROM {qi(t.table)}")[0]
        total = counts[0]
        stats = [{"name": p, "label": find_prop(o, name, p).label or p, "column": c, "filled": counts[1 + i * 2], "distinct": counts[2 + i * 2],
                  "empty": 1 - counts[1 + i * 2] / total if total else 0} for i, (p, c) in enumerate(zip(props, cols))]
        return plain({"ok": True, "name": name, "table": t.table, "total": total, "columns": props, "rows": [list(r) for r in rows], "stats": stats})

    def manage_trial(self) -> dict:
        """The pending edits tried on a copy of the space, as a change request would be, without filing one: each pass
        condition as it stands now and as it would be."""
        from xgen_space.review import review

        ws = self._ws()
        if not ws.dirty:
            raise ValueError("바뀐 내용이 없어 시험하지 못했습니다. 객체 · 속성 · 관계를 수정한 뒤 다시 시험해 주세요.")
        got = review(self.studio, ws.module, attach=ws.current is None)
        gates = [{**g, "label": GATE_LABEL.get((g["stage"], g["condition"]), g["condition"])} for g in got.get("gates") or []]
        return plain({"ok": True, "passed": got.get("passed"), "issues": got.get("issues") or [], "gates": gates,
                      "before": self._standing_gates(), "measured": got.get("measured") or {}, "diff": got.get("diff") or {}})

    def element_yaml(self, element: str) -> dict:
        """One object as the pending edits would leave it, in the shape a person writes it back."""
        import yaml

        kind, _, name = element.partition(":")
        o = self._ws().composed().ontology
        if kind != "object" or name not in o.objects:
            raise LookupError(element)
        t = o.objects[name]
        spec: dict[str, Any] = {k: v for k, v in (("label", t.label), ("description", t.description), ("table", t.table),
                                                  ("key", t.key), ("parent", t.parent), ("title", t.title)) if v}
        props = {}
        for p in t.properties:
            d = find_prop(o, name, p)
            col = column_of(o, name, p) if t.table and not d.expr else ""
            props[p] = {k: v for k, v in (("label", d.label), ("type", d.type), ("column", col if col != p else ""),
                                          ("unit", d.unit), ("values", list(d.values or [])), ("required", d.required),
                                          ("mask", d.mask), ("expr", d.expr), ("description", d.description)) if v}
        spec["properties"] = props
        return {"element": element, "yaml": yaml.safe_dump({name: spec}, allow_unicode=True, sort_keys=False)}

    def manage_yaml(self, element: str, text: str) -> dict:
        """An object written back as YAML: what differs from the form becomes the same edits the form would make."""
        import yaml

        from xgen_space.manage import EditError

        kind, _, name = element.partition(":")
        try:
            doc = yaml.safe_load(text or "")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML을 읽지 못했습니다. {e}") from None
        if kind != "object" or not isinstance(doc, dict) or list(doc) != [name] or not isinstance(doc[name], dict):
            raise ValueError(f"'{name}:' 하나로 시작하는 객체 정의여야 합니다.")
        new = doc[name]
        old = yaml.safe_load(self.element_yaml(element)["yaml"])[name]
        ws = self._ws()
        snap, n = copy.deepcopy(ws.module.to_dict()), len(ws.edits)
        try:
            fields = {k: new.get(k, "") for k in ("label", "description", "table", "parent", "title") if new.get(k, "") != old.get(k, "")}
            if new.get("key") and new.get("key") != old.get("key"):
                fields["key"] = new["key"]
            have, want = old.get("properties") or {}, new.get("properties") or {}
            for p, spec in want.items():
                spec = spec if isinstance(spec, dict) else {"type": str(spec)}
                if p not in have:
                    ws.apply("add_property", {"object": name, "name": p, **spec})
                    continue
                changed = {k: spec.get(k, "") for k in set(spec) | set(have[p]) if spec.get(k, "") != have[p].get(k, "")}
                if changed:
                    ws.apply("update_property", {"object": name, "name": p, **changed})
            if fields:
                ws.apply("update_object", {"name": name, **fields})
            for p in have:
                if p not in want:
                    ws.apply("delete_property", {"object": name, "name": p})
        except EditError as e:
            ws.module, ws.edits, ws._before = Module.from_dict(snap), ws.edits[:n], ws._before[:n]
            raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, **self.manage_state()}

    def _notes(self) -> dict[str, list[dict]]:
        """Comments on elements of the definition, kept in the journal with the change requests when there is one."""
        if self._element_notes is None:
            self._element_notes = {}
            journal = self.studio.changes.journal
            for r in journal.read() if journal is not None else []:
                if r.get("kind") == "comment" and r.get("element"):
                    self._element_notes.setdefault(r["element"], []).append(
                        {k: r.get(k) for k in ("at", "by", "text")})
        return self._element_notes

    _element_notes: dict | None = None

    def element_comments(self, element: str) -> dict:
        return {"element": element, "comments": list(self._notes().get(element, []))}

    def element_comment(self, element: str, text: str) -> dict:
        text = " ".join(str(text or "").split())[:500]
        if not element or not text:
            raise ValueError("댓글이 없어 남기지 못했습니다. 내용을 입력해 주세요.")
        note = {"at": self.studio.now().isoformat(timespec="minutes"), "by": self.who or "page", "text": text}
        self._notes().setdefault(element, []).append(note)
        journal = self.studio.changes.journal
        if journal is not None:
            journal.write("comment", {"element": element, **note})
        return self.element_comments(element)

    def _source_catalog(self, src, read) -> tuple[list, dict]:
        """The source's tables and their row counts, read once per source (edits re-read the state often)."""
        if src is None:
            return [], {}
        if getattr(self, "_catalog_of", None) is src:
            return self._catalog_rows
        try:
            catalog = read(src)
        except Exception:  # a source the catalog reader does not know (a graph, a DB-API driver): tables unknown
            catalog = []
        from xgen_space.compile.sql import qi

        rows: dict = {}
        for t, *_ in catalog:
            try:
                rows[t] = src.fetch(f"SELECT COUNT(*) FROM {qi(t)}")[0][0]
            except Exception:  # a view or a table this account may not read
                rows[t] = None
        self._catalog_of, self._catalog_rows = src, (catalog, rows)
        return catalog, rows

    def manage_edit(self, op: str, args: dict) -> dict:
        from xgen_space.manage import EditError

        try:
            edit = self._ws().apply(str(op), dict(args or {}))
        except EditError as e:
            raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, "edit": {"op": edit.op, "target": edit.target, "took_out": edit.took_out},
                **self.manage_state()}

    def manage_import_questions(self, text: str) -> dict:
        """Questions from a YAML or JSON list ({id, text, query, params, expect} or {id, text, decision, key, expect})."""
        import yaml

        from xgen_space.manage import EditError

        try:
            items = yaml.safe_load(text)
        except yaml.YAMLError:
            raise ValueError("파일을 읽지 못했습니다. YAML 또는 JSON 목록인지 확인해 주세요.") from None
        if isinstance(items, dict):
            items = items.get("questions")
        if not isinstance(items, list) or not items:
            raise ValueError("검증 질문 목록이 없어 불러오지 못했습니다. questions 목록을 입력해 주세요.")
        added, failed = [], []
        for q in items[:200]:
            try:
                self._ws().apply("add_question", dict(q))
                added.append(str(q.get("id")))
            except (EditError, AttributeError) as e:
                failed.append(f"{q.get('id') if isinstance(q, dict) else q}: {_edit_text(str(e))}")
        return {"ok": True, "added": added, "failed": failed, **self.manage_state()}

    def manage_discard(self) -> dict:
        self.workspace = None
        return {"ok": True, **self.manage_state()}

    def manage_propose(self) -> dict:
        """File the pending edits as a change to the workspace module: tried on a copy, then approved by a person."""
        import yaml

        ws = self._ws()
        if not ws.dirty:
            raise ValueError("바뀐 내용이 없어 변경을 요청하지 못했습니다. 객체 · 속성 · 관계를 수정한 뒤 다시 요청해 주세요.")
        text = yaml.safe_dump(ws.module.to_dict(), allow_unicode=True, sort_keys=False)
        res = self.propose_module(text, attach=ws.current is None)
        change = res["change"]
        if not self.studio.changes.self_approve:  # a person approves it on the library screen
            self.workspace = None
            return {"ok": True, "pending": True, "change": change, **self.manage_state()}
        out = self.decide_change(change["id"], True)
        if not out["ok"]:  # the trial did not pass: the edits stay to be fixed, the request goes back with its review
            cr = self.studio.changes.reject(change["id"], by=self.who, reason="흐름 통과 조건 미충족 · 관리 화면에서 수정")
            return {"ok": False, "error": out["error"], "change": self._change(cr), **self.manage_state()}
        self.workspace = None  # approved: what comes next starts from the studio as it now stands
        return {"ok": True, "pending": False, "change": out["change"],
                "warning": _projection_warning(out.get("projection") or {}), **self.manage_state()}

    # ---- the flow's stages and pass conditions, agreement with past decisions, identities, sync --------------

    def flow_settings(self) -> dict:
        from xgen_space.review import GATES, STAGES

        st = self.studio
        qs = [{"name": q.name, "label": q.label or q.name,
               "columns": [c.name for c in st.query(q.name).columns]} for q in st.onto.queries.values()]
        ds = [{"name": d.name, "label": d.label or d.name, "inputs": list(d.inputs), "outputs": list(d.outputs)}
              for d in st.onto.decisions.values()]
        # the form edits the studio's own conditions; a quality module's that ask more are shown next to them
        raised = []
        for ref, m in st.raised_gates().items():
            stage, cond = ref.split(".")
            raised.append({"stage": stage, "condition": cond, "value": st.composition.gates[stage][cond], "module": m,
                           "module_label": self._label(m)})
        return plain({"settings": st.own_flow.to_dict(), "raised": raised,
                      "stages": [{"id": s, "label": STAGE_LABEL[s]} for s in STAGES],
                      "functions": [{"name": x.name, "label": x.label or x.name, "outputs": list(x.outputs)} for x in self.studio.onto.functions.values()],
                      "conditions": {s: [{"id": c, "label": GATE_LABEL[(s, c)]} for c in cs]
                                     for s, cs in GATES.items()},
                      "queries": qs, "decisions": ds})

    def save_flow(self, settings: dict) -> dict:
        from xgen_space.review import FlowSettings

        try:
            fs = FlowSettings.from_dict(settings)
        except ValueError:
            raise ValueError("흐름 설정 값이 올바르지 않아 저장하지 못했습니다. 비율은 0에서 100 사이의 숫자로 입력해 주세요.") from None
        self.studio.settings["flow"] = fs.to_dict()
        self._note("flow", "흐름 단계와 통과 조건을 저장했습니다.")
        return {"ok": True, "settings": fs.to_dict()}

    def agreement(self) -> dict:
        st = self.studio
        if not st.flow.agreement:
            return {"ok": False, "error": "판정 일치율 설정이 없어 측정하지 못했습니다. 흐름 설정에서 비교할 결정표와 "
                                          "처리 기록 질의를 지정해 주세요."}
        try:
            a = st.agreement()
        except Exception as e:
            return {"ok": False, "error": f"처리 기록을 판정하지 못했습니다. {type(e).__name__}: {e}"}
        d = st.onto.decisions[a["decision"]]
        return plain({"ok": True, "label": d.label or d.name, **a})

    def identities(self) -> dict:
        st = self.studio
        out = []
        for name, ident in st.onto.identities.items():
            try:
                rep = st.resolve_identity(name, write=False)
            except Exception as e:
                out.append({"name": name, "label": ident.label or name, "error": f"{type(e).__name__}: {e}"})
                continue
            out.append({"name": name, "label": ident.label or name, "table": ident.table,
                        "members": [{"type": m.type, "label": self._obj_label(m.type), "fields": m.fields}
                                    for m in ident.members.values()],
                        "rules": [{"id": r.id, "match": r.match, "normalize": r.normalize} for r in ident.rules],
                        **rep.to_dict()})
        return plain({"identities": out})

    def resolve_identity(self, name: str) -> dict:
        src = self.studio.backends.get(self.studio.source)
        if src is None or not getattr(src, "capabilities", None) or not src.capabilities.write:
            return {"ok": False, "error": "원천 DB에 쓸 수 없어 교차표를 만들지 못했습니다. 쓰기 가능한 원천을 연결해 주세요."}
        if self.origin.get("kind") == "connect":
            return {"ok": False, "error": "연결한 DB에는 교차표를 쓰지 않습니다. 사내 설치에서 xspace 명령으로 실행해 주세요."}
        rep = self.studio.resolve_identity(name)
        self._note("identity", f"{name}: 기록 {rep.records}건을 {len(rep.clusters)}개로 통합했습니다 "
                               f"(통합된 건 {len(rep.joined)}).")
        return plain({"ok": True, **rep.to_dict()})

    def sync(self) -> dict:
        res = self.studio.sync()
        if res.get("error"):
            return {"ok": False, "error": f"원천을 다시 읽지 못했습니다. {res['error']}"}
        self._note("sync", "원천 변경분을 반영했습니다." if res["changed"] else "원천에 바뀐 내용이 없습니다.")
        return plain({"ok": True, **res})

    # ---- the whole flow, from the source to the checks, with what each stage holds now ----------------------

    def flow(self) -> dict:
        from xgen_space.compile.sql import qi

        st, o = self.studio, self.studio.onto
        self._sync_space()
        space = self.space
        space.index()
        src = st.backends.get(st.source)
        tables = sorted({t.table for t in o.objects.values() if t.table} |
                        {lk.via.table for lk in o.links.values() if lk.via})
        rows = []
        for t in tables:
            try:
                rows.append({"table": t, "rows": src.fetch(f"SELECT COUNT(*) FROM {qi(t)}")[0][0]})
            except Exception:  # a table the definition names but the database lacks; DB 대조 shows it
                rows.append({"table": t, "rows": None})
        comp = st.composition
        modules = [{"name": m.name, "label": m.label or m.name, "kind": m.kind,
                    "kind_label": MODULE_KIND.get(m.kind, m.kind)} for m in (comp.modules if comp else [])]
        from xgen_space.review import gates as pass_gates
        from xgen_space.review import measure

        settings = st.flow
        measured = self._measured = measure(st, settings)
        by = st.raised_gates()
        results = [{**g.__dict__, "label": GATE_LABEL.get((g.stage, g.condition), g.condition),
                    "by": self._label(by[f"{g.stage}.{g.condition}"]) if f"{g.stage}.{g.condition}" in by else ""}
                   for g in pass_gates(measured, settings)]
        bind, conf, qa, agree = (measured.get(k) for k in ("bind", "query", "check", "decide"))
        proj = st.projection
        steps = [
            {"id": "source", "backend": st.source, "dialect": src.capabilities.dialect if src else "",
             "tables": rows, "rows": sum(r["rows"] or 0 for r in rows)},
            {"id": "define", "modules": modules, "objects": len(o.objects), "links": len(o.links),
             "properties": sum(len(t.properties) for t in o.objects.values()),
             "computed": sum(1 for t in o.objects.values() for p in t.properties.values() if p.expr),
             "identities": len(o.identities)},
            {"id": "bind", "ok": bind["ok"] if bind else None, "checked": bind["checked"] if bind else {},
             "findings": len(bind["findings"]) if bind else 0},
            {"id": "project", "backends": [n for n, b in st.backends.items() if b.capabilities.load],
             "nodes": len(proj.nodes) if proj else 0, "edges": len(proj.edges) if proj else 0, "sync": st.last_sync},
            {"id": "index", "documents": len(space.documents()), "chunks": len(space.chunks),
             "sections": len({(c.document, c.section) for c in space.chunks.values()}),
             "embedder": space.embedder.describe(),
             "stores": [{"name": n, "kind": s.kind, "error": space.errors.get(n, "")} for n, s in space.stores.items()],
             "found": (measured.get("index") or {}).get("found"), "questions": (measured.get("index") or {}).get("questions")},
            {"id": "query", "queries": len(o.queries), "targets": len(TARGETS),
             "conformance": {k: conf[k] for k in ("agree", "queries", "error") if k in conf} if conf else None},
            {"id": "decide", "decisions": len(o.decisions), "actions": len(o.actions),
             "rules": sum(len(d.rules) for d in o.decisions.values()),
             "agreement": {k: agree.get(k) for k in ("cases", "agree", "rate", "error") if k in agree}
             if agree else None},
            {"id": "check", "questions": len(o.questions), "accuracy": (qa or {}).get("accuracy"),
             "grounded": (qa or {}).get("grounded"), "value_errors": (qa or {}).get("value_errors")},
        ]
        for s in steps:
            s["on"] = settings.on(s["id"])
            s["gates"] = [g for g in results if g["stage"] == s["id"]]
        return plain({"origin": self.origin, "passed": all(g["passed"] for g in results), "steps": steps})

    # ---- checks ----------------------------------------------------------------------------------------------

    def questions(self) -> dict:
        st = self.studio
        rep = st.questions()
        conf = None
        if len(st.backends) > 1:
            try:
                c = st.conformance()
                conf = {"passed": c.passed, "summary": c.summary(),
                        "queries": [{"name": r.name, "label": st.onto.queries[r.name].label or r.name,
                                     "agree": r.agree, "detail": r.detail,
                                     "rows": {b: (len(o.rows) if o.rows is not None else None)
                                              for b, o in r.outcomes.items()},
                                     "errors": {b: o.error for b, o in r.outcomes.items() if o.error}}
                                    for r in c.queries]}
            except Exception as e:
                conf = {"passed": False, "error": f"{type(e).__name__}: {e}"}
        return plain({"accuracy": rep.accuracy, "grounded": rep.grounded,
                      "results": [{**r.__dict__, "error": said(r.error) if r.error else "", "gaps": [_gap_text(g) for g in r.gaps]}
                                  for r in rep.results],
                      "conformance": conf})

    def bindings(self) -> dict:
        source = self.studio.source
        if not source:
            return {"ok": False, "error": "원천 DB가 연결되어 있지 않아 대조하지 못했습니다."}
        rep = self.studio.check_bindings()
        return plain({"ok": rep.ok, "checked": rep.checked, "backend": source,
                      "findings": [f.__dict__ for f in rep.findings]})


def _next_version(versions: list[str]) -> str:
    from xgen_space.modules import version_key

    last = sorted(versions, key=version_key)[-1]
    parts = last.split(".")
    if all(p.isdigit() for p in parts):
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return f"{last}.1"


def _facts(tables: list, defs: Any) -> dict:
    """What a catalog row says of a file: the kind it turned out to be, and how much of it there is."""
    if tables:
        return {"kind": "data", "tables": len(tables), "rows": sum(len(t.rows) for t in tables),
                "columns": max(len(t.columns) for t in tables)}
    if defs is None:
        return {"kind": "empty"}
    c = defs.counts()
    if c.get("tables") or c.get("codes") or c.get("terms") or c.get("messages"):
        return {"kind": "definition", **c}
    return {"kind": "document", "documents": len(defs.documents), "sections": sum(len(d["sections"]) for d in defs.documents),
            "doc_kind": defs.documents[0]["kind"] if defs.documents else "other"}


def _as_definitions(source: str, tables: list, defs: Any):
    """A file's share of the one JSON: rows bring their columns and types, not the rows."""
    from xgen_space.definitions import ColumnDef, Definitions, TableDef
    from xgen_space.draft import infer_type

    out = defs if defs is not None else Definitions(sources=[source])
    for t in tables:
        columns = [ColumnDef(c, type=infer_type([r[i] for r in t.rows])) for i, c in enumerate(t.columns)]
        out.tables[t.name] = TableDef(t.name, columns=columns)
    return out


def _json_text(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _size(n: int) -> str:
    return f"{n >> 20}MB" if n >= 1 << 20 and not n % (1 << 20) else f"{n >> 10:,}KB"


def _word(v: Any) -> str:
    return ("true" if v else "false") if isinstance(v, bool) else str(plain(v))


def _projection_warning(proj: dict) -> str:
    if "error" not in proj:
        return ""
    return "원천 DB가 정의와 일치하지 않아 그래프 저장소에 반영하지 못했습니다. DB 대조에서 확인해 주세요."


_ZEN: bool | None = None


def _has_zen() -> bool:
    global _ZEN
    if _ZEN is None:
        try:
            import zen  # noqa: F401

            _ZEN = True
        except ImportError:
            _ZEN = False
    return _ZEN
