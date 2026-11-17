  // ---- 데이터 바인더의 항목 화면: 매핑 · 바인딩 · 쿼리 · 액션 (추가 · 편집 / 삭제 / 히스토리는 01-items.js 가 그린다) ----------
  async function bndReady() {  // the definition, read once: whoever asked first is waited for
    for (let i = 0; i < 100 && S.mg.busy && !S.mg.st; i += 1) await new Promise((r) => setTimeout(r, 100));
    if (!S.mg.st) await loadManage();
    if (S.mg.st && S.mg.st.error) throw new Error(S.mg.st.error);
    await bndColsLoad();
  }
  const bndSrcWord = () => { const src = S.st.source || {}; return src.connected ? `${(S.st.origin || {}).detail || src.name} · ${BACKEND_KIND[src.kind] || src.kind} · 연결됨` : '미연결'; };
  const bndOpt = (v, word, cur) => `<option value="${esc(v)}"${String(v) === String(cur ?? '') ? ' selected' : ''}>${esc(word)}</option>`;
  const bndFld = (word, html, hint = '') => `<label class="k-f">${word}${html}${hint ? `<span class="k-hint">${hint}</span>` : ''}</label>`;
  const bndIn = (k, value, extra = '') => `<input class="k-in${extra.includes(' class="k-in mono"') ? ' mono' : ''}" type="text" data-in="itf" data-k="${k}" value="${esc(value ?? '')}"${extra.replace(' class="k-in mono"', '')}>`;
  const bndBase = (grid, extra = '') => `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">${grid}</div>${extra}</div></section>`;
  // rows of a form that are added and taken out: d[list] is a list of objects
  const bndRowIn = (list, i, k, value, extra = '') => `<input class="k-in sm" type="text" data-in="bndRow" data-l="${list}" data-i="${i}" data-k="${k}" value="${esc(value ?? '')}"${extra}>`;
  const bndRowSel = (list, i, k, opts, value, re = false) => `<select class="k-in sm" data-in="bndRow" data-l="${list}" data-i="${i}" data-k="${k}"${re ? ' data-re' : ''}>${opts.map(([v, w]) => bndOpt(v, w, value)).join('')}</select>`;
  const bndRowDel = (list, i) => `<button class="k-lnk" type="button" data-act="bndRowDel" data-l="${list}" data-i="${i}">삭제</button>`;
  const bndRowAdd = (list, word) => `<span class="k-pha k-push"><button class="k-lnk" type="button" data-act="bndRowAdd" data-l="${list}">${ki('plus', 16, 1.75)}${word}</button></span>`;
  const bndRecheck = () => { const box = $('#itchecks'); if (box && ITEM[S.it.kind]) box.innerHTML = itemChecks(ITEM[S.it.kind], S.it); };
  const BND_ROW_NEW = { params: () => ({ name: '', label: '', type: 'string' }), criteria: () => ({ decision: '', field: '', value: 'true' }), set: () => ({ prop: '', value: '' }),
    limits: () => ({ subject: '', kind: 'max', value: '' }), conds: () => ({ prop: '', op: 'eq', value: '' }) };
  Object.assign(INPUT, {
    bndRow: (t) => { const d = S.it.d; if (!d || !d[t.dataset.l] || !d[t.dataset.l][Number(t.dataset.i)]) return; d[t.dataset.l][Number(t.dataset.i)][t.dataset.k] = t.value; if ('re' in t.dataset) render(); else bndRecheck(); },
    bndTick: (t) => { const d = S.it.d, k = t.dataset.k; if (!d) return; d.fields = t.checked ? [...new Set([...d.fields, k])] : d.fields.filter((x) => x !== k); bndRecheck(); },
  });
  Object.assign(ACT, {
    bndRowAdd: (t) => { const d = S.it.d, l = t.dataset.l; if (!d) return; (d[l] = d[l] || []).push(BND_ROW_NEW[l]()); render(); },
    bndRowDel: (t) => { const d = S.it.d; if (!d) return; d[t.dataset.l].splice(Number(t.dataset.i), 1); render(); },
  });
  // a changed field in the words these screens use for it (the shared history says some of them as the definition spells them)
  const BND_FIELD = { transform: '변환식', source_type: '원천 자료형', columns: '키 컬럼', column: '컬럼', source: '소스', table: '테이블', values: '허용값', labels: '코드 변환표', parameters: '파라미터', criteria: '전제조건',
    transition_to: '처리 후 상태', approval: '승인 기준', call: '호출 API', undo: '되돌리기 호출', set: '변경 값', auto_within: '자동 승인 기준', auto_agents: 'Agent 자동 실행', query: '쿼리 정의', params: '입력값', match: '대상',
    edges: '관계', where: '조건', return: '반환', order: '정렬', limit: '건수', label: '이름', description: '설명', key: '키', status: '상태', cite: '근거', target: '대상 Entity', expect: '기대 결과', decision: '규칙' };
  const bndFieldWord = (label) => String(label).split(/ · |\./).map((w) => BND_FIELD[w] || w).join(' · ');
  const bndHist = (kind) => async (x) => (await itemHistoryOf(ITEM[kind], x)).map((e) => ({ ...e, rows: e.rows.map((r) => ({ ...r, label: bndFieldWord(r.label) })), all: e.all.map((r) => ({ ...r, label: bndFieldWord(r.label) })) }));
  const bndSame = (a, b) => ['string', 'enum'].includes(a) ? ['string', 'enum'].includes(b) : ['integer', 'decimal'].includes(a) ? ['integer', 'decimal'].includes(b) : ['date', 'datetime'].includes(a) ? ['date', 'datetime', 'string'].includes(b) : a === 'boolean' ? ['boolean', 'integer'].includes(b) : true;

  // ---- 매핑: one Property and the column it reads -------------------------------------------------------------------
  const bndCodes = (p) => (p.values || []).map((v) => `${v}${(p.labels || {})[v] ? ` = ${p.labels[v]}` : ''}`).join('\n');
  const bndCodeRows = (text) => String(text || '').split(/\n|·/).map((s) => s.trim()).filter(Boolean).map((line) => { const parts = line.split(/\s*(?:=|→|:)\s*/); return [parts[0].trim(), parts.slice(1).join(' ').trim()]; }).filter(([v]) => v);
  function bndMapOf(d) { const m = bndM(), p = m && m.properties.find((x) => bndMapId(x) === d.prop); return p ? { m, p, o: bndObj(m, p.object), t: bndTable(m, (bndObj(m, p.object) || {}).table) } : { m, p: null, o: null, t: null }; }

  item('map', {
    word: '매핑', under: 'sources', list: 'sources', load: bndReady, history: bndHist('map'),
    hint: '데이터 매핑에서 ‘+ 매핑’을 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    lead: { delete: '매핑을 지우면 컬럼 이름과 변환식이 지워지고, Property는 이름이 같은 컬럼을 읽는 기본값으로 돌아갑니다. Property 정의는 그대로 남습니다. 바로 지워지지 않고 변경 요청으로 올라갑니다.' },
    find: (id) => { const m = bndM(), p = m && m.properties.find((x) => bndMapId(x) === id); return p ? { p, o: bndObj(m, p.object) } : null; },
    code: (x) => `${x.o ? x.o.label || x.o.name : x.p.object}.${x.p.label || x.p.name}`,
    name: (x) => (x.p.expr ? '계산 속성 · 컬럼 없음' : x.o && x.o.table ? `${x.o.table}.${bndCol(x.p)}` : '테이블 대기'),
    element: (x) => `property:${x.p.object}.${x.p.name}`,
    draft: (x) => { const p = x ? x.p : null; return { prop: p ? bndMapId(p) : '', column: p ? bndCols(p)[0] : '', how: p && p.transform ? 'expr' : p && (p.values || []).length ? 'code' : 'same', codes: p ? bndCodes(p) : '', transform: p ? p.transform || '' : '', source_type: p ? p.source_type || '' : '', status: p ? p.status || 'active' : 'active', reason: '' }; },
    form: (d, x) => {
      const { m, p, o, t } = bndMapOf(d);
      const props = m.properties.filter((q) => !q.expr).map((q) => [bndMapId(q), `${(bndObj(m, q.object) || {}).label || q.object}.${q.label || q.name}`]);
      const many = p && p.columns && p.columns.length > 1;
      const col = many ? `<input class="k-in mono" type="text" value="${esc(p.columns.join(' + '))}" disabled>` : t ? `<select class="k-in" data-in="itf" data-k="column"><option value="">컬럼 선택</option>${t.columns.map((c) => bndOpt(c.name, `${t.table}.${c.name} · ${c.type || ''}`, d.column)).join('')}${d.column && !bndHas(t, d.column) ? bndOpt(d.column, `${d.column} · 원천에 없음`, d.column) : ''}</select>`
        : bndIn('column', d.column, ` class="k-in mono" placeholder="컬럼 이름"${o && o.table ? '' : ' disabled'}`);
      return bndBase(`${bndFld('Property', `<select class="k-in" data-in="bndMapProp"${x ? ' disabled' : ''}><option value="">Property 선택</option>${props.map(([v, w]) => bndOpt(v, w, d.prop)).join('')}</select>`)}
        ${bndFld('데이터 소스', `<select class="k-in" disabled><option>${esc(bndSrcWord())}</option></select>`)}
        ${bndFld('테이블 · 컬럼', col, many ? '여러 컬럼을 하나의 값으로 읽는 키입니다' : o && o.table ? `${esc(o.table)} 테이블 · Entity의 테이블은 Entity 바인딩에서 정합니다` : 'Entity 바인딩에서 테이블을 먼저 고릅니다')}
        ${bndFld('매핑 방식', `<select class="k-in" data-in="itf" data-k="how" data-re>${[['same', '그대로'], ['code', '코드 변환'], ['expr', '변환식']].map(([v, w]) => bndOpt(v, w, d.how)).join('')}</select>`)}
        ${d.how === 'code' ? `<div class="k-full">${bndFld('코드 변환표', `<textarea class="k-in" rows="4" data-in="itf" data-k="codes" placeholder="소스 값 = 표시 이름, 한 줄에 하나">${esc(d.codes)}</textarea>`, '소스에 들어 있는 값과 그 값의 표시 이름 · 여기 적은 값이 이 Property의 허용값이 됩니다')}</div>` : ''}
        ${d.how === 'expr' ? `${bndFld('변환식', bndIn('transform', d.transform, ' class="k-in mono" placeholder="예: value / 100"'), '원천 값을 value로 참조합니다')}${bndFld('원천 자료형', `<select class="k-in" data-in="itf" data-k="source_type"><option value="">Property와 같음</option>${TYPES.filter((y) => y !== 'enum').map((y) => bndOpt(y, TYPE_WORD[y], d.source_type)).join('')}</select>`)}` : ''}
        ${bndFld('상태', `<select class="k-in" data-in="itf" data-k="status">${Object.entries(STATUS_WORD).map(([k, [, w]]) => bndOpt(k, w, d.status)).join('')}</select>`)}`);
    },
    checks: (d) => {
      const { p, o, t } = bndMapOf(d), out = [];
      if (!p) return [{ say: 'Property를 고르면 검사합니다', tone: 'note' }];
      if (!o || !o.table) out.push({ say: 'Entity가 아직 테이블에 바인딩되지 않음', sub: 'Entity 바인딩에서 테이블을 먼저 고릅니다', tone: 'bad' });
      else if (!d.column && !(p.columns && p.columns.length > 1)) out.push({ say: '컬럼을 고르지 않음', tone: 'bad' });
      else if (t) { const c = t.columns.find((y) => y.name.toLowerCase() === String(d.column).toLowerCase());
        out.push(p.columns && p.columns.length > 1 ? { say: '키 컬럼 결합', sub: p.columns.join(' + '), tone: 'ok' } : c ? { say: '컬럼이 테이블에 있음', sub: `${t.table}.${c.name} ${c.type || ''}`, tone: 'ok' } : { say: '컬럼이 원천 테이블에 없음', sub: `${t.table}.${d.column}`, tone: 'warn', word: '확인 필요' });
        if (c && d.how !== 'expr' && !bndSame(p.type, sqlType(c.type))) out.push({ say: `타입이 다름 · ${TYPE_WORD[p.type] || p.type} ↔ ${c.type}`, sub: '변환식으로 읽는 방법을 정하거나 Property 타입을 맞춥니다', tone: 'warn', word: '확인 필요' });
      } else out.push({ say: '컬럼 이름을 명세로 저장', sub: `${o.table}.${d.column}`, tone: 'ok' });
      if (d.how === 'code') { const n = bndCodeRows(d.codes).length; out.push(n ? { say: `코드값 ${n}종`, tone: 'ok' } : { say: '코드 변환표가 비어 있음', tone: 'warn', word: '확인 필요' }); }
      if (d.how === 'expr') out.push(d.transform.trim() ? { say: '변환식 있음', sub: d.transform.trim(), tone: 'ok' } : { say: '변환식이 비어 있음', tone: 'warn', word: '확인 필요' });
      out.push(noSource() ? { say: '실제 값 분포 확인은 데이터 소스 연결 후', tone: 'note' } : { say: '저장한 뒤 차이 검사에서 실제 값과 대조', tone: 'note' });
      return out;
    },
    valid: (d) => (!d.prop ? 'Property를 골라 주세요.' : ''),
    save: async (d) => {
      const { p } = bndMapOf(d), rows = bndCodeRows(d.codes);
      const args = { object: p.object, name: p.name, transform: d.how === 'expr' ? d.transform.trim() : '', source_type: d.how === 'expr' ? d.source_type : '', status: d.status };
      if (!(p.columns && p.columns.length > 1)) args.column = String(d.column).trim();
      if (d.how === 'code' && rows.length) { args.values = rows.map(([v]) => v); args.labels = Object.fromEntries(rows.filter(([, w]) => w)); }
      await bndEdits([['update_property', args]]);
      S.bnd.map.sel = d.prop;
      return { element: `property:${p.object}.${p.name}` };
    },
    remove: async (x) => { await bndEdits([['update_property', { object: x.p.object, name: x.p.name, column: '', transform: '', source_type: '' }]]); },
  });
  Object.assign(INPUT, { bndMapProp: (t) => { const d = S.it.d, m = bndM(), p = m.properties.find((x) => bndMapId(x) === t.value); d.prop = t.value;
    if (p) Object.assign(d, { column: bndCols(p)[0], how: p.transform ? 'expr' : (p.values || []).length ? 'code' : 'same', codes: bndCodes(p), transform: p.transform || '', source_type: p.source_type || '', status: p.status || 'active' }); render(); } });

  // ---- 바인딩: one Entity, its table, its key, and the column of each Property ---------------------------------------
  const bndBindRows = (m, name) => bndStored(m, name).map((p) => ({ prop: p.name, column: bndCol(p), was: bndCol(p), fixed: bndCols(p).length > 1 }));
  item('binding', {
    word: '바인딩', under: 'bind', list: 'bind', load: bndReady, history: bndHist('binding'),
    hint: 'Entity 바인딩에서 ‘+ 데이터 바인딩’을 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    lead: { delete: '바인딩을 해제하기 전에 이 Entity를 쓰고 있는 곳을 확인합니다. Entity와 Property 정의는 남고 테이블 연결만 지워집니다. 바로 지워지지 않고 변경 요청으로 올라갑니다.' },
    find: (id) => { const m = bndM(); return m ? bndObj(m, id) : null; },
    code: (o) => bndEnt(o), name: (o) => o.table || '바인딩 없음', element: (o) => `object:${o.name}`,
    draft: (o) => { const m = bndM(), pick = !o && itemParam('entity') ? bndObj(m, itemParam('entity')) : null, e = o || pick; return { entity: e ? e.name : '', table: e ? e.table || '' : '', key: e ? e.key || '' : '', rows: e ? bndBindRows(m, e.name) : [], reason: '' }; },
    form: (d, x) => {
      const m = bndM(), o = bndObj(m, d.entity), tables = m.sources.source.tables, t = bndTable(m, d.table);
      const ents = m.objects.filter((e) => x || !e.table).map((e) => [e.name, bndEnt(e)]);
      const table = tables.length ? `<select class="k-in" data-in="itf" data-k="table" data-re><option value="">테이블 선택</option>${tables.map((y) => bndOpt(y.table, `${y.table}${y.objects.filter((n) => n !== d.entity).length ? ` · ${y.objects.filter((n) => n !== d.entity).map((n) => (bndObj(m, n) || {}).label || n).join(', ')}` : ''}`, d.table)).join('')}${d.table && !t ? bndOpt(d.table, `${d.table} · 원천에 없음`, d.table) : ''}</select>`
        : bndIn('table', d.table, ' class="k-in mono" placeholder="테이블 이름"');
      const keyRow = d.rows.find((r) => r.prop === d.key);
      const mine = o && o.module === 'workspace';
      const keys = o ? bndStored(m, o.name).map((p) => [p.name, `${p.name} · ${p.label || p.name}`]) : [];
      const rows = d.rows.map((r, i) => { const p = m.properties.find((q) => q.object === d.entity && q.name === r.prop) || {};
        const col = r.fixed ? `<input class="k-in sm mono" type="text" value="${esc(r.column)}" disabled>` : t ? `<select class="k-in sm" data-in="bndRow" data-l="rows" data-i="${i}" data-k="column">${t.columns.map((c) => bndOpt(c.name, `${c.name} · ${c.type || ''}`, r.column)).join('')}${bndHas(t, r.column) ? '' : bndOpt(r.column, `${r.column} · 원천에 없음`, r.column)}</select>` : bndRowIn('rows', i, 'column', r.column, ' style="font-family:var(--mono)"');
        return `<tr><td>${col}</td><td><span class="k-code k-ink">${esc(r.prop)}</span><br><span class="k-s">${esc(p.label || '')} · ${esc(TYPE_WORD[p.type] || p.type || '')}</span></td><td class="nw">${r.prop === d.key ? '키' : p.transform ? '변환식' : (p.values || []).length ? '코드 → 값' : '그대로'}</td></tr>`; }).join('');
      return `${bndBase(`${bndFld('Entity', `<select class="k-in" data-in="bndBindEnt"${x ? ' disabled' : ''}><option value="">Entity 선택</option>${ents.map(([v, w]) => bndOpt(v, w, d.entity)).join('')}</select>`, x ? '' : '아직 테이블에 바인딩하지 않은 Entity')}
        ${bndFld('데이터 소스', `<select class="k-in" disabled><option>${esc(bndSrcWord())}</option></select>`)}
        ${bndFld('테이블', table, tables.length ? 'Entity마다 기본 바인딩은 하나' : '연결 전에는 테이블 이름을 명세로 적습니다')}
        ${bndFld('Entity 키', `<select class="k-in" data-in="itf" data-k="key" data-re${mine ? '' : ' disabled'}>${keys.map(([v, w]) => bndOpt(v, w, d.key)).join('') || '<option value="">키 없음</option>'}</select>`, mine || !o ? '' : '키는 이 Entity를 정의한 모듈에서 정합니다')}
        ${bndFld('키 컬럼', `<input class="k-in mono" type="text" value="${esc(keyRow ? keyRow.column : '')}" disabled>`, '문자열 · 정수 컬럼만 · 아래 표에서 바꿉니다')}`)}
        <section class="k-card"><div class="k-ch"><h2>Property ↔ 컬럼</h2><span class="k-s">${d.rows.length}개 · 컬럼에서 읽는 Property</span></div>
          ${d.rows.length ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">소스 컬럼</th><th scope="col">Property</th><th scope="col">변환</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="k-cf line">Entity를 고르면 Property가 보입니다.</p>'}</section>`;
    },
    checks: (d, x) => {
      const m = bndM(), o = bndObj(m, d.entity), t = bndTable(m, d.table), out = [];
      if (!o) return [{ say: 'Entity를 고르면 검사합니다', tone: 'note' }];
      out.push(!x && o.table ? { say: '이 Entity에 이미 기본 바인딩이 있음', sub: o.table, tone: 'bad' } : { say: '이 Entity에 다른 기본 바인딩 없음', tone: 'ok' });
      if (!d.table) return out.concat([{ say: '테이블을 고르지 않음', tone: 'bad' }]);
      const key = d.rows.find((r) => r.prop === d.key);
      if (!key) out.push({ say: '키 Property가 없음', tone: 'warn', word: '확인 필요' });
      else if (t) { const cols = key.column.split(' + ').map((c) => t.columns.find((y) => y.name.toLowerCase() === c.toLowerCase()));
        out.push(cols.every(Boolean) ? (cols.every((c) => ['string', 'integer'].includes(sqlType(c.type))) ? { say: '키 컬럼이 문자열 · 정수', sub: cols.map((c) => `${c.name} ${c.type || ''}`).join(' · '), tone: 'ok' } : { say: '키 컬럼이 문자열 · 정수가 아님', sub: cols.map((c) => `${c.name} ${c.type || ''}`).join(' · '), tone: 'warn', word: '확인 필요' })
          : { say: '키 컬럼이 원천 테이블에 없음', sub: key.column, tone: 'bad' }); }
      if (t) {
        const lost = d.rows.filter((r) => !r.fixed && !bndHas(t, r.column));
        const off = d.rows.filter((r) => { const c = t.columns.find((y) => y.name.toLowerCase() === r.column.toLowerCase()), p = m.properties.find((q) => q.object === d.entity && q.name === r.prop); return c && p && !p.transform && !bndSame(p.type, sqlType(c.type)); });
        out.push(off.length ? { say: `타입이 다른 Property ${off.length}개`, sub: off.map((r) => r.prop).join(' · '), tone: 'warn', word: '확인 필요' } : { say: '바인딩한 Property의 타입이 컬럼과 맞음', tone: 'ok' });
        if (lost.length) out.push({ say: `컬럼 확인 대기 ${lost.length}개 · 원천 테이블에 없음`, sub: lost.map((r) => r.column).join(' · '), tone: 'warn', word: '확인 필요' });
      } else out.push({ say: noSource() ? '컬럼 대조는 데이터 소스 연결 후' : '원천에 이 테이블이 없음', sub: d.table, tone: noSource() ? 'note' : 'warn', word: noSource() ? '' : '확인 필요' });
      return out;
    },
    valid: (d) => (!d.entity ? 'Entity를 골라 주세요.' : !d.table.trim() ? '테이블을 골라 주세요.' : ''),
    save: async (d, x) => {
      const m = bndM(), o = bndObj(m, d.entity), ops = [];
      const head = { name: o.name, table: d.table.trim() };
      if (o.module === 'workspace' && d.key && d.key !== o.key) head.key = d.key;
      if (head.table !== (o.table || '') || head.key) ops.push(['update_object', head]);
      d.rows.filter((r) => !r.fixed && r.column.trim() !== r.was).forEach((r) => ops.push(['update_property', { object: o.name, name: r.prop, column: r.column.trim() }]));
      if (!ops.length) throw new Error('바뀐 내용이 없어 저장하지 않았습니다.');
      await bndEdits(ops);
      Object.assign(S.bnd.bind, { sel: o.name, d: null, sql: null, prof: null });
      return { element: `object:${o.name}`, go: `bind?entity=${encodeURIComponent(o.name)}` };
    },
    uses: async (o) => {
      const m = bndM(), props = bndStored(m, o.name), links = m.links.filter((l) => (l.source === o.name || l.target === o.name) && (l.on || l.via));
      const r = await api('item/uses?element=' + encodeURIComponent(`object:${o.name}`));
      return [props.length ? { say: `매핑 명세 ${props.length}개`, sub: `${o.label || o.name}의 Property ↔ 컬럼 명세가 함께 사라집니다`, href: 'sources' } : null,
        links.length ? { say: `관계 바인딩 ${links.length}개`, sub: `${links.slice(0, 2).map((l) => `${(bndObj(m, l.source) || {}).label || l.source} → ${(bndObj(m, l.target) || {}).label || l.target}`).join(', ')}${links.length > 2 ? ` 외 ${links.length - 2}` : ''}이 끊깁니다`, href: 'model' } : null,
        ...r.uses.map((u) => ({ say: `${({ 질의: '쿼리', 결정: '규칙' })[u.kind] || u.kind} ${u.names.length}개`, sub: `${u.names.slice(0, 2).join(', ')}${u.names.length > 2 ? ` 외 ${u.names.length - 2}` : ''}이 값을 읽지 못합니다`, href: u.screen }))].filter(Boolean);
    },
    remove: async (o) => { await bndEdits([['update_object', { name: o.name, table: '' }]]); Object.assign(S.bnd.bind, { d: null, sql: null, prof: null }); },
  });
  Object.assign(INPUT, { bndBindEnt: (t) => { const m = bndM(), e = bndObj(m, t.value), d = S.it.d; Object.assign(d, { entity: t.value, table: e ? e.table || '' : '', key: e ? e.key || '' : '', rows: e ? bndBindRows(m, e.name) : [] }); render(); } });

  // ---- 쿼리: where it starts, the relation it follows, what it takes and what it returns ------------------------------
  const bndRels = (m, type) => m.links.filter((l) => l.source === type || l.target === type).map((l) => ({ name: l.name, label: l.label || l.name, other: l.source === type ? l.target : l.source, forward: l.source === type }));
  // a query's definition as the form holds it, where the form can hold it: one or two Entities, plain columns, plain conditions
  function bndQForm(ir) {
    const nodes = Object.entries((ir || {}).match || {}), edges = (ir || {}).edges || [];
    if (!nodes.length || nodes.length > 2 || edges.length > 1 || (nodes.length === 2 && edges.length !== 1) || ir.distinct) return null;
    const [x, start] = nodes[0], y = nodes[1] ? nodes[1][0] : '';
    const ref = (r) => (typeof r === 'string' && r.startsWith(`${x}.`) ? `x.${r.slice(x.length + 1)}` : y && typeof r === 'string' && r.startsWith(`${y}.`) ? `y.${r.slice(y.length + 1)}` : null);
    let link = '';
    if (edges.length) { const [a, name, b] = edges[0]; if (!((a === x && b === y) || (a === y && b === x))) return null; link = `${name}:${a === x ? 1 : 0}`; }
    // a column written with the name it would have anyway ({col: x.name, as: name}) is the plain column
    const plainCol = (c) => (typeof c === 'string' ? c : c && typeof c.col === 'string' && Object.keys(c).every((k) => k === 'col' || (k === 'as' && c.as === c.col.split('.').pop())) ? c.col : null);
    const fields = (ir.return || []).map((c) => ref(plainCol(c)));
    if (fields.some((f) => !f)) return null;
    const list = !ir.where ? [] : ir.where.and ? ir.where.and : [ir.where], conds = [];
    for (const c of list) {
      const op = Object.keys(c)[0], arg = c[op];
      if (Object.keys(c).length !== 1 || !QB_OPS.some(([k]) => k === op) || !Array.isArray(arg) || arg.length !== 2 || !ref(arg[0])) return null;
      const v = arg[1];
      if (v && typeof v === 'object') { if (!v.param) return null; conds.push({ prop: ref(arg[0]), op, value: `$${v.param}` }); } else conds.push({ prop: ref(arg[0]), op, value: String(v) });
    }
    return { start, link, fields, conds, order: ir.order || null, limit: ir.limit || null };  // the order and the limit are kept as they were written
  }
  function bndQIr(d) {  // what the form says, as the query's definition; a mistake in the JSON is thrown as a sentence
    if (d.mode === 'json') { try { return JSON.parse(d.json); } catch (e) { throw new Error('쿼리 정의가 JSON 형식이 아닙니다.'); } }
    const m = bndM(), rel = bndRels(m, d.start).find((r) => `${r.name}:${r.forward ? 1 : 0}` === d.link);
    const typeOf = (p) => (bndOwn(m, p.startsWith('y.') && rel ? rel.other : d.start).find((q) => q.name === p.slice(2)) || {}).type;
    const key = (bndObj(m, d.start) || {}).key;
    const conds = d.conds.filter((c) => c.prop && c.value !== '').map((c) => { const t = typeOf(c.prop), raw = String(c.value);
      const v = raw.startsWith('$') ? { param: raw.slice(1) } : ['integer', 'decimal'].includes(t) && !Number.isNaN(Number(raw)) ? Number(raw) : t === 'boolean' ? raw === 'true' : raw;
      return { [c.op]: [c.prop, v] }; });
    const fields = d.fields.filter((f) => f.startsWith('x.') || rel);
    return { match: { x: d.start, ...(rel ? { y: rel.other } : {}) }, ...(rel ? { edges: [rel.forward ? ['x', rel.name, 'y'] : ['y', rel.name, 'x']] } : {}),
      ...(conds.length ? { where: conds.length > 1 ? { and: conds } : conds[0] } : {}), return: fields.length ? fields : [`x.${key}`], ...(d.order ? { order: d.order } : {}), ...(d.limit ? { limit: d.limit } : {}) };
  }
  function bndQCheck(d) {  // the definition being written, read into every store's language; the answer comes after the checks are drawn
    const Q = S.bnd.q;
    let ir;
    try { ir = bndQIr(d); } catch (e) { return { error: e.message }; }
    const key = JSON.stringify(ir);
    if (Q.chk && Q.chk.key === key) return Q.chk;
    clearTimeout(Q.chkTimer);
    Q.chkTimer = setTimeout(() => { Q.chk = { key, busy: true }; api('bnd/query/check', { query: ir }).then((r) => { Q.chk = { key, ...r }; }).catch((e) => { Q.chk = { key, error: e.message }; }).finally(() => { if (S.it && S.it.kind === 'queryitem') bndRecheck(); }); }, 350);
    return { busy: true };
  }

  item('queryitem', {
    word: '쿼리', under: 'query', list: 'query', history: bndHist('queryitem'),
    hint: '쿼리에서 ‘+ 쿼리’를 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    load: async () => { await bndReady(); await bndQLoad(true); },
    find: (id) => bndQOf(id), code: (x) => x.name, name: (x) => x.label, element: (x) => `query:${x.name}`,
    draft: (x) => {
      const m = bndM(), seed = S.bnd.q.seed, copy = !x && itemParam('copy') ? bndQOf(itemParam('copy')) : null, from = x || copy;
      S.bnd.q.seed = null; S.bnd.q.chk = null;
      const blank = { start: (m.objects.find((o) => o.table) || m.objects[0] || {}).name || '', link: '', fields: [], conds: [], order: null, limit: null };
      if (from) { const b = bndQForm(from.ir); return { name: x ? x.name : '', label: x ? x.label : `${from.label} 사본`, description: from.description || '', mode: b ? 'form' : 'json', ...(b || blank), json: JSON.stringify(from.ir, null, 2), reason: '' }; }
      if (seed) { let ir = null; try { ir = JSON.parse(seed.ir); } catch (e) { ir = null; } const b = ir && bndQForm(ir); return { name: '', label: seed.label || '', description: '', mode: b ? 'form' : 'json', ...(b || blank), json: ir ? JSON.stringify(ir, null, 2) : String(seed.ir || ''), reason: '' }; }
      return { name: '', label: '', description: '', mode: 'form', ...blank, json: '', reason: '' };
    },
    form: (d, x) => {
      const m = bndM(), locked = !!x && !x.editable;
      const rels = bndRels(m, d.start), rel = rels.find((r) => `${r.name}:${r.forward ? 1 : 0}` === d.link);
      const lab = (t) => (bndObj(m, t) || {}).label || t;
      const props = [...bndOwn(m, d.start).map((p) => [`x.${p.name}`, `${lab(d.start)} · ${p.label || p.name}`]), ...(rel ? bndOwn(m, rel.other).map((p) => [`y.${p.name}`, `${lab(rel.other)} · ${p.label || p.name}`]) : [])];
      const conds = d.conds.map((c, i) => `<div class="bnd-rowed">${bndRowSel('conds', i, 'prop', [['', 'Property 선택'], ...props], c.prop)}${bndRowSel('conds', i, 'op', QB_OPS, c.op)}${bndRowIn('conds', i, 'value', c.value, ' placeholder="값 또는 $입력값 이름"')}${bndRowDel('conds', i)}</div>`).join('');
      const seg = `<div class="k-seg self" role="group" aria-label="작성 방식"><button type="button" class="${d.mode === 'form' ? 'on' : ''}" data-act="bndQMode" data-m="form">양식</button><button type="button" class="${d.mode === 'json' ? 'on' : ''}" data-act="bndQMode" data-m="json">쿼리 정의 JSON</button></div>`;
      const body = d.mode === 'json' ? `<div class="k-full">${bndFld('쿼리 정의', `<textarea class="k-in mono" rows="12" data-in="itf" data-k="json" spellcheck="false" style="font-family:var(--mono);font-size:13px">${esc(d.json)}</textarea>`, '온톨로지 기준의 쿼리 정의 · match, edges, where, return, order, limit')}</div>`
        : `${bndFld('시작 Entity', `<select class="k-in" data-in="bndQStart">${m.objects.map((o) => bndOpt(o.name, bndEnt(o), d.start)).join('')}</select>`)}
          ${bndFld('따라갈 관계', `<select class="k-in" data-in="bndQLink"><option value="">따라가지 않음</option>${rels.map((r) => bndOpt(`${r.name}:${r.forward ? 1 : 0}`, `${r.label} → ${lab(r.other)}`, d.link)).join('')}</select>`)}
          <div class="k-full k-f">입력값 · 조건<div class="k-v">${conds}<div><button class="k-lnk flat" type="button" data-act="bndRowAdd" data-l="conds">${ki('plus', 16, 1.75)}조건</button></div></div><span class="k-hint">값을 $이름으로 적으면 실행할 때 받는 입력값이 됩니다 · 예: $orderNo</span></div>
          <div class="k-full k-f">반환 속성<div class="bnd-ticks">${props.map(([k, w]) => `<label class="k-ck pill"><input type="checkbox" data-in="bndTick" data-k="${esc(k)}"${d.fields.includes(k) ? ' checked' : ''}>${esc(w)}</label>`).join('')}</div><span class="k-hint">고르지 않으면 시작 Entity의 키를 돌려줍니다</span></div>`;
      return `${locked ? `<p class="k-note warn">모듈이 정의한 쿼리는 여기서 바꿀 수 없습니다. 같은 내용으로 새 쿼리를 만들어 고칩니다. <a href="${itemHref('queryitem', 'form')}?copy=${encodeURIComponent(x.name)}">사본으로 새 쿼리 만들기</a></p>` : ''}
        ${bndBase(`${bndFld('이름', bndIn('label', d.label, ' placeholder="예: 주문별 반품 가능 상품"'))}${bndFld('키', bndIn('name', d.name, ` class="k-in mono" placeholder="예: returnableItems"${x ? ' disabled' : ''}`), 'API · MCP에서 이 키로 호출')}
          <div class="k-full">${seg}</div>${body}
          <div class="k-full">${bndFld('설명', `<textarea class="k-in" rows="3" data-in="itf" data-k="description">${esc(d.description)}</textarea>`)}</div>
          ${x ? bndFld('허용 접근 정책', `<input class="k-in" type="text" value="${esc(x.roles.map((r) => r.name).join(' · ') || '없음')}" disabled>`, '접근 정책에서 정합니다') : ''}`)}`;
    },
    checks: (d, x) => {
      const m = bndM(), out = [], all = S.bnd.q.st ? S.bnd.q.st.queries : [];
      if (!x && d.name && !IDENT.test(d.name)) out.push({ say: '키는 영문자로 시작하고 영문자 · 숫자 · _ 만', sub: d.name, tone: 'bad' });
      if (!x && d.name && all.some((q) => q.name === d.name)) out.push({ say: '같은 키의 쿼리가 이미 있음', sub: d.name, tone: 'bad' });
      const c = bndQCheck(d);
      if (c.error) out.push({ say: '쿼리 정의를 읽지 못함', sub: c.error, tone: 'bad' });
      else if (c.busy || !c.translations) out.push({ say: '저장소 언어로 변환하는 중', tone: 'note', word: '검사 중' });
      else { const ok = c.translations.filter((t) => t.ok), bad = c.translations.filter((t) => !t.ok);
        out.push(ok.length ? { say: `${ok.length}개 저장소 언어로 변환됨`, sub: bad.length ? `변환하지 못한 언어 ${bad.map((t) => t.label).join(', ')}` : '', tone: bad.length ? 'warn' : 'ok', word: bad.length ? '확인 필요' : '' } : { say: '어느 저장소 언어로도 변환되지 않음', sub: (bad[0] || {}).error || '', tone: 'bad' });
        out.push((c.masked || []).length ? { say: `반환 속성에 마스킹 대상 ${c.masked.length}개`, sub: `${c.masked.join(', ')} · 접근 정책에 따라 가려집니다`, tone: 'note' } : { say: '반환 속성에 마스킹 대상 없음', tone: 'ok' });
        if ((c.params || []).length) out.push({ say: `입력값 ${c.params.length}개`, sub: c.params.join(', '), tone: 'note' }); }
      let start = d.start;
      if (d.mode === 'json') { try { start = Object.values(JSON.parse(d.json).match || {})[0] || ''; } catch (e) { start = ''; } }
      const o = bndObj(m, start);
      if (o) out.push(o.table ? { say: '시작 Entity의 매핑 명세 있음', sub: `${o.label || o.name} · ${o.table}`, tone: 'ok' } : { say: '시작 Entity가 아직 테이블에 바인딩되지 않음', sub: 'Entity 바인딩에서 테이블을 고르면 실행할 수 있습니다', tone: 'warn', word: '확인 필요' });
      if (noSource()) out.push({ say: '실행은 데이터 소스 연결 후', tone: 'note' });
      return out;
    },
    valid: (d, x) => (x && !x.editable ? '모듈이 정의한 쿼리는 여기서 바꿀 수 없습니다. 사본으로 새 쿼리를 만들어 주세요.' : !d.label.trim() ? '이름을 입력해 주세요.' : !d.name.trim() ? '키를 입력해 주세요.' : ''),
    save: async (d, x) => {
      const ir = bndQIr(d), name = d.name.trim();
      const ops = x ? [['update_query', { name, label: d.label.trim(), description: d.description.trim(), query: ir }]]
        : [['new_query', { name, label: d.label.trim(), description: d.description.trim(), query: ir }]];
      await bndEdits(ops);
      Object.assign(S.bnd.q, { st: null, sel: name, tr: null, run: null });
      return { element: `query:${name}`, go: `query?sel=${encodeURIComponent(name)}` };
    },
    uses: async (x) => [...x.questions.length ? [{ say: `검증 질문 ${x.questions.length}개`, sub: `${x.questions.slice(0, 3).join(', ')} · 값 조회형 질문이 이 쿼리를 사용`, href: 'check' }] : [],
      ...x.roles.length ? [{ say: `접근 정책 ${x.roles.length}개`, sub: `${x.roles.map((r) => r.label).join(', ')}의 실행 범위`, href: 'roles' }] : []],
    remove: async (x) => { await bndEdits([['delete_query', { name: x.name }]]); Object.assign(S.bnd.q, { st: null, sel: '', tr: null, run: null }); },
  });
  Object.assign(INPUT, {
    bndQStart: (t) => { Object.assign(S.it.d, { start: t.value, link: '', fields: [], conds: [], order: null }); render(); },
    bndQLink: (t) => { const d = S.it.d; d.link = t.value; d.fields = d.fields.filter((f) => f.startsWith('x.')); d.conds = d.conds.filter((c) => !c.prop.startsWith('y.')); render(); },
  });
  Object.assign(ACT, { bndQMode: (t) => {
    const d = S.it.d, to = t.dataset.m;
    if (!d || d.mode === to) return;
    if (to === 'json') { try { d.json = JSON.stringify(bndQIr(d), null, 2); } catch (e) { /* the text stays as it is */ } d.mode = 'json'; }
    else { let b = null; try { b = bndQForm(JSON.parse(d.json)); } catch (e) { b = null; }
      if (!b) { toast('이 쿼리 정의는 양식으로 옮길 수 없습니다. 집계나 여러 관계를 쓰는 쿼리는 JSON으로 고칩니다.', true); return; }
      Object.assign(d, b, { mode: 'form' }); }
    render();
  } });

  // ---- 액션: what it takes, what must hold, what it changes, who lets it through ---------------------------------------
  const bndTyped = (x) => (x === 'true' ? true : x === 'false' ? false : (x !== '' && !Number.isNaN(Number(x)) ? Number(x) : x));
  item('act', {
    word: '액션', under: 'actions', list: 'actions', load: bndReady, history: bndHist('act'),
    hint: '액션에서 ‘+ 액션’을 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    find: (id) => { const m = bndM(); return (m && m.actions.find((a) => a.name === id)) || null; },
    code: (a) => a.name, name: (a) => a.label, element: (a) => `action:${a.name}`,
    draft: (a) => {
      const m = bndM();
      if (!a) return { name: '', label: '', target: (m.objects.find((o) => !o.concept) || m.objects[0] || {}).name || '', params: [], criteria: [], transition_to: '', approval: 'always', limits: [], agents: false, set: [], method: 'POST', url: '', body: '', undo_url: '', cite: '', keep: [], call0: {}, undo0: {}, reason: '' };
      const limits = (a.auto_within || []).flatMap((l) => LIMIT_KIND.filter(([k]) => k in l).map(([k]) => ({ subject: l.property ? `p:${l.property}` : `i:${l.parameter}`, kind: k, value: String(l[k]) })));
      const call = a.call || {}, undo = a.undo || {};
      return { name: a.name, label: a.label, target: a.target, params: a.parameters.map((p) => ({ ...p })),
        criteria: a.criteria.filter((c) => c.decision).flatMap((c) => Object.entries(c.expect).map(([field, value]) => ({ decision: c.decision, field, value: String(value) }))),
        transition_to: a.transition_to || '', approval: limits.length ? 'limit' : a.approval ? 'always' : 'auto', limits, agents: !!a.auto_agents,
        set: Object.entries(a.set || {}).map(([prop, value]) => ({ prop, value: String(value) })), method: call.method || 'POST', url: call.url || '',
        body: call.body === undefined ? '' : (typeof call.body === 'string' ? call.body : JSON.stringify(call.body)), undo_url: undo.url || '', cite: a.cite || '',
        keep: a.criteria.filter((c) => !c.decision), call0: call, undo0: undo, reason: '' };
    },
    form: (d, x) => {
      const m = bndM(), machine = m.states.find((s) => s.object === d.target);
      const props = bndOwn(m, d.target).filter((p) => !p.expr && !p.key);
      const decisions = [['', '규칙 선택'], ...m.decisions.filter((y) => y.target === d.target).map((y) => [y.name, y.label])];
      const outs = (r) => { const y = m.decisions.find((z) => z.name === r.decision); return y ? y.outputs.filter((o) => o.name !== 'reason') : []; };
      const expect = (r, i) => { const o = outs(r).find((y) => y.name === r.field); return o && o.type === 'boolean' ? bndRowSel('criteria', i, 'value', [['true', '가능'], ['false', '불가']], r.value) : bndRowIn('criteria', i, 'value', r.value, ' placeholder="기대값"'); };
      const subjects = [['', '기준 선택'], ...props.filter((p) => ['integer', 'decimal'].includes(p.type)).map((p) => [`p:${p.name}`, `Property · ${p.label || p.name}`]), ...d.params.filter((p) => p.name).map((p) => [`i:${p.name}`, `파라미터 · ${p.label || p.name}`])];
      const roles = x ? m.roles.map((r) => { const v = [bndCan(r, 'request', x.name) ? '요청' : '', bndCan(r, 'execute', x.name) ? '실행' : ''].filter(Boolean); return v.length ? `${r.name} ${v.join(' · ')}` : ''; }).filter(Boolean).join(' · ') : '';
      const card = (title, add, body, foot = '') => `<section class="k-card"><div class="k-ch"><h2>${title}</h2>${add}</div>${body}${foot ? `<p class="k-cf line">${foot}</p>` : ''}</section>`;
      const tbl = (heads, rows, none) => (rows ? `<div class="k-x"><table class="k-t"><thead><tr>${heads.map((h) => `<th scope="col">${h}</th>`).join('')}<th scope="col"></th></tr></thead><tbody>${rows}</tbody></table></div>` : `<p class="k-cf line">${none}</p>`);
      return `${bndBase(`${bndFld('이름', bndIn('label', d.label, ' placeholder="예: 반품 신청"'))}${bndFld('키', bndIn('name', d.name, ` class="k-in mono" placeholder="예: requestReturn"${x ? ' disabled' : ''}`))}
          ${bndFld('대상 Entity', `<select class="k-in" data-in="bndActTarget"${x ? ' disabled' : ''}>${m.objects.map((o) => bndOpt(o.name, bndEnt(o), d.target)).join('')}</select>`)}
          ${bndFld('처리 후 상태', machine ? `<select class="k-in" data-in="itf" data-k="transition_to"><option value="">변경 없음</option>${machine.states.map((s) => bndOpt(s, s, d.transition_to)).join('')}</select>` : '<select class="k-in" disabled><option>대상 Entity에 상태 전이가 없습니다</option></select>', '엔티티 관리의 상태 전이와 연결')}
          ${bndFld('승인 기준', `<select class="k-in" data-in="itf" data-k="approval" data-re>${[['always', '항상 승인'], ['auto', '항상 자동'], ['limit', '기준 안이면 자동 · 그 외 승인']].map(([v, w]) => bndOpt(v, w, d.approval)).join('')}</select>`)}
          ${bndFld('호출 API', `<div class="bnd-rowed"><select class="k-in" data-in="itf" data-k="method" style="flex:0 0 108px" aria-label="방식">${['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((y) => bndOpt(y, y, d.method)).join('')}</select>${bndIn('url', d.url, ' class="k-in mono" placeholder="https://service.example/claims/$key" aria-label="호출 주소"')}</div>`, '비워 두면 원천 값만 바꿉니다')}
          ${x ? bndFld('허용 접근 정책', `<input class="k-in" type="text" value="${esc(roles || '없음')}" disabled>`, '접근 정책에서 정합니다') : ''}
          <div class="k-full">${bndFld('근거', bndIn('cite', d.cite, ' placeholder="예: 반품 정책서 v1.2 4조"'))}</div>`)}
        ${card('파라미터', bndRowAdd('params', '파라미터'), tbl(['이름', '타입', '설명'], d.params.map((r, i) => `<tr><td>${bndRowIn('params', i, 'name', r.name, ' placeholder="영문 이름" style="font-family:var(--mono)"')}</td><td>${bndRowSel('params', i, 'type', TYPES.filter((y) => y !== 'enum').map((y) => [y, TYPE_WORD[y]]), r.type)}</td><td>${bndRowIn('params', i, 'label', r.label, ' placeholder="설명"')}</td><td>${bndRowDel('params', i)}</td></tr>`).join(''), '파라미터 없이 대상만 정해 요청합니다.'))}
        ${card('전제조건 규칙', bndRowAdd('criteria', '전제조건'), tbl(['규칙', '결과', '기대값'], d.criteria.map((r, i) => `<tr><td>${bndRowSel('criteria', i, 'decision', decisions, r.decision, true)}</td><td>${bndRowSel('criteria', i, 'field', [['', '결과 선택'], ...outs(r).map((o) => [o.name, outWord(m.decisions.find((y) => y.name === r.decision), o.name)])], r.field, true)}</td><td>${expect(r, i)}</td><td>${bndRowDel('criteria', i)}</td></tr>`).join(''), '전제조건 없이 요청합니다.'), '시멘틱 매니저의 규칙 가운데 대상 Entity를 판정하는 것 · 요청할 때와 실행 직전에 다시 판정합니다')}
        ${card('변경 값', bndRowAdd('set', '변경 값'), tbl(['Property', '값'], d.set.map((r, i) => `<tr><td>${bndRowSel('set', i, 'prop', [['', 'Property 선택'], ...props.map((p) => [p.name, p.label || p.name])], r.prop)}</td><td>${bndRowIn('set', i, 'value', r.value, ' placeholder="값 또는 $파라미터"')}</td><td>${bndRowDel('set', i)}</td></tr>`).join(''), '상태 말고 바꾸는 값이 없습니다.'))}
        ${d.approval === 'limit' ? card('자동 승인 기준', bndRowAdd('limits', '기준'), tbl(['기준', '방식', '값'], d.limits.map((r, i) => `<tr><td>${bndRowSel('limits', i, 'subject', subjects, r.subject)}</td><td>${bndRowSel('limits', i, 'kind', LIMIT_KIND, r.kind)}</td><td>${bndRowIn('limits', i, 'value', r.value, ' placeholder="값 또는 @기준값"')}</td><td>${bndRowDel('limits', i)}</td></tr>`).join(''), '기준을 하나 이상 추가합니다.')
          + `<div class="k-cb" style="padding-top:12px"><label class="k-ck mid"><input type="checkbox" data-in="itf" data-k="agents"${d.agents ? ' checked' : ''}>Agent 요청도 기준 안이면 자동 실행</label></div>`, '기준을 모두 충족하고 실행 권한이 있으면 바로 실행합니다. 기준을 넘으면 승인 대기로 접수합니다') : ''}
        ${d.url.trim() ? `<section class="k-card"><div class="k-ch"><h2>호출 본문 · 되돌리기</h2></div><div class="k-cb">${bndFld('요청 본문', bndIn('body', d.body, ' class="k-in mono" placeholder="JSON, $key · $파라미터 · $after.Property 참조"'))}${bndFld('되돌리기 호출 주소', bndIn('undo_url', d.undo_url, ' class="k-in mono"'), '비워 두면 외부 호출을 실행한 요청은 되돌릴 수 없습니다')}</div></section>` : ''}`;
    },
    checks: (d, x) => {
      const m = bndM(), out = [];
      if (!x && d.name && !IDENT.test(d.name)) out.push({ say: '키는 영문자로 시작하고 영문자 · 숫자 · _ 만', sub: d.name, tone: 'bad' });
      if (!x && d.name && m.actions.some((a) => a.name === d.name)) out.push({ say: '같은 키의 액션이 이미 있음', sub: d.name, tone: 'bad' });
      const used = d.criteria.filter((c) => c.decision);
      const half = used.filter((c) => !c.field);
      const draft = [...new Set(used.map((c) => c.decision))].filter((n) => !S.st.decisions.some((y) => y.name === n));
      if (half.length) out.push({ say: '결과를 고르지 않은 전제조건이 있음', tone: 'bad' });
      out.push(!used.length ? { say: '전제조건 없이 요청', tone: 'note' } : draft.length ? { say: '아직 배포하지 않은 규칙을 전제조건으로 사용', sub: draft.join(', '), tone: 'warn', word: '확인 필요' } : { say: '전제조건 규칙이 모두 배포된 버전에 있음', tone: 'ok' });
      if (d.params.some((p) => p.name && !IDENT.test(p.name))) out.push({ say: '파라미터 이름은 영문자 · 숫자 · _ 만', tone: 'bad' });
      if (d.approval === 'limit' && !d.limits.some((l) => l.subject && l.value !== '')) out.push({ say: '자동 승인 기준이 비어 있음', sub: '기준이 없으면 항상 승인으로 저장합니다', tone: 'warn', word: '확인 필요' });
      out.push(d.url.trim() ? { say: '호출 API 있음', sub: `${d.method} ${d.url.trim()}`, tone: 'ok' } : { say: '호출 API 없음 · 원천 값만 바꿈', tone: 'note' });
      if (noSource()) out.push({ say: '실제 실행은 데이터 소스 연결 후', tone: 'note' });
      return out;
    },
    valid: (d) => (!d.label.trim() ? '이름을 입력해 주세요.' : !d.name.trim() ? '키를 입력해 주세요.' : !d.target ? '대상 Entity를 골라 주세요.' : ''),
    save: async (d, x) => {
      const name = d.name.trim();
      const parameters = Object.fromEntries(d.params.filter((p) => p.name).map((p) => [p.name.trim(), { type: p.type || 'string', label: p.label || p.name }]));
      const by = {};
      d.criteria.filter((c) => c.decision && c.field).forEach((c) => { (by[c.decision] = by[c.decision] || {})[c.field] = bndTyped(c.value); });
      const parts = {};
      d.limits.filter((l) => l.subject && l.value !== '').forEach((l) => { (parts[l.subject] = parts[l.subject] || { [l.subject[0] === 'p' ? 'property' : 'parameter']: l.subject.slice(2) })[l.kind] = String(l.value).startsWith('@') ? l.value : Number(l.value); });
      const limits = Object.values(parts);
      const asBody = (v) => { try { return JSON.parse(v); } catch (e) { return v; } };
      const call = d.url.trim() ? { ...(d.call0 || {}), url: d.url.trim(), method: d.method, ...(d.body ? { body: asBody(d.body) } : {}) } : {};
      const undo = d.url.trim() && d.undo_url.trim() ? { ...(d.undo0 || {}), url: d.undo_url.trim(), method: (d.undo0 || {}).method || 'POST' } : {};
      const set = Object.fromEntries(d.set.filter((r) => r.prop).map((r) => [r.prop, String(r.value).startsWith('$') ? r.value : bndTyped(r.value)]));
      const args = { name, label: d.label.trim(), parameters, set, call, undo, criteria: [...Object.entries(by).map(([decision, expect]) => ({ decision, expect })), ...(d.keep || [])],
        transition_to: d.transition_to || '', approval: d.approval === 'limit' && limits.length ? { auto_within: limits, agents: !!d.agents } : d.approval !== 'auto', cite: d.cite.trim() };
      await bndEdits([x ? ['update_action', args] : ['add_action', { ...args, target: d.target }]]);
      Object.assign(S.bnd.act, { sel: name, res: null });
      return { element: `action:${name}`, go: `actions?action=${encodeURIComponent(name)}` };
    },
    uses: async (a) => {
      const m = bndM(), may = m.roles.filter((r) => bndCan(r, 'request', a.name) || bndCan(r, 'execute', a.name));
      const moves = m.states.flatMap((s) => (s.transitions || []).filter((t) => t.action === a.name).map((t) => `${s.label} ${t.from} → ${t.to}`));
      return [may.length ? { say: `접근 정책 ${may.length}개`, sub: `${may.map((r) => r.label || r.name).join(', ')}의 요청 · 실행 범위`, href: 'roles' } : null,
        moves.length ? { say: `상태 전이 ${moves.length}개`, sub: `${moves.slice(0, 2).join(', ')}${moves.length > 2 ? ` 외 ${moves.length - 2}` : ''}이 이 액션으로 넘어갑니다`, href: 'states' } : null].filter(Boolean);
    },
    remove: async (a) => { await bndEdits([['delete_action', { name: a.name }]]); Object.assign(S.bnd.act, { sel: '', res: null }); },
  });
  Object.assign(INPUT, { bndActTarget: (t) => { Object.assign(S.it.d, { target: t.value, criteria: [], set: [], limits: [], transition_to: '' }); render(); } });
