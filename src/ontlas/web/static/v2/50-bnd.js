  // ==== 데이터 바인더: 데이터 소스 연결 · 데이터 매핑 (Entity 바인딩 51, 쿼리 52, 액션 53, 항목 화면 54) ======================
  // An Entity is bound when it names a table; a Property is mapped when its Entity is bound and it reads a column.
  // With a source connected the binding is checked against the real tables; with none it is a specification.

  S.bnd = {
    db: { way: 'dsn', kind: 'postgres', name: '', host: '', port: '', database: '', user: '', pw: '', path: '', test: null, testing: false },
    map: { area: null, sel: '' },
    bind: { sel: '', q: '', fold: {}, tab: 'base', sql: null, prof: null, d: null },
    q: { st: null, busy: false, err: '', sel: '', find: '', lang: '', run: null, running: false, role: '', principal: {}, params: {}, tr: null },
    act: { sel: '', role: '', key: '', params: {}, inputs: {}, res: null, busy: false },
  };
  Object.assign(OP_WORD, { add_query: '쿼리 추가', new_query: '쿼리 추가', update_query: '쿼리 변경', delete_query: '쿼리 삭제' });

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
    : (p.values || []).length ? `코드 ${p.values.length}종${Object.keys(p.labels || {}).length ? ' · 변환표' : ''}` : '직접 매핑');
  // what the last check of the definition against the source found, by element (object:…, property:…, link:…)
  function bndFound() {
    const r = S.bind, by = {};
    if (r && Array.isArray(r.findings)) r.findings.forEach((f) => { (by[f.element] = by[f.element] || []).push(f); });
    return by;
  }
  const bndChecked = () => !!(S.bind && S.bind.ok !== undefined && !S.bind.busy && !S.bind.error && !S.bind.no_source);
  async function bndCheck() {  // 차이 검사 · 바인딩 검사: the definition against the source's tables, columns, types, keys and values
    if (noSource()) { toast('데이터 소스를 연결하면 실제 스키마와 대조합니다.'); return; }
    S.bind = { busy: true };
    render();
    try { S.bind = await api('bindings', {}); } catch (e) { S.bind = { error: e.message }; }
    render();
    if (S.bind.error) toast(S.bind.error, true); else toast(`대조했습니다. 차이 ${(S.bind.findings || []).length}건`);
  }
  const bndNoSource = (say) => `<div class="k-i3 k-14 bnd-status" role="status"><span class="k-chip b">데이터 소스 미연결</span><span style="flex:1 1 420px;min-width:0">${esc(say)}</span><span class="k-wrap g8"><a class="k-btn" href="#db">데이터 소스 연결</a>${S.tab === 'sources' ? '' : '<a class="k-btn" href="#sources">데이터 매핑</a>'}</span></div>`;

  // ---- BND-01 데이터 소스 연결 -----------------------------------------------------------------------------------
  const BND_DB_KIND = [['postgres', 'PostgreSQL', 'postgresql', '5432'], ['mysql', 'MySQL', 'mysql', '3306'], ['oracle', 'Oracle', 'oracle', '1521'], ['mssql', 'SQL Server', 'mssql', '1433'], ['sqlite', 'SQLite', '', '']];
  const BND_DB_LEAD = '업무 DB나 API를 읽기 전용으로 연결합니다. 연결은 L2 · L3(실제 값과 대조)로 가기 위한 것입니다. 연결이 없어도 정의 · 규칙 조회와 판정은 동작합니다.';

  // the tables the definition names and the tables the source has, one row each
  function bndTableRows(m) {
    const src = m.sources.source, rows = new Map();
    const row = (name) => { if (!rows.has(name)) rows.set(name, { table: name, ents: [], cols: 0, real: null }); return rows.get(name); };
    m.objects.filter((o) => o.table).forEach((o) => { const r = row(o.table); r.ents.push(o); r.cols += bndOwn(m, o.name).filter((p) => !p.expr).length; });
    src.tables.forEach((t) => { row(t.table).real = t; });
    return [...rows.values()].sort((a, b) => (b.ents.length ? 1 : 0) - (a.ents.length ? 1 : 0) || a.table.localeCompare(b.table));
  }

  function bndDbForm() {
    const D = S.bnd.db, st = S.st;
    const input = (k, word, extra = '') => `<label class="k-f">${word}<input class="k-in" type="${k === 'pw' ? 'password' : 'text'}" data-in="bndDb" data-k="${k}" value="${esc(k === 'pw' ? D.pw : D[k])}"${k === 'pw' ? ' autocomplete="new-password"' : ''}${extra}></label>`;
    if (!isOntoAdmin()) return '<p class="k-note">연결 설정은 온톨로지 관리자가 합니다. 지금 연결 상태와 테이블 범위는 누구나 볼 수 있습니다.</p>';
    if (D.way === 'gw') {
      const g = S.gw;
      return `${input('name', '소스 이름', ' placeholder="연결 데이터베이스"')}
        <label class="k-f">쿼리 서비스 주소<input class="k-in" type="text" data-in="gwurl" value="${esc(g.url)}" placeholder="https://platform.example/query"></label>
        <div class="bnd-two"><label class="k-f">연결 번호<input class="k-in" type="text" data-in="gwconn" value="${esc(g.connection)}" placeholder="12"></label>
          <label class="k-f">종류<select class="k-in" data-in="gwdialect">${[['postgres', 'PostgreSQL'], ['mysql', 'MySQL'], ['oracle', 'Oracle']].map(([k, l]) => `<option value="${k}"${g.dialect === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label></div>
        <label class="k-f">접속 토큰<input class="k-in" type="password" data-in="gwtoken" value="${esc(g.token)}" autocomplete="off"></label>
        <p class="k-s bnd-fine">플랫폼이 관리하는 DB 연결을 쿼리 서비스로 사용합니다. DB 비밀번호는 필요하지 않고 읽기 전용과 허용 테이블은 플랫폼 정책을 따릅니다. 토큰은 이 세션의 메모리에만 두고 파일에 저장하지 않습니다.</p>`;
    }
    if (!st.data.connect) return `<p class="k-note">이 서버는 DB 주소 연결을 허용하지 않습니다. 서버를 --allow-connect 옵션으로 시작하면 PostgreSQL, MySQL, Oracle, SQL Server, SQLite를 연결할 수 있습니다. 테이블 파일은 자료 업로드로 올립니다.</p>
      <div class="k-h"><a class="k-btn" href="#catalog">${ki('upload', 16, 1.75)}자료 업로드</a></div>`;
    const kind = BND_DB_KIND.find((x) => x[0] === D.kind) || BND_DB_KIND[0];
    const body = D.kind === 'sqlite' ? input('path', '파일 경로', ' placeholder="서버의 SQLite 파일 경로"')
      : `<div style="display:grid;grid-template-columns:2fr 1fr;gap:8px">${input('host', '호스트', ' placeholder="db-ro.example.com"')}${input('port', '포트', ` placeholder="${kind[3]}"`)}</div>
        <div class="bnd-two">${input('user', '읽기 전용 계정')}${input('pw', '비밀번호')}</div>`;
    return `${input('name', '소스 이름', ' placeholder="연결 데이터베이스"')}
      <div class="bnd-two"><label class="k-f">종류<select class="k-in" data-in="bndDbKind">${BND_DB_KIND.map(([k, l]) => `<option value="${k}"${D.kind === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label>${D.kind === 'sqlite' ? '<span></span>' : input('database', '데이터베이스')}</div>
      ${body}
      <p class="k-s bnd-fine">비밀번호는 이 세션의 메모리에만 두고 화면에 다시 표시하지 않습니다. 읽기만 하고 쓰기는 액션으로만 합니다. 연결하면 테이블을 읽어 초안을 만들고, 검토한 뒤 이 온톨로지의 데이터로 적용합니다.</p>`;
  }

  function bndDbView() {
    const st = S.st, src = st.source || {}, on = !!src.connected, D = S.bnd.db, m = bndM();
    const canAdd = isOntoAdmin() && (D.way === 'gw' || st.data.connect);
    const head = kHead('데이터 소스 연결', BND_DB_LEAD, `${on ? `<button class="k-btn" data-act="bndDbTest"${D.testing ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${D.testing ? '테스트 중' : '연결 테스트'}</button>` : ''}${canAdd ? `<button class="k-btn pri" data-act="bndDbConnect"${S.dr.busy ? ' disabled' : ''}>${ki('plug', 16, 1.75)}${S.dr.busy ? '연결 중' : '데이터 소스 연결 추가'}</button>` : ''}`);
    const store = D.test && D.test.stores ? D.test.stores.find((b) => b.source) : null;
    const origin = st.origin || {};
    const what = origin.kind === 'files' ? '업로드 데이터' : '업무 DB';
    const sub = on ? `${BACKEND_KIND[src.kind] || src.kind} 읽기 전용 · ${origin.detail || origin.label || src.name}${store ? (store.state === 'ok' ? ` · 응답 ${store.ms}ms` : ` · ${store.error || '응답 없음'}`) : ''}` : '아직 연결하지 않았습니다';
    const pipes = st.pipelines.length > 1 ? `<div class="k-h"><label class="k-f" style="flex:0 1 320px">데이터<select class="k-in sm" data-in="bndPipe" aria-label="데이터 선택">${st.pipelines.map((p, i) => `<option value="${esc(p.id)}"${p.id === st.pipeline ? ' selected' : ''}>${esc(i === 0 ? '기본 데이터' : p.label)}</option>`).join('')}</select></label>${st.pipeline !== 'p1' && isOntoAdmin() ? '<button class="k-lnk bad" data-act="bndPipeDrop" style="align-self:flex-end">이 데이터 삭제</button>' : ''}</div>` : '';
    const band = `<section class="k-wrap g16" aria-labelledby="bnd-src-h" style="align-items:stretch">
      <div class="k-v bnd-src${on ? ' on' : ''}"><div class="k-pha"><span class="bnd-ico">${ki('db', 20, 1.75)}</span><div class="k-g0"><h2 class="k-h2" id="bnd-src-h">${what} · ${on ? '연결됨' : '미연결'}</h2><p class="k-s" style="margin:0">${esc(sub)}</p></div><span class="k-chip">L2 · L3</span></div>
        <div class="k-wrap"><div class="bnd-say"><b class="k-ok">지금 동작 (연결 없이)</b><br>정의 · 규칙 조회, 값 입력 판정, 정의형 · 판정형 검증, 매핑 명세 작성</div>
          <div class="bnd-say${on ? '' : ' w'}"><b${on ? ' class="k-ok"' : ''}>${on ? '연결되어 열림' : '연결하면 열림'}</b><br>할인가 · 품절 같은 실시간 값, 판정 일치율 · 거래 값 정확도, 스키마 ↔ 정의서 차이 검사</div></div>${pipes}</div>
      <div class="k-card pad k-v" style="flex:1 1 280px"><p class="k-h2" style="margin:0">연결 방식</p>
        <label class="k-ck" style="font-size:16px"><input type="radio" name="bndway" value="dsn" data-in="bndDbWay"${D.way === 'dsn' ? ' checked' : ''}><span>DB 읽기 전용 계정<br><span class="k-s">쓰기는 액션으로만</span></span></label>
        <label class="k-ck" style="font-size:16px"><input type="radio" name="bndway" value="gw" data-in="bndDbWay"${D.way === 'gw' ? ' checked' : ''}><span>API 호출<br><span class="k-s">플랫폼의 쿼리 서비스로 조회 · DB 비밀번호 없이</span></span></label>
        <p class="k-warn k-13" style="margin:0">연결 방식은 데이터마다 하나 · 연결하면 초안 검토를 거쳐 적용합니다</p></div></section>`;
    let scope = '<section class="k-card pad" style="flex:2 1 560px"><p class="k-p s">불러오는 중입니다.</p></section>';
    if (m) {
      const rows = bndTableRows(m), named = rows.filter((r) => r.ents.length).length;
      const obj = (r) => { const names = [...new Set(r.ents.map((o) => o.area_label || o.label || o.name))]; return names.length ? esc(names.join(' · ')) : '<span class="k-mut">-</span>'; };
      const real = (r) => (!on ? '<span class="k-mut">연결 후</span>' : r.real ? `${r.real.columns.length}컬럼 · ${show(r.real.rows)}행` : '<span class="k-chip warn">테이블 없음</span>');
      const read = (r) => (r.ents.length ? '<span class="k-chip ok">읽음</span>' : canEdit() ? `<button class="k-lnk" data-act="mgobjnew" data-t="${esc(r.table)}">Entity로 추가</button>` : '<span class="k-chip">미사용</span>');
      scope = `<section class="k-card" aria-labelledby="bnd-tb-h" style="flex:2 1 560px"><div class="k-h g12" style="padding:16px 20px"><h2 class="k-h2" id="bnd-tb-h">읽을 테이블 범위</h2><span class="k-chip">정의 기준 ${named}</span><span class="k-s k-push">${on ? `실제 스키마 ${m.sources.source.tables.length}개 테이블` : '실제 스키마 열은 연결 후 채워집니다'}</span></div>
        ${rows.length ? `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">테이블</th><th scope="col">대응 Object</th><th class="r" scope="col">정의서</th><th scope="col" class="bnd-dashl">실제 스키마</th><th scope="col">읽기</th></tr></thead><tbody>
          ${rows.map((r) => `<tr><td class="k-code">${esc(r.table)}</td><td>${obj(r)}</td><td class="r">${r.ents.length ? r.cols : '<span class="k-mut">-</span>'}</td><td class="bnd-dashl${on && r.real ? '' : ' mut'}">${real(r)}</td><td>${read(r)}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="k-cf line">테이블에 바인딩한 Entity가 아직 없습니다. Entity 바인딩에서 Entity마다 테이블을 고릅니다.</p>'}
        <p class="k-cf${rows.length ? '' : ' line'}">테이블 · 컬럼 정의서와 공통코드 파일은 상단 ‘자료 업로드’로 받고, <a href="#sources">데이터 매핑</a>에서 명세 자료로 사용합니다 · 마스킹 컬럼은 <a href="#roles">접근 정책</a>을 따릅니다</p></section>`;
    }
    const by = bndFound(), all = Object.values(by).flat(), n = (kinds) => all.filter((f) => kinds.includes(f.kind)).length;
    const got = on && bndChecked();
    const after = (title, say, value, href) => `<div class="k-v g4 k-14" style="flex:1 1 220px"><b class="k-b">${title}</b><span class="k-s">${say}</span>${value ? `<a class="k-13" href="#${href}">${value}</a>` : ''}</div>`;
    const checks = `<section class="k-v g12 bnd-dash" aria-labelledby="bnd-af-h"><div class="k-h"><h2 class="k-h2" id="bnd-af-h">${on ? '연결 점검' : '연결 후 점검'}</h2>${on ? `<button class="k-lnk k-push" data-act="bndCheckNow"${S.bind && S.bind.busy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.bind && S.bind.busy ? '대조 중' : got ? '다시 대조' : '지금 대조'}</button>` : ''}</div>
      <div class="k-wrap">${after('스키마 ↔ 정의서 차이', '정의서에 없는 테이블 · 컬럼, 타입이 다른 컬럼', got ? `차이 ${n(['table', 'column', 'type'])}건` : '', 'bind')}
        ${after('코드값 실제 분포', '정의와 실제 값이 다른 곳', got ? `정의에 없는 값 ${n(['enum'])}건` : '', 'sources')}
        ${after('매핑 명세 확인', '샘플 값으로 Property ↔ 컬럼 매핑 검사', got ? `컬럼 ${S.bind.checked.columns}개 · 데이터 점검 ${S.bind.checked.data_checks}건` : '', 'sources')}
        ${after('판정 일치율', '과거 처리 기록 재계산 · 품질 관리로 전달', on ? '검증에서 보기' : '', 'flow')}</div></section>`;
    return bndPg(`${head}${band}<div class="k-cols"><section class="k-card pad k-v g12" aria-labelledby="bnd-cf-h" style="flex:1 1 340px"><h2 class="k-h2" id="bnd-cf-h">연결 정보</h2>${bndDbForm()}</section>${scope}</div>${checks}
      ${kNext([['sources', '데이터 매핑'], ['query', '연결 후 쿼리 실행'], ['roles', '접근 정책 · 마스킹'], ['adapters', '저장소 · 엔진'], ['flow', '연결 후 검증']])}`);
  }

  screen('db', { area: 'work', word: '데이터 소스 연결', view: bndDbView, after: bndNeed });

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
        toast(b ? (b.state === 'ok' ? `연결을 확인했습니다. 응답 ${b.ms}ms` : `응답이 없습니다. ${b.error || ''}`) : '연결된 데이터 소스가 없습니다.', !!b && b.state !== 'ok');
      } catch (e) { fail(e); }
      D.testing = false; render();
    },
    bndDbConnect: () => {
      const D = S.bnd.db;
      S.dr.label = D.name.trim();
      if (D.way === 'gw') {
        if (!S.gw.url.trim() || !S.gw.connection.trim()) { toast('쿼리 서비스 주소와 연결 번호를 입력해 주세요.', true); return; }
        ACT.gwconnect();
        return;
      }
      const kind = BND_DB_KIND.find((x) => x[0] === D.kind);
      let dsn = D.path.trim();
      if (D.kind !== 'sqlite') {
        if (!D.host.trim() || !D.database.trim()) { toast('호스트와 데이터베이스를 입력해 주세요.', true); return; }
        const who = D.user ? `${encodeURIComponent(D.user)}${D.pw ? `:${encodeURIComponent(D.pw)}` : ''}@` : '';
        dsn = `${kind[2]}://${who}${D.host.trim()}${D.port.trim() ? `:${D.port.trim()}` : ''}/${encodeURIComponent(D.database.trim())}`;
      } else if (!dsn) { toast('SQLite 파일 경로를 입력해 주세요.', true); return; }
      S.dr.dsn = dsn;
      D.pw = '';
      ACT.connect();
    },
    bndPipeDrop: () => {
      const p = S.st.pipelines.find((x) => x.id === S.st.pipeline);
      if (p && window.confirm(`${p.label} 데이터를 삭제합니다. 그 데이터로 만든 정의와 연결도 함께 사라집니다.`)) pipelineCall({ op: 'delete', id: p.id });
    },
    bndCheckNow: () => bndCheck(),
  });

  // ---- BND-02 데이터 매핑 ---------------------------------------------------------------------------------------
  const BND_MAP_LEAD = 'Property를 소스 컬럼, 코드값, 변환식, 조인 경로에 연결합니다. 매핑 명세는 연결 전에도 정의서로 작성해 둡니다. 연결하면 실제 스키마, 코드값과 대조해 차이를 찾습니다. Entity 하나를 테이블에 묶는 편집은 Entity 바인딩에서 합니다.';
  const bndMapId = (p) => `${p.object}.${p.name}`;
  // one row a Property: where it reads from, how, and where the reading stands
  function bndMapRow(m, by, p) {
    const o = bndObj(m, p.object), state = bndState(m, o, p), found = by[`property:${p.object}.${p.name}`] || [];
    const bad = found[0];
    const mark = state === 'none' ? ['', '테이블 대기'] : state === 'calc' ? ['', '계산 속성'] : bad ? ['warn', FINDING[bad.kind] || bad.kind]
      : state === 'missing' ? ['warn', '컬럼 없음'] : state === 'ok' ? ['ok', bndChecked() ? '값 확인' : '스키마 확인'] : ['b', '명세 완료'];
    return { p, o, state, found, mark, id: bndMapId(p), name: `${o ? o.label || o.name : p.object}.${p.label || p.name}`, source: o && o.table ? `${o.table}.${bndCol(p)}` : '' };
  }

  function bndMapView() {
    const wait = bndWait('데이터 매핑', BND_MAP_LEAD);
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
    const bar = sel ? itemBar('map', sel.id, sel.name, sel.source || '테이블 대기') : '';
    const stats = `<section class="k-wrap" aria-label="매핑 현황">
      <div class="k-card bnd-stat"><p class="k-s" style="margin:0">매핑 명세</p><p class="k-big">${spec.length} <span class="k-mut k-14" style="font-weight:400">/ 속성 ${core.length}</span></p><p class="k-s" style="margin:4px 0 0">테이블에 바인딩한 Entity의 Property</p></div>
      <div class="k-card bnd-stat"><p class="k-s" style="margin:0">코드 매핑</p><p class="k-big">${codes.length}</p><p class="k-s k-cut" style="margin:4px 0 0">${codes.length ? esc(codes.slice(0, 4).map((r) => r.p.label || r.p.name).join(' · ')) : '허용값을 둔 Property'}</p></div>
      ${on && bndChecked() ? `<div class="k-card bnd-stat"><p class="k-s" style="margin:0">실제 값으로 확인</p><p class="k-big">${spec.filter((r) => r.state === 'ok' && !r.found.length).length}</p><p class="k-s" style="margin:4px 0 0">컬럼 ${S.bind.checked.columns}개 · 데이터 점검 ${S.bind.checked.data_checks}건</p></div>`
    : `<div class="bnd-stat dash"><p class="k-s" style="margin:0">실제 값으로 확인</p><p class="k-big mut">-</p><p class="k-s" style="margin:4px 0 0">${on ? '차이 검사 후' : '데이터 소스 연결 후'}</p></div>`}
      <div class="bnd-stat${diff.length ? ' warn' : ' k-card'}"><p class="k-s" style="margin:0">차이</p><p class="k-big${diff.length ? ' warn' : ''}">${diff.length}</p><p class="${diff.length ? 'k-warn' : 'k-mut'} k-13" style="margin:4px 0 0">${diff.length ? esc([...new Set(diff.map((r) => r.mark[1]))].join(' · ')) : (on ? '정의 ↔ 실제 스키마' : '연결 후 대조')}</p></div></section>`;
    const pick = areas.length > 4 ? `<label class="k-push" style="flex:0 1 220px"><span class="k-hide">Object</span><select class="k-in sm" data-in="bndMapArea" aria-label="Object">${areas.map((a) => `<option value="${esc(a.name)}"${a.name === M.area ? ' selected' : ''}>${esc(a.label)}</option>`).join('')}</select></label>`
      : `<div class="k-seg k-push" role="group" aria-label="Object">${areas.map((a) => `<button type="button" class="${a.name === M.area ? 'on' : ''}" data-act="bndMapArea" data-a="${esc(a.name)}">${esc(a.label)}</button>`).join('')}</div>`;
    const tr = (r) => `<tr class="${sel && r.id === sel.id ? 'on' : ''}${r.mark[0] === 'warn' ? ' bnd-diff' : ''}" data-act="bndMapSel" data-id="${esc(r.id)}"><td class="b">${esc(r.name)}</td>
      <td>${r.p.expr ? '<span class="k-mut">컬럼 없음 · 식으로 계산</span>' : r.o && r.o.table ? `${esc(r.o.table)} <span class="k-code">${esc(bndCol(r.p))}</span>` : '<span class="k-mut">[테이블 확인]</span>'}</td><td>${esc(bndHow(r.p))}</td><td><span class="k-chip${r.mark[0] ? ` ${r.mark[0]}` : ''}">${esc(r.mark[1])}</span></td></tr>`;
    const table = `<section class="k-card" aria-labelledby="bnd-mp-h" style="flex:3 1 600px"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="bnd-mp-h">매핑 명세</h2>${pick}</div>
      ${rows.length ? `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">Property</th><th scope="col">소스</th><th scope="col">매핑 방식</th><th scope="col">상태</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div>` : '<p class="k-cf line">이 Object에는 Property가 없습니다.</p>'}
      <p class="k-cf">${on ? '명세는 정의서로 작성 · 실제 값 확인은 차이 검사를 실행할 때마다' : '명세는 정의서로 작성 · 실제 값 확인은 데이터 소스 연결 후'}</p></section>`;
    const first = sel && sel.mark[0] === 'warn' ? sel : diff[0];
    const why = first ? `<section class="k-v bnd-why" aria-labelledby="bnd-df-h"><h2 class="k-15" id="bnd-df-h" style="margin:0;font-weight:600;color:#5E3900">차이 · ${esc(first.name)}</h2>
      <p class="k-14" style="margin:0;line-height:1.55">${esc(first.found[0] ? (FIX[first.found[0].kind] || first.mark[1]) : '원천 테이블에 이 컬럼이 없습니다. 컬럼 이름을 맞추거나 원천에 컬럼을 추가합니다.')}</p>
      ${first.found[0] && first.found[0].detail ? `<p class="k-code k-13" style="margin:0;white-space:normal">${esc(first.found[0].detail)}</p>` : ''}
      <div class="k-wrap g8">${canEdit() ? `<a class="k-btn" href="${itemHref('map', 'form', first.id)}">매핑 고치기</a>` : ''}<a class="k-lnk" style="color:var(--warn)" href="#bind?row=${encodeURIComponent(`bind:property:${first.id}`)}">바인딩 검사에서 보기</a></div></section>` : '';
    const cp = sel && (sel.p.values || []).length ? sel.p : null;
    const code = cp ? `<section class="k-card" aria-labelledby="bnd-st-h"><div style="padding:16px 20px;border-bottom:1px solid var(--row)"><h2 class="k-h2" id="bnd-st-h">코드 매핑 · ${esc(sel.p.label || sel.p.name)}</h2><p class="k-s" style="margin:2px 0 0">규칙은 정의의 값을 대상으로 쓰고 소스 코드는 매핑으로 흡수</p></div>
      <table class="k-t s"><thead><tr><th scope="col">소스 값</th><th scope="col">표시</th></tr></thead><tbody>${cp.values.map((v) => `<tr><td class="k-code">${esc(v)}</td><td>${esc((cp.labels || {})[v] || '-')}</td></tr>`).join('')}</tbody></table></section>`
      : `<section class="k-card pad k-v"><h2 class="k-h2">코드 매핑</h2><p class="k-p s">${sel ? '이 Property에는 허용값이 없습니다. 허용값을 둔 Property를 고르면 소스 값과 표시 이름이 보입니다.' : '표에서 매핑을 고르면 소스 값과 표시 이름이 보입니다.'}</p></section>`;
    return bndPg(`${kHead('데이터 매핑', BND_MAP_LEAD, `<a class="k-btn" href="#bind">Entity 바인딩</a><button class="k-btn" data-act="bndCheckNow"${S.bind && S.bind.busy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.bind && S.bind.busy ? '대조 중' : '차이 검사'}</button>${canEdit() ? `<a class="k-btn pri" href="${itemHref('map', 'form')}">${ki('plus', 16, 1.75)}매핑</a>` : ''}`)}
      ${bar}${on ? '' : bndNoSource('지금은 매핑 명세를 정의서 기준으로 작성합니다. 실제 스키마와 코드값 대조는 데이터 소스를 연결하면 열립니다.')}${stats}<div class="k-cols">${table}<div class="k-c2">${why}${code}</div></div>
      ${kNext([['bind', 'Entity 바인딩'], ['db', '데이터 소스 연결'], ['objects', 'Property 정의'], ['lexicon', '용어 · 코드값'], ['query', '매핑한 데이터로 쿼리'], ['actions', '액션']])}`);
  }

  screen('sources', { area: 'work', word: '데이터 매핑', view: bndMapView, after: bndNeed });
  Object.assign(ACT, {
    bndMapSel: (t) => { S.bnd.map.sel = S.bnd.map.sel === t.dataset.id ? '' : t.dataset.id; render(); },
    bndMapArea: (t) => { S.bnd.map.area = t.dataset.a; render(); },
  });
  Object.assign(INPUT, { bndMapArea: (t) => { S.bnd.map.area = t.value; render(); } });
