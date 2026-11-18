  // ==== an item's own screens: 추가 · 편집, 삭제, 히스토리 ========================================================
  // An area says what a kind of item is with item(kind, {...}); the three screens are then drawn the same way for
  // every kind, and a list reaches them with itemBar / itemHref. What a kind may give:
  //   word      '규칙'                  under  the menu screen it sits under ('semrules')     list  the hash of its list
  //   area      'work' | 'admin'        direct true where saving applies at once (no delete and history screens)
  //   load      async () => {}          makes the data ready          find  (id) => x | null
  //   code      (x) => 'ST-CL-004'      name   (x) => its name        element (x) => 'rule:table.id' (history, uses)
  //   draft     (x | null) => d         the form's values             form  (d, x) => the cards of the left column
  //   checks    (d, x) => [{ say, sub, tone: 'ok' | 'note' | 'warn' | 'bad', word, error }]     tone 'bad' stops the save, said as error
  //   valid     (d, x) => '' | what is missing                         save  async (d, x) => ({ go }) | nothing
  //   side      (d, x) => cards under 저장 전 검사                        saves (d, x) => [[word, html]] in place of 저장하면
  //   uses      async (x) => [{ say, sub, href }]                      remove async (x, { mode, reason }) => ({ go })
  //   disable   true where 사용 중지 can be chosen                       history async (x) => entries   revert async (x, e)
  //   can       () => '' | why nothing can be saved here (the form is then not drawn, as a state with no save button)
  // In a form an input says which value it is with data-in="itf" data-k="<key>" (add data-re to draw the form again).
  const ITEM = {};
  S.it = { key: '' };
  const itemParam = (k) => new URLSearchParams(location.hash.split('?')[1] || '').get(k) || '';
  const itemHref = (kind, what, id) => `#${kind}-${what}${id ? `?id=${encodeURIComponent(id)}` : ''}`;
  const itemObj = (word) => word + josa(word, '을', '를');
  const formWord = (def) => `${def.word} ${def.adds ? '추가' : '추가 · 편집'}`;  // an item that is only ever added

  function item(kind, def) {
    ITEM[kind] = def;
    const base = { area: def.area || 'work', under: def.under, find: false, may: def.may };
    const crumb = def.crumb ? (w) => ({ crumb: () => [...def.crumb, w] }) : () => ({});
    screen(`${kind}-form`, { ...base, word: formWord(def), ...crumb(formWord(def)), view: () => itemForm(kind), after: () => itemLoad(kind, 'form') });
    if (def.direct) return;
    screen(`${kind}-delete`, { ...base, word: `${def.word} 삭제`, ...crumb(`${def.word} 삭제`), view: () => itemDelete(kind), after: () => itemLoad(kind, 'delete') });
    screen(`${kind}-history`, { ...base, word: `${def.word} 이력`, ...crumb(`${def.word} 이력`), view: () => itemHistory(kind), after: () => itemLoad(kind, 'history') });
  }

  // what can be done to a chosen item, as the buttons at the right of the row that names it
  const itemLocked = (def, x) => (def.locked && x ? def.locked(x) : '');  // why this item cannot be changed, if it cannot
  function itemActs(kind, id, { edit = true, history = true, del = true } = {}) {
    const def = ITEM[kind];
    if (!def) return '';
    if (def.locked && itemLocked(def, def.find(id))) { edit = false; del = false; }
    return `${edit && canEdit() ? `<a class="k-btn" href="${itemHref(kind, 'form', id)}">${ki('doc', 16, 1.75)}편집</a>` : ''}${history && !def.direct ? `<a class="k-btn" href="${itemHref(kind, 'history', id)}">${ki('history', 16, 1.75)}이력</a>` : ''}${del && !def.direct && canEdit() ? `<a class="k-btn dan" href="${itemHref(kind, 'delete', id)}">삭제</a>` : ''}`;
  }
  const itemBar = (kind, id, code, name, opt) => (ITEM[kind] ? kBar(`선택한 ${ITEM[kind].word}`, code, name, itemActs(kind, id, opt)) : '');

  function itemState(kind, what) {
    const id = itemParam('id'), key = `${kind}:${what}:${id}`;
    if (S.it.key !== key) S.it = { key, kind, what, id, x: null, d: null, ready: false, loading: false, missing: false, busy: false, err: '', uses: null, hist: null, hsel: 0, hdep: false, hall: false, hcmp: '', mode: 'request', reason: '', confirm: '' };
    return S.it;
  }

  async function itemLoad(kind, what) {
    const it = itemState(kind, what), def = ITEM[kind];
    if (it.ready || it.loading) return;
    it.loading = true;
    try {
      if (def.load) await def.load();
      it.x = it.id ? def.find(it.id) : null;
      it.missing = !!it.id && !it.x;
      if (what !== 'form' && !it.id) it.missing = true;
      if (what === 'form') it.d = def.draft(it.x);
      if (!it.missing && what === 'delete') it.uses = await (def.uses ? def.uses(it.x) : itemUsesOf(def, it.x));
      if (!it.missing && what === 'history') it.hist = await (def.history ? def.history(it.x) : itemHistoryOf(def, it.x));
    } catch (e) { it.err = e.message || String(e); }
    it.loading = false;
    it.ready = true;
    if (S.it === it) render();
  }

  // the shared reading of who uses an item and how it changed, for a kind the definition names (rule:…, object:…)
  async function itemUsesOf(def, x) {
    const el = def.element && def.element(x);
    if (!el) return [];
    const r = await api('item/uses?element=' + encodeURIComponent(el));
    return r.uses.map((u) => ({ say: `${u.kind} ${u.names.length}개`, sub: u.names.slice(0, 3).join(', ') + (u.names.length > 3 ? ` 외 ${u.names.length - 3}` : ''), href: u.screen }));
  }
  async function itemHistoryOf(def, x) {
    const el = def.element && def.element(x);
    if (!el) return [];
    const r = await api('item/history?element=' + encodeURIComponent(el));
    const WORD = { added: '추가', changed: '변경', removed: '삭제' };
    return r.entries.map((e) => ({ ver: e.version ? `v${e.version}` : '', mark: e.status_label, cp: e.change, at: e.at, who: e.by, deployed: e.deployed,
      say: (e.notes || []).map((n) => n.text).join(' · ') || e.reason || `${def.word} ${WORD[e.kind] || '변경'}`,
      rows: e.fields.map((f) => ({ label: f.label, before: f.said && f.said[0] != null ? f.said[0] : f.before, after: f.said && f.said[1] != null ? f.said[1] : f.after })),
      all: e.all || [] }));  // every field as the item read then, in words
  }

  const itemWait = () => '<section class="k-card pad"><p class="k-p s">불러오는 중</p></section>';
  const itemGone = (def) => kEmpty(`${itemObj(def.word)} 찾을 수 없습니다`, '', `<a class="k-btn pri" href="#${def.list}">목록으로</a>`);
  // reading failed: what was said, a way to read again, and the way back
  const itemFailed = (def, it) => kEmpty('불러오지 못했습니다', it.err, `<button class="k-btn pri" data-act="itreload">다시 불러오기</button><a class="k-btn" href="#${def.list}">목록으로</a>`);
  const itemNamed = (def, it, acts) => `<div class="k-bar"><span class="k-s">${esc(def.word)}</span>${def.code ? `<span class="k-code k-ink">${esc(def.code(it.x))}</span>` : ''}<span class="k-14">${esc(def.name(it.x))}</span><span class="k-push">${acts}</span></div>`;
  const CHECK_TONE = { ok: ['ok', '통과'], note: ['b', '참고'], warn: ['warn', '확인'], bad: ['bad', '수정 필요'] };
  const itemChecks = (def, it) => (def.checks ? def.checks(it.d, it.x) : []).map((c) => { const [tone, word] = CHECK_TONE[c.tone] || CHECK_TONE.ok;
    return `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(c.say)}</span>${c.sub ? `<span class="k-s">${esc(c.sub)}</span>` : ''}</span><span class="k-h end"><span class="k-chip ${tone}">${esc(c.word || word)}</span></span></div>`; }).join('');

  function itemForm(kind) {
    const def = ITEM[kind], it = itemState(kind, 'form'), isNew = !it.id;
    const lead = (def.lead && def.lead.form) || `${itemObj(def.word)} 추가하거나 편집합니다.`;
    const saveWord = def.saveWord || (def.direct ? '저장' : '변경 요청에 저장');
    const shut = (def.can ? def.can() : '') || itemLocked(def, it.x);  // a form that cannot be saved shows that state alone
    const head = kHead(formWord(def), lead, `<a class="k-btn" href="#${def.list}">취소</a>${it.ready && !it.missing && !it.err && !shut && canEdit() ? `<button class="k-btn pri" data-act="itsave"${it.busy ? ' disabled' : ''}>${esc(it.busy ? '저장 중' : saveWord)}</button>` : ''}`);
    if (!it.ready) return head + itemWait();
    if (it.err) return head + itemFailed(def, it);
    if (it.missing) return head + itemGone(def);
    if (!canEdit()) return head + kEmpty('편집 권한이 없습니다', '', `<a class="k-btn" href="#${def.list}">목록으로</a>`);
    if (shut) return head + kEmpty(shut, '', `<a class="k-btn" href="#${def.list}">목록으로</a>`);
    const seg = `<div class="k-h g12"><div class="k-seg" role="group" aria-label="추가 또는 편집"><a href="${itemHref(kind, 'form')}" class="${isNew ? 'on' : ''}"${isNew ? ' aria-current="true"' : ''}>추가</a><a ${isNew ? 'aria-disabled="true"' : `href="${itemHref(kind, 'form', it.id)}" aria-current="true"`} class="${isNew ? '' : 'on'}">편집</a></div></div>`;
    const bar = isNew ? '' : itemNamed(def, it, itemActs(kind, it.id, { edit: false }));
    const rows = (def.saves && def.saves(it.d, it.x)) || (def.direct
      ? [['반영', '즉시 적용'], ['기록', known('sys-audit') && isSysAdmin() ? '<a href="#sys-audit">감사 로그</a>' : '감사 로그']]
      : [['반영', '변경 요청 승인 후 배포'], ['변경 요청', '<a href="#changes">작성 중인 변경 요청</a>'], ['검토', selfApply() ? '회귀 테스트 후 자동 승인' : '승인자 승인'], ['회귀 테스트', '변경 요청 등록 시 실행']]);
    const checks = itemChecks(def, it);
    const reason = def.direct || def.noReason ? '' : `<section class="k-card"><div class="k-ch"><h2>변경 사유</h2></div><div class="k-cb"><label class="k-f"><textarea class="k-in" rows="3" data-in="itf" data-k="reason" aria-label="변경 사유">${esc(it.d.reason || '')}</textarea></label><span class="k-hint">편집 시 필수</span></div></section>`;
    return `${head}${seg}${bar}<div class="k-cols"><div class="k-c3">${def.form(it.d, it.x)}${reason}</div>
      <div class="k-c2"><section class="k-card"><div class="k-ch"><h2>저장 결과</h2></div>${rows.map(([k, v]) => kKv(k, v)).join('')}</section>
        ${def.checks ? `<section class="k-card"><div class="k-ch"><h2>저장 전 검사</h2></div><div id="itchecks">${checks}</div></section>` : ''}
        ${def.side ? def.side(it.d, it.x) : ''}
      </div></div>`;
  }

  function itemDelete(kind) {
    const def = ITEM[kind], it = itemState(kind, 'delete');
    const head = kHead(`${def.word} 삭제`, (def.lead && def.lead.delete) || `사용처를 확인하고 삭제를 요청합니다.`,
      it.ready && !it.missing ? `<a class="k-btn" href="${itemHref(kind, 'history', it.id)}">${ki('history', 16, 1.75)}이력</a>${canEdit() && !itemLocked(def, it.x) ? `<a class="k-btn" href="${itemHref(kind, 'form', it.id)}">편집</a>` : ''}` : '');
    if (!it.ready) return head + itemWait();
    if (it.err) return head + itemFailed(def, it);
    if (it.missing) return head + itemGone(def);
    if (!canEdit()) return head + kEmpty('삭제 권한이 없습니다', '', `<a class="k-btn" href="#${def.list}">목록으로</a>`);
    if (itemLocked(def, it.x)) return head + kEmpty(itemLocked(def, it.x), '', `<a class="k-btn" href="#${def.list}">목록으로</a>`);
    const code = def.code ? def.code(it.x) : def.name(it.x);
    const uses = (it.uses || []).map((u) => `<${u.href ? `a href="#${u.href}"` : 'div'} class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(u.say)}</span>${u.sub ? `<span class="k-s">${esc(u.sub)}</span>` : ''}</span>${u.href ? ki('chevR', 16, 1.75) : ''}</${u.href ? 'a' : 'div'}>`).join('')
      || '<div class="k-row"><span class="k-s">사용처 없음</span></div>';
    const radio = (mode, word, say) => `<label class="k-ck"><input type="radio" name="itmode" value="${mode}" data-in="itmode"${it.mode === mode ? ' checked' : ''}><span>${word}<br><span class="k-s">${say}</span></span></label>`;
    const ok = it.reason.trim() && it.confirm.trim() === code;
    return `${head}<section class="k-card narrow"><div class="k-v" style="padding:24px 24px 16px"><h2 class="k-h2" style="font-size:20px">${esc(def.name(it.x))}</h2><div class="k-h">${def.code ? `<span class="k-code k-mut">${esc(code)}</span>` : ''}<span class="k-s">${esc(def.word)}</span></div></div>
      <div style="padding:0 24px 8px"><p class="k-p b">사용처</p></div>${uses}
      <div class="k-v g12" style="padding:16px 24px 24px;border-top:1px solid var(--row)">
        ${radio('request', '삭제 요청', '승인 후 다음 버전에서 제외')}
        ${def.disable ? radio('disable', '사용 중지', '판정 · 검색 · API 응답에서 제외') : ''}
        <label class="k-f">삭제 사유<textarea class="k-in" rows="3" data-in="itreason">${esc(it.reason)}</textarea><span class="k-hint">필수</span></label>
        <label class="k-f">확인 입력 · ${esc(code)}<input class="k-in" type="text" data-in="itconfirm" value="${esc(it.confirm)}" placeholder="${esc(code)}" autocomplete="off"></label>
        <div class="k-h end"><a class="k-btn" href="#${def.list}">취소</a><button class="k-btn red" id="itremove" data-act="itremove"${ok && !it.busy ? '' : ' disabled'}>${it.mode === 'disable' ? '사용 중지' : '삭제 요청'}</button></div>
      </div></section>`;
  }

  function itemHistory(kind) {
    const def = ITEM[kind], it = itemState(kind, 'history');
    const head = kHead(`${def.word} 이력`, (def.lead && def.lead.history) || `${def.word}의 변경 이력을 조회합니다.`,
      `<a class="k-btn" href="#${def.list}">목록으로</a>${it.ready && !it.missing && canEdit() && !itemLocked(def, it.x) ? `<a class="k-btn pri" href="${itemHref(kind, 'form', it.id)}">${ki('doc', 16, 1.75)}편집</a>` : ''}`);
    if (!it.ready) return head + itemWait();
    if (it.err) return head + itemFailed(def, it);
    if (it.missing) return head + itemGone(def);
    const all = it.hist || [], list = it.hdep ? all.filter((e) => e.deployed) : all;
    const sel = list[Math.min(it.hsel, Math.max(list.length - 1, 0))];
    const bar = itemNamed(def, it, itemActs(kind, it.id, { history: false }));
    const when = (at) => (at ? esc(String(at).slice(5, 16).replace('-', '/').replace('T', ' ')) : '');
    const rows = list.map((e, i) => `<button class="k-row tight${e === sel ? ' on' : ''}" data-act="ithsel" data-i="${i}"${e === sel ? ' aria-current="true"' : ''}><span class="k-h sb"><span class="k-h">${e.ver ? `<span class="k-code k-ink">${esc(e.ver)}</span>` : ''}${e.mark ? `<span class="k-s">${esc(e.mark)}</span>` : ''}${e.cp ? `<span class="k-code k-mut">${esc(e.cp)}</span>` : ''}</span><span class="k-s">${when(e.at)}</span></span><span class="k-14">${esc(e.say)}</span><span class="k-s">${esc(e.who || '')}</span></button>`).join('')
      || '<p class="k-cf line">변경 이력이 없습니다.</p>';
    const said = (v) => (v === null || v === undefined || v === '' ? '<span class="k-mut">-</span>' : show(v));
    // 다른 버전과 비교: the chosen change beside another one, field by field, as each left the item (older on the left)
    const named = (e) => [e.ver, e.mark, e.cp].filter(Boolean).join(' ') || '선택한 변경';
    const others = sel && (sel.all || []).length ? list.filter((e) => e !== sel && (e.all || []).length) : [];
    const cmp = it.hcmp !== '' && others.includes(list[Number(it.hcmp)]) ? list[Number(it.hcmp)] : null;
    const compared = () => {
      const [old, now] = list.indexOf(cmp) > list.indexOf(sel) ? [cmp, sel] : [sel, cmp];
      const a = new Map(old.all.map((r) => [r.label, r.value])), b = new Map(now.all.map((r) => [r.label, r.value]));
      const same = (x, y) => JSON.stringify(x === undefined ? null : x) === JSON.stringify(y === undefined ? null : y);
      const labels = [...new Set([...old.all, ...now.all].map((r) => r.label))].filter((l) => it.hall || !same(a.get(l), b.get(l)));
      return `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">항목</th><th scope="col">${esc(named(old))}</th><th scope="col">${esc(named(now))}</th></tr></thead><tbody>${labels.map((l) => `<tr><td class="b">${esc(l)}</td><td class="k-bad">${said(a.get(l))}</td><td class="k-ok">${said(b.get(l))}</td></tr>`).join('') || '<tr><td colspan="3" class="mut">차이 없음</td></tr>'}</tbody></table></div>`;
    };
    const table = !sel ? '' : cmp ? compared() : it.hall
      ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">항목</th><th scope="col">값</th></tr></thead><tbody>${sel.all.map((r) => `<tr><td class="b">${esc(r.label)}</td><td>${said(r.value)}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">항목</th><th scope="col">이전</th><th scope="col">이후</th></tr></thead><tbody>${sel.rows.map((r) => `<tr><td class="b">${esc(r.label)}</td><td class="k-bad">${said(r.before)}</td><td class="k-ok">${said(r.after)}</td></tr>`).join('') || '<tr><td colspan="3" class="mut">변경 항목 없음</td></tr>'}</tbody></table></div>`;
    const revert = sel && def.revert && canEdit() && !itemLocked(def, it.x) && sel.deployed && sel !== all[0] ? '<button class="k-btn" data-act="itrevert">이 시점으로 되돌리기</button>' : '';
    const pick = cmp ? `<select class="k-in sm" style="width:auto;max-width:240px" data-in="ithcmp" aria-label="비교 버전">${others.map((e) => `<option value="${list.indexOf(e)}"${e === cmp ? ' selected' : ''}>${esc(named(e))}</option>`).join('')}</select><button class="k-btn" data-act="ithcmp" data-v="">비교 닫기</button>`
      : others.length ? '<button class="k-btn" data-act="ithcmp">다른 버전과 비교</button>' : '';
    const detail = !sel ? '<p class="k-cf">선택된 변경이 없습니다.</p>' : `${table}${kKv('변경자', esc(sel.who || '-'))}${kKv('시각', when(sel.at) || '-')}${sel.cp ? kKv('변경 요청', `<a href="#changes?id=${encodeURIComponent(sel.cp)}">${esc(sel.cp)}</a>`) : ''}${kKv('사유', esc(sel.say))}
      ${pick || revert ? `<div class="k-cb" style="padding-top:12px"><div class="k-h">${pick}${revert}</div></div>` : ''}`;
    const title = !sel ? '변경 내용' : cmp ? '버전 비교' : `${esc([sel.ver, sel.mark].filter(Boolean).join(' ') || '선택한 변경')} 변경 내용`;
    return `${head}${bar}<div class="k-cols"><div class="k-c2"><section class="k-card"><div class="k-ch"><h2>변경 이력</h2><span class="k-s">${all.length}건</span><div class="k-push"><div class="k-seg"><button class="${it.hdep ? '' : 'on'}" data-act="ithdep" data-v="">전체</button><button class="${it.hdep ? 'on' : ''}" data-act="ithdep" data-v="1">배포</button></div></div></div>${rows}</section></div>
      <div class="k-c3"><section class="k-card"><div class="k-ch"><h2>${title}</h2>${sel ? `<div class="k-push"><div class="k-seg"><button class="${it.hall ? '' : 'on'}" data-act="ithall" data-v="">변경 항목</button><button class="${it.hall ? 'on' : ''}" data-act="ithall" data-v="1">전체 항목</button></div></div>` : ''}</div>${detail}</section>
      </div></div>${kNext([['changes', '변경 요청 · 버전'], ['sys-audit', '감사 로그']])}`;
  }

  // leaving an item's screen forgets what was typed there: the next visit starts from the item as it is
  window.addEventListener('hashchange', () => { if (S.it.key && !S.it.key.startsWith(`${location.hash.slice(1).split('?')[0].replace(/-(form|delete|history)$/, '')}:`)) S.it = { key: '' }; });
  let itemTimer = 0;
  Object.assign(INPUT, {
    itf: (t) => {
      const it = S.it, def = ITEM[it.kind];
      if (!it.d) return;
      it.d[t.dataset.k] = t.type === 'checkbox' ? t.checked : t.value;
      if ('re' in t.dataset) { render(); return; }
      clearTimeout(itemTimer);
      itemTimer = setTimeout(() => { const box = $('#itchecks'); if (box && S.it === it) box.innerHTML = itemChecks(def, it); }, 200);
    },
    itmode: (t) => { S.it.mode = t.value; render(); },
    itreason: (t) => { S.it.reason = t.value; itemArm(); },
    itconfirm: (t) => { S.it.confirm = t.value; itemArm(); },
    ithcmp: (t) => { S.it.hcmp = t.value; render(); },
  });
  // an edit that leaves every value as the item has it: nothing to file, only the reason would be kept
  const itemSame = (def, it) => { const plain = (d) => JSON.stringify({ ...d, reason: '' }); try { return plain(it.d) === plain(def.draft(it.x)); } catch (_) { return false; } };
  function itemArm() {  // the delete button wakes when there is a reason and the name is typed
    const it = S.it, def = ITEM[it.kind], b = $('#itremove');
    if (b) b.disabled = !(it.reason.trim() && it.confirm.trim() === (def.code ? def.code(it.x) : def.name(it.x))) || it.busy;
  }

  Object.assign(ACT, {
    itsave: async () => {
      const it = S.it, def = ITEM[it.kind];
      clearTimeout(itemTimer);  // a check waiting on what was typed would read the screen the save leaves
      if (!it.d || it.busy || (def.can && def.can())) return;
      const missing = def.valid ? def.valid(it.d, it.x) : '';
      const stop = (def.checks ? def.checks(it.d, it.x) : []).find((c) => c.tone === 'bad');
      // a check says its own sentence (error); else it is said in the one form, with what it names
      if (missing || stop) { toast(missing || stop.error || `저장 전 검사에서 ${stop.say}${stop.sub ? ` · ${stop.sub}` : ''} 항목이 확인되어 저장하지 못했습니다. 이 항목을 고쳐 주세요.`, true); return; }
      if (it.id && !def.direct && itemSame(def, it)) { toast('변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.', true); return; }
      if (it.id && !def.direct && !def.noReason && !String(it.d.reason || '').trim()) { toast('변경 사유가 없어 저장하지 못했습니다. 변경 사유를 입력해 주세요.', true); return; }
      it.busy = true; render();
      try {
        const out = (await def.save(it.d, it.x)) || {};
        const el = !def.direct && String(it.d.reason || '').trim() && def.element ? (out.element || (it.x ? def.element(it.x) : '')) : '';
        if (el) await api('element/comment', { id: el, text: it.d.reason }).catch(() => {});  // why, kept beside the item
        S.it = { key: '' };
        toast(out.said || (def.direct ? `${itemObj(def.word)} 저장했습니다.` : '작성 중인 변경 요청에 저장했습니다.'));
        location.hash = '#' + (out.go || def.list);
      } catch (e) { it.busy = false; render(); fail(e); }
    },
    itremove: async () => {
      const it = S.it, def = ITEM[it.kind];
      if (it.busy || !def.remove) return;
      it.busy = true; itemArm();
      try {
        const el = def.element ? def.element(it.x) : '';
        const out = (await def.remove(it.x, { mode: it.mode, reason: it.reason.trim() })) || {};
        if (el) await api('element/comment', { id: el, text: `${it.mode === 'disable' ? '사용 중지' : '삭제 요청'} · ${it.reason.trim()}` }).catch(() => {});
        S.it = { key: '' };
        toast(out.said || (it.mode === 'disable' ? '사용을 중지했습니다.' : '작성 중인 변경 요청에 삭제를 추가했습니다.'));
        // a delete request lands on the change request it went into, open; what is taken out at once goes back to its list,
        // and so does one that left nothing to send (an item added in the same request, taken out again)
        const empty = S.mg.st && S.mg.st.workspace && !S.mg.st.workspace.dirty;
        location.hash = '#' + (out.go || (def.direct || it.mode === 'disable' || empty || !known('changes') ? def.list : 'changes?id=draft'));
      } catch (e) { it.busy = false; render(); fail(e); }
    },
    ithsel: (t) => { S.it.hsel = Number(t.dataset.i); if (S.it.hcmp === t.dataset.i) S.it.hcmp = ''; render(); },
    ithdep: (t) => { S.it.hdep = !!t.dataset.v; S.it.hsel = 0; S.it.hcmp = ''; render(); },
    ithcmp: (t) => {  // 다른 버전과 비교 starts with the change just before the chosen one; 비교 닫기 ends it
      const it = S.it;
      if ('v' in t.dataset) { it.hcmp = ''; render(); return; }
      const list = it.hdep ? it.hist.filter((e) => e.deployed) : it.hist, at = Math.min(it.hsel, list.length - 1);
      const ok = (i) => i !== at && (list[i].all || []).length;
      const keys = [...list.keys()], i = keys.filter((k) => k > at).find(ok);
      it.hcmp = String(i !== undefined ? i : keys.find(ok));
      render();
    },
    ithall: (t) => { S.it.hall = !!t.dataset.v; render(); },
    itrevert: async () => {
      const it = S.it, def = ITEM[it.kind], list = it.hdep ? it.hist.filter((e) => e.deployed) : it.hist, e = list[it.hsel];
      if (!e || !def.revert) return;
      try { const out = (await def.revert(it.x, e)) || {}; S.it = { key: '' }; toast(out.said || '작성 중인 변경 요청에 되돌리기를 저장했습니다.'); location.hash = '#' + (out.go || 'changes'); } catch (err) { fail(err); }
    },
    itreload: () => { const it = S.it; if (it.kind) { S.it = { key: '' }; render(); } },  // the screen reads its item again
  });
