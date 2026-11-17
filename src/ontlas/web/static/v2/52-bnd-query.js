  // ---- BND-03 질의 -----------------------------------------------------------------------------------------------
  // The registered queries on the left; the one chosen on the right: what it is, how each store's language says it,
  // and a run under an access policy. A question in plain words or a query typed by hand is run at the foot.
  const BND_Q_LEAD = '등록 질의를 정의하고 저장소 언어 변환과 실행 결과를 확인합니다.';
  // what the caches of these screens were read from: another ontology, other data or another edit makes them old
  const bndSig = () => `${S.st.library_id}|${S.st.pipeline}|${S.st.stats.queries}|${S.st.changes}|${S.mg.st && S.mg.st.workspace ? S.mg.st.workspace.edits.length : 0}`;

  function bndQLoad(force) {  // one read at a time: whoever asks while it runs waits for the same answer
    const Q = S.bnd.q, sig = bndSig();
    if (Q.loading) return Q.loading;
    if (!force && Q.st && Q.sig === sig) return Promise.resolve();
    Q.loading = api('bnd/queries').then((r) => { Q.st = r; Q.err = ''; }).catch((e) => { Q.st = { queries: [], targets: [], removed: [] }; Q.err = e.message; })
      .finally(() => { Q.sig = sig; Q.loading = null; Q.tr = null; Q.run = null; if (S.tab === 'query') render(); });
    return Q.loading;
  }
  const bndQOf = (name) => (S.bnd.q.st ? S.bnd.q.st.queries.find((x) => x.name === name) : null) || null;
  const bndQParams = (x) => Object.entries(x.params || {}).map(([k, t]) => `${k} · ${TYPE_WORD[t] || t}`).join(', ') || '없음';
  const bndQHops = (x) => (x.hops.length ? x.hops.map((h) => `${h.label} → ${h.to_label}`).join(' · ') : '없음');

  // the rows a store gave back, or why it gave none
  function bndQResults(r) {
    if (!r) return '';
    if (r.ok === false) return `<p class="k-note bad">${esc(r.error || '실행하지 못했습니다.')}</p>`;
    const none = r.no_source ? `<p class="k-note">${esc(r.note || '데이터 소스가 연결되지 않아 질의를 실행하지 못했습니다.')}</p>` : '';
    const agree = (r.results || []).filter((b) => b.ok).length < 2 ? '' : r.agree ? '<span class="k-chip ok">저장소 간 결과 일치</span>' : '<span class="k-chip warn">저장소 간 결과 불일치</span>';
    const one = (b) => {
      const head = `<div class="k-h" style="padding:12px 20px"><span class="k-b k-14">${esc(b.backend)}</span><span class="k-chip">${esc(String(b.language || '').toUpperCase())} · ${esc(b.dialect || '')}</span>${b.ok ? `<span class="k-s k-push">${b.rows.length}행</span>` : ''}</div>`;
      if (!b.ok) return `<div class="bnd-res">${head}<p class="k-cf line k-bad">${esc(b.error)}</p></div>`;
      const th = b.columns.map((c) => `<th scope="col">${esc(c)}${b.masked && b.masked[c] ? ' <span class="k-chip warn">가림</span>' : ''}</th>`).join('');
      return `<div class="bnd-res">${head}<div class="k-x" style="max-height:340px;overflow-y:auto"><table class="k-t s end"><thead><tr>${th}</tr></thead><tbody>${b.rows.slice(0, 50).map((row) => `<tr>${row.map((v) => `<td class="nw${typeof v === 'number' ? ' r' : ''}">${show(v)}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${b.columns.length || 1}" class="mut">결과가 없습니다.</td></tr>`}</tbody></table></div></div>`;
    };
    return `${none}${agree ? `<div class="k-h">${agree}</div>` : ''}${(r.results || []).map(one).join('')}`;
  }

  function bndQTranslate(x) {
    const Q = S.bnd.q, tr = Q.tr && Q.tr.name === x.name ? Q.tr : null;
    const list = tr && tr.translations ? tr.translations : [];
    const first = ['sparql', (S.st.targets.find((t) => t.id.startsWith('sql:')) || {}).id, 'cypher'].filter((id) => list.some((t) => t.target === id));
    const shown = Q.allLang ? list.map((t) => t.target) : first;
    if (!shown.includes(Q.lang)) Q.lang = shown[0] || '';
    const cur = list.find((t) => t.target === Q.lang);
    const okN = list.filter((t) => t.ok).length;
    const seg = list.length ? `<div class="k-seg k-push" role="tablist" aria-label="언어" style="flex-wrap:wrap">${shown.map((id) => { const t = list.find((y) => y.target === id);
      return `<button type="button" role="tab" aria-selected="${id === Q.lang}" class="${id === Q.lang ? 'on' : ''}" data-act="bndQLang" data-l="${esc(id)}">${esc(t.label)}</button>`; }).join('')}${!Q.allLang && list.length > shown.length ? `<button type="button" data-act="bndQLangAll">외 ${list.length - shown.length}</button>` : ''}</div>` : '';
    const body = !tr || tr.busy ? '<p class="k-cf line">변환하는 중입니다.</p>' : tr.error ? `<p class="k-cf line k-bad">${esc(tr.error)}</p>`
      : `<pre class="bnd-code">${esc(cur ? (cur.ok ? cur.text : cur.error) : '')}</pre>`;
    return `<section class="k-card" aria-labelledby="bnd-tr-h"><div class="k-pha" style="padding:12px 20px;border-bottom:1px solid var(--row)"><h2 class="k-h2" id="bnd-tr-h">저장소 언어 변환</h2>${seg}</div>${body}
      ${list.length ? `<div class="k-pha" style="padding:12px 20px"><span class="k-chip ${okN ? 'ok' : 'bad'}">${okN ? '구문 검사 통과' : '구문 검사 실패'}</span><span class="k-chip ${okN === list.length ? 'ok' : 'warn'}">${okN}개 언어 변환</span>${noSource() ? '<span class="k-chip dash">실행 · 미연결</span>' : ''}${cur && cur.ok ? `<button class="k-lnk k-push" data-act="copycode" data-v="${esc(cur.text)}">복사</button>` : ''}</div>` : ''}</section>`;
  }

  function bndQRun(x) {
    const Q = S.bnd.q, roles = S.st.roles || [], role = roles.find((r) => r.name === Q.role);
    const params = Object.keys(x.params || {}).map((k) => `<label class="k-f" style="flex:1 1 180px">${esc(k)}<input class="k-in" type="text" data-in="bndQParam" data-k="${esc(k)}" value="${esc(plainText(Q.params[k] ?? ''))}"></label>`).join('');
    const who = role ? role.principal.map((k) => `<label class="k-f" style="flex:1 1 180px">${esc(k)}<input class="k-in" type="text" data-in="bndQPrincipal" data-k="${esc(k)}" value="${esc(Q.principal[k] || '')}" placeholder="조회 범위 값"></label>`).join('') : '';
    return `<section class="k-card pad k-wrap" aria-labelledby="bnd-run-h" style="align-items:flex-end"><h2 class="k-h2" id="bnd-run-h" style="flex:0 0 100%">테스트 실행</h2>
      ${roles.length ? `<label class="k-f" style="flex:1 1 180px">접근 정책<select class="k-in" data-in="bndQRole"><option value="">정책 없음</option>${roles.map((r) => `<option value="${esc(r.name)}"${r.name === Q.role ? ' selected' : ''}>${esc(r.name)} · ${esc(r.label)}</option>`).join('')}</select></label>` : ''}${who}${params}
      <button class="k-btn pri" data-act="bndQGo"${Q.running ? ' disabled' : ''}>${ki('play', 16, 1.75)}${Q.running ? '실행 중' : '실행'}</button>
      
      ${Q.run && Q.run.name === x.name ? `<div class="k-v g12" style="flex:0 0 100%;min-width:0">${bndQResults(Q.run)}</div>` : ''}</section>`;
  }

  // a question in plain words or a query typed by hand: run once, and kept as a registered query from there if wanted
  function bndQAdhoc() {
    const A = S.bnd.q.adhoc = S.bnd.q.adhoc || { mode: S.st.ask ? 'ask' : 'text', lang: 'sparql', text: '', question: '', res: null, busy: false };
    const modes = (S.st.ask ? [['ask', '자연어 질문']] : []).concat([['text', '질의 입력']]);
    const body = A.mode === 'ask' ? `<label class="k-f">질문<input class="k-in" type="text" id="bndask" data-in="bndQAsk" value="${esc(A.question)}" placeholder="예: 반품 요청 주문상품"></label>`
      : `<div class="k-wrap"><label class="k-f" style="flex:0 1 240px">언어<select class="k-in" data-in="bndQTextLang">${TEXT_LANG.map(([k, l]) => `<option value="${k}"${A.lang === k ? ' selected' : ''}>${l}</option>`).join('')}</select></label></div>
        <label class="k-f">질의<textarea class="k-in mono" rows="6" data-in="bndQText" spellcheck="false" style="font-family:var(--mono);font-size:13px">${esc(A.text)}</textarea></label>`;
    const ok = A.res && A.res.ok;
    const cur = ok ? (A.res.translations.find((t) => t.target === 'sparql' && t.ok) || A.res.translations.find((t) => t.ok)) : null;
    return `<section class="k-card pad k-v g12" id="bnd-adhoc" aria-labelledby="bnd-ad-h"><div class="k-h"><h2 class="k-h2" id="bnd-ad-h">임시 실행</h2>
        ${modes.length > 1 ? `<div class="k-seg k-push" role="group" aria-label="방식">${modes.map(([k, l]) => `<button type="button" class="${A.mode === k ? 'on' : ''}" data-act="bndQAdMode" data-m="${k}">${l}</button>`).join('')}</div>` : ''}</div>
      ${body}<div class="k-h"><button class="k-btn" data-act="bndQAdGo"${A.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}${A.busy ? '실행 중' : '실행'}</button>
        ${ok && canEdit() ? `<button class="k-btn" data-act="bndQAdKeep">${ki('plus', 16, 1.75)}질의 등록</button>` : ''}${ok && A.res.attempts ? `<span class="k-chip b">생성 시도 ${A.res.attempts}회</span>` : ''}</div>
      ${ok ? `<details class="bnd-ir"><summary class="k-lnk flat">질의 정의 · 변환 결과</summary><pre class="bnd-sql" style="border:1px solid var(--row);border-radius:8px;margin-top:8px;white-space:pre-wrap">${esc(A.res.ir || '')}</pre>${cur ? `<pre class="bnd-code" style="border-radius:8px;margin-top:8px">${esc(cur.text || '')}</pre>` : ''}</details>` : ''}
      ${A.res ? bndQResults(A.res) : ''}</section>`;
  }

  function bndQView() {
    const Q = S.bnd.q, lead = BND_Q_LEAD;
    const acts = `${S.st.ask ? '<button class="k-btn" data-act="bndQNl">자연어 질의</button>' : ''}${canEdit() ? `<a class="k-btn" href="${itemHref('queryitem', 'form')}">${ki('plus', 16, 1.75)}질의</a>` : ''}`;
    const head = kHead('질의', lead, acts);
    if (!Q.st) return head + '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>';
    if (Q.err) return head + kEmpty('불러오지 못했습니다', Q.err);
    const all = Q.st.queries;
    const asked = itemParam('sel') || itemParam('query');  // ?query= is the older link, which also runs the query the older way
    if (asked && bndQOf(asked) && Q.asked !== asked) { Q.asked = asked; Q.sel = asked; }
    if (!bndQOf(Q.sel)) Q.sel = (all[0] || {}).name || '';
    const x = bndQOf(Q.sel);
    const f = Q.find.trim().toLowerCase();
    const rows = all.filter((y) => !f || y.label.toLowerCase().includes(f) || y.name.toLowerCase().includes(f));
    const list = `<nav class="k-card" aria-label="등록 질의" style="flex:1 1 300px"><div style="padding:12px"><label class="bnd-find" style="margin:0">${ki('search', 16, 1.75)}<span class="k-hide">질의 검색</span><input type="search" placeholder="질의 검색" data-in="bndQFind" value="${esc(Q.find)}"></label></div>
      <div id="bndqlist">${rows.map((y) => `<button class="bnd-qrow${x && y.name === x.name ? ' on' : ''}" data-act="bndQSel" data-q="${esc(y.name)}" data-row="query:${esc(y.name)}"${x && y.name === x.name ? ' aria-current="true"' : ''}><b>${esc(y.label)}</b><span class="k-code k-mut">${esc(y.name)}</span></button>`).join('') || '<p class="k-cf line">검색 결과가 없습니다.</p>'}</div>
      <p class="k-s" style="margin:0;padding:8px 16px;border-top:1px solid var(--row)">등록 질의 ${all.length} · 검증 질문 사용 ${all.filter((y) => y.questions.length).length}${Q.st.removed.length ? ` · 삭제 요청 ${Q.st.removed.length}` : ''}</p></nav>`;
    if (!x) return bndPg(`${head}${noSource() ? bndNoSource('데이터 소스가 연결되지 않아 질의 결과를 조회할 수 없습니다.') : ''}
      ${kEmpty('등록된 질의가 없습니다', '', canEdit() ? `<a class="k-btn pri" href="${itemHref('queryitem', 'form')}">${ki('plus', 16, 1.75)}질의</a>` : '')}${bndQAdhoc()}`);
    const ro = (word, value) => `<label class="k-f">${word}<input class="k-in" type="text" value="${esc(value)}" readonly></label>`;
    const one = (word, value) => `<label class="k-f">${word}<select class="k-in" aria-readonly="true"><option>${esc(value)}</option></select></label>`;  // shown as the form shows it; it is changed in the form
    const used = [...x.questions.map((q) => `<a class="k-chip" href="#check">검증 질문 ${esc(q)}</a>`), ...x.roles.map((r) => `<a class="k-chip" href="#roles">접근 정책 ${esc(r.label)}</a>`),
      TOOL_WORD.run_query ? '<a class="k-chip" href="#connect">MCP run_query</a>' : ''].join('');
    const detail = `<section class="k-card pad k-v g12" aria-labelledby="bnd-qd-h"><div class="k-pha"><h2 id="bnd-qd-h" style="margin:0;font-size:20px;font-weight:600">${esc(x.label)}</h2><span class="k-code k-mut">${esc(x.name)}</span>
        <span class="k-chip ${x.new ? 'warn' : 'b'} k-push">${x.new ? '작성 중 · 변경 요청 대기' : esc(`${x.module_label || x.module}${x.version ? ` · v${x.version}` : ''}`)}</span></div>
      ${x.description ? `<p class="k-p">${esc(x.description)}</p>` : ''}
      <div class="bnd-two">${one('시작', `${x.start_label}@${x.start}`)}${one('경유 Relation', bndQHops(x))}${ro('입력값', bndQParams(x))}${ro('반환', x.returns.map((r) => r.label).join(' · '))}</div>
      <div class="k-13" style="display:flex;flex-wrap:wrap;gap:6px;align-items:center"><span class="k-s">사용처</span>${used}</div></section>`;
    return bndPg(`${head}${itemBar('queryitem', x.name, x.name, x.label)}${noSource() ? bndNoSource('데이터 소스가 연결되지 않아 질의 결과를 조회할 수 없습니다.') : ''}
      <div class="k-cols">${list}<div class="k-v g16" style="flex:2 1 560px;min-width:0">${detail}${bndQTranslate(x)}${bndQRun(x)}</div></div>${bndQAdhoc()}
      ${kNext([['sources', 'Mapping'], ['actions', 'Action'], ['connect', '연동 · API'], ['roles', '접근 정책'], ['check', '검증 질문']])}`);
  }

  function bndQAfter() {
    const Q = S.bnd.q;
    bndQLoad();
    const x = Q.st && bndQOf(Q.sel);
    if (!x) return;
    if (!Q.tr || Q.tr.name !== x.name) {  // the chosen query in every store's language; nothing is run for this
      Q.tr = { name: x.name, busy: true };
      Q.params = { ...((S.st.queries.find((y) => y.name === x.name) || {}).example || x.example || {}) };  // the values the server would try it with
      api('bnd/query/check', { query: x.ir }).then((r) => { if (Q.tr && Q.tr.name === x.name) Q.tr = { name: x.name, ...r }; }).catch((e) => { Q.tr = { name: x.name, error: e.message }; }).finally(() => { if (S.tab === 'query') render(); });
    }
  }

  screen('query', { area: 'work', word: '질의', view: bndQView, after: bndQAfter });

  Object.assign(INPUT, {
    bndQFind: (t) => { S.bnd.q.find = t.value; const box = $('#bndqlist'), tmp = document.createElement('div'); tmp.innerHTML = bndQView(); const now = tmp.querySelector('#bndqlist'); if (box && now) box.innerHTML = now.innerHTML; },
    bndQParam: (t) => { S.bnd.q.params[t.dataset.k] = t.value; },
    bndQPrincipal: (t) => { S.bnd.q.principal[t.dataset.k] = t.value; },
    bndQRole: (t) => { S.bnd.q.role = t.value; S.bnd.q.principal = {}; render(); },
    bndQAsk: (t) => { S.bnd.q.adhoc.question = t.value; },
    bndQText: (t) => { S.bnd.q.adhoc.text = t.value; },
    bndQTextLang: (t) => { S.bnd.q.adhoc.lang = t.value; },
  });
  Object.assign(ACT, {
    bndQSel: (t) => { const Q = S.bnd.q; Q.sel = t.dataset.q; Q.run = null; render(); },
    bndQLang: (t) => { S.bnd.q.lang = t.dataset.l; render(); },
    bndQLangAll: () => { S.bnd.q.allLang = true; render(); },
    bndQGo: async () => {
      const Q = S.bnd.q, x = bndQOf(Q.sel);
      if (!x || Q.running) return;
      Q.running = true; render();
      const ctx = { role: Q.role, principal: Q.principal };
      let r;
      try { r = x.new ? await api('text', { language: 'ir', text: JSON.stringify(x.ir), ...ctx }) : await api('query', { name: x.name, params: Q.params, ...ctx }); } catch (e) { r = { ok: false, error: e.message }; }
      Q.run = { ...r, name: x.name }; Q.running = false; render();
    },
    bndQNl: () => { const A = S.bnd.q.adhoc; if (A) A.mode = 'ask'; render(); const el = $('#bnd-adhoc'); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); const i = $('#bndask'); if (i) i.focus({ preventScroll: true }); },
    bndQAdMode: (t) => { S.bnd.q.adhoc.mode = t.dataset.m; render(); },
    bndQAdGo: async () => {
      const A = S.bnd.q.adhoc;
      if (A.busy) return;
      if (A.mode === 'ask' ? !A.question.trim() : !A.text.trim()) { toast(A.mode === 'ask' ? '질문을 입력해 주세요.' : '질의를 입력해 주세요.', true); return; }
      A.busy = true; render();
      try { A.res = A.mode === 'ask' ? await api('ask', { question: A.question }) : await api('text', { language: A.lang, text: A.text }); } catch (e) { A.res = { ok: false, error: e.message }; }
      A.busy = false; render();
    },
    bndQAdKeep: () => { const A = S.bnd.q.adhoc; if (!A.res || !A.res.ok) return; S.bnd.q.seed = { ir: A.res.ir, label: A.mode === 'ask' ? A.question.trim().slice(0, 40) : '' }; location.hash = itemHref('queryitem', 'form'); },
  });
