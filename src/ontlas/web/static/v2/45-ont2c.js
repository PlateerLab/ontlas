  // ---- 용어사전 (ONT-04): the terms a definition does not carry itself, and the ways people say the same thing ---------
  // An expression relation is not kept on its own: it is read from a term (its synonyms, the pairs not to be swapped,
  // the words not to use, the wider or narrower word), and editing one edits that term.

  const O2_REL = { confusable: ['혼동주의', 'b', '↔'], broader: ['상위 · 하위', '', '›'], avoid: ['쓰지 않는 표현', 'warn', '→'], synonym: ['동의어', '', '='] };
  const O2_REL_FIELD = { confusable: 'confusable', broader: 'broader', avoid: 'avoid', synonym: 'synonyms' };
  const O2_LX_STEP = 10;
  const o2TermName = (r) => (r.english ? `${r.term}@${r.english}` : r.term);
  const o2Norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, '');
  // which kind of term a row is: the kind its glossary gave it, else what it names
  const o2Bucket = (r) => r.kind || (/^(area|object):/.test(r.concept) ? 'Object · Entity' : r.concept.startsWith('value:') ? '코드값' : r.concept ? (r.concept_kind || '기타') : '기타');
  const o2IsDef = (r) => !r.kind && /^(area|object):/.test(r.concept);  // an Object's or an Entity's own name: defined on its own screen

  function o2Rels(st) {
    const out = [];
    st.rows.forEach((r) => {
      const groups = [];
      r.confusable.forEach((c) => { const g = groups.find((x) => x.note === (c.note || '')); if (g) g.others.push(c.term); else groups.push({ note: c.note || '', others: [c.term] }); });
      groups.forEach((g, i) => out.push({ id: `confusable|${r.id}|${i}`, kind: 'confusable', row: r, others: g.others, note: g.note }));
      if (r.broader.length) out.push({ id: `broader|${r.id}`, kind: 'broader', row: r, others: r.broader, note: '' });
      if (r.avoid.length) out.push({ id: `avoid|${r.id}`, kind: 'avoid', row: r, others: r.avoid, note: '' });
      if (r.synonyms.length) out.push({ id: `synonym|${r.id}`, kind: 'synonym', row: r, others: r.synonyms, note: '' });
    });
    const order = Object.keys(O2_REL);
    return out.sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind));
  }
  const o2RelName = (x) => `${x.row.term} ${O2_REL[x.kind][2]} ${x.others.join(', ')}`;
  // where a term's definition lives, as a link to that screen
  function o2ConceptLink(r) {
    if (!r.concept) return '<span class="k-mut">-</span>';
    const [k] = o2Split(r.concept), to = { area: 'objmgr', object: 'objects', property: 'objects', value: 'objects', decision: 'semrules', parameter: 'semrules', metric: 'semrules', function: 'semrules', query: 'query', action: 'actions', link: 'model' }[k];
    const say = `${r.concept_of ? `${r.concept_of} › ` : ''}${r.concept_label || o2Split(r.concept)[1]}${r.concept_found === false ? ' · 정의 없음' : ''}`;
    return to && known(to) && r.concept_found !== false ? `<a href="#${to}">${esc(say)}</a>` : esc(say);
  }
  const o2TermChips = (r) => `<span class="k-chip${r.status === 'review' ? ' warn' : r.status === 'deprecated' ? ' bad' : ''}">${(TERM_STATUS[r.status] || TERM_STATUS.active)[1]}</span>${r.new ? '<span class="k-chip ok">새로 추가</span>' : r.pending ? '<span class="k-chip warn">변경 대기</span>' : ''}${r.conflicts ? `<span class="k-chip bad">충돌 ${r.conflicts}</span>` : ''}`;

  function o2Lexicon() {
    const X = S.o2.lx, st = S.lx.st;
    const head = kHead('용어사전', '초안에 정의가 없는 용어와 표현 관계를 관리합니다. 표현 관계는 다르게 부르는 표현을 표준 용어에 잇습니다. Object와 Entity의 정의는 오브젝트 관리와 엔티티 관리에 있어 여기에 다시 적지 않습니다.',
      canEdit() ? `<button class="k-btn" data-act="o2lximp">${ki('file', 16, 1.75)}가져오기 · 엑셀 · YAML</button><a class="k-btn" href="${itemHref('termrel', 'form')}">${ki('plus', 16, 1.75)}표현 관계</a><a class="k-btn" href="${itemHref('term', 'form')}">${ki('plus', 16, 1.75)}용어</a>` : '');
    if (!st || S.lx.busy) return head + o2Wait();
    if (st.error) return head + kEmpty('불러오지 못했습니다', st.error);
    const rels = o2Rels(st), terms = st.rows.filter((r) => !o2IsDef(r)), defs = st.rows.length - terms.length;
    const buckets = [...new Set(terms.map(o2Bucket))];
    if (X.kind !== 'all' && X.kind !== 'defs' && !buckets.includes(X.kind)) X.kind = 'all';
    const q = o2Norm(X.q), hit = (r) => !q || o2Norm([r.term, r.english, ...r.synonyms, ...r.abbreviations, r.concept_label, r.definition].join(' ')).includes(q);
    const pool = (X.kind === 'defs' ? st.rows.filter(o2IsDef) : X.kind === 'all' ? terms : terms.filter((r) => o2Bucket(r) === X.kind)).filter(hit);
    if (!S.lx.sel || !st.rows.some((r) => r.id === S.lx.sel)) S.lx.sel = (pool[0] || terms[0] || st.rows[0] || {}).id || '';
    const sel = st.rows.find((r) => r.id === S.lx.sel);
    const rq = o2Norm(X.rq), rpool = rels.filter((x) => (X.rel === 'all' || x.kind === X.rel) && (!rq || o2Norm([x.row.term, x.row.english, ...x.others, x.note].join(' ')).includes(rq)));
    if (X.rsel && !rels.some((x) => x.id === X.rsel)) X.rsel = '';
    if (!X.rsel && rpool.length) X.rsel = rpool[0].id;
    const rsel = rels.find((x) => x.id === X.rsel);
    const chan = st.rows.flatMap((r) => Object.entries(r.channels || {}).map(([c, w]) => ({ row: r, channel: c, word: w })));
    const review = st.rows.filter((r) => r.status === 'review').length;
    const nrel = (k) => rels.filter((x) => x.kind === k).length;
    const ws = S.mg.st && !S.mg.st.error ? S.mg.st.workspace : null;
    const pend = ws && ws.dirty ? `<div class="k-bar"><span class="k-chip warn">변경 대기</span><span class="k-14">작성 중인 변경 요청에 변경 ${ws.edits.length}건이 담겨 있습니다. 올려서 배포해야 검색과 API 응답에 반영됩니다</span><span class="k-push"><a class="k-btn" href="#changes">변경 요청 · 버전</a></span></div>` : '';
    const stat = (word, n, sub, warn) => `<div class="k-card${warn ? ' o2-warn' : ''}" style="flex:1 1 150px;padding:16px"><p class="k-s" style="margin:0">${word}</p><p class="k-big${warn ? ' warn' : ''}">${count(n)}</p><p class="${warn ? 'k-warn k-13' : 'k-s'}" style="margin:4px 0 0">${esc(sub)}</p></div>`;
    const stats = `<section class="k-wrap" aria-label="용어사전 현황">
      ${stat('용어', terms.length, buckets.map((b) => `${b} ${terms.filter((r) => o2Bucket(r) === b).length}`).join(' · ') || '등록된 용어 없음')}
      ${stat('표현 관계', rels.length, `동의어 ${nrel('synonym')} · 혼동주의 ${nrel('confusable')} · 쓰지 않는 표현 ${nrel('avoid')} · 상위 · 하위 ${nrel('broader')}`)}
      ${stat('고객 표기', chan.length, '채널에서 표준 용어를 부르는 말')}
      ${stat('확인 필요', review + st.conflicts.length, `확인 필요 용어 ${review} · 충돌 ${st.conflicts.length}`, review + st.conflicts.length > 0)}</section>`;
    const why = `<section class="k-h g12" role="note" style="padding:12px 16px;border-radius:12px;background:var(--blue-soft)"><span style="width:36px;height:36px;border-radius:8px;background:#fff;color:var(--blue);display:inline-flex;align-items:center;justify-content:center">${ki('search', 20, 1.75)}</span>
      <div style="flex:1 1 420px;min-width:0"><p class="k-b" style="margin:0">왜 필요한가</p><p class="k-i3 k-14" style="margin:2px 0 0">같은 개념을 한영 · 고객사마다 다르게 부르면 AI가 틀립니다. 표준 개념은 그대로 두고 표현 차이는 표현 관계로 흡수합니다.</p></div></section>`;
    const conflicts = st.conflicts.length ? `<section class="k-card"><div class="k-ch"><h2>충돌</h2><span class="k-chip bad">${st.conflicts.length}</span><span class="k-s">용어사전이 같은 말을 두 가지로 말하는 곳</span></div>${st.conflicts.slice(0, 8).map((c) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(CONFLICT_WORD[c.kind] || c.kind)} · ${esc(c.label)}</span><span class="k-s">${esc(c.text)}</span></span>${c.terms[0] ? `<button class="k-lnk" data-act="o2lxsel" data-id="${esc(c.terms[0])}" data-all="1">용어 보기</button>` : ''}</div>`).join('')}</section>` : '';
    // the terms
    const shown = pool.slice(0, X.n || O2_LX_STEP);
    const tr = (r) => { const rules = (r.used_by || []).filter((u) => /^(결정|함수) /.test(u));
      return `<tr class="${r.id === S.lx.sel ? 'on' : ''}" data-act="o2lxsel" data-id="${esc(r.id)}"><td class="b">${esc(r.term)}</td><td class="k-code">${r.english ? esc(r.english) : '<span class="k-mut">-</span>'}</td><td><span class="k-chip${r.kind ? ' b' : ''}">${esc(o2Bucket(r))}</span></td>
        <td>${o2ConceptLink(r)}</td><td>${rules.length ? esc(rules.map((u) => u.replace(/^\S+ /, '')).join(', ')) : '<span class="k-mut">-</span>'}</td><td><span class="k-h g4">${o2TermChips(r)}</span></td></tr>`; };
    const segs = [['all', `전체 ${terms.length}`], ...buckets.map((b) => [b, `${b} ${terms.filter((r) => o2Bucket(r) === b).length}`]), ...(defs ? [['defs', `Object · Entity ${defs}`]] : [])];
    const table = `<section class="k-card" aria-labelledby="o2gl" style="flex:3 1 600px"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="o2gl">용어</h2>${o2Seg('구분', segs, X.kind, 'o2lxkind')}
        <label class="k-search k-push" style="flex:0 1 240px;min-height:40px">${ki('search', 16, 1.75)}<span class="k-hide">용어 검색</span><input type="search" data-in="o2lxq" value="${esc(X.q)}" placeholder="용어 · 영문 · 동의어"></label></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">용어</th><th scope="col">영문 표기</th><th scope="col">구분</th><th scope="col">연결 개념</th><th scope="col">관련 규칙</th><th scope="col">상태</th></tr></thead>
        <tbody>${shown.map(tr).join('') || '<tr><td colspan="6" class="mut">조건에 맞는 용어가 없습니다.</td></tr>'}</tbody></table></div>
      <p class="k-cf line">${shown.length} / ${pool.length}개 표시${pool.length > shown.length ? ` · <button class="k-lnk flat" data-act="o2lxmore">더 보기</button>` : ''} · Object · Entity는 ${known('objmgr') ? '<a href="#objmgr">오브젝트 관리</a>' : '오브젝트 관리'} · ${known('objects') ? '<a href="#objects">엔티티 관리</a>' : '엔티티 관리'}에서 봅니다</p></section>`;
    return `${head}${sel ? itemBar('term', sel.id, o2TermName(sel), sel.definition || sel.concept_label || '') : ''}${pend}${stats}${why}${X.imp ? o2LexImport() : ''}${conflicts}
      <div class="k-cols">${table}${o2TermSide(sel, st)}</div>
      ${rsel ? itemBar('termrel', rsel.id, O2_REL[rsel.kind][0], o2RelName(rsel)) : ''}${o2RelTable(rels, rpool, st)}${o2ChannelTable(chan)}${o2Naming(st)}
      ${kNext([['concepts', '용어 후보 승인'], ...(isOntoAdmin() ? [['settings', '명명 규칙']] : []), ['changes', '변경 요청으로 묶기'], ['search', '검색에서 확인']])}`;
  }

  function o2TermSide(r, st) {
    if (!r) return `<aside class="k-card pad" style="flex:2 1 340px"><p class="k-p s">용어를 고르면 정의와 표현 관계가 여기에 보입니다.</p></aside>`;
    const prop = r.concept.startsWith('property:') && S.mg.st && !S.mg.st.error ? S.mg.st.properties.find((p) => `property:${p.object}.${p.name}` === r.concept) : null;
    const values = prop && (prop.values || []).length ? `<div class="k-v" style="padding:12px 20px;border-bottom:1px solid var(--row)"><p class="k-s k-b" style="margin:0">값 · ${esc(prop.label || prop.name)}</p><div class="k-h g6">${prop.values.slice(0, 24).map((v) => `<span class="k-chip"><span class="k-code">${esc(v)}</span></span>`).join('')}</div></div>`
      : r.concept.startsWith('value:') ? `<div class="k-v" style="padding:12px 20px;border-bottom:1px solid var(--row)"><p class="k-s k-b" style="margin:0">표준 값</p><div class="k-h g6"><span class="k-chip"><span class="k-code">${esc(r.concept.split('=').pop())}</span></span></div></div>` : '';
    const mine = st.conflicts.filter((c) => c.terms.includes(r.id));
    const warn = r.status === 'review' || mine.length ? `<div class="k-v g4" style="margin:12px 20px 0;padding:12px;border-radius:10px;background:var(--warn-soft)"><p class="k-warn k-13" style="margin:0;font-weight:600">확인 필요</p>
      <p class="k-14" style="margin:0">${mine.length ? mine.map((c) => esc(c.text)).join('<br>') : '확인이 필요한 용어로 표시되어 있습니다. 정의와 표현 관계를 확인한 뒤 게시합니다.'}</p></div>` : '';
    const kv = (k, v) => (v ? `<div style="display:flex;justify-content:space-between;gap:12px"><span class="k-mut" style="flex:none">${k}</span><span class="k-r">${v}</span></div>` : '');
    const list = (xs) => (xs || []).map(esc).join(' · ');
    const publish = canEdit() && ['draft', 'review'].includes(r.status);
    return `<aside class="k-card" aria-labelledby="o2td" style="flex:2 1 340px;display:flex;flex-direction:column">
      <div class="k-v" style="padding:16px 20px;border-bottom:1px solid var(--row)"><p class="k-s" style="margin:0">용어 · ${esc(o2Bucket(r))}</p><h2 id="o2td" style="margin:0;font-size:20px;font-weight:600;overflow-wrap:anywhere">${esc(o2TermName(r))}</h2>
        <p class="k-i3 k-14" style="margin:0">${esc(r.definition || '정의 없음')}</p><div class="k-h g6">${r.module_label ? kChip(r.module_label) : ''}${o2TermChips(r)}</div></div>
      ${values}${warn}
      <div class="k-v k-14" style="padding:12px 20px">${kv('동의어', list(r.synonyms))}${kv('약어', list(r.abbreviations))}${kv('혼동주의', r.confusable.map((c) => `${esc(r.term)} ↔ ${esc(c.term)}`).join('<br>'))}${kv('쓰지 않는 표현', list(r.avoid))}
        ${kv('상위 · 하위', list([...r.broader, ...r.narrower]))}${kv('관련어', list(r.related))}${kv('채널 표기', Object.entries(r.channels || {}).map(([c, w]) => `${esc(c)} · ${esc(w)}`).join('<br>'))}${kv('숨은 표기', list(r.hidden))}
        ${kv('연결 개념', r.concept ? o2ConceptLink(r) : '미연결')}${kv('사용처', list(r.used_by))}${kv('출처', esc([r.source, r.cite].filter(Boolean).join(' · ')))}${kv('담당자', esc(r.owner))}</div>
      <div style="margin-top:auto;padding:12px 20px;border-top:1px solid var(--row);display:flex;justify-content:flex-end;gap:8px"><a class="k-btn" href="#changes">변경 요청</a>${publish ? `<button class="k-btn pri" data-act="o2lxpublish" data-id="${esc(r.id)}">게시</button>` : ''}</div></aside>`;
  }

  function o2RelTable(rels, pool, st) {
    const X = S.o2.lx, n = (k) => rels.filter((x) => x.kind === k).length;
    const shown = pool.slice(0, X.rn || O2_LX_STEP);
    const where = (r) => (o2IsDef(r) || r.concept ? o2ConceptLink(r) : `용어 ${esc(r.term)}`);
    const tr = (x) => `<tr class="${x.id === X.rsel ? 'on' : ''}" data-act="o2rlsel" data-id="${esc(x.id)}"><td><span class="k-chip${O2_REL[x.kind][1] ? ` ${O2_REL[x.kind][1]}` : ''}">${O2_REL[x.kind][0]}</span></td><td class="b">${esc(o2TermName(x.row))}</td><td>${esc(x.others.join(', '))}</td>
      <td class="i3">${x.note ? esc(x.note) : '<span class="k-mut">-</span>'}</td><td>${where(x.row)}</td><td>${x.row.status === 'review' ? '<span class="k-chip warn">확인 필요</span>' : ''}</td></tr>`;
    return `<section class="k-card" aria-labelledby="o2rel"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="o2rel">표현 관계</h2>
        ${o2Seg('관계', [['all', `전체 ${rels.length}`], ['confusable', `혼동주의 ${n('confusable')}`], ['broader', `상위 · 하위 ${n('broader')}`], ['avoid', `쓰지 않는 표현 ${n('avoid')}`], ['synonym', `동의어 ${n('synonym')}`]], X.rel, 'o2rlkind')}
        <label class="k-search k-push" style="flex:0 1 240px;min-height:40px">${ki('search', 16, 1.75)}<span class="k-hide">표현 관계 검색</span><input type="search" data-in="o2rlq" value="${esc(X.rq)}" placeholder="표준 용어 · 다른 표현"></label></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">관계</th><th scope="col">표준 용어</th><th scope="col">다른 표현</th><th scope="col">설명</th><th scope="col">정의 위치</th><th scope="col">확인</th></tr></thead>
        <tbody>${shown.map(tr).join('') || '<tr><td colspan="6" class="mut">조건에 맞는 표현 관계가 없습니다.</td></tr>'}</tbody></table></div>
      <p class="k-cf line">${shown.length} / ${pool.length}건 표시${pool.length > shown.length ? ' · <button class="k-lnk flat" data-act="o2rlmore">더 보기</button>' : ''} · 혼동주의는 비슷하지만 뜻이 다른 말, 쓰지 않는 표현은 표준 용어로 바꿔 쓸 말 · Object와 Entity의 동의어는 표현만 적고 정의는 정의 위치에서 봅니다</p></section>`;
  }

  function o2ChannelTable(chan) {
    if (!chan.length) return '';
    const X = S.o2.lx, shown = chan.slice(0, X.cn || O2_LX_STEP);
    const code = (r) => (r.concept.startsWith('value:') ? r.concept.split('=').pop() : r.english);
    return `<section class="k-card" aria-labelledby="o2cu"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="o2cu">고객 표기</h2><span class="k-chip">${chan.length}</span><span class="k-s">표준 용어를 채널에서 고객이나 담당자에게 답하는 말</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">영역</th><th scope="col">표준 용어</th><th scope="col">채널</th><th scope="col">표기</th><th scope="col">표준 값</th><th scope="col">확인</th></tr></thead>
        <tbody>${shown.map((c) => `<tr data-act="o2lxsel" data-id="${esc(c.row.id)}" data-all="1"><td>${esc(c.row.concept_of || c.row.concept_kind || '-')}</td><td>${esc(c.row.term)}</td><td>${esc(c.channel)}</td><td class="b">${esc(c.word)}</td><td class="k-code">${code(c.row) ? esc(code(c.row)) : '<span class="k-mut">-</span>'}</td><td>${c.row.status === 'review' ? '<span class="k-chip warn">확인 필요</span>' : ''}</td></tr>`).join('')}</tbody></table></div>
      <p class="k-cf line">${shown.length} / ${chan.length}건 표시${chan.length > shown.length ? ' · <button class="k-lnk flat" data-act="o2cnmore">더 보기</button>' : ''} · 고객에게는 고객 표기로 답하고 판정은 표준 값으로 합니다 · 표기는 용어 편집의 채널 표기에서 고칩니다</p></section>`;
  }

  // how names are written here, shown with names this ontology holds
  function o2Naming(st) {
    const named = st.rows.find((r) => r.english && !r.english.includes(':')), ext = st.rows.find((r) => /^[a-z0-9]+:/i.test(r.english));
    const box = (b, say) => `<div class="k-box k-13" style="flex:1 1 240px;line-height:1.55"><b>${b}</b><br>${say}</div>`;
    return `<section class="k-card pad k-wrap g16" aria-labelledby="o2nm" style="align-items:flex-start"><h2 class="k-h2" id="o2nm" style="flex:0 0 100%">명명 규칙</h2>
      ${box('한글@영문', named ? `예 · ${esc(o2TermName(named))}` : '용어에 영문 표기를 적으면 한글@영문으로 보입니다')}
      ${ext ? box(`기준 어휘에 없으면 ${esc(ext.english.split(':')[0])}: 확장`, `예 · ${esc(o2TermName(ext))}`) : ''}
      ${box('표현 관계 종류', '동의어 · 혼동주의 · 상위 · 하위 · 쓰지 않는 표현')}</section>`;
  }

  // a glossary brought in: a term list or a table of term pairs
  function o2LexImport() {
    const m = S.o2.lx.imp, r = m.report;
    const WORD = { added: '새 용어', updated: '고친 용어', synonym: '동의어', abbreviation: '약어', confusable: '혼동주의', linked: '정의 연결', unlinked: '정의 미연결', review: '확인 필요', skipped: '건너뜀', conflicts: '새 충돌' };
    const said = r ? Object.keys(WORD).filter((k) => (r[k] || []).length).map((k) => kChip(`${WORD[k]} ${r[k].length}`, ['unlinked', 'review', 'conflicts', 'skipped'].includes(k) ? 'warn' : 'ok')).join('') : '';
    return `<section class="k-card" id="o2imp"><div class="k-ch"><h2>가져오기</h2><span class="k-s">용어 목록이나 용어 짝 표(구분, 용어 A, 용어 B, 관계, 설명, 근거, 확인 필요)를 읽어 작성 중인 변경 요청에 담습니다</span><span class="k-push"><button class="k-lnk" data-act="o2lximpx">닫기</button></span></div>
      <div class="k-cb"><div class="k-g2"><label class="k-f">파일 · CSV · YAML · JSON<input class="k-in" type="file" id="o2lxfile" accept=".csv,.tsv,.yaml,.yml,.json,.txt" style="padding:6px 12px"><span class="k-hint">파일을 고르면 아래에 내용이 들어옵니다</span></label>
        <label class="k-f">자료 업로드에 올린 파일 경로 · 엑셀<input class="k-in" type="text" data-in="o2lxi" data-k="path" value="${esc(m.path)}" placeholder="예: 용어집.xlsx"><span class="k-hint">엑셀은 자료 업로드에 올린 뒤 경로를 적습니다</span></label>
        <label class="k-f k-full">내용<textarea class="k-in mono" rows="6" data-in="o2lxi" data-k="text" placeholder="구분,용어 A,용어 B,관계,설명">${esc(m.text)}</textarea></label></div>
        <div class="k-h"><button class="k-btn pri" data-act="o2lximprun"${m.busy ? ' disabled' : ''}>${m.busy ? '읽는 중' : '가져오기'}</button>${said}</div>
        ${r && (r.unlinked || []).length ? `<span class="k-s">정의 미연결 용어 · ${r.unlinked.slice(0, 8).map((u) => esc(u.term || u)).join(', ')}</span>` : ''}</div></section>`;
  }

  async function o2LexEdit(op, args) {
    S.lx.st = await api('lexicon/edit', { op, args });
    S.o2.lx.for = null;
    await loadManage();  // the edit waits in the workspace with the others
    S.o2.lx.for = S.mg.st;
    return S.lx.st;
  }

  screen('lexicon', {
    area: 'work', word: '용어사전', view: o2Lexicon,
    after: () => {
      const X = S.o2.lx;
      if (!S.mg.st && !S.mg.busy) loadManage();
      if (S.mg.st && X.for !== S.mg.st && !S.lx.busy) { X.for = S.mg.st; loadLexicon(); }  // the lexicon is read again whenever the definition moved
      else if (!S.lx.st && !S.lx.busy) loadLexicon();
    },
  });

  Object.assign(ACT, {
    o2lxsel: (t, ev) => { const a = ev && ev.target.closest('a'); if (a) { location.hash = a.getAttribute('href'); return; } S.lx.sel = t.dataset.id; if (t.dataset.all) { const r = S.lx.st.rows.find((x) => x.id === t.dataset.id); S.o2.lx.kind = r && o2IsDef(r) ? 'defs' : 'all'; S.o2.lx.q = ''; S.o2.lx.n = 9999; } render(); if (t.dataset.all) { const box = $('#o2gl'); if (box) box.scrollIntoView({ block: 'start' }); } },
    o2lxkind: (t) => { Object.assign(S.o2.lx, { kind: t.dataset.k, n: 0 }); S.lx.sel = ''; render(); },
    o2lxmore: () => { S.o2.lx.n = (S.o2.lx.n || O2_LX_STEP) + 20; render(); },
    o2rlsel: (t, ev) => { const a = ev && ev.target.closest('a'); if (a) { location.hash = a.getAttribute('href'); return; } S.o2.lx.rsel = t.dataset.id; render(); },
    o2rlkind: (t) => { Object.assign(S.o2.lx, { rel: t.dataset.k, rn: 0, rsel: '' }); render(); },
    o2rlmore: () => { S.o2.lx.rn = (S.o2.lx.rn || O2_LX_STEP) + 20; render(); },
    o2cnmore: () => { S.o2.lx.cn = (S.o2.lx.cn || O2_LX_STEP) + 20; render(); },
    o2lxpublish: async (t) => {
      try { await o2LexEdit('update_term', { id: t.dataset.id, status: 'active' }); toast('게시했습니다. 작성 중인 변경 요청에 담겼습니다.'); } catch (e) { fail(e); }
      render();
    },
    o2lximp: () => { S.o2.lx.imp = S.o2.lx.imp ? null : { name: '', text: '', path: '', report: null, busy: false }; render(); const box = $('#o2imp'); if (box) box.scrollIntoView({ block: 'nearest' }); },
    o2lximpx: () => { S.o2.lx.imp = null; render(); },
    o2lximprun: async () => {
      const m = S.o2.lx.imp;
      if (!m.text.trim() && !m.path.trim()) { toast('가져올 내용이 없습니다. 파일을 고르거나 내용을 붙여 넣어 주세요.', true); return; }
      m.busy = true; render();
      try {
        const r = await api('lexicon/import', m.path.trim() ? { path: m.path.trim(), name: m.name } : { text: m.text, name: m.name || 'glossary.csv' });
        m.report = r.report; S.lx.st = r; S.o2.lx.for = null;
        await loadManage(); S.o2.lx.for = S.mg.st;
        toast('용어집을 읽었습니다. 작성 중인 변경 요청에 담겼습니다.');
      } catch (e) { fail(e); }
      m.busy = false; render();
    },
  });
  const o2Refocus = (key) => { const box = $(`#main [data-in="${key}"]`); if (box) { const at = box.value.length; box.focus(); box.setSelectionRange(at, at); } };
  Object.assign(INPUT, {
    o2lxq: (t) => { Object.assign(S.o2.lx, { q: t.value, n: 0 }); S.lx.sel = ''; render(); o2Refocus('o2lxq'); },
    o2rlq: (t) => { Object.assign(S.o2.lx, { rq: t.value, rn: 0, rsel: '' }); render(); o2Refocus('o2rlq'); },
    o2lxi: (t) => { S.o2.lx.imp[t.dataset.k] = t.value; },
  });
  document.addEventListener('change', (ev) => {  // a glossary file picked: its text goes into the box to be read
    if (ev.target.id !== 'o2lxfile' || !S.o2.lx.imp || !ev.target.files[0]) return;
    const f = ev.target.files[0];
    f.text().then((text) => { Object.assign(S.o2.lx.imp, { name: f.name, text, path: '' }); if (S.tab === 'lexicon') render(); });
  });

  // ---- a term's own screens ---------------------------------------------------------------------------------------
  const o2LexLoad = async () => { if (!S.mg.st) await loadManage(); if (!S.lx.st || S.lx.st.error || S.o2.lx.for !== S.mg.st) { S.lx.st = await api('lexicon'); S.o2.lx.for = S.mg.st; } };
  const o2TermHistory = async (id, field) => {
    const r = await api(`ont2/term/history?id=${encodeURIComponent(id)}${field ? `&field=${field}` : ''}`);
    const WORD = { added: '추가', changed: '변경', removed: '삭제' };
    return r.entries.map((e) => ({ ver: e.version ? `v${e.version}` : '', mark: e.status_label, cp: e.change, at: e.at, who: e.by, deployed: e.deployed,
      say: (e.notes || []).map((n) => n.text).join(' · ') || e.reason || `${e.fields.map((f) => f.label).join(' · ') || '용어'} ${WORD[e.kind]}`,
      rows: e.fields.map((f) => ({ label: f.label, before: f.before, after: f.after })),
      all: Object.entries(e.after || e.before || {}).filter(([k, v]) => k !== 'id' && !(Array.isArray(v) ? !v.length : v && typeof v === 'object' ? !Object.keys(v).length : !v))
        .map(([k, v]) => ({ label: k, value: Array.isArray(v) ? v.map((x) => (x && x.term ? x.term : x)).join(', ') : v && typeof v === 'object' ? Object.entries(v).map(([a, b]) => `${a} = ${b}`).join(', ') : v })) }));
  };

  item('term', {
    word: '용어', under: 'lexicon', list: 'lexicon',
    hint: '용어사전에서 ‘+ 용어’를 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    load: o2LexLoad,
    find: (id) => S.lx.st.rows.find((r) => r.id === id) || null,
    code: o2TermName, name: (x) => x.definition || x.concept_label || '정의 없음',
    element: (x) => `term:${x.id}`,
    draft: (x) => (x ? { term: x.term, kind: x.kind, english: x.english, concept: x.concept, definition: x.definition, synonyms: x.synonyms.join(', '), abbreviations: x.abbreviations.join(', '),
      channels: Object.entries(x.channels || {}).map(([c, w]) => `${c}=${w}`).join('\n'), hidden: x.hidden.join(', '), owner: x.owner, status: x.status, source: x.source, cite: x.cite }
      : { term: '', kind: '', english: '', concept: '', definition: '', synonyms: '', abbreviations: '', channels: '', hidden: '', owner: '', status: 'draft', source: '', cite: '' }),
    form: (d, x) => {
      const st = S.lx.st, kinds = [...new Set(st.rows.map((r) => r.kind).filter(Boolean))];
      const c = st.concepts.find((y) => y.concept === d.concept);
      const prop = d.concept.startsWith('property:') && S.mg.st && !S.mg.st.error ? S.mg.st.properties.find((p) => `property:${p.object}.${p.name}` === d.concept) : null;
      const rules = x ? (x.used_by || []).filter((u) => /^(결정|함수) /.test(u)).map((u) => u.replace(/^\S+ /, '')) : [];
      const inp = (k, word, hint = '', hold = '') => `<label class="k-f">${word}<input class="k-in" type="text" data-in="itf" data-k="${k}" value="${esc(d[k])}" placeholder="${esc(hold)}">${hint ? `<span class="k-hint">${hint}</span>` : ''}</label>`;
      return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">
          ${inp('term', '용어')}
          <label class="k-f">구분<input class="k-in" type="text" data-in="itf" data-k="kind" value="${esc(d.kind)}" list="o2kinds" placeholder="예: 속성 · 값"><datalist id="o2kinds">${kinds.map((k) => `<option value="${esc(k)}">`).join('')}</datalist></label>
          ${inp('english', '영문 표기', '접두어가 없으면 기준 어휘의 표준')}
          <label class="k-f">연결 개념<select class="k-in" data-in="itf" data-k="concept" data-re><option value="">미연결</option>${st.concepts.map((y) => `<option value="${esc(y.concept)}"${y.concept === d.concept ? ' selected' : ''}>${esc(y.kind_label)} · ${esc(y.label)}${y.of ? ` (${esc(y.of)})` : ''}</option>`).join('')}</select></label>
          <div class="k-full"><label class="k-f">정의<textarea class="k-in" rows="3" data-in="itf" data-k="definition">${esc(d.definition)}</textarea></label></div>
          ${inp('synonyms', '동의어', '쉼표로 구분')}
          ${prop && (prop.values || []).length ? `<label class="k-f">값<input class="k-in" type="text" value="${esc(`${prop.label || prop.name} · ${prop.values.join(' / ')}`)}" readonly><span class="k-hint">연결 개념의 허용값</span></label>` : ''}
          ${rules.length ? `<label class="k-f">관련 규칙<input class="k-in" type="text" value="${esc(rules.join(', '))}" readonly><span class="k-hint">연결 개념을 읽는 규칙</span></label>` : ''}
          ${inp('source', '출처')}
        </div></div></section>
        <section class="k-card"><div class="k-ch"><h2>표기 · 관리</h2><span class="k-s">${c ? `${esc(c.kind_label)} · ${esc(c.label)}에 연결` : '연결 개념 없음'}</span></div><div class="k-cb"><div class="k-g2">
          ${inp('abbreviations', '약어', '쉼표로 구분')}${inp('hidden', '숨은 표기', '검색에만 쓰는 표기 · 쉼표로 구분')}
          <div class="k-full"><label class="k-f">채널 표기<textarea class="k-in" rows="2" data-in="itf" data-k="channels" placeholder="고객=주문완료">${esc(d.channels)}</textarea><span class="k-hint">한 줄에 하나 · 채널=표기 · 용어사전의 고객 표기에 보입니다</span></label></div>
          ${inp('owner', '담당자')}
          <label class="k-f">상태<select class="k-in" data-in="itf" data-k="status" data-re>${Object.entries(TERM_STATUS).map(([k, [, w]]) => `<option value="${k}"${(d.status || 'active') === k ? ' selected' : ''}>${w}</option>`).join('')}</select></label>
          ${inp('cite', '근거')}
        </div></div></section>`;
    },
    checks: (d, x) => {
      const st = S.lx.st, mine = [d.term, d.english, ...csv(d.synonyms), ...csv(d.abbreviations)].map(o2Norm).filter(Boolean);
      const same = st.rows.filter((r) => (!x || r.id !== x.id) && r.concept !== d.concept && [r.term, r.english, ...r.synonyms, ...r.abbreviations].map(o2Norm).some((w) => w && mine.includes(w)));
      const defs = S.mg.st && !S.mg.st.error ? [...S.mg.st.objects.map((o) => [`object:${o.name}`, o.label]), ...S.mg.st.areas.map((a) => [`area:${a.name}`, a.label])] : [];
      const clash = /^(area|object):/.test(d.concept) ? [] : defs.filter(([, label]) => o2Norm(label) === o2Norm(d.term));  // a term that names an Object or an Entity is that name
      return [!String(d.term).trim() ? { say: '용어가 있어야 합니다', tone: 'bad' } : same.length ? { say: `같은 표기를 쓰는 용어 있음 · ${same.slice(0, 3).map((r) => r.term).join(', ')}`, sub: '한 용어에만 남기거나 혼동주의로 잇습니다', tone: 'warn' } : { say: '같은 표기의 용어 없음', tone: 'ok' },
        clash.length ? { say: 'Object · Entity 이름과 겹침', sub: '그 정의에 연결하거나 다른 말로 적습니다', tone: 'warn' } : { say: 'Object · Entity 이름과 겹치지 않음', tone: 'ok' },
        d.concept ? { say: '연결 개념 있음', tone: 'ok' } : { say: '연결 개념 없음 · 정의 미연결 용어로 남습니다', tone: 'note' },
        ...(d.status === 'review' ? [{ say: '확인 필요로 표시됨', tone: 'warn', word: '확인 필요' }] : [])];
    },
    valid: (d) => (String(d.term).trim() ? '' : '용어를 입력해 주세요.'),
    save: async (d, x) => {
      const channels = Object.fromEntries(String(d.channels || '').split('\n').map((l) => l.split('=')).filter((p) => p.length >= 2 && p[0].trim() && p.slice(1).join('=').trim()).map((p) => [p[0].trim(), p.slice(1).join('=').trim()]));
      const args = { term: d.term.trim(), kind: d.kind.trim(), english: d.english.trim(), concept: d.concept, definition: d.definition.trim(), synonyms: csv(d.synonyms), abbreviations: csv(d.abbreviations),
        hidden: csv(d.hidden), channels, owner: d.owner.trim(), status: d.status || 'active', source: d.source.trim(), cite: d.cite.trim() };
      const r = await o2LexEdit(x ? 'update_term' : 'add_term', x ? { id: x.id, ...args } : args);
      S.lx.sel = r.edit.target.replace(/^term:/, '');
      return { element: r.edit.target };
    },
    uses: async (x) => {
      const out = [], by = {};
      (x.used_by || []).forEach((u) => { const k = u.split(' ')[0] === '검증' ? '검증 질문' : u.split(' ')[0]; (by[k] = by[k] || []).push(u.replace(/^(검증 질문|\S+) /, '')); });
      const to = { '검증 질문': 'check', 질의: 'query', 결정: 'semrules', 액션: 'actions', 함수: 'semrules', 역할: 'roles' };
      Object.entries(by).forEach(([k, names]) => out.push({ say: `${k} ${names.length}개`, sub: `${names.slice(0, 3).join(', ')}${names.length > 3 ? ` 외 ${names.length - 3}` : ''} · 이 용어의 표기로 찾습니다`, href: to[k] && known(to[k]) ? to[k] : '' }));
      const others = S.lx.st.rows.filter((r) => r.id !== x.id && [...r.confusable.map((c) => c.term), ...r.related, ...r.broader, ...r.narrower].some((w) => o2Norm(w) === o2Norm(x.term)));
      if (others.length) out.push({ say: `표현 관계 ${others.length}건`, sub: `${others.slice(0, 3).map((r) => r.term).join(', ')}이(가) 이 용어를 가리킵니다`, href: 'lexicon' });
      return out;
    },
    remove: async (x) => { await o2LexEdit('delete_term', { id: x.id }); S.lx.sel = ''; },
    history: (x) => o2TermHistory(x.id, ''),
  });

  // ---- an expression relation's own screens: it is one field of a term ----------------------------------------------
  function o2RelArgs(row, kind, others, note, old) {
    const drop = (old || []).map(o2Norm), fresh = others.filter((w, i) => w && others.findIndex((y) => o2Norm(y) === o2Norm(w)) === i);
    if (kind === 'confusable') return { confusable: [...row.confusable.filter((c) => !drop.includes(o2Norm(c.term)) && !fresh.some((w) => o2Norm(w) === o2Norm(c.term))), ...fresh.map((w) => (note ? { term: w, note } : { term: w }))] };
    const f = O2_REL_FIELD[kind];
    return { [f]: [...row[f].filter((w) => !drop.includes(o2Norm(w)) && !fresh.some((y) => o2Norm(y) === o2Norm(w))), ...fresh] };
  }

  item('termrel', {
    word: '표현 관계', under: 'lexicon', list: 'lexicon',
    hint: '용어사전에서 ‘+ 표현 관계’를 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    load: o2LexLoad,
    find: (id) => o2Rels(S.lx.st).find((x) => x.id === id) || null,
    code: (x) => x.row.term, name: o2RelName,
    element: (x) => `term:${x.row.id}`,
    draft: (x) => (x ? { kind: x.kind, term: x.row.id, others: x.others.join(', '), note: x.note, review: x.row.status === 'review' ? '1' : '' } : { kind: 'confusable', term: '', others: '', note: '', review: '' }),
    form: (d, x) => {
      const st = S.lx.st, row = st.rows.find((r) => r.id === d.term);
      return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">관계<select class="k-in" data-in="itf" data-k="kind" data-re${x ? ' disabled' : ''}>${Object.entries(O2_REL).map(([k, [w]]) => `<option value="${k}"${d.kind === k ? ' selected' : ''}>${w}</option>`).join('')}</select></label>
        <label class="k-f">표준 용어<select class="k-in" data-in="itf" data-k="term" data-re${x ? ' disabled' : ''}><option value="">선택</option>${st.rows.map((r) => `<option value="${esc(r.id)}"${r.id === d.term ? ' selected' : ''}>${esc(o2TermName(r))}${o2IsDef(r) ? ` · ${esc(r.concept_kind)}` : ''}</option>`).join('')}</select><span class="k-hint">용어 · Object · Entity · Property에서 선택 · 목록에 없으면 용어를 먼저 추가합니다</span></label>
        <label class="k-f k-full">다른 표현<input class="k-in" type="text" data-in="itf" data-k="others" value="${esc(d.others)}"><span class="k-hint">여러 개면 쉼표로 구분${d.kind === 'broader' ? ' · 표준 용어보다 넓은 말을 적습니다' : ''}</span></label>
        ${d.kind === 'confusable' ? `<div class="k-full"><label class="k-f">설명<textarea class="k-in" rows="3" data-in="itf" data-k="note">${esc(d.note)}</textarea><span class="k-hint">두 말이 어떻게 다른지 적습니다</span></label></div>` : ''}
        <label class="k-f">정의 위치<input class="k-in" type="text" value="${esc(row ? (row.concept ? `${row.concept_kind} ${row.concept_of ? `${row.concept_of} › ` : ''}${row.concept_label || ''}` : `용어 ${row.term}`) : '')}" readonly><span class="k-hint">Object · Entity의 동의어는 정의를 적지 않고 위치만 가리킴</span></label>
        <label class="k-f">확인 필요<select class="k-in" data-in="itf" data-k="review" data-re><option value="1"${d.review ? ' selected' : ''}>예 · 결정이 필요함</option><option value=""${d.review ? '' : ' selected'}>아니오</option></select><span class="k-hint">표준 용어에 표시됩니다</span></label>
      </div></div></section>`;
    },
    checks: (d, x) => {
      const st = S.lx.st, row = st.rows.find((r) => r.id === d.term), others = csv(d.others).map(o2Norm);
      if (!row) return [{ say: '표준 용어를 고릅니다', tone: 'note' }];
      const syn = st.rows.filter((r) => r.id !== row.id && r.synonyms.some((w) => others.includes(o2Norm(w))));
      const avoid = st.rows.filter((r) => r.avoid.some((w) => others.includes(o2Norm(w))) && !(d.kind === 'avoid' && r.id === row.id));
      const both = d.kind === 'confusable' ? row.synonyms.filter((w) => others.includes(o2Norm(w))) : d.kind === 'synonym' ? row.confusable.filter((c) => others.includes(o2Norm(c.term))).map((c) => c.term) : [];
      return [!others.length ? { say: '다른 표현이 있어야 합니다', tone: 'bad' } : others.includes(o2Norm(row.term)) ? { say: '표준 용어와 같은 말은 다른 표현이 될 수 없습니다', tone: 'bad' }
        : syn.length ? { say: `같은 표현이 다른 표준 용어의 동의어임 · ${syn.slice(0, 3).map((r) => r.term).join(', ')}`, tone: 'warn' } : { say: '같은 표현이 다른 표준 용어의 동의어가 아님', tone: 'ok' },
        avoid.length ? { say: `쓰지 않는 표현 목록과 겹침 · ${avoid.slice(0, 3).map((r) => r.term).join(', ')}`, tone: 'warn' } : { say: '쓰지 않는 표현 목록과 겹치지 않음', tone: 'ok' },
        ...(both.length ? [{ say: `동의어이면서 혼동주의일 수 없습니다 · ${both.join(', ')}`, tone: 'bad' }] : []),
        ...(d.review ? [{ say: '확인 필요로 표시됨 · 정의 결정 대기', tone: 'warn', word: '확인 필요' }] : [])];
    },
    valid: (d) => (!d.term ? '표준 용어를 골라 주세요.' : !csv(d.others).length ? '다른 표현을 입력해 주세요.' : ''),
    save: async (d, x) => {
      const row = S.lx.st.rows.find((r) => r.id === d.term);
      const args = { id: row.id, ...o2RelArgs(row, d.kind, csv(d.others), String(d.note || '').trim(), x ? x.others : []) };
      if (d.review && row.status !== 'review') args.status = 'review';
      if (!d.review && row.status === 'review') args.status = 'active';
      await o2LexEdit('update_term', args);
      S.o2.lx.rsel = '';
      return { element: `term:${row.id}` };
    },
    uses: async (x) => [{ say: `표준 용어 ${x.row.term}`, sub: `${O2_REL[x.kind][0]} ${x.others.length}개가 이 용어에 달려 있습니다. 삭제하면 질문과 문서에서 이 표현으로 찾지 못합니다`, href: '' }],
    remove: async (x) => { await o2LexEdit('update_term', { id: x.row.id, ...o2RelArgs(x.row, x.kind, [], '', x.others) }); S.o2.lx.rsel = ''; },
    history: (x) => o2TermHistory(x.row.id, O2_REL_FIELD[x.kind]),
  });
