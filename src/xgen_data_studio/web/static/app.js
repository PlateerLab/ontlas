'use strict';
(() => {
  const ICON = {
    library: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="16" rx="1"/><path d="M17 5.5l3.5-1 3 15-3.5 1z"/>',
    onto: '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7 7.5l3.6 8.3M17 7.5l-3.6 8.3M7.5 6h9"/>',
    query: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 4l-4 16"/>',
    decide: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    check: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 12l3 3 5-6"/>',
    bind: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
  };
  const NAV = [['library', '온톨로지 라이브러리'], ['onto', '온톨로지'], ['query', '질의'], ['decide', '판정 · 처리'],
    ['check', '검증'], ['bind', 'DB 대조']];
  const ELEMENT = { object: '객체', property: '속성', link: '관계', decision: '결정', action: '액션', query: '질의',
    question: '검증 질문', role: '역할', interface: '인터페이스', rule: '규칙' };
  const FINDING = { table: '테이블 없음', column: '컬럼 없음', type: '타입 불일치', key: '키 중복', required: '필수 값 누락',
    enum: '정의에 없는 값', orphan: '끊긴 관계' };
  const STATUS = { pending: ['warn', '승인 대기'], rejected: ['bad', '반려'], executed: ['ok', '원천 반영'] };
  const TEXT_LANG = [['sparql', 'SPARQL 1.1'], ['cypher', 'Cypher'], ['ir', '온톨로지 질의 IR (JSON)']];

  const S = {
    st: null, tab: 'library', kind: 'all', impact: null, pos: {}, sel: null, obj: null,
    q: { mode: 'list', name: null, params: {}, role: '', principal: {}, target: 'sql:postgres', res: null,
      lang: 'sparql', text: '', dirty: false, question: '', busy: false },
    d: { name: null, key: null, keys: {}, res: null, proposal: null, params: {}, role: '', audit: [], busy: false },
    qa: null, bind: null,
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
    const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const r = await fetch('/api/' + path, opt);
    let j = {};
    try { j = await r.json(); } catch (_) { /* empty body */ }
    if (!r.ok) throw new Error(j.error || `요청을 처리하지 못했습니다. (${r.status})`);
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
    S.st = await api('state');
    if (S.sel && !S.st.graph.nodes.some((n) => n.id === S.sel)) { S.sel = null; S.obj = null; }
    render();
  }

  function stale() {
    S.q.res = null; S.d.res = null; S.d.proposal = null; S.d.keys = {}; S.qa = null; S.bind = null; S.obj = null;
  }

  // ---- frame ---------------------------------------------------------------------------------------------------

  function renderTop() {
    const st = S.st;
    $('#top').innerHTML = `<div class="brand"><div class="logo">X</div>XGEN 데이터 스튜디오</div>
      <span class="chip b">${esc(st.title)}</span><span class="chip">모듈 ${st.modules_on}개</span>
      <span class="chip warn hide-sm">가상 예시 데이터</span><div class="grow"></div>
      ${st.backends.map((b) => `<span class="chip be"><span class="dot"></span>${esc(b.name)} · ${esc(b.language.toUpperCase())}</span>`).join('')}
      <button class="btn sm ghost" data-act="reset">처음 상태로</button>`;
  }

  function renderSide() {
    const st = S.st;
    const n = { library: st.library.length, onto: st.stats.objects, query: st.stats.queries,
      decide: st.stats.decisions + st.stats.actions, check: st.stats.questions };
    $('#side').innerHTML = '<h6>데이터 스튜디오</h6>' + NAV.map(([k, label]) =>
      `<a class="nav${S.tab === k ? ' on' : ''}" href="#${k}"><svg viewBox="0 0 24 24">${ICON[k]}</svg>${label}` +
      `${n[k] ? `<span class="n">${n[k]}</span>` : ''}</a>`).join('') +
      '<div class="foot"><b>정의는 한곳에, 값은 원천에</b>같은 정의가 원천 DB · 그래프 · 추론기에서 같은 답을 냅니다. ' +
      '여기 데이터는 모두 가상 예시입니다.</div>';
  }

  function render() {
    if (!S.st) return;
    renderTop();
    renderSide();
    const views = { library: viewLibrary, onto: viewOnto, query: viewQuery, decide: viewDecide, check: viewCheck, bind: viewBind };
    const main = $('#main');
    main.innerHTML = (views[S.tab] || viewLibrary)();
    after();
  }

  function after() {
    if (S.tab === 'onto') {
      mountGraph();
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
    if (S.tab === 'bind' && !S.bind) runBindings();
  }

  // ---- library -------------------------------------------------------------------------------------------------

  const counts = (c) => [['objects', '객체'], ['links', '관계'], ['decisions', '결정'], ['queries', '질의'], ['extends', '확장'], ['removes', '제거']]
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
          ${r.description ? `<div class="muted" style="font-size:12px;margin-top:3px;line-height:1.45">${esc(r.description)}</div>` : ''}</td>
        <td><span class="kind"><i style="background:${esc(r.color)}"></i>${esc(r.kind_label)}</span></td>
        <td class="mono" style="white-space:nowrap">${esc(r.version)}</td><td>${req}</td>
        <td class="muted" style="font-size:12.5px">${esc(counts(r.counts))}</td>
        <td style="text-align:center"><button class="switch${r.on ? ' on' : ''}" role="switch" aria-checked="${r.on}"
          aria-label="${esc(r.label || r.name)}" data-act="toggle" data-mod="${esc(r.name)}"></button></td></tr>`;
    }).join('');
    const layers = st.layers.map((l) => `<div class="layer"><div class="lbl"><i style="background:${esc(l.color)}"></i>${esc(l.kind_label)}</div>
      <div class="chips">${l.modules.map((m) => `<span class="chip">${esc(m.label)} <span class="muted mono">${esc(m.version)}</span></span>`).join('')}</div></div>`).join('');
    const log = st.log.length ? st.log.slice(0, 8).map((x) => `<div>${esc(x.text)}</div>`).join('')
      : '<div class="muted">아직 바꾼 것이 없습니다.</div>';
    return `
<div class="head"><div><h1>온톨로지 라이브러리</h1><div class="sub">도메인 온톨로지를 따로 만들고 판본을 관리하며, 스튜디오에 꽂고 뺍니다</div></div>
  <div class="right"><a class="btn ghost" href="/api/export/owl" download>OWL 내보내기</a></div></div>
<div class="tabs">${tabs.join('')}</div>
<div class="grid" style="grid-template-columns:minmax(0,1.62fr) minmax(320px,1fr)">
  <div class="card"><div class="ch">모듈<div class="right muted" style="font-weight:600;font-size:12px">스튜디오에 꽂힌 것 ${st.modules_on}개</div></div>
    <div class="cb scroll" style="padding:0"><table><tr><th>온톨로지</th><th>종류</th><th>판본</th><th>요구</th><th>구성</th><th style="text-align:center">스튜디오</th></tr>${rows}</table></div></div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
    <div class="card"><div class="ch">빼기 전 영향</div><div class="cb">${impactCard()}</div></div>
    <div class="card"><div class="ch">지금 꽂힌 구성<div class="right muted" style="font-weight:600;font-size:12px">아래 층이 위 층에 기댑니다</div></div><div class="cb">${layers}</div></div>
    <div class="card"><div class="ch">변경 기록</div><div class="cb loglist">${log}</div></div>
  </div>
</div>`;
  }

  function impactCard() {
    const imp = S.impact;
    if (!imp) return '<div class="hint">스튜디오 칸의 스위치를 끄면, 빼기 전에 무엇이 함께 빠지는지 먼저 보여 줍니다. 꺼진 모듈을 켜면 필요한 모듈까지 함께 꽂습니다.</div>';
    const list = (xs) => `<div class="chips" style="margin-top:8px">${xs.slice(0, 16).map(element).join('')}${xs.length > 16 ? `<span class="chip sm">외 ${xs.length - 16}개</span>` : ''}</div>`;
    const cancel = '<button class="btn" data-act="cancel-impact">취소</button>';
    if (imp.ok) {
      return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip ok">뺄 수 있음</span></div>
        <div class="muted" style="margin-top:6px;font-size:12.5px">${imp.removed.length}개 항목이 빠집니다.${imp.changed.length ? ` 다른 모듈이 확장한 항목 ${imp.changed.length}개는 원래 정의로 돌아갑니다.` : ''}</div>
        ${list(imp.removed)}${imp.changed.length ? list(imp.changed) : ''}
        <div style="display:flex;gap:8px;margin-top:14px"><button class="btn primary" data-act="detach" data-mod="${esc(imp.module)}"
          data-cascade="${imp.cascade ? 1 : 0}">${imp.cascade ? '함께 빼기' : '빼기'}</button>${cancel}</div>`;
    }
    const deps = imp.dependents_labels || [];
    const cas = imp.cascadeImpact;
    return `<div style="display:flex;align-items:center;gap:8px"><b>${esc(imp.label)}</b><span class="chip warn">함께 빼야 함</span></div>
      <div class="muted" style="margin-top:6px;font-size:12.5px;line-height:1.55">${deps.length ? `이 모듈에 기대는 모듈 ${deps.length}개가 있습니다: ${esc(deps.join(', '))}` : '빼면 남은 정의가 없는 항목을 가리킵니다.'}</div>
      ${deps.length ? '' : `<div class="loglist" style="margin-top:6px">${imp.broken.map((b) => `<div class="mono">${esc(b)}</div>`).join('')}</div>`}
      ${cas && cas.ok ? `<div class="muted" style="margin-top:10px;font-size:12.5px">함께 빼면 ${cas.removed.length}개 항목이 빠집니다.</div>${list(cas.removed)}` : ''}
      <div style="display:flex;gap:8px;margin-top:14px">${cas && cas.ok ? `<button class="btn primary" data-act="detach" data-mod="${esc(imp.module)}" data-cascade="1">함께 빼기</button>` : ''}${cancel}</div>`;
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
        await load();
        if (r.warning) toast(r.warning, true); else toast(`${r.added.map(modLabel).join(', ')} 모듈을 꽂았습니다.`);
      }
    } catch (e) { fail(e); }
  }

  async function detach(name, cascade) {
    try {
      const r = await api('detach', { name, cascade });
      if (!r.ok) throw new Error(r.error);
      S.impact = null;
      stale();
      await load();
      if (r.warning) toast(r.warning, true); else toast(`${modLabel(name)} 모듈을 뺐습니다. ${r.impact.removed.length}개 항목이 빠졌습니다.`);
    } catch (e) { fail(e); }
  }

  // ---- ontology ------------------------------------------------------------------------------------------------

  function viewOnto() {
    const s = S.st.stats;
    const stats = [[s.objects, '객체'], [s.links, '관계'], [s.properties, '속성'], [s.decisions, '결정'], [s.actions, '액션'], [s.queries, '등록 질의']]
      .map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join('');
    return `
<div class="head"><div><h1>온톨로지</h1><div class="sub">업무 대상과 관계를 한 번 정의하고 원천 테이블에 바인딩합니다. 노드를 누르면 정의를 봅니다</div></div>
  <div class="right"><a class="btn ghost" href="/api/export/owl" download>OWL 내보내기</a></div></div>
<div class="stats">${stats}</div>
<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(360px,1fr)">
  <div class="card"><div class="ch">스키마 그래프<div class="right legend"><span><i class="fill"></i>객체</span><span><i class="ring"></i>상위 개념</span><span><i class="box"></i>모듈</span><span>- - 하위 유형</span></div></div>
    <div class="cb" style="padding:0"><div class="graph-wrap"><canvas id="graph"></canvas><div class="tip">끌어서 옮기기 · 휠로 확대</div></div></div></div>
  <div class="card"><div class="cb scroll" id="objdetail" style="max-height:640px">${S.obj ? objDetail(S.obj) : '<div class="empty">노드를 누르면 정의가 여기에 보입니다.</div>'}</div></div>
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
        ${p.inherited ? '<span class="chip sm" style="margin-top:4px">상위 개념에서</span>' : (p.module && p.module !== o.module ? `<span class="chip sm b" style="margin-top:4px">${esc(p.module_label)}</span>` : '')}</td>
      <td><span class="chip${p.key ? ' b' : ''}">${esc(p.type)}${p.unit ? ' · ' + esc(p.unit) : ''}</span>
        ${p.values.length ? `<div class="muted" style="font-size:11.5px;margin-top:3px">${esc(p.values.join(' · '))}</div>` : ''}</td>
      <td class="mono">${p.column ? esc(p.column) : '<span class="muted">-</span>'}</td></tr>`).join('');
    const links = o.links.map((l) => `<button class="chip" data-act="select" data-obj="${esc(l.other)}">${l.out ? '' : '← '}${esc(l.label)} · ${esc(l.other_label)}${l.out ? ' →' : ''}</button>`).join('');
    const states = o.states ? `<div class="sec">상태 전이 · ${esc(o.states.property)}</div><div class="chips">${o.states.states.map((x) => `<span class="chip${x === o.states.initial ? ' n' : ''}">${esc(x)}</span>`).join('')}</div>` : '';
    const parent = o.parent ? `<div class="sec">상위 개념</div><button class="chip n" data-act="select" data-obj="${esc(o.parent)}">${esc(o.parent_label)} · ${esc(o.parent)}</button>` : '';
    const children = o.children.length ? `<div class="sec">하위 유형</div><div class="chips">${o.children.map((c) => `<button class="chip" data-act="select" data-obj="${esc(c.name)}">${esc(c.label)}</button>`).join('')}</div>` : '';
    const aligned = o.aligned.length ? `<div class="sec">표준 개념 정렬</div><div class="chips">${o.aligned.map((a) => `<span class="chip sm mono">${esc(a.split('//').pop())}</span>`).join('')}</div>` : '';
    const mod = o.module ? `<span class="chip">정의 ${esc(o.module_label)}</span>` : '';
    const touched = o.touched.length ? `<span class="chip">확장 ${esc(o.touched.join(', '))}</span>` : '';
    return `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px"><b style="font-size:16px">${esc(o.label)}</b>
      <span class="muted mono">${esc(o.name)}</span><span style="flex:1"></span>
      ${o.abstract ? '<span class="chip n">상위 개념</span>' : `<span class="chip b">키 ${esc(o.key)}</span><span class="chip mono">${esc(o.table)}</span>`}</div>
      <div class="chips" style="margin-bottom:12px">${mod}${touched}</div>
      ${o.description ? `<div class="muted" style="font-size:12.5px;margin-bottom:10px">${esc(o.description)}</div>` : ''}
      <table class="tight"><tr><th>속성</th><th>타입</th><th>원천 컬럼</th></tr>${rows}</table>
      ${states}${parent}${children}${aligned}
      ${links ? `<div class="sec">관계</div><div class="chips">${links}</div>` : ''}`;
  }

  // ---- schema graph: positions settle once and stay; modules drawn as dashed groups --------------------------------

  const G = { canvas: null, view: null, nodes: [], edges: [], clusters: [], drag: null, ro: null };

  function hash(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; }

  function layout(data) {
    const ids = data.clusters.map((c) => c.id);
    const centers = {};
    ids.forEach((c, i) => { const a = (2 * Math.PI * i) / Math.max(ids.length, 1) - Math.PI / 2; centers[c] = { x: Math.cos(a) * 240, y: Math.sin(a) * 200 }; });
    const nodes = data.nodes.map((n) => ({ ...n, x: (S.pos[n.id] || {}).x, y: (S.pos[n.id] || {}).y, vx: 0, vy: 0 }));
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
      const pinned = new Set(nodes.filter((n) => S.pos[n.id]).map((n) => n.id));
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
    for (const n of nodes) S.pos[n.id] = { x: n.x, y: n.y };
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

  function mountGraph() {
    const canvas = $('#graph');
    if (!canvas) return;
    const laid = layout(S.st.graph);
    Object.assign(G, { canvas, nodes: laid.nodes, edges: laid.edges, clusters: laid.clusters, view: null });
    if (G.ro) G.ro.disconnect();
    G.ro = new ResizeObserver(() => { G.view = null; drawGraph(); });
    G.ro.observe(canvas);
    const at = (ev) => {
      const r = canvas.getBoundingClientRect();
      const sx = ev.clientX - r.left, sy = ev.clientY - r.top, v = G.view;
      return { sx, sy, x: (sx - v.tx) / v.k, y: (sy - v.ty) / v.k };
    };
    const hit = (p) => G.nodes.find((n) => Math.hypot(n.x - p.x, n.y - p.y) * G.view.k < 16);
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
      if (d.n) { d.n.x = p.x; d.n.y = p.y; S.pos[d.n.id] = { x: p.x, y: p.y }; } else { G.view.tx = d.tx + p.sx - d.sx; G.view.ty = d.ty + p.sy - d.sy; G.manual = true; }
      drawGraph(true);
    };
    canvas.onpointerup = () => {
      const d = G.drag;
      G.drag = null;
      canvas.classList.remove('drag');
      if (d && !d.moved && d.n) selectObject(d.n.id);
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
    // module groups
    for (const c of G.clusters) {
      const pts = [];
      for (const n of c.nodes) for (let i = 0; i < 12; i += 1) { const a = (i / 12) * Math.PI * 2; pts.push([n.x + Math.cos(a) * 38, n.y + Math.sin(a) * 34]); }
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
    const sel = S.sel;
    // edges
    for (const e of G.edges) {
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
    // nodes
    for (const n of G.nodes) {
      const on = n.id === sel;
      if (on) { ctx.beginPath(); ctx.arc(n.x, n.y, 17, 0, Math.PI * 2); ctx.fillStyle = 'rgba(26,115,232,0.16)'; ctx.fill(); }
      ctx.beginPath();
      ctx.arc(n.x, n.y, 10, 0, Math.PI * 2);
      if (n.abstract) { ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 2.6; ctx.strokeStyle = on ? '#1a73e8' : '#13213c'; ctx.stroke(); } else { ctx.fillStyle = on ? '#1a73e8' : '#13213c'; ctx.fill(); }
      ctx.font = font(12.5, 700);
      ctx.textAlign = 'center';
      ctx.lineWidth = 4 / Math.max(v.k, 0.7);
      ctx.strokeStyle = '#fff';
      ctx.strokeText(n.label, n.x, n.y + 27);
      ctx.fillStyle = on ? '#15509f' : '#1b2330';
      ctx.fillText(n.label, n.x, n.y + 27);
    }
  }

  // ---- queries -------------------------------------------------------------------------------------------------

  function roleFields(state) {
    const roles = S.st.roles;
    const role = roles.find((r) => r.name === state.role);
    const opts = ['<option value="">전체 권한 (역할 없이)</option>'].concat(roles.map((r) => `<option value="${esc(r.name)}"${r.name === state.role ? ' selected' : ''}>${esc(r.label)}</option>`));
    const keys = role ? role.principal.map((k) => `<div class="field"><label>${esc(k)}</label><input type="text" data-in="principal" data-k="${esc(k)}" value="${esc(state.principal[k] || '')}" placeholder="이 값으로 보이는 행을 제한합니다"></div>`).join('') : '';
    return `<div class="field"><label>실행 역할</label><select data-in="role">${opts.join('')}</select></div>${keys}`;
  }

  function viewQuery() {
    const st = S.st, q = S.q;
    const modes = [['list', '등록 질의'], ['text', '쿼리문 직접 쓰기']].concat(st.ask ? [['ask', '자연어 질문']] : []);
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
        <div class="hint" style="margin-bottom:12px">다른 언어로 쓴 쿼리문을 온톨로지 질의로 읽은 뒤, 모든 백엔드 언어로 다시 만들어 실행합니다.</div>`;
    } else {
      const ex = st.questions.filter((x) => x.query).slice(0, 4);
      left = `<div class="field"><label>질문</label><input type="text" data-in="question" value="${esc(q.question)}" placeholder="질문을 입력하세요"></div>
        <div class="chips" style="margin-bottom:12px">${ex.map((x) => `<button class="chip" data-act="example" data-text="${esc(x.text)}">${esc(x.text)}</button>`).join('')}</div>`;
    }
    const run = `<button class="btn primary" style="width:100%" data-act="run"${q.busy ? ' disabled' : ''}>${q.busy ? '<span class="spin"></span>실행 중' : '실행'}</button>`;
    return `
<div class="head"><div><h1>질의</h1><div class="sub">질문은 온톨로지 질의로 한 번 쓰고, 백엔드마다 맞는 쿼리문으로 바꿔 실행합니다</div></div>
  <div class="right">${q.res && q.res.ok ? (q.res.agree ? '<span class="chip ok">✓ 모든 백엔드 같은 결과</span>' : '<span class="chip warn">백엔드 결과 차이</span>') : ''}</div></div>
<div class="grid" style="grid-template-columns:320px minmax(0,1fr);align-items:start">
  <div class="card"><div class="ch">질문</div><div class="cb">${seg}${left}${roleFields(q)}${run}</div></div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${queryResult()}</div>
</div>`;
  }

  function queryResult() {
    const r = S.q.res;
    if (!r) return '<div class="card"><div class="cb"><div class="empty">왼쪽에서 질문을 고르고 실행하세요.</div></div></div>';
    if (!r.ok) return `<div class="banner no"><span class="ic x" style="width:26px;height:26px">!</span><div class="why">${esc(r.error)}</div></div>`;
    const cur = r.translations.find((t) => t.target === S.q.target && t.ok) || r.translations.find((t) => t.ok);
    const tabs = r.translations.map((t) => `<button class="tab${cur && t.target === cur.target ? ' on' : ''}${t.ok ? '' : ' off'}" ${t.ok ? `data-act="target" data-target="${esc(t.target)}"` : `title="${esc(t.error)}" disabled`}>${esc(t.label)}</button>`).join('');
    const results = r.results.map((b) => {
      if (!b.ok) return `<div class="card"><div class="ch">${esc(b.backend)}<span class="chip">${esc(b.language.toUpperCase())} · ${esc(b.dialect)}</span></div><div class="cb"><div class="muted mono" style="font-size:12px">${esc(b.error)}</div></div></div>`;
      const head = b.columns.map((c) => `<th>${esc(c)}</th>`).join('');
      const body = b.rows.slice(0, 50).map((row) => `<tr>${row.map((v) => `<td class="${typeof v === 'number' ? 'num' : ''}">${show(v)}</td>`).join('')}</tr>`).join('');
      return `<div class="card"><div class="ch">${esc(b.backend)}<span class="chip">${esc(b.language.toUpperCase())} · ${esc(b.dialect)}</span><div class="right"><span class="chip">${b.rows.length}행</span></div></div>
        <div class="cb scroll" style="padding:0;max-height:340px"><table>${b.rows.length ? `<tr>${head}</tr>${body}` : '<tr><td class="muted">결과가 없습니다.</td></tr>'}</table></div></div>`;
    }).join('');
    const params = Object.keys(r.params || {}).length ? Object.entries(r.params).map(([k, v]) => `${esc(k)} = ${show(v)}`).join(' · ') : '없음';
    return `
<div class="grid" style="grid-template-columns:minmax(0,0.8fr) minmax(0,1.2fr);flex:none">
  <div class="card"><div class="ch">온톨로지 질의 IR${r.attempts ? `<div class="right"><span class="chip b">질문을 ${r.attempts}번 만에 바꿨습니다</span></div>` : ''}</div><div class="cb"><pre class="code ir" style="max-height:340px;overflow:auto">${esc(r.ir)}</pre></div></div>
  <div class="card"><div class="ch">백엔드 쿼리문</div><div class="cb"><div class="tabs" style="margin-bottom:10px">${tabs}</div>
    <pre class="code" style="max-height:300px;overflow:auto">${cur ? cur.html : ''}</pre>
    <div class="muted" style="font-size:12px;margin-top:6px">파라미터 ${params} · 실행할 때는 값을 모두 파라미터로 넘깁니다</div></div></div>
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
    if (!st.decisions.length) return '<div class="head"><div><h1>판정 · 처리</h1></div></div><div class="empty">꽂힌 모듈에 결정표가 없습니다.</div>';
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
      ${qs ? `<div class="label" style="margin:12px 0 6px">검증 질문으로 고르기</div><div class="chips">${qs}</div>` : ''}</div></div>`;
    const r = d.res;
    let body = '';
    if (!r) body = '<div class="empty"><span class="spin"></span>판정하고 있습니다.</div>';
    else if (r.error) body = `<div class="banner no"><span class="ic x" style="width:26px;height:26px">!</span><div class="why">${esc(r.error)}</div></div>`;
    else body = decisionBody(r);
    return `
<div class="head"><div><h1>판정 · 처리</h1><div class="sub">결정표로 판정하고 근거가 된 원천 값을 함께 돌려줍니다. 처리는 사람이 승인한 뒤에만 원천에 씁니다</div></div>
  <div class="right">${r && !r.error ? `<a class="btn ghost" href="/api/export/jdm?decision=${encodeURIComponent(r.name)}" download>ZEN JDM 내려받기</a>` : ''}</div></div>
${controls}${body}`;
  }

  function decisionBody(r) {
    const matched = r.rules.filter((x) => x.hit);
    const cite = matched.map((x) => x.cite).filter(Boolean);
    const engines = [`<span class="chip">엔진 ${esc(r.engine === 'native' ? '기본' : r.engine)}</span>`];
    if (r.zen) engines.push(r.zen.error ? `<span class="chip warn" title="${esc(r.zen.error)}">GoRules ZEN 실행 안 됨</span>` : (r.zen.same ? '<span class="chip ok">GoRules ZEN 같은 판정</span>' : '<span class="chip warn">GoRules ZEN 판정 다름</span>'));
    const th = (n) => `<th>${esc(n).replace(/_/g, '_<wbr>')}</th>`;
    const head = '<th>규칙</th>' + r.inputs.map(th).join('') + r.outputs.map(th).join('');
    const rows = r.rules.map((x) => `<tr class="${x.hit ? 'hit' : ''}"><td class="mono" style="white-space:nowrap">${esc(x.id)}${x.cite ? `<div class="muted cite-note">${esc(x.cite)}</div>` : ''}</td>
      ${r.inputs.map((i) => `<td class="mono" style="white-space:nowrap">${esc(x.when[i] ?? '-')}</td>`).join('')}
      ${r.outputs.map((o) => `<td style="min-width:120px">${show(x.then[o])}</td>`).join('')}</tr>`).join('');
    const ev = r.evidence.map((e) => `<div class="ev"><div><b>${esc(e.input)}</b><div class="muted" style="font-size:12px">${e.object ? `${esc(e.object_label)} ${esc(e.key)}${e.property_label ? ' · ' + esc(e.property_label) : ''}` : esc(e.source)}</div></div>
      <div><span class="chip b">${show(e.value)}</span></div><div class="src mono muted" style="font-size:12px">${e.source && e.object ? '← ' + esc(e.source) : ''}</div></div>`).join('');
    const touched = r.touched.length ? `<div class="right muted" style="font-weight:600;font-size:12px">${esc(r.touched.join(', '))} 모듈이 규칙을 더했습니다</div>` : '';
    return `
<div class="banner ${r.yes ? 'ok' : 'no'}"><span class="ic ${r.yes ? 'y' : 'x'}" style="width:30px;height:30px;font-size:16px">${r.yes ? '✓' : '!'}</span>
  <div><div class="big">${esc(r.label)} · ${r.yes ? '가능' : '불가'}</div><div class="why">${esc(r.reason)}</div>${cite.length ? `<div class="cite">근거 규정 · ${esc(cite.join(', '))}</div>` : ''}</div>
  <div style="margin-left:auto" class="chips">${engines.join('')}${matched.length ? `<span class="chip b">규칙 ${esc(matched.map((x) => x.id).join(', '))}</span>` : ''}</div></div>
<div class="grid" style="grid-template-columns:minmax(0,1.45fr) minmax(360px,1fr);align-items:start">
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
    <div class="card"><div class="ch">결정표<span class="chip">적중 정책 ${esc(r.hit_policy)}</span>${touched}</div>
      <div class="cb scroll" style="padding:0"><table class="tight" style="font-size:12.5px"><tr>${head}</tr>${rows}</table></div></div>
    <div class="card"><div class="ch">근거 경로<div class="right muted" style="font-weight:600;font-size:12px">입력값마다 어느 객체의 어느 컬럼에서 왔는지</div></div><div class="cb">${ev || '<div class="empty">입력값이 모두 파라미터입니다.</div>'}</div></div>
  </div>
  <div style="display:flex;flex-direction:column;gap:16px;min-width:0">${actionCard(r)}${auditCard()}</div>
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
      const buttons = p.status === 'pending' ? `<div style="display:flex;gap:8px;margin-top:12px"><button class="btn primary" style="flex:1" data-act="approve" data-id="${esc(p.id)}">승인하고 실행</button><button class="btn" style="flex:1" data-act="reject" data-id="${esc(p.id)}">반려</button></div>` : '';
      const done = p.status === 'executed' ? '<div class="hint" style="margin-top:10px">원천 DB에 반영하고 그래프 저장소에도 변경분을 반영했습니다. 위 판정은 바뀐 상태로 다시 계산했습니다.</div>' : '';
      state = `<div class="sec" style="display:flex;align-items:center;gap:8px">요청 ${esc(p.id)} · ${esc(p.requested_by)}<span class="chip ${cls}" style="margin-left:auto">${label}</span></div>${checks}${diff ? `<div class="sec">바뀌는 값</div>${diff}` : ''}${buttons}${done}`;
    }
    return `<div class="card"><div class="ch">${esc(a.label)} <span class="muted mono" style="font-weight:600">${esc(a.name)}</span></div><div class="cb">
      <div class="muted" style="font-size:12.5px;margin-bottom:10px;line-height:1.55">에이전트가 요청하면 권한, 파라미터, 상태 전이, 판정을 검사합니다. 검사를 모두 통과한 경우에만 사람이 승인해 원천에 씁니다.</div>
      <div class="field"><label>요청하는 역할</label><select data-in="arole">${roles.map((x) => `<option value="${esc(x.name)}"${x.name === d.role ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></div>
      ${params}<button class="btn primary" style="width:100%" data-act="request" data-action="${esc(a.name)}">${esc(r.target_label)} ${esc(r.key)} ${esc(a.label)} 요청</button>
      ${state}</div></div>`;
  }

  function auditCard() {
    const a = S.d.audit;
    if (!a.length) return '';
    return `<div class="card"><div class="ch">감사 기록</div><div class="cb log">${a.slice(0, 10).map((x) => `<div><span class="muted">${esc(x.event)}</span><span>${esc(x.actor)} · ${esc(x.key)}</span><span class="muted mono">${esc(x.proposal)}</span></div>`).join('')}</div></div>`;
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
      toast(r.proposal.status === 'pending' ? '검사를 통과해 승인을 기다립니다.' : '검사를 통과하지 못해 요청을 반려했습니다.', r.proposal.status !== 'pending');
    } catch (e) { fail(e); }
  }

  async function approve(id, yes) {
    try {
      const r = await api('approve', { id, approve: yes });
      if (!r.ok) throw new Error(r.error);
      S.d.proposal = r.proposal;
      S.q.res = null; S.qa = null; S.bind = null; S.d.keys = {};
      await load();
      await startDecide();
      toast(yes ? '승인해 원천에 반영했습니다.' : '요청을 반려했습니다.');
    } catch (e) { fail(e); }
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
    const head = `<div class="head"><div><h1>검증</h1><div class="sub">답해야 할 질문과 정답을 정의에 함께 두고, 정답률과 백엔드 간 결과 일치를 바로 잽니다</div></div>
      <div class="right"><button class="btn primary" data-act="checks">다시 실행</button></div></div>`;
    if (!r || r.busy) return head + '<div class="empty"><span class="spin"></span>검증 질문을 실행하고 있습니다.</div>';
    if (r.error) return head + `<div class="banner no"><div class="why">${esc(r.error)}</div></div>`;
    const passed = r.results.filter((x) => x.passed).length;
    const c = r.conformance;
    const stats = `<div class="stats"><div class="stat"><b>${Math.round(r.accuracy * 100)}%</b><span>정답률</span></div>
      <div class="stat"><b>${passed} / ${r.results.length}</b><span>맞힌 검증 질문</span></div>
      ${c && c.summary ? `<div class="stat"><b>${c.summary.agree} / ${c.summary.queries}</b><span>백엔드 결과 일치 질의</span></div>` : ''}</div>`;
    const rows = r.results.map((x) => `<tr><td class="mono">${esc(x.id)}</td><td style="min-width:180px">${esc(x.text)}</td><td style="font-size:12px">${showObj(x.expected)}</td>
      <td style="font-size:12px">${x.error ? `<span class="muted">${esc(x.error)}</span>` : (typeof x.got === 'number' ? `${show(x.got)}행` : showObj(x.got))}</td><td><span class="ic ${x.passed ? 'y' : 'x'}">${x.passed ? '✓' : '!'}</span></td></tr>`).join('');
    const conf = c && c.queries ? c.queries.map((x) => `<tr><td><b>${esc(x.label)}</b><div class="muted mono">${esc(x.name)}</div></td>
      <td style="font-size:12px">${Object.entries(x.rows).map(([b, n]) => `${esc(b)} ${n === null ? '오류' : n + '행'}`).join(' · ')}</td>
      <td><span class="ic ${x.agree ? 'y' : 'x'}">${x.agree ? '✓' : '!'}</span></td></tr>`).join('') : '';
    return `${head}${stats}
<div class="grid" style="grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr);align-items:start">
  <div class="card"><div class="ch">검증 질문</div><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>번호</th><th>질문</th><th>정답</th><th>결과</th><th></th></tr>${rows}</table></div></div>
  <div class="card"><div class="ch">백엔드 결과 일치<div class="right muted" style="font-weight:600;font-size:12px">등록 질의를 모든 백엔드에서 실행해 비교합니다</div></div><div class="cb scroll" style="padding:0">${conf ? `<table class="tight"><tr><th>질의</th><th>행</th><th></th></tr>${conf}</table>` : '<div class="empty" style="padding:14px">백엔드가 하나라 비교하지 않습니다.</div>'}</div></div>
</div>`;
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
    const head = `<div class="head"><div><h1>DB 대조</h1><div class="sub">정의와 실제 데이터베이스를 맞대어 테이블, 컬럼, 타입, 키, 필수 값, 허용 값, 관계를 확인합니다</div></div>
      <div class="right"><button class="btn primary" data-act="bindings">다시 대조</button></div></div>`;
    if (!r || r.busy) return head + '<div class="empty"><span class="spin"></span>대조하고 있습니다.</div>';
    if (r.error || r.ok === undefined) return head + `<div class="banner no"><div class="why">${esc(r.error || '')}</div></div>`;
    const label = { tables: '테이블', columns: '컬럼', data_checks: '데이터 점검', links: '관계' };
    const stats = `<div class="stats">${Object.entries(r.checked).map(([k, n]) => `<div class="stat"><b>${n}</b><span>${esc(label[k] || k)}</span></div>`).join('')}
      <div class="stat"><b>${r.findings.length}</b><span>찾은 문제</span></div></div>`;
    const banner = r.ok && !r.findings.length ? '<div class="banner ok"><span class="ic y" style="width:26px;height:26px">✓</span><div><div class="big" style="font-size:16px">정의와 실제 DB가 맞습니다</div><div class="why">모듈을 꽂고 뺀 뒤 다시 대조하면 바인딩이 맞는지 바로 확인할 수 있습니다.</div></div></div>'
      : `<div class="banner ${r.ok ? 'ok' : 'no'}"><span class="ic ${r.ok ? 'y' : 'x'}" style="width:26px;height:26px">${r.ok ? '✓' : '!'}</span><div><div class="big" style="font-size:16px">${r.ok ? '주의할 점이 있습니다' : '정의와 실제 DB가 다릅니다'}</div><div class="why">아래 항목을 확인해 주세요.</div></div></div>`;
    const rows = r.findings.map((f) => `<tr><td><span class="chip ${f.severity === 'error' ? 'bad' : 'warn'}">${f.severity === 'error' ? '오류' : '주의'}</span></td>
      <td>${esc(FINDING[f.kind] || f.kind)}</td><td>${element(f.element)}</td><td class="mono muted" style="font-size:12px">${esc(f.detail)}</td></tr>`).join('');
    return `${head}${stats}${banner}${r.findings.length ? `<div class="card"><div class="cb scroll" style="padding:0"><table class="tight"><tr><th>심각도</th><th>종류</th><th>항목</th><th>내용</th></tr>${rows}</table></div></div>` : ''}`;
  }

  // ---- events --------------------------------------------------------------------------------------------------

  const ACT = {
    reset: async () => {
      if (!window.confirm('꽂고 뺀 모듈과 처리 기록을 처음 상태로 되돌립니다.')) return;
      try {
        await api('reset', {});
        Object.assign(S, { impact: null, pos: {}, sel: null });
        stale();
        S.q.name = null; S.q.text = ''; S.q.dirty = false; S.d.name = null; S.d.key = null;
        await load();
        toast('처음 상태로 되돌렸습니다.');
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
    checks: () => runChecks(),
    bindings: () => runBindings(),
  };

  const INPUT = {
    param: (t) => { S.q.params[t.dataset.k] = t.value; },
    principal: (t) => { S.q.principal[t.dataset.k] = t.value; },
    text: (t) => { S.q.text = t.value; S.q.dirty = true; },
    question: (t) => { S.q.question = t.value; },
    aparam: (t) => { S.d.params[t.dataset.k] = t.value; },
  };

  const CHANGE = {
    role: async (t) => { S.q.role = t.value; S.q.principal = {}; await principalDefaults(S.q); render(); },
    lang: (t) => { S.q.lang = t.value; if (!S.q.dirty || !S.q.text) { S.q.text = textFor(S.q.lang) || S.q.text; S.q.dirty = false; } render(); },
    decision: async (t) => { S.d.name = t.value; S.d.key = null; S.d.res = null; S.d.proposal = null; render(); await startDecide(); },
    key: async (t) => { S.d.key = t.value; S.d.proposal = null; await decide(); },
    arole: (t) => { S.d.role = t.value; },
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
      if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && ev.target.dataset && ev.target.dataset.in === 'text') { ev.preventDefault(); runQuery(); }
    });
    window.addEventListener('hashchange', () => { S.tab = location.hash.slice(1) || 'library'; render(); });
  }

  S.tab = (location.hash.slice(1) && NAV.some(([k]) => k === location.hash.slice(1))) ? location.hash.slice(1) : 'library';
  wire();
  load().catch(fail);
})();
