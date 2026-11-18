  // ==== 사용 안내: what each screen is for, in the order of the menu, beside the introduction video ==================
  // A screen says what is done on it in its own head; this is the map of them. A row leads to its screen.
  const GUIDE_MAP = [
    ['시작', [['ontologies', '온톨로지 선택', '작업 온톨로지 선택'],
      ['ontology-new', '온톨로지 만들기', '도메인 팩 · 기존 온톨로지 · 파일 · 빈 온톨로지로 생성'],
      ['home', '홈', '성숙도 · 구성요소 현황 · 도메인 Object · 할 일'],
      ['catalog', '자료 업로드', '정책서 · 정의서 · 테이블 파일 업로드'],
      ['ai', 'AI 초안 생성', 'Entity · Property · Relation · 규칙 · 검증 질문 초안 생성'],
      ['search', '검색 · 질문', '정의 · 규칙 · 용어 · 자료 통합 검색과 근거 기반 답변']]],
    ['Semantic Layer', [['semrules', '규칙', 'AXIOM · Custom · Standard 규칙 관리와 판정 시험'],
      ['ruleagent', '규칙 초안', '규칙 초안 검토 · 승인']]],
    ['Ontology', [['objmgr', 'Object', 'Object 정의 · 성숙도 · 담당자'],
      ['objects', 'Entity', 'Entity · Property · Restriction · 상태 전이'],
      ['model', '그래프 탐색', 'Relation 그래프 조회 · 편집'],
      ['lexicon', '용어 사전', '용어 · 표현 관계 · 고객 표기'],
      ['concepts', '개념 초안', 'Entity · Property · Relation 초안 검토 · 승인'],
      ['library', '모듈 라이브러리', '계층 구조 · 규모 · 버전 · 모듈 · 내보내기'],
      ['changes', '변경 요청 · 버전', '변경 요청 등록 · 회귀 테스트 · 승인 · 배포 · 롤백']]],
    ['Data Binding', [['db', '데이터 소스', '업무 DB 읽기 전용 연결 · 테이블 범위'],
      ['sources', 'Mapping', 'Property ↔ 컬럼 · 코드 Mapping과 차이 검사'],
      ['bind', 'Entity Binding', 'Entity · Property ↔ 테이블 · 컬럼 Binding'],
      ['query', '질의', '등록 질의 · 질의 언어 변환 · 접근 정책별 실행'],
      ['actions', 'Action', 'Action 정의 · 전제조건 · 승인 기준 · 시험']]],
    ['Quality', [['check', '검증 질문', '검증 질문 · 정답 · 평가 방법'],
      ['flow', '검증', '검증 실행 · 오답 원인 · 통과 조건']]],
    ['Operations', [['adapters', '저장소 · 엔진', '저장소 · 질의 언어 · 추론 엔진 · 임베딩 상태'],
      ['connect', '연동 · API', 'MCP · REST · OpenAPI 연동과 API 실행'],
      ['roles', '접근 정책', '연동 대상별 정의 · 데이터 · Action 범위'],
      ['monitor', '파이프라인 관제', '처리 상태 · 결정 로그 · 알림 기준'],
      ['evidence', '근거 지도', 'Object × 자료 근거 · 근거 누락']]],
    ['관리 · 계정', [['settings', '온톨로지 설정', '이름 · 명명 방식 · 품질 목표 · 승인 정책 · 내보내기'],
      ['members', '멤버 · 권한', '사용자 · 작업 역할별 권한'],
      ['sys-overview', '시스템 관리', '사용자 · 인증 · 도메인 팩 · 기준 어휘 · AI 운영 · 감사 로그 · 시스템'],
      ['inbox', '할 일 · 알림', '승인 요청 · 알림 처리'],
      ['me', '내 계정', '역할 · 로그아웃 · 세션 초기화']]],
  ];

  screen('guide', { area: 'bare', word: '사용 안내', crumb: ['사용 안내'],
    view: () => {
      const g = S.guide || { video: '', chapters: [] };
      const row = ([key, word, what]) => (mayOpen(key) ? `<a class="k-row" href="#${key}"><span class="k-col"><span class="k-ink k-14 k-b">${esc(word)}</span><span class="k-s">${esc(what)}</span></span>${ki('chevR', 16, 1.75)}</a>` : '');
      const parts = GUIDE_MAP.map(([part, rows]) => { const body = rows.map(row).join(''); return body ? `<section class="k-card"><div class="k-ch"><h2>${esc(part)}</h2></div>${body}</section>` : ''; }).join('');
      const head = kHead('사용 안내', '화면별 기능과 소개 영상');
      if (!g.video) return `${head}<div class="k-cols"><div class="k-c3">${parts}</div></div>`;
      const chapters = g.chapters.map((c, i) => `<button class="k-row tight gch" data-act="seek" data-t="${c.t}" data-i="${i}"><span class="k-h sb"><span class="k-14 k-b">${esc(c.chapter)} · ${esc(c.title)}</span><span class="k-code k-mut">${clock(c.t)}</span></span><span class="k-s">${esc((c.captions || [])[0] || '')}</span></button>`).join('');
      return `${head}<div class="k-cols"><div class="k-c3"><section class="k-card" style="overflow:hidden"><video id="gvideo" controls preload="metadata" playsinline src="${esc(g.video)}" style="display:block;width:100%;background:#171717"></video>
          <div class="k-ch"><h2>영상 목차</h2><span class="k-s">${g.chapters.length}개 장</span></div><div style="max-height:420px;overflow:auto">${chapters}</div></section></div>
        <div class="k-c2">${parts}</div></div>`;
    },
    after: () => mountGuide() });
