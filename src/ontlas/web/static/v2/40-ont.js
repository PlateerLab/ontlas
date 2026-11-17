  // ==== 온톨로지 매니저 · 오브젝트 관리, 엔티티 관리, 그래프 탐색, and the screens of an Object, an Entity, a state
  //      machine and a Relation. Object is an area of the definition, Entity an object type, Relation a link. =========
  S.ont = { oq: '', otier: 'all', osel: '',  // 오브젝트 관리: what is searched, the tier shown, the Object picked
    esel: '', ewant: '', eq: '', eopen: {}, etab: 'def', einfo: {}, euses: null, eyaml: null, enotes: null, enote: '', edef: null, ssel: '',  // 엔티티 관리
    g: { focus: '', want: '', open: [], pos: {}, rel: '', show: { object: true, entity: true, member: true, rule: false }, all: false, rd: null },  // 그래프 탐색
    semBusy: false };
  const ONT_TABS = ['objmgr', 'objects', 'model'];
  const ontName = (x) => `${x.label || x.name}@${x.name}`;
  const ontClip = (text, n) => { const s = String(text || ''); return s.length > n ? `${s.slice(0, n - 1)}…` : s; };
  const ontVer = (x) => { const lib = (S.st.library || []).find((r) => r.name === x.module); return lib ? `v${lib.version}` : ''; };
  const ontKv = (k, v) => `<div class="ont-kv"><span class="k-mut">${esc(k)}</span><span>${v}</span></div>`;
  const ontDk = (word) => `<span class="k-chip dk">${esc(word)}</span>`;
  const ONT_KIND = { 결정: '규칙', 질의: '질의', 액션: 'Action', 역할: '접근 정책', '계산 속성': '계산 Property' };

  // the rule cards read with the definition: which Entities a rule applies to is said on each card
  function ontSem() {
    if (S.sem.st || S.ont.semBusy) return;
    S.ont.semBusy = true;
    api('semantic').then((x) => { S.sem.st = x; }).catch((e) => { S.sem.st = { error: e.message, cards: [] }; })
      .finally(() => { S.ont.semBusy = false; if (ONT_TABS.includes(S.tab)) render(); });
  }
  function ontCards(names) {  // null while the cards are being read
    const st = S.sem.st;
    if (!st || !st.cards) return null;
    const set = new Set(names);
    return st.cards.filter((c) => (c.applies_to || []).some((r) => { const i = r.indexOf(':'), k = r.slice(0, i), rest = r.slice(i + 1); return (k === 'object' && set.has(rest)) || (k === 'property' && set.has(rest.split('.')[0])); }));
  }
  const ontLayers = (cards) => ['axiom', 'custom', 'standard'].map((l) => [l, cards.filter((c) => c.layer === l).length]).filter((x) => x[1]).map(([l, n]) => `${LAYER_WORD[l]} ${n}`).join(' · ');

  async function ontReady() {  // the definition as the unsent edits leave it, for a screen opened before the menu read it
    if (!S.mg.st || S.mg.st.error) S.mg.st = await api('manage');
  }
  async function ontEdit(op, args) {  // one edit into the request being written; what was read from the older definition is read again
    const r = await api('manage/edit', { op, args });
    S.mg.st = r;
    Object.assign(S.md, { yaml: null, trial: null, data: null });
    S.mg.review = null; S.sem.st = null;
    Object.assign(S.ont, { einfo: {}, eyaml: null, euses: null, edef: null });
    return r;
  }
  function ontWait(title, lead) {
    const m = S.mg.st;
    if (m && !m.error) return '';
    return kHead(title, lead) + (m ? kEmpty('온톨로지 정의를 불러오지 못했습니다', m.error, '<button class="k-btn" data-act="ontReload">다시 불러오기</button>') : '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>');
  }

  // ---- ONT-01 오브젝트 관리 ---------------------------------------------------------------------------------------
  function ontAreaShown() {
    const st = S.ont, q = st.oq.trim().toLowerCase();
    return (S.mg.st.areas || []).filter((a) => (st.otier === 'all' || String(a.tier) === st.otier) && (!q || `${a.label} ${a.name} ${a.description}`.toLowerCase().includes(q)));
  }
  function ontAreaLevel(a) {
    if (a.status === 'draft') return '<span class="k-chip">초안</span>';
    const ls = areaEntities(a).map((o) => o.level || 0);
    return `<span class="k-chip${ls.length && Math.min(...ls) >= 1 ? ' b' : ''}">${esc(levelWord(ls))}</span>`;
  }
  function ontAreaRows(shown) {
    const st = S.ont;
    return shown.map((a) => {
      const ents = areaEntities(a), cards = ontCards(ents.map((o) => o.name));
      return `<tr class="${a.name === st.osel ? 'on' : ''}" data-act="ontOpick" data-name="${esc(a.name)}"><td class="b nw">${esc(a.label || a.name)}<span class="k-mut" style="font-weight:400">@${esc(a.name)}</span>${a.new ? ' <span class="k-chip ok">새 Object</span>' : a.pending ? ' <span class="k-chip warn">변경 대기</span>' : ''}</td>
        <td><span class="ont-clamp" title="${esc(a.description || '')}">${esc(a.description || '-')}</span></td><td class="r">${ents.length}</td><td class="r">${cards ? cards.length : '-'}</td><td>${ontAreaLevel(a)}</td><td class="nw">${esc(a.owner || '-')}</td></tr>`;
    }).join('') || `<tr><td colspan="6" class="mut">${S.ont.oq ? '검색 결과가 없습니다.' : '등록된 Object가 없습니다.'}</td></tr>`;
  }
  function ontAreaSide(a) {
    if (!a) return '<aside class="k-card pad ont-side"><p class="k-p s">선택된 Object가 없습니다.</p></aside>';
    const m = S.mg.st, ents = areaEntities(a), names = new Set(ents.map((o) => o.name));
    const ls = ents.map((o) => o.level || 0), low = ls.length ? Math.min(...ls) : -1;
    const links = m.links.filter((l) => names.has(l.source) || names.has(l.target));
    const decs = m.decisions.filter((d) => names.has(d.target));
    const qs = m.questions.filter((x) => decs.some((d) => d.name === x.decision));
    const cards = ontCards([...names]);
    const linked = cards ? cards.filter((c) => c.status !== 'draft') : null, drafts = cards ? cards.filter((c) => c.status === 'draft') : null;
    const count = (list, hash) => (list === null ? '-' : `<a href="#${hash}">${list.length}${list.length && ontLayers(list) ? ` · ${esc(ontLayers(list))}` : ''}</a>`);
    const aligned = (a.aligned || []).length ? a.aligned.map((u) => `<span class="k-chip" title="${esc(u)}">${esc(u.replace(/^https?:\/\/schema\.org\//, 'schema.org · '))}</span>`).join('') : '<span class="k-chip">schema.org 클래스 없음 · 확장 어휘</span>';
    const lv = [0, 1, 2, 3].map((l) => `<span class="${l <= low ? 'done' : ''}" title="${esc(LV_WORD[l])} · Entity ${ls.filter((x) => x >= l).length} / ${ls.length}">${LV[l]}${l <= low ? ki('check', 14, 1.75) : ''}</span>`).join('');
    return `<aside class="k-card ont-side" aria-labelledby="ont-ob-h">
      <div class="k-v ont-sec"><p class="k-p s">Object${a.tier ? ` · ${esc(a.tier)}차` : ''}</p><h2 id="ont-ob-h" class="ont-h20">${esc(ontName(a))}</h2><p class="k-p">${esc(a.description || '정의 없음')}</p><div class="k-h g6">${aligned}</div></div>
      <div class="k-v ont-sec"><p class="k-p s k-b">성숙도</p><div class="ont-lvs">${lv}</div></div>
      <div class="k-v ont-sec"><div class="k-h sb"><p class="k-p s k-b">Entity ${ents.length}</p><a class="k-lnk flat" href="#objects?area=${encodeURIComponent(a.name)}" style="min-height:24px">전체 보기${ki('chevR', 14, 1.75)}</a></div>
        <div class="k-h g6">${ents.map((o) => `<a class="k-chip" href="#objects?entity=${encodeURIComponent(o.name)}">${esc(ontName(o))}</a>`).join('') || '<span class="k-s">없음</span>'}${canEdit() ? `<a class="k-chip b" href="${itemHref('entity', 'form')}?area=${encodeURIComponent(a.name)}">+ Entity</a>` : ''}</div></div>
      <div class="k-v k-14" style="padding:12px 20px">
        ${ontKv('Relation', `<a href="#model?focus=${encodeURIComponent(a.name)}">${links.length} · 그래프 보기</a>`)}
        ${ontKv('적용 규칙', count(linked, 'semrules'))}${ontKv('규칙 초안', count(drafts, 'ruleagent'))}
        ${ontKv('검증 질문', `<a href="#check">${qs.length}</a>`)}
        ${ontKv('근거', a.cite ? `<span class="k-m12"><span aria-hidden="true">§</span> ${esc(a.cite)}</span>` : '-')}
        ${ontKv('담당자 · 버전', `${esc(a.owner || '-')} · ${esc(ontVer(a) || a.module_label || '-')}`)}</div></aside>`;
  }
  function ontObjects() {
    const lead = 'Ontology의 최상위 분류인 Object를 관리합니다.';
    const wait = ontWait('Object', lead);
    if (wait) return wait;
    const m = S.mg.st, st = S.ont, areas = m.areas || [];
    const shown = ontAreaShown();
    if (!st.osel || !areas.some((a) => a.name === st.osel)) st.osel = (shown[0] || areas[0] || {}).name || '';
    const sel = areas.find((a) => a.name === st.osel);
    const tiers = [...new Set(areas.map((a) => a.tier).filter((x) => x !== undefined && x !== null && x !== ''))].sort((x, y) => x - y);
    const unfiled = m.objects.filter((o) => !o.area && !o.concept);
    const drafts = areas.filter((a) => a.status === 'draft');
    const from = [...new Set(drafts.map((a) => a.module_label).filter(Boolean))];
    const head = kHead('Object', lead,
      `${known('settings') && isOntoAdmin() ? '<a class="k-btn" href="#settings">명명 규칙</a>' : ''}${canEdit() ? `<a class="k-btn pri" href="${itemHref('object', 'form')}">${ki('plus', 16, 1.75)}Object</a>` : ''}`);
    const bar = sel ? itemBar('object', sel.name, ontName(sel), ontClip(sel.description, 70)) : '';
    const seg = tiers.length ? `<div class="k-seg" role="group" aria-label="차수">${[['all', `전체 ${areas.length}`], ...tiers.map((x) => [String(x), `${x}차 ${areas.filter((a) => String(a.tier) === String(x)).length}`])].map(([k, w]) => `<button class="${st.otier === k ? 'on' : ''}" data-act="ontOtier" data-k="${esc(k)}">${esc(w)}</button>`).join('')}</div>` : '';
    const find = `<div class="k-pha"><label class="k-search ont-find">${ki('search', 16, 1.75)}<span class="k-hide">Object 검색</span><input type="search" placeholder="Object 검색" data-in="ontOq" value="${esc(st.oq)}"></label>${seg}</div>`;
    const table = `<section class="k-card" aria-label="Object 목록" style="flex:3 1 600px"><div class="k-x"><table class="k-t end"><thead><tr><th scope="col">Object</th><th scope="col">정의</th><th scope="col" class="r">Entity</th><th scope="col" class="r">규칙</th><th scope="col">성숙도</th><th scope="col">담당자</th></tr></thead><tbody id="ontorows">${ontAreaRows(shown)}</tbody></table></div>
      <p class="k-cf" id="ontofoot" style="padding:8px 20px">${areas.length}개 · 정의 ${areas.length - drafts.length} · 초안 ${drafts.length}${drafts.length && from.length === 1 ? ` · 초안 출처 ${esc(from[0])}` : ''}</p>
      ${unfiled.length ? `<p class="k-cf line"><span>Object 미지정 Entity ${unfiled.length}</span> ${unfiled.slice(0, 8).map((o) => `<a class="k-chip" href="#objects?entity=${encodeURIComponent(o.name)}">${esc(ontName(o))}</a>`).join(' ')}</p>` : ''}</section>`;
    return `${head}${bar}${find}<div class="k-cols">${table}<div id="ontoside" style="flex:2 1 340px;min-width:0">${ontAreaSide(sel)}</div></div>
      ${kNext([['objects', 'Entity'], ['model', '그래프 탐색'], ['evidence', '근거 지도'], ...(isOntoAdmin() ? [['settings', '온톨로지 설정']] : [])])}`;
  }
  screen('objmgr', { area: 'work', word: 'Object', view: ontObjects, after: ontSem });

  Object.assign(ACT, {
    ontReload: () => { S.mg.st = null; loadManage(); render(); },
    ontOpick: (t) => { S.ont.osel = t.dataset.name; render(); },
    ontOtier: (t) => { S.ont.otier = t.dataset.k; render(); },
  });
  Object.assign(INPUT, {
    ontOq: (t) => {  // the rows that match, without drawing the screen again: the box keeps its place
      S.ont.oq = t.value;
      const box = $('#ontorows');
      if (box) box.innerHTML = ontAreaRows(ontAreaShown());
    },
  });

  // ---- ONT-02 엔티티 관리 ---------------------------------------------------------------------------------------
  const ontObj = (name) => (S.mg.st.objects || []).find((o) => o.name === name) || null;
  const ontLvTag = (o) => `<span class="ont-lv${(o.level || 0) >= 1 ? ' up' : ''}">${LV[o.level || 0]}</span>`;
  const ontAligned = (u) => u.replace(/^https?:\/\/schema\.org\//, 'schema.org · ');
  function ontEntGroups() {  // the Objects with their Entities, then the Entities filed under none; a search keeps what matches
    const m = S.mg.st, q = S.ont.eq.trim().toLowerCase();
    const hit = (o) => !q || `${o.label} ${o.name} ${o.description || ''}`.toLowerCase().includes(q);
    const groups = (m.areas || []).map((a) => ({ key: a.name, word: ontName(a), all: areaEntities(a) }));
    const loose = m.objects.filter((o) => !o.area);
    if (loose.length) groups.push({ key: '', word: AREA_NONE, all: loose });
    return groups.map((g) => ({ ...g, rows: g.all.filter(hit) })).filter((g) => !q || g.rows.length);
  }
  function ontEntTree() {
    const st = S.ont, m = S.mg.st, q = st.eq.trim(), sel = ontObj(st.esel);
    const groups = ontEntGroups();
    const body = groups.map((g) => {
      const open = q ? true : st.eopen[g.key] === undefined ? !!(sel && (sel.area || '') === g.key) : st.eopen[g.key];
      return `<button class="ont-grp" data-act="ontEfold" data-k="${esc(g.key)}" aria-expanded="${open}">${ki(open ? 'chevD' : 'chevR', 16, 1.75)}${g.key ? ontDk('Object') : ''}<span class="k-cut">${esc(g.word)}</span><span class="n">Entity ${g.all.length}</span></button>
        ${open ? `<div class="ont-ents" role="group" aria-label="${esc(g.word)}의 Entity">${g.rows.map((o) => `<button class="ont-ent${o.name === st.esel ? ' on' : ''}" data-act="ontEpick" data-name="${esc(o.name)}"${o.name === st.esel ? ' aria-current="true"' : ''}><span>${esc(ontName(o))}</span>${ontLvTag(o)}</button>`).join('') || '<span class="k-s" style="padding:8px">Entity가 없습니다.</span>'}</div>` : ''}`;
    }).join('') || '<p class="k-p s" style="margin:8px">검색 결과가 없습니다.</p>';
    return `${body}<p class="k-p s" style="margin:8px 8px 6px">Object ${(m.areas || []).length}개 · Entity ${m.objects.length}</p>`;
  }
  function ontEntInfo(name) {  // what the applied definition says of an Entity beyond the list: what it is aligned to, its source, the documents that mention it
    const st = S.ont;
    if (st.einfo[name]) return;
    if ((ontObj(name) || {}).new) { st.einfo[name] = { missing: true, documents: [], aligned: [] }; return; }  // not in the applied definition yet: nothing is said of it there
    st.einfo[name] = { busy: true };
    api(`object?name=${encodeURIComponent(name)}`).then((x) => { st.einfo[name] = x; }).catch(() => { st.einfo[name] = { missing: true, documents: [], aligned: [] }; })
      .finally(() => { if (S.tab === 'objects' && st.esel === name) render(); });
  }
  function ontEntTab(o) {
    const st = S.ont, id = `object:${o.name}`, info = st.einfo[o.name] || {};
    if (st.etab === 'docs') {
      if (info.busy) return '<p class="k-p s">불러오는 중입니다.</p>';
      const docs = info.documents || [];
      return docs.length ? `<div class="k-v g12">${docs.map((d) => `<div class="k-v g4"><span class="k-h g6"><span class="k-m12"><span aria-hidden="true">§</span> ${esc(d.document)}</span><span class="k-s">${esc(d.section || '')}</span><span class="k-chip">${d.count}회</span></span><p class="k-p s">${esc(ontClip(d.text, 220))}</p></div>`).join('')}${known('evidence') ? `<a class="k-lnk flat" href="#evidence">근거 지도${ki('chevR', 14, 1.75)}</a>` : ''}</div>`
        : '<p class="k-p s">이 Entity를 언급한 자료가 없습니다.</p>';
    }
    if (st.etab === 'uses') {
      const u = st.euses && st.euses.id === id ? st.euses.list : null;
      if (!u) return '<p class="k-p s">불러오는 중입니다.</p>';
      return u.length ? `<div class="k-h g6">${u.map((x) => `<span class="k-chip">${esc(x)}</span>`).join('')}</div>` : '<p class="k-p s">사용처가 없습니다.</p>';
    }
    if (st.etab === 'yaml') {
      const y = st.eyaml && st.eyaml.id === id ? st.eyaml : null;
      if (!y) return '<p class="k-p s">불러오는 중입니다.</p>';
      if (y.error) return `<p class="k-note warn">${esc(y.error)}</p>`;
      return `<textarea class="ont-yaml" data-in="ontEyaml" spellcheck="false" aria-label="${esc(o.label)} YAML"${canEdit() ? '' : ' readonly'}>${esc(y.text)}</textarea>
        ${canEdit() ? `<div class="k-h"><button class="k-btn pri" id="ontyamlsave" data-act="ontEyamlSave"${y.text === y.was ? ' disabled' : ''}>변경 요청에 추가</button><button class="k-btn" data-act="ontEyamlReset">되돌리기</button></div>` : ''}`;
    }
    if (st.etab === 'notes') {
      const c = st.enotes && st.enotes.id === id ? st.enotes.list : null;
      if (!c) return '<p class="k-p s">불러오는 중입니다.</p>';
      return `${c.map((x) => `<div class="ont-cmt"><span class="k-s"><b class="k-ink">${esc(x.by)}</b> · ${esc(String(x.at || '').replace('T', ' '))}</span><span class="k-14">${esc(x.text)}</span></div>`).join('') || '<p class="k-p s">댓글이 없습니다.</p>'}
        ${canEdit() ? `<label class="k-f"><span class="k-hide">댓글</span><textarea class="k-in" rows="2" placeholder="댓글 입력" data-in="ontEnote">${esc(st.enote)}</textarea></label><div class="k-h"><button class="k-btn" data-act="ontEnoteSave">댓글 등록</button></div>` : ''}`;
    }
    const area = mgArea(o.area);
    const meta = [info.cite ? `출처 · ${esc(info.cite)}` : '', `담당자 · ${esc(o.owner || (area && area.owner) || '-')}`,
      o.parent ? `상위 Entity ${esc(ontName(ontObj(o.parent) || { name: o.parent }))}` : '',
      (info.aligned || []).length ? info.aligned.map((u) => esc(ontAligned(u))).join(', ') : info.busy || info.missing ? '' : 'schema.org 클래스 없음 · 확장 어휘'].filter(Boolean);
    const cur = st.edef && st.edef.name === o.name ? st.edef.text : (o.description || '');
    return `<label class="k-f">정의<input class="k-in" type="text" data-in="ontEdef" value="${esc(cur)}"${canEdit() ? '' : ' readonly'} placeholder="정의 입력"></label>
      <div class="k-h" id="ontdefsave"${cur !== (o.description || '') ? '' : ' hidden'}><button class="k-btn sm" data-act="ontEdefSave">변경 요청에 추가</button></div>
      <div class="k-wrap g16 k-i3 k-13">${meta.map((x) => `<span>${x}</span>`).join('')}</div>`;
  }
  function ontPropSaid(p) {
    const vals = (p.values || []).map((v) => (p.labels || {})[v] || v);
    return [p.key ? '식별 키' : '', p.required && !p.key ? '필수' : '', vals.length ? `${vals.slice(0, 4).join(', ')}${vals.length > 4 ? ` 외 ${vals.length - 4}` : ''}` : '', p.unit ? `단위 ${p.unit}` : '', p.expr || '', p.mask ? '가림' : ''].filter(Boolean).join(' · ') || '-';
  }
  function ontEntDetail(o) {
    if (!o) return kEmpty('등록된 Entity가 없습니다', '', canEdit() ? `<a class="k-btn pri" href="${itemHref('entity', 'form')}">${ki('plus', 16, 1.75)}Entity</a>` : '');
    const st = S.ont, m = S.mg.st, area = mgArea(o.area), info = st.einfo[o.name] || {};
    const props = mgProps(o.name), notes = (m.comments || {})[`object:${o.name}`] || 0;
    const uses = st.euses && st.euses.id === `object:${o.name}` ? st.euses.list.length : '';
    const tabs = [['def', '정의', ''], ['docs', '근거', info.documents ? info.documents.length || '' : ''], ['uses', '사용처', uses], ['yaml', 'YAML', ''], ['notes', '댓글', notes || '']]
      .map(([k, w, n]) => `<button class="${st.etab === k ? 'on' : ''}" role="tab" aria-selected="${st.etab === k}" data-act="ontEtab" data-k="${k}">${w}${n ? ` ${n}` : ''}</button>`).join('');
    const ver = ontVer(o);
    const head = `<section class="k-card pad k-v" aria-labelledby="ont-en-h"><p class="k-h g6 k-s" style="margin:0">${area ? `${ontDk('Object')}<a class="k-ink k-b" href="#objmgr">${esc(ontName(area))}</a><span aria-hidden="true">›</span>` : ''}<span class="ont-etag">Entity</span><span>${esc(ontName(o))}</span></p>
      <div class="k-pha"><h2 id="ont-en-h" class="ont-h24">${esc(ontName(o))}</h2><span class="k-chip b">${LV[o.level || 0]} · ${esc(LV_WORD[o.level || 0].slice(3))}</span>${ver ? `<span class="k-chip">${esc(ver)}${o.status === 'draft' ? ' 초안' : o.status === 'deprecated' ? ' 폐기 예정' : ''}</span>` : ''}${o.new ? '<span class="k-chip ok">새 Entity</span>' : o.pending ? '<span class="k-chip warn">변경 대기</span>' : ''}</div>
      <div class="k-seg self" role="tablist" aria-label="Entity 상세">${tabs}</div>${ontEntTab(o)}</section>`;
    const bound = (p) => (p.expr ? '<span class="k-chip">계산</span>' : !noSource() && o.table && p.column ? `<span class="k-chip ok"><span class="k-code" style="font-size:12px">${esc(p.column)}</span></span>` : '<span class="k-chip">미연결</span>');
    const table = `<section class="k-card" aria-labelledby="ont-pr-h"><div class="k-ch"><h2 id="ont-pr-h">Property</h2><span class="k-chip">${props.length}</span></div>
      <div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">한글</th><th scope="col">타입</th><th scope="col">허용값 · 제약</th><th scope="col">소스 컬럼</th></tr></thead>
      <tbody>${props.map((p) => `<tr><td class="k-code">${esc(p.name)}</td><td>${esc(p.label || '-')}${p.new ? ' <span class="k-chip ok">새</span>' : p.pending ? ' <span class="k-chip warn">변경</span>' : ''}</td><td class="k-code">${esc(p.type)}${p.expr ? ' · 계산값' : ''}</td><td>${esc(ontPropSaid(p))}</td><td>${bound(p)}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">등록된 Property가 없습니다.</td></tr>'}</tbody></table></div>
      <p class="k-cf line"><a href="#props">Property 표</a></p></section>`;
    const cards = ontCards([o.name]);
    const rest = cards ? cards.filter((c) => ['limit', 'duty', 'ban'].includes(c.type) || c.check) : null;
    const shown = rest ? rest.slice(0, 3) : [];
    const restBox = `<section class="ont-rest" aria-labelledby="ont-rs-h"><div class="k-h sb"><h2 id="ont-rs-h">Restriction</h2><a class="k-lnk" href="#semrules">편집</a></div>
      ${rest === null ? '<p class="k-p s">불러오는 중입니다.</p>' : rest.length ? `${shown.map((c) => `<p class="k-14" style="margin:0;line-height:1.55">${esc(c.statement || c.result || c.id)}</p>`).join('')}<p class="k-warn k-13" style="margin:0">규칙 ${esc(shown.map((c) => c.id).join(', '))}${rest.length > 3 ? ` 외 ${rest.length - 3}` : ''}</p>`
        : `<p class="k-14" style="margin:0;line-height:1.55">적용된 Restriction이 없습니다.</p>${cards.length ? `<p class="k-s" style="margin:0">적용 규칙 ${cards.length}개</p>` : ''}`}</section>`;
    const prep = `<section class="ont-prep" aria-labelledby="ont-cp-h"><h2 id="ont-cp-h">연결 준비 정보</h2>
      ${ontKv('식별 키 후보', o.key ? `<span class="k-code">${esc(o.key)}</span>` : '-')}${ontKv('소스 후보', o.table ? `<span class="k-code">${esc(o.table)}</span>${o.rows !== null && o.rows !== undefined ? ` · ${show(o.rows)}행` : ''}` : '-')}${ontKv('계산 Property', o.computed ? `${o.computed}개` : '없음')}</section>`;
    return `${head}${table}<div class="k-wrap g16">${restBox}${prep}</div>`;
  }
  // a state machine as a line of states: the path from the first state, then the states off it
  function ontFlow(s) {
    const p = S.mg.st.properties.find((x) => x.object === s.object && x.name === s.property) || {};
    const word = (v) => (p.labels || {})[v] || v;
    const path = [s.initial || s.states[0]].filter(Boolean), seen = new Set(path);
    for (;;) { const last = path[path.length - 1], t = s.transitions.find((x) => x.from === last && !seen.has(x.to)); if (!t) break; path.push(t.to); seen.add(t.to); }
    const off = s.states.filter((x) => !seen.has(x));
    return { text: path.map(word).join(' → ') + (off.length ? ` · ${off.map(word).join(', ')}` : ''),
      html: `<span class="ont-flow">${path.map((x) => `<span class="k-chip">${esc(word(x))}</span>`).join('→')}${off.length ? `·${off.map((x) => `<span class="k-chip">${esc(word(x))}</span>`).join('')}` : ''}</span>`,
      prop: p.label || s.property };
  }
  function ontStates() {
    const m = S.mg.st, st = S.ont, list = m.states || [];
    if (!list.some((s) => s.object === st.ssel)) st.ssel = (list.find((s) => s.object === st.esel) || list[0] || {}).object || '';
    const sel = list.find((s) => s.object === st.ssel);
    const acts = (s) => [...new Set(s.transitions.map((t) => t.action).filter(Boolean))].map((a) => { const x = m.actions.find((y) => y.name === a); return `<a href="#actions">${esc(x ? x.label : a)}</a>`; }).join(', ') || '-';
    const bar = sel ? `<div class="k-bar" role="toolbar" aria-label="선택한 상태 전이"><span class="k-s">선택한 상태 전이</span><span class="k-code k-ink">${esc(sel.label)} · ${esc(ontFlow(sel).prop)}</span><span class="k-14">${esc(ontClip(ontFlow(sel).text, 80))}</span><span class="k-push">${itemActs('state', sel.object)}</span></div>` : '';
    return `${bar}<section class="k-card" aria-labelledby="ont-sm-h"><div class="k-ch"><h2 id="ont-sm-h">상태 전이</h2><span class="k-chip">${list.length}</span>${canEdit() ? `<a class="k-btn k-push" href="${itemHref('state', 'form')}">${ki('plus', 16, 1.75)}상태 전이</a>` : ''}</div>
      ${list.length ? `<div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">Entity · Property</th><th scope="col">상태 흐름</th><th scope="col">전이 Action</th></tr></thead><tbody>${list.map((s) => `<tr class="${s.object === st.ssel ? 'on' : ''}" data-act="ontSpick" data-name="${esc(s.object)}"><td class="b">${esc(s.label)} · ${esc(ontFlow(s).prop)}${s.pending ? ' <span class="k-chip warn">변경 대기</span>' : ''}</td><td>${ontFlow(s).html}</td><td>${acts(s)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="k-cf line">등록된 상태 전이가 없습니다.</p>'}</section>`;
  }
  function ontEntities() {
    const lead = 'Object 하위의 Entity와 Property, 상태 전이를 관리합니다.';
    const wait = ontWait('Entity', lead);
    if (wait) return wait;
    const m = S.mg.st, st = S.ont;
    const fromArea = mgArea(itemParam('area'));
    const want = itemParam('entity') || ((fromArea && areaEntities(fromArea)[0]) || {}).name || '';
    if (want && want !== st.ewant && ontObj(want)) { st.esel = want; st.ewant = want; st.etab = 'def'; }
    if (!st.esel || !ontObj(st.esel)) st.esel = (m.objects.find((o) => o.area) || m.objects[0] || {}).name || '';
    const o = ontObj(st.esel), area = o && mgArea(o.area);
    const head = kHead('Entity', lead, canEdit() ? `${o ? `<a class="k-btn" href="${itemHref('entity', 'form', o.name)}&add=prop">${ki('plus', 16, 1.75)}Property</a>` : ''}<a class="k-btn pri" href="${itemHref('entity', 'form')}${area ? `?area=${encodeURIComponent(area.name)}` : ''}">${ki('plus', 16, 1.75)}Entity</a>` : '');
    const bar = o ? `<div class="k-bar" role="toolbar" aria-label="선택한 Entity"><span class="k-s">선택한 Entity</span>${area ? `${ontDk('Object')}<span class="k-s">${esc(ontName(area))} ›</span>` : ''}<span class="k-code k-ink">${esc(ontName(o))}</span><span class="k-14">${esc(ontClip(o.description, 60))}</span><span class="k-push">${itemActs('entity', o.name)}</span></div>` : '';
    return `${head}${bar}<div class="k-cols"><nav class="ont-tree" aria-label="Object별 Entity"><label class="k-search">${ki('search', 16, 1.75)}<span class="k-hide">Entity 검색</span><input type="search" placeholder="Entity 검색" data-in="ontEq" value="${esc(st.eq)}"></label><div id="ontetree">${ontEntTree()}</div></nav>
      <div class="k-c3" id="ontedetail">${ontEntDetail(o)}</div></div>${ontStates()}
      ${kNext([['model', '그래프 탐색'], ['concepts', '개념 초안'], ['sources', 'Mapping'], ['changes', '변경 요청 · 버전']])}`;
  }
  function ontEntitiesAfter() {
    ontSem();
    const st = S.ont, o = S.mg.st && !S.mg.st.error ? ontObj(st.esel) : null;
    if (!o) return;
    const id = `object:${o.name}`, again = () => { if (S.tab === 'objects' && st.esel === o.name) render(); };
    ontEntInfo(o.name);
    if ((!st.euses || st.euses.id !== id) && st.eusesFor !== id) {
      st.eusesFor = id;
      api(`element/readers?id=${encodeURIComponent(id)}`).then((x) => { st.euses = { id, list: x.readers }; }).catch(() => { st.euses = { id, list: [] }; }).finally(() => { st.eusesFor = ''; again(); });
    }
    if (st.etab === 'yaml' && (!st.eyaml || st.eyaml.id !== id) && st.eyamlFor !== id) {
      st.eyamlFor = id;
      api(`element/yaml?id=${encodeURIComponent(id)}`).then((x) => { st.eyaml = { id, text: x.yaml, was: x.yaml }; }).catch((e) => { st.eyaml = { id, error: e.message }; }).finally(() => { st.eyamlFor = ''; again(); });
    }
    if (st.etab === 'notes' && (!st.enotes || st.enotes.id !== id) && st.enotesFor !== id) {
      st.enotesFor = id;
      api(`element/comments?id=${encodeURIComponent(id)}`).then((x) => { st.enotes = { id, list: x.comments }; }).catch(() => { st.enotes = { id, list: [] }; }).finally(() => { st.enotesFor = ''; again(); });
    }
  }
  screen('objects', { area: 'work', word: 'Entity', view: ontEntities, after: ontEntitiesAfter });

  Object.assign(ACT, {
    ontEfold: (t) => { const st = S.ont, k = t.dataset.k, sel = ontObj(st.esel); st.eopen[k] = !(st.eopen[k] === undefined ? !!(sel && (sel.area || '') === k) : st.eopen[k]); $('#ontetree').innerHTML = ontEntTree(); },
    ontEpick: (t) => { Object.assign(S.ont, { esel: t.dataset.name, etab: 'def', edef: null, enote: '' }); render(); },
    ontEtab: (t) => { S.ont.etab = t.dataset.k; render(); },
    ontSpick: (t) => { S.ont.ssel = t.dataset.name; render(); },
    ontEdefSave: async () => {
      const st = S.ont, o = ontObj(st.esel);
      if (!o || !st.edef) return;
      try { await ontEdit('update_object', { name: o.name, description: st.edef.text.trim() }); toast('작성 중인 변경 요청에 정의를 저장했습니다.'); } catch (e) { fail(e); }
      render();
    },
    ontEyamlSave: async () => {
      const st = S.ont, y = st.eyaml;
      if (!y || y.text === y.was) return;
      try { S.mg.st = await api('manage/yaml', { id: y.id, text: y.text }); Object.assign(st, { eyaml: null, einfo: {}, euses: null }); S.sem.st = null; toast('작성 중인 변경 요청에 정의를 저장했습니다.'); } catch (e) { fail(e); }
      render();
    },
    ontEyamlReset: () => { const y = S.ont.eyaml; if (y) y.text = y.was; render(); },
    ontEnoteSave: async () => {
      const st = S.ont, o = ontObj(st.esel);
      if (!o || !st.enote.trim()) { toast('댓글 내용을 입력해 주세요.', true); return; }
      try { const x = await api('element/comment', { id: `object:${o.name}`, text: st.enote }); st.enotes = { id: `object:${o.name}`, list: x.comments }; st.enote = ''; (S.mg.st.comments = S.mg.st.comments || {})[`object:${o.name}`] = x.comments.length; } catch (e) { fail(e); }
      render();
    },
  });
  Object.assign(INPUT, {
    ontEq: (t) => { S.ont.eq = t.value; const box = $('#ontetree'); if (box) box.innerHTML = ontEntTree(); },
    ontEdef: (t) => { const o = ontObj(S.ont.esel); S.ont.edef = { name: o.name, text: t.value }; const b = $('#ontdefsave'); if (b) b.hidden = t.value === (o.description || ''); },
    ontEyaml: (t) => { const y = S.ont.eyaml; if (!y) return; y.text = t.value; const b = $('#ontyamlsave'); if (b) b.disabled = y.text === y.was; },
    ontEnote: (t) => { S.ont.enote = t.value; },
  });

  // ---- ONT-03 그래프 탐색 --------------------------------------------------------------------------------------
  // The graph stands on one Object: its Entities, the Relations that touch them and the Entities at their other ends,
  // each with its own Object. A node pressed twice brings in its neighbours. Where a link asks for the diagram's
  // workspace (#model?ws=1, a link to an element, the Property and Relation tables) the older workspace is shown whole.
  const ontWs = () => S.tab === 'model' && (location.hash.slice(1).split('?')[0] !== 'model' || /[?&](ws|el|left|field)=/.test(location.hash) || !!S.md.wantNew);
  const ONT_R = { a: 38, e: 32 };

  function ontGraphWant() {  // what the address asks for, taken once: an Object to stand on, an Entity or a Relation to show
    const g = S.ont.g, m = S.mg.st;
    const want = `${itemParam('focus')}|${itemParam('entity')}|${itemParam('rel')}`;
    if (want !== '||' && want !== g.want) {
      g.want = want;
      const rel = m.links.find((l) => l.name === itemParam('rel'));
      const ent = ontObj(itemParam('entity')) || (rel && ontObj(rel.source)) || null;
      const area = mgArea(itemParam('focus')) || (ent && mgArea(ent.area)) || null;
      Object.assign(g, { focus: area ? area.name : '', open: ent && (!area || ent.area !== area.name) ? [ent.name] : [], pos: {}, lay: null });
      if (rel) g.rel = rel.name;
    }
    if (!mgArea(g.focus) && !g.open.some((n) => ontObj(n))) {
      const touched = new Set(m.links.flatMap((l) => [l.source, l.target]));
      const first = (m.areas || []).find((a) => areaEntities(a).some((o) => touched.has(o.name))) || (m.areas || []).find((a) => areaEntities(a).length);
      g.focus = first ? first.name : '';
      g.open = first ? [] : m.objects.slice(0, 1).map((o) => o.name);
    }
  }
  function ontGraphData() {
    const m = S.mg.st, g = S.ont.g, focus = mgArea(g.focus), show = g.show;
    const base = new Set([...(focus ? areaEntities(focus).map((o) => o.name) : []), ...g.open.filter((n) => ontObj(n))]);
    const rels = m.links.filter((l) => (base.has(l.source) || base.has(l.target)) && ontObj(l.source) && ontObj(l.target));
    const ents = new Set(base);
    rels.forEach((l) => { ents.add(l.source); ents.add(l.target); });
    const areaOf = (n) => { const a = (ontObj(n) || {}).area; return a && mgArea(a) ? a : ''; };
    const areas = new Set([...ents].map(areaOf).filter(Boolean));
    if (focus) areas.add(focus.name);
    const nodes = [], edges = [];
    const order = [...(focus ? [focus.name] : []), ...[...areas].filter((a) => !focus || a !== focus.name)];
    if (show.object) order.forEach((a) => nodes.push({ id: `a:${a}`, kind: 'a', name: a, label: mgArea(a).label || a, r: ONT_R.a }));
    if (show.entity) {
      [...ents].forEach((n) => nodes.push({ id: `e:${n}`, kind: 'e', name: n, label: ontObj(n).label || n, r: ONT_R.e }));
      if (show.object) [...ents].forEach((n) => { if (areaOf(n)) edges.push({ id: `m:${n}`, kind: 'mem', s: `a:${areaOf(n)}`, t: `e:${n}`, hide: !show.member }); });
      rels.forEach((l) => edges.push({ id: `r:${l.name}`, kind: 'rel', s: `e:${l.source}`, t: `e:${l.target}`, name: l.name, card: CARD[l.cardinality] || '' }));
    } else {  // Objects alone: the Relations between two Objects as one line with their number
      const sum = {};
      rels.forEach((l) => { const a = areaOf(l.source), b = areaOf(l.target); if (a && b && a !== b) { const k = `${a}|${b}`; sum[k] = (sum[k] || 0) + 1; } });
      Object.entries(sum).forEach(([k, n]) => { const [a, b] = k.split('|'); edges.push({ id: `s:${k}`, kind: 'sum', s: `a:${a}`, t: `a:${b}`, name: `Relation ${n}`, card: '' }); });
    }
    return { focus, base, rels, nodes, edges };
  }
  // where each node stands: pushed apart and pulled along its lines until it settles, once for a given set of nodes;
  // a node a person moved stays where it was put
  function ontGraphLayout(nodes, edges) {
    const g = S.ont.g, sig = `${nodes.map((n) => n.id).join(',')}|${edges.length}`;
    if (!g.lay || g.lay.sig !== sig) {
      const ids = nodes.map((n) => n.id), n = ids.length, P = {}, R = Object.fromEntries(nodes.map((v) => [v.id, v.r]));
      ids.forEach((id, i) => { const a = (i / Math.max(n, 1)) * Math.PI * 2, r = i ? 50 + 30 * Math.sqrt(n) : 0; P[id] = [r * Math.cos(a), r * Math.sin(a)]; });
      const K = 118, steps = 320;
      for (let it = 0; it < steps; it++) {
        const t = 32 * (1 - it / steps) + 0.6, D = Object.fromEntries(ids.map((id) => [id, [0, 0]]));
        for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
          const a = ids[i], b = ids[j];
          let dx = P[a][0] - P[b][0], dy = P[a][1] - P[b][1];
          const d = Math.max(Math.hypot(dx, dy), 1), f = (K * K) / d;
          dx /= d; dy /= d;
          D[a][0] += dx * f; D[a][1] += dy * f; D[b][0] -= dx * f; D[b][1] -= dy * f;
        }
        edges.forEach((e) => {
          if (!P[e.s] || !P[e.t]) return;
          let dx = P[e.s][0] - P[e.t][0], dy = P[e.s][1] - P[e.t][1];
          const d = Math.max(Math.hypot(dx, dy), 1), f = (d * d) / (e.kind === 'mem' ? K : K * 1.7);
          dx /= d; dy /= d;
          D[e.s][0] -= dx * f; D[e.s][1] -= dy * f; D[e.t][0] += dx * f; D[e.t][1] += dy * f;
        });
        ids.forEach((id) => { D[id][0] -= P[id][0] * 0.22; D[id][1] -= P[id][1] * 0.22; });  // toward the middle, so a chain does not run off
        ids.forEach((id) => { const d = Math.max(Math.hypot(D[id][0], D[id][1]), 1), s = Math.min(d, t) / d; P[id][0] += D[id][0] * s; P[id][1] += D[id][1] * s; });
      }
      ids.forEach((id) => { P[id][1] *= 0.8; });  // wider than tall, as the card that holds it
      const room = {};  // two Entities a Relation joins stand far enough apart for its name
      edges.forEach((e) => { if (e.kind !== 'mem') { const k = [e.s, e.t].sort().join('|'); room[k] = Math.max(room[k] || 0, e.name.length * 7.3 + 52); } });
      for (let it = 0; it < 60; it++) {  // no two circles closer than their names need
        for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
          const a = ids[i], b = ids[j], need = R[a] + R[b] + Math.max(44, room[[a, b].sort().join('|')] || 0);
          let dx = P[a][0] - P[b][0], dy = P[a][1] - P[b][1];
          const d = Math.max(Math.hypot(dx, dy), 0.01);
          if (d >= need) continue;
          dx /= d; dy /= d;
          const push = (need - d) / 2;
          P[a][0] += dx * push; P[a][1] += dy * push; P[b][0] -= dx * push; P[b][1] -= dy * push;
        }
      }
      g.lay = { sig, pos: Object.fromEntries(ids.map((id) => [id, { x: Math.round(P[id][0]), y: Math.round(P[id][1]) }])) };
    }
    const pos = Object.fromEntries(nodes.map((v) => [v.id, g.pos[v.id] || g.lay.pos[v.id]]));
    const xs = nodes.map((v) => pos[v.id]);
    const box = g.box || { x: Math.min(...xs.map((p) => p.x)) - 110, y: Math.min(...xs.map((p) => p.y)) - 64, x2: Math.max(...xs.map((p) => p.x)) + 110, y2: Math.max(...xs.map((p) => p.y)) + 70 };
    return { pos, box };
  }
  function ontLines(label, max) {  // a name inside a circle: broken at spaces, then by length, three lines at most
    const out = [];
    let cur = '';
    String(label).split(' ').forEach((w) => { if (!cur) cur = w; else if (`${cur} ${w}`.length <= max) cur += ` ${w}`; else { out.push(cur); cur = w; } });
    if (cur) out.push(cur);
    const lines = out.flatMap((l) => { const xs = []; for (let i = 0; i < l.length; i += max) xs.push(l.slice(i, i + max)); return xs; });
    return lines.length > 3 ? [...lines.slice(0, 2), `${lines[2].slice(0, max - 1)}…`] : lines;
  }
  function ontGraphSvg() {
    const g = S.ont.g, { nodes, edges } = ontGraphData();
    if (!nodes.length) return '<p class="k-p s" style="padding:24px 8px">표시할 Object · Entity가 없습니다.</p>';
    const { pos, box } = ontGraphLayout(nodes, edges);
    const at = (id) => [pos[id].x, pos[id].y], R = Object.fromEntries(nodes.map((v) => [v.id, v.r]));
    const sel = edges.find((e) => e.kind === 'rel' && e.name === g.rel);
    const hot = new Set(sel ? [sel.s, sel.t] : []);
    const cards = g.show.rule ? S.sem.st && S.sem.st.cards : null;
    const place = pairs(edges.filter((e) => e.kind !== 'mem'), (e) => [e.s, e.t]);
    const dirs = {};  // the ways lines leave each node, so its name is written on the side they leave freest
    edges.forEach((e) => { if (e.hide || !pos[e.s] || !pos[e.t]) return; const a = Math.atan2(pos[e.t].y - pos[e.s].y, pos[e.t].x - pos[e.s].x); (dirs[e.s] = dirs[e.s] || []).push(a); (dirs[e.t] = dirs[e.t] || []).push(a + Math.PI); });
    const side = (id) => {
      const gap = (c) => Math.min(Math.PI, ...(dirs[id] || []).map((a) => { const d = Math.abs(a - c) % (Math.PI * 2); return d > Math.PI ? Math.PI * 2 - d : d; }));
      return [['b', Math.PI / 2], ['t', -Math.PI / 2], ['r', 0], ['l', Math.PI]].map(([k, c]) => [k, gap(c)]).sort((x, y) => y[1] - x[1])[0][0];
    };
    const line = (e) => {
      if (!pos[e.s] || !pos[e.t] || e.hide) return '';
      const a = at(e.s), b = at(e.t), d = Math.max(Math.hypot(b[0] - a[0], b[1] - a[1]), 1), u = [(b[0] - a[0]) / d, (b[1] - a[1]) / d];
      const p = [a[0] + u[0] * R[e.s], a[1] + u[1] * R[e.s]], q = [b[0] - u[0] * (R[e.t] + (e.kind === 'mem' ? 0 : 4)), b[1] - u[1] * (R[e.t] + (e.kind === 'mem' ? 0 : 4))];
      if (e.kind === 'mem') return `<g class="ont-e mem"><line x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}"/></g>`;
      const on = sel === e, [k, n] = place(e), c = bend(p, q, k, n), w = e.name.length * 7.3 + 16;
      if (n > 1) {  // lines between the same two nodes carry their names at different places along them
        const t = (k + 1) / (n + 1), off = (k - (n - 1) / 2) * 26, len = Math.hypot(q[0] - p[0], q[1] - p[1]) || 1;
        const cx = (p[0] + q[0]) / 2 - ((q[1] - p[1]) / len) * off * 2, cy = (p[1] + q[1]) / 2 + ((q[0] - p[0]) / len) * off * 2;
        c.x = (1 - t) * (1 - t) * p[0] + 2 * (1 - t) * t * cx + t * t * q[0];
        c.y = (1 - t) * (1 - t) * p[1] + 2 * (1 - t) * t * cy + t * t * q[1];
      }
      return `<g class="ont-e rel${on ? ' on' : ''}"${e.kind === 'rel' ? ` data-rel="${esc(e.name)}"` : ''}><path d="${c.d}" marker-end="url(#${on ? 'ontarron' : 'ontarr'})"/>
        <rect class="lb" x="${c.x - w / 2}" y="${c.y - 11}" width="${w}" height="20" rx="6"/><text class="nm" x="${c.x}" y="${c.y + 3}" text-anchor="middle">${esc(e.name)}</text>
        ${e.card ? `<rect class="cdbg" x="${c.x - 16}" y="${c.y + 10}" width="32" height="15"/><text class="cd" x="${c.x}" y="${c.y + 22}" text-anchor="middle">${esc(e.card)}</text>` : ''}</g>`;
    };
    const node = (v) => {
      const [x, y] = at(v.id), lines = ontLines(v.label, v.kind === 'a' ? 4 : 4);
      const marks = cards && v.kind === 'e' ? cards.filter((c) => (['limit', 'duty', 'ban'].includes(c.type) || c.check) && (c.applies_to || []).some((r) => r === `object:${v.name}` || r.startsWith(`property:${v.name}.`))).length : 0;
      const top = v.kind === 'a' ? y + 6 - (lines.length - 1) * 8 : y + 4.5 - (lines.length - 1) * 7.5;
      const words = lines.map((l, i) => `<text class="w" x="${x}" y="${top + i * (v.kind === 'a' ? 17 : 15)}" text-anchor="middle"${lines.length > 2 ? ' style="font-size:12px"' : ''}>${esc(l)}</text>`).join('');
      return `<g class="ont-n ${v.kind === 'a' ? 'obj' : 'ent'}${hot.has(v.id) ? ' on' : ''}" data-n="${esc(v.id)}"><title>${v.kind === 'a' ? 'Object' : 'Entity'} · ${esc(v.label)}@${esc(v.name)}${marks ? ` · Restriction ${marks}` : ''}</title><circle cx="${x}" cy="${y}" r="${v.r}"/>
        ${v.kind === 'a' ? `<text class="k" x="${x}" y="${top - 16}" text-anchor="middle">Object</text>` : ''}${words}
        ${{ b: `<text class="mono" x="${x}" y="${y + v.r + 15}" text-anchor="middle">`, t: `<text class="mono" x="${x}" y="${y - v.r - 8}" text-anchor="middle">`, r: `<text class="mono" x="${x + v.r + 8}" y="${y + 4}" text-anchor="start">`, l: `<text class="mono" x="${x - v.r - 8}" y="${y + 4}" text-anchor="end">` }[side(v.id)]}${esc(v.name)}</text>${marks ? `<circle class="dot" cx="${x + v.r * 0.7}" cy="${y - v.r * 0.7}" r="6"/>` : ''}</g>`;
    };
    const W = Math.round(box.x2 - box.x), H = Math.round(box.y2 - box.y);
    return `<svg class="ont-svg" width="${W}" height="${H}" viewBox="${box.x} ${box.y} ${W} ${H}" role="img" aria-label="Relation 그래프">
      <defs><marker id="ontarr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#5C5C63"/></marker>
      <marker id="ontarron" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#2563EB"/></marker></defs>
      ${edges.filter((e) => e.kind === 'mem').map(line).join('')}${edges.filter((e) => e.kind !== 'mem' && e !== sel).map(line).join('')}${nodes.map(node).join('')}${sel ? line(sel) : ''}</svg>`;
  }
  function ontRelSide(l) {
    if (!l) return '<aside class="k-card pad" style="flex:1 1 320px"><p class="k-p s">선택된 Relation이 없습니다.</p></aside>';
    const g = S.ont.g, m = S.mg.st;
    if (!g.rd || g.rd.name !== l.name) g.rd = { name: l.name, source: l.source, target: l.target, cardinality: l.cardinality };
    const d = g.rd, dirty = d.source !== l.source || d.target !== l.target || d.cardinality !== l.cardinality;
    const ents = (cur) => m.objects.map((o) => { const a = mgArea(o.area); return opt(o.name, `${ontName(o)}${a ? ` · ${a.label || a.name} 소속` : ''}`, cur); }).join('');
    const ro = canEdit() ? '' : ' disabled';
    return `<aside class="k-card ont-side" aria-labelledby="ont-rel-h" style="flex:1 1 320px">
      <div class="ont-sec" style="display:flex;flex-direction:column;gap:6px"><p class="k-p s">Relation</p><h2 id="ont-rel-h" class="ont-h20" style="font-family:var(--mono)">${esc(l.name)}</h2><p class="k-14" style="margin:0">${esc(mgLabel(l.source))} → ${esc(mgLabel(l.target))}${l.label ? ` · ${esc(l.label)}` : ''}</p></div>
      <div class="k-v g12" style="padding:12px 20px">
        <label class="k-f">시작 Entity<select class="k-in" data-in="ontRd" data-k="source"${ro}>${ents(d.source)}</select></label>
        <label class="k-f">끝 Entity<select class="k-in" data-in="ontRd" data-k="target"${ro}>${ents(d.target)}</select></label>
        <label class="k-f">카디널리티<select class="k-in" data-in="ontRd" data-k="cardinality"${ro}>${Object.entries(CARD_WORD).map(([k, w]) => opt(k, w, d.cardinality)).join('')}</select></label>
        ${ontKv('상태', `<span class="k-chip${l.status === 'draft' ? '' : l.status === 'deprecated' ? ' bad' : ' ok'}">${esc((STATUS_WORD[l.status] || STATUS_WORD.active)[1])}</span>${l.new ? ' <span class="k-chip ok">새 Relation</span>' : l.pending ? ' <span class="k-chip warn">변경 대기</span>' : ''}`)}
        ${l.inverse ? ontKv('역방향 이름', `<span class="k-code">${esc(l.inverse)}</span>`) : ''}
        ${ontKv('버전 · 모듈', `${esc(ontVer(l) || '-')} · ${esc(l.module_label || '-')}`)}</div>
      ${canEdit() ? `<div style="margin-top:auto;padding:12px 20px;border-top:1px solid var(--row);display:flex;gap:8px;flex-wrap:wrap"><a class="k-btn" href="${itemHref('relation', 'delete', l.name)}">삭제</a><button class="k-btn pri" id="ontrdsave" data-act="ontRdSave"${dirty ? '' : ' disabled'}>변경 요청에 추가</button></div>` : ''}</aside>`;
  }
  function ontGraph() {
    const lead = 'Object와 Entity 사이의 Relation을 그래프로 보고 편집합니다.';
    const wait = ontWait('그래프 탐색', lead);
    if (wait) return wait;
    const m = S.mg.st, g = S.ont.g;
    ontGraphWant();
    const data = ontGraphData();
    if (!data.rels.some((l) => l.name === g.rel)) g.rel = (data.rels[0] || {}).name || '';
    const sel = m.links.find((l) => l.name === g.rel);
    const head = kHead('그래프 탐색', lead, `<a class="k-btn" href="#objects">Entity</a><button class="k-btn" data-act="ontGall">관계 유형 목록</button><a class="k-btn" href="#model?ws=1">다이어그램 작업 공간</a>${canEdit() ? `<a class="k-btn" href="${itemHref('relation', 'form')}">${ki('plus', 16, 1.75)}Relation</a>` : ''}`);
    const bar = sel ? itemBar('relation', sel.name, sel.name, `${mgLabel(sel.source)} → ${mgLabel(sel.target)}`) : '';
    const chip = (k, w) => `<button class="k-chip${g.show[k] ? ' b' : ''}" data-act="ontGshow" data-k="${k}" aria-pressed="${g.show[k]}">${w}</button>`;
    const legend = `<div class="ont-legend"><span><i style="width:16px;height:16px;border-radius:50%;background:#262626"></i>Object</span><span><i style="width:12px;height:12px;border-radius:50%;background:#fff;border:1.5px solid #5C5C63"></i>Entity</span>
      <span><i style="width:24px;height:0;border-top:1.5px solid #5C5C63"></i>Relation · 시작 → 끝</span><span><i style="width:24px;height:0;border-top:2px dotted #C4C4CA"></i>소속 · Object › Entity</span>
      <span><i style="width:12px;height:12px;border-radius:50%;background:#EEF3FD;border:1.5px solid #2563EB"></i>선택한 Relation</span>${g.show.rule ? '<span><i style="width:10px;height:10px;border-radius:50%;background:#B56A00"></i>Restriction 적용 Entity</span>' : ''}</div>`;
    const moved = g.open.length || Object.keys(g.pos).length;
    const graph = `<section class="k-card" aria-label="Relation 그래프" style="flex:1 1 640px;display:flex;flex-direction:column;min-width:0"><div class="ont-gbox">${legend}<div class="ont-canvas" id="ontcanvas"><div id="ontsvg">${ontGraphSvg()}</div></div></div>
      <p class="k-cf line" style="padding:8px 16px">간선 선택: 편집 · 노드 더블클릭: 이웃 펼치기 · 노드 드래그: 이동${moved ? ' · <button class="k-lnk flat" data-act="ontGreset" style="min-height:0">배치 초기화</button>' : ''}</p></section>`;
    const list = g.all ? m.links : data.rels;
    const rows = list.map((l) => `<tr class="${l.name === g.rel ? 'on' : ''}" data-act="ontGrel" data-name="${esc(l.name)}"><td class="k-code">${esc(l.name)}</td><td>${esc(mgLabel(l.source))} → ${esc(mgLabel(l.target))}</td><td class="nw">${esc(CARD_WORD[l.cardinality] || l.cardinality)}</td><td>${esc(l.label || '-')}${l.required ? ' · 필수' : ''}${l.new ? ' <span class="k-chip ok">새</span>' : l.pending ? ' <span class="k-chip warn">변경</span>' : ''}</td></tr>`).join('');
    const dict = `<section class="k-card" aria-labelledby="ont-dict-h" id="ontrels"><div class="k-ch"><h2 id="ont-dict-h">관계 유형</h2><span class="k-chip">${g.all ? m.links.length : `${data.rels.length} / ${m.links.length}`}</span>
      <div class="k-push"><div class="k-seg"><button class="${g.all ? '' : 'on'}" data-act="ontGlist" data-v="">이 그래프</button><button class="${g.all ? 'on' : ''}" data-act="ontGlist" data-v="1">전체 ${m.links.length}</button></div></div></div>
      ${list.length ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">관계 유형</th><th scope="col">시작 Entity → 끝 Entity</th><th scope="col">카디널리티</th><th scope="col">설명</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="k-cf line">등록된 Relation이 없습니다.</p>'}</section>`;
    return `${head}${bar}<div class="k-pha"><div class="k-h g6">${chip('object', 'Object')}${chip('entity', 'Entity')}${chip('member', '소속 표시')}${chip('rule', 'Restriction 표시')}</div></div>
      <div class="k-wrap g16" style="align-items:stretch">${graph}${ontRelSide(sel)}</div>${dict}${kNext([['query', '질의'], ['concepts', '개념 초안']])}`;
  }
  function ontGraphPaint() { const box = $('#ontsvg'); if (box) box.innerHTML = ontGraphSvg(); }
  function ontGraphMount() {  // pressing, dragging and pressing twice on the drawing; the drawing is replaced, the box that holds it stays
    const box = $('#ontcanvas'), g = S.ont.g;
    if (!box || box.dataset.on) return;
    box.dataset.on = '1';
    if (g.scroll) { box.scrollLeft = g.scroll[0]; box.scrollTop = g.scroll[1]; } else {  // a drawing larger than its card opens on the Object it stands on
      const d = ontGraphData(), svg = box.querySelector('svg'), mid = d.nodes[0];
      if (svg && mid) {
        const { pos, box: frame } = ontGraphLayout(d.nodes, d.edges), sr = svg.getBoundingClientRect(), br = box.getBoundingClientRect();
        box.scrollLeft = sr.left - br.left + box.scrollLeft + pos[mid.id].x - frame.x - box.clientWidth / 2;
        box.scrollTop = sr.top - br.top + box.scrollTop + pos[mid.id].y - frame.y - box.clientHeight / 2;
      }
    }
    let drag = null, last = { id: '', at: 0 };
    box.addEventListener('scroll', () => { g.scroll = [box.scrollLeft, box.scrollTop]; });
    box.addEventListener('pointerdown', (ev) => {
      const n = ev.target.closest('[data-n]');
      if (!n) return;
      const { pos, box: frame } = ontGraphLayout(ontGraphData().nodes, ontGraphData().edges);
      g.box = frame;  // the frame holds still while a node is dragged
      drag = { id: n.dataset.n, x0: ev.clientX, y0: ev.clientY, px: pos[n.dataset.n].x, py: pos[n.dataset.n].y, moved: false };
      box.setPointerCapture(ev.pointerId);
    });
    box.addEventListener('pointermove', (ev) => {
      if (!drag) return;
      const dx = ev.clientX - drag.x0, dy = ev.clientY - drag.y0;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      drag.moved = true;
      g.pos[drag.id] = { x: Math.round(drag.px + dx), y: Math.round(drag.py + dy) };
      ontGraphPaint();
    });
    const end = () => {
      if (!drag) return;
      const d = drag;
      drag = null; g.box = null;
      if (d.moved) { render(); return; }
      const twice = last.id === d.id && Date.now() - last.at < 450;
      last = { id: d.id, at: twice ? 0 : Date.now() };
      if (!twice) return;
      const [kind, name] = [d.id.slice(0, 1), d.id.slice(2)];
      const add = kind === 'a' ? areaEntities(mgArea(name)).map((o) => o.name) : [name];
      const fresh = add.filter((x) => !g.open.includes(x));
      if (fresh.length) { g.open = [...g.open, ...fresh]; render(); }
    };
    box.addEventListener('pointerup', end);
    box.addEventListener('pointercancel', end);
    box.addEventListener('click', (ev) => { const e = ev.target.closest('[data-rel]'); if (e) { g.rel = e.dataset.rel; g.rd = null; render(); } });
  }
  function ontWorkspace() {  // the diagram's workspace as it was: the tree, the diagram and the tables, the forms, the trial and the request
    return `${fixBar()}<div class="ont-wsbar"><a class="k-lnk" href="#model">${ki('chevR', 14, 1.75).replace('<svg', '<svg style="transform:rotate(180deg)"')}그래프 탐색</a><span class="k-14 k-b">다이어그램 작업 공간</span><a class="k-lnk k-push" href="#onto">전체 보기${ki('chevR', 14, 1.75)}</a></div>${viewModel()}`;
  }
  function ontWorkspaceAfter() {
    if (S.md.view === 'diagram') mountEr();
    hotField();
    if (S.md.wantNew && S.mg.st && !S.mg.st.error) { S.md.wantNew = false; ACT.mdobjnew(); return; }
    if (S.md.arrive && $(`#col-${S.md.arrive}`)) { $(`#col-${S.md.arrive}`).scrollIntoView({ block: 'nearest', inline: 'nearest' }); S.md.arrive = ''; }
    if (S.mg.st && !S.mg.st.error && !S.iss.list && !S.iss.busy) loadIssues().then(() => { if (S.tab === 'model') render(); });
  }
  screen('model', { area: 'work', word: '그래프 탐색', get bleed() { return ontWs(); }, view: () => (ontWs() ? ontWorkspace() : ontGraph()),
    crumb: () => ['Ontology', '그래프 탐색', ...(ontWs() ? [S.md.view === 'table' ? 'Property · Relation 표' : '다이어그램 작업 공간'] : [])],
    after: () => { if (ontWs()) ontWorkspaceAfter(); else { ontSem(); ontGraphMount(); } } });

  Object.assign(ACT, {
    ontGshow: (t) => {
      const g = S.ont.g, k = t.dataset.k;
      g.show[k] = !g.show[k];
      if (!g.show.object && !g.show.entity) g.show[k === 'object' ? 'entity' : 'object'] = true;  // one kind of node stays
      render();
    },
    ontGrel: (t) => {
      const g = S.ont.g, l = S.mg.st.links.find((x) => x.name === t.dataset.name);
      if (!l) return;
      if (!ontGraphData().rels.includes(l)) { const o = ontObj(l.source); Object.assign(g, { focus: o && mgArea(o.area) ? o.area : '', open: o && mgArea(o.area) ? [] : [l.source], pos: {}, lay: null }); }
      g.rel = l.name; g.rd = null;
      render();
    },
    ontGlist: (t) => { S.ont.g.all = !!t.dataset.v; render(); },
    ontGall: () => { S.ont.g.all = true; render(); const box = $('#ontrels'); if (box) box.scrollIntoView({ block: 'start', behavior: 'smooth' }); },
    ontGreset: () => { Object.assign(S.ont.g, { open: [], pos: {}, lay: null, scroll: null }); render(); },
    ontRdSave: async () => {
      const g = S.ont.g, d = g.rd, l = d && S.mg.st.links.find((x) => x.name === d.name);
      if (!l) return;
      const args = { name: l.name };
      ['source', 'target', 'cardinality'].forEach((k) => { if (d[k] !== l[k]) args[k] = d[k]; });
      try { await ontEdit('update_link', args); g.rd = null; g.lay = null; toast('작성 중인 변경 요청에 Relation을 저장했습니다.'); } catch (e) { fail(e); }
      render();
    },
  });
  Object.assign(INPUT, {
    ontRd: (t) => {
      const d = S.ont.g.rd, l = d && S.mg.st.links.find((x) => x.name === d.name);
      if (!l) return;
      d[t.dataset.k] = t.value;
      const b = $('#ontrdsave');
      if (b) b.disabled = d.source === l.source && d.target === l.target && d.cardinality === l.cardinality;
    },
  });

  // ---- the screens of an Object, an Entity, a state machine and a Relation: 추가 · 편집, 삭제, 히스토리 -------------
  const ONT_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
  async function ontLoad() {  // what the forms and the delete screens read: the definition and the rule cards
    await ontReady();
    if (!S.sem.st) { try { S.sem.st = await api('semantic'); } catch (e) { S.sem.st = { error: e.message, cards: [] }; } }
  }
  const ontIn = (k, v, more = '', cls = '') => `<input class="k-in${cls}" type="text" data-in="itf" data-k="${k}" value="${esc(v ?? '')}"${more}>`;
  const ontPick = (k, rows, cur, more = '') => `<select class="k-in" data-in="itf" data-k="${k}"${more}>${rows.map(([v, w]) => opt(v, w, cur)).join('')}</select>`;
  const ontStatus = (cur) => ontPick('status', Object.entries(STATUS_WORD).map(([k, [, w]]) => [k, w]), cur || 'active');
  const ontOwners = () => `<datalist id="ontowners">${[...new Set([...S.mg.st.areas, ...S.mg.st.objects].map((x) => x.owner).filter(Boolean))].sort().map((x) => `<option value="${esc(x)}">`).join('')}</datalist>`;
  const ontBasic = (body) => `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">${body}</div></div></section>`;
  const ontNamed = (name, word = '영문 이름') => (!name ? ['warn', `${word} 미입력`] : ONT_NAME.test(name) ? null : ['bad', `${word} 형식 오류 · 영문자로 시작, 영문자 · 숫자 · _ 사용`]);
  const ontChanged = (d, was, keys) => Object.fromEntries(keys.filter((k) => String(d[k] ?? '') !== String(was[k] ?? '')).map((k) => [k, d[k]]));
  const ontNothing = () => { throw new Error('변경된 내용이 없어 저장하지 않았습니다.'); };
  // how a kind of item came to read as it does, from the area's own route (an Entity with its Properties, a state machine)
  async function ontHistory(kind, name, word) {
    const r = await api(`ont/history?kind=${kind}&name=${encodeURIComponent(name)}`);
    const WORD = { added: '추가', changed: '변경', removed: '삭제' };
    return r.entries.map((e) => ({ ver: e.version ? `v${e.version}` : '', mark: e.status_label, cp: e.change, at: e.at, who: e.by, deployed: e.deployed,
      say: (e.notes || []).map((n) => n.text).join(' · ') || e.reason || `${word} ${WORD[e.kind] || '변경'}`, rows: e.rows, all: e.all }));
  }

  // -- Object
  item('object', {
    word: 'Object', under: 'objmgr', list: 'objmgr', load: ontLoad,
    find: (id) => mgArea(id) || null, code: (a) => ontName(a), name: (a) => ontClip(a.description, 70) || a.label || a.name, element: (a) => `area:${a.name}`,
    draft: (a) => {
      const d = a ? { label: a.label || '', name: a.name, vocab: (a.aligned || []).some((u) => /schema\.org/.test(u)) ? 'schema' : 'ext', owner: a.owner || '', description: a.description || '', cite: a.cite || '', tier: a.tier ?? '', status: a.status || 'active' }
        : { label: '', name: '', vocab: 'ext', owner: '', description: '', cite: '', tier: '', status: 'active' };
      return { ...d, was: { ...d }, reason: '' };
    },
    form: (d, a) => ontBasic(`<label class="k-f">한글 이름${ontIn('label', d.label, ' placeholder="예: 주문"')}</label>
      <label class="k-f">영문 이름${ontIn('name', d.name, a ? ' disabled' : ' placeholder="예: Order"')}<span class="k-hint">${a ? '등록 후 변경 불가' : 'schema.org 클래스명 우선'}</span></label>
      <label class="k-f">어휘${ontPick('vocab', [['ext', '확장 어휘'], ['schema', 'schema.org']], d.vocab)}</label>
      <label class="k-f">담당자${ontIn('owner', d.owner, ' list="ontowners" placeholder="예: 주문 담당"')}${ontOwners()}</label>
      <div class="k-full"><label class="k-f">정의<textarea class="k-in" rows="3" data-in="itf" data-k="description">${esc(d.description)}</textarea></label></div>
      <label class="k-f">근거 자료${ontIn('cite', d.cite, ' placeholder="예: 주문결제 정책서"')}</label>
      <label class="k-f">차수<input class="k-in" type="number" min="1" data-in="itf" data-k="tier" value="${esc(d.tier)}" placeholder="예: 1"></label>
      ${a ? `<label class="k-f">상태${ontStatus(d.status)}</label>` : ''}`),
    checks: (d, a) => {
      const m = S.mg.st, name = d.name.trim(), bad = ontNamed(name);
      const dup = !a && m.areas.some((x) => x.name === name), same = d.label.trim() && m.areas.some((x) => x.name !== (a || {}).name && x.label === d.label.trim());
      return [dup ? { say: '영문 이름 중복', tone: 'bad' } : same ? { say: '한글 이름 중복', tone: 'warn' } : { say: '이름 중복 없음', tone: 'ok' },
        bad ? { say: bad[1], tone: bad[0] } : !d.label.trim() ? { say: '한글 이름 미입력', tone: 'warn' } : { say: '명명 규칙 준수', tone: 'ok' }];
    },
    valid: (d) => (!d.label.trim() ? '한글 이름이 없어 저장하지 못했습니다. 한글 이름을 입력해 주세요.' : !d.name.trim() ? '영문 이름이 없어 저장하지 못했습니다. 영문 이름을 입력해 주세요.' : ''),
    save: async (d, a) => {
      const name = d.name.trim(), aligned = d.vocab === 'schema' ? [`https://schema.org/${name}`] : [];
      const tier = d.tier === '' || d.tier === null ? '' : Number(d.tier);
      if (!a) {
        await ontEdit('add_area', { name, label: d.label.trim(), description: d.description.trim(), cite: d.cite.trim(), owner: d.owner.trim(), aligned, tier });
        S.ont.osel = name;
        return { element: `area:${name}` };
      }
      const args = ontChanged({ ...d, label: d.label.trim(), description: d.description.trim(), cite: d.cite.trim(), owner: d.owner.trim(), tier }, d.was, ['label', 'description', 'cite', 'owner', 'tier', 'status']);
      if (d.vocab !== d.was.vocab) args.aligned = aligned.length ? aligned : (a.aligned || []).filter((u) => !/schema\.org/.test(u));
      if (!Object.keys(args).length) ontNothing();
      await ontEdit('update_area', { name: a.name, ...args });
      S.ont.osel = a.name;
      return {};
    },
    uses: async (a) => {
      const m = S.mg.st, ents = areaEntities(a), names = new Set(ents.map((o) => o.name)), cards = ontCards([...names]) || [];
      const qs = m.questions.filter((x) => m.decisions.some((d) => d.name === x.decision && names.has(d.target)));
      return [ents.length ? { say: `Entity ${ents.length}개`, sub: `${ents.slice(0, 4).map((o) => o.label).join(', ')}${ents.length > 4 ? ` 외 ${ents.length - 4}` : ''}`, href: `objects?area=${encodeURIComponent(a.name)}` } : null,
        cards.length ? { say: `규칙 ${cards.length}개`, sub: `${a.label || a.name} 영역 규칙`, href: 'semrules' } : null,
        qs.length ? { say: `검증 질문 ${qs.length}개`, sub: '', href: 'check' } : null].filter(Boolean);
    },
    remove: async (a) => {
      const ents = areaEntities(a);
      if (ents.length) throw new Error(`Entity ${ents.length}개가 이 Object 아래에 있어 삭제를 요청하지 못했습니다. Entity를 다른 Object로 옮기거나 먼저 삭제해 주세요.`);
      await ontEdit('delete_area', { name: a.name });
      S.ont.osel = '';
      return {};
    },
  });

  // -- Entity, with its Properties
  const ontPropRow = (p) => ({ was: p.name, name: p.name, label: p.label || '', type: p.type || 'string', values: (p.values || []).join(', '), required: !!p.required, key: !!p.key, inherited: p.inherited || '', calc: !!p.expr, del: false });
  const ontValues = (text) => String(text || '').split(',').map((x) => x.trim()).filter(Boolean);
  item('entity', {
    word: 'Entity', under: 'objects', list: 'objects', load: ontLoad,
    find: (id) => ontObj(id), code: (o) => ontName(o), name: (o) => ontClip(o.description, 70) || o.label || o.name, element: (o) => `object:${o.name}`,
    draft: (o) => {
      const d = o ? { area: o.area || '', label: o.label || '', name: o.name, owner: o.owner || '', description: o.description || '', key: o.key || '', table: o.table || '', parent: o.parent || '', status: o.status || 'active' }
        : { area: mgArea(itemParam('area')) ? itemParam('area') : '', label: '', name: '', owner: '', description: '', key: '', table: '', parent: '', status: 'active' };
      const props = o ? mgProps(o.name).map(ontPropRow) : [];
      if (itemParam('add') === 'prop') props.push({ was: '', name: '', label: '', type: 'string', values: '', required: false, del: false });
      return { ...d, was: { ...d }, props, reason: '' };
    },
    form: (d, o) => {
      const m = S.mg.st, tables = m.sources.source.tables || [];
      const row = (p, i) => {
        const fixed = p.inherited || p.calc, off = p.del || fixed ? ' disabled' : '';
        const cell = (k, more = '') => `<input class="k-in sm${k === 'name' ? ' mono' : ''}" type="text" data-in="ontPf" data-i="${i}" data-k="${k}" value="${esc(p[k])}" aria-label="${{ name: '이름', label: '한글', values: '허용값' }[k]}"${more}>`;
        return `<tr${p.del ? ' style="opacity:.5"' : ''}><td class="tight">${cell('name', p.was ? ' disabled' : ' placeholder="예: return_reason"')}</td><td class="tight">${cell('label', `${off} placeholder="예: 반품 사유"`)}</td>
          <td class="tight"><select class="k-in sm" style="min-width:124px" data-in="ontPf" data-i="${i}" data-k="type" aria-label="타입"${off}>${TYPES.map((t) => opt(t, t, p.type)).join('')}</select></td>
          <td class="tight">${p.calc ? '<span class="k-s">계산값</span>' : p.inherited ? `<span class="k-s">상속 · ${esc(mgLabel(p.inherited))}</span>` : `<span class="k-h nw">${cell('values', `${off} placeholder="쉼표로 구분"`)}<label class="k-ck mid k-13" style="white-space:nowrap"><input type="checkbox" data-in="ontPf" data-i="${i}" data-k="required"${p.required ? ' checked' : ''}${off || (p.key ? ' disabled' : '')}>필수</label></span>`}</td>
          <td class="tight r">${p.key ? '<span class="k-chip">식별 키</span>' : fixed ? '' : `<button class="k-lnk" type="button" data-act="ontPdel" data-i="${i}">${p.del ? '삭제 취소' : '삭제'}</button>`}</td></tr>`;
      };
      return `${ontBasic(`<label class="k-f">소속 Object<select class="k-in" data-in="itf" data-k="area"><option value="">${AREA_NONE}</option>${m.areas.map((a) => opt(a.name, ontName(a), d.area)).join('')}</select></label>
        <label class="k-f">한글 이름${ontIn('label', d.label, ' placeholder="예: 반품"')}</label>
        <label class="k-f">영문 이름${ontIn('name', d.name, o ? ' disabled' : ' placeholder="예: Return"')}${o ? '<span class="k-hint">등록 후 변경 불가</span>' : ''}</label>
        <label class="k-f">담당자${ontIn('owner', d.owner, ' list="ontowners" placeholder="예: 클레임 담당"')}${ontOwners()}</label>
        <div class="k-full"><label class="k-f">정의<textarea class="k-in" rows="3" data-in="itf" data-k="description">${esc(d.description)}</textarea></label></div>
        <label class="k-f">식별 키 후보${ontIn('key', d.key, ' placeholder="예: return_id"', ' mono')}</label>
        <label class="k-f">소스 후보${ontIn('table', d.table, ` list="onttables" placeholder="${tables.length ? '테이블 선택 또는 입력' : '예: clm_claim'}"`)}<datalist id="onttables">${tables.map((t) => `<option value="${esc(t.table)}">`).join('')}</datalist></label>
        <label class="k-f">상위 Entity<select class="k-in" data-in="itf" data-k="parent"><option value="">없음</option>${m.objects.filter((x) => x.name !== d.name).map((x) => opt(x.name, ontName(x), d.parent)).join('')}</select></label>
        ${o ? `<label class="k-f">상태${ontStatus(d.status)}</label>` : ''}`)}
        <section class="k-card"><div class="k-ch"><h2>Property</h2><span class="k-chip">${d.props.filter((p) => !p.del).length}</span><span class="k-pha k-push"><button class="k-lnk" type="button" data-act="ontPadd">${ki('plus', 16, 1.75)}Property</button></span></div>
        <div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">한글</th><th scope="col">타입</th><th scope="col">허용값 · 제약</th><th scope="col"></th></tr></thead><tbody>${d.props.map(row).join('') || '<tr><td colspan="5" class="mut">등록된 Property가 없습니다.</td></tr>'}</tbody></table></div></section>`;
    },
    checks: (d, o) => {
      const m = S.mg.st, name = d.name.trim(), bad = ontNamed(name), live = d.props.filter((p) => !p.del);
      const names = live.map((p) => p.name.trim()).filter(Boolean), dup = names.filter((n, i) => names.indexOf(n) !== i);
      const odd = live.filter((p) => !p.was && p.name.trim() && !ONT_NAME.test(p.name.trim()));
      const key = d.key.trim();
      return [!o && m.objects.some((x) => x.name === name) ? { say: '영문 이름 중복', tone: 'bad' } : bad ? { say: bad[1], tone: bad[0] } : { say: '명명 규칙 준수', tone: 'ok' },
        d.area ? { say: '소속 Object 지정', tone: 'ok' } : { say: '소속 Object 미지정', tone: 'warn' },
        dup.length ? { say: `Property 이름 중복 · ${[...new Set(dup)].join(', ')}`, tone: 'bad' } : odd.length ? { say: `Property 이름 형식 오류 · ${odd.map((p) => p.name).join(', ')}`, tone: 'bad' } : { say: 'Property 이름 중복 없음', tone: 'ok' },
        !key ? { say: '식별 키 후보 미입력', tone: 'warn' } : names.includes(key) ? { say: '식별 키 Property 확인', tone: 'ok' } : { say: '식별 키 Property 자동 추가', sub: `${key} · string`, tone: 'note' }];
    },
    valid: (d) => (!d.label.trim() ? '한글 이름이 없어 저장하지 못했습니다. 한글 이름을 입력해 주세요.' : !d.name.trim() ? '영문 이름이 없어 저장하지 못했습니다. 영문 이름을 입력해 주세요.' : !d.key.trim() ? '식별 키 후보가 없어 저장하지 못했습니다. 식별 키 후보를 입력해 주세요.' : d.props.some((p) => !p.del && !p.name.trim()) ? '이름이 없는 Property가 있어 저장하지 못했습니다. 이름을 입력하거나 Property를 삭제해 주세요.' : ''),
    save: async (d, o) => {
      const name = d.name.trim(), key = d.key.trim();
      const spec = (p) => ({ label: p.label.trim(), type: p.type, values: ontValues(p.values), required: !!p.required });
      const live = d.props.filter((p) => !p.del && !p.inherited && !p.calc);
      if (!o) {
        const properties = Object.fromEntries(live.map((p) => [p.name.trim(), spec(p)]));
        if (!properties[key]) properties[key] = { type: 'string', label: '식별자', required: true };
        await ontEdit('add_object', { name, label: d.label.trim(), description: d.description.trim(), area: d.area, owner: d.owner.trim(), key, table: d.table.trim(), parent: d.parent, properties });
        Object.assign(S.ont, { esel: name, etab: 'def' });
        return { element: `object:${name}` };
      }
      let n = 0;
      const now = mgProps(o.name);
      for (const p of d.props) {  // one edit a Property: what fails says which one, and what went in before it stays in the request being written
        if (p.inherited || p.calc) continue;
        const was = now.find((x) => x.name === p.was);
        if (!p.was && !p.del) { await ontEdit('add_property', { object: o.name, name: p.name.trim(), ...spec(p) }); n++; continue; }
        if (p.was && p.del) { await ontEdit('delete_property', { object: o.name, name: p.was }); n++; continue; }
        if (!was || p.del) continue;
        const diff = ontChanged({ label: p.label.trim(), type: p.type, required: !!p.required }, { label: was.label || '', type: was.type, required: !!was.required }, ['label', 'type', 'required']);
        if (ontValues(p.values).join('|') !== (was.values || []).join('|')) diff.values = ontValues(p.values);
        if (Object.keys(diff).length) { await ontEdit('update_property', { object: o.name, name: p.was, ...diff }); n++; }
      }
      const args = ontChanged({ ...d, label: d.label.trim(), description: d.description.trim(), owner: d.owner.trim(), table: d.table.trim(), key }, d.was, ['label', 'description', 'area', 'owner', 'table', 'parent', 'status', 'key']);
      if (Object.keys(args).length) { await ontEdit('update_object', { name: o.name, ...args }); n++; }
      if (!n) ontNothing();
      Object.assign(S.ont, { esel: o.name, etab: 'def' });
      return {};
    },
    uses: async (o) => {
      const m = S.mg.st, rels = m.links.filter((l) => l.source === o.name || l.target === o.name), kids = m.objects.filter((x) => x.parent === o.name), cards = ontCards([o.name]) || [];
      const others = [...new Set(rels.map((l) => mgLabel(l.source === o.name ? l.target : l.source)))];
      const r = await api('item/uses?element=' + encodeURIComponent(`object:${o.name}`));
      return [rels.length ? { say: `Relation ${rels.length}개`, sub: `${others.slice(0, 3).join(', ')}${others.length > 3 ? ` 외 ${others.length - 3}` : ''}`, href: `model?entity=${encodeURIComponent(o.name)}` } : null,
        kids.length ? { say: `하위 Entity ${kids.length}개`, sub: kids.map((x) => x.label).join(', '), href: 'objects' } : null,
        cards.length ? { say: `규칙 ${cards.length}개`, sub: cards.slice(0, 3).map((c) => c.id).join(', ') + (cards.length > 3 ? ` 외 ${cards.length - 3}` : ''), href: 'semrules' } : null,
        ...r.uses.filter((u) => u.kind !== '결정').map((u) => ({ say: `${ONT_KIND[u.kind] || u.kind} ${u.names.length}개`, sub: u.names.slice(0, 3).join(', ') + (u.names.length > 3 ? ` 외 ${u.names.length - 3}` : ''), href: u.screen })),
        o.table && !noSource() ? { say: 'Mapping 1개', sub: `${o.table} 테이블 · Property ↔ 컬럼`, href: 'sources' } : null,
        o.states ? { say: '상태 전이 1개', sub: '', href: 'objects' } : null].filter(Boolean);
    },
    remove: async (o) => { await ontEdit('delete_object', { name: o.name }); S.ont.esel = ''; return {}; },
    history: (o) => ontHistory('entity', o.name, 'Entity'),
  });
  Object.assign(INPUT, {
    ontPf: (t) => {
      const it = S.it, p = it.d && it.d.props[Number(t.dataset.i)];
      if (!p) return;
      p[t.dataset.k] = t.type === 'checkbox' ? t.checked : t.value;
      const box = $('#itchecks');
      if (box) box.innerHTML = itemChecks(ITEM.entity, it);
    },
  });
  Object.assign(ACT, {
    ontPadd: () => { if (S.it.d) { S.it.d.props.push({ was: '', name: '', label: '', type: 'string', values: '', required: false, del: false }); render(); } },
    ontPdel: (t) => { const d = S.it.d, i = Number(t.dataset.i), p = d && d.props[i]; if (!p) return; if (p.was) p.del = !p.del; else d.props.splice(i, 1); render(); },
  });

  // -- a state machine: the states of one Entity and the moves allowed between them
  const ontStateList = (d) => ontValues(d.states);
  item('state', {
    word: '상태 전이', under: 'objects', list: 'objects', load: ontLoad,
    find: (id) => (S.mg.st.states || []).find((s) => s.object === id) || null,
    code: (s) => `${s.label} · ${ontFlow(s).prop}`, name: (s) => ontClip(ontFlow(s).text, 80), element: (s) => `object:${s.object}`,
    draft: (s) => {
      const m = S.mg.st, free = m.objects.filter((o) => !o.states);
      const want = free.find((o) => o.name === itemParam('entity')) || free.find((o) => o.name === S.ont.esel) || free[0];
      return s ? { object: s.object, property: s.property, states: s.states.join(', '), initial: s.initial || s.states[0] || '', transitions: s.transitions.map((t) => ({ from: t.from, to: t.to, action: t.action || '' })), from: '', to: '', action: '', reason: '' }
        : { object: want ? want.name : '', property: '', states: '', initial: '', transitions: [], from: '', to: '', action: '', reason: '' };
    },
    form: (d, s) => {
      const m = S.mg.st, states = ontStateList(d);
      const props = d.object ? mgProps(d.object).filter((p) => !p.key && !p.expr && ['enum', 'string'].includes(p.type)) : [];
      const prop = props.find((p) => p.name === d.property);
      const acts = m.actions.filter((a) => a.target === d.object);
      const act = (name) => (name ? (acts.find((a) => a.name === name) || { label: name }).label : '없음 · 시스템 변경');
      const pick = (k, cur) => `<select class="k-in" data-in="itf" data-k="${k}"><option value="">선택</option>${states.map((x) => opt(x, (prop && (prop.labels || {})[x]) || x, cur)).join('')}</select>`;
      const word = (x) => (prop && (prop.labels || {})[x]) || x;
      return `${ontBasic(`<label class="k-f">Entity<select class="k-in" data-in="itf" data-k="object" data-re${s ? ' disabled' : ''}>${(s ? m.objects.filter((o) => o.name === s.object) : m.objects.filter((o) => !o.states)).map((o) => opt(o.name, ontName(o), d.object)).join('') || '<option value="">선택 가능한 Entity 없음</option>'}</select></label>
        <label class="k-f">상태 Property<select class="k-in" data-in="itf" data-k="property" data-re><option value="">선택</option>${props.map((p) => opt(p.name, `${p.label || p.name} · ${p.name}`, d.property)).join('')}</select>${prop && (prop.values || []).length ? `<span class="k-hint">허용값 ${prop.values.length}종</span>` : ''}</label>
        <div class="k-full"><label class="k-f">상태 값${ontIn('states', d.states, ' placeholder="예: NORMAL, RETURN_REQUESTED, RETURNED"')}<span class="k-hint">쉼표로 구분</span></label></div>
        <label class="k-f">초기 상태${pick('initial', d.initial)}</label><span></span>
        <label class="k-f">시작 상태${pick('from', d.from)}</label><label class="k-f">끝 상태${pick('to', d.to)}</label>
        <label class="k-f">전이 Action<select class="k-in" data-in="itf" data-k="action"><option value="">없음 · 시스템 변경</option>${acts.map((a) => opt(a.name, a.label, d.action)).join('')}</select></label>`)}
        <section class="k-card"><div class="k-ch"><h2>허용 전이</h2><span class="k-chip">${d.transitions.length}</span><span class="k-pha k-push"><button class="k-lnk" type="button" data-act="ontTadd">${ki('plus', 16, 1.75)}전이</button></span></div>
        <div class="k-x"><table class="k-t"><thead><tr><th scope="col">시작</th><th scope="col">끝</th><th scope="col">전이 Action</th><th scope="col"></th></tr></thead><tbody>${d.transitions.map((t, i) => `<tr><td>${esc(word(t.from))}</td><td>${esc(word(t.to))}</td><td>${esc(act(t.action))}</td><td class="r"><button class="k-lnk" type="button" data-act="ontTdel" data-i="${i}">삭제</button></td></tr>`).join('') || '<tr><td colspan="4" class="mut">등록된 전이가 없습니다.</td></tr>'}</tbody></table></div></section>`;
    },
    checks: (d) => {
      const m = S.mg.st, states = ontStateList(d), prop = mgProps(d.object).find((p) => p.name === d.property);
      const lost = d.transitions.filter((t) => !states.includes(t.from) || !states.includes(t.to));
      const extra = prop && (prop.values || []).length ? states.filter((x) => !prop.values.includes(x)) : [];
      const ends = states.filter((x) => !d.transitions.some((t) => t.from === x));
      const seen = new Set([d.initial || states[0]]);
      for (let grew = true; grew;) { grew = false; d.transitions.forEach((t) => { if (seen.has(t.from) && !seen.has(t.to)) { seen.add(t.to); grew = true; } }); }
      const far = states.filter((x) => !seen.has(x));
      const off = d.transitions.map((t) => { const a = t.action && m.actions.find((x) => x.name === t.action); return a && a.transition_to && a.transition_to !== t.to ? `${a.label} → ${a.transition_to}` : ''; }).filter(Boolean);
      return [states.length < 2 ? { say: '상태 값 2개 이상 필요', tone: 'warn' } : lost.length ? { say: `상태 값에 없는 전이 · ${lost.map((t) => `${t.from} → ${t.to}`).join(', ')}`, tone: 'bad' } : { say: '전이 상태 확인', tone: 'ok' },
        extra.length ? { say: `허용값 추가 · ${extra.join(', ')}`, tone: 'note' } : null,
        states.length >= 2 ? (ends.length ? { say: `종료 상태 · ${ends.join(', ')}`, tone: 'ok' } : { say: '종료 상태 없음', tone: 'warn' }) : null,
        far.length ? { say: `초기 상태에서 도달 불가 · ${far.join(', ')}`, tone: 'warn' } : null,
        off.length ? { say: `Action 처리 후 상태 불일치 · ${off.join(', ')}`, tone: 'warn' } : d.transitions.some((t) => t.action) ? { say: 'Action 처리 후 상태 일치', tone: 'ok' } : null].filter(Boolean);
    },
    valid: (d) => (!d.object ? 'Entity가 선택되지 않아 저장하지 못했습니다. Entity를 선택해 주세요.' : !d.property ? '상태 Property가 선택되지 않아 저장하지 못했습니다. 상태 Property를 선택해 주세요.' : ontStateList(d).length < 2 ? '상태 값이 부족해 저장하지 못했습니다. 상태 값을 2개 이상 입력해 주세요.' : ''),
    save: async (d) => {
      const states = ontStateList(d);
      await ontEdit('update_states', { object: d.object, property: d.property, states, initial: states.includes(d.initial) ? d.initial : states[0], transitions: d.transitions });
      S.ont.ssel = d.object;
      return { element: `object:${d.object}` };
    },
    uses: async (s) => {
      const m = S.mg.st, acts = m.actions.filter((a) => a.target === s.object && (a.transition_to || s.transitions.some((t) => t.action === a.name) || (a.criteria || []).some((c) => (c.states || []).length)));
      const r = await api('item/uses?element=' + encodeURIComponent(`property:${s.object}.${s.property}`));
      return [acts.length ? { say: `Action ${acts.length}개`, sub: acts.map((a) => a.label).join(', '), href: 'actions' } : null,
        ...r.uses.map((u) => ({ say: `${ONT_KIND[u.kind] || u.kind} ${u.names.length}개`, sub: `${u.names.slice(0, 3).join(', ')}${u.names.length > 3 ? ` 외 ${u.names.length - 3}` : ''}`, href: u.screen }))].filter(Boolean);
    },
    remove: async (s) => { await ontEdit('delete_states', { object: s.object }); S.ont.ssel = ''; return {}; },
    history: (s) => ontHistory('state', s.object, '상태 전이'),
  });
  Object.assign(ACT, {
    ontTadd: () => {
      const d = S.it.d;
      if (!d) return;
      if (!d.from || !d.to) { toast('시작 상태와 끝 상태를 선택해 주세요.', true); return; }
      if (d.transitions.some((t) => t.from === d.from && t.to === d.to)) { toast('동일한 전이가 있어 추가하지 못했습니다.', true); return; }
      d.transitions.push({ from: d.from, to: d.to, action: d.action || '' });
      Object.assign(d, { from: '', to: '', action: '' });
      render();
    },
    ontTdel: (t) => { const d = S.it.d; if (d) { d.transitions.splice(Number(t.dataset.i), 1); render(); } },
  });
  document.addEventListener('change', (ev) => {  // the states typed in: the choices of the selects follow once the box is left
    if (S.tab === 'state-form' && ev.target.dataset && ev.target.dataset.k === 'states' && S.it.d) render();
  });

  // -- Relation
  item('relation', {
    word: 'Relation', under: 'model', list: 'model', load: ontLoad,
    find: (id) => S.mg.st.links.find((l) => l.name === id) || null, code: (l) => l.name, name: (l) => `${mgLabel(l.source)} → ${mgLabel(l.target)}`, element: (l) => `link:${l.name}`,
    draft: (l) => {
      const src = ontObj(itemParam('source')) ? itemParam('source') : '';
      const d = l ? { source: l.source, target: l.target, name: l.name, cardinality: l.cardinality || 'many_to_one', inverse: l.inverse || '', label: l.label || '', cite: '', status: l.status || 'active', required: !!l.required }
        : { source: src, target: '', name: '', cardinality: 'many_to_one', inverse: '', label: '', cite: '', status: 'active', required: false };
      const out = { ...d, was: { ...d }, reason: '' };
      if (l) api('item/history?element=' + encodeURIComponent(`link:${l.name}`)).then((r) => {  // what the list does not carry: where the Relation is said
        if (S.it.d !== out || !r.now || !r.now.cite) return;
        out.cite = r.now.cite; out.was.cite = r.now.cite;
        if (S.tab === 'relation-form') render();
      }).catch(() => {});
      return out;
    },
    form: (d, l) => {
      const ents = (cur) => `<option value="">선택</option>${S.mg.st.objects.map((o) => opt(o.name, ontName(o), cur)).join('')}`;
      return ontBasic(`<label class="k-f">시작 Entity<select class="k-in" data-in="itf" data-k="source">${ents(d.source)}</select></label>
        <label class="k-f">끝 Entity<select class="k-in" data-in="itf" data-k="target">${ents(d.target)}</select></label>
        <label class="k-f">관계 유형${ontIn('name', d.name, l ? ' disabled' : ' placeholder="예: stored_at"', ' mono')}<span class="k-hint">${l ? '등록 후 변경 불가' : '영문자로 시작, 영문자 · 숫자 · _ 사용'}</span></label>
        <label class="k-f">카디널리티${ontPick('cardinality', Object.entries(CARD_WORD), d.cardinality)}</label>
        <label class="k-f">역방향 이름${ontIn('inverse', d.inverse, ' placeholder="예: stores"', ' mono')}</label>
        <label class="k-f">설명${ontIn('label', d.label, ' placeholder="예: 재고가 보관되는 장소"')}</label>
        <label class="k-f">근거 자료${ontIn('cite', d.cite, ' placeholder="예: 인덱스정의서"')}</label>
        ${l ? `<label class="k-f">상태${ontStatus(d.status)}</label>` : '<span></span>'}
        <div class="k-full"><label class="k-ck mid"><input type="checkbox" data-in="itf" data-k="required"${d.required ? ' checked' : ''}>필수 Relation</label></div>`);
    },
    checks: (d, l) => {
      const m = S.mg.st, name = d.name.trim(), bad = ontNamed(name, '관계 유형');
      const dup = !l && m.links.some((x) => x.name === name || x.inverse === name);
      const pair = m.links.filter((x) => x.name !== (l || {}).name && x.source === d.source && x.target === d.target);
      return [dup ? { say: '관계 유형 중복', tone: 'bad' } : bad ? { say: bad[1], tone: bad[0] } : { say: '관계 유형 중복 없음', tone: 'ok' },
        !d.source || !d.target ? { say: '시작 · 끝 Entity 미선택', tone: 'warn' } : d.source === d.target ? { say: '자기 참조 Relation', tone: 'note' } : { say: '순환 참조 없음', tone: 'ok' },
        pair.length ? { say: `같은 Entity 쌍의 다른 Relation ${pair.length}개`, sub: pair.map((x) => x.name).join(', '), tone: 'note' } : null].filter(Boolean);
    },
    valid: (d) => (!d.source || !d.target ? '시작 · 끝 Entity가 선택되지 않아 저장하지 못했습니다. Entity를 선택해 주세요.' : !d.name.trim() ? '관계 유형이 없어 저장하지 못했습니다. 관계 유형을 입력해 주세요.' : ''),
    save: async (d, l) => {
      const name = d.name.trim(), text = { label: d.label.trim(), inverse: d.inverse.trim(), cite: d.cite.trim() };
      if (!l) {
        await ontEdit('add_link', { name, source: d.source, target: d.target, cardinality: d.cardinality, label: text.label, inverse: text.inverse, required: d.required });
        if (text.cite) await ontEdit('update_link', { name, cite: text.cite });
        Object.assign(S.ont.g, { rel: name, rd: null, lay: null, want: '' });
        return { element: `link:${name}`, go: `model?rel=${encodeURIComponent(name)}` };
      }
      const args = ontChanged({ ...d, ...text }, d.was, ['source', 'target', 'cardinality', 'label', 'inverse', 'cite', 'status', 'required']);
      if (!Object.keys(args).length) ontNothing();
      await ontEdit('update_link', { name: l.name, ...args });
      Object.assign(S.ont.g, { rel: l.name, rd: null, lay: null, want: '' });
      return { go: `model?rel=${encodeURIComponent(l.name)}` };
    },
    remove: async (l) => { await ontEdit('delete_link', { name: l.name }); Object.assign(S.ont.g, { rel: '', rd: null, lay: null }); return {}; },
  });
