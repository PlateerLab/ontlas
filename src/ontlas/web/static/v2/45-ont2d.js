  // ---- 개념 초안 (ONT-05): Entity, Property and Relation candidates read from the material, reviewed before they are applied
  // The candidates are the draft the product already makes from the files of 자료 업로드 (structure and values, by rule).
  // What is settled here (kept, dropped, renamed) is the same state the step-by-step review (#data) applies at its end.

  const O2_CC = { object: 'Entity', property: 'Property', link: 'Relation' };
  const O2_CC_STEP = 8;

  async function o2LoadFiles() {
    const C = S.o2.cc;
    if (C.busy) return;
    C.busy = true;
    S.files = { busy: true };
    try { S.files = await api('files'); } catch (e) { S.files = { error: e.message }; }
    if (!S.dr.rules && S.files.rules) S.dr.rules = JSON.parse(JSON.stringify(S.files.rules));
    C.busy = false;
    if (S.tab === 'concepts') render();
  }

  // every candidate of the draft, whatever its kind: { el, kind, x (the draft's row), obj (the Entity it belongs to) }
  function o2Candidates(p) {
    const step = (id) => (p.steps.find((s) => s.id === id) || { items: [] }).items;
    return [...step('links').map((x) => ({ el: x.element, kind: 'link', x, obj: x.from })), ...step('objects').map((x) => ({ el: x.element, kind: 'object', x, obj: x.element.split(':')[1] })),
      ...step('properties').map((x) => ({ el: x.element, kind: 'property', x, obj: x.object }))];
  }
  const o2CcState = (c) => (S.dr.ed.drop[c.el] || (c.kind === 'property' && S.dr.ed.drop[`object:${c.obj}`]) ? 'off' : S.dr.ok[c.el] ? 'ok' : 'wait');
  // how a candidate was found: declared in the source, or read off its values
  const o2CcHow = (c) => ((c.kind === 'object' && c.x.why === 'primary_key') || (c.kind === 'link' && c.x.why === 'foreign_key') ? ['b', '결정론'] : c.kind === 'object' && c.x.why === 'row_number' ? ['warn', '키 없음'] : ['', '값으로 추론']);
  function o2CcName(c, o) {
    const e = S.dr.ed, label = e.labels[c.el] || c.x.label;
    if (c.kind === 'link') return `${o.labelOf(c.x.from)} ${c.el.split(':')[1]} ${o.labelOf(c.x.to)}`;
    if (c.kind === 'property') return `${o.labelOf(c.obj)}.${label}`;
    return `${label}@${c.obj}`;
  }

  function o2Concepts() {
    const C = S.o2.cc, f = S.files, st = S.st;
    const head = kHead('개념 초안', '자료 업로드에 올린 표와 정의서에서 만든 Entity, Property, Relation 초안을 검토합니다. 후보는 원천 테이블과 값을 근거로 달고 승인해야 정의에 반영됩니다. 정책서에서 만드는 규칙 후보는 규칙 초안에 있습니다.',
      `${known('ai') ? `<a class="k-btn" href="#ai">${ki('spark', 16, 1.75)}AI 초안 생성</a>` : ''}${known('ruleagent') ? `<a class="k-btn" href="#ruleagent">${ki('scale', 16, 1.75)}규칙 초안 보기</a>` : ''}`);
    if (!f || f.busy) return head + o2Wait();
    if (f.error) return head + kEmpty('불러오지 못했습니다', f.error);
    const p = f.pending, e = S.dr.ed, edit = canEdit();
    // the material the draft is made from
    const pill = (name, word, note, on) => `<label class="k-ck pill"><input type="checkbox" data-in="dtable" data-t="${esc(name)}"${on ? ' checked' : ''}${edit ? '' : ' disabled'}>${esc(word)}${note ? `<span class="k-s">${esc(note)}</span>` : ''}</label>`;
    const tables = f.files.flatMap((x) => x.tables.map((t) => pill(t.name, x.tables.length > 1 ? `${x.source} · ${t.sheet}` : x.source, `${show(t.rows)}행 · 컬럼 ${t.columns.length}`, S.dr.tables[t.name] !== false)));
    const defs = f.definitions.flatMap((x) => (x.tables.length ? x.tables.map((t) => pill(t.name, `${x.source} · ${t.label || t.name}`, '정의서', S.dr.tables[t.name] !== false))
      : [`<span class="k-chip dash">${esc(x.source)} <span class="k-s">문서 ${show(x.documents || 0)} · 용어 ${show(x.terms || 0)}</span></span>`]));
    const total = f.files.length + f.definitions.length;
    const lib = known('evidence') ? 'evidence' : 'catalog';
    const source = `<section class="k-card" aria-labelledby="o2xs"><div class="k-h g12" style="padding:16px 20px;border-bottom:1px solid var(--row)">
        <span style="width:32px;height:32px;border-radius:8px;background:var(--blue-wash);color:var(--blue);display:inline-flex;align-items:center;justify-content:center">${ki('doc', 18, 1.75)}</span>
        <div style="flex:1 1 320px;min-width:0"><h2 class="k-h2" id="o2xs">바탕 자료</h2><p class="k-s" style="margin:2px 0 0">자료 업로드에 올린 표와 정의서에서 Entity, Property, Relation 후보를 만듭니다. 정책서의 규칙 후보는 규칙 초안에서 만듭니다.</p></div>
        ${edit ? `<a class="k-btn" href="#catalog">${ki('plus', 16, 1.75)}자료 업로드</a><button class="k-btn" data-act="draft"${total && !S.dr.busy ? '' : ' disabled'}>${ki('play', 16, 1.75)}${S.dr.busy ? '초안을 만드는 중' : p ? '선택한 자료로 다시 생성' : '선택한 자료로 초안 생성'}</button>` : ''}</div>
      <div class="k-wrap g8" role="group" aria-label="추출할 자료" style="padding:12px 20px;border-bottom:1px solid var(--row)">${[...tables, ...defs].join('') || `<span class="k-s">초안에 넣을 자료가 없습니다. 자료 업로드에서 표나 정의서를 올립니다.</span>${edit && st.data.samples ? '<button class="k-lnk" data-act="dsample">샘플 데이터 불러오기</button>' : ''}`}
        <a class="k-lnk" href="#${lib}" style="min-height:36px">전체 자료 ${total} · ${lib === 'evidence' ? '근거 지도' : '자료 업로드'}에서 관리${ki('chevR', 14, 1.75)}</a></div>
      <div class="k-14" style="padding:12px 20px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px"><span class="k-s">${p ? `마지막 생성 · ${esc(p.label || st.repository.label)} · 자료 ${(p.steps.find((s) => s.id === 'read') || { items: [] }).items.length}건` : '아직 생성하지 않았습니다'}</span>
        ${p ? `<a href="#data" data-act="o2ccstep" data-k="rules" style="display:inline-flex;align-items:center;gap:6px">${ki('scale', 15, 1.75)}상태 · 역할 · 검증 질문 후보 ${(p.steps.find((s) => s.id === 'rules') || { items: [] }).items.length}</a><a href="#concepts" data-act="o2jump" data-to="o2cl" style="display:inline-flex;align-items:center;gap:6px">${ki('nodes', 15, 1.75)}개념 · 관계 후보 ${o2Candidates(p).length}</a>` : ''}
        <span class="k-push k-h g6"><span class="k-chip b">구조 · 코드 결정론</span>${(S.map.picked || []).length ? '<span class="k-chip">표준과 비교</span>' : ''}</span></div></section>`;
    const request = f.request ? `<div class="k-bar"><span class="k-chip warn">검토 요청</span><span class="k-14">적용을 기다리는 초안이 있습니다 · ${esc(f.request.by || '')}</span><span class="k-push"><a class="k-btn" href="#data">단계별 검토에서 열기</a></span></div>` : '';
    if (!p) {
      return `${head}${source}${request}${kEmpty('검토할 개념 초안이 없습니다', '바탕 자료를 고르고 초안을 생성하면 Entity, Property, Relation 후보가 근거와 함께 여기에 쌓입니다. 후보를 승인해야 정의에 반영됩니다.', edit ? `<a class="k-btn pri" href="#catalog">${ki('upload', 17, 1.75)}자료 업로드</a>` : '')}${o2CcSettings(f)}
        ${kNext([['ai', 'AI 초안 생성'], ['objects', '승인한 Entity'], ['ruleagent', '규칙 초안'], ['changes', '변경 요청으로 묶기'], [lib, '자료 관리']])}`;
    }
    const o = draftContext(p), all = o2Candidates(p);
    const of = (k) => all.filter((c) => c.kind === k), wait = (xs) => xs.filter((c) => o2CcState(c) === 'wait').length;
    const linked = of('object').filter((c) => objProposal(p, c.x).choice === 'standard').length;
    const issues = [...(p.issues || []), ...((S.dr.rev && S.dr.rev.issues) || [])];
    const other = (id) => (p.steps.find((s) => s.id === id) || { items: [] }).items.length;
    const stats = `<section class="k-wrap" aria-label="개념 초안 현황">
      <div class="k-stat"><p class="k-s" style="margin:0">Entity · Property 후보</p><p class="k-big">${of('object').length + of('property').length}</p><p class="k-s" style="margin:4px 0 0">대기 ${wait([...of('object'), ...of('property')])} · 기존 정의에 연결 ${linked}</p></div>
      <div class="k-stat"><p class="k-s" style="margin:0">Relation 후보</p><p class="k-big">${of('link').length}</p><p class="k-s" style="margin:4px 0 0">대기 ${wait(of('link'))}</p></div>
      <div class="k-stat"><p class="k-s" style="margin:0">쿼리 · 상태 · 검증 질문 후보</p><p class="k-big">${other('queries') + other('rules')}</p><p class="k-s" style="margin:4px 0 0">단계별 검토에서 확인</p></div>
      <div class="k-stat${issues.length ? ' warn' : ''}"><p class="k-s" style="margin:0">기존 정의와 충돌</p><p class="k-big${issues.length ? ' warn' : ''}">${issues.length}</p><p class="${issues.length ? 'k-warn k-13' : 'k-s'}" style="margin:4px 0 0">${issues.length ? esc(String(issues[0]).slice(0, 60)) : '정의 검사 통과'}</p></div></section>`;
    if (C.kind !== 'all' && !O2_CC[C.kind]) C.kind = 'all';
    const pool = C.kind === 'all' ? all : of(C.kind);
    if (!C.sel || !all.some((c) => c.el === C.sel)) C.sel = (pool[0] || {}).el || '';
    const sel = all.find((c) => c.el === C.sel);
    const STATE = { off: ['', '거절'], ok: ['ok', '승인'], wait: ['warn', '대기'] };
    const shown = pool.slice(0, C.n || O2_CC_STEP);
    if (sel && !shown.includes(sel) && pool.includes(sel)) shown.push(sel);
    const row = (c) => { const [ht, hw] = o2CcHow(c), [stt, stw] = STATE[o2CcState(c)], on = c.el === C.sel;
      return `<button class="k-row tight o2-cand${on ? ' on' : ''}" data-act="o2ccsel" data-el="${esc(c.el)}"${on ? ' aria-current="true"' : ''}><span class="k-h g6"><span class="k-chip${c.kind === 'link' ? ' b' : ''}">${O2_CC[c.kind]}</span><span class="k-chip${ht ? ` ${ht}` : ''}">${hw}</span><span class="k-chip${stt ? ` ${stt}` : ''}">${stw}</span></span>
        <b class="k-b k-14"${c.kind === 'link' ? ' style="font-family:var(--mono)"' : ''}>${esc(o2CcName(c, o))}</b><span class="k-s">${esc(c.kind === 'link' ? `${c.x.column || c.x.via || ''} · ${o.labelOf(c.x.from)}` : c.kind === 'property' ? `${(p.steps[1].items.find((y) => y.element === `object:${c.obj}`) || {}).table || c.obj} · ${c.x.column}` : `${c.x.table} · ${show(c.x.rows)}행`)}</span></button>`; };
    const list = `<nav class="k-card" id="o2cl" aria-label="개념 후보 목록" style="flex:1 1 320px"><div style="padding:12px"><div class="k-seg fill" role="group" aria-label="종류">${[['all', `전체 ${all.length}`], ['object', 'Entity'], ['property', 'Property'], ['link', 'Relation']].map(([k, w]) => `<button class="${C.kind === k ? 'on' : ''}" data-act="o2cckind" data-k="${k}" aria-pressed="${C.kind === k}">${w}</button>`).join('')}</div></div>
      ${shown.map(row).join('') || '<p class="k-cf line">이 종류의 후보가 없습니다.</p>'}
      <p class="k-s" style="margin:0;padding:8px 16px;border-top:1px solid var(--row)">${shown.length} / ${pool.length}개 표시${pool.length > shown.length ? ' · <button class="k-lnk flat" data-act="o2ccmore">더 보기</button>' : ''}</p></nav>`;
    return `${head}${source}${request}${stats}<div class="k-cols">${list}${sel ? o2CcDetail(p, o, sel, all) : ''}</div>
      <section class="k-card"><div class="k-ch"><h2>단계별 검토 · 적용</h2><span class="k-s">${REVIEW.slice(1).map(([id, w]) => { const s = p.steps.find((y) => y.id === id); return s ? `${w} ${s.items.length}` : w; }).join(' · ')}</span>
        <span class="k-push"><a class="k-btn pri" href="#data">단계별 검토에서 적용${ki('arrow', 16, 1.75)}</a></span></div>
        <p class="k-cf line">여기서 승인하거나 거절한 후보는 단계별 검토에 그대로 이어집니다. 키, 타입, 허용값, 쿼리, 상태 전이를 단계마다 확인한 뒤 [검토 · 적용]에서 한 번에 반영합니다${selfApply() ? '' : ' · 팀에서는 승인 권한이 있는 사람이 적용합니다'}</p></section>
      ${o2CcSettings(f)}
      ${kNext([['ai', 'AI 초안 생성'], ['objects', '승인한 Entity'], ['ruleagent', '규칙 초안'], ['changes', '변경 요청으로 묶기'], [lib, '자료 관리']])}`;
  }

  function o2CcDetail(p, o, c, all) {
    const e = S.dr.ed, edit = canEdit(), state = o2CcState(c), [ht, hw] = o2CcHow(c);
    const objRow = p.steps[1].items.find((y) => y.element === `object:${c.obj}`) || {};
    const pr = c.kind === 'object' ? objProposal(p, c.x) : null;
    const std = pr && pr.sm ? `<span class="k-chip ${pr.choice === 'standard' ? 'ok' : ''}">${pr.choice === 'standard' ? '표준에 연결' : '표준 후보'} · ${esc(pr.sm.label || pr.sm.object)} ${Math.round((pr.sm.score || 0) * 100)}%</span>` : '';
    const title = c.kind === 'link' ? `${esc(o.labelOf(c.x.from))} —${esc(c.el.split(':')[1])}→ ${esc(o.labelOf(c.x.to))}` : esc(o2CcName(c, o));
    const dis = edit && state !== 'off' ? '' : ' disabled';
    const label = `<label class="k-f">이름<input class="k-in" type="text" data-in="o2cclab" data-el="${esc(c.el)}" value="${esc(e.labels[c.el] ?? c.x.label)}"${dis}></label>`;
    const ref = c.el.replace(/^property:/, '');
    const fields = c.kind === 'link'
      ? `<label class="k-f">시작<input class="k-in" type="text" value="${esc(o.labelOf(c.x.from))}@${esc(c.x.from)}" readonly></label>
         <label class="k-f">관계 유형<select class="k-in" data-in="o2cccard" data-link="${esc(c.el.split(':')[1])}"${c.x.via ? ' disabled' : dis}>${Object.entries(CARD).map(([k, w]) => `<option value="${k}"${(e.card[c.el.split(':')[1]] || c.x.cardinality) === k ? ' selected' : ''}>${esc(c.el.split(':')[1])} · ${w}</option>`).join('')}</select></label>
         <label class="k-f">끝<input class="k-in" type="text" value="${esc(o.labelOf(c.x.to))}@${esc(c.x.to)}" readonly></label>`
      : c.kind === 'property'
        ? `${label}<label class="k-f">타입<select class="k-in" data-in="o2cctype" data-ref="${esc(ref)}"${dis}>${TYPES.map((t) => `<option value="${t}"${(e.types[ref] || c.x.type) === t ? ' selected' : ''}>${esc(TYPE_WORD[t] || t)} · ${t}</option>`).join('')}</select></label>
           <label class="k-f">원천 컬럼<input class="k-in mono" type="text" value="${esc(`${objRow.table || c.obj}.${c.x.column}`)}" readonly></label>`
        : `${label}<label class="k-f">키<select class="k-in" data-in="o2cckey" data-obj="${esc(c.obj)}"${dis}>${o.propsOf(c.obj).map((k) => `<option value="${esc(k)}"${o.keyOf(c.obj) === k ? ' selected' : ''}>${esc(k)}</option>`).join('')}</select></label>
           <label class="k-f">원천 테이블<input class="k-in mono" type="text" value="${esc(c.x.table)}" readonly></label>`;
    const basis = c.kind === 'link' ? `${esc(objRow.table || c.x.from)}의 ${why(o, 'link', c.x)}` : c.kind === 'object' ? `${esc(c.x.table)} · 키 <span class="k-code">${esc(o.keyOf(c.obj) || '-')}</span> · ${why(o, 'object', c.x)}` : `${esc(objRow.table || c.obj)}.${esc(c.x.column)} · ${why(o, 'property', c.x)}${c.x.type === 'enum' && c.x.values.length ? ` · ${c.x.values.slice(0, 8).map(esc).join(', ')}${c.x.values.length > 8 ? ' …' : ''}` : ''}`;
    const sib = all.filter((y) => y !== c && y.obj === c.obj).slice(0, 14);
    const ST = { off: '거절', ok: '승인', wait: '대기' };
    const goStep = { object: 'objects', property: 'properties', link: 'links' }[c.kind];
    return `<section class="k-card" aria-labelledby="o2cd" style="flex:2 1 520px"><div class="k-v" style="padding:20px;border-bottom:1px solid var(--row)"><p class="k-s" style="margin:0">개념 초안 · ${O2_CC[c.kind]} · ${esc(o.labelOf(c.obj))}</p>
        <h2 id="o2cd" style="margin:0;font-size:20px;font-weight:600;overflow-wrap:anywhere">${title}</h2><div class="k-h g6"><span class="k-chip${ht ? ` ${ht}` : ''}">${hw}</span><span class="k-chip ${state === 'ok' ? 'ok' : state === 'wait' ? 'warn' : ''}">${ST[state]}</span>${std}</div></div>
      <div class="o2-three">${fields}</div>
      <div class="k-v" style="padding:16px 20px;border-bottom:1px solid var(--row)"><p class="k-b" style="margin:0">근거 · ${esc(objRow.table || c.obj)}</p><p class="k-box k-14" style="margin:0;line-height:1.7;color:var(--ink2)">${basis}</p></div>
      ${sib.length ? `<div class="k-v" style="padding:16px 20px;border-bottom:1px solid var(--row)"><p class="k-b k-14" style="margin:0">같은 표에서 나온 후보</p><div class="k-h g6">${sib.map((y) => `<button class="k-chip${o2CcState(y) === 'wait' ? ' b' : ' w'}" data-act="o2ccsel" data-el="${esc(y.el)}">${esc(y.kind === 'link' ? y.el.split(':')[1] : (e.labels[y.el] || y.x.label))} · ${O2_CC[y.kind]}${o2CcState(y) === 'off' ? ' · 거절' : ''}</button>`).join('')}</div></div>` : ''}
      <div class="k-pha" style="padding:16px 20px"><span class="k-s" style="flex:1 1 220px">승인한 후보는 단계별 검토의 [검토 · 적용]에서 정의에 반영되고 변경 이력에 남습니다</span>
        <a class="k-lnk" href="#data" data-act="o2ccstep" data-k="${goStep}">단계별 검토에서 열기</a>
        ${edit ? `<button class="k-btn" data-act="o2ccdrop" data-el="${esc(c.el)}"${c.kind === 'property' && o.keyOf(c.obj) === ref.split('.').pop() ? ' disabled title="키 Property는 뺄 수 없습니다"' : ''}>${state === 'off' ? '거절 취소' : '거절'}</button><button class="k-btn pri" data-act="o2ccok" data-el="${esc(c.el)}"${state === 'ok' ? ' disabled' : ''}>${state === 'ok' ? '승인함' : '승인'}</button>` : ''}</div></section>`;
  }

  // what a draft is made by: the standards it is compared with, and what it turns into what
  function o2CcSettings(f) {
    const r = S.dr.rules || f.rules, m = S.map, edit = canEdit() ? '' : ' disabled';
    const std = !m.standards ? '<span class="k-s">불러오는 중입니다.</span>' : m.standards.length ? m.standards.map((x) => `<label class="k-ck mid"><input type="checkbox" data-in="mpick" data-v="${esc(x.name)}"${m.picked.includes(x.name) ? ' checked' : ''}${edit}>${esc(x.label)} <span class="k-s">${esc(x.kind_label)}</span></label>`).join('') : '<span class="k-s">비교할 표준 모듈이 없습니다.</span>';
    return `<section class="k-card pad k-v g12" aria-labelledby="o2ex"><div class="k-pha"><h2 class="k-h2" id="o2ex">생성 설정 · 표준과 비교</h2><span class="k-s">바꾼 뒤 초안을 다시 생성하면 적용됩니다</span>${canEdit() ? '<a class="k-lnk k-push" href="#data" data-act="o2ccsetup">세부 설정</a>' : ''}</div>
      <div class="k-wrap g16"><label class="k-f" style="flex:0 1 260px">추출 엔진<input class="k-in" type="text" value="기본 · 구조와 값으로 추출" readonly>${(f.rules_by || []).length ? `<span class="k-hint">구축 규칙 모듈 ${esc(f.rules_by.join(', '))}의 값이 기본값</span>` : ''}</label>
        <fieldset class="k-v" style="flex:1 1 240px;margin:0;padding:0;border:0"><legend class="k-s" style="padding:0;margin-bottom:8px;float:left;width:100%">비교할 표준</legend>${std}</fieldset>
        <fieldset class="k-v" style="flex:1 1 240px;margin:0;padding:0;border:0"><legend class="k-s" style="padding:0;margin-bottom:8px;float:left;width:100%">추출 방식</legend>${RULE_FLAG.map(([k, w]) => `<label class="k-ck mid"><input type="checkbox" data-in="drule" data-k="${k}"${r[k] ? ' checked' : ''}${edit}>${esc(w)}</label>`).join('')}</fieldset></div>
      <p class="k-s" style="margin:0">표준과 같은 개념은 표준에 연결하고 다른 점은 고객사 · 업종 모듈 확장으로 제안합니다. 반영은 승인 후</p></section>`;
  }

  screen('concepts', {
    area: 'work', word: '개념 초안', view: o2Concepts,
    after: () => {
      const f = S.files;
      if (!f) { o2LoadFiles(); return; }
      if (!S.map.standards) mapLoad().then(() => { if (S.tab === 'concepts') render(); });
      if (f.pending && S.map.standards) {  // the draft's tables against the standards picked, once for each set of tables
        const sig = ((f.pending.steps.find((x) => x.id === 'read') || {}).items || []).map((x) => x.table).join(',');
        if (S.map.auto !== sig) { S.map.auto = ''; S.map.sug = null; autoMatch(sig).then(() => { if (S.tab === 'concepts') render(); }); }
      }
    },
  });

  const o2CcEdited = () => { render(); clearTimeout(o2CcEdited.t); o2CcEdited.t = setTimeout(() => preview().then(() => { if (S.tab === 'concepts') render(); }), 200); };
  Object.assign(ACT, {
    o2cckind: (t) => { Object.assign(S.o2.cc, { kind: t.dataset.k, sel: '', n: 0 }); render(); },
    o2ccsel: (t) => { S.o2.cc.sel = t.dataset.el; const k = t.dataset.el.split(':')[0]; if (S.o2.cc.kind !== 'all' && S.o2.cc.kind !== k) S.o2.cc.kind = k; render(); },
    o2ccmore: () => { S.o2.cc.n = (S.o2.cc.n || O2_CC_STEP) + 16; render(); },
    o2ccdrop: (t) => { const el = t.dataset.el; S.dr.ed.drop[el] = !S.dr.ed.drop[el]; if (S.dr.ed.drop[el]) delete S.dr.ok[el]; o2CcEdited(); },
    o2ccok: (t) => { const el = t.dataset.el; S.dr.ed.drop[el] = false; S.dr.ok[el] = true; o2CcEdited(); },
    o2ccstep: (t) => { S.dr.view = t.dataset.k; S.dr.setup = false; location.hash = '#data'; },
    o2ccsetup: () => { S.dr.setup = true; S.dr.rulesOpen = true; location.hash = '#data'; },
  });
  Object.assign(INPUT, {
    o2cclab: (t) => { S.dr.ed.labels[t.dataset.el] = t.value; clearTimeout(o2CcEdited.t); o2CcEdited.t = setTimeout(() => preview(), 300); },
  });
  Object.assign(CHANGE, {
    o2cclab: () => { if (S.tab === 'concepts') render(); },
    o2cctype: (t) => { S.dr.ed.types[t.dataset.ref] = t.value; o2CcEdited(); },
    o2cckey: (t) => { S.dr.ed.keys[t.dataset.obj] = t.value; o2CcEdited(); },
    o2cccard: (t) => { S.dr.ed.card[t.dataset.link] = t.value; o2CcEdited(); },
  });
