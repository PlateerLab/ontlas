  // ==== 사용 안내: what each screen is for, in the order of the menu, beside the introduction video ==================
  // A screen says what is done on it in its own head; this is the map of them. A row leads to its screen.
  const GUIDE_MAP = [
    ['시작', [['ontologies', '온톨로지 선택', '작업할 온톨로지를 고릅니다. 고르면 그 온톨로지의 홈으로 들어갑니다'],
      ['ontology-new', '온톨로지 만들기', '도메인 팩, 기존 온톨로지, 파일 가져오기, 빈 상태에서 새 온톨로지를 만듭니다'],
      ['home', '홈', '성숙도, 구성요소 현황, 도메인 Object, 할 일, 시작하기 단계를 봅니다'],
      ['catalog', '자료 업로드', '정책서, 정의서, 테이블 파일을 올리고 AI 초안 생성으로 이어갑니다'],
      ['ai', 'AI 초안 생성', '올린 자료로 Entity, Property, Relation, 규칙, 검증 질문 초안을 만들어 검토함으로 보냅니다'],
      ['search', '검색 · 질문', '정의, 규칙, 용어, 자료를 한 번에 찾고 질문에 근거와 함께 답합니다']]],
    ['시멘틱 매니저', [['semrules', '규칙', 'AXIOM › Custom › Standard 순서의 규칙을 관리하고 값을 넣어 판정을 시험합니다'],
      ['ruleagent', '규칙 초안', '자료에서 만든 규칙 초안을 검토하고 승인합니다']]],
    ['온톨로지 매니저', [['objmgr', '오브젝트 관리', 'Object의 정의, 명명, 성숙도, 담당자를 관리합니다'],
      ['objects', '엔티티 관리', 'Entity, Property, Restriction, 상태 전이를 관리합니다'],
      ['model', '그래프 탐색', 'Relation을 그래프로 보고 고칩니다'],
      ['lexicon', '용어사전', '용어, 표현 관계, 고객 표기를 관리합니다'],
      ['concepts', '개념 초안', '자료에서 만든 개념과 관계 초안을 검토하고 승인합니다'],
      ['library', '온톨로지', '계층 구조, 규모, 버전, 모듈 라이브러리를 보고 내보냅니다'],
      ['changes', '변경 요청 · 버전', '변경 요청을 올려 회귀 테스트와 검토를 거쳐 버전으로 배포하고, 이전 버전으로 되돌립니다']]],
    ['데이터 바인더', [['db', '데이터 소스 연결', '업무 DB를 읽기 전용으로 연결하고 읽을 테이블을 확인합니다'],
      ['sources', '데이터 매핑', 'Property와 컬럼, 코드의 매핑을 정하고 차이를 검사합니다'],
      ['bind', 'Entity 바인딩', 'Entity와 Property를 테이블과 컬럼에 바인딩하고 미리 봅니다'],
      ['query', '쿼리', '등록 쿼리를 정의하고 저장소 언어로 변환하며 접근 정책별로 실행합니다'],
      ['actions', '액션', '액션의 전제조건과 승인 기준을 정하고 시험합니다']]],
    ['품질 관리', [['check', '검증질문 관리', '검증 질문 세트와 정답, 평가 방법을 관리합니다'],
      ['flow', '검증', '검증을 실행하고 오답 원인과 통과 조건을 봅니다']]],
    ['운영', [['adapters', '저장소 · 엔진', '저장소, 쿼리 언어, 추론 엔진, 임베딩의 상태를 측정합니다'],
      ['connect', '연동 · API', 'XGEN과 외부 Agent에 적용하는 방법(MCP · REST · 파일)과 엔드포인트를 복사하고 실행합니다'],
      ['roles', '접근 정책', '연동 대상별로 정의, 데이터, 액션 범위를 정합니다'],
      ['monitor', '파이프라인 모니터링', '처리 상태와 결정 로그, 알림 기준을 봅니다'],
      ['evidence', '근거 지도', 'Object와 자료의 근거 관계를 보고 근거가 빠진 곳을 찾습니다']]],
    ['관리 · 계정', [['settings', '온톨로지 설정', '이름, 명명 방식, 품질 목표, 승인 정책을 보고 내보냅니다'],
      ['members', '멤버 · 권한', '사용자와 작업 역할별 권한을 봅니다'],
      ['sys-overview', '시스템 관리', '사용자, 인증, 도메인 팩, 기준 어휘, AI 운영, 감사 로그, 시스템 상태를 관리합니다'],
      ['inbox', '할 일 · 알림', '승인 요청과 알림을 처리합니다'],
      ['me', '내 계정', '역할을 확인하고 로그아웃하거나 세션을 초기화합니다']]],
  ];

  screen('guide', { area: 'bare', word: '사용 안내', crumb: ['사용 안내'],
    view: () => {
      const g = S.guide || { video: '', chapters: [] };
      const row = ([key, word, what]) => (known(key) && (!V2[key] || !V2[key].may || V2[key].may()) ? `<a class="k-row" href="#${key}"><span class="k-col"><span class="k-ink k-14 k-b">${esc(word)}</span><span class="k-s">${esc(what)}</span></span>${ki('chevR', 16, 1.75)}</a>` : '');
      const parts = GUIDE_MAP.map(([part, rows]) => { const body = rows.map(row).join(''); return body ? `<section class="k-card"><div class="k-ch"><h2>${esc(part)}</h2></div>${body}</section>` : ''; }).join('');
      const head = kHead('사용 안내', g.video ? '화면이 무엇을 하는 곳인지와 소개 영상입니다. 줄을 누르면 그 화면으로 갑니다.' : '화면이 무엇을 하는 곳인지 봅니다. 줄을 누르면 그 화면으로 갑니다.');
      if (!g.video) return `${head}<div class="k-cols"><div class="k-c3">${parts}</div></div>`;
      const chapters = g.chapters.map((c, i) => `<button class="k-row tight gch" data-act="seek" data-t="${c.t}" data-i="${i}"><span class="k-h sb"><span class="k-14 k-b">${esc(c.chapter)} · ${esc(c.title)}</span><span class="k-code k-mut">${clock(c.t)}</span></span><span class="k-s">${esc((c.captions || [])[0] || '')}</span></button>`).join('');
      return `${head}<div class="k-cols"><div class="k-c3"><section class="k-card" style="overflow:hidden"><video id="gvideo" controls preload="metadata" playsinline src="${esc(g.video)}" style="display:block;width:100%;background:#171717"></video>
          <div class="k-ch"><h2>영상 목차</h2><span class="k-s">${g.chapters.length}개 장</span></div><div style="max-height:420px;overflow:auto">${chapters}</div></section></div>
        <div class="k-c2">${parts}</div></div>`;
    },
    after: () => mountGuide() });
