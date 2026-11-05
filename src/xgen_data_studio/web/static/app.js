'use strict';
(() => {
  const ICON = {
    guide: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M10 9.2v5.6l4.8-2.8z"/>',
    flow: '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="5" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M7.5 12h4M11.5 12V5h5M11.5 12v7h5"/>',
    data: '<path d="M12 15V4M7.5 8.5L12 4l4.5 4.5"/><path d="M4 14v4a2 2 0 002 2h12a2 2 0 002-2v-4"/>',
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
  };
  const NAV = [['guide', '사용 안내'], ['flow', '흐름'], ['sources', '데이터 소스'], ['data', '데이터 연결'], ['objects', '객체 관리'], ['props', '속성 관리'],
    ['links', '관계 관리'], ['library', '온톨로지 라이브러리'], ['onto', '온톨로지'], ['query', '질의'], ['decide', '판정 · 처리'], ['check', '검증'], ['bind', 'DB 대조']];
  const NAV_GROUP = [['시작', ['guide', 'flow']], ['데이터 관리', ['sources', 'data', 'objects', 'props', 'links']], ['온톨로지', ['library', 'onto']],
    ['활용 · 검증', ['query', 'decide', 'check', 'bind']]];
  const ELEMENT = { object: '객체', property: '속성', link: '관계', decision: '결정', action: '액션', query: '질의',
    question: '검증 질문', role: '역할', interface: '인터페이스', rule: '규칙', states: '상태 전이' };
  const FINDING = { table: '테이블 없음', column: '컬럼 없음', type: '타입 불일치', key: '키 중복', required: '필수 값 누락',
    enum: '정의에 없는 값', orphan: '끊긴 관계' };
  const STATUS = { pending: ['warn', '승인 대기'], rejected: ['bad', '반려'], executed: ['ok', '원천 반영'],
    failed: ['bad', '외부 호출 실패 · 원천 복원'], rolled_back: ['b', '되돌림'] };
  const CHANGE_STATUS = { pending: 'warn', approved: 'ok', rejected: 'bad' };
  const TEXT_LANG = [['sparql', 'SPARQL 1.1'], ['cypher', 'Cypher'], ['ir', '온톨로지 질의 IR (JSON)']];
  const STEP = {
    read: ['테이블 읽기', '파일별 테이블 생성과 컬럼 타입 판별'],
    objects: ['객체와 키', '테이블별 객체와 키 컬럼 지정'],
    properties: ['속성과 타입', '컬럼별 속성 타입과 허용값 지정'],
    links: ['관계', '키 컬럼 이름과 값 일치 기준 관계 추론'],
    queries: ['등록 질의', '객체 목록, 관계별 집계, 허용값별 집계 질의 생성'],
    rules: ['규칙 · 역할 · 검증', '상태 전이, 상태 변경 액션, 역할, 검증 질문, 지난 처리 결과로 만든 판정 표'],
    bindings: ['바인딩', '객체, 속성, 관계의 원천 테이블과 컬럼 연결'],
  };
  const CARD = { many_to_one: 'N:1', one_to_many: '1:N', one_to_one: '1:1', many_to_many: 'N:M' };
  const TYPE_WORD = { integer: '정수', decimal: '소수', date: '날짜', datetime: '일시', boolean: '참 · 거짓', string: '문자열', enum: '문자열' };
  // the manual: one section per screen, in the order a first visit goes through them
  const GUIDE = [
    ['flow', '원천 데이터부터 검증까지 단계별 처리 현황과 통과 조건을 확인합니다.', [
      '단계별 카드에서 [열기]를 선택하면 해당 화면으로 이동합니다.',
      '흐름 설정에서 단계를 켜고 끄고, DB 대조 오류 수, 백엔드 결과 일치율, 판정 일치율, 검증 질문 정답률 기준을 지정합니다.',
      '상단 정보에서 현재 데이터 출처를 확인합니다.',
      '모듈 적용 상태를 바꾸거나 데이터를 업로드하면 단계별 수치가 갱신됩니다.']],
    ['sources', '연결된 원천 테이블의 행 수, 컬럼, 키, 참조 컬럼과 테이블별 연결 객체를 확인합니다.', [
      '테이블을 선택하면 컬럼별 타입, 키, 참조 대상과 연결 속성이 표시됩니다.',
      '연결 객체가 없는 테이블은 [객체로 추가]를 선택해 객체 관리에서 바로 객체로 만듭니다.',
      '파일 업로드나 DB 연결은 [데이터 연결]에서 합니다.']],
    ['data', 'CSV, Excel 파일을 업로드해 온톨로지 초안을 생성하고 스튜디오에 적용합니다.', [
      '파일을 끌어 놓거나 [샘플 데이터 불러오기]를 선택합니다. 업로드한 파일은 세션 종료 시 삭제됩니다.',
      '생성 설정에서 허용값 기준, 관계 추론, 이름 규칙, 생성할 질의를 지정하고 초안에 넣을 테이블을 선택합니다.',
      '[초안 생성]을 선택하면 테이블 읽기, 객체와 키, 속성과 타입, 관계, 등록 질의, 바인딩 순서로 초안이 생성됩니다.',
      'SQL 스크립트, ERD 파일, 정의서, 용어집, 메시지 목록, Word, PowerPoint, 한글, PDF 문서를 함께 업로드할 수 있습니다. 형식이 달라도 하나의 JSON으로 모아 같은 방식으로 모듈을 만듭니다.',
      '데이터 파일 없이 정의서만 업로드하면 행 없이 키, 참조, 코드값으로 초안을 만듭니다. 복합 키는 키 속성 하나로 묶습니다.',
      '단계마다 키 컬럼, 속성 타입과 허용값, 이름, 카디널리티, 생성 질의를 수정하고 관계를 추가합니다. 수정할 때마다 정의 검사가 다시 실행됩니다.',
      '규칙 · 역할 · 검증 단계에서 상태 전이, 역할, 검증 질문을 확인하고, 지난 처리 결과 컬럼을 골라 판정 표를 만듭니다.',
      '[표준에 연결]에서 표준 모듈을 선택하면 테이블과 컬럼을 표준 객체와 속성에 대응시킨 제안이 표시됩니다. 확인하고 고친 뒤 [표준에 연결해 적용]을 선택합니다.',
      '[스튜디오에 적용]을 선택하면 모든 화면이 업로드 데이터 기준으로 바뀝니다. [초기화]를 선택하면 예시 스튜디오로 돌아갑니다.']],
    ['objects', '객체의 라벨, 원천 테이블, 키, 상위 객체를 관리합니다.', [
      '[새 객체]에서 원천 테이블을 고르면 키와 속성을 테이블 컬럼에서 채웁니다.',
      '표준 모듈의 객체를 바꾸면 표준 모듈은 그대로 두고 \'관리 변경\' 모듈에 확장으로 기록합니다. 키는 정의한 모듈에서만 바꿀 수 있습니다.',
      '[객체 제외]를 선택하면 그 객체를 쓰는 관계, 질의, 결정, 검증 질문이 함께 빠지고, 빠진 항목은 대기 중인 변경에 표시됩니다.',
      '관계가 없는 객체는 화면 위에 표시됩니다. [관계 관리]에서 관계를 추가하세요.',
      '대기 중인 변경에서 [변경 요청]을 선택하면 사본 스튜디오에서 흐름 통과 조건을 검토하고, 승인 후 모든 화면에 반영됩니다. [변경 취소]로 되돌립니다.']],
    ['props', '객체별 속성의 라벨, 자료형, 원천 컬럼, 허용값, 단위, 필수, 가림을 관리합니다.', [
      '객체를 고르거나 검색어를 입력해 속성을 좁힙니다. 상위 객체에서 물려받은 속성은 상속으로 표시됩니다.',
      '표준 모듈에서 정한 자료형은 바꿀 수 없습니다. 다른 자료형이 필요하면 새 속성을 추가합니다.',
      '키 속성과 물려받은 속성은 제외할 수 없습니다. 물려받은 속성은 상위 객체에서 제외합니다.']],
    ['links', '객체 사이의 관계와 연결 기준 컬럼, 카디널리티, 역관계를 관리합니다.', [
      '원천 테이블의 참조 컬럼(외래 키)으로 찾은 관계 중 아직 없는 관계가 위에 표시됩니다. [관계 추가]로 바로 추가합니다.',
      '[새 관계]에서 출발 객체와 속성, 도착 객체와 속성을 고르면 두 속성 값이 같은 행끼리 연결합니다.',
      '표준 모듈의 관계는 라벨, 카디널리티, 역관계, 필수 여부만 바꿀 수 있습니다.',
      '관계 그래프는 [온톨로지]에서 확인합니다.']],
    ['library', '공통 개념, 도메인, 업종 확장, 고객사 차이, 바인딩, 검증 기준, 구축 규칙 모듈의 적용 여부를 관리합니다. 도메인 경험이 쌓일수록 모듈이 늘어납니다.', [
      '적용 스위치를 끄면 함께 해제되는 모듈과 제거되는 항목을 먼저 표시합니다.',
      '검증 기준 모듈을 적용하면 검증 질문이 추가되고 흐름 통과 조건이 모듈의 기준으로 올라갑니다. 해제하면 스튜디오 설정으로 돌아갑니다.',
      '구축 규칙 모듈을 적용하면 데이터 연결의 생성 설정 기본값이 모듈의 규칙으로 바뀝니다.',
      '고객사 차이 · ACME 모듈을 해제하면 판정 · 처리에서 VIP 반품 규칙 대신 표준 규칙이 적용됩니다.',
      '해제된 모듈을 다시 적용하면 필요한 모듈도 함께 적용됩니다.',
      '[편집]을 선택하면 모듈 정의 파일에서 객체, 관계, 계산 속성, 결정표, 검증 질문, 역할을 수정합니다.',
      '[변경 요청]을 선택하면 사본 스튜디오에서 DB 대조, 백엔드 결과 일치, 검증 질문, 판정 일치율을 검토합니다. 흐름 통과 조건을 충족한 변경만 승인할 수 있습니다.',
      '[새 모듈]로 모듈을 만들고, [내려받기]로 정의 파일을 저장합니다.']],
    ['onto', '데이터 계층을 바탕으로 객체 사이의 관계를 그래프로 확인합니다.', [
      '노드를 선택하면 속성, 원천 컬럼, 계산 속성의 식, 가림 여부, 상태 전이, 시계열, 표준 개념 매핑이 표시됩니다.',
      '식별 통합 객체를 선택하면 묶인 기록과 근거를 확인하고, [다시 묶어 교차표 저장]으로 다시 묶습니다.',
      '관계를 선택하면 연결된 객체로 이동합니다.',
      '[OWL 내보내기]로 정의를 Turtle 형식으로 내려받습니다.']],
    ['query', '온톨로지 질의를 백엔드별 쿼리로 변환해 실행하고 결과를 비교합니다.', [
      '등록 질의를 선택하면 바로 실행됩니다.',
      '언어 탭에서 PostgreSQL, MySQL, Oracle, Cypher, GQL, SPARQL, SQL/PGQ, Gremlin 쿼리를 확인합니다. 역할을 지정하면 가린 속성은 가린 값으로 표시됩니다.',
      '[쿼리 입력]에서 SPARQL, Cypher 쿼리를 입력해 실행할 수 있습니다.',
      '실행 역할을 지정하면 해당 역할의 조회 범위만 표시됩니다.']],
    ['decide', '결정표 판정 결과와 근거를 확인하고 처리 요청을 승인합니다.', [
      '검증 질문을 선택하면 해당 대상을 판정합니다.',
      '처리를 요청하면 권한, 파라미터 값 범위, 상태 전이, 판정 조건을 검사합니다.',
      '[승인]을 선택하면 원천 DB에 반영되고 판정을 다시 계산합니다. 실행한 요청은 [되돌리기]로 이전 값으로 복원합니다.',
      '판정 일치율에서 지난 처리 기록과 결정표 판정이 다른 건을 확인합니다.']],
    ['check', '검증 질문 정답률, 근거 제시율, 백엔드 간 결과 일치 여부를 확인합니다.', [
      '[다시 실행]으로 현재 상태를 다시 검증합니다.',
      '근거 제시율은 답에 적용 규칙 또는 질의, 출처(규정 조항, 원천 컬럼), 판본(모듈 버전)이 모두 있는 질문의 비율입니다. 빠진 항목은 근거 열에 표시됩니다.',
      '검증 질문 관리에서 정답이 정해진 질문을 추가하거나 제외하고, [목록 불러오기]로 YAML · JSON 목록을 한 번에 넣습니다. 변경 요청이 승인되면 정답률 계산에 들어갑니다.',
      '승인 처리로 데이터가 바뀐 경우 [초기화]로 되돌립니다.']],
    ['bind', '온톨로지 정의와 원천 DB의 테이블, 컬럼, 타입, 키, 값을 대조합니다.', [
      '모듈 적용 상태를 바꾼 뒤 [다시 대조]를 선택합니다.',
      '식품 업종 모듈을 적용하면 원천 DB에 없는 컬럼이 오류로 표시됩니다.']],
  ];
  const GUIDE_USE = [
    ['업무 정의 공유', '객체, 속성, 관계, 상태, 규칙, 역할을 원천 테이블 위에 한 번 정의하고 버전이 있는 모듈 파일로 관리합니다.'],
    ['저장소 간 같은 질의', '하나의 질의를 SQL, Cypher, GQL, SPARQL, SQL/PGQ, Gremlin으로 변환해 실행하고 저장소별 결과를 비교합니다.'],
    ['규칙 판정과 근거', '결정표로 판정하고 적용 규칙, 출처 조항, 원천 컬럼, 모듈 버전을 함께 표시합니다.'],
    ['처리 통제', '역할별 조회 범위와 가림을 적용합니다. 에이전트는 처리를 요청만 하고, 승인한 처리만 원천 DB에 반영합니다.'],
    ['변경 검토', '모듈 변경을 사본 스튜디오에서 검토하고, 흐름 통과 조건을 충족한 변경만 승인합니다.'],
    ['시스템 · 고객사별 적용', '표준 모듈은 그대로 두고 시스템 연결과 고객사 차이만 모듈로 추가합니다.']];
  const GUIDE_ADAPT = [
    ['표준 모듈과 원천 테이블', '데이터 연결 > 표준에 연결', '바인딩 모듈'],
    ['SQL 스크립트, ERD 파일, 테이블 정의서', '데이터 연결 > 초안 생성', '도메인 · 바인딩 모듈'],
    ['코드 정의서', '데이터 연결 > 초안 생성', '코드값 이름, 결정표'],
    ['용어집, 메시지 목록', '데이터 연결 > 초안 생성', '용어 사전 모듈'],
    ['CSV, Excel 파일, DB', '데이터 연결 > 초안 생성', '도메인 · 바인딩 모듈'],
    ['지난 처리 기록', '데이터 연결 > 규칙 · 역할 · 검증', '결정표'],
    ['정책서, 화면설계서', '온톨로지 라이브러리 > 정책서로 규칙 초안', '결정표 모듈', 'ask'],
    ['객체, 속성, 관계 수정', '객체 관리, 속성 관리, 관계 관리', '관리 변경 모듈'],
    ['모듈 정의 파일', '온톨로지 라이브러리 > 새 모듈', '종류별 모듈']];
  const ASK_STEP = '[자연어 질문]에서 질문을 입력하면 언어 모델이 온톨로지 질의를 만들어 실행합니다. 결과가 0행이면 비교한 속성의 값을 확인해 한 번 더 만듭니다.';
  const POLICY_STEP = '[정책서로 규칙 초안]에서 정책서 조항을 입력하면 언어 모델이 결정표 초안을 만들고 엔진이 입력 속성, 규칙 형식, 출처 조항을 검사합니다. 초안은 편집기에서 확인한 뒤 변경 요청으로 검토 · 승인합니다.';
  const FLOW = [
    ['source', '원천 데이터', '테이블과 행 수', 'data'],
    ['define', '온톨로지 정의', '적용 모듈과 객체, 관계, 속성', 'library'],
    ['bind', 'DB 대조', '정의와 원천 DB의 스키마, 데이터 대조', 'bind'],
    ['project', '그래프 저장소 반영', '원천 데이터의 노드, 간선 반영', 'onto'],
    ['query', '질의', '백엔드별 쿼리 변환과 결과 일치', 'query'],
    ['decide', '판정 · 처리', '결정표 판정과 승인 처리', 'decide'],
    ['check', '검증', '검증 질문 정답률', 'check'],
  ];

  const S = {
    st: null, tab: 'library', kind: 'all', impact: null, pos: {}, sel: null, obj: null,
    q: { mode: 'list', name: null, params: {}, role: '', principal: {}, target: 'sql:postgres', res: null,
      lang: 'sparql', text: '', dirty: false, question: '', busy: false },
    d: { name: null, key: null, keys: {}, res: null, proposal: null, params: {}, role: '', audit: [], busy: false },
    qa: null, bind: null, fl: null, files: null, dpos: {}, guide: null,
    dr: { step: 0, view: 'read', sel: null, busy: false, timer: 0, label: '', dsn: '', rules: null, tables: {}, rev: null, graph: null,
      ed: { drop: {}, labels: {}, keys: {}, types: {}, values: {}, card: {}, add: [] }, add: { source: '', property: '', target: '', label: '' } },
    ed: null, me: null, change: null, changes: null, flset: null, agree: null, ident: null,
    map: { standards: null, picked: [], sug: null, edits: { objects: {}, columns: {} }, busy: false },
    pol: { open: false, text: '', target: '', busy: false, res: null },
    ind: { target: '', inputs: {} },
    mg: { st: null, busy: false, sel: '', form: null, q: '', obj: '', table: '', open: false, keep: false, qt: 0, review: null },
  };

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
  const plainText = (v) => (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v) ? v.slice(0, 10) : String(v ?? ''));
  const element = (id) => {
    const [kind, ...rest] = String(id).split(':');
    return `<span class="chip sm">${esc(ELEMENT[kind] || kind)} <span class="mono">${esc(rest.join(':'))}</span></span>`;
  };
  const modLabel = (name) => (S.st.library.find((r) => r.name === name) || {}).label || name;

  async function api(path, body) {
    const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-XDS-Request': '1' }, body: JSON.stringify(body) };
    const r = await fetch('/api/' + path, opt);
    let j = {};
    try { j = await r.json(); } catch (_) { /* empty body */ }
    if (r.status === 401 && S.me && S.me.team && path !== 'login') { S.me.user = null; renderLogin(); }
    if (!r.ok) throw new Error(j.error || `서버 오류로 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요. (${r.status})`);
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
  }

  function stale() {
    S.q.res = null; S.d.res = null; S.d.proposal = null; S.d.keys = {}; S.qa = null; S.bind = null; S.obj = null; S.fl = null;
    S.mg.st = null;
  }

  // ---- frame ---------------------------------------------------------------------------------------------------

  function renderLogin() {
    $('#top').innerHTML = '<div class="brand"><div class="logo">X</div>XGEN 데이터 스튜디오</div><div class="grow"></div>';
    $('#side').innerHTML = '';
    $('#main').innerHTML = `<div class="card login"><div class="ch">로그인</div><div class="cb">
      <div class="field"><label for="luser">아이디</label><input type="text" id="luser" autocomplete="username"></div>
      <div class="field"><label for="lpw">비밀번호</label><input type="password" id="lpw" autocomplete="current-password"></div>
      <button class="btn primary" style="width:100%" data-act="login">로그인</button>
      <div class="hint" style="margin-top:10px">팀 스튜디오는 로그인한 사용자만 사용할 수 있습니다. 계정은 관리자에게 요청해 주세요.</div></div></div>`;
  }

  const ROLE_WORD = { viewer: '조회', editor: '편집', approver: '승인', admin: '관리' };

  function renderTop() {
    const st = S.st;
    const u = S.me && S.me.team && S.me.user;
    const who = u ? `<span class="chip b">${esc(u.name)} · ${esc(u.roles.map((r) => ROLE_WORD[r] || r).join(', '))}</span><button class="btn sm ghost" data-act="logout">로그아웃</button>` : '';
    $('#top').innerHTML = `<div class="brand"><div class="logo">X</div>XGEN 데이터 스튜디오</div>
      <span class="chip b">${esc(st.title)}</span><span class="chip">모듈 ${st.modules_on}개</span>
      ${originChip(st.origin)}<div class="grow"></div>
      ${st.backends.map((b) => `<span class="chip be"><span class="dot"></span>${esc(b.name)} · ${esc(b.language.toUpperCase())}</span>`).join('')}
      ${S.tab === 'guide' ? '' : '<a class="btn sm" href="#guide">사용 안내</a>'}
      ${who}${u && !u.roles.includes('admin') ? '' : '<button class="btn sm ghost" data-act="reset">초기화</button>'}`;
  }

  function originChip(o) {
    if (o.kind === 'files') return `<span class="chip ok hide-sm">업로드 데이터 · ${esc(o.label || '')}</span>`;
    if (o.kind === 'database') return `<span class="chip ok hide-sm">연결 DB · ${esc(o.detail || '')}</span>`;
    if (o.kind === 'definitions') return `<span class="chip ok hide-sm">정의서 · ${esc(o.label || '')}</span>`;
    return o.notice ? `<span class="chip warn hide-sm">${esc(o.notice)}</span>` : '';
  }

  function renderSide() {
    const st = S.st;
    const n = { data: st.data.files, library: st.changes || st.library.length, objects: st.stats.objects, links: st.stats.links,
      query: st.stats.queries, decide: st.stats.decisions + st.stats.actions, check: st.stats.questions,
      sources: S.mg.st && S.mg.st.sources ? S.mg.st.sources.source.tables.length : 0 };
    const wait = S.mg.st && S.mg.st.workspace && S.mg.st.workspace.dirty;
    const link = (k) => `<a class="nav${S.tab === k ? ' on' : ''}" href="#${k}"><svg viewBox="0 0 24 24">${ICON[k]}</svg>${navLabel(k)}` +
      `${n[k] ? `<span class="n">${n[k]}</span>` : ''}</a>`;
    $('#side').innerHTML = NAV_GROUP.map(([h, keys]) => `<h6>${h}${h === '데이터 관리' && wait ? ' <span class="chip sm warn">변경 대기</span>' : ''}</h6>${keys.map(link).join('')}`).join('');
  }

  function render() {
    if (!S.st) return;
    renderTop();
    renderSide();
    const views = { guide: viewGuide, flow: viewFlow, data: viewData, library: viewLibrary, onto: viewOnto, query: viewQuery, decide: viewDecide, check: viewCheck, bind: viewBind,
      sources: viewSources, objects: viewObjects, props: viewProps, links: viewLinks };
    const main = $('#main');
    main.innerHTML = (views[S.tab] || viewFlow)();
    after();
  }

  function after() {
    if (S.tab === 'guide') mountGuide();
    if (S.tab === 'flow' && !S.fl) loadFlow();
    if (S.tab === 'flow' && !S.flset) loadFlowSettings();
    if (S.tab === 'library' && !S.changes) loadChanges();
    if (S.tab === 'decide' && !S.agree) loadAgreement();
    if (S.tab === 'data') { if (!S.files) loadFiles(); else mountDraftGraph(); }
    if (S.tab === 'onto') {
      mountGraph($('#graph'), S.st.graph, { pos: S.pos, sel: () => S.sel, pick: selectObject });
      if (!S.sel) {
        const d = S.st.decisions[0];
        S.sel = (d && S.st.graph.nodes.some((x) => x.id === d.target)) ? d.target : (S.st.graph.nodes[0] || {}).id;
      }
      if (S.sel && (!S.obj || S.obj.name !== S.sel)) selectObject(S.sel);
    }
    if (S.tab === 'query' && !S.q.res && !S.q.busy && S.q.mode === 'list') {
      if (!S.q.name && S.st.queries.length) pickQuery(S.st.queries[0].name);
      else if (S.q.name) runQuery();
    }
    if (S.tab === 'decide' && !S.d.res && !S.d.busy && S.st.decisions.length) startDecide();
    if (S.tab === 'check' && !S.qa) runChecks();
    if ((MG_TABS.includes(S.tab) || S.tab === 'check') && !S.mg.st && !S.mg.busy) loadManage();
    if (S.tab === 'bind' && !S.bind) runBindings();
  }

  // ---- library -------------------------------------------------------------------------------------------------

  const counts = (c) => [['objects', '객체'], ['links', '관계'], ['decisions', '결정'], ['queries', '질의'], ['questions', '검증 질문'], ['gates', '통과 조건'], ['draft_rules', '구축 규칙'], ['terms', '용어'], ['messages', '메시지'], ['extends', '확장'], ['removes', '제거']]
    .filter(([k]) => c[k]).map(([k, l]) => `${l} ${c[k]}`).join(' · ') || '-';

  function viewLibrary() {
    const st = S.st;
    const kinds = [...new Set(st.library.map((r) => r.kind))];
    const tabs = [`<button class="tab${S.kind === 'all' ? ' on' : ''}" data-act="kind" data-kind="all">전체 ${st.library.length}</button>`]
      .concat(kinds.map((k) => {
        const r = st.library.find((x) => x.kind === k);
        return `<button class="tab${S.kind === k ? ' on' : ''}" data-act="kind" data-kind="${esc(k)}">${esc(r.kind_label)} ` +
          `${st.library.filter((x) => x.kind === k).length}</button>`;
      }));
    const rows = st.library.filter((r) => S.kind === 'all' || r.kind === S.kind).map((r) => {
      const req = r.requires.length ? r.requires.map((x) => `<span class="chip sm mono">${esc(x)}</span>`).join(' ') : '<span class="muted">-</span>';
      return `<tr class="${S.impact && S.impact.module === r.name ? 'sel' : ''}">
        <td><b>${esc(r.label || r.name)}</b><div class="muted mono">${esc(r.name)}</div>
          ${r.description ? `<div class="muted" style="font-size:12px;margin-top:3px;line-height:1.45">${esc(r.description)}</div>` : ''}
          <button class="chip sm" data-act="medit" data-mod="${esc(r.name)}" style="margin-top:6px">편집</button></td>
        <td><span class="kind"><i style="background:${esc(r.color)}"></i>${esc(r.kind_label)}</span></td>
        <td class="mono" style="white-space:nowrap">${esc(r.version)}</td><td>${req}</td>
        <td class="muted" style="font-size:12.5px">${esc(counts(r.counts))}</td>
        <td style="text-align:center"><button class="switch${r.on ? ' on' : ''}" role="switch" aria-checked="${r.on}"
          aria-label="${esc(r.label || r.name)}" data-act="toggle" data-mod="${esc(r.name)}"></button></td></tr>`;
    }).join('');
    const layers = st.layers.map((l) => `<div class="layer"><div class="lbl"><i style="background:${esc(l.color)}"></i>${esc(l.kind_label)}</div>
      <div class="chips">${l.modules.map((m) => `<span class="chip">${esc(m.label)} <span class="muted mono">${esc(m.version)}</span></span>`).join('')}</div></div>`).join('');
    const log = st.log.length ? st.log.slice(0, 8).map((x) => `<div>${esc(x.text)}</div>`).join('')
      : '<div class="muted">변경 이력이 없습니다.</div>';
    return `
<div class="head"><div><h1>온톨로지 라이브러리</h1><div class="sub">도메인별 온톨로지 모듈과 버전을 관리하고 스튜디오 적용 여부를 설정합니다</div></div>
  <div class="right">${st.ask ? '<button class="btn" data-act="popen">정책서로 규칙 초안</button>' : ''}<button class="btn" data-act="mnew">새 모듈</button><a class="btn ghost" href="/api/export/owl" download>OWL 내보내기</a></div></div>
<div class="tabs">${tabs.join('')}</div>${policyCard()}${editorCard()}
<div class="grid" style="grid-template-columns:minmax(0,1.62fr) minmax(320px,1fr)">
  <div class="card"><div class="ch">모듈<div class="right muted" style="font-weight:600;font-size:12px">적용 ${st.modules_on}개</div></div>
    <div class="cb scroll" style="padding:0"><table><tr><th>온톨로지</th><th>종류</th><th>버전</th><th>의존 모듈</th><th>구성</th><th style="text-align:center">적용</th></tr>${rows}</table></div></div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
    ${changesCard()}
    <div class="card"><div class="ch">해제 영향</div><div class="cb">${impactCard()}</div></div>
    <div class="card"><div class="ch">적용 구성</div><div class="cb">${layers}</div></div>
    <div class="card"><div class="ch">변경 이력</div><div class="cb loglist">${log}</div></div>
  </div>
</div>`;
  }

  // policy text -> a decision table drafted by the language model and checked by the engine, opened in the editor
  function policyCard() {
    const p = S.pol;
    if (!p.open) return '';
    const nodes = S.st.graph.nodes.filter((n) => n.table);
    const docs = ((S.files || {}).definitions || []).flatMap((x) => x.document_list || []);
    const targets = `<option value="">자동</option>${nodes.map((n) => `<option value="${esc(n.id)}"${n.id === p.target ? ' selected' : ''}>${esc(n.label)} · ${esc(n.id)}</option>`).join('')}`;
    let body = '';
    const r = p.res;
    if (r && !r.ok) body = `<div class="banner no" style="margin-top:12px"><div class="why">${esc(r.error)}</div></div>`;
    else if (r) {
      const when = (w) => Object.keys(w).length ? Object.entries(w).map(([k, v]) => `<span class="mono">${esc(k)} ${esc(v)}</span>`).join('<br>') : '<span class="muted">그 밖의 경우</span>';
      const rows = r.rules.map((x) => `<tr><td class="mono">${esc(x.id)}</td><td style="font-size:12px">${when(x.when)}</td><td style="font-size:12px">${showObj(x.then)}</td><td>${x.cite ? `<span class="chip sm">${esc(x.cite)}</span>` : '<span class="chip sm bad">출처 없음</span>'}</td></tr>`).join('');
      const from = (x) => {  // where an input is read: along the path to a property, its days since, or a count
        if (x.param) return `파라미터 ${x.param}`;
        const end = x.count ? '개수' : (x.days_since ? `${x.days_since} 경과일` : x.property);
        return [...(x.path || x.count || []), end].filter(Boolean).join(' → ');
      };
      const inputs = r.inputs.map((x) => `<span class="chip sm"><span class="mono">${esc(x.name)}</span> ← ${esc(from(x))}</span>`).join('');
      const issues = r.issues.length ? `<div class="banner no" style="margin-top:10px"><div><div class="big" style="font-size:14px">초안 검사 오류 ${r.issues.length}건</div><div class="loglist">${r.issues.map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div><div class="why">편집기에서 고친 뒤 [검사]를 선택하세요.</div></div></div>` : '';
      body = `<div class="chips" style="margin-top:12px"><span class="chip ${r.issues.length ? 'warn' : 'ok'}">${r.issues.length ? '검사 오류 있음' : '✓ 초안 검사 통과'}</span><span class="chip mono">${esc(r.decision)}</span><span class="chip">대상 ${esc(r.target)}</span><span class="chip">모델 시도 ${r.attempts}회</span></div>
        <div class="sec">입력</div><div class="chips">${inputs}</div>
        <table class="tight" style="margin-top:10px"><tr><th>규칙</th><th>조건</th><th>결과</th><th>출처 조항</th></tr>${rows}</table>${issues}
        <div class="hint" style="margin-top:8px">아래 편집기에 모듈 초안을 열었습니다. 규칙과 출처 조항을 확인하고 고친 뒤 [적용 변경 요청]을 선택하면 사본 스튜디오에서 검토하고 승인 대기로 등록됩니다.</div>`;
    }
    return `<div class="card" style="margin-bottom:16px"><div class="ch">정책서로 규칙 초안<div class="right"><button class="btn sm ghost" data-act="pclose">닫기</button></div></div><div class="cb">
      <div class="hint" style="margin-bottom:8px">정책서 조항을 입력하면 언어 모델이 결정표 초안을 만들고, 엔진이 입력 속성, 규칙 형식, 출처 조항을 검사합니다. 초안은 사람이 확인하고 승인해야 반영됩니다.</div>
      ${docs.length ? `<div class="rgrid two" style="margin-bottom:8px"><label class="field" style="margin:0"><span>업로드한 문서</span><select data-in="pdoc"><option value="">선택</option>${docs.map((d) => `<option value="${esc(d.name)}"${d.name === p.doc ? ' selected' : ''}>${esc(d.name)}</option>`).join('')}</select></label>
        ${(p.sections || []).length ? `<label class="field" style="margin:0"><span>절</span><select data-in="psec"><option value="">전체</option>${p.sections.map((x) => `<option value="${esc(x)}"${x === p.section ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select></label>` : ''}</div>` : ''}
      <textarea class="code" data-in="ptext" spellcheck="false" style="min-height:180px" placeholder="제1조 (목적) ...">${esc(p.text)}</textarea>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px">
        <label class="field" style="margin:0;min-width:220px"><span>대상 객체</span><select data-in="ptarget">${targets}</select></label>
        ${S.st.data.policy_sample ? '<button class="btn" data-act="psample">예시 정책서 불러오기</button>' : ''}
        <button class="btn primary" data-act="pdraft"${p.busy || !p.text.trim() ? ' disabled' : ''}>${p.busy ? '<span class="spin"></span>초안 생성 중 · 최대 5분' : '초안 생성'}</button></div>${body}</div></div>`;
  }

  async function loadDocument(name, section) {
    S.pol.doc = name; S.pol.section = section; S.pol.res = null;
    if (!name) { render(); return; }
    try {
      const r = await api('policy/document', { name, section });
      if (!r.ok) throw new Error(r.error);
      S.pol.text = r.text; S.pol.sections = r.sections;
      if (r.cut) toast('문서가 길어 앞부분만 불러왔습니다. 절을 선택하면 해당 절만 불러옵니다.');
    } catch (e) { fail(e); }
    render();
  }

  function moduleTemplate() {
    const st = S.st;
    const dom = st.library.find((r) => r.on && r.kind === 'domain');
    const node = dom && st.graph.nodes.find((n) => n.module === dom.name && n.table);
    const head = '# objects, links, decisions, actions, roles, queries, questions 를 정의합니다.\n# 다른 모듈의 항목은 extend 로 확장하고 remove 로 제외합니다.\n';
    if (dom && node) {
      return `${head}module: my-module\nversion: 0.1.0\nkind: customer\nlabel: 새 모듈\ndescription: 모듈 설명을 입력하세요.\nrequires: [${dom.name}]\nqueries:\n  custom${node.id}List:\n    label: ${node.label} 목록\n    query:\n      match: {x: ${node.id}}\n      return: [x.${node.key}]\n      order: [${node.key}]\n`;
    }
    return `${head}module: my-module\nversion: 0.1.0\nkind: domain\nlabel: 새 모듈\ndescription: 모듈 설명을 입력하세요.\nobjects:\n  Item:\n    label: 항목\n    key: item_id\n    properties:\n      item_id: {type: string, label: 항목 번호, required: true}\n`;
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
      <div class="right"><button class="btn sm ghost" data-act="mclose">닫기</button></div></div>
      <div class="cb"><textarea class="code" data-in="mtext" spellcheck="false">${esc(ed.text)}</textarea>
      <div class="hint" style="margin:8px 0 12px">kind: core, domain, industry, customer, binding, quality, method. 계산 속성은 expr, 가림은 mask: partial | full 로 지정합니다. 검증 기준(quality)은 questions 와 flow.gates, 구축 규칙(method)은 draft_rules 로 지정합니다. [변경 요청]을 선택하면 사본 스튜디오에서 검토한 뒤 승인 대기로 등록됩니다. 같은 버전이 이미 있으면 버전을 올려 요청합니다.</div>
      <div id="mresult">${moduleCheck()}</div>
      ${S.change ? changeReview(S.change) : ''}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><button class="btn" data-act="mcheck"${busy}>검사</button>
        <button class="btn primary" data-act="mpropose" data-apply="0"${busy}>${ed.busy ? '<span class="spin"></span>검토 중' : '변경 요청'}</button>
        ${ed.applied ? '' : `<button class="btn primary" data-act="mpropose" data-apply="1"${busy}>적용 변경 요청</button>`}
        ${ed.name && !ed.isNew ? `<a class="btn ghost" href="/api/export/module?name=${encodeURIComponent(ed.name)}" download>내려받기</a>` : ''}</div></div></div>`;
  }

  async function openModule(name) {
    const m = await api('module?name=' + encodeURIComponent(name));
    S.ed = { ...m, text: m.yaml, check: null, busy: false, isNew: false };
    S.change = null;
  }

  async function loadChanges() {
    S.changes = { busy: true };
    try { S.changes = await api('changes'); } catch (e) { S.changes = { error: e.message, changes: [] }; }
    if (S.tab === 'library') render();
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
    if (m.query && m.query.queries !== undefined) facts.push(`백엔드 결과 일치 ${m.query.agree} / ${m.query.queries}`);
    if (m.check && m.check.accuracy !== undefined) facts.push(`검증 질문 정답률 ${pct(m.check.accuracy)}${m.check.failed && m.check.failed.length ? ` (틀린 질문 ${esc(m.check.failed.join(', '))})` : ''}`);
    if (m.decide && m.decide.rate !== undefined) facts.push(m.decide.cases ? `판정 일치율 ${pct(m.decide.rate)} (${m.decide.agree} / ${m.decide.cases})` : '판정 일치율 측정 불가 · 판정표 없음');
    const issues = c.issues.length ? `<div class="banner no" style="margin:8px 0"><span class="ic x" style="width:24px;height:24px">!</span><div class="loglist">${c.issues.slice(0, 6).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div>` : '';
    const act = c.status === 'pending' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" data-act="capprove" data-id="${esc(c.id)}"${c.passed ? '' : ' disabled'}>승인</button><button class="btn" data-act="creject" data-id="${esc(c.id)}">반려</button></div>
      ${S.st.self_approve ? '' : '<div class="hint" style="margin-top:6px">요청한 사람과 다른 승인자가 승인합니다.</div>'}` : '';
    return `<div class="review"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b>변경 ${esc(c.id)} · ${esc(c.module_label)} ${esc(c.base_version || '')}${c.base_version ? ' → ' : ''}${esc(c.version)}</b>
        <span class="chip ${CHANGE_STATUS[c.status] || ''}">${esc(c.status_label)}</span><span class="chip ${c.passed ? 'ok' : 'bad'}">${c.passed ? '흐름 통과 조건 충족' : '흐름 통과 조건 미충족'}</span>
        <span class="muted" style="font-size:12px">요청 ${esc(c.requested_by)}${c.decided_by ? ` · 결정 ${esc(c.decided_by)}` : ''}</span></div>
      ${issues}${list(d.added, '추가', 'ok')}${list(d.changed, '변경', 'b')}${list(d.removed, '제거', 'bad')}
      ${facts.length ? `<div class="label" style="margin:10px 0 4px">사본 스튜디오 측정</div><div class="loglist">${facts.map((x) => `<div>${x}</div>`).join('')}</div>` : ''}
      <div class="label" style="margin:10px 0 4px">통과 조건</div>${gateRows(c.gates)}
      ${m.findings && m.findings.length ? `<div class="label" style="margin:10px 0 4px">DB 대조에서 나온 항목</div><table class="tight" style="font-size:12px"><tr><th>심각도</th><th>종류</th><th>항목</th><th>내용</th></tr>${m.findings.slice(0, 8).map((f) => `<tr><td><span class="chip sm ${f.severity === 'error' ? 'bad' : 'warn'}">${f.severity === 'error' ? '오류' : '주의'}</span></td><td>${esc(FINDING[f.kind] || f.kind)}</td><td>${element(f.element)}</td><td class="mono muted">${esc(f.detail)}</td></tr>`).join('')}</table>` : ''}
      ${m.mismatches && m.mismatches.length ? `<div class="label" style="margin:10px 0 4px">판정이 실제 처리와 다른 건</div>${mismatchRows(m.mismatches)}` : ''}${act}</div>`;
  }

  function changesCard() {
    const ch = S.changes;
    if (!ch || ch.busy || !ch.changes || !ch.changes.length) return '';
    return `<div class="card"><div class="ch">변경 요청<div class="right muted" style="font-weight:600;font-size:12px">${ch.writes_folder ? '승인하면 라이브러리 폴더에 저장' : '승인하면 현재 세션에 저장'}</div></div><div class="cb loglist">${ch.changes.slice(0, 8).map((c) => `<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <span class="chip sm ${CHANGE_STATUS[c.status] || ''}">${esc(c.status_label)}</span><b>${esc(c.module_label)} ${esc(c.version)}</b><span class="muted" style="font-size:12px">${esc(c.requested_by)}</span>
      <span style="flex:1"></span><button class="chip sm" data-act="cshow" data-id="${esc(c.id)}">검토 보기</button></div>`).join('')}</div></div>`;
  }

  function impactCard() {
    const imp = S.impact;
    if (!imp) return '<div class="hint">적용 스위치를 끄면 해제 시 함께 제거되는 항목을 표시합니다.</div>';
    const list = (xs) => `<div class="chips" style="margin-top:8px">${xs.slice(0, 16).map(element).join('')}${xs.length > 16 ? `<span class="chip sm">외 ${xs.length - 16}개</span>` : ''}</div>`;
    const cancel = '<button class="btn" data-act="cancel-impact">취소</button>';
    if (imp.ok) {
      return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip ok">해제 가능</span></div>
        <div class="muted" style="margin-top:6px;font-size:12.5px">항목 ${imp.removed.length}개가 제거됩니다.${imp.changed.length ? ` 다른 모듈이 확장한 항목 ${imp.changed.length}개는 원래 정의로 복원됩니다.` : ''}</div>
        ${list(imp.removed)}${imp.changed.length ? list(imp.changed) : ''}
        <div style="display:flex;gap:8px;margin-top:14px"><button class="btn primary" data-act="detach" data-mod="${esc(imp.module)}"
          data-cascade="${imp.cascade ? 1 : 0}">${imp.cascade ? '함께 해제' : '해제'}</button>${cancel}</div>`;
    }
    const deps = imp.dependents_labels || [];
    const cas = imp.cascadeImpact;
    return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip warn">의존 모듈 있음</span></div>
      <div class="muted" style="margin-top:6px;font-size:12.5px;line-height:1.55">${deps.length ? `이 모듈을 사용하는 모듈 ${deps.length}개: ${esc(deps.join(', '))}` : '해제하면 참조가 끊어지는 항목이 있습니다.'}</div>
      ${deps.length ? '' : `<div class="loglist" style="margin-top:6px">${imp.broken.map((b) => `<div class="mono">${esc(b)}</div>`).join('')}</div>`}
      ${cas && cas.ok ? `<div class="muted" style="margin-top:10px;font-size:12.5px">함께 해제하면 항목 ${cas.removed.length}개가 제거됩니다.</div>${list(cas.removed)}` : ''}
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
      if (r.warning) toast(r.warning, true); else toast(`${modLabel(name)} 모듈을 해제했습니다. 항목 ${r.impact.removed.length}개가 제거되었습니다.`);
    } catch (e) { fail(e); }
  }

  // ---- ontology ------------------------------------------------------------------------------------------------

  function viewOnto() {
    const s = S.st.stats;
    const stats = [[s.objects, '객체'], [s.links, '관계'], [s.properties, '속성'], [s.decisions, '결정'], [s.actions, '액션'], [s.queries, '등록 질의']]
      .map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join('');
    return `
<div class="head"><div><h1>온톨로지</h1><div class="sub">객체, 관계, 속성 정의와 원천 테이블 매핑을 확인합니다</div></div>
  <div class="right"><a class="btn ghost" href="/api/export/owl" download>OWL 내보내기</a></div></div>
<div class="stats">${stats}</div>
<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(360px,1fr)">
  <div class="card"><div class="ch">스키마 그래프<div class="right legend"><span><i class="fill"></i>객체</span><span><i class="ring"></i>상위 개념</span><span><i class="box"></i>모듈</span><span>- - 하위 유형</span></div></div>
    <div class="cb" style="padding:0"><div class="graph-wrap"><canvas id="graph"></canvas><div class="tip">드래그로 이동 · 휠로 확대</div></div></div></div>
  <div class="card"><div class="cb scroll" id="objdetail" style="max-height:640px">${S.obj ? objDetail(S.obj) : '<div class="empty">노드를 선택하면 정의가 표시됩니다.</div>'}</div></div>
</div>`;
  }

  async function selectObject(name) {
    S.sel = name;
    drawGraph();
    try {
      S.obj = await api('object?name=' + encodeURIComponent(name));
      const box = $('#objdetail');
      if (box) box.innerHTML = objDetail(S.obj);
    } catch (e) { fail(e); }
  }

  function objDetail(o) {
    const rows = o.properties.map((p) => `<tr><td><b>${esc(p.label)}</b><div class="muted mono">${esc(p.name)}</div>
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
    const aligned = o.aligned.length ? `<div class="sec">표준 개념 매핑</div><div class="chips">${o.aligned.map((a) => `<span class="chip sm mono">${esc(a.split('//').pop())}</span>`).join('')}</div>` : '';
    const mod = o.module ? `<span class="chip">정의 모듈 ${esc(o.module_label)}</span>` : '';
    const touched = o.touched.length ? `<span class="chip">확장 모듈 ${esc(o.touched.join(', '))}</span>` : '';
    return `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px"><b style="font-size:16px">${esc(o.label)}</b>
      <span class="muted mono">${esc(o.name)}</span><span style="flex:1"></span>
      ${o.abstract ? '<span class="chip n">상위 개념</span>' : `<span class="chip b">키 ${esc(o.key)}</span><span class="chip mono">${esc(o.table)}</span>`}</div>
      <div class="chips" style="margin-bottom:12px">${mod}${touched}</div>
      ${o.description ? `<div class="muted" style="font-size:12.5px;margin-bottom:10px">${esc(o.description)}</div>` : ''}
      <table class="tight"><tr><th>속성</th><th>타입</th><th>원천 컬럼</th></tr>${rows}</table>
      ${states}${series}${ident}${parent}${children}${aligned}
      ${links ? `<div class="sec">관계</div><div class="chips">${links}</div>` : ''}`;
  }

  // ---- schema graph: positions settle once and stay; modules drawn as dashed groups --------------------------------

  const G = { canvas: null, view: null, nodes: [], edges: [], clusters: [], drag: null, ro: null, sel: () => null, pick: null, shown: null, label: null };

  function hash(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; }

  function layout(data, pos) {
    const ids = data.clusters.map((c) => c.id);
    const centers = {};
    ids.forEach((c, i) => { const a = (2 * Math.PI * i) / Math.max(ids.length, 1) - Math.PI / 2; centers[c] = { x: Math.cos(a) * 240, y: Math.sin(a) * 200 }; });
    const nodes = data.nodes.map((n) => ({ ...n, x: (pos[n.id] || {}).x, y: (pos[n.id] || {}).y, vx: 0, vy: 0 }));
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const edges = data.edges.filter((e) => byId[e.source] && byId[e.target]).map((e) => ({ ...e, s: byId[e.source], t: byId[e.target] }));
    let fresh = 0;
    for (const n of nodes) {
      if (n.x !== undefined) continue;
      fresh += 1;
      const known = edges.filter((e) => (e.s === n && e.t.x !== undefined) || (e.t === n && e.s.x !== undefined)).map((e) => (e.s === n ? e.t : e.s));
      const base = known.length ? { x: known.reduce((a, k) => a + k.x, 0) / known.length, y: known.reduce((a, k) => a + k.y, 0) / known.length } : centers[n.module] || { x: 0, y: 0 };
      const a = hash(n.id) * Math.PI * 2;
      n.x = base.x + Math.cos(a) * 60; n.y = base.y + Math.sin(a) * 60;
    }
    if (fresh) {
      const pinned = new Set(nodes.filter((n) => pos[n.id]).map((n) => n.id));
      let alpha = pinned.size ? 0.5 : 1;
      for (let t = 0; t < 500 && alpha > 0.004; t += 1) {
        for (let i = 0; i < nodes.length; i += 1) {
          for (let j = i + 1; j < nodes.length; j += 1) {
            const a = nodes[i], b = nodes[j];
            let dx = a.x - b.x, dy = a.y - b.y;
            const d2 = Math.max(dx * dx + dy * dy, 64), d = Math.sqrt(d2);
            const f = (a.module === b.module ? 7600 : 9500) / d2 * alpha;
            dx /= d; dy /= d;
            a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
          }
        }
        for (const e of edges) {
          if (e.s === e.t) continue;
          const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y, d = Math.max(Math.hypot(dx, dy), 1);
          const f = (d - (e.subtype ? 130 : 160)) * 0.035 * alpha;
          e.s.vx += (dx / d) * f; e.s.vy += (dy / d) * f; e.t.vx -= (dx / d) * f; e.t.vy -= (dy / d) * f;
        }
        const cm = {};
        for (const n of nodes) { const c = cm[n.module] || (cm[n.module] = { x: 0, y: 0, k: 0 }); c.x += n.x; c.y += n.y; c.k += 1; }
        for (const n of nodes) {
          const c = cm[n.module];
          n.vx += ((c.x / c.k) - n.x) * 0.04 * alpha - n.x * 0.006 * alpha;
          n.vy += ((c.y / c.k) - n.y) * 0.04 * alpha - n.y * 0.006 * alpha;
        }
        for (const n of nodes) {
          if (pinned.has(n.id)) { n.vx = 0; n.vy = 0; continue; }
          n.vx *= 0.6; n.vy *= 0.6; n.x += n.vx; n.y += n.vy;
        }
        alpha *= 0.985;
      }
    }
    for (const n of nodes) pos[n.id] = { x: n.x, y: n.y };
    const clusters = data.clusters.map((c) => ({ ...c, nodes: nodes.filter((n) => n.module === c.id) })).filter((c) => c.nodes.length);
    return { nodes, edges, clusters };
  }

  function fit(W, H) {
    const xs = G.nodes.map((n) => n.x), ys = G.nodes.map((n) => n.y);
    if (!xs.length) return { k: 1, tx: W / 2, ty: H / 2 };
    const minX = Math.min(...xs) - 70, maxX = Math.max(...xs) + 70, minY = Math.min(...ys) - 60, maxY = Math.max(...ys) + 60;
    const k = Math.min(W / (maxX - minX), H / (maxY - minY), 1.6);
    return { k, tx: W / 2 - ((minX + maxX) / 2) * k, ty: H / 2 - ((minY + maxY) / 2) * k };
  }

  function hull(points) {
    const p = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return p;
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const x of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], x) <= 0) lo.pop(); lo.push(x); }
    for (const x of p.slice().reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], x) <= 0) up.pop(); up.push(x); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }

  function mountGraph(canvas, data, opt) {
    if (!canvas) return;
    const laid = layout(data, opt.pos);
    Object.assign(G, { canvas, nodes: laid.nodes, edges: laid.edges, clusters: laid.clusters, view: null,
      pos: opt.pos, sel: opt.sel, pick: opt.pick, shown: opt.shown || null, label: opt.label || null });
    if (G.ro) G.ro.disconnect();
    G.ro = new ResizeObserver(() => { G.view = null; drawGraph(); });
    G.ro.observe(canvas);
    const at = (ev) => {
      const r = canvas.getBoundingClientRect();
      const sx = ev.clientX - r.left, sy = ev.clientY - r.top, v = G.view;
      return { sx, sy, x: (sx - v.tx) / v.k, y: (sy - v.ty) / v.k };
    };
    const hit = (p) => G.nodes.find((n) => (!G.shown || G.shown('node', n)) && Math.hypot(n.x - p.x, n.y - p.y) * G.view.k < 16);
    canvas.onpointerdown = (ev) => {
      const p = at(ev), n = hit(p);
      G.drag = { n, sx: p.sx, sy: p.sy, tx: G.view.tx, ty: G.view.ty, moved: false };
      canvas.setPointerCapture(ev.pointerId);
      canvas.classList.add('drag');
    };
    canvas.onpointermove = (ev) => {
      if (!G.drag) { const n = hit(at(ev)); canvas.style.cursor = n ? 'pointer' : 'grab'; return; }
      const p = at(ev), d = G.drag;
      if (Math.hypot(p.sx - d.sx, p.sy - d.sy) > 3) d.moved = true;
      if (!d.moved) return;
      if (d.n) { d.n.x = p.x; d.n.y = p.y; G.pos[d.n.id] = { x: p.x, y: p.y }; } else { G.view.tx = d.tx + p.sx - d.sx; G.view.ty = d.ty + p.sy - d.sy; G.manual = true; }
      drawGraph(true);
    };
    canvas.onpointerup = () => {
      const d = G.drag;
      G.drag = null;
      canvas.classList.remove('drag');
      if (d && !d.moved && d.n && G.pick) G.pick(d.n.id);
    };
    canvas.onwheel = (ev) => {
      ev.preventDefault();
      const p = at(ev), f = Math.exp(-ev.deltaY * 0.0015), v = G.view;
      v.k = Math.min(Math.max(v.k * f, 0.3), 3);
      v.tx = p.sx - p.x * v.k; v.ty = p.sy - p.y * v.k; G.manual = true;
      drawGraph(true);
    };
    G.manual = false;
    drawGraph();
  }

  function drawGraph(keepView) {
    const canvas = G.canvas;
    if (!canvas || !document.body.contains(canvas)) return;
    const W = canvas.clientWidth, H = canvas.clientHeight, dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
    if (!G.view || (!keepView && !G.manual)) G.view = fit(W, H);
    const v = G.view, ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.translate(v.tx, v.ty);
    ctx.scale(v.k, v.k);
    const font = (px, w = 600) => `${w} ${px / Math.max(v.k, 0.7)}px Pretendard, "Malgun Gothic", sans-serif`;
    const seen = (kind, x) => (G.shown ? G.shown(kind, x) : 1);
    const name = (n) => (G.label ? G.label(n) : n.label);
    // module groups
    for (const c of G.clusters) {
      const pts = [];
      const members = c.nodes.filter((n) => seen('node', n));
      if (!members.length) continue;
      for (const n of members) for (let i = 0; i < 12; i += 1) { const a = (i / 12) * Math.PI * 2; pts.push([n.x + Math.cos(a) * 38, n.y + Math.sin(a) * 34]); }
      const h = hull(pts);
      ctx.beginPath();
      h.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.fillStyle = 'rgba(26,115,232,0.035)';
      ctx.fill();
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = '#c3ccd8';
      ctx.lineWidth = 1.2 / v.k;
      ctx.lineJoin = 'round';
      ctx.stroke();
      ctx.setLineDash([]);
      const top = Math.min(...h.map((p) => p[1]));
      const mid = (Math.min(...h.map((p) => p[0])) + Math.max(...h.map((p) => p[0]))) / 2;
      ctx.font = font(11.5, 700);
      ctx.textAlign = 'center';
      ctx.lineWidth = 4 / Math.max(v.k, 0.7);
      ctx.strokeStyle = '#fff';
      ctx.strokeText(c.label, mid, top - 7);
      ctx.fillStyle = '#8a96a5';
      ctx.fillText(c.label, mid, top - 7);
    }
    const sel = G.sel();
    // edges
    for (const e of G.edges) {
      const alpha = Math.min(seen('edge', e), seen('node', e.s), seen('node', e.t));
      if (!alpha) continue;
      ctx.globalAlpha = alpha;
      const on = sel && (e.source === sel || e.target === sel);
      const { s, t } = e;
      ctx.strokeStyle = on ? '#1a73e8' : '#a7b2c1';
      ctx.fillStyle = ctx.strokeStyle;
      ctx.lineWidth = (on ? 1.8 : 1.2) / Math.max(v.k, 0.7);
      ctx.setLineDash(e.subtype ? [5, 4] : []);
      if (s === t) {
        ctx.beginPath();
        ctx.arc(s.x + 20, s.y - 20, 12, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        continue;
      }
      const dx = t.x - s.x, dy = t.y - s.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
      const x1 = s.x + ux * 12, y1 = s.y + uy * 12, x2 = t.x - ux * 14, y2 = t.y - uy * 14;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(x2, y2); ctx.lineTo(x2 - ux * 8 - uy * 4, y2 - uy * 8 + ux * 4); ctx.lineTo(x2 - ux * 8 + uy * 4, y2 - uy * 8 - ux * 4); ctx.closePath(); ctx.fill();
      if (!e.subtype && s !== t && (on || v.k > 1.4)) {
        ctx.font = font(10.5, on ? 700 : 500);
        ctx.textAlign = 'center';
        ctx.lineWidth = 4 / Math.max(v.k, 0.7);
        ctx.strokeStyle = '#fff';
        ctx.strokeText(e.label, (s.x + t.x) / 2, (s.y + t.y) / 2 - 3);
        ctx.fillStyle = on ? '#15509f' : '#6b7685';
        ctx.fillText(e.label, (s.x + t.x) / 2, (s.y + t.y) / 2 - 3);
      }
    }
    ctx.globalAlpha = 1;
    // nodes
    for (const n of G.nodes) {
      const alpha = seen('node', n);
      if (!alpha) continue;
      ctx.globalAlpha = alpha;
      const on = n.id === sel;
      if (on) { ctx.beginPath(); ctx.arc(n.x, n.y, 17, 0, Math.PI * 2); ctx.fillStyle = 'rgba(26,115,232,0.16)'; ctx.fill(); }
      ctx.beginPath();
      ctx.arc(n.x, n.y, 10, 0, Math.PI * 2);
      if (n.abstract) { ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 2.6; ctx.strokeStyle = on ? '#1a73e8' : '#13213c'; ctx.stroke(); } else { ctx.fillStyle = on ? '#1a73e8' : '#13213c'; ctx.fill(); }
      ctx.font = font(12.5, 700);
      ctx.textAlign = 'center';
      ctx.lineWidth = 4 / Math.max(v.k, 0.7);
      ctx.strokeStyle = '#fff';
      ctx.strokeText(name(n), n.x, n.y + 27);
      ctx.fillStyle = on ? '#15509f' : '#1b2330';
      ctx.fillText(name(n), n.x, n.y + 27);
    }
    ctx.globalAlpha = 1;
  }

  // ---- queries -------------------------------------------------------------------------------------------------

  function roleFields(state) {
    const roles = S.st.roles;
    const role = roles.find((r) => r.name === state.role);
    const opts = ['<option value="">역할 지정 안 함</option>'].concat(roles.map((r) => `<option value="${esc(r.name)}"${r.name === state.role ? ' selected' : ''}>${esc(r.label)}</option>`));
    const keys = role ? role.principal.map((k) => `<div class="field"><label>${esc(k)}</label><input type="text" data-in="principal" data-k="${esc(k)}" value="${esc(state.principal[k] || '')}" placeholder="조회 범위 값"></div>`).join('') : '';
    return `<div class="field"><label>실행 역할</label><select data-in="role">${opts.join('')}</select></div>${keys}`;
  }

  function viewQuery() {
    const st = S.st, q = S.q;
    const modes = [['list', '등록 질의'], ['text', '쿼리 입력']].concat(st.ask ? [['ask', '자연어 질문']] : []);
    const seg = `<div class="seg">${modes.map(([k, l]) => `<button class="${q.mode === k ? 'on' : ''}" data-act="qmode" data-mode="${k}">${l}</button>`).join('')}</div>`;
    let left = '';
    if (q.mode === 'list') {
      const sel = st.queries.find((x) => x.name === q.name);
      const params = sel ? Object.entries(sel.params).map(([k, t]) => `<div class="field"><label>${esc(k)} · ${esc(t)}</label><input type="text" data-in="param" data-k="${esc(k)}" value="${esc(plainText(q.params[k]))}"></div>`).join('') : '';
      const asked = sel ? st.questions.filter((x) => x.query === sel.name) : [];
      left = `<div class="qlist">${st.queries.map((x) => `<button class="qitem${x.name === q.name ? ' on' : ''}" data-act="pick" data-q="${esc(x.name)}"><b>${esc(x.label)}</b><span>${esc(x.name)}</span></button>`).join('')}</div>
        ${params}${asked.length ? `<div class="hint" style="margin-bottom:12px">검증 질문 · ${asked.map((x) => esc(x.text)).join('<br>')}</div>` : ''}`;
    } else if (q.mode === 'text') {
      left = `<div class="field"><label>언어</label><select data-in="lang">${TEXT_LANG.map(([k, l]) => `<option value="${k}"${q.lang === k ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
        <div class="field"><textarea class="code" data-in="text" spellcheck="false">${esc(q.text)}</textarea></div>
        <div class="hint" style="margin-bottom:12px">입력한 쿼리를 모든 백엔드 쿼리로 변환해 실행합니다.</div>`;
    } else {
      const ex = st.questions.filter((x) => x.query).slice(0, 4);
      left = `<div class="field"><label>질문</label><input type="text" data-in="question" value="${esc(q.question)}" placeholder="질문을 입력하세요"></div>
        <div class="chips" style="margin-bottom:12px">${ex.map((x) => `<button class="chip" data-act="example" data-text="${esc(x.text)}">${esc(x.text)}</button>`).join('')}</div>`;
    }
    const run = `<button class="btn primary" style="width:100%" data-act="run"${q.busy ? ' disabled' : ''}>${q.busy ? '<span class="spin"></span>실행 중' : '실행'}</button>`;
    return `
<div class="head"><div><h1>질의</h1><div class="sub">온톨로지 질의를 백엔드별 쿼리로 변환해 실행합니다</div></div>
  <div class="right">${q.res && q.res.ok ? (q.res.agree ? '<span class="chip ok">✓ 백엔드 결과 일치</span>' : '<span class="chip warn">백엔드 결과 불일치</span>') : ''}</div></div>
<div class="grid" style="grid-template-columns:320px minmax(0,1fr);align-items:start">
  <div class="card"><div class="ch">질의</div><div class="cb">${seg}${left}${roleFields(q)}${run}</div></div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${queryResult()}</div>
</div>`;
  }

  function queryResult() {
    const r = S.q.res;
    if (!r) return '<div class="card"><div class="cb"><div class="empty">질의를 선택하세요.</div></div></div>';
    if (!r.ok) return `<div class="banner no"><span class="ic x" style="width:26px;height:26px">!</span><div class="why">${esc(r.error)}</div></div>`;
    const cur = r.translations.find((t) => t.target === S.q.target && t.ok) || r.translations.find((t) => t.ok);
    const tabs = r.translations.map((t) => `<button class="tab${cur && t.target === cur.target ? ' on' : ''}${t.ok ? '' : ' off'}" ${t.ok ? `data-act="target" data-target="${esc(t.target)}"` : `title="${esc(t.error)}" disabled`}>${esc(t.label)}</button>`).join('');
    const results = r.results.map((b) => {
      if (!b.ok) return `<div class="card"><div class="ch">${esc(b.backend)}<span class="chip">${esc(b.language.toUpperCase())} · ${esc(b.dialect)}</span></div><div class="cb"><div class="muted mono" style="font-size:12px">${esc(b.error)}</div></div></div>`;
      const head = b.columns.map((c) => `<th>${esc(c)}${b.masked && b.masked[c] ? ' <span class="chip sm warn">가림</span>' : ''}</th>`).join('');
      const body = b.rows.slice(0, 50).map((row) => `<tr>${row.map((v) => `<td class="${typeof v === 'number' ? 'num' : ''}">${show(v)}</td>`).join('')}</tr>`).join('');
      return `<div class="card"><div class="ch">${esc(b.backend)}<span class="chip">${esc(b.language.toUpperCase())} · ${esc(b.dialect)}</span><div class="right"><span class="chip">${b.rows.length}행</span></div></div>
        <div class="cb scroll" style="padding:0;max-height:340px"><table>${b.rows.length ? `<tr>${head}</tr>${body}` : '<tr><td class="muted">결과가 없습니다.</td></tr>'}</table></div></div>`;
    }).join('');
    const params = Object.keys(r.params || {}).length ? Object.entries(r.params).map(([k, v]) => `${esc(k)} = ${show(v)}`).join(' · ') : '없음';
    return `
<div class="grid" style="grid-template-columns:minmax(0,0.8fr) minmax(0,1.2fr);flex:none">
  <div class="card"><div class="ch">온톨로지 질의 IR${r.attempts ? `<div class="right"><span class="chip b">생성 시도 ${r.attempts}회</span></div>` : ''}</div><div class="cb"><pre class="code ir" style="max-height:340px;overflow:auto">${esc(r.ir)}</pre></div></div>
  <div class="card"><div class="ch">백엔드 쿼리</div><div class="cb"><div class="tabs" style="margin-bottom:10px">${tabs}</div>
    <pre class="code" style="max-height:300px;overflow:auto">${cur ? cur.html : ''}</pre>
    <div class="muted" style="font-size:12px;margin-top:6px">파라미터 ${params}</div></div></div>
</div>
<div class="grid" style="grid-template-columns:repeat(${Math.max(r.results.length, 1)}, minmax(0,1fr));flex:none">${results}</div>`;
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
      const keys = await keysFor(dec.target);
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
    if (!st.decisions.length) return '<div class="head"><div><h1>판정 · 처리</h1></div></div><div class="empty">적용된 모듈에 결정표가 없습니다.</div>';
    const dec = st.decisions.find((x) => x.name === d.name) || st.decisions[0];
    const keys = S.d.keys[dec.target] || [];
    const keyOpts = keys.map((k) => {
      const extra = Object.values(k.fields).filter((v) => v !== null && v !== '').map(plainText).join(' · ');
      return `<option value="${esc(k.key)}"${k.key === d.key ? ' selected' : ''}>${esc(k.key)}${extra ? ' · ' + esc(extra) : ''}</option>`;
    }).join('');
    const qs = st.questions.filter((x) => x.decision).map((x) => `<button class="chip" data-act="ask-decision" data-name="${esc(x.decision)}" data-key="${esc(x.key)}">${esc(x.text)}</button>`).join('');
    const controls = `<div class="card"><div class="cb">
      <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:12px">
        <div class="field" style="margin:0"><label>결정</label><select data-in="decision">${st.decisions.map((x) => `<option value="${esc(x.name)}"${x.name === dec.name ? ' selected' : ''}>${esc(x.label)} · ${esc(x.name)}</option>`).join('')}</select></div>
        <div class="field" style="margin:0"><label>대상 ${esc(dec.target_label)}</label><select data-in="key">${keyOpts}</select></div></div>
      ${qs ? `<div class="label" style="margin:12px 0 6px">검증 질문</div><div class="chips">${qs}</div>` : ''}</div></div>`;
    const r = d.res;
    let body = '';
    if (!r) body = '<div class="empty"><span class="spin"></span>판정 중입니다.</div>';
    else if (r.error) body = `<div class="banner no"><span class="ic x" style="width:26px;height:26px">!</span><div class="why">${esc(r.error)}</div></div>`;
    else body = decisionBody(r);
    return `
<div class="head"><div><h1>판정 · 처리</h1><div class="sub">결정표 판정 결과와 근거를 확인하고 처리 요청을 승인합니다</div></div>
  <div class="right">${r && !r.error ? `<a class="btn ghost" href="/api/export/jdm?decision=${encodeURIComponent(r.name)}" download>ZEN JDM 내려받기</a>` : ''}</div></div>
${controls}${body}`;
  }

  function decisionBody(r) {
    const matched = r.rules.filter((x) => x.hit);
    const cite = matched.map((x) => x.cite).filter(Boolean);
    const engines = [`<span class="chip">엔진 ${esc(r.engine === 'native' ? '기본' : r.engine)}</span>`];
    if (r.zen) engines.push(r.zen.error ? `<span class="chip warn" title="${esc(r.zen.error)}">GoRules ZEN 실행 실패</span>` : (r.zen.same ? '<span class="chip ok">GoRules ZEN 판정 일치</span>' : '<span class="chip warn">GoRules ZEN 판정 불일치</span>'));
    const th = (n) => `<th>${esc(n).replace(/_/g, '_<wbr>')}</th>`;
    const head = '<th>규칙</th>' + r.inputs.map(th).join('') + r.outputs.map(th).join('');
    const rows = r.rules.map((x) => `<tr class="${x.hit ? 'hit' : ''}"><td class="mono" style="white-space:nowrap">${esc(x.id)}${x.cite ? `<div class="muted cite-note">${esc(x.cite)}</div>` : ''}</td>
      ${r.inputs.map((i) => `<td class="mono" style="white-space:nowrap">${esc(x.when[i] ?? '-')}</td>`).join('')}
      ${r.outputs.map((o) => `<td style="min-width:120px">${show(x.then[o])}</td>`).join('')}</tr>`).join('');
    const ev = r.evidence.map((e) => `<div class="ev"><div><b>${esc(e.input)}</b><div class="muted" style="font-size:12px">${e.object ? `${esc(e.object_label)} ${esc(e.key)}${e.property_label ? ' · ' + esc(e.property_label) : ''}` : esc(e.source)}</div></div>
      <div><span class="chip b">${show(e.value)}</span></div><div class="src mono muted" style="font-size:12px">${e.source && e.object ? '← ' + esc(e.source) : ''}</div></div>`).join('');
    const touched = r.touched.length ? `<div class="right muted" style="font-weight:600;font-size:12px">규칙 추가 모듈 ${esc(r.touched.join(', '))}</div>` : '';
    return `
<div class="banner ${r.yes ? 'ok' : 'no'}"><span class="ic ${r.yes ? 'y' : 'x'}" style="width:30px;height:30px;font-size:16px">${r.yes ? '✓' : '!'}</span>
  <div><div class="big">${esc(r.label)} · ${r.yes ? '가능' : '불가'}</div><div class="why">${esc(r.reason)}</div>${(r.messages || []).map((m) => `<div class="cite">${esc(m.code)} · ${esc(m.text)}</div>`).join('')}${cite.length ? `<div class="cite">근거 규정 · ${esc(cite.join(', '))}</div>` : ''}</div>
  <div style="margin-left:auto" class="chips">${engines.join('')}${matched.length ? `<span class="chip b">규칙 ${esc(matched.map((x) => x.id).join(', '))}</span>` : ''}</div></div>
<div class="grid" style="grid-template-columns:minmax(0,1.45fr) minmax(360px,1fr);align-items:start">
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
    <div class="card"><div class="ch">결정표<span class="chip">적중 정책 ${esc(r.hit_policy)}</span>${touched}</div>
      <div class="cb scroll" style="padding:0"><table class="tight" style="font-size:12.5px"><tr>${head}</tr>${rows}</table></div></div>
    <div class="card"><div class="ch">근거 경로<div class="right muted" style="font-weight:600;font-size:12px">입력값별 원천 컬럼</div></div><div class="cb">${ev || '<div class="empty">원천 컬럼에서 읽은 입력값이 없습니다.</div>'}</div></div>
  </div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${actionCard(r)}${agreementCard()}${auditCard()}</div>
</div>`;
  }

  function actionCard(r) {
    const a = S.st.actions.find((x) => r.actions.includes(x.name));
    if (!a) return '';
    const d = S.d, p = d.proposal && d.proposal.key === r.key && d.proposal.action === a.name ? d.proposal : null;
    const roles = S.st.roles;
    if (!d.role) d.role = (roles.find((x) => x.principal.length) || roles[0] || {}).name || '';
    const params = Object.keys(a.parameters).map((k) => `<div class="field"><label>${esc(k)}</label><input type="text" data-in="aparam" data-k="${esc(k)}" value="${esc(d.params[k] ?? (k === 'reason' ? '사이즈가 맞지 않음' : ''))}"></div>`).join('');
    let state = '';
    if (p) {
      const [cls, label] = STATUS[p.status] || ['', p.status];
      const checks = p.checks.map((c) => `<div class="check"><span class="ic ${c.passed ? 'y' : 'x'}">${c.passed ? '✓' : '!'}</span><b style="min-width:120px">${esc(c.title)}</b><span class="muted" style="font-size:12px;overflow-wrap:anywhere">${esc(c.detail)}</span></div>`).join('');
      const diff = Object.keys(p.changes).map((k) => `<div class="diff"><span class="mono">${esc(k)}</span><span class="chip">${show(p.before[k])}</span><span class="arrow">→</span><span class="chip ${p.status === 'executed' ? 'ok' : 'b'}">${show(p.changes[k])}</span></div>`).join('');
      const buttons = p.status === 'pending' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" style="flex:1" data-act="approve" data-id="${esc(p.id)}">승인</button><button class="btn" style="flex:1" data-act="reject" data-id="${esc(p.id)}">반려</button></div>`
        : (p.can_roll_back ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn" style="flex:1" data-act="rollback" data-id="${esc(p.id)}">되돌리기</button></div>` : '');
      const call = p.call && (p.call.status || p.call.error) ? `<div class="hint" style="margin-top:8px">외부 호출 ${p.call.error ? esc(p.call.error) : `${esc(p.call.method)} ${esc(p.call.url)} · ${esc(p.call.status)}`}</div>` : '';
      const done = (p.status === 'executed' ? '<div class="hint" style="margin-top:10px">원천 DB와 그래프 저장소에 반영했습니다. 판정을 다시 계산했습니다.</div>'
        : (p.status === 'rolled_back' ? `<div class="hint" style="margin-top:10px">${esc(p.rolled_back_by)} 님이 실행 전 값으로 되돌렸습니다.</div>` : '')) + call;
      state = `<div class="sec" style="display:flex;align-items:center;gap:8px">요청 ${esc(p.id)} · ${esc(p.requested_by)}<span class="chip ${cls}" style="margin-left:auto">${label}</span></div>${checks}${diff ? `<div class="sec">변경 값</div>${diff}` : ''}${buttons}${done}`;
    }
    return `<div class="card"><div class="ch">${esc(a.label)} <span class="muted mono" style="font-weight:600">${esc(a.name)}</span></div><div class="cb">
      <div class="muted" style="font-size:12.5px;margin-bottom:10px;line-height:1.55">요청 시 권한, 파라미터, 상태 전이, 판정 조건을 검사합니다. 승인한 요청만 원천 DB에 반영합니다.</div>
      <div class="field"><label>요청 역할</label><select data-in="arole">${roles.map((x) => `<option value="${esc(x.name)}"${x.name === d.role ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></div>
      ${params}<button class="btn primary" style="width:100%" data-act="request" data-action="${esc(a.name)}">${esc(r.target_label)} ${esc(r.key)} ${esc(a.label)} 요청</button>
      ${state}</div></div>`;
  }

  async function loadAgreement() {
    S.agree = { busy: true };
    try { S.agree = await api('agreement'); } catch (e) { S.agree = { ok: false, error: e.message }; }
    if (S.tab === 'decide') render();
  }

  function agreementCard() {
    const a = S.agree;
    if (!a || a.busy) return '';
    if (!a.ok) return `<div class="card"><div class="ch">판정 일치율</div><div class="cb"><div class="hint">${esc(a.error)}</div></div></div>`;
    const conf = Object.entries(a.confusion || {}).map(([out, cells]) => `<div class="label" style="margin:8px 0 4px">${esc(out)} · 실제 → 판정</div><div class="chips">${Object.entries(cells).map(([k, n]) => `<span class="chip sm${k.split(' → ')[0] === k.split(' → ')[1] ? ' ok' : ' warn'}">${esc(k)} · ${n}건</span>`).join('')}</div>`).join('');
    return `<div class="card"><div class="ch">판정 일치율 · ${esc(a.label)}<div class="right"><span class="chip ${a.rate === 1 ? 'ok' : 'warn'}">${pct(a.rate)}</span></div></div><div class="cb">
      <div class="muted" style="font-size:12.5px;line-height:1.55">지난 처리 기록 ${a.cases}건을 그때 값으로 다시 판정해 실제 처리와 비교했습니다. ${a.agree}건이 일치합니다.</div>
      ${conf}${a.mismatches.length ? `<div class="label" style="margin:10px 0 4px">다른 건</div>${mismatchRows(a.mismatches)}` : ''}</div></div>`;
  }

  function auditCard() {
    const a = S.d.audit;
    if (!a.length) return '';
    return `<div class="card"><div class="ch">감사 로그</div><div class="cb log">${a.slice(0, 10).map((x) => `<div><span class="muted">${esc(x.event)}</span><span>${esc(x.actor)} · ${esc(x.key)}</span><span class="muted mono">${esc(x.proposal)}</span></div>`).join('')}</div></div>`;
  }

  async function requestAction(action) {
    const d = S.d;
    const a = S.st.actions.find((x) => x.name === action);
    const params = {};
    for (const k of Object.keys(a.parameters)) params[k] = d.params[k] ?? (k === 'reason' ? '사이즈가 맞지 않음' : '');
    try {
      const r = await api('request', { action, key: d.key, params, role: d.role });
      d.proposal = r.proposal;
      d.audit = (await api('audit')).audit;
      render();
      toast(r.proposal.status === 'pending' ? '검사를 통과했습니다. 승인 대기 중입니다.' : '검사를 통과하지 못해 요청이 반려되었습니다.', r.proposal.status !== 'pending');
    } catch (e) { fail(e); }
  }

  async function approve(id, yes) {
    try {
      const r = await api('approve', { id, approve: yes });
      if (!r.ok) throw new Error(r.error);
      S.d.proposal = r.proposal;
      S.q.res = null; S.qa = null; S.bind = null; S.fl = null; S.d.keys = {};
      await load();
      await startDecide();
      toast(yes ? '승인했습니다. 원천 DB에 반영되었습니다.' : '요청을 반려했습니다.');
    } catch (e) { fail(e); }
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
      toast(yes ? `${r.change.module_label} ${r.change.version} 변경을 승인하고 적용했습니다.` : '변경을 반려했습니다.');
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
      <div class="muted" style="font-size:12.5px;margin:6px 0">기록 ${v.records}건 · 통합 ${v.identities}건 · 둘 이상 묶인 건 ${v.joined}${v.findings ? ` · 확인 필요 ${v.findings}` : ''}</div>
      ${clusters ? `<table class="tight"><tr><th>통합 번호</th><th>구성원</th><th>근거</th></tr>${clusters}</table>` : ''}
      <button class="btn sm" data-act="iresolve" data-name="${esc(name)}" style="margin-top:8px">다시 묶어 교차표 저장</button>`;
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
    if (S.tab === 'check') render();
  }

  function viewCheck() {
    const r = S.qa;
    const head = `<div class="head"><div><h1>검증</h1><div class="sub">검증 질문 정답률, 근거 제시율, 백엔드 간 결과 일치 여부를 확인합니다</div></div>
      <div class="right"><button class="btn primary" data-act="checks">다시 실행</button></div></div>`;
    if (!r || r.busy) return head + '<div class="empty"><span class="spin"></span>검증 중입니다.</div>';
    if (r.error) return head + `<div class="banner no"><div class="why">${esc(r.error)}</div></div>`;
    const passed = r.results.filter((x) => x.passed).length;
    const c = r.conformance;
    const stats = `<div class="stats"><div class="stat"><b>${r.results.length ? Math.round(r.accuracy * 100) + '%' : '-'}</b><span>정답률</span></div>
      <div class="stat"><b>${passed} / ${r.results.length}</b><span>정답 수</span></div>
      <div class="stat"><b>${r.results.length ? Math.round(r.grounded * 100) + '%' : '-'}</b><span>근거 제시율</span></div>
      ${c && c.summary ? `<div class="stat"><b>${c.summary.agree} / ${c.summary.queries}</b><span>백엔드 결과 일치 질의</span></div>` : ''}</div>`;
    const rows = r.results.map((x) => `<tr><td class="mono">${esc(x.id)}</td><td style="min-width:180px">${esc(x.text)}</td><td style="font-size:12px">${showObj(x.expected)}</td>
      <td style="font-size:12px">${x.error ? `<span class="muted">${esc(x.error)}</span>` : (typeof x.got === 'number' ? `${show(x.got)}행` : showObj(x.got))}</td>
      <td style="font-size:12px">${x.grounded ? '<span class="ic y">✓</span>' : `<span class="muted">${esc((x.gaps || []).join(', '))}</span>`}</td><td><span class="ic ${x.passed ? 'y' : 'x'}">${x.passed ? '✓' : '!'}</span></td></tr>`).join('');
    const conf = c && c.queries ? c.queries.map((x) => `<tr><td><b>${esc(x.label)}</b><div class="muted mono">${esc(x.name)}</div></td>
      <td style="font-size:12px">${Object.entries(x.rows).map(([b, n]) => `${esc(b)} ${n === null ? '오류' : n + '행'}`).join(' · ')}</td>
      <td><span class="ic ${x.agree ? 'y' : 'x'}">${x.agree ? '✓' : '!'}</span></td></tr>`).join('') : '';
    return `${head}${stats}
<div class="grid" style="grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr);align-items:start">
  <div class="card"><div class="ch">검증 질문</div><div class="cb scroll" style="padding:0">${rows ? `<table class="tight"><tr><th>번호</th><th>질문</th><th>정답</th><th>결과</th><th>근거</th><th></th></tr>${rows}</table>` : '<div class="empty" style="padding:14px">등록된 검증 질문이 없습니다.</div>'}</div></div>
  <div class="card"><div class="ch">백엔드 결과 일치<div class="right muted" style="font-weight:600;font-size:12px">등록 질의 기준</div></div><div class="cb scroll" style="padding:0">${conf ? `<table class="tight"><tr><th>질의</th><th>행</th><th></th></tr>${conf}</table>` : '<div class="empty" style="padding:14px">비교할 백엔드가 하나뿐입니다.</div>'}</div></div>
</div>${questionCard()}`;
  }

  // ---- bindings ------------------------------------------------------------------------------------------------

  async function runBindings() {
    S.bind = { busy: true };
    if (S.tab === 'bind') render();
    try { S.bind = await api('bindings', {}); } catch (e) { S.bind = { error: e.message }; }
    if (S.tab === 'bind') render();
  }

  function viewBind() {
    const r = S.bind;
    const head = `<div class="head"><div><h1>DB 대조</h1><div class="sub">온톨로지 정의와 원천 DB의 테이블, 컬럼, 타입, 키, 값을 대조합니다</div></div>
      <div class="right"><button class="btn primary" data-act="bindings">다시 대조</button></div></div>`;
    if (!r || r.busy) return head + '<div class="empty"><span class="spin"></span>대조 중입니다.</div>';
    if (r.error || r.ok === undefined) return head + `<div class="banner no"><div class="why">${esc(r.error || '')}</div></div>`;
    const label = { tables: '테이블', columns: '컬럼', data_checks: '데이터 점검', links: '관계' };
    const stats = `<div class="stats">${Object.entries(r.checked).map(([k, n]) => `<div class="stat"><b>${n}</b><span>${esc(label[k] || k)}</span></div>`).join('')}
      <div class="stat"><b>${r.findings.length}</b><span>문제</span></div></div>`;
    const banner = r.ok && !r.findings.length ? '<div class="banner ok"><span class="ic y" style="width:26px;height:26px">✓</span><div><div class="big" style="font-size:16px">정의와 원천 DB가 일치합니다</div></div></div>'
      : `<div class="banner ${r.ok ? 'ok' : 'no'}"><span class="ic ${r.ok ? 'y' : 'x'}" style="width:26px;height:26px">${r.ok ? '✓' : '!'}</span><div><div class="big" style="font-size:16px">${r.ok ? '확인이 필요한 항목이 있습니다' : '정의와 원천 DB가 일치하지 않습니다'}</div></div></div>`;
    const rows = r.findings.map((f) => `<tr><td><span class="chip ${f.severity === 'error' ? 'bad' : 'warn'}">${f.severity === 'error' ? '오류' : '주의'}</span></td>
      <td>${esc(FINDING[f.kind] || f.kind)}</td><td>${element(f.element)}</td><td class="mono muted" style="font-size:12px">${esc(f.detail)}</td></tr>`).join('');
    return `${head}${stats}${banner}${r.findings.length ? `<div class="card"><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>심각도</th><th>종류</th><th>항목</th><th>내용</th></tr>${rows}</table></div></div>` : ''}`;
  }

  // ---- guide: the demo video beside the manual, each pointing at the other -------------------------------------

  const bytes = (n) => (n >= 1 << 20 && n % (1 << 20) === 0 ? `${n >> 20}MB` : `${(n >> 10).toLocaleString('ko-KR')}KB`);
  const clock = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  const navLabel = (tab) => (NAV.find((x) => x[0] === tab) || [tab, tab])[1];

  function viewGuide() {
    const g = S.guide || { video: '', chapters: [] };
    const head = `<div class="head"><div><h1>사용 안내</h1><div class="sub">${g.video ? '화면별 사용 방법과 시연 영상입니다' : '화면별 사용 방법입니다'}</div></div></div>`;
    const sections = GUIDE.map(([tab, what, steps], i) => {
      if (S.st && S.st.ask && tab === 'query') steps = steps.concat(ASK_STEP);  // only where a language model is connected
      if (S.st && S.st.ask && tab === 'library') steps = steps.concat(POLICY_STEP);
      const ch = g.chapters.find((c) => c.tab === tab);
      return `<div class="card gsec" data-gtab="${tab}"><div class="cb">
        <div class="fhead"><span class="fno">${i + 1}</span><svg class="gic" viewBox="0 0 24 24">${ICON[tab]}</svg><b>${navLabel(tab)}</b></div>
        <div class="gwhat">${esc(what)}</div>
        <ol class="gsteps">${steps.map((x) => `<li>${esc(x)}</li>`).join('')}</ol>
        <div class="chips"><a class="btn sm" href="#${tab}">${navLabel(tab)} 열기</a>${ch && g.video ? `<button class="btn sm ghost" data-act="seek" data-t="${ch.t}">영상 ${clock(ch.t)}</button>` : ''}</div></div></div>`;
    }).join('');
    const ways = GUIDE_ADAPT.filter((x) => !x[3] || (S.st && S.st.ask));
    const intro = `<div class="card gsec"><div class="cb"><div class="fhead"><b>스튜디오 용도</b></div>
        <table class="tight">${GUIDE_USE.map(([k, v]) => `<tr><td style="white-space:nowrap"><b>${esc(k)}</b></td><td style="font-size:12.5px">${esc(v)}</td></tr>`).join('')}</table></div></div>
      <div class="card gsec"><div class="cb"><div class="fhead"><b>도메인 어댑팅</b></div>
        <div class="gwhat">표준 모듈은 그대로 두고 달라지는 내용만 모듈로 추가합니다. 모든 경로의 결과는 같은 모듈 파일이며, 같은 방식으로 검토 · 승인 · 적용 · 해제합니다.</div>
        <table class="tight"><tr><th>보유 자료</th><th>경로</th><th>결과</th></tr>${ways.map(([a, b, c]) => `<tr><td>${esc(a)}</td><td style="font-size:12.5px">${esc(b)}</td><td style="font-size:12.5px">${esc(c)}</td></tr>`).join('')}</table>
        <div class="chips">${['공통 개념', '도메인', '업종 확장', '고객사 차이', '바인딩', '검증 기준', '구축 규칙'].map((x) => `<span class="chip sm">${x}</span>`).join('')}</div></div></div>`;
    if (!g.video) return `${head}<div class="guide-only">${intro}${sections}</div>`;
    const chapters = g.chapters.map((c, i) => `<button class="gch" data-act="seek" data-t="${c.t}" data-i="${i}"><span class="mono">${clock(c.t)}</span><span><b>${esc(c.chapter)} · ${esc(c.title)}</b><span class="muted">${esc((c.captions || [])[0] || '')}</span></span></button>`).join('');
    return `${head}<div class="guide">
      <div class="gside"><div class="card"><div class="cb" style="padding:0"><video id="gvideo" controls preload="metadata" playsinline src="${esc(g.video)}"></video></div>
        <div class="cb scroll gchs">${chapters}</div></div></div>
      <div class="gmain">${intro}${sections}</div></div>`;
  }

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
    try { S.fl = await api('flow'); } catch (e) { S.fl = { error: e.message }; }
    if (S.tab === 'flow') render();
  }

  function originInfo(o) {
    const item = (k, v) => `<span class="chip"><span class="muted">${k}</span> ${v}</span>`;
    if (o.kind === 'files') return [item('데이터 출처', '업로드 파일'), item('파일', esc(o.files.join(', ')))].join('');
    if (o.kind === 'database') return item('데이터 출처', esc(o.detail));
    const out = [item('데이터 출처', '예시 스튜디오'), item('구성 파일', `<span class="mono">${esc(o.config || '')}</span>`)];
    const kind = { sqlite: 'SQLite', postgres: 'PostgreSQL', dbapi: 'DB-API', rdflib: 'RDF', sparql: 'SPARQL 엔드포인트', neo4j: 'Neo4j' };
    for (const [n, k] of Object.entries(o.backends || {})) out.push(item(esc(n), esc(kind[k] || k)));
    if ((o.seeds || []).length) out.push(item('시드', esc(o.seeds.join(', '))));
    if (o.notice) out.push(`<span class="chip warn">${esc(o.notice)}</span>`);
    return out.join('');
  }

  function flowCard(step, i) {
    const [id, title, does, tab] = FLOW[i];
    let ok = true, lines = '';
    if (id === 'source') {
      lines = `<b>${esc((step.dialect || '').toUpperCase())}</b> · 테이블 ${show(step.tables.length)} · ${show(step.rows)}행
        <div class="chips" style="margin-top:6px">${step.tables.slice(0, 8).map((t) => `<span class="chip sm">${esc(t.table)}</span>`).join('')}${step.tables.length > 8 ? `<span class="chip sm">외 ${step.tables.length - 8}개</span>` : ''}</div>`;
    } else if (id === 'define') {
      lines = `모듈 ${step.modules.length} · 객체 ${step.objects} · 관계 ${step.links} · 속성 ${step.properties}${step.computed ? ` · 계산 속성 ${step.computed}` : ''}${step.identities ? ` · 식별 통합 ${step.identities}` : ''}
        <div class="chips" style="margin-top:6px">${step.modules.map((m) => `<span class="chip sm">${esc(m.label)}</span>`).join('')}</div>`;
    } else if (id === 'bind') {
      ok = step.ok !== false && !step.findings;
      const c = step.checked || {};
      lines = `테이블 ${show(c.tables || 0)} · 컬럼 ${show(c.columns || 0)} · 데이터 점검 ${show(c.data_checks || 0)}<div style="margin-top:4px">문제 <b>${step.findings}</b></div>`;
    } else if (id === 'project') {
      ok = step.nodes > 0;
      lines = step.backends.length ? `${esc(step.backends.join(', '))} · 노드 ${show(step.nodes)} · 간선 ${show(step.edges)}` : '그래프 저장소 없음';
      if (step.sync && step.sync.at) lines += `<div class="muted" style="margin-top:4px;font-size:12px">마지막 다시 읽기 ${esc(step.sync.at.replace('T', ' '))} · ${step.sync.error ? '실패' : (step.sync.changed ? '변경분 반영' : '변경 없음')}</div>`;
    } else if (id === 'query') {
      const c = step.conformance;
      ok = !c || (!c.error && c.agree === c.queries);
      lines = `등록 질의 ${step.queries} · 쿼리 언어 ${step.targets}개${c ? (c.error ? `<div class="muted" style="margin-top:4px">${esc(c.error)}</div>` : `<div style="margin-top:4px">백엔드 결과 일치 <b>${c.agree} / ${c.queries}</b></div>`) : ''}`;
    } else if (id === 'decide') {
      ok = step.decisions > 0 ? true : null;
      lines = step.decisions ? `결정 ${step.decisions} · 규칙 ${step.rules} · 액션 ${step.actions}` : (step.actions ? `액션 ${step.actions}` : '등록된 결정표 없음');
      if (step.agreement && step.agreement.cases) lines += `<div style="margin-top:4px">판정 일치율 <b>${pct(step.agreement.rate)}</b> (${step.agreement.agree} / ${step.agreement.cases})</div>`;
    } else if (id === 'check') {
      ok = step.questions ? step.accuracy === 1 : null;
      lines = step.questions ? `검증 질문 ${step.questions} · 정답률 <b>${Math.round(step.accuracy * 100)}%</b> · 근거 제시율 <b>${Math.round((step.grounded || 0) * 100)}%</b>` : '등록된 검증 질문 없음';
    }
    const gates = step.gates || [];
    if (gates.length) ok = gates.every((g) => g.passed);
    let chip = ok === null ? '<span class="chip">미등록</span>' : (ok ? '<span class="chip ok">✓</span>' : '<span class="chip warn">확인 필요</span>');
    if (step.on === false) chip = '<span class="chip">꺼짐</span>';
    const gateChips = gates.length ? `<div class="chips" style="margin-top:6px">${gates.map((g) => `<span class="chip sm ${g.passed ? 'ok' : 'bad'}">${esc(g.label)} ${gateValue(g, g.limit)} · 현재 ${gateValue(g, g.value)}${g.by ? ` · ${esc(g.by)}` : ''}</span>`).join('')}</div>` : '';
    const sync = id === 'project' && step.backends.length ? `<button class="btn sm ghost" data-act="sync">원천 다시 읽기</button>` : '';
    return `<div class="card fstep${step.on === false ? ' off' : ''}"><div class="cb">
      <div class="fhead"><span class="fno">${i + 1}</span><b>${title}</b><span style="flex:1"></span>${chip}</div>
      <div class="muted fdoes">${does}</div><div class="flive">${lines}${gateChips}</div>
      <div class="chips"><a class="btn sm ghost" href="#${tab}">${navLabel(tab)} 열기</a>${sync}</div></div></div>`;
  }

  function viewFlow() {
    const head = `<div class="head"><div><h1>흐름</h1><div class="sub">원천 데이터부터 검증까지 단계별 처리 현황입니다</div></div>
      <div class="right"><a class="btn primary" href="#data">데이터 연결</a></div></div>`;
    const banner = `<div class="chips origin">${originInfo(S.st.origin)}</div>`;
    const r = S.fl;
    if (!r || r.busy) return head + banner + '<div class="empty"><span class="spin"></span>현황을 불러오는 중입니다.</div>';
    if (r.error) return head + banner + `<div class="banner no"><div class="why">${esc(r.error)}</div></div>`;
    const cards = r.steps.map((x, i) => flowCard(x, i)).join('');
    const passed = (r.steps || []).some((x) => (x.gates || []).length) ? `<div class="banner ${r.passed ? 'ok' : 'no'}" style="margin:0 0 12px"><span class="ic ${r.passed ? 'y' : 'x'}" style="width:24px;height:24px">${r.passed ? '✓' : '!'}</span><div><div class="big" style="font-size:15px">${r.passed ? '모든 통과 조건을 충족합니다' : '충족하지 못한 통과 조건이 있습니다'}</div><div class="why">변경 요청은 같은 조건으로 검토합니다.</div></div></div>` : '';
    return `${head}${banner}${passed}<div class="flow">${cards}</div>${flowSettings()}`;
  }

  async function loadFlowSettings() {
    S.flset = { busy: true };
    try { S.flset = await api('flow/settings'); } catch (e) { S.flset = { error: e.message }; }
    if (S.tab === 'flow') render();
  }

  function flowSettings() {
    const f = S.flset;
    if (!f || f.busy) return '';
    if (f.error) return `<div class="banner no"><div class="why">${esc(f.error)}</div></div>`;
    const s = f.settings;
    const stages = f.stages.filter((x) => !['source', 'define'].includes(x.id)).map((x) => `<label class="tick"><input type="checkbox" data-in="fstage" data-k="${x.id}"${s.off.includes(x.id) ? '' : ' checked'}>${esc(x.label)}</label>`).join('');
    const conds = Object.entries(f.conditions).map(([stage, cs]) => cs.map((c) => {
      const v = (s.gates[stage] || {})[c.id];
      const share = c.id.startsWith('min_');
      const up = (f.raised || []).find((x) => x.stage === stage && x.condition === c.id);  // a quality module asks more
      const upText = up ? `<span class="muted" style="font-size:11.5px">${esc(up.module_label)} 적용 중 · ${share ? Math.round(up.value * 100) + '%' : up.value}</span>` : '';
      return `<label class="field"><span>${esc(c.label)}${share ? ' (%)' : ''}</span><input type="number" min="0"${share ? ' max="100"' : ''} step="1" data-in="fgate" data-s="${stage}" data-k="${c.id}" value="${v === undefined || v === null ? '' : (share ? Math.round(v * 100) : v)}" placeholder="조건 없음">${upText}</label>`;
    }).join('')).join('');
    const a = s.agreement || {};
    const dec = f.decisions.find((d) => d.name === a.decision);
    const q = f.queries.find((x) => x.name === a.query);
    const cols = q ? q.columns : [];
    const colSel = (kind, k, cur) => `<select class="inline" data-in="fagree" data-kind="${kind}" data-k="${esc(k)}"><option value="">-</option>${cols.map((c) => `<option value="${esc(c)}"${c === cur ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select>`;
    const maps = dec && q ? `<table class="tight" style="margin-top:8px"><tr><th>결정표</th><th>처리 기록 컬럼</th></tr>
      ${dec.inputs.map((i) => `<tr><td>입력 <span class="mono">${esc(i)}</span></td><td>${colSel('inputs', i, (a.inputs || {})[i])}</td></tr>`).join('')}
      ${dec.outputs.map((o) => `<tr><td>결과 <span class="mono">${esc(o)}</span></td><td>${colSel('expect', o, (a.expect || {})[o])}</td></tr>`).join('')}</table>` : '';
    return `<div class="card" style="margin-top:16px"><div class="ch">흐름 설정<div class="right"><button class="btn sm primary" data-act="flowsave">저장</button></div></div><div class="cb drules">
      <div class="sec">사용할 단계</div><div class="chips">${stages}</div>
      <div class="sec">통과 조건</div><div class="rgrid two">${conds}</div>
      <div class="sec">판정 일치율</div><div class="rgrid two">
        <label class="field"><span>결정표</span><select data-in="fagree" data-kind="decision"><option value="">사용 안 함</option>${f.decisions.map((d) => `<option value="${esc(d.name)}"${d.name === a.decision ? ' selected' : ''}>${esc(d.label)}</option>`).join('')}</select></label>
        <label class="field"><span>처리 기록 질의</span><select data-in="fagree" data-kind="query"><option value="">-</option>${f.queries.map((x) => `<option value="${esc(x.name)}"${x.name === a.query ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></label></div>
      ${maps}<div class="hint" style="margin-top:10px">처리 기록 질의는 한 건이 한 행입니다. 결정표 입력마다 그때 값을 담은 컬럼을, 결과마다 실제 처리 결과 컬럼을 지정합니다. 변경 요청은 저장한 조건으로 검토합니다.${(f.raised || []).length ? ' 검증 기준 모듈이 더 높은 조건을 정한 항목은 모듈 조건을 적용하고, 모듈을 해제하면 저장한 조건으로 돌아갑니다.' : ''}</div></div></div>`;
  }

  // ---- data in: files or a database, drafted step by step, reviewed, plugged in ------------------------------------

  async function loadFiles() {
    S.files = { busy: true };
    try { S.files = await api('files'); } catch (e) { S.files = { error: e.message }; }
    if (!S.dr.rules && S.files.rules) S.dr.rules = JSON.parse(JSON.stringify(S.files.rules));
    if (S.tab === 'data') render();
  }

  async function uploadFiles(list) {
    const files = [...list];
    if (!files.length) return;
    S.dr.busy = true;
    if (S.tab === 'data') render();
    const lim = (S.files && S.files.limits) || {};
    for (const f of files) {
      if (lim.file_bytes && f.size > lim.file_bytes) { fail(new Error(`${f.name}: 파일 크기가 ${bytes(lim.file_bytes)} 한도를 초과해 업로드하지 못했습니다. 파일을 나누어 다시 업로드해 주세요.`)); continue; }
      try {
        const r = await fetch('/api/upload?name=' + encodeURIComponent(f.name), { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-XDS-Request': '1' }, body: f });
        let j = {};
        try { j = await r.json(); } catch (_) { /* empty body */ }
        if (!r.ok) throw new Error(j.error || `서버 오류로 파일을 업로드하지 못했습니다. 잠시 후 다시 시도해 주세요. (${r.status})`);
        S.files = j;
      } catch (e) { fail(e); }
    }
    S.dr.busy = false;
    S.st = await api('state');
    render();
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
  const RULE_FLAG = [['infer_links', '이름과 값으로 관계 추론'], ['link_tables', '중간 테이블을 다대다 관계로 변환'], ['row_keys', '키 없는 테이블에 행 번호 추가'],
    ['states', '상태 컬럼을 상태 전이로'], ['roles', '역할 생성'], ['questions', '검증 질문 생성']];
  const RULE_QUERY = [['list', '객체 목록'], ['count_by', '관계별 집계'], ['values', '허용값별 집계']];
  const RULE_LIST = [['title_hints', '표시 이름 컬럼'], ['parent_hints', '상위 관계 접두어'], ['key_suffixes', '키 컬럼 접미어'], ['generic_keys', '공용 키 이름'],
    ['state_hints', '상태 컬럼 이름'], ['person_hints', '본인 조회 기준 테이블 이름'], ['table_prefixes', '객체 이름에서 뺄 테이블 접두어']];
  const TYPES = ['string', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'enum'];

  function refreshDraft() {
    const box = $('#draft');
    if (box) { box.innerHTML = draftBody(); mountDraftGraph(); }
  }

  function startDraft() {
    clearInterval(S.dr.timer);
    Object.assign(S.dr, { step: 0, view: 'read', sel: null, ed: NEW_EDITS(), rev: null, graph: null, add: { source: '', property: '', target: '', label: '' } });
    S.dpos = {};
    S.dr.timer = setInterval(() => {
      const p = S.files && S.files.pending;
      if (!p) { clearInterval(S.dr.timer); S.dr.timer = 0; return; }
      S.dr.step = Math.min(S.dr.step + 1, p.steps.length);
      if (S.dr.step >= p.steps.length) { clearInterval(S.dr.timer); S.dr.timer = 0; }
      S.dr.view = p.steps[Math.min(S.dr.step, p.steps.length - 1)].id;
      if (S.tab === 'data') refreshDraft();
    }, 900);
    requestAnimationFrame(() => { const box = $('#draft'); if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
  }

  // ---- edits: kept on the page, checked on the server after each change ----

  function toEdits() {
    const e = S.dr.ed;
    return { drop: Object.keys(e.drop).filter((k) => e.drop[k]), labels: e.labels, keys: e.keys, types: e.types,
      values: e.values, cardinality: e.card, add_links: e.add };
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
    const bar = $('#dcheck');
    if (bar) bar.innerHTML = checkBar();
    const detail = $('#ddetail');
    if (detail && (S.dr.view === 'yaml' || S.dr.view === 'queries')) detail.innerHTML = stepDetail(S.files.pending, currentStep());
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
    mountGraph($('#dgraph'), S.dr.graph || p.graph, { pos: S.dpos, sel: () => S.dr.sel, shown: draftShown,
      label: (n) => S.dr.ed.labels['object:' + n.id] || n.label,
      pick: (id) => { S.dr.sel = S.dr.sel === id ? null : id; S.dr.view = 'properties'; S.dr.step = Math.max(S.dr.step, stepIndex('properties') + 1); refreshDraft(); } });
  }

  function stepCount(st) {
    const n = st.items.length;
    if (st.id === 'read') return `테이블 ${n} · ${show(st.items.reduce((a, x) => a + x.rows, 0))}행`;
    if (st.id === 'objects') return `객체 ${n}${st.skipped.length ? ` · 제외 ${st.skipped.length}` : ''}`;
    if (st.id === 'properties') return `속성 ${n} · 허용값 ${st.items.filter((x) => x.type === 'enum').length}`;
    if (st.id === 'links') return `관계 ${n}`;
    if (st.id === 'queries') return `질의 ${n}`;
    if (st.id === 'rules') {
      const k = (kind) => st.items.filter((x) => x.kind === kind).length;
      return `상태 ${k('states')} · 역할 ${k('role')} · 질문 ${k('question')}${k('decision') ? ` · 판정 ${k('decision')}` : ''}`;
    }
    return `연결 ${n}`;
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

  const currentStep = () => {
    const p = S.files.pending;
    return S.dr.view === 'yaml' ? { id: 'yaml' } : p.steps.find((x) => x.id === S.dr.view) || p.steps[0];
  };

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

  function stepDetail(p, st) {
    const o = draftContext(p);
    const e = S.dr.ed;
    if (st.id === 'read') {
      return `<table class="tight"><tr><th>파일</th><th>테이블</th><th>행</th><th>컬럼</th><th></th></tr>${st.items.map((x) => `<tr><td>${esc(x.source || '-')}</td><td class="mono">${esc(x.table)}</td><td class="num">${show(x.rows)}</td><td class="num">${x.columns}</td>
        <td class="muted" style="font-size:12px">${x.truncated ? '행 한도까지 읽음 · ' : ''}${x.row_key ? `키 컬럼 없음 · <span class="mono">${esc(x.row_key)}</span> 추가` : ''}</td></tr>`).join('')}</table>`;
    }
    if (st.id === 'objects') {
      const rows = st.items.map((x) => {
        const id = x.element.split(':')[1];
        const on = !e.drop[x.element];
        return `<tr class="${on ? '' : 'off'}"><td style="width:28px"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''} aria-label="${esc(x.label)} 포함"></td>
          <td>${labelInput(x.element, x.label)}<div class="muted mono">${esc(id)}</div></td>
          <td class="mono">${esc(x.table)}</td>
          <td><select class="inline" data-in="dkey" data-obj="${esc(id)}">${options(o.propsOf(id).map((n) => [n, n]), o.keyOf(id))}</select></td>
          <td class="muted" style="font-size:12px">${e.keys[id] && e.keys[id] !== x.key ? '직접 지정' : why(o, 'object', x)}</td></tr>`;
      }).join('');
      const left = (k, text) => { const xs = st.skipped.filter((x) => x.why === k); return xs.length ? `<div class="hint" style="margin-top:10px">${text}: ${xs.map((x) => esc(x.table)).join(', ')}</div>` : ''; };
      const skipped = left('no_key', '키 컬럼이 없어 제외된 테이블');
      return `<table class="tight"><tr><th></th><th>이름</th><th>테이블</th><th>키</th><th>근거</th></tr>${rows}</table>${skipped}`;
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
          <td class="muted" style="font-size:12px">${isKey ? '키' : (e.types[ref] && e.types[ref] !== x.type ? '직접 지정' : why(o, 'property', x))}</td></tr>`;
      }).join('');
      const filter = S.dr.sel ? `<div class="hint" style="margin-bottom:8px">${esc(o.labelOf(S.dr.sel))} 속성만 표시합니다. <button class="chip sm" data-act="dsel">전체 보기</button></div>` : '';
      return `${filter}<table class="tight"><tr><th></th><th>속성</th><th>원천 컬럼</th><th>타입</th><th>근거</th></tr>${rows}</table>`;
    }
    if (st.id === 'links') {
      const card = (cur, name, fixed) => `<select class="inline" data-in="dcard" data-link="${esc(name)}"${fixed ? ' disabled' : ''}>${options(Object.entries(CARD), cur)}</select>`;
      const rows = st.items.map((x) => {
        const name = x.element.split(':')[1];
        const on = !e.drop[x.element];
        return `<tr class="${on ? '' : 'off'}"><td style="width:28px"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''} aria-label="${esc(x.label)} 포함"></td>
          <td>${labelInput(x.element, x.label)}<div class="muted">${esc(o.labelOf(x.from))} → ${esc(o.labelOf(x.to))} <span class="mono">${esc(name)}</span></div></td>
          <td>${card(e.card[name] || x.cardinality, name, !!x.via)}</td><td class="muted" style="font-size:12px">${why(o, 'link', x)}</td></tr>`;
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
        <div class="hint" style="margin-top:6px">선택한 속성 값을 대상 객체의 키와 연결합니다.</div>`;
      const table = rows || added ? `<table class="tight"><tr><th></th><th>관계</th><th>카디널리티</th><th>근거</th></tr>${rows}${added}</table>` : '<div class="empty">추론된 관계가 없습니다.</div>';
      return table + form;
    }
    if (st.id === 'queries') {
      const items = (S.dr.rev && S.dr.rev.query_items) || st.items;
      if (!items.length) return '<div class="empty">생성할 질의가 없습니다. 생성 설정의 생성 질의를 확인하세요.</div>';
      return `<div class="qpick">${items.map((x) => {
        const on = !e.drop[x.element];
        return `<label class="${on ? '' : 'off'}"><input type="checkbox" data-in="dkeep" data-el="${esc(x.element)}"${on ? ' checked' : ''}><span>${esc(x.label)}</span><span class="muted mono">${esc(x.element.split(':')[1])}</span></label>`;
      }).join('')}</div><div class="hint" style="margin-top:10px">스튜디오에 적용한 뒤 질의 화면에서 실행할 수 있습니다.</div>`;
    }
    if (st.id === 'rules') return rulesDetail(p, st, o);
    if (st.id === 'yaml') {
      const mods = (S.dr.rev && S.dr.rev.modules) || p.modules;
      return mods.map((m) => `<div class="sec">${esc(m.label)} <span class="muted mono">${esc(m.name)}</span></div><pre class="code" style="max-height:360px;overflow:auto">${esc(m.yaml)}</pre>`).join('');
    }
    return `<table class="tight"><tr><th>항목</th><th>원천</th></tr>${st.items.map((x) => `<tr><td>${element(x.element)}</td><td class="mono">${esc(x.table || x.column || '')}${x.table && x.column ? ' · ' + esc(x.column) : ''}${x.columns ? ` · 컬럼 ${x.columns}` : ''}</td></tr>`).join('')}</table>`;
  }

  function rulesDetail(p, st, o) {
    const by = (kind) => st.items.filter((x) => x.kind === kind);
    const sm = by('states').map((s) => `<tr><td><b>${esc(o.labelOf(s.object))}</b><div class="muted mono">${esc(s.property)}</div></td>
      <td>${s.transitions.length ? s.transitions.map((t) => `<span class="chip sm">${esc(t.from)} → ${esc(t.to)} · ${t.seen}회</span>`).join(' ') : `<span class="muted">${esc(s.states.join(' · '))}</span>`}</td>
      <td class="muted" style="font-size:12px">${s.why === 'history' ? `이력 테이블 <span class="mono">${esc(s.history)}</span> 의 시간 순서${s.initial ? ` · 초기 상태 ${esc(s.initial)}` : ''}` : '허용값만 확인 · 전이는 직접 지정'}</td></tr>`).join('');
    const acts = by('action').map((a) => `<span class="chip">${esc(a.label)}</span>`).join('');
    const roles = by('role').map((r) => `<tr><td><b>${esc(r.label)}</b></td><td class="muted" style="font-size:12px">조회 ${esc(r.read.join(', '))}${r.filters.length ? ` · 본인 행만: ${esc(r.filters.join(', '))}` : ''}</td></tr>`).join('');
    const qs = by('question').map((q) => `<div>${esc(q.text)} <span class="muted">${showObj(q.expect)}</span></div>`).join('');
    const decs = by('decision').map((x) => {
      const r = x.report || {};
      return `<tr><td><b>${esc(x.label)}</b><div class="muted mono">${esc(x.element.split(':')[1])}</div></td><td class="muted" style="font-size:12px">규칙 ${x.rules}개 · 지난 ${r.cases}건 · 맞춤 ${pct(r.accuracy)} · 교차 검증 ${r.cross_validated === null || r.cross_validated === undefined ? '건수 부족' : pct(r.cross_validated)}</td>
        <td><button class="chip sm" data-act="dinddel" data-name="${esc(x.element.split(':')[1])}">삭제</button></td></tr>`;
    }).join('');
    const props = p.steps.find((x) => x.id === 'properties').items.filter((x) => !S.dr.ed.drop[x.element]);
    const outs = props.filter((x) => ['enum', 'boolean', 'string'].includes(S.dr.ed.types[x.element.slice(9)] || x.type) && !x.key);
    const t = S.ind.target && outs.some((x) => x.element === S.ind.target) ? S.ind.target : '';
    let inputs = '';
    if (t) {
      const obj = t.slice(9).split('.')[0];
      const mine = props.filter((x) => x.object === obj && x.element !== t && !x.key).map((x) => [x.element.slice(9).split('.').pop(), `${x.label}`]);
      const links = p.steps.find((x) => x.id === 'links').items.filter((l) => l.from === obj && !S.dr.ed.drop[l.element] && ['many_to_one', 'one_to_one'].includes(S.dr.ed.card[l.element.split(':')[1]] || l.cardinality));
      const far = links.flatMap((l) => props.filter((x) => x.object === l.to && !x.key).map((x) => [`${l.element.split(':')[1]}.${x.element.slice(9).split('.').pop()}`, `${o.labelOf(l.to)} · ${x.label}`]));
      inputs = `<div class="label" style="margin:8px 0 4px">입력</div><div class="qpick">${[...mine, ...far].map(([v, l]) => `<label><input type="checkbox" data-in="dindin" data-v="${esc(v)}"${S.ind.inputs[v] ? ' checked' : ''}><span>${esc(l)}</span><span class="muted mono">${esc(v)}</span></label>`).join('')}</div>`;
    }
    const form = `<div class="sec">지난 처리 결과로 판정 표 만들기</div>
      <div class="field"><label>결과 컬럼</label><select data-in="dindt"><option value="">선택</option>${outs.map((x) => `<option value="${esc(x.element)}"${x.element === t ? ' selected' : ''}>${esc(o.labelOf(x.object))} · ${esc(x.label)}</option>`).join('')}</select></div>
      ${inputs}<button class="btn sm" data-act="dinduce" style="margin-top:8px"${t && Object.values(S.ind.inputs).some(Boolean) ? '' : ' disabled'}>판정 표 만들기</button>
      <div class="hint" style="margin-top:6px">결과 컬럼은 실제 처리 결과(허용값 또는 참 · 거짓)입니다. 규칙마다 지난 몇 건 중 몇 건이 맞는지 표시하고, 교차 검증으로 처음 보는 건의 정확도를 잽니다.</div>`;
    return `<div class="sec">상태 전이</div>${sm ? `<table class="tight"><tr><th>객체</th><th>전이</th><th>근거</th></tr>${sm}</table>` : '<div class="muted" style="font-size:12.5px">상태 컬럼이 없습니다. 생성 설정의 상태 컬럼 이름을 확인하세요.</div>'}
      ${acts ? `<div class="sec">상태 변경 액션</div><div class="chips">${acts}</div>` : ''}
      <div class="sec">역할</div>${roles ? `<table class="tight">${roles}</table>` : '<div class="muted" style="font-size:12.5px">역할을 만들지 않았습니다.</div>'}
      <div class="sec">검증 질문 · 지금 데이터 기준</div><div class="loglist">${qs || '<div class="muted">없음</div>'}</div>
      ${decs ? `<div class="sec">판정 표</div><table class="tight">${decs}</table>` : ''}${form}`;
  }

  async function mapLoad() {
    if (S.map.standards) return;
    try { S.map.standards = (await api('standards')).standards; } catch (_) { S.map.standards = []; }
    if (S.tab === 'data') render();
  }

  function mappingCard() {
    const m = S.map;
    if (!m.standards) { mapLoad(); return ''; }
    if (!m.standards.length) return '';
    const picks = m.standards.map((s) => `<label class="tick"><input type="checkbox" data-in="mpick" data-v="${esc(s.name)}"${m.picked.includes(s.name) ? ' checked' : ''}>${esc(s.label)} <span class="muted" style="font-size:11.5px">${esc(s.kind_label)}</span></label>`).join('');
    let body = '';
    const sg = m.sug;
    if (sg && sg.ok) {
      const tables = sg.tables.map((x) => x.table);
      const rows = sg.objects.map((x) => {
        const table = m.edits.objects[x.object] === undefined ? x.table : m.edits.objects[x.object];
        const here = sg.tables.find((y) => y.table === table) || { columns: [], names: {} };
        const colsOf = here.columns;
        const cols = x.columns.map((c) => {
          const cur = m.edits.columns[`${x.object}.${c.property}`] === undefined ? c.column : m.edits.columns[`${x.object}.${c.property}`];
          return `<div class="mrow"><span>${esc(c.label)} <span class="muted mono">${esc(c.property)}</span></span><select class="inline" data-in="mcol" data-ref="${esc(x.object + '.' + c.property)}"><option value="">없음</option>${colsOf.map((n) => `<option value="${esc(n)}"${n === cur ? ' selected' : ''}>${esc(here.names[n] || n)}</option>`).join('')}</select><span class="muted" style="font-size:11.5px">${esc(c.why)}</span></div>`;
        }).join('');
        return `<tr class="${table ? '' : 'off'}"><td><b>${esc(x.label)}</b><div class="muted mono">${esc(x.object)}</div></td>
          <td><select class="inline" data-in="mobj" data-obj="${esc(x.object)}"><option value="">제외</option>${tables.map((n) => `<option value="${esc(n)}"${n === table ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select><div class="muted" style="font-size:11.5px;margin-top:3px">점수 ${pct(x.score)} · ${esc(x.why)}</div></td>
          <td>${cols}${x.missing.length ? `<div class="muted" style="font-size:11.5px;margin-top:4px">테이블에 없는 속성(제외): ${esc(x.missing.map((y) => y.label).join(', '))}</div>` : ''}${x.extra.length ? `<div class="muted" style="font-size:11.5px">표준에 없는 컬럼: ${esc(x.extra.join(', '))}</div>` : ''}</td></tr>`;
      }).join('');
      const links = Object.entries(sg.links).map(([k, v]) => `<span class="chip sm">${esc(k)} · ${esc(v.why)}</span>`).join('');
      body = `<table class="tight" style="margin-top:12px"><tr><th>표준 객체</th><th>테이블</th><th>속성 ↔ 컬럼</th></tr>${rows}</table>
        ${links ? `<div class="sec">관계</div><div class="chips">${links}</div>` : ''}
        ${sg.unmatched_tables.length ? `<div class="hint" style="margin-top:8px">표준에 대응하지 않은 테이블: ${esc(sg.unmatched_tables.join(', '))}</div>` : ''}
        ${sg.unbound_objects.length ? `<div class="hint">연결할 테이블이 없는 표준 객체: ${esc(sg.unbound_objects.map((y) => y.label).join(', '))}. 이 객체를 쓰는 질의는 제외됩니다.</div>` : ''}
        <div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" data-act="mapapply"${m.busy ? ' disabled' : ''}>표준에 연결해 적용</button></div>`;
    } else if (sg && !sg.ok) body = `<div class="banner no" style="margin-top:10px"><div class="why">${esc(sg.error)}</div></div>`;
    return `<div class="card"><div class="ch">표준에 연결<div class="right muted" style="font-weight:600;font-size:12px">새 객체 대신 표준 정의에 바인딩</div></div><div class="cb">
      <div class="chips">${picks}</div><button class="btn sm" data-act="mapsuggest" style="margin-top:10px"${m.picked.length && !m.busy ? '' : ' disabled'}>${m.busy ? '<span class="spin"></span>처리 중' : '연결 제안'}</button>
      <div class="hint" style="margin-top:6px">테이블과 컬럼을 표준 객체와 속성에 이름, 라벨, 타입, 허용값, 키로 대응시킵니다. 제안을 확인하고 고친 뒤 적용하세요.</div>${body}</div></div>`;
  }

  function checkBar() {
    const p = S.files.pending;
    const r = S.dr.rev;
    const done = S.dr.step >= p.steps.length;
    const issues = r && r.issues ? r.issues : [];
    const c = (r && r.counts) || { objects: p.steps[1].items.length, links: p.steps[3].items.length, properties: p.steps[2].items.length, queries: p.steps[4].items.length };
    const list = issues.length ? `<div class="banner no" style="margin:0 0 12px"><span class="ic x" style="width:24px;height:24px">!</span><div><div class="big" style="font-size:14px">정의 검사 오류 ${issues.length}건</div><div class="loglist">${issues.slice(0, 8).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div></div>` : '';
    return `${list}<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <div class="chips" style="flex:1;min-width:240px"><span class="chip">객체 ${c.objects}</span><span class="chip">관계 ${c.links}</span><span class="chip">속성 ${c.properties}</span><span class="chip">질의 ${c.queries}</span>${issues.length ? '' : '<span class="chip ok">✓ 정의 검사 통과</span>'}</div>
      <span class="muted" style="font-size:12.5px">적용하면 현재 스튜디오가 이 정의와 데이터로 교체됩니다.</span>
      <button class="btn primary" data-act="dapply"${done && c.objects && !issues.length && !S.dr.busy ? '' : ' disabled'}>스튜디오에 적용</button></div>`;
  }

  function draftBody() {
    const p = S.files.pending;
    const done = S.dr.step >= p.steps.length;
    const steps = p.steps.map((st, i) => {
      const state = i < S.dr.step ? 'done' : (i === S.dr.step ? 'now' : 'wait');
      return `<button class="dstep ${state}${S.dr.view === st.id ? ' on' : ''}" data-act="dview" data-view="${st.id}"${state === 'wait' ? ' disabled' : ''}>
        <span class="ic ${state === 'done' ? 'y' : ''}">${state === 'done' ? '✓' : i + 1}</span><span><b>${STEP[st.id][0]}</b><span class="muted">${state === 'wait' ? '' : stepCount(st)}</span></span></button>`;
    }).join('') + `<button class="dstep ${done ? 'done' : 'wait'}${S.dr.view === 'yaml' ? ' on' : ''}" data-act="dview" data-view="yaml"${done ? '' : ' disabled'}><span class="ic">{ }</span><span><b>정의 파일</b><span class="muted">${done ? `모듈 ${p.modules.length}개` : ''}</span></span></button>`;
    const cur = currentStep();
    const curTitle = cur.id === 'yaml' ? ['정의 파일', '정의 모듈, 바인딩 모듈'] : STEP[cur.id];
    return `<div class="grid" style="grid-template-columns:240px minmax(0,1fr);align-items:start">
      <div class="card"><div class="ch">생성 단계</div><div class="cb dsteps">${steps}</div></div>
      <div class="card"><div class="ch">${esc(p.label)} 초안<div class="right legend"><span><i class="fill"></i>객체</span><span>→ 관계</span></div></div>
        <div class="cb" style="padding:0"><div class="graph-wrap" style="height:360px"><canvas id="dgraph"></canvas><div class="tip">${done ? '노드를 선택하면 속성이 표시됩니다' : esc(STEP[p.steps[Math.min(S.dr.step, p.steps.length - 1)].id][1])}</div></div></div></div>
    </div>
    <div class="card"><div class="ch">${curTitle[0]}<div class="right muted" style="font-weight:600;font-size:12px">${curTitle[1]}</div></div><div class="cb scroll" id="ddetail" style="max-height:520px">${stepDetail(p, cur)}</div></div>
    <div class="card"><div class="cb" id="dcheck">${checkBar()}</div></div>`;
  }

  function rulesCard(f) {
    const r = S.dr.rules || f.rules;
    const num = RULE_NUM.map(([k, l]) => `<label class="field"><span>${l}</span><input type="number" min="${k === 'enum_repeat' ? 1 : 0}" step="${k === 'enum_repeat' ? 0.5 : 1}" data-in="drule" data-k="${k}" value="${esc(r[k])}"></label>`).join('');
    const flags = RULE_FLAG.map(([k, l]) => `<label class="tick"><input type="checkbox" data-in="drule" data-k="${k}"${r[k] ? ' checked' : ''}>${l}</label>`).join('');
    const queries = RULE_QUERY.map(([k, l]) => `<label class="tick"><input type="checkbox" data-in="drule" data-k="queries" data-v="${k}"${r.queries.includes(k) ? ' checked' : ''}>${l}</label>`).join('');
    const lists = RULE_LIST.map(([k, l]) => `<label class="field"><span>${l}</span><input type="text" data-in="drule" data-k="${k}" value="${esc(r[k].join(', '))}"></label>`).join('');
    const by = (f.rules_by || []).length ? `<div class="hint" style="margin-bottom:8px">구축 규칙 모듈 ${esc(f.rules_by.join(', '))}의 값을 기본값으로 사용합니다.</div>` : '';
    return `<div class="card"><div class="ch">생성 설정<div class="right"><button class="btn sm ghost" data-act="drules-reset">기본값</button></div></div><div class="cb drules">
      ${by}<div class="sec">허용값</div><div class="rgrid">${num}</div>
      <div class="sec">관계 · 키 · 규칙</div>${flags}
      <div class="sec">생성 질의</div><div class="chips">${queries}</div>
      <div class="sec">이름 규칙</div><div class="rgrid two">${lists}</div>
      ${f.pending ? '<div class="hint" style="margin-top:12px">설정을 바꾼 뒤 [초안 생성]을 다시 선택하세요.</div>' : ''}</div></div>`;
  }

  function viewData() {
    const head = `<div class="head"><div><h1>데이터 연결</h1><div class="sub">파일 업로드 또는 DB 연결로 온톨로지 초안을 생성합니다</div></div></div>`;
    const f = S.files;
    if (!f || f.busy) return head + '<div class="empty"><span class="spin"></span>불러오는 중입니다.</div>';
    if (f.error) return head + `<div class="banner no"><div class="why">${esc(f.error)}</div></div>`;
    const lim = f.limits;
    const list = f.files.length ? f.files.map((x) => `<div class="fileitem"><div style="flex:1;min-width:0"><b>${esc(x.source)}</b>
        ${x.tables.map((t) => `<div class="muted" style="font-size:12px"><label class="tick inline-tick"><input type="checkbox" data-in="dtable" data-t="${esc(t.name)}"${S.dr.tables[t.name] === false ? '' : ' checked'}>${x.tables.length > 1 ? esc(t.sheet) + ' · ' : ''}테이블 <span class="mono">${esc(t.name)}</span> · ${show(t.rows)}행 · 컬럼 ${t.columns.length}개${t.truncated ? ' · 행 한도까지 읽음' : ''}</label>
          <div class="chips" style="margin-top:4px">${t.columns.slice(0, 10).map((c) => `<span class="chip sm">${esc(c)}</span>`).join('')}${t.columns.length > 10 ? `<span class="chip sm">외 ${t.columns.length - 10}개</span>` : ''}</div></div>`).join('')}</div>
        <button class="btn sm ghost" data-act="fremove" data-name="${esc(x.source)}" aria-label="${esc(x.source)} 삭제">삭제</button></div>`).join('')
      : (f.definitions.length ? '' : '<div class="muted" style="font-size:12.5px">업로드한 파일이 없습니다.</div>');
    const defFacts = (x) => [['테이블', x.tables.length], ['컬럼', x.columns], ['참조', x.references], ['코드 그룹', x.codes], ['코드값', x.code_values], ['용어', x.terms], ['메시지', x.messages], ['문서', x.documents]]
      .filter(([, n]) => n).map(([k, n]) => `${k} ${show(n)}`).join(' · ');
    const docKind = { policy: '정책', screen: '화면', other: '문서' };
    const defs = f.definitions.map((x) => `<div class="fileitem"><div style="flex:1;min-width:0"><b>${esc(x.source)}</b> <span class="chip sm b">${x.tables.length || x.groups.length || x.terms || x.messages ? '정의서' : '문서'}</span>
        <div class="muted" style="font-size:12px;margin:3px 0">${defFacts(x)}</div>
        ${x.tables.length ? `<div class="scroll deflist">${x.tables.map((t) => `<label class="tick inline-tick" style="display:flex"><input type="checkbox" data-in="dtable" data-t="${esc(t.name)}"${S.dr.tables[t.name] === false ? '' : ' checked'}><span class="mono">${esc(t.name)}</span>&nbsp;<span class="muted">${esc(t.label)} · 컬럼 ${t.columns}${t.key.length > 1 ? ' · 복합 키' : (t.key.length ? '' : ' · 키 없음')}</span></label>`).join('')}</div>
          <div style="display:flex;gap:6px;margin-top:6px"><button class="btn sm ghost" data-act="dtall" data-src="${esc(x.source)}" data-on="1">전체 선택</button><button class="btn sm ghost" data-act="dtall" data-src="${esc(x.source)}" data-on="0">전체 해제</button></div>` : ''}
        ${x.groups.length ? `<div class="chips" style="margin-top:6px">${x.groups.slice(0, 12).map((g) => `<span class="chip sm">${esc(g.name)} ${esc(g.label)} · ${g.values}</span>`).join('')}${x.groups.length > 12 ? `<span class="chip sm">외 ${x.groups.length - 12}개</span>` : ''}</div>` : ''}
        ${x.document_list.length ? `<div class="chips" style="margin-top:6px">${x.document_list.slice(0, 12).map((d) => `<span class="chip sm">${esc(d.name)} · ${docKind[d.kind] || '문서'} · 섹션 ${show(d.sections)}</span>`).join('')}</div>` : ''}</div>
        <button class="btn sm ghost" data-act="fremove" data-name="${esc(x.source)}" aria-label="${esc(x.source)} 삭제">삭제</button></div>`).join('');
    const defHint = f.definitions.length ? `<div class="hint" style="margin-top:10px">${f.files.length ? '정의서의 테이블 한글명, 컬럼 한글명, 코드값과 코드명으로 초안의 이름과 허용값을 채웁니다.' : '데이터 파일 없이 정의서만 있으면 행 없이 스키마(키, 참조, 코드값)로 초안을 생성합니다.'}</div>` : '';
    const connect = f.connect ? `<div class="sec">데이터베이스 연결</div><div style="display:flex;gap:8px"><input type="text" data-in="dsn" value="${esc(S.dr.dsn)}" placeholder="postgresql://, mysql://, oracle:// 주소 또는 SQLite 파일 경로" style="flex:1">
        <button class="btn" data-act="connect"${S.dr.busy ? ' disabled' : ''}>연결</button></div><div class="hint" style="margin-top:6px">데이터는 원본 DB에 그대로 유지됩니다.</div>`
      : '<div class="hint" style="margin-top:12px">공개 데모에서는 DB 연결을 지원하지 않습니다. 설치형에서 PostgreSQL, MySQL, Oracle, SQLite를 연결할 수 있습니다.</div>';
    const samples = f.samples.length ? `<button class="btn" data-act="fsample"${S.dr.busy ? ' disabled' : ''}>샘플 데이터 불러오기</button>` : '';
    const left = `<div class="card"><div class="ch">데이터 가져오기</div><div class="cb">
      <label class="drop" data-drop="1"><input type="file" id="fileinput" multiple accept=".csv,.tsv,.txt,.xlsx,.json,.sql,.ddl,.dbml,.pdm,.mwb,.docx,.pptx,.hwpx,.html,.htm,.md,.pdf" hidden>
        <b>CSV, Excel 파일을 끌어 놓거나 클릭해 선택하세요</b><span class="muted">테이블 정의서, 코드 정의서, 용어 사전, 메시지 정의서, SQL, ERD, 문서 파일도 업로드할 수 있습니다.</span><span class="muted">최대 ${lim.files}개 · 파일당 ${bytes(lim.file_bytes)} · 테이블당 ${show(lim.rows)}행. 업로드한 파일은 세션 종료 시 삭제됩니다. 개인정보가 포함된 파일은 업로드하지 마세요.</span></label>
      <div style="display:flex;gap:8px;margin:12px 0;flex-wrap:wrap">${samples}</div>
      ${list}${defs}${defHint}${connect}
      <div style="display:flex;gap:8px;margin-top:14px;align-items:center"><input type="text" data-in="dname" value="${esc(S.dr.label)}" placeholder="온톨로지 이름" style="flex:1;min-width:0">
        <button class="btn primary" data-act="draft"${(f.files.length || f.definitions.some((x) => x.tables.length)) && !S.dr.busy ? '' : ' disabled'}>${S.dr.busy ? '<span class="spin"></span>처리 중' : '초안 생성'}</button></div></div></div>`;
    const draft = f.pending ? `<div id="draft" style="display:flex;flex-direction:column;gap:16px">${draftBody()}</div>${mappingCard()}` : '';
    return `${head}<div class="grid" style="grid-template-columns:minmax(0,1.3fr) minmax(300px,1fr);align-items:start">${left}${rulesCard(f)}</div>${draft}`;
  }

  // ---- management: data sources, objects, properties, relations, questions ---------------------------------------
  // Every edit lands in one overlay module ("관리 변경") over the standard modules, and reaches the other screens only
  // once it is filed as a change request and approved.

  const MG_TABS = ['sources', 'objects', 'props', 'links'];
  const OP_WORD = { add_object: '객체 추가', update_object: '객체 변경', delete_object: '객체 제외', add_property: '속성 추가',
    update_property: '속성 변경', delete_property: '속성 제외', add_link: '관계 추가', update_link: '관계 변경', delete_link: '관계 제외',
    add_question: '검증 질문 추가', delete_question: '검증 질문 제외' };
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
    if (MG_TABS.includes(S.tab) || S.tab === 'check') render();
  }

  async function mgEdit(op, args, done) {
    S.mg.busy = true;
    try {
      const r = await api('manage/edit', { op, args });
      S.mg.st = r;
      S.mg.form = null;
      S.mg.review = null;
      const out = r.edit.took_out.length;
      toast(`${done} ${out ? `함께 빠진 항목 ${out}개는 대기 중인 변경에서 확인하세요.` : '변경 요청 후 승인되면 모든 화면에 반영됩니다.'}`);
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
    const edits = w.edits.map((e) => `<div><b>${esc(OP_WORD[e.op] || e.op)}</b> ${element(e.target)}${e.took_out.length
      ? `<div class="chips" style="margin-top:5px"><span class="muted" style="font-size:11.5px">함께 제외</span>${e.took_out.map(element).join('')}</div>` : ''}</div>`).join('');
    const issues = w.issues.length ? `<div class="banner no" style="margin-top:10px"><div class="loglist">${w.issues.slice(0, 6).map((x) => `<div class="mono">${esc(x)}</div>`).join('')}</div></div>` : '';
    const body = S.mg.open ? `<div class="cb" style="border-top:1px solid var(--line)">
        ${edits ? `<div class="loglist">${edits}</div>` : '<div class="muted" style="font-size:12.5px">이전 세션에서 이어진 변경입니다. 정의 파일에서 확인하세요.</div>'}${issues}
        <div class="sec" style="margin-top:12px">정의 파일 · ${esc(w.label)}</div><pre class="code" style="max-height:260px;overflow:auto">${esc(w.yaml)}</pre></div>` : '';
    const review = S.mg.review ? `<div class="cb" style="border-top:1px solid var(--line)"><div class="banner no" style="margin:0 0 4px"><span class="ic x" style="width:24px;height:24px">!</span><div class="why">사본 스튜디오에서 흐름 통과 조건을 충족하지 못해 적용하지 않았습니다. 아래 항목을 고친 뒤 다시 [변경 요청]을 선택하세요.</div></div>${changeReview(S.mg.review)}</div>` : '';
    return `<div class="card mgpend"><div class="ch"><span class="chip warn">대기 중인 변경 ${w.edits.length || ''}</span>
      <span class="muted" style="font-weight:600;font-size:12.5px">추가 ${d.added.length} · 변경 ${d.changed.length} · 제외 ${d.removed.length}</span>
      <div class="right"><button class="btn sm" data-act="mgopen">${S.mg.open ? '접기' : '내용 보기'}</button><button class="btn sm ghost" data-act="mgdiscard"${S.mg.busy ? ' disabled' : ''}>변경 취소</button>
      <button class="btn sm primary" data-act="mgpropose"${S.mg.busy || w.issues.length ? ' disabled' : ''}>변경 요청</button></div></div>${review}${body}
      <div class="cb mgnote">표준 모듈은 그대로 두고 '${esc(w.label)}' 모듈에 확장 · 제외로 기록합니다. [변경 요청]을 선택하면 사본 스튜디오에서 흐름 통과 조건을 검토하고, 승인 후 질의 · 판정 · 검증 화면에 반영됩니다.</div></div>`;
  }

  const ownerChip = (x) => `<span class="chip sm${own(x) ? ' b' : ''}">${esc(x.module_label || x.module || '-')}</span>`;
  const stateChips = (x) => (x.new ? '<span class="chip sm warn">새로 추가</span>' : (x.pending ? '<span class="chip sm warn">변경 대기</span>' : ''));

  // ---- data sources

  function viewSources() {
    const title = '데이터 소스', sub = '연결된 원천 테이블과 테이블별 연결 객체를 확인합니다';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st, s = m.sources.source;
    const head = mgHead(title, sub, '<a class="btn sm" href="#data">데이터 연결</a>');
    if (!s.name) return head + '<div class="hint">원천 DB가 연결되지 않았습니다. [데이터 연결]에서 파일을 업로드하거나 DB를 연결하세요.</div>';
    const tables = s.tables;
    const rows = tables.reduce((a, t) => a + (t.rows || 0), 0);
    const stats = `<div class="stats"><div class="stat"><b>${esc(s.dialect || s.name)}</b><span>원천 · ${esc(s.name)}</span></div>
      <div class="stat"><b>${tables.length}</b><span>테이블</span></div><div class="stat"><b>${tables.length - s.unbound.length}</b><span>사용 테이블</span></div>
      <div class="stat"><b>${s.unbound.length}</b><span>미사용 테이블</span></div><div class="stat"><b>${show(rows)}</b><span>행 합계</span></div>
      <div class="stat"><b>${m.sources.graphs.length}</b><span>그래프 저장소${m.sources.graphs.length ? ' · ' + esc(m.sources.graphs.map((g) => g.language.toUpperCase()).join(', ')) : ''}</span></div></div>`;
    const list = tables.map((t) => `<tr class="${S.mg.table === t.table ? 'sel' : ''}" data-act="mgtable" data-t="${esc(t.table)}" style="cursor:pointer">
        <td class="mono">${esc(t.table)}</td><td class="num">${show(t.rows)}</td><td class="num">${t.columns.length}</td>
        <td class="mono" style="font-size:11.5px">${esc(t.key.join(', ')) || '<span class="muted">-</span>'}</td>
        <td style="font-size:12px">${t.fks.length ? t.fks.map((f) => `<span class="mono">${esc(f.column)}</span> → <span class="mono">${esc(f.table)}</span>`).join('<br>') : '<span class="muted">-</span>'}</td>
        <td>${t.objects.length || t.links.length ? `<div class="chips">${t.objects.map((o) => `<a class="chip sm b" href="#objects" data-act="mgobjgo" data-name="${esc(o)}">${esc(mgLabel(o))}</a>`).join('')}${t.links.map((l) => `<a class="chip sm" href="#links" data-act="mglinkgo" data-name="${esc(l)}">관계 · ${esc(linkLabel(l))}</a>`).join('')}</div>`
          : `<button class="btn sm" data-act="mgobjnew" data-t="${esc(t.table)}">객체로 추가</button>`}</td></tr>`).join('');
    const sel = S.mg.table && mgTable(S.mg.table);
    let detail = '<div class="empty">테이블을 선택하면 컬럼과 연결 속성이 표시됩니다.</div>';
    if (sel) {
      const readers = (c) => m.properties.filter((p) => p.column && p.column.toLowerCase() === c.toLowerCase() && (mgObj(p.object) || {}).table === sel.table);
      detail = `<table class="tight"><tr><th>컬럼</th><th>타입</th><th>연결 속성</th></tr>${sel.columns.map((c) => {
        const fk = sel.fks.find((f) => f.column === c.name);
        const rd = readers(c.name);
        return `<tr><td class="mono">${esc(c.name)}${sel.key.includes(c.name) ? ' <span class="chip sm b">키</span>' : ''}${fk ? `<div class="muted" style="font-size:11px">→ ${esc(fk.table)}.${esc(fk.ref)}</div>` : ''}</td>
          <td class="mono" style="font-size:11.5px">${esc(c.type)}</td><td>${rd.length ? rd.map((p) => `<span class="chip sm">${esc(mgLabel(p.object))} · ${esc(p.label || p.name)}</span>`).join(' ') : '<span class="muted">-</span>'}</td></tr>`;
      }).join('')}</table>`;
    }
    const graphs = m.sources.graphs.length ? `<div class="hint" style="margin-top:12px">그래프 저장소 ${esc(m.sources.graphs.map((g) => `${g.name} (${g.language.toUpperCase()})`).join(', '))}에는 원천 행이 노드와 간선으로 반영됩니다. 관계 그래프는 [온톨로지]에서 확인합니다.</div>` : '';
    return `${head}${stats}${pendingBar()}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(300px,1fr);align-items:start">
      <div class="card"><div class="ch">원천 테이블<div class="right muted" style="font-weight:600;font-size:12px">${esc(s.name)}</div></div><div class="cb scroll" style="padding:0;max-height:620px">
        <table class="tight"><tr><th>테이블</th><th>행</th><th>컬럼</th><th>키</th><th>참조</th><th>연결 객체</th></tr>${list}</table></div></div>
      <div class="card"><div class="ch">${sel ? `<span class="mono">${esc(sel.table)}</span> 컬럼` : '컬럼'}</div><div class="cb scroll" style="max-height:620px${sel ? ';padding:0' : ''}">${detail}</div></div></div>${graphs}`;
  }

  // ---- objects

  function viewObjects() {
    const title = '객체 관리', sub = '객체의 원천 테이블, 키, 상위 객체를 관리합니다';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    const q = S.mg.q.trim().toLowerCase();
    const list = m.objects.filter((o) => !q || `${o.name} ${o.label} ${o.table}`.toLowerCase().includes(q));
    const rows = list.map((o) => `<tr class="${S.mg.sel === o.name ? 'sel' : ''}" data-act="mgobj" data-name="${esc(o.name)}" style="cursor:pointer">
      <td><b>${esc(o.label)}</b><div class="muted mono">${esc(o.name)}</div></td>
      <td>${o.concept ? '<span class="chip sm">개념 · 테이블 없음</span>' : `<span class="mono">${esc(o.table)}</span>`}</td>
      <td class="mono" style="font-size:11.5px">${esc(o.key)}</td><td>${o.parent ? esc(mgLabel(o.parent)) : '<span class="muted">-</span>'}</td>
      <td class="num">${o.properties}</td><td class="num">${o.links || (o.concept ? '0' : '<span class="chip sm bad">0</span>')}</td><td class="num">${o.concept ? '<span class="muted">-</span>' : show(o.rows)}</td>
      <td><div class="chips">${ownerChip(o)}${stateChips(o)}</div></td></tr>`).join('');
    const unlinked = m.unlinked.length ? `<div class="hint">관계가 없는 객체: ${m.unlinked.map((n) => `<b>${esc(mgLabel(n))}</b>`).join(', ')}. 다른 객체로 이어지는 질의를 만들 수 없습니다. [관계 관리]에서 관계를 추가하세요.</div>` : '';
    const head = mgHead(title, sub, `<input type="text" data-in="mgq" value="${esc(S.mg.q)}" placeholder="객체 · 테이블 검색" style="width:200px"><button class="btn sm primary" data-act="mgobjnew">새 객체</button>`);
    return `${head}${pendingBar()}${unlinked}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(320px,1fr);align-items:start">
      <div class="card"><div class="ch">객체 <span class="chip sm">${list.length}</span></div><div class="cb scroll" style="padding:0;max-height:640px">
        <table class="tight"><tr><th>객체</th><th>원천 테이블</th><th>키</th><th>상위</th><th>속성</th><th>관계</th><th>행</th><th>정의</th></tr>${rows}</table></div></div>
      ${objectForm()}</div>`;
  }

  function objectForm() {
    const f = S.mg.form && S.mg.form.kind === 'object' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">객체 정보</div><div class="cb"><div class="empty">객체를 선택하면 라벨, 원천 테이블, 키, 상위 객체를 수정할 수 있습니다. [새 객체]로 객체를 추가합니다.</div></div></div>';
    const v = f.v, o = f.mode === 'edit' ? mgObj(v.name) : null;
    const tables = m.sources.source.tables;
    const tableSel = `<select data-in="mgf" data-f="table" data-re="1"><option value="">개념 · 테이블 없음</option>${tables.map((t) => opt(t.table, `${t.table}${t.objects.length && t.table !== (o || {}).table ? ` · ${t.objects.map(mgLabel).join(', ')}` : ''}`, v.table)).join('')}</select>`;
    const parents = `<select data-in="mgf" data-f="parent"><option value="">없음</option>${m.objects.filter((x) => x.name !== v.name).map((x) => opt(x.name, `${x.label} (${x.name})`, v.parent)).join('')}</select>`;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    if (f.mode === 'new') {
      const t = v.table ? mgTable(v.table) : null;
      const keySel = t ? `<select data-in="mgf" data-f="key">${t.columns.map((c) => opt(c.name, `${c.name} · ${c.type}`, v.key)).join('')}</select>`
        : `<input type="text" data-in="mgf" data-f="key" value="${esc(v.key)}" placeholder="예: coupon_id">`;
      return `<div class="card"><div class="ch">새 객체<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
        ${field('원천 테이블', tableSel, '테이블을 고르면 키와 속성을 컬럼에서 채웁니다.')}
        ${field('영문 이름', `<input type="text" data-in="mgf" data-f="name" value="${esc(v.name)}" placeholder="예: Coupon">`)}
        ${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}" placeholder="예: 쿠폰">`)}
        ${t && t.key.length > 1 ? field('키', `<input type="text" value="${esc(t.key.join(', '))}" class="mono" disabled>`, '복합 키는 여러 컬럼을 하나의 값으로 읽습니다.') : field(t ? '키 컬럼' : '키 속성', keySel)}
        ${t && !t.key.length ? `<div class="hint" style="margin:-4px 0 12px">기본 키가 없는 테이블입니다. 값이 겹치지 않는 컬럼을 키로 고르세요. 값이 겹치면 변경 요청 검토의 DB 대조에서 키 중복 오류로 막힙니다.</div>` : ''}
        ${t && t.links.length ? `<div class="hint" style="margin:-4px 0 12px">관계 ${esc(t.links.map(linkLabel).join(', '))}의 연결 테이블입니다. 객체로 만들 필요가 없으면 [닫기]를 선택하세요.</div>` : ''}
        ${t ? `<label class="tick"><input type="checkbox" data-in="mgf" data-f="cols"${v.cols ? ' checked' : ''}>테이블 컬럼 ${t.columns.length}개를 속성으로 추가</label>` : ''}
        ${field('상위 객체', parents, '상위 객체의 속성과 관계를 물려받습니다.')}
        ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>객체 추가</button></div></div>`;
    }
    const keys = mgProps(v.name).filter((p) => !p.inherited);
    const keyField = own(o) ? `<select data-in="mgf" data-f="key">${keys.map((p) => opt(p.name, `${p.label || p.name} (${p.name})`, v.key)).join('')}</select>`
      : `<input type="text" value="${esc(v.key)}" disabled>`;
    return `<div class="card"><div class="ch">${esc(o.label)} <span class="muted mono" style="font-weight:600">${esc(o.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px">${ownerChip(o)}${stateChips(o)}<span class="chip sm">속성 ${o.properties}</span><span class="chip sm">관계 ${o.links}</span>${o.states ? '<span class="chip sm">상태 전이</span>' : ''}</div>
      ${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}">`)}
      ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}
      ${field('원천 테이블', tableSel)}
      ${field('키', keyField, own(o) ? '' : '키는 정의한 모듈에서만 바꿀 수 있습니다.')}
      ${field('상위 객체', parents)}
      ${own(o) ? '' : `<div class="hint" style="margin-bottom:12px">${esc(o.module_label)} 모듈의 객체입니다. 바꾼 내용은 표준 모듈을 고치지 않고 '관리 변경'에 확장으로 기록됩니다.</div>`}
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button>
        <a class="btn" href="#props" data-act="mgpropsof" data-name="${esc(o.name)}">속성 보기</a><a class="btn" href="#links" data-act="mglinksof" data-name="${esc(o.name)}">관계 보기</a>
        <div class="grow" style="flex:1"></div><button class="btn danger" data-act="mgdel"${S.mg.busy ? ' disabled' : ''}>객체 제외</button></div></div></div>`;
  }

  // ---- properties

  function viewProps() {
    const title = '속성 관리', sub = '객체별 속성의 자료형, 원천 컬럼, 허용값, 필수, 가림을 관리합니다';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    const q = S.mg.q.trim().toLowerCase();
    const all = m.properties.filter((p) => (!S.mg.obj || p.object === S.mg.obj) && (!q || `${p.name} ${p.label} ${p.column} ${p.object}`.toLowerCase().includes(q)));
    const shown = all.slice(0, 400);
    const rows = shown.map((p) => {
      const id = `${p.object}.${p.name}`;
      return `<tr class="${S.mg.sel === id ? 'sel' : ''}" data-act="mgprop" data-id="${esc(id)}" style="cursor:pointer">
        ${S.mg.obj ? '' : `<td>${esc(mgLabel(p.object))}</td>`}
        <td><b>${esc(p.label || p.name)}</b> ${p.key ? '<span class="chip sm b">키</span>' : ''}${p.inherited ? `<span class="chip sm">상속 · ${esc(mgLabel(p.inherited))}</span>` : ''}<div class="muted mono">${esc(p.name)}</div></td>
        <td>${esc(TYPE_WORD[p.type] || p.type)}${p.values.length ? `<div class="muted" style="font-size:11.5px" title="${esc(valueText(p, ', '))}">허용값 ${p.values.length}개${Object.keys(p.labels || {}).length ? ' · 코드명 등록' : ''}</div>` : ''}</td>
        <td class="mono" style="font-size:11.5px">${p.expr ? '<span class="chip sm">계산 속성</span>' : esc(p.column)}</td>
        <td><div class="chips">${p.required ? '<span class="chip sm">필수</span>' : ''}${p.mask ? `<span class="chip sm warn">${MASK_WORD[p.mask]}</span>` : ''}</div></td>
        <td><div class="chips">${ownerChip(p)}${stateChips(p)}</div></td></tr>`;
    }).join('');
    const objSel = `<select data-in="mgpobj" style="width:180px"><option value="">전체 객체</option>${m.objects.map((o) => opt(o.name, o.label, S.mg.obj)).join('')}</select>`;
    const head = mgHead(title, sub, `${objSel}<input type="text" data-in="mgq" value="${esc(S.mg.q)}" placeholder="속성 · 컬럼 검색" style="width:180px"><button class="btn sm primary" data-act="mgpropnew">새 속성</button>`);
    return `${head}${pendingBar()}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(320px,1fr);align-items:start">
      <div class="card"><div class="ch">속성 <span class="chip sm">${all.length}</span>${all.length > shown.length ? `<span class="muted" style="font-weight:600;font-size:12px">앞 ${shown.length}개 표시 · 객체나 검색어로 좁히세요</span>` : ''}</div>
        <div class="cb scroll" style="padding:0;max-height:640px"><table class="tight"><tr>${S.mg.obj ? '' : '<th>객체</th>'}<th>속성</th><th>자료형</th><th>원천 컬럼</th><th>제약</th><th>정의</th></tr>${rows}</table></div></div>
      ${propForm()}</div>`;
  }

  function columnsOf(obj) {
    const o = mgObj(obj);
    const t = o && o.table ? mgTable(o.table) : null;
    return t ? t.columns : [];
  }

  function propForm() {
    const f = S.mg.form && S.mg.form.kind === 'prop' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">속성 정보</div><div class="cb"><div class="empty">속성을 선택하면 라벨, 원천 컬럼, 허용값, 필수, 가림을 수정할 수 있습니다. [새 속성]으로 속성을 추가합니다.</div></div></div>';
    const v = f.v;
    const p = f.mode === 'edit' ? m.properties.find((x) => x.object === v.object && x.name === v.name) : null;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    const typeOk = !p || p.new || own(p);
    const types = `<select data-in="mgf" data-f="type"${typeOk ? '' : ' disabled'}>${TYPES.map((t) => opt(t, `${TYPE_WORD[t]} (${t})`, v.type)).join('')}</select>`;
    const cols = columnsOf(v.object);
    const used = new Set(mgProps(v.object).map((x) => (x.column || '').toLowerCase()));
    const colSel = cols.length ? `<select data-in="mgf" data-f="column" data-re="1"><option value="">${f.mode === 'new' ? '선택' : '이름과 같은 컬럼'}</option>${cols.map((c) => opt(c.name, `${c.name} · ${c.type}${used.has(c.name.toLowerCase()) && c.name !== v.column ? ' · 사용 중' : ''}`, v.column)).join('')}</select>`
      : `<input type="text" data-in="mgf" data-f="column" value="${esc(v.column)}" placeholder="원천 컬럼 이름">`;
    const common = `${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}">`)}
      ${field('자료형', types, typeOk ? '' : '표준 모듈에서 정한 자료형은 바꿀 수 없습니다. 다른 자료형이 필요하면 새 속성을 추가하세요.')}
      ${v.expr ? field('계산식', `<input type="text" data-in="mgf" data-f="expr" value="${esc(v.expr)}" class="mono">`)
        : (p && p.columns.length ? field('원천 컬럼', `<input type="text" value="${esc(p.columns.join(', '))}" class="mono" disabled>`, '복합 키는 여러 컬럼을 하나의 값으로 읽습니다.') : field('원천 컬럼', colSel))}
      ${field('허용값', `<input type="text" data-in="mgf" data-f="values" value="${esc(v.values)}" placeholder="쉼표로 구분, 예: BASIC, SILVER, VIP 또는 10=주문, 20=취소">`, '값=이름으로 적으면 코드값에 이름을 붙입니다.')}
      <div class="rgrid two">${field('단위', `<input type="text" data-in="mgf" data-f="unit" value="${esc(v.unit)}" placeholder="예: 원">`)}
        ${field('가림', `<select data-in="mgf" data-f="mask">${Object.entries(MASK_WORD).map(([k, l]) => opt(k, l, v.mask)).join('')}</select>`)}</div>
      <label class="tick" style="margin-bottom:12px"><input type="checkbox" data-in="mgf" data-f="required"${v.required ? ' checked' : ''}>필수 값</label>
      ${field('설명', `<input type="text" data-in="mgf" data-f="description" value="${esc(v.description)}">`)}`;
    if (f.mode === 'new') {
      const objSel = `<select data-in="mgf" data-f="object" data-re="1">${m.objects.map((o) => opt(o.name, `${o.label} (${o.name})`, v.object)).join('')}</select>`;
      return `<div class="card"><div class="ch">새 속성<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
        ${field('객체', objSel)}${field('영문 이름', `<input type="text" data-in="mgf" data-f="name" value="${esc(v.name)}" placeholder="예: nickname">`)}${common}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>속성 추가</button></div></div>`;
    }
    const why = p.key ? `'${p.name}'은 ${mgLabel(p.object)}의 키라서 제외할 수 없습니다.` : (p.inherited ? `상위 객체 ${mgLabel(p.inherited)}에서 물려받은 속성입니다. ${mgLabel(p.inherited)}에서 제외하세요.` : '');
    return `<div class="card"><div class="ch">${esc(mgLabel(p.object))} · ${esc(p.label || p.name)} <span class="muted mono" style="font-weight:600">${esc(p.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px">${ownerChip(p)}${stateChips(p)}${p.key ? '<span class="chip sm b">키</span>' : ''}</div>${common}
      ${own(p) || p.new ? '' : `<div class="hint" style="margin-bottom:12px">${esc(p.module_label)} 모듈의 속성입니다. 바꾼 내용은 '관리 변경'에 확장으로 기록됩니다.</div>`}
      <div style="display:flex;gap:8px;align-items:center"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button><div style="flex:1"></div>
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

  function viewLinks() {
    const title = '관계 관리', sub = '객체 사이의 관계와 연결 기준 컬럼, 카디널리티를 관리합니다';
    const wait = mgWait(title, sub);
    if (wait) return wait;
    const m = S.mg.st;
    const q = S.mg.q.trim().toLowerCase();
    const list = m.links.filter((l) => (!S.mg.obj || l.source === S.mg.obj || l.target === S.mg.obj)
      && (!q || `${l.name} ${l.label} ${l.source} ${l.target} ${mgLabel(l.source)} ${mgLabel(l.target)}`.toLowerCase().includes(q)));
    const how = (l) => (l.on ? `<span class="mono">${esc(l.source)}.${esc(l.on[0])} = ${esc(l.target)}.${esc(l.on[1])}</span>`
      : (l.via ? `<span class="mono">${esc(l.via.table)}</span> <span class="muted">(${esc(l.via.source)} · ${esc(l.via.target)})</span>` : '<span class="chip sm">개념 관계</span>'));
    const rows = list.map((l) => `<tr class="${S.mg.sel === l.name ? 'sel' : ''}" data-act="mglink" data-name="${esc(l.name)}" style="cursor:pointer">
      <td><b>${esc(l.label || l.name)}</b><div class="muted mono">${esc(l.name)}${l.inverse ? ` · 역 ${esc(l.inverse)}` : ''}</div></td>
      <td>${esc(mgLabel(l.source))} <span class="muted">→</span> ${esc(mgLabel(l.target))}</td><td><span class="chip sm">${CARD[l.cardinality] || esc(l.cardinality)}</span></td>
      <td style="font-size:11.5px">${how(l)}</td><td><div class="chips">${l.required ? '<span class="chip sm">필수</span>' : ''}${ownerChip(l)}${stateChips(l)}</div></td></tr>`).join('');
    const sug = fkSuggestions();
    const sugCard = sug.length ? `<div class="card"><div class="ch">참조 컬럼으로 찾은 관계 <span class="chip sm">${sug.length}</span><div class="right muted" style="font-weight:600;font-size:12px">원천 테이블의 외래 키 기준</div></div><div class="cb scroll" style="padding:0;max-height:240px">
      <table class="tight"><tr><th>출발 → 도착</th><th>연결 기준</th><th>이름</th><th></th></tr>${sug.map((x, i) => `<tr><td>${esc(mgLabel(x.source))} → ${esc(mgLabel(x.target))}</td>
        <td class="mono" style="font-size:11.5px">${esc(x.column)}</td><td class="mono">${esc(x.name)}</td><td><button class="btn sm" data-act="mgsug" data-i="${i}"${S.mg.busy ? ' disabled' : ''}>관계 추가</button></td></tr>`).join('')}</table></div></div>` : '';
    const unlinked = m.unlinked.length ? `<div class="hint">관계가 없는 객체: ${m.unlinked.map((n) => `<b>${esc(mgLabel(n))}</b>`).join(', ')}. 다른 객체로 이어지는 질의를 만들 수 없습니다.</div>` : '';
    const objSel = `<select data-in="mgpobj" style="width:180px"><option value="">전체 객체</option>${m.objects.map((o) => opt(o.name, o.label, S.mg.obj)).join('')}</select>`;
    const head = mgHead(title, sub, `${objSel}<input type="text" data-in="mgq" value="${esc(S.mg.q)}" placeholder="관계 검색" style="width:160px"><button class="btn sm primary" data-act="mglinknew">새 관계</button>`);
    return `${head}${pendingBar()}${unlinked}${sugCard}<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(320px,1fr);align-items:start">
      <div class="card"><div class="ch">관계 <span class="chip sm">${list.length}</span><div class="right muted" style="font-weight:600;font-size:12px">그래프는 [온톨로지]에서 확인</div></div><div class="cb scroll" style="padding:0;max-height:640px">
        <table class="tight"><tr><th>관계</th><th>출발 → 도착</th><th>카디널리티</th><th>연결 기준</th><th>정의</th></tr>${rows}</table></div></div>
      ${linkForm()}</div>`;
  }

  function linkForm() {
    const f = S.mg.form && S.mg.form.kind === 'link' ? S.mg.form : null;
    const m = S.mg.st;
    if (!f) return '<div class="card"><div class="ch">관계 정보</div><div class="cb"><div class="empty">관계를 선택하면 라벨, 카디널리티, 역관계를 수정할 수 있습니다. [새 관계]로 두 객체를 연결합니다.</div></div></div>';
    const v = f.v;
    const l = f.mode === 'edit' ? m.links.find((x) => x.name === v.name) : null;
    const field = (label, html, hint = '') => `<div class="field"><label>${label}</label>${html}${hint ? `<span class="muted" style="font-size:11.5px">${hint}</span>` : ''}</div>`;
    const ends = !l || own(l);
    const objSel = (k) => `<select data-in="mgf" data-f="${k}" data-re="1"${ends ? '' : ' disabled'}><option value="">선택</option>${m.objects.map((o) => opt(o.name, `${o.label} (${o.name})`, v[k])).join('')}</select>`;
    const propSel = (k, obj) => `<select data-in="mgf" data-f="${k}"${ends && obj ? '' : ' disabled'}><option value="">선택</option>${(obj ? mgProps(obj) : []).filter((p) => !p.expr).map((p) => opt(p.name, `${p.label || p.name} (${p.name})${p.key ? ' · 키' : ''}`, v[k])).join('')}</select>`;
    const cards = `<select data-in="mgf" data-f="cardinality">${Object.entries(CARD).map(([k, x]) => opt(k, `${x} (${k})`, v.cardinality)).join('')}</select>`;
    const body = `${f.mode === 'new' ? field('영문 이름', `<input type="text" data-in="mgf" data-f="name" value="${esc(v.name)}" placeholder="예: usedCoupon">`) : ''}
      ${field('라벨', `<input type="text" data-in="mgf" data-f="label" value="${esc(v.label)}" placeholder="예: 사용 쿠폰">`)}
      <div class="rgrid two">${field('출발 객체', objSel('source'))}${field('출발 속성', propSel('sp', v.source))}</div>
      <div class="rgrid two">${field('도착 객체', objSel('target'))}${field('도착 속성', propSel('tp', v.target))}</div>
      ${ends ? '<div class="muted" style="font-size:11.5px;margin:-4px 0 10px">출발 속성 값과 도착 속성 값이 같은 행끼리 연결합니다.</div>' : '<div class="muted" style="font-size:11.5px;margin:-4px 0 10px">양 끝 객체와 연결 기준은 정의한 모듈에서만 바꿀 수 있습니다.</div>'}
      <div class="rgrid two">${field('카디널리티', cards)}${field('역관계 이름', `<input type="text" data-in="mgf" data-f="inverse" value="${esc(v.inverse)}" placeholder="예: couponUsedBy">`)}</div>
      <label class="tick" style="margin-bottom:12px"><input type="checkbox" data-in="mgf" data-f="required"${v.required ? ' checked' : ''}>필수 관계</label>`;
    if (f.mode === 'new') {
      return `<div class="card"><div class="ch">새 관계<div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">${body}
        <button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>관계 추가</button></div></div>`;
    }
    return `<div class="card"><div class="ch">${esc(l.label || l.name)} <span class="muted mono" style="font-weight:600">${esc(l.name)}</span><div class="right"><button class="btn sm ghost" data-act="mgcancel">닫기</button></div></div><div class="cb">
      <div class="chips" style="margin-bottom:12px">${ownerChip(l)}${stateChips(l)}</div>${body}
      <div style="display:flex;gap:8px"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>저장</button><div style="flex:1"></div>
        <button class="btn danger" data-act="mgdel"${S.mg.busy ? ' disabled' : ''}>관계 제외</button></div></div></div>`;
  }

  // ---- questions (on the 검증 screen)

  function questionCard() {
    const m = S.mg.st;
    if (!m || m.error) return '';
    const f = S.mg.form && S.mg.form.kind === 'question' ? S.mg.form : null;
    const target = (x) => (x.decision ? `판정 <span class="mono">${esc(x.decision)}</span> · 키 <span class="mono">${esc(x.key)}</span>`
      : `질의 <span class="mono">${esc(x.query)}</span>${Object.keys(x.params || {}).length ? ` <span class="muted mono">${esc(JSON.stringify(x.params))}</span>` : ''}`);
    const rows = m.questions.map((x) => `<tr><td class="mono">${esc(x.id)}</td><td style="min-width:180px">${esc(x.text)}</td><td style="font-size:12px">${target(x)}</td>
      <td style="font-size:12px">${showObj(x.expect)}</td><td><div class="chips">${ownerChip(x)}${x.pending ? '<span class="chip sm warn">새로 추가</span>' : ''}</div></td>
      <td><button class="btn sm ghost" data-act="mgqdel" data-id="${esc(x.id)}"${S.mg.busy ? ' disabled' : ''}>제외</button></td></tr>`).join('');
    let form = '';
    if (f && f.mode === 'new') {
      const v = f.v;
      const field = (label, html) => `<div class="field"><label>${label}</label>${html}</div>`;
      const pick = v.kind === 'decision'
        ? `${field('판정', `<select data-in="mgf" data-f="decision">${S.st.decisions.map((d) => opt(d.name, `${d.label} (${d.name})`, v.decision)).join('')}</select>`)}${field('대상 키', `<input type="text" data-in="mgf" data-f="key" value="${esc(v.key)}" placeholder="예: I1001">`)}`
        : `${field('질의', `<select data-in="mgf" data-f="query">${S.st.queries.map((q) => opt(q.name, `${q.label} (${q.name})`, v.query)).join('')}</select>`)}${field('JSON 파라미터', `<input type="text" data-in="mgf" data-f="params" value="${esc(v.params)}" class="mono" placeholder='예: {"customer": "C001"}'>`)}`;
      form = `<div class="review"><div class="rgrid">${field('번호', `<input type="text" data-in="mgf" data-f="id" value="${esc(v.id)}" placeholder="예: G1">`)}
          ${field('종류', `<select data-in="mgf" data-f="kind" data-re="1">${opt('query', '질의 결과 행 수', v.kind)}${opt('decision', '판정 결과', v.kind)}</select>`)}
          ${field(v.kind === 'decision' ? 'JSON 기대값' : '기대 행 수', `<input type="text" data-in="mgf" data-f="expect" value="${esc(v.expect)}" class="mono" placeholder="${v.kind === 'decision' ? '예: {&quot;eligible&quot;: true}' : '예: 2'}">`)}</div>
        ${field('질문', `<input type="text" data-in="mgf" data-f="text" value="${esc(v.text)}" placeholder="예: C001 고객의 주문은 몇 건인가요?">`)}<div class="rgrid two">${pick}</div>
        <div style="display:flex;gap:8px"><button class="btn primary" data-act="mgsave"${S.mg.busy ? ' disabled' : ''}>질문 추가</button><button class="btn ghost" data-act="mgcancel">닫기</button></div></div>`;
    }
    if (f && f.mode === 'import') {
      form = `<div class="review"><div class="field"><label>YAML 또는 JSON 검증 질문 목록</label><textarea class="code" data-in="mgf" data-f="text" style="min-height:160px" placeholder="- {id: G1, text: &quot;C001 고객의 주문은 몇 건인가요?&quot;, query: ordersOfCustomer, params: {customer: C001}, expect: {rows: 2}}">${esc(f.v.text)}</textarea></div>
        <div style="display:flex;gap:8px"><button class="btn primary" data-act="mgqimport"${S.mg.busy ? ' disabled' : ''}>불러오기</button><button class="btn ghost" data-act="mgcancel">닫기</button></div></div>`;
    }
    return `<div class="card"><div class="ch">검증 질문 관리 <span class="chip sm">${m.questions.length}</span><div class="right"><button class="btn sm" data-act="mgqimp">목록 불러오기</button><button class="btn sm primary" data-act="mgqnew">새 질문</button></div></div>
      <div class="cb">${pendingBar()}<div class="hint" style="margin-bottom:12px">정답이 정해진 골든 질문입니다. 질문을 추가하거나 제외하면 '관리 변경'에 기록되고, 변경 요청이 승인되면 위 정답률 계산에 들어갑니다.</div>${form}</div>
      <div class="cb scroll" style="padding:0;max-height:420px"><table class="tight"><tr><th>번호</th><th>질문</th><th>대상</th><th>정답</th><th>정의</th><th></th></tr>${rows}</table></div></div>`;
  }

  // ---- edits from the forms

  function mgSave() {
    const f = S.mg.form;
    const v = f.v;
    const list = (s) => String(s || '').split(',').map((x) => x.trim()).filter(Boolean);
    if (f.kind === 'object' && f.mode === 'new') {
      if (!IDENT.test(v.name || '')) { toast('이름은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있습니다.', true); return; }
      const t = v.table ? mgTable(v.table) : null;
      const props = {};
      if (t && v.cols) t.columns.forEach((c) => { props[propName(c.name)] = { type: sqlType(c.type), label: c.name, column: c.name }; });
      const wide = t && t.key.length > 1;
      const key = wide ? `${propName(v.name)}_key` : (t ? propName(v.key || t.key[0] || t.columns[0].name) : propName(v.key || ''));
      if (wide) props[key] = { type: 'string', label: `${v.label || v.name} 키`, columns: t.key };
      if (!key) { toast('키를 정하지 않아 객체를 추가하지 못했습니다. 키를 입력해 주세요.', true); return; }
      if (!props[key]) { const c = t && t.columns.find((x) => propName(x.name) === key); props[key] = { type: c ? sqlType(c.type) : 'string', label: c ? c.name : key, column: c ? c.name : key }; }
      props[key].required = true;
      S.mg.sel = v.name;
      mgEdit('add_object', { name: v.name, label: v.label, table: v.table, key, properties: props, parent: v.parent, description: v.description }, `객체 ${v.label || v.name}을 추가했습니다.`);
      return;
    }
    if (f.kind === 'object') {
      const o = f.orig, args = { name: v.name };
      for (const k of ['label', 'description', 'table', 'parent']) if ((v[k] || '') !== (o[k] || '')) args[k] = v[k] || '';
      if (own(mgObj(v.name)) && v.key !== o.key) args.key = v.key;
      if (Object.keys(args).length === 1) { toast('바뀐 내용이 없습니다.'); return; }
      mgEdit('update_object', args, `객체 ${v.label || v.name}을 바꿨습니다.`);
      return;
    }
    if (f.kind === 'prop') {
      const pairs = list(v.values).map((x) => { const i = x.indexOf('='); return i > 0 ? [x.slice(0, i).trim(), x.slice(i + 1).trim()] : [x, '']; });
      const spec = { label: v.label, description: v.description, type: v.type, unit: v.unit, values: pairs.map(([c]) => c),
        labels: Object.fromEntries(pairs.filter(([, n]) => n)), required: !!v.required, mask: v.mask || '' };
      if (v.expr) spec.expr = v.expr; else spec.column = v.column || '';
      if (f.mode === 'new') {
        if (!IDENT.test(v.name || '')) { toast('이름은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있습니다.', true); return; }
        S.mg.sel = `${v.object}.${v.name}`;
        mgEdit('add_property', { object: v.object, name: v.name, ...spec }, `속성 ${v.label || v.name}을 추가했습니다.`);
        return;
      }
      const o = f.orig, args = { object: v.object, name: v.name };
      for (const [k, x] of Object.entries(spec)) if (JSON.stringify(x) !== JSON.stringify(o[k])) args[k] = x;
      if (Object.keys(args).length === 2) { toast('바뀐 내용이 없습니다.'); return; }
      mgEdit('update_property', args, `속성 ${v.label || v.name}을 바꿨습니다.`);
      return;
    }
    if (f.kind === 'link') {
      if (f.mode === 'new') {
        if (!IDENT.test(v.name || '')) { toast('이름은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있습니다.', true); return; }
        if (!v.source || !v.target || !v.sp || !v.tp) { toast('출발 · 도착 객체와 연결할 속성을 모두 골라 주세요.', true); return; }
        S.mg.sel = v.name;
        mgEdit('add_link', { name: v.name, label: v.label, source: v.source, target: v.target, on: [v.sp, v.tp], cardinality: v.cardinality, inverse: v.inverse, required: !!v.required }, `관계 ${v.label || v.name}을 추가했습니다.`);
        return;
      }
      const o = f.orig, args = { name: v.name };
      for (const k of ['label', 'cardinality', 'inverse']) if ((v[k] || '') !== (o[k] || '')) args[k] = v[k] || '';
      if (!!v.required !== !!o.required) args.required = !!v.required;
      if (own(o)) {
        if (v.source !== o.source) args.source = v.source;
        if (v.target !== o.target) args.target = v.target;
        if (v.sp !== o.sp || v.tp !== o.tp) args.on = [v.sp, v.tp];
      }
      if (Object.keys(args).length === 1) { toast('바뀐 내용이 없습니다.'); return; }
      mgEdit('update_link', args, `관계 ${v.label || v.name}을 바꿨습니다.`);
      return;
    }
    if (f.kind === 'question') {
      let expect = {}, params = {};
      try {
        if (v.kind === 'decision') expect = v.expect.trim() ? JSON.parse(v.expect) : {};
        else { expect = v.expect.trim() === '' ? {} : { rows: Number(v.expect) }; params = v.params.trim() ? JSON.parse(v.params) : {}; }
      } catch (_) { toast('JSON 형식이 아니어서 읽지 못했습니다. 예시처럼 입력해 주세요.', true); return; }
      const args = v.kind === 'decision' ? { id: v.id, text: v.text, decision: v.decision, key: v.key, expect }
        : { id: v.id, text: v.text, query: v.query, params, expect };
      mgEdit('add_question', args, `검증 질문 ${v.id}을 추가했습니다.`);
    }
  }

  function mgDelete() {
    const f = S.mg.form;
    const v = f.v;
    const say = { object: `객체 ${v.label || v.name}`, prop: `속성 ${v.label || v.name}`, link: `관계 ${v.label || v.name}` }[f.kind];
    if (!window.confirm(`${say}을 제외합니다. 이 항목을 쓰는 질의, 결정, 검증 질문도 함께 빠지며, 빠진 항목은 대기 중인 변경에서 확인할 수 있습니다.`)) return;
    S.mg.sel = '';
    if (f.kind === 'object') mgEdit('delete_object', { name: v.name }, `${say}을 제외했습니다.`);
    if (f.kind === 'prop') mgEdit('delete_property', { object: v.object, name: v.name }, `${say}을 제외했습니다.`);
    if (f.kind === 'link') mgEdit('delete_link', { name: v.name }, `${say}을 제외했습니다.`);
  }

  function mgOpen(kind, key) {
    const m = S.mg.st;
    S.mg.sel = key;
    if (kind === 'object') {
      const o = mgObj(key);
      S.mg.form = { kind, mode: 'edit', orig: o, v: { name: o.name, label: o.label, description: o.description, table: o.table, key: o.key, parent: o.parent } };
    }
    if (kind === 'prop') {
      const [obj, name] = key.split('.');
      const p = m.properties.find((x) => x.object === obj && x.name === name);
      S.mg.form = { kind, mode: 'edit', orig: { ...p, column: p.column || '' }, v: { object: obj, name, label: p.label, description: p.description, type: p.type, column: p.column || '', values: valueText(p, ', '), unit: p.unit, required: p.required, mask: p.mask, expr: p.expr } };
    }
    if (kind === 'link') {
      const l = m.links.find((x) => x.name === key);
      const v = { name: l.name, label: l.label, source: l.source, target: l.target, sp: l.on ? l.on[0] : '', tp: l.on ? l.on[1] : '', cardinality: l.cardinality, inverse: l.inverse, required: l.required };
      S.mg.form = { kind, mode: 'edit', orig: { ...v, module: l.module }, v: { ...v } };
    }
    render();
  }

  // ---- events --------------------------------------------------------------------------------------------------

  const ACT = {
    reset: async () => {
      if (!window.confirm('업로드한 데이터와 변경 내용을 모두 삭제하고 예시 스튜디오로 초기화합니다.')) return;
      try {
        await api('reset', {});
        clearInterval(S.dr.timer);
        Object.assign(S, { impact: null, pos: {}, sel: null, files: null, dpos: {} });
        Object.assign(S.dr, { step: 0, view: 'read', sel: null, ed: NEW_EDITS(), rev: null, graph: null, rules: null, tables: {}, timer: 0 });
        S.ed = null;
        stale();
        Object.assign(S.mg, { form: null, sel: '', q: '', obj: '', table: '', open: false, review: null });
        S.q.name = null; S.q.text = ''; S.q.dirty = false; S.d.name = null; S.d.key = null;
        await load();
        toast('초기화했습니다.');
      } catch (e) { fail(e); }
    },
    kind: (t) => { S.kind = t.dataset.kind; render(); },
    toggle: (t) => toggleModule(t.dataset.mod),
    detach: (t) => detach(t.dataset.mod, t.dataset.cascade === '1'),
    'cancel-impact': () => { S.impact = null; render(); },
    select: (t) => selectObject(t.dataset.obj),
    qmode: (t) => {
      S.q.mode = t.dataset.mode;
      if (S.q.mode === 'text' && !S.q.dirty) S.q.text = textFor(S.q.lang) || S.q.text;
      render();
    },
    pick: (t) => pickQuery(t.dataset.q),
    run: () => runQuery(),
    example: (t) => { S.q.question = t.dataset.text; runQuery(); },
    target: (t) => { S.q.target = t.dataset.target; render(); },
    'ask-decision': async (t) => { S.d.name = t.dataset.name; S.d.key = t.dataset.key; S.d.proposal = null; S.d.res = null; render(); await startDecide(); },
    request: (t) => requestAction(t.dataset.action),
    approve: (t) => approve(t.dataset.id, true),
    reject: (t) => approve(t.dataset.id, false),
    rollback: async (t) => {
      try {
        const r = await api('rollback', { id: t.dataset.id });
        if (!r.ok) throw new Error(r.error);
        S.d.proposal = r.proposal;
        S.q.res = null; S.qa = null; S.bind = null; S.fl = null; S.d.keys = {}; S.agree = null;
        await load();
        await startDecide();
        toast('실행 전 값으로 되돌렸습니다.');
      } catch (e) { fail(e); }
    },
    login: async () => {
      try {
        const r = await api('login', { user: ($('#luser') || {}).value || '', password: ($('#lpw') || {}).value || '' });
        S.me = { team: true, user: r.user };
        await load();
      } catch (e) { fail(e); }
    },
    logout: async () => { try { await api('logout', {}); } catch (_) { /* signed out anyway */ } S.me.user = null; renderLogin(); },
    sync: async () => {
      try {
        const r = await api('sync', {});
        if (!r.ok) throw new Error(r.error);
        S.fl = null; stale();
        await load();
        toast(r.changed ? '원천 변경분을 그래프 저장소에 반영했습니다.' : '원천에 바뀐 내용이 없습니다.');
      } catch (e) { fail(e); }
    },
    flowsave: async () => {
      try {
        await api('flow/save', { settings: S.flset.settings });
        S.fl = null; S.flset = null; S.agree = null;
        render();
        toast('흐름 설정을 저장했습니다.');
      } catch (e) { fail(e); }
    },
    cshow: (t) => {
      const c = (S.changes.changes || []).find((x) => x.id === t.dataset.id);
      if (!c) return;
      if (!S.ed || S.ed.name !== c.module) S.ed = { name: c.module, label: c.module_label, applied: true, isNew: false, text: '', check: null, busy: false, readonly: true };
      S.change = c;
      render();
      requestAnimationFrame(() => { const e = $('#editor'); if (e) e.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
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
    mapsuggest: async () => {
      S.map.busy = true; render();
      try { S.map.sug = await api('draft/map', { standard: S.map.picked, edits: toEdits() }); S.map.edits = { objects: {}, columns: {} }; } catch (e) { S.map.sug = { ok: false, error: e.message }; }
      S.map.busy = false; render();
    },
    mapapply: async () => {
      S.map.busy = true; render();
      const edits = { objects: {}, columns: {} };
      for (const [k, v] of Object.entries(S.map.edits.objects)) edits.objects[k] = v || null;
      for (const [k, v] of Object.entries(S.map.edits.columns)) edits.columns[k] = v || null;
      try {
        await api('draft/map/apply', { standard: S.map.picked, edits: toEdits(), mapping: edits });
        Object.assign(S, { impact: null, pos: {}, sel: null, files: null, dpos: {} });
        stale();
        S.map = { standards: null, picked: [], sug: null, edits: { objects: {}, columns: {} }, busy: false };
        S.q.name = null; S.q.text = ''; S.q.dirty = false; S.q.role = ''; S.q.principal = {}; S.d.name = null; S.d.key = null;
        S.changes = null; S.agree = null; S.flset = null;
        await load();
        location.hash = '#flow';
        toast('업로드한 테이블을 표준 정의에 연결해 적용했습니다.');
      } catch (e) { S.map.busy = false; render(); fail(e); }
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
    fsample: () => filesCall('files/sample', {}),
    dtall: (t) => {
      const x = (S.files.definitions || []).find((d) => d.source === t.dataset.src);
      if (x) x.tables.forEach((tb) => { S.dr.tables[tb.name] = t.dataset.on === '1'; });
      render();
    },
    fremove: (t) => filesCall('files/remove', { name: t.dataset.name }),
    draft: () => {
      const data = (S.files.files || []).flatMap((x) => x.tables.map((t) => t.name));
      const all = data.length ? data : (S.files.definitions || []).flatMap((x) => x.tables.map((t) => t.name));
      const tables = all.filter((n) => S.dr.tables[n] !== false);
      filesCall('draft', { label: S.dr.label, rules: S.dr.rules, tables }, startDraft);
    },
    connect: () => filesCall('connect', { dsn: S.dr.dsn, label: S.dr.label, rules: S.dr.rules }, startDraft),
    dview: (t) => { S.dr.view = t.dataset.view; refreshDraft(); },
    dsel: () => { S.dr.sel = null; refreshDraft(); },
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
        toast(`기록 ${r.records}건을 ${r.identities}건으로 묶어 교차표를 저장했습니다.`);
      } catch (e) { fail(e); }
    },
    medit: async (t) => {
      try { await openModule(t.dataset.mod); render(); requestAnimationFrame(() => { const e = $('#editor'); if (e) e.scrollIntoView({ behavior: 'smooth', block: 'start' }); }); } catch (e) { fail(e); }
    },
    mnew: () => { S.ed = { name: '', label: '새 모듈', applied: false, isNew: true, text: moduleTemplate(), check: null, busy: false }; render(); },
    mclose: () => { S.ed = null; S.change = null; render(); },
    popen: () => { S.pol.open = !S.pol.open; render(); },
    pclose: () => { S.pol.open = false; render(); },
    psample: async () => {
      try {
        const r = await api('policy/sample', {});
        if (!r.ok) throw new Error(r.error);
        S.pol.text = r.text; S.pol.res = null; render();
      } catch (e) { fail(e); }
    },
    pdraft: async () => {
      S.pol.busy = true; S.pol.res = null; render();
      try {
        let r = await api('policy/draft', { text: S.pol.text, target: S.pol.target });
        const { job } = r;
        while (job && (r.job || r.running)) { // the model works on the server; the page collects the draft
          await new Promise((done) => setTimeout(done, 2000));
          r = await api('policy/draft/result', { job });
        }
        S.pol.res = r;
        if (r.ok) {
          S.ed = { name: '', label: r.label, applied: false, isNew: true, text: r.yaml, check: null, busy: false };
          S.change = null;
        }
      } catch (e) { S.pol.res = { ok: false, error: e.message }; }
      S.pol.busy = false; render();
    },
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
        toast(r.bumped ? `버전 ${r.bumped} 이(가) 이미 있어 ${r.change.version} (으)로 변경을 요청했습니다.` : '변경을 요청했습니다. 검토 결과를 확인하세요.', !r.change.passed);
      } catch (e) {
        S.ed.busy = false;
        S.ed.check = { error: e.message };
        render();
      }
    },
    mgtable: (t) => { S.mg.table = t.dataset.t; render(); },
    mgobj: (t) => mgOpen('object', t.dataset.name),
    mgprop: (t) => mgOpen('prop', t.dataset.id),
    mglink: (t) => mgOpen('link', t.dataset.name),
    mglinkgo: (t) => { S.mg.keep = true; S.mg.q = ''; S.mg.obj = ''; location.hash = '#links'; mgOpen('link', t.dataset.name); },
    mgobjgo: (t) => { S.mg.keep = true; S.mg.q = ''; location.hash = '#objects'; mgOpen('object', t.dataset.name); },
    mgobjnew: (t) => {
      const tb = t.dataset.t || '';
      const x = tb ? mgTable(tb) : null;
      S.mg.sel = '';
      S.mg.form = { kind: 'object', mode: 'new', v: { table: tb, name: tb ? typeName(tb) : '', label: '', key: x ? (x.key[0] || (x.columns[0] || {}).name || '') : '', parent: '', description: '', cols: true } };
      if (S.tab !== 'objects') { S.mg.keep = true; location.hash = '#objects'; } else render();
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
    mgpropsof: (t) => { S.mg.obj = t.dataset.name; S.mg.q = ''; S.mg.form = null; S.mg.sel = ''; location.hash = '#props'; },
    mglinksof: (t) => { S.mg.obj = t.dataset.name; S.mg.q = ''; S.mg.form = null; S.mg.sel = ''; location.hash = '#links'; },
    mgcancel: () => { S.mg.form = null; S.mg.sel = ''; render(); },
    mgsave: () => mgSave(),
    mgdel: () => mgDelete(),
    mgsug: (t) => {
      const x = fkSuggestions()[Number(t.dataset.i)];
      if (x) mgEdit('add_link', { name: x.name, label: mgLabel(x.target), source: x.source, target: x.target, on: [x.sp, x.tp], cardinality: 'many_to_one' }, `관계 ${x.name}을 추가했습니다.`);
    },
    mgopen: () => { S.mg.open = !S.mg.open; render(); },
    mgdiscard: async () => {
      if (!window.confirm('대기 중인 변경을 모두 취소합니다. 표준 모듈과 승인된 변경은 그대로 남습니다.')) return;
      try { S.mg.st = await api('manage/discard', {}); S.mg.form = null; S.mg.sel = ''; S.mg.review = null; toast('대기 중인 변경을 취소했습니다.'); } catch (e) { fail(e); }
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
        S.mg.st = r; S.mg.form = null; S.mg.sel = ''; S.mg.open = false;
        S.changes = null; S.change = r.change; S.agree = null; S.flset = null; S.pos = {};
        S.mg.busy = false;
        await load();
        toast(r.pending ? '변경을 요청했습니다. 승인자가 승인하면 반영됩니다. [온톨로지 라이브러리]의 변경 요청에서 확인하세요.'
          : `변경을 승인하고 적용했습니다. '${r.change.module_label}' ${r.change.version} 기준으로 모든 화면이 바뀝니다.${r.warning ? ' ' + r.warning : ''}`);
      } catch (e) { S.mg.busy = false; render(); fail(e); }
    },
    mgqnew: () => {
      const ids = new Set(S.mg.st.questions.map((x) => x.id));
      let i = 1;
      while (ids.has(`G${i}`)) i += 1;
      S.mg.form = { kind: 'question', mode: 'new', v: { id: `G${i}`, text: '', kind: 'query', query: (S.st.queries[0] || {}).name || '', params: '', decision: (S.st.decisions[0] || {}).name || '', key: '', expect: '' } };
      render();
    },
    mgqimp: () => { S.mg.form = { kind: 'question', mode: 'import', v: { text: '' } }; render(); },
    mgqimport: async () => {
      S.mg.busy = true; render();
      try {
        const r = await api('manage/questions', { text: S.mg.form.v.text });
        S.mg.st = r; S.mg.form = null;
        toast(`검증 질문 ${r.added.length}개를 불러왔습니다.${r.failed.length ? ` ${r.failed.length}개는 불러오지 못했습니다. ${r.failed.slice(0, 2).join(' / ')}` : ''}`, !r.added.length);
      } catch (e) { fail(e); }
      S.mg.busy = false; render();
    },
    mgqdel: (t) => {
      if (!window.confirm(`검증 질문 ${t.dataset.id}을 제외합니다.`)) return;
      mgEdit('delete_question', { id: t.dataset.id }, `검증 질문 ${t.dataset.id}을 제외했습니다.`);
    },
    dapply: async () => {
      S.dr.busy = true;
      render();
      try {
        await api('draft/apply', { edits: toEdits() });
        Object.assign(S, { impact: null, pos: {}, sel: null, files: null, dpos: {} });
        stale();
        S.q.name = null; S.q.text = ''; S.q.dirty = false; S.q.role = ''; S.q.principal = {}; S.d.name = null; S.d.key = null;
        S.dr.busy = false;
        await load();
        location.hash = '#flow';
        toast('온톨로지를 스튜디오에 적용했습니다.');
      } catch (e) { S.dr.busy = false; render(); fail(e); }
    },
  };

  const INPUT = {
    param: (t) => { S.q.params[t.dataset.k] = t.value; },
    principal: (t) => { S.q.principal[t.dataset.k] = t.value; },
    text: (t) => { S.q.text = t.value; S.q.dirty = true; },
    question: (t) => { S.q.question = t.value; },
    aparam: (t) => { S.d.params[t.dataset.k] = t.value; },
    dname: (t) => { S.dr.label = t.value; },
    dsn: (t) => { S.dr.dsn = t.value; },
    dlab: (t) => { S.dr.ed.labels[t.dataset.el] = t.value; if (t.dataset.el.startsWith('object:')) drawGraph(true); },
    dvalues: (t) => { S.dr.ed.values[t.dataset.ref] = t.value; },
    dalabel: (t) => { S.dr.add.label = t.value; },
    drule: (t) => {
      if (t.type === 'number') S.dr.rules[t.dataset.k] = Number(t.value);
      else if (t.type === 'text') S.dr.rules[t.dataset.k] = t.value.split(',').map((x) => x.trim()).filter(Boolean);
    },
    mtext: (t) => { S.ed.text = t.value; },
    ptext: (t) => {
      const was = !S.pol.text.trim();
      S.pol.text = t.value;
      if (was !== !t.value.trim()) { const b = $('[data-act=pdraft]'); if (b) b.disabled = !t.value.trim(); }
    },
    mgf: (t) => {
      if (t.type === 'checkbox' || !S.mg.form) return;
      S.mg.form.v[t.dataset.f] = t.value;
      if (t.dataset.f === 'name') S.mg.form.v.touched = true;
    },
    mgq: (t) => {
      S.mg.q = t.value;
      clearTimeout(S.mg.qt);
      S.mg.qt = setTimeout(() => {
        render();
        const e = $('[data-in="mgq"]');
        if (e) { e.focus(); e.setSelectionRange(e.value.length, e.value.length); }
      }, 220);
    },
    fgate: (t) => {
      const g = S.flset.settings.gates;
      const stage = t.dataset.s, k = t.dataset.k;
      g[stage] = g[stage] || {};
      if (t.value === '') delete g[stage][k];
      else g[stage][k] = k.startsWith('min_') ? Number(t.value) / 100 : Number(t.value);
    },
  };

  const CHANGE = {
    ptarget: (t) => { S.pol.target = t.value; },
    pdoc: (t) => loadDocument(t.value, ''),
    psec: (t) => loadDocument(S.pol.doc, t.value),
    mgpobj: (t) => { S.mg.obj = t.value; S.mg.form = null; S.mg.sel = ''; render(); },
    mgf: (t) => {
      const f = S.mg.form;
      if (!f) return;
      const v = f.v, k = t.dataset.f;
      v[k] = t.type === 'checkbox' ? t.checked : t.value;
      if (!t.dataset.re) return;
      if (f.kind === 'object' && k === 'table') {
        const x = v.table ? mgTable(v.table) : null;
        v.key = x ? (x.key[0] || (x.columns[0] || {}).name || '') : '';
        if (!v.touched) v.name = v.table ? typeName(v.table) : '';
      }
      if (f.kind === 'prop' && k === 'object') v.column = '';
      if (f.kind === 'prop' && k === 'column' && f.mode === 'new' && v.column) {
        if (!v.touched) v.name = propName(v.column);
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
      render();
    },
    role: async (t) => { S.q.role = t.value; S.q.principal = {}; await principalDefaults(S.q); render(); },
    lang: (t) => { S.q.lang = t.value; if (!S.q.dirty || !S.q.text) { S.q.text = textFor(S.q.lang) || S.q.text; S.q.dirty = false; } render(); },
    decision: async (t) => { S.d.name = t.value; S.d.key = null; S.d.res = null; S.d.proposal = null; render(); await startDecide(); },
    key: async (t) => { S.d.key = t.value; S.d.proposal = null; await decide(); },
    arole: (t) => { S.d.role = t.value; },
    dkeep: (t) => { S.dr.ed.drop[t.dataset.el] = !t.checked; edited(); },
    dlab: () => { clearTimeout(previewTimer); previewTimer = setTimeout(preview, 150); },
    dvalues: () => { clearTimeout(previewTimer); previewTimer = setTimeout(preview, 150); },
    dkey: (t) => { S.dr.ed.keys[t.dataset.obj] = t.value; edited(); },
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
    mpick: (t) => { S.map.picked = t.checked ? [...new Set([...S.map.picked, t.dataset.v])] : S.map.picked.filter((x) => x !== t.dataset.v); S.map.sug = null; render(); },
    mobj: async (t) => {
      S.map.edits.objects[t.dataset.obj] = t.value;
      if (!t.value) { render(); return; }
      const tables = Object.fromEntries(Object.entries(S.map.edits.objects).filter(([, v]) => v));
      try { S.map.sug = await api('draft/map', { standard: S.map.picked, edits: toEdits(), tables }); } catch (e) { fail(e); }
      render();
    },
    mcol: (t) => { S.map.edits.columns[t.dataset.ref] = t.value; },
  };

  function wire() {
    const main = $('#main');
    document.addEventListener('click', (ev) => {
      const t = ev.target.closest('[data-act]');
      if (t && ACT[t.dataset.act]) { ev.preventDefault(); ACT[t.dataset.act](t, ev); }
    });
    main.addEventListener('input', (ev) => { const t = ev.target; if (t.dataset && INPUT[t.dataset.in]) INPUT[t.dataset.in](t); });
    main.addEventListener('change', (ev) => { const t = ev.target; if (t.dataset && CHANGE[t.dataset.in]) CHANGE[t.dataset.in](t); });
    main.addEventListener('keydown', (ev) => {
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
    });
    main.addEventListener('change', (ev) => { if (ev.target.id === 'fileinput') uploadFiles(ev.target.files); });
    main.addEventListener('dragover', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) { ev.preventDefault(); z.classList.add('over'); } });
    main.addEventListener('dragleave', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) z.classList.remove('over'); });
    main.addEventListener('drop', (ev) => { const z = ev.target.closest('[data-drop]'); if (z) { ev.preventDefault(); z.classList.remove('over'); uploadFiles(ev.dataTransfer.files); } });
    window.addEventListener('hashchange', () => {
      S.tab = location.hash.slice(1) || 'flow';
      if (S.mg.keep) S.mg.keep = false;
      else if (S.mg.form && S.mg.form.kind !== 'question') { S.mg.form = null; S.mg.sel = ''; }
      render();
    });
  }

  S.tab = (location.hash.slice(1) && NAV.some(([k]) => k === location.hash.slice(1))) ? location.hash.slice(1) : 'flow';
  wire();
  load().catch(fail);
})();
