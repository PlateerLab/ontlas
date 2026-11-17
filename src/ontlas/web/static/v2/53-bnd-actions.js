  // ---- BND-04 Action -----------------------------------------------------------------------------------------------
  // The actions on the left; the one chosen on the right as its definition says it, and a run that asks what a request
  // would be asked and changes nothing. Requests waiting for a person stay on 처리 요청 (#decide).
  const BND_ACT_LEAD = '처리 요청을 Parameter · 전제조건 · 호출 API로 정의합니다.';
  const bndActMark = (a) => (a.new ? ['warn', '작성 중'] : a.pending ? ['warn', '변경 대기'] : ['b', '사용 중']);
  const bndExpect = (m, c) => { const d = m.decisions.find((x) => x.name === c.decision);
    const said = Object.entries(c.expect || {}).map(([k, v]) => (v === true ? '가능' : v === false ? '불가' : `${k} ${v}`)).join(' · ');
    return `${d ? d.label : c.decision}${said ? ` 판정 = ${said}` : ''}`; };
  const bndCan = (r, verb, name) => (r[verb] || []).includes('*') || (r[verb] || []).includes(name);
  // how an action is let through: every time by a person, by itself, or by itself inside the limits it names
  function bndApproval(m, a) {
    if (a.auto_within && a.auto_within.length) {
      const props = bndOwn(m, a.target);
      const one = (l) => { const kind = LIMIT_KIND.find(([k]) => k in l), subject = l.property ? ((props.find((p) => p.name === l.property) || {}).label || l.property) : ((a.parameters.find((p) => p.name === l.parameter) || {}).label || l.parameter);
        return `${subject} ${kind ? kind[1] : ''} ${kind ? l[kind[0]] : ''}`.trim(); };
      return `${a.auto_within.map(one).join(' · ')} 이내 자동 접수 · 초과 시 승인 대기${a.auto_agents ? ' · Agent 요청 자동' : ''}`;
    }
    return a.approval ? '항상 승인 필요' : '항상 자동 실행';
  }

  function bndActTry(m, a) {
    const A = S.bnd.act, on = !noSource(), roles = S.st.roles || [], applied = S.st.actions.some((x) => x.name === a.name);
    if (!applied) return `<section class="k-card pad k-v" id="bnd-try" aria-labelledby="bnd-dry-h"><div class="k-h"><h2 class="k-h2" id="bnd-dry-h">테스트 실행</h2><span class="k-chip warn">미배포</span>${known('changes') ? '<a class="k-btn k-push" href="#changes">변경 요청 · 버전</a>' : ''}</div></section>`;
    if (!A.role && roles.length) A.role = (roles.find((r) => bndCan(m.roles.find((x) => x.name === r.name) || {}, 'request', a.name)) || roles[0]).name;
    const keys = A.keys && A.keys.type === a.target ? A.keys.list : null;
    const byRecord = on && !!A.key;
    const record = on ? `<label class="k-f" style="flex:1 1 220px">대상 ${esc(a.target_label)}<select class="k-in" data-in="bndActKey"><option value="">레코드 없음 · 값 입력</option>${(keys || []).map((k) => { const extra = Object.values(k.fields || {}).filter((v) => v !== null && v !== '' && String(v) !== String(k.key)).map(plainText).join(' · ');
      return `<option value="${esc(k.key)}"${k.key === A.key ? ' selected' : ''}>${esc(k.key)}${extra ? ` · ${esc(extra)}` : ''}</option>`; }).join('')}</select></label>` : '';
    const params = a.parameters.map((p) => `<label class="k-f" style="flex:1 1 180px">${esc(p.label || p.name)}<input class="k-in" type="text" data-in="bndActParam" data-k="${esc(p.name)}" value="${esc(A.params[p.name] ?? '')}"></label>`).join('');
    const vals = byRecord ? '' : a.criteria.filter((c) => c.decision).map((c) => { const d = m.decisions.find((x) => x.name === c.decision);
      if (!d) return '';
      const field = (i) => { const v = ((A.inputs[d.name] || {})[i.name]) ?? '', head = `${esc(i.label || i.name)}${i.unit ? ` · ${esc(i.unit)}` : ''}`;
        const ctl = (i.values || []).length ? `<select class="k-in" data-in="bndActIn" data-d="${esc(d.name)}" data-k="${esc(i.name)}"><option value="">값 없음</option>${i.values.map((x) => `<option value="${esc(x)}"${String(v) === String(x) ? ' selected' : ''}>${esc((i.labels || {})[x] ? `${i.labels[x]} · ${x}` : x)}</option>`).join('')}</select>`
          : i.type === 'boolean' ? `<select class="k-in" data-in="bndActIn" data-d="${esc(d.name)}" data-k="${esc(i.name)}"><option value="">값 없음</option><option value="true"${String(v) === 'true' ? ' selected' : ''}>예</option><option value="false"${String(v) === 'false' ? ' selected' : ''}>아니요</option></select>`
            : `<input class="k-in" type="text" data-in="bndActIn" data-d="${esc(d.name)}" data-k="${esc(i.name)}" value="${esc(v)}">`;
        return `<label class="k-f" style="flex:1 1 180px">${head}${ctl}</label>`; };
      return `<div class="k-v" style="flex:0 0 100%"><p class="k-s" style="margin:0">전제조건 입력값 · ${esc(d.label)}</p><div class="k-wrap">${d.inputs.map(field).join('')}</div></div>`; }).join('');
    const r = A.res && A.res.action === a.name ? A.res : null;
    const said = r ? [r.on_record ? `${a.target_label} ${r.key}` : '', ...a.parameters.filter((p) => String(A.params[p.name] ?? '') !== '').map((p) => `${p.label || p.name} ${A.params[p.name]}`)].filter(Boolean).join(' · ') : '';
    const out = !r ? '' : r.error ? `<p class="k-note bad">${esc(r.error)}</p>` : `<p class="k-14" style="margin:0">입력 · ${esc(said || '없음')}</p>
      <div class="k-wrap g8">${r.checks.map((c) => `<span class="k-chip ${c.passed ? 'ok' : 'bad'}">${esc(c.title)} ${c.passed ? '통과' : '불가'}</span>`).join('')}</div>
      <ul class="bnd-checks" style="padding:0">${r.checks.map((c) => `<li>${c.passed ? `<span class="k-ok">${ki('check', 16, 1.75)}</span>` : `<span class="k-bad">${ki('alert', 16, 1.75)}</span>`}<span class="k-g0"><span class="k-14">${esc(c.title)}</span><br><span class="k-s">${esc(c.detail || '')}</span></span></li>`).join('')}</ul>
      <p class="bnd-out">${r.call ? `${esc(r.call.method)} ${esc(r.call.url)}` : `${esc(a.target_label)} 값 변경`}${r.state && r.state.to ? ` · ${esc(r.state.property)} ${r.state.from ? `${esc(r.state.from)} → ` : '→ '}${esc(r.state.to)}` : ''}
        <br>→ ${r.ok ? (r.approval ? '승인 대기 접수' : '즉시 실행') : '반려'} · ${r.call ? '호출 없음' : '변경 없음'} · 테스트 실행</p>`;
    return `<section class="k-card pad k-v" id="bnd-try" aria-labelledby="bnd-dry-h"><div class="k-h sb"><h2 class="k-h2" id="bnd-dry-h">${r ? '테스트 실행 결과' : '테스트 실행'}</h2><span class="k-chip ok">${byRecord ? '레코드 값' : '입력 값'}</span></div>
      <div class="k-wrap" style="align-items:flex-end">${roles.length ? `<label class="k-f" style="flex:1 1 180px">접근 정책<select class="k-in" data-in="bndActRole">${roles.map((x) => `<option value="${esc(x.name)}"${x.name === A.role ? ' selected' : ''}>${esc(x.name)} · ${esc(x.label)}</option>`).join('')}</select></label>` : ''}${record}${params}${vals}
        <button class="k-btn pri" data-act="bndActGo"${A.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}${A.busy ? '실행 중' : '테스트 실행'}</button></div>${out}</section>`;
  }

  function bndActView() {
    const wait = bndWait('Action', BND_ACT_LEAD);
    if (wait) return wait;
    const m = bndM(), A = S.bnd.act, on = !noSource();
    const waits = ((S.pa || {}).pending || []).length;
    const head = kHead('Action', BND_ACT_LEAD, `${on && S.st.actions.length ? `<a class="k-btn" href="#decide">처리 요청${waits ? ` · 승인 대기 ${waits}` : ''}</a>` : ''}${canEdit() ? `<a class="k-btn" href="${itemHref('act', 'form')}">${ki('plus', 16, 1.75)}Action</a>` : ''}`);
    const asked = itemParam('action');
    if (asked && m.actions.some((x) => x.name === asked) && A.asked !== asked) { A.asked = asked; A.sel = asked; }
    if (!m.actions.some((x) => x.name === A.sel)) A.sel = (m.actions[0] || {}).name || '';
    const a = m.actions.find((x) => x.name === A.sel);
    if (!a) return bndPg(head + kEmpty('등록된 Action이 없습니다', '', canEdit() ? `<a class="k-btn pri" href="${itemHref('act', 'form')}">${ki('plus', 16, 1.75)}Action</a>` : '')
      + kNext([['semrules', '규칙'], ['roles', '접근 정책'], ['connect', '연동 · API'], ['objects', 'Entity'], ['query', '질의']]));
    const row = (x) => { const mk = bndActMark(x), n = x.criteria.filter((c) => c.decision || (c.states || []).length || c.function).length;
      return `<button class="bnd-arow${x.name === a.name ? ' on' : ''}" data-act="bndActSel" data-name="${esc(x.name)}"${x.name === a.name ? ' aria-current="true"' : ''}><span class="k-h sb nw"><b>${esc(x.label)}</b><span class="k-chip ${mk[0]}">${mk[1]}</span></span><span class="k-s">${esc(x.target_label)} · Parameter ${x.parameters.length} · 전제조건 ${n}</span></button>`; };
    const list = `<nav class="k-card" aria-label="Action 목록" style="flex:1 1 300px">${m.actions.map(row).join('')}</nav>`;
    const mk = bndActMark(a);
    const pre = a.criteria.map((c) => (c.decision ? `<a class="k-chip" href="#mgrules?decision=${encodeURIComponent(c.decision)}">${esc(bndExpect(m, c))}</a>` : (c.states || []).length ? `<span class="k-chip">허용 상태 ${esc(c.states.join(', '))}</span>` : c.function ? `<span class="k-chip">함수 ${esc(c.function)}</span>` : '')).join('');
    const machine = m.states.find((s) => s.object === a.target);
    const rights = m.roles.map((r) => { const verbs = [bndCan(r, 'request', a.name) ? '요청' : '', bndCan(r, 'execute', a.name) ? '실행' : ''].filter(Boolean); return verbs.length ? `<span class="k-13">${esc(r.label || r.name)} · ${verbs.join(', ')}</span>` : ''; }).join('');
    const props = bndOwn(m, a.target);
    const sets = Object.entries(a.set || {}).map(([k, v]) => `${(props.find((p) => p.name === k) || {}).label || k} = ${v}`).join(' · ');
    const half = (title, body) => `<div style="flex:1 1 220px;display:flex;flex-direction:column;gap:6px;min-width:0"><p class="k-b k-14" style="margin:0">${title}</p>${body}</div>`;
    const detail = `<section class="k-card" aria-labelledby="bnd-ac-h"><div class="k-pha bnd-sec" style="padding:16px 20px"><h2 id="bnd-ac-h" style="margin:0;font-size:20px;font-weight:600">${esc(a.label)}</h2><span class="k-code k-mut">${esc(a.name)}</span>
        <span class="k-push" style="display:flex;gap:6px"><span class="k-chip ${mk[0]}">${mk[1]}</span><span class="k-chip">${on ? '실행 · 승인 후 반영' : '실행 · 미연결'}</span></span></div>
      <div class="bnd-sec"><p class="k-b k-14" style="margin:0 0 8px">Parameter</p>${a.parameters.length ? `<div class="k-x"><table class="k-t s"><thead><tr><th scope="col">이름</th><th scope="col">타입</th><th scope="col">설명</th></tr></thead><tbody>${a.parameters.map((p) => `<tr><td class="k-code">${esc(p.name)}</td><td class="k-code">${esc(p.type)}</td><td>${esc(p.label || '-')}</td></tr>`).join('')}</tbody></table></div>` : '<span class="k-s">Parameter 없음</span>'}</div>
      <div class="k-v bnd-sec"><p class="k-b k-14" style="margin:0">전제조건 규칙</p><div class="k-wrap g8">${pre || '<span class="k-s">전제조건 없음</span>'}</div></div>
      <div class="k-wrap g16 bnd-sec">${half('처리 후 상태', `<span class="k-13">${a.transition_to ? `${esc(a.target_label)} 상태 → ${esc(a.transition_to)}` : '상태 변경 없음'}${machine ? ` · <a href="#objects?entity=${encodeURIComponent(a.target)}">상태 전이</a>` : ''}</span>${sets ? `<span class="k-13">${esc(sets)}</span>` : ''}`)}
        ${half('승인 기준', `<span class="k-13">${esc(bndApproval(m, a))}</span>`)}</div>
      <div class="k-wrap g16 bnd-sec">${half('호출 API', a.call && a.call.url ? `<span class="k-code" style="white-space:normal;overflow-wrap:anywhere">${esc(a.call.method || 'POST')} ${esc(a.call.url)}</span>${a.undo && a.undo.url ? '<span class="k-s">되돌리기 호출 있음</span>' : '<span class="k-s">되돌리기 호출 없음</span>'}` : '<span class="k-13">없음 · 소스 값 변경</span>')}
        ${half('권한', rights || '<span class="k-13">요청 가능한 접근 정책 없음</span>')}</div>
      ${a.cite ? `<div class="bnd-sec"><span class="k-s">근거 · ${esc(a.cite)}</span></div>` : ''}
      <div style="padding:12px 20px;display:flex;justify-content:flex-end;gap:8px">${canEdit() ? `<a class="k-btn" href="${itemHref('act', 'form', a.name)}">편집</a>` : ''}<button class="k-btn pri" data-act="bndActGo"${A.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}테스트 실행</button></div></section>`;
    return bndPg(`${head}${itemBar('act', a.name, a.name, a.label)}<div class="k-cols">${list}<div class="k-v g16" style="flex:2 1 560px;min-width:0">${detail}${bndActTry(m, a)}</div></div>
      ${kNext([['semrules', '규칙'], ['roles', '접근 정책'], ['connect', '연동 · API'], ['objects', 'Entity'], ['query', '질의']])}`);
  }

  function bndActAfter() {
    bndNeed();
    const m = bndM(), A = S.bnd.act;
    if (!m) return;
    if (!noSource() && !S.pa) api('actions/pending').then((r) => { S.pa = r; if (S.tab === 'actions') renderActHead(); }).catch(() => { S.pa = { pending: [] }; });
    const a = m.actions.find((x) => x.name === A.sel);
    if (a && !noSource() && (!A.keys || A.keys.type !== a.target)) {
      A.keys = { type: a.target, list: [] };
      api('keys?type=' + encodeURIComponent(a.target)).then((r) => { if (A.keys && A.keys.type === a.target) { A.keys.list = r.keys || []; if (S.tab === 'actions') render(); } }).catch(() => { /* a type with no rows to pick from is tried on given values */ });
    }
  }
  const renderActHead = () => { if (S.tab === 'actions') render(); };

  screen('actions', { area: 'work', word: 'Action', view: bndActView, after: bndActAfter });

  Object.assign(INPUT, {
    bndActRole: (t) => { S.bnd.act.role = t.value; },
    bndActKey: (t) => { S.bnd.act.key = t.value; S.bnd.act.res = null; render(); },
    bndActParam: (t) => { S.bnd.act.params[t.dataset.k] = t.value; },
    bndActIn: (t) => { const A = S.bnd.act; (A.inputs[t.dataset.d] = A.inputs[t.dataset.d] || {})[t.dataset.k] = t.value; },
  });
  Object.assign(ACT, {
    bndActSel: (t) => { Object.assign(S.bnd.act, { sel: t.dataset.name, res: null, key: '', params: {}, inputs: {}, role: '' }); render(); },
    bndActGo: async () => {
      const m = bndM(), A = S.bnd.act, a = m && m.actions.find((x) => x.name === A.sel);
      if (!a || A.busy) return;
      if (!S.st.actions.some((x) => x.name === a.name)) { toast('배포되지 않은 Action이라 테스트를 실행하지 못했습니다. 변경 요청을 승인한 뒤 실행해 주세요.', true); return; }
      A.busy = true; render();
      try { A.res = await api('bnd/action/try', { action: a.name, role: A.role, key: noSource() ? '' : A.key, params: A.params, inputs: A.inputs }); } catch (e) { A.res = { action: a.name, error: e.message }; }
      A.busy = false; render();
      const el = $('#bnd-try'); if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    },
  });
