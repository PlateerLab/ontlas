  // ---- BND-05 Entity Binding -------------------------------------------------------------------------------------
  // One Entity at a time: the table it reads, its key, and which column each Property reads. What is changed here waits
  // in the screen (S.bnd.bind.d) until 저장 · 변경 요청에 추가, which makes the edits the workspace keeps.
  const BND_BIND_LEAD = 'Entity와 Property를 테이블과 컬럼에 연결합니다.';
  const BND_OBJ = '<span class="k-chip dk">Object</span>';

  const bndStored = (m, name) => bndOwn(m, name).filter((p) => !p.expr);
  // how many of an Entity's stored Properties read a column that is there (or, with no source, that is written down)
  const bndBound = (m, o) => (o.table ? bndStored(m, o.name).filter((p) => ['ok', 'spec'].includes(bndState(m, o, p))).length : 0);
  function bndBindDraft(o) {
    const B = S.bnd.bind;
    if (!B.d || B.d.entity !== o.name) B.d = { entity: o.name, table: o.table || '', cols: {}, add: {} };
    return B.d;
  }
  const bndBindDirty = (o, d) => d.table !== (o.table || '') || Object.keys(d.cols).length > 0 || Object.keys(d.add).length > 0;
  // the Entities whose rows keep an Entity's history: its values over time (series) or rows valid for a time (period)
  const bndHists = (name) => ((S.bnd.cols && S.bnd.cols.hist) || []).filter((h) => h.owner === name);
  // a relation's table and the two columns that hold its ends, as its definition says them
  function bndLinkRow(m, l, by) {
    const s = bndObj(m, l.source), t = bndObj(m, l.target);
    const many = l.cardinality === 'one_to_many';
    const table = l.via ? (l.via.table || '') : ((many ? t : s) || {}).table || '';
    const colOf = (o, prop) => { const p = o && m.properties.find((x) => x.object === o.name && x.name === prop); return p ? bndCol(p) : prop; };
    const on = Array.isArray(l.on) ? l.on : null;
    const a = l.via ? (l.via.source || l.via.from || '') : on ? colOf(s, on[0]) : '';
    const b = l.via ? (l.via.target || l.via.to || '') : on ? colOf(t, on[1]) : '';
    const found = by[`link:${l.name}`] || [];
    const mark = !(s && s.table) || !(t && t.table) ? ['', '테이블 미지정'] : !on && !l.via ? ['', '소스 없음'] : found.length ? ['warn', FINDING[found[0].kind] || found[0].kind] : ['ok', '연결됨'];
    return { l, s, t, table, a, b, mark, bound: mark[0] === 'ok' };
  }

  function bndBindTree(m, sel) {
    const B = S.bnd.bind, q = B.q.trim().toLowerCase();
    const hit = (o) => !q || (o.label || '').toLowerCase().includes(q) || o.name.toLowerCase().includes(q);
    const groups = bndAreas(m).map((a) => {
      const list = a.objects.filter(hit);
      if (!list.length) return '';
      const open = q ? true : B.fold[a.name] === undefined ? (a.objects.some((o) => o.name === sel) || a.objects.some((o) => o.table)) : !B.fold[a.name];
      const n = a.objects.filter((o) => o.table).length;
      const rows = open ? `<div class="bnd-ents" role="group" aria-label="${esc(a.label)}의 Entity">${list.map((o) => { const total = bndStored(m, o.name).length;
        return `<button class="bnd-enta${o.name === sel ? ' on' : ''}" data-act="bndBindSel" data-name="${esc(o.name)}"${o.name === sel ? ' aria-current="true"' : ''}><span>${esc(bndEnt(o))}</span><span class="n${o.table ? ' b' : ''}">${o.table ? `${bndBound(m, o)} / ${total}` : '-'}</span></button>`; }).join('')}</div>` : '';
      return `<button class="bnd-area" data-act="bndBindFold" data-a="${esc(a.name)}" aria-expanded="${open}">${ki(open ? 'chevD' : 'chevR', 16, 1.75)}${a.name ? BND_OBJ : ''}<span class="k-cut">${esc(a.name ? `${a.label}@${a.name}` : a.label)}</span><span class="n">${n} / ${a.objects.length}</span></button>${rows}`;
    }).join('');
    return `<nav class="bnd-tree" aria-label="Object별 Entity"><label class="bnd-find">${ki('search', 16, 1.75)}<span class="k-hide">Entity 검색</span><input type="search" placeholder="Entity 검색" data-in="bndBindQ" value="${esc(B.q)}"></label>
      <div id="bndtree">${groups || '<p class="k-s" style="margin:8px">검색 결과가 없습니다.</p>'}</div></nav>`;
  }

  // the Entity's own card: the table, the key, and each column with the Property that reads it
  function bndBindCard(m, o, by) {
    const B = S.bnd.bind, d = bndBindDraft(o), on = !noSource(), src = S.st.source || {};
    const real = d.table ? bndTable(m, d.table) : null;
    const props = bndStored(m, o.name), dirty = bndBindDirty(o, d);
    const colOf = (p) => (p.name in d.cols ? d.cols[p.name] || p.name : bndCol(p));
    const key = m.properties.find((p) => p.object === o.name && p.name === o.key) || props.find((p) => p.key);
    const links = m.links.filter((l) => l.source === o.name || l.target === o.name);
    const area = o.area ? m.areas.find((a) => a.name === o.area) : null;
    const status = !d.table ? ['', '테이블 미지정'] : !on ? ['b', 'L2 · 명세'] : real ? ['ok', 'L2 · 실제 스키마'] : ['warn', '테이블 없음'];
    const head = `<p class="k-h g6 k-s" style="margin:0">${area ? `${BND_OBJ}<a class="k-ink k-b" href="#objmgr?area=${encodeURIComponent(area.name)}">${esc(`${area.label || area.name}@${area.name}`)}</a><span aria-hidden="true">›</span>` : ''}<span class="bnd-ent">Entity</span><span>${esc(bndEnt(o))}</span></p>
      <div class="k-pha"><h2 class="bnd-h" id="bnd-bd-h">${esc(bndEnt(o))} Binding</h2><span class="k-chip${status[0] ? ` ${status[0]}` : ''}">${status[1]}</span></div>
      <div class="k-seg self" role="tablist" aria-label="Binding 종류"><button type="button" role="tab" aria-selected="true" class="on">기본 Binding</button><button type="button" role="tab" aria-selected="false" data-act="bndBindPast"${bndHists(o.name).length ? '' : ' disabled'}>이력 Binding ${bndHists(o.name).length}</button><button type="button" role="tab" aria-selected="false" data-act="bndBindRel">Relation Binding ${links.length}</button></div>`;
    const tables = m.sources.source.tables;
    const tableField = tables.length ? `<select class="k-in" data-in="bndBindTable" aria-label="테이블"${canEdit() ? '' : ' disabled'}><option value="">테이블 없음</option>${tables.map((t) => `<option value="${esc(t.table)}"${t.table === d.table ? ' selected' : ''}>${esc(t.table)}${t.objects.filter((x) => x !== o.name).length ? ` · ${esc(t.objects.filter((x) => x !== o.name).map((x) => (bndObj(m, x) || {}).label || x).join(', '))}` : ''}</option>`).join('')}${d.table && !real ? `<option value="${esc(d.table)}" selected>${esc(d.table)} · 소스에 없음</option>` : ''}</select>`
      : `<input class="k-in mono" type="text" data-in="bndBindTable" value="${esc(d.table)}" placeholder="테이블 이름" aria-label="테이블"${canEdit() ? '' : ' disabled'}>`;
    const step1 = `<div class="k-h base"><span class="k-num">1</span><h3 class="bnd-step">소스</h3></div>
      <div class="k-wrap"><label class="k-f" style="flex:2 1 240px">데이터 소스<select class="k-in" disabled><option>${esc(on ? `${(S.st.origin || {}).detail || src.name} · ${BACKEND_KIND[src.kind] || src.kind} · 연결됨` : '미연결')}</option></select></label>
        <label class="k-f" style="flex:2 1 200px">테이블${tableField}</label></div>`;
    const save = `${dirty ? '<button class="k-btn" data-act="bndBindReset">되돌리기</button>' : ''}<button class="k-btn pri" data-act="bndBindSave"${dirty && !B.saving ? '' : ' disabled'}>${B.saving ? '저장 중' : '저장 · 변경 요청에 추가'}</button>`;
    if (!d.table) return `<section class="k-card pad k-navs" aria-labelledby="bnd-bd-h">${head}${step1}<p class="k-note">테이블이 지정되지 않았습니다.</p>${canEdit() && dirty ? `<div class="k-h end">${save}</div>` : ''}</section>`;
    const keyCols = key ? (key.name in d.cols ? [d.cols[key.name] || key.name] : bndCols(key)) : [];
    const dup = (by[`object:${o.name}`] || []).concat(key ? by[`property:${o.name}.${key.name}`] || [] : []).find((f) => f.kind === 'key');
    const step2 = `<div class="k-h base"><span class="k-num">2</span><h3 class="bnd-step">Entity 키</h3><span class="k-s">문자열 · 정수 컬럼</span></div>
      <div class="k-pha bnd-key">${keyCols.map((c) => `<span class="k-chip w"><span class="k-code">${esc(c)}</span></span>`).join('<span class="k-mut">+</span>') || '<span class="k-s">키 Property 없음</span>'}${key ? `${ki('arrow', 16, 1.75)}<span class="k-b"><span class="k-code">${esc(key.name)}</span> · ${esc(key.label || key.name)}</span>` : ''}
        <span class="k-push k-s">${!on ? '유일성 검사 · 미연결' : dup ? '<span class="k-warn">키 중복</span>' : bndChecked() ? '유일성 확인됨' : '유일성 검사 전'}</span></div>`;
    // rows: the source's columns when its table is known, the Properties when it is only named
    const typeWord = (p) => `${TYPE_WORD[p.type] || p.type} · ${esc(p.label || p.name)}`;
    const how = (p) => (key && p.name === key.name ? (keyCols.length > 1 ? `키 ${keyCols.length}컬럼` : '키') : p.transform ? '변환식' : (p.values || []).length ? '코드 → 값' : '컬럼 그대로');
    let rows = '', bound = 0, wait = 0, out = 0, plus = 0, total = 0;
    const free = () => props.filter((p) => !real || !real.columns.some((c) => c.name.toLowerCase() === colOf(p).toLowerCase()));
    if (real) {
      total = real.columns.length;
      rows = real.columns.map((c) => {
        const mine = props.filter((p) => colOf(p).toLowerCase() === c.name.toLowerCase());
        const p = mine.find((x) => x.name in d.cols) || mine[0], adding = !!d.add[c.name];
        const bad = p ? (by[`property:${o.name}.${p.name}`] || [])[0] : null;
        const mark = adding ? ['b', '추가 예정'] : !p ? ['', '제외'] : bad ? ['warn', FINDING[bad.kind] || '컬럼 확인'] : ['ok', '연결됨'];
        if (adding) plus += 1; else if (p && !bad) bound += 1; else if (p) wait += 1; else out += 1;
        const opts = `${p ? '' : `<option value=""${adding ? '' : ' selected'}>연결 안 함</option><option value="+"${adding ? ' selected' : ''}>새 Property 추가</option>`}${p ? `<option value="${esc(p.name)}" selected>${esc(p.name)}</option>` : ''}${free().filter((x) => !p || x.name !== p.name).map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('')}`;
        return `<tr><td class="nw"><span class="k-code">${esc(c.name)}</span><br><span class="k-s">${esc(c.type || '')}${real.key.includes(c.name) ? ' · 키' : ''}</span></td><td class="bnd-arrow">${ki('arrow', 16, 1.75)}</td>
          <td><select class="bnd-sel" data-in="bndBindProp" data-c="${esc(c.name)}" aria-label="${esc(c.name)}의 Property"${canEdit() ? '' : ' disabled'}>${opts}</select>${p ? `<span class="k-s" style="display:block;margin-top:4px">${typeWord(p)}</span>` : ''}</td>
          <td class="i3 nw">${p ? how(p) : '-'}</td><td class="nw"><span class="k-chip${mark[0] ? ` ${mark[0]}` : ''}">${esc(mark[1])}</span></td></tr>`;
      }).join('');
    } else {
      total = props.length;
      rows = props.map((p) => {
        if (on) wait += 1; else bound += 1;
        return `<tr><td><input class="k-in sm mono" type="text" data-in="bndBindCol" data-p="${esc(p.name)}" value="${esc(colOf(p))}" aria-label="${esc(p.name)}의 소스 컬럼"${canEdit() && bndCols(p).length < 2 ? '' : ' disabled'}></td><td class="bnd-arrow">${ki('arrow', 16, 1.75)}</td>
          <td><span class="k-code k-ink">${esc(p.name)}</span><span class="k-s" style="display:block;margin-top:4px">${typeWord(p)}</span></td><td class="i3 nw">${how(p)}</td><td class="nw"><span class="k-chip ${on ? 'warn' : 'b'}">${on ? '테이블 없음' : '명세'}</span></td></tr>`;
      }).join('');
    }
    const loose = real ? free() : [];
    const calc = bndOwn(m, o.name).filter((p) => p.expr);
    const step3 = `<div class="k-h base"><span class="k-num">3</span><h3 class="bnd-step">Property ↔ 컬럼</h3></div>
      <div class="k-x bnd-box"><table class="k-t s"><thead><tr><th scope="col">소스 컬럼</th><th scope="col" class="bnd-arrow"><span class="k-hide">방향</span></th><th scope="col">Property · 타입</th><th scope="col">변환</th><th scope="col">상태</th></tr></thead><tbody>${rows || '<tr><td colspan="5" class="mut">컬럼 Property가 없습니다.</td></tr>'}</tbody></table></div>
      ${loose.length ? `<div class="k-pha"><span class="k-s">미연결 Property ${loose.length}</span>${loose.map((p) => `<span class="k-chip"><span class="k-code">${esc(p.name)}</span>${esc(p.label || '')}</span>`).join('')}</div>` : ''}
      ${calc.length ? `<div class="k-pha"><span class="k-s">계산 Property ${calc.length}</span>${calc.map((p) => `<span class="k-chip dash"><span class="k-code">${esc(p.name)}</span>${esc(p.label || '')}</span>`).join('')}</div>` : ''}
      <div class="k-pha" style="padding-top:12px;border-top:1px solid var(--row)"><span class="k-s">${real ? `컬럼 ${total}개 · 연결 ${bound} · 컬럼 확인 ${wait}${plus ? ` · 추가 예정 ${plus}` : ''} · 제외 ${out}` : `Property ${total}개 · ${on ? '소스 테이블 없음' : '명세'}`}</span>
        ${canEdit() ? `<span class="k-wrap g8 k-push">${real && out ? `<button class="k-btn" data-act="bndBindAddAll">${ki('plus', 16, 1.75)}컬럼에서 Property 추가</button>` : ''}${save}</span>` : ''}</div>`;
    return `<section class="k-card pad k-navs" aria-labelledby="bnd-bd-h">${head}${step1}${step2}${step3}</section>`;
  }

  function bndBindChecks(m, o, by) {
    const on = !noSource(), t = o.table ? bndTable(m, o.table) : null, props = bndStored(m, o.name), list = [];
    const key = m.properties.find((p) => p.object === o.name && p.name === o.key);
    const add = (ok, say, sub) => list.push({ ok, say, sub });
    if (!o.table) return list;
    if (key) {
      const cols = bndCols(key).map((c) => ({ name: c, real: t ? t.columns.find((x) => x.name.toLowerCase() === c.toLowerCase()) : null }));
      if (t && cols.every((c) => c.real)) { const good = cols.every((c) => ['string', 'integer'].includes(sqlType(c.real.type))); add(good, good ? '키 컬럼이 문자열 · 정수' : '키 컬럼이 문자열 · 정수가 아님', cols.map((c) => `${c.name} ${c.real.type || ''}`.trim()).join(' · ')); }
      else add(!t, t ? '키 컬럼이 테이블에 없음' : '키 Property가 컬럼에 연결됨', cols.map((c) => c.name).join(' · '));
    } else add(false, '키 Property가 없음', '');
    const typed = props.flatMap((p) => (by[`property:${o.name}.${p.name}`] || []).filter((f) => f.kind === 'type'));
    if (on && bndChecked()) add(!typed.length, typed.length ? `타입이 맞지 않는 Property ${typed.length}개` : '타입 호환', typed.length ? typed.map((f) => f.detail).join(' · ') : `연결 Property ${bndBound(m, o)}개 타입 일치`);
    const lost = t ? props.filter((p) => bndState(m, o, p) === 'missing') : [];
    const must = lost.filter((p) => p.required || p.key);
    if (must.length) add(false, `컬럼 미확인 필수 Property ${must.length}개`, must.map((p) => p.name).join(' · '));
    else if (lost.length) add(false, `컬럼이 없는 Property ${lost.length}개`, lost.map((p) => p.name).join(' · '));
    else if (t) add(true, '모든 Property 컬럼 확인됨', `${o.table} · ${t.columns.length}컬럼`);
    m.links.filter((l) => (l.source === o.name || l.target === o.name) && !l.on && !l.via).forEach((l) => add(false, `Relation ${l.name} 소스 없음`, '연결 테이블 미지정'));
    // a missing column is said once, by the line above; the check's other findings each get a line
    [`object:${o.name}`, ...props.map((p) => `property:${o.name}.${p.name}`)].flatMap((el) => by[el] || []).filter((f) => f.kind !== 'type' && !(t && f.kind === 'column')).forEach((f) => add(false, `${FINDING[f.kind] || f.kind} · ${f.element.split(':')[1]}`, f.detail));
    return list;
  }

  function bndBindPreview(o) {
    const B = S.bnd.bind, on = !noSource();
    if (!on) return '<div class="bnd-prev"><p class="k-b k-14" style="margin:0">데이터 미리보기</p><p class="k-s" style="margin:0">데이터 소스 미연결</p><a class="k-push k-13" href="#db">데이터 소스 연결</a></div>';
    const p = B.prof && B.prof.name === o.name && B.prof.sig === bndSig() ? B.prof : null;
    if (!p || p.busy) return '<div class="bnd-prev"><p class="k-b k-14" style="margin:0">데이터 미리보기</p><p class="k-s" style="margin:0">불러오는 중입니다.</p></div>';
    if (!p.ok) return `<div class="bnd-prev"><p class="k-b k-14" style="margin:0">데이터 미리보기</p><p class="k-s" style="margin:0">${esc(p.error || '')}</p></div>`;
    const keyStat = p.stats.find((s) => s.name === o.key);
    const empty = p.stats.filter((s) => s.empty > 0).sort((a, b) => b.empty - a.empty).slice(0, 3);
    return `<div class="bnd-prev on"><div class="k-pha" style="padding:12px"><p class="k-b k-14" style="margin:0">데이터 미리보기</p><span class="k-s">${show(p.total)}행 중 ${Math.min(5, p.rows.length)}행</span>
        ${keyStat ? `<span class="k-chip ${keyStat.distinct === p.total ? 'ok' : 'warn'}">${keyStat.distinct === p.total ? '키 중복 없음' : `키 중복 ${show(p.total - keyStat.distinct)}`}</span>` : ''}
        ${empty.length ? `<span class="k-s">빈 값 ${empty.map((s) => `${esc(s.label)} ${Math.round(s.empty * 100)}%`).join(' · ')}</span>` : '<span class="k-s">빈 값 없음</span>'}
        <a class="k-push k-13" href="#records?type=${encodeURIComponent(o.name)}">레코드 탐색</a></div>
      <div class="k-x"><table class="k-t s"><thead><tr>${p.stats.map((s) => `<th scope="col">${esc(s.label)}</th>`).join('')}</tr></thead><tbody>${p.rows.slice(0, 5).map((r) => `<tr>${r.map((v) => `<td class="nw">${show(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`;
  }

  // where a finding is mended: a Property's column on its Mapping, an Entity's table on its Binding, a Relation on its form
  const bndFixHref = (el) => { const [kind, ...rest] = el.split(':'), id = rest.join(':');
    return kind === 'property' ? itemHref('map', 'form', id) : kind === 'object' ? itemHref('binding', 'form', id) : kind === 'link' && ITEM.relation ? itemHref('relation', 'form', id) : ''; };

  function bndBindView() {
    const wait = bndWait('Entity Binding', BND_BIND_LEAD);
    if (wait) return wait;
    const m = bndM(), B = S.bnd.bind, by = bndFound(), on = !noSource();
    const row = itemParam('row').split(':'), about = row[0] === 'bind' && ['object', 'property'].includes(row[1]) ? (row[2] || '').split('.')[0] : '';
    const asked = itemParam('entity') || about;
    if (asked && bndObj(m, asked) && B.asked !== asked) { B.asked = asked; B.sel = asked; B.d = null; }
    if (!bndObj(m, B.sel)) B.sel = (m.objects.find((o) => o.table) || m.objects[0] || {}).name || '';
    const o = bndObj(m, B.sel);
    const acts = `<a class="k-btn" href="#sources">Mapping</a><button class="k-btn" data-act="bndCheckNow"${S.bind && S.bind.busy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.bind && S.bind.busy ? '검사 중' : 'Binding 검사'}</button>${canEdit() ? `<a class="k-btn pri" href="${itemHref('binding', 'form')}">${ki('plus', 16, 1.75)}Binding</a>` : ''}`;
    const head = kHead('Entity Binding', BND_BIND_LEAD, acts);
    if (!o) return bndPg(head + kEmpty('Entity가 없습니다', '', `<a class="k-btn pri" href="#objects">Entity</a>`));
    const ents = m.objects, boundE = ents.filter((x) => x.table);
    const allP = ents.flatMap((x) => bndStored(m, x.name).map((p) => [x, p]));
    const boundP = allP.filter(([x, p]) => ['ok', 'spec'].includes(bndState(m, x, p)));
    const lostP = allP.filter(([x, p]) => bndState(m, x, p) === 'missing');
    const rel = m.links.map((l) => bndLinkRow(m, l, by));
    const noSrc = rel.filter((r) => r.mark[1] === '소스 없음');
    // each place to mend once: a column the source lacks is also what the check found there
    const need = new Set([...lostP.map(([x, p]) => `property:${x.name}.${p.name}`), ...noSrc.map((r) => `link:${r.l.name}`), ...Object.keys(by)]).size;
    const area = o.area ? m.areas.find((a) => a.name === o.area) : null;
    const total = bndStored(m, o.name).length;
    const bar = `<div class="k-bar" role="toolbar" aria-label="선택한 Binding"><span class="k-s">선택한 Binding</span>${area ? `${BND_OBJ}<span class="k-s">${esc(`${area.label || area.name}@${area.name}`)} ›</span>` : ''}<span class="k-code k-ink">${esc(bndEnt(o))}</span><span class="k-14">${o.table ? `${esc(o.table)} · Property ${bndBound(m, o)} / ${total}` : '테이블 미지정'}</span>
      <span class="k-push"><a class="k-btn" href="#objects?entity=${encodeURIComponent(o.name)}">${ki('doc', 16, 1.75)}Entity</a>${canEdit() ? `<a class="k-btn" href="${itemHref('binding', 'form', o.name)}">${ki('doc', 16, 1.75)}편집</a>` : ''}<a class="k-btn" href="${itemHref('binding', 'history', o.name)}">${ki('history', 16, 1.75)}이력</a>${canEdit() && o.table ? `<a class="k-btn dan" href="${itemHref('binding', 'delete', o.name)}">Binding 해제</a>` : ''}</span></div>`;
    const stat = (title, big, of, sub) => `<div class="k-card bnd-stat s5"><p class="k-s" style="margin:0">${title}</p><p class="k-big">${big}${of ? ` <span class="k-mut k-14" style="font-weight:400">/ ${of}</span>` : ''}</p><p class="k-s k-cut" style="margin:4px 0 0">${sub}</p></div>`;
    const stats = `<section class="k-wrap" aria-label="Binding 현황">${stat('연결 Entity', boundE.length, ents.length, boundE.length ? esc(boundE.slice(0, 3).map((x) => x.label || x.name).join(' · ')) : '없음')}
      ${stat('연결 Property', boundP.length, allP.length, 'Mapping 명세')}${stat('Relation Binding', rel.filter((r) => r.bound).length, rel.length, '연결 테이블 지정')}
      ${on && bndChecked() ? stat('실제 값 확인', S.bind.checked.columns, '', `테이블 ${S.bind.checked.tables} · 데이터 점검 ${S.bind.checked.data_checks}건`) : `<div class="bnd-stat s5 dash"><p class="k-s" style="margin:0">실제 값 확인</p><p class="k-big mut">-</p><p class="k-s" style="margin:4px 0 0">${on ? 'Binding 검사 전' : '데이터 소스 미연결'}</p></div>`}
      <div class="bnd-stat s5${need ? ' warn' : ' k-card'}"><p class="k-s" style="margin:0">확인 필요</p><p class="k-big${need ? ' warn' : ''}">${need}</p><p class="${need ? 'k-warn' : 'k-mut'} k-13" style="margin:4px 0 0">컬럼 확인 ${lostP.length} · 소스 없음 ${noSrc.length}</p></div></section>`;
    const sql = B.sql && !B.sql.busy && B.sql.entity === o.name && B.sql.sig === bndSig() ? B.sql : null;
    const sqlCard = !o.table ? '' : `<section class="k-card" aria-labelledby="bnd-sq-h"><div class="k-h" style="padding:16px 20px"><h2 class="k-h2" id="bnd-sq-h">생성 SQL</h2><span class="k-chip">읽기 전용</span>${sql && sql.sql ? `<button class="k-lnk k-push" data-act="copycode" data-v="${esc(sql.sql)}">복사</button>` : ''}</div>
      ${sql && sql.sql ? `<pre class="bnd-sql">${esc(sql.sql)}</pre>` : `<p class="k-cf line">${esc(sql ? sql.error || 'SQL을 생성하지 못했습니다.' : '불러오는 중입니다.')}</p>`}
      </section>`;
    const checks = bndBindChecks(m, o, by), pass = checks.filter((c) => c.ok).length;
    const checkCard = `<section class="k-card" aria-labelledby="bnd-ck-h"><div class="k-pha" style="padding:16px 20px 12px"><h2 class="k-h2" id="bnd-ck-h">검사</h2>${checks.length ? `<span class="k-chip ok">통과 ${pass}</span>${checks.length - pass ? `<span class="k-chip warn">확인 ${checks.length - pass}</span>` : ''}` : ''}</div>
      ${checks.length ? `<ul class="bnd-checks">${checks.map((c) => `<li>${c.ok ? `<span class="k-ok">${ki('check', 16, 1.75)}</span>` : `<span class="k-warn">${ki('alert', 16, 1.75)}</span>`}<span class="k-g0"><span class="k-14">${esc(c.say)}</span><br><span class="k-s">${esc(c.sub || '')}</span></span></li>`).join('')}</ul>` : '<p class="k-cf">테이블 미지정</p>'}
      ${o.table ? bndBindPreview(o) : ''}</section>`;
    const mine = rel.filter((r) => r.l.source === o.name || r.l.target === o.name);
    const lab = (x, name) => (x ? (x.name === o.name ? x.label || x.name : bndEnt(x)) : name);
    const relCard = `<section class="k-card" id="bnd-rel" aria-labelledby="bnd-rb-h"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="bnd-rb-h">Relation Binding</h2><span class="k-chip">${mine.length}</span><a class="k-btn k-push" href="#model?entity=${encodeURIComponent(o.name)}">그래프 탐색</a></div>
      ${mine.length ? `<div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">Relation</th><th scope="col">시작 → 끝</th><th scope="col">소스 테이블</th><th scope="col">시작 키 컬럼</th><th scope="col">끝 키 컬럼</th><th scope="col">상태</th></tr></thead><tbody>
        ${mine.map((r) => `<tr data-row="bind:link:${esc(r.l.name)}"><td class="k-code">${esc(r.l.name)}</td><td>${esc(lab(r.s, r.l.source))} → ${esc(lab(r.t, r.l.target))}</td><td class="k-code">${esc(r.table || '-')}</td><td class="k-code">${esc(r.a || '-')}</td><td class="k-code">${esc(r.b || '-')}</td><td><span class="k-chip${r.mark[0] ? ` ${r.mark[0]}` : ''}">${esc(r.mark[1])}</span></td></tr>`).join('')}</tbody></table></div>` : '<p class="k-cf line">Relation이 없습니다.</p>'}
      </section>`;
    const hists = bndHists(o.name);
    const histRow = (h) => { const x = bndObj(m, h.entity), lk = m.links.find((l) => l.name === h.of), bad = (by[`object:${h.entity}`] || [])[0];
      const cols = h.time.map((n) => { const p = x && bndOwn(m, x.name).find((q) => q.name === n); return p ? bndCol(p) : n; });
      const mark = !(x && x.table) ? ['', '테이블 미지정'] : bad ? ['warn', FINDING[bad.kind] || bad.kind] : ['ok', '연결됨'];
      return `<tr><td><a href="#bind?entity=${encodeURIComponent(h.entity)}">${esc(x ? bndEnt(x) : h.entity)}</a></td><td class="nw">${h.kind === 'period' ? '유효 기간' : '시계열'}</td><td class="k-code">${esc((x && x.table) || '-')}</td>
        <td class="k-code">${esc(cols.join(' · ') || '-')}</td><td>${esc(lk ? lk.label || lk.name : h.of || '-')}</td><td><span class="k-chip${mark[0] ? ` ${mark[0]}` : ''}">${esc(mark[1])}</span></td></tr>`; };
    const histCard = !hists.length ? '' : `<section class="k-card" id="bnd-hist" aria-labelledby="bnd-hb-h"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="bnd-hb-h">이력 Binding</h2><span class="k-chip">${hists.length}</span></div>
      <div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">Entity</th><th scope="col">종류</th><th scope="col">소스 테이블</th><th scope="col">시간 컬럼</th><th scope="col">Relation</th><th scope="col">상태</th></tr></thead><tbody>${hists.map(histRow).join('')}</tbody></table></div></section>`;
    const found = on && bndChecked() ? S.bind.findings : [];
    const foundCard = found.length ? `<section class="k-card" aria-labelledby="bnd-fd-h"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="bnd-fd-h">Binding 검사 결과</h2><span class="k-chip warn">${found.length}</span></div>
      <div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">심각도</th><th scope="col">종류</th><th scope="col">항목</th><th scope="col">조치</th><th scope="col"></th></tr></thead><tbody>${found.map((f) => `<tr data-row="bind:${esc(f.element)}"><td><span class="k-chip ${f.severity === 'error' ? 'bad' : 'warn'}">${f.severity === 'error' ? '오류' : '주의'}</span></td><td class="nw">${esc(FINDING[f.kind] || f.kind)}</td><td class="k-code">${esc(f.element.split(':').slice(1).join(':'))}</td><td>${esc(FIX[f.kind] || '')}<br><span class="k-s">${esc(f.detail || '')}</span></td><td>${canEdit() && bndFixHref(f.element) ? `<a class="k-lnk" href="${bndFixHref(f.element)}">편집</a>` : ''}</td></tr>`).join('')}</tbody></table></div></section>`
      : on && bndChecked() ? `<section class="k-card pad k-h"><span class="k-ok">${ki('check', 16, 1.75)}</span><span class="k-14">정의와 데이터 소스 일치 · 테이블 ${S.bind.checked.tables} · 컬럼 ${S.bind.checked.columns} · 데이터 점검 ${S.bind.checked.data_checks}건</span></section>` : '';
    return bndPg(`${head}${bar}${stats}<div class="k-cols">${bndBindTree(m, o.name)}<div class="k-v g16" style="flex:3 1 640px;min-width:0">${bndBindCard(m, o, by)}${sqlCard}${checkCard}</div></div>${histCard}${relCard}${foundCard}
      ${kNext([['sources', 'Mapping'], ['db', '데이터 소스'], ['objects', 'Entity'], ['query', '질의'], ['records', '레코드 탐색']])}`);
  }

  // what the card of the chosen Entity reads from the server: the SQL its binding makes, and a few of its rows
  function bndBindAfter() {
    bndNeed();
    const m = bndM(), B = S.bnd.bind, o = m && bndObj(m, B.sel);
    if (!m || !o) return;
    if (!noSource() && (!S.bind || (!S.bind.busy && S.bind.sig !== bndSig()))) bndCheckRun().finally(() => { if (S.tab === 'bind') render(); });
    // both are of the definition as it stands: another Entity, an edit or an edit taken back reads them again
    const sig = bndSig();
    if (o.table && (!B.sql || B.sql.entity !== o.name || B.sql.sig !== sig)) {
      B.sql = { entity: o.name, sig, sql: '', error: '', busy: true };
      api('bnd/binding?entity=' + encodeURIComponent(o.name)).then((r) => { if (B.sql && B.sql.entity === r.entity && B.sql.sig === sig) B.sql = { ...r, sig }; })
        .catch((e) => { if (B.sql && B.sql.sig === sig) B.sql = { entity: o.name, sig, sql: '', error: e.message }; }).finally(() => { if (S.tab === 'bind' && B.sel === o.name) render(); });
    }
    if (o.table && !noSource() && (!B.prof || B.prof.name !== o.name || B.prof.sig !== sig)) {
      B.prof = { name: o.name, sig, busy: true };
      api('object/profile?name=' + encodeURIComponent(o.name)).then((r) => { if (B.prof && B.prof.sig === sig && B.prof.name === o.name) B.prof = { name: o.name, sig, ...r }; })
        .catch((e) => { if (B.prof && B.prof.sig === sig) B.prof = { name: o.name, sig, ok: false, error: e.message }; }).finally(() => { if (S.tab === 'bind' && B.sel === o.name) render(); });
    }
  }

  screen('bind', { area: 'work', word: 'Entity Binding', view: bndBindView, after: bndBindAfter });

  // several edits made one after another; the first that does not hold stops the rest and says why
  async function bndEdits(ops) {
    let last = null;
    for (const [op, args] of ops) last = await api('manage/edit', { op, args });
    if (last) { S.mg.st = last; S.md.yaml = null; S.md.trial = null; S.md.data = null; S.mg.review = null; }
    return last;
  }

  let bndTableTimer = 0;
  Object.assign(INPUT, {
    bndBindQ: (t) => { const m = bndM(); S.bnd.bind.q = t.value; const box = $('#bndtree'); if (m && box) { const tmp = document.createElement('div'); tmp.innerHTML = bndBindTree(m, S.bnd.bind.sel); box.innerHTML = tmp.querySelector('#bndtree').innerHTML; } },
    bndBindTable: (t) => { const m = bndM(), o = bndObj(m, S.bnd.bind.sel), d = bndBindDraft(o); d.table = t.value.trim(); d.cols = {}; d.add = {};
      if (t.tagName === 'SELECT') { render(); return; }
      clearTimeout(bndTableTimer);  // a name being typed: the card is drawn again when the typing rests, and the caret stays where it was
      bndTableTimer = setTimeout(() => { if (S.tab !== 'bind') return; const at = t.selectionStart; render(); const el = $('input[data-in=bndBindTable]'); if (el) { el.focus(); el.setSelectionRange(at, at); } }, 600); },
    bndBindCol: (t) => { const m = bndM(), o = bndObj(m, S.bnd.bind.sel), d = bndBindDraft(o), p = bndStored(m, o.name).find((x) => x.name === t.dataset.p); const v = t.value.trim();
      if (p && v === bndCol(p)) delete d.cols[p.name]; else d.cols[t.dataset.p] = v;
      const b = $('[data-act=bndBindSave]'); if (b) b.disabled = !bndBindDirty(o, d); },
    bndBindProp: (t) => { const m = bndM(), o = bndObj(m, S.bnd.bind.sel), d = bndBindDraft(o), c = t.dataset.c;
      if (t.value === '+') d.add[c] = true; else { delete d.add[c]; if (t.value) { const p = bndStored(m, o.name).find((x) => x.name === t.value); if (p && bndCol(p).toLowerCase() === c.toLowerCase()) delete d.cols[p.name]; else d.cols[t.value] = c; } }
      render(); },
  });
  Object.assign(ACT, {
    bndBindSel: (t) => {  // the card of the Entity picked comes into view where it is not (under the tree on a narrow screen)
      const B = S.bnd.bind; B.sel = t.dataset.name; B.d = null; render();
      const card = $('#bnd-bd-h'), box = card && card.closest('section'), main = $('#main');
      if (box && main) { const top = box.getBoundingClientRect().top, view = main.getBoundingClientRect(); if (top < view.top || top > view.top + view.height * 0.6) box.scrollIntoView({ block: 'start' }); }
    },
    bndBindFold: (t) => { const B = S.bnd.bind, a = t.dataset.a; B.fold[a] = t.getAttribute('aria-expanded') === 'true'; render(); },
    bndBindRel: () => { const el = $('#bnd-rel'); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); },
    bndBindPast: () => { const el = $('#bnd-hist'); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); },
    bndBindReset: () => { S.bnd.bind.d = null; render(); },
    bndBindAddAll: () => {
      const m = bndM(), o = bndObj(m, S.bnd.bind.sel), d = bndBindDraft(o), t = bndTable(m, d.table);
      const props = bndStored(m, o.name), colOf = (p) => (p.name in d.cols ? d.cols[p.name] || p.name : bndCol(p));
      if (t) t.columns.filter((c) => !props.some((p) => colOf(p).toLowerCase() === c.name.toLowerCase())).forEach((c) => { d.add[c.name] = true; });
      render();
    },
    bndBindSave: async () => {
      const m = bndM(), B = S.bnd.bind, o = bndObj(m, B.sel), d = bndBindDraft(o), t = bndTable(m, d.table);
      const ops = [];
      if (d.table !== (o.table || '')) ops.push(['update_object', { name: o.name, table: d.table }]);
      Object.entries(d.cols).forEach(([p, c]) => ops.push(['update_property', { object: o.name, name: p, column: c }]));
      const taken = new Set(m.properties.filter((p) => p.object === o.name).map((p) => p.name));
      Object.keys(d.add).forEach((c) => {
        const col = t && t.columns.find((x) => x.name === c);
        let name = propName(c), i = 2;
        while (taken.has(name)) { name = `${propName(c)}_${i}`; i += 1; }
        taken.add(name);
        ops.push(['add_property', { object: o.name, name, label: c, type: col ? sqlType(col.type) : 'string', column: c }]);
      });
      if (!ops.length) return;
      B.saving = true; render();
      try {
        await bndEdits(ops);
        B.d = null; B.sql = null; B.prof = null;
        toast(`작성 중인 변경 요청에 Binding 변경 ${ops.length}건을 저장했습니다.`);
      } catch (e) { fail(e); try { S.mg.st = await api('manage'); } catch (_) { /* the last state stays */ } }
      B.saving = false; render();
    },
  });
