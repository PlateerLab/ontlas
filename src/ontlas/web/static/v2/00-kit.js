  // ==== the frame: the menu, the bar on top, and the parts every screen is made of (their look is kit.css) =========
  // The work area holds 홈, AI 초안 생성 and five parts; the admin area holds what only an admin sets; choosing an
  // ontology and a person's own screens have no menu. One list at the top left leads between them.

  const KI = {
    chevR: '<path d="m9 6 6 6-6 6"/>', chevD: '<path d="m6 9 6 6 6-6"/>', arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    layers: '<path d="M12 3 2.5 8 12 13l9.5-5z"/><path d="M2.5 12.5 12 17.5l9.5-5"/><path d="M2.5 16.5 12 21.5l9.5-5"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>', plus: '<path d="M12 5v14M5 12h14"/>', close: '<path d="M6 6l12 12M18 6 6 18"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h.01"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
    scale: '<path d="M12 3v18M7 21h10M4 7h16M6 7l-3 7a3.2 3.2 0 0 0 6 0zM18 7l-3 7a3.2 3.2 0 0 0 6 0z"/>',
    inbox: '<path d="M3 13h5l2 3h4l2-3h5"/><path d="M3 13 5.5 5h13L21 13v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    pulse: '<path d="M3 12h4l3-8 4 16 3-8h4"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    plug: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>',
    nodes: '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="8" r="2.5"/><circle cx="10" cy="18" r="2.5"/><path d="M8.4 6.4l7.2 1.2M6.9 8.4l2.2 7.2M16.6 10.1l-5.1 5.9"/>',
    upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>', download: '<path d="M12 4v12M7 11l5 5 5-5M4 20h16"/>',
    spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
    history: '<path d="M4 12a8 8 0 1 0 2.3-5.7L4 8"/><path d="M4 4v4h4M12 8v4l3 2"/>',
    doc: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8.5 13h7M8.5 17h5"/>',
    file: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/>',
    db: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c1-3.5 3.5-5 6.5-5s5.5 1.5 6.5 5"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 15.2c1.8.7 3 2.2 3.5 4.8"/>',
    box: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    reload: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>', play: '<path d="M7 4.5v15l12-7.5z"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    alert: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>', out: '<path d="M14 5h5v5M19 5l-8 8M10 5H5v14h14v-5"/>',
  };
  const ki = (k, size = 16, w = 1.5) => `<svg class="k-i" width="${size}" height="${size}" viewBox="0 0 24 24" stroke-width="${w}" aria-hidden="true">${KI[k] || ''}</svg>`;

  // what the person may do. In a space of one's own (no sign-in) everything; in a team space what the roles allow
  const inTeam = () => !!(S.me && S.me.team);
  const hasRole = (...rs) => !inTeam() || !!(S.me.user && (S.me.user.roles || []).some((r) => r === 'admin' || rs.includes(r)));
  const isSysAdmin = () => hasRole();
  const isOntoAdmin = () => hasRole();
  const canEdit = () => hasRole('editor', 'approver');
  const canApprove = () => hasRole('approver');
  const WORK_ROLE = { admin: '관리자', approver: '영역 담당', editor: '편집', viewer: '조회' };
  const workRole = () => { const rs = inTeam() && S.me.user ? S.me.user.roles || [] : ['admin']; return WORK_ROLE[['admin', 'approver', 'editor', 'viewer'].find((r) => rs.includes(r)) || 'viewer']; };

  // a screen that is not one of the older tabs says what it is: area (work, admin, bare, auth), its words, how it is drawn
  const V2 = {};
  const screen = (key, def) => { V2[key] = def; };

  const PARTS = [['sem', '시멘틱 매니저', 'scale'], ['ont', '온톨로지 매니저', 'nodes'], ['bnd', '데이터 바인더', 'plug'], ['qa', '품질 관리', 'check'], ['ops', '운영', 'pulse']];
  // the menu's screens: the tab its link opens, its part, its word, and every tab that is this screen
  const MENU = [
    ['semrules', 'sem', '규칙', ['semrules', 'mgrules', 'rules', 'mgfuncs']],
    ['ruleagent', 'sem', '규칙 초안', ['ruleagent']],
    ['objmgr', 'ont', '오브젝트 관리', ['objmgr']],
    ['objects', 'ont', '엔티티 관리', ['objects', 'states']],
    ['model', 'ont', '그래프 탐색', ['model', 'onto']],
    ['lexicon', 'ont', '용어사전', ['lexicon']],
    ['concepts', 'ont', '개념 초안', ['concepts', 'data', 'convert']],
    ['library', 'ont', '온톨로지', ['library']],
    ['changes', 'ont', '변경 요청 · 버전', ['changes', 'versions']],
    ['db', 'bnd', '데이터 소스 연결', ['db']],
    ['sources', 'bnd', '데이터 매핑', ['sources']],
    ['bind', 'bnd', 'Entity 바인딩', ['bind', 'records', 'record', 'graph']],
    ['query', 'bnd', '쿼리', ['query']],
    ['actions', 'bnd', '액션', ['actions', 'decide']],
    ['check', 'qa', '검증질문 관리', ['check']],
    ['flow', 'qa', '검증', ['flow']],
    ['adapters', 'ops', '저장소 · 엔진', ['adapters', 'vectors']],
    ['connect', 'ops', '연동 · API', ['connect']],
    ['roles', 'ops', '접근 정책', ['roles']],
    ['monitor', 'ops', '파이프라인 모니터링', ['monitor']],
    ['evidence', 'ops', '근거 지도', ['evidence', 'docs', 'explorer', 'map']],
  ];
  const ADMIN = [
    ['onto', '온톨로지 관리', [['settings', '온톨로지 설정', 'sliders'], ['members', '멤버 · 권한', 'key']]],
    ['sys', '시스템 관리', [['sys-overview', '관리 현황', 'pulse'], ['sys-users', '사용자 · 그룹', 'users'], ['sys-auth', '인증 · 보안', 'shield'], ['sys-gov', '거버넌스 정책', 'scale'],
      ['sys-packs', '도메인 팩', 'box'], ['sys-vocab', '기준 어휘', 'layers'], ['sys-ai', 'AI 운영', 'chip'], ['sys-audit', '감사 로그', 'history'], ['sys-system', '시스템', 'db']]],
  ];
  const ADMIN_KEYS = ADMIN.flatMap((g) => g[2].map((x) => x[0]));
  // screens reached from the bar on top or from another screen, with the words the bar says where they are
  const ASIDE = { search: ['검색 · 질문'], catalog: ['자료 업로드'], inbox: ['할 일 · 알림'], guide: ['사용 안내'] };

  const oldTabs = () => new Set(NAV.map((x) => x[0]));
  const known = (key) => !!V2[key] || oldTabs().has(key);
  const menuRow = (tab) => { const k = TABLE_TABS.includes(tab) ? 'objects' : tab; return MENU.find((r) => r[3].includes(k)) || MENU.find((r) => V2[tab] && V2[tab].under === r[0]); };
  const areaOf = (tab) => (V2[tab] && V2[tab].area) || (ADMIN_KEYS.includes(tab) ? 'admin' : 'work');
  const firstAdmin = (group) => { const g = ADMIN.find((x) => x[0] === group); const hit = g && g[2].find((x) => V2[x[0]]); return hit ? hit[0] : ''; };

  // where the person is, as the bar on top says it: 시멘틱 매니저 › 규칙 › 규칙 추가 · 편집
  function crumbs() {
    const tab = curTab(), v = V2[S.tab];
    if (v && v.crumb) return (typeof v.crumb === 'function' ? v.crumb() : v.crumb);
    if (S.tab === 'home') return ['홈'];
    if (ASIDE[S.tab]) return ASIDE[S.tab];
    if (ADMIN_KEYS.includes(S.tab)) { const g = ADMIN.find((x) => x[2].some((y) => y[0] === S.tab)); return ['관리', g[1], g[2].find((y) => y[0] === S.tab)[1]]; }
    const row = menuRow(tab);
    if (!row) return [v ? v.word : navLabel(tab)];
    const part = PARTS.find((p) => p[0] === row[1]);
    const out = [part[1], row[2]];
    if (v && v.word && v.word !== row[2]) out.push(v.word);
    return out;
  }

  const XGEN_MARK = XGEN_WORD.replace('class="xword" viewBox="128 0 72 32"', 'viewBox="128 6 68.4 20" width="68" height="20"');
  const brand = (href = '#home') => `<a class="k-brand" href="${href}" aria-label="XGEN Ontlas">${XGEN_MARK}<span>Ontlas</span></a>`;

  function renderTop() {
    const area = areaOf(S.tab), st = S.st;
    const waits = S.home.box ? S.home.box.counts.assigned : 0;
    const menu = `<button class="k-tbtn k-menu" data-act="navopen" aria-label="메뉴 열기">${ki('menu', 17, 1.75)}</button>`;
    const crumb = `<p class="k-crumb">${crumbs().map(esc).join(' › ')}</p>`;
    const find = `<button class="k-find" data-act="palette" aria-label="검색 또는 질문">${ki('search', 16, 1.75)}<span>검색 또는 질문</span><span class="k-kbd">${/Mac|iPhone|iPad/.test(navigator.platform) ? '⌘K' : 'Ctrl K'}</span></button>`;
    const upload = canEdit() ? `<a class="k-tbtn${S.tab === 'catalog' ? ' on' : ''}" href="#catalog">${ki('upload', 17, 1.75)}<span class="w">자료 업로드</span></a>` : '';
    const inbox = `<a class="k-tbtn${S.tab === 'inbox' ? ' on' : ''}" href="#inbox" aria-label="할 일 ${waits}건">${ki('inbox', 17, 1.75)}<span class="w">할 일</span>${waits ? `<span class="n">${waits}</span>` : ''}</a>`;
    const me = `<a class="k-me${S.tab === 'me' ? ' on' : ''}" href="#me" aria-label="내 계정">${ki('user', 18, 1.75)}</a>`;
    // which data the screens read, while there is more than one to choose from
    const pipes = area === 'work' && st.pipelines.length > 1 ? `<select class="k-in sm" style="width:auto;max-width:200px" data-top="pipe" aria-label="데이터 선택">${st.pipelines.map((p, i) => `<option value="${esc(p.id)}"${p.id === st.pipeline ? ' selected' : ''}>${esc(i === 0 ? '기본 데이터' : p.label)}</option>`).join('')}</select>` : '';
    const repo = area === 'work' && REPO_TABS.has(S.tab) ? `<button class="k-tbtn" data-act="repopick" aria-label="레포지토리 선택">${ki('box', 17)}<span class="k-cut" style="max-width:160px">${esc(st.repository.label)}</span>${ki('chevD', 16, 1.75)}</button>` : '';
    if (area === 'bare') {
      $('#top').innerHTML = `${brand()}${switcher('bare')}${crumb}${inbox}${me}`;
      return;
    }
    $('#top').innerHTML = area === 'admin' ? `${menu}${crumb}${inbox}${me}` : `${menu}${crumb}${repo}${pipes}${find}${upload}${inbox}${me}`;
  }

  // the list at the top left: the ontologies the person works in, every ontology, and the way into the admin screens
  function switcher(area) {
    const st = S.st, libs = st.libraries || [];
    const cur = libs.find((x) => x.id === st.library_id);
    const dom = (st.layers.find((l) => l.kind === 'domain') || st.layers[0] || { modules: [] }).modules[0];
    const name = area === 'admin' ? '관리' : area === 'bare' ? '온톨로지 전환' : (cur ? cur.label : st.title || '온톨로지');
    const sub = area === 'admin' ? '누르면 온톨로지로 전환' : area === 'bare' ? `최근 사용 · ${cur ? cur.label : st.title || ''}`
      : `${dom ? `v${dom.version} · ` : ''}온톨로지 ${Math.max(libs.length, 1)}개 중`;
    const role = workRole();
    const row = (x) => { const on = area === 'work' && x.id === st.library_id;
      return `<button class="k-opt${on ? ' on' : ''}" data-act="swlib" data-id="${esc(x.id)}"><span>${esc(x.label)}</span><span class="k-chip w">${esc(role)}</span>${on ? ki('check', 16, 1.75) : ''}</button>`; };
    const rows = libs.length ? libs.map(row).join('') : `<button class="k-opt${area === 'work' ? ' on' : ''}" data-act="swlib" data-id=""><span>${esc(st.title || '온톨로지')}</span><span class="k-chip w">${esc(role)}</span></button>`;
    const all = V2.ontologies ? `<a class="k-opt${S.tab === 'ontologies' ? ' on' : ''}" href="#ontologies">${ki('layers')}<span>모든 온톨로지 보기</span></a>` : '';
    const make = V2['ontology-new'] && canMakeLibrary() ? `<a class="k-opt${S.tab === 'ontology-new' ? ' on' : ''}" href="#ontology-new">${ki('plus')}<span>온톨로지 만들기</span></a>` : '';
    const onto = isOntoAdmin() && firstAdmin('onto'), sys = isSysAdmin() && firstAdmin('sys');
    const inOnto = area === 'admin' && ADMIN[0][2].some((x) => x[0] === S.tab), inSys = area === 'admin' && !inOnto;
    const admin = onto || sys ? `<p class="k-optg sep">관리</p>${onto ? `<a class="k-opt${inOnto ? ' on' : ''}" href="#${onto}">${ki('sliders')}<span>이 온톨로지 관리</span></a>` : ''}${sys ? `<a class="k-opt${inSys ? ' on' : ''}" href="#${V2['sys-users'] ? 'sys-users' : sys}">${ki('shield')}<span>시스템 관리</span></a>` : ''}` : '';
    return `<details class="k-switch"${area === 'bare' ? ' style="flex:0 1 288px;min-width:240px"' : ''}><summary aria-label="온톨로지 전환">${ki(area === 'admin' ? 'sliders' : 'layers', 18)}<span><b>${esc(name)}</b><small>${esc(sub)}</small></span>${ki('chevD', 16, 1.75)}</summary>
      <div class="k-pop"><p class="k-optg">내가 참여한 온톨로지</p>${rows}${all}${make}${admin}</div></details>`;
  }

  // how far the definition has come, L0 to L3, from the Entities' levels; with no source the last two wait for one
  function maturityFoot() {
    const m = S.mg.st;
    if (!m || m.error || !m.objects || !m.objects.length) return '';
    const filed = m.objects.filter((o) => o.area);
    const ls = (filed.length ? filed : m.objects).map((o) => o.level || 0);
    const low = Math.min(...ls), at = Math.min(low + 1, 3);
    const share = (l) => Math.round((ls.filter((x) => x >= l).length / ls.length) * 100);
    const bar = (l) => (l <= low ? '<i class="done"></i>' : `<i${share(l) ? ` style="background:linear-gradient(90deg,#171717 ${share(l)}%,#E6E6E8 ${share(l)}%)"` : ''}></i>`);
    const say = noSource() ? '데이터 미연결 · 정의 · 규칙 조회와 판정은 연결 없이 동작' : 'L2 · L3은 데이터 매핑과 바인딩 검사 결과로 측정';
    return `<a class="k-foot" href="#objmgr" title="Object별 성숙도"><div><span>성숙도</span><span>${low >= 3 ? 'L3 완료' : `L${at} 진행 중`}</span></div>
      <div class="k-lv" role="img" aria-label="성숙도 L${low} 완료">${[0, 1, 2, 3].map(bar).join('')}${[0, 1, 2, 3].map((l) => `<span${l === at && low < 3 ? ' class="now"' : ''}>L${l}</span>`).join('')}</div><p>${esc(say)}</p></a>`;
  }

  function workMenu() {
    const cur = curTab(), here = menuRow(cur);
    const waitEdit = S.mg.st && S.mg.st.workspace && S.mg.st.workspace.dirty;
    const top = (key, word, icon) => (known(key) ? `<a class="k-nav${S.tab === key ? ' on' : ''}" href="#${key}"${S.tab === key ? ' aria-current="page"' : ''}>${ki(icon, 18)}<span>${word}</span></a>` : '');
    const item = (r) => {
      const on = here === r;
      const mark = r[0] === 'changes' && S.st.changes ? `<span class="k-chip w">${S.st.changes}</span>` : r[0] === 'objects' && waitEdit ? '<span class="k-chip warn">변경 대기</span>' : '';
      return `<a class="k-nav sub${on ? ' on' : ''}" href="#${r[0]}"${on ? ' aria-current="page"' : ''}><span>${esc(r[2])}</span>${mark}</a>`;
    };
    const part = ([id, word, icon]) => {
      const rows = MENU.filter((r) => r[1] === id && known(r[0]));
      if (!rows.length) return '';
      const open = S.nopen[id] === undefined ? !!(here && here[1] === id) : S.nopen[id];
      return `<div class="k-navg"><a class="k-nav part${open ? ' open' : ''}" href="#${rows[0][0]}" data-act="nfold" data-k="${id}" aria-expanded="${open}">${ki(icon, 18)}<span>${word}</span>${ki(open ? 'chevD' : 'chevR', 16, 1.75)}</a>${open ? rows.map(item).join('') : ''}</div>`;
    };
    return `<div class="k-navs">${top('home', '홈', 'home')}${top('ai', 'AI 초안 생성', 'spark')}${PARTS.map(part).join('')}</div>${maturityFoot()}`;
  }

  function adminMenu() {
    const st = S.st, libs = st.libraries || [];
    const link = ([key, word, icon]) => (V2[key] ? `<a class="k-nav${S.tab === key ? ' on' : ''}" href="#${key}"${S.tab === key ? ' aria-current="page"' : ''}>${ki(icon, 18)}<span>${word}</span></a>` : '');
    const target = libs.length > 1 ? `<label class="k-navf">대상 온톨로지<select class="k-in sm" data-side="lib" aria-label="관리할 온톨로지">${libs.map((x) => `<option value="${esc(x.id)}"${x.id === st.library_id ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></label>` : '';
    const onto = isOntoAdmin() && firstAdmin('onto') ? `<div class="k-navg"><p class="k-navh"><b>온톨로지 관리</b></p>${target}${ADMIN[0][2].map(link).join('')}</div>` : '';
    const sys = isSysAdmin() && firstAdmin('sys') ? `<div class="k-navg${onto ? ' sep' : ''}"><p class="k-navh"><b>시스템 관리</b></p>${ADMIN[1][2].map(link).join('')}</div>` : '';
    const ver = S.me && S.me.version ? `<div class="k-foot tight"><div><span>설치 버전</span><span class="k-m12 k-ink">${esc(S.me.version)}</span></div></div>` : '';
    return `<div class="k-navs">${onto}${sys}</div><p class="k-sidenote">온톨로지 작업으로 돌아가려면 위에서 온톨로지를 고릅니다.</p>${ver}`;
  }

  function renderSide() {
    if (!S.st) return;
    if (!S.mg.st && !S.mg.busy) loadManage();  // the menu's maturity reads the definition
    const area = areaOf(S.tab), app = $('#app'), side = $('#side');
    app.classList.toggle('bare', area === 'bare');
    app.classList.remove('auth');
    const was = side.querySelector('details.k-switch'), open = !!(was && was.open), kept = side.scrollTop;
    side.innerHTML = area === 'bare' ? '' : `${brand()}${switcher(area)}${area === 'admin' ? adminMenu() : workMenu()}`;
    const now = side.querySelector('details.k-switch');
    if (now && open) now.open = true;
    side.scrollTop = kept;
  }

  // one screen made of several older tabs shows them as a row of choices under its head
  function subTabs() {
    const row = menuRow(curTab());
    if (!row || V2[S.tab]) return '';
    const tabs = row[3].filter((k) => !NO_TAB.has(k) && oldTabs().has(k));
    if (tabs.length < 2) return '';
    const cur = curTab(), n = tabCounts();
    return `<nav class="k-seg self" aria-label="${esc(row[2])}">${tabs.map((k) => `<a href="#${k}" class="${cur === k ? 'on' : ''}"${cur === k ? ' aria-current="page"' : ''}>${esc(tabWord(k))}${n[k] ? `&nbsp;<span class="k-m12">${n[k]}</span>` : ''}</a>`).join('')}</nav>`;
  }

  function tabCounts() {
    const st = S.st;
    return { catalog: st.data.files, objects: st.stats.objects, query: st.stats.queries, check: st.stats.questions };
  }

  // ---- parts a screen is written with ---------------------------------------------------------------------------
  // the head: the screen's name, one or two sentences on what is done here, and what can be started from it
  const kHead = (title, lead, actions = '', meta = '') => `<section class="k-ph"><div><h1>${esc(title)}${meta ? `<small>${esc(meta)}</small>` : ''}</h1>${lead ? `<p class="k-lead">${esc(lead)}</p>` : ''}</div>${actions ? `<div class="k-pha">${actions}</div>` : ''}</section>`;
  // the screens this one leads to, at the foot: [[hash, word], ...]
  const kNext = (links) => `<nav class="k-next" aria-label="이어지는 화면"><span>이어지는 화면</span>${links.filter((x) => known(x[0].split('?')[0])).map(([h, w]) => `<a class="k-lnk" href="#${h}">${esc(w)}${ki('chevR', 14, 1.75)}</a>`).join('')}</nav>`;
  const kChip = (word, tone = '') => `<span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span>`;
  const kLayer = (layer) => `<span class="k-layer ${esc(String(layer).toLowerCase())}"><i aria-hidden="true"></i>${esc(LAYER_WORD[String(layer).toLowerCase()] || layer)}</span>`;
  // a card: its title with what sits at the right of it, then its body as given
  const kCard = (title, body, opt = {}) => `<section class="k-card${opt.cls ? ` ${opt.cls}` : ''}"${opt.id ? ` id="${opt.id}"` : ''}><div class="k-ch"><h2>${esc(title)}</h2>${opt.note ? `<span class="k-s">${esc(opt.note)}</span>` : ''}${opt.right ? `<div class="k-push">${opt.right}</div>` : ''}</div>${body}</section>`;
  const kKv = (k, v) => `<div class="k-kv"><span>${esc(k)}</span><span>${v}</span></div>`;
  // the row that names what is chosen in a list, with what can be done to it at the right
  const kBar = (label, code, name, actions) => `<div class="k-bar" role="toolbar" aria-label="${esc(label)}"><span class="k-s">${esc(label)}</span>${code ? `<span class="k-code k-ink">${esc(code)}</span>` : ''}<span class="k-14">${esc(name)}</span><span class="k-push">${actions}</span></div>`;
  const kEmpty = (title, say, actions = '') => `<section class="k-empty"><h2>${esc(title)}</h2><p>${esc(say)}</p>${actions ? `<div class="k-h">${actions}</div>` : ''}</section>`;

  // sign-in: no menu and no bar, the form in the middle
  function renderLogin() {
    $('#app').classList.add('auth');
    $('#top').innerHTML = '';
    $('#side').innerHTML = '';
    $('#main').innerHTML = (V2.login ? V2.login.view() : `<div class="k-auth">${brand('#')}<main><section class="k-card"><div><h1 class="k-h1">로그인</h1><p class="k-p s" style="margin-top:4px">계정으로 로그인합니다</p></div>
      <label class="k-f">아이디<input type="text" id="luser" autocomplete="username"></label>
      <label class="k-f">비밀번호<input type="password" id="lpw" autocomplete="current-password"></label>
      <button class="k-btn pri wide" data-act="login">로그인</button>
      <p class="k-p xs">계정은 관리자에게 요청합니다.</p></section></main></div>`);
  }

  document.addEventListener('click', (ev) => {  // the list closes when something outside it is chosen
    document.querySelectorAll('details.k-switch[open]').forEach((d) => { if (!d.contains(ev.target) || ev.target.closest('.k-pop a, .k-pop button')) d.open = false; });
  });

  // the part a tab belongs to, for what still asks by tab: [part, the screen's word, its tabs]
  const groupOf = (tab) => { const r = menuRow(tab); return r ? [r[1], r[2], r[3]] : [ADMIN_KEYS.includes(tab) ? 'admin' : 'home', (V2[tab] && V2[tab].word) || navLabel(tab), [tab]]; };
  // every screen the search box can open: [hash, its word, where it sits, icon key]
  function screenList() {
    const part = (id) => (PARTS.find((p) => p[0] === id) || [])[1] || '';
    const rows = [['home', '홈', '', 'home']];
    if (V2.ai) rows.push(['ai', 'AI 초안 생성', '', 'home']);
    MENU.filter((r) => known(r[0])).forEach((r) => {
      rows.push([r[0], r[2], part(r[1]), r[0]]);
      r[3].filter((k) => k !== r[0] && !NO_TAB.has(k) && oldTabs().has(k)).forEach((k) => rows.push([k, tabWord(k), `${part(r[1])} › ${r[2]}`, k]));
    });
    Object.keys(ASIDE).filter(known).forEach((k) => rows.push([k, ASIDE[k][0], '', k]));
    Object.keys(V2).filter((k) => V2[k].find !== false && V2[k].area !== 'auth' && !rows.some((r) => r[0] === k) && (!V2[k].may || V2[k].may())).forEach((k) => rows.push([k, V2[k].word, V2[k].area === 'admin' ? '관리' : '', k]));
    return rows;
  }
  // what a person without the right to a screen sees in its place
  const noAccess = () => kEmpty('이 화면을 볼 권한이 없습니다', '온톨로지 관리자나 시스템 관리자에게 권한을 요청합니다. 온톨로지 작업 화면은 그대로 사용할 수 있습니다.', '<a class="k-btn pri" href="#home">홈으로</a>');
