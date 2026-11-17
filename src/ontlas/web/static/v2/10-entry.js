  // ==== outside an ontology: choosing one, making one, the person's own screens, sign-in, and what a screen says
  // when it has nothing to show ===================================================================================
  // An ontology is a library: the ones the server offers and the ones made in this session. Nobody is a member of
  // one or kept out of one, so every ontology can be opened and the role shown is the person's role on this server.

  S.ent = { onto: null, sig: '', busy: false, err: '', q: '', kind: 'all', nw: null, more: null, moreFor: null, moreBusy: false, tab: 'todo', filt: 'assigned', out: false, filesBusy: false, acct: null, acctBusy: false, pwBusy: false };

  // ---- what a screen says when it has nothing to show, each with at least one thing to do next -------------------
  const ENT_STATE = {
    empty: { title: '아직 자료가 없습니다', say: '정책서나 정의서를 올리면 규칙과 개념 초안을 AI가 만듭니다. 표준 도메인 팩으로 시작할 수도 있습니다.',
      acts: () => [canEdit() && ['#catalog', '자료 업로드', 'pri', 'upload'], known('library') && ['#library', '모듈 라이브러리에서 도메인 팩 적용']] },
    none: { title: '조건에 맞는 항목이 없습니다', say: '필터를 지우거나 검색어를 바꿔 보세요.',
      acts: (o) => [o.clear && [`@${o.clear}`, '필터 지우기'], ['#search', '검색']] },
    forbidden: { code: '403', title: '이 화면을 볼 권한이 없습니다', say: '이 온톨로지에서 내 작업 역할로는 열 수 없는 화면입니다. 온톨로지 관리자에게 역할을 요청하세요.',
      acts: () => [['#home', '홈으로', 'pri'], ['#me', '내 역할 보기']] },
    admin: { code: '403', title: '관리 화면은 관리자만 열 수 있습니다', say: '온톨로지 관리는 그 온톨로지의 관리자에게만 열립니다. 시스템 관리는 시스템 관리자에게만 열립니다. 주소로 직접 들어와도 이 안내가 나오고 전환 목록에는 관리 항목이 보이지 않습니다.',
      acts: () => [['#home', '온톨로지로 돌아가기', 'pri'], ['#ontologies', '온톨로지 선택']] },
    missing: { code: '404', title: '찾는 항목이 없습니다', say: '삭제됐거나 다른 버전에만 있는 정의일 수 있습니다. 버전 이력에서 확인할 수 있습니다.',
      acts: () => [['#home', '홈으로', 'pri'], ['#changes', '버전 이력']] },
    model: { title: '모델 서버에 연결할 수 없습니다', say: 'AI 초안 생성과 답변 다듬기가 멈췄습니다. 정의 조회, 규칙 판정, API는 계속 동작합니다.',
      acts: () => { const a = [isSysAdmin() && known('sys-ai') && ['#sys-ai', 'AI 운영', 'pri'], isSysAdmin() && known('sys-system') && ['#sys-system', '시스템 상태']].filter(Boolean); return a.length ? a : [['#home', '홈으로', 'pri']]; } },
    'no-source': { title: '데이터 소스를 연결해야 합니다', say: '실제 값 조회와 판정 일치율은 읽기 전용 연결이 있어야 합니다. 정의와 규칙은 지금도 사용할 수 있습니다.',
      acts: () => [['#db', '데이터 소스 연결', 'pri', 'plug']] },
    error: { code: '500', title: '일시적인 문제가 있습니다', say: '잠시 뒤 다시 시도해 주세요.',
      acts: () => [['@entReload', '다시 시도', 'pri', 'reload'], isSysAdmin() && known('sys-system') && ['#sys-system', '시스템 상태']] },
  };
  // one of the states above as a block to put where the screen's content would be. kind: empty, none, forbidden,
  // admin, missing, model, no-source, error. opt: { title, say } to say it in the screen's own words, { clear } the
  // action that clears a filter (none), { acts } buttons of the screen's own as [[target, word, 'pri'?, icon?]]
  // where a target is '#hash' or '@action'.
  function stateBlock(kind, opt = {}) {
    const st = ENT_STATE[kind] || ENT_STATE.missing;
    const acts = (opt.acts || st.acts(opt)).filter(Boolean).filter(([to]) => to[0] !== '#' || known(to.slice(1).split('?')[0]));
    const btn = ([to, word, tone, icon]) => { const cls = `k-btn${tone === 'pri' ? ' pri' : ''}`, mark = icon ? ki(icon, 16, 1.75) : '';
      return to[0] === '@' ? `<button class="${cls}" type="button" data-act="${esc(to.slice(1))}">${mark}${esc(word)}</button>` : `<a class="${cls}" href="${esc(to)}">${mark}${esc(word)}</a>`; };
    return `<section class="k-empty">${st.code ? `<span class="k-code k-mut">${st.code}</span>` : ''}<h2>${esc(opt.title || st.title)}</h2><p>${esc(opt.say || st.say)}</p>${acts.length ? `<div class="k-wrap g8">${acts.map(btn).join('')}</div>` : ''}</section>`;
  }
  screen('state', { area: 'bare', word: '안내', find: false, crumb: ['안내'],
    view: () => `<div class="ent-narrow">${stateBlock(ENT_STATE[itemParam('kind')] ? itemParam('kind') : 'missing')}</div>` });

  // ---- the ontologies -------------------------------------------------------------------------------------------
  const ENT_USED = 'ontlas-onto-used';
  const entUsed = () => { try { const v = JSON.parse(localStorage.getItem(ENT_USED) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
  // the ontologies a person worked in on this browser, the last one first; an id alone is not enough across sessions
  function entRemember(id) {
    const x = ((S.st && S.st.libraries) || []).find((y) => y.id === id);
    if (!x) return;
    try { localStorage.setItem(ENT_USED, JSON.stringify([{ id: x.id, label: x.label }, ...entUsed().filter((y) => y.label !== x.label)].slice(0, 8))); } catch (e) { /* this visit only */ }
  }
  const entWorked = () => { const libs = (S.st && S.st.libraries) || []; return entUsed().map((u) => libs.find((x) => x.id === u.id && x.label === u.label)).filter(Boolean); };
  const entSig = () => `${(S.st.libraries || []).map((x) => `${x.id}:${x.label}`).join('|')}@${S.st.library_id}#${S.st.changes || 0}`;
  const ENT_SCREENS = ['ontologies', 'ontology-new', 'me'];
  const entOut = () => inTeam() && !S.me.user;  // the sign-in ran out while something was being read: the form stays, nothing is drawn over it

  async function entLoad() {
    const e = S.ent;
    if (e.busy) return;
    e.busy = true;
    const sig = entSig();
    try { e.onto = await api('entry/ontologies'); e.err = ''; } catch (err) { e.onto = null; e.err = err.message || String(err); }
    e.sig = sig; e.busy = false;
    if (ENT_SCREENS.includes(S.tab) && !entOut()) render();
  }
  const entNeed = () => { const e = S.ent; if (!e.busy && (e.sig !== entSig() || (!e.onto && !e.err))) entLoad(); };

  const entLevel = (m) => (!m ? '' : m.full ? 'L3' : `L${m.at} · ${m.done} / ${m.all}`);
  function entPack(o) {
    if (o.base) return `기반 · ${o.base}`;
    const on = o.modules.filter((m) => m.on), dom = on.filter((m) => m.kind === 'domain'), first = dom[0] || on[0];
    return first ? `${first.label} ${first.version}${dom.length > 1 ? ` 외 ${dom.length - 1}` : ''}` : '';
  }
  function entWhen(at) {
    const s = String(at || '');
    if (s.length < 16) return '';
    const d = new Date(s), now = new Date(), day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    if (Number.isNaN(d.getTime())) return s.slice(0, 16).replace('T', ' ');
    const gap = Math.round((day(now) - day(d)) / 86400000);
    return gap === 0 ? `오늘 ${s.slice(11, 16)}` : gap === 1 ? '어제' : `${s.slice(5, 7)}/${s.slice(8, 10)}`;
  }
  const entRole = () => { const w = workRole(); return `<span class="k-chip${w === '관리자' ? ' b' : ''}">${esc(w)}</span>`; };
  const entStatus = (o) => `${o.current ? '<span class="k-chip ok">열려 있음</span>' : ''}${o.made ? '<span class="k-chip warn">이 세션에만 있음</span>' : o.current ? '' : '<span class="k-chip">서버 제공</span>'}`;
  const entManages = () => isOntoAdmin() && firstAdmin('onto');
  const entLine = (k, v) => `<span class="ent-kv k-14"><span class="k-mut">${esc(k)}</span><span>${v}</span></span>`;

  function entCard(o) {
    const rows = [entPack(o) && entLine('도메인 팩', esc(entPack(o))), o.maturity && entLine('성숙도', `<span class="k-code k-blue">${esc(entLevel(o.maturity))}</span>`),
      o.version && entLine('운영 버전', `<span class="k-code k-ink">v${esc(o.version)}</span>`), o.last && entLine('최근 활동', esc(`${entWhen(o.last.at)} · ${o.last.text}`))].filter(Boolean).join('');
    return `<section class="k-card pad k-v g12 ent-card${o.current ? ' sel' : ''}"><div class="k-pha"><h2 class="k-h2">${esc(o.label)}</h2><span class="k-chip${workRole() === '관리자' ? ' b' : ''}">내 역할 · ${esc(workRole())}</span>${o.current ? '<span class="k-chip ok">마지막에 사용</span>' : ''}</div>
      ${o.description ? `<p class="k-p ent-clip">${esc(o.description)}</p>` : ''}${rows ? `<div class="ent-kvs">${rows}</div>` : ''}
      <div class="k-pha"><button class="k-btn pri" data-act="entOpen" data-id="${esc(o.id)}">이 온톨로지에서 작업${ki('arrow', 16, 1.75)}</button>${entManages() ? `<button class="k-btn" data-act="entOpen" data-id="${esc(o.id)}" data-go="${esc(entManages())}">${ki('sliders', 16, 1.75)}관리</button>` : ''}</div></section>`;
  }

  function entRows() {
    const e = S.ent, q = e.q.trim().toLowerCase();
    const list = e.onto.ontologies.filter((o) => (e.kind === 'all' || (e.kind === 'made') === o.made) && (!q || `${o.label} ${o.description} ${entPack(o)}`.toLowerCase().includes(q)));
    if (!list.length) return '<tr><td colspan="8" class="mut">조건에 맞는 온톨로지가 없습니다. 검색어를 바꿔 보세요.</td></tr>';
    const acts = (o) => [entManages() && `<button class="k-lnk" data-act="entOpen" data-id="${esc(o.id)}" data-go="${esc(entManages())}">관리</button>`,
      canMakeLibrary() && o.modules.some((m) => m.on) && `<a class="k-lnk" href="#ontology-new?start=base&base=${encodeURIComponent(o.id)}">복제</a>`,
      o.modules.some((m) => m.on) && `<button class="k-lnk" data-act="entExport" data-id="${esc(o.id)}">내보내기</button>`,
      o.made && canMakeLibrary() && `<button class="k-lnk bad" data-act="libdrop" data-id="${esc(o.id)}">삭제</button>`].filter(Boolean).join('');
    return list.map((o) => `<tr${o.current ? ' class="on"' : ''}><td><button class="ent-name" data-act="entOpen" data-id="${esc(o.id)}"><b class="k-b">${esc(o.label)}</b></button>${o.description ? `<br><span class="k-s ent-clip1">${esc(o.description)}</span>` : ''}</td>
      <td class="ent-pack">${esc(entPack(o)) || '<span class="k-s">-</span>'}</td><td>${o.maturity ? `<span class="k-code ${o.maturity.low ? 'k-blue' : 'k-mut'}">${esc(entLevel(o.maturity))}</span>` : '<span class="k-s">-</span>'}</td>
      <td>${o.version ? `<span class="k-code k-mut">v${esc(o.version)}</span>` : '<span class="k-s">-</span>'}</td><td><span class="k-h g4">${entStatus(o)}</span></td><td>${entRole()}</td>
      <td class="nw"><button class="k-lnk" data-act="entOpen" data-id="${esc(o.id)}">열기</button></td><td class="nw">${acts(o)}</td></tr>`).join('');
  }

  // what the last ontology made here holds, and what its import adjusted or could not carry
  function entMadeCard() {
    const r = S.lib.res;
    if (!r) return '';
    const made = LIB_MADE.filter(([k]) => r.made[k]).map(([k, w]) => `<span class="k-chip">${w} ${count(r.made[k])}</span>`).join('') || '<span class="k-s">정의 없음</span>';
    const part = (title, x) => (x && x.count ? `<details class="ent-more"><summary class="k-14">${title} ${count(x.count)}건 <span class="k-s">${x.kinds.map((k) => `${esc(k.label)} ${count(k.count)}`).join(' · ')}</span></summary><div class="ent-lines">${x.lines.map((l) => `<div>${esc(l)}</div>`).join('')}${x.count > x.lines.length ? `<div class="k-mut">이하 ${count(x.count - x.lines.length)}건 생략</div>` : ''}</div></details>` : '');
    return `<section class="k-card"><div class="k-ch"><h2>방금 만든 온톨로지</h2><span class="k-14">${esc(r.label)}</span><span class="k-chip ok">생성 완료</span><div class="k-push"><button class="k-lnk" data-act="libresx">닫기</button></div></div>
      <div class="k-cb"><div class="k-h">${made}</div>${r.report ? `<span class="k-s">가져온 항목 ${count(r.report.preserved)}건</span>${part('조정', r.report.adjusted)}${part('옮기지 못한 항목', r.report.unsupported)}` : ''}</div></section>`;
  }

  function entTree(list) {
    const kids = (o) => list.filter((x) => x.base === o.label && x !== o);
    const node = (o, depth) => `<div class="ent-node" style="margin-left:${depth * 24}px"><b class="k-b">${esc(o.label)}</b><br><span class="k-s">${esc([o.base ? '위 온톨로지를 기반으로' : '팩에서 시작', o.counts ? `Object ${count(o.counts.objects)} · 규칙 ${count(o.counts.rules)}` : '', o.version ? `v${o.version}` : ''].filter(Boolean).join(' · '))}</span></div>${kids(o).map((k) => node(k, depth + 1)).join('')}`;
    return list.filter((o) => !o.base || !list.some((x) => x.label === o.base)).map((o) => {
      const on = o.modules.filter((m) => m.on), dom = on.filter((m) => m.kind === 'domain');
      const pack = dom.length ? `<div class="ent-node dash"><b class="k-b">도메인 팩 · ${esc(dom.map((m) => `${m.label} ${m.version}`).join(' · '))}</b><br><span class="k-s">${esc(`모듈 ${count(on.length)}개 · ${[...new Set(on.map((m) => m.kind_label))].join(' · ')}`)}</span></div>` : '';
      return `${pack}${node(o, dom.length ? 1 : 0)}`;
    }).join('');
  }

  function viewOntologies() {
    const e = S.ent;
    const head = kHead('온톨로지 선택', '작업할 온톨로지를 고릅니다. 온톨로지마다 도메인 팩이 다를 수 있습니다. 고르면 그 온톨로지의 홈으로 들어갑니다. 화면 왼쪽 위 전환 목록에서 언제든 다른 온톨로지로 옮길 수 있습니다.',
      canMakeLibrary() ? `<a class="k-btn" href="#ontology-new?start=files">${ki('upload', 16, 1.75)}가져오기 · OWL · YAML</a><a class="k-btn pri" href="#ontology-new">${ki('plus', 16, 1.75)}온톨로지 만들기</a>` : '');
    if (e.err) return head + stateBlock('error', { say: e.err });
    if (!e.onto) return `${head}<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>`;
    const all = e.onto.ontologies, made = all.filter((o) => o.made).length;
    const cur = all.find((o) => o.current), worked = entWorked().map((u) => all.find((o) => o.id === u.id)).filter((o) => o && o !== cur);
    const cards = [cur, ...worked].filter(Boolean).slice(0, 3);
    const seg = made ? `<div class="k-seg" role="group" aria-label="온톨로지 종류">${[['all', `전체 ${all.length}`], ['server', `서버 제공 ${all.length - made}`], ['made', `이 세션에서 만든 것 ${made}`]].map(([k, w]) => `<button class="${e.kind === k ? 'on' : ''}" data-act="entKind" data-k="${k}">${w}</button>`).join('')}</div>` : '';
    const land = `<section class="k-card" style="flex:3 1 480px"><div class="k-ch"><h2>${inTeam() ? '로그인한 뒤 어디로 가나요' : '처음 들어오면 어디로 가나요'}</h2></div>
      <a class="k-row" href="#home"><span class="k-col"><span class="k-ink k-14">온톨로지가 하나이거나 마지막에 쓴 온톨로지가 있으면</span><span class="k-s">그 온톨로지의 홈이 바로 열립니다</span></span><span class="k-h end"><span class="k-chip">홈</span></span>${ki('chevR', 16, 1.75)}</a>
      <div class="k-row"><span class="k-col"><span class="k-ink k-14">여러 개인데 쓴 기록이 없으면</span><span class="k-s">이 화면에서 고릅니다</span></span><span class="k-h end"><span class="k-chip">지금 화면</span></span></div>
      ${entManages() || (isSysAdmin() && firstAdmin('sys')) ? '<div class="k-cb" style="padding-top:12px"><span class="k-s">시스템 관리자와 온톨로지 관리자도 같은 규칙으로 들어옵니다. 관리 화면은 왼쪽 위 전환 목록의 ‘이 온톨로지 관리’나 ‘시스템 관리’에서 엽니다</span></div>' : ''}</section>`;
    const packs = isSysAdmin() && known('sys-packs') ? 'sys-packs' : known('library') ? 'library' : '';
    const tree = `<section class="k-card" style="flex:2 1 380px"><div class="k-ch"><h2>도메인 팩 · 기반 관계</h2></div><div class="k-cb"><div class="k-v">${entTree(all)}</div>
      <span class="k-s">도메인 팩은 분야별 출발점이고 기반은 다른 온톨로지를 물려받는 관계입니다. 기반으로 만든 온톨로지는 만든 시점의 모듈을 자기 것으로 갖습니다</span>
      ${packs ? `<a class="k-lnk flat" href="#${packs}">도메인 팩${ki('chevR', 14, 1.75)}</a>` : ''}</div></section>`;
    return `${head}${entMadeCard()}<section class="k-wrap g16" aria-label="최근에 쓴 온톨로지">${cards.map(entCard).join('')}</section>
      <section class="k-card"><div class="k-ch"><h2>모든 온톨로지</h2><span class="k-s">${all.length}개${made ? ` · 서버 제공 ${all.length - made} · 이 세션에서 만든 것 ${made}` : ''}</span><span class="k-pha k-push">${seg}<label class="k-search" style="flex:0 1 280px">${ki('search', 16, 1.75)}<input type="search" data-in="entQ" value="${esc(e.q)}" placeholder="온톨로지 검색" aria-label="온톨로지 검색"></label></span></div>
        <div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">도메인 팩 · 기반</th><th scope="col">성숙도</th><th scope="col">운영 버전</th><th scope="col">상태</th><th scope="col">내 역할</th><th scope="col"></th><th scope="col">관리 동작</th></tr></thead><tbody id="enttbody">${entRows()}</tbody></table></div>
        ${made ? '<p class="k-cf line">이 세션에서 만든 온톨로지는 세션이 끝나면 사라집니다. 계속 쓰려면 내보내기로 내려받아 서버에 등록합니다</p>' : ''}</section>
      <div class="k-cols">${land}${tree}</div>`;
  }
  screen('ontologies', { area: 'bare', word: '온톨로지 선택', crumb: ['온톨로지 선택'], view: viewOntologies, after: entNeed });

  // ---- making an ontology ---------------------------------------------------------------------------------------
  const ENT_START = [['pack', '도메인 팩으로 시작', '검증된 Object · 규칙 · 질문 포함'], ['base', '기존 온톨로지를 기반으로', '표준을 물려받고 Custom만 추가'],
    ['files', '파일에서 가져오기', 'OWL · TTL · YAML'], ['ai', 'AI 초안으로 시작', '자료를 올리면 Object · Entity 초안 생성']];
  function entNew() {
    const e = S.ent, hash = location.hash;
    if (!e.nw || e.nw.from !== hash) {
      const start = itemParam('start'), base = itemParam('base');
      e.nw = { from: hash, start: ENT_START.some((x) => x[0] === start) ? start : (base ? 'base' : 'pack'), base: base || S.st.library_id, label: '', key: '', desc: '', mods: null, busy: false };
    }
    return e.nw;
  }
  const entBase = (nw) => (S.ent.onto ? S.ent.onto.ontologies.find((o) => o.id === nw.base) || S.ent.onto.ontologies.find((o) => o.current) : null);
  // the modules the picked ones stand on: they come along whether picked or not
  function entNeeded(rows, picked) {
    const by = Object.fromEntries(rows.map((r) => [r.name, r])), need = new Set();
    const walk = (n) => ((by[n] || {}).requires || []).forEach((q) => { if (by[q] && !need.has(q)) { need.add(q); walk(q); } });
    picked.forEach(walk);
    return need;
  }
  const entPicked = (nw, rows) => (nw.start === 'base' ? new Set(rows.filter((r) => r.on).map((r) => r.name)) : nw.mods || new Set(rows.filter((r) => r.on).map((r) => r.name)));
  const ENT_HOLDS = [['areas', 'Object'], ['objects', 'Entity'], ['rule_cards', '규칙 카드'], ['decisions', '결정표'], ['terms', '용어'], ['questions', '검증 질문']];
  const entHolds = (r) => ENT_HOLDS.filter(([k]) => r.counts[k]).map(([k, w]) => `${w} ${count(r.counts[k])}`).join(' · ');

  function entMadeOf(nw) {  // what the choices so far would make: [word, value]
    const keep = ['보관', '이 세션에 유지 · 내려받아 서버에 등록'];
    if (nw.start === 'ai') return [['도메인 팩', '없음 · 빈 온톨로지'], ['Object · Entity', '<span class="k-code k-ink">0 · 0</span>'], keep];
    if (nw.start === 'files') {
      // the files' rows by section as they were read. A definition two files both hold is read as one, so these are
      // not yet counts of what is made
      const files = (S.lib.files && S.lib.files.files) || [], rows = {};
      files.forEach((f) => Object.entries(f.sections || {}).forEach(([k, n]) => { rows[k] = (rows[k] || 0) + n; }));
      const said = Object.entries(rows).map(([k, n]) => `${esc(k)} ${count(n)}`).join(' · ');
      return [['파일', `${count(files.length)}개`], ['구역별 행 수', said ? `<span class="k-code k-ink" style="white-space:normal">${said}</span>` : '-'], keep];
    }
    const base = entBase(nw), rows = base ? base.modules : [], picked = entPicked(nw, rows), need = entNeeded(rows, picked);
    const on = rows.filter((r) => picked.has(r.name) || need.has(r.name)), sum = (k) => on.reduce((n, r) => n + (r.counts[k] || 0), 0);
    const dom = on.filter((r) => r.kind === 'domain');
    return [[nw.start === 'base' ? '기반 온톨로지' : '도메인 팩', esc(nw.start === 'base' ? (base ? base.label : '-') : (dom.map((r) => `${r.label} ${r.version}`).join(' · ') || `모듈 ${on.length}개`))],
      ['Object · Entity', `<span class="k-code k-ink">${count(sum('areas'))} · ${count(sum('objects'))}</span>`], ['규칙 카드 · 결정표', `<span class="k-code k-ink">${count(sum('rule_cards'))} · ${count(sum('decisions'))}</span>`],
      ['용어', `<span class="k-code k-ink">${count(sum('terms'))}</span>`], keep];
  }

  function entStep3(nw) {
    if (nw.start === 'ai') return '';
    if (nw.start === 'files') {
      const f = S.lib, held = (f.files && f.files.files) || [];
      const rows = held.map((x) => `<tr><td class="b">${esc(x.name)}</td><td>${x.kind === 'definitions' ? '정의 초안' : 'OWL'}</td><td class="mut">${Object.entries(x.sections || {}).map(([k, n]) => `${esc(k)} ${count(n)}`).join(' · ') || '-'}</td><td class="r nw">${fileSize(x.size)}</td><td class="r"><button class="k-lnk" data-act="libfiledrop" data-name="${esc(x.name)}">빼기</button></td></tr>`).join('');
      return `<section class="k-card"><div class="k-ch"><h2>3 · 파일</h2><span class="k-pha k-push"><button class="k-btn sm" data-act="libpick"${f.up ? ' disabled' : ''}>${ki('upload', 16, 1.75)}${f.up ? '읽는 중' : '파일 추가'}</button><input type="file" id="libfileinput" multiple hidden accept=".yaml,.yml,.json,.ttl,.owl,.rdf"></span></div>
        ${held.length ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">파일</th><th scope="col">형식</th><th scope="col">구역별 행 수</th><th scope="col" class="r">크기</th><th scope="col"></th></tr></thead><tbody>${rows}</tbody></table></div>` : ''}
        <p class="k-cf${held.length ? ' line' : ''}">정의 초안 YAML · JSON(구역: objects · entities · relations · rules · parameters · terms)과 OWL .ttl · .owl · .rdf를 읽습니다. 정의 초안은 여러 파일을 하나로 읽습니다 · 최대 ${count((f.files && f.files.files_max) || 8)}개</p></section>`;
    }
    const base = entBase(nw), rows = base ? base.modules : [], picked = entPicked(nw, rows), need = entNeeded(rows, picked), whole = nw.start === 'base';
    const shown = whole ? rows.filter((r) => r.on) : rows;
    const body = shown.map((r) => { const locked = whole || need.has(r.name), on = locked || picked.has(r.name);
      return `<tr><td>${esc(r.label)}</td><td>${esc(r.kind_label)}</td><td><span class="k-code k-mut">${esc(r.version)}</span></td><td class="i3">${esc(entHolds(r) || r.description.split('. ')[0])}</td>
        <td><input type="checkbox" data-in="entMod" data-mod="${esc(r.name)}"${on ? ' checked' : ''}${locked ? ' disabled' : ''} aria-label="${esc(r.label)}${locked ? ' 필수' : ''}"></td></tr>`; }).join('');
    return `<section class="k-card"><div class="k-ch"><h2>${whole ? '3 · 물려받는 모듈' : '3 · 도메인 팩 모듈'}</h2>${known('library') && base && base.current ? `<span class="k-pha k-push"><a class="k-lnk" href="#library">모듈 라이브러리${ki('chevR', 14, 1.75)}</a></span>` : ''}</div>
      <div class="k-x"><table class="k-t"><thead><tr><th scope="col">모듈</th><th scope="col">종류</th><th scope="col">버전</th><th scope="col">포함</th><th scope="col">적용</th></tr></thead><tbody>${body || '<tr><td colspan="5" class="mut">이 온톨로지에는 모듈이 없습니다. 다른 시작 방법을 선택해 주세요.</td></tr>'}</tbody></table></div>
      <p class="k-cf">${whole ? '기반 온톨로지가 적용한 모듈을 그대로 물려받습니다 · 데이터 소스 연결은 가져오지 않습니다' : '기반 온톨로지를 바꾸면 목록이 그 온톨로지의 모듈로 바뀝니다 · 필수 모듈은 뺄 수 없고 나머지는 만든 뒤 온톨로지 › 모듈 라이브러리에서 바꿉니다'}</p></section>`;
  }

  function viewOntologyNew() {
    const e = S.ent;
    const head = kHead('온톨로지 만들기', '도메인 팩이나 기존 온톨로지에서 시작합니다. 팩이 없는 분야는 자료를 올려 AI 초안으로 시작할 수 있습니다. 데이터 소스 연결 없이 시작합니다.', '<a class="k-btn" href="#ontologies">취소</a>');
    if (e.err) return head + stateBlock('error', { say: e.err });
    if (!e.onto) return `${head}<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>`;
    const nw = entNew(), all = e.onto.ontologies, left = Math.max(e.onto.made_max - e.onto.made, 0);
    const tile = ([k, w, say]) => `<label class="k-ck box"><input type="radio" name="entstart" value="${k}" data-in="entStart"${nw.start === k ? ' checked' : ''}><span class="k-14">${w}<br><span class="k-s">${say}</span></span></label>`;
    const withBase = nw.start === 'pack' || nw.start === 'base';
    const baseSel = withBase ? `<label class="k-f">기반 온톨로지<select class="k-in" data-in="entBase">${all.filter((o) => o.modules.length).map((o) => `<option value="${esc(o.id)}"${o.id === (entBase(nw) || {}).id ? ' selected' : ''}>${esc(o.label)}</option>`).join('')}</select>
      <span class="k-hint">${nw.start === 'base' ? '기반을 고르면 그 온톨로지가 적용한 모듈을 모두 물려받습니다' : '이 온톨로지의 모듈 라이브러리에서 팩을 고릅니다'}</span></label>` : '';
    const made = entMadeOf(nw), aiFirst = nw.start === 'ai' && known('ai');
    const go = (to, word, pri) => `<button class="k-btn wide${pri ? ' pri' : ''}" data-act="entMake" data-go="${to}"${nw.busy || !left ? ' disabled' : ''}>${nw.busy && pri ? '만드는 중' : word}</button>`;
    return `${head}<div class="k-cols"><div class="k-c3 wide">
      <section class="k-card"><div class="k-ch"><h2>1 · 시작 방법</h2></div><div class="k-cb"><div class="ent-tiles">${ENT_START.map(tile).join('')}</div></div></section>
      <section class="k-card"><div class="k-ch"><h2>2 · 기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">이름<input class="k-in" type="text" data-in="entNl" id="entnl" value="${esc(nw.label)}" maxlength="60"></label>
        <label class="k-f">키<input class="k-in mono" type="text" data-in="entNk" value="${esc(nw.key)}" maxlength="40"><span class="k-hint">네임스페이스와 내보내기 파일 이름에 쓰입니다 · 비우면 자동으로 정합니다</span></label>
        ${baseSel}</div>
        <label class="k-f">설명<input class="k-in" type="text" data-in="entNd" value="${esc(nw.desc)}" maxlength="200"></label></div></section>
      ${entStep3(nw)}</div>
      <div class="k-v g24" style="flex:2 1 320px;min-width:0"><section class="k-card"><div class="k-ch"><h2>만들어지는 것</h2></div><div id="entmade">${made.map(([k, v]) => kKv(k, v)).join('')}</div>
        <div class="k-cb" style="padding-top:12px">${aiFirst ? go('ai', '만들고 AI 초안 생성', true) + go('home', '만들기') : go('home', '만들기', true) + (known('ai') ? go('ai', '만들고 AI 초안 생성') : '')}${canEdit() ? go('catalog', '만들고 자료 업로드') : ''}
          <span class="k-s">${left ? `한 세션에 ${e.onto.made_max}개까지 만듭니다 · 남은 ${left}개` : `한 세션에 만들 수 있는 ${e.onto.made_max}개를 모두 만들었습니다. 만든 온톨로지를 삭제한 뒤 다시 만듭니다`}</span></div></section>
        <p class="k-note">팩이 없는 분야는 ‘AI 초안으로 시작’을 고릅니다. 자료를 올리면 ${known('ai') ? '<a href="#ai">AI 초안 생성</a>이' : 'AI 초안 생성이'} Object와 Entity 후보를 만들고 사람이 검토해 승인합니다.</p></div></div>`;
  }
  screen('ontology-new', { area: 'bare', word: '온톨로지 만들기', crumb: ['온톨로지 만들기'], may: () => canMakeLibrary(), view: viewOntologyNew,
    after: () => {
      entNeed();
      const nw = S.ent.nw;
      if (nw && nw.start === 'files' && !S.lib.files && !S.ent.filesBusy) {
        S.ent.filesBusy = true;
        api('library/files').then((x) => { S.lib.files = x; }).catch(fail).finally(() => { S.ent.filesBusy = false; if (S.tab === 'ontology-new' && !entOut()) render(); });
      }
    } });

  async function entMake(go) {
    const nw = entNew();
    if (nw.busy) return;
    if (!nw.label.trim()) { toast('이름이 없어 만들지 못했습니다. 이름을 입력해 주세요.', true); const el = $('#entnl'); if (el) el.focus(); return; }
    if (nw.start === 'files' && !((S.lib.files && S.lib.files.files) || []).length) { toast('파일이 없어 만들지 못했습니다. 정의 초안 또는 OWL 파일을 추가해 주세요.', true); return; }
    const base = entBase(nw), body = { label: nw.label, key: nw.key, description: nw.desc, start: nw.start === 'ai' ? 'empty' : nw.start };
    if (nw.start === 'pack' || nw.start === 'base') body.base = base ? base.id : '';
    if (nw.start === 'pack') body.modules = [...entPicked(nw, base ? base.modules : [])];
    nw.busy = true; render();
    try {
      const res = await api('entry/ontology/new', body);
      S.lib.res = res; S.lib.files = null; S.ent.nw = null; S.ent.onto = null; S.ent.sig = '';
      clearViews();
      Object.assign(S.home, { box: null, ov: null });
      S.mg.st = null; S.ver = null; S.lx.st = null; S.sem.st = null;
      location.hash = `#${known(go) ? go : 'home'}`;
      await load();
      entRemember(res.id);
      const rep = res.report, more = rep && (rep.adjusted.count || rep.unsupported.count) ? ` 조정 ${count(rep.adjusted.count)}건 · 옮기지 못한 항목 ${count(rep.unsupported.count)}건은 온톨로지 선택에서 확인합니다.` : '';
      toast(`${res.label} 온톨로지를 만들었습니다.${more}`);
    } catch (err) { nw.busy = false; render(); fail(err); }
  }

  // ---- the person's own screens ---------------------------------------------------------------------------------
  // how this server lets people in (how long a sign-in lasts, whether a password can be changed here), read once
  function entAcctNeed() {
    const e = S.ent;
    if (e.acct || e.acctBusy) return;
    e.acctBusy = true;
    api('entry/me').then((x) => { e.acct = x; }).catch(() => { e.acct = {}; }).finally(() => { e.acctBusy = false; if ((S.tab === 'me' || S.tab === 'reset') && !entOut()) render(); });
  }
  const ENT_ROLE_SAY = { 관리자: '전체 영역 · 이 온톨로지 관리', '영역 담당': '편집 · 승인 · 배포', 편집: '정의와 규칙 편집 · 변경 요청', 조회: '조회와 질문' };
  function viewMe() {
    const team = inTeam(), u = team ? S.me.user : null, libs = S.st.libraries || [], sys = isSysAdmin() && firstAdmin('sys'), acct = S.ent.acct || {};
    const head = kHead('내 계정', '내 계정과 역할, 들어갈 수 있는 곳을 봅니다. 내 계정은 관리 화면이 아니라 누구에게나 있는 개인 화면이고 상단 계정 버튼에서 엽니다.',
      `<a class="k-btn" href="#inbox">${ki('inbox', 16, 1.75)}할 일 · 알림</a>${team ? '<button class="k-btn" data-act="entLogout">로그아웃</button>' : ''}`);
    const profile = `<section class="k-card"><div class="k-ch"><h2>프로필</h2></div><div class="k-cb"><div class="k-g2">
      <label class="k-f">이름<input class="k-in" type="text" value="${esc(u ? u.name : S.st.who || '방문자')}" readonly>${team ? `<span class="k-hint">${acct.can_change_password ? '이름은 시스템 관리자가 바꿉니다' : '이름과 비밀번호는 시스템 관리자가 바꿉니다'}</span>` : ''}</label>
      ${u ? `<label class="k-f">아이디<input class="k-in mono" type="text" value="${esc(u.id)}" readonly></label>` : ''}</div>
      ${team ? '' : '<span class="k-s">로그인 없이 쓰는 세션입니다. 이 세션에서 고친 정의와 올린 자료는 다른 방문자에게 보이지 않습니다</span>'}</div></section>`;
    const guide = known('guide') ? `<a class="k-row" href="#guide"><span class="k-col"><span class="k-ink k-14">사용 안내</span><span class="k-s">화면별 사용 방법과 소개 영상</span></span>${ki('chevR', 16, 1.75)}</a>` : '';
    const reset = isSysAdmin() ? `<div class="k-row"><span class="k-col"><span class="k-ink k-14">초기화</span><span class="k-s">${S.st.data.kept ? '변경 내용을 지우고 예시로 되돌립니다. 레포지토리의 파일은 남습니다' : '올린 데이터와 변경 내용을 모두 지우고 예시로 되돌립니다'}</span></span><span class="k-h end"><button class="k-btn dan" data-act="reset">초기화</button></span></div>` : '';
    const help = guide || reset ? `<section class="k-card"><div class="k-ch"><h2>사용 안내 · 세션</h2></div>${guide}${reset}</section>` : '';
    const security = `<section class="k-card"><div class="k-ch"><h2>로그인 보안</h2></div>${kKv('계정', team ? '로컬 계정' : '로그인 없음 · 방문자 세션')}${team ? kKv('비밀번호', acct.can_change_password ? `<a class="k-lnk" href="#reset">변경${ki('chevR', 14, 1.75)}</a>` : '<span class="k-s">시스템 관리자가 변경</span>') + (acct.hours ? kKv('로그인 유지', `${esc(acct.hours)}시간`) : '')
      : (acct.idle_minutes ? kKv('세션', `${esc(acct.idle_minutes)}분 동안 쓰지 않으면 끝남`) : '')}</section>`;
    const sysRow = `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${team ? (isSysAdmin() ? '시스템 관리자' : '사용자') : '이 세션의 관리자'}</span><span class="k-s">${team ? (isSysAdmin() ? '시스템 역할 · 관리 › 시스템 관리 전체' : '시스템 역할 · 온톨로지 작업') : '로그인 없는 서버 · 모든 화면 사용'}</span></span>${sys ? `<span class="k-h end"><a class="k-lnk" href="#${V2['sys-users'] ? 'sys-users' : sys}">시스템 관리${ki('chevR', 14, 1.75)}</a></span>` : ''}</div>`;
    const role = workRole();
    const rows = libs.map((x) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(x.label)} · ${esc(role)}</span><span class="k-s">작업 역할 · ${esc(ENT_ROLE_SAY[role] || '')}</span></span><span class="k-h end"><button class="k-lnk" data-act="entOpen" data-id="${esc(x.id)}"${entManages() ? ` data-go="${esc(entManages())}"` : ''}>${entManages() ? '온톨로지 관리' : '열기'}${ki('chevR', 14, 1.75)}</button></span></div>`).join('');
    const roles = `<section class="k-card"><div class="k-ch"><h2>내 역할 · 들어갈 수 있는 곳</h2></div>${sysRow}${rows}<div class="k-cb" style="padding-top:12px"><span class="k-s">역할에 따라 왼쪽 위 전환 목록에 보이는 항목이 달라집니다</span><a class="k-lnk flat" href="#ontologies">온톨로지 선택${ki('chevR', 14, 1.75)}</a></div></section>`;
    return `${head}<div class="k-cols"><div class="k-v g24" style="flex:3 1 520px;min-width:0">${profile}${help}</div><div class="k-c2 wide">${security}${roles}</div></div>`;
  }
  screen('me', { area: 'bare', word: '내 계정', crumb: ['계정', '내 계정'], view: viewMe, after: entAcctNeed });

  // a local account's own password, changed with the one it has now
  function viewReset() {
    const a = S.ent.acct;
    if (!inTeam()) return `<div class="ent-narrow">${stateBlock('missing', { title: '이 서버는 로그인 없이 씁니다', say: '비밀번호가 없는 서버입니다. 방문자마다 자기 세션에서 작업합니다.', acts: [['#me', '내 계정', 'pri']] })}</div>`;
    if (!a) return '<div class="ent-auth"><section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section></div>';
    if (!a.can_change_password) return `<div class="ent-narrow">${stateBlock('missing', { title: '이 서버에서는 비밀번호를 바꿀 수 없습니다', say: '시스템 관리자에게 새 비밀번호를 요청합니다.', acts: [['#me', '내 계정', 'pri']] })}</div>`;
    return `<div class="ent-auth"><section class="k-card ent-form"><div><h1 class="k-h1" style="line-height:1.3">비밀번호 재설정</h1><p class="k-p" style="margin-top:4px;color:var(--muted)">로컬 계정의 비밀번호를 바꿉니다. 지금 비밀번호를 잊었으면 시스템 관리자에게 새 비밀번호를 요청합니다</p></div>
        <label class="k-f">지금 비밀번호<input class="k-in" type="password" id="entpw0" autocomplete="current-password"></label>
        <label class="k-f">새 비밀번호<input class="k-in" type="password" id="entpw1" autocomplete="new-password"><span class="k-hint">${esc(a.password_min)}자 이상</span></label>
        <label class="k-f">새 비밀번호 확인<input class="k-in" type="password" id="entpw2" autocomplete="new-password"></label>
        <button class="k-btn pri wide" data-act="entPw"${S.ent.pwBusy ? ' disabled' : ''}>비밀번호 변경</button>
        <span class="k-s">변경하면 모든 기기에서 로그아웃됩니다</span></section>
      <p class="k-crumb" style="text-align:center;flex:none"><a href="#me">내 계정으로 돌아가기</a></p></div>`;
  }
  screen('reset', { area: 'bare', word: '비밀번호 재설정', find: false, crumb: ['계정', '비밀번호 재설정'], view: viewReset, after: entAcctNeed });

  const ENT_NOTE = { change: ['b', '변경 요청', 'changes'], approve: ['ok', '액션', 'decide'], request: ['', '액션', 'decide'], draft: ['', '초안', 'data'], attach: ['', '모듈', 'library'], detach: ['', '모듈', 'library'],
    flow: ['', '검증', 'flow'], identity: ['', '식별 통합', 'objects'], sync: ['', '동기화', 'db'] };
  function entTodoRow(x) {
    const box = S.home.box, [tone, word] = INBOX_KIND[x.kind] || ['', x.kind];
    let meta = '', to = '', buttons = '';
    if (x.kind === 'action') {
      meta = [`${x.by}${x.by_kind === 'agent' && !/agent/i.test(x.by) ? ' · Agent' : ''} 요청`, x.change, x.failed.length ? `검사 미통과 ${x.failed.join(', ')}` : '판정 · 권한 검사 통과', x.delta || (x.outside ? '자동 승인 한도 밖' : '')].filter(Boolean).join(' · ');
      to = `data-act="rec" data-type="${esc(x.target)}" data-key="${esc(x.key)}"`;
      buttons = x.mine && !box.alone ? '' : `<button class="k-btn sm pri" data-act="ibapprove" data-id="${esc(x.id)}">승인</button><button class="k-btn sm" data-act="ibreject" data-id="${esc(x.id)}">반려</button>`;
    } else if (x.kind === 'change') {
      const d = x.diff || {}, worse = (x.worse || []).map((w) => `${w.label} ${w.rate ? pct(w.was) : w.was} → ${w.rate ? pct(w.now) : w.now}`).join(' · ');
      meta = `${x.by} 작성 · 회귀 테스트 ${x.passed ? '통과' : '미통과'} ${x.gates[0]}/${x.gates[1]}${worse ? ` · ${worse}` : ''} · 추가 ${d.added || 0} · 변경 ${d.changed || 0} · 제거 ${d.removed || 0}`;
      to = `data-act="ibchange" data-id="${esc(x.id)}"`;
    } else if (x.kind === 'check') {
      meta = x.detail; to = 'data-act="issopen" data-key="bind"';
    } else if (x.kind === 'conflict') {
      meta = `${x.detail} · 고를 때까지 기존 규칙으로 판정합니다`; to = `data-act="issopen" data-key="conflict:${esc(x.id)}"`;
    } else if (x.kind === 'draft') {
      meta = `${x.by} 요청 · ${x.detail} · 검토한 그대로 적용됩니다`; to = 'href="#data"';
      buttons = canApplyDraft() ? '<button class="k-btn sm pri" data-act="drequestapply">적용</button><button class="k-btn sm" data-act="drequestdrop">반려</button>' : x.mine ? '<button class="k-btn sm" data-act="drequestdrop">요청 거두기</button>' : '';
    } else {
      meta = `${x.detail} · ${selfApply() ? '검토 후 적용해야' : '변경 요청을 올려야'} 반영됩니다`; to = 'href="#changes"';
    }
    return `<div class="k-row" data-row="${esc(x.kind)}:${esc(x.id)}"><a class="k-col ent-go" ${to.startsWith('href') ? to : `href="#" ${to}`}><span class="k-ink k-14">${esc(x.title)}</span><span class="k-s">${esc(meta)}</span></a><span class="k-h end">${buttons}<span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span></span><a class="ent-go" ${to.startsWith('href') ? to : `href="#" ${to}`} aria-label="${esc(x.title)} 열기">${ki('chevR', 16, 1.75)}</a></div>`;
  }
  function entTodoCard() {
    const h = S.home, box = h.box;
    const filt = box && !box.alone ? `<div class="k-push"><div class="k-seg" role="group" aria-label="할 일 범위">${INBOX_TAB.map(([k, w]) => `<button class="${h.tab === k ? 'on' : ''}" data-act="ibtab" data-k="${k}">${k === 'all' ? '팀 전체' : w} ${box.counts[k]}</button>`).join('')}</div></div>` : '';
    const head = `<div class="k-ch"><h2>할 일</h2><span class="k-s">${h.tab === 'mine' && box && !box.alone ? '내가 요청해 기다리는 것' : '내가 처리해야 하는 것'}</span>${filt}</div>`;
    let body = '';
    if (h.err) body = '<div class="k-cb"><span class="k-s">서버 응답 오류로 할 일을 불러오지 못했습니다.</span><div class="k-h"><button class="k-btn sm" data-act="ibretry">다시 시도</button></div></div>';
    else if (!box) body = '<p class="k-cf">불러오는 중입니다.</p>';
    else body = inboxShown(h.tab).map(entTodoRow).join('') || `<p class="k-cf line">${h.tab === 'mine' ? '내가 요청해 기다리는 일이 없습니다.' : '처리할 일이 없습니다. 승인, 변경 검토, 충돌 선택이 생기면 여기에 모입니다.'}</p>`;
    return `<section class="k-card" style="flex:1 1 480px">${head}${body}</section>`;
  }
  function entNotesCard() {
    const m = S.ent.more, notes = m ? m.notes : null;
    const row = (n) => { const [tone, word, to] = ENT_NOTE[n.kind] || ['', n.kind, ''], link = to && known(to);
      return `<${link ? `a href="#${to}"` : 'div'} class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(n.text)}</span><span class="k-s">${esc(entWhen(n.at))}</span></span><span class="k-h end"><span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span></span>${link ? ki('chevR', 16, 1.75) : ''}</${link ? 'a' : 'div'}>`; };
    return `<section class="k-card" style="flex:1 1 480px"><div class="k-ch"><h2>알림</h2><span class="k-s">${notes ? `이 온톨로지에서 일어난 일 · 최근 ${notes.length}건` : '이 온톨로지에서 일어난 일'}</span></div>
      ${!notes ? '<p class="k-cf">불러오는 중입니다.</p>' : notes.map(row).join('') || '<p class="k-cf line">아직 알림이 없습니다. 변경 요청, 승인, 모듈 적용이 생기면 여기에 남습니다.</p>'}</section>`;
  }
  function entDoneCard() {
    const m = S.ent.more, done = m ? m.done : null;
    const row = (x) => { const [tone, word] = x.kind === 'change' ? [CHANGE_STATUS[x.status] || '', x.status_label] : (STATUS[x.status] || ['', x.status]);
      const to = x.kind === 'change' ? `data-act="ibchange" data-id="${esc(x.id)}"` : `data-act="rec" data-type="${esc(x.target)}" data-key="${esc(x.key)}"`;
      return `<a class="k-row" href="#" ${to}><span class="k-col"><span class="k-ink k-14">${esc(x.title)}</span><span class="k-s">${esc([x.by, entWhen(x.at), x.detail].filter(Boolean).join(' · '))}</span></span><span class="k-h end"><span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span></span>${ki('chevR', 16, 1.75)}</a>`; };
    return `<section class="k-card" style="flex:1 1 480px"><div class="k-ch"><h2>완료</h2><span class="k-s">승인하거나 반려한 변경 요청과 액션</span></div>
      ${!done ? '<p class="k-cf">불러오는 중입니다.</p>' : done.map(row).join('') || '<p class="k-cf line">아직 처리한 일이 없습니다.</p>'}</section>`;
  }
  function viewInboxV2() {
    const e = S.ent, box = S.home.box, m = e.more;
    const head = kHead('할 일 · 알림', '지금 열린 온톨로지의 승인 · 검토 요청과 알림을 모아 봅니다. 항목을 누르면 처리하는 화면으로 이동합니다.');
    const tabs = [['todo', `할 일${box ? ` ${box.counts.assigned}` : ''}`], ['notes', `알림${m ? ` ${m.notes.length}` : ''}`], ['done', '완료']];
    const seg = `<div class="k-pha"><div class="k-seg" role="group" aria-label="보기">${tabs.map(([k, w]) => `<button class="${e.tab === k ? 'on' : ''}" data-act="entTab" data-k="${k}">${w}</button>`).join('')}</div></div>`;
    return `${head}${seg}<div class="k-cols">${e.tab === 'done' ? entDoneCard() : e.tab === 'notes' ? entNotesCard() : entTodoCard() + entNotesCard()}</div>`;
  }
  screen('inbox', { area: 'bare', word: '할 일 · 알림', crumb: ['계정', '할 일 · 알림'], view: viewInboxV2,
    after: () => {
      const h = S.home, e = S.ent;
      if (!h.box && !h.busy && !h.err) loadInbox();
      if (h.box && e.moreFor !== h.box && !e.moreBusy) {  // what happened and what was settled are read again whenever the list is
        e.moreBusy = true;
        const of = h.box;
        api('entry/inbox').then((x) => { e.more = { notes: x.notes, done: x.done }; }).catch(() => { e.more = { notes: [], done: [] }; })
          .finally(() => { e.moreFor = of; e.moreBusy = false; if (S.tab === 'inbox' && !entOut()) render(); });
      }
    } });

  // ---- sign-in --------------------------------------------------------------------------------------------------
  function viewLogin() {
    if (!(inTeam() && !S.me.user)) {  // someone already inside opened this address
      return `<div class="k-main"><div class="ent-narrow">${stateBlock('missing', inTeam() ? { title: '이미 로그인했습니다', say: `${S.me.user.name} 님으로 로그인한 상태입니다. 다른 계정으로 들어가려면 먼저 로그아웃합니다.`, acts: [['#home', '홈으로', 'pri'], ['@entLogout', '로그아웃']] }
        : { title: '이 서버는 로그인 없이 씁니다', say: '방문자마다 자기 세션에서 작업합니다. 팀이 함께 쓰는 서버는 사용자 목록과 함께 띄웁니다.', acts: [['#home', '홈으로', 'pri']] })}</div></div>`;
    }
    const expired = S.st && !S.ent.out;  // was inside and did not sign out: the sign-in ran out
    S.ent.out = false;
    return `<div class="k-auth">${brand('#')}<main>
      <section class="k-card"><div><h1 class="k-h1" style="line-height:1.3">로그인</h1><p class="k-p" style="margin-top:4px;color:var(--muted)">계정으로 로그인합니다</p></div>
        ${expired ? '<p class="k-note warn">로그인한 지 12시간이 지나 로그아웃됐습니다. 다시 로그인해 주세요.</p>' : ''}
        <label class="k-f">아이디<input class="k-in" type="text" id="luser" autocomplete="username" autofocus></label>
        <label class="k-f">비밀번호<input class="k-in" type="password" id="lpw" autocomplete="current-password"></label>
        <div class="k-h end"><button class="k-lnk flat" type="button" data-act="entForgot">비밀번호 재설정</button></div>
        <button class="k-btn pri wide" data-act="login">로그인</button></section>
      <section class="k-card"><div class="k-h sb base"><h2 class="k-h2">로그인하면</h2><span class="k-s">역할과 관계없이 같은 규칙</span></div>
        <div class="k-v k-14" style="line-height:1.6"><span>온톨로지가 하나이거나 마지막에 쓴 온톨로지가 있으면 → 그 온톨로지의 홈</span><span>여러 개인데 쓴 기록이 없으면 → 온톨로지 선택</span></div>
        <span class="k-s">관리 화면은 로그인 직후에 열리지 않습니다. 권한이 있는 사람이 왼쪽 위 전환 목록에서 들어갑니다</span></section>
      <p class="k-note">로그인 시도는 1분에 10번까지 받습니다 · 계정이 없으면 시스템 관리자에게 등록을 요청합니다</p></main></div>`;
  }
  screen('login', { area: 'auth', word: '로그인', find: false, view: viewLogin });
  document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter') return;
    if (ev.target.id === 'lpw' || ev.target.id === 'luser') { ev.preventDefault(); ACT.login(); }
    if (ev.target.id === 'entpw2') { ev.preventDefault(); ACT.entPw(); }
  });

  // ---- arriving: the last ontology worked in, or the list to choose from ------------------------------------------
  window.addEventListener('hashchange', () => {  // working in an ontology is what makes it the last one used
    const tab = location.hash.slice(1).split('?')[0] || 'home';
    if (S.st && areaOf(tab) === 'work') entRemember(S.st.library_id);
  });
  function entLand() {
    if (location.hash.length > 1) return;  // came to a screen by its address
    const libs = S.st.libraries || [], last = entWorked()[0];
    if (last && last.id !== S.st.library_id && !inTeam()) { libraryUse(last.id); return; }
    if (!last && libs.length > 1) location.hash = '#ontologies';
  }
  const entArrive = setInterval(() => { if (S.st) { clearInterval(entArrive); entLand(); } }, 100);

  Object.assign(ACT, {
    entOpen: async (t) => {  // into an ontology: its home, or the screen the button names
      const id = t.dataset.id, go = t.dataset.go || 'home';
      if (id !== S.st.library_id) await libraryUse(id);
      if (S.st.library_id !== id) return;  // it did not open; libraryUse said why
      entRemember(id);
      location.hash = `#${go}`;
    },
    entExport: async (t) => {
      const id = t.dataset.id;
      if (id !== S.st.library_id) await libraryUse(id);
      if (S.st.library_id !== id) return;
      const a = document.createElement('a');
      a.href = '/api/export/library'; a.download = '';
      document.body.appendChild(a); a.click(); a.remove();
    },
    entKind: (t) => { S.ent.kind = t.dataset.k; render(); },
    entMake: (t) => entMake(t.dataset.go),
    entTab: (t) => { S.ent.tab = t.dataset.k; render(); },
    entReload: () => location.reload(),
    entLogout: () => { S.ent.out = true; ACT.logout(); },
    entForgot: () => {  // before signing in there is nothing to prove who asks: the way on is said
      $('#main').innerHTML = `<div class="k-auth">${brand('#')}<main><section class="k-card"><div><h1 class="k-h1" style="line-height:1.3">비밀번호 재설정</h1>
        <p class="k-p" style="margin-top:4px;color:var(--muted)">로컬 계정의 비밀번호는 로그인한 뒤 내 계정에서 바꿉니다. 비밀번호를 잊었으면 시스템 관리자에게 새 비밀번호를 요청하고, 그 비밀번호로 로그인해 바꿉니다</p></div>
        <button class="k-btn wide" type="button" data-act="entBack">로그인으로 돌아가기</button></section></main></div>`;
    },
    entBack: () => { S.ent.out = true; renderLogin(); },
    entPw: async () => {
      const e = S.ent, now = ($('#entpw0') || {}).value || '', next = ($('#entpw1') || {}).value || '', again = ($('#entpw2') || {}).value || '';
      const min = (e.acct && e.acct.password_min) || 10;
      if (e.pwBusy) return;
      if (!now || !next) { toast('비밀번호를 입력하지 않아 바꾸지 못했습니다. 지금 비밀번호와 새 비밀번호를 입력해 주세요.', true); return; }
      if (next !== again) { toast('새 비밀번호와 확인이 달라 바꾸지 못했습니다. 다시 입력해 주세요.', true); const el = $('#entpw2'); if (el) el.focus(); return; }
      if (next.length < min) { toast(`새 비밀번호가 ${min}자보다 짧아 바꾸지 못했습니다. ${min}자 이상으로 입력해 주세요.`, true); return; }
      e.pwBusy = true;
      try {
        await api('entry/password', { current: now, new: next });
        e.pwBusy = false; e.out = true;
        S.me.user = null;  // every sign-in of this account ended with the change
        renderLogin();
        toast('비밀번호를 바꿨습니다. 새 비밀번호로 다시 로그인해 주세요.');
      } catch (err) { e.pwBusy = false; fail(err); }
    },
  });
  Object.assign(INPUT, {
    entQ: (t) => { S.ent.q = t.value; const box = $('#enttbody'); if (box) box.innerHTML = entRows(); },
    entNl: (t) => { entNew().label = t.value; },
    entNk: (t) => { entNew().key = t.value; },
    entNd: (t) => { entNew().desc = t.value; },
    entStart: (t) => { const nw = entNew(); nw.start = t.value; nw.mods = null; render(); },
    entBase: (t) => { const nw = entNew(); nw.base = t.value; nw.mods = null; render(); },
    entMod: (t) => {
      const nw = entNew(), base = entBase(nw), on = new Set(entPicked(nw, base ? base.modules : []));
      if (t.checked) on.add(t.dataset.mod); else on.delete(t.dataset.mod);
      nw.mods = on; render();
    },
  });
