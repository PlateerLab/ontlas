'use strict';
(() => {
  const ICON = {
    sec_sem: '<path d="M12 4v15M7 20h10"/><path d="M5 8h14"/><path d="M5 8l-2.6 5.5h5.2zM19 8l-2.6 5.5h5.2z"/>',
    sec_ont: '<circle cx="6" cy="7" r="2.3"/><circle cx="18" cy="6" r="2.3"/><circle cx="12" cy="18" r="2.3"/><path d="M8.2 7.6l7.5-1.2M7.3 9l3.6 7M16.8 8.1l-3.6 7.9"/>',
    sec_bnd: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
    sec_qa: '<path d="M4.5 12.5l4.5 4.5L19.5 6.5"/>',
    sec_ops: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    objmgr: '<rect x="3.5" y="4" width="7" height="7" rx="1.5"/><rect x="13.5" y="4" width="7" height="7" rx="1.5"/><rect x="3.5" y="14" width="7" height="6" rx="1.5"/><rect x="13.5" y="14" width="7" height="6" rx="1.5"/>',
    semrules: '<rect x="4" y="3.5" width="16" height="5" rx="1.5"/><rect x="4" y="10" width="16" height="5" rx="1.5"/><rect x="4" y="16.5" width="16" height="4" rx="1.5"/>',
    lexicon: '<path d="M5 4.5h10.5a3 3 0 0 1 3 3V20H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h10.5"/><path d="M9 8.5h6"/>',
    versions: '<path d="M12 8v4l2.5 2.5"/><path d="M3.5 12a8.5 8.5 0 1 0 2.5-6"/><path d="M3 4.5V9h4.5"/>',
    ruleagent: '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/><path d="M18.5 15l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8z"/>',
    home: '<path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12V9.5"/><path d="M10 20v-5h4v5"/>',
    inbox: '<path d="M4 13l2.5-8h11L20 13v6H4z"/><path d="M4 13h5l1 2.5h4l1-2.5h5"/>',
    records: '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    graph: '<circle cx="6" cy="7" r="2.3"/><circle cx="18" cy="6" r="2.3"/><circle cx="12" cy="18" r="2.3"/><path d="M8.2 7.6l7.5-1.2M7.3 9l3.6 7M16.8 8.1l-3.6 7.9"/>',
    mgrules: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M9 9.5v10"/>',
    changes: '<circle cx="6.5" cy="6" r="2.2"/><circle cx="6.5" cy="18" r="2.2"/><circle cx="17.5" cy="18" r="2.2"/><path d="M6.5 8.2v7.6M17.5 15.8V10a3 3 0 00-3-3H10"/><path d="M12 5l-2 2 2 2"/>',
    model: '<rect x="3" y="4" width="6" height="16" rx="1.5"/><circle cx="14" cy="8" r="2.2"/><circle cx="19" cy="16" r="2.2"/><path d="M15.6 9.7l2.2 4.4"/>',
    explorer: '<path d="M3 6.5a1.5 1.5 0 011.5-1.5H9l2 2h8.5A1.5 1.5 0 0121 8.5v9a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 17.5z"/><path d="M7 11h6M7 14.5h9"/>',
    map: '<path d="M9 4L3 6.5v13L9 17l6 2.5 6-2.5v-13L15 6.5z"/><path d="M9 4v13M15 6.5v13"/>',
    docs: '<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><circle cx="10" cy="13" r="1.4"/><circle cx="15" cy="16" r="1.4"/><path d="M11.2 13.8l2.6 1.4"/>',
    vectors: '<path d="M4 20l7-7M4 20h6M4 20v-6"/><path d="M12 12l8-8M20 4h-6M20 4v6"/>',
    adapters: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M16.5 16.5L21 21"/><path d="M8 11h6"/>',
    rules: '<path d="M4 6h10M4 12h16M4 18h7"/><circle cx="18" cy="6" r="2"/><circle cx="15" cy="18" r="2"/>',
    connect: '<path d="M10 14l4-4"/><path d="M9 7l1.5-1.5a4 4 0 0 1 5.7 5.7L15 12.5"/><path d="M15 17l-1.5 1.5a4 4 0 0 1-5.7-5.7L9 11.5"/>',
    guide: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M10 9.2v5.6l4.8-2.8z"/>',
    flow: '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="5" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M7.5 12h4M11.5 12V5h5M11.5 12v7h5"/>',
    data: '<path d="M4 20l1-4L16 5l3 3L8 19z"/><path d="M14 7l3 3"/>',
    library: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="16" rx="1"/><path d="M17 5.5l3.5-1 3 15-3.5 1z"/>',
    onto: '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7 7.5l3.6 8.3M17 7.5l-3.6 8.3M7.5 6h9"/>',
    query: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 4l-4 16"/>',
    decide: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    check: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 12l3 3 5-6"/>',
    bind: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    sources: '<rect x="4" y="4" width="16" height="6" rx="1.5"/><rect x="4" y="14" width="16" height="6" rx="1.5"/><path d="M8 7h.01M8 17h.01M12 10v4"/>',
    objects: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12L4 7.5M12 12v9"/>',
    props: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/><circle cx="4.5" cy="18" r="1.2"/>',
    links: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
    monitor: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12.5l9 5 9-5"/><path d="M3 17l9 5 9-5"/>',
    catalog: '<path d="M3 7.5a2 2 0 012-2h4.2l2 2.2H19a2 2 0 012 2V18a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
    db: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 01-12 0zM12 17v4"/>',
    convert: '<path d="M4 8h13l-3.5-3.5M20 16H7l3.5 3.5"/>',
  };
  const UI = {
    chevron: '<path d="M6 9l6 6 6-6"/>',
    inbox: '<path d="M4 13l2.5-8h11L20 13v6H4z"/><path d="M4 13h5l1 2.5h4l1-2.5h5"/>',
    fold: '<path d="M14.5 6.5L9 12l5.5 5.5"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1"/>',
    upload: '<path d="M12 16V5M7.5 9.5L12 5l4.5 4.5"/><path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3"/>',
    reload: '<path d="M20 11a8 8 0 10-2.3 6.3"/><path d="M20 5v6h-6"/>',
    up: '<path d="M12 19V6M6.5 11.5L12 6l5.5 5.5"/>',
    plus: '<path d="M3 7.5a2 2 0 012-2h4.2l2 2.2H19a2 2 0 012 2V18a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M12 11.5v5M9.5 14h5"/>',
    more: '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    catalog2: '<path d="M3 7.5a2 2 0 012-2h4.2l2 2.2H19a2 2 0 012 2V18a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  };
  const ui = (k) => `<svg class="ui" viewBox="0 0 24 24" aria-hidden="true">${UI[k]}</svg>`;
  const NAV = [['home', '홈'], ['inbox', '할 일'], ['records', '레코드 탐색'], ['record', '레코드'], ['changes', '변경 요청'], ['graph', '레코드 그래프'], ['model', '그래프 탐색'], ['rules', '기준값 · 지표'], ['monitor', '파이프라인 관제'], ['guide', '사용 안내'], ['flow', '흐름 · 통과 조건'], ['explorer', '자산 탐색기'], ['map', '자산 그래프'], ['docs', '문서'], ['vectors', '벡터 · 임베딩'], ['adapters', '어댑터'],
    ['search', '질문'], ['connect', '외부 연동'], ['catalog', '자료 업로드'], ['db', 'DB 연결'], ['convert', '변환 결과'], ['sources', '데이터 소스'],
    ['data', '초안 생성'], ['objects', 'Entity'], ['props', 'Property 표'], ['links', 'Relation 표'], ['states', '상태 전이'], ['mgrules', '결정표'], ['mgfuncs', '함수'], ['actions', 'Action'], ['roles', '권한'], ['library', '모듈 라이브러리'], ['onto', '전체 보기'],
    ['query', '질의'], ['decide', '처리 요청'], ['check', '검증 질문'], ['bind', 'DB 대조'], ['objmgr', 'Object'], ['ruleagent', '규칙 생성 Agent'], ['versions', '버전 이력'], ['lexicon', '용어 사전'], ['semrules', '규칙 카드']];
  const SECTION = [['home', '홈'], ['sem', 'Semantic Layer'], ['ont', 'Ontology'], ['bnd', 'Data Binding'], ['qa', 'Quality'], ['ops', 'Operations']];
  const REPO_TABS = new Set(['convert', 'data', 'explorer', 'map', 'docs', 'vectors']);  // where the repository decides what is shown (the catalog names it in its own head)
  const NO_TAB = new Set(['record', 'inbox']);  // screens reached from another (a record from its list, 할 일 from the top bar and the home)
  // a tab sits under its screen, so it does not repeat the screen's word; screens of one thing are one tab with a switch
  const TAB_WORD = { semrules: '규칙 카드', mgrules: '결정표', rules: '기준값 · 지표', mgfuncs: '함수', actions: 'Action 정의', decide: '처리 요청', changes: '변경 요청', versions: '버전 이력', library: '모듈 라이브러리', model: '다이어그램', onto: '전체 보기', objects: 'Entity · Property · Relation', states: '상태 전이', docs: '문서', graph: '레코드 그래프', records: '레코드 탐색', monitor: '관제', catalog: '자료 업로드', db: 'DB 연결', data: '초안 생성', convert: '변환 결과', sources: '데이터 소스', bind: 'DB 대조', adapters: '어댑터', vectors: '벡터 · 임베딩', connect: '외부 연동', check: '검증 질문', flow: '흐름 · 통과 조건', search: '질문해 보기', explorer: '자산 탐색기', map: '자산 그래프' };
  const TABLE_TABS = ['objects', 'props', 'links'];
  const tabWord = (tab) => TAB_WORD[tab] || navLabel(tab);
  const KIND = { database: 'DB', table: '테이블', column: '컬럼', folder: '폴더', file: '파일', document: '문서', collection: '문서 컬렉션', object: 'Entity', property: 'Property', link: 'Relation', query: '질의',
    decision: '결정표', action: 'Action', role: '접근 정책', agent: 'Agent', workflow: '워크플로우', vector_store: '벡터 저장소', graph_store: '그래프 저장소', reasoner: '추론기', embedder: '임베딩 모델' };
  const KIND_TAB = { database: 'db', table: 'sources', column: 'sources', folder: 'catalog', file: 'catalog', document: 'docs', collection: 'vectors', object: 'objects', property: 'props', link: 'links',
    query: 'query', decision: 'decide', action: 'decide', vector_store: 'vectors', graph_store: 'adapters', reasoner: 'adapters', embedder: 'vectors' };
  const MAP_ORDER = ['Entity', 'Property', 'Relation', '질의', '결정표', 'Action', '접근 정책', 'Agent', '문서', '문서 컬렉션', '테이블', '컬럼', '파일', '저장소 어댑터'];
  const MAP_STORE = new Set(['vector_store', 'graph_store', 'reasoner', 'embedder']);
  const MAP_PARTS = [['데이터 소스', '파일, 폴더, DB, 테이블'], ['문서', '정책서, 안내문, 문서 컬렉션'], ['온톨로지', '업무 Entity'], ['저장소 어댑터', '벡터 · 그래프 저장소, 임베딩 모델, 추론기'], ['활용', '질의, 결정, Action, 역할']];
  const ELEMENT = { area: 'Object', object: 'Entity', property: 'Property', link: 'Relation', decision: '결정표', action: 'Action', query: '질의',
    question: '검증 질문', role: '접근 정책', interface: 'Interface', rule: '규칙', rule_card: '규칙 카드', term: '용어', states: '상태 전이', parameter: '기준값', function: '함수', metric: '지표', identity: '식별 통합', conflict: '출처 충돌' };
  const FINDING = { table: '테이블 없음', column: '컬럼 없음', type: '타입 불일치', key: '키 중복', required: '필수 값 누락',
    enum: '정의에 없는 값', orphan: '끊긴 관계' };
  // what to do about each kind of finding; the engine's own text stays below it for whoever fixes the source
  const FIX = { table: '테이블 이름 수정 · 데이터 소스에 테이블 추가',
    column: '컬럼 이름 수정 · 데이터 소스에 컬럼 추가 · 모듈 적용 해제',
    type: '자료형 수정 · 변환식 지정',
    key: '키 컬럼 재지정 · 중복 행 정리', required: '필수 해제 · 빈 값 입력',
    enum: '허용값 추가 · 값 정리', orphan: '연결 기준 컬럼 확인 · 끊긴 행 정리' };
  const findingText = (f) => `${FIX[f.kind] ? `<div style="font-size:12.5px">${esc(FIX[f.kind])}</div>` : ''}<div class="mono muted" style="font-size:12px">${esc(f.detail)}</div>`;
  const STATUS = { pending: ['warn', '승인 대기'], stale: ['warn', '실행 전 재검사 실패'], rejected: ['bad', '반려'], executed: ['ok', '데이터 소스 반영'],
    failed: ['bad', '외부 호출 실패 · 데이터 소스 복원'], rolled_back: ['b', '되돌림'] };
  const BACKEND_KIND = { sqlite: 'SQLite', postgres: 'PostgreSQL', mysql: 'MySQL', oracle: 'Oracle', mssql: 'SQL Server', dbapi: 'DB-API', rdflib: 'RDF', sparql: 'SPARQL 엔드포인트', neo4j: 'Neo4j', gremlin: 'Gremlin Server', gateway: '플랫폼 연결' };  // the kinds config.open_backend opens
  const CHANGE_STATUS = { pending: 'warn', approved: 'ok', rejected: 'bad' };
  const TEXT_LANG = [['sparql', 'SPARQL 1.1'], ['cypher', 'Cypher'], ['ir', '온톨로지 질의 IR (JSON)']];
  const STEP = {
    read: ['테이블 읽기', '파일별 테이블 생성과 컬럼 타입 판별'],
    objects: ['Entity와 키', '테이블별 Entity와 키 컬럼 지정'],
    properties: ['속성과 타입', '컬럼별 속성 타입과 허용값 지정'],
    links: ['Relation', '키 컬럼 이름과 값 일치 기준 Relation 추론'],
    queries: ['등록 질의', 'Entity 목록, 관계별 집계, 허용값별 집계 질의 생성'],
    rules: ['규칙 · 역할 · 검증', '상태 전이, 상태 변경 Action, 역할, 검증 질문, 지난 처리 결과로 만든 판정 표'],
    bindings: ['Binding', 'Entity · Property · Relation의 테이블과 컬럼 연결'],
  };
  const HIT_WORD = { first: '위 규칙부터 첫 적중 적용', collect: '적중한 규칙 모두 적용', priority: '우선순위가 높은 규칙 적용', unique: '하나만 적중해야 함' };
  const CARD = { many_to_one: 'N:1', one_to_many: '1:N', one_to_one: '1:1', many_to_many: 'N:M' };
  const TYPE_WORD = { integer: '정수', decimal: '소수', date: '날짜', datetime: '일시', boolean: '참 · 거짓', string: '문자열', enum: '문자열' };
  const FLOW = [
    ['source', '데이터 소스', '테이블과 행 수', 'catalog'],
    ['define', '온톨로지 정의', '적용 모듈과 Entity, 관계, 속성', 'library'],
    ['bind', 'DB 대조', '정의와 데이터 소스의 Schema · 데이터 대조', 'bind'],
    ['project', '그래프 저장소 반영', '데이터 소스의 Node · Edge 반영', 'onto'],
    ['index', '문서 · 벡터 색인', '문서를 나눠 벡터 저장소에 색인하고 검색 적중 확인', 'vectors'],
    ['query', '질의', 'Backend별 질의 변환과 결과 일치', 'query'],
    ['decide', '처리 요청', '결정표 판정과 승인 처리', 'decide'],
    ['check', '검증', '검증 질문 정답률', 'check'],
  ];

  const S = {
    st: null, tab: 'library', kind: 'all', libFocus: '', libScroll: false, ontoPick: '', impact: null, pos: {}, sel: null, gsel: null, obj: null,
    nopen: {}, lopen: false, xp: new Set(), explain: false,  // the shell: folded sidebar sections, the connection card, notes opened on a card, notes always shown
    ru: null, met: {}, sp: null, sr: { text: '', folder: '', res: null, busy: false, more: null, moreBusy: false, fb: '', di: 0, fix: null, tab: '' }, dg: null, dsec: null, dq: null, dgx: { nodes: {}, edges: [], seed: '', layout: 'radial', zoom: 1, pos: {}, hide: [], sel: '', of: null }, dfolder: '', drel: null, djob: null, dreader: '',
    vs: { kind: 'qdrant', url: '' }, gw: { url: '', connection: '', dialect: 'postgres', token: '' }, ad: null, adrep: null, adbusy: false, adrs: null,
    ex: { tree: null, items: null, node: '', open: { 'group:repos': true }, tab: 'store', q: '', kind: '', hits: null, sel: {}, tsel: {}, edit: null, moving: null, busy: false, loading: false, error: '' }, amap: null, mapn: null, mapsel: null, mappos: {}, conn: null, links: null, ltab: 'store', help: false,
    q: { mode: 'list', name: null, params: {}, role: '', principal: {}, target: 'sql:postgres', res: null, code: false, props: {},
      b: { type: '', link: '', fields: [], conds: [], name: '', label: '' },
      lang: 'sparql', text: '', dirty: false, question: '', busy: false },
    d: { name: null, key: null, keys: {}, res: null, proposal: null, params: {}, role: '', audit: [], busy: false },
    qa: null, bind: null, fl: null, files: null, dpos: {}, guide: null,
    dr: { step: 0, view: 'objects', sel: null, busy: false, timer: 0, label: '', dsn: '', rules: null, tables: {}, rev: null, graph: null,
      choice: {}, names: {}, ok: {}, seen: {}, tbl: {}, pick: '', setup: false, rv: 'bind',
      ed: { drop: {}, labels: {}, keys: {}, types: {}, values: {}, card: {}, add: [] }, add: { source: '', property: '', target: '', label: '' } },
    ed: null, me: null, change: null, changes: null, flset: null, agree: null, ident: null,
    map: { standards: null, picked: [], sug: null, edits: { objects: {}, columns: {} }, busy: false, auto: '' },
    pol: { open: false, text: '', target: '', busy: false, res: null },
    ind: { target: '', inputs: {} },
    mg: { st: null, busy: false, sel: '', form: null, q: '', obj: '', table: '', open: false, keep: false, qt: 0, review: null },
    cat: null, conv: null, pick: false, menu: null, pal: null, seen: {}, slim: false, om: { tier: 'all', q: '', sel: '' }, lx: { st: null, busy: false, q: '', show: 'all', sel: '', form: null, imp: null }, sem: { st: null, busy: false, layer: 'all', type: '', sel: '' },
    mon: { st: null, timer: 0, rtt: [], focus: '', busy: false, fault: 0, shape: '' },
    home: { role: 'ops', box: null, busy: false, tab: 'assigned', q: '', ov: null, ovBusy: false },
    rec: { type: '', key: '', res: null, busy: false, err: '', act: '', role: '', seeAs: '', params: {}, fn: {}, tab: 'overview' },
    rl: { type: '', q: '', res: null, busy: false },
    chg: { sel: '', det: null, busy: false, item: '', text: '' },
    lib: { open: false, start: 'files', label: '', key: '', files: null, mods: null, busy: false, up: false, res: null },  // a library being made on the page
    cn: {},  // which settings texts of the connection ways are open
    sim: { dec: '', key: '', vals: {}, res: null, busy: false, err: '' },
    gx: { nodes: {}, edges: [], links: {}, sel: '', route: [], routeEdges: [], err: '', busy: false, seed: { type: '', key: '' }, to: { type: '', key: '' }, pos: {},
      q: '', toq: '', fromq: '', from: null, found: null, hide: [], view: '', viewRole: '', log: [], info: {}, layout: 'layered', zoom: 1, open: [], views: null, color: {}, labelBy: {} },
    ov: { sel: '', pos: {} },
    md: { sel: '', q: '', tab: 'form', file: null, fileBusy: false, uses: null, pos: {}, fold: false, yaml: null, yamlBusy: false, notes: null, note: '', trial: null, trialOpen: false,
      view: 'diagram', arrive: '', cq: { objects: '', props: '', links: '' }, left: 'objects', leftOff: false, rightOff: false, list: 'props', hot: null, draft: null, only: false, src: {}, data: null, wide: true, posFor: '' },
    iss: { list: null, busy: false, open: '', preview: null, done: null, running: false, at: '', gates: null },
    fix: null, land: null, hit: '', hitDone: '',
  };
  const NEW_CAT = () => ({ st: null, folder: '', sel: {}, sort: 'name', dir: 1, ext: '', busy: false, up: null, file: null, view: 'preview', edit: null, paste: null });
  S.cat = NEW_CAT();

  const $ = (s, root = document) => root.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const show = (v) => {
    if (v === null || v === undefined || v === '') return '<span class="muted">-</span>';
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'number') return v.toLocaleString('ko-KR', { maximumFractionDigits: 2 });
    if (typeof v === 'object') return esc(JSON.stringify(v));
    const s = String(v);
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) return esc(s.slice(0, 16).replace('T', ' '));
    return esc(s);
  };
  const showObj = (v) => {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      if (Object.keys(v).length === 1 && 'rows' in v) return `${show(v.rows)}행`;
      return Object.entries(v).map(([k, x]) => `<div><span class="muted mono">${esc(k)}</span> ${showObj(x)}</div>`).join('');
    }
    if (Array.isArray(v)) return v.map((x) => (x && typeof x === 'object' ? showObj(x) : show(x))).join(', ');
    return show(v);
  };
  const cellWord = (v) => (v === 'null' ? '값 없음' : v);
  const yesNo = (v) => (v === true ? '예' : v === false ? '아니요' : show(v));
  const plainText = (v) => (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v) ? v.slice(0, 10) : String(v ?? ''));
  const element = (id) => {
    const [kind, ...rest] = String(id).split(':');
    return `<span class="chip sm">${esc(ELEMENT[kind] || kind)} <span class="mono">${esc(rest.join(':'))}</span></span>`;
  };
  const elementText = (id) => { const [kind, ...rest] = String(id).split(':'); return `${ELEMENT[kind] || kind} ${rest.join(':')}`; };
  const modLabel = (name) => (S.st.library.find((r) => r.name === name) || {}).label || name;

  async function api(path, body) {
    const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Ontlas-Request': '1' }, body: JSON.stringify(body) };
    const r = await fetch('/api/' + path, opt);
    let j = {};
    try { j = await r.json(); } catch (_) { /* empty body */ }
    if (r.status === 401 && S.me && S.me.team && path !== 'login') { S.me.user = null; renderLogin(); }
    if (!r.ok) throw Object.assign(new Error(j.error || `서버 오류로 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요. (${r.status})`), { status: r.status, body: j });
    return j;
  }

  let toastTimer = 0;
  function toast(msg, bad = false) {
    const t = $('#toast');
    t.textContent = msg;
    t.className = 'toast' + (bad ? ' bad' : '');
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, bad ? 6000 : 3200);
  }
  const fail = (e) => toast(e.message || String(e), true);

  async function load() {
    if (!S.me) { try { S.me = await api('me'); } catch (_) { S.me = { team: false, user: null }; } }
    if (S.me.team && !S.me.user) { renderLogin(); return; }
    if (!S.guide) { try { S.guide = await api('guide'); } catch (_) { S.guide = { video: '', chapters: [] }; } }
    S.st = await api('state');
    if (S.sel && !S.st.graph.nodes.some((n) => n.id === S.sel)) { S.sel = null; S.obj = null; }
    render();
    if (!S.home.box && !S.home.busy) loadInbox();  // the sidebar says how many things wait, whatever the screen
  }

  function stale() {
    S.q.res = null; S.d.res = null; S.d.proposal = null; S.d.keys = {}; S.qa = null; S.bind = null; S.obj = null; S.fl = null;
    S.mg.st = null; S.iss.list = null; S.home.box = null;
    S.home.sug = null; S.home.ov = null; S.ver = null; S.lx.st = null; S.sem.st = null; S.q.props = {}; S.md.trial = null;  // read from a definition that is no longer the one shown
    Object.assign(S.sim, { dec: '', key: '', vals: {}, res: null, err: '', auto: false });  // a record and a verdict of the space that was shown
  }

  // ---- frame ---------------------------------------------------------------------------------------------------

  const keep = (k, v) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch (e) { /* this visit only */ } };
  const noSource = () => !!(S.st && S.st.source && S.st.source.connected === false);
  // what a screen that reads rows says when there are none to read, with the one way on
  const noSourceCard = () => `<div class="card nosrc"><div class="cb"><b>연결된 데이터 소스가 없습니다</b><a class="btn sm primary" href="#catalog">데이터 연결</a></div></div>`;
  try {
    (localStorage.getItem('ontlas-nopen') || '').split(',').filter(Boolean).forEach((k) => { S.nopen[k] = true; });
    S.explain = localStorage.getItem('ontlas-explain') === '1';
  } catch (e) { /* the defaults stand */ }
  document.body.classList.toggle('explain', S.explain);

  // notes a person can do without (class xp) fold behind an (i) on the card they sit in; a card with no title keeps them shown
  function declutter() {
    const main = $('#main');
    if (!main) return;
    main.querySelectorAll('.xp').forEach((x) => {
      const box = x.closest('.card, .xpbox');
      const head = box && box.querySelector(':scope > .ch, :scope > .xph');
      if (!box) {  // a note of the page itself hangs on the page title
        const h1 = main.querySelector('.head h1');
        if (!h1) { x.classList.remove('xp'); return; }
        x.classList.add('pg');
        if (!h1.querySelector('.info')) {
          const key = `${S.tab}:page`, on = S.xp.has(key);
          h1.insertAdjacentHTML('beforeend', `<button class="info" data-act="info" data-k="${esc(key)}" data-pg="1" aria-expanded="${on}" aria-label="설명 보기" title="설명">i</button>`);
          main.classList.toggle('pgo', on);
        }
        return;
      }
      if (!head || head.offsetParent === null) { x.classList.remove('xp'); return; }  // no title to hang the button on: the note stays in view
      if (box.dataset.xp) return;
      const key = `${S.tab}:${(head.firstChild && head.firstChild.textContent ? head.firstChild.textContent : head.textContent).trim().slice(0, 24)}`;
      box.dataset.xp = key;
      const on = S.xp.has(key);
      const btn = `<button class="info" data-act="info" data-k="${esc(key)}" aria-expanded="${on}" aria-label="설명 보기" title="설명">i</button>`;
      const right = head.querySelector(':scope > .right');
      if (right) right.insertAdjacentHTML('beforebegin', btn); else head.insertAdjacentHTML('beforeend', btn);
      box.classList.toggle('xpo', on);
    });
  }
  const curTab = () => (S.tab === 'model' && S.md.view === 'table' ? 'objects' : S.tab);  // the workspace's table is the Entity screen, its diagram 그래프 탐색
  // the XGEN wordmark, beside the product's name
  const XGEN_WORD = '<svg class="xword" viewBox="128 0 72 32" aria-hidden="true"><path d="M137.98 10.0889L140.191 6H147.779L142.142 15.9863L148.001 26H140.263L137.977 21.8135L135.708 26H128L133.806 15.9893L128.194 6H135.806L137.98 10.0889Z"/><path d="M196.336 8.0835V23.9173H194.102L185.984 12.3481H185.852V23.9173H183.419V8.0835H185.675L193.792 19.6745H193.947V8.0835H196.336Z"/><path d="M168.419 23.9173V8.0835H178.332V10.1611H170.821V14.9506H177.808V17.0064H170.821V21.8397H178.419V23.9173H168.419Z"/><path d="M160.847 13.0211C160.258 11.0945 158.842 9.92961 156.75 9.92961C154.091 9.92961 152.043 12.0802 152.043 16.0006C152.043 19.9209 154.07 22.0715 156.859 22.0715C159.376 22.0715 161.043 20.4362 161.086 17.8376H157.208V15.799H163.418V17.6359C163.418 21.7355 160.672 24.3342 156.837 24.3342C152.566 24.3342 149.668 21.1307 149.668 16.0006C149.668 10.8257 152.653 7.66699 156.728 7.66699C160.149 7.66699 162.764 9.8624 163.309 13.0211H160.847Z"/></svg>';
  function render() {
    if (!S.st) return;
    if (S.me && S.me.team && !S.me.user) return;  // signed out: the sign-in form stays, whatever finishes loading behind it
    renderTop();
    renderSide();
    const views = { graph: viewGraph, records: viewRecords, record: viewRecord, rules: viewRules, convert: viewConvert, data: viewData, onto: viewOnto, decide: viewDecide, states: viewStates, mgrules: viewMgRules, mgfuncs: viewMgFunctions };
    const main = $('#main');
    const v2 = V2[S.tab];
    const bleed = v2 ? !!v2.bleed : S.tab === 'model';  // a screen that fills the window to its edges (the diagram's workspace)
    main.classList.toggle('wsmode', bleed);
    main.classList.remove('pgo');
    $('#app').classList.toggle('ro', !canEdit());  // the older screens drop the edits the server would refuse (app.css)
    main.dataset.sec = ['home', 'inbox', 'records', 'record', 'graph', 'decide', 'search'].includes(S.tab) ? 'use' : groupOf(S.tab)[0];  // code names are left out of the screens people use the ontology on
    const kept = [...main.querySelectorAll('.wscolb')].map((x) => x.scrollTop);
    if (v2 && v2.may && !v2.may()) { main.innerHTML = `<div class="k-main">${noAccess()}</div>`; paintLayer(); return; }
    const body = v2 ? (v2.area === 'auth' || bleed ? '' : fixBar()) + v2.view() : (S.tab === 'model' ? '' : subTabs()) + fixBar() + (views[S.tab] || viewHome)();
    main.innerHTML = bleed || (v2 && v2.area === 'auth') ? body : `<div class="k-main">${body}</div>`;
    main.querySelectorAll('.wscolb').forEach((x, i) => { x.scrollTop = kept[i] || 0; });
    declutter();
    paintLayer();
    if (v2) { if (v2.after) v2.after(); landNow(); showHit(); return; }
    after();
  }

  function after() {
    if ((S.tab === 'home' || S.tab === 'inbox') && !S.home.box && !S.home.busy && !S.home.err) loadInbox();
    if (S.tab === 'home' && S.home.role !== 'domain' && !S.fl) loadHomeFlow();
    if (S.tab === 'home' && !S.home.ov && !S.home.ovBusy) loadOverview();
    if (S.tab === 'versions' && !S.ver) loadVersions();
    if (S.tab === 'lexicon' && !S.lx.st && !S.lx.busy) loadLexicon();
    if (S.tab === 'semrules' && !S.sem.st && !S.sem.busy) loadSemantic();
    if (S.tab === 'records' && !S.rl.res && !S.rl.busy) loadRecords();
    if (S.tab === 'graph' && $('#gxcanvas')) { mountGx(); gxPaint(); }
    if (S.tab === 'graph' && !S.gx.views) gxLoadViews();
    if (S.tab === 'model' && S.md.view === 'diagram') mountEr();
    if (S.tab === 'model') hotField();
    if (S.tab === 'model' && S.md.wantNew && S.mg.st && !S.mg.st.error) { S.md.wantNew = false; ACT.mdobjnew(); return; }  // came to define something by hand
    if (S.tab === 'model' && S.md.arrive && $(`#col-${S.md.arrive}`)) { $(`#col-${S.md.arrive}`).scrollIntoView({ block: 'nearest', inline: 'nearest' }); S.md.arrive = ''; }
    if (S.tab === 'model' && S.mg.st && !S.mg.st.error && !S.iss.list && !S.iss.busy) loadIssues().then(() => { if (S.tab === 'model') render(); });
    if (S.tab === 'record' && !S.rec.res && !S.rec.busy && !S.rec.err) loadRecord();
    if (S.tab === 'guide') mountGuide();
    if (S.tab === 'docs') mountDocs();
    if ((S.tab === 'rules' || S.tab === 'mgrules') && !S.ru) api('rules').then((x) => { S.ru = x; render(); }).catch(fail);
    if (S.tab === 'mgrules' && !S.agree) loadAgreement();
    if (S.tab === 'changes') {
      if (!S.changes) loadChanges();
      else if (S.changes.changes && S.chg.sel && (!S.chg.det || S.chg.det.id !== S.chg.sel) && !S.chg.busy) loadChange(S.chg.sel);
    }
    if (S.tab === 'data' && S.files && S.files.pending && S.map.standards) {
      const sig = ((S.files.pending.steps.find((x) => x.id === 'read') || {}).items || []).map((x) => x.table).join(',');
      if (S.map.auto !== sig) { S.map.auto = ''; S.map.sug = null; autoMatch(sig); }
    }
    if ((S.tab === 'vectors' || S.tab === 'search') && !S.sp) loadSpace();
    if (S.tab === 'explorer' && !S.ex.tree && !S.ex.loading) { S.ex.loading = true; loadExplorer().finally(() => { S.ex.loading = false; }); }
    if (S.tab === 'adapters' && S.ad) balanceAdapters();
    if (S.tab === 'adapters' && !S.ad) api('adapters').then((x) => { S.ad = x; render(); if (!S.adrep && !S.adbusy) adCheck(false); }).catch(fail);
    if (S.tab === 'connect' && !S.conn) api('integrations').then((x) => { S.conn = x; render(); }).catch(fail);
    if (S.tab === 'map') {
      if (!S.amap) api('space/map').then((x) => { S.amap = x; render(); }).catch((e) => { S.amap = { error: e.message }; render(); });
      else if (!S.amap.error) mountGraph($('#mapgraph'), S.amap, { key: 'map', pos: S.mappos, sel: () => S.mapsel, tag: (n) => KIND[n.table] || n.table, clear: () => { S.mapsel = null; S.mapn = null; const box = $('#mapside'); if (box) box.innerHTML = mapSide(); },
        pick: async (id) => { S.mapsel = id; drawGraph(); try { S.mapn = await api('space/map/node?node=' + encodeURIComponent(id)); $('#mapside').innerHTML = mapSide(); } catch (e) { fail(e); } } });
    }
    if (S.tab === 'monitor') mountMonitor();
    if (S.tab === 'flow' && !S.fl) loadFlow();
    if (S.tab === 'flow' && !S.flset) loadFlowSettings();
    if (S.tab === 'library' && !S.changes) loadChanges();
    if (S.tab === 'decide' && !S.agree) loadAgreement();
    if (S.tab === 'decide' && !S.pa) loadPending();
    if (S.tab === 'data') { if (!S.files) loadFiles(); else { mountDraftGraph(); if (S.me && S.me.team) refreshFiles(); } }
    if (S.tab === 'library' && S.libScroll) { S.libScroll = false; const row = $('#main tr.sel'); if (row) row.scrollIntoView({ block: 'center' }); }
    if (S.tab === 'onto' && S.ontoPick && $('#ontocanvas svg')) { const n = S.ontoPick; S.ontoPick = ''; ER_VIEW.onto.pick(n); }  // arrived here from an object named elsewhere
    if (S.tab === 'library' && !S.files) loadFiles();  // the documents a policy draft can start from
    if (S.tab === 'catalog') {
      if (!S.cat.st && !S.cat.busy) loadCatalog();
      const box = $('#cedit');
      if (box && document.activeElement !== box) { box.focus(); box.select(); }
    }
    if (S.tab === 'convert' && !S.conv) loadConvert();
    if (S.tab === 'onto') {
      if (!S.mg.st) { if (!S.mg.busy) loadManage().then(() => { if (S.tab === 'onto') render(); }); } else mountEr('onto');
      if (!S.sel) {
        const d = S.st.decisions[0];
        S.sel = (d && S.st.graph.nodes.some((x) => x.id === d.target)) ? d.target : (S.st.graph.nodes[0] || {}).id;
      }
      if (S.sel && (!S.obj || S.obj.name !== S.sel)) selectObject(S.sel, true);
      if (!S.ov.sel) S.ov.sel = S.sel;
    }
    if (S.tab === 'decide' && !S.d.res && !S.d.busy && S.st.decisions.length) startDecide();
    if (S.tab === 'check' && !S.qa) runChecks();
    if ((MG_TABS.includes(S.tab) || S.tab === 'check') && !S.mg.st && !S.mg.busy) loadManage();
    if (S.tab === 'bind' && !S.bind) runBindings();
    landNow();
    showHit();
  }

  // ---- the pages for people who use the ontology: a home, what waits on them, records one by one -------------------

  const HOME_ROLE = [['ops', '운영 담당'], ['domain', '도메인 전문가'], ['model', '모델러']];
  const INBOX_KIND = { action: ['warn', 'Action 승인'], change: ['b', '변경 요청'], conflict: ['bad', '충돌 선택'], check: ['', '점검'], workspace: ['', '변경 대기'], draft: ['b', '초안 적용'] };
  const INBOX_TAB = [['assigned', '나에게 할당'], ['mine', '내가 요청'], ['all', '전체']];
  let RECENT = [];
  try { RECENT = JSON.parse(localStorage.getItem('ontlas-recent') || '[]'); } catch (e) { RECENT = []; }
  try { S.home.role = localStorage.getItem('ontlas-role') || 'ops'; } catch (e) { S.home.role = 'ops'; }

  function remember(x, opened = true) {  // the records a person opened, newest first with how often, for the home and the record list
    const was = RECENT.find((y) => y.type === x.type && y.key === x.key);
    RECENT = [{ ...x, n: was ? (was.n || 1) + (opened ? 1 : 0) : 1, at: Date.now() }, ...RECENT.filter((y) => y !== was)].slice(0, 12);
    try { localStorage.setItem('ontlas-recent', JSON.stringify(RECENT)); } catch (e) { /* kept for this visit only */ }
  }
  const often = () => [...RECENT].sort((a, b) => (b.n || 1) - (a.n || 1) || (b.at || 0) - (a.at || 0));  // most opened first, latest among equals

  // the questions asked on this browser, newest first, so a person can ask one again
  const askedBefore = () => { try { return JSON.parse(localStorage.getItem('ontlas-asked') || '[]'); } catch (e) { return []; } };
  function rememberAsked(q) {
    try { localStorage.setItem('ontlas-asked', JSON.stringify([q, ...askedBefore().filter((x) => x !== q)].slice(0, 8))); } catch (e) { /* this visit only */ }
  }

  const recChip = (x) => `<button class="chip" data-act="rec" data-type="${esc(x.type)}" data-key="${esc(x.key)}">${esc(x.label || x.type)} ${esc(x.key)}${x.title ? ` · ${esc(x.title)}` : ''}</button>`;

  async function loadInbox() {
    S.home.busy = true;
    try { S.home.box = await api('inbox'); S.home.err = false; } catch (e) { S.home.box = null; S.home.err = true; }  // a failed load is not an empty list
    S.home.busy = false;
    $('#app').classList.toggle('ibfail', S.home.err);
    if (S.tab === 'home' || S.tab === 'inbox') render(); else { renderSide(); renderTop(); }
  }

  async function loadHomeFlow() {
    S.fl = { busy: true };
    try { S.fl = await api('flow'); S.fl.at = new Date().toTimeString().slice(0, 5); } catch (e) { S.fl = { error: e.message }; }
    if (S.home.ov) { S.home.ov = null; if (S.tab === 'home') loadOverview(); }  // the QA part reads the measurement the flow just took
    if (S.mg.st && !S.mg.busy) loadManage();  // and the Entities' levels read the database check it took
    if (S.tab === 'home' || S.tab === 'flow') render();
  }

  function inboxShown(tab) {
    const box = S.home.box || {}, items = box.items || [];
    if (tab === 'all' || (tab === 'assigned' && box.alone)) return items;
    return items.filter((x) => (tab === 'mine' ? x.mine : !x.mine));
  }

  function inboxRow(x) {
    const [cls, word] = INBOX_KIND[x.kind] || ['', x.kind];
    let meta = '', buttons = '';
    if (x.kind === 'action') {
      meta = [`${x.by}${x.by_kind === 'agent' && !/agent/i.test(x.by) ? ' · Agent' : ''} 요청`, x.change, x.failed.length ? `검사 미통과 ${x.failed.join(', ')}` : '판정 · 권한 검사 통과',
        x.delta || (x.outside ? '자동 승인 한도 밖' : '')].filter(Boolean).join(' · ');
      buttons = `<button class="btn sm" data-act="rec" data-type="${esc(x.target)}" data-key="${esc(x.key)}">레코드</button>${x.mine && !S.home.box.alone ? ''
        : `<button class="btn sm primary" data-act="ibapprove" data-id="${esc(x.id)}">승인</button><button class="btn sm" data-act="ibreject" data-id="${esc(x.id)}">반려</button>`}`;
    } else if (x.kind === 'change') {
      const d = x.diff || {};
      const worse = (x.worse || []).map((w) => `${w.label} ${w.rate ? pct(w.was) : w.was} → ${w.rate ? pct(w.now) : w.now}`).join(' · ');
      meta = `${x.by} 작성 · 사본 시험 ${x.passed ? '통과' : '미통과'} ${x.gates[0]}/${x.gates[1]}${worse ? ` · ${worse}` : ''} · 추가 ${d.added || 0} · 변경 ${d.changed || 0} · 제거 ${d.removed || 0}`;
      buttons = `<button class="btn sm" data-act="ibchange" data-id="${esc(x.id)}">검토</button>`;
    } else if (x.kind === 'check') {
      meta = x.detail;
      buttons = '<button class="btn sm" data-act="issopen" data-key="bind">조치 보기</button>';
    } else if (x.kind === 'conflict') {
      meta = x.detail;
      buttons = `<button class="btn sm" data-act="issopen" data-key="conflict:${esc(x.id)}">고르기</button>`;
    } else if (x.kind === 'draft') {  // a reviewed draft filed for applying: the approver applies it as it stands
      meta = `${x.by} 요청 · ${x.detail}`;
      buttons = `<a class="btn sm" href="#data">초안 보기</a>${canApplyDraft() ? `<button class="btn sm primary" data-act="drequestapply">적용</button><button class="btn sm" data-act="drequestdrop">반려</button>`
        : x.mine ? '<button class="btn sm" data-act="drequestdrop">요청 거두기</button>' : ''}`;
    } else {
      meta = `${x.detail} · ${selfApply() ? '[검토 후 적용]을 선택해야' : '변경 요청을 만들어야'} 반영됩니다`;
      buttons = '<a class="btn sm" href="#model?left=changes">변경 목록 열기</a>';
    }
    return `<div class="ibrow" data-row="${esc(x.kind)}:${esc(x.id)}"><span class="chip sm ${cls}">${esc(word)}</span><div class="ibmain"><b>${esc(x.title)}</b><div class="muted">${esc(meta)}</div></div><div class="ibact">${buttons}</div></div>`;
  }

  function inboxCard(limit) {
    const h = S.home, box = h.box;
    if (h.err) return '<div class="card"><div class="ch">할 일</div><div class="cb"><div class="empty">서버 응답 오류로 할 일을 불러오지 못했습니다. 다시 시도해 주세요.<div style="margin-top:10px"><button class="btn sm" data-act="ibretry">다시 시도</button></div></div></div></div>';
    if (!box) return '<div class="card"><div class="ch">할 일</div><div class="cb"><div class="empty"><span class="spin"></span>불러오는 중입니다.</div></div></div>';
    const tabs = INBOX_TAB.map(([k, w]) => `<button class="${h.tab === k ? 'on' : ''}" data-act="ibtab" data-k="${k}">${k === 'all' && S.me && S.me.team ? '팀 전체' : w} ${box.counts[k]}</button>`).join('');
    const shown = inboxShown(h.tab);
    const rows = (limit ? shown.slice(0, limit) : shown).map(inboxRow).join('');
    const more = limit && shown.length > limit ? `<div class="ibmore"><a href="#inbox">할 일 ${shown.length}건 모두 보기</a></div>` : '';
    return `<div class="card"><div class="ch">할 일${box.counts.assigned ? `<span class="chip sm bad">${box.counts.assigned}</span>` : ''}<div class="right"><div class="seg" style="margin:0">${tabs}</div></div></div>
      <div class="cb" style="padding:0">${rows || `<div class="empty" style="padding:18px 16px">${h.tab === 'mine' ? '요청한 일이 없습니다.' : '처리할 일이 없습니다.'}</div>`}${more}</div></div>`;
  }

  function opsCard() {
    const f = S.fl;
    if (!f || f.busy) return '<div class="card"><div class="ch">운영 상태</div><div class="cb"><div class="empty"><span class="spin"></span>통과 조건을 측정하는 중입니다.</div></div></div>';
    if (f.error) return `<div class="card"><div class="ch">운영 상태</div><div class="cb"><div class="hint warn">${esc(f.error)}</div></div></div>`;
    const gates = f.steps.flatMap((s) => s.gates);
    const passed = gates.filter((g) => g.passed).length;
    const step = (id) => f.steps.find((s) => s.id === id) || {};
    const conf = (step('query').conformance || {});
    const agree = (step('decide').agreement || {});
    const stat = (v, w) => `<div class="stat"><b>${v}</b><span>${w}</span></div>`;
    return `<div class="card"><div class="ch"><i class="dot ${f.passed ? 'ok' : 'bad'}"></i>운영 상태 ${f.passed ? '정상' : '확인 필요'}<div class="right"><a class="btn sm ghost" href="#monitor">관제</a></div></div>
      <div class="cb"><div class="hstats">${stat(`${passed} / ${gates.length}`, '통과 조건')}${stat(conf.queries ? `${conf.agree} / ${conf.queries}` : '-', '저장소 간 결과 일치')}${stat(agree.rate === undefined || agree.rate === null ? '-' : pct(agree.rate), '과거 판정 일치율')}${stat(step('check').accuracy === undefined || step('check').accuracy === null ? '-' : pct(step('check').accuracy), '검증 질문 정답률')}</div>
      ${gates.filter((g) => !g.passed).map((g) => `<button class="hint warn ihint" data-act="issopen" data-key="${esc(gateKey(g))}">${esc(g.label)} · 기준 ${esc(g.limit)} · 측정 ${g.value === null ? '-' : esc(Math.round(g.value * 1000) / 1000)}<span>조치 보기</span></button>`).join('')}</div></div>`;
  }

  function recentCard() {
    let list = often().slice(0, 5);
    if (!list.length) {  // nothing opened yet: the records the decisions are about
      if (!S.home.sug) {
        const t = (S.st.decisions[0] || {}).target;
        S.home.sug = { rows: [] };
        if (t) api(`records?type=${encodeURIComponent(t)}&limit=3`).then((x) => { S.home.sug = { rows: x.rows.map((r) => ({ type: t, key: r.key, label: x.label, title: x.title && r.fields[x.title] ? String(r.fields[x.title]) : Object.values(r.fields).filter((v) => v !== null && v !== '').slice(0, 2).map(String).join(' · ') })) }; if (S.tab === 'home') render(); }).catch(() => {});
      }
      list = S.home.sug.rows;
    }
    const rows = list.map((x) => `<button class="hrow" data-act="rec" data-type="${esc(x.type)}" data-key="${esc(x.key)}"><span class="rtag">${esc(x.label || x.type)}</span><b>${esc(x.key)}</b><span class="muted">${esc(x.title || '')}</span>${x.n > 1 ? `<span class="chip sm" title="이 브라우저에서 연 횟수">${x.n}회</span>` : ''}</button>`).join('');
    return `<div class="card"><div class="ch">${RECENT.length ? '자주 보는 레코드' : '추천 레코드'}<div class="right"><a class="btn sm ghost" href="#records">레코드 탐색</a></div></div><div class="cb" style="padding:6px 8px">${rows || '<div class="empty" style="padding:8px">최근 연 레코드가 없습니다.</div>'}</div></div>`;
  }

  function savedCard() {
    const checked = new Set(S.st.questions.map((q) => q.query).filter(Boolean));
    if (!S.ru && !S.home.ruBusy) { S.home.ruBusy = true; api('rules').then((x) => { S.ru = x; if (S.tab === 'home') render(); }).catch(() => {}).finally(() => { S.home.ruBusy = false; }); }
    const metrics = ((S.ru && S.ru.metrics) || []).slice(0, 3).map((m) => `<a class="hrow" href="#rules"><b>${esc(m.label || m.name)}</b><span class="chip sm" style="margin-left:auto">지표</span></a>`);
    const rows = [...askedBefore().slice(0, 2).map((q) => `<button class="hrow" data-act="homeask" data-q="${esc(q)}"><b>${esc(q)}</b><span class="chip sm" style="margin-left:auto">최근 질문</span></button>`),
      ...S.st.queries.slice(0, 5).map((q) => `<button class="hrow" data-act="homeq2" data-q="${esc(q.name)}"><b>${esc(q.label)}</b><span class="chip sm ${checked.has(q.name) ? 'ok' : 'b'}" style="margin-left:auto">${checked.has(q.name) ? '검증됨' : '등록 질의'}</span></button>`),
      ...metrics].join('');
    return `<div class="card"><div class="ch">저장된 질의<div class="right"><a class="btn sm ghost" href="#query">질의 ${S.st.queries.length}</a></div></div><div class="cb" style="padding:6px 8px">${rows || '<div class="empty" style="padding:8px">등록 질의가 없습니다.</div>'}</div></div>`;
  }

  async function loadOverview() {  // how far the space has come, read from what is here: maturity, the four parts, the Objects
    S.home.ovBusy = true;
    try { S.home.ov = await api('overview'); } catch (e) { S.home.ov = { error: e.message }; }
    S.home.ovBusy = false;
    if (S.tab === 'home') render();
  }

  // where a definition can start: none of the three needs data
  const START_WAYS = [['startmodel', '직접 정의', '데이터 없이 이름과 속성부터 만듭니다'], ['startlib', '표준에서 시작', '표준 모듈을 적용하고 차이만 더합니다'],
    ['startdata', '문서 · 데이터에서 초안', '정의서, 정책서, 테이블에서 초안을 만들어 검토합니다']];

  // ---- the home: how far the space has come, its four parts, its Objects ------------------------------------------
  const COMP_TAB = { semantic: ['sem', 'mgrules'], ontology: ['ont', 'objmgr'], binding: ['bnd', 'sources'], qa: ['qa', 'check'] };
  const COMP_TONE = { ok: 'ok', attention: 'warn' };
  const LV_WORD = ['L0 개념', 'L1 논리', 'L2 연결', 'L3 검증'];
  const levelBar = (levels, total) => {  // the Entities per level as one bar
    const n = total || levels.reduce((a, b) => a + b, 0) || 1;
    return `<span class="lvbar">${levels.map((c, l) => (c ? `<i class="lv${l}" style="width:${(c / n) * 100}%" title="${LV_WORD[l]} · Entity ${c}"></i>` : '')).join('')}</span>`;
  };

  function compCard(c) {
    const [sec, tab] = COMP_TAB[c.id] || ['', 'home'];
    const k = c.counts || {};
    const said = {
      semantic: [`결정표 ${count(k.decisions)}`, `규칙 ${count(k.rules)}`, `기준값 ${count(k.parameters)}`, `함수 ${count(k.functions)}`, `지표 ${count(k.metrics)}`],
      ontology: [`Object ${count(k.objects)}`, `Entity ${count(k.entities)}`, `관계 ${count(k.relations)}`, `속성 ${count(k.properties)}`],
      binding: [c.source && c.source.connected ? `데이터 소스 ${BACKEND_KIND[String(c.source.kind || '').toLowerCase()] || c.source.kind || ''}` : '데이터 소스 미연결',
        `연결된 Entity ${count(k.bound)} / ${count(k.entities)}`, `테이블 ${count(k.tables)}`],
      qa: [`검증 질문 ${count(k.questions)}`, `정답률 ${pct(c.accuracy)}`, `근거 제시 ${pct(c.grounded)}`, c.gates ? `통과 조건 ${c.gates.met} / ${c.gates.all}` : ''],
    }[c.id] || [];
    const more = c.id === 'semantic' && k.uncited ? `근거 없는 규칙 ${k.uncited}` : c.id === 'ontology' && k.definition_only ? `L0 Entity ${k.definition_only}`
      : c.id === 'binding' && c.check && (c.check.errors || c.check.warnings) ? `DB 대조 오류 ${c.check.errors} · 경고 ${c.check.warnings}` : c.id === 'qa' && k.failed ? `오답 ${k.failed}` : '';
    const word = (SECTION.find((x) => x[0] === sec) || [])[1] || c.title;
    return `<a class="hcomp" href="#${tab}" title="${esc(c.part || '')}"><span class="hch"><b>${esc(word)}</b><span class="chip sm ${COMP_TONE[c.status] || ''}">${esc(c.status_label)}</span></span>
      <span class="hcl">${said.filter(Boolean).map((x) => `<span>${esc(x)}</span>`).join('')}</span>${more ? `<span class="hcx">${esc(more)}</span>` : ''}</a>`;
  }

  function overviewCard() {
    const ov = S.home.ov;
    if (!ov) return '<div class="card hov"><div class="cb empty"><span class="spin"></span>현황을 불러오는 중입니다.</div></div>';
    if (ov.error) return `<div class="banner no"><div class="why">${esc(ov.error)}</div></div>`;
    const m = ov.maturity, lv = m.levels.map((x) => x.entities);
    const keys = m.levels.map((x) => `<span class="lvk"><i class="lv${x.level}"></i>${esc(x.label)} <b>${count(x.entities)}</b></span>`).join('');
    const ms = ov.milestones || [], next = ms.find((x) => x.state === 'next');
    const stones = ms.map((x) => `<span class="mst ${esc(x.state || '')}" title="${esc(x.detail || '')}"><b>${esc(x.label)}</b><span>${x.date ? esc(x.date.slice(5).replace('-', '.')) : '일정 미정'}${x.state === 'next' && x.days !== null ? ` · D-${x.days}` : ''}</span></span>`).join('');
    return `<div class="card hov"><div class="ch">온톨로지 현황<span class="chip sm b">${esc(ov.version.label)}</span><div class="right"><a class="btn sm ghost" href="#versions">버전 이력</a></div></div>
      <div class="cb hovtop"><div class="hmat"><div class="label">성숙도 · Object ${count(m.objects)} · Entity ${count(m.entities)}</div>${levelBar(lv, m.entities)}<div class="lvkeys">${keys}</div></div>
        ${stones ? `<div class="hstones"><div class="label">일정</div><div class="mstrip">${stones}</div></div>` : ''}</div>
      <div class="hcomps">${ov.components.map(compCard).join('')}</div></div>`;
  }

  // the Objects as tiles: name, tier, Entities, and how far they have come (the lowest level, and the spread)
  function objMapCard() {
    const ov = S.home.ov;
    if (!ov || ov.error || !ov.objects.length) return '';
    const named = ov.objects.filter((o) => o.name).sort((x, y) => (Number(x.tier) || 99) - (Number(y.tier) || 99)), loose = ov.objects.find((o) => !o.name);  // first tier first
    const steps = (o) => [0, 1, 2, 3].map((l) => {
      const at = o.levels.slice(l).reduce((a, b) => a + b, 0);  // Entities at this level or past it
      return `<i class="${at === o.count ? 'full' : at ? 'part' : ''}"></i>`;
    }).join('');
    const tile = (o) => `<button class="otile" data-act="homeobj" data-name="${esc(o.name)}" title="${esc(o.description || '')}">
      <span class="oth"><b>${esc(o.label)}</b>${o.tier ? `<span class="chip sm">${esc(o.tier)}차</span>` : ''}</span><span class="otn mono">${esc(o.name)}</span>
      <span class="otl"><span class="otsteps">${steps(o)}</span><b>${esc(LV[o.level] || '')}</b><span class="muted">Entity ${count(o.count)}</span></span></button>`;
    return `<div class="card"><div class="ch">Object <span class="chip sm">${count(named.length)}</span><div class="right"><a class="btn sm ghost" href="#objmgr">전체 보기</a></div></div>
      <div class="cb otiles">${named.map(tile).join('')}</div>${loose ? `<div class="cb otloose"><button class="chip sm" data-act="homeobj" data-name="">Object 미지정 Entity ${count(loose.count)}</button></div>` : ''}</div>`;
  }

  function startCard() {  // a space with nothing defined yet: where to start, none of the three needs data
    return `<div class="card bsteps"><div class="cb"><div class="bnext"><b>정의가 없습니다</b><span>시작 방법</span></div>
      <div class="bways">${START_WAYS.map(([act, title, what]) => `<button class="bway" data-act="${act}"><b>${title}</b><span>${what}</span></button>`).join('')}</div></div></div>`;
  }

  function viewHome() {
    const h = S.home;
    const name = (S.me && S.me.user && S.me.user.name) || '';
    const box = h.box;
    const f = S.fl && !S.fl.busy && !S.fl.error ? S.fl : null;
    const sub = '업무를 온톨로지로 정의하고, 그 정의로 질문에 답하고 판정합니다';
    const roles = `<label class="hrole"><span>보는 역할</span><select data-in="hrole" aria-label="보는 역할">${HOME_ROLE.map(([k, w]) => opt(k, w, h.role)).join('')}</select></label>`;
    const head = `<div class="head"><div><h1>${name ? `안녕하세요, ${esc(name)}님` : 'Ontlas'}</h1><div class="sub">${esc(sub)}</div></div><div class="right">${roles}</div></div>`;
    const recent = [...RECENT.slice(0, 3).map(recChip), ...askedBefore().slice(0, 3).map((q) => `<button class="chip" data-act="homeask" data-q="${esc(q)}">${esc(q.length > 24 ? `${q.slice(0, 23)}…` : q)}</button>`)].join('');
    const ask = `<div class="card hask"><div class="cb"><div class="srform"><input type="search" id="homeq" data-in="homeq" value="${esc(h.q)}" placeholder="레코드 · 정의 · 문서 검색 또는 질문, 예: 주문상품 I1001 반품 가능 여부" aria-label="검색 또는 질문"><button class="btn primary" data-act="homego">질문</button></div>
      ${recent ? `<div class="chips" style="margin-top:10px"><span class="muted" style="font-size:12px">최근</span>${recent}</div>` : ''}</div></div>`;
    const cols = {
      ops: [inboxCard(6) + recentCard() + objMapCard(), opsCard() + savedCard()],
      domain: [recentCard() + savedCard(), inboxCard(4) + objMapCard()],
      model: [objMapCard() + inboxCard(5), opsCard()],
    }[h.role] || [inboxCard(6) + objMapCard(), opsCard()];
    const start = h.ov && !h.ov.error && h.ov.maturity.entities === 0;
    return `${head}${ask}${start ? startCard() : overviewCard()}<div class="grid hgrid"><div class="hcol">${cols[0]}</div><div class="hcol">${cols[1]}</div></div>`;
  }

  // ---- records ------------------------------------------------------------------------------------------------------

  function recordTypes() {
    return S.st.graph.nodes.filter((n) => n.table);
  }

  async function loadRecords() {
    const r = S.rl;
    if (!r.type) {
      const d = S.st.decisions.find((x) => recordTypes().some((n) => n.id === x.target));
      r.type = d ? d.target : (recordTypes()[0] || {}).id || '';
    }
    if (!r.type) return;
    r.busy = true;
    try { r.res = await api(`records?type=${encodeURIComponent(r.type)}&q=${encodeURIComponent(r.q)}&limit=100`); } catch (e) { r.res = { error: e.message, rows: [], columns: [] }; }
    r.busy = false;
    if (S.tab === 'records') render();
  }

  function viewRecords() {
    const r = S.rl, res = r.res;
    const types = recordTypes();
    const head = pageHead('레코드 탐색', '타입별 레코드를 찾아 조회합니다.');
    if (noSource() || !types.length) return head + noSourceCard();
    const form = `<div class="card"><div class="cb"><div class="srform"><select data-in="rltype" aria-label="타입" style="width:auto;flex:none;min-width:180px">${types.map((n) => `<option value="${esc(n.id)}"${n.id === r.type ? ' selected' : ''}>${esc(n.label)} · ${esc(n.id)}</option>`).join('')}</select>
      <input type="search" id="rlq" data-in="rlq" value="${esc(r.q)}" placeholder="번호나 이름으로 찾기" aria-label="찾을 말"><button class="btn primary" data-act="rlgo">찾기</button></div>
      ${RECENT.length ? `<div class="chips" style="margin-top:10px"><span class="muted" style="font-size:12px">최근 본 레코드</span>${RECENT.slice(0, 6).map(recChip).join('')}</div>` : ''}</div></div>`;
    if (!res) return head + form + '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>';
    if (res.error) return head + form + `<div class="banner no" style="margin-top:12px"><div class="why">${esc(res.error)}</div></div>`;
    const cols = res.columns;
    const rows = res.rows.map((x) => `<tr class="click" data-act="rec" data-type="${esc(res.type)}" data-key="${esc(x.key)}"><td class="mono"><b>${esc(x.key)}</b></td>${cols.slice(1).map((c) => `<td>${show(x.fields[c])}</td>`).join('')}</tr>`).join('');
    // words that find nothing here but something in another type: one press moves the search there
    const other = (res.elsewhere || []).map((x) => `<button class="chip b" data-act="rlpick" data-type="${esc(x.type)}">${esc(x.label)} ${count(x.count)}${x.more ? '+' : ''}건</button>`).join('');
    const none = !res.q ? '레코드가 없습니다.' : `${esc(res.label)}에서 ${esc(res.q)} 검색 결과가 없습니다.${other ? `<div class="chips" style="justify-content:center;margin-top:10px"><span class="muted">다른 타입 결과</span>${other}</div>` : ''}`;
    return `${head}${form}<div class="card" style="margin-top:14px"><div class="ch">${esc(res.label)}<span class="chip sm">${count(res.total)}건</span><div class="right"><span class="muted" style="font-size:12px">${res.total > res.rows.length ? `처음 ${count(res.rows.length)}건 표시` : ''}</span></div></div>
      <div class="cb scroll" style="padding:0">${rows ? `<table class="tight"><tr>${cols.map((c) => `<th>${esc(res.labels[c])}</th>`).join('')}</tr>${rows}</table>` : `<div class="empty" style="padding:16px">${none}</div>`}</div></div>`;
  }

  function openRecord(type, key) {
    S.rec = { type, key: String(key), res: null, busy: false, err: '', act: '', role: '', params: {}, fn: {}, tab: 'overview' };
    const t = S.st.graph.nodes.find((n) => n.id === type);
    remember({ type, key: String(key), label: t ? t.label : type, title: '' });
    if (S.tab === 'record') render(); else location.hash = '#record';
  }

  async function loadRecord() {
    const r = S.rec;
    if (!r.type) {
      if (!RECENT.length) { location.hash = '#records'; return; }
      Object.assign(r, { type: RECENT[0].type, key: RECENT[0].key });
    }
    r.busy = true;
    try {
      r.res = await api(`record?type=${encodeURIComponent(r.type)}&key=${encodeURIComponent(r.key)}`);
      r.err = '';
      remember({ type: r.type, key: r.key, label: r.res.label, title: r.res.title || '' }, false);  // the same opening, now with its name
    } catch (e) { r.res = null; r.err = e.message; }
    r.busy = false;
    if (S.tab === 'record') render();
  }

  function recordValue(p) {
    if (p.value === null || p.value === undefined || p.value === '') return '<span class="muted">-</span>';
    const v = p.type === 'boolean' ? yesNo(p.value) : show(p.value);
    return `${v}${p.unit ? ` <span class="muted">${esc(p.unit)}</span>` : ''}${p.value_label ? ` <span class="muted">${esc(p.value_label)}</span>` : ''}`;
  }

  function recordHead(d) {
    const st = d.state, r = S.rec;
    const shown = d.props.filter((p) => !p.key && p.name !== (st && st.property) && p.value !== null && p.value !== '' && typeof p.value !== 'boolean').slice(0, 4);
    // the actions a role may request: with a role picked, the others are not shown at all
    const roles = [...new Map(d.actions.flatMap((a) => a.roles).map((x) => [x.name, x])).values()];
    const allowed = d.actions.filter((a) => !r.seeAs || a.roles.some((x) => x.name === r.seeAs));
    const acts = allowed.map((a) => `<button class="btn sm${a.ready ? ' primary' : ''}" data-act="recact" data-name="${esc(a.name)}"${a.ready ? '' : ` disabled title="지금 상태 ${esc(st ? st.now : '')}에서는 할 수 없습니다"`}>${esc(a.label)}</button>`).join('')
      + (roles.length && d.actions.length ? `<select data-in="recrole" class="rrole" aria-label="보는 역할"><option value="">모든 역할</option>${roles.map((x) => `<option value="${esc(x.name)}"${r.seeAs === x.name ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select>` : '')
      + (r.seeAs && allowed.length < d.actions.length ? `<span class="muted" style="font-size:12px">이 역할에 없는 Action ${d.actions.length - allowed.length}개 숨김</span>` : '');
    const fns = d.functions.map((f) => `<button class="btn sm" data-act="recfn" data-name="${esc(f.name)}">${esc(f.label)}</button>`).join('');
    let steps = '';
    if (st) {
      const next = (s) => st.next.find((n) => n.to === s);
      steps = `<div class="rsteps" aria-label="상태 전이">${st.states.map((s) => {
        const n = next(s);
        return `<span class="rstep${s === st.now ? ' on' : (n ? ' next' : '')}">${esc(s)}${s === st.now ? ' · 지금' : (n && n.action_label ? ` · '${esc(n.action_label)}'로 이동` : '')}</span>`;
      }).join('<i class="rline"></i>')}</div>`;
    }
    let form = '';
    const a = d.actions.find((x) => x.name === r.act);
    if (a) {
      if (!r.role) r.role = (a.roles[0] || {}).name || '';
      form = `<div class="ractform"><div class="label">${esc(a.label)} 요청 · 권한, 값, 상태 전이, 판정 조건을 검사한 뒤 ${a.approval ? '승인 대기로 접수합니다' : '바로 실행합니다'}</div>
        <div class="ractrow"><div class="field"><label>요청 역할</label><select data-in="rrole">${a.roles.map((x) => `<option value="${esc(x.name)}"${x.name === r.role ? ' selected' : ''}>${esc(x.label)}</option>`).join('') || '<option value="">요청할 수 있는 역할 없음</option>'}</select></div>
        ${a.params.map((p) => `<div class="field"><label>${esc(p.label || p.name)}</label><input type="text" data-in="rparam" data-k="${esc(p.name)}" value="${esc(r.params[p.name] ?? '')}"></div>`).join('')}</div>
        <div style="display:flex;gap:8px"><button class="btn primary" data-act="recreq" data-name="${esc(a.name)}">${esc(d.label)} ${esc(d.key)} ${esc(a.label)} 요청</button><button class="btn" data-act="recactx">취소</button></div></div>`;
    }
    const name = d.title || (d.named_by ? d.named_by.title : '');
    const ctx = (d.context || []).flatMap((c) => [c, ...c.next.map((n) => ({ ...n, deep: true }))]).slice(0, 3)
      .map((c) => `<button class="rlink" data-act="rec" data-type="${esc(c.type)}" data-key="${esc(c.key)}">${esc(c.type_label)} <b>${esc(c.key)}${c.title ? ` ${esc(c.title)}` : ''}</b>${c.sub ? ` <span class="muted">· ${esc(c.sub)}</span>` : ''}</button>`).join('');
    return `<div class="card rhead"><div class="cb"><div class="rtop"><span class="rtype">${esc(d.label)}</span>
      <div class="rmain"><div class="rtitle"><b>${esc(d.key)}${name ? ` · ${esc(name)}` : ''}</b>${!d.title && d.named_by ? `<span class="muted" style="font-size:12.5px">${esc(d.named_by.type_label)} ${esc(d.named_by.key)}의 이름</span>` : ''}${st ? `<span class="chip n">${esc(st.now)}</span>` : ''}</div>
        ${ctx ? `<div class="rmeta rctx">${ctx}</div>` : ''}
        <div class="rmeta">${shown.map((p) => `<span>${esc(p.label)} <b>${recordValue(p)}</b></span>`).join('')}</div></div>
      <div class="ract">${acts}${fns}</div></div>${steps}${form}</div></div>`;
  }

  function recordLinks(d, all) {
    const ones = new Set((d.context || []).map((c) => c.type));
    const row = (c, deep) => `<button class="lrow${deep ? ' deep' : ''}" data-act="rec" data-type="${esc(c.type)}" data-key="${esc(c.key)}"><span class="rtag">${esc(c.type_label)}</span>
      <span class="lmain"><b>${esc(c.key)}${c.title ? ` ${esc(c.title)}` : ''}</b>${c.sub ? `<span class="muted">${esc(c.sub)}</span>` : ''}</span><span class="muted" aria-hidden="true">→</span></button>`;
    const tree = (d.context || []).map((c) => row(c) + c.next.map((n) => row(n, true)).join('')).join('');
    const many = d.links.filter((l) => (l.count || l.error) && !(ones.has(l.type) && l.count === 1));
    const empty = d.links.filter((l) => !l.count && !l.error);
    const group = (l) => `<div class="lgrp"><div class="lgh"><b>${esc(l.type_label)}</b><span class="muted">${esc(l.label)} · ${l.count}${l.more ? '+' : ''}건</span></div>
      ${l.error ? `<div class="hint warn">${esc(l.error)}</div>` : `<div class="chips">${l.items.slice(0, all ? 50 : 6).map((i) => `<button class="chip" data-act="rec" data-type="${esc(l.type)}" data-key="${esc(i.key)}">${esc(i.key)}${i.title ? ` · ${esc(i.title)}` : ''}</button>`).join('')}${l.count > (all ? 50 : 6) ? `<span class="muted" style="font-size:12px">외 ${l.count - (all ? 50 : 6)}건</span>` : ''}</div>`}</div>`;
    return `<div class="card"><div class="ch">연결된 레코드<div class="right"><button class="btn sm ghost" data-act="recgraph">그래프로 보기</button></div></div><div class="cb">${tree ? `<div class="ltree">${tree}</div>` : ''}${many.map(group).join('')}${tree || many.length ? '' : '<div class="empty">연결된 레코드가 없습니다.</div>'}
      ${empty.length ? `<div class="muted" style="font-size:12px;margin-top:8px">연결 없음 · ${empty.map((l) => esc(l.type_label)).join(', ')}</div>` : ''}</div></div>`;
  }

  function recordSide(d, only) {
    const r = S.rec;
    const dec = d.decisions.map((x) => (x.error ? `<div class="hit"><b>${esc(x.label)}</b><div class="hint warn">${esc(x.error)}</div></div>`
      : `<div class="hit"><div class="hit-top"><b>${esc(x.label)}</b><span class="chip ${x.yes ? 'ok' : 'warn'}" style="margin-left:auto">${esc(x.verdict)}</span></div>
        <div class="hit-text">${esc(x.reason)}</div><div class="muted" style="font-size:12px">규칙 ${esc(x.matched.join(', ') || '-')}${x.cite ? ` · 근거 ${esc(x.cite)}` : ''}</div>
        <div><button class="btn sm" data-act="srdecide" data-name="${esc(x.name)}" data-key="${esc(d.key)}">처리 요청 열기</button></div></div>`)).join('');
    const computed = (d.computed || []).filter((c) => !c.error);
    const worked = new Set(computed.map((c) => c.name));
    const vals = computed.map((c) => ({ ...c, outputs: r.fn[c.name] && r.fn[c.name].ok && r.fn[c.name].outputs ? r.fn[c.name].outputs : c.outputs })).map((c) => `<div class="hit"><div class="hit-top"><b>${esc(c.label)}</b><span class="muted" style="font-size:11.5px">함수</span><b style="margin-left:auto">${Object.values(c.outputs).map((v) => (typeof v === 'number' ? show(v) : esc(String(v)))).join(' · ')}</b></div></div>`).join('');
    const fn = d.functions.filter((f) => !worked.has(f.name)).map((f) => {
      const out = r.fn[f.name];
      return `<div class="hit"><div class="hit-top"><b>${esc(f.label)}</b><span class="muted mono" style="font-size:11.5px">${esc(f.name)}</span><button class="btn sm" style="margin-left:auto" data-act="recfn" data-name="${esc(f.name)}">실행</button></div>
        ${out ? (out.ok ? `<div class="hit-text">${showObj(out.outputs !== undefined ? out.outputs : out)}</div>` : `<div class="hint warn">${esc(out.error)}</div>`) : ''}</div>`;
    }).join('');
    const docs = d.key_documents.map((x) => `<div class="hit"><div class="hit-top"><b>${esc(x.document)}</b><span class="muted">${esc(x.section)}</span><span class="chip sm b" style="margin-left:auto">번호 언급</span></div><div class="hit-text">${esc(x.text)}</div></div>`)
      .concat(d.documents.map((x) => `<div class="hit"><div class="hit-top"><b>${esc(x.document)}</b><span class="muted">${esc(x.section)}</span></div><div class="hit-text">${esc(x.text)}</div></div>`)).join('');
    const hist = d.history.map((x) => `<div class="hrow static"><i class="dot ${x.pending ? 'warn' : x.kind === 'source' ? '' : 'ok'}"></i><b>${esc(x.event)}</b><span class="muted">${x.at ? esc(dayOf(x.at)) : '처리 전'} · ${esc(x.actor)}${x.kind === 'agent' && !/agent/i.test(x.actor) ? ' (Agent)' : ''}${x.proposal ? ` · ${esc(x.proposal)}` : ''}</span></div>`).join('');
    const parts = {
      decide: `${dec || vals ? `<div class="card"><div class="ch">지금 판정하면<div class="right muted" style="font-size:12px;font-weight:600">열 때 계산 · 기록하지 않음</div></div><div class="cb">${dec}${vals}</div></div>` : ''}
        ${fn ? `<div class="card"><div class="ch">함수</div><div class="cb">${fn}</div></div>` : ''}`,
      docs: `<div class="card"><div class="ch">이 레코드를 다루는 문서</div><div class="cb">${docs || '<div class="empty">이 Entity를 언급한 문서가 없습니다.</div>'}</div></div>`,
      history: `<div class="card"><div class="ch">이력</div><div class="cb" style="padding:6px 8px">${hist || '<div class="empty" style="padding:8px">요청이나 승인 이력이 없습니다.</div>'}</div></div>`,
    };
    return only ? parts[only] : parts.decide + parts.docs + parts.history;
  }

  function viewRecord() {
    const r = S.rec, d = r.res;
    if (!d) {
      const head = pageHead('레코드', r.err ? '레코드를 열지 못했습니다' : '레코드를 불러오는 중입니다', '<a class="btn" href="#records">레코드 탐색</a>');
      return head + (r.err ? `<div class="banner no"><div class="why">${esc(r.err)}</div></div>` : '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>');
    }
    const props = d.props.map((p) => `<tr><td class="muted">${esc(p.label)}${p.key ? ' <span class="chip sm b">키</span>' : ''}</td><td><b>${recordValue(p)}</b>${p.mask ? ' <span class="chip sm warn">가림 대상</span>' : ''}${p.module && p.module_label && !['commerce', 'core'].includes(p.module) ? ` <span class="chip sm">${esc(p.module_label)}</span>` : ''}</td>
      <td class="mono muted" style="font-size:11.5px" title="${esc(p.expr || '')}">${p.expr ? '<span class="chip sm b">계산</span>' : esc(p.column)}</td></tr>`).join('');
    const crumbs = `<div class="rcrumb"><a href="#records">레코드 탐색</a><i>›</i><span>${esc(d.label)}</span><i>›</i><b>${esc(d.key)}</b></div>`;
    const nLinks = d.links.reduce((a, l) => a + (l.count || 0), 0);
    const nDocs = d.documents.length + d.key_documents.length;
    const tabs = [['overview', '개요', ''], ['links', '연결', nLinks], ['decide', '판정', d.decisions.length + (d.computed || []).length], ['docs', '문서', nDocs], ['history', '이력', d.history.length]]
      .map(([k, w, n]) => `<button class="${r.tab === k ? 'on' : ''}" role="tab" aria-selected="${r.tab === k}" data-act="rtab" data-k="${k}">${w}${n ? `<span class="n">${n}</span>` : ''}</button>`).join('');
    const propsCard = `<div class="card"><div class="ch">Property<div class="right"><span class="muted mono" style="font-size:12px">${esc(d.table || '')}</span></div></div><div class="cb scroll" style="padding:0"><table class="tight">${props}</table></div></div>`;
    const body = r.tab === 'links' ? recordLinks(d, true) : r.tab === 'decide' ? `<div class="hcol" style="max-width:860px">${recordSide(d, 'decide')}</div>`
      : r.tab === 'docs' ? recordSide(d, 'docs') : r.tab === 'history' ? recordSide(d, 'history')
        : `<div class="grid rgrid">${propsCard}${recordLinks(d)}<div class="hcol">${recordSide(d)}</div></div>`;
    return `${crumbs}${recordHead(d)}<div class="atabs rtabs" role="tablist" aria-label="레코드 보기">${tabs}</div>${body}`;
  }

  async function recordRequest(name) {
    const r = S.rec, a = r.res.actions.find((x) => x.name === name);
    const params = {};
    for (const p of a.params) params[p.name] = r.params[p.name] ?? '';
    const empty = a.params.filter((p) => p.required !== false && String(params[p.name]).trim() === '');
    if (empty.length) { toast(`${empty.map((p) => p.label || p.name).join(', ')} 값이 없어 요청하지 못했습니다. 값을 입력해 주세요.`, true); return; }
    try {
      const out = await api('request', { action: name, key: r.key, params, role: r.role, kind: 'human' });
      const said = { pending: '검사를 통과했습니다. 할 일에서 승인을 기다립니다.', executed: '자동 승인 기준을 충족해 바로 실행했습니다.' }[out.proposal.status];
      toast(said || `검사를 통과하지 못해 요청이 반려되었습니다. ${out.proposal.checks.filter((c) => !c.passed).map((c) => c.title).join(', ')}`, !said);
      S.home.box = null; S.pa = null; S.d.res = null; S.q.res = null; S.d.keys = {};
      r.act = ''; r.params = {}; r.res = null;
      if (out.proposal.status === 'executed') await load(); else render();
    } catch (e) { fail(e); }
  }

  async function inboxDecide(id, yes) {
    try {
      const out = await api('approve', { id, approve: yes });
      if (!out.ok) throw new Error(out.error);
      S.home.box = null; S.pa = null; S.rec.res = null; S.d.res = null; S.d.proposal = null; S.q.res = null; S.qa = null; S.fl = null; S.d.keys = {};
      await load();
      toast(yes ? 'Action 요청을 승인했습니다.' : 'Action 요청을 반려했습니다.');
    } catch (e) { fail(e); }
  }

  // ---- what the question was taken to be, and where its answer came from ----------------------------------------

  const ROUTE_BADGE = {
    decision: ['ok', '결정표로 판정 · 언어 모델 사용 안 함'], record: ['b', '레코드 조회 · 언어 모델 사용 안 함'],
    query: ['b', '등록 질의로 답함 · 검증된 경로'], documents: ['', '문서에서 찾은 근거'], none: ['bad', '모름 · 추측하지 않음'],
  };

  function answerBadge(res, more) {
    if (more && more.ok) return more.route === 'query' ? ['warn', 'AI가 만든 질의 · 검증 필요'] : ['warn', 'AI가 근거로 쓴 답 · 검증 필요'];
    return ROUTE_BADGE[res.route] || ['', res.route];
  }

  // 은/는, 이/가, 을/를, 으로/로, 과/와 by the last sound, a closing quote or bracket aside: a Hangul syllable by its final
  // consonant, a digit as it is read, capitals by their letter names (L M N R end in a consonant), any other Latin word
  // as it is said (…l · …m · …n · …ng end in one: Item을, Binding을, Order를, Sku를); ㄹ and l take 로
  function josa(word, withFinal, without) {
    const s = String(word ?? '').trim().replace(/['"’”)\]」』]+$/, '');
    const c = s.slice(-1);
    const code = c.charCodeAt(0);
    const roll = withFinal === '으로';
    if (code >= 0xac00 && code <= 0xd7a3) { const f = (code - 0xac00) % 28; return f && !(roll && f === 8) ? withFinal : without; }
    if (/\d/.test(c)) return (roll ? '036' : '013678').includes(c) ? withFinal : without;
    if (/[A-Z]{2}$|(^|[^A-Za-z])[A-Z]$/.test(s)) return 'MN'.includes(c) || (!roll && 'LR'.includes(c)) ? withFinal : without;
    if (/[a-z]$/i.test(s)) return /[mn]$|ng$/i.test(s) || (!roll && /l$/i.test(s)) ? withFinal : without;
    return without;
  }

  const pickedDecision = (res) => (res.decisions || [])[S.sr.di || 0] || null;

  function understood(res) {
    const d = pickedDecision(res), rec = res.record;
    const fixable = !!(d || rec);
    const chip = (word, k) => (fixable ? `<button class="chip b" data-act="srfix" data-k="${k}" aria-expanded="${!!S.sr.fix}">${esc(word)}<span aria-hidden="true">▾</span></button>` : `<span class="chip b">${esc(word)}</span>`);
    const chips = [];
    if (d) chips.push(chip(`레코드 · ${d.target_label} ${d.key}`, 'key'), chip(`판정 · ${d.label}`, 'decision'), chip(`기준 시각 · ${d.at.replace('T', ' ')}`, 'at'));
    else if (rec) chips.push(chip(`레코드 · ${rec.label} ${rec.key}`, 'key'), ...((res.choices || []).length ? [chip('판정 · 없음', 'decision')] : []));
    else if (res.query) chips.push(chip(`등록 질의 · ${res.query.label}`));
    else chips.push(`<span class="chip">${res.route === 'none' ? '찾을 대상 없음' : '문서와 규칙에서 찾기'}</span>`);
    const hint = fixable ? '다르게 이해했다면 칩을 눌러 고친 뒤 다시 물을 수 있습니다.' : '레코드 번호나 등록 질의 이름을 넣으면 데이터에서 바로 답합니다.';
    return `<div class="understood"><span class="label">이렇게 이해했습니다</span>${chips.join('')}<span class="muted" style="font-size:12px">${hint}</span></div>${S.sr.fix && fixable ? fixRow(res) : ''}`;
  }

  // what a person corrects of how the question was taken: the record, the decision, the time days are counted to
  function fixRow(res) {
    const f = S.sr.fix, d = pickedDecision(res);
    const type = d ? d.target_label : res.record.label;
    return `<div class="srfix" role="group" aria-label="질문 고치기">
      <div class="field"><label for="srfkey">${esc(type)} 번호</label><input id="srfkey" type="text" data-in="srfkey" value="${esc(f.key)}"></div>
      <div class="field"><label for="srfdec">판정</label><select id="srfdec" data-in="srfdec"><option value="">판정 없이 값 보기</option>${(res.choices || []).map((c) => `<option value="${esc(c.name)}"${c.name === f.decision ? ' selected' : ''}>${esc(c.label)}</option>`).join('')}</select></div>
      ${f.decision ? `<div class="field"><label for="srfat">기준 시각</label><input id="srfat" type="datetime-local" data-in="srfat" value="${esc(f.at)}"></div>` : ''}
      <div class="srfixgo"><button class="btn sm primary" data-act="srrefix"${S.sr.busy ? ' disabled' : ''}>${S.sr.busy ? '<span class="spin"></span>묻는 중' : '다시 묻기'}</button><button class="btn sm" data-act="srfixx">취소</button></div>
      </div>`;
  }

  // ---- a change request, element by element ------------------------------------------------------------------------

  const MARK_WORD = { ok: ['ok', '승인'], fix: ['bad', '수정 요청'] };

  async function loadChange(id) {
    const c = S.chg;
    c.busy = true;
    try { c.det = await api(`change?id=${encodeURIComponent(id)}`); } catch (e) { c.det = { error: e.message }; }
    c.busy = false;
    if (S.tab === 'changes') render();
  }

  // ---- a decision table tried while it is edited ------------------------------------------------------------------

  async function simulateNow(key, inputs) {
    const s = S.sim;
    s.busy = true; render();
    try { s.res = await api('decide/simulate', { name: s.dec, key: key || '', inputs: inputs || {} }); s.err = ''; } catch (e) {
      s.err = e.message;
      s.key = s.res ? s.res.key : '';  // the picker goes back to the record whose values are on screen
    }
    s.busy = false;
    if (S.tab === 'mgrules') render();
  }

  function simCard(d) {
    const s = S.sim;
    if (s.dec !== d.name) { Object.assign(s, { dec: d.name, res: null, key: '', vals: {}, err: '' }); }
    const keys = (S.d.keys[d.target] || []).slice(0, 300);
    if (d.target && !S.d.keys[d.target]) keysFor(d.target).then(() => { if (S.tab === 'mgrules') render(); });
    if (d.target && !d.new && !s.key && keys.length && !s.busy && !s.res && !s.auto) { s.auto = true; s.key = keys[0].key; simulateNow(s.key, {}); }  // a table not applied yet reads no record
    const pick = d.target ? `<select data-in="simkey" aria-label="레코드" style="width:auto;min-width:150px"><option value="">레코드 고르기</option>${keys.map((k) => `<option value="${esc(k.key)}"${k.key === s.key ? ' selected' : ''}>${esc(k.key)}</option>`).join('')}</select>` : '';
    const r = s.res;
    const spec = Object.fromEntries(d.inputs.map((i) => [i.name, i]));
    const inputs = (r ? r.inputs : d.inputs.map((i) => ({ name: i.name, label: i.label, type: i.type, value: null }))).map((i) => {
      const v = s.vals[i.name] ?? (i.value === null || i.value === undefined ? '' : String(i.value));
      const known = (spec[i.name] || {}).values || [];
      const field = i.type === 'boolean' ? `<select data-in="simval" data-k="${esc(i.name)}"><option value="">값 없음</option>${[['true', '예'], ['false', '아니요']].map(([k, l]) => `<option value="${k}"${v === k ? ' selected' : ''}>${l}</option>`).join('')}</select>`
        : known.length ? `<select data-in="simval" data-k="${esc(i.name)}"><option value="">값 없음</option>${known.map((x) => `<option value="${esc(x)}"${v === String(x) ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select>`
          : `<input type="${['integer', 'decimal'].includes(i.type) ? 'number' : 'text'}" data-in="simval" data-k="${esc(i.name)}" value="${esc(v)}" placeholder="값 없음">`;
      return `<div class="simrow"><span>${esc(i.label)}</span>${field}</div>`;
    }).join('');
    let out = '';
    if (s.err) out = `<div class="hint warn">${esc(s.err)}</div>`;
    else if (r) {
      out = `<div class="simres"><span class="chip ${r.yes ? 'ok' : 'warn'}">${esc(r.verdict)}</span><span class="muted">규칙 ${esc(r.matched.join(', ') || '없음')}</span></div>${pathLine(r.path)}
        ${r.other.length ? `<div class="label" style="margin-top:10px">결과가 바뀌는 값</div>${r.other.map((o) => `<div class="muted" style="font-size:12.5px">${esc(o.label)} <b>${typeof o.value === 'boolean' ? yesNo(o.value) : esc(String(o.value))}</b> → ${esc(o.verdict)} (${esc(o.matched.join(', ') || '적중 없음')})</div>`).join('')}` : '<div class="muted" style="font-size:12.5px;margin-top:8px">결과가 바뀌는 단일 입력 없음</div>'}`;
    }
    return `<div class="card"><div class="ch">시뮬레이션${r && r.key ? `<span class="muted" style="font-weight:600;font-size:12px">레코드 ${esc(r.key)} 불러옴</span>` : ''}<div class="right">${pick}</div></div><div class="cb">
      <div class="hint xp" style="margin-bottom:10px">값을 바꿔 결정표가 어떻게 답하는지 봅니다. ${r && r.pending ? '대기 중인 변경을 반영한 결정표로 판정합니다. ' : ''}저장하거나 요청하지 않습니다.</div>${inputs}
      <button class="btn sm primary" data-act="simrun" style="margin-top:8px"${s.busy ? ' disabled' : ''}>${s.busy ? '<span class="spin"></span>판정 중' : '이 값으로 판정'}</button>${out ? `<div style="margin-top:12px">${out}</div>` : ''}</div></div>`;
  }

  // ---- a draft against the standards: which tables a standard already names -----------------------------------------

  function standardMatch(table) {
    const sg = S.map.sug;
    if (!sg || !sg.ok) return null;
    return sg.objects.find((o) => o.table === table) || null;
  }

  async function autoMatch(sig) {  // the draft's tables scored against every domain standard, once per set of tables
    const m = S.map;
    if (!m.standards || !m.standards.length) return;
    m.auto = sig;
    if (!m.picked.length) m.picked = m.standards.filter((s) => s.kind === 'domain').map((s) => s.name);
    if (!m.picked.length) return;
    try { m.sug = await api('draft/map', { standard: m.picked, edits: { objects: {}, columns: {} } }); } catch (e) { m.sug = { ok: false, error: e.message }; }
    if (S.tab === 'data') render();
  }

  // ---- records as a graph: start from one record, grow by relation, find what joins two -----------------------------

  const gxId = (type, key) => `${type}:${key}`;

  function gxAdd(n) {
    const id = gxId(n.type, n.key);
    const was = S.gx.nodes[id];
    S.gx.nodes[id] = { type: n.type, key: String(n.key), label: n.label || (was && was.label) || n.type, title: n.title || (was && was.title) || '' };
    return id;
  }

  function gxEdge(source, target, link, label, group) {
    const was = S.gx.edges.find((e) => e.source === source && e.target === target && e.link === link);
    if (was) {
      if (group && !was.groups.includes(group)) was.groups.push(group);
      if (!group) was.route = true;
      return;
    }
    S.gx.edges.push({ source, target, link, label, groups: group ? [group] : [], route: !group });
  }

  // where a graph starts or ends: a record found by its key or its name, of any type
  // ---- finding a record: as a person types, by key, name or definition ("VIP 고객"); Enter takes the best one --------

  const FIND_FIELD = { start: 'q', from: 'fromq', to: 'toq' };
  let findTimer = 0;

  function gxFindSoon(which) {
    clearTimeout(findTimer);
    findTimer = setTimeout(() => gxFind(which), 220);
  }

  async function gxFind(which, take) {
    const g = S.gx, q = String(g[FIND_FIELD[which]] || '').trim();
    if (!q) { g.found = null; gxFoundPaint(which); return; }
    let got;
    try { got = await api(`records/find?q=${encodeURIComponent(q)}&limit=8`); } catch (e) { got = { items: [], error: e.message }; }
    if (String(g[FIND_FIELD[which]] || '').trim() !== q) return;  // typed on since
    g.found = { which, ...got };
    if (take) { gxTake(which); return; }
    gxFoundPaint(which);
  }

  function gxTake(which) {  // Enter: the record the words name exactly, else the first one found
    const f = S.gx.found;
    if (!f || f.which !== which || !f.items.length) { toast('일치하는 레코드가 없어 선택하지 못했습니다. 다른 번호나 이름을 입력해 주세요.', true); return; }
    gxChoose(which, f.items[0]);
  }

  function gxChoose(which, x) {
    const g = S.gx;
    g.found = null;
    const word = `${x.type_label} ${x.key}${x.title ? ` ${x.title}` : ''}`;
    if (which === 'start') { g.q = word; gxStart(x.type, x.key); return; }
    if (which === 'from') { g.from = { type: x.type, key: x.key, label: x.type_label, title: x.title || '' }; g.fromq = word; }
    if (which === 'to') { g.to = { type: x.type, key: x.key }; g.toq = word; }
    gxPathPaint();
  }

  function gxFoundPaint(which) {
    const box = $(`#gxfound-${which}`);
    if (box) box.innerHTML = gxFound(which);
  }

  function gxFound(which) {
    const f = S.gx.found;
    if (!f || f.which !== which) return '';
    if (!f.items.length) return '<div class="muted" style="font-size:12px;margin-top:6px">일치하는 레코드가 없습니다.</div>';
    const head = f.type_label ? `<div class="muted" style="font-size:11.5px;margin:6px 0 2px">${esc(f.type_label)} ${count(f.total)}건 중</div>` : '';
    return `${head}<div class="gxfound">${f.items.map((x) => `<button class="hrow" data-act="gxfound" data-w="${which}" data-type="${esc(x.type)}" data-key="${esc(x.key)}" data-label="${esc(x.type_label)}" data-title="${esc(x.title || '')}"><span class="rtag">${esc(x.type_label)}</span><b>${esc(x.key)}</b><span class="muted">${esc(x.title || x.sub || '')}</span></button>`).join('')}</div>
      ${f.more ? `<button class="btn sm ghost" data-act="rpopen" data-w="${which}" style="margin-top:4px">더 많은 결과는 목록에서 찾기</button>` : ''}`;
  }

  function gxPathCard() {
    const g = S.gx;
    const sel = g.nodes[g.sel] && g.nodes[g.sel].type !== 'bundle' ? g.nodes[g.sel] : null;
    const from = g.from || (sel ? { type: sel.type, key: sel.key, label: sel.label, title: sel.title } : null);
    const fromWord = from ? `${from.label} ${from.key}${from.title ? ` ${from.title}` : ''}` : '';
    const field = (which, label, value, hold) => `<div class="field" style="margin-bottom:8px"><label for="gx${which}q">${label}</label>
      <div class="gxfield"><input type="search" id="gx${which}q" data-in="gx${which}q" value="${esc(value)}" placeholder="${hold}" autocomplete="off"><button class="iconbtn" data-act="rpopen" data-w="${which}" title="목록에서 찾기" aria-label="${label} 목록에서 찾기">☰</button></div><div id="gxfound-${which}">${gxFound(which)}</div></div>`;
    return `<div class="card"><div class="ch">경로 찾기</div><div class="cb">
      ${field('from', '시작', g.fromq || fromWord, '그래프에서 고르거나 입력')}${field('to', '도착', g.toq, '예: 카테고리 K3 니트, 니트')}
      <div style="display:flex;align-items:center;gap:8px"><button class="btn sm primary" data-act="gxpath"${g.busy || !g.to.key || !from ? ' disabled' : ''}>${g.busy ? '<span class="spin"></span>찾는 중' : '찾기'}</button>${g.route && g.route.length ? `<span class="muted" style="font-size:12px">${g.route.length - 1}단계 경로 1개</span>` : ''}</div>
      <div class="muted" style="font-size:11.5px;margin-top:6px">최대 5단계</div></div></div>`;
  }

  function gxPathPaint() {
    const box = $('#gxpathcard');
    if (box) box.innerHTML = gxPathCard(); else render();
  }

  // ---- a window to find a record among many: by type, by words or a definition, a page at a time ------------------

  async function rpLoad(more) {
    const r = S.rp;
    if (!r) return;
    r.busy = true; paintLayer();
    const offset = more ? r.items.length : 0;
    let got;
    try { got = await api(`records/find?q=${encodeURIComponent(r.q)}&type=${encodeURIComponent(r.type)}&limit=30&offset=${offset}`); } catch (e) { got = { items: [], error: e.message }; }
    if (!S.rp) return;
    r.items = more ? [...r.items, ...got.items] : got.items;
    Object.assign(r, { total: got.total, more: got.more, label: got.type_label, busy: false, error: got.error || '' });
    paintLayer();
  }

  function pickerBox() {
    const r = S.rp, types = recordTypes();
    const rows = r.items.map((x) => `<button class="rprow" data-act="rppick" data-type="${esc(x.type)}" data-key="${esc(x.key)}" data-label="${esc(x.type_label)}" data-title="${esc(x.title || '')}"><span class="rtag">${esc(x.type_label)}</span><b>${esc(x.key)}</b><span>${esc(x.title || '')}</span><span class="muted">${esc(x.sub || '')}</span></button>`).join('');
    const say = r.error ? `<div class="hint warn">${esc(r.error)}</div>` : r.busy && !r.items.length ? '<div class="empty"><span class="spin"></span></div>'
      : !r.items.length ? `<div class="empty">${r.q || r.type ? '일치하는 레코드가 없습니다.' : '레코드가 없습니다.'}</div>` : '';
    return `<div class="rpback" data-act="rpclose"></div><div class="rpbox" role="dialog" aria-label="레코드 찾기">
      <div class="rphead"><b>${{ start: '시작 레코드', from: '경로의 시작', to: '경로의 도착' }[r.which] || '레코드'} 찾기</b><button class="iconbtn" data-act="rpclose" aria-label="닫기">×</button></div>
      <div class="rpform"><select id="rptype" aria-label="타입"><option value="">모든 타입</option>${types.map((n) => `<option value="${esc(n.id)}"${n.id === r.type ? ' selected' : ''}>${esc(n.label)}</option>`).join('')}</select>
        <input type="search" id="rpq" value="${esc(r.q)}" placeholder="번호 · 이름 · 정의, 예: VIP 고객, I100" autocomplete="off"></div>
      <div class="muted" style="font-size:12px;padding:0 16px 8px">${r.label && r.total !== undefined ? `${esc(r.label)} ${count(r.total)}건${r.q ? ` · '${esc(r.q)}'` : ''}` : ''}</div>
      <div class="rplist">${rows}${say}${r.more ? `<button class="btn sm" data-act="rpmore"${r.busy ? ' disabled' : ''}>${r.busy ? '<span class="spin"></span>' : '더 보기'}</button>` : ''}</div></div>`;
  }

  // how a group of people like to see records, under a name the studio keeps for everyone (graph/views): which types
  // are shown, each type's colour, and the property that names a type's records
  const gxViews = () => S.gx.views || {};
  async function gxLoadViews() {
    if (S.gx.views) return;
    try { S.gx.views = (await api('graph/views')).views || {}; } catch (e) { S.gx.views = {}; }
    if (!S.gx.view) gxApplyRole();
    if (S.tab === 'graph') render();
  }
  function gxApplyRole() {  // the perspective kept for the role the person views as, when one is
    const bound = Object.entries(gxViews()).find(([, v]) => v.role && v.role === S.home.role);
    if (bound && S.gx.view !== bound[0]) gxApplyView(bound[0]);
  }
  function gxApplyView(name) {
    const v = gxViews()[name];
    S.gx.view = v ? name : '';
    S.gx.viewRole = v ? (v.role || '') : '';
    S.gx.hide = v ? [...(v.hide || [])] : [];
    S.gx.color = v ? { ...(v.color || {}) } : {};
    S.gx.labelBy = v ? { ...(v.label || {}) } : {};
    gxFetchLabels().then(() => { if (S.tab === 'graph') render(); });
  }
  async function gxFetchLabels() {  // the naming property of a perspective, read for the records on the canvas that lack it
    const by = S.gx.labelBy || {};
    const jobs = [];
    for (const [type, prop] of Object.entries(by)) {
      const keys = Object.values(S.gx.nodes).filter((n) => n.type === type && (n.altFor !== prop)).map((n) => n.key);
      if (!keys.length) continue;
      jobs.push(api(`records/labels?type=${encodeURIComponent(type)}&prop=${encodeURIComponent(prop)}&keys=${encodeURIComponent(keys.join(','))}`)
        .then((r) => { for (const n of Object.values(S.gx.nodes)) if (n.type === type) { n.alt = r.labels[n.key] === undefined ? '' : String(r.labels[n.key]); n.altFor = prop; } }).catch(() => {}));
    }
    for (const n of Object.values(S.gx.nodes)) if (n.alt !== undefined && !by[n.type]) { delete n.alt; delete n.altFor; }
    await Promise.all(jobs);
  }

  function gxViewCard() {
    const g = S.gx, views = gxViews();
    const types = [...new Set(Object.values(g.nodes).map((n) => n.type))].filter((t) => t !== 'bundle');
    const propsOf = (t) => ((S.mg.st && S.mg.st.properties) || []).filter((p) => p.object === t).map((p) => [p.name, p.label || p.name]);
    const rows = types.map((t) => {
      const [ink] = gxColor(t), node = S.st.graph.nodes.find((x) => x.id === t) || {};
      const props = propsOf(t);
      return `<div class="gxvrow"><label class="tick" style="margin:0"><input type="checkbox" data-in="gxshow" data-t="${esc(t)}"${g.hide.includes(t) ? '' : ' checked'}>${gxGlyph(t)}${esc(node.label || t)}</label>
        <input type="color" data-in="gxcolor" data-t="${esc(t)}" value="${esc(ink)}" aria-label="${esc(node.label || t)} 색" title="색">
        ${props.length ? `<select data-in="gxlabel" data-t="${esc(t)}" aria-label="${esc(node.label || t)} 라벨 속성" title="레코드를 부를 속성"><option value="">기본 이름</option>${props.map(([n, l]) => `<option value="${esc(n)}"${(g.labelBy || {})[t] === n ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>` : ''}</div>`;
    }).join('');
    if (!S.mg.st && types.length && !S.mg.busy) { S.mg.busy = true; api('manage').then((x) => { S.mg.st = x; }).catch(() => {}).finally(() => { S.mg.busy = false; if (S.tab === 'graph') render(); }); }
    return `<div class="card"><div class="ch">관점${g.view ? `<span class="chip sm b" style="margin-left:6px">${esc(g.view)}</span>` : ''}</div><div class="cb">
      ${Object.keys(views).length ? `<select data-in="gxview" aria-label="저장한 관점" style="width:100%;margin-bottom:8px"><option value="">저장한 관점 고르기</option>${Object.keys(views).map((k) => `<option value="${esc(k)}"${g.view === k ? ' selected' : ''}>${esc(k)}${views[k].role ? ` · ${esc(roleWord(views[k].role))}` : ''}${views[k].by ? ` · ${esc(views[k].by)}` : ''}</option>`).join('')}</select>` : ''}
      ${rows ? `<div class="gxticks">${rows}</div>` : '<div class="muted" style="font-size:12px">표시 중인 타입이 없습니다.</div>'}
      ${rows ? `<label class="field" style="margin:8px 0 0"><span>기본 적용 역할</span><select data-in="gxviewrole" aria-label="관점을 쓰는 역할">${[['', '정하지 않음'], ...HOME_ROLE].map(([k, w]) => opt(k, w, g.viewRole || '')).join('')}</select></label>` : ''}
      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap"><button class="btn sm" data-act="gxviewsave"${rows ? '' : ' disabled'}>관점 저장</button>${g.view ? '<button class="btn sm ghost danger" data-act="gxviewforget">관점 삭제</button>' : ''}<button class="btn sm" data-act="gxlink"${g.seed.key ? '' : ' disabled'}>링크 복사</button></div></div></div>`;
  }

  function gxInfo(id) {  // what the side says of a record: a few values and what the rules say of it now
    const n = S.gx.nodes[id];
    if (!n || n.type === 'bundle' || S.gx.info[id]) return;
    S.gx.info[id] = { busy: true };
    api(`record?type=${encodeURIComponent(n.type)}&key=${encodeURIComponent(n.key)}`)
      .then((r) => { S.gx.info[id] = r; }).catch((e) => { S.gx.info[id] = { error: e.message }; })
      .finally(() => { const side = $('#gxside'); if (side && S.gx.sel === id) side.innerHTML = gxSide(); });
  }

  // ---- the record graph drawn as boxes: each record by its type, key and name; each relation by its name; a found path
  //      in orange. Laid out in layers by distance from where it started, or in rings around it ----------------------

  const GX = { h: 30, padX: 12, gapX: 64, gapY: 18, ring: 170, pad: 24 };
  const GX_COLOR = [['#1a73e8', '#eaf2fe'], ['#12805c', '#e7f6ef'], ['#c2410c', '#fff1e6'], ['#7c3aed', '#f3edff'], ['#0e7490', '#e6f6f9'],
    ['#b42318', '#fdecea'], ['#a16207', '#fdf6dc'], ['#475467', '#f2f4f7']];
  const textW = (t) => [...String(t)].reduce((a, c) => a + (c.charCodeAt(0) > 0x1100 ? 12.4 : 7), 0);

  function gxColor(type) {
    if (type === 'bundle') return ['#667085', '#ffffff'];
    const own = (S.gx.color || {})[type];
    if (own) return [own, `${own}1f`];  // the perspective's colour, with a light fill of the same hue
    const i = S.st.graph.nodes.findIndex((n) => n.id === type);
    return GX_COLOR[(i < 0 ? 0 : i) % GX_COLOR.length];
  }
  // each type an outline of its own as well as a colour, so types tell apart when colours are alike or printed grey
  const GX_SHAPE = ['pill', 'box', 'hex', 'slant', 'round', 'tag'];  // six shapes against eight colours: no two of the first 24 types share both
  function gxShape(type) {
    if (type === 'bundle') return 'pill';
    const i = S.st.graph.nodes.findIndex((n) => n.id === type);
    return GX_SHAPE[(i < 0 ? 0 : i) % GX_SHAPE.length];
  }
  function gxShapeSvg(type, b, fill, ink, k = gxShape(type)) {
    const st = `style="fill:${fill};stroke:${ink}"`, { x, y, w, h } = b;
    if (k === 'box') return `<rect class="shape" x="${x}" y="${y}" width="${w}" height="${h}" rx="4" ${st}/>`;
    if (k === 'round') return `<rect class="shape" x="${x}" y="${y}" width="${w}" height="${h}" rx="9" ${st}/>`;
    if (k === 'hex') { const d = Math.min(10, h / 2); return `<path class="shape" d="M${x + d},${y} H${x + w - d} L${x + w},${y + h / 2} L${x + w - d},${y + h} H${x + d} L${x},${y + h / 2} Z" ${st}/>`; }
    if (k === 'slant') { const d = Math.min(8, h / 2); return `<path class="shape" d="M${x + d},${y} H${x + w} L${x + w - d},${y + h} H${x} Z" ${st}/>`; }
    if (k === 'tag') { const d = Math.min(9, h / 2); return `<path class="shape" d="M${x},${y} H${x + w - d} L${x + w},${y + h / 2} L${x + w - d},${y + h} H${x} Z" ${st}/>`; }
    return `<rect class="shape" x="${x}" y="${y}" width="${w}" height="${h}" rx="${h / 2}" ${st}/>`;
  }
  const gxGlyph = (type) => { const [ink, fill] = gxColor(type); return `<svg class="gxglyph" viewBox="0 0 28 16" aria-hidden="true">${gxShapeSvg(type, { x: 1, y: 1, w: 26, h: 14 }, fill, ink)}</svg>`; };
  const roleWord = (k) => (HOME_ROLE.find((r) => r[0] === k) || [k, k])[1];

  const gxName = (n) => (n.alt !== undefined && n.alt !== '' ? n.alt : n.title);  // a perspective may name records by another property
  const gxWord = (n) => (n.type === 'bundle' ? `${n.label} ${n.key} · 펼치기` : `${n.label} ${n.key}${gxName(n) ? ` ${String(gxName(n)).length > 9 ? `${String(gxName(n)).slice(0, 8)}…` : gxName(n)}` : ''}`);

  // how a graph of typed nodes is drawn: the record graph's look here, the document graph's by the documents
  const GX_LOOK = { word: (n) => gxWord(n), shape: (type) => gxShape(type), color: (type) => gxColor(type), seed: (g) => gxId(g.seed.type, g.seed.key), name: '레코드 그래프' };

  function gxLayout(g = S.gx, look = GX_LOOK) {
    const ids = Object.keys(g.nodes).filter((id) => !g.hide.includes(g.nodes[id].type));
    const seed = look.seed(g);
    const near = {};
    g.edges.forEach((e) => { (near[e.source] = near[e.source] || []).push(e.target); (near[e.target] = near[e.target] || []).push(e.source); });
    const dist = { [seed]: 0 }, queue = [seed];
    while (queue.length) { const x = queue.shift(); (near[x] || []).forEach((y) => { if (dist[y] === undefined) { dist[y] = dist[x] + 1; queue.push(y); } }); }
    const far = Math.max(0, ...Object.values(dist));
    const levels = [];
    ids.forEach((id) => { const d = dist[id] ?? far + 1; (levels[d] = levels[d] || []).push(id); });
    // within a level, a record sits near the records it hangs off
    const at = {};
    levels.forEach((lv, d) => {
      if (!lv) return;
      if (d) lv.sort((a, b) => Math.min(...(near[a] || []).map((x) => at[x] ?? 99)) - Math.min(...(near[b] || []).map((x) => at[x] ?? 99)));
      lv.forEach((id, i) => { at[id] = i; });
    });
    const boxes = {};
    const size = (id) => ({ w: Math.max(70, textW(look.word(g.nodes[id])) + GX.padX * 2 + (['hex', 'slant', 'tag'].includes(look.shape(g.nodes[id].type)) ? 16 : 0)), h: GX.h });  // a pointed outline needs room at its ends
    if (g.layout === 'radial') {
      const ang = {};
      let outer = 0;  // a ring is far enough out for its nodes to stand side by side, and past the ring inside it
      // a node on a ring faces the nodes it hangs off: the ring is ordered by their mean angle and turned to match
      const want = (id, d) => {
        const xs = (near[id] || []).filter((y) => dist[y] === d - 1 && ang[y] !== undefined).map((y) => ang[y]);
        return xs.length ? Math.atan2(xs.reduce((s, a) => s + Math.sin(a), 0), xs.reduce((s, a) => s + Math.cos(a), 0)) : 0;
      };
      levels.forEach((lv, d) => {
        if (!lv) return;
        const step = (Math.PI * 2) / lv.length;
        let turn = -Math.PI / 2;
        if (d > 0) {
          const w = Object.fromEntries(lv.map((id) => [id, want(id, d)]));
          lv.sort((x, y) => w[x] - w[y]);
          const sx = lv.reduce((s, id, i) => s + Math.cos(w[id] - i * step), 0), sy = lv.reduce((s, id, i) => s + Math.sin(w[id] - i * step), 0);
          turn = Math.atan2(sy, sx);
        }
        const r = d ? Math.max(d * GX.ring, outer + GX.ring * 0.75, lv.reduce((s, id) => s + size(id).w + 18, 0) * 1.35 / (Math.PI * 2)) : 0;
        outer = r;
        lv.forEach((id, i) => {
          const a = i * step + turn;
          ang[id] = a;
          const sz = size(id);
          boxes[id] = { ...sz, x: r * Math.cos(a) - sz.w / 2, y: r * Math.sin(a) - sz.h / 2 };
        });
      });
    } else {  // layers top to bottom, each centred under the widest
      const rowW = (lv) => lv.reduce((a, id) => a + size(id).w, 0) + (lv.length - 1) * 24;
      const wide = Math.max(...levels.map((lv) => (lv ? rowW(lv) : 0)));
      let y = 0;
      levels.forEach((lv) => {
        if (!lv) return;
        let x = (wide - rowW(lv)) / 2;
        lv.forEach((id) => { const sz = size(id); boxes[id] = { ...sz, x, y }; x += sz.w + 24; });
        y += GX.h + GX.gapX;
      });
    }
    Object.entries(g.pos).forEach(([id, p]) => { if (boxes[id]) Object.assign(boxes[id], p); });
    const xs = Object.values(boxes);
    const minX = Math.min(0, ...xs.map((b) => b.x)) - GX.pad, minY = Math.min(0, ...xs.map((b) => b.y)) - GX.pad - 10;
    xs.forEach((b) => { b.x -= minX; b.y -= minY; });
    return { boxes, minX, minY, W: Math.max(...xs.map((b) => b.x + b.w), 300) + GX.pad, H: Math.max(...xs.map((b) => b.y + b.h), 200) + GX.pad };
  }

  function gxSvg(g = S.gx, look = GX_LOOK) {
    if (!Object.keys(g.nodes).length) return '';
    const L = gxLayout(g, look), z = g.zoom || 1;
    const way = new Set((g.routeEdges || []).map((e) => `${e.source}|${e.target}`));
    const onWay = new Set((g.route || []).map((x) => x.id));
    const place = pairs(g.edges, (e) => [e.source, e.target]);
    const edges = g.edges.map((e) => {
      const a = L.boxes[e.source], b = L.boxes[e.target];
      if (!a || !b) return '';
      const [p, q] = erEdge(a, b);
      const hot = way.has(`${e.source}|${e.target}`) || way.has(`${e.target}|${e.source}`);
      const on = g.sel === e.source || g.sel === e.target;
      const c = bend(p, q, ...place(e));
      // an arrowhead for each way the relation was opened: from its source, from its target, or both
      const back = (e.groups || []).some((x) => x.endsWith('|0')), ahead = e.route || !back || (e.groups || []).some((x) => x.endsWith('|1'));
      const tip = `url(#${hot ? 'gxhot' : 'gxarrow'})`;
      return `<g class="gxe${hot ? ' hot' : ''}${on ? ' on' : ''}"><path d="${c.d}"${ahead ? ` marker-end="${tip}"` : ''}${back ? ` marker-start="${tip}"` : ''}/><text x="${c.x}" y="${c.y - 5}" text-anchor="middle">${esc(e.label || '')}</text></g>`;
    }).join('');
    const nodes = Object.entries(L.boxes).map(([id, b]) => {
      const n = g.nodes[id], [ink, fill] = look.color(n.type);
      const cls = `${id === g.sel ? ' on' : ''}${onWay.has(id) ? ' way' : ''}${n.type === 'bundle' ? ' bundle' : ''}${id === look.seed(g) ? ' seed' : ''}`;
      return `<g class="gxn${cls}" data-gx="${esc(id)}">${gxShapeSvg(n.type, b, fill, ink, look.shape(n.type))}
        <text x="${b.x + b.w / 2}" y="${b.y + b.h / 2 + 4.5}" text-anchor="middle" style="fill:${ink}">${esc(look.word(n))}</text></g>`;
    }).join('');
    return `<svg class="gxsvg" width="${Math.round(L.W * z)}" height="${Math.round(L.H * z)}" viewBox="0 0 ${L.W} ${L.H}" role="img" aria-label="${esc(look.name)}">
      <defs><marker id="gxarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#98a2b3"/></marker>
      <marker id="gxhot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#e8590c"/></marker></defs>${edges}${nodes}</svg>`;
  }

  function mountGx(box = $('#gxcanvas'), g = S.gx, look = GX_LOOK, on = { pick: (id) => gxPick(id), open: (id) => gxOpen(id), zoom: (step) => gxZoom(step) }) {
    if (!box || box.dataset.on) return;
    box.dataset.on = '1';
    let drag = null, pinch = null;
    const fingers = new Map();  // the pointers down on the canvas: two of them pinch
    const spread = () => { const [a, b] = [...fingers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
    const zoomAt = (x, y, step) => {  // the drawing point under (x, y) stays under it, as the other graphs zoom
      const svg = box.querySelector('svg'), z0 = g.zoom || 1;
      if (!svg) { on.zoom(step); return; }
      const s = svg.getBoundingClientRect(), cx = (x - s.left) / z0, cy = (y - s.top) / z0;
      on.zoom(step);
      const r = box.getBoundingClientRect(), z1 = g.zoom || 1;
      box.scrollLeft = cx * z1 - (x - r.left);
      box.scrollTop = cy * z1 - (y - r.top);
    };
    box.addEventListener('pointerdown', (ev) => {
      fingers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      if (fingers.size === 2) { drag = null; pinch = { d: spread(), z: g.zoom || 1 }; box.setPointerCapture(ev.pointerId); return; }
      const n = ev.target.closest('[data-gx]');
      const L = n && gxLayout(g, look), b = L && L.boxes[n.dataset.gx];
      drag = b ? { id: n.dataset.gx, x0: ev.clientX, y0: ev.clientY, bx: b.x + L.minX, by: b.y + L.minY, moved: false }
        : { pan: true, x0: ev.clientX, y0: ev.clientY, sl: box.scrollLeft, st: box.scrollTop, moved: false };
      box.setPointerCapture(ev.pointerId);
    });
    box.addEventListener('pointermove', (ev) => {
      if (fingers.has(ev.pointerId)) fingers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
      if (pinch && fingers.size === 2) {  // the zoom follows the fingers' spread, a tenth at a time as the buttons do
        const [a, b] = [...fingers.values()], want = Math.min(1.8, Math.max(0.35, pinch.z * (spread() / Math.max(pinch.d, 1))));
        const steps = Math.round((want - (g.zoom || 1)) / 0.1);
        for (let i = 0; i < Math.abs(steps); i += 1) zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, Math.sign(steps));
        return;
      }
      if (!drag) return;
      const dx = ev.clientX - drag.x0, dy = ev.clientY - drag.y0;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      drag.moved = true;
      if (drag.pan) { box.scrollLeft = drag.sl - dx; box.scrollTop = drag.st - dy; box.classList.add('panning'); return; }
      const z = g.zoom || 1;
      g.pos[drag.id] = { x: drag.bx + dx / z, y: drag.by + dy / z };
      box.innerHTML = gxSvg(g, look);
    });
    let last = { id: '', at: 0 };  // the canvas is redrawn on a press, so a double-click is two presses on one box in time
    const end = (ev) => {
      fingers.delete(ev.pointerId);
      if (pinch) { if (!fingers.size) pinch = null; return; }  // a pinch picks nothing
      if (drag && !drag.moved && !drag.pan) {
        const twice = last.id === drag.id && Date.now() - last.at < 450;
        last = { id: drag.id, at: twice ? 0 : Date.now() };
        if (twice) on.open(drag.id); else on.pick(drag.id);
      } else if (drag && drag.pan && !drag.moved && on.clear) on.clear();  // a press on the empty canvas lets the pick go
      drag = null; box.classList.remove('panning');
    };
    box.addEventListener('pointerup', end);
    box.addEventListener('pointercancel', end);
    box.addEventListener('wheel', (ev) => { ev.preventDefault(); zoomAt(ev.clientX, ev.clientY, ev.deltaY < 0 ? 1 : -1); }, { passive: false });  // the wheel zooms around the pointer; the canvas pans by dragging
  }

  function gxZoom(step) {
    const g = S.gx, box = $('#gxcanvas');
    g.zoomed = step !== 0;
    if (step === 0 && box) { g.zoom = 1; gxFit(); }
    else g.zoom = Math.min(1.8, Math.max(0.35, Math.round(((g.zoom || 1) + step * 0.1) * 10) / 10));
    gxRedraw();
  }

  function gxFit(g = S.gx, box = $('#gxcanvas'), look = GX_LOOK) {
    if (g.zoomed || !box || !Object.keys(g.nodes).length) return;
    const L = gxLayout(g, look);
    g.zoom = Math.min(1, Math.max(0.35, Math.min((box.clientWidth - 8) / L.W, (box.clientHeight - 8) / L.H)));
  }

  function gxRedraw() {
    if ($('#gxcanvas')) gxPaint(); else render();
  }

  function gxPaint() {  // the canvas and its zoom figure, where the person left them
    const box = $('#gxcanvas');
    if (!box) return;
    gxFit();
    box.innerHTML = gxSvg();
    const z = $('[data-act=gxzoom][data-z="0"]');
    if (z) z.textContent = `${Math.round((S.gx.zoom || 1) * 100)}%`;
  }

  async function gxLinks(id) {
    const n = S.gx.nodes[id];
    if (!n || S.gx.links[id]) return;
    try {
      const r = await api(`record/links?type=${encodeURIComponent(n.type)}&key=${encodeURIComponent(n.key)}`);
      S.gx.links[id] = r;
      gxAdd({ type: r.type, key: r.key, label: r.label, title: r.title || '' });
    } catch (e) { S.gx.links[id] = { links: [], error: e.message }; }
    if (Object.keys(S.gx.labelBy || {}).length) await gxFetchLabels();
  }

  async function gxStart(type, key) {
    Object.assign(S.gx, { nodes: {}, edges: [], links: {}, sel: '', route: [], routeEdges: [], err: '', open: [], pos: {} });
    const id = gxAdd({ type, key, label: (S.st.graph.nodes.find((x) => x.id === type) || {}).label || type });
    S.gx.seed = { type, key: String(key) };
    S.gx.sel = id;
    S.gx.log = [{ id, word: `${key}에서 시작` }];
    S.gx.info = {};
    gxInfo(id);
    await gxLinks(id);
    const first = S.gx.links[id];
    if (first && first.error) { S.gx.err = first.error; S.gx.nodes = {}; S.gx.sel = ''; }
    else if (first) {  // a start with few neighbours opens its first hop; one with many stays closed for the person to choose
      const near = first.links.reduce((n, l) => n + l.count, 0);
      if (near && near <= GX_ROWS) { gxGrow(id); return; }
    }
    if (S.tab === 'graph') render();
  }

  const BUNDLE = 6;  // more records than this on one relation are folded into one node until it is opened
  const GX_ROWS = 25;  // records one relation adds at a time (pages_api.GRAPH_ROWS)

  const gxGroup = (id, link, forward) => `${id}|${link}|${forward ? 1 : 0}`;

  function gxShrink(id, link, forward) {
    const g = S.gx, key = gxGroup(id, link, forward);
    const said = (g.edges.find((e) => e.groups.includes(key)) || {}).label || link;
    g.open = g.open.filter((x) => x !== key);
    g.edges.forEach((e) => { e.groups = e.groups.filter((x) => x !== key); });
    g.edges = g.edges.filter((e) => e.groups.length || e.route);
    const held = new Set([gxId(g.seed.type, g.seed.key), g.sel, ...(g.route || []).map((x) => x.id)]);
    g.edges.forEach((e) => { held.add(e.source); held.add(e.target); });
    Object.keys(g.nodes).forEach((n) => { if (!held.has(n)) delete g.nodes[n]; });
    g.log.push({ id, word: `${said} 접음` });
    render();
  }

  function gxGrow(id, link, forward, open) {
    const r = S.gx.links[id];
    if (!r) return;
    const groups = r.links.filter((l) => (link === undefined || (l.link === link && l.forward === forward)) && l.count);
    for (const l of groups) {
      const key = gxGroup(id, l.link, l.forward);
      if (!S.gx.open.includes(key)) S.gx.open.push(key);
      const bid = `bundle:${id}:${l.link}:${l.forward ? 1 : 0}`;
      if (l.count > BUNDLE && !open) {
        S.gx.nodes[bid] = { type: 'bundle', key: `${l.count}${l.more ? '+' : ''}`, label: `${l.type_label}`, title: '펼치기', of: { id, link: l.link, forward: l.forward } };
        if (l.forward) gxEdge(id, bid, l.base || l.link, l.base_label || l.label, key); else gxEdge(bid, id, l.base || l.link, l.base_label || l.label, key);
        continue;
      }
      delete S.gx.nodes[bid];
      S.gx.edges = S.gx.edges.filter((e) => e.source !== bid && e.target !== bid);
      for (const it of l.items) {
        const other = gxAdd({ type: l.type, key: it.key, label: l.type_label, title: it.title || '' });
        if (l.forward) gxEdge(id, other, l.base || l.link, l.base_label || l.label, key); else gxEdge(other, id, l.base || l.link, l.base_label || l.label, key);
      }
    }
    const n = S.gx.nodes[id];
    S.gx.log.push({ id, word: link === undefined ? `${n.key} 모두 펼침` : `${(groups[0] || {}).type_label || ''} 펼침` });
    render();
  }

  async function gxPick(id) {
    const b = S.gx.nodes[id];
    if (b && b.type === 'bundle') { gxGrow(b.of.id, b.of.link, b.of.forward, true); return; }
    S.gx.sel = id;
    S.gx.from = null; S.gx.fromq = '';
    gxInfo(id);
    gxRedraw();
    gxPathPaint();
    await gxLinks(id);
    const left = $('#gxgrow'), side = $('#gxside');
    if (left) left.innerHTML = gxGrowCard();
    if (side) side.innerHTML = gxSide();
  }

  async function gxOpen(id) {  // a double-click: every relation of the box, with the limits and bundles of [모두]
    const n = S.gx.nodes[id];
    if (!n || n.type === 'bundle') return;
    await gxLinks(id);
    if (!S.gx.nodes[id] || !S.gx.links[id]) return;
    const was = Object.keys(S.gx.nodes).length;
    S.gx.sel = id;
    gxGrow(id);
    if (Object.keys(S.gx.nodes).length === was) toast('더 펼칠 관계가 없습니다.');
  }

  async function gxPath() {
    const g = S.gx;
    const sel = g.nodes[g.sel] && g.nodes[g.sel].type !== 'bundle' ? g.nodes[g.sel] : null;
    const from = g.from || sel;
    if (!from) { toast('시작 레코드가 없어 경로를 찾지 못했습니다. 시작 레코드를 선택해 주세요.', true); return; }
    if (!g.nodes[gxId(from.type, from.key)]) { await gxStart(from.type, from.key); g.from = null; }
    if (!g.to.type || !g.to.key.trim()) { toast('도착 레코드가 없어 경로를 찾지 못했습니다. 도착 레코드를 선택해 주세요.', true); return; }
    g.busy = true; render();
    try {
      const r = await api(`record/path?from_type=${encodeURIComponent(from.type)}&from_key=${encodeURIComponent(from.key)}&to_type=${encodeURIComponent(g.to.type)}&to_key=${encodeURIComponent(g.to.key.trim())}`);
      if (!r.ok) { g.route = []; toast(r.error, true); } else {
        const ids = r.nodes.map((n) => gxAdd(n));
        r.edges.forEach((e) => gxEdge(e.source, e.target, e.link, e.label));
        g.route = r.nodes.map((n, i) => ({ id: ids[i], ...n }));
        g.routeEdges = r.edges;
        g.sel = ids[ids.length - 1];
        g.log.push({ id: g.sel, word: `경로: ${g.to.key}` });
        gxInfo(g.sel);
      }
    } catch (e) { fail(e); }
    g.busy = false; render();
    if (g.sel && !g.links[g.sel]) { await gxLinks(g.sel); if (S.tab === 'graph') render(); }
  }

  function gxGrowCard() {
    const g = S.gx, r = g.links[g.sel], n = g.nodes[g.sel];
    if (!n) return '<div class="card"><div class="ch">관계로 펼치기</div><div class="cb"><div class="empty">선택된 레코드가 없습니다.</div></div></div>';
    if (!r) return `<div class="card"><div class="ch">관계로 펼치기</div><div class="cb"><div class="empty"><span class="spin"></span>${esc(n.label)} ${esc(n.key)}의 관계를 읽는 중입니다.</div></div></div>`;
    const rows = r.links.map((l) => `<label class="gxrow${l.count ? '' : ' off'}"><input type="checkbox" data-in="gxrel" data-link="${esc(l.link)}" data-fw="${l.forward ? 1 : 0}"${g.open.includes(gxGroup(g.sel, l.link, l.forward)) ? ' checked' : ''}${l.count ? '' : ' disabled'}>
      <span>${l.forward ? `${esc(l.base_label || l.label)} → <b>${esc(l.type_label)}</b>` : `← ${esc(l.base_label || l.label)} · <b>${esc(l.type_label)}</b>`}</span><span class="chip sm">${l.count}${l.more ? '+' : ''}</span></label>`).join('');
    return `<div class="card"><div class="ch">관계로 펼치기<div class="right"><button class="btn sm" data-act="gxgrowall" title="최대 ${GX_ROWS}개 · ${BUNDLE}개 초과 시 묶음">모두 펼치기</button></div></div><div class="cb">
      ${rows || '<div class="empty">관계가 없습니다.</div>'}
      </div></div>`;
  }

  function gxSide() {
    const g = S.gx, n = g.nodes[g.sel];
    const route = g.route && g.route.length ? `<div class="card"><div class="ch">찾은 경로 · ${g.route.length - 1}단계</div><div class="cb">${g.route.map((x, i) => `${i ? `<div class="muted gxhop">↓ ${esc((g.routeEdges[i - 1] || {}).label || '')}</div>` : ''}<button class="hrow" data-act="gxsel" data-id="${esc(x.id)}"><span class="rtag">${esc(x.label)}</span><b>${esc(x.key)}</b><span class="muted">${esc(x.title || '')}</span></button>`).join('')}</div></div>` : '';
    let card = '';
    if (n) {
      const info = g.info[g.sel];
      const vals = info && info.props ? info.props.filter((p) => !p.key && p.value !== null && p.value !== '' && !p.mask).slice(0, 4)
        .map((p) => `<dt>${esc(p.label)}</dt><dd>${recordValue(p)}</dd>`).join('') : '';
      const decs = info && info.decisions ? info.decisions.filter((x) => !x.error).map((x) => `<div class="gxdec"><span class="chip sm ${x.yes ? 'ok' : 'warn'}">${esc(x.label)} · ${esc(x.verdict)}</span><span class="muted">${esc(x.matched.join(', '))}</span></div>`).join('') : '';
      card = `<div class="card"><div class="ch"><span class="rtag">${esc(n.label)}</span>${esc(n.key)}${n.title ? ` <span class="muted" style="font-weight:600">${esc(n.title)}</span>` : ''}</div>
        ${info && info.busy ? '<div class="cb"><span class="spin"></span></div>' : ''}${vals ? `<dl class="gxkv cb">${vals}</dl>` : ''}${decs ? `<div class="cb" style="border-top:1px solid var(--line)">${decs}</div>` : ''}
        <div class="cb" style="border-top:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm primary" data-act="rec" data-type="${esc(n.type)}" data-key="${esc(n.key)}">레코드 열기</button><button class="btn sm" data-act="gxroot" data-id="${esc(g.sel)}">시작점으로 지정</button></div></div>`;
    }
    const log = g.log.length ? `<div class="card"><div class="ch">탐색 기록</div><div class="cb"><div class="chips">${g.log.map((x) => `<button class="chip sm" data-act="gxsel" data-id="${esc(x.id)}">${esc(x.word)}</button>`).join('')}</div></div></div>` : '';
    return card + route + log;
  }

  function viewGraph() {
    const g = S.gx;
    const types = recordTypes();
    if (noSource() || !types.length) return pageHead('레코드 그래프', '레코드의 관계와 두 레코드 사이의 경로를 탐색합니다.') + noSourceCard();  // records are read from the source
    if (!g.seed.type) {
      const asked = new URLSearchParams(location.search).get('gx');  // a link someone copied from this screen
      const [t, ...k] = (asked || '').split(':');
      const r = t && types.some((x) => x.id === t) ? { type: t, key: k.join(':') } : RECENT[0];
      if (r) { g.seed = { type: r.type, key: r.key }; gxStart(r.type, r.key); } else g.seed = { type: (types[0] || {}).id || '', key: '' };
    }
    const head = pageHead('레코드 그래프', '레코드의 관계와 두 레코드 사이의 경로를 탐색합니다.');
    const start = `<div class="card"><div class="cb"><div class="gxfield big"><span class="gxlens" aria-hidden="true">⌕</span><input type="search" id="gxq" data-in="gxq" value="${esc(g.q)}" placeholder="시작 레코드 · 번호, 이름, 정의 (예: VIP 고객)" aria-label="시작 레코드 찾기" autocomplete="off"><button class="iconbtn" data-act="rpopen" data-w="start" title="목록에서 찾기" aria-label="목록에서 찾기">☰</button></div>
      <div id="gxfound-start">${gxFound('start')}</div>${g.err ? `<div class="hint warn" style="margin-top:8px">${esc(g.err)}</div>` : ''}</div></div>`;
    const path = `<div id="gxpathcard">${gxPathCard()}</div>`;
    const n = Object.keys(g.nodes).length;
    const seed = g.nodes[gxId(g.seed.type, g.seed.key)];
    const shownTypes = [...new Set(Object.values(g.nodes).map((x) => x.type))].filter((t) => t !== 'bundle');
    const legend = shownTypes.map((t) => { const [ink, fill] = gxColor(t); return `<span class="gxleg"><i style="background:${fill};border-color:${ink}"></i>${esc((S.st.graph.nodes.find((x) => x.id === t) || {}).label || t)} ${Object.values(g.nodes).filter((x) => x.type === t).length}</span>`; }).join('');
    const canvas = n ? `<div class="card"><div class="ch">${seed ? `${esc(seed.label)} ${esc(seed.key)}${seed.title ? ` ${esc(seed.title)}` : ''}에서 시작` : '레코드 그래프'}
        <div class="right"><label class="chip chipsel">레이아웃: <select data-in="gxlayout" aria-label="레이아웃">${[['layered', '계층'], ['radial', '방사형']].map(([k, w]) => opt(k, w, g.layout)).join('')}</select></label><button class="btn sm ghost" data-act="gxreset">초기화</button>
        <span class="erzoom" role="group" aria-label="확대"><button class="iconbtn" data-act="gxzoom" data-z="-1" aria-label="축소">−</button><button class="btn sm ghost" data-act="gxzoom" data-z="0" title="화면에 맞춤">${Math.round((g.zoom || 1) * 100)}%</button><button class="iconbtn" data-act="gxzoom" data-z="1" aria-label="확대">+</button></span></div></div>
      <div class="cb gxcanvas" id="gxcanvas">${gxSvg()}</div>
      <div class="cb gxfoot"><span class="gxlegs">${legend}</span><span class="muted">레코드 ${n} · 관계 ${g.edges.length}</span></div></div>`
      : '<div class="card"><div class="cb"><div class="empty">선택된 시작 레코드가 없습니다.</div></div></div>';
    return `${head}<div class="grid gxgrid"><div class="hcol">${start}<div id="gxgrow">${gxGrowCard()}</div>${path}${gxViewCard()}</div>${canvas}<div class="hcol" id="gxside">${gxSide()}</div></div>`;
  }

  // ---- one workspace for the definition: modules and objects, the schema graph, and the object's form or file --------

  // the top level of a definition is its Objects (areas), each holding Entities; a definition without them groups by module
  const AREA_NONE = 'Object 미지정';
  const areasOn = () => !!(S.mg.st && (S.mg.st.areas || []).length);
  const byArea = () => areasOn() && S.md.group !== 'module';
  const groupOfObj = (o) => (byArea() ? (o.area_label || o.area || AREA_NONE) : (o.module_label || o.module || '정의'));
  const mgArea = (name) => ((S.mg.st && S.mg.st.areas) || []).find((a) => a.name === name);

  function modelTree() {
    const m = S.mg.st, md = S.md;
    const q = md.q.trim().toLowerCase();
    const has = (s) => String(s || '').toLowerCase().includes(q);
    if (q) {
      const obj = m.objects.filter((o) => has(o.name) || has(o.label) || has(o.table));
      const props = m.properties.filter((p) => !p.inherited && (has(p.name) || has(p.label) || has(p.column))).slice(0, 30);
      const links = m.links.filter((l) => has(l.name) || has(l.label)).slice(0, 20);
      const cols = m.sources.source.tables.flatMap((t) => t.columns.filter((c) => has(c.name)).map((c) => ({ t, c }))).slice(0, 30);
      const group = (word, rows) => (rows.length ? `<div class="mdgrp"><div class="mdgh">${word}<span class="muted">${rows.length}</span></div>${rows.join('')}</div>` : '');
      return group('Entity', obj.map((o) => `<button class="mdnode${o.name === md.sel ? ' on' : ''}" data-act="mdpick" data-name="${esc(o.name)}"><span>${esc(o.label)}</span><span class="muted mono">${esc(o.table || '')}</span></button>`))
        + group('Property', props.map((p) => `<button class="mdnode" data-act="mdprop" data-name="${esc(`${p.object}.${p.name}`)}"><span>${esc(mgLabel(p.object))} · ${esc(p.label || p.name)}</span></button>`))
        + group('Relation', links.map((l) => `<button class="mdnode" data-act="mdlink" data-name="${esc(l.name)}"><span>${esc(l.label || l.name)}</span><span class="muted">${esc(mgLabel(l.source))} → ${esc(mgLabel(l.target))}</span></button>`))
        + group('소스 컬럼', cols.map((x) => `<button class="mdnode" data-act="mdcol" data-col="${esc(`${x.t.table}|${x.c.name}|${x.c.type}`)}"><span class="mono">${esc(x.t.table)}.${esc(x.c.name)}</span></button>`))
        || '<div class="empty">찾은 항목이 없습니다.</div>';
    }
    const groups = {};
    if (byArea()) (m.areas || []).forEach((a) => { groups[a.label || a.name] = []; });  // an Object with no Entity yet is still listed
    m.objects.forEach((o) => { const k = groupOfObj(o); (groups[k] = groups[k] || []).push(o); });
    const by = modelProblems().by;
    const marks = (o) => [(by[o.name] || []).length ? ['bad', `문제 ${by[o.name].length}`] : null, o.status && o.status !== 'active' ? STATUS_WORD[o.status] : null, o.new ? ['ok', '새 Entity'] : o.pending ? ['warn', '변경'] : null, m.unlinked.includes(o.name) ? ['warn', 'Relation 없음'] : null,
      o.series ? ['', '시계열'] : null, (o.extended_by || []).length ? ['', `+ ${shortMod(o.extended_by[0])}`] : null, (m.comments || {})[`object:${o.name}`] ? ['', `댓글 ${m.comments[`object:${o.name}`]}`] : null]
      .filter(Boolean).map(([c, w]) => `<span class="chip sm ${c}">${esc(w)}</span>`).join('');
    const areaOf = (k) => (byArea() ? (m.areas || []).find((a) => (a.label || a.name) === k) : null);
    const head = (k, list) => {
      const a = areaOf(k);
      if (!a) return `<div class="mdgh">${esc(k)}<span class="muted">${list.length}</span></div>`;
      const on = S.mg.form && S.mg.form.kind === 'area' && S.mg.form.v.name === a.name;
      return `<button class="mdgh mdarea${on ? ' on' : ''}" data-act="mdarea" data-name="${esc(a.name)}" title="Object ${esc(a.label || a.name)} 열기"><span>${esc(a.label || a.name)}</span><span class="muted mono">${esc(a.name)}</span>${a.new ? '<span class="chip sm ok">새</span>' : a.pending ? '<span class="chip sm warn">변경</span>' : ''}<span class="muted">${list.length}</span></button>`;
    };
    const seg = areasOn() ? `<div class="mdgroupby"><div class="seg" role="group" aria-label="묶는 기준"><button class="${byArea() ? 'on' : ''}" data-act="mdgroup" data-k="area">Object별</button><button class="${byArea() ? '' : 'on'}" data-act="mdgroup" data-k="module">모듈별</button></div>${byArea() ? '<button class="btn sm" data-act="mdareanew">+ Object</button>' : ''}</div>`
      : '<div class="mdgroupby"><span class="muted">모듈별</span><button class="btn sm" data-act="mdareanew">+ Object</button></div>';
    return seg + (Object.entries(groups).sort((a, b) => (a[0] === AREA_NONE) - (b[0] === AREA_NONE)).map(([k, list]) => `<div class="mdgrp">${head(k, list)}${list.map((o) => `<button class="mdnode${o.name === md.sel ? ' on' : ''}" data-act="mdpick" data-name="${esc(o.name)}"><span>${esc(o.label)}</span>${o.parent ? `<span class="muted mdpar" title="상위 Entity">상위 ${esc(mgLabel(o.parent))}</span>` : ''}${o.concept ? '<span class="chip sm">개념</span>' : ''}${marks(o)}</button>`).join('')}</div>`).join('') || '<div class="empty">Entity가 없습니다.</div>');
  }

  function modelUses(o) {
    const u = S.md.uses;
    if (!u || u.id !== `object:${o.name}`) {
      if (S.md.usesFor === o.name) return '<div class="empty"><span class="spin"></span>사용처를 찾는 중입니다.</div>';
      S.md.usesFor = o.name;
      api(`element/readers?id=${encodeURIComponent(`object:${o.name}`)}`).then((x) => { S.md.uses = { id: `object:${o.name}`, list: x.readers }; paintSide(); }).catch(fail).finally(() => { S.md.usesFor = ''; });
      return '<div class="empty"><span class="spin"></span>사용처를 찾는 중입니다.</div>';
    }
    return u.list.length ? `<div class="chips">${u.list.map((x) => `<span class="chip">${esc(x)}</span>`).join('')}</div>` : '<div class="empty">사용처가 없습니다.</div>';
  }

  function modelSide() {
    const m = S.mg.st, md = S.md, o = mgObj(md.sel), f = S.mg.form;
    const creating = f && f.mode === 'new' && ['object', 'prop', 'link'].includes(f.kind);
    if (creating) {
      const word = { object: '새 Entity', prop: '새 Property', link: '새 Relation' }[f.kind];
      const inArea = f.kind === 'object' && f.v.area ? mgArea(f.v.area) : null;
      const up = inArea ? `<button class="ilinkb" data-act="mdarea" data-name="${esc(inArea.name)}">Object · ${esc(inArea.label || inArea.name)}</button> › `
        : o && f.kind !== 'object' ? `<button class="ilinkb" data-act="mdpick" data-name="${esc(o.name)}">${esc(o.label)}</button> › ` : '';
      return `<div class="ihead"><div style="display:flex;align-items:center;gap:8px"><div class="icrumb" style="flex:1;min-width:0">${up}<b>${word}</b></div><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="ibody">${f.kind === 'prop' ? propForm() : f.kind === 'link' ? linkForm() : objectForm()}</div>`;
    }
    if (f && f.kind === 'area') {  // an Object in the inspector: its name above its form
      const a = f.mode === 'edit' ? mgArea(f.v.name) : null;
      return `<div class="ihead"><div class="icrumb"><b>${a ? `Object · ${esc(a.label || a.name)}` : '새 Object'}</b>${a ? ` <span class="muted mono">${esc(a.name)}</span>` : ''}</div></div><div class="ibody">${wsForm()}</div>`;
    }
    if (!o) return '<div class="empty" style="padding:24px 12px">선택된 Entity가 없습니다.</div>';
    const uses = md.uses && md.uses.id === `object:${o.name}` ? md.uses.list.length : null;
    if (uses === null && md.tab !== 'uses') modelUses(o);  // whether anything reads it is said on every tab
    const notes = (m.comments || {})[`object:${o.name}`] || 0;
    const tabs = [['form', '폼', ''], ['data', '데이터', ''], ['uses', '사용처', uses || ''], ['yaml', 'YAML', ''], ['notes', '댓글', notes || '']]
      .map(([k, w, n]) => `<button class="${md.tab === k ? 'on' : ''}" data-act="mdtab" data-k="${k}">${w}${n ? ` <span class="muted">${n}</span>` : ''}</button>`).join('');
    const inner = f && f.kind === 'prop' ? (m.properties.find((p) => p.object === f.v.object && p.name === f.v.name) || {}) : f && f.kind === 'link' ? (m.links.find((l) => l.name === f.v.name) || {}) : null;
    const crumb = `<div class="icrumb">${inner ? `<button class="ilinkb" data-act="mdpick" data-name="${esc(o.name)}">${esc(o.label)}</button> › <b>${esc(inner.label || inner.name || '')}</b> <span class="muted mono">${esc(inner.name || '')}</span>` : `<b>${esc(o.label)}</b> <span class="muted mono">${esc(o.name)}</span>`}</div>`;
    let body;
    if (md.tab === 'yaml') body = modelYaml(o);
    else if (md.tab === 'uses') body = modelUses(o);
    else if (md.tab === 'notes') body = modelComments(o);
    else if (md.tab === 'data') body = modelData(o);
    else body = `${md.hot && md.hot.note ? `<div class="ierr">${esc(md.hot.note)}</div>` : ''}${f && f.kind === 'prop' ? propForm() : f && f.kind === 'link' ? linkForm() : objectForm()}`;
    const by = modelProblems().elements;
    const props = mgProps(o.name).map((p) => { const id = `${o.name}.${p.name}`; return `<button class="ilist-i${S.mg.sel === id ? ' on' : ''}" data-act="mdprop" data-name="${esc(id)}"><span>${esc(p.label || p.name)}</span>${by.has(`property:${id}`) ? '<span class="chip sm bad">문제</span>' : p.new ? '<span class="chip sm ok">새</span>' : p.pending ? '<span class="chip sm warn">변경</span>' : `<span class="muted mono">${esc(p.expr ? '계산' : p.name)}</span>`}</button>`; }).join('');
    const links = m.links.filter((l) => l.source === o.name || l.target === o.name).map((l) => `<button class="ilist-i${S.mg.sel === l.name ? ' on' : ''}" data-act="mdlink" data-name="${esc(l.name)}"><span>${esc(l.label || l.name)}</span>${l.new ? '<span class="chip sm ok">새</span>' : l.pending ? '<span class="chip sm warn">변경</span>' : `<span class="muted">${esc(mgLabel(l.source === o.name ? l.target : l.source))} ${esc(CARD[l.cardinality] || '')}</span>`}</button>`).join('');
    const count = m.links.filter((l) => l.source === o.name || l.target === o.name).length;
    const list = `<div class="ilist"><div class="ilist-h"><div class="seg" style="margin:0"><button class="${md.list === 'props' ? 'on' : ''}" data-act="mdlist" data-k="props">속성 ${mgProps(o.name).length}</button><button class="${md.list === 'links' ? 'on' : ''}" data-act="mdlist" data-k="links">관계 ${count}</button></div><button class="btn sm" data-act="${md.list === 'props' ? 'mdaddprop' : 'mdlinknew'}">+ 추가</button></div><div class="ilist-b">${(md.list === 'props' ? props : links) || '<div class="empty" style="padding:10px">항목이 없습니다.</div>'}</div></div>`;
    return `<div class="ihead">${crumb}${f && f.kind === 'object' ? objectStatus(o) : ''}<div class="seg" style="margin:0">${tabs}</div></div><div class="ibody">${body}</div>${list}`;
  }

  function modelData(o) {
    const d = S.md.data;
    if (!d || d.id !== o.name) {
      S.md.data = { id: o.name, busy: true };
      api(`object/profile?name=${encodeURIComponent(o.name)}`).then((x) => { S.md.data = { id: o.name, res: x }; }).catch((e) => { S.md.data = { id: o.name, res: { ok: false, error: e.message } }; })
        .finally(() => { paintSide(); });
      return '<div class="empty"><span class="spin"></span>데이터를 읽는 중입니다.</div>';
    }
    if (d.busy) return '<div class="empty"><span class="spin"></span>데이터를 읽는 중입니다.</div>';
    const r = d.res;
    if (!r.ok) return `<div class="hint warn">${esc(r.error)}</div>`;
    return `<div class="muted" style="font-size:12px;margin-bottom:6px"><span class="mono">${esc(r.table)}</span> · ${show(r.total)}행</div>
      <div class="cb scroll" style="padding:0;border:1px solid var(--line);border-radius:8px"><table class="tight"><tr><th>Property</th><th>빈 값</th><th>고유값</th></tr>${r.stats.map((x) => `<tr><td>${esc(x.label)}<div class="muted mono">${esc(x.column)}</div></td><td class="num">${x.empty ? `<span class="chip sm warn">${Math.round(x.empty * 100)}%</span>` : '0%'}</td><td class="num">${show(x.distinct)}</td></tr>`).join('')}</table></div>
      <div class="label" style="margin:12px 0 4px">샘플 ${r.rows.length}행</div><div class="cb scroll" style="padding:0;border:1px solid var(--line);border-radius:8px;overflow-x:auto"><table class="tight"><tr>${r.columns.map((c) => `<th class="mono">${esc(c)}</th>`).join('')}</tr>${r.rows.map((x) => `<tr>${x.map((v) => `<td>${show(v)}</td>`).join('')}</tr>`).join('')}</table></div>`;
  }

  // ---- the schema as an entity diagram: each object with its key, its main and computed properties, each relation
  //      with its name and cardinality; the picked object's module as a region, the modules it reaches beside it ------

  const ER = { w: 190, row: 17, head: 34, gapX: 70, gapY: 46, cols: 2, pad: 16, regionPad: 18, title: 26, wMax: 330 };
  let erCtx = null;
  function erTextW(text, size, weight = 400) {  // the drawn width of a line on a card, measured with the page's font
    if (!erCtx) erCtx = document.createElement('canvas').getContext('2d');
    erCtx.font = `${weight} ${size}px ${getComputedStyle(document.body).fontFamily}`;
    return erCtx.measureText(String(text)).width;
  }
  function erFit(text, size, max) {  // the text that fits the width, shortened with an ellipsis when it does not
    if (erTextW(text, size) <= max) return [String(text), false];
    let s = String(text);
    while (s.length > 1 && erTextW(`${s}…`, size) > max) s = s.slice(0, -1);
    return [`${s}…`, true];
  }
  function erWidth(o) {  // a card is as wide as its title line or its longest row, up to a limit
    const title = 12 + erTextW(o.label, 13, 800) + 6 + erTextW(o.name, 11) + 10 + 48;
    const rows = Math.max(0, ...erRows(o).map((r) => erTextW(r.text, 11) + 24));
    return Math.round(Math.min(ER.wMax, Math.max(ER.w, title, rows)));
  }
  const CARD_WORD = { many_to_one: 'N : 1', one_to_many: '1 : N', one_to_one: '1 : 1', many_to_many: 'N : M' };
  const shortMod = (x) => String(x || '').replace(/\s*온톨로지$/, '').replace(/^이커머스\s+/, '').replace(/^고객사 차이 · /, '');

  function erRows(o) {
    const props = mgProps(o.name);
    const key = props.find((p) => p.key);
    const rest = props.filter((p) => !p.key && !p.inherited);
    const broken = modelProblems().elements;
    const isBad = (p) => broken.has(`property:${o.name}.${p.name}`);
    const pick = [...rest.filter(isBad), ...rest.filter((p) => p.expr), ...rest.filter((p) => p.module && p.module !== o.module), ...rest.filter((p) => p.mask), ...rest]
      .filter((p, i, a) => a.indexOf(p) === i).slice(0, Math.max(3, rest.filter(isBad).length));
    const rows = [];
    const word = (p) => p.label || p.name;
    if (key) rows.push({ kind: 'key', text: `🔑 ${word(key)}` });
    pick.forEach((p) => rows.push(isBad(p) ? { kind: 'bad', text: `${word(p)} !` } : p.expr ? { kind: 'expr', text: `${word(p)} · 계산` }
      : p.module && p.module !== o.module ? { kind: 'ext', text: `${word(p)} · ${shortMod(p.module_label || p.module)}` }
        : { kind: p.mask ? 'mask' : '', text: `${word(p)}${p.mask ? ' · 가림' : ''}` }));
    const more = rest.length - pick.length;
    if (more > 0) rows.push({ kind: 'more', text: `외 Property ${more}개` });
    return rows;
  }

  const ER_VIEW = {
    model: { state: () => S.md, box: 'ercanvas', card: 'ercard', pick: (n) => modelPick(n), html: () => erCard(), clear: () => focusOff('model') },
    onto: { state: () => S.ov, box: 'ontocanvas', card: 'ontocard', pick: (n) => { focusOn('onto', n); selectObject(n, true); }, html: () => ontoCard(), all: true, clear: () => focusOff('onto') },
  };

  function erLayout(v = 'model') {
    const m = S.mg.st, md = ER_VIEW[v].state(), sel = mgObj(md.sel);
    if (!sel && !ER_VIEW[v].all) return null;
    const modOf = (x) => groupOfObj(x);
    const deg = (n) => m.links.filter((l) => l.source === n || l.target === n).length;
    const ordered = (list) => {  // neighbours sit next to each other: breadth first from the most connected object
      const order = [];
      const left = [...list].sort((a, b) => deg(b.name) - deg(a.name));
      while (left.length) {
        const queue = [left.shift()];
        while (queue.length) {
          const x = queue.shift();
          order.push(x);
          m.links.filter((l) => l.source === x.name || l.target === x.name).forEach((l) => {
            const other = l.source === x.name ? l.target : l.source;
            const i = left.findIndex((y) => y.name === other);
            if (i >= 0) queue.push(left.splice(i, 1)[0]);
          });
        }
      }
      return order;
    };
    const home = sel ? modOf(sel) : '';
    const inMod = m.objects.filter((x) => modOf(x) === home);
    const names = new Set(inMod.map((x) => x.name));
    const near = new Set();
    m.links.forEach((l) => {
      if (names.has(l.source) && !names.has(l.target)) near.add(l.target);
      if (names.has(l.target) && !names.has(l.source)) near.add(l.source);
    });
    inMod.forEach((x) => { if (x.parent && !names.has(x.parent)) near.add(x.parent); });
    const order = ordered(inMod);
    const boxes = {}, regions = [];
    const place = (list, x0, y0, cols, label, fold) => {
      if (fold) {
        const r = { label, x: x0, y: y0, w: 260, h: 54, fold: true, n: list.length, names: list.map((x) => x.name) };
        list.forEach((x) => { boxes[x.name] = { x: x0 + 14, y: y0 + 14, w: 232, h: 30, o: x, folded: r }; });
        regions.push(r);
        return r;
      }
      let rowH = [], y = y0 + ER.title + ER.regionPad, maxW = 0;
      const widths = list.map(erWidth), colW = [];  // a column is as wide as its widest card
      list.forEach((x, i) => { const c = i % cols; colW[c] = Math.max(colW[c] || 0, widths[i]); });
      const colX = colW.map((_, c) => colW.slice(0, c).reduce((a, w) => a + w + ER.gapX, 0));
      list.forEach((x, i) => {
        const c = i % cols, r = Math.floor(i / cols);
        if (!rowH[r]) rowH[r] = 0;
        const h = ER.head + erRows(x).length * ER.row + 10;
        rowH[r] = Math.max(rowH[r], h);
        boxes[x.name] = { x: x0 + ER.regionPad + colX[c], y: 0, w: widths[i], h, o: x, r };
      });
      const tops = rowH.map((_, r) => y + rowH.slice(0, r).reduce((a, h) => a + h + ER.gapY, 0));
      list.forEach((x) => { const b = boxes[x.name]; b.y = tops[b.r]; const p = md.pos[x.name]; if (p) { b.x = p.x; b.y = p.y; } maxW = Math.max(maxW, b.x + b.w - x0); });
      const bottom = Math.max(...list.map((x) => boxes[x.name].y + boxes[x.name].h), y0 + 60);
      const r = { label, x: x0, y: y0, w: Math.max(maxW + ER.regionPad, 240), h: bottom - y0 + ER.regionPad, n: list.length };
      regions.push(r);
      return r;
    };
    if (ER_VIEW[v].all) {  // every module a region of its own, two to a row
      const mods = [...new Set(m.objects.map(modOf))].sort((a, b) => (a === AREA_NONE) - (b === AREA_NONE));  // what has no Object goes last
      let x = ER.pad, y = ER.pad, rowH = 0;
      const perRow = md.perRow || 2;
      mods.forEach((label, i) => {
        const r = place(ordered(m.objects.filter((o) => modOf(o) === label)), x, y, ER.cols, label, false);
        rowH = Math.max(rowH, r.h);
        if (i % perRow === perRow - 1) { x = ER.pad; y += rowH + 28; rowH = 0; } else x += r.w + 40;
      });
      return { boxes, regions, home: '온톨로지 전체' };
    }
    const top = place(order, ER.pad, ER.pad, md.cols || ER.cols, home, false);
    // the modules it reaches stand in a column beside it, one card wide, so its relations stay short
    const byMod = {};
    [...near].map((n) => mgObj(n)).filter(Boolean).forEach((x) => { (byMod[modOf(x)] = byMod[modOf(x)] || []).push(x); });
    const x = top.x + top.w + 56;
    let y = ER.pad;
    Object.entries(byMod).forEach(([label, list]) => {
      const r = place(list, x, y, 1, label, md.fold);
      y += r.h + 24;
    });
    return { boxes, regions, home };
  }

  // the k-th of n relations between the same two boxes: a curve bent off the straight line, and where its name sits
  function bend(p, q, k, n) {
    const off = (k - (n - 1) / 2) * 26;
    const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2, dx = q[0] - p[0], dy = q[1] - p[1], len = Math.hypot(dx, dy) || 1;
    const cx = mx - (dy / len) * off * 2, cy = my + (dx / len) * off * 2;
    return { d: off ? `M${p[0]},${p[1]} Q${cx},${cy} ${q[0]},${q[1]}` : `M${p[0]},${p[1]} L${q[0]},${q[1]}`, x: off ? (mx + cx) / 2 : mx, y: off ? (my + cy) / 2 : my };
  }

  function pairs(list, ends) {  // each edge's place among the edges joining the same two boxes
    const seen = {};
    list.forEach((e) => { const [a, b] = ends(e); const k = [a, b].sort().join('|'); (seen[k] = seen[k] || []).push(e); });
    return (e) => { const [a, b] = ends(e); const all = seen[[a, b].sort().join('|')]; return [all.indexOf(e), all.length]; };
  }

  function erEdge(a, b) {  // where the straight line between two boxes leaves each of them
    const ca = [a.x + a.w / 2, a.y + a.h / 2], cb = [b.x + b.w / 2, b.y + b.h / 2];
    const cut = (box, from, to) => {
      const dx = to[0] - from[0], dy = to[1] - from[1];
      const sx = dx ? (box.w / 2) / Math.abs(dx) : Infinity, sy = dy ? (box.h / 2) / Math.abs(dy) : Infinity;
      const s = Math.min(sx, sy);
      return [from[0] + dx * s, from[1] + dy * s];
    };
    return [cut(a, ca, cb), cut(b, cb, ca)];
  }

  // a picked card with everything it connects to, gathered at reading size around where the person was looking: what
  // points at it on the left, what it points at on the right, what it is a kind of above, its kinds below
  const FOCUS = { rows: 5, gapX: 120, gapY: 20 };

  function erFocus(v, L) {
    const m = S.mg.st, md = ER_VIEW[v].state(), sel = md.focus, base = L.boxes;
    if (!sel || !base[sel]) return null;
    const ids = new Set([sel]), inc = [], out = [];
    m.links.forEach((l) => {
      const other = l.source === sel ? l.target : l.target === sel ? l.source : '';
      if (!other || ids.has(other) || !base[other]) return;
      ids.add(other);
      (l.target === sel ? inc : out).push(other);
    });
    const parent = mgObj(sel).parent;
    const up = parent && base[parent] && !ids.has(parent) ? [parent] : [];
    const down = m.objects.filter((o) => o.parent === sel && base[o.name] && !ids.has(o.name)).map((o) => o.name);
    [...up, ...down].forEach((n) => ids.add(n));
    const chunk = (list) => { const c = []; for (let i = 0; i < list.length; i += FOCUS.rows) c.push(list.slice(i, i + FOCUS.rows)); return c; };
    // the nearest column is the first, so the rest of a long side stands further out
    const columns = [...chunk(inc).reverse(), [...up, sel, ...down], ...chunk(out)];
    const leftN = chunk(inc).length;
    const tall = (c) => c.reduce((a, n) => a + base[n].h, 0) + (c.length - 1) * FOCUS.gapY;
    const cw = Math.max(ER.w, ...[...ids].map((n) => base[n].w));  // columns as wide as the widest card gathered
    const w = columns.length * cw + (columns.length - 1) * FOCUS.gapX;
    const h = Math.max(...columns.map(tall));
    const at = md.anchor || { x: base[sel].x + base[sel].w / 2, y: base[sel].y + base[sel].h / 2 };
    const x0 = Math.max(8, at.x - w / 2), y0 = Math.max(34, at.y - h / 2);
    const boxes = {}, from = {};
    columns.forEach((c, i) => {
      const x = x0 + i * (cw + FOCUS.gapX);
      let y = y0 + (h - tall(c)) / 2;
      c.forEach((n) => {
        boxes[n] = { ...base[n], x, y };
        const was = (md.last && md.last[n]) || base[n];
        from[n] = [was.x - x, was.y - y];
        y += base[n].h + FOCUS.gapY;
      });
    });
    const heads = [];
    if (inc.length) heads.push({ x: x0, text: `들어오는 관계 ${inc.length}` });
    if (out.length) heads.push({ x: x0 + (leftN + 1) * (cw + FOCUS.gapX), text: `나가는 관계 ${out.length}` });
    return { sel, ids, base, boxes, from, heads, w, h, y0, cx: x0 + w / 2, cy: y0 + h / 2 };
  }

  function erSvg(v = 'model') {
    const L = erLayout(v);
    if (!L) return S.mg.st && !S.mg.st.objects.length
      ? '<div class="empty wsstart"><b>정의가 없습니다</b><span class="chips"><button class="btn primary" data-act="mdareanew">+ Object</button><button class="btn" data-act="mdobjnew">+ Entity</button><a class="btn ghost" href="#library">표준 모듈 적용</a></span></div>'
      : '<div class="empty">선택된 Entity가 없습니다.</div>';
    const m = S.mg.st, md = ER_VIEW[v].state();
    const F = erFocus(v, L);
    const live = v === 'model';
    const prob = live ? modelProblems().by : {};
    const quiet = (name) => live && md.only && !(prob[name] || []).length;
    const every = F ? [...Object.values(F.base), ...Object.values(F.boxes)] : Object.values(L.boxes);
    const W = Math.max(...every.map((b) => b.x + b.w), ...L.regions.map((r) => r.x + r.w)) + ER.pad;
    const H = Math.max(...every.map((b) => b.y + b.h), ...L.regions.map((r) => r.y + r.h)) + ER.pad;
    const regions = L.regions.map((r, i) => `<g class="erreg${i && !ER_VIEW[v].all ? ' near' : ''}${F ? ' erdim' : ''}"><rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="14"/><text x="${r.x + 14}" y="${r.y + 19}">${esc(r.label)} · ${r.n}</text>${r.fold ? `<text class="erfoldt" x="${r.x + 14}" y="${r.y + 40}">${esc(r.names.map((n) => mgLabel(n)).join(', '))}</text>` : ''}</g>`).join('');
    const relations = (list, boxes, cls) => {
      const drawn = list.filter((l) => { const a = boxes[l.source], b = boxes[l.target]; return a && b && l.source !== l.target && !(a.folded && b.folded); });
      const place = pairs(drawn, (l) => [boxes[l.source].folded ? boxes[l.source].folded.label : l.source, boxes[l.target].folded ? boxes[l.target].folded.label : l.target]);
      return drawn.map((l) => {
        const a = boxes[l.source], b = boxes[l.target];
        const [p, q] = erEdge(a.folded ? { ...a.folded } : a, b.folded ? { ...b.folded } : b);
        const c = bend(p, q, ...place(l));
        const on = cls === ' top' || (!F && (md.sel === l.source || md.sel === l.target));
        const state = !live ? '' : `${l.new ? ' fresh' : l.pending ? ' pend' : ''}${S.mg.sel === l.name ? ' picked' : ''}${quiet(l.source) && quiet(l.target) ? ' erdim' : ''}`;
        return `<g class="ered${on ? ' on' : ''}${cls}${state}"${live ? ` data-link="${esc(l.name)}"` : ''}>${live ? `<path class="erhit" d="${c.d}"/>` : ''}<path d="${c.d}" marker-end="url(#${on ? 'erhot' : 'erarrow'})"/>
          <text x="${c.x + 6}" y="${c.y - 4}">${esc(l.label || l.name)}</text><text class="card" x="${c.x + 6}" y="${c.y + 10}">${esc(CARD_WORD[l.cardinality] || '')}</text></g>`;
      }).join('');
    };
    const kinds = (list, boxes, cls) => list.map((o) => {
      const a = boxes[o.name], b = o.parent && boxes[o.parent];
      if (!a || !b || a.folded) return '';
      const [p, q] = erEdge(a, b.folded ? b.folded : b);
      return `<g class="ered isa${cls}"><path d="M${p[0]},${p[1]} L${q[0]},${q[1]}" marker-end="url(#erarrow)"/><text x="${(p[0] + q[0]) / 2 + 6}" y="${(p[1] + q[1]) / 2}">↑ 상위</text></g>`;
    }).join('');
    const card = (b, cls, shift) => {
      const o = b.o, on = md.sel === o.name;
      const rows = erRows(o).map((r, i) => {  // a row longer than the card is shortened, and the whole of it shows on hover
        const [t, cut] = erFit(r.text, 11, b.w - 24);
        return `<text class="r ${r.kind}" x="${b.x + 12}" y="${b.y + ER.head + 13 + i * ER.row}">${cut ? `<title>${esc(r.text)}</title>` : ''}${esc(t)}</text>`;
      }).join('');
      const bad = (prob[o.name] || []).length;
      const tag = bad ? `문제 ${bad}` : o.status === 'deprecated' ? '폐기 예정' : o.status === 'draft' ? '초안' : o.new ? '새 Entity' : o.pending ? '변경' : (o.extended_by || []).length ? `+ ${shortMod(o.extended_by[0])}` : (o.concept ? '개념' : '');
      const plus = live && !F ? `<g class="erplus" data-from="${esc(o.name)}"><circle cx="${b.x + b.w}" cy="${b.y + b.h / 2}" r="9"/><text x="${b.x + b.w}" y="${b.y + b.h / 2 + 4}" text-anchor="middle">+</text></g>` : '';
      return `<g class="ernode${on ? ' on' : ''}${o.new ? ' fresh' : o.pending ? ' pend' : ''}${bad ? ' problem' : ''}${quiet(o.name) ? ' erdim' : ''}${cls}" data-er="${esc(o.name)}"${shift ? ` data-dx="${shift[0]}" data-dy="${shift[1]}"` : ''} transform="translate(0,0)"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="10"/>
        <text class="t" x="${b.x + 12}" y="${b.y + 21}">${esc(o.label)}</text><text class="n" x="${b.x + 12 + erTextW(o.label, 13, 800) + 6}" y="${b.y + 21}">${esc(o.name)}</text>
        ${tag ? `<text class="tag" x="${b.x + b.w - 10}" y="${b.y + 21}" text-anchor="end">${esc(tag)}</text>` : ''}
        <line x1="${b.x}" y1="${b.y + ER.head - 4}" x2="${b.x + b.w}" y2="${b.y + ER.head - 4}" class="sep"/>${rows}${plus}</g>`;
    };
    let body;
    if (F) {  // what is not connected stays where it was, faint; what is connected is drawn last, so it lies on top
      const apart = (l) => !F.ids.has(l.source) && !F.ids.has(l.target);
      const touches = (l) => l.source === F.sel || l.target === F.sel;
      const faint = relations(m.links.filter(apart), F.base, ' erdim') + kinds(m.objects.filter((o) => !F.ids.has(o.name) && !F.ids.has(o.parent)), F.base, ' erdim')
        + Object.values(F.base).filter((b) => !F.ids.has(b.o.name)).map((b) => card(b, ' erdim')).join('');
      const near = relations(m.links.filter(touches), F.boxes, ' top') + kinds(m.objects.filter((o) => o.name === F.sel || o.parent === F.sel), F.boxes, ' top')
        + Object.values(F.boxes).map((b) => card(b, '', F.from[b.o.name])).join('')
        + F.heads.map((x) => `<text class="erside" x="${x.x}" y="${F.y0 - 12}">${esc(x.text)}</text>`).join('');
      body = `${regions}${faint}${near}`;
    } else body = `${regions}${relations(m.links, L.boxes, '')}${kinds(m.objects, L.boxes, '')}${Object.values(L.boxes).filter((b) => !b.folded).map((b) => card(b, '')).join('')}`;
    const z = md.zoom || 1;
    return `<svg class="ersvg" width="${Math.round(W * z)}" height="${Math.round(H * z)}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(L.home)} 모듈의 Entity와 관계">
      <defs><marker id="erarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker>
      <marker id="erhot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker></defs>
      ${body}</svg>`;
  }

  function erCard() {
    const md = S.md, fold = md.fold;
    return `<div class="wstools"><button class="btn sm" data-act="mdobjnew">+ Entity</button><button class="btn sm" data-act="mdlinknew">+ Relation</button><button class="btn sm" data-act="erreset">정렬</button>
      <button class="btn sm" data-act="erfold" aria-pressed="${!!fold}">${fold ? '모듈 펼치기' : '모듈 접기'}</button>
      <button class="btn sm${md.focus ? ' primary' : ''}" data-act="mdfocus" aria-pressed="${!!md.focus}">연결만 보기</button><button class="btn sm${md.only ? ' primary' : ''}" data-act="mdonly" aria-pressed="${!!md.only}">문제만 보기</button>
      <span class="grow"></span><span class="erzoom" role="group" aria-label="확대"><button class="iconbtn" data-act="erzoom" data-z="-1" aria-label="축소">−</button><button class="btn sm ghost" data-act="erzoom" data-z="0" title="화면에 맞춤">${Math.round((md.zoom || 1) * 100)}%</button><button class="iconbtn" data-act="erzoom" data-z="1" aria-label="확대">+</button></span></div>
      <div class="ercanvas${md.focus ? ' focused' : ''}" id="ercanvas">${erSvg()}</div>`;
  }

  function mountEr(v = 'model') {
    declutter();  // a card drawn again on its own gets its info button back
    const box = $(`#${ER_VIEW[v].box}`), md = ER_VIEW[v].state();
    if (!box || box.dataset.on) return;
    box.dataset.on = '1';
    let drag = null;
    const at = (ev) => { const r = box.getBoundingClientRect(), z = md.zoom || 1; return [(ev.clientX - r.left + box.scrollLeft) / z, (ev.clientY - r.top + box.scrollTop) / z]; };
    const under = (ev) => { const t = document.elementFromPoint(ev.clientX, ev.clientY); return t && t.closest('[data-er]'); };
    box.addEventListener('pointerdown', (ev) => {
      const plus = ev.target.closest('[data-from]');
      if (plus) {  // from the + on a card's edge to another card makes a relation
        drag = { from: plus.dataset.from, x0: ev.clientX, y0: ev.clientY, moved: false };
        box.setPointerCapture(ev.pointerId);
        return;
      }
      const g = ev.target.closest('[data-er]');
      const edge = !g && ev.target.closest('[data-link]');
      const L = g && erLayout(v), b = L && L.boxes[g.dataset.er];
      if (g && b && !b.folded && !md.focus) drag = { name: g.dataset.er, x0: ev.clientX, y0: ev.clientY, bx: b.x, by: b.y, moved: false };
      else drag = { pan: true, card: g ? g.dataset.er : '', edge: edge ? edge.dataset.link : '', x0: ev.clientX, y0: ev.clientY, sl: box.scrollLeft, st: box.scrollTop, moved: false };
      box.setPointerCapture(ev.pointerId);
    });
    if (v === 'model') {
      box.addEventListener('dragover', (ev) => { if ([...ev.dataTransfer.types].includes('text/x-column')) ev.preventDefault(); });
      box.addEventListener('drop', (ev) => {
        const c = ev.dataTransfer.getData('text/x-column');
        if (!c) return;
        ev.preventDefault();
        const [table, column, type] = c.split('|'), g = ev.target.closest('[data-er]'), o = g && mgObj(g.dataset.er);
        if (!o) { toast('컬럼은 Entity 카드 위에 놓아 주세요.', true); return; }
        if (o.table !== table) { toast(`${table} 테이블의 컬럼이라 이 Entity에 추가하지 못했습니다. ${table}${josa(table, '을', '를')} 읽는 Entity 카드에 놓아 주세요.`, true); return; }
        columnToProp(table, column, type, o.name);
      });
    }
    box.addEventListener('pointermove', (ev) => {
      if (!drag) return;
      const dx = ev.clientX - drag.x0, dy = ev.clientY - drag.y0;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      drag.moved = true;
      if (drag.from) {
        const L = erLayout(v), b = L.boxes[drag.from], [x, y] = at(ev), svg = box.querySelector('svg');
        let line = svg.querySelector('#erdrag');
        if (!line) { line = document.createElementNS('http://www.w3.org/2000/svg', 'line'); line.id = 'erdrag'; svg.appendChild(line); }
        line.setAttribute('x1', b.x + b.w); line.setAttribute('y1', b.y + b.h / 2); line.setAttribute('x2', x); line.setAttribute('y2', y);
        box.querySelectorAll('.droptarget').forEach((n) => n.classList.remove('droptarget'));
        const g = under(ev);
        if (g && g.dataset.er !== drag.from) g.classList.add('droptarget');
        return;
      }
      if (drag.pan) { box.scrollLeft = drag.sl - dx; box.scrollTop = drag.st - dy; box.classList.add('panning'); return; }
      const z = md.zoom || 1;
      md.pos[drag.name] = { x: Math.max(4, drag.bx + dx / z), y: Math.max(30, drag.by + dy / z) };
      box.innerHTML = erSvg(v);
    });
    const end = (ev) => {
      const was = drag;
      drag = null;
      box.classList.remove('panning');
      if (was && was.from) {
        const line = box.querySelector('#erdrag');
        if (line) line.remove();
        box.querySelectorAll('.droptarget').forEach((n) => n.classList.remove('droptarget'));
        const g = was.moved && under(ev);
        if (g && g.dataset.er !== was.from) linkDraft(was.from, g.dataset.er, ev);
        return;
      }
      if (was && was.moved && was.name) erPosSave();
      if (!was || was.moved) return;
      if (!was.pan) ER_VIEW[v].pick(was.name);
      else if (was.card) ER_VIEW[v].pick(was.card);
      else if (was.edge) modelLink(was.edge);
      else if (md.focus) ER_VIEW[v].clear();
    };
    box.addEventListener('pointerup', end);
    box.addEventListener('pointercancel', end);
    box.addEventListener('wheel', (ev) => {  // the wheel zooms, around where the pointer is; the canvas pans by dragging
      ev.preventDefault();
      erZoomAt(ev, ev.deltaY < 0 ? 1 : -1, v);
    }, { passive: false });
    if (md.zoom === undefined) erZoom(0, ER_VIEW[v].all ? 0.6 : 0.75, v);  // the first look fits the width, as far as names stay readable
  }

  function erZoomAt(ev, step, v) {  // zoom so that the point under the pointer stays under it
    const md = ER_VIEW[v].state(), box = $(`#${ER_VIEW[v].box}`), svg = box && box.querySelector('svg');
    if (!svg) return;
    const s = svg.getBoundingClientRect(), z0 = md.zoom || 1;
    const cx = (ev.clientX - s.left) / z0, cy = (ev.clientY - s.top) / z0;  // the drawing point under the pointer
    erZoom(step, 0.4, v);
    const after = $(`#${ER_VIEW[v].box}`), z1 = md.zoom || 1;
    if (!after) return;
    const r = after.getBoundingClientRect();  // a drawing narrower than the canvas is centred and does not scroll, so this holds only where it can
    after.scrollLeft = cx * z1 - (ev.clientX - r.left);
    after.scrollTop = cy * z1 - (ev.clientY - r.top);
  }

  function erCols(v) {  // how many cards stand side by side: as many as the canvas is wide at reading size
    const md = ER_VIEW[v].state(), box = $(`#${ER_VIEW[v].box}`);
    if (!box || !box.clientWidth) return;
    const unit = ER.w + ER.gapX, inner = box.clientWidth - 2 * ER.pad;
    if (ER_VIEW[v].all) {  // whole modules side by side
      const region = ER.cols * ER.w + (ER.cols - 1) * ER.gapX + 2 * ER.regionPad;
      md.perRow = Math.max(2, Math.min(4, Math.floor((inner + 40) / (region + 40))));  // never fewer than two: a narrow canvas fits by zoom instead
    } else {  // the picked module's cards, beside the one-card column of the modules it reaches
      const avail = inner - 56 - (ER.w + 2 * ER.regionPad);
      md.cols = Math.max(ER.cols, Math.min(4, Math.floor((avail - 2 * ER.regionPad + ER.gapX) / unit)));
    }
  }

  function erExtent(v) {  // the drawing's size at reading size
    const L = erLayout(v);
    if (!L) return null;
    const every = Object.values(L.boxes);
    return { W: Math.max(...every.map((b) => b.x + b.w), ...L.regions.map((r) => r.x + r.w)) + ER.pad,
      H: Math.max(...every.map((b) => b.y + b.h), ...L.regions.map((r) => r.y + r.h)) + ER.pad };
  }

  function erZoom(step, floor = 0.4, v = 'model') {  // 0 fits the diagram to the canvas's width
    const md = ER_VIEW[v].state(), box = $(`#${ER_VIEW[v].box}`);
    if (step === 0 && md.focus) { focusPaint(v); return; }
    if (step === 0 && box) {
      erCols(v);
      const e = erExtent(v);
      md.zoom = e ? Math.min(1, Math.max(floor, (box.clientWidth - 8) / e.W)) : 1;
    } else md.zoom = Math.min(1.6, Math.max(0.4, Math.round(((md.zoom || 1) + step * 0.1) * 10) / 10));
    const card = $(`#${ER_VIEW[v].card}`);
    if (card) {
      const sl = box ? box.scrollLeft : 0, st = box ? box.scrollTop : 0;
      card.innerHTML = ER_VIEW[v].html(); mountEr(v);
      const nb = $(`#${ER_VIEW[v].box}`);
      if (nb) { nb.scrollLeft = sl; nb.scrollTop = st; }
    }
  }

  // the whole ontology as the same cards: every module a region, a press opens the object's definition beside it
  function ontoCard() {
    const ov = S.ov, o = ov.focus && S.mg.st ? mgObj(ov.focus) : null;
    const zoom = `<span class="erzoom" role="group" aria-label="확대"><button class="iconbtn" data-act="erzoom" data-v="onto" data-z="-1" aria-label="축소">−</button><button class="btn sm ghost" data-act="erzoom" data-v="onto" data-z="0" title="화면에 맞춤">${Math.round((ov.zoom || 1) * 100)}%</button><button class="iconbtn" data-act="erzoom" data-v="onto" data-z="1" aria-label="확대">+</button></span>`;
    return `<div class="card"><div class="ch">${o ? `${esc(o.label)}${josa(o.label, '과', '와')} 연결된 카드 <span class="chip sm b">${ov.near || 0}</span>` : '온톨로지 전체'}<div class="right">${o ? '<button class="btn sm" data-act="ontoall">전체 보기</button>' : ''}${zoom}</div></div>
      <div class="cb ercanvas${o ? ' focused' : ''}" id="ontocanvas">${S.mg.st ? erSvg('onto') : '<div class="empty"><span class="spin"></span>정의를 읽는 중입니다.</div>'}</div>
      <div class="cb ernote muted xp">🔑 키 · <span class="erk expr">= 계산 속성</span> · <span class="erk ext">다른 모듈이 더한 속성</span></div></div>`;
  }

  function focusPaint(v) {  // the card again, the gathered cards fitted to the canvas and in the middle of it
    const ov = ER_VIEW[v].state(), card = $(`#${ER_VIEW[v].card}`), was = $(`#${ER_VIEW[v].box}`);
    if (!card || !was) return;
    const F = ov.focus ? erFocus(v, erLayout(v)) : null;
    if (F) {
      ov.zoom = Math.min(1, Math.max(0.5, Math.min((was.clientWidth - 32) / F.w, (was.clientHeight - 64) / (F.h + 34))));
      ov.near = F.ids.size - 1;
    }
    card.innerHTML = ER_VIEW[v].html();
    mountEr(v);
    const box = $(`#${ER_VIEW[v].box}`);
    if (!F || !box) return;
    box.scrollLeft = Math.max(0, F.cx * ov.zoom - box.clientWidth / 2);
    box.scrollTop = Math.max(0, F.cy * ov.zoom - box.clientHeight / 2);
    ov.last = Object.fromEntries(Object.entries(F.boxes).map(([k, b]) => [k, { x: b.x, y: b.y }]));
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const moving = [...box.querySelectorAll('[data-dx]')];  // each card travels from where it was, so it can be followed
    moving.forEach((g) => { g.style.transition = 'none'; g.style.transform = `translate(${g.dataset.dx}px, ${g.dataset.dy}px)`; });
    box.getBoundingClientRect();
    requestAnimationFrame(() => moving.forEach((g) => { g.style.transition = 'transform .28s ease'; g.style.transform = ''; }));
  }

  function focusOn(v, name) {
    const ov = ER_VIEW[v].state(), box = $(`#${ER_VIEW[v].box}`);
    if (!ov.focus && box) {  // what to come back to, and the spot to gather around
      const z = ov.zoom || 1;
      ov.before = { zoom: ov.zoom, left: box.scrollLeft, top: box.scrollTop };
      ov.anchor = { x: (box.scrollLeft + box.clientWidth / 2) / z, y: (box.scrollTop + box.clientHeight / 2) / z };
    }
    ov.sel = name; ov.focus = name;
    focusPaint(v);
  }

  function focusOff(v) {
    const ov = ER_VIEW[v].state(), b = ov.before || {};
    if (!ov.focus) return;
    Object.assign(ov, { focus: '', anchor: null, last: null, zoom: b.zoom });
    focusPaint(v);
    const box = $(`#${ER_VIEW[v].box}`);
    if (box) { box.scrollLeft = b.left || 0; box.scrollTop = b.top || 0; }
  }

  // what the definition check would refuse in a property, said under its field, with the way to fix it
  function propIssues(v, mode) {
    const out = {};
    const other = S.mg.st.properties.find((x) => v.name && x.name === v.name && x.object !== v.object && !x.inherited && x.type !== v.type);
    if (other && !v.expr) out.type = { text: `같은 이름의 Property가 ${mgLabel(other.object)}에서 ${other.type} 타입이라 타입이 맞지 않습니다. ${other.type}${josa(other.type, '으로', '로')} 맞춰 주세요.`, fix: ['type', other.type, `${other.type}${josa(other.type, '으로', '로')} 맞추기`] };
    if (mode === 'new' && v.name && !/^[a-z][a-z0-9_]*$/.test(v.name)) out.name = { text: '영문 이름은 소문자로 시작하고 소문자, 숫자, _만 씁니다.' };
    if (mode === 'new' && v.name && mgProps(v.object).some((p) => p.name === v.name)) out.name = { text: `${mgLabel(v.object)}에 '${v.name}' 속성이 이미 있습니다.` };
    if (v.type === 'enum' && !String(v.values || '').trim()) out.values = { text: '허용값 타입은 허용값이 하나 이상 있어야 합니다.' };
    return out;
  }
  const fieldErr = (e) => (e ? `<div class="ferr" role="alert">${esc(e.text)}${e.fix ? ` <button class="btn sm" data-act="mgfix" data-f="${esc(e.fix[0])}" data-v="${esc(e.fix[1])}">${esc(e.fix[2])}</button>` : ''}</div>` : '');

  // ---- a new object or property is named by its display name: the English name is suggested from it (the words drafts
  //      use, server side), stays editable, and is checked where it is typed; an object without a table keys on <name>_id
  const REQUIRED = ' <span class="chip sm">필수</span>';
  const snakeOf = (s) => (s ? propName(String(s).replace(/([a-z0-9])([A-Z])/g, '$1_$2')) : '');
  const autoKey = (v) => (v.name ? `${snakeOf(v.name)}_id` : '');
  const naming = (f) => f && f.mode === 'new' && ['object', 'prop', 'area'].includes(f.kind);
  function nameIssue(f) {
    const v = f.v;
    if (f.kind === 'prop') return propIssues(v, 'new').name || null;
    if (!v.name) return null;
    if (!IDENT.test(v.name)) return { text: '영문 이름은 영문자로 시작하고 영문자, 숫자, _만 씁니다.' };
    if (f.kind === 'area') return mgArea(v.name) ? { text: '같은 영문 이름의 Object가 이미 있습니다. 다른 영문 이름을 입력해 주세요.' } : null;
    return mgObj(v.name) ? { text: '같은 영문 이름의 Entity가 이미 있습니다. 다른 영문 이름을 입력해 주세요.' } : null;
  }
  function nameHint(f) {
    const v = f.v, s = f.sug;
    if (v.touched) return '직접 입력했습니다.';
    if (!s || !v.name || s.name !== v.name) return '';
    return s.roman ? '모르는 단어가 있어 로마자로 표기했습니다. 확인해 주세요.' : `자동 생성 · ${s.parts.map(([k, w]) => `${k}=${w}`).join(' + ')}`;
  }
  const keyHint = (v) => `미입력 시 ${autoKey(v) || '<영문 이름>_id'}`;
  const nameField = (f, hold) => `<div class="field"><label>영문 이름</label><input type="text" data-in="mgf" data-f="name" value="${esc(f.v.name)}" placeholder="${esc(hold)}" class="mono" autocomplete="off">
    <span class="muted" style="font-size:11.5px" data-hint="name">${esc(nameHint(f))}</span></div><div data-err="name">${fieldErr(nameIssue(f))}</div>`;
  function paintName() {  // what follows the name, painted where it stands: the form is not drawn again under the cursor
    const f = S.mg.form;
    if (!naming(f)) return;
    const v = f.v, all = (s) => document.querySelectorAll(`#main ${s}`);
    all('[data-in="mgf"][data-f="name"]').forEach((e) => { if (e !== document.activeElement && e.value !== v.name) e.value = v.name; });
    all('[data-hint="name"]').forEach((e) => { e.textContent = nameHint(f); });
    all('[data-err="name"]').forEach((e) => { e.innerHTML = fieldErr(nameIssue(f)); });
    all('[data-in="mgf"][data-f="key"][data-auto]').forEach((e) => { e.placeholder = autoKey(v) || 'coupon_id'; });
    all('[data-hint="key"]').forEach((e) => { e.textContent = keyHint(v); });
  }
  async function nameNow(f) {  // the suggestion for the display name as it stands now
    const v = f.v, label = String(v.label || '').trim();
    if (!label) return;
    try {
      const got = await api(`naming?kind=${f.kind === 'prop' ? 'property' : 'object'}&label=${encodeURIComponent(label)}`);
      if (S.mg.form !== f || v.touched || String(v.label || '').trim() !== label) return;
      f.sug = got; v.name = got.name;
    } catch (_) { /* the person can still type one */ }
  }
  let nameTimer = 0;
  function suggestName(f) { clearTimeout(nameTimer); nameTimer = setTimeout(() => nameNow(f).then(paintName), 200); }
  function formStop(field, msg) {  // a form that cannot be saved says which field and leaves the cursor there
    toast(msg, true);
    render();
    const e = $(`#main [data-in="mgf"][data-f="${field}"]`);
    if (!e) return;
    const box = e.closest('.field');
    if (box) box.classList.add('fieldhot');
    e.focus();
  }

  // a form painted again while a person moves through it: the field they are on, or moved to, keeps the cursor; a press
  // under way ends on the button it started on before the form is painted (a text field's change comes on leaving it)
  function repaintKept(wait) {
    if (wait && document.querySelector('#main :active')) { document.addEventListener('pointerup', () => setTimeout(() => repaintKept(false), 0), { once: true, capture: true }); return; }
    const a = document.activeElement, d = (a && a.dataset) || {};
    const at = d.in ? ['in', 'f', 'list', 'i', 'k', 'p'].filter((k) => d[k] !== undefined).map((k) => `[data-${k}="${CSS.escape(d[k])}"]`).join('') : '';
    const caret = a && typeof a.selectionStart === 'number' ? [a.selectionStart, a.selectionEnd] : null;
    render();
    const e = at && $(`#main ${at}`);
    if (!e || e === document.activeElement) return;
    e.focus({ preventScroll: true });
    if (caret) try { e.setSelectionRange(caret[0], caret[1]); } catch (_) { /* a field without a caret */ }
  }

  function objectStatus(o) {  // where an object comes from, who adds to it, whether anything reads it, whether it is being changed
    const u = S.md.uses && S.md.uses.id === `object:${o.name}` ? S.md.uses.list : null;
    return `<div class="chips mdstat"><button class="chip sm b" data-act="libshow" data-mod="${esc(o.module)}" title="라이브러리에서 이 모듈로">정의 · ${esc(shortMod(o.module_label || o.module))}</button>${(o.extended_by || []).map((x) => `<button class="chip sm warn" data-act="libshow" data-mod="${esc(x)}" title="라이브러리에서 이 모듈로">확장 · ${esc(shortMod(x))}</button>`).join('')}
      ${statusChip(o)}${o.new ? '<span class="chip sm warn">새로 추가</span>' : o.pending ? '<span class="chip sm warn">변경 대기</span>' : ''}${u ? (u.length ? `<span class="chip sm${o.status === 'deprecated' ? ' bad' : ''}" title="${o.status === 'deprecated' ? '폐기 예정 · 사용처 있음' : ''}">사용처 ${u.length}</span>` : '<span class="chip sm">사용처 없음</span>') : ''}
      ${S.mg.st.unlinked.includes(o.name) ? '<span class="chip sm warn">Relation 없음</span>' : ''}</div>`;
  }

  function modelYaml(o) {
    const y = S.md.yaml;
    const id = `object:${o.name}`;
    if (!y || y.id !== id) {
      if (!S.md.yamlBusy) {
        S.md.yamlBusy = true;
        api(`element/yaml?id=${encodeURIComponent(id)}`).then((x) => { S.md.yaml = { id, text: x.yaml, was: x.yaml }; }).catch((e) => { S.md.yaml = { id, error: e.message }; })
          .finally(() => { S.md.yamlBusy = false; paintSide(); });
      }
      return '<div class="empty"><span class="spin"></span>정의를 읽는 중입니다.</div>';
    }
    if (y.error) return `<div class="hint warn">${esc(y.error)}</div>`;
    return `<div class="muted" style="font-size:12px;margin-bottom:6px">${esc(o.label)} 정의 · 대기 중인 변경 반영</div>
      <textarea class="mono mdyaml" data-in="mdyaml" spellcheck="false" aria-label="${esc(o.label)} YAML">${esc(y.text)}</textarea>
      ${y.err ? `<div class="ferr" role="alert">${esc(y.err)}</div>` : ''}
      <div style="display:flex;gap:8px;margin-top:8px"><button class="btn sm primary" data-act="mdyamlsave"${y.text === y.was || S.mg.busy ? ' disabled' : ''}>YAML 반영</button><button class="btn sm" data-act="mdyamlreset"${y.text === y.was ? ' disabled' : ''}>되돌리기</button>
      <button class="btn sm ghost" data-act="mdedit" data-module="${esc(o.module)}">모듈 파일 전체 편집</button></div>`;
  }

  function modelComments(o) {
    const id = `object:${o.name}`, c = S.md.notes;
    if (!c || c.id !== id) {
      api(`element/comments?id=${encodeURIComponent(id)}`).then((x) => { S.md.notes = { id, list: x.comments }; paintSide(); }).catch(fail);
      return '<div class="empty"><span class="spin"></span></div>';
    }
    const list = c.list.map((x) => `<div class="cmt"><span class="av">${esc(String(x.by || '?').slice(0, 1))}</span><div><div class="muted" style="font-size:12px"><b style="color:var(--ink)">${esc(x.by)}</b> · ${esc(String(x.at || '').replace('T', ' '))}</div><div style="font-size:13px;margin-top:2px">${esc(x.text)}</div></div></div>`).join('');
    return `${list || '<div class="muted" style="font-size:12.5px">등록된 댓글이 없습니다.</div>'}
      <textarea data-in="mdnote" rows="2" placeholder="댓글 쓰기" style="width:100%;margin-top:10px;box-sizing:border-box">${esc(S.md.note || '')}</textarea>
      <button class="btn sm primary" data-act="mdnotesave" style="margin-top:6px">댓글 남기기</button>`;
  }

  // the edits waiting, what they reach, and the way to try them, take the last one back or file them
  function wsChanges() {
    const m = S.mg.st, w = m.workspace, md = S.md, t = md.trial;
    if (!w.dirty) return '<div class="empty" style="padding:18px 12px">변경된 내용이 없습니다.</div>';
    const row = (e, i) => `<div class="wsrow"><div><b>${esc(OP_WORD[e.op] || e.op)}</b> <span class="mono muted cn">${esc(elementText(e.target))}</span>${e.took_out.length ? `<div class="muted" style="font-size:11.5px">함께 제외 ${e.took_out.length}개</div>` : ''}</div><button class="btn sm" data-act="mdrevert" data-i="${i}"${S.mg.busy ? ' disabled' : ''}>되돌리기</button></div>`;
    const list = w.edits.length ? w.edits.map(row).join('') : [...w.diff.added.map((x) => ['추가', x]), ...w.diff.changed.map((x) => ['변경', x]), ...w.diff.removed.map((x) => ['제외', x])].map(([a, x]) => `<div class="wsrow"><div><b>${a}</b> <span class="mono muted cn">${esc(elementText(x))}</span></div></div>`).join('');
    const checked = !w.issues.length;
    const tried = t && t.gates ? (t.passed ? 'ok' : 'bad') : '';
    const steps = `<div class="wssteps"><span class="chip sm ${checked ? 'ok' : 'bad'}">1 검사 ${checked ? '통과' : `오류 ${w.issues.length}`}</span>›<span class="chip sm ${tried}">2 사본 시험${t && t.gates ? ` ${t.gates.filter((g) => g.passed).length}/${t.gates.length}` : ''}</span>›<span class="chip sm">3 ${selfApply() ? '적용' : fileWord()}</span></div>`;
    const blocks = w.issues.length ? `<div class="banner no" style="padding:10px 12px"><div class="why" style="font-size:12.5px"><b>${selfApply() ? '적용할 수 없습니다.' : '변경 요청을 만들 수 없습니다.'}</b> 아래 정의 검사 오류를 먼저 고쳐 주세요.<div class="loglist" style="margin-top:6px">${w.issues.slice(0, 6).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div></div>` : '';
    const reach = [['queries', '질의'], ['decisions', '판정'], ['questions', '검증 질문'], ['actions', 'Action']].map(([k, l]) => `${l} ${(w.impact || {})[k] || 0}`).join(' · ');
    return `<div class="wslist">${list}</div>${steps}${blocks}<div class="muted" style="font-size:12px">영향: ${esc(reach)}</div>
      ${t && t.error ? `<div class="hint warn">${esc(t.error)}</div>` : ''}${t && t.gates ? trialPanel(t) : ''}
      <div class="wsbtns"><button class="btn sm" data-act="mdtrial"${t && t.busy ? ' disabled' : ''}>${t && t.busy ? '<span class="spin"></span>시험 중' : '사본에서 시험'}</button><button class="btn sm primary" data-act="mgpropose"${S.mg.busy || w.issues.length || (t && t.busy) ? ' disabled' : ''}>${selfApply() ? '적용' : fileWord(true)}</button><span class="grow"></span><button class="btn sm ghost danger" data-act="mgdiscard">모두 취소</button></div>
      <details class="wsyaml"><summary>정의 파일 보기 · ${esc(w.label)}</summary><pre class="code">${esc(w.yaml)}</pre></details>`;
  }

  // what is wrong with the definition, element by element: the last measurement, less what the pending edits already mend
  let probMemo = null;
  function modelProblems() {
    const m = S.mg.st;
    if (!m || m.error) return { list: [], by: {}, elements: new Set() };
    if (probMemo && probMemo.st === m && probMemo.issues === S.iss.list) return probMemo;
    const w = m.workspace;
    const still = new Set((w.findings || []).map((f) => f.element));
    const objectOf = (el) => { const [k, ...r] = el.split(':'), n = r.join(':'); return k === 'property' ? n.split('.')[0] : k === 'object' ? n : ((m.links.find((l) => l.name === n) || {}).source || ''); };
    const list = [];
    issueAll().forEach((x) => x.items.forEach((it, i) => {
      if (!/^(object|property|link):/.test(it.element)) return;
      const mended = w.dirty && ['컬럼 없음', '테이블 없음'].includes(it.say) && !still.has(it.element);
      if (!list.some((y) => y.element === it.element)) list.push({ element: it.element, label: it.label, say: it.say, issue: x.id, i, mended, object: objectOf(it.element) });
    }));
    (w.findings || []).forEach((f) => {  // what the pending edits themselves would break
      if (!list.some((y) => y.element === f.element)) list.push({ element: f.element, label: elementText(f.element), say: FINDING[f.kind] || f.kind, issue: '', i: -1, mended: false, object: objectOf(f.element) });
    });
    const by = {};
    list.filter((x) => !x.mended).forEach((x) => { (by[x.object] = by[x.object] || []).push(x); });
    probMemo = { st: m, issues: S.iss.list, list, by, elements: new Set(list.filter((x) => !x.mended).map((x) => x.element)) };
    return probMemo;
  }

  function wsProblems() {
    const m = S.mg.st, P = modelProblems();
    const objects = [...new Set(P.list.map((x) => x.object))];
    const fixRow = (x) => `<div class="wsrow"><span>${esc(x.label.split(' · ').pop())} · ${esc(x.say)}</span>${x.mended ? '<span class="chip sm ok">변경으로 해결</span>' : x.issue ? `<button class="btn sm" data-act="mdprob" data-id="${esc(x.issue)}" data-i="${x.i}">고치기</button>` : `<a class="btn sm" href="${elementTo(x.element)}">열기</a>`}</div>`;
    const broken = objects.map((o) => `<div class="mdgh">${esc(mgLabel(o))}</div>${P.list.filter((x) => x.object === o).map(fixRow).join('')}`).join('');
    const look = [...m.unlinked.map((n) => [n, 'Relation 없음']), ...m.unread.filter((n) => !m.unlinked.includes(n)).map((n) => [n, '사용처 없음'])];
    const check = look.length ? `<div class="mdgh" style="margin-top:8px">확인 필요</div>${look.map(([n, w]) => `<button class="wsrow wsbtnrow" data-act="mdpick" data-name="${esc(n)}"><span>${esc(mgLabel(n))} · ${w}</span></button>`).join('')}` : '';
    const defs = m.workspace.issues.length ? `<div class="mdgh" style="color:#a3261e">정의 검사 오류</div>${m.workspace.issues.slice(0, 6).map((x) => `<div class="wsrow mono" style="font-size:11.5px">${esc(x)}</div>`).join('')}` : '';
    return defs + broken + check || '<div class="empty" style="padding:18px 12px">최근 측정에서 정의 문제를 찾지 못했습니다.</div>';
  }

  function wsSource() {
    const m = S.mg.st, md = S.md, s = m.sources.source;
    if (!s.name) return '<div class="hint" style="margin:8px">데이터 소스 미연결</div>';
    const used = (t, c) => t.objects.flatMap((o) => mgProps(o)).find((p) => (p.column || '').toLowerCase() === c.toLowerCase() || (p.columns || []).includes(c));
    const row = (t) => {
      const open = md.src[t.table], free = t.columns.filter((c) => !used(t, c.name)).length;
      const cols = open ? t.columns.map((c) => { const u = used(t, c.name); return `<button class="srcc" draggable="true" data-act="mdcol" data-col="${esc(`${t.table}|${c.name}|${c.type}`)}" title="카드에 끌어 놓거나 눌러서 속성으로 추가합니다"><span class="mono">${esc(c.name)}</span><span class="muted">${esc(c.type)}</span>${u ? `<span class="chip sm">${esc(u.label || u.name)}</span>` : '<span class="chip sm warn">미사용</span>'}</button>`; }).join('') : '';
      return `<div class="srct"><button class="srch" data-act="mdsrc" data-t="${esc(t.table)}" aria-expanded="${!!open}"><span class="srca">${open ? '▾' : '▸'}</span><b class="mono">${esc(t.table)}</b><span class="grow"></span>${t.objects.length ? `<span class="muted">${esc(t.objects.map(mgLabel).join(', '))}</span>` : t.links.length ? '<span class="muted">연결 테이블</span>' : '<span class="chip sm warn">미사용</span>'}${free && t.objects.length ? `<span class="chip sm warn">${free}</span>` : ''}</button>${open ? `<div class="srcb">${cols}${t.objects.length ? '' : `<button class="btn sm" data-act="mgobjnew" data-t="${esc(t.table)}" style="margin:6px">Entity로 추가</button>`}</div>` : ''}</div>`;
    };
    return s.tables.slice().sort((a, b) => (b.objects.length ? 1 : 0) - (a.objects.length ? 1 : 0) || a.table.localeCompare(b.table)).map(row).join('');
  }

  function wsLeft() {
    const md = S.md, m = S.mg.st, w = m.workspace, P = modelProblems();
    const n = P.list.filter((x) => !x.mended).length, c = w.edits.length || (w.dirty ? w.diff.added.length + w.diff.changed.length + w.diff.removed.length : 0);
    const tabs = [['objects', '정의', 0], ['source', '데이터 소스', 0], ['issues', '문제', n], ['changes', '변경', c]].map(([k, l, x]) => `<button class="${md.left === k ? 'on' : ''}" data-act="mdleft" data-k="${k}">${l}${x ? ` <span class="wsn${k === 'issues' ? ' bad' : ''}">${x}</span>` : ''}</button>`).join('');
    const body = md.left === 'source' ? wsSource() : md.left === 'issues' ? wsProblems() : md.left === 'changes' ? wsChanges()
      : `<div style="padding:8px"><input type="text" data-in="mdq" value="${esc(md.q)}" placeholder="Entity · Property · Relation · 컬럼 검색" aria-label="검색"></div><div class="mdtree" id="mdtree">${modelTree()}</div>`;
    return `<div class="wstabs">${tabs}</div><div class="wsleftb">${body}</div>`;
  }

  function wsBar() {
    const w = S.mg.st.workspace, md = S.md, t = md.trial;
    const n = w.edits.length || (w.dirty ? w.diff.added.length + w.diff.changed.length + w.diff.removed.length : 0);
    const imp = Object.entries({ queries: '질의', decisions: '판정', questions: '검증 질문', actions: 'Action' }).filter(([k]) => (w.impact || {})[k]).map(([k, l]) => `${l} ${w.impact[k]}`).join(' · ');
    const state = w.dirty ? `<button class="chip sm warn" data-act="mdleft" data-k="changes">변경 ${n}건</button><span class="muted wsmeta">${esc(w.label)}에 기록${imp ? ` · 영향: ${esc(imp)}` : ''}</span>` : '<span class="muted wsmeta">바뀐 내용 없음</span>';
    const tried = t && t.gates ? `<button class="chip sm ${t.passed ? 'ok' : 'bad'}" data-act="mdleft" data-k="changes">${t.passed ? '✓ 사본 시험 통과' : '사본 시험 실패'} ${t.gates.filter((g) => g.passed).length}/${t.gates.length}</button>` : '';
    const blocked = w.issues.length ? `<button class="chip sm bad" data-act="mdleft" data-k="changes">검사 오류 ${w.issues.length}건</button>` : '';
    const seg = `<div class="seg wsseg"><button class="${md.view === 'diagram' ? 'on' : ''}" data-act="mdview" data-k="diagram">다이어그램</button><button class="${md.view === 'table' ? 'on' : ''}" data-act="mdview" data-k="table">표</button></div>`;
    return `<div class="wsbar">${subTabs()}${seg}<a class="btn sm ghost" href="#catalog">파일로 초안</a><span class="grow"></span>${state}${tried}${blocked}
      <button class="btn sm" data-act="mdundo"${w.edits.length ? '' : ' disabled'}>되돌리기</button><button class="btn sm" data-act="mdredo"${w.redo ? '' : ' disabled'}>다시 실행</button><button class="btn sm primary" data-act="mdreview"${!w.dirty || S.mg.busy || (t && t.busy) ? ' disabled' : ''}>${fileWord(true)}</button>
      ${md.view === 'table' ? '' : `<button class="iconbtn" data-act="mdpanel" data-k="leftOff" aria-label="왼쪽 패널 ${md.leftOff ? '펼치기' : '접기'}" title="왼쪽 패널 ${md.leftOff ? '펼치기' : '접기'}">◧</button><button class="iconbtn" data-act="mdpanel" data-k="rightOff" aria-label="오른쪽 패널 ${md.rightOff ? '펼치기' : '접기'}" title="오른쪽 패널 ${md.rightOff ? '펼치기' : '접기'}">◨</button>`}</div>`;
  }

  // what a definition is made of, side by side: pick an object and the other two follow it; a row opens for editing where it stands
  function wsColumn(key, title, count, add, hint, body) {
    return `<section class="wscol${S.md.arrive === key ? ' arrive' : ''}" id="col-${key}"><div class="wscolh"><b>${title}</b><span class="chip sm">${count}</span><span class="grow"></span>${add}</div>
      <div class="wscolq"><input type="text" data-in="mdcq" data-k="${key}" value="${esc(S.md.cq[key])}" placeholder="${hint}" aria-label="${hint}"></div><div class="wscolb">${body}</div></section>`;
  }

  const wsTags = (list) => list.filter(Boolean).map(([c, w]) => `<span class="chip sm ${c}">${esc(w)}</span>`).join('');
  function wsForm() {
    const f = S.mg.form, body = { object: objectForm, prop: propForm, link: linkForm, area: areaForm }[f.kind]();
    // a person who may not edit reads the form: every field in it is shut, as its save button is gone
    return `<div class="wsform${f.mode === 'new' ? ' new' : ''}">${canEdit() ? body : `<fieldset disabled style="border:0;padding:0;margin:0;min-width:0">${body}</fieldset>`}</div>`;
  }

  // an Object: the top-level classification its Entities belong to, with a definition of its own
  function areaForm() {
    const f = S.mg.form, v = f.v, a = f.mode === 'edit' ? mgArea(v.name) : null;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    const ents = a ? S.mg.st.objects.filter((o) => o.area === a.name) : [];
    return `<div class="card"><div class="ch">${a ? `Object ${esc(a.label || a.name)} <span class="muted mono" style="font-weight:600">${esc(a.name)}</span>` : '새 Object'}<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      ${a ? `<div class="chips" style="margin-bottom:12px">${a.module_label ? `<button class="chip sm b" data-act="libshow" data-mod="${esc(a.module)}">정의 · ${esc(shortMod(a.module_label))}</button>` : ''}<span class="chip sm">Entity ${ents.length}</span></div>` : ''}
      ${field('이름', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}" placeholder="예: 주문">`)}
      ${a ? '' : nameField(f, '예: Order')}
      ${field('정의', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}" placeholder="예: 고객이 상품이나 서비스의 구매를 요청하는 것">`)}
      ${field('출처', `<input type="text" data-in="mgf" data-f="cite" value="${esc(v.cite)}" placeholder="예: 주문결제 정책서 · 주문 개요">`)}
      <div class="rgrid two">${field('소유자', `<input type="text" data-in="mgf" data-f="owner" value="${esc(v.owner || '')}" placeholder="예: 주문팀">`)}${field('차수', `<input type="number" min="1" data-in="mgf" data-f="tier" value="${esc(v.tier || '')}" placeholder="예: 1">`)}</div>
      ${a ? field('상태', statusSelect(v.status)) : ''}
      ${a ? `<div class="sec">Entity</div><div class="chips" style="margin-bottom:12px">${ents.map((o) => `<button class="chip" data-act="mdpick" data-name="${esc(o.name)}">${esc(o.label)}</button>`).join('') || '<span class="muted" style="font-size:12px">없음</span>'}<button class="chip b" data-act="mdobjnewin" data-area="${esc(a.name)}">+ Entity</button></div>` : ''}
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>${a ? '저장' : 'Object 추가'}</button>
        <div class="grow" style="flex:1"></div>${a ? `<button class="btn danger" data-act="mgdel"${S.mg.busy || ents.length ? ' disabled' : ''} title="${ents.length ? 'Entity를 다른 Object로 옮긴 뒤 제외할 수 있습니다' : ''}">Object 제외</button>` : ''}</div></div></div>`;
  }

  function colObjects() {
    const m = S.mg.st, md = S.md, f = S.mg.form, by = modelProblems().by;
    const q = md.cq.objects.trim().toLowerCase();
    const groups = {};
    m.objects.filter((o) => !q || `${o.name} ${o.label} ${o.table}`.toLowerCase().includes(q)).forEach((o) => { const k = o.module_label || o.module || '정의'; (groups[k] = groups[k] || []).push(o); });
    const row = (o) => {
      const on = md.sel === o.name, open = on && f && f.kind === 'object' && f.mode === 'edit', bad = (by[o.name] || []).length;
      const tags = wsTags([bad ? ['bad', `문제 ${bad}`] : null, o.new ? ['ok', '새 Entity'] : o.pending ? ['warn', '변경'] : null, m.unlinked.includes(o.name) ? ['warn', 'Relation 없음'] : null, o.concept ? ['', '개념'] : null, o.series ? ['', '시계열'] : null]);
      const facts = [o.table, o.parent ? `상위 ${mgLabel(o.parent)}` : '', `속성 ${o.properties}`, `관계 ${o.links}`, o.concept ? '' : `${count(o.rows || 0)}행`].filter(Boolean).join(' · ');
      return `<div class="wsi${on ? ' on' : ''}"><button class="wsib" data-act="mdpick" data-name="${esc(o.name)}"><span class="wsit"><b>${esc(o.label)}</b><span class="mono muted cn">${esc(o.name)}</span>${tags}</span><span class="wsis">${esc(facts)}</span></button>${on ? `<button class="btn sm" data-act="mdobjedit">${open ? '접기' : '편집'}</button>` : ''}</div>${open ? wsForm() : ''}`;
    };
    const list = Object.entries(groups).map(([k, rows]) => `<div class="mdgh">${esc(k)}<span class="muted">${rows.length}</span></div>${rows.map(row).join('')}`).join('') || '<div class="empty">찾은 Entity가 없습니다.</div>';
    return wsColumn('objects', 'Entity', m.objects.length, '<button class="btn sm" data-act="mdobjnew">새 Entity</button>', 'Entity · 테이블 검색',
      `${f && f.kind === 'object' && f.mode === 'new' ? wsForm() : ''}${list}${q ? '' : `<div class="wscolx">${identityCard()}${identityForm()}</div>`}`);
  }

  function colProps(o) {
    const md = S.md, f = S.mg.form, broken = modelProblems().elements;
    const q = md.cq.props.trim().toLowerCase();
    const all = mgProps(o.name), list = all.filter((p) => !q || `${p.name} ${p.label} ${p.column}`.toLowerCase().includes(q));
    const row = (p) => {
      const id = `${o.name}.${p.name}`, open = f && f.kind === 'prop' && f.mode === 'edit' && S.mg.sel === id;
      const tags = wsTags([broken.has(`property:${id}`) ? ['bad', '문제'] : null, p.key ? ['b', '키'] : null, p.new ? ['ok', '새'] : p.pending ? ['warn', '변경'] : null, p.required && !p.key ? ['', '필수'] : null, p.mask ? ['warn', MASK_WORD[p.mask]] : null,
        p.inherited ? ['', `상속 · ${mgLabel(p.inherited)}`] : p.module && p.module !== o.module ? ['', shortMod(p.module_label || p.module)] : null]);
      const facts = [TYPE_WORD[p.type] || p.type, p.expr ? '계산 Property' : p.column, p.values.length ? `허용값 ${p.values.length}개` : ''].filter(Boolean).join(' · ');
      return `<div class="wsi${open ? ' on' : ''}"><button class="wsib" data-act="mdprop" data-name="${esc(id)}" aria-expanded="${!!open}"><span class="wsit"><b>${esc(p.label || p.name)}</b><span class="mono muted cn">${esc(p.name)}</span>${tags}</span><span class="wsis">${esc(facts)}</span></button></div>${open ? wsForm() : ''}`;
    };
    return wsColumn('props', `${esc(o.label)}의 Property`, all.length, '<button class="btn sm" data-act="mdaddprop">새 Property</button>', 'Property · 컬럼 검색',
      `${f && f.kind === 'prop' && f.mode === 'new' ? wsForm() : ''}${list.map(row).join('') || '<div class="empty">검색된 Property가 없습니다.</div>'}`);
  }

  function colLinks(o) {
    const m = S.mg.st, md = S.md, f = S.mg.form;
    const q = md.cq.links.trim().toLowerCase();
    const all = m.links.filter((l) => l.source === o.name || l.target === o.name);
    const list = all.filter((l) => !q || `${l.name} ${l.label} ${mgLabel(l.source)} ${mgLabel(l.target)}`.toLowerCase().includes(q));
    const row = (l) => {
      const open = f && f.kind === 'link' && f.mode === 'edit' && S.mg.sel === l.name;
      const how = l.on ? `${l.on[0]} = ${l.on[1]}` : l.via ? `${l.via.table} (${l.via.source} · ${l.via.target})` : '개념 관계';
      const tags = wsTags([l.new ? ['ok', '새'] : l.pending ? ['warn', '변경'] : null, l.required ? ['', '필수'] : null, l.module && l.module !== o.module ? ['', shortMod(l.module_label || l.module)] : null]);
      return `<div class="wsi${open ? ' on' : ''}"><button class="wsib" data-act="mdlink" data-name="${esc(l.name)}" aria-expanded="${!!open}"><span class="wsit"><b>${esc(l.label || l.name)}</b><span class="mono muted cn">${esc(l.name)}</span>${tags}</span><span class="wsis">${esc(mgLabel(l.source))} → ${esc(mgLabel(l.target))} · ${esc(CARD[l.cardinality] || l.cardinality)}</span><span class="wsis mono">${esc(how)}</span></button></div>${open ? wsForm() : ''}`;
    };
    const sug = fkSuggestions().map((x, i) => [x, i]).filter(([x]) => x.source === o.name || x.target === o.name);
    const extra = sug.length && !q ? `<div class="wscolx"><div class="card"><div class="ch">참조 컬럼으로 찾은 관계 <span class="chip sm">${sug.length}</span></div><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>출발 → 도착</th><th>연결 기준</th><th></th></tr>${sug.map(([x, i]) => `<tr><td>${esc(mgLabel(x.source))} → ${esc(mgLabel(x.target))}</td><td class="mono" style="font-size:11.5px">${esc(x.column)}</td><td><button class="btn sm" data-act="mgsug" data-i="${i}"${S.mg.busy ? ' disabled' : ''}>추가</button></td></tr>`).join('')}</table></div></div></div>` : '';
    return wsColumn('links', `${esc(o.label)}의 관계`, all.length, '<button class="btn sm" data-act="mdlinknew">새 관계</button>', '관계 검색',
      `${f && f.kind === 'link' && f.mode === 'new' ? wsForm() : ''}${list.map(row).join('') || '<div class="empty">찾은 관계가 없습니다.</div>'}${extra}`);
  }

  function modelCols() {
    const o = mgObj(S.md.sel);
    return `<div class="wscols">${colObjects()}${o ? `${colProps(o)}${colLinks(o)}` : ''}</div>`;
  }

  function paintCols(picked) {  // the rows again, each column where it was; the two that follow an object start over for another one
    const c = $('#wscenter');
    if (!c) return;
    const kept = [...c.querySelectorAll('.wscolb')].map((x) => x.scrollTop);
    c.innerHTML = wsMain();
    c.querySelectorAll('.wscolb').forEach((x, i) => { x.scrollTop = picked && i ? 0 : (kept[i] || 0); });
    const open = c.querySelector('.wsform');
    if (open) {  // the row it opened from stays in sight above it
      const box = open.closest('.wscolb'), frame = box.getBoundingClientRect(), top = (open.previousElementSibling || open).getBoundingClientRect().top;
      if (top < frame.top || open.getBoundingClientRect().bottom > frame.bottom) box.scrollTop += top - frame.top - 4;
    }
  }

  const wsMain = () => (S.md.view === 'table' ? modelCols() : `<div id="ercard">${erCard()}</div><div id="erpop">${draftBox()}</div>`);

  // where the cards stand: the studio keeps one layout per pipeline for everyone (workspace/layout); this browser
  // keeps a copy so the canvas opens where it was before the state arrives
  function erPosKey() { return `ontlas-er-pos:${S.st.pipeline || ''}`; }
  function erPosLoad() {
    const md = S.md, key = erPosKey();
    const shared = S.mg.st && S.mg.st.layout && Object.keys(S.mg.st.layout).length ? S.mg.st.layout : null;
    if (md.posFor === key && !(shared && md.posFrom !== 'studio')) return;
    md.posFor = key;
    if (shared) { md.pos = { ...shared }; md.posFrom = 'studio'; return; }
    md.posFrom = 'browser';
    try { md.pos = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) { md.pos = {}; }
  }
  let erPosTimer = 0;
  function erPosSave() {
    try { localStorage.setItem(erPosKey(), JSON.stringify(S.md.pos)); } catch (e) { /* kept for this visit */ }
    if (!canEdit()) return;
    clearTimeout(erPosTimer);
    erPosTimer = setTimeout(() => {
      api('workspace/layout', { pipeline: S.st.pipeline || '', positions: S.md.pos }).then(() => { if (S.mg.st) S.mg.st.layout = { ...S.md.pos }; S.md.posFrom = 'studio'; }).catch(() => { /* this browser keeps it */ });
    }, 600);
  }

  async function linkDraft(source, target, ev) {
    const wrap = $('#wscenter').getBoundingClientRect();
    S.md.draft = { source, target, busy: true, x: ev.clientX - wrap.left, y: ev.clientY - wrap.top };
    paintDraft();
    try {
      const r = await api(`manage/link/suggest?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
      const o = r.options[0];
      Object.assign(S.md.draft, { busy: false, res: r, name: r.name, label: r.label, sp: o ? o.sp : '', tp: o ? o.tp : '', cardinality: o ? o.cardinality : 'many_to_one' });
    } catch (e) { S.md.draft = null; fail(e); }
    paintDraft();
  }

  function draftBox() {
    const d = S.md.draft;
    if (!d) return '';
    const left = Math.max(8, Math.min(d.x, ($('#wscenter') || { clientWidth: 900 }).clientWidth - 340)), top = Math.max(50, Math.min(d.y, ($('#wscenter') || { clientHeight: 600 }).clientHeight - 300));
    const pos = `style="left:${left}px;top:${top}px"`;
    const head = `<div class="erpoph"><b>${esc(mgLabel(d.source))} → ${esc(mgLabel(d.target))}</b><button class="iconbtn" data-act="draftclose" aria-label="닫기">×</button></div>`;
    if (d.busy) return `<div class="erpopb" ${pos}>${head}<div class="empty" style="padding:12px"><span class="spin"></span>연결 기준을 찾는 중입니다.</div></div>`;
    const r = d.res, cur = r.options.find((o) => o.sp === d.sp && o.tp === d.tp);
    const sel = (f, list) => `<select data-in="mddraft" data-f="${f}"><option value="">선택</option>${list.map((p) => opt(p.name, `${p.label} (${p.name})`, d[f])).join('')}</select>`;
    const meets = cur && cur.ratio !== null ? `${Math.round(cur.ratio * 100)}% 연결됩니다 (${show(cur.matched)} / ${show(cur.total)}행)` : d.sp && d.tp ? '실제 행 연결 비율은 추가 후 DB 대조에서 확인합니다' : '';
    return `<div class="erpopb" ${pos}>${head}
      ${r.options.length ? `<div class="field"><label>연결 기준 · 같은 이름에서 제안</label><select data-in="mddraftopt">${r.options.map((o, i) => `<option value="${i}"${o === cur ? ' selected' : ''}>${esc(o.sp)} = ${esc(o.tp)}${o.ratio === null ? '' : ` · ${Math.round(o.ratio * 100)}%`}</option>`).join('')}<option value="-1"${cur ? '' : ' selected'}>직접 고르기</option></select></div>` : '<div class="muted" style="font-size:12px;margin-bottom:8px">같은 이름의 컬럼을 찾지 못했습니다. 연결할 속성을 골라 주세요.</div>'}
      ${cur ? '' : `<div class="rgrid two"><div class="field"><label>출발 속성</label>${sel('sp', r.props.source)}</div><div class="field"><label>도착 속성</label>${sel('tp', r.props.target)}</div></div>`}
      <div class="rgrid two"><div class="field"><label>Cardinality</label><select data-in="mddraft" data-f="cardinality">${Object.entries(CARD).map(([k, x]) => opt(k, x, d.cardinality)).join('')}</select></div><div class="field"><label>영문 이름</label><input type="text" data-in="mddraft" data-f="name" value="${esc(d.name)}"></div></div>
      <div class="field"><label>라벨</label><input type="text" data-in="mddraft" data-f="label" value="${esc(d.label)}"></div>
      <div class="erpopf"><span class="muted" id="erpopm">${esc(meets)}</span><span class="grow"></span><button class="btn sm primary" data-act="draftadd"${S.mg.busy ? ' disabled' : ''}>추가</button></div></div>`;
  }

  function paintDraft() { const b = $('#erpop'); if (b) b.innerHTML = draftBox(); }

  function columnToProp(table, column, type, objName) {
    const t = mgTable(table), md = S.md, obj = objName || t.objects[0];
    md.hot = null;
    if (!obj) {
      S.mg.sel = '';
      S.mg.form = { kind: 'object', mode: 'new', v: { table, name: typeName(table), label: '', key: t.key[0] || (t.columns[0] || {}).name || '', parent: '', description: '', cols: true } };
      render();
      return;
    }
    const p = mgProps(obj).find((x) => (x.column || '').toLowerCase() === column.toLowerCase());
    Object.assign(md, { sel: obj, tab: 'form', rightOff: false });
    if (p) mgOpen('prop', `${obj}.${p.name}`, true);
    else {
      S.mg.sel = '';
      S.mg.form = { kind: 'prop', mode: 'new', v: { object: obj, name: propName(column), label: '', description: '', type: sqlType(type), column, values: '', unit: '', required: false, mask: '', expr: '' } };
    }
    render();
    erReveal(obj);
  }

  function hotField() {
    const h = S.md.hot;
    if (!h || !h.field) return;
    const el = document.querySelector(`#mdside [data-f="${h.field}"]`);
    if (!el) return;
    const box = el.closest('.field, .tick');
    if (box) box.classList.add('fieldhot');
    if (h.fresh) { h.fresh = false; el.scrollIntoView({ block: 'center' }); }
    if (document.activeElement === document.body) el.focus({ preventScroll: true });
  }

  function paintSide() { const b = $('#mdside'); if (b) { b.innerHTML = modelSide(); hotField(); } }

  function trialPanel(t) {
    const before = (g) => (t.before || {})[`${g.stage}.${g.condition}`];
    return `<div class="wstrial"><div class="mdgh" style="padding:0 0 3px">사본에서 시험한 결과</div>${regressionBlock(t.regression)}${t.issues && t.issues.length ? `<div class="hint warn">${esc(t.issues.join(' · '))}</div>` : ''}${t.gates.map((g) => `<div class="wstrialr"><span>${esc(g.label)}</span><span class="muted">${before(g) === undefined || before(g) === null ? '-' : gateValue(g, before(g))} → ${g.value === null ? '-' : gateValue(g, g.value)}</span><span class="ic ${g.passed ? 'y' : 'x'}" style="width:16px;height:16px;font-size:10px">${g.passed ? '✓' : '!'}</span></div>`).join('')}</div>`;
  }

  function viewModel() {
    const wait = mgWait('작업 공간', 'Entity 정의를 다이어그램과 폼으로 편집합니다.');
    if (wait) return wait;
    erPosLoad();
    const md = S.md, f = S.mg.form;
    if (f && f.mode === 'edit') {  // a form opened from a list or a link belongs to its object
      const owner = f.kind === 'object' ? f.v.name : f.kind === 'prop' ? f.v.object : f.kind === 'link' ? f.v.source : '';
      if (owner && mgObj(owner) && owner !== md.sel && !(f.kind === 'link' && f.v.target === md.sel)) md.sel = owner;
    }
    if (!md.sel || !mgObj(md.sel)) md.sel = (S.st.decisions[0] && mgObj(S.st.decisions[0].target) ? S.st.decisions[0].target : (S.mg.st.objects[0] || {}).name) || '';
    if (md.view === 'table') return `<div class="ws">${wsBar()}<div class="wscenter" id="wscenter">${wsMain()}</div></div>`;
    if (md.sel && !S.mg.form) mgOpen('object', md.sel, true);
    return `<div class="ws">${wsBar()}<div class="wsbody${md.leftOff ? ' noleft' : ''}${md.rightOff ? ' noright' : ''}"><div class="wsleft" id="wsleft">${wsLeft()}</div><div class="wscenter" id="wscenter">${wsMain()}</div><div class="insp" id="mdside">${modelSide()}</div></div></div>`;
  }

  function modelPick(name) {
    const md = S.md;
    if (md.view === 'table') {
      if (md.sel !== name) Object.assign(md.cq, { props: '', links: '' });
      md.sel = name; md.hot = null; S.mg.form = null; S.mg.sel = '';
      paintCols(true);
      return;
    }
    md.sel = name; md.tab = md.tab || 'form'; md.hot = null;
    S.mg.keep = true;
    mgOpen('object', name, true);
    S.gsel = name;
    if (md.focus) focusOn('model', name);
    wsRefresh(name);
  }

  function modelLink(name) {
    if (S.md.view === 'table' && S.mg.form && S.mg.form.kind === 'link' && S.mg.sel === name) { S.mg.form = null; S.mg.sel = ''; paintCols(); return; }
    S.md.hot = null; S.md.tab = 'form'; S.md.list = 'links';
    mgOpen('link', name, true);
    wsRefresh();
  }

  function wsRefresh(reveal) {  // what shows the selection, without losing the canvas's place
    const left = $('#wsleft'), side = $('#mdside'), md = S.md;
    if (md.view === 'table') { paintCols(); return; }
    if (left) left.innerHTML = wsLeft();
    if (side) paintSide();
    const box = $('#ercanvas');
    if (box && !md.focus) box.innerHTML = erSvg();
    if (reveal && !md.focus) erReveal(reveal);
  }

  function erReveal(name) {  // the picked card comes into view, wherever the diagram was scrolled to
    const box = $('#ercanvas'), L = erLayout(), b = L && L.boxes[name];
    if (!box || !b) return;
    const z = S.md.zoom || 1;
    box.scrollTo({ left: Math.max(0, b.x * z - box.clientWidth / 2 + (b.w * z) / 2), top: Math.max(0, b.y * z - 40), behavior: 'smooth' });
  }

  // ---- Object: the Objects with what is filed under each, how far it has come, and who owns it -------------------
  const LV = ['L0', 'L1', 'L2', 'L3'];
  const areaEntities = (a) => S.mg.st.objects.filter((o) => o.area === a.name);
  function levelWord(ls) {
    if (!ls.length) return 'Entity 없음';
    const lo = Math.min(...ls), hi = Math.max(...ls);
    return lo === hi ? LV[lo] : `${LV[lo]}~${LV[hi]}`;
  }

  // ---- 규칙 카드: rules in three layers, AXIOM first, then a customer's, then the common ones --------------------------
  const LAYER_WORD = { axiom: 'AXIOM', custom: 'Custom', standard: 'Standard' };
  const layerChip = (l) => (l && l !== 'standard' ? `<span class="chip sm ly-${esc(l)}">${esc(LAYER_WORD[l] || l)}</span>` : '');

  // the way a decision went through the layers: AXIOM passed › Custom vip-window fired › Standard held
  function pathLine(p) {
    if (!p || !p.layers) return '';
    const step = (x) => `<span class="pstep ${esc(x.state)} ly-${esc(x.layer)}"><b>${esc(x.label)}</b>${esc(x.said)}${x.fired.length ? ` <span class="mono">${esc(x.fired.join(', '))}</span>` : ''}</span>`;
    const src = p.source && p.source.rule ? `<span class="psrc">근거 ${esc(p.source.module_label || p.source.module || '')} ${esc(p.source.version || '')}${p.source.cite ? ` · ${esc(p.source.cite)}` : ''}</span>` : '';
    return `<div class="ppath" title="${esc(p.text || '')}"><span class="plabel">판정 경로</span>${p.layers.map(step).join('<i>›</i>')}${src}</div>`;
  }

  async function loadSemantic() {
    S.sem.busy = true;
    try { S.sem.st = await api('semantic'); } catch (e) { S.sem.st = { error: e.message }; }
    S.sem.busy = false;
    if (S.tab === 'semrules') render();
  }

  // ---- 용어 사전: what people call each definition, the words that mean the same, the pairs that must not be swapped ----
  const TERM_STATUS = { active: ['ok', '사용 중'], draft: ['warn', '초안'], review: ['warn', '확인 필요'], deprecated: ['bad', '폐기 예정'] };
  const CONFLICT_WORD = { label: '표기 중복', synonym_confusable: '동의어 · 혼동 금지 중복', missing_concept: '정의 없음' };
  const csv = (s) => String(s || '').split(/[,\n]/).map((x) => x.trim()).filter(Boolean);

  async function loadLexicon() {
    S.lx.busy = true;
    try { S.lx.st = await api('lexicon'); } catch (e) { S.lx.st = { error: e.message }; }
    S.lx.busy = false;
    if (S.tab === 'lexicon') render();
  }

  // ---- 버전 이력: each approved change that is swapped in makes a version; who asked, who decided, what it did to the answers
  async function loadVersions() {
    S.ver = { busy: true };
    try { S.ver = await api('versions'); } catch (e) { S.ver = { error: e.message }; }
    if (S.tab === 'versions') render();
  }

  // what a change does to the answers: questions that newly fail or pass, the measures before and after
  function regressionBlock(r) {
    if (!r || (!r.measured && !r.note)) return '';
    const q = (x) => `<div class="rgq"><b>${esc(x.id)}</b> ${esc(x.text)}<div class="muted mono">기대 ${esc(JSON.stringify(x.expected))} → 결과 ${esc(JSON.stringify(x.got))}${x.error ? ` · ${esc(x.error)}` : ''}</div></div>`;
    const d = (k, w) => { const m = r[k]; return m && (m.before !== null || m.after !== null) ? `<span>${w} ${pct(m.before)} → <b class="${m.change < 0 ? 'warnv' : ''}">${pct(m.after)}</b></span>` : ''; };
    const g = (x) => `<div class="rgq"><b>${esc(x.stage_label || x.stage)}</b> ${esc(x.label)} · 기준 ${pct(x.limit)} · ${pct(x.before)} → ${pct(x.after)}</div>`;
    const part = (word, xs, f) => (xs && xs.length ? `<div class="label" style="margin-top:8px">${word} ${xs.length}</div>${xs.map(f).join('')}` : '');
    return `<div class="rgbox${r.worse ? ' worse' : r.better ? ' better' : ''}"><div class="rghead"><b>회귀 평가</b><span>${esc(r.summary || '변화 없음')}</span></div>
      <div class="rgnums">${d('accuracy', '정답률')}${d('grounded', '근거 제시')}${d('agreement', '과거 판정 일치')}</div>
      ${part('신규 오답', r.newly_failing, q)}${part('신규 정답', r.newly_passing, q)}${part('미충족으로 바뀐 통과 조건', r.gates_failing, g)}${part('충족으로 바뀐 통과 조건', r.gates_passing, g)}
      ${r.note ? `<div class="muted" style="font-size:12px;margin-top:6px">${esc(r.note)}</div>` : ''}</div>`;
  }

  // ---- library -------------------------------------------------------------------------------------------------

  const counts = (c) => [['areas', 'Object'], ['objects', 'Entity'], ['links', 'Relation'], ['rule_cards', '규칙 카드'], ['parameters', '기준값'], ['decisions', '결정표'], ['queries', '질의'], ['questions', '검증 질문'], ['gates', '통과 조건'], ['draft_rules', '구축 규칙'], ['terms', '용어'], ['messages', '메시지'], ['extends', '확장'], ['removes', '제거']]
    .filter(([k]) => c[k]).map(([k, l]) => `${l} ${c[k]}`).join(' · ') || '-';

  const canMakeLibrary = () => !(S.me && S.me.team) || !!(S.me.user && (S.me.user.roles || []).includes('admin'));
  const LIB_START = [['files', '파일에서 가져오기'], ['base', '열려 있는 온톨로지 기반'], ['empty', '빈 온톨로지']];
  const LIB_MADE = [['areas', 'Object'], ['objects', 'Entity'], ['properties', 'Property'], ['links', 'Relation'], ['cards', '규칙 카드'], ['parameters', '기준값'], ['terms', '용어'], ['decisions', '결정표'], ['modules', '모듈']];

  // what the last library made here holds, and what its import adjusted or could not carry
  function libraryMade() {
    const r = S.lib.res;
    if (!r) return '';
    const made = LIB_MADE.filter(([k]) => r.made[k]).map(([k, w]) => `<span class="chip sm">${w} ${count(r.made[k])}</span>`).join('') || '<span class="muted">정의 없음</span>';
    const part = (title, x) => (x && x.count ? `<details class="libnote"><summary>${title} ${count(x.count)}건 <span class="muted">${x.kinds.map((k) => `${esc(k.label)} ${count(k.count)}`).join(' · ')}</span></summary><div class="liblines mono">${x.lines.map((l) => `<div>${esc(l)}</div>`).join('')}${x.count > x.lines.length ? `<div class="muted">이하 ${count(x.count - x.lines.length)}건 생략</div>` : ''}</div></details>` : '');
    const rep = r.report ? `<div class="muted" style="font-size:12.5px;margin-top:8px">가져온 항목 ${count(r.report.preserved)}건</div>${part('조정', r.report.adjusted)}${part('옮기지 못한 항목', r.report.unsupported)}` : '';
    return `<div class="libmade"><div class="libmadeh"><b>${esc(r.label)}</b><span class="chip sm ok">생성 완료</span><button class="btn sm ghost" data-act="libresx" style="margin-left:auto">닫기</button></div><div class="chips">${made}</div>${rep}</div>`;
  }

  function libraryForm() {
    const f = S.lib, st = S.st;
    if (!f.open) return '';
    const seg = `<div class="seg" role="group" aria-label="시작 방법">${LIB_START.map(([k, w]) => `<button class="${f.start === k ? 'on' : ''}" data-act="libstart" data-k="${k}" aria-pressed="${f.start === k}">${w}</button>`).join('')}</div>`;
    let body = '';
    if (f.start === 'files') {
      const held = (f.files && f.files.files) || [];
      const rows = held.map((x) => `<tr><td><b>${esc(x.name)}</b></td><td>${x.kind === 'definitions' ? '정의 초안' : 'OWL'}</td><td class="muted" style="font-size:12.5px">${Object.entries(x.sections || {}).map(([k, n]) => `${esc(k)} ${count(n)}`).join(' · ') || '-'}</td><td style="text-align:right">${fileSize(x.size)}</td><td style="text-align:right"><button class="btn sm ghost" data-act="libfiledrop" data-name="${esc(x.name)}">빼기</button></td></tr>`).join('');
      body = `${held.length ? `<div class="scroll" style="margin-bottom:8px"><table class="tight"><tr><th>파일</th><th>형식</th><th>구역별 행 수</th><th style="text-align:right">크기</th><th></th></tr>${rows}</table></div>` : ''}
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn sm" data-act="libpick"${f.up ? ' disabled' : ''}>${f.up ? '<span class="spin"></span>읽는 중' : '파일 추가'}</button><input type="file" id="libfileinput" multiple hidden accept=".yaml,.yml,.json,.ttl,.owl,.rdf">
          <span class="muted" style="font-size:12px">정의 초안 YAML · JSON(구역: objects · entities · relations · rules · parameters · terms), OWL .ttl · .owl · .rdf. 정의 초안은 여러 파일을 하나로 읽습니다. 최대 ${count((f.files && f.files.files_max) || 8)}개</span></div>`;
    } else if (f.start === 'base') {
      const on = f.mods || new Set(st.library.filter((r) => r.on).map((r) => r.name));
      body = st.library.length ? `<div class="libmods">${st.library.map((r) => `<label class="libmod"><input type="checkbox" data-in="libmod" data-mod="${esc(r.name)}"${on.has(r.name) ? ' checked' : ''}><span><b>${esc(r.label || r.name)}</b> <span class="muted mono">${esc(r.version)}</span></span><span class="kind"><i style="background:${esc(r.color)}"></i>${esc(r.kind_label)}</span></label>`).join('')}</div>
        <div class="muted" style="font-size:12px;margin-top:6px">기반 · ${esc(st.title || '')}</div>`
        : '<div class="muted">모듈 없음</div>';
    } else {
      body = '<div class="muted" style="font-size:12.5px">정의 없이 시작합니다. Object · Entity · 규칙은 생성 후 각 화면에서 추가합니다</div>';
    }
    const left = f.files ? f.files.made_max - f.files.made : null;
    return `<div class="libnew" id="libnew">${seg}
      <div class="libnewrow"><div class="field"><label for="libnl">이름</label><input type="text" id="libnl" data-in="libnl" value="${esc(f.label)}" maxlength="60" placeholder="이커머스 표준"></div>
        <div class="field"><label for="libnk">키 <span class="muted" style="font-weight:500">모듈 이름 · 네임스페이스. 미입력 시 자동 지정</span></label><input type="text" id="libnk" data-in="libnk" value="${esc(f.key)}" maxlength="40" placeholder="commerce-standard"></div></div>
      ${body}
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px"><button class="btn primary" data-act="libmake"${f.busy ? ' disabled' : ''}>${f.busy ? '<span class="spin"></span>만드는 중' : '만들기'}</button><button class="btn ghost" data-act="libnewx">닫기</button>
        <span class="muted" style="font-size:12px">생성한 라이브러리는 현재 세션에 유지됩니다${left === null ? '' : ` · 생성 가능 ${count(Math.max(left, 0))}개`}. 계속 사용하려면 [내려받기] 후 서버에 등록합니다</span></div></div>`;
  }

  function librariesCard() {
    const libs = S.st.libraries || [];
    const row = (x) => `<tr class="${x.id === S.st.library_id ? 'sel' : ''}"><td><b>${esc(x.label)}</b>${x.made ? ' <span class="chip sm">세션 생성</span>' : ''}</td><td style="text-align:right">${count(x.modules)}</td><td>${esc(x.source ? (BACKEND_KIND[x.source] || x.source) : '미연결')}</td>
      <td style="text-align:right;white-space:nowrap">${x.id === S.st.library_id ? '<span class="chip sm ok">사용 중</span> <a class="btn sm ghost" href="/api/export/library" download title="스튜디오 파일과 적용 모듈 파일(zip)">내려받기</a>' : `<button class="btn sm" data-act="libuse" data-id="${esc(x.id)}">열기</button>`}${x.made && canMakeLibrary() ? ` <button class="btn sm ghost" data-act="libdrop" data-id="${esc(x.id)}">삭제</button>` : ''}</td></tr>`;
    return `<div class="card" style="margin-bottom:14px"><div class="ch">라이브러리 <span class="chip sm">${libs.length}</span><div class="right"><span class="muted hide-sm" style="font-size:12px">라이브러리마다 정의, 데이터, 적용 내역을 따로 유지합니다</span>${canMakeLibrary() && !S.lib.open ? '<button class="btn sm" data-act="libnew">새 라이브러리</button>' : ''}</div></div>
      <div class="cb scroll" style="padding:0"><table class="tight"><tr><th>온톨로지</th><th style="text-align:right">모듈</th><th>데이터 소스</th><th></th></tr>${libs.map(row).join('')}</table></div>
      ${S.lib.res || S.lib.open ? `<div class="cb" style="border-top:1px solid var(--line)">${libraryMade()}${libraryForm()}</div>` : ''}</div>`;
  }

  async function loadDocument(name, section) {
    S.pol.doc = name; S.pol.section = section; S.pol.res = null;
    if (!name) { render(); return; }
    try {
      const r = await api('policy/document', { name, section });
      if (!r.ok) throw new Error(r.error);
      S.pol.text = r.text; S.pol.sections = r.sections;
      if (r.cut) toast('문서가 길어 앞부분만 불러왔습니다. 항목을 선택하면 해당 항목만 불러옵니다.');
    } catch (e) { fail(e); }
    render();
  }

  function moduleTemplate() {
    const st = S.st;
    const dom = st.library.find((r) => r.on && r.kind === 'domain');
    const node = dom && st.graph.nodes.find((n) => n.module === dom.name && n.table);
    const head = '# objects, links, decisions, actions, roles, queries, questions 를 정의합니다.\n# 다른 모듈의 항목은 extend 로 확장하고 remove 로 제외합니다.\n';
    if (dom && node) {
      return `${head}module: my-module\nversion: 0.1.0\nkind: customer\nlabel: 새 모듈\ndescription: 모듈 설명\nrequires: [${dom.name}]\nqueries:\n  custom${node.id}List:\n    label: ${node.label} 목록\n    query:\n      match: {x: ${node.id}}\n      return: [x.${node.key}]\n      order: [${node.key}]\n`;
    }
    return `${head}module: my-module\nversion: 0.1.0\nkind: domain\nlabel: 새 모듈\ndescription: 모듈 설명\nobjects:\n  Item:\n    label: 항목\n    key: item_id\n    properties:\n      item_id: {type: string, label: 항목 번호, required: true}\n`;
  }

  function moduleCheck() {
    const c = S.ed && S.ed.check;
    if (!c) return '';
    if (c.error) return `<div class="banner no" style="margin:0"><span class="ic x" style="width:24px;height:24px">!</span><div class="why">${esc(c.error)}</div></div>`;
    if (c.ok) return `<div class="chips"><span class="chip ok">✓ 정의 검사 통과</span><span class="chip mono">${esc(c.name)} ${esc(c.version)}</span><span class="chip">${esc(counts(c.counts))}</span></div>`;
    return `<div class="banner no" style="margin:0"><span class="ic x" style="width:24px;height:24px">!</span><div><div class="big" style="font-size:14px">정의 검사 오류 ${c.issues.length}건</div><div class="loglist">${c.issues.slice(0, 10).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div></div>`;
  }

  function editorCard() {
    const ed = S.ed;
    if (!ed) return '';
    if (ed.readonly) {
      return `<div class="card editor" id="editor"><div class="ch">변경 검토 · ${esc(ed.label)}<div class="right"><button class="btn sm ghost" data-act="mclose">닫기</button></div></div>
        <div class="cb">${S.change ? changeReview(S.change) : ''}</div></div>`;
    }
    const busy = ed.busy ? ' disabled' : '';
    return `<div class="card editor" id="editor"><div class="ch">${ed.isNew ? '새 모듈' : `모듈 편집 · ${esc(ed.label)}`}${ed.applied ? '<span class="chip ok">적용 중</span>' : ''}
      <div class="right">${(ed.versions || []).length > 1 ? `<select class="inline" data-in="medver" aria-label="버전">${ed.versions.map((x) => opt(x, x, ed.version)).join('')}</select>` : ''}<button class="btn sm ghost" data-act="mclose">닫기</button></div></div>
      <div class="cb"><textarea class="code" data-in="mtext" spellcheck="false">${esc(ed.text)}</textarea>
      <div id="mresult">${moduleCheck()}</div>
      ${S.change ? changeReview(S.change) : ''}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><button class="btn" data-act="mcheck"${busy}>검사</button>
        <button class="btn primary" data-act="mpropose" data-apply="0"${busy}>${ed.busy ? '<span class="spin"></span>검토 중' : '변경 요청'}</button>
        ${ed.applied ? '' : `<button class="btn primary" data-act="mpropose" data-apply="1"${busy}>적용 변경 요청</button>`}
        ${ed.name && !ed.isNew ? `<a class="btn ghost" href="/api/export/module?name=${encodeURIComponent(ed.name)}" download>내려받기</a>` : ''}</div></div></div>`;
  }

  async function openModule(name, version = '') {
    const m = await api('module?name=' + encodeURIComponent(name) + (version ? '&version=' + encodeURIComponent(version) : ''));
    S.ed = { ...m, text: m.yaml, check: null, busy: false, isNew: false };
    S.change = null;
  }

  async function loadChanges() {
    S.changes = { busy: true };
    try { S.changes = await api('changes'); } catch (e) { S.changes = { error: e.message, changes: [] }; }
    if (S.tab === 'library' || S.tab === 'changes') render();
  }

  const pct = (v) => (v === null || v === undefined ? '-' : `${Math.round(v * 1000) / 10}%`);
  const gateValue = (g, v) => (g.condition.startsWith('min_') ? pct(v) : (v === null || v === undefined ? '-' : show(v)));

  function gateRows(gates) {
    if (!gates.length) return '<div class="muted" style="font-size:12.5px">지정된 통과 조건이 없습니다.</div>';
    return `<table class="tight"><tr><th>단계</th><th>조건</th><th>기준</th><th>결과</th><th></th></tr>${gates.map((g) => `<tr><td>${esc(g.stage_label || g.stage)}</td><td>${esc(g.label)}</td>
      <td class="num">${gateValue(g, g.limit)}</td><td class="num">${gateValue(g, g.value)}</td><td><span class="ic ${g.passed ? 'y' : 'x'}">${g.passed ? '✓' : '!'}</span></td></tr>`).join('')}</table>`;
  }

  function mismatchRows(list) {
    if (!list || !list.length) return '';
    return `<table class="tight" style="font-size:12px"><tr><th>처리 기록</th><th>실제</th><th>판정</th><th>규칙</th></tr>${list.slice(0, 10).map((m) => {
      const id = Object.values(m.case)[0];
      return `<tr><td class="mono">${esc(id)}</td><td>${showObj(m.expected)}</td><td>${showObj(m.got)}</td><td class="mono">${esc((m.matched || []).join(', '))}</td></tr>`;
    }).join('')}</table>`;
  }

  function changeReview(c) {
    const d = c.diff || {};
    const list = (xs, label, cls) => (xs && xs.length ? `<div class="label" style="margin:8px 0 4px">${label} ${xs.length}</div><div class="chips">${xs.slice(0, 20).map(element).join('')}${xs.length > 20 ? `<span class="chip sm">외 ${xs.length - 20}개</span>` : ''}</div>` : '');
    const m = c.measured || {};
    const facts = [];
    if (m.bind && m.bind.errors !== undefined) facts.push(`DB 대조 오류 ${m.bind.errors} · 경고 ${m.bind.warnings}`);
    if (m.query && m.query.queries !== undefined) facts.push(`Backend 결과 일치 ${m.query.agree} / ${m.query.queries}`);
    if (m.check && m.check.accuracy !== undefined) facts.push(`검증 질문 정답률 ${pct(m.check.accuracy)}${m.check.failed && m.check.failed.length ? ` (틀린 질문 ${esc(m.check.failed.join(', '))})` : ''}`);
    if (m.decide && m.decide.rate !== undefined) facts.push(m.decide.cases ? `판정 일치율 ${pct(m.decide.rate)} (${m.decide.agree} / ${m.decide.cases})` : '판정 일치율 측정 불가 · 판정표 없음');
    const issues = c.issues.length ? `<div class="banner no" style="margin:8px 0"><span class="ic x" style="width:24px;height:24px">!</span><div class="loglist">${c.issues.slice(0, 6).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div>` : '';
    const act = c.status === 'pending' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" data-act="capprove" data-id="${esc(c.id)}"${c.passed ? '' : ' disabled'}>승인</button><button class="btn" data-act="creject" data-id="${esc(c.id)}">반려</button></div>
      ${S.st.self_approve ? '' : '<div class="hint" style="margin-top:6px">요청한 사람과 다른 승인자가 승인합니다.</div>'}` : '';
    return `<div class="review"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b>변경 ${esc(c.id)} · ${esc(c.module_label)} ${esc(c.base_version || '')}${c.base_version ? ' → ' : ''}${esc(c.version)}</b>
        <span class="chip ${CHANGE_STATUS[c.status] || ''}">${esc(c.status_label)}</span><span class="chip ${c.passed ? 'ok' : 'bad'}">${c.passed ? '흐름 통과 조건 충족' : '흐름 통과 조건 미충족'}</span>
        <span class="muted" style="font-size:12px">요청 ${esc(c.requested_by)}${c.decided_by ? ` · 결정 ${esc(c.decided_by)}` : ''}</span></div>
      ${issues}${list(d.added, '추가', 'ok')}${list(d.changed, '변경', 'b')}${list(d.removed, '제거', 'bad')}
      ${facts.length ? `<div class="label" style="margin:10px 0 4px">사본 측정</div><div class="loglist">${facts.map((x) => `<div>${x}</div>`).join('')}</div>` : ''}
      <div class="label" style="margin:10px 0 4px">통과 조건</div>${gateRows(c.gates)}
      ${m.findings && m.findings.length ? `<div class="label" style="margin:10px 0 4px">DB 대조에서 나온 항목</div><table class="tight" style="font-size:12px"><tr><th>심각도</th><th>종류</th><th>항목</th><th>내용</th></tr>${m.findings.slice(0, 8).map((f) => `<tr><td><span class="chip sm ${f.severity === 'error' ? 'bad' : 'warn'}">${f.severity === 'error' ? '오류' : '주의'}</span></td><td>${esc(FINDING[f.kind] || f.kind)}</td><td>${element(f.element)}</td><td class="mono muted">${esc(f.detail)}</td></tr>`).join('')}</table>` : ''}
      ${m.check && m.check.wrong && m.check.wrong.length ? `<div class="label" style="margin:10px 0 4px">틀린 검증 질문</div><table class="tight" style="font-size:12px"><tr><th>질문</th><th>정답</th><th>사본의 답</th></tr>${m.check.wrong.slice(0, 8).map((q) => `<tr><td>${esc(q.text)}<div class="muted mono">${esc(q.id)}</div></td><td>${showObj(q.expected)}</td><td>${q.error ? `<span class="muted">${esc(q.error)}</span>` : showObj(q.got)}</td></tr>`).join('')}</table><div class="hint">의도한 변경이라면 검증 질문 관리에서 이 질문을 제외하고 새 정답으로 다시 추가한 뒤 함께 변경 요청합니다.</div>` : ''}
      ${m.check && (m.check.values || []).some((v) => v.errors) ? `<div class="label" style="margin:10px 0 4px">거래 값이 다른 건</div><table class="tight" style="font-size:12px"><tr><th>항목</th><th>대상</th><th>온톨로지 값</th><th>거래 시스템 값</th></tr>${m.check.values.flatMap((v) => v.mismatches.slice(0, 5).map((x) => `<tr><td>${esc(v.label)}</td><td class="mono">${esc(x.key)}</td><td>${show(x.answer)}</td><td>${show(x.truth)}</td></tr>`)).join('')}</table>` : ''}
      ${m.mismatches && m.mismatches.length ? `<div class="label" style="margin:10px 0 4px">판정이 실제 처리와 다른 건</div>${mismatchRows(m.mismatches)}` : ''}${act}</div>`;
  }

  function impactCard() {
    const imp = S.impact;
    if (!imp) return '';
    const list = (xs) => `<div class="chips" style="margin-top:8px">${xs.slice(0, 16).map(element).join('')}${xs.length > 16 ? `<span class="chip sm">외 ${xs.length - 16}개</span>` : ''}</div>`;
    const cancel = '<button class="btn" data-act="cancel-impact">취소</button>';
    if (imp.ok) {
      return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip ok">해제 가능</span></div>
        <div class="muted" style="margin-top:6px;font-size:12.5px">제거 ${imp.removed.length}개${imp.changed.length ? ` · 원래 정의로 복원 ${imp.changed.length}개` : ''}</div>
        ${list(imp.removed)}${imp.changed.length ? list(imp.changed) : ''}
        <div style="display:flex;gap:8px;margin-top:14px"><button class="btn primary" data-act="detach" data-mod="${esc(imp.module)}"
          data-cascade="${imp.cascade ? 1 : 0}">${imp.cascade ? '함께 해제' : '해제'}</button>${cancel}</div>`;
    }
    const deps = imp.dependents_labels || [];
    const cas = imp.cascadeImpact;
    return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip warn">의존 모듈 있음</span></div>
      <div class="muted" style="margin-top:6px;font-size:12.5px;line-height:1.55">${deps.length ? `의존 모듈 ${deps.length}개 · ${esc(deps.join(', '))}` : '참조가 끊어지는 항목'}</div>
      ${deps.length ? '' : `<div class="loglist" style="margin-top:6px">${imp.broken.map((b) => `<div class="mono">${esc(b)}</div>`).join('')}</div>`}
      ${cas && cas.ok ? `<div class="muted" style="margin-top:10px;font-size:12.5px">함께 해제 시 제거 ${cas.removed.length}개</div>${list(cas.removed)}` : ''}
      <div style="display:flex;gap:8px;margin-top:14px">${cas && cas.ok ? `<button class="btn primary" data-act="detach" data-mod="${esc(imp.module)}" data-cascade="1">함께 해제</button>` : ''}${cancel}</div>`;
  }

  async function toggleModule(name) {
    const row = S.st.library.find((r) => r.name === name);
    if (!row) return;
    try {
      if (row.on) {
        const imp = await api('impact', { name });
        if (!imp.ok && imp.dependents.length) {
          const cas = await api('impact', { name, cascade: true });
          imp.cascadeImpact = cas;
        }
        S.impact = imp;
        render();
      } else {
        const r = await api('attach', { name });
        if (!r.ok) throw new Error(r.error);
        S.impact = null;
        stale();
        Object.assign(S, { files: null, flset: null }); S.dr.rules = null;  // a method or quality module moves these
        await load();
        if (r.warning) toast(r.warning, true); else toast(`${r.added.map(modLabel).join(', ')} 모듈을 적용했습니다.`);
      }
    } catch (e) { fail(e); }
  }

  async function detach(name, cascade) {
    try {
      const r = await api('detach', { name, cascade });
      if (!r.ok) throw new Error(r.error);
      S.impact = null;
      stale();
      Object.assign(S, { files: null, flset: null }); S.dr.rules = null;  // a method or quality module moves these
      await load();
      if (r.warning) toast(r.warning, true); else toast(`${modLabel(name)} 모듈을 해제했습니다.`);
    } catch (e) { fail(e); }
  }

  // ---- ontology ------------------------------------------------------------------------------------------------

  function viewOnto() {
    const s = S.st.stats;
    const stats = [...(s.areas ? [[s.areas, 'Object']] : []), [s.objects, 'Entity'], [s.links, 'Relation'], [s.properties, 'Property'], [s.decisions, '결정표'], [s.actions, 'Action'], [s.queries, '등록 질의']]
      .map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join('');
    return `
<div class="head"><div><h1>전체 보기</h1><div class="sub">Entity · Relation · Property 정의와 Mapping을 조회합니다.</div></div>
  <div class="right"><a class="btn ghost" href="/api/export/owl" download>OWL 내보내기</a></div></div>
<div class="stats">${stats}</div>
<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(360px,1fr)">
  <div id="ontocard">${ontoCard()}</div>
  <div class="card"><div class="ch">정의<div class="right"><button class="btn sm" data-act="ontoedit">작업 공간에서 열기</button></div></div><div class="cb scroll" id="objdetail" style="max-height:640px">${S.obj ? objDetail(S.obj) : '<div class="empty">선택된 Entity가 없습니다.</div>'}</div></div>
</div>`;
  }

  async function selectObject(name, quiet) {
    S.sel = name;
    if (!quiet) { S.gsel = name; drawGraph(); }
    try {
      S.obj = await api('object?name=' + encodeURIComponent(name));
      const box = $('#objdetail');
      if (box) box.innerHTML = objDetail(S.obj);
    } catch (e) { fail(e); }
  }

  function objDetail(o) {
    const rows = o.properties.map((p) => `<tr><td><b>${esc(p.label)}</b><div class="muted mono cn">${esc(p.name)}</div>
        ${p.inherited ? '<span class="chip sm" style="margin-top:4px">상위 개념 상속</span>' : (p.module && p.module !== o.module ? `<span class="chip sm b" style="margin-top:4px">${esc(p.module_label)}</span>` : '')}</td>
      <td><span class="chip${p.key ? ' b' : ''}">${esc(p.type)}${p.unit ? ' · ' + esc(p.unit) : ''}</span>
        ${p.values.length ? `<div class="muted" style="font-size:11.5px;margin-top:3px">${esc(valueText(p, ' · '))}</div>` : ''}</td>
      <td class="mono">${p.expr ? `<span class="chip sm b">계산</span> <span style="font-size:11.5px">${esc(p.expr)}</span>` : (p.column ? esc(p.column) : '<span class="muted">-</span>')}
        ${p.mask ? `<div><span class="chip sm warn" style="margin-top:4px">가림 · ${p.mask === 'full' ? '전체' : '일부'}</span></div>` : ''}</td></tr>`).join('');
    const links = o.links.map((l) => `<button class="chip" data-act="select" data-obj="${esc(l.other)}">${l.out ? '' : '← '}${esc(l.label)} · ${esc(l.other_label)}${l.out ? ' →' : ''}</button>`).join('');
    const trans = o.states && o.states.transitions.length ? `<div class="chips" style="margin-top:6px">${o.states.transitions.map((x) => `<span class="chip sm">${esc(x.from)} → ${esc(x.to)}</span>`).join('')}</div>` : '';
    const states = o.states ? `<div class="sec">상태 전이 · ${esc(o.states.property)}</div><div class="chips">${o.states.states.map((x) => `<span class="chip${x === o.states.initial ? ' n' : ''}">${esc(x)}</span>`).join('')}</div>${trans}` : '';
    const series = o.series && o.series.time ? `<div class="sec">시계열</div><div class="muted" style="font-size:12.5px">시간 속성 <span class="mono">${esc(o.series.time)}</span>${o.series.of ? ` · 관계 <span class="mono">${esc(o.series.of)}</span>` : ''}. 계산 속성의 latest(), earliest() 로 최근 · 최초 값을 읽습니다.</div>` : '';
    const ident = o.identity ? identityPanel(o.name) : '';
    const parent = o.parent ? `<div class="sec">상위 개념</div><button class="chip n" data-act="select" data-obj="${esc(o.parent)}">${esc(o.parent_label)} · ${esc(o.parent)}</button>` : '';
    const children = o.children.length ? `<div class="sec">하위 유형</div><div class="chips">${o.children.map((c) => `<button class="chip" data-act="select" data-obj="${esc(c.name)}">${esc(c.label)}</button>`).join('')}</div>` : '';
    const aligned = o.aligned.length ? `<div class="sec">표준 개념 Mapping</div><div class="chips">${o.aligned.map((a) => `<span class="chip sm mono">${esc(a.split('//').pop())}</span>`).join('')}</div>` : '';
    const mod = o.module ? `<button class="chip" data-act="libshow" data-mod="${esc(o.module)}" title="라이브러리에서 이 모듈로">정의 모듈 ${esc(o.module_label)}</button>` : '';
    const touched = o.touched.map((x) => `<button class="chip" data-act="libshow" data-mod="${esc(x)}" title="라이브러리에서 이 모듈로">확장 모듈 ${esc(x)}</button>`).join('');
    return `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px"><b style="font-size:16px">${esc(o.label)}</b>
      <span class="muted mono">${esc(o.name)}</span><span style="flex:1"></span>
      ${o.abstract ? '<span class="chip n">상위 개념</span>' : `<span class="chip b">키 ${esc(o.key)}</span><span class="chip mono">${esc(o.table)}</span>`}</div>
      <div class="chips" style="margin-bottom:12px">${mod}${touched}</div>
      ${o.description ? `<div class="muted" style="font-size:12.5px;margin-bottom:10px">${esc(o.description)}</div>` : ''}
      <table class="tight"><tr><th>Property</th><th>타입</th><th>소스 컬럼</th></tr>${rows}</table>
      ${states}${series}${ident}${parent}${children}${aligned}
      ${links ? `<div class="sec">Relation</div><div class="chips">${links}</div>` : ''}
      ${(o.documents || []).length ? `<div class="sec">이 Entity를 언급한 문서</div>${o.documents.map((d) => `<div class="hit" style="padding:6px 0"><div class="hit-top"><b>${esc(d.document)}</b><span class="muted">${esc(d.section)}</span></div><div class="muted" style="font-size:12px">${esc(d.text)}</div></div>`).join('')}` : ''}`;
  }

  // ---- graph: graph.js draws it; positions stay in S.pos and S.dpos across renders ---------------------------------------

  const mountGraph = (el, data, opt) => window.SpaceGraph.mount(el, data, opt);
  const drawGraph = () => window.SpaceGraph.refresh();

  // ---- the space: documents, vectors, ports, the map, the way in from outside ------------------------------------------------

  const KIND_LABEL = { object: 'Entity', property: 'Property', value: '허용값', decision: '결정표', action: 'Action', term: '용어', keyword: '키워드' };

  async function loadSpace() {
    S.sp = { busy: true };
    try { S.sp = await api('space'); } catch (e) { S.sp = { error: e.message }; }
    if (['docs', 'vectors', 'search'].includes(S.tab)) render();
  }

  function pageHead(title, sub, right = '') {
    return `<div class="head"><div><h1>${esc(title)}</h1><div class="sub">${esc(sub)}</div></div><div class="right">${right}</div></div>`;
  }

  function sourceCard(h, i) {
    const doc = h.kind === 'document';
    const bar = Math.min(100, Math.max(4, Math.round(h.score * 100)));
    return `<div class="hit"><div class="hit-top"><span class="fno">${i + 1}</span><span class="chip sm${doc ? '' : ' b'}">${esc(h.kind_label)}</span><b>${esc(doc ? h.document : h.title)}</b>${doc ? `<span class="muted">${esc(h.section)}</span>` : ''}
        <span class="hit-score" title="관련도"><i style="width:${bar}%"></i></span></div>
      <div class="hit-text">${esc(h.text)}</div>${h.cite ? `<div class="muted" style="font-size:12px">출처 ${esc(h.cite)}</div>` : ''}
      ${(h.concepts || []).length ? `<div class="chips">${h.concepts.map((c) => `<span class="chip sm b">${esc(c)}</span>`).join('')}</div>` : ''}</div>`;
  }

  // ---- one answer: what it is and where it came from, what can be done next, then why in three layers --------------

  function policyStep(d) {
    const used = d.rules.map((x) => x.id), first = d.rules[0];
    if (!first) return '맞는 규칙이 없습니다.';
    const rule = (id) => `<b>${esc(id)}</b>`;
    const others = d.also.filter((x) => !x.fallback).map((x) => x.id);
    const test = (t) => ({ true: '예', false: '아니요' }[t] || cellWord(t));
    const cond = first.when.length ? ` 규칙 ${esc(first.id)}의 조건은 ${first.when.map((w) => `${esc(w.input)} ${esc(test(w.test))}`).join(', ')}입니다.` : ` 규칙 ${esc(first.id)}${josa(first.id, '은', '는')} 조건이 없는 기본 규칙입니다.`;
    if (d.hit_policy === 'first') return `결정표는 위에서부터 처음 맞는 규칙 하나를 씁니다. 처음 맞는 규칙은 ${rule(first.id)}입니다.${others.length ? ` ${others.map(esc).join(', ')} 규칙도 맞지만 순서가 뒤라 쓰지 않았습니다.` : ''}${cond}`;
    if (d.hit_policy === 'priority') return `결정표는 맞는 규칙 가운데 우선순위가 가장 높은 규칙을 씁니다. 쓴 규칙은 ${rule(first.id)}입니다.${cond}`;
    if (d.hit_policy === 'collect') return `결정표는 맞는 규칙을 모두 모읍니다. 맞은 규칙은 ${used.map(rule).join(', ')}입니다.`;
    return `결정표는 맞는 규칙이 하나뿐이어야 합니다. 맞은 규칙은 ${rule(first.id)}입니다.${cond}`;
  }

  function howSteps(d) {
    const val = (e) => (e.value === null || e.value === undefined ? '<b>값 없음</b>' : `<b>${typeof e.value === 'boolean' ? yesNo(e.value) : show(e.value)}</b>`);
    const steps = [[`${esc(d.target_label)} <b>${esc(d.key)}</b>${josa(d.key, '을', '를')} 찾았습니다.`, d.target]];
    d.evidence.forEach((e) => {
      const name = e.property || e.label;
      const where = e.path.length ? `${e.path.join(' → ')} · ${e.source}` : e.source;
      if (e.kind === 'param') steps.push([`입력한 ${esc(e.label)}${josa(e.label, '은', '는')} ${val(e)}입니다.`, '']);
      else if (e.kind === 'count') steps.push([`${esc(e.path.join(' → '))} 수는 <b>${show(e.value)}</b>개입니다.`, e.source]);
      else if (e.kind === 'days_since') {
        steps.push([e.value === null || e.value === undefined ? `${esc(name)} 값이 없어 경과일을 셀 수 없습니다.` : `${esc(name)}${e.since ? ` ${show(e.since)}` : ''}, 기준 시각까지 <b>${show(e.value)}일</b>입니다.`, where]);
      } else steps.push([`${e.path.length && e.key ? `${esc(e.type_label)} ${esc(e.key)}의 ` : ''}${esc(name)}${josa(name, '은', '는')} ${val(e)}입니다.`, where]);
    });
    steps.push([policyStep(d), '']);
    return `<ol class="asteps">${steps.map(([t, m], i) => `<li><span class="sno">${i + 1}</span><div>${t}${m ? ` <span class="mono muted cn">${esc(m)}</span>` : ''}</div></li>`).join('')}</ol>`;
  }

  function valuesTable(d) {
    const rows = d.evidence.map((e) => `<tr><td>${esc(e.label)}</td><td>${typeof e.value === 'boolean' ? yesNo(e.value) : show(e.value)}${e.kind === 'days_since' && e.since ? `<div class="muted" style="font-size:11.5px">${show(e.since)}부터</div>` : ''}</td>
      <td>${e.type_label ? `${esc(e.type_label)} ${esc(e.key)}` : '<span class="muted">입력값</span>'}</td><td class="mono muted" style="font-size:12px">${esc(e.source)}${e.path.length ? `<div>${esc(e.path.join(' → '))}</div>` : ''}</td></tr>`).join('');
    return `<table class="tight"><tr><th>입력값</th><th>값</th><th>읽은 레코드</th><th>데이터 소스</th></tr>${rows}</table>`;
  }

  function codePane(res, d, q) {
    if (!d) {
      const text = (q && q.text) || (res.record && res.record.query) || '';
      return text ? `<div class="label">${q ? `${esc(q.label)} · ${esc(q.backend || '')}` : '레코드를 읽은 질의'}</div><pre class="acode">${esc(text)}</pre>` : '<div class="empty">실행한 질의가 없습니다.</div>';
    }
    const r = d.rules[0];
    const when = r ? `<div class="label">적용한 규칙 · ${esc(r.id)}${r.cite ? ` · ${esc(r.cite)}` : ''}</div><table class="tight" style="margin-top:6px"><tr><th>입력값</th><th>조건</th></tr>${r.when.map((w) => `<tr><td>${esc(w.input)}</td><td class="mono">${esc(w.test)}</td></tr>`).join('') || '<tr><td colspan="2" class="muted">조건 없음 · 기본 규칙</td></tr>'}</table>` : '';
    const sql = d.reading ? `<div class="label" style="margin-top:14px">판정 값 조회 SQL</div><pre class="acode">${esc(d.reading)}</pre>
      <div class="muted" style="font-size:12px">경과일 기준 시각 · ${esc(d.at.replace('T', ' '))}</div>` : '';
    return when + sql;
  }

  function folderPick(key, value, sp, label) {
    const folders = (sp && sp.folders) || [];
    if (!folders.length) return '';
    return `<select class="inline" data-in="${key}" aria-label="${esc(label)}"><option value="">전체 문서</option>${folders.map((f) => `<option value="${esc(f)}"${value === f ? ' selected' : ''}>${esc(f)}</option>`).join('')}</select>`;
  }

  // `pick` asks the same question again as a person corrected it; when that fails, the answer before stays
  async function searchNow(pick) {
    const r = S.sr;
    const asked = pick && r.res ? r.res.question : r.text;
    if (!asked.trim()) return toast('질문이 없어 검색하지 못했습니다. 질문을 입력해 주세요.', true);
    rememberAsked(asked.trim());
    const seq = (r.seq || 0) + 1;
    r.seq = seq;
    r.busy = true;
    render();
    let res;
    try { res = await api('space/ask', { text: asked, folder: r.folder, ...(pick ? { pick } : {}) }); } catch (e) { res = { error: e.message, no_source: !!(e.body && e.body.no_source) }; }
    if (r.seq !== seq) return null;  // a later question was asked meanwhile: its answer is the one shown
    if (res && res.ok === false) res = { error: res.error, no_source: !!res.no_source };
    r.busy = false;
    if (pick && res.error) { render(); return toast(res.error, true); }
    Object.assign(r, { res, more: null, moreBusy: false, fb: '', di: 0, fix: null, tab: pick ? r.tab : '' });
    render();
    if (!pick && res && res.needs_model && res.can_model) {
      r.moreBusy = true;
      render();
      let more;
      try { more = await api('space/ask/more', { text: asked, folder: r.folder }); } catch (e) { more = { ok: false, error: e.message }; }
      if (r.seq !== seq) return null;
      r.more = more;
      r.moreBusy = false;
      if (S.tab === 'search') render();
    }
    return null;
  }

  const READER_WORD = { basic: '기본', 'ontology-build': 'xgen-ontology-build' };

  function readCard() {
    const sp = S.sp, j = S.djob, rd = (j && j.folder === S.dfolder ? j : null) || (S.drel && S.drel.reading) || (S.dfolder ? { read: 0, passages: 0, relations: 0, names: 0 } : sp.reading);
    const running = j && j.running;
    const share = rd.passages ? Math.round(rd.read / rd.passages * 100) : 0;
    const readers = (sp.readers || []).length > 1 ? `<select class="inline" data-in="dreader" aria-label="관계 추출 엔진"${running ? ' disabled' : ''}>${sp.readers.map((k) => `<option value="${esc(k)}"${(S.dreader || sp.reader) === k ? ' selected' : ''}>${esc(READER_WORD[k] || k)}</option>`).join('')}</select>` : '';
    const acts = !sp.can_read ? '<span class="muted" style="font-size:12.5px">언어 모델이 연결된 설치형에서 사용합니다</span>'
      : running ? `<button class="btn sm" data-act="dstop"${j.stop ? ' disabled' : ''}>${j.stop ? '중지하는 중' : '중지'}</button>`
        : `${readers}<button class="btn sm primary" data-act="dread"${rd.read >= rd.passages ? ' disabled' : ''}>${rd.read ? '이어서 추출' : '관계 추출'}</button>${rd.read ? '<button class="btn sm ghost" data-act="dforget">다시 추출</button>' : ''}`;
    const bar = running ? `<div class="cprog" style="margin-top:10px"><span class="spin"></span><b>${j.total ? `${j.done} / ${j.total}` : '준비 중'}</b><span class="muted">${esc(READER_WORD[j.reader] || j.reader)} · ${j.seconds}초 경과</span><div class="bar"><i style="width:${j.total ? Math.round(j.done / j.total * 100) : 0}%"></i></div></div>` : '';
    return `<div class="ch">관계 추출<div class="right">${acts}</div></div><div class="cb">
      <div class="chips"><span class="chip">읽은 청크 ${count(rd.read)} / ${count(rd.passages)} (${share}%)</span><span class="chip ${rd.relations ? 'ok' : ''}">관계 ${count(rd.relations)}</span><span class="chip">관계 이름 ${count(rd.names)}</span>${(rd.readers || []).map((k) => `<span class="chip sm">${esc(READER_WORD[k] || k)}</span>`).join('')}</div>
      ${bar}<div class="hint xp" style="margin-top:8px">청크마다 개념이 둘 이상 나오는 문장만 언어 모델에 보내고, 문장이 직접 말하는 관계만 근거 문장과 함께 추가합니다.</div></div>`;
  }

  function relationCard() {
    const r = S.drel;
    if (!r || !r.total) return '';
    const meaning = (x) => (x.label ? `<div class="muted mono" style="font-size:11px">${esc(x.predicate)}</div>` : (r.vocabulary || {})[x.predicate] ? `<div class="muted" style="font-size:11px">${esc(r.vocabulary[x.predicate])}</div>` : '');
    const rows = r.relations.slice(0, 60).map((x) => `<tr><td><b>${esc(x.source)}</b></td><td><span class="chip sm b">${esc(x.label || x.predicate)}</span>${meaning(x)}</td><td><b>${esc(x.target)}</b></td><td style="font-size:12px">${esc(x.evidence)}<div class="muted" style="font-size:11px">${esc(x.document)} · ${esc(x.section)}</div></td></tr>`).join('');
    return `<div class="card" style="margin-top:14px"><div class="ch">추출한 관계<div class="right muted" style="font-size:12px;font-weight:600">${count(r.total)}개${r.total > 60 ? ' · 앞 60개 표시' : ''}</div></div><div class="cb scroll" style="max-height:420px">
      <table class="tight"><tr><th>주어</th><th>관계</th><th>목적어</th><th>근거 문장</th></tr>${rows}</table></div></div>`;
  }

  function viewDocs() {
    const sp = S.sp;
    const pick = sp && !sp.busy && !sp.error ? folderPick('dfolder', S.dfolder, sp, '문서 범위') : '';
    const head = pageHead('문서 온톨로지', '문서 · 항목 · 개념과 온톨로지 연결을 조회합니다.', `${pick}<a class="btn" href="#catalog">문서 추가</a>`);
    if (!sp || sp.busy) return `${head}<div class="empty"><span class="spin"></span>문서를 읽는 중입니다.</div>`;
    if (sp.error) return `${head}<div class="banner no"><div class="why">${esc(sp.error)}</div></div>`;
    const g = S.dg && !S.dg.busy ? S.dg : null;
    const inScope = sp.items.filter(inDocScope);
    const inGraph = (kinds) => (g.nodes || []).filter((n) => kinds.includes(n.module)).length;
    const stats = [[inScope.length, '문서'], [g && g.sections_shown ? inGraph(['section']) : sp.sections, '항목'], [g ? (g.nodes || []).length - inGraph(['document', 'section']) : sp.concepts, '개념'],
      [g ? g.relations : (sp.reading || {}).relations || 0, '관계'], [inScope.reduce((n, d) => n + d.chunks, 0), '벡터 청크']].map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join('');
    const qs = S.dq;
    const queries = !qs ? '' : `<div class="card" style="margin-top:14px"><div class="ch">문서 온톨로지 질의${qs.conformance ? `<div class="right"><span class="chip ${qs.conformance.agree === qs.conformance.queries ? 'ok' : 'bad'}">SQL · 그래프 결과 일치 ${qs.conformance.agree} / ${qs.conformance.queries}</span></div>` : ''}</div><div class="cb">
        ${qs.queries.map((q) => `<div class="sec" style="margin-top:6px">${esc(q.label)} <span class="mono muted cn">${esc(q.name)}</span></div>${q.error ? `<div class="hint warn">${esc(q.error)}</div>` : `<table class="tight"><tr>${q.columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>${q.rows.slice(0, 5).map((row) => `<tr>${row.map((v) => `<td>${esc(cellWord(v))}</td>`).join('')}</tr>`).join('')}</table><div class="muted" style="font-size:11.5px;margin-top:4px">전체 ${q.total}행</div>`}`).join('')}
      </div></div>`;
    return `${head}<div class="stats">${stats}</div>
      <div class="card" id="dreadcard" style="margin-bottom:14px">${readCard()}</div>
      <div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(320px,1fr)">
        ${dgxCard(g)}
        <div class="card" id="docside">${docSide()}</div>
      </div>${relationCard()}${queries}`;
  }

  async function readRelations() {
    if (S.djob && S.djob.running) return;
    let r;
    try { r = await api('space/relations/start', { folder: S.dfolder, reader: S.dreader }); } catch (e) { return fail(e); }
    if (!r.ok) return toast(r.error, true);
    if (r.done) return toast('추출할 청크가 없습니다. 이 범위의 청크를 모두 읽었습니다.');
    S.djob = { id: r.job, running: true, done: 0, total: 0, seconds: 0, folder: S.dfolder, reader: S.dreader || S.sp.reader, read: 0, passages: 0, relations: 0, names: 0 };
    render();
    while (S.djob && S.djob.id === r.job && S.djob.running) {
      await new Promise((ok) => { setTimeout(ok, 2000); });
      let st;
      try { st = await api(`space/relations/status?job=${encodeURIComponent(r.job)}`); } catch (e) { st = { ok: false, error: e.message }; }
      if (!st.ok) { S.djob = null; toast(st.error, true); break; }
      S.djob = { ...S.djob, ...st, stop: S.djob.stop };
      const card = $('#dreadcard');
      if (card && S.tab === 'docs') card.innerHTML = readCard();
      if (!st.running) {
        const out = st.result || {};
        if (!out.ok || out.error) toast(out.error || '관계를 추출하지 못했습니다.', true);
        else toast(out.busy ? `모델 호출 한도로 멈췄습니다. 청크 ${out.read}개를 읽고 관계 ${out.found}개를 추가했습니다. 다시 선택하면 이어서 추출합니다.`
          : `청크 ${out.read}개를 읽고 관계 ${out.found}개를 추가했습니다.${out.left ? ` 남은 청크 ${out.left}개는 다시 선택하면 이어서 추출합니다.` : ''}`);
        S.djob = null; S.dg = null; S.drel = null; S.dq = null; S.sp = null;
        if (S.tab === 'docs') { loadSpace(); render(); }
      }
    }
  }

  const inDocScope = (d) => !S.dfolder || d.folder === S.dfolder || (d.folder || '').startsWith(S.dfolder + '/');

  // what the node picked in the document graph holds: an item's text and concepts, a document's items, where a concept is named
  const DOC_KIND = { document: '문서', section: '항목', ontology: '온톨로지 요소', keyword: '키워드' };
  function elementWord(el) {  // a concept's definition, as the definition reads it
    const [kind, rest] = [el.split(':')[0], el.split(':').slice(1).join(':')];
    const m = S.mg.st && !S.mg.st.error ? S.mg.st : null;
    if (kind === 'object') { const o = m && m.objects.find((x) => x.name === rest); return { kind: 'Entity', label: o ? o.label : rest, text: o ? o.description : '', obj: rest }; }
    if (kind === 'area') { const a = m && (m.areas || []).find((x) => x.name === rest); return { kind: 'Object', label: a ? a.label : rest, text: a ? a.description : '', area: rest }; }
    if (kind === 'property') {
      const [o, p] = rest.split('.'), pr = m && m.properties.find((x) => x.object === o && x.name === p);
      return { kind: 'Property', label: pr ? pr.label : rest, text: pr ? pr.description : '', obj: o };
    }
    if (kind === 'value') { const [path, v] = rest.split('='); return { kind: '허용값', label: v, text: `${path} 의 값`, obj: path.split('.')[0] }; }
    const named = { decision: S.st.decisions, query: S.st.queries }[kind];  // a table or a query goes by its label
    const d = named && named.find((x) => x.name === rest);
    return { kind: ELEMENT[kind] || kind, label: d ? d.label : rest, text: '' };
  }

  function docSide() {
    const sp = S.sp, dg = S.dg && !S.dg.busy && !S.dg.error ? S.dg : null, id = S.dgx.sel;
    const byId = dg ? Object.fromEntries((dg.nodes || []).map((n) => [n.id, n])) : {};
    const node = byId[id];
    const near = (label) => (dg ? dg.edges.filter((e) => e.label === label && (e.source === id || e.target === id)).map((e) => byId[e.source === id ? e.target : e.source]).filter(Boolean) : []);
    const pick = (n) => `<button class="chip" data-act="dgxpick" data-id="${esc(n.id)}">${esc(n.label)}</button>`;
    const chips = (xs) => (xs.length ? `<div class="chips" style="margin-top:4px">${xs.map(pick).join('')}</div>` : '<div class="muted" style="font-size:12px">없음</div>');
    let body;
    if (node && node.module === 'section') {
      const sel = S.dsec && S.dsec.id === id ? S.dsec : null;
      body = !sel ? '<div class="empty"><span class="spin"></span>본문을 불러오는 중입니다.</div>'
        : `<div class="muted" style="font-size:12px;margin:0 0 10px">${esc(sel.document)}</div><div class="hit-text" style="white-space:pre-wrap">${esc(sel.text)}</div>
          <div class="sec">언급한 개념</div>${sel.concepts.length ? `<div class="chips">${sel.concepts.map((c) => (c.element.startsWith('object:') ? `<button class="chip b" data-act="srobj" data-obj="${esc(c.element.slice(7))}">${esc(c.label)}</button>` : `<span class="chip">${esc(c.label)} · ${esc(KIND_LABEL[c.kind] || c.kind)}</span>`)).join('')}</div>` : '<div class="muted" style="font-size:12px">없음</div>'}`;
    } else if (node && node.module === 'document') {
      const items = near('항목'), ids = new Set(items.map((n) => n.id));
      // what a document names is what its items name
      const named = [...new Map(dg.edges.filter((e) => e.label === '언급' && (ids.has(e.source) || ids.has(e.target))).map((e) => byId[ids.has(e.source) ? e.target : e.source]).filter(Boolean).map((n) => [n.id, n])).values()];
      body = `<div class="label">항목 ${items.length}</div>${chips(items)}<div class="label" style="margin-top:12px">언급한 개념 ${named.length}</div>${chips(named)}`;
    } else if (node) {
      const named = near('언급'), items = named.filter((n) => n.module === 'section'), docs = named.filter((n) => n.module === 'document');
      const el = node.module === 'ontology' && node.table && node.table.includes(':') ? elementWord(node.table) : null;
      const open = el && el.obj ? `<button class="btn sm" data-act="srobj" data-obj="${esc(el.obj)}" style="margin-top:8px">Entity 열기</button>` : '';
      body = `${el ? `<div class="odrow"><span>${esc(el.kind)}</span><b>${esc(el.label)}</b></div>${el.text ? `<div class="muted" style="font-size:12.5px;margin:4px 0 8px">${esc(el.text)}</div>` : ''}${open}` : ''}
        <div class="label" style="margin-top:12px">언급한 항목 ${items.length}</div>${chips(items)}
        ${docs.length ? `<div class="label" style="margin-top:12px">언급한 문서 ${docs.length}</div>${chips(docs)}` : ''}
        ${near('함께 언급').length ? `<div class="label" style="margin-top:12px">함께 언급된 개념 ${near('함께 언급').length}</div>${chips(near('함께 언급').slice(0, 20))}` : ''}`;
    } else {
      body = `<table class="tight"><tr><th>문서</th><th>항목</th><th>언급</th></tr>${sp.items.filter(inDocScope).map((d) => `<tr><td><b>${esc(d.name)}</b>${d.fixed ? '' : ' <span class="chip sm b">업로드</span>'}</td><td>${d.sections}</td><td>${d.mentions}</td></tr>`).join('')}</table>`;
    }
    const head = node ? `${esc(node.label)} <span class="chip sm">${esc(DOC_KIND[node.module] || node.module)}</span>` : '문서 목록';
    return `<div class="ch">${head}${node ? '<div class="right"><button class="btn sm ghost" data-act="dsecclose">문서 목록</button></div>' : ''}</div><div class="cb scroll" style="max-height:600px">${body}</div>`;
  }

  async function dgxPick(id) {  // a node pressed in the graph or named in the side: shown there, an item with its text
    const dg = S.dg;
    if (!dg || dg.busy) return;
    const outside = !S.dgx.nodes[id];
    if (outside) dgxAround(id);  // a node not in the picture moves to its middle
    S.dgx.sel = id;
    S.dsec = null;
    if (outside) render(); else { dgxPaint(); $('#docside').innerHTML = docSide(); }
    const title = (dg.titles || {})[id];
    if (!title) return;
    const parent = (dg.edges.find((e) => e.label === '항목' && e.target === id) || {}).source;
    const doc = (dg.nodes.find((n) => n.id === parent) || {}).label || '';
    try {
      const sec = await api(`space/section?document=${encodeURIComponent(doc)}&section=${encodeURIComponent(title)}`);
      if (S.dgx.sel !== id) return;
      S.dsec = { ...sec, id };
      const side = $('#docside');
      if (side) side.innerHTML = docSide();
    } catch (e) { fail(e); }
  }

  // ---- the document graph: one document or concept in the middle, what it holds and names around it -----------------
  const DGX_SHAPE = { document: 'box', section: 'round', ontology: 'pill', keyword: 'tag' };
  const DGX_LOOK = {
    word: (n) => (n.label.length > 14 ? `${n.label.slice(0, 13)}…` : n.label),
    shape: (type) => DGX_SHAPE[type] || 'pill',
    color: (type) => GX_COLOR[Math.max(0, ((S.dg && S.dg.clusters) || []).findIndex((c) => c.id === type)) % GX_COLOR.length],
    seed: (g) => g.seed,
    name: '문서 그래프',
  };
  const DGX_MAX = 26;  // nodes around the one in the middle, nearest first

  function dgxAround(seed) {
    const dg = S.dg, x = S.dgx, near = {};
    const kind = Object.fromEntries(dg.nodes.map((n) => [n.id, n.module]));
    // a document's sections carry what it names: around a document the path is document, section, concept
    const direct = (e) => kind[seed] === 'document' && e.label !== '항목' && (kind[e.source] === 'document' || kind[e.target] === 'document');
    dg.edges.forEach((e) => { (near[e.source] = near[e.source] || []).push(e); (near[e.target] = near[e.target] || []).push(e); });
    const keep = new Set([seed]);
    let ring = [seed];
    for (let d = 0; d < 2 && keep.size < DGX_MAX; d += 1) {
      const next = [];
      ring.forEach((id) => (near[id] || []).forEach((e) => {
        if (e.label === '함께 언급') return;  // the section between two concepts says the same, without the crowd
        if (direct(e)) return;
        const o = e.source === id ? e.target : e.source;
        if (!keep.has(o) && keep.size < DGX_MAX) { keep.add(o); next.push(o); }
      }));
      ring = next;
    }
    const byId = Object.fromEntries(dg.nodes.map((n) => [n.id, n]));
    Object.assign(x, { seed, pos: {}, zoomed: false, sel: keep.has(x.sel) ? x.sel : '' });
    x.nodes = Object.fromEntries([...keep].filter((id) => byId[id]).map((id) => [id, { type: byId[id].module, label: byId[id].label }]));
    x.edges = dg.edges.filter((e) => keep.has(e.source) && keep.has(e.target) && !direct(e) && e.label !== '함께 언급')
      .map((e) => ({ source: e.source, target: e.target, label: e.label }));
  }

  function dgxCard(g) {
    const x = S.dgx, n = Object.keys(x.nodes).length;
    const docs = g ? (g.nodes || []).filter((d) => d.module === 'document') : [];
    const kinds = g ? (g.clusters || []).filter((c) => Object.values(x.nodes).some((v) => v.type === c.id)) : [];
    const legend = kinds.map((c) => { const [ink, fill] = DGX_LOOK.color(c.id); return `<span class="gxleg"><i style="background:${fill};border-color:${ink}"></i>${esc(c.label)} ${Object.values(x.nodes).filter((v) => v.type === c.id).length}</span>`; }).join('');
    const seed = x.nodes[x.seed];
    return `<div class="card"><div class="ch">${seed ? `${esc(seed.label)} 중심` : '문서 그래프'}<div class="right">
        ${docs.length ? `<select data-in="dgxseed" aria-label="중심 문서"><option value="">문서 선택</option>${docs.map((d) => opt(d.id, d.label, x.seed)).join('')}</select>` : ''}
        <label class="chip chipsel">레이아웃: <select data-in="dgxlayout" aria-label="레이아웃">${[['radial', '방사형'], ['layered', '계층']].map(([k, w]) => opt(k, w, x.layout)).join('')}</select></label>
        <span class="erzoom" role="group" aria-label="확대"><button class="iconbtn" data-act="dgxzoom" data-z="-1" aria-label="축소">−</button><button class="btn sm ghost" data-act="dgxzoom" data-z="0" title="화면에 맞춤">${Math.round((x.zoom || 1) * 100)}%</button><button class="iconbtn" data-act="dgxzoom" data-z="1" aria-label="확대">+</button></span></div></div>
      <div class="cb gxcanvas dgxcanvas" id="dgxcanvas">${n ? gxSvg(x, DGX_LOOK) : '<div class="empty">문서가 없습니다.</div>'}</div>
      <div class="cb gxfoot"><span class="gxlegs">${legend}</span><span class="muted">표시 ${n}개 · 관계 ${x.edges.length}</span></div></div>`;
  }

  function dgxPaint() {
    const box = $('#dgxcanvas'), x = S.dgx;
    if (!box || !Object.keys(x.nodes).length) return;
    gxFit(x, box, DGX_LOOK);
    box.innerHTML = gxSvg(x, DGX_LOOK);
    const z = $('[data-act=dgxzoom][data-z="0"]');
    if (z) z.textContent = `${Math.round((x.zoom || 1) * 100)}%`;
  }

  function dgxZoom(step) {
    const x = S.dgx;
    x.zoomed = step !== 0;
    if (step === 0) x.zoom = 1; else x.zoom = Math.min(1.8, Math.max(0.35, Math.round(((x.zoom || 1) + step * 0.1) * 10) / 10));
    dgxPaint();
  }

  async function mountDocs() {
    if (!S.sp) loadSpace();
    if (S.sp && !S.sp.busy && !S.sp.error) {
      if (!S.dg) {
        S.dg = { busy: true };
        try { S.dg = await api(`space/graph?folder=${encodeURIComponent(S.dfolder)}`); } catch (e) { S.dg = { nodes: [], edges: [], clusters: [], error: e.message }; }
        if (S.tab === 'docs') { render(); return; }
      }
      if (S.drel === null) {
        S.drel = 0;
        try { S.drel = await api(`space/relations?folder=${encodeURIComponent(S.dfolder)}`); } catch (e) { S.drel = { total: 0, relations: [] }; }
        if (S.drel.total && S.tab === 'docs') { render(); return; }
        const card = $('#dreadcard');  // the reading of this folder came with the list, relations or none
        if (card && S.tab === 'docs') card.innerHTML = readCard();
      }
      if (S.dg && !S.dg.busy) {
        if (S.dgx.of !== S.dg) {  // a graph read anew: its first document in the middle
          S.dgx.of = S.dg;
          const first = (S.dg.nodes || []).find((n) => n.module === 'document');
          if (first) dgxAround(first.id); else Object.assign(S.dgx, { nodes: {}, edges: [], seed: '' });
          if (S.tab === 'docs') render();
          return;
        }
        mountGx($('#dgxcanvas'), S.dgx, DGX_LOOK, { open: (id) => { dgxAround(id); render(); }, zoom: dgxZoom, pick: (id) => dgxPick(id), clear: () => { if (S.dgx.sel || S.dsec) ACT.dsecclose(); } });
        dgxPaint();
      }
      if (!S.dq) { S.dq = 0; try { S.dq = await api('space/queries'); if (S.tab === 'docs') render(); } catch (e) { S.dq = null; } }
    }
  }

  async function adCheck(say) {  // the page runs it once on opening; the button runs it again
    S.adbusy = true; render();
    try { S.adrep = await api('adapters/check', {}); S.adrs = null; if (say) toast('적합성 시험을 마쳤습니다.'); } catch (e) { fail(e); }
    S.adbusy = false; render();
  }

  function balanceAdapters() {  // the reasoners card joins whichever column is shorter as drawn, when the two sit side by side
    const cols = [...document.querySelectorAll('.adcol')], card = $('#adreas');
    if (cols.length !== 2 || !card || cols[0].offsetTop !== cols[1].offsetTop) return;
    card.remove();
    (cols[0].offsetHeight <= cols[1].offsetHeight ? cols[0] : cols[1]).appendChild(card);
  }

  // ---- data explorer: every asset of the space as folders, searched and managed in one place ------------------------

  const EX_ACTION = { upload: '업로드', replace: '교체', folder: '폴더 생성', rename: '이름 변경', move: '이동', trash: '휴지통으로 이동',
    restore: '복원', purge: '영구 삭제', include: '초안 포함', exclude: '초안 제외', embed: '임베딩 켜기', unembed: '임베딩 끄기' };
  const EX_NODE = { group: '분류', repo: '저장소', dir: '폴더', kind: '분류' };
  const EX_FOUND = { 이름: 'b', 경로: 'b', 정의: 'ok', '단어 일치': '', '의미 유사': '' };
  const exHolds = (id) => /^(group|repo|dir|kind|database|collection|table|object):/.test(id);  // what opens into a list
  const exInRepo = (id) => /^(repo|dir):/.test(id);
  const exFolder = (id) => (id.startsWith('dir:') ? id.slice(4) : '');

  async function loadExplorer(node) {
    const x = S.ex;
    if (node !== undefined) Object.assign(x, { node, sel: {}, edit: null, moving: null });
    try {
      x.tree = await api('explorer');
      if (!x.node || (x.node.startsWith('repo:') && x.node !== `repo:${x.tree.repo}`)) x.node = `repo:${x.tree.repo}`;  // another repository was put in use
      try { x.items = await api('explorer/items?node=' + encodeURIComponent(x.node)); } catch (e) {  // a node that went from under the page
        x.node = `repo:${x.tree.repo}`;
        x.items = await api('explorer/items?node=' + encodeURIComponent(x.node));
      }
      for (const t of x.items.trail) x.open[t.id] = true;
      if (x.tab === 'log') x.log = (await api('catalog/history')).items;
      if (x.tab === 'trash') x.trash = (await api('catalog/trash')).items;
      if (x.q && x.hits) x.hits = await api(`explorer/search?q=${encodeURIComponent(x.q)}&kind=${encodeURIComponent(x.kind)}`);
    } catch (e) { x.error = e.message; }
    if (S.tab === 'explorer') render();
  }

  async function explorerChanged(node) {  // a change to files touches the catalog, the drafts and the space as well
    spaceChanged();
    S.files = null; S.conv = null; S.cat.sel = {}; S.cat.st = null; S.ex.sel = {};
    S.st = await api('state');
    await loadExplorer(node);
  }

  function exTree() {
    const x = S.ex, t = x.tree.tree;
    const kids = (id) => t.filter((n) => n.parent === id);
    const row = (n, depth) => {
      const sub = kids(n.id), open = x.open[n.id];
      return `<div class="exn${x.node === n.id ? ' on' : ''}" style="padding-left:${4 + depth * 14}px">
        ${sub.length ? `<button class="exc${open ? ' open' : ''}" data-act="extoggle" data-id="${esc(n.id)}" aria-label="${open ? '접기' : '펼치기'}">${ui('chevron')}</button>` : '<span class="exc"></span>'}
        <button class="exl" data-act="exgo" data-id="${esc(n.id)}"${n.id.startsWith('repo:') && !n.current ? ' data-switch="1"' : ''}>${esc(n.label)}</button>
        ${n.current ? '<span class="chip sm b">사용 중</span>' : ''}<span class="exk">${count(n.count)}</span></div>${open ? sub.map((c) => row(c, depth + 1)).join('') : ''}`;
    };
    return kids('').map((n) => row(n, 0)).join('');
  }

  function exKind(r) {
    return r.kind === 'group' ? (KIND[r.id.split(':')[0]] || EX_NODE[r.id.split(':')[0]] || '분류') : (KIND[r.kind] || r.kind);
  }

  function exRow(r, search) {
    const x = S.ex;
    const status = r.status.map((s) => `<span class="chip sm ${esc(s.tone || '')}"${s.why ? ` title="${esc(s.why)}"` : ''}>${esc(s.text)}</span>`).join('');
    const holds = exHolds(r.id) || r.kind === 'folder';
    const name = x.edit && x.edit.id === r.id
      ? `<input type="text" id="exedit" data-in="exedit" value="${esc(x.edit.value)}" aria-label="새 이름">`
      : `<button class="fname" data-act="exopen" data-id="${esc(r.id)}" data-kind="${esc(r.kind)}"${r.current === false && r.id.startsWith('repo:') ? ' data-switch="1"' : ''}>${holds ? ui('catalog2') : ''}<span>${esc(r.label)}</span></button>`;
    const tab = !holds && r.kind !== 'file' ? KIND_TAB[r.kind] : '';
    const acts = [r.kind === 'file' ? `<button class="btn sm ghost" data-act="exview" data-path="${esc(r.path)}">보기</button><a class="btn sm ghost" href="/api/catalog/download?path=${encodeURIComponent(r.path)}">내려받기</a>` : '',
      tab ? `<a class="btn sm ghost" href="#${tab}">${esc(navLabel(tab))} 열기</a>` : '',
      r.kind === 'object' ? `<button class="btn sm ghost" data-act="exrecords" data-type="${esc(r.id.split(':').pop())}">레코드 보기</button>` : '',
      r.manage ? `<button class="btn sm ghost" data-act="exrename" data-id="${esc(r.id)}">이름 변경</button>` : ''].join('');
    const where = search ? `<td class="muted" style="font-size:12px;white-space:nowrap">${(r.trail || []).map((t) => `<button class="plink" data-act="exgo" data-id="${esc(t.id)}">${esc(t.label)}</button>`).join(' › ') || '-'}</td>
      <td><div class="chips">${r.found.map((f) => `<span class="chip sm ${EX_FOUND[f] || ''}">${esc(f)}</span>`).join('')}</div></td>` : `<td class="muted">${r.bytes !== undefined ? fileSize(r.bytes) : '-'}</td>`;
    const what = search && r.snippet ? `<span class="muted" style="font-size:12px">${esc(r.snippet)}</span>` : esc(r.facts.join(' · ')) || '<span class="muted">-</span>';
    return `<tr class="${x.sel[r.path] ? 'sel' : ''}"><td>${r.manage ? `<input type="checkbox" data-in="exsel" data-path="${esc(r.path)}"${x.sel[r.path] ? ' checked' : ''} aria-label="${esc(r.label)} 선택">` : ''}</td>
      <td>${name}</td><td style="white-space:nowrap">${esc(exKind(r))}</td>${where}<td style="font-size:12.5px">${what}</td><td><div class="chips">${status || '<span class="muted">-</span>'}</div></td>
      <td style="text-align:right;white-space:nowrap">${acts}</td></tr>`;
  }

  function exTable(items, search) {
    const head = `<tr><th style="width:30px"></th><th>이름</th><th>종류</th>${search ? '<th>위치</th><th>찾은 곳</th>' : '<th>크기</th>'}<th>내용</th><th>상태</th><th></th></tr>`;
    const adding = S.ex.edit && S.ex.edit.id === '' ? `<tr><td></td><td colspan="${search ? 7 : 6}"><input type="text" id="exedit" data-in="exedit" value="${esc(S.ex.edit.value)}" placeholder="새 폴더 이름" aria-label="새 폴더 이름"></td></tr>` : '';
    return `<div class="cwrap"><table class="tight extable">${head}${adding}${items.map((r) => exRow(r, search)).join('')}</table></div>`;
  }

  function viewExplorer() {
    const x = S.ex;
    const seg = `<div class="seg">${[['store', '보관함'], ['log', '작업 기록'], ['trash', `휴지통${x.tree && x.tree.summary.trash ? ` ${x.tree.summary.trash}` : ''}`]]
      .map(([k, l]) => `<button class="${x.tab === k ? 'on' : ''}" data-act="extab" data-k="${k}">${esc(l)}</button>`).join('')}</div>`;
    const head = pageHead('자산 탐색기', '파일 · 테이블 · 문서 · Entity를 찾고 관리합니다.', seg);
    if (x.error && !x.tree) return `${head}<div class="banner no"><div class="why">${esc(x.error)}</div></div>`;
    if (!x.tree || !x.items) return `${head}<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>`;
    const s = x.tree.summary;
    const sum = `<div class="exsum">${[[s.files, '파일'], [s.folders, '폴더'], [s.tables, '테이블'], [s.columns, '컬럼'], [s.documents, '문서'], [s.chunks, '청크'],
      [s.objects, 'Entity'], [s.properties, 'Property'], [s.links, 'Relation'], [s.uses, '질의 · 결정 · Action · 역할']].map(([n, l]) => `<span><b>${count(n)}</b>${esc(l)}</span>`).join('')}</div>`;
    if (x.tab === 'log') {
      const rows = (x.log || []).map((e) => `<tr><td class="muted" style="white-space:nowrap">${esc(e.at.replace('T', ' '))}</td><td>${esc(EX_ACTION[e.action] || e.action)}</td>
        <td class="mono" style="font-size:12px">${esc(e.path)}</td><td class="muted" style="font-size:12.5px">${esc(e.detail || '')}</td></tr>`).join('');
      return `${head}${sum}<div class="card"><div class="ch">작업 기록<div class="right muted" style="font-size:12px">${esc(x.tree.tree.find((n) => n.current).label)} · 최근 ${count((x.log || []).length)}건</div></div>
        <div class="cb">${rows ? `<div class="cwrap"><table class="tight"><tr><th>시각</th><th>작업</th><th>경로</th><th>상세</th></tr>${rows}</table></div>` : '<div class="empty">기록된 작업이 없습니다.</div>'}</div></div>`;
    }
    if (x.tab === 'trash') {
      const picked = (x.trash || []).filter((t) => x.tsel[t.id]);
      const rows = (x.trash || []).map((t) => `<tr><td><input type="checkbox" data-in="extsel" data-id="${esc(t.id)}"${x.tsel[t.id] ? ' checked' : ''} aria-label="${esc(t.name)} 선택"></td>
        <td><b>${esc(t.name)}</b></td><td class="mono muted" style="font-size:12px">${esc(t.path)}</td><td>${t.kind === 'folder' ? '폴더' : '파일'}</td><td>${count(t.files)}개</td><td>${fileSize(t.bytes)}</td>
        <td class="muted" style="white-space:nowrap">${esc(t.at.replace('T', ' '))}</td><td style="text-align:right;white-space:nowrap"><button class="btn sm" data-act="exrestore" data-id="${esc(t.id)}">복원</button>
        <button class="btn sm ghost danger" data-act="expurge" data-id="${esc(t.id)}">영구 삭제</button></td></tr>`).join('');
      const tools = `${picked.length ? `<button class="btn sm" data-act="exrestore">선택 복원 ${picked.length}</button><button class="btn sm ghost danger" data-act="expurge">선택 영구 삭제</button>` : ''}
        <button class="btn sm ghost danger" data-act="expurge" data-all="1"${rows ? '' : ' disabled'}>휴지통 비우기</button>`;
      return `${head}${sum}<div class="card"><div class="ch">휴지통<div class="right">${tools}</div></div>
        <div class="cb">${rows ? `<div class="cwrap"><table class="tight"><tr><th style="width:30px"></th><th>이름</th><th>원래 위치</th><th>종류</th><th>파일</th><th>크기</th><th>삭제일</th><th></th></tr>${rows}</table></div>` : '<div class="empty">휴지통에 항목이 없습니다.</div>'}</div></div>`;
    }
    const kinds = ['', 'file', 'folder', 'table', 'column', 'document', 'object', 'property', 'link', 'query', 'decision', 'action', 'role'];
    const repo = exInRepo(x.node), picked = Object.keys(x.sel).filter((k) => x.sel[k]);
    const tool = `<div class="extool"><div class="exq">${ui('search')}<input type="search" data-in="exq" value="${esc(x.q)}" placeholder="이름 · 경로 · 정의 · 문서 내용" aria-label="데이터 검색"></div>
      <select class="inline" data-in="exkind" aria-label="종류">${kinds.map((k) => `<option value="${k}"${x.kind === k ? ' selected' : ''}>${k ? esc(KIND[k] || k) : '전체 종류'}</option>`).join('')}</select>
      <button class="btn sm primary" data-act="exsearch"${x.busy ? ' disabled' : ''}>${x.busy ? '<span class="spin"></span>' : ''}검색</button>${x.hits ? '<button class="btn sm ghost" data-act="exclear">검색 지우기</button>' : ''}
      <div class="grow"></div>${repo && canEdit() ? `<button class="btn sm" data-act="exnew">새 폴더</button><button class="btn sm" data-act="exupload">업로드</button>
      <button class="btn sm" data-act="exmove"${picked.length ? '' : ' disabled'}>이동</button><button class="btn sm ghost danger" data-act="exdelete"${picked.length ? '' : ' disabled'}>삭제</button>` : ''}
      <button class="iconbtn" data-act="exreload" aria-label="새로고침" title="새로고침">${ui('reload')}</button></div>`;
    const folders = [''].concat(x.tree.tree.filter((n) => n.id.startsWith('dir:')).map((n) => n.id.slice(4)));
    const moving = x.moving ? `<div class="cbulk"><b>${picked.length}개 이동</b><select class="inline" data-in="exto" aria-label="이동할 폴더">${folders.map((f) => `<option value="${esc(f)}"${x.moving.to === f ? ' selected' : ''}>${esc(f || x.tree.tree.find((n) => n.current).label)}</option>`).join('')}</select>
      <button class="btn sm primary" data-act="exmoveok">이동</button><button class="btn sm ghost" data-act="exmovecancel">취소</button></div>` : '';
    let list;
    if (x.hits) {
      const h = x.hits, by = {};
      for (const r of h.hits) for (const f of r.found) by[f] = (by[f] || 0) + 1;
      const nearest = h.hits.length && h.hits.every((r) => r.found.every((f) => f === '의미 유사'));
      const note = nearest ? '<div class="hint" style="margin-bottom:8px">이름, 정의, 단어로 찾은 항목이 없어 의미가 가장 가까운 문서를 표시합니다.</div>' : '';
      list = `<div class="card exlist"><div class="ch">'${esc(h.q)}' 검색 결과<div class="right muted" style="font-size:12px">${count(h.total)}건${Object.entries(by).map(([f, n]) => ` · ${esc(f)} ${count(n)}`).join('')}</div></div>
        <div class="cb">${h.hits.length ? note + exTable(h.hits, true) : '<div class="empty">찾은 항목이 없습니다.</div>'}</div></div>`;
    } else {
      const trail = x.items.trail.concat([{ id: x.node, label: x.items.label }]);
      const bar = trail.map((t, i) => (i === trail.length - 1 ? `<b>${esc(t.label)}</b>` : `<button class="plink" data-act="exgo" data-id="${esc(t.id)}">${esc(t.label)}</button>`)).join(' › ');
      list = `<div class="card exlist"><div class="ch"><div class="extrail">${bar}</div><div class="right muted" style="font-size:12px">항목 ${count(x.items.items.length)}개</div></div>
        <div class="cb">${x.items.items.length || (x.edit && x.edit.id === '') ? exTable(x.items.items, false) : '<div class="empty">항목이 없습니다.</div>'}</div></div>`;
    }
    return `${head}${sum}${tool}${moving}<div class="exbody"><div class="card extree"><div class="cb">${exTree()}</div></div>${list}</div>`;
  }

  async function exSwitch(repo) {
    if (!window.confirm('사용 중인 저장소를 전환합니다.')) return;
    try { await api('catalog/repository', { op: 'use', id: repo }); await explorerChanged(`repo:${repo}`); } catch (e) { fail(e); }
  }

  function viewMap() {
    const m = S.amap;
    const head = pageHead('자산 그래프', '자산 간 연결 관계와 영향 범위를 조회합니다.');
    if (!m) return `${head}<div class="empty"><span class="spin"></span>지도를 그리는 중입니다.</div>`;
    if (m.error) return `${head}<div class="banner no"><div class="why">${esc(m.error)}</div></div>`;
    return `${head}<div class="grid" style="grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr)">
      <div class="card"><div class="ch">자산 그래프</div><div class="cb" style="padding:0"><div class="kg" id="mapgraph"></div></div></div>
      <div class="card"><div class="ch">자산 정보</div><div class="cb scroll" style="max-height:600px" id="mapside">${mapSide()}</div></div></div>`;
  }

  function mapGroups(rows) {
    const by = new Map();
    rows.forEach((x) => {
      const word = MAP_STORE.has(x.kind) ? '저장소 어댑터' : KIND[x.kind] || x.kind;
      const list = by.get(word) || [];
      if (!list.some((y) => y.label === x.label)) by.set(word, [...list, x]);
    });
    const rank = (w) => { const i = MAP_ORDER.indexOf(w); return i < 0 ? MAP_ORDER.length : i; };
    return [...by].sort((a, b) => rank(a[0]) - rank(b[0]));
  }

  const mapCount = (rows) => mapGroups(rows).reduce((n, [, list]) => n + list.length, 0);

  function mapRows(rows) {
    if (!rows.length) return '<div class="muted" style="font-size:12.5px">없음</div>';
    const shown = new Set(S.amap.nodes.map((x) => x.id));
    return mapGroups(rows).map(([word, list]) => `<div class="mrow"><span class="mk">${esc(word)} ${list.length}</span><div class="chips">${list.map((x) => (shown.has(x.id)
      ? `<button class="chip sm" data-act="mapgo" data-id="${esc(x.id)}">${esc(x.label)}</button>` : `<span class="chip sm">${esc(x.label)}</span>`)).join('')}</div></div>`).join('');
  }

  function mapSide() {
    const m = S.amap, n = S.mapn;
    if (n) {
      const tab = KIND_TAB[n.kind];
      return `<div class="mapnode"><div><span>${esc(KIND[n.kind] || n.kind)}</span><b>${esc(n.label)}</b></div>${tab ? `<a class="btn sm" href="#${tab}">${esc(navLabel(tab))} 열기</a>` : ''}</div>
        <div class="sec">영향 범위<span class="n">${mapCount(n.impact)}건</span></div>${mapRows(n.impact)}
        <div class="sec">참조 자산<span class="n">${mapCount(n.uses)}건</span></div>${mapRows(n.uses)}`;
    }
    return `<div class="sec" style="margin-top:0">요소</div><dl class="mparts">${MAP_PARTS.map(([a, b]) => `<dt>${esc(a)}</dt><dd>${esc(b)}</dd>`).join('')}</dl>
      ${m.unused.length ? `<div class="sec">미사용 자산<span class="n">${m.unused.length}건</span></div><div class="chips">${m.unused.map((x) => `<span class="chip sm">${esc(x.label)}</span>`).join('')}</div>` : ''}`;
  }

  // what each REST tool does, in the page's words; the OpenAPI document keeps the English an agent framework reads
  const TOOL_WORD = { describe_space: '공간에 있는 문서, 벡터 저장소, 임베딩 모델, 그래프 저장소, 추론기, 온톨로지 규모', describe_ontology: '이 토큰이 사용할 수 있는 Entity, 속성, 관계, 등록 질의, 결정, Action',
    answer_question: '질문 하나에 결정, 데이터, 문서로 답하고 적용 규칙, 소스 값, 조항을 함께 반환', agent_context: '질문과 관련된 정의와 규칙을 Agent 프롬프트에 넣을 글로 반환',
    find_definitions: '질문과 관련된 Entity, 규칙, 질의, Action', describe_object: 'Entity 하나의 계층 위치, 속성, 관계, 결정, Action', list_documents: '공간의 문서와 항목, 언급한 개념',
    search_documents: '문서를 의미로 검색하고 문서, 항목, 관련 온톨로지 요소를 반환', run_query: '등록 질의 또는 질의 IR을 저장소에서 실행', translate_query: '질의를 저장소 언어의 질의문으로 변환',
    run_sparql: 'SPARQL SELECT를 어느 저장소에서든 실행', run_cypher: 'Cypher 조회를 어느 저장소에서든 실행', decide: '레코드 키 또는 판정 값으로 결정표를 실행해 결과, 적용 규칙, 판정 경로, 근거, 모듈 버전을 반환',
    find_rules: '규칙 카드를 AXIOM부터 조회하고 조건, 결과, 예외, 근거, 소유자, 실행 연결을 반환', read_terms: '문장의 용어를 대표어로 바꾸고 뜻, 검색 표기, 혼동 주의 용어, 정의에서 찾은 이름을 반환',
    validate_values: 'Entity 값이 정의와 규칙 카드의 범위 안에 있는지 확인하고 위반 사유와 근거 규칙을 반환',
    run_questions: '검증 질문을 값 기준과 레코드 기준으로 측정하고 오답의 원인을 규칙과 Mapping으로 구분', list_libraries: '이 서버의 온톨로지와 모듈 버전',
    list_functions: '이 토큰이 실행할 수 있는 함수와 입출력, 버전, 담당', run_function: '등록 함수를 Entity 하나 또는 입력값으로 실행',
    request_action: 'Action 요청 · 검사 통과 시 승인 대기 접수 · 자동 승인 기준 안이면 즉시 실행', list_proposals: '이 토큰이 요청한 처리와 상태', get_record: 'Entity 하나의 값을 행 범위와 가림 안에서 반환' };

  // ---- calling the library as a workflow or an agent does: one /v1 call tried on this page, and how XGEN calls it

  const TRY_STATUS = { 422: ['warn', '판정 값 필요'], 409: ['warn', '데이터 소스 미연결'], 400: ['bad', '요청 오류'], 403: ['bad', '권한 없음'], 404: ['bad', '대상 없음'] };
  // the calls a platform makes first: id, label, path, the run button, what a 200 is called, what the panel says before a run
  const TRY_API = [
    ['decide', '판정', '/v1/decide', '판정 실행', '판정 완료', '실행 결과가 없습니다.'],
    ['validate', '값 검증', '/v1/validate', '검증 실행', '검증 완료', '실행 결과가 없습니다.'],
    ['terms', '용어 해석', '/v1/terms', '해석 실행', '해석 완료', '실행 결과가 없습니다.'],
    ['object', '개념 조회', '/v1/object', '조회 실행', '조회 완료', '실행 결과가 없습니다.']];
  const TRY_KIND = { rule: '규칙 위반', type: '형식 불일치', code: '허용되지 않은 코드', missing: '필수 값 누락', unknown: '정의에 없는 속성' };
  const tryApi = (c) => TRY_API.find((x) => x[0] === c.api) || TRY_API[0];

  function tryState(i) {
    const c = S.ctry || (S.ctry = { api: 'decide', decision: '', mode: 'values', values: {}, key: '', at: '', text: '', object: '', ovalues: {}, complete: false, res: null, busy: false, view: 'body' });
    if (!i.decisions.some((d) => d.name === c.decision)) { c.decision = (i.decisions[0] || {}).name || ''; c.values = {}; if (c.api === 'decide') c.res = null; }
    if (!(i.objects || []).some((o) => o.name === c.object)) { c.object = ((i.objects || [])[0] || {}).name || ''; c.ovalues = {}; if (c.api !== 'decide' && c.api !== 'terms') c.res = null; }
    return c;
  }

  // values as a platform sends them: typed, '' left out, '값 없음' as null
  function tryTyped(fields, raw) {
    const values = {};
    for (const f of fields || []) {
      const s = String((raw || {})[f.name] ?? '').trim();
      if (s === '') continue;
      if (s === 'null' || s === '값 없음') values[f.name] = null;
      else if (f.type === 'boolean') values[f.name] = s === 'true';
      else if (['integer', 'decimal', 'number'].includes(f.type) && !Number.isNaN(Number(s))) values[f.name] = Number(s);
      else values[f.name] = s;
    }
    return values;
  }

  // the body this page sends is the one a platform sends
  function tryBody(c, i) {
    if (c.api === 'terms') return { text: c.text.trim() };
    if (c.api === 'object') return { name: c.object };
    if (c.api === 'validate') {
      const o = (i.objects || []).find((x) => x.name === c.object);
      return { object: c.object, values: tryTyped(o && o.properties, c.ovalues), ...(c.complete ? { complete: true } : {}) };
    }
    const d = i.decisions.find((x) => x.name === c.decision);
    const body = { decision: c.decision };
    if (c.mode === 'record') { body.key = c.key.trim(); return body; }
    body.values = tryTyped(d && d.inputs, c.values);
    for (const x of d ? d.inputs : []) {  // a date given where days since it are read goes under its date Property
      const v = body.values[x.name];
      if (x.days_since && x.property && typeof v === 'string') { delete body.values[x.name]; body.values[x.property] = v; }
    }
    if (c.at.trim()) body.at = c.at.trim();
    return body;
  }

  function tryCode(c, i) {
    const base = location.origin, body = tryBody(c, i), path = tryApi(c)[2];
    const lib = i.library && i.libraries > 1 ? { library: i.library.id } : {};
    const json = JSON.stringify({ ...lib, ...body }, null, 2);
    const curl = `curl -X POST ${base}${path} \\\n  -H "Authorization: Bearer $ONTLAS_API_TOKEN" \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify({ ...lib, ...body })}'`;
    const node = [['method', 'POST'], ['url', `${base}${path}`], ['auth_type', 'bearer'], ['auth_token', 'API 토큰'], ['body_type', 'json'], ['body', JSON.stringify({ ...lib, ...body })], ['passthrough_input', 'false'], ['failure_mode', 'emit']];
    const text = { body: json, curl, node: node.map(([k, v]) => `${k}: ${v}`).join('\n') }[c.view];
    const tab = (k, label) => `<button class="tab${c.view === k ? ' on' : ''}" data-act="ctryview" data-k="${k}" aria-pressed="${c.view === k}">${label}</button>`;
    // how the node takes what the step before it sends: `input` is that step's whole value
    const template = { decide: `{"decision": "${c.decision}", "values": {{ input | tojson }}}`, validate: `{"object": "${c.object}", "values": {{ input | tojson }}}`, terms: '{"text": {{ input | tojson }}}' }[c.api];
    return `<div class="trycode"><div class="tabs">${tab('body', '요청 본문')}${tab('curl', 'cURL')}${tab('node', 'XGEN HTTP 요청 노드')}<div class="grow"></div><button class="iconbtn" data-act="copycode" data-v="${esc(text)}" aria-label="복사" title="복사">${ui('copy')}</button></div>
      ${c.view === 'node' ? `<table class="tight">${node.map(([k, v]) => `<tr><td class="mono" style="width:140px">${esc(k)}</td><td class="mono" style="word-break:break-all">${esc(v)}</td></tr>`).join('')}</table><div class="hint" style="margin-top:6px">${template ? `앞 노드의 값은 body에 템플릿으로 넣습니다. 예: <span class="mono">${esc(template)}</span>. ` : ''}출력의 result에 응답이 들어 있고, 실패하면 success가 false입니다.</div>` : `<pre class="code">${esc(text)}</pre>`}</div>`;
  }

  function repaintTry() {
    const box = document.querySelector('.trycode'), i = S.conn;
    if (!box || !i) return;
    box.outerHTML = tryCode(S.ctry, i);
  }

  function viewRules() {
    const r = S.ru;
    const head = pageHead('기준값 · 지표', '기준값 · 지표 산식 · 출처 충돌 · 결정표 점검 결과를 조회합니다.', '<a class="btn" href="#mgrules">규칙 수정</a>');
    if (!r) return `${head}<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>`;
    const empty = (t) => `<div class="muted" style="font-size:12.5px">${esc(t)}</div>`;
    const params = r.parameters.length ? `<table class="tight"><tr><th>이름</th><th>값</th><th>범위</th><th>변경 모듈</th></tr>${r.parameters.map((p) => `<tr><td><b>${esc(p.label)}</b><div class="muted mono cn">@${esc(p.name)}</div></td><td>${show(p.value)}${p.unit ? ` ${esc(p.unit)}` : ''}</td><td>${p.min === null && p.max === null ? '-' : `${p.min ?? ''} ~ ${p.max ?? ''}`}</td><td>${esc(p.touched.join(', ') || '-')}</td></tr>`).join('')}</table>` : empty('기준값이 없습니다. 모듈의 parameters에 정의합니다.');
    const metric = (m) => {
      const a = S.met[m.metric];
      return `<div class="hit"><div class="hit-top"><b>${esc(m.label || m.metric)}</b><span class="muted">${esc(m.owner || '')}</span><span style="margin-left:auto"></span><button class="btn sm" data-act="rmetric" data-name="${esc(m.metric)}">계산</button></div>
        <div class="muted" style="font-size:12.5px">${esc(m.description || m.formula)}${m.denominator ? ` · 분모 ${esc(m.denominator)}` : ''}${m.time_basis ? ` · 기준 ${esc(m.time_basis)}` : ''}</div>
        ${a ? `<div style="font-size:15px"><b>${show(a.value)}${esc(a.unit || '')}</b> <span class="muted" style="font-size:12.5px">${a.numerator !== null ? `${show(a.numerator)} / ${show(a.denominator)}` : ''}</span></div>${(a.notes || []).map((x) => `<div class="hint warn">${esc(x)}</div>`).join('')}` : ''}</div>`;
    };
    const metrics = r.metrics.length ? r.metrics.map(metric).join('') : empty('지표가 없습니다. 모듈의 metrics에 정의합니다.');
    const warn = r.findings.filter((f) => f.severity === 'warning'), info = r.findings.filter((f) => f.severity !== 'warning');
    const WORD = { gap: '누락 구간', overlap: '중복 조건', unreachable: '미적용 규칙', tie: '우선순위 동률', unchecked: '점검 불가' };
    const said = (f) => {
      const at = Object.entries(f.where || {}).map(([k, v]) => `${k} = ${v}`).join(', ');
      const names = (f.rules || []).join(', ');
      return { gap: `${at} 입력에 맞는 규칙이 없습니다.`, overlap: `${names} 규칙이 ${at} 입력에서 중복됩니다. 앞선 규칙을 적용합니다.`,
        unreachable: `${names} 규칙은 앞선 규칙에 가려 적용되지 않습니다.`, tie: `${names} 규칙의 우선순위가 같고 결과가 다릅니다.`,
        unchecked: '입력 조건을 자동으로 비교하지 못했습니다.' }[f.kind] || f.detail;
    };
    const tables = [...new Set(r.findings.map((f) => f.decision))];
    const KINDS = ['gap', 'unreachable', 'tie', 'overlap'];
    const cell = (list, k) => { const n = list.filter((f) => f.kind === k).length; return `<td>${n ? `<span class="chip sm ${k === 'overlap' ? '' : 'warn'}">${n}건</span>` : '<span class="muted">-</span>'}</td>`; };
    const table = (d) => {
      const list = r.findings.filter((f) => f.decision === d);
      const open = S.ruopen === d;
      const detail = open ? `<tr><td colspan="6"><div class="fdetail">${[...list].sort((a, b) => (a.severity === 'warning' ? 0 : 1) - (b.severity === 'warning' ? 0 : 1)).map((f) => `<div><span class="chip sm ${f.severity === 'warning' ? 'warn' : ''}">${esc(WORD[f.kind] || f.kind)}</span><span>${esc(said(f))}</span></div>`).join('')}</div></td></tr>` : '';
      return `<tr><td><b>${esc(list[0].label || d)}</b><div class="muted mono cn">${esc(d)}</div></td>${KINDS.map((k) => cell(list, k)).join('')}<td style="text-align:right"><button class="btn sm" data-act="ruopen" data-d="${esc(d)}" aria-expanded="${open}">${open ? '접기' : '보기'}</button></td></tr>${detail}`;
    };
    const findings = tables.length ? `<table class="tight"><tr><th>결정표</th>${KINDS.map((k) => `<th>${esc(WORD[k])}</th>`).join('')}<th></th></tr>${tables.map(table).join('')}</table>` : empty('점검 결과 이상이 없습니다.');
    const conflict = (c) => `<div class="hit" data-row="conflict:${esc(c.id)}"><div class="hit-top"><b>${esc(c.label || c.id)}</b><span class="chip sm ${c.status === 'open' ? 'warn' : 'ok'}">${c.status === 'open' ? '미결정' : `${esc(c.picked)} 선택`}</span></div>
      <table class="tight"><tr><th>출처</th><th>값</th><th></th></tr>${c.answers.map((x) => `<tr><td>${esc(x.source)}</td><td>${esc(x.says && typeof x.says === 'object' ? Object.values(x.says).map(show).join(', ') : show(x.says))}</td><td>${c.status === 'open' ? `<button class="btn sm" data-act="rpick" data-id="${esc(c.id)}" data-source="${esc(x.source)}">이 출처 선택</button>` : ''}</td></tr>`).join('')}</table></div>`;
    const conflicts = r.conflicts.length ? r.conflicts.map(conflict).join('') : empty('출처 충돌이 없습니다.');
    const due = r.due.length ? `<table class="tight"><tr><th>Entity</th><th>대상</th><th>전이</th></tr>${r.due.map((d) => `<tr><td>${esc(d.type)}</td><td class="mono">${esc(d.key)}</td><td>${esc(d.source)} → ${esc(d.target)}</td></tr>`).join('')}</table><button class="btn sm" data-act="radvance" style="margin-top:8px">기한 지난 전이 처리</button>` : empty('기한이 지난 전이가 없습니다.');
    return `${head}<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(420px,1fr));align-items:start">
      <div class="card"><div class="ch">기준값</div><div class="cb">${params}</div></div>
      <div class="card"><div class="ch">지표</div><div class="cb">${metrics}</div></div>
      <div class="card"><div class="ch">출처 충돌<div class="right"><span class="chip sm ${r.conflicts.some((c) => c.status === 'open') ? 'warn' : ''}">${r.conflicts.filter((c) => c.status === 'open').length}건 미결정</span></div></div><div class="cb">${conflicts}</div></div>
      <div class="card"><div class="ch">기한 전이</div><div class="cb">${due}</div></div>
      <div class="card" style="grid-column:1/-1"><div class="ch">결정표 점검<div class="right"><span class="chip sm ${warn.length ? 'warn' : 'ok'}">주의 ${warn.length}건</span></div></div><div class="cb">${findings}</div></div></div>`;
  }

  // ---- help where the work is: the steps of the screen on screen ---------------------------------------------------------------

  // ---- queries -------------------------------------------------------------------------------------------------

  // ---- a query put together without code: an object, a relation to follow, the values to show, conditions as chips --

  const QB_OPS = [['eq', '='], ['ne', '≠'], ['gt', '>'], ['gte', '≥'], ['lt', '<'], ['lte', '≤'], ['contains', '포함']];

  function qbProps(type) {  // an object's properties, read once
    const c = S.q.props;
    if (!type) return [];
    if (!c[type]) {
      c[type] = { busy: true, list: [] };
      api(`object?name=${encodeURIComponent(type)}`).then((o) => { c[type] = { list: o.properties.map((p) => ({ name: p.name, label: p.label, type: p.type })) }; if (S.tab === 'query') render(); }).catch(() => { c[type] = { list: [] }; });
    }
    return c[type].list;
  }

  function qbRelations(type) {
    return S.st.graph.edges.filter((e) => !e.subtype && (e.source === type || e.target === type))
      .map((e) => ({ name: e.id, label: e.label, other: e.source === type ? e.target : e.source, forward: e.source === type }));
  }

  function qbQuery() {  // what the builder says, as the query IR
    const b = S.q.b;
    const rel = qbRelations(b.type).find((r) => `${r.name}:${r.forward ? 1 : 0}` === b.link);
    const match = { x: b.type, ...(rel ? { y: rel.other } : {}) };
    const fields = b.fields.length ? b.fields : [`x.${(S.st.graph.nodes.find((n) => n.id === b.type) || {}).key}`];
    const conds = b.conds.filter((c) => c.prop && c.value !== '').map((c) => {
      const t = (qbProps(c.prop.split('.')[0] === 'y' && rel ? rel.other : b.type).find((p) => p.name === c.prop.split('.')[1]) || {}).type;
      const v = ['integer', 'decimal'].includes(t) && !Number.isNaN(Number(c.value)) ? Number(c.value) : (t === 'boolean' ? c.value === 'true' : c.value);
      return { [c.op]: [c.prop, v] };
    });
    return { match, ...(rel ? { edges: [rel.forward ? ['x', rel.name, 'y'] : ['y', rel.name, 'x']] } : {}),
      ...(conds.length ? { where: conds.length > 1 ? { and: conds } : conds[0] } : {}), return: fields, limit: 200 };
  }

  function pickQuery(name) {
    const sel = S.st.queries.find((x) => x.name === name);
    S.q.name = name;
    S.q.params = { ...(sel ? sel.example : {}) };
    runQuery();
  }

  async function principalDefaults(state) {
    const role = S.st.roles.find((r) => r.name === state.role);
    if (!role) return;
    for (const k of role.principal) {
      if (state.principal[k]) continue;
      const node = S.st.graph.nodes.find((n) => n.key === k && n.table);
      if (!node) continue;
      try {
        const { keys } = await api('keys?type=' + encodeURIComponent(node.id));
        if (keys.length) state.principal[k] = keys[0].key;
      } catch (_) { /* leave empty */ }
    }
  }

  async function runQuery() {
    const q = S.q;
    q.busy = true;
    if (S.tab === 'query') render();
    const ctx = { role: q.role, principal: q.principal };
    try {
      if (q.mode === 'text') q.res = await api('text', { language: q.lang, text: q.text, ...ctx });
      else if (q.mode === 'build') q.res = await api('text', { language: 'ir', text: JSON.stringify(qbQuery()), ...ctx });
      else if (q.mode === 'ask') q.res = await api('ask', { question: q.question, ...ctx });
      else if (q.name) q.res = await api('query', { name: q.name, params: q.params, ...ctx });
      if (q.mode !== 'text' && q.res && q.res.ok && !q.dirty) q.text = textFor(q.lang) || q.text;
    } catch (e) { q.res = { ok: false, error: e.message }; }
    q.busy = false;
    if (S.tab === 'query') render();
  }

  function textFor(lang) {
    const r = S.q.res;
    if (!r || !r.ok) return '';
    return (r.source || {})[lang] || '';
  }

  // ---- decisions and actions -----------------------------------------------------------------------------------

  async function keysFor(type) {
    if (!S.d.keys[type]) S.d.keys[type] = (await api('keys?type=' + encodeURIComponent(type))).keys;
    return S.d.keys[type];
  }

  async function startDecide() {
    const d = S.d, st = S.st;
    if (!st.decisions.some((x) => x.name === d.name)) {
      const q = st.questions.find((x) => x.decision);
      d.name = q ? q.decision : st.decisions[0].name;
      d.key = q ? q.key : null;
    }
    const dec = st.decisions.find((x) => x.name === d.name);
    d.busy = true;
    try {
      const keys = dec.target ? await keysFor(dec.target) : [];  // a decision on stated values alone reads no record
      if (!keys.some((k) => k.key === d.key)) d.key = keys.length ? keys[0].key : null;
    } catch (e) { d.busy = false; d.res = { error: e.message }; if (S.tab === 'decide') render(); return; }
    await decide();
  }

  async function decide() {
    const d = S.d;
    if (!d.name || !d.key) { d.busy = false; d.res = { error: '판정할 대상이 없습니다.' }; if (S.tab === 'decide') render(); return; }
    d.busy = true;
    try { d.res = await api('decide', { name: d.name, key: d.key }); } catch (e) { d.res = { error: e.message }; }
    d.busy = false;
    try { d.audit = (await api('audit')).audit; } catch (_) { d.audit = []; }
    if (S.tab === 'decide') render();
  }

  function viewDecide() {
    const st = S.st, d = S.d;
    if (!st.decisions.length) return '<div class="head"><div><h1>처리 요청</h1></div></div><div class="empty">적용된 모듈에 결정표가 없습니다.</div>';
    const dec = st.decisions.find((x) => x.name === d.name) || st.decisions[0];
    if (noSource()) {
      return `<div class="head"><div><h1>처리 요청</h1><div class="sub">결정표 판정 결과와 근거를 조회하고 처리를 요청합니다.</div></div></div>
        <div class="card nosrc"><div class="cb"><b>연결된 데이터 소스가 없습니다</b>
        <div class="chips">${st.decisions.map((x) => `<a class="btn sm${x.name === dec.name ? ' primary' : ''}" href="#mgrules?decision=${encodeURIComponent(x.name)}">${esc(x.label)} 판정하기</a>`).join('')}<a class="btn sm" href="#catalog">데이터 연결</a></div></div></div>`;
    }
    const keys = S.d.keys[dec.target] || [];
    const keyOpts = keys.map((k) => {
      const extra = Object.values(k.fields).filter((v) => v !== null && v !== '').map(plainText).join(' · ');
      return `<option value="${esc(k.key)}"${k.key === d.key ? ' selected' : ''}>${esc(k.key)}${extra ? ' · ' + esc(extra) : ''}</option>`;
    }).join('');
    const asked = st.questions.filter((x) => x.decision);  // three to pick from at a glance, the rest on request
    const qs = (d.allq ? asked : asked.slice(0, 3)).map((x) => `<button class="chip" data-act="ask-decision" data-name="${esc(x.decision)}" data-key="${esc(x.key)}">${esc(x.text)}</button>`).join('')
      + (asked.length > 3 ? `<button class="chip b" data-act="dallq" aria-expanded="${!!d.allq}">${d.allq ? '접기' : `외 ${asked.length - 3}개`}</button>` : '');
    const controls = `<div class="card"><div class="cb">
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:12px">
        <div class="field" style="margin:0"><label>결정</label><select data-in="decision">${st.decisions.map((x) => `<option value="${esc(x.name)}"${x.name === dec.name ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></div>
        <div class="field" style="margin:0"><label>대상 ${esc(dec.target_label)}</label><select data-in="key">${keyOpts}</select></div></div>
      ${qs ? `<div class="label" style="margin:12px 0 6px">검증 질문</div><div class="chips">${qs}</div>` : ''}</div></div>`;
    const r = d.res;
    let body = '';
    if (!r) body = '<div class="empty"><span class="spin"></span>판정 중입니다.</div>';
    else if (r.error) body = `<div class="banner no"><span class="ic x" style="width:26px;height:26px">!</span><div class="why">${esc(r.error)}</div></div>`;
    else body = decisionBody(r);
    return `
<div class="head"><div><h1>처리 요청</h1><div class="sub">결정표 판정 결과와 근거를 조회하고 처리를 요청합니다.</div></div>
  <div class="right">${r && !r.error ? `<a class="btn ghost" href="/api/export/jdm?decision=${encodeURIComponent(r.name)}" download>ZEN JDM 내려받기</a>` : ''}</div></div>
${controls}${body}`;
  }

  function decisionBody(r) {
    const matched = r.rules.filter((x) => x.hit);
    const cite = matched.map((x) => x.cite).filter(Boolean);
    const engines = r.engine === 'native' ? [] : [`<span class="chip">엔진 ${esc(r.engine)}</span>`];  // the built-in engine is not news
    if (r.zen) engines.push(r.zen.error ? `<span class="chip warn" title="${esc(r.zen.error)}">GoRules ZEN 실행 실패</span>` : (r.zen.same ? '<span class="chip ok">GoRules ZEN 판정 일치</span>' : '<span class="chip warn">GoRules ZEN 판정 불일치</span>'));
    const th = (n) => `<th>${esc(n)}</th>`;
    const head = '<th>규칙</th>' + r.inputs.map((i) => th(r.input_labels[i] || i)).join('') + r.outputs.map((o) => th(({ reason: '사유', eligible: '결과' })[o] || o)).join('');
    const rows = r.rules.map((x) => `<tr class="${x.hit ? 'hit' : ''}"><td class="mono" style="white-space:nowrap">${esc(x.id)} ${layerChip(x.layer)}${x.cite ? `<div class="muted cite-note">${esc(x.cite)}</div>` : ''}</td>
      ${r.inputs.map((i) => `<td style="white-space:nowrap">${esc(x.said[i])}</td>`).join('')}
      ${r.outputs.map((o) => `<td style="min-width:120px">${yesNo(x.then[o])}</td>`).join('')}</tr>`).join('');
    const ev = r.evidence.map((e) => `<div class="ev"><div><b>${esc(r.input_labels[e.input] || e.input)}</b><div class="muted" style="font-size:12px">${e.object ? `${esc(e.object_label)} ${esc(e.key)}${e.property_label ? ' · ' + esc(e.property_label) : ''}` : esc(e.source)}</div></div>
      <div><span class="chip b">${yesNo(e.value)}</span></div><div class="src mono muted" style="font-size:12px">${e.source && e.object ? '← ' + esc(e.source) : ''}</div></div>`).join('');
    const touched = r.touched.length ? `<div class="right muted" style="font-weight:600;font-size:12px">규칙 추가 모듈 ${esc(r.touched.join(', '))}</div>` : '';
    return `
<div class="banner ${r.yes ? 'ok' : 'no'}"><span class="ic ${r.yes ? 'y' : 'x'}" style="width:30px;height:30px;font-size:16px">${r.yes ? '✓' : '!'}</span>
  <div><div class="big">${esc(r.label)} · ${esc(r.verdict)}</div><div class="why">${esc(r.reason)}</div>${pathLine(r.path)}${(r.messages || []).map((m) => `<div class="cite">${esc(m.code)} · ${esc(m.text)}</div>`).join('')}${cite.length ? `<div class="cite">근거 규정 · ${esc(cite.join(', '))}</div>` : ''}</div>
  <div style="margin-left:auto" class="chips">${engines.join('')}${matched.map((x) => `<button class="chip b" data-act="rulego" data-dec="${esc(S.d.name || '')}" data-rule="${esc(x.id)}" title="결정표에서 이 규칙으로">규칙 ${esc(x.id)}</button>`).join('')}</div></div>
<div class="grid" style="grid-template-columns:minmax(0,1.45fr) minmax(360px,1fr);align-items:start">
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
    <div class="card"><div class="ch">결정표<span class="chip" title="${esc(r.hit_policy)}">${esc(HIT_WORD[r.hit_policy] || r.hit_policy)}</span>${touched}</div>
      <div class="cb scroll" style="padding:0"><table class="tight" style="font-size:12.5px"><tr>${head}</tr>${rows}</table></div></div>
    <div class="card"><div class="ch">근거 경로<div class="right muted" style="font-weight:600;font-size:12px">입력값별 소스 컬럼</div></div><div class="cb">${ev || '<div class="empty">소스 컬럼에서 읽은 입력값이 없습니다.</div>'}</div></div>
  </div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${pendingCard()}${actionCard(r)}${doneCard()}${agreementCard()}${auditCard()}</div>
</div>`;
  }

  function actionCard(r) {
    const a = S.st.actions.find((x) => r.actions.includes(x.name));
    if (!a) return '';
    const d = S.d, p = d.proposal && d.proposal.key === r.key && d.proposal.action === a.name ? d.proposal : null;
    const roles = S.st.roles;
    if (!d.role) d.role = (roles.find((x) => x.principal.length) || roles[0] || {}).name || '';
    const params = Object.keys(a.parameters).map((k) => `<div class="field"><label>${esc((a.parameters[k] || {}).label || k)}</label><input type="text" data-in="aparam" data-k="${esc(k)}" value="${esc(d.params[k] ?? '')}"></div>`).join('');
    let state = '';
    if (p) {
      const [cls, label] = STATUS[p.status] || ['', p.status];
      const checks = p.checks.map((c) => `<div class="check"><span class="ic ${c.passed ? 'y' : 'x'}">${c.passed ? '✓' : '!'}</span><b style="min-width:120px">${esc(c.title)}</b><span class="muted" style="font-size:12px;overflow-wrap:anywhere">${esc(c.detail)}</span></div>`).join('');
      const diff = Object.keys(p.changes).map((k) => `<div class="diff"><span class="mono">${esc(k)}</span><span class="chip">${show(p.before[k])}</span><span class="arrow">→</span><span class="chip ${p.status === 'executed' ? 'ok' : 'b'}">${show(p.changes[k])}</span></div>`).join('');
      const buttons = p.status === 'pending' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" style="flex:1" data-act="approve" data-id="${esc(p.id)}">승인</button><button class="btn" style="flex:1" data-act="reject" data-id="${esc(p.id)}">반려</button></div>`
        : p.status === 'stale' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn" style="flex:1" data-act="reject" data-id="${esc(p.id)}">반려로 종료</button></div>`
          : (p.can_roll_back ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn" style="flex:1" data-act="rollback" data-id="${esc(p.id)}">되돌리기</button></div>` : '');
      const limits = (p.limits || []).length ? `<div class="hint" style="margin-top:8px">${p.approved_by === 'auto' ? '자동 승인 기준을 충족해 바로 실행했습니다.' : waitWord(p)} ${p.limits.map((l) => `${esc(p.labels[l.subject] || l.subject)} ${esc(({ percent: '변화율', delta: '변화폭', max: '값', min: '값' })[l.kind])} ${l.value === null ? '-' : show(Math.round(l.value * 100) / 100)}${l.kind === 'percent' ? '%' : ''} / 기준 ${show(l.limit)}${l.kind === 'percent' ? '%' : ''}`).join(' · ')}</div>` : '';
      const call = p.call && (p.call.status || p.call.error) ? `<div class="hint" style="margin-top:8px">외부 호출 ${p.call.error ? esc(p.call.error) : `${esc(p.call.method)} ${esc(p.call.url)} · ${esc(p.call.status)}`}</div>` : '';
      const done = (p.status === 'executed' ? '<div class="hint" style="margin-top:10px">데이터 소스와 그래프 저장소에 반영했습니다.</div>'
        : (p.status === 'rolled_back' ? `<div class="hint" style="margin-top:10px">${esc(p.rolled_back_by)} 님이 실행 전 값으로 되돌렸습니다.</div>` : '')) + call;
      state = `<div class="sec" style="display:flex;align-items:center;gap:8px">요청 ${esc(p.id)} · ${esc(p.requested_by)}<span class="chip ${cls}" style="margin-left:auto">${label}</span></div>${checks}${diff ? `<div class="sec">변경 값</div>${diff}` : ''}${buttons}${done}`;
    }
    return `<div class="card"><div class="ch">${esc(a.label)} <span class="muted mono cn" style="font-weight:600">${esc(a.name)}</span></div><div class="cb">
      
      <div class="field"><label>요청 역할</label><select data-in="arole">${roles.map((x) => `<option value="${esc(x.name)}"${x.name === d.role ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></div>
      <div class="field"><label>요청자</label><select data-in="akind">${[['agent', 'Agent'], ['human', '사람']].map(([k, l]) => `<option value="${k}"${(d.kind || 'agent') === k ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
      ${params}<button class="btn primary" style="width:100%" data-act="request" data-action="${esc(a.name)}">${esc(r.target_label)} ${esc(r.key)} ${esc(a.label)} 요청</button>
      ${state}</div></div>`;
  }

  async function loadPending() {
    S.pa = { pending: [] };
    try { S.pa = await api('actions/pending'); } catch (e) { S.pa = { pending: [] }; }
    if (S.tab === 'decide') render();
  }

  function pendingCard() {
    const mine = S.d.proposal ? S.d.proposal.id : '';
    const list = ((S.pa || {}).pending || []).filter((p) => p.id !== mine);
    if (!list.length) return '';
    const row = (p) => `<div class="hit"><div class="hit-top"><b>${esc(p.target_label)} ${esc(p.key)} ${esc(p.label)}</b><span style="margin-left:auto"></span><span class="muted" style="font-size:12px">요청 ${esc(p.id)} · ${esc(p.requested_by)}${p.requested_kind === 'agent' && !/agent/i.test(p.requested_by) ? ' · Agent' : ''}</span></div>
      <div class="muted" style="font-size:12.5px">${Object.entries(p.params).map(([k, v]) => `${esc(p.labels[k] || k)} ${show(v)}`).join(' · ') || '요청 값 없음'}</div>
      ${Object.keys(p.changes).length ? `<div class="muted" style="font-size:12.5px">${Object.keys(p.changes).map((k) => `${esc(p.labels[k] || k)} ${show(p.before[k])} → ${show(p.changes[k])}`).join(' · ')}</div>` : ''}
      <div style="display:flex;gap:8px;margin-top:8px"><button class="btn sm primary" data-act="approve" data-id="${esc(p.id)}">승인</button><button class="btn sm" data-act="reject" data-id="${esc(p.id)}">반려</button></div></div>`;
    return `<div class="card"><div class="ch">승인 대기 요청<div class="right"><span class="chip sm warn">${list.length}건</span></div></div><div class="cb">${list.map(row).join('')}</div></div>`;
  }

  function doneCard() {
    const mine = S.d.proposal ? S.d.proposal.id : '';
    const list = ((S.pa || {}).done || []).filter((p) => p.id !== mine);
    if (!list.length) return '';
    const row = (p) => {
      const [cls, word] = STATUS[p.status] || ['', p.status];
      return `<div class="hit"><div class="hit-top"><b>${esc(p.target_label)} ${esc(p.key)} ${esc(p.label)}</b><span style="margin-left:auto"></span><span class="chip sm ${cls}">${esc(word)}</span></div>
      ${Object.keys(p.changes).length ? `<div class="muted" style="font-size:12.5px">${Object.keys(p.changes).map((k) => `${esc(p.labels[k] || k)} ${show(p.before[k])} → ${show(p.changes[k])}`).join(' · ')}</div>` : ''}
      <div class="muted" style="font-size:12px">요청 ${esc(p.id)} · ${esc(p.requested_by)}${p.approved_by ? ` · 승인 ${p.approved_by === 'auto' ? '자동 승인 기준' : esc(p.approved_by)}` : ''}</div>
      ${p.can_roll_back ? `<div style="display:flex;gap:8px;margin-top:8px"><button class="btn sm" data-act="rollback" data-id="${esc(p.id)}">되돌리기</button></div>` : ''}</div>`;
    };
    return `<div class="card"><div class="ch">실행한 요청<div class="right"><span class="chip sm">${list.length}건</span></div></div><div class="cb">${list.map(row).join('')}<div class="hint xp">실행 뒤 다른 변경이 없으면 실행 전 값으로 되돌릴 수 있습니다.</div></div></div>`;
  }

  async function loadAgreement() {  // on 규칙 the past cases are decided by the tables as the pending edits leave them
    S.agree = { busy: true };
    try { S.agree = await api(S.tab === 'mgrules' ? 'agreement?pending=1' : 'agreement'); } catch (e) { S.agree = { ok: false, error: e.message }; }
    if (S.tab === 'decide' || S.tab === 'mgrules') render();
  }

  function agreementCard() {
    const a = S.agree;
    if (!a || a.busy) return '';
    if (!a.ok) return `<div class="card"><div class="ch">판정 일치율</div><div class="cb"><div class="hint">${esc(a.error)}</div></div></div>`;
    const conf = Object.entries(a.confusion || {}).map(([out, cells]) => `<div class="label" style="margin:8px 0 4px">${esc(out)} · 실제 → 판정</div><div class="chips">${Object.entries(cells).map(([k, n]) => `<span class="chip sm${k.split(' → ')[0] === k.split(' → ')[1] ? ' ok' : ' warn'}">${esc(k.replace(/\bTrue\b/g, '예').replace(/\bFalse\b/g, '아니요').replace(/\bNone\b/g, '값 없음'))} · ${n}건</span>`).join('')}</div>`).join('');
    return `<div class="card"><div class="ch">판정 일치율 · ${esc(a.label)}<div class="right"><span class="chip ${a.rate === 1 ? 'ok' : 'warn'}">${pct(a.rate)}</span></div></div><div class="cb">
      <div class="muted" style="font-size:12.5px;line-height:1.55">과거 처리 ${a.cases}건 중 ${a.agree}건 일치</div>
      ${conf}${a.mismatches.length ? `<div class="label" style="margin:10px 0 4px">다른 건</div>${mismatchRows(a.mismatches)}` : ''}</div></div>`;
  }

  function auditCard() {
    const a = S.d.audit;
    if (!a.length) return '';
    const rules = (x) => ((x.detail || {}).rules || []).join(', ');
    return `<div class="card"><div class="ch">감사 로그</div><div class="cb log">${a.slice(0, 10).map((x) => `<div title="${esc(`버전 ${(x.versions || []).join(', ')}${rules(x) ? ` · 규칙 ${rules(x)}` : ''}`)}"><span class="muted">${esc(x.event)}</span><span>${esc(x.actor)} · ${esc(x.key)}</span><span class="muted mono">${esc(x.proposal)}</span></div>`).join('')}</div></div>`;
  }

  async function requestAction(action) {
    const d = S.d;
    const a = S.st.actions.find((x) => x.name === action);
    const params = {};
    for (const k of Object.keys(a.parameters)) params[k] = d.params[k] ?? '';
    const empty = Object.entries(a.parameters).filter(([k, spec]) => (spec || {}).required !== false && String(params[k]).trim() === '');
    if (empty.length) { toast(`${empty.map(([k, spec]) => (spec || {}).label || k).join(', ')} 값이 없어 요청하지 못했습니다. 값을 입력해 주세요.`, true); return; }
    try {
      const r = await api('request', { action, key: d.key, params, role: d.role, kind: d.kind || 'agent' });
      d.proposal = r.proposal; S.pa = null;
      d.audit = (await api('audit')).audit;
      render();
      const said = { pending: '검사를 통과했습니다. 승인 대기 중입니다.', executed: '자동 승인 기준을 충족해 바로 실행했습니다.' }[r.proposal.status];
      toast(said || '검사를 통과하지 못해 요청이 반려되었습니다. 검사 결과를 확인해 주세요.', !said);
    } catch (e) { fail(e); }
  }

  async function approve(id, yes) {
    try {
      const r = await api('approve', { id, approve: yes });
      if (!r.ok) throw new Error(r.error);
      S.d.proposal = r.proposal; S.pa = null;
      S.q.res = null; S.qa = null; S.bind = null; S.fl = null; S.d.keys = {};
      await load();
      await startDecide();
      toast(yes ? 'Action 요청을 승인했습니다.' : 'Action 요청을 반려했습니다.');
    } catch (e) { fail(e); }
  }

  // what an approval made, in the product's version words (버전 2), read once the change has landed
  async function deployedWord() {
    try { const v = await api('versions'); return (v.current && v.current.label) || ''; } catch (e) { return ''; }
  }

  async function decideChange(id, yes) {
    try {
      const r = await api('change/decide', { id, approve: yes });
      if (r.change) S.change = r.change;
      if (!r.ok) throw new Error(r.error);
      S.changes = null; S.impact = null; S.agree = null;
      stale();
      if (yes && S.ed && S.ed.name === r.change.module) await openModule(r.change.module).catch(() => {});
      S.change = r.change;
      await load();
      if (S.fix && yes) await fixRecheck(false);
      const made = yes ? await deployedWord() : '';
      toast(!yes ? '변경 요청을 반려했습니다.' : made ? `${made}${josa(made, '을', '를')} 배포했습니다.` : '변경 요청을 승인했습니다.');
    } catch (e) { render(); fail(e); }
  }

  function identityPanel(name) {
    const v = S.ident && S.ident.identities ? S.ident.identities.find((x) => x.name === name) : null;
    if (!S.ident) { loadIdentities(); return '<div class="sec">식별 통합</div><div class="muted"><span class="spin"></span>불러오는 중입니다.</div>'; }
    if (!v) return '';
    if (v.error) return `<div class="sec">식별 통합</div><div class="muted">${esc(v.error)}</div>`;
    const rules = v.rules.map((r) => `<span class="chip sm">${esc(r.id)} · ${esc(r.match.join(' + '))}</span>`).join('');
    const clusters = v.clusters.map((c) => `<tr><td class="mono">${esc(c.id)}</td><td>${c.members.map((m) => `<span class="chip sm">${esc(m)}</span>`).join(' ')}</td>
      <td class="muted" style="font-size:12px">${c.evidence.map((e) => `${esc(e.rule)}: ${esc(e.value)}`).join('<br>')}</td></tr>`).join('');
    return `<div class="sec">식별 통합 · 구성원 ${esc(v.members.map((m) => m.label).join(', '))}</div><div class="chips">${rules}</div>
      <div class="muted" style="font-size:12.5px;margin:6px 0">기록 ${v.records}건 · 통합 ${v.identities}건 · 둘 이상 통합된 건 ${v.joined}${v.findings ? ` · 확인 필요 ${v.findings}` : ''}</div>
      ${clusters ? `<table class="tight"><tr><th>통합 번호</th><th>구성원</th><th>근거</th></tr>${clusters}</table>` : ''}
      <button class="btn sm" data-act="iresolve" data-name="${esc(name)}" style="margin-top:8px">재통합 후 교차표 저장</button>`;
  }

  async function loadIdentities() {
    S.ident = { busy: true };
    try { S.ident = await api('identities'); } catch (e) { S.ident = { identities: [] }; }
    const box = $('#objdetail');
    if (box && S.obj) box.innerHTML = objDetail(S.obj);
  }

  // ---- checks --------------------------------------------------------------------------------------------------

  async function runChecks() {
    S.qa = { busy: true };
    if (S.tab === 'check') render();
    try { S.qa = await api('questions', {}); } catch (e) { S.qa = { error: e.message }; }
    try { S.val = await api('values'); } catch (e) { S.val = { ok: false, configured: true, error: e.message }; }
    if (S.tab === 'check') render();
  }

  // ---- bindings ------------------------------------------------------------------------------------------------

  async function runBindings() {
    S.bind = { busy: true };
    if (S.tab === 'bind') render();
    try { S.bind = await api('bindings', {}); } catch (e) { S.bind = { error: e.message }; }
    if (S.tab === 'bind') render();
    if (!S.bind.error) toast(`다시 대조했습니다.${Array.isArray(S.bind.findings) ? ` 지적 ${S.bind.findings.length}건` : ''}`);  // the same result as before is still an answer
  }

  // ---- guide: the demo video beside the manual, each pointing at the other -------------------------------------

  const bytes = (n) => (n >= 1 << 20 && n % (1 << 20) === 0 ? `${n >> 20}MB` : `${(n >> 10).toLocaleString('ko-KR')}KB`);
  const clock = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  const navLabel = (tab) => (NAV.find((x) => x[0] === tab) || [tab, tab])[1];

  function mountGuide() {
    const v = $('#gvideo');
    const g = S.guide;
    if (!v || !g) return;
    const mark = () => {
      let i = -1;
      g.chapters.forEach((c, k) => { if (v.currentTime + 0.05 >= c.t) i = k; });
      const tab = i >= 0 ? g.chapters[i].tab : '';
      document.querySelectorAll('.gch').forEach((b) => b.classList.toggle('on', Number(b.dataset.i) === i));
      document.querySelectorAll('.gsec').forEach((x) => x.classList.toggle('on', x.dataset.gtab === tab));
    };
    v.addEventListener('timeupdate', mark);
    v.addEventListener('seeked', mark);
  }

  // ---- flow: every stage of this studio, with what it holds now -------------------------------------------------

  async function loadFlow() {
    S.fl = { busy: true };
    try { S.fl = await api('flow'); S.fl.at = new Date().toTimeString().slice(0, 5); } catch (e) { S.fl = { error: e.message }; }
    if (S.tab === 'flow') render();
  }

  async function loadFlowSettings() {
    S.flset = { busy: true };
    try { S.flset = await api('flow/settings'); S.flset.read = JSON.parse(JSON.stringify(S.flset.settings)); } catch (e) { S.flset = { error: e.message }; }  // as read, beside the copy the form edits
    if (S.tab === 'flow') render();
  }

  // ---- data in: files or a database, drafted step by step, reviewed, plugged in ------------------------------------

  async function loadFiles() {
    S.files = { busy: true };
    try { S.files = await api('files'); } catch (e) { S.files = { error: e.message }; }
    if (!S.dr.rules && S.files.rules) S.dr.rules = JSON.parse(JSON.stringify(S.files.rules));
    drRestore();
    if (S.tab === 'data' || S.tab === 'library') render();
  }
  // a reload opens a draft's review where it was left: the server keeps what the page last sent of it
  function drRestore() {
    const r = S.files && S.files.pending && S.files.pending.review;
    if (!r || S.dr.restored) return;
    S.dr.restored = true;
    const e = r.edits || {};
    if (Object.keys(e).length) S.dr.ed = { drop: Object.fromEntries((e.drop || []).map((k) => [k, true])), labels: e.labels || {}, keys: e.keys || {}, types: e.types || {}, values: e.values || {}, card: e.cardinality || {}, add: e.add_links || [] };
    Object.assign(S.dr.choice, r.choices || {});
    if (Array.isArray(r.standard) && r.standard.length && !S.map.picked.length) S.map.picked = [...r.standard];
  }
  async function refreshFiles() {  // in a team the draft is shared: what another person filed, applied or dropped shows on coming back
    if (!S.files || S.files.busy) return;
    try {
      const f = await api('files');
      if (JSON.stringify(f.request || null) === JSON.stringify(S.files.request || null) && !!f.pending === !!S.files.pending) return;
      S.files = f;
      if (S.tab === 'data') render();
    } catch (e) { /* the page keeps what it has */ }
  }

  async function filesCall(path, body, done) {
    S.dr.busy = true;
    if (S.tab === 'data') render();
    try {
      S.files = await api(path, body);
      S.st = await api('state');
      if (done) done();
    } catch (e) { fail(e); }
    S.dr.busy = false;
    render();
  }

  const NEW_EDITS = () => ({ drop: {}, labels: {}, keys: {}, types: {}, values: {}, card: {}, add: [] });
  const RULE_NUM = [['enum_max', '허용값 최대 종류 수'], ['enum_repeat', '최소 평균 반복 횟수'], ['text_max', '허용값 최대 길이']];
  const RULE_HINT = { enum_max: '값의 종류가 이 수 이하인 컬럼을 허용값(코드) 후보로 봅니다.', enum_repeat: '값 하나가 평균 이 횟수 이상 반복되는 컬럼을 허용값으로 봅니다.',
    text_max: '이 길이보다 긴 값이 있는 컬럼은 허용값으로 보지 않습니다.', title_hints: 'Entity를 대표하는 이름으로 쓸 컬럼입니다.', parent_hints: '이 접두어로 시작하는 키는 상위 Entity로 연결합니다.',
    key_suffixes: '이 접미어로 끝나는 컬럼을 키 후보로 봅니다.', generic_keys: '여러 테이블에 같은 이름으로 있어 관계 추론에서 빼는 키입니다.', state_hints: '이 이름의 컬럼을 상태 전이로 만듭니다.',
    person_hints: '이 이름의 테이블을 사람(회원, 고객)으로 보고, 본인 행만 조회하는 역할을 만듭니다.', table_prefixes: '테이블 이름에서 이 접두어를 빼고 Entity 이름을 만듭니다.' };
  const RULE_FLAG = [['infer_links', '이름과 값으로 관계 추론'], ['link_tables', '중간 테이블을 다대다 관계로 변환'], ['row_keys', '키 없는 테이블에 행 번호 추가'],
    ['states', '상태 컬럼을 상태 전이로'], ['roles', '역할 생성'], ['questions', '검증 질문 생성']];
  const RULE_QUERY = [['list', 'Entity 목록'], ['count_by', '관계별 집계'], ['values', '허용값별 집계']];
  const RULE_LIST = [['title_hints', '표시 이름 컬럼'], ['parent_hints', '상위 관계 접두어'], ['key_suffixes', '키 컬럼 접미어'], ['generic_keys', '공용 키 이름'],
    ['state_hints', '상태 컬럼 이름'], ['person_hints', '본인 조회 기준 테이블 이름'], ['table_prefixes', 'Entity 이름에서 뺄 테이블 접두어']];
  const TYPES = ['string', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'enum'];

  function refreshDraft() {
    const box = $('#draft');
    if (box) { box.innerHTML = draftBody(); mountDraftGraph(); }
  }

  function startDraft() {
    clearInterval(S.dr.timer);
    Object.assign(S.dr, { step: 99, view: 'objects', sel: null, ed: NEW_EDITS(), rev: null, graph: null, add: { source: '', property: '', target: '', label: '' },
      choice: {}, names: {}, ok: {}, seen: {}, tbl: {}, pick: '', setup: false, rv: 'plan', plan: null });
    S.dpos = {}; S.dr.timer = 0;
    S.map.auto = ''; S.map.sug = null;
    if (S.tab === 'data') render();
    requestAnimationFrame(() => { const box = $('#draft'); if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  }

  // ---- edits: kept on the page, checked on the server after each change ----

  function toEdits() {
    const e = S.dr.ed;
    const p = S.files && S.files.pending, names = {};
    if (p) {
      for (const x of p.steps.find((st) => st.id === 'objects').items) {
        const r = objProposal(p, x);
        if (r.choice !== 'standard' && r.api && r.api !== r.id) names[r.id] = r.api;
      }
    }
    return { drop: Object.keys(e.drop).filter((k) => e.drop[k]), labels: e.labels, keys: e.keys, types: e.types,
      values: e.values, cardinality: e.card, add_links: e.add, names };
  }

  let previewTimer = 0;
  function edited() {
    refreshDraft();
    clearTimeout(previewTimer);
    previewTimer = setTimeout(preview, 150);
  }

  async function preview() {
    if (!S.files || !S.files.pending) return;
    try { S.dr.rev = await api('draft/preview', { edits: toEdits() }); } catch (e) { S.dr.rev = { ok: false, issues: [e.message] }; }
    if (S.dr.rev.graph) S.dr.graph = S.dr.rev.graph;
    const detail = $('#ddetail');
    if (detail && ['review', 'queries'].includes(reviewStep())) detail.innerHTML = reviewMain(S.files.pending, reviewStep());
    mountDraftGraph();
  }

  const stepIndex = (id) => ((S.files && S.files.pending) ? S.files.pending.steps.findIndex((x) => x.id === id) : -1);

  function draftShown(kind, x) {
    if (kind === 'node') return S.dr.step < stepIndex('objects') ? 0 : 1;
    if (x.subtype) return 1;
    return S.dr.step < stepIndex('links') ? 0 : 1;
  }

  function mountDraftGraph() {
    const p = S.files && S.files.pending;
    if (!p) return;
    mountGraph($('#dgraph'), S.dr.graph || p.graph, { key: 'draft', pos: S.dpos, sel: () => S.dr.sel, shown: draftShown,
      clear: () => { S.dr.sel = null; },
      label: (n) => S.dr.ed.labels['object:' + n.id] || n.label,
      pick: (id) => { S.dr.sel = S.dr.sel === id ? null : id; S.dr.view = 'properties'; S.dr.step = Math.max(S.dr.step, stepIndex('properties') + 1); refreshDraft(); } });
  }

  function why(o, kind, x) {
    const files = (o.origin || {}).kind === 'files';
    if (kind === 'object') return { primary_key: '선언된 기본키', unique: `${show(x.rows)}행 · 값 중복 없음`, row_number: '키 컬럼 없음 · 행 번호 추가' }[x.why] || x.why;
    if (kind === 'link') {
      if (x.via) return `중간 테이블 <span class="mono">${esc(x.via)}</span> · 다대다`;
      return x.why === 'foreign_key' ? '선언된 외래키' : `<span class="mono">${esc(x.column)}</span> 값 ${show(x.values)}개가 ${esc(o.labelOf(x.to))} 키와 일치`;
    }
    if (x.type === 'enum') return `허용값 ${x.distinct}종`;
    const filled = x.rows - x.nulls;
    const base = files ? (filled ? `값 ${show(filled)}개 · ${TYPE_WORD[x.type]} 형식` : '값 없음 · 문자열') : `선언 타입 ${esc(x.declared || '-')}`;
    return base + (x.nulls ? ` · 빈 값 ${show(x.nulls)}` : '') + (x.title ? ' · 표시 이름' : '');
  }

  function draftContext(p) {
    const nodes = p.graph.nodes;
    const e = S.dr.ed;
    const props = p.steps.find((x) => x.id === 'properties').items;
    const objects = p.steps.find((x) => x.id === 'objects').items.map((x) => x.element.split(':')[1]);
    const keyOf = (obj) => e.keys[obj] || (p.steps[1].items.find((x) => x.element === 'object:' + obj) || {}).key;
    const propsOf = (obj) => props.filter((x) => x.object === obj && !e.drop[x.element]).map((x) => x.element.split('.').pop());
    return { origin: p.origin, objects, keyOf, propsOf, live: objects.filter((x) => !e.drop['object:' + x]),
      labelOf: (id) => e.labels['object:' + id] || ((nodes.find((n) => n.id === id) || {}).label || id) };
  }

  const labelInput = (el, value) => `<input type="text" class="inline" data-in="dlab" data-el="${esc(el)}" value="${esc(S.dr.ed.labels[el] ?? value)}">`;
  const options = (items, cur) => items.map(([v, l]) => `<option value="${esc(v)}"${v === cur ? ' selected' : ''}>${esc(l)}</option>`).join('');

  function okCell(x, asks, word) {  // a proposal a person adopts, or one that needed nobody
    if (S.dr.ed.drop[x.element]) return '<span class="muted">제외</span>';
    if (!asks || S.dr.ok[x.element]) return '<span class="rvok">채택</span>';
    return `<button class="btn sm" data-act="dok" data-el="${esc(x.element)}" title="${esc(word)}">확인 · 채택</button>`;
  }

  function stepDetail(p, st) {
    const o = draftContext(p);
    const e = S.dr.ed;
    if (st.id === 'read') {
      return `<table class="tight"><tr><th>파일</th><th>테이블</th><th>행</th><th>컬럼</th><th></th></tr>${st.items.map((x) => `<tr><td>${esc(x.source || '-')}</td><td class="mono">${esc(x.table)}</td><td class="num">${show(x.rows)}</td><td class="num">${x.columns}</td>
        <td class="muted" style="font-size:12px">${x.truncated ? '행 한도까지 읽음 · ' : ''}${x.row_key ? `키 컬럼 없음 · <span class="mono">${esc(x.row_key)}</span> 추가` : ''}</td></tr>`).join('')}</table>`;
    }
    if (st.id === 'properties') {
      const items = st.items.filter((x) => !S.dr.sel || x.object === S.dr.sel);
      const rows = items.map((x) => {
        const ref = x.element.slice('property:'.length);
        const isKey = o.keyOf(x.object) === ref.split('.').pop();
        const on = !e.drop[x.element];
        const type = e.types[ref] || x.type;
        const vals = e.values[ref] ?? x.values.join(', ');
        const objOff = e.drop['object:' + x.object];
        return `<tr class="${on && !objOff ? '' : 'off'}"><td style="width:28px"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''}${isKey ? ' disabled' : ''} aria-label="${esc(x.label)} 포함"></td>
          <td>${labelInput(x.element, x.label)}<div class="muted mono">${esc(ref.split('.').pop())}</div></td>
          <td class="mono">${esc(o.labelOf(x.object))}.${esc(x.column)}</td>
          <td><select class="inline" data-in="dtype" data-ref="${esc(ref)}">${options(TYPES.map((t) => [t, t]), type)}</select>
            ${type === 'enum' ? `<input type="text" class="inline wide" data-in="dvalues" data-ref="${esc(ref)}" value="${esc(vals)}" placeholder="허용값, 쉼표로 구분">` : ''}</td>
          <td class="muted" style="font-size:12px">${isKey ? '키' : (e.types[ref] && e.types[ref] !== x.type ? '직접 지정' : why(o, 'property', x))}</td>
          <td>${okCell(x, x.type === 'enum' && !isKey, '허용값 추정')}</td></tr>`;
      }).join('');
      const filter = S.dr.sel ? `<div class="hint" style="margin-bottom:8px">${esc(o.labelOf(S.dr.sel))} 속성만 표시합니다. <button class="chip sm" data-act="dsel">전체 보기</button></div>` : '';
      return `${filter}<table class="tight"><tr><th></th><th>Property</th><th>소스 컬럼</th><th>타입</th><th>근거</th><th>상태</th></tr>${rows}</table>`;
    }
    if (st.id === 'links') {
      const card = (cur, name, fixed) => `<select class="inline" data-in="dcard" data-link="${esc(name)}"${fixed ? ' disabled' : ''}>${options(Object.entries(CARD), cur)}</select>`;
      const rows = st.items.map((x) => {
        const name = x.element.split(':')[1];
        const on = !e.drop[x.element];
        return `<tr class="${on ? '' : 'off'}"><td style="width:28px"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''} aria-label="${esc(x.label)} 포함"></td>
          <td>${labelInput(x.element, x.label)}<div class="muted">${esc(o.labelOf(x.from))} → ${esc(o.labelOf(x.to))} <span class="mono">${esc(name)}</span></div></td>
          <td>${card(e.card[name] || x.cardinality, name, !!x.via)}</td><td class="muted" style="font-size:12px">${why(o, 'link', x)}</td>
          <td>${okCell(x, x.why !== 'foreign_key' && !x.via, '값으로 추론')}</td></tr>`;
      }).join('');
      const added = e.add.map((a, i) => `<tr><td></td><td><b>${esc(a.label || o.labelOf(a.target))}</b><div class="muted">${esc(o.labelOf(a.source))}.${esc(a.property)} → ${esc(o.labelOf(a.target))}</div></td>
        <td>${esc(CARD[a.cardinality] || a.cardinality)}</td><td class="muted" style="font-size:12px">직접 추가 <button class="chip sm" data-act="dadddel" data-i="${i}">삭제</button></td></tr>`).join('');
      const a = S.dr.add;
      const src = o.live.includes(a.source) ? a.source : (o.live[0] || '');
      const prop = o.propsOf(src).includes(a.property) ? a.property : (o.propsOf(src)[0] || '');
      const tgt = o.live.includes(a.target) ? a.target : (o.live.find((x) => x !== src) || src);
      const form = `<div class="sec">관계 추가</div><div class="addlink">
        <select data-in="dasrc">${options(o.live.map((x) => [x, o.labelOf(x)]), src)}</select>
        <select data-in="daprop">${options(o.propsOf(src).map((x) => [x, x]), prop)}</select><span class="muted">→</span>
        <select data-in="datgt">${options(o.live.map((x) => [x, o.labelOf(x)]), tgt)}</select>
        <select data-in="dacard">${options(Object.entries(CARD).filter(([k]) => k !== 'many_to_many'), a.cardinality || 'many_to_one')}</select>
        <input type="text" data-in="dalabel" value="${esc(a.label)}" placeholder="관계 이름">
        <button class="btn sm" data-act="dadd"${src && prop && tgt ? '' : ' disabled'}>추가</button></div>
        <div class="hint xp" style="margin-top:6px">선택한 속성 값을 대상 Entity의 키와 연결합니다.</div>`;
      const table = rows || added ? `<table class="tight"><tr><th></th><th>Relation</th><th>Cardinality</th><th>근거</th></tr>${rows}${added}</table>` : '<div class="empty">추론된 관계가 없습니다.</div>';
      return table + form;
    }
    if (st.id === 'queries') {
      const items = (S.dr.rev && S.dr.rev.query_items) || st.items;
      if (!items.length) return '<div class="empty">생성할 질의가 없습니다.</div>';
      return `<div class="qpick">${items.map((x) => {
        const on = !e.drop[x.element];
        return `<label class="${on ? '' : 'off'}"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''}><span>${esc(x.label)}</span><span class="muted mono">${esc(x.element.split(':')[1])}</span></label>`;
      }).join('')}</div>`;
    }
    if (st.id === 'rules') return rulesDetail(p, st, o);
    if (st.id === 'yaml') {
      const mods = (S.dr.rev && S.dr.rev.modules) || p.modules;
      return mods.map((m) => `<div class="sec">${esc(m.label)} <span class="muted mono">${esc(m.name)}</span></div><pre class="code" style="max-height:360px;overflow:auto">${esc(m.yaml)}</pre>`).join('');
    }
    return `<table class="tight"><tr><th>항목</th><th>데이터 소스</th></tr>${st.items.map((x) => `<tr><td>${element(x.element)}</td><td class="mono">${esc(x.table || x.column || '')}${x.table && x.column ? ' · ' + esc(x.column) : ''}${x.columns ? ` · 컬럼 ${x.columns}` : ''}</td></tr>`).join('')}</table>`;
  }

  function rulesDetail(p, st, o) {
    const by = (kind) => st.items.filter((x) => x.kind === kind);
    const sm = by('states').map((s) => `<tr><td><b>${esc(o.labelOf(s.object))}</b><div class="muted mono cn">${esc(s.property)}</div></td>
      <td>${s.transitions.length ? s.transitions.map((t) => `<span class="chip sm">${esc(t.from)} → ${esc(t.to)} · ${t.seen}회</span>`).join(' ') : `<span class="muted">${esc(s.states.join(' · '))}</span>`}</td>
      <td class="muted" style="font-size:12px">${s.why === 'history' ? `이력 테이블 <span class="mono">${esc(s.history)}</span> 의 시간 순서${s.initial ? ` · 초기 상태 ${esc(s.initial)}` : ''}` : '허용값만 확인 · 전이는 직접 지정'}</td></tr>`).join('');
    const acts = by('action').map((a) => `<span class="chip">${esc(a.label)}</span>`).join('');
    const roles = by('role').map((r) => `<tr><td><b>${esc(r.label)}</b></td><td class="muted" style="font-size:12px">조회 ${esc(r.read.join(', '))}${r.filters.length ? ` · 본인 행만: ${esc(r.filters.join(', '))}` : ''}</td></tr>`).join('');
    const qs = by('question').map((q) => `<div>${esc(q.text)} <span class="muted">${showObj(q.expect)}</span></div>`).join('');
    const decs = by('decision').map((x) => {
      const r = x.report || {};
      return `<tr><td><b>${esc(x.label)}</b><div class="muted mono cn">${esc(x.element.split(':')[1])}</div></td><td class="muted" style="font-size:12px">규칙 ${x.rules}개 · 지난 ${r.cases}건 · 맞춤 ${pct(r.accuracy)} · 교차 검증 ${r.cross_validated === null || r.cross_validated === undefined ? '건수 부족' : pct(r.cross_validated)}</td>
        <td><button class="chip sm" data-act="dinddel" data-name="${esc(x.element.split(':')[1])}">삭제</button></td></tr>`;
    }).join('');
    const props = p.steps.find((x) => x.id === 'properties').items.filter((x) => !S.dr.ed.drop[x.element]);
    const outs = props.filter((x) => ['enum', 'boolean', 'string'].includes(S.dr.ed.types[x.element.slice(9)] || x.type) && !x.key);
    const t = S.ind.target && outs.some((x) => x.element === S.ind.target) ? S.ind.target : '';
    let inputs = '';
    if (t) {
      const obj = t.slice(9).split('.')[0];
      const fits = (x) => !['date', 'datetime'].includes(S.dr.ed.types[x.element.slice(9)] || x.type);
      const mine = props.filter((x) => x.object === obj && x.element !== t && !x.key && fits(x)).map((x) => [x.element.slice(9).split('.').pop(), `${x.label}`]);
      const links = p.steps.find((x) => x.id === 'links').items.filter((l) => l.from === obj && !S.dr.ed.drop[l.element] && ['many_to_one', 'one_to_one'].includes(S.dr.ed.card[l.element.split(':')[1]] || l.cardinality));
      const far = links.flatMap((l) => props.filter((x) => x.object === l.to && !x.key && fits(x)).map((x) => [`${l.element.split(':')[1]}.${x.element.slice(9).split('.').pop()}`, `${o.labelOf(l.to)} · ${x.label}`]));
      inputs = `<div class="label" style="margin:8px 0 4px">입력</div><div class="qpick">${[...mine, ...far].map(([v, l]) => `<label><input type="checkbox" data-in="dindin" data-v="${esc(v)}"${S.ind.inputs[v] ? ' checked' : ''}><span>${esc(l)}</span><span class="muted mono">${esc(v)}</span></label>`).join('')}</div>`;
    }
    const form = `<div class="sec">지난 처리 결과로 판정 표 만들기</div>
      <div class="field"><label>결과 컬럼</label><select data-in="dindt"><option value="">선택</option>${outs.map((x) => `<option value="${esc(x.element)}"${x.element === t ? ' selected' : ''}>${esc(o.labelOf(x.object))} · ${esc(x.label)}</option>`).join('')}</select></div>
      ${inputs}<button class="btn sm" data-act="dinduce" style="margin-top:8px"${t && Object.values(S.ind.inputs).some(Boolean) ? '' : ' disabled'}>판정 표 만들기</button>
      <div class="hint xp" style="margin-top:6px">결과 컬럼은 실제 처리 결과(허용값 또는 참 · 거짓)입니다. 규칙마다 지난 몇 건 중 몇 건이 맞는지 표시하고, 교차 검증으로 처음 보는 건의 정확도를 측정합니다.</div>`;
    return `<div class="sec">상태 전이</div>${sm ? `<table class="tight"><tr><th>Entity</th><th>전이</th><th>근거</th></tr>${sm}</table>` : '<div class="muted" style="font-size:12.5px">상태 컬럼이 없습니다.</div>'}
      ${acts ? `<div class="sec">상태 변경 Action</div><div class="chips">${acts}</div>` : ''}
      <div class="sec">역할</div>${roles ? `<table class="tight">${roles}</table>` : '<div class="muted" style="font-size:12.5px">역할을 만들지 않았습니다.</div>'}
      <div class="sec">검증 질문 · 지금 데이터 기준</div><div class="loglist">${qs || '<div class="muted">없음</div>'}</div>
      ${decs ? `<div class="sec">판정 표</div><table class="tight">${decs}</table>` : ''}${form}`;
  }

  async function mapLoad() {
    if (S.map.standards) return;
    try { S.map.standards = (await api('standards')).standards; } catch (_) { S.map.standards = []; }
    if (S.tab === 'data') render();
  }

  function standardsCard() {  // which standards a draft is compared with, table by table
    const m = S.map;
    if (!m.standards) { mapLoad(); return ''; }
    if (!m.standards.length) return '';
    const picks = m.standards.map((x) => `<label class="tick"><input type="checkbox" data-in="mpick" data-v="${esc(x.name)}"${m.picked.includes(x.name) ? ' checked' : ''}>${esc(x.label)} <span class="muted" style="font-size:11.5px">${esc(x.kind_label)}</span></label>`).join('');
    return `<div class="card"><div class="ch">비교할 표준</div><div class="cb"><div class="chips">${picks}</div>
      <div class="hint xp" style="margin-top:8px">초안의 테이블마다 이 표준의 Entity와 이름, 컬럼, 타입, 허용값, 키를 비교합니다. 맞는 테이블은 새 Entity 대신 표준 Entity에 연결할 수 있습니다.</div></div></div>`;
  }

  // ---- the draft as a review: each table a proposal to adopt, bound to a standard or kept as a new object ------------

  const MATCH_SURE = 0.85;  // a standard match this close is adopted unless a person says otherwise
  const REVIEW = [['read', '파일 선택'], ['objects', 'Entity · 키'], ['properties', 'Property · 타입'], ['links', 'Relation'], ['queries', '질의'], ['rules', '상태 · 규칙'], ['review', '검토 · 적용']];
  const reviewStep = () => (REVIEW.some((x) => x[0] === S.dr.view) ? S.dr.view : 'objects');
  const shortModule = (label) => String(label || '').replace(/\s*온톨로지$/, '').replace(/^이커머스\s+/, '');

  function stdNames() {
    const sg = S.map.sug;
    return sg && sg.ok ? new Set([...sg.objects.map((o) => o.object), ...sg.unbound_objects.map((o) => o.name)]) : new Set();
  }

  function objProposal(p, x) {
    const id = x.element.split(':')[1];
    const sm = standardMatch(x.table);
    const choice = S.dr.choice[x.table] || (sm && sm.score >= MATCH_SURE ? 'standard' : (sm ? '' : 'new'));
    const sug = (p.names || {})[id] || { name: '', parts: [] };
    const typed = S.dr.names[id];
    const api = choice !== 'new' && sm ? sm.object : (typed || sug.name || id);
    const clash = choice === 'new' && stdNames().has(api);
    const roman = choice === 'new' && !typed && !sug.name;
    const status = S.dr.ed.drop[x.element] ? 'off' : (!choice || clash || (roman && !S.dr.ok[x.element])) ? 'check' : 'ok';
    return { id, x, sm, choice, api, sug, typed, clash, roman, status };
  }

  function stepChecks(p, st) {  // what a person has not settled yet in a step
    const e = S.dr.ed;
    if (st.id === 'objects') return st.items.filter((x) => objProposal(p, x).status === 'check').length;
    if (st.id === 'properties') return st.items.filter((x) => x.type === 'enum' && !x.key && !e.drop[x.element] && !e.drop[`object:${x.object}`] && !S.dr.ok[x.element]).length;
    if (st.id === 'links') return st.items.filter((x) => x.why !== 'foreign_key' && !x.via && !e.drop[x.element] && !S.dr.ok[x.element]).length;
    return 0;
  }

  function stepTotal(st) {
    const n = st.items.length;
    return `${n}개`;
  }

  function reviewSteps(p) {
    const cur = reviewStep();
    return `<nav class="rvsteps" aria-label="초안 검토 단계">${REVIEW.map(([id, word], i) => {
      const st = p.steps.find((s) => s.id === id);
      const n = st ? stepChecks(p, st) : 0;
      const done = S.dr.seen[id] && !n && id !== cur;
      const tail = id === 'review' ? '' : (n ? ` · 확인 ${n}` : (st ? ` · ${stepTotal(st)}` : ''));
      return `${i ? '<i class="rvline" aria-hidden="true"></i>' : ''}<button class="rvstep${id === cur ? ' on' : ''}${n ? ' warn' : ''}${done ? ' done' : ''}" data-act="dview" data-view="${id}"${id === cur ? ' aria-current="step"' : ''}>${done ? '✓ ' : ''}${word}${tail}</button>`;
    }).join('')}</nav>`;
  }

  function objectsReview(p, st) {
    const o = draftContext(p);
    const read = p.steps.find((s) => s.id === 'read').items;
    const rows = st.items.map((x) => objProposal(p, x));
    const colOf = Object.fromEntries(p.steps.find((s) => s.id === 'properties').items.map((x) => [x.element.slice(9), x.column]));
    const word = { ok: '<span class="rvok">채택</span>', check: '<span class="rvwarn">확인</span>', off: '<span class="muted">제외</span>' };
    const tr = rows.map((r) => {
      const { x, sm, id } = r;
      const src = read.find((y) => y.table === x.table) || {};
      const std = sm ? `<span class="chip sm${r.choice === 'standard' ? ' b' : ''}" title="${esc(sm.why)}">${esc(shortModule(sm.module_label) || '표준')} · ${esc(sm.label)} ${Math.round(sm.score * 100)}%</span>${r.choice === 'new' ? '<div class="muted" style="font-size:11px">새 Entity로 유지</div>' : ''}`
        : (S.map.sug ? '<span class="muted" style="font-size:12px">일치 없음</span>' : '<span class="spin"></span>');
      const name = r.choice !== 'new' && sm ? `<span class="mono">${esc(r.api)}</span>`
        : `<input type="text" class="inline mono" data-in="dapi" data-obj="${esc(id)}" value="${esc(r.api)}" aria-label="${esc(x.label)} API 이름" style="width:150px">`;
      const nameWhy = r.choice === 'standard' ? '표준 Entity 이름' : !r.choice ? '표준에 연결하면 쓰는 이름' : r.typed ? '직접 입력' : r.sug.name ? r.sug.parts.map(([k, v]) => `${k}=${v}`).join(' + ') : '로마자 표기 · 이름 확인';
      const keyWhy = x.why === 'primary_key' ? '선언된 기본 키' : x.why === 'unique' ? `고유 ${show(x.rows)}/${show(x.rows)}` : why(o, 'object', x);
      const pick = `data-act="dpick" data-t="${esc(x.table)}"`;
      return `<tr class="${r.status === 'off' ? 'off' : ''}${S.dr.pick === x.table ? ' sel' : ''}">
        <td style="width:28px"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${r.status === 'off' ? '' : ' checked'} aria-label="${esc(x.label)} 포함"></td>
        <td ${pick} class="rvpick">${esc(src.source || x.table)}<div class="muted mono">${show(x.rows)}행</div></td>
        <td>${labelInput(x.element, x.label)}${r.choice === 'standard' && sm && sm.label !== x.label ? `<div class="muted" style="font-size:11.5px">→ <b>${esc(sm.label)}</b></div>` : ''}</td>
        <td>${name}<div class="muted" style="font-size:11px">${esc(nameWhy)}</div>${r.clash ? '<div class="rvbad">표준 Entity 이름과 같습니다</div>' : ''}</td>
        <td><select class="inline" data-in="dkey" data-obj="${esc(id)}">${options(o.propsOf(id).map((n) => [n, colOf[`${id}.${n}`] || n]), o.keyOf(id))}</select><div class="muted" style="font-size:11px">${S.dr.ed.keys[id] && S.dr.ed.keys[id] !== x.key ? '직접 지정' : esc(keyWhy)}</div></td>
        <td ${pick} class="rvpick">${std}</td><td ${pick} class="rvpick">${word[r.status]}</td></tr>`;
    }).join('');
    const left = st.skipped.filter((x) => x.why === 'no_key');
    return `<table class="tight rvtable"><tr><th></th><th>데이터 소스</th><th>Entity 이름</th><th>API 이름</th><th>키</th><th>표준과 일치</th><th>상태</th></tr>${tr}</table>
      ${left.length ? `<div class="hint" style="margin-top:10px">키 컬럼이 없어 제외된 테이블: ${left.map((x) => esc(x.table)).join(', ')}</div>` : ''}`;
  }

  async function loadDraftTable(table) {
    S.dr.tbl[table] = null;
    try { S.dr.tbl[table] = await api('draft/table', { table }); } catch (e) { S.dr.tbl[table] = { error: e.message }; }
    if (S.tab === 'data') refreshDraft();
  }

  function bar(label, v, text) {
    return `<div class="rvbar"><span>${esc(label)}</span><i><b style="width:${Math.max(2, Math.round(Math.min(1, v) * 100))}%"></b></i><span class="mono">${esc(text)}</span></div>`;
  }

  function objectSide(p, st) {
    const rows = st.items.map((x) => objProposal(p, x));
    const r = rows.find((y) => y.x.table === S.dr.pick) || rows.find((y) => y.status === 'check') || rows[0];
    if (!r) return '';
    const t = S.dr.tbl[r.x.table];
    if (t === undefined) loadDraftTable(r.x.table);
    const sm = r.sm;
    const title = r.choice === 'standard' && sm ? `${esc(r.x.table)} → ${esc(sm.label)}(${esc(sm.object)})`
      : !r.choice && sm ? `${esc(r.x.table)} → ${esc(sm.label)} 연결 제안` : `${esc(r.x.table)} → 새 Entity ${esc(r.api)}`;
    let sample = '<div class="empty" style="padding:10px"><span class="spin"></span>행을 읽는 중입니다.</div>';
    let facts = '';
    if (t && t.error) sample = `<div class="hint warn">${esc(t.error)}</div>`;
    else if (t) {
      const cols = t.columns.slice(0, 5);
      sample = t.sample.length ? `<div class="scroll"><table class="tight rvsample"><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>${t.sample.map((row) => `<tr>${cols.map((c, i) => `<td>${show(row[i])}</td>`).join('')}</tr>`).join('')}</table></div>` : '<div class="muted">행이 없습니다.</div>';
      const k = t.key;
      const keySay = k.why === 'primary_key' ? '선언된 기본 키입니다' : (k.nulls === 0 && k.distinct === t.rows ? `${show(t.rows)}행 모두 값이 있고 서로 다릅니다` : `${show(t.rows)}행 중 서로 다른 값 ${show(k.distinct)}개, 빈 값 ${show(k.nulls)}개`);
      const chips = [...t.personal.map((c) => `<span class="chip sm warn">${esc(c)} · 가림 권장</span>`),
        ...t.profile.filter((c) => c.values).map((c) => `<span class="chip sm">${esc(c.name)} · 허용값 ${c.values}개</span>`)];
      facts = `<div class="rvfacts"><div><b>키 근거</b> · <span class="mono">${esc(k.column)}</span> ${esc(keySay)}</div>`;
      if (sm) {
        const n = sm.columns.length, all = n + sm.missing.length;
        const form = n ? sm.columns.reduce((a, c) => a + c.score, 0) / n : 0;
        facts += `<div><b>일치 근거</b> · ${esc(sm.why)}</div>${bar('이름 · 용어 사전', sm.name_score, sm.name_score.toFixed(2))}${bar('속성 일치', all ? n / all : 0, `${n}/${all}`)}${bar('값 형태', form, form.toFixed(2))}`;
        if (sm.missing.length) facts += `<div class="muted" style="font-size:12px">테이블에 없는 표준 속성: ${esc(sm.missing.map((y) => y.label).join(', '))}</div>`;
      } else facts += `<div class="muted">표준 모듈에 맞는 Entity가 없어 새 Entity로 만듭니다.${r.sug.name ? ` 이름은 ${esc(r.sug.parts.map(([a, b]) => `${a}=${b}`).join(' + '))}로 지었습니다.` : ''}</div>`;
      if (r.roman) facts += '<div class="hint warn" style="margin:0">이름에 모르는 단어가 있어 로마자로 표기했습니다. API 이름을 고치거나 이대로 채택해 주세요.</div>';
      facts += chips.length ? `<div class="chips">${chips.join('')}</div>` : '';
      facts += '</div>';
    }
    const t0 = esc(r.x.table);
    const acts = sm ? `<button class="btn sm${r.choice === 'standard' ? ' primary' : ''}" data-act="dchoose" data-t="${t0}" data-c="standard">${esc(sm.label)}에 연결</button><button class="btn sm${r.choice === 'new' ? ' primary' : ''}" data-act="dchoose" data-t="${t0}" data-c="new">새 Entity로 유지</button>`
      : `<button class="btn sm${r.status === 'ok' ? '' : ' primary'}" data-act="dchoose" data-t="${t0}" data-c="new">${r.roman ? '이 이름으로 채택' : '새 Entity로 채택'}</button>`;
    return `<div class="card"><div class="ch">${title}</div><div class="cb">${sample}</div><div class="cb rvline2">${facts}</div><div class="cb rvline2"><div class="chips">${acts}</div></div></div>`;
  }

  function reviewMain(p, cur) {
    if (cur === 'objects') return objectsReview(p, p.steps.find((s) => s.id === 'objects'));
    if (cur === 'review') return reviewPlan(p);
    return stepDetail(p, p.steps.find((s) => s.id === cur));
  }

  function reviewChoices(p) {
    const rows = p.steps.find((x) => x.id === 'objects').items.map((x) => objProposal(p, x)).filter((r) => r.status !== 'off');
    return Object.fromEntries(rows.map((r) => [r.x.table, r.choice]));
  }

  async function loadPlan() {
    const p = S.files.pending, body = { standard: S.map.picked, edits: toEdits(), choices: reviewChoices(p) };
    const sig = JSON.stringify(body);
    if (S.dr.plan && S.dr.plan.sig === sig) return;
    S.dr.plan = { sig, busy: true };
    let got;
    try { got = await api('draft/review/preview', body); } catch (e) { got = { ok: false, issues: [e.message] }; }
    if (S.dr.plan.sig !== sig) return;
    S.dr.plan = { sig, ...got };
    if (S.tab === 'data' && reviewStep() === 'review') refreshDraft();
  }

  // what applying will do, table by table, with the module files it writes and what the definition check says of them
  function reviewPlan(p) {
    loadPlan();
    const plan = S.dr.plan || { busy: true };
    const rows = p.steps.find((x) => x.id === 'objects').items.map((x) => objProposal(p, x));
    const read = p.steps.find((x) => x.id === 'read').items;
    const to = (r) => (r.status === 'off' ? '<span class="muted">제외</span>'
      : r.choice === 'standard' && r.sm ? `<span class="chip sm b">표준에 연결</span> ${esc(r.sm.label)} <span class="mono muted cn">${esc(r.sm.object)}</span> <span class="muted">· ${esc(shortModule(r.sm.module_label))}</span>`
        : !r.choice ? '<span class="rvwarn">정하지 않음</span>' : `<span class="chip sm">새 Entity</span> ${esc(S.dr.ed.labels[r.x.element] || r.x.label)} <span class="mono muted cn">${esc(r.api)}</span>`);
    const table = `<table class="tight"><tr><th>데이터 소스</th><th>적용 결과</th><th>상태</th></tr>${rows.map((r) => `<tr class="${r.status === 'off' ? 'off' : ''}"><td>${esc((read.find((y) => y.table === r.x.table) || {}).source || r.x.table)}</td><td>${to(r)}</td><td>${{ ok: '<span class="rvok">채택</span>', check: '<span class="rvwarn">확인</span>', off: '' }[r.status]}</td></tr>`).join('')}</table>`;
    const issues = plan.issues || [];
    // tables nobody settled block the apply: what each one waits on, and the way to settle it without going back five steps
    const left = rows.filter((r) => r.status === 'check'), match = left.filter((r) => r.sm);
    const waits = (r) => (r.sm ? `표준 Entity ${esc(r.sm.label)} <span class="mono">${esc(r.sm.object)}</span>와 ${Math.round(r.sm.score * 100)}% 일치${r.clash ? ' · API 이름이 표준 Entity와 같음' : ''}` : r.clash ? 'API 이름이 표준 Entity와 같음' : '로마자로 표기한 API 이름 · 확인 필요');
    const settle = left.length ? `<div class="banner no" style="margin:0"><span class="ic x" style="width:24px;height:24px">!</span><div><div class="big" style="font-size:14px">확인할 테이블 ${left.length}개가 남아 적용하지 못했습니다</div>
        <div class="loglist">${left.map((r) => `<div><b>${esc((read.find((y) => y.table === r.x.table) || {}).source || r.x.table)}</b> · ${waits(r)}</div>`).join('')}</div>
        <div class="chips" style="margin-top:10px">${match.length ? `<button class="btn sm primary" data-act="dsettle">표준 Entity에 연결 ${match.length}개</button>` : ''}<button class="btn sm" data-act="dview" data-view="objects">Entity · 키 단계에서 정하기</button></div></div></div>` : '';
    const check = settle || (plan.busy ? '<span class="chip"><span class="spin"></span>정의 검사 중</span>'
      : issues.length ? `<div class="banner no" style="margin:0"><span class="ic x" style="width:24px;height:24px">!</span><div><div class="big" style="font-size:14px">정의 검사 오류 ${issues.length}건</div><div class="loglist">${issues.slice(0, 8).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div></div>`
        : '<span class="chip ok">✓ 정의 검사 통과</span>');
    const v = S.dr.rv === 'yaml' ? 'yaml' : 'plan';
    const tabs = [['plan', '적용할 내용'], ['yaml', '정의 파일']].map(([k, w]) => `<button class="${v === k ? 'on' : ''}" data-act="drv" data-k="${k}">${w}</button>`).join('');
    const mods = plan.modules || [];
    const files = mods.map((m) => `<div class="sec">${esc(m.label)} <span class="muted mono">${esc(m.name)}</span></div><pre class="code" style="max-height:360px;overflow:auto">${esc(m.yaml)}</pre>`).join('') || '<div class="empty"><span class="spin"></span></div>';
    return `<div class="chips" style="align-items:center">${check}</div><div class="seg" style="margin:14px 0 10px;width:max-content">${tabs}</div>${v === 'yaml' ? files : table}`;
  }

  function reviewFoot(p) {
    const cur = reviewStep(), i = REVIEW.findIndex((s) => s[0] === cur);
    const next = REVIEW[i + 1];
    const st = p.steps.find((s) => s.id === cur);
    const left = st ? stepChecks(p, st) : 0;
    let say;
    if (cur === 'objects') {
      const rows = st.items.map((x) => objProposal(p, x)).filter((r) => r.status !== 'off');
      const ok = rows.filter((r) => r.status === 'ok').length, std = rows.filter((r) => r.choice === 'standard').length;
      say = `<b>${rows.length}개 중 ${ok}개 채택${rows.length - ok ? ` · ${rows.length - ok}개 확인 필요` : ''}</b><span class="muted">표준에 연결 ${std} · 새 Entity ${rows.length - std}</span>`;
    } else if (cur === 'review') {
      const os = p.steps.find((s) => s.id === 'objects');
      const n = os.items.filter((x) => objProposal(p, x).status === 'check').length;
      // the same counts the step chips show: what nobody looked at is applied as proposed, and the footer says so
      const rest = REVIEW.map(([id, word]) => { const s = p.steps.find((y) => y.id === id); return [word, s && id !== 'objects' ? stepChecks(p, s) : 0]; }).filter((x) => x[1]);
      say = n ? `<b class="rvwarn">Entity · 키 단계에 확인할 테이블 ${n}개가 남았습니다</b>`
        : rest.length ? `<b>확인하지 않은 제안 ${rest.reduce((a, x) => a + x[1], 0)}개는 제안대로 적용됩니다</b><span class="muted">${esc(rest.map(([w, k]) => `${w} ${k}`).join(' · '))} · 적용하면 새 파이프라인으로 추가됩니다</span>`
          : '<b>모든 제안을 검토했습니다</b><span class="muted">적용하면 지금 데이터는 그대로 두고 새 데이터로 추가됩니다. 위쪽 [데이터] 목록에서 오갑니다</span>';
    } else say = left ? `<b>확인 필요 ${left}</b><span class="muted">${esc(STEP[cur][1])}</span>` : `<b>${esc(STEP[cur][0])} · 확인할 제안 없음</b><span class="muted">${esc(STEP[cur][1])}</span>`;
    const nst = next && p.steps.find((s) => s.id === next[0]);
    const hint = nst ? `<span class="muted">다음 단계 · ${esc(REVIEW[i + 1][1])} ${esc(stepTotal(nst))}</span>` : '';
    const all = left ? '<button class="btn" data-act="dokall">남은 제안 모두 채택</button>' : '';
    const req = S.files.request, blocked = S.dr.busy || !S.dr.plan || S.dr.plan.busy || (S.dr.plan.issues || []).length;
    const busy = '<span class="spin"></span>적용 중';
    let go, note = '';
    if (next) go = `<button class="btn primary" data-act="dview" data-view="${next[0]}">다음: ${next[1]}</button>`;
    else if (req) {  // a request waits: the approver applies it as filed, the requester can take it back
      note = `<span class="chip sm warn">적용 요청 대기 · ${esc(req.by)} · ${esc(dayOf(req.at))}</span>`;
      go = canApplyDraft() ? `<button class="btn" data-act="drequestdrop"${S.dr.busy ? ' disabled' : ''}>반려</button><button class="btn primary" data-act="drequestapply"${S.dr.busy ? ' disabled' : ''}>${S.dr.busy ? busy : '요청대로 적용'}</button>`
        : (S.me && S.me.user && S.me.user.name === req.by ? '<button class="btn" data-act="drequestdrop">요청 거두기</button>' : '');
    } else if (canApplyDraft()) go = `<button class="btn primary" data-act="dapply"${blocked ? ' disabled' : ''}>${S.dr.busy ? busy : '온톨로지에 적용'}</button>`;
    else {  // an editor in a team: the last step files the request
      note = '<span class="muted" style="font-size:12px">적용은 승인자가 합니다</span>';
      go = `<button class="btn primary" data-act="drequest"${blocked ? ' disabled' : ''} title="검토한 그대로 승인자에게 보냅니다">${S.dr.busy ? '<span class="spin"></span>보내는 중' : '적용 요청'}</button>`;
    }
    return `<div class="rvfoot">${say}${hint}<span style="flex:1"></span>${all}${note}${go}</div>`;
  }

  function draftBody() {
    const p = S.files.pending;
    if (S.dr.step < p.steps.length) S.dr.step = p.steps.length;
    const cur = reviewStep();
    S.dr.seen[cur] = true;
    const read = p.steps.find((s) => s.id === 'read').items;
    const files = new Set(read.map((x) => x.source || x.table)).size;
    const std = S.map.picked.map((n) => ((S.map.standards || []).find((x) => x.name === n) || { label: n }).label);
    const meta = `${esc(S.st.repository.label)} · 파일 ${files}개 · ${show(read.reduce((a, x) => a + x.rows, 0))}행${std.length ? ` · ${esc(std.join(', '))}${josa(std[std.length - 1], '과', '와')} 비교` : ''}`;
    const side = cur === 'objects' ? objectSide(p, p.steps.find((s) => s.id === 'objects'))
      : `<div class="card"><div class="ch">초안 그래프<div class="right legend"><span><i class="fill"></i>Entity</span><span>→ 관계</span></div></div><div class="cb" style="padding:0;position:relative"><div class="kg" id="dgraph" style="height:420px"></div><div class="kg-tip">Node를 선택하면 속성이 표시됩니다</div></div></div>`;
    return `<div class="rvhead"><div><h2>${esc(p.label)} 초안</h2><div class="sub">${meta}</div></div><button class="btn sm" data-act="dsetup" aria-expanded="${!!S.dr.setup}">${S.dr.setup ? '설정 닫기' : '생성 설정'}</button></div>
      ${reviewSteps(p)}
      <div class="grid rvgrid"><div class="card"><div class="ch">${cur === 'objects' ? '소스 테이블 → Entity' : esc(cur === 'review' ? '검토 · 적용' : STEP[cur][0])}<div class="right muted" style="font-weight:600;font-size:12px">${cur === 'objects' ? '' : esc(cur === 'review' ? '적용할 내용, 정의 파일' : STEP[cur][1])}</div></div>
        <div class="cb scroll" id="ddetail">${reviewMain(p, cur)}</div></div><div class="hcol">${side}</div></div>
      ${reviewFoot(p)}`;
  }

  function rulesCard(f) {
    const r = S.dr.rules || f.rules;
    const num = RULE_NUM.map(([k, l]) => `<label class="field" title="${esc(RULE_HINT[k] || '')}"><span>${l}</span><input type="number" min="${k === 'enum_repeat' ? 1 : 0}" step="${k === 'enum_repeat' ? 0.5 : 1}" data-in="drule" data-k="${k}" value="${esc(r[k])}"></label>`).join('');
    const flags = RULE_FLAG.map(([k, l]) => `<label class="tick"><input type="checkbox" data-in="drule" data-k="${k}"${r[k] ? ' checked' : ''}>${l}</label>`).join('');
    const queries = RULE_QUERY.map(([k, l]) => `<label class="tick"><input type="checkbox" data-in="drule" data-k="queries" data-v="${k}"${r.queries.includes(k) ? ' checked' : ''}>${l}</label>`).join('');
    const lists = RULE_LIST.map(([k, l]) => `<label class="field" title="${esc(RULE_HINT[k] || '')}"><span>${l}</span><input type="text" data-in="drule" data-k="${k}" value="${esc(r[k].join(', '))}"></label>`).join('');
    const by = (f.rules_by || []).length ? `<div class="hint" style="margin-bottom:8px">구축 규칙 모듈 ${esc(f.rules_by.join(', '))}의 값을 기본값으로 사용합니다.</div>` : '';
    return `<div class="card drcard${S.dr.rulesOpen ? '' : ' shut'}"><div class="ch">생성 설정${S.dr.rulesOpen ? '' : '<span class="muted" style="font-weight:500;font-size:12px;margin-left:8px">기본값 사용</span>'}<div class="right">${S.dr.rulesOpen ? '<button class="btn sm ghost" data-act="drules-reset">기본값</button>' : ''}<button class="btn sm" data-act="drrules" aria-expanded="${!!S.dr.rulesOpen}">${S.dr.rulesOpen ? '접기' : '보기'}</button></div></div><div class="cb drules">
      ${by}<div class="sec">허용값</div><div class="rgrid">${num}</div>
      <div class="sec">관계 · 키 · 규칙</div>${flags}
      <div class="sec">생성 질의</div><div class="chips">${queries}</div>
      <div class="sec">이름 규칙</div><div class="rgrid two">${lists}</div>
      ${f.pending ? '<div class="hint" style="margin-top:12px">설정 변경 · 초안 재생성 필요</div>' : ''}</div></div>`;
  }

  function viewData() {
    const head = `<div class="head"><div><h1>초안 생성</h1><div class="sub">자료 파일로 온톨로지 초안을 생성합니다.</div></div>
      <div class="right"><a class="btn sm" href="#catalog">자료 업로드</a><a class="btn sm" href="#db">DB 연결</a></div></div>`;
    const f = S.files;
    if (!f || f.busy) return head + '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>';
    if (f.error) return head + `<div class="banner no"><div class="why">${esc(f.error)}</div></div>`;
    const list = f.files.length ? f.files.map((x) => `<div class="fileitem"><div style="flex:1;min-width:0"><b>${esc(x.source)}</b>
        ${x.tables.map((t) => `<div class="muted" style="font-size:12px"><label class="tick inline-tick"><input type="checkbox" data-in="dtable" data-t="${esc(t.name)}"${S.dr.tables[t.name] === false ? '' : ' checked'}>${x.tables.length > 1 ? esc(t.sheet) + ' · ' : ''}테이블 <span class="mono">${esc(t.name)}</span> · ${show(t.rows)}행 · 컬럼 ${t.columns.length}개${t.truncated ? ' · 행 한도까지 읽음' : ''}</label>
          <div class="chips" style="margin-top:4px">${t.columns.slice(0, 10).map((c) => `<span class="chip sm">${esc(c)}</span>`).join('')}${t.columns.length > 10 ? `<span class="chip sm">외 ${t.columns.length - 10}개</span>` : ''}</div></div>`).join('')}</div>
        <button class="btn sm ghost" data-act="fout" data-name="${esc(x.source)}" aria-label="${esc(x.source)} 초안에서 제외">제외</button></div>`).join('')
      : (f.definitions.length ? '' : `<div class="muted" style="font-size:12.5px">초안에 포함한 파일이 없습니다.</div>${S.st.data.samples && canEdit() ? '<button class="btn sm" data-act="dsample" style="margin-top:8px">샘플 데이터 불러오기</button>' : ''}`);
    const defFacts = (x) => [['테이블', x.tables.length], ['컬럼', x.columns], ['참조', x.references], ['코드 그룹', x.codes], ['코드값', x.code_values], ['용어', x.terms], ['메시지', x.messages], ['문서', x.documents]]
      .filter(([, n]) => n).map(([k, n]) => `${k} ${show(n)}`).join(' · ');
    const docKind = { policy: '정책', screen: '화면', other: '문서' };
    const defs = f.definitions.map((x) => `<div class="fileitem"><div style="flex:1;min-width:0"><b>${esc(x.source)}</b> <span class="chip sm b">${x.tables.length || x.groups.length || x.terms || x.messages ? '정의서' : '문서'}</span>
        <div class="muted" style="font-size:12px;margin:3px 0">${defFacts(x)}</div>
        ${x.tables.length ? `<div class="scroll deflist">${x.tables.map((t) => `<label class="tick inline-tick" style="display:flex"><input type="checkbox" data-in="dtable" data-t="${esc(t.name)}"${S.dr.tables[t.name] === false ? '' : ' checked'}><span class="mono">${esc(t.name)}</span>&nbsp;<span class="muted">${esc(t.label)} · 컬럼 ${t.columns}${t.key.length > 1 ? ' · 복합 키' : (t.key.length ? '' : ' · 키 없음')}</span></label>`).join('')}</div>
          <div style="display:flex;gap:6px;margin-top:6px"><button class="btn sm ghost" data-act="dtall" data-src="${esc(x.source)}" data-on="1">전체 선택</button><button class="btn sm ghost" data-act="dtall" data-src="${esc(x.source)}" data-on="0">전체 해제</button></div>` : ''}
        ${x.groups.length ? `<div class="chips" style="margin-top:6px">${x.groups.slice(0, 12).map((g) => `<span class="chip sm">${esc(g.name)} ${esc(g.label)} · ${g.values}</span>`).join('')}${x.groups.length > 12 ? `<span class="chip sm">외 ${x.groups.length - 12}개</span>` : ''}</div>` : ''}
        ${x.document_list.length ? `<div class="chips" style="margin-top:6px">${x.document_list.slice(0, 12).map((d) => `<span class="chip sm">${esc(d.name)} · ${docKind[d.kind] || '문서'} · 섹션 ${show(d.sections)}</span>`).join('')}</div>` : ''}</div>
        <button class="btn sm ghost" data-act="fout" data-name="${esc(x.source)}" aria-label="${esc(x.source)} 초안에서 제외">제외</button></div>`).join('');
    const defHint = f.definitions.length ? `<div class="hint" style="margin-top:10px">${f.files.length ? '정의서의 테이블 한글명, 컬럼 한글명, 코드값과 코드명으로 초안의 이름과 허용값을 입력합니다.' : '데이터 파일 없이 정의서만 있으면 행 없이 Schema(키, 참조, 코드값)로 초안을 생성합니다.'}</div>` : '';
    const left = `<div class="card"><div class="ch">초안에 넣을 파일<span class="chip sm">${esc(S.st.repository.label)}</span></div><div class="cb">
      ${list}${defs}${defHint}
      <div class="field" style="margin-top:14px"><label>온톨로지 이름</label><input type="text" data-in="dname" value="${esc(S.dr.label)}" placeholder="예: 가상 쇼핑몰"></div>
      ${f.pending ? `<button class="btn primary" data-act="draft"${S.dr.busy ? ' disabled' : ''}>${S.dr.busy ? '<span class="spin"></span>처리 중' : '이 파일로 다시 생성'}</button>` : ''}</div></div>`;
    const setup = `<div class="grid" style="grid-template-columns:minmax(0,1.3fr) minmax(300px,1fr);align-items:start">${left}<div class="hcol">${rulesCard(f)}${standardsCard()}</div></div>`;
    if (!S.map.standards) mapLoad();
    if (!f.pending) {
      const tables = f.files.flatMap((x) => x.tables).filter((t) => S.dr.tables[t.name] !== false);
      const defs = f.definitions.flatMap((x) => x.tables).filter((t) => S.dr.tables[t.name] !== false);
      const steps = `<nav class="rvsteps" aria-label="초안 검토 단계">${REVIEW.map(([id, word], i) => `${i ? '<i class="rvline" aria-hidden="true"></i>' : ''}<span class="rvstep${i ? ' wait' : ' on'}"${i ? '' : ' aria-current="step"'}>${word}</span>`).join('')}</nav>`;
      const ready = (f.files.length || f.definitions.some((x) => x.tables.length)) && !S.dr.busy;
      const foot = `<div class="rvfoot"><b>${f.files.length ? `파일 ${f.files.length}개 · 테이블 ${tables.length}개 선택` : '선택된 파일이 없습니다'}</b><span class="muted">${defs.length ? `정의서 테이블 ${defs.length}개` : ''}</span>
        <span style="flex:1"></span>${f.files.length ? '' : '<a class="btn" href="#catalog">자료 업로드</a>'}<button class="btn primary" data-act="draft"${ready ? '' : ' disabled'}>${S.dr.busy ? '<span class="spin"></span>초안을 만드는 중' : '초안 생성 · 다음: Entity · 키'}</button></div>`;
      return `${head}<div class="rvwrap"><div class="rvhead"><div><h2>${esc(S.dr.label || '새')} 초안</h2><div class="sub">${esc(S.st.repository.label)}</div></div></div>${steps}${setup}${foot}</div>`;
    }
    return `${head}${S.dr.setup ? setup : ''}<div id="draft" class="rvwrap">${draftBody()}</div>`;
  }

  // ---- catalog: repositories of raw files, by folder, each file with what it turned out to be ----------------------

  const DOC_WORD = { policy: '정책 문서', screen: '화면 문서', other: '문서' };
  const count = (n) => Number(n || 0).toLocaleString('ko-KR');
  const fileSize = (n) => (n >= 1 << 20 ? `${(n / (1 << 20)).toFixed(1)}MB` : (n >= 1024 ? `${Math.round(n / 1024).toLocaleString('ko-KR')}KB` : `${n}B`));
  const dayOf = (v) => String(v || '').slice(0, 16).replace('T', ' ');
  const baseName = (p) => p.split('/').pop();

  const USE_WORD = { '': '자동', data: '테이블 데이터', definition: '정의서', document: '문서', raw: '원본 보관' };
  function kindChip(f) {
    const set = f.use ? ' title="사람이 지정한 용도입니다"' : '';  // what a person said the file is, over what its content looked like
    const pin = f.use ? ' <span class="muted" style="font-size:10.5px">지정</span>' : '';
    if (f.error) return `<span class="chip sm bad"${set}>읽기 실패</span>${pin}`;
    const k = (f.facts || {}).kind;
    if (k === 'raw') return `<span class="chip sm"${set}>원본 보관</span>${pin}`;
    if (k === 'data') return `<span class="chip sm b"${set}>테이블 데이터</span>${pin}`;
    if (k === 'definition') return `<span class="chip sm ok"${set}>정의서</span>${pin}`;
    if (k === 'document') return `<span class="chip sm"${set}>${DOC_WORD[f.facts.doc_kind] || '문서'}</span>${pin}`;
    return '<span class="chip sm">내용 없음</span>';
  }

  function amount(f) {
    const c = f.facts || {};
    if (f.error) return '-';
    if (c.kind === 'data') return `${c.tables > 1 ? `시트 ${c.tables} · ` : ''}${count(c.rows)}행 · 컬럼 ${c.columns}`;
    if (c.kind === 'document') return `섹션 ${count(c.sections)}`;
    return [['tables', '테이블'], ['codes', '코드 그룹'], ['terms', '용어'], ['messages', '메시지'], ['documents', '문서']].filter(([k]) => c[k]).map(([k, l]) => `${l} ${count(c[k])}`).slice(0, 2).join(' · ') || '-';
  }

  function routeOf(f) {
    const c = f.facts || {};
    if (f.error) return '-';
    if (c.kind === 'data' || c.tables) return '도메인 · Binding 모듈';
    if (c.codes) return '코드값 이름, 결정표';
    if (c.terms || c.messages) return '용어 사전 모듈';
    if (c.kind === 'document') return S.st.ask ? '정책서로 규칙 초안' : '문서 본문';
    return '-';
  }

  async function loadCatalog() {
    const c = S.cat;
    c.busy = true;
    try {
      c.st = await api('catalog?folder=' + encodeURIComponent(c.folder));
    } catch (e) {
      if (c.folder) { c.folder = ''; c.busy = false; return loadCatalog(); }  // a folder that went from under this page
      c.st = { error: e.message };
    }
    c.busy = false;
    if (S.tab === 'catalog') render();
  }

  // after anything that changes the files: the catalog, what a draft reads, and the counts in the menu
  async function catalogChanged() {
    spaceChanged();  // the explorer reads the files again too
    S.files = null; S.conv = null; S.cat.sel = {};
    S.st = await api('state');
    await loadCatalog();
    if (S.tab !== 'catalog') render();  // the draft screen asks for its files again
  }

  async function catalogCall(path, body, done) {
    try {
      const r = await api(path, body);
      if (done) done(r);
      await catalogChanged();
    } catch (e) { fail(e); }
  }

  async function uploadAll(items) {
    const c = S.cat;
    if (!items.length || c.up) return;
    const lim = (c.st && c.st.limits) || {};
    c.up = { done: 0, total: items.length, name: '' };
    let skipped = 0, sent = 0;
    for (const [f, rel] of items) {
      c.up.name = rel;
      if (S.tab === 'catalog') render();
      try {
        if (lim.file_bytes && f.size > lim.file_bytes) throw new Error(`${baseName(rel)}: 파일 크기가 ${bytes(lim.file_bytes)} 한도를 초과해 업로드하지 못했습니다. 파일을 나누어 다시 업로드해 주세요.`);
        const path = (c.folder ? c.folder + '/' : '') + rel;
        const r = await fetch('/api/upload?path=' + encodeURIComponent(path), { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-Ontlas-Request': '1' }, body: f });
        let j = {};
        try { j = await r.json(); } catch (_) { /* empty body */ }
        if (!r.ok) throw new Error(j.error || `서버 오류로 파일을 업로드하지 못했습니다. 잠시 후 다시 시도해 주세요. (${r.status})`);
        if (j.skipped) skipped += 1; else sent += 1;
      } catch (e) { fail(e); }
      c.up.done += 1;
    }
    c.up = null;
    await catalogChanged();
    if (sent) { c.next = { files: sent }; toast(`파일 ${count(sent)}개를 업로드했습니다.${skipped ? ` 시스템 파일 ${skipped}개는 제외했습니다.` : ''}`); render(); }
  }

  // a dropped folder arrives as entries: walk them, keeping each file's path below the drop
  async function walkEntry(entry, prefix, out) {
    if (entry.isFile) {
      out.push([await new Promise((ok, no) => entry.file(ok, no)), prefix + entry.name]);
      return;
    }
    const reader = entry.createReader();
    for (;;) {  // readEntries gives a batch at a time
      const batch = await new Promise((ok, no) => reader.readEntries(ok, no));
      if (!batch.length) break;
      for (const e of batch) await walkEntry(e, `${prefix}${entry.name}/`, out);
    }
  }

  async function dropped(dt) {
    const entries = [...dt.items].map((x) => (x.webkitGetAsEntry ? x.webkitGetAsEntry() : null)).filter(Boolean);
    const out = [];
    if (!entries.length) return uploadAll([...dt.files].map((f) => [f, f.name]));
    try {
      for (const e of entries) await walkEntry(e, '', out);
    } catch (e) { fail(e); }
    return uploadAll(out);
  }

  function sortedRows(c) {
    const { folders, files } = c.st;
    const key = { name: (x) => x.name, bytes: (x) => x.bytes, uploaded: (x) => x.uploaded || '' }[c.sort];
    const by = (a, b) => { const x = key(a), y = key(b); return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y), 'ko')) * c.dir; };
    return [...[...folders].sort(by), ...files.filter((f) => !c.ext || f.ext === c.ext).sort(by)];
  }

  function folderTrail(c) {
    const parts = c.folder ? c.folder.split('/') : [];
    const links = parts.map((x, i) => `<i>/</i><button class="plink" data-act="copen" data-path="${esc(parts.slice(0, i + 1).join('/'))}">${esc(x)}</button>`).join('');
    return `<button class="plink" data-act="copen" data-path="">${esc(c.st.repository.label)}</button>${links}`;
  }

  function catalogRow(x, i, c) {
    const folder = x.files !== undefined;
    const editing = c.edit && c.edit.path === x.path;
    const name = editing
      ? `<input type="text" id="cedit" data-in="cedit" value="${esc(c.edit.value)}" aria-label="새 이름">`
      : `<button class="fname" data-act="${folder ? 'copen' : 'cview'}" data-path="${esc(x.path)}">${folder ? ui('catalog2') : ''}<span>${esc(x.name)}</span></button>`;
    const on = !!c.sel[x.path];
    const pick = `<input type="checkbox" data-in="csel" data-path="${esc(x.path)}"${on ? ' checked' : ''} aria-label="${esc(x.name)} 선택">`;
    const more = `<button class="iconbtn" data-act="cmenu" data-path="${esc(x.path)}" data-folder="${folder ? 1 : ''}" data-use="${esc(x.use || '')}" aria-label="${esc(x.name)} 작업">${ui('more')}</button>`;
    if (folder) {
      const inc = x.files ? `<input type="checkbox" data-in="cinc" data-path="${esc(x.path)}"${x.included === x.files ? ' checked' : ''} aria-label="${esc(x.name)} 초안 포함">${x.included && x.included < x.files ? `<span class="muted"> ${x.included}/${x.files}</span>` : ''}` : '<span class="muted">-</span>';
      const emb = x.files ? `<input type="checkbox" data-in="cemb" data-path="${esc(x.path)}"${x.embedded === x.files ? ' checked' : ''} aria-label="${esc(x.name)} 임베딩">${x.embedded && x.embedded < x.files ? `<span class="muted"> ${x.embedded}/${x.files}</span>` : ''}` : '<span class="muted">-</span>';
      return `<tr class="crow"><td>${pick}</td><td class="muted">${i + 1}</td><td>${name}</td><td><span class="chip sm folder">폴더</span></td><td class="muted">-</td><td>${x.files ? fileSize(x.bytes) : '<span class="muted">-</span>'}</td><td class="muted">-</td><td class="muted">${count(x.files)}개 파일</td><td class="muted">-</td><td>${inc}</td><td>${emb}</td><td>${more}</td></tr>`;
    }
    return `<tr class="crow${x.included && !x.error ? '' : ' out'}" data-row="file:${esc(x.path)}"><td>${pick}</td><td class="muted">${i + 1}</td><td>${name}</td><td>${kindChip(x)}</td><td class="mono muted">${esc(x.ext || '-')}</td><td>${fileSize(x.bytes)}</td><td>${amount(x)}</td><td class="muted">${esc(dayOf(x.uploaded))}</td><td class="route">${esc(routeOf(x))}</td>
      <td>${x.error || (x.facts || {}).kind === 'raw' ? '<span class="muted">-</span>' : `<input type="checkbox" data-in="cinc" data-path="${esc(x.path)}"${x.included ? ' checked' : ''} aria-label="${esc(x.name)} 초안 포함">`}</td><td>${embedCell(x)}</td><td>${more}</td></tr>`;
  }

  const EMBED_STATE = { embedded: ['ok', '임베딩됨'], off: ['', '꺼짐'], pending: ['warn', '임베딩 대기'], failed: ['bad', '임베딩 실패'] };

  function embedCell(x) {  // only a file that holds documents has passages to embed
    const ix = x.index;
    if (!ix || !x.included) return '<span class="muted">-</span>';
    const [tone, word] = EMBED_STATE[ix.state] || ['', ix.state];
    const tip = ix.state === 'embedded' ? `청크 ${ix.chunks}` : ix.state === 'off' ? `문서 온톨로지에는 포함 · 청크 ${ix.passages}` : '';
    return `<label class="cemb"><input type="checkbox" data-in="cemb" data-path="${esc(x.path)}"${x.embed ? ' checked' : ''} aria-label="${esc(x.name)} 임베딩"><span class="chip sm ${tone}" title="${esc(tip)}">${word}</span></label>`;
  }

  // ---- what floats over the page: repository picker, row menu, file detail, screen search --------------------------

  function paintLayer() {
    const layer = $('#layer');
    const c = S.cat;
    let html = '';
    if (S.pick) {
      const rows = S.st.repositories.map((r) => `<button class="pitem${r.id === S.st.repository.id ? ' on' : ''}" data-act="repouse" data-id="${esc(r.id)}"><b>${esc(r.label)}</b><span class="muted">${count(r.files)}개 파일 · ${fileSize(r.bytes)}</span></button>`).join('');
      html += `<div class="pop" style="top:${S.pick.top}px;right:${S.pick.right}px" role="dialog" aria-label="저장소 선택"><div class="ptitle">저장소</div>${rows}
        <div class="pform"><input type="text" id="repolabel" value="${esc(S.pick.label || '')}" placeholder="저장소 이름" aria-label="저장소 이름"><button class="btn sm primary" data-act="repomake">추가</button></div>
        <div class="pfoot"><button class="btn sm ghost" data-act="reporename">이름 변경</button><button class="btn sm ghost danger" data-act="repodelete"${S.st.repositories.length > 1 ? '' : ' disabled'}>삭제</button></div></div>`;
    }
    if (S.menu) {
      const p = esc(S.menu.path);
      html += `<div class="menu" style="top:${S.menu.top}px;right:${S.menu.right}px" role="menu">${S.menu.folder
        ? `<button data-act="copen" data-path="${p}">열기</button>`
        : `<button data-act="cview" data-path="${p}">보기</button><a href="/api/catalog/download?path=${encodeURIComponent(S.menu.path)}">내려받기</a>`}
        <button data-act="crename" data-path="${p}">이름 변경</button>${S.menu.folder ? '' : `<div class="msub"><span class="muted">용도</span>${Object.entries(USE_WORD).map(([k, w]) => `<button data-act="cuse" data-path="${p}" data-v="${k}"${(S.menu.use || '') === k ? ' class="on"' : ''}>${w}</button>`).join('')}</div>`}<button class="bad" data-act="cdelete" data-path="${p}">삭제</button></div>`;
    }
    if (c.file) html += fileDrawer(c);
    if (S.pal) html += paletteBox();
    if (S.rp) html += pickerBox();
    html += issuePanel();
    const keep = layer.querySelector('#palq') || layer.querySelector('#rpq');
    const at = keep ? keep.selectionStart : null;
    const typing = document.activeElement && document.activeElement.id === 'repolabel';
    layer.innerHTML = html;
    const box = $('#palq') || $('#rpq');
    if (box) { box.focus(); if (at !== null) box.setSelectionRange(at, at); }
    if (typing && $('#repolabel')) $('#repolabel').focus();
    const menu = layer.querySelector('.menu');  // a row's menu near the bottom opens upward, inside the window
    if (menu) { const b = menu.getBoundingClientRect(); if (b.bottom > window.innerHeight - 8) menu.style.top = `${Math.max(8, window.innerHeight - b.height - 8)}px`; }
  }

  function fileDrawer(c) {
    const f = c.file;
    const facts = [['유형', kindChip(f)], ['크기', fileSize(f.bytes)], ['규모', esc(amount(f))], ['업로드일', esc(dayOf(f.uploaded))], ['처리 경로', esc(routeOf(f))], ['경로', `<span class="mono">${esc(f.path)}</span>`]];
    const table = (t) => `<div class="sec">${esc(t.sheet || t.name)} · ${count(t.rows)}행</div><div class="cwrap"><table class="tight"><tr>${t.columns.map((x) => `<th>${esc(x)}</th>`).join('')}</tr>${t.preview.map((r) => `<tr>${r.map((v) => `<td>${show(v)}</td>`).join('')}</tr>`).join('')}</table></div>`;
    const sections = f.sections.length ? `<div class="loglist">${f.sections.slice(0, 60).map((x) => `<div>${esc(x.title || x.document)} <span class="muted">${count(x.chars)}자</span></div>`).join('')}</div>` : '';
    const preview = f.tables.map(table).join('') + sections || '<div class="muted" style="font-size:12.5px">표시할 미리보기가 없습니다. JSON에서 내용을 확인합니다.</div>';
    const body = (f.facts || {}).kind === 'raw' ? '<div class="muted" style="font-size:12.5px">이미지, 영상, 압축 파일은 원본으로 보관합니다.</div>' : f.error ? `<div class="banner no"><div class="why">${esc(f.error)}</div></div>`
      : `<div class="seg"><button class="${c.view === 'preview' ? 'on' : ''}" data-act="cdview" data-v="preview">미리보기</button><button class="${c.view === 'json' ? 'on' : ''}" data-act="cdview" data-v="json">JSON</button></div>${c.view === 'json' ? `<pre class="code">${esc(f.json)}</pre>` : preview}`;
    return `<aside class="drawer" role="dialog" aria-label="${esc(f.name)}"><div class="dhead"><b>${esc(f.name)}</b><a class="btn sm" href="/api/catalog/download?path=${encodeURIComponent(f.path)}">내려받기</a><button class="iconbtn" data-act="cdclose" aria-label="닫기">${ui('close')}</button></div>
      <div class="dbody"><dl class="kv">${facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>${body}</div></aside>`;
  }

  // what the search reaches: every screen, and by name the things a person asks for most: an object's definition, a
  // decision table, a registered query. Each item says where it leads: [hash, label, where, icon key]
  function palItems() {
    const q = S.pal.q.trim().toLowerCase();
    const tabs = screenList().filter(([, l, where]) => !q || l.toLowerCase().includes(q) || where.toLowerCase().includes(q));
    if (!q) return tabs;
    const hit = (...xs) => xs.some((s) => String(s || '').toLowerCase().includes(q));
    const st = S.st;
    return [...tabs,
      ...st.graph.nodes.filter((n) => hit(n.label, n.id)).slice(0, 6).map((n) => [`objects?entity=${encodeURIComponent(n.id)}`, `${n.label || n.id}@${n.id}`, 'Entity', 'model']),
      ...st.decisions.filter((d) => hit(d.label, d.name)).slice(0, 4).map((d) => [`semrules`, d.label, '규칙 · 결정표', 'mgrules', d.name]),
      ...st.queries.filter((x) => hit(x.label, x.name)).slice(0, 4).map((x) => [`query?query=${encodeURIComponent(x.name)}`, x.label, '질의', 'query']),
      [`search?q=${encodeURIComponent(S.pal.q.trim())}`, S.pal.q.trim(), '질문', 'search']];
  }
  // an item picked in the search box; a decision table opens 규칙 with that table in its test
  function palOpen(item) {
    closeFloats();
    if (item[4] && typeof smrFresh === 'function') { smrFresh(); Object.assign(S.smr, { dec: item[4], vals: {}, key: '', res: null, simErr: '', agree: null, decFor: S.smr.sel }); }  // as the test's own 결정표 select
    if (location.hash === '#' + item[0]) render(); else location.hash = '#' + item[0];
  }

  function paletteBox() {
    const items = palItems();
    S.pal.i = Math.min(S.pal.i, Math.max(items.length - 1, 0));
    return `<div class="palback" data-act="palclose"></div><div class="pal" role="dialog" aria-label="메뉴 검색"><input type="text" id="palq" value="${esc(S.pal.q)}" placeholder="화면, Entity, 결정표, 질의 이름 또는 질문" aria-label="화면이나 정의 이름">
      <div class="pallist">${items.map(([k, l, where, icon], i) => `<a class="${i === S.pal.i ? 'on' : ''}" href="#${k}" data-act="palgo" data-i="${i}"><svg viewBox="0 0 24 24">${ICON[icon] || ICON.home}</svg><span>${esc(l)}</span><span class="muted">${esc(where)}</span></a>`).join('') || '<div class="muted" style="padding:10px 12px;font-size:12.5px">검색 결과가 없습니다.</div>'}</div></div>`;
  }

  function closeFloats() {
    if (!S.pick && !S.menu && !S.pal) return;
    S.pick = false; S.menu = null; S.pal = null;
    paintLayer();
  }

  // ---- convert: every file going into a draft, as the one JSON --------------------------------------------------

  async function loadConvert() {
    S.conv = { busy: true };
    try { S.conv = await api('catalog/convert'); } catch (e) { S.conv = { error: e.message }; }
    if (S.tab === 'convert') render();
  }

  function viewConvert() {
    const c = S.conv;
    const has = c && c.counts && Object.keys(c.counts).length;
    const head = `<div class="head"><div><h1>변환 결과</h1><div class="sub">초안 파일의 변환 결과를 조회합니다.</div></div>
      <div class="right">${has ? '<a class="btn sm" href="/api/catalog/json">JSON 내려받기</a>' : ''}<a class="btn sm primary" href="#data">초안 생성</a></div></div>`;
    if (!c || c.busy) return head + '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>';
    if (c.error) return head + `<div class="banner no"><div class="why">${esc(c.error)}</div></div>`;
    if (!c.rows.length) return head + '<div class="hint">업로드한 파일이 없습니다.</div>';
    const tiles = [['tables', '테이블'], ['columns', '컬럼'], ['references', '참조'], ['codes', '코드 그룹'], ['code_values', '코드값'], ['terms', '용어'], ['messages', '메시지'], ['documents', '문서']]
      .filter(([k]) => c.counts[k]).map(([k, l]) => `<div class="stat"><b>${count(c.counts[k])}</b><span>${l}</span></div>`).join('');
    const rows = c.rows.map((r) => {
      const f = { ...r, facts: r.facts };
      return `<tr class="${r.included && !r.error ? '' : 'off'}"><td class="mono">${esc(r.path)}</td><td>${kindChip(f)}</td><td>${amount(f)}</td><td>${r.error ? esc(r.error) : ((r.facts || {}).kind === 'raw' ? '원본 보관' : (r.included ? '포함' : '제외'))}</td></tr>`;
    }).join('');
    return `${head}${tiles ? `<div class="stats">${tiles}</div>` : ''}
      <div class="grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:start">
        <div class="card"><div class="ch">파일별 변환<span class="chip sm">${esc(c.repository.label)}</span></div><div class="cb scroll"><table class="tight"><tr><th>파일</th><th>유형</th><th>규모</th><th>상태</th></tr>${rows}</table></div></div>
        <div class="card"><div class="ch">통합 JSON<span class="chip sm">${fileSize(c.bytes)}</span></div><div class="cb">${c.json ? `<pre class="code cjson">${esc(c.json)}</pre>${c.cut ? '<div class="hint" style="margin-top:8px">앞부분 표시</div>' : ''}` : '<div class="muted" style="font-size:12.5px">초안에 포함한 파일이 없습니다.</div>'}</div></div></div>`;
  }

  // ---- control board: the pipeline as floors, every number from the space as it is now ---------------------------

  const ST_WORD = { ok: '정상', warn: '주의', bad: '장애', off: '꺼짐' };
  const hms = (v) => String(v || '').slice(11, 19);

  function spark(list) {
    if (list.length < 2) return '';
    const top = Math.max(...list, 1);
    const line = list.map((v, i) => `${(i / (list.length - 1) * 96).toFixed(1)},${(22 - v / top * 20).toFixed(1)}`).join(' ');
    return `<svg class="spark" viewBox="0 0 96 24" aria-hidden="true"><polyline points="${line}"/></svg>`;
  }

  function monitorBrief(m) {
    const cards = [...m.floors].reverse().map((f) => `<a class="mfloor st-${f.status}" href="#${f.tab}"${f.alerts ? ` data-act="issfloor" data-floor="${f.id}"` : ''}><div class="mfh"><b>${esc(f.no)} ${esc(f.label)}</b><span>${ST_WORD[f.status]}</span></div>
      <div class="mfn"><b>${f.alerts}</b> 알림</div><div class="mfk">${f.tags.slice(0, 3).map((t) => `<span>${esc(t.label)} <b>${esc(t.value)}</b></span>`).join('')}</div></a>`).join('');
    const clear = m.alerts.some((a) => a.level === 'bad') ? '' : '<div class="mclear"><span class="ic y" style="width:22px;height:22px">✓</span>모든 통과 조건을 충족했습니다.</div>';
    const events = m.events.length ? m.events.map((e) => `<div class="mevent"><span class="mono muted cn">${esc(hms(e.at))}</span><span>${esc(e.text)}</span></div>`).join('') : '<div class="muted" style="font-size:12.5px">최근 활동이 없습니다.</div>';
    const causes = m.issues.filter((x) => x.members.length).length;
    return `<div class="card mbrief"><h2>단계별 현황</h2>
      <div class="mfloors">${cards}</div>${clear}
      <div class="mcols"><div><div class="sec">활성 알림 ${m.alerts.length}${causes ? ` · 원인 ${causes}` : ''}</div>${issueList(m.issues)}</div><div><div class="sec">최근 활동</div><div class="mevents">${events}</div></div></div></div>`;
  }

  function monitorStrip(m) {
    const rtt = S.mon.rtt;
    return `<span class="mdot st-${m.status}"></span><span>파이프라인 상태 <b>${ST_WORD[m.status]}</b></span>
      <span>활성 알림 <b>${m.alerts.length}</b></span><span>통과 조건 <b>${m.gates.met} / ${m.gates.all}</b></span>
      <span>최근 점검 <b>${esc(hms(m.measured_at))}</b> <span class="muted">${count(m.took)}ms</span></span><span>접속자 <b>${count(m.visitors)}</b></span>
      <span class="mgrow"></span><span>응답 시간 <b>${rtt.length ? `${rtt[rtt.length - 1]}ms` : '-'}</b></span>${spark(rtt)}`;
  }

  const monitorTicker = (m) => (m.events[0] ? `<span class="mono">${esc(hms(m.events[0].at))}</span>${esc(m.events[0].text)}` : '');

  function mountMonitor() {
    const m = S.mon.st;
    if (m && $('#mscene')) {
      window.SpaceScene.mount($('#mscene'), m);
      S.mon.shape = m.shape;
      window.SpaceScene.focus(S.mon.focus);
    }
    if (!S.mon.st || !S.mon.timer) monitorTick();
  }

  async function monitorTick() {
    clearTimeout(S.mon.timer);
    if (S.mon.ticking) return;
    if (S.tab !== 'monitor') { S.mon.timer = 0; return; }
    S.mon.ticking = true;
    if (!document.hidden) {
      const start = performance.now();
      try {
        const m = await api('monitor');
        S.mon.rtt.push(Math.round(performance.now() - start));
        S.mon.rtt = S.mon.rtt.slice(-40);
        const first = !S.mon.st;
        S.mon.st = m;
        if (S.tab === 'monitor') {
          if (first || m.shape !== S.mon.shape || !$('#mscene')) {
            S.mon.ticking = false;
            S.mon.timer = setTimeout(monitorTick, 2000);
            render();
            return;
          }
          window.SpaceScene.patch(m);
          if (m.measured) window.SpaceScene.sweep();
          $('#mstrip').innerHTML = monitorStrip(m);
          $('#mtick').innerHTML = monitorTicker(m);
          $('#mbrief').innerHTML = monitorBrief(m);
        }
      } catch (e) { fail(e); }
    }
    S.mon.ticking = false;
    S.mon.timer = setTimeout(monitorTick, 2000);
  }

  // ---- database -------------------------------------------------------------------------------------------------

  // ---- management: data sources, objects, properties, relations, questions ---------------------------------------
  // Every edit lands in one overlay module ("관리 변경") over the standard modules, and reaches the other screens only
  // once it is filed as a change request and approved.

  const MG_TABS = ['model', 'sources', 'objects', 'props', 'links', 'states', 'mgrules', 'mgfuncs', 'actions', 'roles', 'objmgr', 'lexicon'];
  const OP_WORD = { add_object: 'Entity 추가', update_object: 'Entity 변경', delete_object: 'Entity 제외', add_property: '속성 추가',
    update_property: '속성 변경', delete_property: '속성 제외', add_link: '관계 추가', update_link: '관계 변경', delete_link: '관계 제외',
    add_question: '검증 질문 추가', delete_question: '검증 질문 제외', add_rule: '규칙 추가', update_rule: '규칙 변경', delete_rule: '규칙 제외',
    add_decision: '결정표 추가', update_parameter: '기준값 변경', add_action: 'Action 추가', update_action: 'Action 변경', delete_action: 'Action 제외',
    add_role: '역할 추가', update_role: '역할 변경', delete_role: '역할 제외', update_states: '상태 전이 변경',
    update_question: '검증 질문 정답 변경', pick_conflict: '출처 선택' };
  const MASK_WORD = { '': '가리지 않음', partial: '일부 가림', full: '전체 가림' };
  const IDENT = /^[A-Za-z_][A-Za-z0-9_]*$/;
  const sqlType = (t) => {
    const s = String(t || '').toLowerCase();
    if (/int|serial/.test(s)) return 'integer';
    if (/real|float|double|numeric|decimal|number|money/.test(s)) return 'decimal';
    if (/timestamp|datetime/.test(s)) return 'datetime';
    if (/^date/.test(s)) return 'date';
    if (/bool/.test(s)) return 'boolean';
    return 'string';
  };
  const propName = (c) => { let s = String(c).trim().toLowerCase().replace(/[^a-z0-9_]/g, '_'); if (!/^[a-z_]/.test(s)) s = 'c_' + s; return s; };
  const typeName = (t) => String(t).split(/[^A-Za-z0-9]+/).filter(Boolean).map((x) => x[0].toUpperCase() + x.slice(1).toLowerCase()).join('') || 'Item';
  const lowerFirst = (s) => s ? s[0].toLowerCase() + s.slice(1) : s;
  const mgObj = (name) => (S.mg.st.objects.find((o) => o.name === name) || null);
  const mgLabel = (name) => { const o = mgObj(name); return o ? o.label : name; };
  const linkLabel = (name) => { const l = S.mg.st.links.find((x) => x.name === name); return l ? (l.label || l.name) : name; };
  const mgTable = (name) => (S.mg.st.sources.source.tables.find((t) => t.table === name) || null);
  const mgProps = (obj) => S.mg.st.properties.filter((p) => p.object === obj);
  const opt = (v, label, cur) => `<option value="${esc(v)}"${String(v) === String(cur ?? '') ? ' selected' : ''}>${esc(label)}</option>`;
  const own = (x) => x.module === 'workspace';
  const valueText = (p, sep) => p.values.map((x) => ((p.labels || {})[x] ? `${x}=${p.labels[x]}` : x)).join(sep);

  async function loadManage() {
    S.mg.busy = true;
    try { S.mg.st = await api('manage'); } catch (e) { S.mg.st = { error: e.message }; }
    S.mg.busy = false;
    // the sidebar's maturity reads it on every screen, so a screen that reads it may be waiting on a load it did not start
    if (MG_TABS.includes(S.tab) || ['check', 'onto', 'lexicon'].includes(S.tab)) render(); else if (S.st) renderSide();
  }

  async function mgEdit(op, args, done) {
    S.mg.busy = true;
    try {
      const r = await api('manage/edit', { op, args });
      S.mg.st = r;
      const was = S.tab === 'model' && S.md.view === 'diagram' && S.mg.form && S.mg.form.mode === 'edit' && S.mg.sel ? [S.mg.form.kind, S.mg.sel] : null;
      if (op === 'add_object') S.md.sel = args.name;  // what was just made is what is worked on next
      S.mg.form = null;
      if (was && (was[0] === 'object' ? mgObj(was[1]) : was[0] === 'prop' ? r.properties.some((x) => `${x.object}.${x.name}` === was[1]) : was[0] === 'link' ? r.links.some((x) => x.name === was[1]) : false)) mgOpen(was[0], was[1], true);  // the workspace stays on what was just saved
      S.md.yaml = null; S.md.trial = null; S.md.data = null; S.md.hot = null;
      S.mg.review = null;
      if (S.fix && S.fix.phase === 'work') S.fix.phase = 'edited';
      const out = r.edit.took_out.length;
      toast(out ? `${done.replace(/\.$/, '')} · 함께 제외 ${out}개` : done);
    } catch (e) { fail(e); }
    S.mg.busy = false;
    render();
  }

  function mgHead(title, sub, right = '') {
    return `<div class="head"><div><h1>${title}</h1><div class="sub">${sub}</div></div><div class="right">${right}</div></div>`;
  }

  function mgWait(title, sub) {
    const m = S.mg.st;
    if (!m) return mgHead(title, sub) + '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>';
    if (m.error) return mgHead(title, sub) + `<div class="banner no"><div class="why">${esc(m.error)}</div></div>`;
    return '';
  }

  function pendingBar() {
    const w = S.mg.st.workspace;
    if (!w.dirty) return '';
    const d = w.diff;
    const tr = S.md.trial, tried = S.mg.open && tr && tr.gates;  // reviewed here: the list is open and the copy has run
    const edits = w.edits.map((e) => `<div><b>${esc(OP_WORD[e.op] || e.op)}</b> ${element(e.target)}${e.took_out.length
      ? `<div class="chips" style="margin-top:5px"><span class="muted" style="font-size:11.5px">함께 제외</span>${e.took_out.map(element).join('')}</div>` : ''}</div>`).join('');
    const issues = w.issues.length ? `<div class="banner no" style="margin-top:10px"><div class="loglist">${w.issues.slice(0, 6).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div>` : '';
    const body = S.mg.open ? `<div class="cb" style="border-top:1px solid var(--line)">
        ${edits ? `<div class="loglist">${edits}</div>` : '<div class="muted" style="font-size:12.5px">이전 세션의 변경</div>'}${issues}
        ${tr && tr.busy ? '<div class="muted" style="margin-top:10px"><span class="spin"></span> 사본에서 시험하는 중입니다</div>' : tr && tr.gates ? trialPanel(tr) : tr && tr.error ? `<div class="hint warn">${esc(tr.error)}</div>` : ''}
        <details class="wsyaml" style="margin-top:12px"><summary>정의 파일 보기 · ${esc(w.label)}</summary><pre class="code" style="max-height:260px;overflow:auto">${esc(w.yaml)}</pre></details></div>` : '';
    const review = S.mg.review ? `<div class="cb" style="border-top:1px solid var(--line)"><div class="banner no" style="margin:0 0 4px"><span class="ic x" style="width:24px;height:24px">!</span><div class="why">사본에서 통과 조건을 충족하지 못해 적용하지 못했습니다. 항목을 수정한 뒤 다시 요청해 주세요.</div></div>${changeReview(S.mg.review)}</div>` : '';
    return `<div class="card mgpend"><div class="ch"><span class="chip warn">대기 중인 변경 ${w.edits.length || ''}</span>
      <span class="muted" style="font-weight:600;font-size:12.5px">추가 ${d.added.length} · 변경 ${d.changed.length} · 제외 ${d.removed.length}</span>
      <div class="right"><button class="btn sm" data-act="mgopen">${S.mg.open ? '접기' : '내용 보기'}</button><button class="btn sm ghost" data-act="mgdiscard"${S.mg.busy ? ' disabled' : ''}>변경 취소</button>
      <button class="btn sm primary" data-act="${tried ? 'mgpropose' : 'mgreview'}"${S.mg.busy || w.issues.length || (tr && tr.busy) ? ' disabled' : ''}>${tried && selfApply() ? '적용' : fileWord()}</button></div></div>${review}${body}
      <div class="cb mgnote xp">표준 모듈은 그대로 두고 '${esc(w.label)}' 모듈에 확장 · 제외로 기록합니다. [${fileWord()}]을 선택하면 바뀐 내용과 사본에서 시험한 흐름 통과 조건을 먼저 보여 주고, ${selfApply() ? '[적용]을 선택하면' : '요청이 승인되면'} 질의 · 판정 · 검증 화면에 반영됩니다.</div></div>`;
  }

  const ownerChip = (x) => `<span class="chip sm${own(x) ? ' b' : ''}">${esc(x.module_label || x.module || '-')}</span>`;
  // an element's life, as its definition says it: being drafted, in use, going out of use
  const STATUS_WORD = { draft: ['warn', '초안'], active: ['ok', '사용 중'], deprecated: ['bad', '폐기 예정'] };
  const statusChip = (x) => { const s = STATUS_WORD[x && x.status] || STATUS_WORD.active; return `<span class="chip sm ${s[0]}">${s[1]}</span>`; };
  const statusSelect = (v) => `<select data-in="mgf" data-f="status">${Object.entries(STATUS_WORD).map(([k, [, w]]) => opt(k, w, v || 'active')).join('')}</select>`;
  // a reviewed draft replaces the shared space, so in a team an approver applies it; a visitor's own page is theirs
  const canApplyDraft = () => !(S.me && S.me.team) || !!(S.me.user && (S.me.user.roles || []).some((r) => r === 'approver' || r === 'admin'));
  const stateChips = (x) => `${statusChip(x)}${x.new ? '<span class="chip sm warn">새로 추가</span>' : (x.pending ? '<span class="chip sm warn">변경 대기</span>' : '')}`;
  // one visitor is both sides of a change, so filing the pending edits tries them on a copy and applies them at once;
  // in a team the same press files a request an approver decides. The words say which of the two will happen.
  const selfApply = () => !!(S.st && S.st.self_approve);
  const fileWord = (long) => (selfApply() ? '검토 후 적용' : long ? '변경 요청 만들기' : '변경 요청');
  const fileAsk = () => (selfApply() ? '작업 공간에서 [검토 후 적용]을 선택해 주세요.' : '작업 공간에서 변경 요청을 만들어 주세요.');

  // ---- data sources

  // ---- objects

  function identityCard() {
    const m = S.mg.st;
    const rows = m.identities.map((x) => `<tr class="${S.mg.sel === `identity:${x.name}` ? 'sel' : ''}" data-act="mgident" data-name="${esc(x.name)}" style="cursor:pointer"><td><b>${esc(x.label)}</b><div class="muted mono cn">${esc(x.name)}</div></td><td>${esc(Object.keys(x.members).map(mgLabel).join(', '))}</td><td>${x.rules.length}</td><td><div class="chips">${ownerChip(x)}</div></td></tr>`).join('');
    return `<div class="card"><div class="ch">식별 통합 <span class="chip sm">${m.identities.length}</span><div class="right"><button class="btn sm" data-act="mgidentnew">새 식별 통합</button></div></div><div class="cb scroll" style="padding:0">${rows ? `<table class="tight"><tr><th>이름</th><th>구성 Entity</th><th>규칙</th><th>정의</th></tr>${rows}</table>` : '<div class="empty">등록된 식별 통합이 없습니다.</div>'}</div></div>`;
  }

  function identityForm() {
    const f = S.mg.form && S.mg.form.kind === 'identity' ? S.mg.form : null;
    if (!f) return '<div></div>';
    const v = f.v, m = S.mg.st;
    const objects = m.objects.filter((o) => !o.concept).map((o) => [o.name, o.label]);
    const propsOf = (t) => [['', '속성 선택'], ...mgProps(t).map((p) => [p.name, p.label || p.name])];
    return `<div class="card"><div class="ch">${f.mode === 'new' ? '새 식별 통합' : `식별 통합 ${esc(v.label)}`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${f.mode === 'new' ? mgField('영문 이름', mgInput('name', v.name, 'placeholder="예: Person"')) : ''}${mgField('라벨', mgInput('label', v.label))}
      <div class="sec">구성 Entity와 비교 항목</div>${mgRows('imembers', (r, i) => `${rowSelect('imembers', i, 'type', objects, r.type)}${rowInput('imembers', i, 'field', r.field, '비교 항목 이름')}${rowSelect('imembers', i, 'prop', propsOf(r.type), r.prop)}`, v.imembers)}
      <div class="sec">통합 규칙</div>${mgRows('irules', (r, i) => `${rowInput('irules', i, 'id', r.id, '규칙 번호')}${rowInput('irules', i, 'match', r.match, '비교 항목, 쉼표로 구분')}${rowSelect('irules', i, 'normalize', [['none', '그대로'], ['digits', '숫자만'], ['lower', '소문자'], ['trim', '공백 제거']], r.normalize)}`, v.irules)}
      <div class="hint xp" style="margin-top:10px">승인 후 온톨로지 화면의 식별 통합에서 교차표를 저장합니다.</div>${mgButtons(f, '식별 통합 제외')}</div></div>`;
  }

  function objectForm() {
    const f = S.mg.form && S.mg.form.kind === 'object' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">Entity 정보</div><div class="cb"><div class="empty">선택된 Entity가 없습니다.</div></div></div>';
    const v = f.v, o = f.mode === 'edit' ? mgObj(v.name) : null;
    const tables = m.sources.source.tables;
    const tableSel = `<select data-in="mgf" data-f="table" data-re="1"><option value="">개념 · 테이블 없음</option>${tables.map((t) => opt(t.table, `${t.table}${t.objects.length && t.table !== (o || {}).table ? ` · ${t.objects.map(mgLabel).join(', ')}` : ''}`, v.table)).join('')}</select>`;
    const parents = `<select data-in="mgf" data-f="parent"><option value="">없음</option>${m.objects.filter((x) => x.name !== v.name).map((x) => opt(x.name, `${x.label} (${x.name})`, v.parent)).join('')}</select>`;
    const areaSel = (m.areas || []).length ? `<div class="field"><label>Object</label><select data-in="mgf" data-f="area"><option value="">${AREA_NONE}</option>${m.areas.map((a) => opt(a.name, `${a.label || a.name} · ${a.name}`, v.area)).join('')}</select></div>` : '';
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    if (f.mode === 'new') {
      const t = v.table ? mgTable(v.table) : null;
      const keySel = t ? `<select data-in="mgf" data-f="key">${t.columns.map((c) => opt(c.name, `${c.name} · ${c.type}`, v.key)).join('')}</select>`
        : `<input type="text" data-in="mgf" data-f="key" data-auto="1" value="${esc(v.key)}" placeholder="${esc(autoKey(v) || 'coupon_id')}" class="mono"><span class="muted" style="font-size:11.5px" data-hint="key">${esc(keyHint(v))}</span>`;
      return `<div class="card"><div class="ch">새 Entity<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
        ${field(`표시 이름${REQUIRED}`, `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}" placeholder="예: 쿠폰" aria-required="true">`)}
        ${nameField(f, '예: Coupon')}
        ${field('소스 테이블', tableSel)}
        ${t && t.key.length > 1 ? field('키', `<input type="text" value="${esc(t.key.join(', '))}" class="mono" disabled>`, '복합 키는 여러 컬럼을 하나의 값으로 읽습니다.') : field(t ? '키 컬럼' : '키 속성', keySel)}
        ${t && !t.key.length ? `<div class="hint" style="margin:-4px 0 12px">기본 키가 없는 테이블입니다. 값이 겹치지 않는 컬럼을 키로 선택해 주세요.</div>` : ''}
        ${t && t.links.length ? `<div class="hint" style="margin:-4px 0 12px">Relation ${esc(t.links.map(linkLabel).join(', '))}의 연결 테이블</div>` : ''}
        ${t ? `<label class="tick"><input type="checkbox" data-in="mgf" data-f="cols"${v.cols ? ' checked' : ''}>테이블 컬럼 ${t.columns.length}개를 속성으로 추가</label>` : ''}
        ${areaSel}${field('상위 Entity', parents)}
        ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>Entity 추가</button></div></div>`;
    }
    const keys = mgProps(v.name).filter((p) => !p.inherited);
    const keyField = own(o) ? `<select data-in="mgf" data-f="key">${keys.map((p) => opt(p.name, `${p.label || p.name} (${p.name})`, v.key)).join('')}</select>`
      : `<input type="text" value="${esc(v.key)}" disabled>`;
    return `<div class="card"><div class="ch">${esc(o.label)} <span class="muted mono" style="font-weight:600">${esc(o.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px">${o.area ? `<button class="chip sm b" data-act="mdarea" data-name="${esc(o.area)}">Object · ${esc(o.area_label || o.area)}</button>` : ''}${o.level_label ? `<span class="chip sm" title="L0 개념 · L1 논리 · L2 연결 · L3 검증">${esc(o.level_label)}</span>` : ''}<span class="nows">${ownerChip(o)}${stateChips(o)}</span><span class="chip sm">속성 ${o.properties}</span><span class="chip sm">관계 ${o.links}</span>${o.states ? '<span class="chip sm">상태 전이</span>' : ''}</div>
      ${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}">`)}
      ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}
      ${areaSel}${field('소스 테이블', tableSel)}
      ${field('키', keyField, own(o) ? '' : '다른 모듈 정의')}
      <div class="rgrid two">${field('상위 Entity', parents)}${field('상태', statusSelect(v.status))}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button><button class="btn ghost wsonly" data-act="mgcancel">접기</button>

        <div class="grow" style="flex:1"></div><button class="btn danger" data-act="mgdel"${S.mg.busy ? ' disabled' : ''}>Entity 제외</button></div></div></div>`;
  }

  // ---- properties

  function columnsOf(obj) {
    const o = mgObj(obj);
    const t = o && o.table ? mgTable(o.table) : null;
    return t ? t.columns : [];
  }

  function propForm() {
    const f = S.mg.form && S.mg.form.kind === 'prop' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">Property 정보</div><div class="cb"><div class="empty">선택된 Property가 없습니다.</div></div></div>';
    const v = f.v;
    const p = f.mode === 'edit' ? m.properties.find((x) => x.object === v.object && x.name === v.name) : null;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    const typeOk = !p || p.new || own(p);
    const iss = propIssues(v, f.mode);
    const types = `<select data-in="mgf" data-f="type" data-re="1"${typeOk ? '' : ' disabled'}>${TYPES.map((t) => opt(t, `${TYPE_WORD[t]} (${t})`, v.type)).join('')}</select>`;
    const used = new Set(mgProps(v.object).map((x) => (x.column || '').toLowerCase()));
    const near = (S.md.hot && S.md.hot.near || '').toLowerCase();
    const rank = (c) => (c.name.toLowerCase() === near ? 0 : used.has(c.name.toLowerCase()) ? 2 : 1);  // what could fit first
    const cols = [...columnsOf(v.object)].sort((a, b) => rank(a) - rank(b));
    const blank = S.md.hot && S.md.hot.field === 'column' ? '컬럼을 고르세요' : f.mode === 'new' ? '선택' : '이름과 같은 컬럼';
    const colSel = cols.length ? `<select data-in="mgf" data-f="column" data-re="1"><option value="">${blank}</option>${cols.map((c) => opt(c.name, `${c.name} · ${c.type}${used.has(c.name.toLowerCase()) && c.name !== v.column ? ' · 사용 중' : ''}`, v.column)).join('')}</select>`
      : `<input type="text" data-in="mgf" data-f="column" value="${esc(v.column)}" placeholder="소스 컬럼 이름">`;
    const sourced = !!(mgObj(v.object) || {}).table;  // a property of an object with no table reads no column
    const source = v.expr ? field('계산식', `<input type="text" data-in="mgf" data-f="expr" value="${esc(v.expr)}" class="mono">`)
      : !sourced ? '' : `${p && p.columns.length ? field('소스 컬럼', `<input type="text" value="${esc(p.columns.join(', '))}" class="mono" disabled>`, '복합 키는 여러 컬럼을 하나의 값으로 읽습니다.') : field('소스 컬럼', colSel)}
      ${p && p.columns.length ? '' : `<div class="rgrid two">${field('변환식', `<input type="text" data-in="mgf" data-f="transform" value="${esc(v.transform || '')}" class="mono" placeholder="예: value / 100">`, '소스 값: value')}
        ${field('소스 자료형', `<select data-in="mgf" data-f="source_type"><option value="">속성과 동일</option>${TYPES.filter((t) => t !== 'enum').map((t) => opt(t, TYPE_WORD[t], v.source_type || '')).join('')}</select>`)}</div>`}`;
    // what most properties leave as it is waits behind one closed 고급; it opens by itself when any of it holds a value
    const MORE = ['expr', 'column', 'transform', 'source_type', 'values', 'unit', 'mask', 'description', 'required', 'status'];
    const filled = MORE.some((k) => (k === 'status' ? (v.status || 'active') !== 'active' : !!v[k])) || !!iss.values || !!(S.md.hot && MORE.includes(S.md.hot.field));
    const common = `${field(f.mode === 'new' ? `표시 이름${REQUIRED}` : '라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}"${f.mode === 'new' ? ' placeholder="예: 별명" aria-required="true"' : ''}>`)}
      ${f.mode === 'new' ? nameField(f, '예: nickname') : ''}
      ${field(typeOk ? '자료형' : `자료형 · ${esc(p.module_label || '표준 모듈')}에서 정함`, types, '')}${fieldErr(iss.type)}
      <details class="mgmore" data-more="1"${(f.more ?? filled) ? ' open' : ''}><summary>고급 · ${sourced || v.expr ? '소스 컬럼, ' : ''}허용값, 단위, 가림, 상태, 필수, 설명</summary>
      ${source}
      ${field('허용값', `<input type="text" data-in="mgf" data-f="values" value="${esc(v.values)}" placeholder="쉼표로 구분, 예: BASIC, SILVER, VIP 또는 10=주문, 20=취소">`, '값=이름으로 적으면 코드값에 이름을 지정합니다.')}${fieldErr(iss.values)}
      <div class="rgrid two">${field('단위', `<input type="text" data-in="mgf" data-f="unit" value="${esc(v.unit)}" placeholder="예: 원">`)}
        ${field('가림', `<select data-in="mgf" data-f="mask">${Object.entries(MASK_WORD).map(([k, l]) => opt(k, l, v.mask)).join('')}</select>`)}</div>
      ${field('상태', statusSelect(v.status))}
      <label class="tick" style="margin-bottom:12px"><input type="checkbox" data-in="mgf" data-f="required"${v.required ? ' checked' : ''}>필수 값</label>
      ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}</details>`;
    if (f.mode === 'new') {
      return `<div class="card"><div class="ch">새 속성 · ${esc(mgLabel(v.object))}<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
        ${common}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>속성 추가</button></div></div>`;
    }
    const why = p.key ? `${p.name}${josa(p.name, '은', '는')} ${mgLabel(p.object)}의 키라서 제외할 수 없습니다.` : (p.inherited ? `상위 Entity ${mgLabel(p.inherited)}에서 상속한 Property라 제외할 수 없습니다. ${mgLabel(p.inherited)}에서 제외해 주세요.` : '');
    return `<div class="card"><div class="ch">${esc(mgLabel(p.object))} · ${esc(p.label || p.name)} <span class="muted mono" style="font-weight:600">${esc(p.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px"><span class="nows">${ownerChip(p)}${stateChips(p)}</span>${p.key ? '<span class="chip sm b">키</span>' : ''}</div>${common}
      <div style="display:flex;gap:8px;align-items:center"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button><button class="btn ghost wsonly" data-act="mgcancel">접기</button><div style="flex:1"></div>
        <button class="btn danger" data-act="mgdel"${why || S.mg.busy ? ' disabled' : ''} title="${esc(why)}">속성 제외</button></div>
      ${why ? `<div class="muted" style="font-size:11.5px;margin-top:6px;text-align:right">${esc(why)}</div>` : ''}</div></div>`;
  }

  // ---- relations

  function fkSuggestions() {
    const m = S.mg.st;
    const objOf = {};
    m.objects.forEach((o) => { if (o.table) (objOf[o.table] = objOf[o.table] || []).push(o.name); });
    const colProp = (obj, col) => (m.properties.find((p) => p.object === obj && !p.expr && (p.column || '').toLowerCase() === String(col).toLowerCase()) || {}).name;
    const has = new Set(m.links.filter((l) => l.on).flatMap((l) => [`${l.source}|${l.target}|${l.on[0]}|${l.on[1]}`, `${l.target}|${l.source}|${l.on[1]}|${l.on[0]}`]));
    const names = new Set(m.links.flatMap((l) => [l.name, l.inverse]).filter(Boolean));
    const out = [];
    for (const t of m.sources.source.tables) {
      for (const fk of t.fks) {
        for (const a of objOf[t.table] || []) {
          for (const b of objOf[fk.table] || []) {
            const sp = colProp(a, fk.column), tp = colProp(b, fk.ref);
            if (!sp || !tp || has.has(`${a}|${b}|${sp}|${tp}`)) continue;
            let name = lowerFirst(b), i = 2;
            while (names.has(name)) name = lowerFirst(b) + i++;
            names.add(name);
            out.push({ name, source: a, target: b, sp, tp, column: `${t.table}.${fk.column} → ${fk.table}.${fk.ref}` });
          }
        }
      }
    }
    return out;
  }

  function linkForm() {
    const f = S.mg.form && S.mg.form.kind === 'link' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">관계 정보</div><div class="cb"><div class="empty">관계를 선택하면 라벨, Cardinality, 역관계를 수정할 수 있습니다. [새 관계]로 두 Entity를 연결합니다.</div></div></div>';
    const v = f.v;
    const l = f.mode === 'edit' ? m.links.find((x) => x.name === v.name) : null;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    const ends = !l || own(l);
    const objSel = (k) => `<select data-in="mgf" data-f="${k}" data-re="1"${ends ? '' : ' disabled'}><option value="">선택</option>${m.objects.map((o) => opt(o.name, `${o.label} (${o.name})`, v[k])).join('')}</select>`;
    const propSel = (k, obj) => `<select data-in="mgf" data-f="${k}"${ends && obj ? '' : ' disabled'}><option value="">선택</option>${(obj ? mgProps(obj) : []).filter((p) => !p.expr).map((p) => opt(p.name, `${p.label || p.name} (${p.name})${p.key ? ' · 키' : ''}`, v[k])).join('')}</select>`;
    const cards = `<select data-in="mgf" data-f="cardinality">${Object.entries(CARD).map(([k, x]) => opt(k, `${x} (${k})`, v.cardinality)).join('')}</select>`;
    const body = `${f.mode === 'new' ? field('영문 이름', `<input type="text" data-in="mgf" data-f="name" value="${esc(v.name)}" placeholder="예: usedCoupon">`) : ''}
      ${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}" placeholder="예: 사용 쿠폰">`)}
      <div class="rgrid two">${field('출발 Entity', objSel('source'))}${field('출발 Property', propSel('sp', v.source))}</div>
      <div class="rgrid two">${field('도착 Entity', objSel('target'))}${field('도착 Property', propSel('tp', v.target))}</div>
      ${ends ? '' : '<div class="muted" style="font-size:11.5px;margin:-4px 0 10px">양 끝 Entity · 연결 기준 · 다른 모듈 정의</div>'}
      <div class="rgrid two">${field('Cardinality', cards)}${field('역관계 이름', `<input type="text" data-in="mgf" data-f="inverse" value="${esc(v.inverse)}" placeholder="예: couponUsedBy">`)}</div>
      ${f.mode === 'new' ? '' : field('상태', statusSelect(v.status))}
      <label class="tick" style="margin-bottom:12px"><input type="checkbox" data-in="mgf" data-f="required"${v.required ? ' checked' : ''}>필수 관계</label>`;
    if (f.mode === 'new') {
      return `<div class="card"><div class="ch">새 관계<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">${body}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>관계 추가</button></div></div>`;
    }
    return `<div class="card"><div class="ch">${esc(l.label || l.name)} <span class="muted mono" style="font-weight:600">${esc(l.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px">${ownerChip(l)}${stateChips(l)}</div>${body}
      <div style="display:flex;gap:8px"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button><button class="btn ghost wsonly" data-act="mgcancel">접기</button><div style="flex:1"></div>
        <button class="btn danger" data-act="mgdel"${S.mg.busy ? ' disabled' : ''}>관계 제외</button></div></div></div>`;
  }

  // ---- questions (on the 검증 screen)

  // ---- edits from the forms

  // ---- rules, named values, states, actions and roles: the same way as an object, an edit and then a change request

  const CELL_OPS = { any: '조건 없음', eq: '같음', ne: '다름', lte: '이하', gte: '이상', lt: '미만', gt: '초과', in: '다음 중 하나', notin: '다음 제외', null: '값 없음', notnull: '값 있음', raw: '직접 입력' };
  // a condition typed the way people say it ("14일 이하", "NORMAL 아님", "A, B 중", "값 없음", "조건 없음") becomes a comparison
  // and a value; null when the text is a plain value, which stays as typed
  function cellPhrase(text, i, op) {
    const t = String(text || '').trim();
    if (!t || !i) return null;
    const plain = (s) => {
      s = s.trim();
      if (i.type === 'boolean') return ['예', 'true', '참'].includes(s) ? 'true' : ['아니요', 'false', '거짓'].includes(s) ? 'false' : s;
      return Object.keys(i.labels || {}).find((x) => i.labels[x] === s) || s;
    };
    if (['조건 없음', '아무거나', '-', '–', '—'].includes(t)) return { op: 'any', value: '' };
    if (['값 없음', '없음', '비어 있음'].includes(t)) return { op: 'null', value: '' };
    if (['값 있음', '있음'].includes(t)) return { op: 'notnull', value: '' };
    let m = t.match(/^(.+?)\s*(이하|까지|이상|부터|미만|초과)$/);
    if (m) { const n = m[1].replace(/[,\s]/g, '').match(/-?\d+(\.\d+)?/); if (n) return { op: { 이하: 'lte', 까지: 'lte', 이상: 'gte', 부터: 'gte', 미만: 'lt', 초과: 'gt' }[m[2]], value: n[0] }; }
    m = t.match(/^(.+?)\s*(아님|아닌|제외|빼고)$/);
    if (m) { const list = m[1].split(',').map(plain).filter(Boolean); return list.length > 1 ? { op: 'notin', value: list.join(',') } : { op: 'ne', value: list[0] || '' }; }
    m = t.match(/^(.+?)\s*(중 하나|중에|중)$/);
    if (m) return { op: 'in', value: m[1].split(',').map(plain).filter(Boolean).join(',') };
    if (t.includes(',') && !['in', 'notin'].includes(op)) return { op: 'in', value: t.split(',').map(plain).filter(Boolean).join(',') };
    if (i.type === 'boolean' && ['예', '아니요', '참', '거짓'].includes(t)) return { op: 'eq', value: plain(t) };
    const k = Object.keys(i.labels || {}).find((x) => i.labels[x] === t);
    return k ? { op: 'eq', value: k } : null;
  }
  const cellHint = (i, op) => (op === 'in' || op === 'notin' ? '쉼표로 구분' : ['integer', 'decimal', 'number'].includes(i.type) ? `예: 14${i.unit || ''} 이하` : i.type === 'boolean' ? '예 · 아니요' : '예: NORMAL 아님');
  const opsOf = (type) => (['integer', 'decimal', 'number', 'float', 'date', 'datetime'].includes(type) ? ['any', 'eq', 'ne', 'lte', 'gte', 'lt', 'gt', 'null', 'notnull']
    : (type === 'boolean' ? ['any', 'eq'] : ['any', 'eq', 'ne', 'in', 'notin', 'null', 'notnull']));
  const mgField = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${esc(hint)}</span>` : ''}</div>`;
  const mgInput = (f, v, extra = '') => `<input type="text" data-in="mgf" data-f="${f}" value="${esc(v ?? '')}" ${extra}>`;
  const mgButtons = (f, del) => `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button>${f.mode === 'edit' && del ? `<button class="btn danger" style="margin-left:auto" data-act="mgdel"${S.mg.busy ? ' disabled' : ''}>${del}</button>` : ''}</div>`;
  const mgEmpty = (title, text) => `<div class="card"><div class="ch">${title}</div><div class="cb"><div class="empty">${text}</div></div></div>`;
  const mgRows = (list, cols, rows) => `<div class="mgrows">${rows.map((r, i) => `<div class="mgrow">${cols(r, i, list)}<button class="iconbtn" data-act="mgrowdel" data-list="${list}" data-i="${i}" aria-label="행 삭제">×</button></div>`).join('')}<button class="btn sm" data-act="mgrowadd" data-list="${list}">행 추가</button></div>`;
  const rowInput = (list, i, f, v, hold) => `<input type="text" data-in="mgrow" data-list="${list}" data-i="${i}" data-f="${f}" value="${esc(v ?? '')}" placeholder="${esc(hold)}">`;
  const rowSelect = (list, i, f, options, v) => `<select data-in="mgrow" data-list="${list}" data-i="${i}" data-f="${f}">${options.map(([k, l]) => opt(k, l, v)).join('')}</select>`;

  const outWord = (d, name) => (name === 'reason' ? '사유' : (d.outputs[0].name === name || d.outputs[0] === name ? (d.outputs[0].type === 'boolean' || typeof d.outputs[0] === 'string' ? '결과' : d.label) : name));

  function ruleValue(i, part) {
    const name = `data-in="mgwhen" data-k="${esc(i.name)}" data-p="value"`;
    if (['any', 'null', 'notnull'].includes(part.op)) return '';
    if (i.type === 'boolean') return `<select ${name}>${[['true', '예'], ['false', '아니요']].map(([k, l]) => opt(k, l, part.value)).join('')}</select>`;
    if (i.values.length && ['eq', 'ne'].includes(part.op)) return `<select ${name}>${i.values.map((x) => opt(x, i.labels[x] || x, part.value)).join('')}</select>`;
    return `<input type="text" ${name} value="${esc(part.value)}" placeholder="${esc(cellHint(i, part.op))}" title="예: 14일 이하, NORMAL 아님, A, B 중, 값 없음">`;
  }

  function ruleForm(d) {
    const f = S.mg.form && S.mg.form.kind === 'rule' ? S.mg.form : null;
    if (!f) return mgEmpty('규칙 정보', '선택된 규칙이 없습니다.');
    const v = f.v;
    const conds = d.inputs.map((i) => {
      const part = v.when[i.name] || { op: 'any', value: '' };
      const ops = part.op === 'raw' ? ['raw'] : opsOf(i.type);
      return `<div class="mgcond"><span>${esc(i.label)}</span><select data-in="mgwhen" data-k="${esc(i.name)}" data-p="op" data-re="1">${ops.map((o) => opt(o, CELL_OPS[o], part.op)).join('')}</select>${ruleValue(i, part)}</div>`;
    }).join('');
    const outs = d.outputs.map((o) => {
      const val = v.then[o.name], word = outWord(d, o.name);
      if (o.type === 'boolean') return mgField(word, `<select data-in="mgthen" data-k="${esc(o.name)}" data-t="boolean">${[['true', '예'], ['false', '아니요']].map(([k, l]) => opt(k, l, String(val))).join('')}</select>`);
      return mgField(word, `<input type="text" data-in="mgthen" data-k="${esc(o.name)}" data-t="${esc(o.type)}" value="${esc(val ?? '')}">`);
    }).join('');
    return `<div class="card"><div class="ch">${f.mode === 'new' ? '새 규칙' : `규칙 ${esc(v.id)}`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${f.mode === 'new' ? mgField('규칙 번호', mgInput('id', v.id, 'placeholder="예: gold-window"')) : ''}
      <div class="sec" style="margin-top:0">조건</div>${conds}
      <div class="sec">적용 결과</div>${outs}
      ${mgField('출처', mgInput('cite', v.cite, 'placeholder="예: 반품 정책서 v1.2 3조"'))}
      ${f.mode === 'new' ? `<label class="tick"><input type="checkbox" data-in="mgf" data-f="first"${v.first ? ' checked' : ''}>기존 규칙보다 먼저 적용</label>` : ''}
      ${(d.rules.find((r) => r.id === v.id) || {}).layer === 'axiom' ? '<div class="hint">AXIOM 규칙 · 읽기 전용</div>' : mgButtons(f, '규칙 제외')}</div></div>`;
  }

  function paramForm() {
    const f = S.mg.form && S.mg.form.kind === 'param' ? S.mg.form : null;
    if (!f) return '';
    const v = f.v, fresh = f.mode === 'new';
    return `<div class="card"><div class="ch">${fresh ? '새 기준값' : `기준값 ${esc(v.label)}`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${fresh ? `${mgField('영문 이름', mgInput('name', v.name, 'placeholder="예: free_shipping_over"'), '영문자로 시작, 영문자 · 숫자 · _ 사용')}
        ${mgField('자료형', `<select data-in="mgf" data-f="type">${[['integer', '정수'], ['decimal', '소수'], ['string', '문자열'], ['boolean', '참 · 거짓']].map(([k, l]) => opt(k, l, v.type)).join('')}</select>`)}` : ''}
      ${mgField('라벨', mgInput('label', v.label))}${mgField('값', mgInput('value', v.value))}
      <div class="rgrid two">${mgField('단위', mgInput('unit', v.unit))}${mgField('출처', mgInput('cite', v.cite))}</div>
      <div class="rgrid two">${mgField('최솟값', mgInput('min', v.min))}${mgField('최댓값', mgInput('max', v.max))}</div>
      ${fresh ? '' : `<div class="hint">${(v.readers || []).length ? `사용처 · ${esc(v.readers.join(', '))}` : '사용처 없음'}</div>`}${mgButtons(f, '기준값 제외')}</div></div>`;
  }

  // a condition as rows of the form: {property, op, value}; one the form cannot say stays as it was written
  const WHERE_OPS = [['eq', '같음'], ['ne', '다름'], ['lt', '미만'], ['lte', '이하'], ['gt', '초과'], ['gte', '이상'], ['not_null', '값 있음'], ['is_null', '값 없음']];
  const typedValue = (x) => (x === 'true' ? true : x === 'false' ? false : (x !== '' && !Number.isNaN(Number(x)) ? Number(x) : x));
  const oneCond = (w) => {
    const k = Object.keys(w || {})[0];
    if (['not_null', 'is_null'].includes(k)) return { property: String(w[k]).split('.').pop(), op: k, value: '' };
    if (WHERE_OPS.some(([o]) => o === k) && Array.isArray(w[k])) return { property: String(w[k][0]).split('.').pop(), op: k, value: String(w[k][1]) };
    return null;
  };
  const condRows = (w) => {
    if (!w) return [];
    const list = (w.and || [w]).map(oneCond);
    return list.every(Boolean) ? list : null;
  };
  const condSpec = (rows, alias) => {
    const list = rows.filter((r) => r.property).map((r) => (['not_null', 'is_null'].includes(r.op) ? { [r.op]: `${alias}.${r.property}` } : { [r.op]: [`${alias}.${r.property}`, typedValue(r.value)] }));
    return list.length > 1 ? { and: list } : list[0];
  };
  const AGG_WORD = [['count', '건수'], ['sum', '합계'], ['avg', '평균'], ['min', '최솟값'], ['max', '최댓값']];
  const aggOf = (part) => { const v = (part || {}).value || {}; const fn = Object.keys(v)[0] || 'count'; return { fn, prop: String(v[fn] || '').includes('.') ? String(v[fn]).split('.').pop() : '' }; };

  function metricForm() {
    const f = S.mg.form && S.mg.form.kind === 'metric' ? S.mg.form : null;
    if (!f) return '';
    const v = f.v, m = S.mg.st;
    const props = [['', '대상 자체'], ...mgProps(v.object).map((p) => [p.name, p.label || p.name])];
    const conds = (list) => mgRows(list, (r, i) => `${rowSelect(list, i, 'property', props.slice(1), r.property)}${rowSelect(list, i, 'op', WHERE_OPS, r.op)}${rowInput(list, i, 'value', r.value, '값')}`, v[list]);
    const fixed = f.raw ? '<div class="hint">식이 여러 Entity를 잇고 있어 대상과 조건은 라이브러리의 모듈 편집에서 수정합니다.</div>' : `
      ${mgField('대상 Entity', `<select data-in="mgf" data-f="object" data-re="1">${(m.objects.some((o) => !o.concept) ? m.objects.filter((o) => !o.concept) : m.objects).map((o) => opt(o.name, o.label, v.object)).join('')}</select>`)}
      <div class="rgrid two">${mgField('집계', `<select data-in="mgf" data-f="fn">${AGG_WORD.map(([k, l]) => opt(k, l, v.fn)).join('')}</select>`)}${mgField('집계 속성', `<select data-in="mgf" data-f="prop">${props.map(([k, l]) => opt(k, l, v.prop)).join('')}</select>`)}</div>
      <div class="sec">조건</div>${conds('where')}
      <label class="tick" style="margin-top:10px"><input type="checkbox" data-in="mgf" data-f="ratio" data-re="1"${v.ratio ? ' checked' : ''}>분모로 나누어 비율로 표시</label>
      ${v.ratio ? `<div class="sec">분모 조건</div>${conds('den')}${mgField('분모 이름', mgInput('den_label', v.den_label))}` : ''}`;
    return `<div class="card"><div class="ch">${f.mode === 'new' ? '새 지표' : `지표 ${esc(v.label)}`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${f.mode === 'new' ? mgField('영문 이름', mgInput('name', v.name, 'placeholder="예: cancelRate"')) : ''}
      ${mgField('라벨', mgInput('label', v.label))}${mgField('담당', mgInput('owner', v.owner), '필수')}
      ${fixed}
      <div class="rgrid two">${mgField('단위', mgInput('unit', v.unit))}${mgField('배율', mgInput('scale', v.scale), '백분율은 100')}</div>
      ${mgField('기준 시각', mgInput('basis', v.basis, 'placeholder="예: 주문 일시"'), '필수')}
      ${f.raw ? '' : mgField('기준 시각 속성', `<select data-in="mgf" data-f="time_prop"><option value="">없음</option>${mgProps(v.object).filter((p) => ['date', 'datetime'].includes(p.type)).map((p) => opt(p.name, p.label || p.name, v.time_prop)).join('')}</select>`)}
      ${mgField('설명', mgInput('description', v.description))}${mgField('출처', mgInput('cite', v.cite))}
      ${mgButtons(f, '지표 제외')}</div></div>`;
  }

  function metricCard() {
    const m = S.mg.st;
    const rows = m.metrics.map((x) => `<tr class="${S.mg.sel === `metric:${x.name}` ? 'sel' : ''}" data-act="mgmetric" data-name="${esc(x.name)}" style="cursor:pointer"><td><b>${esc(x.label)}</b><div class="muted mono cn">${esc(x.name)}</div></td><td>${esc(x.owner || '-')}</td><td>${esc(x.unit || '-')}</td><td><div class="chips">${ownerChip(x)}${stateChips(x)}</div></td></tr>`).join('');
    return `<div class="card"><div class="ch">지표 <span class="chip sm">${m.metrics.length}</span><div class="right"><button class="btn sm" data-act="mgmetricnew">새 지표</button></div></div><div class="cb scroll" style="padding:0">${rows ? `<table class="tight"><tr><th>이름</th><th>담당</th><th>단위</th><th>정의</th></tr>${rows}</table>` : '<div class="empty">지표가 없습니다.</div>'}</div></div>`;
  }

  function decisionForm() {
    const f = S.mg.form && S.mg.form.kind === 'decision' ? S.mg.form : null;
    if (!f) return '';
    const v = f.v, m = S.mg.st;
    const props = m.properties.filter((p) => p.object === v.target);
    const hops = m.links.filter((l) => l.source === v.target).flatMap((l) => m.properties.filter((p) => p.object === l.target).map((p) => ({ ...p, via: l })));
    const options = [['', '선택'], ...props.map((p) => [p.name, p.label || p.name]), ...hops.map((p) => [`${p.via.name}.${p.name}`, `${mgLabel(p.object)} · ${p.label || p.name}`])];
    return `<div class="card"><div class="ch">새 결정표<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${mgField('영문 이름', mgInput('name', v.name, 'placeholder="예: exchangeEligibility"'))}${mgField('라벨', mgInput('label', v.label, 'placeholder="예: 교환 가능 여부"'))}
      ${mgField('대상 Entity', `<select data-in="mgf" data-f="target" data-re="1">${m.objects.map((o) => opt(o.name, o.label, v.target)).join('')}</select>`)}
      <div class="sec">입력값</div>${mgRows('inputs', (r, i) => rowSelect('inputs', i, 'property', options, r.property), v.inputs)}
      ${mgField('규칙에 맞지 않는 경우 사유', mgInput('otherwise', v.otherwise))}${mgButtons(f, '')}</div></div>`;
  }

  // ---- a decision table edited and tried at once: how it applies its rules, cells said and changed in place, rows
  //      moved by dragging, what overlaps, a simulator on a real record, and the tests run on the table as edited --

  const POLICY_WORD = { first: '위에서 첫 규칙', priority: '우선순위가 높은 규칙', collect: '맞는 규칙 모두', unique: '하나만 맞아야 함' };
  const modWord = (name) => (name === S.mg.st.workspace.module ? S.mg.st.workspace.label : modLabel(name));

  function cellSay(c) {  // a finding's cell in a person's words: "<= 7" is 7 이하
    const s = String(c).trim();
    const m = s.match(/^(<=|>=|<|>|!=|=)\s*(.+)$/);
    const v = (x) => ({ true: '예', false: '아니요', null: '값 없음' }[x] || x.replace(/^"|"$/g, ''));
    if (m) return `${v(m[2])} ${{ '<=': '이하', '>=': '이상', '<': '미만', '>': '초과', '!=': '아님', '=': '' }[m[1]]}`.trim();
    // numbers and ranges that run on into each other read as one range: 0 | 1..6 | 7 is 0~7
    const parts = s.replace(/^\[|\]$/g, '').split('|').map((x) => x.trim());
    const spans = parts.map((x) => { const q = x.match(/^(-?\d+(?:\.\d+)?)(?:\.\.(-?\d+(?:\.\d+)?))?$/); return q ? [Number(q[1]), Number(q[2] ?? q[1])] : null; });
    if (spans.every(Boolean)) {
      const merged = [];
      spans.sort((a, b) => a[0] - b[0]).forEach(([lo, hi]) => { const last = merged[merged.length - 1]; if (last && lo <= last[1] + 1) last[1] = Math.max(last[1], hi); else merged.push([lo, hi]); });
      return merged.map(([lo, hi]) => (lo === hi ? String(lo) : `${lo}~${hi}`)).join(' 또는 ');
    }
    return parts.map((x) => v(x)).join(' 또는 ');
  }

  function overlapSay(d, f) {
    const where = Object.entries(f.where || {}).map(([k, c]) => `${(d.inputs.find((i) => i.name === k) || { label: k }).label} ${cellSay(c)}`).join(' · ');
    const [a, b] = f.rules;
    const how = f.severity === 'warning' ? '두 규칙의 답이 달라 어느 쪽을 쓸지 정해야 합니다.'
      : d.hit_policy === 'first' ? `위에서 첫 규칙인 ${a}${josa(a, '이', '가')} 적용됩니다.` : '우선순위가 높은 규칙이 적용됩니다.';
    return `${a}${josa(a, '과', '와')} ${b}${josa(b, '이', '가')} ${where}에서 겹칩니다. ${how}`;
  }

  function findingsBar(d) {
    if (!S.ru) return '';
    const fs = (S.ru.findings || []).filter((f) => f.decision === d.name);
    const n = (k) => fs.filter((f) => f.kind === k).length;
    const warn = fs.filter((f) => f.severity === 'warning');
    const sel = fs.find((f) => f.kind === 'overlap' && f.rules.includes(S.mg.sel));
    const shown = warn[0] || sel;
    const say = shown ? (shown.kind === 'overlap' || shown.kind === 'tie' ? overlapSay(d, shown) : shown.detail)
      : n('overlap') ? `겹침 처리 · ${POLICY_WORD[d.hit_policy]}` : '검사 통과';
    return `<div class="fbar${warn.length ? ' warn' : ''}"><b>검사</b><span>겹침 ${n('overlap') + n('tie')}${warn.length ? ` (확인 ${warn.length})` : ''}</span><span>도달 불가 ${n('unreachable')}</span><span>빈 구간 ${n('gap')}</span>
      <span class="muted"${shown ? '' : ''}>${esc(say)}</span></div>`;
  }

  function rulesHead(d) {
    const extra = d.rules.filter((r) => r.module && r.module !== d.module);
    const by = {};
    extra.forEach((r) => { by[r.module] = (by[r.module] || 0) + 1; });
    const policy = `<label class="chip n chipsel">적용 방식 · <select data-in="mgpolicy" aria-label="적용 방식"${canEdit() ? '' : ' disabled'}>${Object.entries(POLICY_WORD).filter(([k]) => k !== 'priority' || d.hit_policy === 'priority').map(([k, w]) => opt(k, w, d.hit_policy)).join('')}</select></label>`;
    return `<div class="rhead2"><div><div class="rtitle2"><h2>${esc(d.label)}</h2><span class="mono muted cn">${esc(d.name)}</span></div>
      <div class="chips" style="margin-top:7px">${policy}${d.target ? `<button class="chip" data-act="select" data-obj="${esc(d.target)}" title="이 Entity의 정의로">대상 · ${esc(d.target_label || d.target)}</button>` : ''}<button class="chip b" data-act="libshow" data-mod="${esc(d.module)}" title="라이브러리에서 이 모듈로">${esc(shortMod(modWord(d.module)))}</button>
        ${Object.entries(by).map(([mname, k]) => `<button class="chip warn" data-act="libshow" data-mod="${esc(mname)}" title="라이브러리에서 이 모듈로">+ ${esc(shortMod(modWord(mname)))} 규칙 ${k}</button>`).join('')}${stateChips(d)}</div></div>
      <div class="right"><a class="btn sm" href="/api/export/jdm?decision=${encodeURIComponent(d.name)}" download title="GoRules ZEN JSON">내보내기</a><button class="btn sm" data-act="mgrulenew">규칙 추가</button></div></div>`;
  }

  function ruleCell(d, r, i) {
    if (r.layer === 'axiom') return `<td title="AXIOM 규칙 · 읽기 전용">${esc(r.said[i.name])}</td>`;  // read where it stands
    const c = S.mg.cell;
    if (c && c.rule === r.id && c.input === i.name) {
      const part = c.part;
      const ops = part.op === 'raw' ? ['raw'] : opsOf(i.type);
      const val = ['any', 'null', 'notnull'].includes(part.op) ? '' : (i.type === 'boolean' ? `<select data-in="cellv">${[['true', '예'], ['false', '아니요']].map(([k, l]) => opt(k, l, part.value)).join('')}</select>`
        : i.values.length && ['eq', 'ne'].includes(part.op) ? `<select data-in="cellv">${i.values.map((x) => opt(x, i.labels[x] || x, part.value)).join('')}</select>`
          : `<input type="text" data-in="cellv" value="${esc(part.value)}" style="width:110px" placeholder="${esc(cellHint(i, part.op))}" title="예: 14일 이하, NORMAL 아님, 값 없음">`);
      return `<td class="cellon"><div class="celled"><select data-in="cellop">${ops.map((o) => opt(o, CELL_OPS[o], part.op)).join('')}</select>${val}
        <button class="iconbtn" data-act="cellsave" aria-label="저장">✓</button><button class="iconbtn" data-act="cellx" aria-label="취소">×</button></div></td>`;
    }
    return `<td class="celltd" data-act="celledit" data-rule="${esc(r.id)}" data-k="${esc(i.name)}" title="편집">${esc(r.said[i.name])}</td>`;
  }

  // the open cell's text read as a comparison and a value ("14일 이하"); null when it is a plain value
  const cellSaid = () => { const c = S.mg.cell, d = S.mg.st.decisions.find((x) => x.name === S.mg.dec); return cellPhrase(c.part.value, d && d.inputs.find((x) => x.name === c.input), c.part.op); };
  function cellFocus(all) {  // the open cell takes the keyboard: Enter saves, Escape cancels
    const e = $('.celled [data-in="cellv"]') || $('.celled [data-in="cellop"]');
    if (!e) return;
    e.focus();
    if (all && e.select) e.select();
  }

  // a number in a condition changed: the reasons that still say the old number are named, with one press to follow
  const numAt = (n) => new RegExp(`(^|[^\\d.])${String(n).replace('.', '\\.')}(?![\\d.])`, 'g');
  function staleCheck(dec, from, to) {
    S.mg.stale = null;
    const a = String(from ?? '').trim(), b = String(to ?? '').trim();
    if (!/^\d+(\.\d+)?$/.test(a) || !/^\d+(\.\d+)?$/.test(b) || a === b) return;
    const d = S.mg.st.decisions.find((x) => x.name === dec);
    const hits = d ? d.rules.filter((r) => Object.values(r.then || {}).some((v) => typeof v === 'string' && numAt(a).test(v))) : [];
    if (hits.length) S.mg.stale = { decision: dec, from: a, to: b, rules: hits.map((r) => r.id) };
  }
  function staleBar(d) {
    const s = S.mg.stale;
    if (!s || s.decision !== d.name) return '';
    return `<div class="hint warn stalebar"><span><b>사유 문구 ${s.rules.length}곳에 변경 전 값 ${esc(s.from)}${josa(s.from, '이', '가')} 남아 있습니다</b> · ${s.rules.map(esc).join(', ')}</span>
      <span class="chips"><button class="btn sm primary" data-act="stalefix">${esc(s.to)}${josa(s.to, '으로', '로')} 변경</button><button class="btn sm ghost" data-act="staleskip">그대로 두기</button></span></div>`;
  }
  function rulesEdited() {  // a table edited: tried and checked again as it now stands, past cases included
    S.ru = null;
    if (S.sim.key) simulateNow(S.sim.key, S.sim.vals);
    api('rules').then((x) => { S.ru = x; if (S.tab === 'mgrules') render(); }).catch(fail);
    if (S.agree && S.agree.ok !== false) loadAgreement();
  }

  async function moveRule(id, to) {
    const d = S.mg.st.decisions.find((x) => x.name === S.mg.dec);
    if (!d || d.rules.findIndex((r) => r.id === id) === to) return;
    S.mg.sel = id;
    await mgEdit('move_rule', { decision: d.name, id, to }, `규칙 ${id}의 순서를 바꿨습니다.`);
    rulesEdited();
  }

  function rulesTable(d) {
    const hitNow = S.sim.res && S.sim.dec === d.name ? S.sim.res.matched : [];
    const fs = ((S.ru || {}).findings || []).filter((f) => f.decision === d.name);
    const warn = new Set(fs.filter((f) => f.severity === 'warning').flatMap((f) => f.rules));
    const near = new Set(fs.filter((f) => f.kind === 'overlap' && f.rules.includes(S.mg.sel)).flatMap((f) => f.rules).filter((x) => x !== S.mg.sel));
    const rows = d.rules.map((r) => `<tr class="${S.mg.sel === r.id ? 'sel' : ''}${hitNow.includes(r.id) ? ' hitrow' : ''}${warn.has(r.id) || near.has(r.id) ? ' warnrow' : ''}"${r.layer === 'axiom' ? '' : ` draggable="true" data-drag-rule="${esc(r.id)}"`}>
      <td class="draghandle" aria-hidden="true">⋮⋮</td>
      <td class="mono" style="white-space:nowrap;cursor:pointer" data-act="mgrule" data-name="${esc(r.id)}"><b>${esc(r.id)}</b> ${layerChip(r.layer)}${hitNow.includes(r.id) ? ' <span class="chip sm ok">적중</span>' : ''}${near.has(r.id) ? ' <span class="chip sm warn">겹침</span>' : ''}
        ${r.cite ? `<div><span class="chip sm${r.module && r.module !== d.module ? ' warn' : ''}" style="margin-top:3px">${esc(r.cite)}</span></div>` : ''}</td>
      ${d.inputs.map((i) => ruleCell(d, r, i)).join('')}${d.outputs.map((o, k) => `<td style="min-width:${o.name === 'reason' ? 150 : 70}px${k === 0 ? ';border-left:2px solid var(--line)' : ''}">${yesNo((r.gives || r.then)[o.name])}</td>`).join('')}</tr>`).join('');
    const reads = S.mg.st.parameters.filter((p) => (p.readers || []).some((x) => x.startsWith(`${d.label} ·`)));
    const params = reads.length ? `<div class="cb rparams"><span class="label">기준값</span>${reads.map((p) => `<button class="chip" data-act="mgparam" data-name="${esc(p.name)}">@${esc(p.name)} <b>${show(p.value)}${p.unit ? ` ${esc(p.unit)}` : ''}</b></button>`).join('')}</div>` : '';
    return `${staleBar(d)}<div class="card"><div class="cb scroll" style="padding:0"><table class="tight rtable" style="font-size:12.5px"><tr><th></th><th>규칙</th>${d.inputs.map((i) => `<th>${esc(i.label)}</th>`).join('')}${d.outputs.map((o, k) => `<th${k === 0 ? ' style="border-left:2px solid var(--line)"' : ''}>→ ${esc(outWord(d, o.name))}</th>`).join('')}</tr>${rows}
      <tr><td colspan="${2 + d.inputs.length + d.outputs.length}" class="muted" style="padding:10px;font-size:12px"><button class="btn sm" data-act="mgrulenew">+ 규칙 추가</button></td></tr></table></div>${params}</div>`;
  }

  function testCard(d) {
    const r = S.sim.res && S.sim.dec === d.name ? S.sim.res : null;
    const a = S.agree && S.agree.ok && S.agree.decision === d.name ? S.agree : null;
    const qs = r ? r.questions : null;
    const okq = qs ? qs.filter((q) => q.passed).length : 0;
    const flips = r ? r.edges.filter((e) => e.verdict !== r.verdict).length : 0;
    const edges = r && S.sim.edges ? `<table class="tight" style="font-size:12.5px;margin-top:6px"><tr><th>입력</th><th>값</th><th>결과</th><th>규칙</th></tr>${r.edges.map((e) => `<tr><td>${esc(e.label)}</td><td class="mono">${typeof e.value === 'boolean' ? yesNo(e.value) : esc(String(e.value))}</td><td><span class="chip sm ${e.yes ? 'ok' : 'warn'}">${esc(e.verdict)}</span></td><td class="mono muted">${esc(e.matched.join(', '))}</td></tr>`).join('')}</table>` : '';
    const failing = qs ? qs.filter((q) => !q.passed).map((q) => `<div class="hint warn" style="margin:6px 0 0"><b>${esc(q.id)}</b> ${esc(q.text)} · 기대 ${esc(JSON.stringify(q.expect || {}))} → 결과 ${esc(q.error || JSON.stringify(q.got || {}))}</div>`).join('') : '';
    return `<div class="card"><div class="ch">테스트${r && r.pending ? '<span class="chip sm warn">대기 중인 변경 반영</span>' : ''}</div><div class="cb">
      <div class="hrow static"><div><b>과거 판정 다시 계산</b><div class="muted" style="font-size:12px">${a ? `${a.cases}건 중 ${a.agree}건 일치` : '과거 사례 없음'}</div></div>${a ? `<span class="chip sm ${a.rate === 1 ? 'ok' : 'warn'}" style="margin-left:auto">${pct(a.rate)}</span>` : ''}</div>
      <div class="hrow static"><div><b>경계값 자동 생성</b><div class="muted" style="font-size:12px">${r ? `규칙이 비교하는 값의 앞뒤 ${r.edges.length}건 · 결과가 바뀌는 값 ${flips}건` : '레코드 미선택'}</div></div>${r ? `<button class="btn sm ghost" data-act="simedges" style="margin-left:auto">${S.sim.edges ? '접기' : '보기'}</button>` : ''}</div>${edges}
      <div class="hrow static"><div><b>검증 질문</b><div class="muted" style="font-size:12px">${qs ? `이 결정표를 쓰는 질문 ${qs.length}개` : '레코드 미선택'}</div></div>${qs ? `<span class="chip sm ${okq === qs.length ? 'ok' : 'bad'}" style="margin-left:auto">${okq} / ${qs.length}</span>` : ''}</div>${failing}
    </div></div>`;
  }

  function viewMgRules() {
    const title = '결정표', sub = '결정표의 규칙과 기준값을 관리합니다.';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    if (!S.mg.dec || !m.decisions.some((d) => d.name === S.mg.dec)) S.mg.dec = (m.decisions[0] || {}).name || '';
    const d = m.decisions.find((x) => x.name === S.mg.dec);
    const pick = `<select data-in="mgdec" style="width:220px">${m.decisions.map((x) => opt(x.name, x.label, S.mg.dec)).join('')}</select>`;
    const head = mgHead(title, sub, `${pick}<button class="btn sm" data-act="mgparamnew">기준값 추가</button><button class="btn sm" data-act="mgdecnew">새 결정표</button>`);
    const params = m.parameters.length ? `<div class="card" data-mgparams="1"><div class="ch">기준값 <span class="chip sm">${m.parameters.length}</span></div><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>이름</th><th>값</th><th>범위</th><th>정의</th></tr>${m.parameters.map((p) => `<tr class="${S.mg.sel === `param:${p.name}` ? 'sel' : ''}" data-act="mgparam" data-name="${esc(p.name)}" style="cursor:pointer"><td><b>${esc(p.label)}</b><div class="muted mono cn">@${esc(p.name)}</div></td><td>${show(p.value)}${p.unit ? ` ${esc(p.unit)}` : ''}</td><td>${p.min === null && p.max === null ? '-' : `${p.min ?? ''} ~ ${p.max ?? ''}`}</td><td><div class="chips">${ownerChip(p)}${stateChips(p)}</div></td></tr>`).join('')}</table></div></div>` : '';
    if (!d) return `${head}${pendingBar()}${params}${metricCard()}${paramForm()}${metricForm()}${decisionForm() || mgEmpty('결정표', '결정표가 없습니다. [새 결정표]로 만듭니다.')}`;
    return `${head}${pendingBar()}${rulesHead(d)}${findingsBar(d)}<div class="grid" style="grid-template-columns:minmax(0,1.65fr) minmax(330px,1fr);align-items:start"><div class="hcol">${rulesTable(d)}${params}${metricCard()}</div>
      <div class="hcol">${decisionForm()}${paramForm()}${metricForm()}${S.mg.form && ['param', 'metric', 'decision'].includes(S.mg.form.kind) ? '' : (S.mg.form && S.mg.form.kind === 'rule' ? ruleForm(d) : '')}${simCard(d)}${testCard(d)}</div></div>`;
  }

  const RUNTIME = [['expr', '계산식'], ['decision', '결정표'], ['query', '등록 질의'], ['python', 'Python'], ['http', '외부 호출']];
  const FN_STATUS = [['active', '사용'], ['draft', '초안'], ['retired', '중단']];

  function functionForm() {
    const f = S.mg.form && S.mg.form.kind === 'function' ? S.mg.form : null;
    if (!f) return mgEmpty('함수 정보', '선택된 함수가 없습니다.');
    const v = f.v, m = S.mg.st;
    const by = {
      expr: mgField('계산식', mgInput('expr', v.expr, 'class="mono" placeholder="예: line_total * @rate"'), '속성 · 이름, 입력값 · @이름'),
      decision: mgField('결정표', `<select data-in="mgf" data-f="decision"><option value="">선택</option>${m.decisions.map((d) => opt(d.name, d.label, v.decision)).join('')}</select>`),
      query: mgField('등록 질의', `<select data-in="mgf" data-f="query"><option value="">선택</option>${m.queries.map((q) => opt(q.name, q.label, v.query)).join('')}</select>`),
      python: mgField('등록 이름', mgInput('entry', v.entry), 'studio 파일 functions.python 의 등록 이름'),
      http: `${mgField('호출 주소', mgInput('url', v.url, 'class="mono" placeholder="https://service.example/score/$key"'), '허용 호스트 · $key, $row.속성, $입력값 사용')}
        <div class="rgrid two">${mgField('방식', `<select data-in="mgf" data-f="method">${['POST', 'GET'].map((x) => opt(x, x, v.method)).join('')}</select>`)}${mgField('응답 경로', mgInput('path', v.path, 'placeholder="예: data"'))}</div>`,
    }[v.runtime] || '';
    return `<div class="card"><div class="ch">${f.mode === 'new' ? '새 함수' : `함수 ${esc(v.label || v.name)}`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${f.mode === 'new' ? mgField('영문 이름', mgInput('name', v.name, 'placeholder="예: refundEstimate"')) : ''}
      ${mgField('라벨', mgInput('label', v.label))}
      <div class="rgrid two">${mgField('실행 방식', `<select data-in="mgf" data-f="runtime" data-re="1">${RUNTIME.map(([k, l]) => opt(k, l, v.runtime)).join('')}</select>`)}
        ${mgField('대상 Entity', `<select data-in="mgf" data-f="target"><option value="">없음</option>${(m.objects.some((o) => !o.concept) ? m.objects.filter((o) => !o.concept) : m.objects).map((o) => opt(o.name, o.label, v.target)).join('')}</select>`)}</div>
      ${by}
      <div class="sec">입력값</div>${mgRows('fin', (r, i) => `${rowInput('fin', i, 'name', r.name, '영문 이름')}${rowInput('fin', i, 'label', r.label, '라벨')}${rowSelect('fin', i, 'type', TYPES.filter((t) => t !== 'enum').map((t) => [t, TYPE_WORD[t]]), r.type)}`, v.fin)}
      <div class="sec">출력값</div>${mgRows('fout', (r, i) => `${rowInput('fout', i, 'name', r.name, '영문 이름')}${rowSelect('fout', i, 'type', TYPES.filter((t) => t !== 'enum').map((t) => [t, TYPE_WORD[t]]), r.type)}`, v.fout)}
      <div class="rgrid two">${mgField('버전', mgInput('version', v.version))}${mgField('담당', mgInput('owner', v.owner))}</div>
      <div class="rgrid two">${mgField('상태', `<select data-in="mgf" data-f="status">${FN_STATUS.map(([k, l]) => opt(k, l, v.status)).join('')}</select>`)}${mgField('외부 의존', mgInput('depends', v.depends, 'placeholder="쉼표로 구분"'))}</div>
      ${mgField('설명', mgInput('description', v.description))}${mgField('출처', mgInput('cite', v.cite))}
      ${mgButtons(f, '함수 제외')}</div></div>`;
  }

  function functionRun() {
    const f = S.mg.form && S.mg.form.kind === 'function' && S.mg.form.mode === 'edit' ? S.mg.form : null;
    if (!f) return '';
    const x = S.mg.st.functions.find((y) => y.name === f.v.name), r = S.mg.fnres;
    if (!x) return '';
    const inputs = Object.keys(x.inputs).map((k) => mgField(esc((x.inputs[k] || {}).label || k), `<input type="text" data-in="fnin" data-k="${esc(k)}" value="${esc((S.mg.fnin || {})[k] ?? '')}">`)).join('');
    const out = r ? (r.ok ? `<div class="sec">결과 · 버전 ${esc(r.version)}</div><table class="tight">${Object.entries(r.outputs).map(([k, val]) => `<tr><td class="mono">${esc(k)}</td><td>${Array.isArray(val) ? `${val.length}행` : show(val)}</td></tr>`).join('')}</table>
      ${(r.evidence || []).filter((e) => e.property).length ? `<div class="sec">사용한 값</div><table class="tight">${r.evidence.filter((e) => e.property).map((e) => `<tr><td class="mono">${esc(e.property)}</td><td>${show(e.value)}</td></tr>`).join('')}</table>` : ''}` : `<div class="hint" style="margin-top:10px">${esc(r.error)}</div>`) : '';
    return `<div class="card"><div class="ch">실행</div><div class="cb">${x.target ? mgField(`${esc(mgLabel(x.target))} 번호`, `<input type="text" data-in="fnkey" value="${esc(S.mg.fnkey || '')}">`) : ''}${inputs}
      <button class="btn primary" data-act="fnrun"${S.mg.busy ? ' disabled' : ''}>실행</button>${out}</div></div>`;
  }

  function viewMgFunctions() {
    const title = '함수', sub = '계산 · 판정 · 외부 호출 함수를 관리합니다.';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    const head = mgHead(title, sub, '<button class="btn sm primary" data-act="mgfnnew">새 함수</button>');
    const word = (list, k) => (list.find((x) => x[0] === k) || [k, k])[1];
    const rows = m.functions.map((x) => `<tr class="${S.mg.sel === x.name ? 'sel' : ''}" data-act="mgfn" data-name="${esc(x.name)}" style="cursor:pointer"><td><b>${esc(x.label)}</b><div class="muted mono cn">${esc(x.name)}</div></td><td>${esc(word(RUNTIME, x.runtime))}</td><td>${esc(x.target ? mgLabel(x.target) : '-')}</td><td class="mono">${esc(x.version)}</td><td>${esc(x.owner || '-')}</td><td><span class="chip sm${x.status === 'active' ? ' ok' : ''}">${esc(word(FN_STATUS, x.status))}</span></td><td><div class="chips">${ownerChip(x)}${stateChips(x)}</div></td></tr>`).join('');
    return `${head}${pendingBar()}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(340px,1fr);align-items:start">
      <div class="card"><div class="ch">함수 <span class="chip sm">${m.functions.length}</span></div><div class="cb scroll" style="padding:0">${rows ? `<table class="tight"><tr><th>함수</th><th>실행 방식</th><th>대상</th><th>버전</th><th>담당</th><th>상태</th><th>정의</th></tr>${rows}</table>` : '<div class="empty">등록된 함수가 없습니다.</div>'}</div></div>
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${functionForm()}${functionRun()}</div></div>`;
  }

  function stateForm() {
    const f = S.mg.form && S.mg.form.kind === 'states' ? S.mg.form : null;
    if (!f) return mgEmpty('상태 전이 정보', '선택된 상태 전이가 없습니다.');
    const v = f.v, m = S.mg.st;
    const props = m.properties.filter((p) => p.object === v.object);
    const states = String(v.states || '').split(',').map((x) => x.trim()).filter(Boolean);
    const choices = states.map((s) => [s, s]);
    return `<div class="card"><div class="ch">${f.mode === 'new' ? '새 상태 전이' : `${esc(mgLabel(v.object))} 상태 전이`}<div class="right"><button class="btn sm ghost" data-act="mgclose">닫기</button></div></div><div class="cb">
      ${f.mode === 'new' ? mgField('Entity', `<select data-in="mgf" data-f="object" data-re="1">${m.objects.filter((o) => !o.states).map((o) => opt(o.name, o.label, v.object)).join('')}</select>`) : ''}
      ${mgField('상태 속성', `<select data-in="mgf" data-f="property">${props.map((p) => opt(p.name, p.label || p.name, v.property)).join('')}</select>`)}
      ${mgField('상태 값', mgInput('states', v.states, 'data-re="1" placeholder="쉼표로 구분"'))}
      ${mgField('초기 상태', `<select data-in="mgf" data-f="initial"><option value="">없음</option>${states.map((s) => opt(s, s, v.initial)).join('')}</select>`)}
      <div class="sec">전이</div>${mgRows('transitions', (r, i) => `${rowSelect('transitions', i, 'from', choices, r.from)}<span class="muted">→</span>${rowSelect('transitions', i, 'to', choices, r.to)}${rowInput('transitions', i, 'action', r.action, 'Action')}`, v.transitions)}
      ${mgButtons(f, '')}</div></div>`;
  }

  function viewStates() {
    const title = '상태 전이', sub = 'Entity의 상태 값과 전이를 관리합니다.';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    const head = mgHead(title, sub, '<button class="btn sm primary" data-act="mgstatenew">새 상태 전이</button>');
    const rows = m.states.map((s) => `<tr class="${S.mg.sel === s.object ? 'sel' : ''}" data-act="mgstate" data-name="${esc(s.object)}" style="cursor:pointer"><td><b>${esc(s.label)}</b><div class="muted mono cn">${esc(s.object)}.${esc(s.property)}</div></td>
      <td><div class="chips">${s.states.map((x) => `<span class="chip sm${x === s.initial ? ' b' : ''}">${esc(x)}</span>`).join('')}</div></td><td>${s.transitions.length}</td><td><div class="chips">${ownerChip(s)}${stateChips(s)}</div></td></tr>`).join('');
    return `${head}${pendingBar()}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(340px,1fr);align-items:start">
      <div class="card"><div class="ch">상태 전이 <span class="chip sm">${m.states.length}</span></div><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>Entity</th><th>상태</th><th>전이</th><th>정의</th></tr>${rows}</table></div></div>${stateForm()}</div>`;
  }

  const LIMIT_KIND = [['percent', '변화율 이내 (%)'], ['delta', '변화폭 이내'], ['max', '최댓값 이하'], ['min', '최솟값 이상']];

  // why a request waits: past a limit, or inside every limit but asked by an agent the action does not let run alone
  const waitWord = (p) => ({ agent: '자동 승인 기준 안이지만 Agent 요청은 자동 실행을 허용하지 않아 승인 대기로 접수했습니다.',
    right: '자동 승인 기준 안이지만 요청 역할에 실행 권한이 없어 승인 대기로 접수했습니다.' })[p.waits] || (p.status === 'pending' ? '자동 승인 기준을 넘어 승인 대기로 접수했습니다.' : '');

  function actionTry() {
    const f = S.mg.form && S.mg.form.kind === 'action' && S.mg.form.mode === 'edit' ? S.mg.form : null;
    const a = f && S.mg.st.actions.find((x) => x.name === f.v.name);
    if (!a) return '';
    const roles = (S.st.roles || []).map((r) => [r.name, r.label || r.name]);
    const t = S.mg.actry = S.mg.actry && S.mg.actry.action === a.name ? S.mg.actry : { action: a.name, key: '', role: (roles[roles.length - 1] || [''])[0], kind: 'human', params: {}, res: null };
    const inputs = a.parameters.map((p) => mgField(esc(p.label || p.name), `<input type="text" data-in="actry" data-k="${esc(p.name)}" value="${esc(t.params[p.name] ?? '')}">`)).join('');
    const p = t.res && t.res.proposal;
    const [cls, word] = p ? (STATUS[p.status] || ['', p.status]) : ['', ''];
    const out = t.res ? (p ? `<div class="sec">결과</div><div class="chips"><span class="chip ${cls}">${esc(word)}</span>${p.approved_by === 'auto' ? '<span class="chip sm ok">자동 승인</span>' : ''}</div>
      ${(p.limits || []).map((l) => `<div class="muted" style="font-size:12.5px;margin-top:6px">${esc(p.labels[l.subject] || l.subject)} ${l.value === null ? '-' : show(Math.round(l.value * 100) / 100)}${l.kind === 'percent' ? '%' : ''} / 기준 ${show(l.limit)}${l.kind === 'percent' ? '%' : ''}</div>`).join('')}
      ${p.status === 'pending' && waitWord(p) ? `<div class="hint" style="margin-top:6px">${esc(waitWord(p))}</div>` : ''}
      ${p.checks.filter((c) => !c.passed).map((c) => `<div class="hint" style="margin-top:6px">${esc(c.title)} ${esc(c.detail)}</div>`).join('')}` : `<div class="hint" style="margin-top:10px">${esc(t.res.error)}</div>`) : '';
    return `<div class="card"><div class="ch">요청</div><div class="cb">${mgField(`${esc(mgLabel(a.target))} 번호`, `<input type="text" data-in="actrykey" value="${esc(t.key)}">`)}${inputs}
      ${mgField('요청 역할', `<select data-in="actryrole">${roles.map(([k, l]) => opt(k, l, t.role)).join('')}</select>`)}
      ${mgField('요청자', `<select data-in="actrykind">${[['human', '사람'], ['agent', 'Agent']].map(([k, l]) => opt(k, l, t.kind)).join('')}</select>`, 'Agent 요청은 Action에서 Agent 자동 실행을 허용한 경우에만 기준 안에서 바로 실행합니다.')}
      <button class="btn primary" data-act="actrygo"${S.mg.busy ? ' disabled' : ''}>요청</button>${out}</div></div>`;
  }

  const hopsOf = (t) => [['', '직접'], ...S.mg.st.links.filter((l) => l.source === t || l.target === t).map((l) => [l.source === t ? l.name : (l.inverse || l.name), `${l.label || l.name} · ${mgLabel(l.source === t ? l.target : l.source)}`])];
  const hopEnd = (t, step) => { const l = S.mg.st.links.find((x) => x.name === step || x.inverse === step); return !l ? t : (l.name === step ? l.target : l.source); };
  const hopProps = (r) => [['', '속성 선택'], ...mgProps(r.via ? hopEnd(r.type, r.via) : r.type).map((p) => [p.name, p.label || p.name])];
  const roleObjects = () => S.mg.st.objects.filter((o) => !o.concept).map((o) => [o.name, o.label]);

  function mgOpenMore(kind, key) {
    const m = S.mg.st;
    S.mg.sel = key;
    if (kind === 'rule') {
      const d = m.decisions.find((x) => x.name === S.mg.dec), r = d.rules.find((x) => x.id === key);
      S.mg.form = { kind, mode: 'edit', v: { id: r.id, cite: r.cite, when: JSON.parse(JSON.stringify(r.when)), then: { ...r.then } } };
    }
    if (kind === 'param') {
      const p = m.parameters.find((x) => x.name === key);
      S.mg.sel = `param:${key}`;
      S.mg.form = { kind, mode: 'edit', v: { ...p } };
    }
    if (kind === 'states') {
      const s = m.states.find((x) => x.object === key);
      S.mg.form = { kind, mode: 'edit', v: { object: s.object, property: s.property, states: s.states.join(', '), initial: s.initial, transitions: s.transitions.map((t) => ({ ...t })) } };
    }
    if (kind === 'action') {
      const a = m.actions.find((x) => x.name === key);
      const criteria = a.criteria.filter((c) => c.decision).flatMap((c) => Object.entries(c.expect).map(([field, value]) => ({ decision: c.decision, field, value: String(value) })));
      const limits = a.auto_within.flatMap((l) => LIMIT_KIND.filter(([k]) => k in l).map(([k]) => ({ subject: l.property ? `p:${l.property}` : `i:${l.parameter}`, kind: k, value: String(l[k]) })));
      const set = Object.entries(a.set).map(([prop, value]) => ({ prop, value: String(value) }));
      const body = a.call.body === undefined ? '' : (typeof a.call.body === 'string' ? a.call.body : JSON.stringify(a.call.body));
      S.mg.form = { kind, mode: 'edit', keep: a.criteria.filter((c) => !c.decision), call: a.call, undo: a.undo, v: { name: a.name, label: a.label, target: a.target, params: a.parameters.map((p) => ({ ...p })), criteria, set, limits, agents: a.auto_agents, method: a.call.method || 'POST', url: a.call.url || '', body, undo_url: a.undo.url || '', transition_to: a.transition_to, approval: a.approval, cite: a.cite } };
    }
    if (kind === 'metric') {
      const x = m.metrics.find((y) => y.name === key);
      S.mg.sel = `metric:${key}`;
      const match = x.formula.match || {}, alias = Object.keys(match)[0], where = condRows(x.formula.where), den = condRows((x.denominator || {}).where), agg = aggOf(x.formula);
      const raw = Object.keys(match).length !== 1 || where === null || den === null || !!x.formula.edges;
      S.mg.form = { kind, mode: 'edit', raw, orig: x, v: { name: x.name, label: x.label, owner: x.owner, object: match[alias] || '', fn: agg.fn, prop: agg.prop, where: where || [], den: den || [], ratio: !!Object.keys(x.denominator || {}).length, den_label: (x.denominator || {}).label || '', unit: x.unit, scale: x.scale, basis: (x.time || {}).basis || '', time_prop: String((x.time || {}).property || '').split('.').pop(), description: x.description, cite: x.cite } };
    }
    if (kind === 'identity') {
      const x = m.identities.find((y) => y.name === key);
      S.mg.sel = `identity:${key}`;
      const imembers = Object.entries(x.members).flatMap(([type, fields]) => Object.entries(fields).map(([field, prop]) => ({ type, field, prop })));
      const irules = x.rules.map((r) => ({ id: r.id, match: r.match.join(', '), normalize: Object.values(r.normalize)[0] || 'none' }));
      S.mg.form = { kind, mode: 'edit', v: { name: x.name, label: x.label, imembers, irules } };
    }
    if (kind === 'function') {
      const x = m.functions.find((y) => y.name === key);
      const fin = Object.entries(x.inputs).map(([name, s]) => ({ name, label: (s || {}).label || name, type: (typeof s === 'string' ? s : (s || {}).type) || 'string' }));
      S.mg.form = { kind, mode: 'edit', call: x.call, v: { name: x.name, label: x.label, runtime: x.runtime, target: x.target, expr: x.expr, decision: x.decision, query: x.query, entry: x.entry, url: x.call.url || '', method: x.call.method || 'POST', path: x.call.path || '', fin, fout: Object.entries(x.outputs).map(([name, type]) => ({ name, type })), version: x.version, owner: x.owner, status: x.status, depends: x.depends.join(', '), description: x.description, cite: x.cite } };
    }
    if (kind === 'role') {
      const r = m.roles.find((x) => x.name === key);
      const rows = r.rows.map((x) => (x.raw ? { ...x } : { type: x.type, via: (x.via || [])[0] || '', property: x.property, mode: x.principal ? 'principal' : 'value', value: x.principal || String(x.value ?? '') }));
      const scopes = Object.entries((r.scope || {}).types || {}).map(([type, w]) => (typeof w === 'string' ? { type, via: '', property: w } : { type, via: (w.via || [])[0] || '', property: w.property }));
      S.mg.form = { kind, mode: 'edit', v: { name: r.name, label: r.label, read: [...r.read], run: [...r.run], request: [...r.request], mask: Object.entries(r.mask).map(([prop, style]) => ({ prop, style })), rows, scope_attr: (r.scope || {}).attribute || '', scopes, docs: r.documents === null || r.documents === undefined ? ['*'] : [...r.documents] } };
    }
    if (S.mg.form && S.mg.form.mode === 'edit') S.mg.form.seen = JSON.stringify(S.mg.form.v);
    render();
  }

  const NEW_ROW = { params: { name: '', label: '', type: 'string' }, criteria: { decision: '', field: '', value: '' }, transitions: { from: '', to: '', action: '' }, mask: { prop: '', style: 'partial' }, inputs: { property: '' },
    set: { prop: '', value: '' }, limits: { subject: '', kind: 'percent', value: '' }, rows: { type: '', via: '', property: '', mode: 'principal', value: '' }, scopes: { type: '', via: '', property: '' },
    where: { property: '', op: 'eq', value: '' }, den: { property: '', op: 'eq', value: '' }, imembers: { type: '', field: '', prop: '' }, irules: { id: '', match: '', normalize: 'none' }, fin: { name: '', label: '', type: 'string' }, fout: { name: '', type: 'decimal' } };

  function mgSaveMore(f) {
    const v = f.v;
    if (f.mode === 'edit' && f.seen !== undefined && JSON.stringify(v) === f.seen) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return true; }
    if (f.kind === 'area') {
      if (f.mode === 'new') {
        (async () => {
          if (!String(v.label || '').trim()) { formStop('label', '이름이 비어 있어 Object를 추가하지 못했습니다. 이름을 입력해 주세요.'); return; }
          if (!v.name) await nameNow(f);
          if (S.mg.form !== f) return;
          if (!v.name || !IDENT.test(v.name) || nameIssue(f)) { formStop('name', '영문 이름을 쓸 수 없어 Object를 추가하지 못했습니다. 영문 이름 칸 아래 안내대로 고쳐 주세요.'); return; }
          S.md.areaPick = v.name;
          await mgEdit('add_area', { name: v.name, label: v.label || '', description: v.description || '', cite: v.cite || '', ...(v.owner ? { owner: v.owner } : {}), ...(v.tier ? { tier: Number(v.tier) } : {}) }, `Object ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 추가했습니다.`);
          if (mgArea(v.name)) { mgOpen('area', v.name, true); render(); }  // what was just made is what is shown next
        })();
        return true;
      }
      const o = f.orig, args = { name: v.name };
      for (const k of ['label', 'description', 'cite', 'owner']) if ((v[k] || '') !== (o[k] || '')) args[k] = v[k] || '';
      if (String(v.tier || '') !== String(o.tier || '')) args.tier = v.tier ? Number(v.tier) : null;
      if ((v.status || 'active') !== (o.status || 'active')) args.status = v.status || 'active';
      if (Object.keys(args).length === 1) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return true; }
      mgEdit('update_area', args, `Object ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 변경했습니다.`);
      S.md.areaPick = v.name;
      return true;
    }
    const typed = (x) => (x === 'true' ? true : x === 'false' ? false : (x !== '' && !Number.isNaN(Number(x)) ? Number(x) : x));
    if (f.kind === 'rule') {
      if (f.mode === 'new' && !String(v.id || '').trim()) { formStop('id', '규칙 번호가 없어 규칙을 추가하지 못했습니다. 규칙 번호를 입력해 주세요.'); return true; }
      const args = { decision: S.mg.dec, id: v.id, when: v.when, then: v.then, cite: v.cite || '' };
      if (f.mode === 'new') { S.mg.sel = v.id; mgEdit('add_rule', { ...args, first: !!v.first }, '규칙을 추가했습니다.'); } else mgEdit('update_rule', args, '규칙을 변경했습니다.');
      return true;
    }
    if (f.kind === 'param') {
      if (f.mode === 'new' && !IDENT.test(String(v.name || ''))) { formStop('name', v.name ? '영문 이름 형식이 맞지 않아 기준값을 추가하지 못했습니다. 영문자로 시작하고 영문자 · 숫자 · _ 만 입력해 주세요.' : '영문 이름이 없어 기준값을 추가하지 못했습니다. 영문 이름을 입력해 주세요.'); return true; }
      const meta = { label: v.label || '', unit: v.unit || '', cite: v.cite || '', min: v.min === '' || v.min === null ? null : Number(v.min), max: v.max === '' || v.max === null ? null : Number(v.max) };
      S.mg.sel = `param:${v.name}`;
      if (f.mode === 'new') mgEdit('add_parameter', { name: v.name, type: v.type, value: v.value, ...meta }, '기준값을 추가했습니다.'); else mgEdit('update_parameter', { name: v.name, value: v.value, ...meta }, '기준값을 변경했습니다.');
      return true;
    }
    if (f.kind === 'metric') {
      if (!String(v.owner || '').trim()) { formStop('owner', '담당이 비어 있어 지표를 저장하지 못했습니다. 담당을 입력해 주세요.'); return true; }
      if (!String(v.basis || '').trim()) { formStop('basis', '기준 시각이 비어 있어 지표를 저장하지 못했습니다. 기준 시각을 입력해 주세요.'); return true; }
      const args = { name: v.name, label: v.label, owner: v.owner, unit: v.unit || '', scale: Number(v.scale) || 1, description: v.description || '', cite: v.cite || '' };
      if (f.raw) args.time = { ...(f.orig.time || {}), basis: v.basis };
      else {
        const al = 'x', ref = v.prop ? `${al}.${v.prop}` : al, where = condSpec(v.where, al), den = condSpec(v.den, al);
        args.formula = { match: { [al]: v.object }, ...(where ? { where } : {}), value: { [v.fn]: ref } };
        args.denominator = v.ratio ? { ...(den ? { where: den } : {}), value: { count: al }, ...(v.den_label ? { label: v.den_label } : {}) } : {};
        args.time = { basis: v.basis, ...(v.time_prop ? { property: `${al}.${v.time_prop}` } : {}) };
      }
      S.mg.sel = `metric:${v.name}`;
      if (f.mode === 'new') mgEdit('add_metric', args, '지표를 추가했습니다.'); else mgEdit('update_metric', args, '지표를 변경했습니다.');
      return true;
    }
    if (f.kind === 'identity') {
      const members = {};
      for (const r of v.imembers.filter((x) => x.type && x.field && x.prop)) (members[r.type] = members[r.type] || {})[r.field] = r.prop;
      const rules = v.irules.filter((r) => r.id && r.match).map((r) => { const match = String(r.match).split(',').map((x) => x.trim()).filter(Boolean); return { id: r.id, match, ...(r.normalize && r.normalize !== 'none' ? { normalize: Object.fromEntries(match.map((x) => [x, r.normalize])) } : {}) }; });
      const args = { name: v.name, label: v.label, members, rules };
      S.mg.sel = `identity:${v.name}`;
      if (f.mode === 'new') mgEdit('add_identity', args, '식별 통합을 추가했습니다.'); else mgEdit('update_identity', args, '식별 통합을 변경했습니다.');
      return true;
    }
    if (f.kind === 'function') {
      if (f.mode === 'new' && !IDENT.test(String(v.name || ''))) { formStop('name', v.name ? '영문 이름 형식이 맞지 않아 함수를 추가하지 못했습니다. 영문자로 시작하고 영문자 · 숫자 · _ 만 입력해 주세요.' : '영문 이름이 없어 함수를 추가하지 못했습니다. 영문 이름을 입력해 주세요.'); return true; }
      if (v.runtime === 'expr' && !v.target) { formStop('target', '대상 Entity가 없어 계산식 함수를 저장하지 못했습니다. 대상 Entity를 선택해 주세요.'); return true; }
      // an input keeps what this form does not show (required, default, range, allowed values) while its type stays
      const before = f.mode === 'edit' ? ((S.mg.st.functions.find((y) => y.name === v.name) || {}).inputs || {}) : {};
      const inputs = Object.fromEntries(v.fin.filter((p) => p.name).map((p) => { const was = before[p.name], keep = was && typeof was === 'object' && (was.type || 'string') === (p.type || 'string') ? was : {}; return [p.name, { ...keep, type: p.type || 'string', label: p.label || p.name }]; }));
      const outputs = Object.fromEntries(v.fout.filter((p) => p.name).map((p) => [p.name, p.type || 'string']));
      const by = { expr: { expr: v.expr }, decision: { decision: v.decision }, query: { query: v.query }, python: { entry: v.entry }, http: { call: { ...(f.call || {}), url: v.url, method: v.method, ...(v.path ? { path: v.path } : {}) } } }[v.runtime] || {};
      const args = { name: v.name, label: v.label, runtime: v.runtime, target: v.target || '', inputs, outputs, version: v.version, owner: v.owner || '', status: v.status, description: v.description || '', cite: v.cite || '', depends: String(v.depends || '').split(',').map((x) => x.trim()).filter(Boolean), expr: '', decision: '', query: '', entry: '', call: {}, ...by };
      S.mg.sel = v.name;
      if (f.mode === 'new') mgEdit('add_function', args, '함수를 추가했습니다.'); else mgEdit('update_function', args, '함수를 변경했습니다.');
      return true;
    }
    if (f.kind === 'decision') {
      if (!IDENT.test(String(v.name || ''))) { formStop('name', v.name ? '영문 이름 형식이 맞지 않아 결정표를 추가하지 못했습니다. 영문자로 시작하고 영문자 · 숫자 · _ 만 입력해 주세요.' : '영문 이름이 없어 결정표를 추가하지 못했습니다. 영문 이름을 입력해 주세요.'); return true; }
      if (!String(v.label || '').trim()) { formStop('label', '이름이 없어 결정표를 추가하지 못했습니다. 이름을 입력해 주세요.'); return true; }
      const inputs = {};
      for (const r of v.inputs.filter((x) => x.property)) {
        const parts = r.property.split('.');
        const name = parts[parts.length - 1];
        const link = parts.length > 1 ? S.mg.st.links.find((l) => l.name === parts[0]) : null;
        const p = S.mg.st.properties.find((x) => x.object === (link ? link.target : v.target) && x.name === name);
        inputs[name] = { type: (p || {}).type === 'enum' ? 'string' : ((p || {}).type || 'string'), property: name, ...(link ? { path: [link.name] } : {}) };
      }
      S.mg.dec = v.name;
      mgEdit('add_decision', { name: v.name, label: v.label, target: v.target, inputs, otherwise: v.otherwise }, '결정표를 추가했습니다.');
      return true;
    }
    if (f.kind === 'states') {
      S.mg.sel = v.object;
      mgEdit('update_states', { object: v.object, property: v.property, initial: v.initial, states: String(v.states || '').split(','), transitions: v.transitions }, '상태 전이를 저장했습니다.');
      return true;
    }
    if (f.kind === 'action') {
      const parameters = Object.fromEntries(v.params.filter((p) => p.name).map((p) => [p.name, { type: p.type || 'string', label: p.label || p.name }]));
      const by = {};
      for (const c of v.criteria.filter((x) => x.decision && x.field)) (by[c.decision] = by[c.decision] || {})[c.field] = typed(c.value);
      const parts = {};
      for (const l of v.limits.filter((x) => x.subject && x.value !== '')) (parts[l.subject] = parts[l.subject] || { [l.subject[0] === 'p' ? 'property' : 'parameter']: l.subject.slice(2) })[l.kind] = String(l.value).startsWith('@') ? l.value : Number(l.value);
      const limits = Object.values(parts);
      const asBody = (x) => { try { return JSON.parse(x); } catch (e) { return x; } };
      const call = v.url ? { ...(f.call || {}), url: v.url, method: v.method, ...(v.body ? { body: asBody(v.body) } : {}) } : {};
      const undo = v.undo_url ? { ...(f.undo || {}), url: v.undo_url, method: (f.undo || {}).method || 'POST' } : {};
      const set = Object.fromEntries(v.set.filter((x) => x.prop).map((x) => [x.prop, String(x.value).startsWith('$') ? x.value : typed(x.value)]));
      const args = { name: v.name, label: v.label, parameters, set, call, undo, criteria: [...Object.entries(by).map(([decision, expect]) => ({ decision, expect })), ...(f.keep || [])], transition_to: v.transition_to || '', approval: limits.length ? { auto_within: limits, agents: !!v.agents } : !!v.approval, cite: v.cite || '' };
      S.mg.sel = v.name;
      if (f.mode === 'new') mgEdit('add_action', { ...args, target: v.target }, 'Action을 추가했습니다.'); else mgEdit('update_action', args, 'Action을 변경했습니다.');
      return true;
    }
    if (f.kind === 'role') {
      const mask = Object.fromEntries(v.mask.filter((r) => r.prop).map((r) => [r.prop, r.style]));
      const rows = v.rows.filter((r) => r.raw || (r.type && r.property)).map((r) => (r.raw ? { type: r.type, raw: r.raw } : { type: r.type, via: r.via ? [r.via] : [], property: r.property, ...(r.mode === 'value' ? { value: typed(r.value) } : { principal: r.value }) }));
      const scope = v.scope_attr ? { attribute: v.scope_attr, types: v.scopes.filter((r) => r.type && r.property).map((r) => ({ type: r.type, via: r.via ? [r.via] : [], property: r.property })) } : {};
      const args = { name: v.name, label: v.label, read: v.read, run: v.run, request: v.request, mask, rows, scope, documents: v.docs.includes('*') ? null : v.docs };
      S.mg.sel = v.name;
      if (f.mode === 'new') mgEdit('add_role', args, '역할을 추가했습니다.'); else mgEdit('update_role', args, '역할을 변경했습니다.');
      return true;
    }
    return false;
  }

  function mgDeleteMore(f) {
    const v = f.v;
    if (f.kind === 'area') {
      if (!window.confirm(`Object ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 제외합니다.`)) return true;
      S.mg.sel = '';
      mgEdit('delete_area', { name: v.name }, 'Object 제외를 저장했습니다.');
      return true;
    }
    const say = { rule: '규칙', action: 'Action', role: '접근 정책', param: '기준값', metric: '지표', identity: '식별 통합', function: '함수' }[f.kind];
    if (!say) return false;
    if (!window.confirm(`${say}${josa(say, '을', '를')} 제외합니다.`)) return true;
    S.mg.sel = '';
    if (f.kind === 'rule') mgEdit('delete_rule', { decision: S.mg.dec, id: v.id }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'action') mgEdit('delete_action', { name: v.name }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'role') mgEdit('delete_role', { name: v.name }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'param') mgEdit('delete_parameter', { name: v.name }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'metric') mgEdit('delete_metric', { name: v.name }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'identity') mgEdit('delete_identity', { name: v.name }, `${say} 제외를 저장했습니다.`);
    if (f.kind === 'function') mgEdit('delete_function', { name: v.name }, `${say} 제외를 저장했습니다.`);
    return true;
  }

  async function mgSave() {
    const f = S.mg.form;
    if (mgSaveMore(f)) return;
    const v = f.v;
    const list = (s) => String(s || '').split(',').map((x) => x.trim()).filter(Boolean);
    if (naming(f)) {  // the display name is the one thing a person must write; the English name follows it unless typed
      const what = f.kind === 'prop' ? '속성을' : 'Entity를';
      if (!String(v.label || '').trim()) { formStop('label', `표시 이름이 비어 있어 ${what} 추가하지 못했습니다. 표시 이름을 입력해 주세요.`); return; }
      if (!v.name) await nameNow(f);
      if (S.mg.form !== f) return;
      if (!v.name || !IDENT.test(v.name) || nameIssue(f)) { formStop('name', `영문 이름을 쓸 수 없어 ${what} 추가하지 못했습니다. 영문 이름 칸 아래 안내대로 고쳐 주세요.`); return; }
    }
    if (f.kind === 'object' && f.mode === 'new') {
      const t = v.table ? mgTable(v.table) : null;
      const props = {};
      if (t && v.cols) t.columns.forEach((c) => { props[propName(c.name)] = { type: sqlType(c.type), label: c.name, column: c.name }; });
      const wide = t && t.key.length > 1;
      const key = wide ? `${propName(v.name)}_key` : (t ? propName(v.key || t.key[0] || t.columns[0].name) : (v.key ? propName(v.key) : autoKey(v)));
      if (wide) props[key] = { type: 'string', label: `${v.label || v.name} 키`, columns: t.key };
      if (!key) { toast('키를 정하지 않아 Entity를 추가하지 못했습니다. 키를 입력해 주세요.', true); return; }
      if (!props[key]) { const c = t && t.columns.find((x) => propName(x.name) === key); props[key] = { type: c ? sqlType(c.type) : 'string', label: c ? c.name : `${v.label || v.name} 키`, column: c ? c.name : key }; }
      props[key].required = true;
      S.mg.sel = v.name;
      mgEdit('add_object', { name: v.name, label: v.label, table: v.table, key, properties: props, parent: v.parent, description: v.description, ...(v.area ? { area: v.area } : {}) }, `Entity ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 추가했습니다.`);
      return;
    }
    if (f.kind === 'object') {
      if (!String(v.label || '').trim()) { formStop('label', '한글 이름이 없어 저장하지 못했습니다. 한글 이름을 입력해 주세요.'); return; }  // as the Entity form
      const o = f.orig, args = { name: v.name };
      for (const k of ['label', 'description', 'table', 'parent', 'area']) if ((v[k] || '') !== (o[k] || '')) args[k] = v[k] || '';
      if ((v.status || 'active') !== (o.status || 'active')) args.status = v.status || 'active';
      if (own(mgObj(v.name)) && v.key !== o.key) args.key = v.key;
      if (Object.keys(args).length === 1) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return; }
      mgEdit('update_object', args, `Entity ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 변경했습니다.`);
      return;
    }
    if (f.kind === 'prop') {
      const pairs = list(v.values).map((x) => { const i = x.indexOf('='); return i > 0 ? [x.slice(0, i).trim(), x.slice(i + 1).trim()] : [x, '']; });
      const spec = { label: v.label, description: v.description, type: v.type, unit: v.unit, values: pairs.map(([c]) => c),
        labels: Object.fromEntries(pairs.filter(([, n]) => n)), required: !!v.required, mask: v.mask || '', status: v.status || 'active' };
      if (v.expr) spec.expr = v.expr; else { spec.column = v.column || ''; spec.transform = (v.transform || '').trim(); spec.source_type = v.transform ? (v.source_type || '') : ''; }
      if (f.mode === 'new') {
        S.mg.sel = `${v.object}.${v.name}`;
        mgEdit('add_property', { object: v.object, name: v.name, ...spec }, `Property ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 추가했습니다.`);
        return;
      }
      const o = f.orig, args = { object: v.object, name: v.name };
      for (const [k, x] of Object.entries(spec)) if (JSON.stringify(x) !== JSON.stringify(o[k])) args[k] = x;
      if (Object.keys(args).length === 2) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return; }
      mgEdit('update_property', args, `Property ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 변경했습니다.`);
      return;
    }
    if (f.kind === 'link') {
      if (f.mode === 'new') {
        if (!IDENT.test(v.name || '')) { formStop('name', '영문 이름 칸에 쓸 수 없는 글자가 있어 관계를 추가하지 못했습니다. 영문자로 시작하고 영문자 · 숫자 · _ 만 써 주세요.'); return; }
        if (!v.source || !v.target || !v.sp || !v.tp) { toast('출발 · 도착 Entity와 연결할 속성을 모두 선택해 주세요.', true); return; }
        S.mg.sel = v.name;
        mgEdit('add_link', { name: v.name, label: v.label, source: v.source, target: v.target, on: [v.sp, v.tp], cardinality: v.cardinality, inverse: v.inverse, required: !!v.required }, `Relation ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 추가했습니다.`);
        return;
      }
      const o = f.orig, args = { name: v.name };
      for (const k of ['label', 'cardinality', 'inverse']) if ((v[k] || '') !== (o[k] || '')) args[k] = v[k] || '';
      if ((v.status || 'active') !== (o.status || 'active')) args.status = v.status || 'active';
      if (!!v.required !== !!o.required) args.required = !!v.required;
      if (own(o)) {
        if (v.source !== o.source) args.source = v.source;
        if (v.target !== o.target) args.target = v.target;
        if (v.sp !== o.sp || v.tp !== o.tp) args.on = [v.sp, v.tp];
      }
      if (Object.keys(args).length === 1) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return; }
      mgEdit('update_link', args, `Relation ${v.label || v.name}${josa(v.label || v.name, '을', '를')} 변경했습니다.`);
      return;
    }
    if (f.kind === 'question') {
      let expect = {}, params = {};
      const meta = { holdout: v.holdout === '1', ...(v.grading ? { grading: v.grading } : {}), ...(csv(v.keywords).length ? { keywords: csv(v.keywords) } : {}) };
      if (v.kind === 'definition') {
        if (!csv(v.keywords).length) { toast('키워드가 없어 정의 질문을 추가하지 못했습니다. 답에 포함할 단어를 입력해 주세요.', true); return; }
        mgEdit('add_question', { id: v.id, text: v.text, type: 'definition', ...meta }, `검증 질문 ${v.id}${josa(v.id, '을', '를')} 추가했습니다.`);
        return;
      }
      let values = {};
      if (v.kind === 'decision') {
        const d = S.st.decisions.find((x) => x.name === v.decision);
        const typed = (raw, type) => {  // '' is not given, '값 없음' or null is given as none
          const s = String(raw ?? '').trim();
          if (s === '') return undefined;
          if (s === 'null' || s === '값 없음') return null;
          if (type === 'boolean') return s === 'true';
          if (['integer', 'decimal', 'number'].includes(type)) return Number(s);
          return s;
        };
        for (const i of (d && d.inputs) || []) { const x = typed((v.values || {})[i.name], i.type); if (x !== undefined) values[i.name] = x; }
        for (const o of (d && d.outputs) || []) { const x = typed((v.expectv || {})[o.name], o.type); if (x !== undefined) expect[o.name] = x; }
        const bad = Object.entries({ ...values, ...expect }).find(([, x]) => typeof x === 'number' && Number.isNaN(x));
        if (bad) { toast(`${bad[0]} 값이 숫자가 아니어서 저장하지 못했습니다. 숫자를 입력해 주세요.`, true); return; }
        if (!Object.keys(expect).length) { toast('기대 결과가 없어 질문을 추가하지 못했습니다. 확인할 결과를 하나 이상 입력해 주세요.', true); return; }
        if (!v.key.trim() && !Object.keys(values).length) { toast('판정 값과 레코드 키가 모두 비어 있어 질문을 추가하지 못했습니다. 판정 값을 입력하거나 레코드 키를 입력해 주세요.', true); return; }
        const missing = Object.keys(values).length ? ((d && d.inputs) || []).filter((i) => !(i.name in values)) : [];
        if (missing.length) { toast(`판정 값이 빠져 있어 질문을 추가하지 못했습니다: ${missing.map((i) => i.label).join(', ')}. 값이 없으면 '값 없음'을 선택해 주세요.`, true); return; }
      } else {
        try { params = v.params.trim() ? JSON.parse(v.params) : {}; } catch (_) { toast('JSON 형식이 아니어서 읽지 못했습니다. 예시처럼 입력해 주세요.', true); return; }
        expect = v.expect.trim() === '' ? {} : { rows: Number(v.expect) };
        if (Number.isNaN(expect.rows)) { toast('기대 행 수가 숫자가 아니어서 저장하지 못했습니다. 숫자를 입력해 주세요.', true); return; }
      }
      const args = v.kind === 'decision' ? { id: v.id, text: v.text, decision: v.decision, key: v.key.trim(), expect, ...(Object.keys(values).length ? { values } : {}), ...meta }
        : { id: v.id, text: v.text, query: v.query, params, expect, ...meta };
      mgEdit('add_question', args, `검증 질문 ${v.id}${josa(v.id, '을', '를')} 추가했습니다.`);
    }
  }

  function mgDelete() {
    const f = S.mg.form;
    if (mgDeleteMore(f)) return;
    const v = f.v;
    const say = { object: `Entity ${v.label || v.name}`, prop: `속성 ${v.label || v.name}`, link: `관계 ${v.label || v.name}` }[f.kind];
    if (!window.confirm(`${say}${josa(say, '을', '를')} 제외합니다. 사용하는 질의 · 결정표 · 검증 질문도 함께 제외합니다.`)) return;
    S.mg.sel = '';
    if (f.kind === 'object') mgEdit('delete_object', { name: v.name }, `${say}${josa(say, '을', '를')} 제외했습니다.`);
    if (f.kind === 'prop') mgEdit('delete_property', { object: v.object, name: v.name }, `${say}${josa(say, '을', '를')} 제외했습니다.`);
    if (f.kind === 'link') mgEdit('delete_link', { name: v.name }, `${say}${josa(say, '을', '를')} 제외했습니다.`);
  }

  function mgOpen(kind, key, quiet) {
    const m = S.mg.st;
    S.mg.sel = key;
    if (kind === 'object') {
      const o = mgObj(key);
      S.mg.form = { kind, mode: 'edit', orig: o, v: { name: o.name, label: o.label, description: o.description, table: o.table, key: o.key, parent: o.parent, area: o.area || '', status: o.status || 'active' } };
    }
    if (kind === 'area') {
      const a = mgArea(key);
      S.mg.form = { kind, mode: 'edit', orig: a, v: { name: a.name, label: a.label || '', description: a.description || '', cite: a.cite || '', status: a.status || 'active', owner: a.owner || '', tier: a.tier ? String(a.tier) : '' } };
    }
    if (kind === 'prop') {
      const [obj, name] = key.split('.');
      const p = m.properties.find((x) => x.object === obj && x.name === name);
      S.mg.form = { kind, mode: 'edit', orig: { ...p, column: p.column || '', status: p.status || 'active' }, v: { object: obj, name, label: p.label, description: p.description, type: p.type, column: p.column || '', transform: p.transform || '', source_type: p.source_type || '', values: valueText(p, ', '), unit: p.unit, required: p.required, mask: p.mask, expr: p.expr, status: p.status || 'active' } };
    }
    if (kind === 'link') {
      const l = m.links.find((x) => x.name === key);
      const v = { name: l.name, label: l.label, source: l.source, target: l.target, sp: l.on ? l.on[0] : '', tp: l.on ? l.on[1] : '', cardinality: l.cardinality, inverse: l.inverse, required: l.required, status: l.status || 'active' };
      S.mg.form = { kind, mode: 'edit', orig: { ...v, module: l.module }, v: { ...v } };
    }
    if (!quiet) render();
  }

  // ---- what is wrong, and the way to each fix -------------------------------------------------------------------

  const WHERE_WORD = { here: ['b', '변경 요청'], now: ['ok', '즉시 적용'], source: ['warn', '데이터 소스 수정'] };
  const FLOOR_WORD = { source: '데이터 소스', convert: '변환', ontology: '구축', store: '저장소', use: '활용', verify: '검증' };
  const DIRECT_WORD = { workspace: '변경 열기', change: '검토 열기', action: '처리 열기' };
  const BACK_WORD = { monitor: '관제로 돌아가기', inbox: '할 일로 돌아가기', home: '홈으로 돌아가기', flow: '흐름으로 돌아가기', check: '검증으로 돌아가기', bind: 'DB 대조로 돌아가기' };
  const gateKey = (g) => (g.stage === 'bind' ? 'bind' : `gate:${g.stage}.${g.condition}`);
  const issueAll = () => (S.iss.list || []).flatMap((x) => [x, ...x.members]);
  const issueOf = (id) => issueAll().find((x) => x.id === id);
  const issuesLeft = () => issueAll().filter((x) => !x.direct && x.kind !== 'conflict').length;
  const rootOf = (x) => (S.iss.list || []).find((r) => r.members.some((y) => y.id === x.id)) || x;
  const elementTo = (id) => `#model?el=${encodeURIComponent(id)}`;

  function loadIssues() {  // one fetch at a time: whoever asks while it runs waits for the same answer
    const I = S.iss;
    if (I.busy) return I.busy;
    I.busy = api('issues').then((r) => { Object.assign(I, { list: r.issues, at: r.measured_at, gates: r.gates }); }).catch((e) => { I.list = I.list || []; fail(e); }).finally(() => { I.busy = null; });
    return I.busy;
  }

  function issueList(list) {
    if (!list.length) return '<div class="muted" style="font-size:12.5px">활성 알림이 없습니다.</div>';
    const row = (x) => {
      const on = S.iss.open === x.id || x.members.some((y) => y.id === S.iss.open);
      if (x.direct) return `<div class="iagroup"><div class="iahead"><i class="dot ${x.level}"></i><b>${esc(x.title)}</b><span class="muted">${esc(x.detail)}</span><span class="grow"></span><button class="btn sm" data-act="issopen" data-id="${esc(x.id)}">${DIRECT_WORD[x.kind] || '열기'}</button></div></div>`;
      const sub = (y, title) => `<button class="iasub" data-act="issopen" data-id="${esc(y.id)}"><span>${esc(title)}</span><span class="muted">${esc(FLOOR_WORD[y.floor])} · ${esc(y.detail)}</span></button>`;
      if (!x.members.length) return `<div class="iagroup${on ? ' on' : ''}"><button class="iahead" data-act="issopen" data-id="${esc(x.id)}"><i class="dot ${x.level}"></i><b>${esc(x.title)}</b><span class="muted">${esc(x.detail)}</span></button></div>`;
      return `<div class="iagroup${on ? ' on' : ''}"><button class="iahead" data-act="issopen" data-id="${esc(x.id)}"><i class="dot ${x.level}"></i><b>${esc(x.title)}</b><span class="grow"></span><span class="chip sm">알림 ${x.members.length + 1}</span></button>
        ${sub(x, x.bind_title || x.title)}${x.members.map((y) => sub(y, y.title)).join('')}</div>`;
    };
    return `<div class="ialist">${list.map(row).join('')}</div>`;
  }

  async function issueOpen(id, key) {
    await loadIssues();
    const list = S.iss.list || [];
    const x = id ? issueOf(id) : list.find((y) => y.keys.includes(key)) || issueAll().find((y) => y.keys.includes(key));
    if (!x) { toast('최근 측정에 없는 문제라 열지 못했습니다. 다시 측정해 주세요.', true); return; }
    if (x.direct) { follow(x.direct); return; }
    Object.assign(S.iss, { open: x.id, preview: null, done: null });
    paintLayer();
    const box = $('#mbrief');
    if (box && S.mon.st) box.innerHTML = monitorBrief(S.mon.st);
  }

  function sceneIssue(a) {  // a badge or number on the picture: where something is wrong it opens that, otherwise its screen
    const m = S.mon.st;
    if (!m) return false;
    const floor = a.dataset.badge || String(a.dataset.key || '').split('.')[0];
    const f = m.floors.find((x) => x.id === floor);
    const tag = f && a.dataset.key ? f.tags.find((t) => t.key === a.dataset.key) : null;
    if (!f || !f.alerts || (tag && tag.status === 'ok')) return false;
    ACT.issfloor({ dataset: { floor } });
    return true;
  }

  function issuePanel() {
    const I = S.iss;
    if (I.done) {
      const d = I.done;
      return `<aside class="drawer ipanel" role="dialog" aria-label="해결됨"><div class="dhead"><b>조치 결과</b><button class="iconbtn" data-act="issclose" aria-label="닫기">${ui('close')}</button></div>
        <div class="dbody"><div class="banner ok"><span class="ic y" style="width:26px;height:26px">✓</span><div><div class="big" style="font-size:16px">해결됐습니다</div><div class="muted" style="font-size:12.5px">다시 측정 ${esc(hms(d.at))} · 통과 조건 ${d.gates ? `${d.gates.met} / ${d.gates.all}` : '-'} · 남은 문제 ${d.left}건</div></div></div>
        <div class="muted" style="font-size:13px;margin-top:12px">${esc(d.title)}</div></div></aside>`;
    }
    const x = I.open && issueOf(I.open);
    if (!x) return '';
    const root = rootOf(x);
    const section = (word, body) => `<div class="isec"><div class="ish">${word}</div>${body}</div>`;
    const items = x.items.map((it, i) => `<button class="iitem" data-act="issitem" data-i="${i}"><span class="iilabel">${esc(it.label)}${it.name && it.name !== it.label ? ` <span class="mono muted cn">${esc(it.name)}</span>` : ''}</span><span class="muted">${esc(it.say)}</span>${it.evidence ? `<span class="iiproof muted">${esc(it.evidence)}</span>` : ''}</button>`).join('');
    const more = x.total > x.items.length ? `<div class="muted" style="font-size:12px">외 ${x.total - x.items.length}건</div>` : '';
    const cause = x.cause ? section('원인', `<div class="itext">${esc(x.cause.text)}</div>${root !== x ? `<button class="ilinkb" data-act="issopen" data-id="${esc(root.id)}">원인 전체 보기</button>` : ''}`) : '';
    const effects = x.effects.length ? section('영향 범위', x.effects.map((e) => `<div class="ikv"><span>${esc(e.label)}</span><span class="muted">${esc(e.say)}</span></div>`).join('')) : '';
    const members = x.members.length ? section('같은 원인의 알림', [`<button class="iitem" data-act="issopen" data-id="${esc(x.id)}"><span class="iilabel">${esc(x.bind_title)}</span><span class="muted">${esc(x.detail)}</span></button>`, ...x.members.map((y) => `<button class="iitem" data-act="issopen" data-id="${esc(y.id)}"><span class="iilabel">${esc(y.title)}</span><span class="muted">${esc(y.detail)}</span></button>`)].slice(1).join('')) : '';
    const fix = (f, i) => {
      const [c, w] = WHERE_WORD[f.where];
      const p = I.preview && I.preview.i === i ? I.preview : null;
      const body = !p ? '' : p.busy ? '<div class="ipreview"><span class="spin"></span>사본 시험 중</div>'
        : p.error ? `<div class="ipreview"><div class="hint warn">${esc(p.error)}</div></div>` : `<div class="ipreview">
          <div class="ikv"><span>빠지는 항목</span><span class="muted">${esc((p.res.removed || []).join(', ') || '없음')}</span></div>
          <div class="ikv"><span>해제 후 통과 조건</span><span><b>${p.res.gates ? `${p.res.gates.met} / ${p.res.gates.all}` : '-'}</b></span></div>
          ${p.res.impact.broken.length ? `<div class="hint warn">${esc(p.res.impact.broken.join(', '))}</div>` : ''}
          <div class="iacts"><button class="btn sm primary" data-act="issrun" data-i="${i}"${I.running || !p.res.impact.ok ? ' disabled' : ''}>${I.running ? '<span class="spin"></span>처리 중' : '해제'}</button><button class="btn sm ghost" data-act="isscancel">취소</button></div></div>`;
      return `<div class="ifix${f.recommended ? ' rec' : ''}"><div class="ifh"><b>${esc(f.label)}</b><span class="chip sm ${c}">${w}</span>${f.recommended ? '<span class="chip sm b">추천</span>' : ''}<span class="grow"></span>
        ${p ? '' : `<button class="btn sm${f.recommended ? ' primary' : ''}" data-act="issfix" data-i="${i}"${I.running ? ' disabled' : ''}>${esc(f.cta)}</button>`}</div>${body}</div>`;
    };
    const since = x.since ? `${hms(x.since)}부터 · ` : '';
    return `<aside class="drawer ipanel" role="dialog" aria-label="${esc(x.title)}"><div class="dhead"><span class="chip sm ${x.level}">${x.level === 'bad' ? '장애' : '주의'}</span><span class="muted" style="font-size:12.5px">${esc(since)}${esc(x.floors.map((f) => FLOOR_WORD[f]).join(', '))}</span><span class="grow"></span><button class="btn sm ghost" data-act="issclose">닫기</button></div>
      <div class="dbody"><h3 class="ititle">${esc(x.title)}</h3>
      ${items ? section('문제 위치', `${items}${more}${x.note ? `<div class="muted" style="font-size:12px">${esc(x.note)}</div>` : ''}`) : (x.note ? section('문제 위치', `<div class="itext">${esc(x.note)}</div>`) : '')}
      ${cause}${effects}${members}
      ${section('조치', x.fixes.map(fix).join('') || '<div class="muted" style="font-size:12.5px">제안할 조치가 없습니다.</div>')}
      </div></aside>`;
  }

  function goHash(go, issue) {
    const { tab, ...rest } = go;
    const q = new URLSearchParams();
    Object.entries(rest).forEach(([k, v]) => q.set(k, typeof v === 'string' ? v : JSON.stringify(v)));
    if (issue) q.set('issue', issue);
    const s = q.toString();
    return `#${tab}${s ? `?${s}` : ''}`;
  }

  function follow(go, issue) {
    const h = goHash(go, issue);
    if (location.hash === h) { readHash(); render(); $('#main').scrollTop = 0; } else location.hash = h;
  }

  function startFix(x, steps, i, label) {
    S.fix = { id: x.id, title: x.bind_title || x.title, level: x.level, label, steps, i, back: S.fix ? S.fix.back : S.tab, phase: 'work', at: '', gates: null, left: 0 };
    S.iss.open = '';
    paintLayer();
    follow(steps[i].go, x.id);
  }

  async function fixRecheck(waiting) {  // a change has gone in, or is waiting for someone: whether the problem is still there
    const f = S.fix;
    if (!f) return;
    if (waiting) { f.phase = 'waiting'; render(); return; }
    await loadIssues();
    Object.assign(f, { phase: issueOf(f.id) ? 'left' : 'done', at: S.iss.at, gates: S.iss.gates, left: issuesLeft() });
    render();
  }

  function fixBar() {
    const f = S.fix;
    if (!f) return '';
    const n = f.steps.length, back = `<button class="btn sm ghost" data-act="fixback">${BACK_WORD[f.back] || '돌아가기'}</button>`;
    const panel = '<button class="btn sm" data-act="fixpanel">조치 패널</button>';
    const next = n > 1 && f.i < n - 1 ? '<button class="btn sm" data-act="fixnext">다음 문제</button>' : '';
    if (f.phase === 'done') return `<div class="fixbar done"><i class="dot ok"></i><b>해결됐습니다</b><span class="muted">다시 측정 ${esc(hms(f.at))} · 통과 조건 ${f.gates ? `${f.gates.met} / ${f.gates.all}` : '-'} · 남은 문제 ${f.left}건</span><span class="grow"></span>${back}</div>`;
    if (f.phase === 'left') return `<div class="fixbar"><i class="dot bad"></i><b>남은 문제</b><span class="muted">다시 측정 ${esc(hms(f.at))} · ${esc(f.title)}</span><span class="grow"></span>${panel}${back}</div>`;
    if (f.phase === 'waiting') return `<div class="fixbar edit"><i class="dot warn"></i><b>승인을 기다립니다</b><span class="muted">승인되면 반영되고 다시 측정합니다</span><span class="grow"></span><a class="btn sm" href="#changes">변경 요청 보기</a>${back}</div>`;
    const where = `<span class="muted">${n > 1 ? `${f.i + 1} / ${n} · ` : ''}${esc(f.steps[f.i].label)}</span>`;
    if (f.phase === 'edited') {
      const t = S.md.trial, done = t && t.gates, file = selfApply() ? '[검토 후 적용]을 선택하면' : '변경 요청을 만들면';
      const say = done ? (t.passed ? `사본 시험 통과 ${t.gates.filter((g) => g.passed).length} / ${t.gates.length} · ${file} 반영되고 다시 측정합니다` : '사본 시험에서 통과하지 못한 조건이 있습니다. 왼쪽 변경 목록에서 확인해 주세요') : `사본에서 시험한 뒤 ${file} 반영되고 다시 측정합니다`;
      return `<div class="fixbar edit"><i class="dot warn"></i><b>수정했습니다</b><span class="muted">${say}</span>${where}<span class="grow"></span>${next}${back}</div>`;
    }
    return `<div class="fixbar"><i class="dot ${f.level}"></i><b>${esc(f.title)} 고치는 중</b>${where}<span class="grow"></span>${next}${panel}${back}</div>`;
  }

  // a link can say what to open on the screen it leads to: #model?el=property:Sku.expires_on&field=column
  function readHash() {
    const [tab, query] = location.hash.slice(1).split('?');
    if (TABLE_TABS.includes(tab) && !V2[tab]) { S.tab = 'model'; S.md.view = 'table'; S.md.arrive = tab; } else S.tab = tab || 'home';
    if (!known(S.tab)) S.tab = 'state';  // an address that is no screen: said as that, with the way back
    if (tab === 'model') S.md.view = 'diagram';  // 그래프 탐색 is the diagram; the table is the Entity screen (#objects)
    S.land = query ? Object.fromEntries(new URLSearchParams(query)) : null;
    S.hit = ''; S.hitDone = '';
    if (!S.land) S.md.hot = null;
  }

  const LAND = {
    model: (l) => {
      if (!S.mg.st) return false;
      const m = S.mg.st, md = S.md;
      S.land = null;
      if (l.left) Object.assign(md, { left: l.left, leftOff: false, view: 'diagram' });
      if (l.el) {
        const [kind, ...rest] = l.el.split(':'), name = rest.join(':');
        const exists = kind === 'property' ? m.properties.some((x) => `${x.object}.${x.name}` === name) : kind === 'object' ? !!mgObj(name) : kind === 'link' ? m.links.some((x) => x.name === name) : false;
        if (!exists) { toast('이 항목은 정의에서 찾지 못했습니다. 이미 고쳐졌을 수 있습니다.'); render(); return true; }
        Object.assign(md, { view: 'diagram', tab: 'form', rightOff: false, focus: '' });
        if (kind === 'property') { md.sel = name.split('.')[0]; mgOpen('prop', name, true); }
        if (kind === 'object') { md.sel = name; mgOpen('object', name, true); }
        if (kind === 'link') { md.sel = m.links.find((x) => x.name === name).source; mgOpen('link', name, true); }
        const item = issueAll().flatMap((x) => x.items).find((x) => x.element === l.el);
        md.hot = l.field || (item && item.message) ? { field: l.field || '', note: (item && item.message) || '', fresh: true, near: l.prefill || '' } : null;
        const v = S.mg.form && S.mg.form.v;
        if (v && l.prefill !== undefined) {
          const cols = kind === 'property' ? columnsOf(md.sel) : [];
          const named = l.field === 'column' && cols.find((c) => c.name.toLowerCase() === l.prefill.toLowerCase());
          v[l.field] = l.prefill === 'false' ? false : (named ? named.name : l.prefill);
        }
        if (v && l.append) v.values = [v.values, ...JSON.parse(l.append)].filter(Boolean).join(', ');
      }
      render();
      if (l.el) erReveal(md.sel);
      return true;
    },
    bind: (l) => { if (!S.bind || S.bind.busy) return false; S.hit = l.row || ''; return true; },
    flow: (l) => { if (!S.flset || S.flset.busy) return false; S.hit = l.row || ''; return true; },
    rules: (l) => { if (!S.ru) return false; S.hit = l.row || ''; return true; },
    inbox: (l) => { if (!S.home.box) return false; S.hit = l.row || ''; return true; },
    search: (l) => { if (l.q) { S.land = null; S.sr.text = l.q; searchNow(); } return true; },
    mgrules: (l) => {
      if (!S.mg.st) return false;
      S.land = null;
      if (l.decision) S.mg.dec = l.decision;
      if (l.key) { S.sim.dec = l.decision; S.sim.key = l.key; S.sim.vals = {}; simulateNow(l.key, {}); } else render();
      return true;
    },
    changes: (l) => { if (l.change) { S.land = null; S.chg.sel = l.change; S.chg.det = null; S.chg.item = ''; render(); } return true; },
    onto: (l) => { if (l.object) { S.land = null; S.ontoPick = l.object; render(); } return true; },
    catalog: (l) => {
      if (!l.file) return true;
      S.land = null;
      const folder = l.file.includes('/') ? l.file.slice(0, l.file.lastIndexOf('/')) : '';
      Object.assign(S.cat, { folder });
      S.hit = `file:${l.file}`;
      loadCatalog();
      ACT.cview({ dataset: { path: l.file } });
      return true;
    },
  };

  function landNow() {
    const l = S.land;
    if (!l) return;
    const go = LAND[S.tab];
    if (go && go(l) === false) return;  // what it points at is still loading; the next render comes back here
    if (S.land === l) S.land = null;
    if (l.issue && !S.fix) {  // a reloaded or shared link: the bar comes back with the problem it was about
      loadIssues().then(() => {
        const x = issueOf(l.issue), f = x && x.fixes.find((y) => y.go);
        if (x && f) { S.fix = { id: x.id, title: x.bind_title || x.title, level: x.level, label: f.label, steps: f.steps.length ? f.steps : [{ label: x.title, go: f.go }], i: 0, back: 'monitor', phase: 'work' }; render(); }
      });
    }
  }

  function showHit() {
    if (!S.hit) return;
    const el = document.querySelector(`[data-row="${CSS.escape(S.hit)}"]`);
    if (!el) return;
    el.classList.add('hitrow');
    if (S.hitDone !== S.hit) { S.hitDone = S.hit; el.scrollIntoView({ block: 'center' }); }
  }

  // ---- events --------------------------------------------------------------------------------------------------

  // what every screen holds of the pipeline on screen, for when another one takes its place
  function clearViews() {
    clearInterval(S.dr.timer);
    spaceChanged();
    Object.assign(S, { impact: null, pos: {}, sel: null, gsel: null, files: null, dpos: {}, conv: null, changes: null, agree: null, flset: null, ident: null, ed: null, change: null });
    Object.assign(S.dr, { step: 0, view: 'read', sel: null, ed: NEW_EDITS(), rev: null, graph: null, rules: null, tables: {}, timer: 0 });
    stale();
    Object.assign(S.mg, { form: null, sel: '', q: '', obj: '', table: '', open: false, review: null });
    S.q.name = null; S.q.text = ''; S.q.dirty = false; S.d.name = null; S.d.key = null;
    S.mon.st = null;
    Object.assign(S.pol, { open: false, text: '', target: '', busy: false, res: null });
    S.map = { standards: null, picked: [], sug: null, edits: { objects: {}, columns: {} }, busy: false };
    S.ind = { target: '', inputs: {} };
  }

  async function libraryUse(id) {  // another library: its own definition, data and pipelines
    try {
      await api('library', { id });
      clearViews();
      Object.assign(S.home, { box: null, ov: null });
      S.mg.st = null; S.ver = null; S.lx.st = null; S.sem.st = null;
      await load();
      const label = (S.st.libraries.find((x) => x.id === id) || {}).label || '온톨로지';
      toast(`${label}${josa(label, '으로', '로')} 전환했습니다.`);
      return true;
    } catch (e) { fail(e); return false; }
  }

  // ---- a library made on the page ----
  async function libraryNewOpen() {
    Object.assign(S.lib, { open: true, mods: null });
    if (S.tab !== 'library') location.hash = '#library'; else render();
    try { S.lib.files = await api('library/files'); } catch (e) { fail(e); }
    if (S.tab === 'library') { render(); const box = $('#libnew'); if (box) box.scrollIntoView({ block: 'nearest' }); }
  }

  async function libraryFilesAdd(files) {  // each file is the body of its own request, read on the server
    const f = S.lib;
    if (!files.length || f.up) return;
    f.up = true; render();
    let added = 0;
    for (const file of files) {
      try {
        const r = await fetch('/api/library/file?path=' + encodeURIComponent(file.name), { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-Ontlas-Request': '1' }, body: file });
        let j = {};
        try { j = await r.json(); } catch (_) { /* empty body */ }
        if (!r.ok) throw new Error(j.error || `서버 오류로 파일을 읽지 못했습니다. 잠시 후 다시 시도해 주세요. (${r.status})`);
        f.files = j; added += 1;
      } catch (e) { fail(e); }
    }
    f.up = false; render();
    if (added) toast(`파일 ${count(added)}개를 추가했습니다.`);
  }

  async function libraryMake() {
    const f = S.lib;
    if (f.busy) return;
    if (!f.label.trim()) { toast('이름이 없어 만들지 못했습니다. 이름을 입력해 주세요.', true); const el = $('#libnl'); if (el) el.focus(); return; }
    if (f.start === 'files' && !((f.files && f.files.files) || []).length) { toast('파일이 없어 만들지 못했습니다. 정의 초안 또는 OWL 파일을 추가해 주세요.', true); return; }
    const body = { label: f.label, key: f.key, start: f.start };
    if (f.start === 'base') body.modules = [...(f.mods || new Set(S.st.library.filter((r) => r.on).map((r) => r.name)))];
    f.busy = true; render();
    try {
      const res = await api('library/new', body);
      Object.assign(f, { open: false, label: '', key: '', files: null, mods: null, res });
      clearViews();
      Object.assign(S.home, { box: null, ov: null });
      S.mg.st = null; S.ver = null; S.lx.st = null; S.sem.st = null;
      await load();
      toast(`${res.label} 라이브러리를 만들었습니다.`);
    } catch (e) { fail(e); }
    f.busy = false; render();
  }

  async function libraryDrop(id) {
    const x = (S.st.libraries || []).find((y) => y.id === id);
    if (!x || !window.confirm(`${x.label} 온톨로지를 삭제합니다. 삭제 후 복구할 수 없습니다.`)) return;
    const here = id === S.st.library_id;
    try {
      await api('library/drop', { id });
      if (S.lib.res && S.lib.res.id === id) S.lib.res = null;
      if (here) { clearViews(); Object.assign(S.home, { box: null, ov: null }); S.mg.st = null; S.ver = null; S.lx.st = null; S.sem.st = null; }
      await load();
      if (S.lib.open) { try { S.lib.files = await api('library/files'); } catch (_) { /* the form says nothing of the count then */ } render(); }
      toast(`${x.label} 온톨로지를 삭제했습니다.`);
    } catch (e) { fail(e); }
  }

  async function pipelineCall(body) {
    try {
      await api('pipeline', body);
      clearViews();
      await load();
    } catch (e) { fail(e); }
  }

  const spaceChanged = () => { Object.assign(S, { ru: null, met: {}, sp: null, dg: null, dq: null, dsec: null, drel: null, vemb: null, amap: null, mapn: null, ad: null, adrep: null, adrs: null }); Object.assign(S.ex, { tree: null, items: null, hits: null }); };
  const ACT = {
    rpopen: (t) => { const w = t.dataset.w, f = S.gx.found, q = f && f.which === w ? f.q || '' : ''; S.rp = { which: w, type: (f && f.which === w && f.type) || (q ? '' : (recordTypes()[0] || {}).id || ''), q, items: [], busy: false }; paintLayer(); rpLoad(); setTimeout(() => { const i = $('#rpq'); if (i) i.focus(); }, 0); },
    rpclose: () => { S.rp = null; paintLayer(); },
    rpmore: () => rpLoad(true),
    rppick: (t) => { const w = S.rp.which; S.rp = null; paintLayer(); gxChoose(w, { type: t.dataset.type, key: t.dataset.key, type_label: t.dataset.label, title: t.dataset.title }); },
    gxzoom: (t) => gxZoom(Number(t.dataset.z)),
    dgxzoom: (t) => dgxZoom(Number(t.dataset.z)),
    gxfound: (t) => gxChoose(t.dataset.w, { type: t.dataset.type, key: t.dataset.key, type_label: t.dataset.label, title: t.dataset.title }),
    gxreset: () => { S.gx.pos = {}; S.gx.hide = []; S.gx.zoom = 1; S.gx.zoomed = false; gxStart(S.gx.seed.type, S.gx.seed.key); },
    gxviewsave: async () => {
      const name = (window.prompt('관점 이름', S.gx.view || '고객 상담') || '').trim();
      if (!name) return;
      try {
        const r = await api('graph/view', { name, hide: S.gx.hide, color: S.gx.color, label: S.gx.labelBy, role: S.gx.viewRole || '' });
        S.gx.views = r.views; S.gx.view = name; toast(`관점 ${name}${josa(name, '을', '를')} 저장했습니다.`);
      } catch (e) { fail(e); return; }
      render();
    },
    gxviewforget: async () => {
      if (!S.gx.view) return;
      try { const r = await api('graph/view/forget', { name: S.gx.view }); S.gx.views = r.views; S.gx.view = ''; toast('관점을 삭제했습니다.'); } catch (e) { fail(e); }
      render();
    },
    srbuild: () => { S.q.mode = 'build'; location.hash = '#query'; },
    cuse: async (t) => {
      S.menu = null;
      try { await api('catalog/use', { path: t.dataset.path, use: t.dataset.v }); S.cat.st = null; toast('파일 용도를 변경했습니다.'); } catch (e) { fail(e); }
      stale(); render();
    },
    gxlink: async () => {
      const u = `${location.origin}${location.pathname}?gx=${encodeURIComponent(`${S.gx.seed.type}:${S.gx.seed.key}`)}#graph`;
      try { await navigator.clipboard.writeText(u); toast('링크를 복사했습니다.'); } catch (_) { toast(u); }
    },
    gxgrow: (t) => gxGrow(S.gx.sel, t.dataset.link, t.dataset.fw === '1'),
    gxgrowall: () => gxGrow(S.gx.sel),
    gxpath: () => gxPath(),
    gxsel: (t) => gxPick(t.dataset.id),
    gxroot: (t) => { const n = S.gx.nodes[t.dataset.id]; if (n) gxStart(n.type, n.key); },
    recgraph: () => { const r = S.rec; S.gx.seed = { type: r.type, key: r.key }; location.hash = '#graph'; gxStart(r.type, r.key); },
    issopen: (t) => issueOpen(t.dataset.id, t.dataset.key),
    issclose: () => { Object.assign(S.iss, { open: '', preview: null, done: null }); paintLayer(); const box = $('#mbrief'); if (box && S.mon.st) box.innerHTML = monitorBrief(S.mon.st); },
    isscancel: () => { S.iss.preview = null; paintLayer(); },
    issfloor: async (t) => {
      await loadIssues();
      const x = issueAll().find((y) => y.alert && y.floor === t.dataset.floor);
      if (x) issueOpen(x.id);
    },
    issel: async (t) => {
      await loadIssues();
      const x = issueAll().find((y) => y.items.some((i) => i.element === t.dataset.el));
      if (x) issueOpen(x.id); else toast('최근 측정에 없는 문제라 열지 못했습니다. 다시 측정해 주세요.', true);
    },
    issitem: (t) => {
      const x = issueOf(S.iss.open), i = Number(t.dataset.i), it = x.items[i];
      startFix(x, x.items.map((y) => ({ label: y.label, go: y.go })), i, it.label);
    },
    issfix: async (t) => {
      const I = S.iss, i = Number(t.dataset.i), x = issueOf(I.open), f = x.fixes[i];
      if (f.copy) {
        try { await navigator.clipboard.writeText(f.copy); toast('내용을 복사했습니다. 담당자에게 전달해 주세요.'); } catch (_) { window.prompt('아래 내용을 복사해 주세요.', f.copy); }
        return;
      }
      if (f.preview) {
        I.preview = { i, busy: true };
        paintLayer();
        try { I.preview = { i, res: await api(`issue/preview?module=${encodeURIComponent(f.preview)}`) }; } catch (e) { I.preview = { i, error: e.message }; }
        paintLayer();
        return;
      }
      if (f.run) { ACT.issrun(t); return; }
      startFix(x, f.steps.length ? f.steps : [{ label: x.title, go: f.go }], 0, f.label);
    },
    issrun: async (t) => {
      const I = S.iss, x = issueOf(I.open), f = x.fixes[Number(t.dataset.i)];
      I.running = true;
      paintLayer();
      try {
        const r = await api(f.run.route, f.run.body);
        if (r.ok === false) throw new Error(r.error || '조치를 실행하지 못했습니다.');
        if (r.pending) {  // it waits in the pending edits, like any other change
          Object.assign(I, { running: false, open: '', preview: null });
          S.mg.st = null;
          toast(`대기 중인 변경에 기록했습니다. ${fileAsk()}`);
          follow({ tab: 'model', left: 'changes' });
          return;
        }
        stale();
        S.mg.form = null; S.changes = null; S.home.box = null; S.agree = null; S.cat.st = null;
        S.st = await api('state');
        await loadIssues();
        const still = issueOf(x.id);
        S.mon.st = S.tab === 'monitor' ? await api('monitor') : S.mon.st;
        Object.assign(I, { running: false, preview: null, open: still ? x.id : '', done: still ? null : { title: x.title, at: I.at, gates: I.gates, left: issuesLeft() } });
        if (still) toast('조치했지만 문제가 남아 있습니다. 측정 결과를 다시 확인해 주세요.', true);
        render();
      } catch (e) { I.running = false; paintLayer(); fail(e); }
    },
    fixnext: () => { const f = S.fix; f.i += 1; f.phase = 'work'; follow(f.steps[f.i].go, f.id); },
    fixpanel: () => issueOpen(S.fix.id),
    fixback: () => { const to = S.fix.back; S.fix = null; S.md.hot = null; if (S.tab === to) render(); else location.hash = `#${to}`; },
    chkopen: (t) => {
      const q = S.st.questions.find((x) => x.id === t.dataset.id);
      if (q) follow(q.decision ? { tab: 'mgrules', decision: q.decision } : { tab: 'query', query: q.query });
    },
    chkexpect: async (t) => {
      const r = S.qa.results.find((x) => x.id === t.dataset.id);
      const expect = typeof r.got === 'number' ? { rows: r.got } : Object.fromEntries(Object.keys(r.expected || {}).map((k) => [k, (r.got || {})[k]]));
      if (!window.confirm(`${r.id}의 정답을 현재 결과로 바꿉니다. 의도한 변경일 때만 사용해 주세요. ${selfApply() ? '사본 검토를' : '변경 요청을'} 거쳐 반영됩니다.`)) return;
      try { S.mg.st = await api('manage/edit', { op: 'update_question', args: { id: r.id, expect } }); toast(`정답 변경을 대기 중인 변경에 기록했습니다. ${fileAsk()}`); render(); } catch (e) { fail(e); }
    },
    mdpick: (t) => modelPick(t.dataset.name),
    dgxpick: (t) => dgxPick(t.dataset.id),
    navopen: () => { $('#app').classList.add('navopen'); },  // a narrow window: the sidebar opens over the page
    navclose: () => { $('#app').classList.remove('navopen'); },
    libuse: (t) => libraryUse(t.dataset.id),
    libnew: () => libraryNewOpen(),
    libnewx: () => { S.lib.open = false; render(); },
    libresx: () => { S.lib.res = null; render(); },
    libstart: (t) => { S.lib.start = t.dataset.k; render(); },
    libpick: () => { if (!S.lib.up) $('#libfileinput').click(); },
    libfiledrop: async (t) => { try { S.lib.files = await api('library/file/drop', { name: t.dataset.name }); render(); } catch (e) { fail(e); } },
    libmake: () => libraryMake(),
    libdrop: (t) => libraryDrop(t.dataset.id),
    homeobj: (t) => { if (t.dataset.name) { S.om.sel = t.dataset.name; location.hash = '#objmgr'; } else location.hash = '#objects'; },
    mdarea: (t) => { Object.assign(S.md, { rightOff: false, view: 'diagram', tab: 'form' }); mgOpen('area', t.dataset.name, true); if (S.tab !== 'model') location.hash = '#model'; else render(); },
    mdareanew: () => { S.mg.sel = ''; S.md.tab = 'form'; S.md.group = 'area'; S.mg.form = { kind: 'area', mode: 'new', v: { name: '', label: '', description: '', cite: '' } }; render(); },
    mdobjnewin: (t) => { ACT.mdobjnew(); S.mg.form.v.area = t.dataset.area; render(); },
    mdgroup: (t) => { S.md.group = t.dataset.k; S.md.pos = {}; render(); },
    mdobjnew: () => { S.mg.sel = ''; S.md.tab = 'form'; S.mg.form = { kind: 'object', mode: 'new', v: { table: '', name: '', label: '', key: '', parent: '', description: '', cols: true } }; render(); },
    mdlinknew: () => { S.mg.obj = S.md.sel; S.md.tab = 'form'; ACT.mglinknew(); },
    erreset: () => { S.md.pos = {}; erPosSave(); const c = $('#ercanvas'); if (c) c.innerHTML = erSvg(); },
    erzoom: (t) => erZoom(Number(t.dataset.z), t.dataset.v === 'onto' ? 0.3 : 0.4, t.dataset.v || 'model'),
    ontoall: () => focusOff('onto'),
    ontoedit: () => { S.md.sel = S.ov.sel || S.sel; S.mg.form = null; location.hash = '#model?ws=1'; },
    erfold: () => { S.md.fold = !S.md.fold; render(); },
    mgfix: (t) => { if (S.mg.form) { S.mg.form.v[t.dataset.f] = t.dataset.v; render(); } },
    mdyamlreset: () => { const y = S.md.yaml; if (y) { y.text = y.was; y.err = ''; } render(); },
    mdyamlsave: async () => {
      const y = S.md.yaml;
      S.mg.busy = true;
      try {
        S.mg.st = await api('manage/yaml', { id: y.id, text: y.text });
        S.md.yaml = null; S.md.trial = null; S.mg.form = null;
        toast('YAML 변경을 대기 중인 변경에 저장했습니다.');
      } catch (e) { const at = /line (\d+)/.exec(e.message); y.err = at && /[a-z]{4,}/.test(e.message) ? `YAML 형식이 맞지 않아 반영하지 못했습니다. ${at[1]}행을 확인해 주세요.` : e.message; }
      S.mg.busy = false;
      render();
    },
    mdnotesave: async () => {
      if (!String(S.md.note || '').trim()) { toast('댓글이 없어 등록하지 못했습니다. 댓글을 입력해 주세요.', true); return; }
      const id = `object:${S.md.sel}`;
      try {
        const r = await api('element/comment', { id, text: S.md.note || '' });
        S.md.notes = { id, list: r.comments }; S.md.note = '';
        S.mg.st.comments = { ...(S.mg.st.comments || {}), [id]: r.comments.length };
        render();
      } catch (e) { fail(e); }
    },
    mdundo: async () => {
      try { S.mg.st = await api('manage/undo', {}); S.mg.form = null; S.md.yaml = null; S.md.trial = null; toast('마지막 변경을 되돌렸습니다.'); render(); } catch (e) { fail(e); }
    },
    mdtrial: async () => {
      S.md.trial = { busy: true }; render();
      S.md.left = 'changes';
      try { S.md.trial = await api('manage/trial', {}); S.md.trialOpen = true; } catch (e) { S.md.trial = { error: e.message }; }
      render();
    },

    mdprop: (t) => {
      const id = t.dataset.name;
      if (S.md.view === 'table' && S.mg.form && S.mg.form.kind === 'prop' && S.mg.sel === id) { S.mg.form = null; S.mg.sel = ''; paintCols(); return; }
      S.md.hot = null; S.md.tab = 'form'; S.md.list = 'props'; S.md.sel = id.split('.')[0];
      mgOpen('prop', id, true);
      wsRefresh();
    },
    mdobjedit: () => {
      if (S.mg.form && S.mg.form.kind === 'object' && S.mg.form.mode === 'edit') { S.mg.form = null; S.mg.sel = ''; } else mgOpen('object', S.md.sel, true);
      paintCols();
    },
    mdleft: (t) => { Object.assign(S.md, { left: t.dataset.k, leftOff: false, view: 'diagram' }); render(); },
    mdreview: () => {  // the review comes before the apply: the changes listed, then tried on a copy
      Object.assign(S.md, { left: 'changes', leftOff: false, view: 'diagram' });
      if (S.mg.st.workspace.issues.length) { render(); return; }
      ACT.mdtrial();
    },
    mdview: (t) => {  // the workspace's own two views: its diagram (#model?ws=1) and its Property · Relation tables (#props)
      S.md.focus = '';
      if (t.dataset.k === 'table') { S.mg.form = null; S.mg.sel = ''; }
      location.hash = t.dataset.k === 'table' ? '#props' : '#model?ws=1';
    },
    mdlist: (t) => { S.md.list = t.dataset.k; paintSide(); },
    mdpanel: (t) => { S.md[t.dataset.k] = !S.md[t.dataset.k]; render(); },
    mdaddprop: () => { S.mg.obj = S.md.sel; S.md.tab = 'form'; S.md.hot = null; ACT.mgpropnew(); },
    mdfocus: () => { if (S.md.focus) focusOff('model'); else if (S.md.sel) focusOn('model', S.md.sel); },
    mdonly: () => { if (!S.md.only && !Object.keys(modelProblems().by).length) { toast('표시할 문제가 없습니다.'); return; } S.md.only = !S.md.only; const c = $('#ercard'); if (c) { c.innerHTML = erCard(); mountEr(); } },
    mdsrc: (t) => { S.md.src[t.dataset.t] = !S.md.src[t.dataset.t]; const b = $('#wsleft'); if (b) b.innerHTML = wsLeft(); },
    mdcol: (t) => { const [table, column, type] = t.dataset.col.split('|'); columnToProp(table, column, type); },
    mdprob: (t) => {
      const x = issueOf(t.dataset.id);
      if (x) startFix(x, x.items.map((y) => ({ label: y.label, go: y.go })), Number(t.dataset.i), x.title);
    },
    mdrevert: async (t) => {
      S.mg.busy = true; render();
      try { S.mg.st = await api('manage/revert', { index: Number(t.dataset.i) }); S.mg.form = null; S.md.yaml = null; S.md.trial = null; toast('변경을 되돌렸습니다.'); } catch (e) { fail(e); }
      S.mg.busy = false; render();
    },
    mdredo: async () => {
      try { S.mg.st = await api('manage/redo', {}); S.mg.form = null; S.md.yaml = null; S.md.trial = null; toast('되돌린 변경을 다시 적용했습니다.'); render(); } catch (e) { fail(e); }
    },
    draftclose: () => { S.md.draft = null; paintDraft(); },
    draftadd: () => {
      const d = S.md.draft;
      if (!IDENT.test(d.name || '')) { toast('이름은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있습니다.', true); return; }
      if (!d.sp || !d.tp) { toast('연결할 속성을 모두 골라 주세요.', true); return; }
      S.md.draft = null;
      mgEdit('add_link', { name: d.name, label: d.label, source: d.source, target: d.target, on: [d.sp, d.tp], cardinality: d.cardinality }, `Relation ${d.label || d.name}${josa(d.label || d.name, '을', '를')} 추가했습니다.`);
    },
    mdlink: (t) => modelLink(t.dataset.name),
    mdtab: (t) => { S.md.tab = t.dataset.k; paintSide(); },
    mdedit: async (t) => { location.hash = '#library'; await openModule(t.dataset.module).catch(fail); },
    ibchange: (t) => { S.chg.sel = t.dataset.id; S.chg.det = null; S.chg.item = ''; location.hash = '#changes'; },
    chgview: (t) => { S.chg.view = t.dataset.k; render(); },
    chgmark: async (t) => {
      try { S.chg.det = await api('change/mark', { id: S.chg.sel, element: t.dataset.el, mark: t.dataset.mark }); render(); } catch (e) { fail(e); }
    },
    chgcomment: async (t) => {
      if (!S.chg.text.trim()) { toast('댓글이 없어 등록하지 못했습니다. 댓글을 입력해 주세요.', true); return; }
      try { S.chg.det = await api('change/comment', { id: S.chg.sel, element: t.dataset.el, text: S.chg.text }); S.chg.text = ''; render(); } catch (e) { fail(e); }
    },
    chgdecide: async (t) => {
      const yes = t.dataset.yes === '1';
      await decideChange(S.chg.sel, yes);
      S.chg.det = null; S.home.box = null; S.home.ov = null; S.ver = null; render();
    },
    simrun: () => simulateNow(S.sim.key, S.sim.vals),
    rec: (t) => openRecord(t.dataset.type, t.dataset.key),
    recact: (t) => { S.rec.act = S.rec.act === t.dataset.name ? '' : t.dataset.name; S.rec.role = ''; S.rec.params = {}; render(); },
    recactx: () => { S.rec.act = ''; render(); },
    rtab: (t) => { S.rec.tab = t.dataset.k; render(); },
    recreq: (t) => recordRequest(t.dataset.name),
    recfn: async (t) => {
      const r = S.rec, f = (r.res.functions || []).find((x) => x.name === t.dataset.name) || { label: t.dataset.name };
      try { r.fn[t.dataset.name] = await api('function/run', { name: t.dataset.name, key: r.key, params: {} }); } catch (e) { r.fn[t.dataset.name] = { ok: false, error: e.message }; }
      if (!['overview', 'decide'].includes(r.tab)) r.tab = 'decide';  // the result shows beside the record
      const out = r.fn[t.dataset.name];
      if (out.ok) toast(`${f.label}${josa(f.label, '을', '를')} 계산했습니다.`); else toast(out.error, true);
      render();
    },
    rlgo: () => { S.rl.res = null; render(); },
    rlpick: (t) => { S.rl.type = t.dataset.type; S.rl.res = null; render(); },
    ibtab: (t) => { S.home.tab = t.dataset.k; render(); },
    ibretry: () => { S.home.err = false; render(); },  // render asks for the list again
    ibapprove: (t) => inboxDecide(t.dataset.id, true),
    ibreject: (t) => inboxDecide(t.dataset.id, false),
    hrole: (t) => {
      S.home.role = t.dataset.k || t.value;
      try { localStorage.setItem('ontlas-role', S.home.role); } catch (e) { /* this visit only */ }
      gxLoadViews().then(gxApplyRole);  // the graph takes the perspective kept for this role
      render(); renderSide();
    },
    // the three ways a definition starts: by hand in the workspace, from a standard module, from documents or data
    startmodel: () => { S.md.wantNew = true; location.hash = '#model'; },
    startlib: () => { S.kind = 'all'; location.hash = '#library'; },
    startdata: () => { location.hash = '#catalog'; },
    homeask: (t) => { S.sr.text = t.dataset.q; location.hash = '#search'; searchNow(); },
    homego: () => { if (!S.home.q.trim()) { toast('찾을 말이나 질문을 입력해 주세요.', true); return; } S.sr.text = S.home.q; location.hash = '#search'; searchNow(); },
    homeq2: (t) => { location.hash = `#query?query=${encodeURIComponent(t.dataset.q)}`; },
    srgood: () => { S.sr.fb = 'good'; render(); },
    srbad: () => { S.sr.fb = 'bad'; render(); },
    srsave: async () => {
      const res = S.sr.res, d = pickedDecision(res);
      try {
        await api('manage/edit', { op: 'add_question', args: { id: `ask-${Date.now().toString(36)}`, text: res.question, decision: d.name, key: d.key, expect: d.outputs } });
        S.mg.st = null; S.sr.fb = 'saved'; render();
      } catch (e) { fail(e); }
    },
    rmetric: async (t) => {
      try { S.met[t.dataset.name] = await api('metric?name=' + encodeURIComponent(t.dataset.name)); render(); } catch (e) { fail(e); }
    },
    rpick: async (t) => {
      try { await api('conflict/pick', { id: t.dataset.id, source: t.dataset.source }); S.ru = null; toast('출처 선택을 대기 중인 변경에 추가했습니다.'); render(); } catch (e) { fail(e); }
    },
    radvance: async () => {
      try { const r = await api('transitions/advance', {}); S.ru = null; toast(`기한이 지난 전이 ${r.moved}건을 처리했습니다.`); render(); } catch (e) { fail(e); }
    },
    srgo: () => searchNow(),
    srex: (t) => { S.sr.text = t.dataset.text; searchNow(); },
    srobj: (t) => { location.hash = '#onto'; selectObject(t.dataset.obj); },
    srdecide: async (t) => { S.d.name = t.dataset.name; S.d.key = t.dataset.key; S.d.proposal = null; S.d.res = null; location.hash = '#decide'; },
    srfix: (t) => {
      const res = S.sr.res, d = pickedDecision(res);
      if (S.sr.fix) { S.sr.fix = null; render(); return; }
      S.sr.fix = d ? { key: d.key, decision: d.name, at: d.at } : { key: res.record.key, decision: '', at: res.now || '' };
      render();
      const el = $({ decision: '#srfdec', at: '#srfat' }[t.dataset.k] || '#srfkey');
      if (el) el.focus();
    },
    srfixx: () => { S.sr.fix = null; render(); },
    srrefix: () => {
      const f = S.sr.fix, res = S.sr.res, d = pickedDecision(res);
      if (!f.key.trim()) { toast('레코드 번호가 없어 다시 묻지 못했습니다. 번호를 입력해 주세요.', true); return; }
      const type = d ? d.target : res.record.type;
      searchNow(f.decision ? { decision: f.decision, key: f.key.trim(), at: f.at } : { type, key: f.key.trim() });
    },
    srtab: (t) => { S.sr.tab = t.dataset.k; render(); },
    srdi: (t) => { S.sr.di = Number(t.dataset.i); S.sr.fb = ''; S.sr.fix = null; render(); },
    sract: (t) => { openRecord(t.dataset.type, t.dataset.key); S.rec.act = t.dataset.name; },
    srsim: (t) => {
      S.mg.dec = t.dataset.name; S.mg.form = null; S.mg.sel = '';
      Object.assign(S.sim, { dec: t.dataset.name, key: t.dataset.key, vals: {}, res: null, err: '' });
      location.hash = '#mgrules';
      simulateNow(t.dataset.key, {});
    },
    dsecclose: () => { S.dsec = null; S.dgx.sel = ''; dgxPaint(); $('#docside').innerHTML = docSide(); },
    dread: () => readRelations(),
    dstop: async () => {
      if (!S.djob) return;
      S.djob.stop = true;
      const card = $('#dreadcard');
      if (card) card.innerHTML = readCard();
      try { await api('space/relations/stop', {}); } catch (e) { fail(e); }
    },
    vembplan: async () => {
      const v = S.vemb, c = (S.sp.embedders || [])[Number(v.pick)];
      if (!c) return;
      v.busy = true; v.plan = null; render();
      try { v.plan = await api('space/embedder', { op: 'plan', spec: c.spec }); } catch (e) { fail(e); }
      v.busy = false; render();
    },
    vembuse: async () => {
      const v = S.vemb, c = (S.sp.embedders || [])[Number(v.pick)];
      if (!c) return;
      v.busy = true; render();
      try {
        const st = await api('space/embedder', { op: 'use', spec: c.spec });
        const ad = S.ad;
        spaceChanged(); Object.assign(S, { sp: st, ad });  // the stores' screen stays where it is while they are read again
        toast(`임베딩 모델을 ${st.embedder.name}${josa(st.embedder.name, '으로', '로')} 변경했습니다.`);
        render();
        if (typeof opsReload === 'function') opsReload(); else S.ad = null;
        return;
      } catch (e) { v.busy = false; fail(e); }
      render();
    },
    vembcancel: () => { S.vemb = null; render(); },
    dforget: async () => {
      if (!window.confirm(`${S.dfolder ? `${S.dfolder} 폴더` : '전체 문서'}에서 추출한 관계를 삭제하고 다시 추출합니다.`)) return;
      try { const r = await api('space/relations/forget', { folder: S.dfolder }); toast(`청크 ${r.forgot}개의 관계를 지웠습니다. [관계 추출]을 선택하면 다시 추출합니다.`); } catch (e) { return fail(e); }
      S.dg = null; S.drel = null; S.dq = null; S.sp = null; loadSpace(); render();
    },
    adreason: async (t) => {
      try { S.adrs = { ...(S.adrs || {}), [t.dataset.name]: await api('reasoner', { name: t.dataset.name }) }; render(); } catch (e) { fail(e); }
    },
    reset: async () => {
      if (!window.confirm(S.st.data.kept ? '변경 내용을 삭제하고 예시 상태로 초기화합니다. 저장소 파일은 유지합니다.' : '업로드 데이터와 변경 내용을 삭제하고 예시 상태로 초기화합니다.')) return;
      try {
        await api('reset', {});
        try { sessionStorage.setItem('ontlas-said', '예시 상태로 초기화했습니다.'); } catch (_) { /* the page says nothing after it starts again */ }
        location.reload();  // every screen kept what it read from the space that is gone: the page starts again on the new one
      } catch (e) { fail(e); }
    },
    kind: (t) => { S.kind = t.dataset.kind; S.libFocus = ''; if (S.tab !== 'library') location.hash = '#library'; else render(); },
    // a module named anywhere (a layer, a dependency, a definition's source, a rule's origin) leads to its row in the library
    libshow: (t) => { S.kind = 'all'; S.libFocus = t.dataset.mod; S.libScroll = true; if (S.tab !== 'library') location.hash = '#library'; else render(); },
    // a rule named in an answer leads to that rule in its decision table
    rulego: (t) => { S.mg.dec = t.dataset.dec; S.mg.sel = t.dataset.rule; S.mg.form = null; S.mg.cell = null; if (S.tab !== 'mgrules') location.hash = '#mgrules'; else render(); },
    toggle: (t) => toggleModule(t.dataset.mod),
    detach: (t) => detach(t.dataset.mod, t.dataset.cascade === '1'),
    'cancel-impact': () => { S.impact = null; render(); },
    dallq: () => { S.d.allq = !S.d.allq; render(); },
    select: (t) => {  // on the ontology page the definition opens beside the cards; from elsewhere the page opens on that card
      if (S.tab === 'onto') { selectObject(t.dataset.obj); return; }
      S.ontoPick = t.dataset.obj;
      location.hash = '#onto';
    },
    pick: (t) => pickQuery(t.dataset.q),
    run: () => runQuery(),
    example: (t) => { S.q.question = t.dataset.text; runQuery(); },
    target: (t) => { S.q.target = t.dataset.target; render(); },
    'ask-decision': async (t) => {
      if (S.d.name === t.dataset.name && String(S.d.key) === String(t.dataset.key) && S.d.res) {  // the answer on the page is this question's
        toast('이미 이 질문으로 판정한 결과입니다.');
        const b = $('#main .banner');
        if (b) b.scrollIntoView({ block: 'center' });
        return;
      }
      S.d.name = t.dataset.name; S.d.key = t.dataset.key; S.d.proposal = null; S.d.res = null; render(); await startDecide();
    },
    request: (t) => requestAction(t.dataset.action),
    approve: (t) => approve(t.dataset.id, true),
    reject: (t) => approve(t.dataset.id, false),
    rollback: async (t) => {
      try {
        const r = await api('rollback', { id: t.dataset.id });
        if (!r.ok) throw new Error(r.error);
        S.d.proposal = r.proposal; S.pa = null;
        S.q.res = null; S.qa = null; S.bind = null; S.fl = null; S.d.keys = {}; S.agree = null;
        await load();
        await startDecide();
        toast('실행 전 값으로 되돌렸습니다.');
      } catch (e) { fail(e); }
    },
    login: async () => {
      const b = $('[data-act=login]');
      if (b && b.disabled) return;  // one sign-in at a time: each press counts against the minute's limit
      if (b) { b.disabled = true; b.dataset.was = b.textContent; b.textContent = '로그인 중'; }
      try {
        const r = await api('login', { user: ($('#luser') || {}).value || '', password: ($('#lpw') || {}).value || '' });
        S.me = { team: true, user: r.user };
        await load();
      } catch (e) {
        fail(e);
        const now = $('[data-act=login]');
        if (now) { now.disabled = false; now.textContent = now.dataset.was || '로그인'; }
      }
    },
    logout: async () => { try { await api('logout', {}); } catch (_) { /* signed out anyway */ } S.me.user = null; renderLogin(); },
    sync: async () => {
      try {
        const r = await api('sync', {});
        if (!r.ok) throw new Error(r.error);
        S.fl = null; stale();
        await load();
        toast(r.changed ? '데이터 소스 변경분을 그래프 저장소에 반영했습니다.' : '데이터 소스 변경분이 없습니다.');
      } catch (e) { fail(e); }
    },
    flowsave: async () => {
      try {
        await api('flow/save', { settings: S.flset.settings, base: S.flset.read });  // only what was changed here is written
        S.fl = null; S.flset = null; S.agree = null;
        render();
        toast('통과 조건을 저장했습니다.');
      } catch (e) { fail(e); }
    },
    capprove: (t) => decideChange(t.dataset.id, true),
    creject: (t) => decideChange(t.dataset.id, false),
    dinduce: async () => {
      const target = S.ind.target.slice('property:'.length);
      const inputs = Object.keys(S.ind.inputs).filter((k) => S.ind.inputs[k]);
      try {
        const r = await api('draft/decision', { target, inputs, edits: toEdits() });
        if (!r.ok) throw new Error(r.error);
        S.files = await api('files');
        S.dr.view = 'rules';
        render();
        toast(`판정 표를 만들었습니다. 규칙 ${r.report.rules}개 · 지난 ${r.report.cases}건 중 맞춤 ${pct(r.report.accuracy)}`);
      } catch (e) { fail(e); }
    },
    dinddel: async (t) => {
      try { await api('draft/decision/drop', { name: t.dataset.name }); S.files = await api('files'); S.dr.view = 'rules'; render(); } catch (e) { fail(e); }
    },
    checks: () => runChecks(),
    bindings: () => runBindings(),
    seek: (t) => {
      const v = $('#gvideo');
      if (!v) return;
      v.currentTime = Number(t.dataset.t) + 0.05;
      v.play().catch(() => { /* the viewer starts it */ });
      if (t.classList.contains('btn')) v.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },
    mpipedel: () => {
      const p = S.st.pipelines.find((x) => x.id === S.st.pipeline);
      if (window.confirm(`${p.label} 파이프라인을 삭제합니다.`)) pipelineCall({ op: 'delete', id: p.id });
    },
    mfocus: (t) => { S.mon.focus = t.dataset.k; document.querySelectorAll('.mseg button').forEach((b) => b.classList.toggle('on', b === t)); window.SpaceScene.focus(S.mon.focus); },
    mfault: async () => {
      const m = S.mon.st;
      const f = m.faults.find((x) => x.on) || m.faults[S.mon.fault];
      if (!f) return;
      S.mon.busy = true;
      render();
      try {
        await api(f.on ? 'detach' : 'attach', { name: f.module });
        stale();
        S.st = await api('state');
        S.mon.st = await api('monitor');
      } catch (e) { fail(e); }
      S.mon.busy = false;
      render();
      window.SpaceScene.sweep();
    },
    fsample: () => catalogCall('files/sample', {}, () => { S.cat.next = { files: 0 }; }),
    dsample: async () => { try { await api('files/sample', {}); S.files = await api('files'); render(); } catch (e) { fail(e); } },
    exrecords: (t) => { Object.assign(S.rl, { type: t.dataset.type, q: '', res: null }); location.hash = '#records'; },
    fout: (t) => catalogCall('catalog/include', { paths: [t.dataset.name], on: false }),
    ruopen: (t) => { S.ruopen = S.ruopen === t.dataset.d ? null : t.dataset.d; render(); },
    nfold: (t) => {  // a part of the menu: its name opens its first screen; on one of its screens it folds and unfolds
      const k = t.dataset.k, here = menuRow(curTab());
      const drawer = $('#app').classList.contains('navopen');  // in the drawer a part's name only unfolds it, so its screens can be picked
      if (!drawer && (!here || here[1] !== k)) { S.nopen[k] = true; if (location.hash === t.getAttribute('href')) renderSide(); else location.hash = t.getAttribute('href'); return; }
      S.nopen[k] = !(S.nopen[k] === undefined ? !!(here && here[1] === k) : S.nopen[k]);  // as the menu draws it
      keep('ontlas-nopen', Object.keys(S.nopen).filter((x) => S.nopen[x]).join(','));
      renderSide();
    },
    swlib: async (t) => {  // an ontology picked from the list: its home, whatever screen the person was on
      const id = t.dataset.id, same = !id || id === S.st.library_id;
      ACT.navclose();  // a choice made in the drawer closes it, also when the screen stays
      if (!same && !(await libraryUse(id))) { render(); return; }  // refused: the person stays where they were
      if (S.tab !== 'home' && (areaOf(S.tab) !== 'work' || !same)) location.hash = '#home'; else render();
    },
    // a card's notes open and close where they stand; what was opened stays open while the person is on that screen
    info: (t) => {
      const k = t.dataset.k, on = !S.xp.has(k);
      if (on) S.xp.add(k); else S.xp.delete(k);
      const box = t.dataset.pg ? null : t.closest('.card, .xpbox');
      if (box) box.classList.toggle('xpo', on); else $('#main').classList.toggle('pgo', on);
      t.setAttribute('aria-expanded', on);
    },
    extab: (t) => { S.ex.tab = t.dataset.k; loadExplorer(); },
    exgo: (t) => {
      if (t.dataset.switch) return exSwitch(t.dataset.id.slice(5));
      S.ex.hits = null;
      return loadExplorer(t.dataset.id);
    },
    extoggle: (t) => { S.ex.open[t.dataset.id] = !S.ex.open[t.dataset.id]; render(); },
    exopen: (t) => {
      const id = t.dataset.id, kind = t.dataset.kind;
      if (t.dataset.switch) return exSwitch(id.slice(5));
      if (exHolds(id) || kind === 'folder') { S.ex.hits = null; return loadExplorer(id); }
      if (kind === 'file') return ACT.exview({ dataset: { path: id.slice(5) } });
      if (KIND_TAB[kind]) location.hash = '#' + KIND_TAB[kind];
    },
    exview: async (t) => {
      try { S.cat.file = await api('catalog/file?path=' + encodeURIComponent(t.dataset.path)); S.cat.view = 'preview'; paintLayer(); } catch (e) { fail(e); }
    },
    exsearch: async () => {
      const x = S.ex;
      if (!x.q.trim()) { x.hits = null; return render(); }
      x.busy = true; render();
      try { x.hits = await api(`explorer/search?q=${encodeURIComponent(x.q)}&kind=${encodeURIComponent(x.kind)}`); } catch (e) { fail(e); }
      x.busy = false; render();
    },
    exclear: () => { Object.assign(S.ex, { hits: null, q: '' }); render(); },
    exreload: () => loadExplorer(),
    exnew: () => { S.ex.edit = { id: '', value: '' }; render(); const i = $('#exedit'); if (i) i.focus(); },
    exrename: (t) => {
      const r = S.ex.items.items.concat(S.ex.hits ? S.ex.hits.hits : []).find((x) => x.id === t.dataset.id);
      if (!r) return;
      S.ex.edit = { id: r.id, value: r.label, path: r.path };
      render();
      const i = $('#exedit'); if (i) { i.focus(); i.select(); }
    },
    exsave: async () => {
      const x = S.ex, e = x.edit;
      if (!e) return;
      const name = e.value.trim();
      x.edit = null;
      if (!name || (e.id && name === baseName(e.path))) return render();
      try {
        if (e.id) await api('catalog/rename', { path: e.path, name });
        else await api('catalog/folder', { path: (exFolder(x.node) ? exFolder(x.node) + '/' : '') + name });
        await explorerChanged();
      } catch (err) { fail(err); render(); }
    },
    excancel: () => { S.ex.edit = null; render(); },
    exdelete: async () => {
      const paths = Object.keys(S.ex.sel).filter((k) => S.ex.sel[k]);
      if (!paths.length || !window.confirm(`선택한 ${paths.length}개를 휴지통으로 이동합니다. 폴더는 안의 파일도 함께 이동합니다.`)) return;
      try { await api('catalog/remove', { paths }); toast('휴지통으로 이동했습니다.'); await explorerChanged(); } catch (e) { fail(e); }
    },
    exmove: () => { S.ex.moving = { to: exFolder(S.ex.node) }; render(); },
    exmovecancel: () => { S.ex.moving = null; render(); },
    exmoveok: async () => {
      const x = S.ex, paths = Object.keys(x.sel).filter((k) => x.sel[k]);
      try { await api('catalog/move', { paths, folder: x.moving.to }); x.moving = null; toast(`${paths.length}개를 이동했습니다.`); await explorerChanged(); } catch (e) { fail(e); }
    },
    exupload: () => { Object.assign(S.cat, { folder: exFolder(S.ex.node), sel: {}, ext: '', edit: null, file: null, st: null }); location.hash = '#catalog'; },
    exrestore: async (t) => {
      const x = S.ex, ids = t.dataset.id ? [t.dataset.id] : Object.keys(x.tsel).filter((k) => x.tsel[k]);
      try { const r = await api('catalog/trash', { op: 'restore', ids }); x.tsel = {}; toast(`${count(r.items)}개를 복원했습니다.`); await explorerChanged(); } catch (e) { fail(e); }
    },
    expurge: async (t) => {
      const x = S.ex, all = !!t.dataset.all, ids = all ? [] : t.dataset.id ? [t.dataset.id] : Object.keys(x.tsel).filter((k) => x.tsel[k]);
      if (!all && !ids.length) return;
      if (!window.confirm(all ? '휴지통의 항목을 모두 영구 삭제합니다. 영구 삭제한 항목은 복원할 수 없습니다.' : `선택한 ${ids.length}개를 영구 삭제합니다. 영구 삭제한 항목은 복원할 수 없습니다.`)) return;
      try { await api('catalog/trash', { op: 'purge', ids }); x.tsel = {}; toast('영구 삭제했습니다.'); await loadExplorer(); } catch (e) { fail(e); }
    },
    mapgo: async (t) => {
      S.mapsel = t.dataset.id;
      window.SpaceGraph.focus(t.dataset.id);
      drawGraph();
      try { S.mapn = await api('space/map/node?node=' + encodeURIComponent(t.dataset.id)); $('#mapside').innerHTML = mapSide(); } catch (e) { fail(e); }
    },
    repopick: (t) => {
      const r = t.getBoundingClientRect();
      const was = S.pick;
      closeFloats();
      S.pick = was ? false : { top: r.bottom + 6, right: Math.max(window.innerWidth - r.right, 8) };
      paintLayer();
    },
    repouse: async (t) => { S.pick = false; S.cat.folder = ''; S.cat.ext = ''; await catalogCall('catalog/repository', { op: 'use', id: t.dataset.id }); },
    repomake: async () => {
      const label = ($('#repolabel') || {}).value || '';
      S.pick = false; S.cat.folder = ''; S.cat.ext = '';
      await catalogCall('catalog/repository', { op: 'create', label });
    },
    reporename: async () => {
      const label = ($('#repolabel') || {}).value || '';
      if (!label.trim()) { toast('이름이 없어 저장소 이름을 변경하지 못했습니다. 새 이름을 입력해 주세요.', true); return; }
      S.pick = false;
      await catalogCall('catalog/repository', { op: 'rename', label });
    },
    repodelete: async () => {
      const r = S.st.repository;
      if (!window.confirm(`${r.label} 저장소와 파일 ${count(r.files)}개를 삭제합니다.`)) return;
      S.pick = false; S.cat.folder = ''; S.cat.ext = '';
      await catalogCall('catalog/repository', { op: 'delete' });
    },
    palette: () => { const was = S.pal; closeFloats(); S.pal = was ? null : { q: '', i: 0 }; paintLayer(); },
    palclose: () => closeFloats(),
    palgo: (t) => { const it = palItems()[+t.dataset.i]; if (it) palOpen(it); else { closeFloats(); location.hash = t.getAttribute('href'); } },
    cimport: () => {
      const c = S.cat;
      catalogCall('catalog/import', { path: c.paste, folder: c.folder }, (r) => { c.paste = null; toast(`파일 ${count(r.imported)}개를 가져왔습니다.`); });
    },
    copen: (t) => { closeFloats(); Object.assign(S.cat, { folder: t.dataset.path, sel: {}, ext: '', edit: null, file: null }); loadCatalog(); },
    cup: () => { const c = S.cat; Object.assign(c, { folder: c.folder.includes('/') ? c.folder.slice(0, c.folder.lastIndexOf('/')) : '', sel: {}, ext: '' }); loadCatalog(); },
    creload: async () => { await loadCatalog(); toast('목록을 새로 고쳤습니다.'); },
    cnew: () => { S.cat.edit = { path: '', value: '' }; render(); },
    crename: (t) => { closeFloats(); S.cat.edit = { path: t.dataset.path, value: baseName(t.dataset.path) }; render(); },
    csort: (t) => { const c = S.cat; const k = t.dataset.k; c.dir = c.sort === k ? -c.dir : 1; c.sort = k; render(); },
    cmenu: (t) => {
      const r = t.getBoundingClientRect();
      const same = S.menu && S.menu.path === t.dataset.path;
      closeFloats();
      S.menu = same ? null : { path: t.dataset.path, folder: !!t.dataset.folder, use: t.dataset.use || '', top: Math.min(r.bottom + 4, window.innerHeight - 300), right: Math.max(window.innerWidth - r.right, 8) };
      paintLayer();
    },
    cview: async (t) => {
      closeFloats();
      try { S.cat.file = await api('catalog/file?path=' + encodeURIComponent(t.dataset.path)); S.cat.view = 'preview'; paintLayer(); } catch (e) { fail(e); }
    },
    cdview: (t) => { S.cat.view = t.dataset.v; paintLayer(); },
    cdclose: () => { S.cat.file = null; paintLayer(); },
    cdelete: async (t) => {
      const c = S.cat;
      const paths = t.dataset.path ? [t.dataset.path] : Object.keys(c.sel).filter((k) => c.sel[k]);
      closeFloats();
      if (!paths.length || !window.confirm(paths.length === 1 ? `${baseName(paths[0])}${josa(baseName(paths[0]), '을', '를')} 휴지통으로 이동합니다.` : `선택한 ${paths.length}개를 휴지통으로 이동합니다.`)) return;
      if (c.file && paths.includes(c.file.path)) c.file = null;
      await catalogCall('catalog/remove', { paths });
    },
    cbulk: (t) => catalogCall('catalog/include', { paths: Object.keys(S.cat.sel).filter((k) => S.cat.sel[k]), on: !!t.dataset.on }),
    cembulk: (t) => catalogCall('catalog/embed', { paths: Object.keys(S.cat.sel).filter((k) => S.cat.sel[k]), on: !!t.dataset.on }),
    cclear: () => { S.cat.sel = {}; render(); },
    ctrymode: (t) => { S.ctry.mode = t.dataset.k; S.ctry.res = null; render(); },
    ctryview: (t) => { S.ctry.view = t.dataset.k; render(); },
    cngo: (t) => { const el = document.getElementById(t.dataset.to); if (el) { el.scrollIntoView({ block: 'start', behavior: 'smooth' }); el.classList.add('cnhere'); setTimeout(() => el.classList.remove('cnhere'), 1400); } },
    cnnode: () => {  // the decision call as the settings of an XGEN HTTP request node
      Object.assign(S.ctry, S.ctry.api === 'decide' ? { view: 'node' } : { api: 'decide', view: 'node', res: null, saved: false });
      render();
      const el = document.querySelector('.trycode');
      if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    },
    ctryclear: () => {
      const c = S.ctry;
      Object.assign(c, c.api === 'terms' ? { text: '' } : c.api === 'validate' ? { ovalues: {} } : { values: {}, key: '', at: '' }, { res: null, saved: false });
      render();
    },
    ctryfill: () => {
      const c = S.ctry, d = S.conn.decisions.find((x) => x.name === c.decision);
      if (!d || !d.example) return;
      c.values = Object.fromEntries(Object.entries(d.example.values).map(([k, v]) => [k, v === null ? 'null' : String(v)]));
      c.res = null; c.saved = false; render();
    },
    ctrysave: async () => {
      const c = S.ctry, r = c.res, d = S.conn.decisions.find((x) => x.name === c.decision);
      if (!r || r.status !== 200) return;
      const values = tryBody(c, S.conn).values;
      const said = Object.entries(values).map(([k, v]) => `${(d.inputs.find((i) => i.name === k) || {}).label || k} ${v === null ? '값 없음' : show(v)}`).join(', ');
      try {
        await api('manage/edit', { op: 'add_question', args: { id: `api-${Date.now().toString(36)}`, text: `${d.label}: ${said}`, decision: d.name, values, expect: r.body.outputs } });
        S.mg.st = null; c.saved = true; render(); toast('검증 질문을 작성 중인 변경 요청에 저장했습니다.');
      } catch (e) { fail(e); }
    },
    ctryrun: async () => {
      const c = S.ctry;
      if (c.api === 'terms' && !c.text.trim()) { toast('문장을 입력해 주세요.', true); return; }
      c.busy = true; render();
      c.saved = false;
      try { c.res = await api('rest/try', { path: tryApi(c)[2], body: tryBody(c, S.conn) }); } catch (e) { c.res = { status: 400, body: { error: e.message } }; }
      c.busy = false; render();
    },
    copycode: async (t) => {
      // what was copied, as the button names it (data-say, or its label without 복사)
      const what = t.dataset.say || String(t.getAttribute('aria-label') || '').replace(/\s*복사$/, '').trim() || '내용';
      try { await navigator.clipboard.writeText(t.dataset.v); toast(`${what}${josa(what, '을', '를')} 복사했습니다.`); } catch (_) { toast(`클립보드를 쓸 수 없어 ${what}${josa(what, '을', '를')} 복사하지 못했습니다. 직접 선택해 복사해 주세요.`, true); }
    },
    ccopy: async () => {
      const c = S.cat;
      const text = [c.st.repository.label, c.folder].filter(Boolean).join('/');
      try { await navigator.clipboard.writeText(text); toast('경로를 복사했습니다.'); } catch (_) { toast(text); }
    },
    dtall: (t) => {
      const x = (S.files.definitions || []).find((d) => d.source === t.dataset.src);
      if (x) x.tables.forEach((tb) => { S.dr.tables[tb.name] = t.dataset.on === '1'; });
      render();
    },
    draft: () => {
      const data = (S.files.files || []).flatMap((x) => x.tables.map((t) => t.name));
      const all = data.length ? data : (S.files.definitions || []).flatMap((x) => x.tables.map((t) => t.name));
      const tables = all.filter((n) => S.dr.tables[n] !== false);
      filesCall('draft', { label: S.dr.label, rules: S.dr.rules, tables }, startDraft);
    },
    connect: () => filesCall('connect', { dsn: S.dr.dsn, label: S.dr.label, rules: S.dr.rules }, () => { startDraft(); location.hash = '#data'; }),
    gwconnect: () => filesCall('connect/gateway', { ...S.gw, label: S.dr.label, rules: S.dr.rules }, () => { S.gw.token = ''; startDraft(); location.hash = '#data'; }),
    dview: (t) => { S.dr.view = t.dataset.view; refreshDraft(); const box = $('#draft'); if (box) box.scrollIntoView({ block: 'start' }); },
    dpick: (t) => { S.dr.pick = t.dataset.t; refreshDraft(); },
    dchoose: (t) => {
      const p = S.files.pending, x = p.steps.find((st) => st.id === 'objects').items.find((y) => y.table === t.dataset.t);
      S.dr.choice[t.dataset.t] = t.dataset.c;
      if (x) S.dr.ok[x.element] = true;
      edited();
    },
    dok: (t) => { S.dr.ok[t.dataset.el] = true; refreshDraft(); },
    dokall: () => {
      const p = S.files.pending, cur = reviewStep(), st = p.steps.find((x) => x.id === cur);
      if (cur === 'objects') {
        for (const x of st.items) {
          const r = objProposal(p, x);
          if (r.status !== 'check') continue;
          if (!r.choice) S.dr.choice[x.table] = r.sm ? 'standard' : 'new';
          else if (r.clash && r.sm) S.dr.choice[x.table] = 'standard';
          S.dr.ok[x.element] = true;
        }
        edited();
        const left = st.items.filter((x) => objProposal(p, x).status === 'check').length;
        if (left) toast(`이름이 표준 Entity와 같은 테이블 ${left}개는 API 이름을 바꾸거나 표준에 연결해 주세요.`, true);
        return;
      }
      for (const x of st.items) S.dr.ok[x.element] = true;
      refreshDraft();
    },
    dsettle: () => {  // on the last step: each table left unsettled goes to the standard object it matched
      const p = S.files.pending;
      for (const x of p.steps.find((st) => st.id === 'objects').items) {
        const r = objProposal(p, x);
        if (r.status === 'check' && r.sm) { S.dr.choice[x.table] = 'standard'; S.dr.ok[x.element] = true; }
      }
      edited();
    },
    dsetup: () => { S.dr.setup = !S.dr.setup; render(); },
    drv: (t) => { S.dr.rv = t.dataset.k; refreshDraft(); },
    dsel: () => { S.dr.sel = null; refreshDraft(); },
    drrules: () => { S.dr.rulesOpen = !S.dr.rulesOpen; render(); },
    'drules-reset': () => { S.dr.rules = JSON.parse(JSON.stringify(S.files.defaults)); render(); },
    dadd: () => {
      const box = $('#ddetail');
      const v = (k) => (box.querySelector(`[data-in="${k}"]`) || {}).value || '';
      S.dr.ed.add.push({ source: v('dasrc'), property: v('daprop'), target: v('datgt'), cardinality: v('dacard') || 'many_to_one', label: S.dr.add.label.trim() });
      S.dr.add.label = '';
      edited();
    },
    dadddel: (t) => { S.dr.ed.add.splice(Number(t.dataset.i), 1); edited(); },
    iresolve: async (t) => {
      try {
        const r = await api('identity/resolve', { name: t.dataset.name });
        if (!r.ok) throw new Error(r.error);
        S.ident = null; stale();
        await load();
        toast(`기록 ${r.records}건을 ${r.identities}건으로 통합해 교차표를 저장했습니다.`);
      } catch (e) { fail(e); }
    },
    medit: async (t) => {
      try { await openModule(t.dataset.mod); render(); requestAnimationFrame(() => { const e = $('#editor'); if (e) e.scrollIntoView({ behavior: 'smooth', block: 'start' }); }); } catch (e) { fail(e); }
    },
    mnew: () => { S.ed = { name: '', label: '새 모듈', applied: false, isNew: true, text: moduleTemplate(), check: null, busy: false }; render(); },
    mclose: () => { S.ed = null; S.change = null; render(); },
    mcheck: async () => {
      try { S.ed.check = await api('module/check', { text: S.ed.text }); } catch (e) { S.ed.check = { error: e.message }; }
      const r = $('#mresult');
      if (r) r.innerHTML = moduleCheck();
    },
    mpropose: async (t) => {
      S.ed.busy = true;
      render();
      try {
        const r = await api('module/propose', { text: S.ed.text, apply: t.dataset.apply === '1' });
        S.ed.busy = false;
        S.ed.check = null;
        S.change = r.change;
        S.changes = null;
        S.st = await api('state');
        render();
        toast(`변경 요청 ${r.change.id}${josa(r.change.id, '을', '를')} ${r.change.passed ? '' : '미통과 상태로 '}등록했습니다.`, !r.change.passed);
      } catch (e) {
        S.ed.busy = false;
        S.ed.check = { error: e.message };
        render();
      }
    },
    mgrule: (t) => mgOpenMore('rule', t.dataset.name),
    celledit: (t) => {
      const d = S.mg.st.decisions.find((x) => x.name === S.mg.dec), r = d && d.rules.find((x) => x.id === t.dataset.rule);
      if (!r) return;
      S.mg.cell = { rule: r.id, input: t.dataset.k, part: { ...(r.when[t.dataset.k] || { op: 'any', value: '' }) } };
      render();
      cellFocus(true);
    },
    cellx: () => { S.mg.cell = null; render(); },
    cellsave: () => {
      const c = S.mg.cell, d = S.mg.st.decisions.find((x) => x.name === S.mg.dec), r = d && d.rules.find((x) => x.id === c.rule);
      if (!r) return;
      const old = r.when[c.input] || { op: 'any', value: '' }, was = old.value;
      c.part = cellSaid() || c.part;
      S.mg.cell = null; S.mg.sel = r.id;
      if (c.part.op === old.op && String(c.part.value ?? '') === String(old.value ?? '')) { render(); return; }  // nothing changed: no edit to record
      mgEdit('update_rule', { decision: d.name, id: r.id, when: { ...r.when, [c.input]: c.part }, then: r.then, cite: r.cite || '' }, `규칙 ${r.id}의 조건을 바꿨습니다.`)
        .then(() => { staleCheck(d.name, was, c.part.value); rulesEdited(); render(); });
    },
    stalefix: async () => {
      const s = S.mg.stale;
      S.mg.stale = null;
      if (!s) return;
      for (const id of s.rules) {
        const d = S.mg.st.decisions.find((x) => x.name === s.decision), r = d && d.rules.find((x) => x.id === id);
        if (!r) continue;
        const then = Object.fromEntries(Object.entries(r.then).map(([k, v]) => [k, typeof v === 'string' ? v.replace(numAt(s.from), `$1${s.to}`) : v]));
        await mgEdit('update_rule', { decision: d.name, id, when: r.when, then, cite: r.cite || '' }, `사유 문구 ${s.rules.length}곳의 ${s.from}${josa(s.from, '을', '를')} ${s.to}${josa(s.to, '으로', '로')} 변경했습니다.`);
      }
      rulesEdited();
    },
    staleskip: () => { S.mg.stale = null; render(); },
    simedges: () => { S.sim.edges = !S.sim.edges; render(); },
    mgparam: (t) => mgOpenMore('param', t.dataset.name),
    mgstate: (t) => mgOpenMore('states', t.dataset.name),
    mgclose: () => { S.mg.form = null; S.mg.sel = ''; render(); },
    fvaladd: () => { const s = S.flset.settings; (s.values = s.values || []).push({ name: '', label: '', query: '', key: '', truth: '', answer: {} }); render(); },
    fvaldel: (t) => { S.flset.settings.values.splice(Number(t.dataset.i), 1); render(); },
    mgrowadd: (t) => { S.mg.form.v[t.dataset.list].push({ ...NEW_ROW[t.dataset.list] }); render(); },
    mgrowdel: (t) => { S.mg.form.v[t.dataset.list].splice(Number(t.dataset.i), 1); render(); },
    mgrulenew: () => {
      const d = S.mg.st.decisions.find((x) => x.name === S.mg.dec);
      S.mg.sel = '';
      S.mg.form = { kind: 'rule', mode: 'new', v: { id: '', cite: '', first: true, when: Object.fromEntries(d.inputs.map((i) => [i.name, { op: 'any', value: '' }])), then: Object.fromEntries(d.outputs.map((o) => [o.name, o.type === 'boolean' ? true : ''])) } };
      render();
    },
    mgdecnew: () => { S.mg.sel = ''; S.mg.form = { kind: 'decision', mode: 'new', v: { name: '', label: '', target: (S.mg.st.objects.find((o) => !o.concept) || S.mg.st.objects[0] || {}).name || '', inputs: [{ property: '' }], otherwise: '해당하는 규칙이 없습니다' } }; render(); },
    mgstatenew: () => { const o = S.mg.st.objects.find((x) => !x.states); S.mg.sel = ''; S.mg.form = { kind: 'states', mode: 'new', v: { object: o ? o.name : '', property: '', states: '', initial: '', transitions: [] } }; render(); },
    mgparamnew: () => { S.mg.sel = ''; S.mg.form = { kind: 'param', mode: 'new', v: { name: '', label: '', type: 'integer', value: '', unit: '', cite: '', min: '', max: '' } }; render(); },
    mgmetric: (t) => mgOpenMore('metric', t.dataset.name),
    mgmetricnew: () => { S.mg.sel = ''; S.mg.form = { kind: 'metric', mode: 'new', v: { name: '', label: '', owner: '', object: (S.mg.st.objects.find((o) => !o.concept) || S.mg.st.objects[0] || {}).name || '', fn: 'count', prop: '', where: [], den: [], ratio: false, den_label: '', unit: '', scale: 1, basis: '', time_prop: '', description: '', cite: '' } }; render(); },
    mgident: (t) => mgOpenMore('identity', t.dataset.name),
    mgidentnew: () => { S.mg.sel = ''; S.mg.form = { kind: 'identity', mode: 'new', v: { name: '', label: '', imembers: [{ ...NEW_ROW.imembers }], irules: [{ ...NEW_ROW.irules }] } }; render(); },
    mgfn: (t) => { S.mg.fnres = null; S.mg.fnkey = ''; S.mg.fnin = {}; mgOpenMore('function', t.dataset.name); },
    mgfnnew: () => { S.mg.sel = ''; S.mg.fnres = null; S.mg.form = { kind: 'function', mode: 'new', v: { name: '', label: '', runtime: 'expr', target: (S.mg.st.objects.find((o) => !o.concept) || S.mg.st.objects[0] || {}).name || '', expr: '', decision: '', query: '', entry: '', url: '', method: 'POST', path: '', fin: [], fout: [{ name: 'value', type: 'decimal' }], version: '1.0.0', owner: '', status: 'draft', depends: '', description: '', cite: '' } }; render(); },
    actrygo: async () => {
      const t = S.mg.actry;
      S.mg.busy = true; render();
      try { t.res = await api('request', { action: t.action, key: t.key, params: t.params, role: t.role, kind: t.kind }); S.mg.st = await api('manage'); } catch (e) { t.res = { error: e.message }; }
      S.pa = null; S.mg.busy = false; render();
    },
    fnrun: async () => {
      const fx = S.mg.st.functions.find((y) => y.name === S.mg.form.v.name);
      if (fx && fx.target && !String(S.mg.fnkey || '').trim()) { S.mg.fnres = { ok: false, error: `${mgLabel(fx.target)} 번호가 없어 함수를 실행하지 못했습니다. ${mgLabel(fx.target)} 번호를 입력해 주세요.` }; render(); return; }
      S.mg.busy = true; render();
      try { S.mg.fnres = await api('function/run', { name: S.mg.form.v.name, key: S.mg.fnkey || '', params: S.mg.fnin || {} }); } catch (e) { S.mg.fnres = { ok: false, error: e.message }; }
      S.mg.busy = false; render();
    },
    mgobjnew: (t) => {
      const tb = t.dataset.t || '';
      const x = tb ? mgTable(tb) : null;
      S.mg.sel = '';
      S.mg.form = { kind: 'object', mode: 'new', v: { table: tb, name: tb ? typeName(tb) : '', label: '', key: x ? (x.key[0] || (x.columns[0] || {}).name || '') : '', parent: '', description: '', cols: true } };
      if (S.tab !== 'model') { S.mg.keep = true; location.hash = '#model?ws=1'; } else render();  // the form is the workspace's
    },
    mgpropnew: () => {
      const m = S.mg.st;
      const obj = S.mg.obj || (m.objects.find((o) => o.table) || m.objects[0] || {}).name || '';
      S.mg.sel = '';
      S.mg.form = { kind: 'prop', mode: 'new', v: { object: obj, name: '', label: '', description: '', type: 'string', column: '', values: '', unit: '', required: false, mask: '', expr: '' } };
      render();
    },
    mglinknew: () => {
      S.mg.sel = '';
      S.mg.form = { kind: 'link', mode: 'new', v: { name: '', label: '', source: S.mg.obj || '', target: '', sp: '', tp: '', cardinality: 'many_to_one', inverse: '', required: false } };
      render();
    },

    mgcancel: () => { S.mg.form = null; S.mg.sel = ''; render(); },
    mgsave: () => mgSave(),
    mgdel: () => mgDelete(),
    mgsug: (t) => {
      const x = fkSuggestions()[Number(t.dataset.i)];
      if (x) mgEdit('add_link', { name: x.name, label: mgLabel(x.target), source: x.source, target: x.target, on: [x.sp, x.tp], cardinality: 'many_to_one' }, `Relation ${x.name}${josa(x.name, '을', '를')} 추가했습니다.`);
    },
    mgopen: () => { S.mg.open = !S.mg.open; render(); },
    mgreview: async () => {  // the pending changes opened and tried on a copy before anything is applied
      S.mg.open = true;
      if (S.mg.st.workspace.issues.length) { render(); return; }
      S.md.trial = { busy: true }; render();
      try { S.md.trial = await api('manage/trial', {}); } catch (e) { S.md.trial = { error: e.message }; }
      render();
    },
    mgdiscard: async () => {
      if (!window.confirm('대기 중인 변경을 모두 취소합니다. 표준 모듈과 승인된 변경은 유지됩니다.')) return;
      try { S.mg.st = await api('manage/discard', {}); S.mg.form = null; S.mg.sel = ''; S.mg.review = null; S.md.trial = null; toast('대기 중인 변경을 취소했습니다.'); } catch (e) { fail(e); }
      render();
    },
    mgpropose: async () => {
      S.mg.busy = true; render();
      try {
        const r = await api('manage/propose', {});
        if (!r.ok) {
          const { error, change, ok, ...state } = r;
          S.mg.st = state; S.mg.review = change; S.mg.busy = false; S.changes = null;
          render();
          fail(new Error(r.error));
          return;
        }
        S.mg.review = null;
        stale();
        S.mg.st = r; S.mg.form = null; S.mg.sel = ''; S.mg.open = false; S.md.trial = null;
        if (S.md.left === 'changes') S.md.left = 'objects';  // nothing left to review: the tree again
        S.changes = null; S.change = r.change; S.agree = null; S.flset = null; S.pos = {};
        S.mg.busy = false;
        await load();
        if (S.fix) await fixRecheck(r.pending);
        const made = r.pending ? '' : await deployedWord();
        toast(r.pending ? '변경 요청을 등록했습니다.' : made ? `${made}${josa(made, '을', '를')} 배포했습니다.` : '변경을 적용했습니다.');
        if (r.warning) toast(r.warning, true);
      } catch (e) { S.mg.busy = false; render(); fail(e); }
    },
    dapply: async () => {
      const got = draftChoices();
      if (!got) return;
      S.dr.busy = true;
      render();
      try {
        await api('draft/review/apply', { standard: S.map.picked, edits: toEdits(), choices: got });
        await draftApplied();
      } catch (e) { S.dr.busy = false; render(); fail(e); }
    },
    drequest: async () => {  // in a team, an editor's last step: the reviewed draft goes to an approver as it stands
      const got = draftChoices();
      if (!got) return;
      S.dr.busy = true;
      render();
      try {
        await api('draft/request', { standard: S.map.picked, edits: toEdits(), choices: got });
        S.dr.busy = false;
        await loadFiles();
        toast('적용 요청을 보냈습니다. 승인자가 할 일이나 초안 화면에서 적용합니다.');
      } catch (e) { S.dr.busy = false; render(); fail(e); }
    },
    drequestdrop: async () => {
      try { await api('draft/request/drop', {}); } catch (e) { fail(e); return; }
      S.home.box = null;
      await loadFiles();
      if (S.tab !== 'data') render();
      toast('초안 적용 요청을 취소했습니다.');
    },
    drequestapply: async () => {
      S.dr.busy = true;
      render();
      try {
        await api('draft/request/apply', {});
        await draftApplied();
      } catch (e) { S.dr.busy = false; render(); fail(e); }
    },
  };

  function draftChoices() {  // every table settled as standard or new; otherwise the first unsettled one is shown and nothing goes
    const p = S.files.pending, os = p.steps.find((x) => x.id === 'objects');
    const rows = os.items.map((x) => objProposal(p, x)).filter((r) => r.status !== 'off');
    const left = rows.filter((r) => r.status === 'check');
    if (left.length) { S.dr.view = 'objects'; S.dr.pick = left[0].x.table; render(); toast(`확인할 테이블 ${left.length}개가 남아 적용하지 못했습니다. 표준에 연결할지 새 Entity로 둘지 정해 주세요.`, true); return null; }
    return Object.fromEntries(rows.map((r) => [r.x.table, r.choice]));
  }

  async function draftApplied() {  // the space is another one now: everything read from the old one goes
    Object.assign(S, { impact: null, pos: {}, sel: null, gsel: null, files: null, dpos: {}, cat: NEW_CAT(), conv: null });
    S.map = { standards: null, picked: [], sug: null, edits: { objects: {}, columns: {} }, busy: false, auto: '' };
    S.changes = null; S.agree = null; S.flset = null;
    stale();
    S.q.name = null; S.q.text = ''; S.q.dirty = false; S.q.role = ''; S.q.principal = {}; S.d.name = null; S.d.key = null;
    S.dr.busy = false;
    await load();
    location.hash = '#flow';
    const now = S.st.pipelines.find((p) => p.id === S.st.pipeline);  // applying adds a pipeline and moves to it
    toast('초안을 적용했습니다.');
  }

  const INPUT = {
    gxq: (t) => { S.gx.q = t.value; gxFindSoon('start'); },
    gxfromq: (t) => { S.gx.fromq = t.value; S.gx.from = null; gxFindSoon('from'); },
    gxtoq: (t) => { S.gx.toq = t.value; S.gx.to = { type: '', key: '' }; gxFindSoon('to'); },
    lxf: (t) => { S.lx.form.v[t.dataset.f] = t.value; },
    mdq: (t) => { S.md.q = t.value; const b = $('#mdtree'); if (b) b.innerHTML = modelTree(); },
    mdcq: (t) => {  // only that column's rows, so the box keeps the cursor
      S.md.cq[t.dataset.k] = t.value;
      const o = mgObj(S.md.sel), html = { objects: colObjects, props: () => colProps(o), links: () => colLinks(o) }[t.dataset.k]();
      const box = $(`#col-${t.dataset.k} .wscolb`), now = document.createElement('div');
      now.innerHTML = html;
      if (box) box.innerHTML = now.querySelector('.wscolb').innerHTML;
    },
    chgtext: (t) => { S.chg.text = t.value; },
    simval: (t) => { S.sim.vals[t.dataset.k] = t.value; },
    homeq: (t) => { S.home.q = t.value; },
    rlq: (t) => { S.rl.q = t.value; },
    rparam: (t) => { S.rec.params[t.dataset.k] = t.value; },
    exq: (t) => { S.ex.q = t.value; },
    exedit: (t) => { if (S.ex.edit) S.ex.edit.value = t.value; },
    gwurl: (t) => { S.gw.url = t.value; },
    gwconn: (t) => { S.gw.connection = t.value; },
    gwdialect: (t) => { S.gw.dialect = t.value; },
    gwtoken: (t) => { S.gw.token = t.value; },
    srtext: (t) => { S.sr.text = t.value; },
    srfolder: (t) => { S.sr.folder = t.value; },
    cellv: (t) => {  // the text stays as typed; "14일 이하" shows its comparison beside it and is read when the cell is saved
      if (!S.mg.cell) return;
      S.mg.cell.part.value = t.value;
      const said = cellSaid(), op = $('.celled [data-in="cellop"]');
      if (said && op && [...op.options].some((o) => o.value === said.op)) op.value = said.op;
    },
    mdyaml: (t) => { if (S.md.yaml) S.md.yaml.text = t.value; const b = $('[data-act=mdyamlsave]'); if (b) b.disabled = S.md.yaml.text === S.md.yaml.was; },
    mdnote: (t) => { S.md.note = t.value; },
    srfkey: (t) => { S.sr.fix.key = t.value; },
    srfat: (t) => { S.sr.fix.at = t.value; },
    dfolder: (t) => { S.dfolder = t.value; S.dg = null; S.drel = null; S.dsec = null; S.dgx.sel = ''; render(); },
    dreader: (t) => { S.dreader = t.value; },
    vemb: (t) => { S.vemb = { pick: t.value, plan: null, busy: false }; render(); },
    cedit: (t) => { if (S.cat.edit) S.cat.edit.value = t.value; },
    cpath: (t) => { S.cat.paste = t.value; },
    param: (t) => { S.q.params[t.dataset.k] = t.value; },
    principal: (t) => { S.q.principal[t.dataset.k] = t.value; },
    text: (t) => { S.q.text = t.value; S.q.dirty = true; },
    question: (t) => { S.q.question = t.value; },
    aparam: (t) => { S.d.params[t.dataset.k] = t.value; },
    dname: (t) => { S.dr.label = t.value; },
    dsn: (t) => { S.dr.dsn = t.value; },
    dlab: (t) => { S.dr.ed.labels[t.dataset.el] = t.value; if (t.dataset.el.startsWith('object:')) drawGraph(); },
    dapi: (t) => { S.dr.names[t.dataset.obj] = t.value.trim(); },
    dvalues: (t) => { S.dr.ed.values[t.dataset.ref] = t.value; },
    dalabel: (t) => { S.dr.add.label = t.value; },
    drule: (t) => {
      if (t.type === 'number') S.dr.rules[t.dataset.k] = Number(t.value);
      else if (t.type === 'text') S.dr.rules[t.dataset.k] = t.value.split(',').map((x) => x.trim()).filter(Boolean);
    },
    mtext: (t) => { S.ed.text = t.value; },
    libnl: (t) => { S.lib.label = t.value; },
    libnk: (t) => { S.lib.key = t.value; },
    mgf: (t) => {
      const f = S.mg.form;
      if (t.type === 'checkbox' || !f) return;
      f.v[t.dataset.f] = t.value;
      if (t.dataset.f === 'name') { f.v.touched = !!t.value; paintName(); }  // emptied, it follows the display name again
      if (t.dataset.f === 'label' && naming(f) && !f.v.touched) suggestName(f);
    },
    mgwhen: (t) => { S.mg.form.v.when[t.dataset.k] = { ...(S.mg.form.v.when[t.dataset.k] || { op: 'any', value: '' }), [t.dataset.p]: t.value }; },
    mgthen: (t) => { S.mg.form.v.then[t.dataset.k] = t.dataset.t === 'boolean' ? t.value === 'true' : (['integer', 'decimal', 'number'].includes(t.dataset.t) && t.value !== '' ? Number(t.value) : t.value); },
    mgrow: (t) => { S.mg.form.v[t.dataset.list][Number(t.dataset.i)][t.dataset.f] = t.value; },
    ctryv: (t) => { const c = S.ctry; c.values = { ...(c.values || {}), [t.dataset.k]: t.value }; repaintTry(); },
    ctryk: (t) => { S.ctry.key = t.value; repaintTry(); },
    ctryt: (t) => { S.ctry.text = t.value; repaintTry(); },
    ctryo: (t) => { Object.assign(S.ctry, { object: t.value, ovalues: {}, res: null }); render(); },
    ctryov: (t) => { const c = S.ctry; c.ovalues = { ...(c.ovalues || {}), [t.dataset.k]: t.value }; repaintTry(); },
    ctryc: (t) => { S.ctry.complete = t.value === '1'; repaintTry(); },
    ctryat: (t) => { S.ctry.at = t.value; repaintTry(); },
    ctryd: (t) => { Object.assign(S.ctry, { decision: t.value, values: {}, res: null }); render(); },
    fnkey: (t) => { S.mg.fnkey = t.value; },
    actrykey: (t) => { S.mg.actry.key = t.value; },
    actry: (t) => { S.mg.actry.params[t.dataset.k] = t.value; },
    actryrole: (t) => { S.mg.actry.role = t.value; },
    actrykind: (t) => { S.mg.actry.kind = t.value; },
    fnin: (t) => { (S.mg.fnin = S.mg.fnin || {})[t.dataset.k] = t.value; },
    fgate: (t) => {
      const g = S.flset.settings.gates;
      const stage = t.dataset.s, k = t.dataset.k;
      g[stage] = g[stage] || {};
      if (t.value === '') delete g[stage][k];
      else g[stage][k] = k.startsWith('min_') ? Number(t.value) / 100 : Number(t.value);
    },
  };

  const CHANGE = {
    semtype: (t) => { S.sem.type = t.value; render(); },
    hrole: (t) => ACT.hrole(t),
    srfdec: (t) => { S.sr.fix.decision = t.value; render(); },
    gxlayout: (t) => { S.gx.layout = t.value; S.gx.pos = {}; S.gx.zoomed = false; gxRedraw(); },
    dgxlayout: (t) => { S.dgx.layout = t.value; S.dgx.pos = {}; S.dgx.zoomed = false; dgxPaint(); },
    dgxseed: (t) => { if (t.value) { dgxAround(t.value); render(); } },
    gxrel: (t) => { if (t.checked) gxGrow(S.gx.sel, t.dataset.link, t.dataset.fw === '1'); else gxShrink(S.gx.sel, t.dataset.link, t.dataset.fw === '1'); },
    gxshow: (t) => { S.gx.hide = t.checked ? S.gx.hide.filter((x) => x !== t.dataset.t) : [...S.gx.hide, t.dataset.t]; S.gx.view = ''; render(); },
    gxview: (t) => { gxApplyView(t.value); render(); },
    gxviewrole: (t) => { S.gx.viewRole = t.value; },
    gxcolor: (t) => { S.gx.color = { ...S.gx.color, [t.dataset.t]: t.value }; S.gx.view = ''; render(); },
    gxlabel: (t) => { S.gx.labelBy = { ...S.gx.labelBy }; if (t.value) S.gx.labelBy[t.dataset.t] = t.value; else delete S.gx.labelBy[t.dataset.t]; S.gx.view = ''; gxFetchLabels().then(render); },
    recrole: (t) => { S.rec.seeAs = t.value; render(); },
    simkey: (t) => { S.sim.key = t.value; S.sim.vals = {}; simulateNow(t.value, {}); },
    simval: (t) => { S.sim.vals[t.dataset.k] = t.value; },
    rltype: (t) => { S.rl.type = t.value; S.rl.res = null; render(); },  // the words stay: the same search in another type
    rrole: (t) => { S.rec.role = t.value; },
    exkind: (t) => { S.ex.kind = t.value; if (S.ex.hits) ACT.exsearch(); },
    exsel: (t) => { S.ex.sel[t.dataset.path] = t.checked; render(); },
    extsel: (t) => { S.ex.tsel[t.dataset.id] = t.checked; render(); },
    exto: (t) => { S.ex.moving.to = t.value; },
    ptarget: (t) => { S.pol.target = t.value; },
    medver: async (t) => { try { await openModule(S.ed.name, t.value); render(); toast(`${t.value} 버전을 불러왔습니다. [변경 요청]을 선택하면 새 버전으로 되돌립니다.`); } catch (e) { fail(e); } },
    pdoc: (t) => loadDocument(t.value, ''),
    psec: (t) => loadDocument(S.pol.doc, t.value),
    mgpobj: (t) => { S.mg.obj = t.value; S.mg.form = null; S.mg.sel = ''; render(); },
    qbtype: (t) => { Object.assign(S.q.b, { type: t.value, link: '', fields: [], conds: [] }); render(); },
    qblink: (t) => { S.q.b.link = t.value; S.q.b.fields = S.q.b.fields.filter((f) => f.startsWith('x.')); S.q.b.conds = S.q.b.conds.filter((c) => c.prop.startsWith('x.')); render(); },
    qbfield: (t) => { const b = S.q.b; b.fields = t.checked ? [...b.fields, t.dataset.k] : b.fields.filter((f) => f !== t.dataset.k); },
    qbc: (t) => { S.q.b.conds[Number(t.dataset.i)][t.dataset.f] = t.value; render(); },
    mgdec: (t) => { S.mg.dec = t.value; S.mg.form = null; S.mg.sel = ''; S.mg.cell = null; render(); },
    mgpolicy: (t) => mgEdit('update_decision', { decision: S.mg.dec, hit_policy: t.value }, `적용 방식을 ${POLICY_WORD[t.value]}${josa(POLICY_WORD[t.value], '으로', '로')} 변경했습니다.`).then(rulesEdited),
    cellop: (t) => { const c = S.mg.cell, said = cellSaid(); if (said) c.part.value = said.value; c.part.op = t.value; render(); cellFocus(); },
    mgwhen: (t) => {
      const w = S.mg.form.v.when, k = t.dataset.k;
      const i = S.mg.st.decisions.find((x) => x.name === S.mg.dec).inputs.find((x) => x.name === k);
      if (t.dataset.p === 'value') {  // a phrase like "14일 이하" sets the comparison too
        const said = cellPhrase(t.value, i, (w[k] || {}).op);
        w[k] = said || { ...(w[k] || { op: 'any', value: '' }), value: t.value };
        if (said) render();
        return;
      }
      w[k] = { ...(w[k] || { op: 'any', value: '' }), op: t.value };
      if (!w[k].value && ['eq', 'ne'].includes(t.value)) w[k].value = i.type === 'boolean' ? 'true' : (i.values[0] || '');
      render();
    },
    mgthen: (t) => { S.mg.form.v.then[t.dataset.k] = t.dataset.t === 'boolean' ? t.value === 'true' : (['integer', 'decimal', 'number'].includes(t.dataset.t) && t.value !== '' ? Number(t.value) : t.value); },
    mgrow: (t) => {
      const row = S.mg.form.v[t.dataset.list][Number(t.dataset.i)];
      row[t.dataset.f] = t.value;
      if (t.dataset.list === 'criteria' && t.tagName === 'SELECT' && t.dataset.f !== 'value') render();
      if (['rows', 'scopes', 'imembers'].includes(t.dataset.list) && t.tagName === 'SELECT' && ['type', 'via', 'mode', 'property'].includes(t.dataset.f)) render();
    },
    mgtick: (t) => {
      const list = S.mg.form.v[t.dataset.list], at = list.indexOf(t.dataset.v);
      if (t.checked && at < 0) list.push(t.dataset.v);
      if (!t.checked && at >= 0) list.splice(at, 1);
      if (t.dataset.v === '*') render();
    },
    mddraftopt: (t) => {
      const d = S.md.draft, i = Number(t.value), o = d.res.options[i];
      Object.assign(d, o ? { sp: o.sp, tp: o.tp, cardinality: o.cardinality } : { sp: '', tp: '' });
      paintDraft();
    },
    mddraft: (t) => { const d = S.md.draft; d[t.dataset.f] = t.value; if (['sp', 'tp'].includes(t.dataset.f)) paintDraft(); },
    mgf: (t) => {
      const f = S.mg.form;
      if (!f) return;
      const v = f.v, k = t.dataset.f;
      v[k] = t.type === 'checkbox' ? t.checked : t.value;
      if (!t.dataset.re) return;
      if (f.kind === 'object' && k === 'table') {
        const x = v.table ? mgTable(v.table) : null;
        v.key = x ? (x.key[0] || (x.columns[0] || {}).name || '') : '';
        if (!v.touched && !String(v.label || '').trim()) v.name = v.table ? typeName(v.table) : '';  // a display name already names it
      }
      if (f.kind === 'prop' && k === 'object') v.column = '';
      if (f.kind === 'prop' && k === 'column' && f.mode === 'new' && v.column) {
        if (!v.touched && !v.label) v.name = propName(v.column);
        if (!v.label) v.label = v.column;
        const c = columnsOf(v.object).find((x) => x.name === v.column);
        if (c) v.type = sqlType(c.type);
      }
      if (f.kind === 'link' && k === 'source') v.sp = '';
      if (f.kind === 'link' && k === 'target') {
        const o = mgObj(v.target);
        v.tp = o ? o.key : '';
        if (f.mode === 'new' && !v.touched && v.target) v.name = lowerFirst(v.target);
      }
      if (f.kind === 'link' && v.source && v.tp && !v.sp && mgProps(v.source).some((p) => p.name === v.tp)) v.sp = v.tp;
      if (f.kind === 'question' && k === 'decision') { v.values = {}; v.expectv = {}; }  // another decision takes other values
      if (t.tagName === 'INPUT' && t.type === 'text') setTimeout(() => repaintKept(true), 0);  // once the cursor has moved on
      else repaintKept(false);
    },
    role: async (t) => { S.q.role = t.value; S.q.principal = {}; await principalDefaults(S.q); render(); },
    lang: (t) => { S.q.lang = t.value; if (!S.q.dirty || !S.q.text) { S.q.text = textFor(S.q.lang) || S.q.text; S.q.dirty = false; } render(); },
    decision: async (t) => { S.d.name = t.value; S.d.key = null; S.d.res = null; S.d.proposal = null; render(); await startDecide(); },
    key: async (t) => { S.d.key = t.value; S.d.proposal = null; await decide(); },
    arole: (t) => { S.d.role = t.value; },
    akind: (t) => { S.d.kind = t.value; },
    dkeep: (t) => { S.dr.ed.drop[t.dataset.el] = !t.checked; edited(); },
    dlab: () => { clearTimeout(previewTimer); previewTimer = setTimeout(preview, 150); },
    dvalues: () => { clearTimeout(previewTimer); previewTimer = setTimeout(preview, 150); },
    dkey: (t) => { S.dr.ed.keys[t.dataset.obj] = t.value; edited(); },
    dapi: () => edited(),
    dtype: (t) => { S.dr.ed.types[t.dataset.ref] = t.value; edited(); },
    dcard: (t) => { S.dr.ed.card[t.dataset.link] = t.value; clearTimeout(previewTimer); previewTimer = setTimeout(preview, 150); },
    dtable: (t) => { S.dr.tables[t.dataset.t] = t.checked; },
    drule: (t) => {
      if (t.type !== 'checkbox') return;
      const r = S.dr.rules;
      if (t.dataset.v) r.queries = t.checked ? [...new Set([...r.queries, t.dataset.v])] : r.queries.filter((x) => x !== t.dataset.v);
      else r[t.dataset.k] = t.checked;
    },
    dasrc: (t) => { S.dr.add.source = t.value; S.dr.add.property = ''; refreshDraft(); },
    daprop: (t) => { S.dr.add.property = t.value; },
    datgt: (t) => { S.dr.add.target = t.value; },
    dacard: (t) => { S.dr.add.cardinality = t.value; },
    fstage: (t) => {
      const s = S.flset.settings;
      s.off = t.checked ? s.off.filter((x) => x !== t.dataset.k) : [...new Set([...s.off, t.dataset.k])];
    },
    fval: (t) => {
      const s = S.flset.settings, v = s.values[Number(t.dataset.i)], k = t.dataset.k;
      if (k === 'by') {
        const [kind, name] = t.value.split(':');
        v.answer = t.value ? { [kind]: name, output: '' } : {};
        render();
        return;
      }
      if (k === 'output') { v.answer = { ...(v.answer || {}), output: t.value }; return; }
      v[k] = t.value;
      if (k === 'label' && !v.name) v.name = `value${Number(t.dataset.i) + 1}`;
      if (k === 'query') render();
    },
    fagree: (t) => {
      const s = S.flset.settings;
      const a = s.agreement = s.agreement || {};
      if (t.dataset.kind === 'decision') { if (!t.value) { s.agreement = {}; } else { a.decision = t.value; a.inputs = {}; a.expect = {}; } render(); return; }
      if (t.dataset.kind === 'query') { a.query = t.value; render(); return; }
      a[t.dataset.kind] = a[t.dataset.kind] || {};
      if (t.value) a[t.dataset.kind][t.dataset.k] = t.value; else delete a[t.dataset.kind][t.dataset.k];
    },
    dindt: (t) => { S.ind.target = t.value; S.ind.inputs = {}; refreshDraft(); },
    dindin: (t) => { S.ind.inputs[t.dataset.v] = t.checked; refreshDraft(); },
    mpick: (t) => { S.map.picked = t.checked ? [...new Set([...S.map.picked, t.dataset.v])] : S.map.picked.filter((x) => x !== t.dataset.v); S.map.sug = null; S.map.auto = ''; render(); },
    csel: (t) => { S.cat.sel[t.dataset.path] = t.checked; render(); },
    call: (t) => {
      const c = S.cat;
      c.sel = {};
      if (t.checked) sortedRows(c).forEach((x) => { c.sel[x.path] = true; });
      render();
    },
    cinc: (t) => catalogCall('catalog/include', { paths: [t.dataset.path], on: t.checked }),
    cemb: (t) => catalogCall('catalog/embed', { paths: [t.dataset.path], on: t.checked }),
    cext: (t) => { S.cat.ext = t.value; render(); },
    mfault: (t) => { S.mon.fault = Number(t.value); },
  };

  async function finishEdit() {
    const c = S.cat;
    const e = c.edit;
    if (!e) return;
    c.edit = null;
    const value = e.value.trim();
    if (!value || (e.path && value === baseName(e.path))) { render(); return; }
    if (e.path) await catalogCall('catalog/rename', { path: e.path, name: value });
    else await catalogCall('catalog/folder', { path: (c.folder ? c.folder + '/' : '') + value });
  }

  function wire() {
    const main = $('#main');
    const layer = $('#layer');
    const OPENS = ['repopick', 'palette', 'cmenu'];  // these decide for themselves whether a float stays
    document.addEventListener('click', (ev) => {
      const scene = ev.target.closest('#mscene a.badge, #mscene a.tag');
      if (scene && sceneIssue(scene)) { ev.preventDefault(); return; }
      const t = ev.target.closest('[data-act]');
      if (!ev.target.closest('#layer') && !(t && OPENS.includes(t.dataset.act))) closeFloats();
      if (!t && ev.target.closest('#side a[href^="#"]')) ACT.navclose();  // a screen picked from the drawer closes it, also the screen already open
      if (t && ACT[t.dataset.act]) { ev.preventDefault(); ACT[t.dataset.act](t, ev); }
    });
    document.addEventListener('keydown', (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') { ev.preventDefault(); ACT.palette(); }
      if (ev.key === 'Escape') { if (S.pick || S.menu || S.pal) closeFloats(); else if (S.iss.open || S.iss.done) ACT.issclose(); else if (S.md.draft) ACT.draftclose(); else if (S.rp) ACT.rpclose(); else if (S.tab === 'onto' && S.ov.focus) focusOff('onto'); else if (S.tab === 'model' && S.md.focus) focusOff('model'); else if ($('#app').classList.contains('navopen')) ACT.navclose(); else if (S.cat.file) ACT.cdclose(); }
    });
    layer.addEventListener('input', (ev) => {
      if (ev.target.id === 'repolabel') S.pick.label = ev.target.value;
      if (ev.target.id === 'palq') { S.pal.q = ev.target.value; S.pal.i = 0; paintLayer(); }
      if (ev.target.id === 'rpq' && S.rp) { S.rp.q = ev.target.value; clearTimeout(findTimer); findTimer = setTimeout(() => rpLoad(), 250); }
    });
    layer.addEventListener('change', (ev) => { if (ev.target.id === 'rptype' && S.rp) { S.rp.type = ev.target.value; rpLoad(); } });
    layer.addEventListener('keydown', (ev) => {
      if (ev.target.id === 'repolabel' && ev.key === 'Enter') { ev.preventDefault(); ACT.repomake(); }
      if (ev.target.id !== 'palq') return;
      const items = palItems();
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
        ev.preventDefault();
        S.pal.i = (S.pal.i + (ev.key === 'ArrowDown' ? 1 : -1) + items.length) % Math.max(items.length, 1);
        paintLayer();
        const on = $('#layer .pallist a.on');
        if (on) on.scrollIntoView({ block: 'nearest' });  // the marked item stays in sight
      }
      if (ev.key === 'Enter' && items[S.pal.i]) { ev.preventDefault(); palOpen(items[S.pal.i]); }
    });
    $('#side').addEventListener('change', (ev) => { if (ev.target.dataset.side === 'lib') { ACT.navclose(); libraryUse(ev.target.value); } });  // the ontology the admin screens are about
    main.addEventListener('input', (ev) => { const t = ev.target; if (t.dataset && INPUT[t.dataset.in]) INPUT[t.dataset.in](t); });
    main.addEventListener('dragstart', (ev) => {
      const c = canEdit() && ev.target.closest && ev.target.closest('[data-col]');
      if (c) { ev.dataTransfer.setData('text/x-column', c.dataset.col); ev.dataTransfer.effectAllowed = 'copy'; }
    });
    main.addEventListener('change', (ev) => { const t = ev.target; if (t.dataset && CHANGE[t.dataset.in]) CHANGE[t.dataset.in](t); else if (t.tagName === 'SELECT' && t.dataset && t.dataset.in === 'lxf') INPUT.lxf(t); });
    main.addEventListener('keydown', (ev) => {
      if (ev.target.dataset && ev.target.dataset.in === 'exq' && ev.key === 'Enter') { ev.preventDefault(); ACT.exsearch(); }
      if (ev.target.dataset && ev.target.dataset.in === 'exedit' && (ev.key === 'Enter' || ev.key === 'Escape')) { ev.preventDefault(); ACT[ev.key === 'Enter' ? 'exsave' : 'excancel'](); }
      if (S.mg.cell && ev.target.dataset && ['cellv', 'cellop'].includes(ev.target.dataset.in) && (ev.key === 'Enter' || ev.key === 'Escape')) { ev.preventDefault(); ev.stopPropagation(); ACT[ev.key === 'Enter' ? 'cellsave' : 'cellx'](); }  // as ✓ and × do
      if (ev.key === 'Enter' && ev.target.dataset && ['param', 'principal', 'question'].includes(ev.target.dataset.in)) { ev.preventDefault(); runQuery(); }
      if (ev.key === 'Enter' && ev.target.dataset && ['dlab', 'dvalues'].includes(ev.target.dataset.in)) { ev.preventDefault(); ev.target.blur(); }
      if (ev.key === 'Tab' && ev.target.dataset && ev.target.dataset.in === 'mtext') {
        ev.preventDefault();
        const t = ev.target, a = t.selectionStart;
        t.setRangeText('  ', a, t.selectionEnd, 'end');
        S.ed.text = t.value;
      }
      if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && ev.target.dataset && ev.target.dataset.in === 'text') { ev.preventDefault(); runQuery(); }
      if (ev.key === 'Enter' && (ev.target.id === 'lpw' || ev.target.id === 'luser')) { ev.preventDefault(); ACT.login(); }
      if (ev.target.id === 'cedit' && ev.key === 'Enter') { ev.preventDefault(); finishEdit(); }
      if (ev.target.id === 'cedit' && ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); S.cat.edit = null; render(); }
    });
    main.addEventListener('focusout', (ev) => { if (ev.target.id === 'cedit' && S.cat.edit) finishEdit(); });
    main.addEventListener('toggle', (ev) => { if (ev.target.dataset && ev.target.dataset.more && S.mg.form) S.mg.form.more = ev.target.open; }, true);  // 고급 stays as left
    main.addEventListener('toggle', (ev) => { if (ev.target.dataset && ev.target.dataset.cn) S.cn[ev.target.dataset.cn] = ev.target.open; }, true);  // a connection way's settings stay open across a repaint
    main.addEventListener('change', (ev) => {
      if (ev.target.id === 'fileinput') uploadAll([...ev.target.files].map((f) => [f, f.name]));
      if (ev.target.id === 'libfileinput') libraryFilesAdd([...ev.target.files]);
      if (ev.target.dataset && ev.target.dataset.in === 'libmod') {
        const on = S.lib.mods || new Set(S.st.library.filter((r) => r.on).map((r) => r.name));
        if (ev.target.checked) on.add(ev.target.dataset.mod); else on.delete(ev.target.dataset.mod);
        S.lib.mods = on;
      }
      if (ev.target.id === 'dirinput') uploadAll([...ev.target.files].map((f) => [f, f.webkitRelativePath || f.name]));
    });
    main.addEventListener('dragstart', (ev) => { const r = canEdit() && ev.target.closest && ev.target.closest('[data-drag-rule]'); if (r) { S.mg.drag = r.dataset.dragRule; ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', S.mg.drag); r.classList.add('dragging'); } });
    main.addEventListener('dragend', () => { S.mg.drag = ''; document.querySelectorAll('.dragging, .dropat').forEach((x) => x.classList.remove('dragging', 'dropat')); });
    main.addEventListener('dragover', (ev) => {
      const r = S.mg.drag && ev.target.closest('[data-drag-rule]');
      if (r) { ev.preventDefault(); document.querySelectorAll('.dropat').forEach((x) => x.classList.remove('dropat')); r.classList.add('dropat'); }
    });
    main.addEventListener('drop', (ev) => {
      const r = S.mg.drag && ev.target.closest('[data-drag-rule]');
      if (!r) return;
      ev.preventDefault();
      const all = [...r.parentElement.querySelectorAll('[data-drag-rule]')].map((x) => x.dataset.dragRule);
      const from = all.indexOf(S.mg.drag), at = all.indexOf(r.dataset.dragRule);
      moveRule(S.mg.drag, at);  // the rule takes the place of the row it is dropped on
      if (from < 0) S.mg.drag = '';
    });
    main.addEventListener('dragover', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) { ev.preventDefault(); z.classList.add('over'); } });
    main.addEventListener('dragleave', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) z.classList.remove('over'); });
    main.addEventListener('drop', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) { ev.preventDefault(); z.classList.remove('over'); dropped(ev.dataTransfer); } });
    document.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && ev.target.id === 'srtext') searchNow();
      if (ev.key === 'Enter' && ev.target.id === 'srfkey') ACT.srrefix();
      if (ev.key === 'Enter' && ev.target.id === 'homeq') ACT.homego();
      if (ev.key === 'Enter' && ev.target.id === 'rlq') ACT.rlgo();
      const finding = { gxq: 'start', gxfromq: 'from', gxtoq: 'to' }[ev.target.id];
      if (ev.key === 'Enter' && finding) { ev.preventDefault(); clearTimeout(findTimer); gxFind(finding, true); }
      if (ev.key === 'Enter' && ev.target.id === 'chgtext') { const b = $('[data-act=chgcomment]'); if (b) ACT.chgcomment(b); }
    });
    window.addEventListener('hashchange', () => {
      $('#app').classList.remove('navopen');  // a screen picked from the drawer closes it
      readHash();
      $('#main').scrollTop = 0;
      S.cat.file = null; S.pa = null;
      if (S.mg.keep) S.mg.keep = false;
      else if (S.mg.form && S.mg.form.kind !== 'question') { S.mg.form = null; S.mg.sel = ''; }
      render();
    });
  }

  /*PARTS*/
  readHash();
  setInterval(() => { const c = $('#mclock'); if (c) c.textContent = new Date().toTimeString().slice(0, 8); }, 1000);
  wire();
  load().then(() => {  // what the page did just before it started again, such as a reset
    let said = '';
    try { said = sessionStorage.getItem('ontlas-said') || ''; sessionStorage.removeItem('ontlas-said'); } catch (_) { /* nothing kept */ }
    if (said) toast(said);
  }).catch(fail);
})();
