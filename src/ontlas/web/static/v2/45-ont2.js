  // ==== Ontology 의 뒤쪽 화면: 용어 사전, 개념 초안, 모듈 라이브러리, 변경 요청 · 버전 ==============================
  // This file: what the four screens share, then 변경 요청 · 버전 (where every edit of the other screens ends up) and the
  // form of the request being written. 45-ont2b.js is 온톨로지, 45-ont2c.js 용어사전, 45-ont2d.js 개념 초안.

  S.o2 = {
    ch: { tab: '', sel: '', synced: '', more: null, dm: null, dmFor: null, busy: false },  // 변경 요청 · 버전
    lib: { kind: 'all', sem: null },                                                          // 온톨로지
    lx: { kind: 'all', q: '', rel: 'all', rq: '', rsel: '', imp: null },                      // 용어사전
    cc: { kind: 'all', sel: '', set: false },                                                 // 개념 초안
  };
  const O2_KIND = { area: 'Object', object: 'Entity', property: 'Property', link: 'Relation', rule: '규칙', decision: '결정표', action: 'Action', role: '접근 정책',
    query: '질의', question: '검증 질문', function: '함수', identity: '식별 통합', parameter: '기준값', metric: '지표', term: '용어', terms: '용어집' };
  const O2_SCREEN = { area: 'objmgr', object: 'objects', property: 'objects', link: 'model', rule: 'semrules', decision: 'semrules', action: 'actions', role: 'roles',
    query: 'query', question: 'check', function: 'semrules', parameter: 'semrules', metric: 'semrules', term: 'lexicon', terms: 'lexicon' };
  const O2_OP = { ...OP_WORD, add_object: 'Entity 추가', update_object: 'Entity 변경', delete_object: 'Entity 제외', add_property: 'Property 추가', update_property: 'Property 변경',
    delete_property: 'Property 제외', add_link: 'Relation 추가', update_link: 'Relation 변경', delete_link: 'Relation 제외', add_area: 'Object 추가', update_area: 'Object 변경',
    delete_area: 'Object 제외', add_term: '용어 추가', update_term: '용어 변경', delete_term: '용어 제외', import_terms: '용어집 가져오기', add_rule_card: '규칙 카드 추가',
    update_rule_card: '규칙 카드 변경', delete_rule_card: '규칙 카드 제외', add_parameter: '기준값 추가', delete_parameter: '기준값 제외', add_metric: '지표 추가',
    update_metric: '지표 변경', delete_metric: '지표 제외', add_function: '함수 추가', update_function: '함수 변경', delete_function: '함수 제외', add_query: '질의 추가',
    update_decision: '결정표 변경', move_rule: '규칙 순서 변경', add_role: '접근 정책 추가', update_role: '접근 정책 변경', delete_role: '접근 정책 제외' };
  const o2Split = (id) => { const [k, ...r] = String(id).split(':'); return [k, r.join(':')]; };
  const o2ElWord = (id) => { const [k, n] = o2Split(id); return `${O2_KIND[k] || k} ${n}`; };
  const o2When = (at) => (at ? esc(String(at).slice(5, 16).replace('-', '/').replace('T', ' ').replace(/^0/, '')) : '-');
  const o2Wait = () => '<section class="k-card pad"><p class="k-p s">불러오는 중</p></section>';
  const o2Seg = (label, items, cur, act) => `<div class="k-seg" role="group" aria-label="${esc(label)}">${items.map(([k, w]) => `<button class="${cur === k ? 'on' : ''}" data-act="${act}" data-k="${esc(k)}" aria-pressed="${cur === k}">${esc(w)}</button>`).join('')}</div>`;

  // the menu loads the definition for its maturity and draws only itself; a screen that reads it waits here
  function o2NeedManage(tab) {
    if (S.mg.st) return true;
    if (!S.mg.busy) loadManage();
    clearTimeout(o2NeedManage.t);
    o2NeedManage.t = setTimeout(() => { if (S.tab !== tab) return; if (S.mg.st) render(); else o2NeedManage(tab); }, 150);
    return false;
  }

  async function o2LoadVersions() {
    S.ver = { busy: true };
    let v, more;
    try { v = await api('versions'); } catch (e) { v = { error: e.message }; }
    try { more = await api('ont2/versions'); } catch (e) { more = { rollbacks: [], kept: 0 }; }
    S.ver = v; S.o2.ch.more = more;
    if (['changes', 'library'].includes(S.tab)) render();
  }

  // the request being written: its title, and the number it would be deployed as
  async function o2LoadDraft() {
    const c = S.o2.ch, at = S.mg.st;
    if (c.dmBusy) return;
    c.dmBusy = true;
    try { c.dm = await api('ont2/draft'); } catch (e) { c.dm = { error: e.message, title: '', description: '', next: 0 }; }
    c.dmFor = at; c.dmBusy = false;
    if (['changes', 'library', 'change-form'].includes(S.tab)) render();
  }
  const o2DraftStale = () => !S.o2.ch.dm || S.o2.ch.dmFor !== S.mg.st;
  // what a request is called: the title it was sent with (its module is called by its latest), or that it has none yet
  const O2_UNTITLED = '제목 없는 변경 요청';
  const o2Title = (x) => {
    const own = ((S.o2.ch.more || {}).titles || {})[x.id];
    if (own) return own;
    const h = S.ver && S.ver.history ? [...S.ver.pending, ...S.ver.history].find((y) => y.id === x.id) : null;
    return (h && h.summary) || x.summary || x.module_label || x.module;  // one sent without a title goes by what it changes
  };
  const o2DraftTitle = () => (S.o2.ch.dm && S.o2.ch.dm.title) || O2_UNTITLED;

  // ---- parts both the list and the detail are written with -------------------------------------------------------
  const O2_STATE = { draft: ['', '작성 중'], pending: ['b', '검토 대기'], approved: ['ok', '배포됨'], filed: ['', '라이브러리 저장'], rejected: ['', '반려'] };
  const o2Steps = (n) => `<div class="o2-steps" role="img" aria-label="${n} / 5 단계">${['작성', '회귀 테스트', '검토', '승인', '배포'].map((w, i) => `<span class="k-v g4 k-g"><i class="${i < n ? 'on' : ''}"></i><span class="${i < n ? 'k-ink' : 'k-hint'}" style="font-size:12px">${w}</span></span>`).join('')}</div>`;
  const O2_SIGN = { added: ['k-ok', '+'], changed: ['k-warn', '~'], removed: ['k-bad', '−'] };
  const o2Sign = (change) => { const [cls, s] = O2_SIGN[change] || ['', '']; return `<span class="k-code ${cls}">${s}</span>`; };

  // what a change does to the answers: the questions it newly gets wrong, the shares before and after, each pass condition
  function o2Regression(r, gates, before) {
    const moved = (m) => (m && (m.before !== null || m.after !== null) ? `<span class="k-code k-ink">${m.before === m.after || m.before === null ? pct(m.after) : `${pct(m.before)} → ${pct(m.after)}`}</span>` : '<span class="k-mut">-</span>');
    const rows = [];
    if (r && r.measured) {
      const n = (r.newly_failing || []).length;
      rows.push(kKv('신규 오답', `<span class="k-code ${n ? 'k-bad' : 'k-ok'}">${n}</span>`), kKv('정답률', moved(r.accuracy)), kKv('근거 제시율', moved(r.grounded)), kKv('과거 판정 일치율', moved(r.agreement)));
    } else rows.push(`<p class="k-cf line">${esc((r && r.note) || '측정한 검증 질문이 없습니다.')}</p>`);
    const gate = (g) => {
      const was = (before || {})[`${g.stage}.${g.condition}`], max = g.condition.startsWith('max_');
      const fmt = (x) => (x === null || x === undefined ? '-' : max ? show(x) : pct(x));
      return `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(g.stage_label || g.stage)} · ${esc(g.label)}</span><span class="k-s">기준 ${fmt(g.limit)} · ${was === undefined ? '' : `${fmt(was)} → `}${fmt(g.value)}${g.note ? ` · ${esc(g.note)}` : ''}</span></span><span class="k-h end"><span class="k-chip ${g.passed ? 'ok' : 'bad'}">${g.passed ? '통과' : '미통과'}</span></span></div>`;
    };
    const wrong = ((r && r.newly_failing) || []).map((w) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14"><span class="k-code">${esc(w.id)}</span> ${esc(w.text)}</span><span class="k-s">기대 ${esc(JSON.stringify(w.expected))} → 결과 ${esc(JSON.stringify(w.got))}</span></span><span class="k-h end"><span class="k-chip bad">신규 오답</span></span></div>`).join('');
    return `${rows.join('')}${wrong}${(gates || []).map(gate).join('')}`;
  }

  // ---- 변경 요청 · 버전 ----------------------------------------------------------------------------------------------
  function o2Changes() {
    const c = S.o2.ch;
    if (S.land && S.land.id) { c.sel = S.land.id; c.tab = ''; }  // a link names the request to open: #changes?id=C3
    else if (S.chg.sel && S.chg.sel !== c.synced) { c.sel = S.chg.sel; c.tab = ''; }  // another screen chose one before coming here
    const head = kHead('변경 요청 · 버전', '정의 · 규칙 · 접근 정책의 변경 요청과 버전을 관리합니다.',
      `<button class="k-btn" data-act="o2jump" data-to="o2vers">버전 비교</button>${canEdit() ? `<a class="k-btn pri" href="${itemHref('change', 'form')}">${ki('plus', 16, 1.75)}변경 요청 만들기</a>` : ''}`);
    const all = S.changes && S.changes.changes, v = S.ver && S.ver.current ? S.ver : null;
    if (S.changes && S.changes.error) return head + kEmpty('불러오지 못했습니다', S.changes.error);
    if (S.ver && S.ver.error) return head + kEmpty('불러오지 못했습니다', S.ver.error);
    if (!all || !v || !S.mg.st) return head + o2Wait();
    const ws = S.mg.st.error ? null : S.mg.st.workspace, draft = !!(ws && ws.dirty), dm = c.dm || {};
    const hist = Object.fromEntries([...v.pending, ...v.history].map((x) => [x.id, x]));
    const state = (x) => (x.status === 'approved' && hist[x.id] && !hist[x.id].applied ? 'filed' : x.status);
    const open = all.filter((x) => x.status === 'pending'), done = all.filter((x) => x.status === 'approved'), no = all.filter((x) => x.status === 'rejected');
    const tabOf = (id) => { if (id === 'draft') return 'open'; const x = all.find((y) => y.id === id); return !x ? '' : x.status === 'pending' ? 'open' : x.status === 'approved' ? 'done' : 'no'; };
    if (c.sel && !(c.sel === 'draft' ? draft : all.some((x) => x.id === c.sel))) c.sel = '';
    if (!c.tab) c.tab = (c.sel && tabOf(c.sel)) || (draft || open.length ? 'open' : done.length ? 'done' : no.length ? 'no' : 'open');
    const rows = c.tab === 'open' ? [...(draft ? ['draft'] : []), ...open] : c.tab === 'done' ? done : no;
    if (!c.sel || tabOf(c.sel) !== c.tab) c.sel = rows.length ? (rows[0] === 'draft' ? 'draft' : rows[0].id) : '';
    if (c.sel && c.sel !== 'draft' && S.chg.sel !== c.sel) Object.assign(S.chg, { sel: c.sel, det: null, item: '', text: '' });
    c.synced = S.chg.sel;
    const cur = v.current, next = `버전 ${cur.number + 1} 초안`, more = c.more || { rollbacks: [], kept: cur.number };
    const lastBack = more.rollbacks[more.rollbacks.length - 1];
    const stats = `<section class="k-wrap" aria-label="현황">
      <div class="k-stat"><p class="k-s" style="margin:0">열린 변경 요청</p><p class="k-big">${open.length + (draft ? 1 : 0)}</p><p class="k-s" style="margin:4px 0 0">검토 대기 ${open.length} · 작성 중 ${draft ? 1 : 0}</p></div>
      <div class="k-stat"><p class="k-s" style="margin:0">운영 버전</p><p class="k-big">${esc(cur.label)}</p><p class="k-s" style="margin:4px 0 0">${cur.at ? `${o2When(cur.at)} 배포` : '처음 구성'}</p></div>
      <div class="k-stat"><p class="k-s" style="margin:0">미리보기</p><p class="k-big${draft || open.length ? '' : ' mut'}">${draft || open.length ? esc(next) : '없음'}</p><p class="k-s" style="margin:4px 0 0">${draft ? `작성 중인 변경 ${ws.edits.length}건${open.length ? ` · ${esc(open.map((x) => x.id).join(' · '))}` : ''}` : open.length ? `${esc(open.map((x) => x.id).join(' · '))} 포함` : '변경 없음'}</p></div>
      <div class="k-stat"><p class="k-s" style="margin:0">마지막 롤백</p><p class="k-big${lastBack ? '' : ' mut'}">${lastBack ? esc(lastBack.change) : '없음'}</p><p class="k-s" style="margin:4px 0 0">${lastBack ? `${o2When(lastBack.at)} · ` : ''}이력 ${more.kept}개 보관</p></div></section>`;
    const item = (x) => {
      const id = x === 'draft' ? 'draft' : x.id, on = c.sel === id, h = x === 'draft' ? null : hist[x.id];
      const [tone, word] = O2_STATE[x === 'draft' ? 'draft' : state(x)] || ['', ''];
      const title = x === 'draft' ? o2DraftTitle() : o2Title(x);
      const sub = x === 'draft' ? `변경 ${ws.edits.length}건 · ${S.st.who || ''} · 작성 중`.replace(' ·  ·', ' ·')
        : `${h && h.summary && h.summary !== title ? `${h.summary} · ` : ''}${x.requested_by} · ${x.status === 'pending' ? o2When(x.at) : `${o2When(x.decided_at || x.at)}${x.status === 'rejected' && x.reason ? ` · ${x.reason}` : ''}`}`;
      return `<button class="k-row tight${on ? ' on' : ''}" data-act="o2chsel" data-id="${esc(id)}"${on ? ' aria-current="true"' : ''}><span class="k-h">${x === 'draft' ? '' : `<span class="k-code k-mut">${esc(x.id)}</span>`}<span class="k-chip${tone ? ` ${tone}` : ''}">${word}</span></span><b class="k-b">${esc(title)}</b><span class="k-s">${esc(sub)}</span></button>`;
    };
    const list = `<nav class="k-card" aria-label="변경 요청 목록" style="flex:1 1 300px"><div style="padding:12px">${o2Seg('상태', [['open', `열림 ${open.length + (draft ? 1 : 0)}`], ['done', '배포됨'], ['no', '반려']], c.tab, 'o2chtab')}</div>
      ${rows.map(item).join('') || `<p class="k-cf line">${c.tab === 'open' ? '열린 변경 요청이 없습니다.' : c.tab === 'done' ? '배포된 변경 요청이 없습니다.' : '반려된 변경 요청이 없습니다.'}</p>`}</nav>`;
    const detail = !c.sel ? `<div class="k-v g16" style="flex:2 1 560px;min-width:0">${kEmpty('선택된 변경 요청이 없습니다', '')}</div>`
      : c.sel === 'draft' ? o2DraftDetail(ws, dm, cur) : o2ChangeDetail(cur, hist[c.sel]);
    return `${head}${stats}<div class="k-cols">${list}${detail}</div>${o2VersionTable(v, more, draft ? ws : null, open)}
      ${kNext([['library', '모듈 라이브러리'], ...(isSysAdmin() ? [['sys-packs', '도메인 팩']] : []), ['inbox', '할 일 · 알림']])}`;
  }

  // the request being written: the edits waiting in the workspace, tried on a copy, then sent
  function o2DraftDetail(ws, dm, cur) {
    const d = ws.diff, tr = S.md.trial, tried = tr && tr.gates;
    const view = S.chg.view === 'yaml' ? 'yaml' : 'fields';
    const els = [...d.added.map((e) => [e, 'added']), ...d.changed.map((e) => [e, 'changed']), ...d.removed.map((e) => [e, 'removed'])];
    const terms = ws.edits.filter((e) => /^terms?:/.test(e.target)).length;
    const elRow = ([e, change]) => { const [k] = o2Split(e), to = O2_SCREEN[k];
      return `<${to && known(to) ? `a href="#${to}"` : 'div'} class="k-row"><span class="k-col"><span class="k-ink k-14">${o2Sign(change)} ${esc(o2ElWord(e))}</span></span>${to && known(to) ? ki('chevR', 16, 1.75) : ''}</${to && known(to) ? 'a' : 'div'}>`; };
    const edits = ws.edits.map((e, i) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(O2_OP[e.op] || e.op)} · ${esc(o2ElWord(e.target).replace(/^용어집 /, ''))}</span>${e.took_out.length ? `<span class="k-s">함께 제외 · ${esc(e.took_out.map(o2ElWord).join(', '))}</span>` : ''}</span>${canEdit() ? `<button class="k-lnk" data-act="mdrevert" data-i="${i}"${S.mg.busy ? ' disabled' : ''}>되돌리기</button>` : ''}</div>`).join('');
    const yaml = `<div class="k-cb"><pre class="o2-yaml k-x">${esc(ws.yaml)}</pre></div>`;
    const issues = ws.issues.length ? `<div class="k-cb"><p class="k-note bad">${ws.issues.slice(0, 6).map(esc).join('<br>')}</p></div>` : '';
    const test = tr && tr.busy ? '<p class="k-cf line">회귀 테스트 실행 중</p>' : tr && tr.error ? `<div class="k-cb"><p class="k-note bad">${esc(tr.error)}</p></div>`
      : tried ? `${o2Regression(tr.regression, tr.gates, tr.before)}${tr.issues && tr.issues.length ? `<div class="k-cb" style="padding-top:12px"><p class="k-note warn">${tr.issues.map(esc).join('<br>')}</p></div>` : ''}`
        : '<p class="k-cf line">실행 전</p>';
    return `<div class="k-v g16" style="flex:2 1 560px;min-width:0">
      <section class="k-card"><div class="k-ch"><h2>${esc(o2DraftTitle())}</h2><span class="k-push"><span class="k-chip">작성 중</span>${canEdit() ? `<a class="k-btn sm" href="${itemHref('change', 'form', 'draft')}">${ki('doc', 16, 1.75)}편집</a>` : ''}</span></div>
        <div class="k-cb">${o2Steps(tried ? 2 : 1)}<p class="k-p">${esc(dm.description || '')}${dm.description ? ' ' : ''}요청 ${esc(S.st.who || '-')} · 대상 ${esc(cur.label)} → 버전 ${cur.number + 1}</p></div></section>
      <section class="k-card"><div class="k-ch"><h2>변경 항목</h2><span class="k-s">추가 ${d.added.length} · 수정 ${d.changed.length} · 삭제 ${d.removed.length}${terms ? ` · 용어 ${terms}` : ''}</span><span class="k-push">${o2Seg('보기', [['fields', '요약'], ['yaml', 'YAML 비교']], view, 'chgview')}</span></div>
        ${view === 'yaml' ? yaml : `${els.map(elRow).join('')}${issues}<div class="o2-sub"><span class="k-b k-13">저장 순서 ${ws.edits.length}건</span>${canEdit() ? `<span class="k-push k-h">${ws.edits.length ? '<button class="k-lnk" data-act="mdundo">마지막 변경 되돌리기</button>' : ''}${ws.redo ? '<button class="k-lnk" data-act="mdredo">다시 적용</button>' : ''}</span>` : ''}</div>${edits || '<p class="k-cf line">이전 변경 · YAML 비교 참조</p>'}`}</section>
      <section class="k-card"><div class="k-ch"><h2>회귀 테스트</h2><span class="k-push">${canEdit() ? `<button class="k-btn sm" data-act="mgreview"${(tr && tr.busy) || ws.issues.length ? ' disabled' : ''}>${ki('play', 16, 1.75)}${tried ? '다시 실행' : '지금 실행'}</button>` : ''}${known('flow') ? `<a class="k-lnk" href="#flow">검증 결과${ki('chevR', 14, 1.75)}</a>` : ''}</span></div>${test}</section>
      <section class="k-card"><div class="k-ch"><h2>검토 요청</h2></div><div class="k-cb">
        ${canEdit() ? `<div class="k-wrap g8" style="justify-content:flex-end"><button class="k-btn dan" data-act="mgdiscard"${S.mg.busy ? ' disabled' : ''}>폐기</button><button class="k-btn pri" data-act="mgpropose"${S.mg.busy || ws.issues.length || (tr && tr.busy) ? ' disabled' : ''}>${S.mg.busy ? '등록 중' : selfApply() ? `버전 ${cur.number + 1} 배포` : '검토 요청'}</button></div>` : ''}</div></section></div>`;
  }

  // a request that was sent: what it changes element by element, what it does to the answers, and the review
  function o2ChangeDetail(cur, h) {
    const c = S.chg, d = c.det && c.det.id === c.sel ? c.det : null;
    if (!d) return `<div class="k-v g16" style="flex:2 1 560px;min-width:0">${c.det && c.det.error ? kEmpty('불러오지 못했습니다', c.det.error) : o2Wait()}</div>`;
    const items = d.items, applied = !(h && !h.applied);
    if (c.item && !items.some((x) => x.element === c.item)) c.item = '';
    const [tone, word] = O2_STATE[d.status === 'approved' && !applied ? 'filed' : d.status] || ['', d.status_label];
    const view = c.view === 'yaml' ? 'yaml' : 'fields';
    const n = (k) => items.filter((x) => x.change === k).length;
    const done = items.filter((x) => x.mark === 'ok').length, sent = items.filter((x) => x.mark === 'fix').length;
    const said = (v, w) => (v === null || v === undefined ? '<span class="k-mut">없음</span>' : w ? esc(w) : typeof v === 'object' ? `<span class="k-code" style="white-space:normal">${esc(JSON.stringify(v))}</span>` : typeof v === 'boolean' ? yesNo(v) : esc(String(v)));
    const open = (x) => {
      const to = O2_SCREEN[x.kind];
      const fields = x.fields.length ? `<div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">항목</th><th scope="col">${d.status === 'pending' ? '현재' : '이전'}</th><th scope="col">이후</th></tr></thead><tbody>${x.fields.map((f) => `<tr><td class="b nw">${esc(f.label)}</td><td class="k-bad">${said(f.before, (f.said || [])[0])}</td><td class="k-ok">${said(f.after, (f.said || [])[1])}</td></tr>`).join('')}</tbody></table></div>`
        : `<p class="k-p s">${x.change === 'removed' ? '정의에서 삭제' : x.change === 'added' ? '신규 항목 · 값은 YAML 비교 참조' : '항목별 비교 불가 · YAML 비교 참조'}</p>`;
      const notes = x.comments.map((m) => `<div class="o2-note"><b class="k-b">${esc(m.by)}</b> <span class="k-s">${esc(dayOf(m.at))}</span><div>${esc(m.text)}</div></div>`).join('');
      return `<div class="o2-open">${fields}
        ${x.readers.length ? `<div class="k-h g6"><span class="k-s">사용처</span>${x.readers.map((r) => kChip(r)).join('')}</div>` : ''}
        ${notes}<div class="k-h"><label class="k-search k-g0" style="flex:1 1 220px"><span class="k-hide">댓글</span><input type="text" id="chgtext" data-in="chgtext" value="${esc(c.text)}" placeholder="댓글"></label><button class="k-btn" data-act="chgcomment" data-el="${esc(x.element)}">등록</button>
          ${d.can_mark ? `<button class="k-btn${x.mark === 'fix' ? ' dan' : ''}" data-act="chgmark" data-el="${esc(x.element)}" data-mark="${x.mark === 'fix' ? '' : 'fix'}">${x.mark === 'fix' ? '수정 요청 취소' : '수정 요청'}</button><button class="k-btn${x.mark === 'ok' ? ' pri' : ''}" data-act="chgmark" data-el="${esc(x.element)}" data-mark="${x.mark === 'ok' ? '' : 'ok'}">${x.mark === 'ok' ? '승인됨' : '항목 승인'}</button>` : ''}
          ${to && known(to) ? `<a class="k-lnk" href="#${to}">화면 열기${ki('chevR', 14, 1.75)}</a>` : ''}</div></div>`;
    };
    const row = (x) => { const on = c.item === x.element, m = MARK_WORD[x.mark];
      return `<button class="k-row${on ? ' on' : ''}" data-act="o2chitem" data-el="${esc(x.element)}" aria-expanded="${on}"><span class="k-col"><span class="k-ink k-14">${o2Sign(x.change)} ${esc(O2_KIND[x.kind] || x.kind)} ${esc(x.label)}</span><span class="k-s">${esc(x.fields.map((f) => f.label).join(' · ') || { added: '추가', removed: '삭제', changed: '변경' }[x.change] || '')}${x.comments.length ? ` · 댓글 ${x.comments.length}` : ''}</span></span>
        <span class="k-h end">${m ? `<span class="k-chip ${m[0]}">${m[1]}</span>` : ''}</span>${ki(on ? 'chevD' : 'chevR', 16, 1.75)}</button>${on ? open(x) : ''}`; };
    const lines = (d.yaml || []).map(([t, l]) => `<span class="${t === '+' ? 'k-ok' : t === '-' ? 'k-bad' : ''}">${t === ' ' ? ' ' : t} ${esc(l) || ' '}</span>`).join('\n');
    const ready = d.can_decide && !sent && done === items.length;
    const why = !d.can_decide ? (d.self_approve ? '' : '본인 요청 승인 불가') : sent ? `수정 요청 항목 ${sent}개` : done < items.length ? `미검토 항목 ${items.length - done}개` : '전 항목 검토 완료';
    const review = d.status === 'pending'
      ? `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(d.who || '검토자')}${d.who && d.who === d.requested_by ? ' · 작성자' : ''}</span><span class="k-s">검토 요청 ${o2When(d.at)} · 항목 ${done} / ${items.length} 승인${sent ? ` · 수정 요청 ${sent}` : ''}</span></span><span class="k-h end"><span class="k-chip warn">대기</span></span></div>
         <div class="k-cb" style="padding-top:12px"><div class="k-wrap g8" style="justify-content:flex-end"><button class="k-btn" data-act="chgdecide" data-yes="0"${d.can_decide ? '' : ' disabled'}>반려</button><button class="k-btn pri" data-act="chgdecide" data-yes="1"${ready ? '' : ' disabled'}>승인 후 버전 ${cur.number + 1} 배포</button></div>
           <span class="k-s">${esc(why)}</span></div>`
      : `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(d.decided_by || '-')}</span><span class="k-s">${d.status === 'approved' ? '승인' : '반려'} ${o2When(d.decided_at)}${d.reason ? ` · ${esc(d.reason)}` : ''}</span></span><span class="k-h end"><span class="k-chip${d.status === 'approved' ? ' ok' : ''}">${d.status === 'approved' ? '승인' : '반려'}</span></span></div>`;
    return `<div class="k-v g16" style="flex:2 1 560px;min-width:0">
      <section class="k-card"><div class="k-ch"><h2><span class="k-code k-mut">${esc(d.id)}</span> ${esc(o2Title(d))}</h2><span class="k-push"><span class="k-chip${tone ? ` ${tone}` : ''}">${esc(word)}</span></span></div>
        <div class="k-cb">${o2Steps(d.status === 'approved' ? (applied ? 5 : 4) : 3)}<p class="k-p">${h && h.summary && h.summary !== o2Title(d) ? `${esc(h.summary)}. ` : ''}요청 ${esc(d.requested_by || '-')}${d.decided_by ? ` · ${d.status === 'approved' ? '승인' : '반려'} ${esc(d.decided_by)}` : ''} · ${esc(d.module_label)} ${esc(d.from_version || d.base_version || '새 모듈')} → ${esc(d.version)}${h && h.number ? ` · 버전 ${h.number}` : ''}</p></div></section>
      <section class="k-card"><div class="k-ch"><h2>변경 항목</h2><span class="k-s">추가 ${n('added')} · 수정 ${n('changed')} · 삭제 ${n('removed')}</span><span class="k-push">${o2Seg('보기', [['fields', '요약'], ['yaml', 'YAML 비교']], view, 'chgview')}</span></div>
        ${view === 'yaml' ? `<div class="k-cb"><pre class="o2-yaml k-x">${lines || '비교할 파일이 없습니다.'}</pre><span class="k-s">${d.base_version ? '모듈 파일 전체 비교' : '첫 버전 · 전체 추가'}</span></div>` : (items.map(row).join('') || '<p class="k-cf line">변경 항목 없음 · YAML 비교 참조</p>')}
        ${(d.affected || []).length ? `<div class="o2-sub"><span class="k-b k-13">영향 범위 ${d.affected.length}</span></div><div class="k-cb"><div class="k-h g6">${d.affected.map((r) => kChip(r)).join('')}</div></div>` : ''}</section>
      <section class="k-card"><div class="k-ch"><h2>회귀 테스트</h2><span class="k-push"><span class="k-chip ${d.passed ? 'ok' : 'bad'}">${d.passed ? '통과' : '미통과'}</span>${known('flow') ? `<a class="k-lnk" href="#flow">검증 결과${ki('chevR', 14, 1.75)}</a>` : ''}</span></div>
        ${o2Regression(d.regression, d.gates, d.before)}${d.issues.length ? `<div class="k-cb" style="padding-top:12px"><p class="k-note bad">${d.issues.map(esc).join('<br>')}</p></div>` : ''}</section>
      <section class="k-card"><div class="k-ch"><h2>검토</h2></div>
        <div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(d.requested_by || '-')}</span><span class="k-s">요청 ${o2When(d.at)}</span></span><span class="k-h end"><span class="k-chip">작성자</span></span></div>${review}</section></div>`;
  }

  // every version: the one being written or reviewed, the one in use, the ones kept
  function o2VersionTable(v, more, ws, open) {
    const cur = v.current, c = S.o2.ch;
    const applied = v.history.filter((x) => x.applied).sort((a, b) => b.number - a.number);
    const back = Object.fromEntries(more.rollbacks.map((b) => [b.change, b]));
    const roll = canApprove() && cur.change && !ws ? `<button class="k-lnk" data-act="o2rollback" data-id="${esc(cur.change)}"${c.busy ? ' disabled' : ''}>롤백</button>` : '';
    const rows = [];
    if (ws || open.length) rows.push(`<tr><td><span class="k-code k-ink">버전 ${cur.number + 1} 초안</span></td><td><span class="k-chip b">미리보기</span></td><td>${[ws ? '작성 중인 변경 요청' : '', ...open.map((x) => esc(x.id))].filter(Boolean).join(' · ')}</td><td>-</td><td>-</td>
      <td>${ws ? '<button class="k-lnk" data-act="o2chsel" data-id="draft">변경 항목 보기</button>' : `<button class="k-lnk" data-act="o2chsel" data-id="${esc(open[0].id)}">검토</button>`}</td></tr>`);
    applied.forEach((x) => rows.push(`<tr><td><span class="k-code k-ink">버전 ${x.number}</span></td><td>${x.number === cur.number ? '<span class="k-chip ok">운영</span>' : '<span class="k-chip">보관</span>'}</td>
      <td>${esc(x.id)} · ${esc(o2Title(x))}${x.summary && x.summary !== o2Title(x) ? ` · ${esc(x.summary)}` : ''}${back[x.id] ? ` · ${esc(back[x.id].restored)} 롤백` : ''}</td><td class="nw">${o2When(x.decided_at)}</td><td>${esc(x.decided_by || '-')}</td>
      <td><button class="k-lnk" data-act="o2chsel" data-id="${esc(x.id)}">비교</button>${x.number === cur.number ? '<a class="k-lnk" href="/api/export/library" download>내보내기</a>' : ''}${x.number === cur.number - 1 ? roll : ''}</td></tr>`));
    rows.push(`<tr><td><span class="k-code k-ink">버전 1</span></td><td>${cur.number === 1 ? '<span class="k-chip ok">운영</span>' : '<span class="k-chip">보관</span>'}</td><td>처음 구성</td><td>-</td><td>-</td>
      <td>${cur.number === 1 ? '<a class="k-lnk" href="/api/export/library" download>내보내기</a>' : ''}${cur.number === 2 ? roll : ''}</td></tr>`);
    return `<section class="k-card" id="o2vers" aria-labelledby="o2vers-h"><div class="k-ch"><h2 id="o2vers-h">버전 이력</h2></div>
      <div class="k-x"><table class="k-t end"><thead><tr><th scope="col">버전</th><th scope="col">환경</th><th scope="col">포함</th><th scope="col">배포</th><th scope="col">배포자</th><th scope="col"></th></tr></thead><tbody>${rows.join('')}</tbody></table></div></section>`;
  }

  screen('changes', {
    area: 'work', word: '변경 요청 · 버전', view: o2Changes,
    after: () => {
      const c = S.o2.ch;
      o2NeedManage('changes');
      if (!S.changes) loadChanges();
      if (!S.ver) o2LoadVersions();
      if (S.mg.st && o2DraftStale()) o2LoadDraft();
      if (S.changes && S.changes.changes && c.sel && c.sel !== 'draft' && (!S.chg.det || S.chg.det.id !== c.sel) && !S.chg.busy) loadChange(c.sel);
      if (c.jump && $('#o2vers')) { c.jump = false; $('#o2vers').scrollIntoView({ block: 'start' }); }
    },
  });
  // the older address of the version list leads to the same screen, at its versions
  screen('versions', { area: 'work', word: '변경 요청 · 버전', under: 'changes', find: false, view: o2Wait,
    after: () => { S.o2.ch.jump = true; location.replace(`${location.pathname}${location.search}#changes`); } });

  Object.assign(ACT, {
    o2jump: (t) => { const box = document.getElementById(t.dataset.to); if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' }); },
    o2chtab: (t) => { Object.assign(S.o2.ch, { tab: t.dataset.k, sel: '' }); render(); },
    o2chsel: (t) => { Object.assign(S.o2.ch, { sel: t.dataset.id, tab: '' }); S.chg.view = 'fields'; render(); $('#main').scrollTop = 0; },
    o2chitem: (t) => { S.chg.item = S.chg.item === t.dataset.el ? '' : t.dataset.el; S.chg.text = ''; render(); },
    o2rollback: async (t) => {
      const c = S.o2.ch, cur = S.ver.current;
      if (!window.confirm(`${cur.label}을(를) 롤백합니다. 이전 정의로 새 버전을 생성합니다.`)) return;
      c.busy = true; render();
      try {
        const r = await api('ont2/rollback', { change: t.dataset.id });
        c.busy = false;
        Object.assign(S, { changes: null, impact: null, agree: null });
        stale();
        Object.assign(c, { sel: r.change.id, tab: '' });
        await load();
        toast(r.pending ? `롤백 요청 ${r.change.id}을(를) 등록했습니다.` : `이전 정의로 롤백했습니다.`);
      } catch (e) { c.busy = false; render(); fail(e); }
    },
  });

  // ---- the request being written, as an item: its title and description, and throwing it away -------------------
  item('change', {
    word: '변경 요청', under: 'changes', list: 'changes', direct: true,
    lead: { form: '작성 중인 변경 요청의 제목과 설명을 편집합니다.' },
    load: async () => { if (!S.mg.st) await loadManage(); S.o2.ch.dm = await api('ont2/draft'); S.o2.ch.dmFor = S.mg.st; },
    find: (id) => (id === 'draft' ? S.o2.ch.dm : null),
    code: () => '작성 중', name: (x) => x.title || O2_UNTITLED,
    draft: (x) => { const d = x || S.o2.ch.dm || {}; return { title: d.title || '', description: d.description || '', test: 'auto' }; },
    form: (d) => {
      const ws = S.mg.st && !S.mg.st.error ? S.mg.st.workspace : null, dm = S.o2.ch.dm || {};
      const by = {};
      (ws ? [...ws.diff.added, ...ws.diff.changed, ...ws.diff.removed] : []).forEach((e) => { const k = O2_KIND[o2Split(e)[0]] || o2Split(e)[0]; by[k] = (by[k] || 0) + 1; });
      const terms = ws ? ws.edits.filter((e) => /^terms?:/.test(e.target)).length : 0;
      if (terms) by['용어'] = terms;
      const held = Object.entries(by).map(([k, n]) => `${k} ${n}`).join(' · ') || '없음';
      return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f k-full">제목<input class="k-in" type="text" data-in="itf" data-k="title" value="${esc(d.title)}" maxlength="60"></label>
        <label class="k-f k-full">설명<textarea class="k-in" rows="3" data-in="itf" data-k="description" maxlength="500">${esc(d.description)}</textarea></label>
        <label class="k-f">포함 항목<input class="k-in" type="text" value="${esc(held)}" readonly></label>
        <label class="k-f">배포 대상 버전<input class="k-in" type="text" value="${dm.next ? `버전 ${dm.next}` : '-'}" readonly></label>
        <label class="k-f">회귀 테스트<select class="k-in" data-in="itf" data-k="test"><option value="auto"${d.test === 'auto' ? ' selected' : ''}>검토 요청 시 자동 실행</option><option value="now"${d.test === 'now' ? ' selected' : ''}${ws && ws.dirty ? '' : ' disabled'}>지금 실행</option></select></label>
      </div></div></section>`;
    },
    side: () => { const ws = S.mg.st && !S.mg.st.error ? S.mg.st.workspace : null;
      return ws && ws.dirty && canEdit() ? `<section class="k-card"><div class="k-ch"><h2>폐기</h2></div><div class="k-cb"><div class="k-wrap g8"><button class="k-btn dan" data-act="o2discard">폐기</button>${known('sys-audit') && isSysAdmin() ? `<a class="k-lnk" href="#sys-audit">감사 로그${ki('chevR', 14, 1.75)}</a>` : ''}</div></div></section>` : ''; },
    saves: () => [['저장', '즉시 적용'], ['검토 요청', '<a href="#changes">변경 요청 · 버전</a>']],
    checks: (d) => {
      const ws = S.mg.st && !S.mg.st.error ? S.mg.st.workspace : null, n = ws ? ws.edits.length : 0, bad = ws ? ws.issues.length : 0;
      return [!String(d.title).trim() ? { say: '제목 없음', tone: 'bad' } : { say: '제목 있음', tone: 'ok' },
        n ? { say: bad ? `포함 항목 ${n}개 · 정의 오류 ${bad}건` : `포함 항목 ${n}개 · 정의 검사 통과`, tone: bad ? 'warn' : 'ok', word: bad ? '확인' : '' } : { say: '포함 항목 없음', tone: 'note' }];
    },
    valid: (d) => (String(d.title).trim() ? '' : '제목이 없어 저장하지 못했습니다. 제목을 입력해 주세요.'),
    save: async (d) => {
      S.o2.ch.dm = await api('ont2/draft', { title: d.title, description: d.description });
      S.o2.ch.dmFor = S.mg.st;
      if (d.test === 'now' && S.mg.st.workspace.dirty) { S.md.trial = { busy: true }; api('manage/trial', {}).then((r) => { S.md.trial = r; }).catch((e) => { S.md.trial = { error: e.message }; }).finally(() => { if (S.tab === 'changes') render(); }); }
      Object.assign(S.o2.ch, { sel: S.mg.st.workspace.dirty ? 'draft' : '', tab: '' });
    },
  });
  Object.assign(ACT, {
    o2discard: async () => {
      if (!window.confirm('작성 중인 변경 요청과 포함 항목을 모두 폐기합니다.')) return;
      try { S.mg.st = await api('manage/discard', {}); S.md.trial = null; S.lx.st = null; S.it = { key: '' }; toast('작성 중인 변경 요청을 폐기했습니다.'); location.hash = '#changes'; } catch (e) { fail(e); }
    },
  });
