  // ==== Data Binding: 데이터 소스 · Mapping (Entity Binding 51, 질의 52, Action 53, 항목 화면 54) ======================
  // An Entity is bound when it names a table; a Property is mapped when its Entity is bound and it reads a column.
  // With a source connected the binding is checked against the real tables; with none it is a specification.

  S.bnd = {
    db: { way: 'dsn', kind: 'postgres', name: '', host: '', port: '', database: '', user: '', pw: '', path: '', test: null, testing: false },
    map: { area: null, sel: '' },
    bind: { sel: '', q: '', fold: {}, tab: 'base', sql: null, prof: null, d: null },
    q: { st: null, busy: false, err: '', sel: '', find: '', lang: '', run: null, running: false, role: '', principal: {}, params: {}, tr: null },
    act: { sel: '', role: '', key: '', params: {}, inputs: {}, res: null, busy: false },
  };
  Object.assign(OP_WORD, { add_query: '질의 추가', new_query: '질의 추가', update_query: '질의 변경', delete_query: '질의 삭제' });
  // a link (#bind?entity= · #query?sel= · #actions?action=) picks what it names each time it is followed; a pick made by
  // hand on the screen holds until the address changes
  window.addEventListener('hashchange', () => { S.bnd.bind.asked = ''; S.bnd.q.asked = ''; S.bnd.act.asked = ''; });

  const bndM = () => (S.mg.st && !S.mg.st.error ? S.mg.st : null);
  // text with no size of its own is 16px on these screens, as the screen plan draws it
  const bndPg = (html) => `<div class="bnd-pg">${html}</div>`;
  let bndWaiting = 0;
  // the columns each Property reads, as the server resolves them (a Property taken from a parent Entity may read another column)
  function bndColsLoad() {
    const sig = bndSig();
    if (S.bnd.colsBusy) return S.bnd.colsBusy;
    if (S.bnd.cols && S.bnd.cols.sig === sig) return Promise.resolve();
    S.bnd.colsBusy = api('bnd/columns').then((r) => { S.bnd.cols = { sig, map: r.columns }; }).catch(() => { S.bnd.cols = { sig, map: {} }; })
      .finally(() => { S.bnd.colsBusy = null; if (['db', 'sources', 'bind'].includes(S.tab)) render(); });
    return S.bnd.colsBusy;
  }
  function bndNeed() {  // the definition is read once for every screen: a screen that needs it waits for whoever asked first
    if (S.mg.st && !S.mg.st.error) bndColsLoad();
    if (S.mg.st || bndWaiting) return;
    if (!S.mg.busy) loadManage();
    const tab = S.tab;
    bndWaiting = setInterval(() => { if (!S.mg.st) return; clearInterval(bndWaiting); bndWaiting = 0; if (S.tab === tab) render(); }, 150);
  }
  const bndWait = (title, lead) => (!S.mg.st ? kHead(title, lead) + '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>'
    : S.mg.st.error ? kHead(title, lead) + kEmpty('불러오지 못했습니다', S.mg.st.error) : '');
  const bndEnt = (o) => `${o.label || o.name}@${o.name}`;
  const bndObj = (m, name) => m.objects.find((o) => o.name === name) || null;
  const bndTable = (m, name) => m.sources.source.tables.find((t) => t.table === name) || null;
  // an Entity's Properties, with those it takes from the Entity it specialises: a bound Entity reads them from its own table
  const bndOwn = (m, obj) => m.properties.filter((p) => p.object === obj);
  const bndCols = (p) => { const r = S.bnd.cols && S.bnd.cols.map[`${p.object}.${p.name}`]; return r && r.length ? r : p.columns && p.columns.length ? p.columns : [p.column || p.name]; };
  const bndCol = (p) => bndCols(p).join(' + ');
  const bndHas = (t, col) => !!t && t.columns.some((c) => c.name.toLowerCase() === String(col).toLowerCase());
  // the Objects with their Entities, in the definition's order; Entities under no Object come last
  function bndAreas(m) {
    const out = (m.areas || []).map((a) => ({ name: a.name, label: a.label || a.name, objects: m.objects.filter((o) => o.area === a.name) })).filter((a) => a.objects.length);
    const rest = m.objects.filter((o) => !o.area || !out.some((a) => a.name === o.area));
    if (rest.length) out.push({ name: '', label: 'Object 미지정', objects: rest });
    return out;
  }
  // where a Property stands: none (its Entity has no table), calc (computed), spec (written, not yet checked),
  // ok (the column is in the source), missing (the source has no such column)
  function bndState(m, o, p) {
    if (p.expr) return 'calc';
    if (!o || !o.table) return 'none';
    const t = bndTable(m, o.table);
    if (!t) return 'spec';
    return bndCols(p).every((c) => bndHas(t, c)) ? 'ok' : 'missing';
  }
  const bndHow = (p) => (p.expr ? '계산식' : p.columns && p.columns.length > 1 ? `컬럼 ${p.columns.length}개 결합` : p.transform ? `변환식 · ${p.transform}`
    : (p.values || []).length ? `코드 ${p.values.length}종${Object.keys(p.labels || {}).length ? ' · 변환표' : ''}` : '컬럼 그대로');
  // what the last check of the definition against the source found, by element (object:…, property:…, link:…)
  function bndFound() {
    const r = S.bind, by = {};
    if (r && Array.isArray(r.findings)) r.findings.forEach((f) => { (by[f.element] = by[f.element] || []).push(f); });
    return by;
  }
  // how many places the last check found a difference at, of the kinds named (all when none): every screen counts the same
  const bndDiffs = (kinds) => new Set(((S.bind && S.bind.findings) || []).filter((f) => !kinds || kinds.includes(f.kind)).map((f) => f.element)).size;
  // a check is of the definition it was made on: an edit since makes it old, and the screens say 검사 전 again
  const bndChecked = () => !!(S.bind && S.bind.ok !== undefined && !S.bind.busy && !S.bind.error && !S.bind.no_source && S.bind.sig === bndSig());
  function bndCheckRun() {  // the definition as the pending edits leave it, which is what these screens show
    const sig = bndSig();
    S.bind = { busy: true, sig };
    return api('bnd/check', {}).then((r) => { S.bind = { ...r, sig }; }).catch((e) => { S.bind = { error: e.message, sig }; });
  }
  async function bndCheck() {  // 차이 검사 · Binding 검사: the definition against the source's tables, columns, types, keys and values
    if (noSource()) { toast('연결된 데이터 소스가 없어 대조하지 못했습니다. 데이터 소스를 연결해 주세요.', true); return; }
    const run = bndCheckRun();
    render();
    await run;
    render();
    if (S.bind.error) toast(S.bind.error, true); else toast(`스키마 대조 결과 차이 ${bndDiffs()}건을 확인했습니다.`);
  }
  const bndNoSource = () => `<div class="k-i3 k-14 bnd-status" role="status"><span class="k-chip b">데이터 소스 미연결</span><span class="k-wrap g8 k-push"><a class="k-btn" href="#db">데이터 소스 연결</a>${S.tab === 'sources' ? '' : '<a class="k-btn" href="#sources">Mapping</a>'}</span></div>`;

  // ---- BND-01 데이터 소스 연결 -----------------------------------------------------------------------------------
  const BND_DB_KIND = [['postgres', 'PostgreSQL', 'postgresql', '5432'], ['mysql', 'MySQL', 'mysql', '3306'], ['oracle', 'Oracle', 'oracle', '1521'], ['mssql', 'SQL Server', 'mssql', '1433'], ['sqlite', 'SQLite', '', '']];
  const BND_DB_LEAD = '업무 DB와 API를 읽기 전용 데이터 소스로 연결합니다.';

  // the tables the definition names (an Entity's table, the table a Relation is read from) and the tables the source has
  function bndTableRows(m) {
    const src = m.sources.source, rows = new Map();
    const row = (name) => { if (!rows.has(name)) rows.set(name, { table: name, ents: [], links: [], cols: 0, real: null, used: false }); return rows.get(name); };
    m.objects.filter((o) => o.table).forEach((o) => { const r = row(o.table); r.ents.push(o); r.cols += bndOwn(m, o.name).filter((p) => !p.expr).length; r.used = true; });
    m.links.filter((l) => l.via && l.via.table).forEach((l) => { const r = row(l.via.table); r.links.push(l); r.cols += new Set([l.via.source || l.via.from, l.via.target || l.via.to].filter(Boolean)).size; r.used = true; });
    src.tables.forEach((t) => { row(t.table).real = t; });
    return [...rows.values()].sort((a, b) => (b.used ? 1 : 0) - (a.used ? 1 : 0) || a.table.localeCompare(b.table));
  }

  function bndDbForm() {
    const D = S.bnd.db, st = S.st;
    const input = (k, word, extra = '') => `<label class="k-f">${word}<input class="k-in" type="${k === 'pw' ? 'password' : 'text'}" data-in="bndDb" data-k="${k}" value="${esc(k === 'pw' ? D.pw : D[k])}"${k === 'pw' ? ' autocomplete="new-password"' : ''}${extra}></label>`;
    if (!isOntoAdmin()) return '<p class="k-note">연결 설정은 온톨로지 관리자 권한이 필요합니다.</p>';
    if (D.way === 'gw') {
      const g = S.gw;
      return `${input('name', '소스 이름', ' placeholder="예: 주문 DB"')}
        <label class="k-f">질의 서비스 주소<input class="k-in" type="text" data-in="gwurl" value="${esc(g.url)}" placeholder="https://platform.example/query"></label>
        <div class="bnd-two"><label class="k-f">연결 번호<input class="k-in" type="text" data-in="gwconn" value="${esc(g.connection)}" placeholder="12"></label>
          <label class="k-f">종류<select class="k-in" data-in="gwdialect">${[['postgres', 'PostgreSQL'], ['mysql', 'MySQL'], ['oracle', 'Oracle']].map(([k, l]) => `<option value="${k}"${g.dialect === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label></div>
        <label class="k-f">접속 토큰<input class="k-in" type="password" data-in="gwtoken" value="${esc(g.token)}" autocomplete="off"></label>`;
    }
    if (!st.data.connect) return `<div class="k-h"><span class="k-chip">DB 연결 · 서버 설정</span><a class="k-btn k-push" href="#catalog">${ki('upload', 16, 1.75)}자료 업로드</a></div>`;
    const kind = BND_DB_KIND.find((x) => x[0] === D.kind) || BND_DB_KIND[0];
    const body = D.kind === 'sqlite' ? input('path', '파일 경로', ' placeholder="예: /data/shop.db"')
      : `<div style="display:grid;grid-template-columns:2fr 1fr;gap:8px">${input('host', '호스트', ' placeholder="db-ro.example.com"')}${input('port', '포트', ` placeholder="${kind[3]}"`)}</div>
        <div class="bnd-two">${input('user', '읽기 전용 계정')}${input('pw', '비밀번호')}</div>`;
    return `${input('name', '소스 이름', ' placeholder="예: 주문 DB"')}
      <div class="bnd-two"><label class="k-f">종류<select class="k-in" data-in="bndDbKind">${BND_DB_KIND.map(([k, l]) => `<option value="${k}"${D.kind === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label>${D.kind === 'sqlite' ? '<span></span>' : input('database', '데이터베이스')}</div>
      ${body}`;
  }

  function bndDbView() {
    const st = S.st, src = st.source || {}, on = !!src.connected, D = S.bnd.db, m = bndM();
    const canAdd = isOntoAdmin() && (D.way === 'gw' || st.data.connect);
    const head = kHead('데이터 소스', BND_DB_LEAD, `${on ? `<button class="k-btn" data-act="bndDbTest"${D.testing ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${D.testing ? '테스트 중' : '연결 테스트'}</button>` : ''}${canAdd ? `<button class="k-btn pri" data-act="bndDbConnect"${S.dr.busy ? ' disabled' : ''}>${ki('plug', 16, 1.75)}${S.dr.busy ? '연결 중' : '데이터 소스 추가'}</button>` : ''}`);
    const store = D.test && D.test.stores ? D.test.stores.find((b) => b.source) : null;
    const origin = st.origin || {};
    const what = origin.kind === 'files' ? '업로드 데이터' : '업무 DB';
    const sub = on ? `${BACKEND_KIND[src.kind] || src.kind} 읽기 전용 · ${origin.detail || origin.label || src.name}${store ? (store.state === 'ok' ? ` · 응답 ${store.ms}ms` : ` · ${store.error || '응답 없음'}`) : ''}` : '연결된 데이터 소스 없음';
    const pipes = st.pipelines.length > 1 ? `<div class="k-h"><label class="k-f" style="flex:0 1 320px">데이터<select class="k-in sm" data-in="bndPipe" aria-label="데이터 선택">${st.pipelines.map((p, i) => `<option value="${esc(p.id)}"${p.id === st.pipeline ? ' selected' : ''}>${esc(i === 0 ? '기본 데이터' : p.label)}</option>`).join('')}</select></label>${st.pipeline !== 'p1' && isOntoAdmin() ? '<button class="k-lnk bad" data-act="bndPipeDrop" style="align-self:flex-end">데이터 삭제</button>' : ''}</div>` : '';
    const band = `<section class="k-wrap g16" aria-labelledby="bnd-src-h" style="align-items:stretch">
      <div class="k-v bnd-src${on ? ' on' : ''}"><div class="k-pha"><span class="bnd-ico">${ki('db', 20, 1.75)}</span><div class="k-g0"><h2 class="k-h2" id="bnd-src-h">${what} · ${on ? '연결됨' : '미연결'}</h2><p class="k-s" style="margin:0">${esc(sub)}</p></div><span class="k-chip">L2 · L3</span></div>${pipes}</div>
      <div class="k-card pad k-v" style="flex:1 1 280px"><p class="k-h2" style="margin:0">연결 방식</p>
        <label class="k-ck" style="font-size:16px"><input type="radio" name="bndway" value="dsn" data-in="bndDbWay"${D.way === 'dsn' ? ' checked' : ''}><span>DB 읽기 전용 계정</span></label>
        <label class="k-ck" style="font-size:16px"><input type="radio" name="bndway" value="gw" data-in="bndDbWay"${D.way === 'gw' ? ' checked' : ''}><span>API 호출 · 질의 서비스</span></label></div></section>`;
    let scope = '<section class="k-card pad" style="flex:2 1 560px"><p class="k-p s">불러오는 중입니다.</p></section>';
    if (m) {
      const rows = bndTableRows(m), named = rows.filter((r) => r.used).length;
      const obj = (r) => { const names = [...new Set(r.ents.map((o) => o.area_label || o.label || o.name))], rels = r.links.map((l) => l.label || l.name);
        return names.length || rels.length ? esc([...names, ...(rels.length ? [`Relation ${rels.join(', ')}`] : [])].join(' · ')) : '<span class="k-mut">-</span>'; };
      const real = (r) => (!on ? '<span class="k-mut">미연결</span>' : r.real ? `${r.real.columns.length}컬럼 · ${show(r.real.rows)}행` : '<span class="k-chip warn">테이블 없음</span>');
      const read = (r) => (r.used ? '<span class="k-chip ok">사용</span>' : canEdit() ? `<a class="k-lnk" href="#entity-form?table=${encodeURIComponent(r.table)}">+ Entity</a>` : '<span class="k-chip">미사용</span>');
      scope = `<section class="k-card" aria-labelledby="bnd-tb-h" style="flex:2 1 560px"><div class="k-h g12" style="padding:16px 20px"><h2 class="k-h2" id="bnd-tb-h">테이블 범위</h2><span class="k-chip">정의 ${named}</span><span class="k-s k-push">${on ? `실제 스키마 ${m.sources.source.tables.length}개 테이블` : ''}</span></div>
        ${rows.length ? `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">테이블</th><th scope="col">대응 Object</th><th class="r" scope="col">정의서</th><th scope="col" class="bnd-dashl">실제 스키마</th><th scope="col">사용</th></tr></thead><tbody>
          ${rows.map((r) => `<tr><td class="k-code">${esc(r.table)}</td><td>${obj(r)}</td><td class="r">${r.used ? r.cols : '<span class="k-mut">-</span>'}</td><td class="bnd-dashl${on && r.real ? '' : ' mut'}">${real(r)}</td><td>${read(r)}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="k-cf line">테이블이 지정된 Entity가 없습니다.</p>'}
        </section>`;
    }
    const got = on && bndChecked();
    const after = (title, value, href) => `<div class="k-v g4 k-14" style="flex:1 1 220px"><b class="k-b">${title}</b>${value ? `<a class="k-13" href="#${href}">${value}</a>` : `<span class="k-s">${on ? '대조 전' : '미연결'}</span>`}</div>`;
    const checks = `<section class="k-v g12 bnd-dash" aria-labelledby="bnd-af-h"><div class="k-h"><h2 class="k-h2" id="bnd-af-h">연결 점검</h2>${on ? `<button class="k-lnk k-push" data-act="bndCheckNow"${S.bind && S.bind.busy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.bind && S.bind.busy ? '대조 중' : got ? '다시 대조' : '대조 실행'}</button>` : ''}</div>
      <div class="k-wrap">${after('스키마 ↔ 정의서 차이', got ? `차이 ${bndDiffs(['table', 'column', 'type'])}건` : '', 'bind')}
        ${after('코드값 실제 분포', got ? `정의에 없는 값 ${bndDiffs(['enum'])}건` : '', 'sources')}
        ${after('Mapping 명세 확인', got ? `컬럼 ${S.bind.checked.columns}개 · 데이터 점검 ${S.bind.checked.data_checks}건` : '', 'sources')}
        ${after('판정 일치율', on ? '검증' : '', 'flow')}</div></section>`;
    return bndPg(`${head}${band}<div class="k-cols"><section class="k-card pad k-v g12" aria-labelledby="bnd-cf-h" style="flex:1 1 340px"><h2 class="k-h2" id="bnd-cf-h">연결 정보</h2>${bndDbForm()}</section>${scope}</div>${checks}
      ${kNext([['sources', 'Mapping'], ['query', '질의'], ['roles', '접근 정책'], ['adapters', '저장소 · 엔진'], ['flow', '검증']])}`);
  }

  screen('db', { area: 'work', word: '데이터 소스', view: bndDbView, after: bndNeed });

  Object.assign(INPUT, {
    bndDb: (t) => { S.bnd.db[t.dataset.k] = t.value; },
    bndDbKind: (t) => { S.bnd.db.kind = t.value; render(); },
    bndDbWay: (t) => { S.bnd.db.way = t.value; render(); },
    bndPipe: (t) => pipelineCall({ op: 'use', id: t.value }),
  });
  Object.assign(ACT, {
    bndDbTest: async () => {
      const D = S.bnd.db;
      D.testing = true; render();
      try {
        D.test = await api('connections');
        const b = D.test.stores.find((x) => x.source);
        toast(b ? (b.state === 'ok' ? '데이터 소스 연결을 확인했습니다.' :'데이터 소스가 응답하지 않아 연결을 확인하지 못했습니다. 연결 정보를 확인해 주세요.') : '연결된 데이터 소스가 없어 테스트하지 못했습니다. 데이터 소스를 연결해 주세요.', !!b && b.state !== 'ok');
      } catch (e) { fail(e); }
      D.testing = false; render();
    },
    bndDbConnect: () => {
      const D = S.bnd.db;
      S.dr.label = D.name.trim();
      if (D.way === 'gw') {
        if (!S.gw.url.trim() || !S.gw.connection.trim()) { toast('질의 서비스 주소와 연결 번호가 없어 연결하지 못했습니다. 주소와 연결 번호를 입력해 주세요.', true); return; }
        ACT.gwconnect();
        return;
      }
      const kind = BND_DB_KIND.find((x) => x[0] === D.kind);
      let dsn = D.path.trim();
      if (D.kind !== 'sqlite') {
        if (!D.host.trim() || !D.database.trim()) { toast('호스트와 데이터베이스가 없어 연결하지 못했습니다. 호스트와 데이터베이스를 입력해 주세요.', true); return; }
        const who = D.user ? `${encodeURIComponent(D.user)}${D.pw ? `:${encodeURIComponent(D.pw)}` : ''}@` : '';
        dsn = `${kind[2]}://${who}${D.host.trim()}${D.port.trim() ? `:${D.port.trim()}` : ''}/${encodeURIComponent(D.database.trim())}`;
      } else if (!dsn) { toast('SQLite 파일 경로가 없어 연결하지 못했습니다. 파일 경로를 입력해 주세요.', true); return; }
      // the password stays in its field until the source is connected, so a second try sends what the field shows
      S.dr.dsn = dsn;
      filesCall('connect', { dsn, label: S.dr.label, rules: S.dr.rules }, () => { D.pw = ''; startDraft(); location.hash = '#data'; });
    },
    bndPipeDrop: () => {
      const p = S.st.pipelines.find((x) => x.id === S.st.pipeline);
      if (p && window.confirm(`${p.label} 데이터를 삭제합니다. 이 데이터로 만든 정의와 연결도 함께 삭제됩니다.`)) pipelineCall({ op: 'delete', id: p.id });
    },
    bndCheckNow: () => bndCheck(),
  });

  // ---- BND-02 Mapping ---------------------------------------------------------------------------------------
  const BND_MAP_LEAD = 'Property와 소스 컬럼 · 코드값 · 변환식의 Mapping을 관리합니다.';
  const bndMapId = (p) => `${p.object}.${p.name}`;
  // one row a Property: where it reads from, how, and where the reading stands
  function bndMapRow(m, by, p) {
    const o = bndObj(m, p.object), state = bndState(m, o, p), found = by[`property:${p.object}.${p.name}`] || [];
    const bad = found[0];
    const mark = state === 'none' ? ['', '테이블 미지정'] : state === 'calc' ? ['', '계산 Property'] : bad ? ['warn', FINDING[bad.kind] || bad.kind]
      : state === 'missing' ? ['warn', '컬럼 없음'] : state === 'ok' ? ['ok', bndChecked() ? '값 확인됨' : '스키마 확인됨'] : ['b', '명세'];
    return { p, o, state, found, mark, id: bndMapId(p), name: `${o ? o.label || o.name : p.object}.${p.label || p.name}`, source: o && o.table && !p.expr ? `${o.table}.${bndCol(p)}` : '' };
  }

  function bndMapView() {
    const wait = bndWait('Mapping', BND_MAP_LEAD);
    if (wait) return wait;
    const m = bndM(), M = S.bnd.map, by = bndFound(), on = !noSource();
    const areas = bndAreas(m);
    if (M.area === null || !areas.some((a) => a.name === M.area)) M.area = (areas.find((a) => a.objects.some((o) => o.table)) || areas[0] || { name: '' }).name;
    const every = m.objects.flatMap((o) => bndOwn(m, o.name)).map((p) => bndMapRow(m, by, p));
    const spec = every.filter((r) => ['spec', 'ok', 'missing'].includes(r.state));
    const core = every.filter((r) => r.state !== 'calc');
    const codes = spec.filter((r) => (r.p.values || []).length);
    const diff = every.filter((r) => r.mark[0] === 'warn');
    const area = areas.find((a) => a.name === M.area) || { objects: [] };
    const rows = area.objects.flatMap((o) => bndOwn(m, o.name)).map((p) => bndMapRow(m, by, p));
    const sel = every.find((r) => r.id === M.sel) || null;
    // a computed Property reads no column: it has no Mapping to edit, and its formula is changed on its Entity
    const bar = !sel ? '' : sel.state === 'calc' ? kBar('선택한 Property', sel.name, `계산식 · ${sel.p.expr}`, `<a class="k-btn" href="#objects?entity=${encodeURIComponent(sel.p.object)}">${ki('doc', 16, 1.75)}Entity</a>`)
      : itemBar('map', sel.id, sel.name, sel.source || '테이블 미지정');
    const stats = `<section class="k-wrap" aria-label="Mapping 현황">
      <div class="k-card bnd-stat"><p class="k-s" style="margin:0">Mapping 명세</p><p class="k-big">${spec.length} <span class="k-mut k-14" style="font-weight:400">/ Property ${core.length}</span></p><p class="k-s" style="margin:4px 0 0">테이블 지정 Entity의 Property</p></div>
      <div class="k-card bnd-stat"><p class="k-s" style="margin:0">코드 Mapping</p><p class="k-big">${codes.length}</p><p class="k-s k-cut" style="margin:4px 0 0">${codes.length ? esc(codes.slice(0, 4).map((r) => r.p.label || r.p.name).join(' · ')) : '허용값 Property'}</p></div>
      ${on && bndChecked() ? `<div class="k-card bnd-stat"><p class="k-s" style="margin:0">실제 값 확인</p><p class="k-big">${spec.filter((r) => r.state === 'ok' && !r.found.length).length}</p><p class="k-s" style="margin:4px 0 0">컬럼 ${S.bind.checked.columns}개 · 데이터 점검 ${S.bind.checked.data_checks}건</p></div>`
    : `<div class="bnd-stat dash"><p class="k-s" style="margin:0">실제 값 확인</p><p class="k-big mut">-</p><p class="k-s" style="margin:4px 0 0">${on ? '차이 검사 전' : '데이터 소스 미연결'}</p></div>`}
      <div class="bnd-stat${diff.length ? ' warn' : ' k-card'}"><p class="k-s" style="margin:0">차이</p><p class="k-big${diff.length ? ' warn' : ''}">${diff.length}</p><p class="${diff.length ? 'k-warn' : 'k-mut'} k-13" style="margin:4px 0 0">${diff.length ? esc([...new Set(diff.map((r) => r.mark[1]))].join(' · ')) : (on ? '정의 ↔ 실제 스키마' : '미연결')}</p></div></section>`;
    const pick = areas.length > 4 ? `<label class="k-push" style="flex:0 1 220px"><span class="k-hide">Object</span><select class="k-in sm" data-in="bndMapArea" aria-label="Object">${areas.map((a) => `<option value="${esc(a.name)}"${a.name === M.area ? ' selected' : ''}>${esc(a.label)}</option>`).join('')}</select></label>`
      : `<div class="k-seg k-push" role="group" aria-label="Object">${areas.map((a) => `<button type="button" class="${a.name === M.area ? 'on' : ''}" data-act="bndMapArea" data-a="${esc(a.name)}">${esc(a.label)}</button>`).join('')}</div>`;
    const tr = (r) => `<tr class="${sel && r.id === sel.id ? 'on' : ''}${r.mark[0] === 'warn' ? ' bnd-diff' : ''}" data-act="bndMapSel" data-id="${esc(r.id)}"><td class="b">${esc(r.name)}</td>
      <td>${r.p.expr ? '<span class="k-mut">계산식</span>' : r.o && r.o.table ? `${esc(r.o.table)} <span class="k-code">${esc(bndCol(r.p))}</span>` : '<span class="k-mut">테이블 미지정</span>'}</td><td>${esc(bndHow(r.p))}</td><td><span class="k-chip${r.mark[0] ? ` ${r.mark[0]}` : ''}">${esc(r.mark[1])}</span></td></tr>`;
    const table = `<section class="k-card" aria-labelledby="bnd-mp-h" style="flex:3 1 600px"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="bnd-mp-h">Mapping 명세</h2>${pick}</div>
      ${rows.length ? `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">Property</th><th scope="col">소스</th><th scope="col">Mapping 방식</th><th scope="col">상태</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div>` : '<p class="k-cf line">Property가 없습니다.</p>'}
      </section>`;
    const first = sel && sel.mark[0] === 'warn' ? sel : diff[0];
    const why = first ? `<section class="k-v bnd-why" aria-labelledby="bnd-df-h"><h2 class="k-15" id="bnd-df-h" style="margin:0;font-weight:600;color:#5E3900">차이 · ${esc(first.name)}</h2>
      <p class="k-14" style="margin:0;line-height:1.55">${esc(first.found[0] ? (FIX[first.found[0].kind] || first.mark[1]) : '소스 테이블에 컬럼이 없습니다. 컬럼 이름을 맞추거나 소스 테이블에 컬럼을 추가해 주세요.')}</p>
      ${first.found[0] && first.found[0].detail ? `<p class="k-code k-13" style="margin:0;white-space:normal">${esc(first.found[0].detail)}</p>` : ''}
      <div class="k-wrap g8">${canEdit() ? `<a class="k-btn" href="${itemHref('map', 'form', first.id)}">Mapping 편집</a>` : ''}<a class="k-lnk" style="color:var(--warn)" href="#bind?row=${encodeURIComponent(`bind:property:${first.id}`)}">Binding 검사 결과</a></div></section>` : '';
    const cp = sel && (sel.p.values || []).length ? sel.p : null;
    const code = cp ? `<section class="k-card" aria-labelledby="bnd-st-h"><div style="padding:16px 20px;border-bottom:1px solid var(--row)"><h2 class="k-h2" id="bnd-st-h">코드 Mapping · ${esc(sel.p.label || sel.p.name)}</h2></div>
      <table class="k-t s"><thead><tr><th scope="col">소스 값</th><th scope="col">표시</th></tr></thead><tbody>${cp.values.map((v) => `<tr><td class="k-code">${esc(v)}</td><td>${esc((cp.labels || {})[v] || '-')}</td></tr>`).join('')}</tbody></table></section>`
      : `<section class="k-card pad k-v"><h2 class="k-h2">코드 Mapping</h2><p class="k-p s">${sel ? '허용값이 없습니다.' : '선택된 Mapping이 없습니다.'}</p></section>`;
    return bndPg(`${kHead('Mapping', BND_MAP_LEAD, `<a class="k-btn" href="#bind">Entity Binding</a><button class="k-btn" data-act="bndCheckNow"${S.bind && S.bind.busy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.bind && S.bind.busy ? '대조 중' : '차이 검사'}</button>${canEdit() ? `<a class="k-btn pri" href="${itemHref('map', 'form')}">${ki('plus', 16, 1.75)}Mapping</a>` : ''}`)}
      ${bar}${on ? '' : bndNoSource()}${stats}<div class="k-cols">${table}<div class="k-c2">${why}${code}</div></div>
      ${kNext([['bind', 'Entity Binding'], ['db', '데이터 소스'], ['objects', 'Entity'], ['lexicon', '용어 사전'], ['query', '질의'], ['actions', 'Action']])}`);
  }

  screen('sources', { area: 'work', word: 'Mapping', view: bndMapView, after: bndNeed });
  Object.assign(ACT, {
    bndMapSel: (t) => { S.bnd.map.sel = S.bnd.map.sel === t.dataset.id ? '' : t.dataset.id; render(); },
    bndMapArea: (t) => { S.bnd.map.area = t.dataset.a; render(); },
  });
  Object.assign(INPUT, { bndMapArea: (t) => { S.bnd.map.area = t.value; render(); } });
