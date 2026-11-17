  // ==== 홈, AI 초안 생성, 검색 · 질문, 자료 업로드 =================================================================
  // The home says where the ontology stands (maturity, the four parts, the Objects, what waits, the steps of getting
  // started). The other three are reached from the menu and the bar on top: making drafts, asking, bringing files in.

  S.h2 = { busy: false, err: '', find: null, findBusy: false, findOf: '', cat: 'all',
    ai: { st: null, busy: false, run: false, said: '', kinds: { concepts: true, questions: true, rules: false }, target: '', doc: '', section: '', sections: [], guide: false },
    up: { staged: [], use: '', then: true, busy: false, links: null } };

  // ---- 홈 ----------------------------------------------------------------------------------------------------------

  const hmSum = () => (S.home.ov && S.home.ov.steps ? S.home.ov : null);  // the overview with the home's own facts beside it
  async function hmLoad() {
    const h = S.h2;
    if (h.busy) return;
    h.busy = true;
    try { S.home.ov = await api('home/summary'); h.err = ''; } catch (e) { h.err = e.message || String(e); }
    h.busy = false;
    if (S.tab === 'home') render();
  }

  const HM_LEVEL = [
    ['L0 개념', 'Object · Entity 정의, 계층, 한글@영어 표기', '정책서 · 문서'],
    ['L1 논리', 'Relation, 논리 Property, Restriction, AXIOM · Standard 규칙, 정의형 평가 질문', '정책서 · 메타데이터 · 소스코드'],
    ['L2 연결', '컬럼 · 코드 매핑, 실시간 값 조회', '데이터 바인더'],
    ['L3 검증', '정의 · 실제 차이 검사, 판정 일치율, 거래 값 정확도', '인스턴스 데이터 · 로그'],
  ];

  // how far the ontology has come, one column a level: the Objects (the Entities where none is filed) that reached it
  function hmMaturity(sum) {
    const named = sum.objects.filter((o) => o.name && o.count);
    const unit = named.length ? named.map((o) => o.level) : sum.objects.flatMap((o) => o.entities.map((e) => e.level));
    const total = unit.length, linked = !noSource();
    const col = ([word, what, from], l) => {
      const got = unit.filter((x) => x >= l).length, waits = l >= 2 && !linked && !got;
      const share = total ? Math.round((got / total) * 100) : 0;
      const bar = !total || !got ? 'background:var(--row)' : got === total ? 'background:var(--blue)' : `background:linear-gradient(90deg,#2563EB ${share}%,#E6E6E8 ${share}%)`;
      const state = !total ? '<span class="k-s">정의 전</span>' : got === total ? '<span class="k-ok k-13">완료</span>' : waits ? '<span class="k-s">연결 후</span>'
        : got ? `<span class="k-code k-blue">${got} / ${total}</span>` : '<span class="k-s">시작 전</span>';
      const dim = waits || !total ? ' k-mut' : '';
      return `<div class="k-v"><span class="hm-bar" style="${bar}"></span><span class="hm-lvh"><b class="k-b k-18${dim}">${word}</b>${state}</span>
        <span class="${dim ? 'k-mut' : 'k-i3'} k-14" style="line-height:1.55">${what}</span><span class="k-s">${from}</span></div>`;
    };
    return `<section class="k-card" aria-labelledby="hm-mat"><div class="k-h base sb" style="padding:20px 24px 0"><h2 class="k-h2" id="hm-mat">성숙도</h2><span class="k-s">인스턴스 데이터 없이 L1까지 · ERD · 공통코드 · API 명세 · 소스코드 같은 메타데이터는 사용</span></div>
      <div class="hm-mat"><p class="k-s hm-matg" style="grid-column:1 / span 2">데이터 없이 · 표준</p><p class="k-s hm-matg" style="grid-column:3 / span 2">데이터 바인더 연결 후 · 고객사별</p>${HM_LEVEL.map(col).join('')}</div></section>`;
  }

  // the four parts the ontology is built from: one number each, and what needs a look
  function hmParts(sum) {
    const by = Object.fromEntries(sum.components.map((c) => [c.id, c]));
    const r = sum.rules, w = sum.waiting, sem = by.semantic, ont = by.ontology, bnd = by.binding, qa = by.qa;
    const linked = !!(bnd.source && bnd.source.connected);
    const tone = { ok: 'k-ok', attention: 'k-warn' };
    const part = (href, word, state, n, unit, sub, dim) => `<a class="k-v g4 k-ink hm-part" href="#${href}"><span class="k-h sb nw"><span class="k-i3 k-14">${word}</span>${state}</span>
      <span class="k-big${dim ? ' mut' : ''}">${count(n)} <span class="k-s">${esc(unit)}</span></span><span class="k-s">${esc(sub)}</span></a>`;
    const semState = r.legal ? `<span class="k-warn k-13">법무 검토 ${count(r.legal)}</span>` : r.review ? `<span class="k-warn k-13">검토 중 ${count(r.review)}</span>` : `<span class="${tone[sem.status] || 'k-mut'} k-13">${esc(sem.status_label)}</span>`;
    const layers = ['axiom', 'custom', 'standard'].filter((k) => r.layers[k]).map((k) => `${LAYER_WORD[k]} ${count(r.layers[k])}`).join(' · ');
    const ontState = w.concepts ? `<span class="k-blue k-13">초안 ${count(w.concepts)}</span>` : `<span class="${tone[ont.status] || 'k-mut'} k-13">${esc(ont.status_label)}</span>`;
    const filed = ont.counts.objects > 0;
    const check = bnd.check && (bnd.check.errors || bnd.check.warnings);
    const bndState = `<span class="${linked ? (check ? 'k-warn' : 'k-ok') : 'k-mut'} k-13">${linked ? esc(bnd.status_label) : '미연결'}</span>`;
    const kind = linked ? BACKEND_KIND[String(bnd.source.kind || '').toLowerCase()] || bnd.source.kind || '' : '';
    const acc = qa.accuracy === null || qa.accuracy === undefined ? null : qa.accuracy;
    const qaState = acc === null ? `<span class="k-mut k-13">${esc(qa.status_label)}</span>` : `<span class="${acc < 1 ? 'k-warn' : 'k-ok'} k-13">정답률 ${pct(acc)}</span>`;
    return `<section class="k-card hm-parts" aria-label="네 구성요소">
      ${part('semrules', '시멘틱 매니저', semState, r.cards, '규칙 카드', [layers, r.draft ? `초안 ${count(r.draft)} 대기` : ''].filter(Boolean).join(' · ') || '규칙 없음')}
      ${part('objmgr', '온톨로지 매니저', ontState, filed ? ont.counts.objects : ont.counts.entities, filed ? 'Object' : 'Entity', `${filed ? `Entity ${count(ont.counts.entities)} · ` : ''}Property ${count(ont.counts.properties)} · Relation ${count(ont.counts.relations)}`)}
      ${part('db', '데이터 바인더', bndState, bnd.counts.bound, '매핑 명세', linked ? `${kind} · 테이블 ${count(bnd.counts.tables)}${check ? ` · 오류 ${count(bnd.check.errors)} · 경고 ${count(bnd.check.warnings)}` : ''}` : '연결하면 L2 · L3 검증이 열립니다', !linked)}
      ${part('flow', '품질 관리', qaState, qa.counts.questions, '검증 질문', acc === null ? '검증을 실행하면 정답률을 측정합니다' : `근거 제시율 ${pct(qa.grounded)}${linked ? (qa.gates ? ` · 통과 조건 ${qa.gates.met} / ${qa.gates.all}` : '') : ' · 판정 일치율은 연결 후'}`)}</section>`;
  }

  function hmObjects(sum) {
    const named = sum.objects.filter((o) => o.name), loose = sum.objects.find((o) => !o.name);
    const chip = (o) => (o.count
      ? `<button class="hm-obj" data-act="homeobj" data-name="${esc(o.name)}" title="${esc(o.description || '')}">${esc(o.label)}<span class="k-mut">@${esc(o.name)}</span><span class="k-code k-blue">L${o.level}</span></button>`
      : `<button class="hm-obj dash" data-act="homeobj" data-name="${esc(o.name)}" title="${esc(o.description || '')}">${esc(o.label)}<span class="k-mut">@${esc(o.name)}</span><span class="k-code k-mut">Entity 없음</span></button>`);
    const body = named.length ? `<div class="k-wrap g8">${named.map(chip).join('')}${loose ? `<a class="hm-obj dash" href="#objects">Object 미지정<span class="k-mut">Entity ${count(loose.count)}</span></a>` : ''}</div>
      <p class="k-p s">L0 ~ L3은 Object에 속한 Entity 가운데 가장 낮은 단계입니다</p>`
      : `<p class="k-p s">${loose ? `Entity ${count(loose.count)}개가 Object 없이 정의되어 있습니다. 오브젝트 관리에서 Object를 만들어 묶습니다.` : '아직 정의한 Object가 없습니다.'}</p>`;
    return `<section class="k-card pad k-v g16" aria-labelledby="hm-map" style="flex:3 1 520px"><div class="k-h sb"><h2 class="k-h2" id="hm-map">도메인 Object ${count(named.length)}개</h2><a class="k-lnk" href="#objmgr">오브젝트 관리${ki('chevR', 14, 1.75)}</a></div>${body}</section>`;
  }

  // what waits on a person, each row leading to where it is handled
  const HM_TODO = { action: '승인', change: '배포', conflict: '차이', check: '점검', workspace: '변경', draft: '초안' };
  function hmTodoRow(x) {
    const sub = `${HM_TODO[x.kind] || x.kind} · ${x.kind === 'change' ? `${x.by} 작성 · 회귀 테스트 ${x.passed ? '통과' : '미통과'}` : x.kind === 'action' ? `${x.by} 요청 · ${x.change || ''}` : x.detail || ''}`;
    const body = `<span class="k-col"><span class="k-14">${esc(x.title)}</span><span class="k-s">${esc(sub)}</span></span>${ki('chevR', 16, 1.75)}`;
    if (x.kind === 'change') return `<button class="k-row" data-act="ibchange" data-id="${esc(x.id)}">${body}</button>`;
    if (x.kind === 'check') return `<button class="k-row" data-act="issopen" data-key="bind">${body}</button>`;
    if (x.kind === 'conflict') return `<button class="k-row" data-act="issopen" data-key="conflict:${esc(x.id)}">${body}</button>`;
    return `<a class="k-row" href="#${x.kind === 'draft' ? (known('concepts') ? 'concepts' : 'data') : x.kind === 'workspace' ? 'changes' : 'inbox'}">${body}</a>`;
  }
  function hmTodo() {
    const h = S.home, box = h.box;
    const n = box ? box.counts.assigned : 0;
    const head = `<div class="k-h base" style="padding:20px 20px 12px"><h2 class="k-h2" id="hm-todo">할 일</h2>${box ? `<span class="k-code k-mut">${count(n)}</span>` : ''}<a class="k-lnk k-push" href="#inbox">전체 보기${ki('chevR', 14, 1.75)}</a></div>`;
    const rows = h.err ? '<div class="k-row"><span class="k-col"><span class="k-14">할 일을 불러오지 못했습니다</span><span class="k-s">잠시 뒤 다시 시도해 주세요.</span></span><button class="k-btn sm" data-act="ibretry">다시 시도</button></div>'
      : !box ? '<p class="k-cf line">불러오는 중입니다.</p>'
        : inboxShown('assigned').slice(0, 5).map(hmTodoRow).join('') || '<p class="k-cf line">처리할 일이 없습니다. 승인, 변경 검토, 충돌 선택이 생기면 여기에 모입니다.</p>';
    return `<section class="k-card" aria-labelledby="hm-todo" style="flex:2 1 360px">${head}${rows}</section>`;
  }

  const HM_STEP = { upload: ['자료 업로드', 'catalog'], drafts: ['초안 승인', 'ruleagent'], questions: ['검증 질문', 'check'], version: ['첫 버전 배포', 'changes'], agents: ['에이전트 연동', 'connect'], source: ['데이터 소스', 'db'] };
  const HM_STATE = { done: ['k-ok', '완료'], doing: ['k-blue', '진행 중'], todo: ['k-mut', '시작 전'], optional: ['k-mut', '선택'] };
  function hmStepSay(x) {
    if (x.id === 'upload') return x.files ? [[x.documents, '문서'], [x.definitions, '정의서'], [x.data, '데이터']].filter(([n]) => n).map(([n, w]) => `${w} ${count(n)}`).join(' · ') || `자료 ${count(x.files)}건` : '올린 자료 없음';
    if (x.id === 'drafts') return x.state === 'doing' ? [x.waiting ? `초안 ${count(x.waiting)}건 대기` : '', x.changes ? `변경 요청 ${count(x.changes)}건 검토 중` : '', x.edits ? `작성 중인 변경 ${count(x.edits)}건` : ''].filter(Boolean).join(' · ') : x.state === 'done' ? '대기 중인 초안 없음' : '정의를 만들면 시작';
    if (x.id === 'questions') return x.questions ? `${count(x.questions)}개 등록${x.accuracy === null || x.accuracy === undefined ? '' : ` · 정답률 ${pct(x.accuracy)}`}` : '등록한 질문 없음';
    if (x.id === 'version') return x.state === 'done' ? `${x.label} 배포됨` : '정의를 만들면 배포';
    if (x.id === 'agents') return x.rest ? 'REST API · MCP 사용 가능' : 'API 꺼짐 · 서버 옵션으로 켬';
    return x.state === 'done' ? `${BACKEND_KIND[String(x.kind).toLowerCase()] || x.kind || '원천'} 연결됨` : '선택 · L2부터 필요';
  }
  function hmSteps(sum) {
    const w = sum.waiting;
    const go = (x) => (x.id === 'drafts' ? (w.rules || !w.concepts ? (w.rules || !sum.changes.pending ? 'ruleagent' : 'changes') : known('concepts') ? 'concepts' : 'data') : HM_STEP[x.id][1]);
    const step = (x) => { const [cls, word] = HM_STATE[x.state] || HM_STATE.todo;
      return `<a class="k-v g4 k-ink hm-step${x.state === 'doing' ? ' now' : ''}" href="#${go(x)}"><span class="k-h sb base nw"><span class="k-14">${HM_STEP[x.id][0]}</span><span class="${cls} k-13">${word}</span></span><span class="k-s">${esc(hmStepSay(x))}</span></a>`; };
    return `<section class="k-card hm-steps" aria-labelledby="hm-sch"><div class="k-v g4" style="padding:16px 20px"><h2 class="k-h2" id="hm-sch">시작하기</h2><span class="k-s">${sum.steps.filter((x) => x.state === 'done').length} / ${sum.steps.length} 단계</span></div>${sum.steps.map(step).join('')}</section>`;
  }

  // the dates the studio file names, where it names any
  function hmDates(sum) {
    const ms = sum.milestones || [];
    if (!ms.length) return '';
    const row = (x) => `<div class="k-row"><span class="k-col"><span class="k-14">${esc(x.label)}</span>${x.detail ? `<span class="k-s">${esc(x.detail)}</span>` : ''}</span><span class="k-h end"><span class="k-code k-mut">${esc(x.date || '일정 미정')}</span>${x.state === 'next' && x.days !== null ? `<span class="k-chip b">D-${x.days}</span>` : x.state === 'past' ? '<span class="k-chip">지남</span>' : ''}</span></div>`;
    return `<section class="k-card" aria-labelledby="hm-dates"><div class="k-ch"><h2 id="hm-dates">일정</h2><span class="k-s">${count(ms.length)}건</span></div>${ms.map(row).join('')}</section>`;
  }

  function hmView() {
    const sum = hmSum(), st = S.st;
    const lib = (st.libraries || []).find((x) => x.id === st.library_id);
    const name = (sum && sum.name) || (lib && lib.label) || st.title || '온톨로지';
    if (!sum) return kHead(name, '') + (S.h2.err ? kEmpty('일시적인 문제가 있습니다', S.h2.err, '<button class="k-btn" data-act="hmRetry">다시 시도</button>') : '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>');
    const m = sum.maturity, ch = sum.changes, w = sum.waiting;
    const meta = [`${sum.version.label} 배포`, ch.pending ? `변경 요청 ${count(ch.pending)}건 검토 중` : '', ch.draft ? `작성 중인 변경 ${count(ch.edits)}건` : ''].filter(Boolean).join(' · ');
    const bound = (sum.components.find((c) => c.id === 'binding') || { counts: {} }).counts.bound || 0;
    const filed = m.objects ? `Object ${count(m.objects)}개, Entity ${count(m.entities)}개` : `Entity ${count(m.entities)}개`;
    const lead = !m.entities ? '아직 정의가 없습니다. 자료를 올리거나 표준 도메인 팩에서 시작합니다.'
      : noSource() ? `데이터 소스 연결 없이 정의와 규칙을 구축하고 있습니다. ${filed}를 정의했습니다.`
        : `데이터 소스에 연결되어 있습니다. ${filed}를 정의했고 Entity ${count(bound)}개가 테이블에 바인딩되어 있습니다.`;
    const review = w.all ? `<a class="k-btn pri" href="#${w.rules ? 'ruleagent' : w.concepts ? (known('concepts') ? 'concepts' : 'data') : 'lexicon'}">초안 ${count(w.all)}건 검토${ki('arrow', 16, 1.75)}</a>` : '';
    const head = kHead(name, lead, `<a class="k-btn" href="#flow">${ki('check', 16, 1.75)}검증 실행</a>${review}`, meta);
    if (!m.entities) {
      return `${head}${kEmpty('아직 자료가 없습니다', '정책서나 정의서를 올리면 규칙과 개념 초안을 AI가 만듭니다. 표준 도메인 팩으로 시작할 수도 있습니다.',
        `${canEdit() ? `<a class="k-btn pri" href="#catalog">${ki('upload', 16, 1.75)}자료 업로드</a><button class="k-btn" data-act="startlib">모듈 라이브러리에서 도메인 팩 적용</button><button class="k-btn" data-act="startmodel">직접 정의</button>` : ''}`)}${hmSteps(sum)}${kNext([['ai', 'AI 초안 생성'], ['changes', '변경 요청 · 버전'], ['evidence', '근거 지도'], ['flow', '검증'], ['connect', '연동 · API']])}`;
    }
    return `${head}${hmMaturity(sum)}${hmParts(sum)}<div class="hm-row">${hmObjects(sum)}${hmTodo()}</div>${hmSteps(sum)}${hmDates(sum)}
      ${kNext([['ai', 'AI 초안 생성'], ['changes', '변경 요청 · 버전'], ['evidence', '근거 지도'], ['flow', '검증'], ['connect', '연동 · API']])}`;
  }

  screen('home', {
    area: 'work', word: '홈', crumb: ['홈'], view: hmView,
    after: () => {
      if (!hmSum() && !S.h2.busy && !S.h2.err) hmLoad();
      if (!S.home.box && !S.home.busy && !S.home.err) loadInbox();
      if (!S.fl) loadHomeFlow();  // the quality part reads the measurement the flow takes
    },
  });
  Object.assign(ACT, { hmRetry: () => { S.h2.err = ''; render(); } });

  // ---- 검색 · 질문 --------------------------------------------------------------------------------------------------
  // One box: what is typed is looked up in the definitions, the rules, the terms and the documents, and a question is
  // answered by the rule engine with what the answer stands on. The asking itself is searchNow(), as before.

  const SQ_CAT = [['all', '전체'], ['answer', '답'], ['def', '정의'], ['rule', '규칙'], ['term', '용어'], ['doc', '자료']];
  const SQ_SHOWN = 8;

  async function sqFind(q) {
    const h = S.h2;
    h.findBusy = true; h.findOf = q;
    try { h.find = await api('home/find?q=' + encodeURIComponent(q)); } catch (e) { h.find = { error: e.message, found: [], total: 0, counts: {} }; }
    h.findBusy = false;
    if (S.tab === 'search') render();
  }

  // where a found thing is looked at, with the way the older screens open it where there is one
  function sqRow(x) {
    const body = `<span class="k-col"><span class="k-ink k-14">${esc(x.title)}</span>${x.sub ? `<span class="k-s">${esc(x.sub)}</span>` : ''}</span><span class="k-h end"><span class="k-chip">${esc(x.word)}</span></span>${ki('chevR', 16, 1.75)}`;
    if (x.kind === 'object') return `<button class="k-row" data-act="srobj" data-obj="${esc(x.id.slice(7))}">${body}</button>`;
    if (x.kind === 'rule') { const name = x.id.slice(5), at = name.indexOf('.'); return `<button class="k-row" data-act="rulego" data-dec="${esc(name.slice(0, at))}" data-rule="${esc(name.slice(at + 1))}">${body}</button>`; }
    if (x.kind === 'query') return `<a class="k-row" href="#query?query=${encodeURIComponent(x.id.slice(6))}">${body}</a>`;
    const go = x.kind === 'document' ? (known('evidence') ? 'evidence' : 'docs') : x.go;
    return `<a class="k-row" href="#${go}">${body}</a>`;
  }

  function sqFound(cat) {
    const f = S.h2.find, asked = S.sr.res && S.sr.res.question;
    if (!f || S.h2.findOf !== asked) return '<section class="k-card"><div class="k-ch"><h2>찾은 것</h2></div><p class="k-cf line">찾는 중입니다.</p></section>';
    if (f.error) return `<section class="k-card"><div class="k-ch"><h2>찾은 것</h2></div><p class="k-cf line">${esc(f.error)}</p></section>`;
    const rows = cat === 'all' ? f.found : f.found.filter((x) => x.group === cat);
    const shown = cat === 'all' && !S.h2.more ? rows.slice(0, SQ_SHOWN) : rows;
    const more = shown.length < rows.length ? `<div class="k-cb" style="padding-top:12px"><button class="k-lnk flat" data-act="sqMore">${count(rows.length - shown.length)}건 더 보기${ki('chevD', 14, 1.75)}</button></div>` : '';
    return `<section class="k-card" aria-labelledby="sq-found"><div class="k-ch"><h2 id="sq-found">찾은 것</h2><span class="k-s">${count(f.total)}건 중 ${count(shown.length)}건</span></div>
      ${shown.map(sqRow).join('') || '<p class="k-cf line">조건에 맞는 항목이 없습니다. 필터를 지우거나 검색어를 바꿔 보세요.</p>'}${more}</section>`;
  }

  // the answer, as the rule engine gave it: how the question was taken, the verdict, what each layer said, what it rests on
  function sqAnswer(r) {
    const res = r.res, more = r.more, d = pickedDecision(res);
    const q = (more && more.ok && more.query) || res.query;
    const badge = answerBadge(res, more)[1];
    const fixable = !!(d || res.record);
    const chip = (word, k) => (fixable ? `<button class="k-chip w sq-fix" data-act="srfix" data-k="${k}" aria-expanded="${!!r.fix}">${esc(word)}${ki('chevD', 12, 1.75)}</button>` : `<span class="k-chip">${esc(word)}</span>`);
    const took = d ? [chip(`${d.target_label} · ${d.key}`, 'key'), chip(`판정 · ${d.label}`, 'decision'), chip(`기준 시각 · ${String(d.at).replace('T', ' ')}`, 'at')]
      : res.record ? [chip(`${res.record.label} · ${res.record.key}`, 'key'), ...((res.choices || []).length ? [chip('판정 · 없음', 'decision')] : [])]
        : q ? [`<span class="k-chip">등록 쿼리 · ${esc(q.label)}</span>`] : [`<span class="k-chip">${res.route === 'none' ? '찾을 대상 없음' : '자료와 규칙에서 찾기'}</span>`];
    const understood = `<div class="k-h g6"><span class="k-s">이렇게 이해했습니다</span>${took.join('')}</div>${r.fix && fixable ? fixRow(res) : ''}`;
    const wait = r.moreBusy ? '<p class="k-note">언어 모델이 찾은 근거로 답을 다듬는 중입니다. 1분 정도 걸릴 수 있습니다.</p>' : '';
    const failed = more && !more.ok ? `<p class="k-note warn">${esc(more.error)}</p>` : '';
    let body = '';
    if (d) {
      const layers = ((d.path || {}).layers || []).map((x) => `<span class="k-h nw" style="align-items:baseline">${kLayer(x.layer)}<span>${esc(!x.rules ? '해당 규칙 없음' : [x.fired.join(' · '), x.said].filter(Boolean).join(' · '))}</span></span>`).join('');
      const src = (d.path || {}).source || {};
      const cites = [...new Set(d.rules.map((x) => x.cite).filter(Boolean))];
      const acts = d.actions.map((a) => `<button class="k-btn sm" data-act="sract" data-type="${esc(d.target)}" data-key="${esc(d.key)}" data-name="${esc(a.name)}"${a.ready ? '' : ' disabled'}>${esc(a.label)}하기</button>`).join('');
      const fb = r.fb === 'saved' ? `<span class="k-s">검증 질문을 작성 중인 변경 요청에 담았습니다.</span><a class="k-lnk k-push" href="#check">검증질문 관리${ki('chevR', 14, 1.75)}</a>`
        : `<span class="k-s">이 답이 맞나요?</span><button class="k-btn${r.fb === 'good' ? ' sel' : ''}" data-act="srgood" aria-pressed="${r.fb === 'good'}">맞아요</button><button class="k-btn${r.fb === 'bad' ? ' sel' : ''}" data-act="srbad" aria-pressed="${r.fb === 'bad'}">틀려요</button>
          ${canEdit() ? `<button class="k-lnk k-push" data-act="srsave">검증 질문으로 저장${ki('chevR', 14, 1.75)}</button>` : ''}`;
      body = `${understood}<p class="k-b k-18" style="margin:0;line-height:1.5">${esc(d.verdict)}</p>${d.reason ? `<p class="k-p">${esc(d.reason)}</p>` : ''}
        ${layers ? `<div class="k-v k-14" style="gap:6px">${layers}</div>` : ''}
        <div class="k-wrap">${cites.map((c) => `<span class="k-m12" style="white-space:nowrap"><span aria-hidden="true">§</span> ${esc(c)}</span>`).join('')}${src.module_label ? `<span class="k-code k-mut">${esc(src.module_label)} ${esc(src.version || '')}</span>` : ''}</div>
        <div class="k-h"><button class="k-btn sm" data-act="rec" data-type="${esc(d.target)}" data-key="${esc(d.key)}">${esc(d.target_label)} ${esc(d.key)} 열기</button><button class="k-btn sm" data-act="srsim" data-name="${esc(d.name)}" data-key="${esc(d.key)}">조건 바꿔 보기</button>${acts}</div>
        ${r.fb === 'bad' ? '<p class="k-note warn">판정에 쓴 값과 규칙을 확인해 주세요. [조건 바꿔 보기]에서 어떤 값일 때 답이 바뀌는지 볼 수 있습니다.</p>' : ''}
        <div class="k-pha sq-fb">${fb}</div>`;
    } else if (res.record) {
      const rec = res.record;
      body = `${understood}<p class="k-b k-18" style="margin:0;line-height:1.5">${esc(rec.label)} ${esc(rec.key)}</p>
        <div class="k-x sq-in"><table class="k-t s"><tbody>${rec.values.map((v) => `<tr><td class="mut" style="width:40%">${esc(v.label)}</td><td>${typeof v.value === 'boolean' ? yesNo(v.value) : show(v.value)}</td></tr>`).join('')}</tbody></table></div>
        <div class="k-h"><button class="k-btn sm" data-act="rec" data-type="${esc(rec.type)}" data-key="${esc(rec.key)}">레코드 열기</button><button class="k-btn sm" data-act="srobj" data-obj="${esc(rec.type)}">Entity 정의 보기</button></div>`;
    } else if (q) {
      const cell = (v) => (v === null || v === undefined ? '' : show(v));
      body = `${understood}<p class="k-b k-18" style="margin:0;line-height:1.5">${esc(q.label)} 결과 ${count(q.total)}건</p>
        <div class="k-x sq-in"><table class="k-t s"><thead><tr>${q.columns.map((c) => `<th scope="col">${esc(c)}</th>`).join('')}</tr></thead><tbody>${q.rows.map((row) => `<tr>${q.columns.map((c) => `<td>${cell(row[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        ${q === res.query ? `<div class="k-h"><button class="k-btn sm" data-act="homeq2" data-q="${esc(q.name)}">쿼리 화면에서 열기</button></div>` : ''}`;
    } else if (res.route === 'none' && !(more && more.ok)) {
      const ask = (res.ask || []).map((x) => `<span class="k-chip warn">${esc(x.about)} 담당 ${esc(x.who)}에게 요청</span>`).join('');
      body = r.moreBusy ? understood : `${understood}<p class="k-b k-18" style="margin:0;line-height:1.5">답하지 않았습니다</p><p class="k-p">${esc(res.reason || res.answer)} 근거 없이 추측하지 않습니다.</p>
        <div class="k-h">${ask}<button class="k-btn sm" data-act="srbuild">쿼리 직접 만들기</button><a class="k-btn sm" href="#records">레코드 탐색</a></div>
        <p class="k-p s">번호, 이름, 정의된 용어를 넣어 다시 묻거나 등록 쿼리를 만들어 두면 다음부터 데이터에서 바로 답합니다.</p>`;
    } else {
      const nearest = res.needs_model && !(more && more.ok);
      body = `${understood}${nearest && r.moreBusy ? '' : `${nearest ? '<span class="k-s">질문과 가장 가까운 근거</span>' : ''}<p class="k-p" style="font-size:16px;color:var(--ink);white-space:pre-wrap">${esc(more && more.ok ? more.answer : res.answer)}</p>`}`;
    }
    return `<section class="k-card" aria-labelledby="sq-ans"><div class="k-ch"><h2 id="sq-ans">답</h2><span class="k-s">${esc(badge)}</span></div><div class="k-cb">${body}${wait}${failed}</div></section>${sqWhy(res, d, q)}`;
  }

  // what the answer stands on: how it was judged, the values it used, the passages, the query that was run
  function sqWhy(res, d, q) {
    const tabs = d ? [['how', '어떻게 판단했나'], ['values', `사용한 값 ${d.evidence.length}`]] : [];
    tabs.push(['docs', `근거 ${res.sources.length}`]);
    if (d || (q && q.text) || (res.record && res.record.query)) tabs.push(['code', '실행한 쿼리']);
    if (tabs.length === 1 && !res.sources.length) return '';
    const on = tabs.some((t) => t[0] === S.sr.tab) ? S.sr.tab : tabs[0][0];
    const seg = tabs.length > 1 ? `<div class="k-push"><div class="k-seg" role="tablist" aria-label="답의 근거">${tabs.map(([k, w]) => `<button role="tab" aria-selected="${k === on}" class="${k === on ? 'on' : ''}" data-act="srtab" data-k="${k}">${esc(w)}</button>`).join('')}</div></div>` : '';
    const body = on === 'how' ? howSteps(d) : on === 'values' ? `<div class="k-x">${valuesTable(d)}</div>` : on === 'code' ? codePane(res, d, q)
      : res.sources.map(sourceCard).join('') || '<p class="k-p s">찾은 근거가 없습니다.</p>';
    return `<section class="k-card sq-why" aria-labelledby="sq-why"><div class="k-ch"><h2 id="sq-why">근거</h2>${seg}</div><div class="k-cb" role="tabpanel">${body}</div></section>`;
  }

  function sqSide(res) {
    const asked = askedBefore();
    const recent = `<section class="k-card" aria-labelledby="sq-recent"><div class="k-ch"><h2 id="sq-recent">최근 검색</h2></div>
      ${asked.map((q) => `<button class="k-row" data-act="homeask" data-q="${esc(q)}"><span class="k-col"><span class="k-ink k-14">${esc(q)}</span></span></button>`).join('') || '<p class="k-cf line">아직 검색한 것이 없습니다.</p>'}</section>`;
    const others = res && (res.decisions || []).length > 1 ? `<section class="k-card" aria-labelledby="sq-others"><div class="k-ch"><h2 id="sq-others">함께 찾은 판정</h2></div>
      ${res.decisions.map((x, i) => `<button class="k-row${i === (S.sr.di || 0) ? ' on' : ''}" data-act="srdi" data-i="${i}" aria-pressed="${i === (S.sr.di || 0)}"><span class="k-col"><span class="k-ink k-14">${esc(x.label)}</span></span><span class="k-chip ${x.good ? 'ok' : 'warn'}">${esc(x.verdict)}</span></button>`).join('')}</section>` : '';
    const rel = res && (res.relations || []).length ? `<section class="k-card" aria-labelledby="sq-rel"><div class="k-ch"><h2 id="sq-rel">연결 관계</h2><span class="k-s">검색 엔진 · ${esc(res.engine || '')}</span></div><div class="k-cb"><div class="k-v g4 k-s">${res.relations.slice(0, 6).map((x) => `<span>${esc(x)}</span>`).join('')}</div></div></section>` : '';
    return `<div class="k-v g24" style="flex:2 1 320px;min-width:0">${others}${recent}${rel}
      ${noSource() ? '<p class="k-note">재고 수량 · 할인가처럼 실제 값을 묻는 질문은 <a href="#db">데이터 소스 연결</a> 뒤에 답합니다.</p>' : ''}
      <p class="k-note">답은 운영 버전 기준으로 나옵니다. 에이전트와 외부 앱이 받는 범위는 <a href="#roles">접근 정책</a>에서 정합니다.</p></div>`;
  }

  function sqView() {
    const r = S.sr, h = S.h2, res = r.res && !r.res.error ? r.res : null;
    const sp = S.sp && !S.sp.busy && !S.sp.error ? S.sp : null;
    const head = kHead('검색 · 질문', '정의, 규칙, 용어, 자료를 한 번에 찾고 질문에는 규칙 판정과 근거로 답합니다.');
    const box = `<label class="sq-box"><span class="k-mut" style="display:inline-flex">${ki('search', 18, 1.75)}</span><input class="k-g0" type="search" id="srtext" data-in="srtext" value="${esc(r.text)}" placeholder="찾을 말이나 질문을 입력합니다" aria-label="검색 또는 질문" autocomplete="off"><span class="k-code k-mut">${r.busy ? '찾는 중' : 'Enter'}</span></label>`;
    const n = (h.find && h.findOf === (res && res.question) && h.find.counts) || {};
    const scope = folderPick('srfolder', r.folder, sp, '검색 범위').replace('class="inline"', 'class="k-in sm" style="width:auto;max-width:220px"');
    const cats = res ? `<div class="k-h sb"><div class="k-seg" role="group" aria-label="보기">${SQ_CAT.map(([k, w]) => `<button class="${h.cat === k ? 'on' : ''}" data-act="sqCat" data-k="${k}" aria-pressed="${h.cat === k}">${w}${n[k] !== undefined ? ` ${count(n[k])}` : ''}</button>`).join('')}</div>${scope}</div>` : '';
    if (!r.res) {
      const examples = sp ? (sp.examples || []).slice(0, 4).map((c) => `<button class="k-chip w" data-act="srex" data-text="${esc(c)}">${esc(c)}</button>`).join('') : '';
      return `${head}${box}${examples ? `<div class="k-h g6"><span class="k-s">예시</span>${examples}</div>` : ''}<div class="k-cols"><div class="k-c3 wide">${kEmpty('찾을 말이나 질문을 입력합니다', 'Entity, 규칙, 용어, 자료의 이름으로 찾거나 "주문상품 I1001 반품 되나요?"처럼 묻습니다. 질문에는 규칙 엔진이 판정하고 근거를 함께 보여 줍니다.')}</div>${sqSide(null)}</div>`;
    }
    if (r.res.error) return `${head}${box}<div class="k-cols"><div class="k-c3 wide">${kEmpty('일시적인 문제가 있습니다', r.res.error, '<button class="k-btn" data-act="srgo">다시 시도</button>')}</div>${sqSide(null)}</div>`;
    const left = h.cat === 'all' ? sqAnswer(r) + sqFound('all') : h.cat === 'answer' ? sqAnswer(r) : sqFound(h.cat);
    return `${head}${box}${cats}<div class="k-cols"><div class="k-c3 wide">${left}</div>${sqSide(res)}</div>`;
  }

  screen('search', {
    area: 'work', word: '검색 · 질문', crumb: ['검색 · 질문'], view: sqView,
    after: () => {
      if (!S.sp) loadSpace();
      const res = S.sr.res && !S.sr.res.error ? S.sr.res : null;
      if (res && S.h2.findOf !== res.question && !S.h2.findBusy) { S.h2.more = false; sqFind(res.question); }
    },
  });
  Object.assign(ACT, {
    sqCat: (t) => { S.h2.cat = t.dataset.k; render(); },
    sqMore: () => { S.h2.more = true; render(); },
  });

  // ---- 자료 업로드 --------------------------------------------------------------------------------------------------
  // Files are chosen first and sent when a person says so (업로드만, or 업로드하고 AI 초안 생성). What was uploaded is
  // managed in the list below, as the catalog did: folders, what a file is read as, whether a draft and the search
  // read it.

  const UP_FORMATS = 'PDF · DOCX · HWPX · XLSX · CSV · MD · YAML · SQL';

  function upStage(items) {
    const u = S.h2.up, had = new Set(u.staged.map((x) => x[1]));
    items.forEach(([f, rel]) => { if (!had.has(rel)) { had.add(rel); u.staged.push([f, rel]); } });
    if (S.tab === 'catalog') render();
  }
  async function upDropped(dt) {
    const entries = [...dt.items].map((x) => (x.webkitGetAsEntry ? x.webkitGetAsEntry() : null)).filter(Boolean);
    const out = [];
    if (!entries.length) out.push(...[...dt.files].map((f) => [f, f.name]));
    else { try { for (const e of entries) await walkEntry(e, '', out); } catch (e) { fail(e); } }
    upStage(out);
  }

  function upFiles(st) {
    const c = S.cat, u = S.h2.up, lim = st.limits;
    const staged = u.staged.map(([f, rel], i) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14"><b class="k-b">${esc(rel)}</b></span><span class="k-s">${fileSize(f.size)}${lim.file_bytes && f.size > lim.file_bytes ? ` · 파일당 ${bytes(lim.file_bytes)} 한도 초과` : ''}</span></span>
      <span class="k-h end"><span class="k-chip ${lim.file_bytes && f.size > lim.file_bytes ? 'bad' : 'b'}">${lim.file_bytes && f.size > lim.file_bytes ? '올릴 수 없음' : '대기'}</span><button class="k-lnk" data-act="upDrop" data-i="${i}">빼기</button></span></div>`).join('');
    const prog = c.up ? `<div class="k-row"><span class="k-col"><span class="k-ink k-14"><b class="k-b">${esc(c.up.name)}</b></span><span class="k-meter b"><i style="width:${Math.round((c.up.done / c.up.total) * 100)}%"></i></span></span><span class="k-h end"><span class="k-chip b">${count(c.up.done)} / ${count(c.up.total)} 올리는 중</span></span></div>` : '';
    const sent = new Set(u.sent || []);
    const done = (st.files || []).filter((f) => sent.has(f.path)).map((f) => { const k = (f.facts || {}).kind;
      const word = f.error ? '읽지 못함' : k === 'data' ? '테이블 데이터로 인식' : k === 'definition' ? '정의서로 인식' : k === 'document' ? `${DOC_WORD[f.facts.doc_kind] || '문서'}로 인식` : k === 'raw' ? '원본으로 보관' : '내용 없음';
      return `<div class="k-row"><span class="k-col"><span class="k-ink k-14"><b class="k-b">${esc(f.name)}</b></span><span class="k-s">${esc(f.error || `${word} · ${amount(f)}`)}</span></span><span class="k-h end"><span class="k-chip ${f.error ? 'bad' : 'ok'}">${f.error ? '읽기 실패' : '업로드 완료'}</span></span></div>`; }).join('');
    return staged + prog + done;
  }

  // the files of the repository, as the catalog listed them: what each is read as, and whether a draft and the search read it
  function upList(st) {
    const c = S.cat, rows = sortedRows(c);
    const exts = [...new Set(st.files.map((f) => f.ext).filter(Boolean))].sort();
    const arrow = (k) => (c.sort === k ? `<span class="arrow">${c.dir > 0 ? '↑' : '↓'}</span>` : '');
    const th = (k, l) => `<th class="sort${c.sort === k ? ' on' : ''}" data-act="csort" data-k="${k}">${l} ${arrow(k)}</th>`;
    const picked = Object.keys(c.sel).filter((k) => c.sel[k]);
    const bulk = picked.length ? `<div class="k-h up-bulk"><b class="k-b k-13">${picked.length}개 선택</b><button class="k-btn sm" data-act="cbulk" data-on="1">초안 포함</button><button class="k-btn sm" data-act="cbulk" data-on="">초안 제외</button><button class="k-btn sm" data-act="cembulk" data-on="1">임베딩 켜기</button><button class="k-btn sm" data-act="cembulk" data-on="">임베딩 끄기</button><button class="k-btn sm dan" data-act="cdelete">삭제</button><button class="k-lnk" data-act="cclear">선택 해제</button></div>` : '';
    const adding = c.edit && c.edit.path === '' ? `<tr class="crow"><td></td><td></td><td colspan="10"><input type="text" id="cedit" data-in="cedit" value="${esc(c.edit.value)}" placeholder="새 폴더 이름" aria-label="새 폴더 이름"></td></tr>` : '';
    const table = rows.length || adding ? `<div class="k-x"><table class="ctable"><thead><tr><th style="width:34px"><input type="checkbox" data-in="call"${rows.length && picked.length === rows.length ? ' checked' : ''} aria-label="전체 선택"></th><th style="width:44px">No.</th>${th('name', '파일명')}<th>유형</th><th>형식</th>${th('bytes', '크기')}<th>규모</th>${th('uploaded', '업로드일')}<th>처리 경로</th><th style="width:52px">초안</th><th style="width:118px">임베딩</th><th style="width:48px">작업</th></tr></thead>
      <tbody>${adding}${rows.map((x, i) => catalogRow(x, i, c)).join('')}</tbody></table></div>`
      : `<p class="k-cf line">${c.folder ? '폴더가 비어 있습니다.' : '올린 자료가 없습니다. 위에서 파일을 고르면 여기에 쌓입니다.'}</p>`;
    const tools = `<div class="k-h up-tool"><div class="ctrail">${folderTrail(c)}</div>
      ${exts.length > 1 ? `<select class="k-in sm" style="width:auto" data-in="cext" aria-label="확장자"><option value="">확장자</option>${exts.map((x) => `<option value="${esc(x)}"${x === c.ext ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select>` : ''}
      <span class="k-push k-h"><button class="k-btn sm" data-act="ccopy" title="경로 복사" aria-label="경로 복사">${ki('copy', 16)}</button><button class="k-btn sm" data-act="creload" title="새로고침" aria-label="새로고침">${ki('reload', 16, 1.75)}</button>
        <button class="k-btn sm" data-act="cup"${c.folder ? '' : ' disabled'}>상위 폴더</button><button class="k-btn sm" data-act="cnew">${ki('plus', 16)}새 폴더</button></span></div>`;
    return `<section class="k-card" aria-labelledby="up-list"><div class="k-ch"><h2 id="up-list">올린 자료</h2><span class="k-s">${esc(st.repository.label)} · ${count(st.repository.files)}개</span>
      <div class="k-push"><button class="k-btn sm" data-act="repopick">${ki('box', 16)}레포지토리 선택${ki('chevD', 14, 1.75)}</button>${st.repository.files ? '<a class="k-btn sm" href="#convert">변환 결과</a>' : ''}</div></div>
      ${tools}${bulk}${table}</section>`;
  }

  function upWork() {
    const a = S.h2.ai.st;
    const rows = !a ? '<p class="k-cf line">불러오는 중입니다.</p>'
      : `${kKv('검토 대기', `<span class="k-code k-ink">${count(a.waiting.all)}</span>`)}${kKv('진행 중인 생성', `<span class="k-code k-ink">${a.running ? 1 : 0}</span>`)}${kKv('모델 서버', a.model.on ? '<span class="k-chip ok">연결됨</span>' : '<span class="k-chip">미연결</span>')}`;
    return `<section class="k-card" aria-labelledby="up-work"><div class="k-ch"><h2 id="up-work">AI 초안 작업</h2></div>${rows}
      <div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#ai">AI 초안 생성${ki('chevR', 14, 1.75)}</a>${known('sys-ai') && isSysAdmin() ? `<a class="k-lnk flat" href="#sys-ai">AI 운영${ki('chevR', 14, 1.75)}</a>` : ''}</div></section>`;
  }

  function upView() {
    const c = S.cat, u = S.h2.up;
    const back = known('evidence') ? 'evidence' : 'home';
    const head = kHead('자료 업로드', '정책서, 정의서, 용어집, 소스코드를 올리면 AI가 규칙과 개념의 초안을 만듭니다. 개인정보가 포함된 파일은 올리지 않습니다.', `<a class="k-btn" href="#${back}"${u.staged.length ? ' data-act="upCancel"' : ''}>취소</a>`);
    if (!c.st) return head + '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>';
    if (c.st.error) return head + kEmpty('일시적인 문제가 있습니다', c.st.error, '<button class="k-btn" data-act="creload">다시 시도</button>');
    if (!canEdit()) return head + kEmpty('이 화면을 볼 권한이 없습니다', '이 온톨로지에서 편집 이상 역할이 있어야 자료를 올릴 수 있습니다.', '<a class="k-btn pri" href="#home">홈으로</a>');
    const st = c.st, lim = st.limits;
    const path = st.server_paths && u.from === 'path';
    const seg = st.server_paths ? `<div class="k-seg self" role="group" aria-label="올리는 방법"><button class="${path ? '' : 'on'}" data-act="upFrom" data-k="file">파일</button><button class="${path ? 'on' : ''}" data-act="upFrom" data-k="path">서버 경로</button></div>` : '';
    const drop = path ? `<div class="k-h nw"><input class="k-in mono" type="text" data-in="cpath" value="${esc(c.paste || '')}" placeholder="서버의 파일 또는 폴더 경로" aria-label="서버 경로"><button class="k-btn" data-act="cimport">가져오기</button></div><span class="k-s">서버가 읽을 수 있는 경로의 파일을 지금 폴더로 가져옵니다</span>`
      : `<div class="k-v up-drop" data-updrop="1">${ki('upload', 24, 1.75)}<span class="k-14">파일을 끌어다 놓거나 <button class="k-lnk" data-act="upPick">파일 선택</button><button class="k-lnk" data-act="upPickDir">폴더 선택</button></span>
          <span class="k-s">${UP_FORMATS} · 파일당 ${bytes(lim.file_bytes)}</span></div>
        <input type="file" id="upfile" multiple hidden><input type="file" id="updir" webkitdirectory multiple hidden>`;
    const room = `사용 ${count(lim.used_files)} / ${count(lim.files)}개 · ${fileSize(lim.used_bytes)} / ${bytes(lim.total_bytes)}${st.persistent ? '' : ' · 올린 파일은 세션이 끝나면 지워집니다'}`;
    const ready = u.staged.length && !c.up;
    return `${head}<div class="k-cols"><div class="k-c3 wide">
        <section class="k-card" aria-labelledby="up-h"><div class="k-ch"><h2 id="up-h">올릴 자료</h2><span class="k-s">${esc(c.folder ? `${st.repository.label} / ${c.folder}` : st.repository.label)}에 올립니다</span>
          ${st.samples && !st.repository.files ? '<div class="k-push"><button class="k-btn sm" data-act="fsample">샘플 데이터 불러오기</button></div>' : ''}</div>
          <div class="k-cb">${seg}${drop}</div>${upFiles(st)}</section>
        <section class="k-card" aria-labelledby="up-info"><div class="k-ch"><h2 id="up-info">자료 정보</h2></div><div class="k-cb">
          <div class="k-g2"><label class="k-f">자료 종류<select class="k-in" data-in="upUse" aria-label="자료 종류">${Object.entries(USE_WORD).map(([k, w]) => opt(k, k ? w : '자동 인식', u.use)).join('')}</select><span class="k-hint">고르면 내용과 달라도 그 종류로 읽습니다</span></label>
            <div class="k-f"><span>남은 자리</span><span class="k-14 k-ink" style="min-height:36px;display:flex;align-items:center">${esc(room)}</span></div></div>
          <span class="k-s">업로드하고 AI 초안 생성을 고르면 올린 뒤 AI 초안 생성 화면으로 이어집니다. 규칙 초안은 규칙 초안에 쌓이고 개념 초안은 개념 초안에 쌓입니다</span>
          <div class="k-h end"><button class="k-btn" data-act="upGo" data-then=""${ready ? '' : ' disabled'}>업로드만</button><button class="k-btn pri" data-act="upGo" data-then="1"${ready ? '' : ' disabled'}>${ki('spark', 16, 1.75)}업로드하고 AI 초안 생성</button></div></div></section></div>
      <div class="k-c2 wide">${upWork()}
        <p class="k-note">AI 초안 결과 · <a href="#ruleagent">규칙 초안</a> · <a href="#${known('concepts') ? 'concepts' : 'data'}">개념 초안</a>${known('evidence') ? ' · 자료 목록은 <a href="#evidence">근거 지도</a>' : ''}</p></div></div>
      ${upList(st)}`;
  }

  screen('catalog', {
    area: 'work', word: '자료 업로드', under: 'evidence', crumb: ['자료 업로드'], view: upView,
    after: () => {
      if (!S.cat.st && !S.cat.busy) loadCatalog();
      if (!S.h2.ai.st && !S.h2.ai.busy) aiLoad();
      const box = $('#cedit');
      if (box && document.activeElement !== box) { box.focus(); box.select(); }
    },
  });
  Object.assign(ACT, {
    upPick: () => { if (!S.cat.up) $('#upfile').click(); },
    upPickDir: () => { if (!S.cat.up) $('#updir').click(); },
    upDrop: (t) => { S.h2.up.staged.splice(Number(t.dataset.i), 1); render(); },
    upCancel: () => { S.h2.up.staged = []; render(); },
    upFrom: (t) => { S.h2.up.from = t.dataset.k; if (t.dataset.k === 'path' && S.cat.paste === null) S.cat.paste = ''; render(); },
    upGo: async (t) => {
      const u = S.h2.up, c = S.cat, then = !!t.dataset.then;
      const lim = (c.st && c.st.limits) || {};
      const items = u.staged.filter(([f]) => !(lim.file_bytes && f.size > lim.file_bytes));
      if (!items.length || c.up) { toast('올릴 수 있는 파일이 없습니다. 파일당 한도를 넘지 않는 파일을 골라 주세요.', true); return; }
      const paths = items.map(([, rel]) => (c.folder ? `${c.folder}/` : '') + rel);
      u.staged = [];
      await uploadAll(items);
      u.sent = paths;
      c.next = null;
      if (u.use) {
        const here = new Set((c.st && c.st.files ? c.st.files : []).map((f) => f.path));
        for (const p of paths.filter((x) => here.has(x))) { try { await api('catalog/use', { path: p, use: u.use }); } catch (e) { fail(e); } }
        await catalogChanged();
      }
      S.h2.ai.st = null;
      if (then) location.hash = '#ai'; else render();
    },
  });
  Object.assign(INPUT, { upUse: (t) => { S.h2.up.use = t.value; } });
  document.addEventListener('change', (ev) => {
    if (ev.target.id === 'upfile') { upStage([...ev.target.files].map((f) => [f, f.name])); ev.target.value = ''; }
    if (ev.target.id === 'updir') { upStage([...ev.target.files].map((f) => [f, f.webkitRelativePath || f.name])); ev.target.value = ''; }
  });
  document.addEventListener('dragover', (ev) => { const z = ev.target.closest && ev.target.closest('[data-updrop]'); if (z) { ev.preventDefault(); z.classList.add('over'); } });
  document.addEventListener('dragleave', (ev) => { const z = ev.target.closest && ev.target.closest('[data-updrop]'); if (z) z.classList.remove('over'); });
  document.addEventListener('drop', (ev) => { const z = ev.target.closest && ev.target.closest('[data-updrop]'); if (z) { ev.preventDefault(); z.classList.remove('over'); upDropped(ev.dataTransfer); } });

  // ---- AI 초안 생성 -------------------------------------------------------------------------------------------------
  // Two drafts can be made here, each with what the product already had: Entity · Property · Relation from the tables
  // and definition files that were uploaded (read from their keys, references and codes, no model), and rules from a
  // policy document (a model writes a decision table, the engine checks every rule against the clause it cites).
  // Either one is only a draft: it is reviewed on 개념 초안 or 규칙 초안 and reaches the definition as a change request.

  async function aiLoad() {
    const a = S.h2.ai;
    a.busy = true;
    try { a.st = await api('home/ai'); a.err = ''; } catch (e) { a.err = e.message || String(e); }
    a.busy = false;
    if (S.tab === 'ai' || S.tab === 'catalog') render();
  }

  const aiConcepts = () => (known('concepts') ? 'concepts' : 'data');
  const aiWhen = (at) => { const s = String(at || ''), today = new Date().toISOString().slice(0, 10); return s.slice(0, 10) === today ? `오늘 ${s.slice(11, 16)}` : `${s.slice(5, 10).replace('-', '/')} ${s.slice(11, 16)}`; };
  const AI_JOB = { concepts: '개념', rules: '규칙' };
  const AI_JOB_TONE = { waiting: 'b', filed: 'warn', done: 'ok' };

  function aiTargets(st) {
    const a = S.h2.ai, k = a.kinds, on = st.model.on;
    const tick = (key, word, off, why) => `<label class="k-ck"${off ? ` title="${esc(why)}"` : ''}><input type="checkbox" data-in="aiKind" data-k="${key}"${k[key] && !off ? ' checked' : ''}${off ? ' disabled' : ''}><span${off ? ' class="k-mut"' : ''}>${word}</span></label>`;
    const docs = st.documents.map((d) => opt(d.name, `${d.name} · 섹션 ${count(d.sections)}`, a.doc)).join('');
    const fields = [
      k.concepts ? `<label class="k-f">초안 이름<input class="k-in" type="text" data-in="dname" value="${esc(S.dr.label)}" placeholder="예: 주문 · 결제 초안" maxlength="40"><span class="k-hint">비워 두면 자료 이름으로 붙입니다</span></label>` : '',
      k.rules && on ? `<label class="k-f">규칙의 바탕 문서<select class="k-in" data-in="aiDoc" aria-label="규칙의 바탕 문서"><option value="">문서 선택</option>${docs}${st.sample_policy ? opt('@sample', '예시 정책서', a.doc) : ''}</select>${!st.documents.length ? '<span class="k-hint">올린 문서가 없습니다. 자료 업로드에서 정책서를 올립니다</span>' : ''}</label>` : '',
      k.rules && on && a.sections.length ? `<label class="k-f">절<select class="k-in" data-in="aiSection" aria-label="절"><option value="">문서 전체</option>${a.sections.map((x) => opt(x, x, a.section)).join('')}</select></label>` : '',
      k.rules && on ? `<label class="k-f">범위<select class="k-in" data-in="aiTarget" aria-label="범위"><option value="">자동 · 문서가 다루는 Entity</option>${st.targets.map((t) => opt(t.id, `${t.label} · ${t.id}`, a.target)).join('')}</select></label>` : '',
    ].filter(Boolean).join('');
    return `<section class="k-card" aria-labelledby="ai-h1"><div class="k-ch"><h2 id="ai-h1">만들 대상</h2><span class="k-s">1</span></div><div class="k-cb">
      <div class="ai-ticks">${tick('concepts', 'Entity · Property · Relation')}${tick('questions', '검증 질문', !k.concepts, 'Entity 초안과 함께 만듭니다')}${tick('rules', '규칙', !on, '언어 모델이 연결되어야 만듭니다')}</div>
      ${fields ? `<div class="k-g2">${fields}</div>` : ''}
      ${on ? '' : '<p class="k-note">모델 서버에 연결되어 있지 않아 규칙 초안은 만들 수 없습니다. Entity · Property · Relation 초안은 언어 모델 없이 만듭니다.</p>'}</div></section>`;
  }

  function aiSources(st) {
    const m = st.materials, e = st.existing;
    const on = (label) => `<input type="checkbox" checked disabled aria-label="${label}">`;
    const mats = [[m.document, '문서'], [m.definition, '정의서'], [m.data, '테이블 데이터']].filter(([n]) => n).map(([n, w]) => `${w} ${count(n)}`).join(' · ');
    const rows = [
      st.packs.length ? ['도메인 팩', st.packs.map((p) => `${p.label} ${p.version}`).join(' · '), '표준 Object · 규제 규칙의 출발점', on('도메인 팩 사용')] : null,
      ['올린 자료', m.files ? `${mats || `자료 ${count(m.files)}건`}${m.included < m.files - m.raw ? ` · 초안에 넣은 것 ${count(m.included)}` : ''}` : '올린 자료 없음', '근거 인용 · 고객사 규칙',
        m.included ? on('자료 사용') : `<a class="k-lnk" href="#catalog">자료 업로드</a>`],
      ['기존 정의', [e.objects ? `Object ${count(e.objects)}` : '', `Entity ${count(e.entities)}`, `규칙 ${count(e.rules)}`].filter(Boolean).join(' · '), '중복 · 충돌 검사', on('기존 정의 필수')],
    ].filter(Boolean);
    return `<section class="k-card" aria-labelledby="ai-h2"><div class="k-ch"><h2 id="ai-h2">바탕 자료</h2><span class="k-s">2</span>${st.samples && !m.files && canEdit() ? '<div class="k-push"><button class="k-btn sm" data-act="aiSample">샘플 데이터 불러오기</button></div>' : ''}</div>
      <div class="k-x"><table class="k-t end"><thead><tr><th scope="col">바탕</th><th scope="col">내용</th><th scope="col">쓰임</th><th scope="col"></th></tr></thead>
        <tbody>${rows.map(([a, b, c, d]) => `<tr><td><b class="k-b" style="white-space:nowrap">${a}</b></td><td>${esc(b)}</td><td>${c}</td><td class="r">${d}</td></tr>`).join('')}</tbody></table></div>
      <p class="k-cf">자료는 <a href="#catalog">자료 업로드</a>에서 올리고${known('evidence') ? ' <a href="#evidence">근거 지도</a>에서 관리합니다' : ' 그 화면의 올린 자료에서 관리합니다'} · 팩이 없는 분야는 자료만으로 만듭니다</p></section>`;
  }

  function aiGuide(st) {
    const a = S.h2.ai, r = S.dr.rules || (S.files && S.files.rules) || null;
    const shown = a.guide && r ? `<div class="ai-guide">${RULE_NUM.map(([k, l]) => kKv(l, esc(String(r[k])))).join('')}${RULE_FLAG.map(([k, l]) => kKv(l, r[k] ? '사용' : '사용 안 함')).join('')}
      <div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#data" data-act="aiGuideEdit">생성 설정 고치기${ki('chevR', 14, 1.75)}</a></div></div>` : '';
    return `<section class="k-card" aria-labelledby="ai-h3"><div class="k-ch"><h2 id="ai-h3">생성 지침</h2><span class="k-s">3</span></div><div class="k-cb">
      <div class="k-g2"><label class="k-f">지침<input class="k-in" type="text" readonly value="${esc(st.rules_by.length ? st.rules_by.join(', ') : '기본 구축 규칙')}"></label>
        <label class="k-f">모델<input class="k-in" type="text" readonly value="${st.model.on ? `언어 모델 연결됨${AI_LLM_KIND[st.model.kind] ? ` · ${AI_LLM_KIND[st.model.kind]}` : ''}` : '언어 모델 미연결'}"></label></div>
      <ul class="k-i3 k-14" style="margin:0;padding-left:16px;line-height:1.7">
        <li>Entity · Property · Relation은 올린 테이블과 정의서의 키, 참조, 코드값에서 만들고 언어 모델을 쓰지 않음</li>
        <li>규칙은 정책 문서의 조항에서 만들고 규칙마다 출처 조항을 붙임 · 문서에 없는 조항을 댄 규칙은 검사에서 걸러짐</li>
        <li>자료에 없는 내용을 추정해 채우지 않음</li>
        <li>만든 것은 모두 초안 · 사람이 검토하고 승인해야 반영됨</li></ul>
      <div class="k-h end"><button class="k-lnk" data-act="aiGuide" aria-expanded="${!!a.guide}">${a.guide ? '지침 접기' : '지침 보기'}</button>${aiRunButton(st)}</div></div>${shown}</section>`;
  }
  const AI_LLM_KIND = { openai: 'OpenAI 호환 API' };
  const aiRunButton = (st) => (canEdit() ? `<button class="k-btn pri" data-act="aiRun"${S.h2.ai.run || !st.composed ? ' disabled' : ''}>${ki('spark', 16, 1.75)}${S.h2.ai.run ? '생성 중' : '초안 생성'}</button>` : '');

  function aiSteps(st) {
    const a = S.h2.ai, w = st.waiting, last = st.jobs[0];
    const chip = (tone, word) => `<span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span>`;
    const row = (n, word, what, mark) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${n} · ${word}</span><span class="k-s">${what}</span></span><span class="k-h end">${mark}</span></div>`;
    const made = !!(last || w.draft);
    return `<section class="k-card" aria-labelledby="ai-h4"><div class="k-ch"><h2 id="ai-h4">생성 단계</h2>${last ? `<span class="k-s">마지막 생성 · ${esc(aiWhen(last.at))}</span>` : ''}</div>
      ${row(1, '자료 읽기', '올린 테이블 · 정의서 · 문서를 읽음', st.materials.included ? chip('ok', `자료 ${count(st.materials.included)}건`) : chip('', '자료 없음'))}
      ${row(2, '후보 만들기', 'Entity → Property → Relation → 규칙 순서', a.run ? chip('b', '생성 중') : made ? chip('ok', '완료') : chip('', '대기'))}
      ${row(3, '자동 검사', '키 없는 테이블 · 출처 없는 규칙 · 정의와 충돌', a.run || !last ? chip('', '대기') : last.made.excluded ? chip('warn', `${count(last.made.excluded)}건 제외`) : chip('ok', '통과'))}
      ${row(4, '검토함에 쌓기', '규칙은 규칙 초안, 개념은 개념 초안', w.all ? chip('b', `${count(w.all)}건`) : chip('', '0건'))}
      ${a.run && a.said ? `<p class="k-cf line">${esc(a.said)}</p>` : ''}
      <div class="k-cb" style="padding-top:12px"><div class="k-wrap g8"><a class="k-btn pri" href="#ruleagent">규칙 초안 검토</a><a class="k-btn" href="#${aiConcepts()}">개념 초안 검토</a></div></div></section>`;
  }

  function aiJobs(st) {
    const rows = st.jobs.map((j) => `<tr><td class="nw">${esc(aiWhen(j.at))}</td><td>${esc([AI_JOB[j.kind] || j.kind, j.scope || j.label].filter(Boolean).join(' · '))}</td><td>초안 ${count(j.made.all)} · 제외 ${count(j.made.excluded)}</td><td><span class="k-chip ${AI_JOB_TONE[j.state] || ''}">${esc(j.state_label)}</span></td></tr>`).join('');
    return `<section class="k-card" aria-labelledby="ai-h5" id="ai-jobs"><div class="k-ch"><h2 id="ai-h5">생성 작업</h2></div>
      ${rows ? `<div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">언제</th><th scope="col">범위</th><th scope="col">결과</th><th scope="col">상태</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="k-cf line">아직 이 화면에서 만든 초안이 없습니다.</p>'}
      <p class="k-cf">작업마다 언어 모델 사용 여부와 바탕 자료 수가 기록됩니다 · 서버를 다시 띄우면 비워집니다</p></section>`;
  }

  function aiView() {
    const a = S.h2.ai, st = a.st;
    const lead = '자료와 도메인 팩을 바탕으로 Entity, Property, Relation, 규칙, 검증 질문의 초안을 만듭니다. 초안만 만들고 근거를 댈 수 없는 규칙은 만들지 않습니다. 반영은 사람이 검토해 승인해야 합니다.';
    if (!st) return kHead('AI 초안 생성', lead) + (a.err ? kEmpty('일시적인 문제가 있습니다', a.err, '<button class="k-btn" data-act="aiRetry">다시 시도</button>') : '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>');
    const head = kHead('AI 초안 생성', lead, `<button class="k-btn" data-act="aiHist">생성 이력</button>${aiRunButton(st)}`);
    const w = st.waiting;
    const tile = (word, n, sub) => `<div class="k-stat"><p class="k-s" style="margin:0">${word}</p><p class="k-big">${count(n)}</p><p class="k-s" style="margin:4px 0 0">${esc(sub)}</p></div>`;
    const tiles = `<section class="k-wrap" aria-label="현황">${tile('검토 대기', w.all, `규칙 ${count(w.rules)} · 개념 ${count(w.concepts)} · 용어 ${count(w.terms)}`)}${tile('이번 달 생성', st.month.made, `작업 ${count(st.month.jobs)}회 · 이 화면에서 만든 것`)}${tile('검사에서 제외', st.month.excluded, '자동 검사에서 걸러짐')}</section>`;
    const settings = known('settings') && isOntoAdmin() ? '<a href="#settings">온톨로지 설정</a>' : '온톨로지 설정';
    const none = st.composed ? '' : '<p class="k-note warn">모듈로 구성된 온톨로지가 아니어서 초안을 변경 요청으로 올릴 수 없습니다. 온톨로지 선택에서 모듈로 만든 온톨로지를 엽니다.</p>';
    return `${head}${tiles}${none}<div class="k-cols"><div class="k-c3 wide">${aiTargets(st)}${aiSources(st)}${aiGuide(st)}</div>
      <div class="k-v g24" style="flex:2 1 360px;min-width:0">${aiSteps(st)}${aiJobs(st)}
        <p class="k-note">AI가 만든 것은 모두 초안입니다. 승인 기준은 ${settings}의 승인 정책을 따르고, 승인한 초안은 <a href="#changes">변경 요청</a>에 담깁니다.</p></div></div>
      ${kNext([['ruleagent', '규칙 초안 검토'], [aiConcepts(), '개념 초안 검토'], ['catalog', '자료 업로드'], ['evidence', '근거 지도']])}`;
  }

  screen('ai', {
    area: 'work', word: 'AI 초안 생성', crumb: ['AI 초안', 'AI 초안 생성'], view: aiView,
    after: () => {
      const a = S.h2.ai;
      if (!a.st && !a.busy && !a.err) aiLoad();
      if (!S.files) loadFiles();  // what a draft is made from, and the settings it is made with
    },
  });

  Object.assign(INPUT, {
    aiKind: (t) => { const k = S.h2.ai.kinds; k[t.dataset.k] = t.checked; if (!k.concepts) k.questions = false; render(); },
    aiTarget: (t) => { S.h2.ai.target = t.value; },
    aiSection: (t) => { S.h2.ai.section = t.value; },
    aiDoc: async (t) => {
      const a = S.h2.ai;
      Object.assign(a, { doc: t.value, section: '', sections: [] });
      if (a.doc && a.doc !== '@sample') { try { const r = await api('policy/document', { name: a.doc, section: '' }); a.sections = r.ok ? r.sections || [] : []; } catch (e) { a.sections = []; } }
      render();
    },
  });

  Object.assign(ACT, {
    aiRetry: () => { S.h2.ai.err = ''; render(); },
    aiHist: () => { const box = $('#ai-jobs'); if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' }); },
    aiGuide: () => { S.h2.ai.guide = !S.h2.ai.guide; render(); },
    aiGuideEdit: () => { S.dr.setup = true; S.dr.rulesOpen = true; location.hash = '#data'; },
    aiSample: async () => { try { await api('files/sample', {}); S.files = await api('files'); S.cat.st = null; S.st = await api('state'); S.h2.ai.st = await api('home/ai'); toast('샘플 데이터를 불러왔습니다.'); render(); } catch (e) { fail(e); } },
    aiRun: async () => {
      const a = S.h2.ai, st = a.st, k = a.kinds;
      if (!st || a.run) return;
      const rules = k.rules && st.model.on;
      if (!k.concepts && !rules) { toast('만들 대상을 하나 이상 고릅니다.', true); return; }
      if (k.concepts && !st.tables) { toast('테이블 데이터나 테이블 정의서가 없어 Entity 초안을 만들지 못했습니다. 자료를 먼저 올려 주세요.', true); return; }
      if (rules && !a.doc) { toast('규칙의 바탕 문서를 골라 주세요.', true); return; }
      a.run = true;
      let made = 0;
      try {
        if (k.concepts) {
          a.said = 'Entity · Property · Relation 후보를 만드는 중입니다'; render();
          if (!S.files || S.files.busy || S.files.error) S.files = await api('files');
          if (!S.dr.rules && S.files.rules) S.dr.rules = JSON.parse(JSON.stringify(S.files.rules));
          const data = (S.files.files || []).flatMap((x) => x.tables.map((t) => t.name));
          const all = data.length ? data : (S.files.definitions || []).flatMap((x) => x.tables.map((t) => t.name));
          S.files = await api('draft', { label: S.dr.label, rules: { ...S.dr.rules, questions: !!k.questions }, tables: all.filter((n) => S.dr.tables[n] !== false) });
          S.st = await api('state');
          startDraft();
          a.st = await api('home/ai/job', { kind: 'concepts' });
          made += 1;
        }
        if (rules) {
          a.said = '정책 문서에서 규칙 후보를 만드는 중입니다 · 최대 5분'; render();
          const src = a.doc === '@sample' ? await api('policy/sample', {}) : await api('policy/document', { name: a.doc, section: a.section });
          if (!src.ok) throw new Error(src.error);
          Object.assign(S.pol, { text: src.text, target: a.target, doc: a.doc === '@sample' ? '' : a.doc, section: a.section, res: null });
          let r = await api('policy/draft', { text: src.text, target: a.target });
          const { job } = r;
          while (job && (r.job || r.running)) { await new Promise((done) => setTimeout(done, 2000)); r = await api('policy/draft/result', { job }); }
          S.pol.res = r;
          if (!r.ok) throw new Error(r.error);
          S.ed = { name: '', label: r.label, applied: false, isNew: true, text: r.yaml, check: null, busy: false };
          S.change = null;
          a.st = await api('home/ai/job', { kind: 'rules', scope: [a.doc === '@sample' ? '예시 정책서' : a.doc, a.section].filter(Boolean).join(' › ') });
          made += 1;
        }
        toast('초안을 만들었습니다. 검토함에서 확인합니다.');
      } catch (e) {
        fail(e);
        if (made) toast(`${e.message || e} 먼저 만든 초안은 검토함에 있습니다.`, true);
        try { a.st = await api('home/ai'); } catch (_) { /* the state before stays */ }
      }
      a.run = false; a.said = '';
      S.home.ov = null;
      if (S.tab === 'ai') render();
    },
  });
