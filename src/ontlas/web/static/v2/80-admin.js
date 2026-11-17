  // ==== 관리: 온톨로지 관리 (온톨로지 설정 · 멤버 · 권한) 와 시스템 관리 ==========================================
  // What these screens show is read from the server as it runs: its users file, what each route asks of a role,
  // its connections, its limits and the records it keeps. What this version does not have (groups, LDAP, licences,
  // backups) is not drawn. The few things that can be set here are the pass conditions and the users.
  S.adm = { at: '', d: {}, busy: {}, err: {}, flow: null, flowBusy: false, gates: null, typed: {}, dirty: false, saving: false,
    uq: '', mq: '', aq: '', akind: 'all', pkind: 'all', psel: '', vsel: '', test: null, testing: false, ver: false, seen: '', st: null };

  const admSig = () => `${S.st.library_id}|${S.st.pipeline}`;
  // what was read belongs to the ontology it was read from: another one starts empty
  function admFresh() {
    const A = S.adm;
    if (A.at !== admSig()) Object.assign(A, { at: admSig(), d: {}, err: {}, flow: null, gates: null, typed: {}, dirty: false, psel: '', vsel: '', test: null });
    return A;
  }
  // again: the screen was just come to, so what it shows is read again (the last reading stays drawn until then)
  function admNeed(key, path, again = false) {
    const A = admFresh(), at = A.at, tab = S.tab;
    if (A.busy[key] || (!again && (A.d[key] || A.err[key]))) return;
    A.busy[key] = true;
    api(path).then((x) => { if (S.adm.at === at) { S.adm.d[key] = x; delete S.adm.err[key]; } }, (e) => { if (S.adm.at === at) S.adm.err[key] = e.message || String(e); })
      .then(() => { A.busy[key] = false; if (S.tab === tab) render(); });  // drawn again only for the screen that asked
  }
  window.addEventListener('hashchange', () => { S.adm.seen = ''; });  // runs before the page draws the screen it goes to
  const admGot = (key) => admFresh().d[key];
  const admAgain = (key) => { const A = admFresh(); delete A.d[key]; delete A.err[key]; };
  // the version installed, at the foot of the admin menu
  function admVersion() {
    if (S.adm.ver || !S.me) return;
    S.adm.ver = true;
    api('admin/version').then((x) => { S.me.version = x.version; renderSide(); }).catch(() => {});
  }
  const admWait = () => '<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>';
  // a screen's body once its reading is here: waiting and failing are said the same way on every screen
  const admBody = (key, draw) => (S.adm.err[key] ? kEmpty('불러오지 못했습니다', S.adm.err[key], `<button class="k-btn" data-act="admRetry" data-k="${key}">다시 시도</button>`) : admGot(key) ? draw(admGot(key)) : admWait());
  const admStat = (label, big, sub = '', cls = '', quiet = false) => `<div class="k-stat${cls ? ` ${cls}` : ''}"><p class="k-s" style="margin:0">${esc(label)}</p><p class="k-big${quiet ? ' mut' : ''}">${esc(big)}</p>${sub ? `<p class="k-s" style="margin:4px 0 0">${esc(sub)}</p>` : ''}</div>`;
  // one thing that is so on this server, with a word at the right for how it stands
  const admFact = (say, sub, tone = '', word = '') => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(say)}</span>${sub ? `<span class="k-s">${esc(sub)}</span>` : ''}</span><span class="k-h end">${word ? kChip(word, tone) : ''}</span></div>`;
  const admWhen = (at) => (at ? String(at).slice(5, 16).replace('-', '/').replace('T', ' ') : '-');
  // a row picked by its name: the whole row takes a click, the name also takes the keyboard
  const admPick = (act, n, word, on) => `<button class="adm-pick${on ? ' k-b' : ''}" data-act="${act}" data-n="${esc(n)}"${on ? ' aria-current="true"' : ''}>${esc(word)}</button>`;
  const admRefocus = (act, n) => { const b = [...document.querySelectorAll(`#main button[data-act="${act}"]`)].find((x) => x.dataset.n === n); if (b) b.focus(); };
  const admRoles = (roles) => ['admin', 'approver', 'editor', 'viewer'].filter((r) => (roles || []).includes(r)).map((r) => kChip(WORK_ROLE[r], r === 'admin' || r === 'approver' ? 'b' : '')).join(' ');
  const admCode = (text) => `<div class="k-h nw"><pre class="k-pre k-g0">${esc(text)}</pre><button class="k-btn" data-act="copycode" data-v="${esc(text)}" aria-label="명령 복사">${ki('copy', 16, 1.75)}복사</button></div>`;
  // a server nobody signs in to: said once, with the way to start it for a team
  const admAlone = () => `<section class="k-card"><div class="k-ch"><h2>팀 계정</h2><span class="k-pha k-push">${kChip('사용 안 함')}</span></div><div class="k-cb"><p class="k-xs" style="margin:0">팀 모드 시작 명령</p>
    ${admCode('ontlas users add users.yaml admin --name 관리자 --roles admin')}${admCode('ontlas serve studio.yaml --users users.yaml --journal journal.jsonl')}</div></section>`;
  function admCsv(name, head, rows) {
    const cell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['﻿' + [head, ...rows].map((r) => r.map(cell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // ---- SET-01 온톨로지 설정 ----------------------------------------------------------------------------------------
  // the pass conditions a person sets here: [stage, condition, the word for it, what the number is]
  const ADM_TARGETS = [['check', 'min_accuracy', '정답률', '% 이상'], ['check', 'min_grounded', '근거 제시율', '% 이상'], ['decide', 'min_agreement', '판정 일치율', '% 이상 · 데이터 소스 연결 시'],
    ['index', 'min_found', '문서 검색 적중률', '% 이상'], ['query', 'min_agree', '저장소 간 결과 일치율', '% 이상'], ['bind', 'max_errors', 'Binding 검사 오류', '건 이하']];
  // again: read the targets again, keeping what was typed and not saved; moved: the space itself was read again
  // (초기화 puts its conditions back), so what was typed goes with what it was typed over
  function admFlow(again = false, moved = false) {
    const A = admFresh(), at = A.at, tab = S.tab;
    if (A.flowBusy || (A.flow && !(again && (moved || !A.dirty)))) return;
    A.flowBusy = true;
    api('flow/settings').then((x) => { if (S.adm.at === at) Object.assign(S.adm, { flow: x, gates: JSON.parse(JSON.stringify(x.settings.gates || {})), typed: {}, dirty: false }); },
      (e) => { if (S.adm.at === at) S.adm.flow = { error: e.message || String(e) }; }).then(() => { A.flowBusy = false; if (S.tab === tab) render(); });
  }
  const admGate = (stage, cond) => {  // what was typed and not saved is shown as typed, a wrong number too
    const typed = (S.adm.typed || {})[`${stage}.${cond}`], v = ((S.adm.gates || {})[stage] || {})[cond];
    return typed !== undefined ? typed : v === undefined || v === null ? '' : cond.startsWith('min_') ? String(Math.round(v * 1000) / 10) : String(v); };
  // what a target box holds: a share typed as a percent up to 100, a count as a whole number; anything else is NaN
  // and stops the save (Number() would take 0x50 for 80 and 1e1 for 10)
  const admRead = (cond, text) => (text === '' ? undefined : cond.startsWith('min_')
    ? (/^\d{1,3}(\.\d+)?$/.test(text) && Number(text) <= 100 ? Math.round(Number(text) * 10) / 1000 : NaN)
    : /^\d{1,6}$/.test(text) ? Number(text) : NaN);
  const admStyle = (n) => (n.total ? `${n.style} · ${n.follow} / ${n.total}` : '-');
  // the model as its last call left it: set and not yet called is 설정됨, not 연결됨
  const ADM_MODEL = { ok: '연결됨', bad: '응답 없음', idle: '설정됨', off: '미연결' };

  function admSettings() {
    const A = admFresh(), f = A.flow;
    const save = f && !f.error ? `<button class="k-btn pri" id="admsave" data-act="admSave"${A.dirty && !A.saving ? '' : ' disabled'}>${A.saving ? '저장 중' : '저장'}</button>` : '';
    const head = kHead('온톨로지 설정', '이름, 명명 규칙, 승인 정책과 품질 목표를 관리합니다.', save);
    return head + admBody('settings', (d) => {
      const ro = (label, value, hint = '') => `<label class="k-f">${label}<input class="k-in" type="text" value="${esc(value)}" readonly>${hint ? `<span class="k-hint">${hint}</span>` : ''}</label>`;
      const basic = `<section class="k-card adm-ro"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
          ${ro('이름', d.label)}${ro('식별자', d.id, 'API library 값')}
          ${ro('도메인 팩', `모듈 ${d.modules.length}개`)}${ro('운영 버전', d.version.label)}</div>
          ${d.description ? `<label class="k-f">설명<textarea class="k-in" rows="3" readonly>${esc(d.description)}</textarea></label>` : ''}
          ${known('library') ? '<a class="k-lnk flat" href="#library">모듈 라이브러리</a>' : ''}</div></section>`;
      const vocab = d.vocabularies.map((v) => v.name).join(' · ');
      const naming = `<section class="k-card adm-ro"><div class="k-ch"><h2>네임스페이스 · 명명 규칙</h2></div><div class="k-cb"><div class="k-g2">
          ${ro('네임스페이스', d.namespace)}${ro('기준 어휘', vocab || '-', `정렬된 Object · Entity ${d.aligned} / ${d.defined}`)}
          ${ro('표기', '한글@영어')}${ro('Entity 영문', admStyle(d.naming.entity))}${ro('Property 영문', admStyle(d.naming.property))}${ro('Relation', admStyle(d.naming.link))}</div>
          <div class="k-h g16">${known('lexicon') ? '<a class="k-lnk flat" href="#lexicon">용어 사전</a>' : ''}${known('sys-vocab') && isSysAdmin() ? '<a class="k-lnk flat" href="#sys-vocab">기준 어휘</a>' : ''}</div></div></section>`;
      const ai = `<section class="k-card"><div class="k-ch"><h2>AI 초안</h2></div>
          ${admFact('AI 초안 생성', `언어 모델 ${ADM_MODEL[d.model_state] || '미연결'}`, d.model_state === 'ok' ? 'ok' : d.model_state === 'bad' ? 'bad' : '', d.model ? '사용' : '사용 안 함')}
          ${known('ai') ? '<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#ai">AI 초안 생성</a></div>' : ''}</section>`;
      const targets = !f ? admWait() : f.error ? `<section class="k-card"><div class="k-ch"><h2>품질 목표</h2></div><p class="k-cf">${esc(f.error)}</p></section>`
        : `<section class="k-card"><div class="k-ch"><h2>품질 목표</h2></div><div class="k-cb"><div class="adm-g3">${ADM_TARGETS.map(([s, c, word, unit]) => `<label class="k-f">${word}<input class="k-in" type="text" inputmode="decimal" data-in="admGate" data-s="${s}" data-c="${c}" value="${esc(admGate(s, c))}" placeholder="조건 없음"><span class="k-hint">${unit}</span></label>`).join('')}</div>
          ${f.raised && f.raised.length ? `<span class="k-s">모듈 기준 우선 적용 ${f.raised.length}개</span>` : ''}</div></section>`;
      const ap = d.approval;
      const approval = `<section class="k-card"><div class="k-ch"><h2>승인 정책</h2></div>
          ${admFact('정의 변경 시 변경 요청 필수', '', 'ok', '적용')}${admFact('배포 전 회귀 테스트 통과 필수', '', 'ok', '적용')}
          ${admFact('본인 변경 요청 승인 불가', ap.self_approve ? '단독 사용 공간' : '', ap.self_approve ? '' : 'ok', ap.self_approve ? '해당 없음' : '적용')}
          ${admFact(`초안 적용 · 변경 승인 권한: ${WORK_ROLE[ap.decide_needs] || ap.decide_needs} 이상`, '', inTeam() ? 'ok' : '', inTeam() ? '적용' : '해당 없음')}
          <div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#members">역할별 권한${ki('chevR', 14, 1.75)}</a></div></section>`;
      const out = `<section class="k-card"><div class="k-ch"><h2>내보내기</h2></div><div class="k-cb"><p class="k-s" style="margin:0">정의 · 규칙 · 모듈 구성</p><div class="k-wrap g8"><a class="k-btn" href="/api/export/library">YAML</a><a class="k-btn" href="/api/export/owl">OWL · TTL</a></div></div></section>`;
      const risk = (say, sub, btn) => `<div class="k-row"><span class="k-14 k-g">${say}<br><span class="k-s">${sub}</span></span>${btn}</div>`;
      const danger = `<section class="k-card"><div class="k-ch"><h2>위험 구역</h2></div>
          ${risk('다른 서버로 이전', '온톨로지 파일 내보내기', '<a class="k-btn dan" href="/api/export/library">내보내기</a>')}
          ${d.made ? risk('삭제', '세션 생성 온톨로지 · 복구 불가', `<button class="k-btn dan" data-act="libdrop" data-id="${esc(d.id)}">삭제</button>`) : ''}
          ${inTeam() ? '' : risk('초기화', S.st.data.kept ? '변경 내용 삭제 · 저장소 파일 유지' : '업로드 자료 · 변경 내용 삭제', '<button class="k-btn dan" data-act="reset">초기화</button>')}
          ${known('ontologies') ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#ontologies">온톨로지 선택${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      return `<div class="k-cols"><div class="k-c3 wide">${basic}${naming}${ai}${targets}</div><div class="k-c2 wide">${approval}${out}${danger}</div></div>
        ${kNext([['members', '멤버 · 권한'], ['sys-gov', '거버넌스 정책'], ['changes', '변경 요청 · 버전'], ['home', '홈']])}`;
    });
  }

  // ---- SET-02 멤버 · 권한 -------------------------------------------------------------------------------------------
  const admUserHit = (u, q) => !q || `${u.name} ${u.id}`.toLowerCase().includes(q.toLowerCase());
  const admMemberRows = (d) => d.users.filter((u) => admUserHit(u, S.adm.mq)).map((u) => `<tr><td><b class="k-b">${esc(u.name)}</b></td><td><span class="k-code k-mut">${esc(u.id)}</span></td><td>${admRoles(u.roles)}</td><td>${u.signed_in ? kChip('로그인 중', 'ok') : '<span class="k-mut">-</span>'}</td>
    <td class="r">${d.managed && isSysAdmin() && V2['user-form'] ? `<a class="k-lnk" href="${itemHref('user', 'form', u.id)}">편집</a>` : ''}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">검색 결과가 없습니다.</td></tr>';
  const admMatrix = (rows) => `<div class="k-x"><table class="k-t adm-mid"><thead><tr><th scope="col">작업</th>${['admin', 'approver', 'editor', 'viewer'].map((r) => `<th scope="col" class="c">${WORK_ROLE[r]}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((m) => `<tr><td>${esc(m.label)}</td>${['admin', 'approver', 'editor', 'viewer'].map((r) => `<td class="c">${m.may[r] ? `<span class="k-blue" aria-label="${WORK_ROLE[r]} 가능">${ki('check', 16, 1.75)}</span>` : `<span class="k-mut" aria-label="${WORK_ROLE[r]} 불가">-</span>`}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;

  function admMembers() {
    const d0 = admGot('members');
    const add = d0 && d0.managed && isSysAdmin() && V2['user-form'] ? `<a class="k-btn pri" href="${itemHref('user', 'form')}">${ki('plus', 16, 1.75)}멤버 추가</a>` : '';
    const head = kHead('멤버 · 권한', '온톨로지 멤버와 작업 역할별 권한을 확인합니다.',
      `${known('connect') ? '<a class="k-btn" href="#connect">연동 · API</a>' : ''}${add}`);
    return head + admBody('members', (d) => {
      const owned = d.areas.filter((x) => x.owner).length;
      const stats = `<section class="k-wrap" aria-label="사용자 현황">${d.team ? admStat('멤버', String(d.users.length), `로그인 중 ${d.users.filter((u) => u.signed_in).length}`) : admStat('멤버', '1', '팀 계정 사용 안 함')}
        ${admStat('작업 역할', String(d.levels.length), ['admin', 'approver', 'editor', 'viewer'].map((r) => WORK_ROLE[r]).join(' · '))}${admStat('영역 담당 지정', d.areas.length ? `${owned} / ${d.areas.length}` : '-', '담당자 지정 Object')}
        ${admStat('Agent · API 키', d.rest ? String(d.clients.length) : '-', d.rest ? `쓰기 허용 ${d.clients.filter((c) => c.write).length}` : '외부 API 사용 안 함')}</section>`;
      const people = !d.team ? admAlone() : !d.managed ? kEmpty('사용자 목록을 불러오지 못했습니다', '서버 응답에 사용자 목록이 없어 표시하지 못했습니다. 서버를 다시 시작해 주세요.')
        : `<section class="k-card"><div class="k-h g12" style="padding:16px 20px"><h2 class="k-h2">멤버</h2><label class="k-search k-push" style="flex:0 1 260px">${ki('search', 15, 1.75)}<input type="search" placeholder="이름 · 아이디 검색" aria-label="사용자 검색" data-in="admUq" data-box="admmembers" value="${esc(S.adm.mq)}"></label></div>
          <div class="k-x"><table class="k-t end adm-mid"><thead><tr><th scope="col">이름</th><th scope="col">아이디</th><th scope="col">작업 역할</th><th scope="col">로그인</th><th scope="col"></th></tr></thead><tbody id="admmembers">${admMemberRows(d)}</tbody></table></div>
          <p class="k-cf">${d.users.length}명</p></section>`;
      const matrix = `<section class="k-card" style="flex:3 1 600px"><div class="k-h g12" style="padding:16px 20px"><h2 class="k-h2">작업 역할별 권한</h2></div>${admMatrix(d.matrix)}</section>`;
      const owners = `<aside class="k-card" style="flex:2 1 340px"><div style="padding:16px 20px;border-bottom:1px solid var(--row)"><h2 class="k-h2">영역 담당</h2></div>
        ${d.areas.map((x) => `<div class="k-14 adm-own"><span>${esc(x.label)}</span>${x.owner ? `<b class="k-b">${esc(x.owner)}</b>` : kChip('미지정', 'warn')}</div>`).join('') || '<p class="k-cf">Object가 없습니다.</p>'}
        ${known('objmgr') ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#objmgr">Object${ki('chevR', 14, 1.75)}</a></div>` : ''}</aside>`;
      const keys = `<section class="k-card pad k-h g12"><div style="flex:1 1 320px"><h2 class="k-h2">Agent · API 키</h2><p class="k-s" style="margin:4px 0 0">${d.rest ? `키 ${d.clients.length}개` : '외부 API 사용 안 함'}</p></div>
        ${known('roles') ? '<a class="k-btn" href="#roles">접근 정책</a>' : ''}${known('connect') ? '<a class="k-btn" href="#connect">연동 · API</a>' : ''}</section>`;
      return `${stats}${people}<div class="k-cols">${matrix}${owners}</div>${keys}${kNext([['settings', '온톨로지 설정'], ['roles', '접근 정책'], ['inbox', '할 일 · 알림'], ['home', '홈']])}`;
    });
  }

  // ---- SYS-09 관리 현황 ---------------------------------------------------------------------------------------------
  function admLevel(levels) {  // the level being worked toward and how many Entities have reached it
    const total = levels.reduce((a, b) => a + b, 0);
    if (!total) return '-';
    const low = levels.findIndex((n) => n > 0), at = Math.min(low + 1, 3);
    return low >= 3 ? 'L3' : `L${at} · ${levels.slice(at).reduce((a, b) => a + b, 0)} / ${total}`;
  }
  function admOverview() {
    const head = kHead('관리 현황', '설치 전체의 온톨로지와 처리 대기 항목을 확인합니다.',
      V2['ontology-new'] && canMakeLibrary() ? `<a class="k-btn pri" href="#ontology-new">${ki('plus', 16, 1.75)}온톨로지 만들기</a>` : '');
    return head + admBody('overview', (d) => {
      const made = d.libraries.filter((x) => x.made).length, waits = d.todo.filter((t) => ['action', 'change', 'draft'].includes(t.kind)).length;
      const stats = `<section class="k-wrap" aria-label="현황">${admStat('온톨로지', String(d.libraries.length), made ? `세션 생성 ${made}` : '서버 등록')}
        ${d.users === null ? '' : admStat('사용자', String(d.users), '팀 계정')}${admStat('승인 대기', String(waits), `현재 온톨로지 · 처리 대기 ${d.todo.length}건`, waits ? 'warn' : '')}
        ${admStat('연동 대상', d.clients === null ? '-' : String(d.clients), d.rest ? 'REST /v1 · MCP' : '외부 API 사용 안 함')}</section>`;
      const num = (v) => (v === null || v === undefined ? '<span class="k-mut">-</span>' : String(v));
      const rows = d.libraries.map((x) => `<tr><td><button class="k-lnk flat" data-act="admOpen" data-id="${esc(x.id)}">${esc(x.label)}</button></td><td>모듈 ${x.modules || 0}개</td><td>${x.source ? esc(BACKEND_KIND[String(x.source).toLowerCase()] || x.source) : '<span class="k-mut">미연결</span>'}</td>
        <td>${x.levels ? `<span class="k-code k-blue">${esc(admLevel(x.levels))}</span>` : '<span class="k-mut">-</span>'}</td><td>${x.version ? `<span class="k-code k-mut">${esc(x.version)}</span>` : '<span class="k-mut">-</span>'}</td>
        <td>${num(x.counts && x.counts.objects)}</td><td>${num(x.counts && x.counts.entities)}</td><td>${num(x.counts && x.counts.rules)}</td><td>${num(x.counts && x.counts.pending)}</td>
        <td>${x.open ? kChip('현재', 'ok') : x.made ? kChip('세션 생성') : ''}</td></tr>`).join('');
      const table = `<section class="k-card"><div class="k-ch"><h2>온톨로지</h2><span class="k-s">${d.libraries.length}개</span></div><div class="k-x"><table class="k-t end adm-wide"><thead><tr><th scope="col">이름</th><th scope="col">도메인 팩</th><th scope="col">데이터 소스</th><th scope="col">성숙도</th><th scope="col">운영 버전</th><th scope="col">Object</th><th scope="col">Entity</th><th scope="col">규칙</th><th scope="col">승인 대기</th><th scope="col">상태</th></tr></thead><tbody>${rows}</tbody></table></div>
        </section>`;
      const todo = `<section class="k-card" style="flex:3 1 520px"><div class="k-ch"><h2>처리 대기</h2><span class="k-s">${d.todo.length}건</span></div>
        ${d.todo.map((t) => { const [tone, word] = INBOX_KIND[t.kind] || ['', t.kind]; return `<a class="k-row" href="#inbox"><span class="k-col"><span class="k-ink k-14">${esc(t.title)}</span>${t.detail ? `<span class="k-s">${esc(t.detail)}</span>` : ''}</span><span class="k-h end">${kChip(word, tone === 'bad' ? 'bad' : tone === 'warn' ? 'warn' : tone === 'b' ? 'b' : '')}</span>${ki('chevR', 16, 1.75)}</a>`; }).join('') || '<p class="k-cf line">처리 대기 항목이 없습니다.</p>'}</section>`;
      const recent = `<div class="k-v g24" style="flex:2 1 380px;min-width:0"><section class="k-card"><div class="k-ch"><h2>최근 관리 활동</h2></div>
        ${d.recent.map((e) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(e.text)}</span><span class="k-s">${esc([e.by, admWhen(e.at)].filter(Boolean).join(' · '))}</span></span></div>`).join('') || '<p class="k-cf line">기록된 활동이 없습니다.</p>'}
        ${V2['sys-audit'] ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#sys-audit">감사 로그${ki('chevR', 14, 1.75)}</a></div>` : ''}</section></div>`;
      return `${stats}${table}<div class="k-cols">${todo}${recent}</div>${kNext([['sys-packs', '도메인 팩'], ['sys-gov', '거버넌스 정책'], ['sys-users', '사용자 · 그룹'], ['sys-audit', '감사 로그']])}`;
    });
  }

  // ---- SYS-04 사용자 · 그룹 -----------------------------------------------------------------------------------------
  const admUserRows = (d) => d.users.filter((u) => admUserHit(u, S.adm.uq)).map((u) => `<tr><td><b class="k-b" style="white-space:nowrap">${esc(u.name)}</b></td><td><span class="k-code k-mut">${esc(u.id)}</span></td><td>${admRoles(u.roles)}</td><td>${u.signed_in ? kChip('로그인 중', 'ok') : '<span class="k-mut">-</span>'}</td>
    <td class="r">${d.managed ? `<a class="k-lnk" href="${itemHref('user', 'form', u.id)}">편집</a>` : ''}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">검색 결과가 없습니다.</td></tr>';
  // what a role adds to the one below it, in the words of the table of what each may do
  const admAdds = (matrix, role) => matrix.filter((m) => m.needs === role).map((m) => m.label).join(' · ');

  function admUsers() {
    const d0 = admGot('users');
    const acts = d0 && d0.managed ? `<button class="k-btn" data-act="admUsersCsv">CSV로 내보내기</button><a class="k-btn pri" href="${itemHref('user', 'form')}">${ki('plus', 16, 1.75)}사용자 추가</a>` : '';
    const head = kHead('사용자 · 그룹', '서버 사용자와 역할을 관리합니다.', acts);
    return head + admBody('users', (d) => {
      const roles = `<section class="k-card"><div class="k-ch"><h2>역할</h2></div>${['admin', 'approver', 'editor', 'viewer'].map((r) => kKv(WORK_ROLE[r], `<span class="k-s">${esc(r === 'viewer' ? '정의 · 규칙 조회, 검색 · 질문' : admAdds(d.matrix, r))}</span>`)).join('')}
        ${V2['sys-auth'] ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#sys-auth">인증 · 보안${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      if (!d.team) return `${admAlone()}<div class="k-cols"><div class="k-c2">${roles}</div></div>${kNext([['sys-auth', '인증 · 보안'], ['sys-audit', '감사 로그']])}`;
      if (!d.managed) return kEmpty('사용자 목록을 불러오지 못했습니다', '서버 응답에 사용자 목록이 없어 표시하지 못했습니다. 서버를 다시 시작해 주세요.');
      const stats = `<section class="k-wrap" aria-label="현황">${admStat('사용자', String(d.users.length), d.kept ? '사용자 파일' : '메모리 보관')}${admStat('관리자', String(d.users.filter((u) => u.roles.includes('admin')).length))}
        ${admStat('로그인 중', String(d.users.filter((u) => u.signed_in).length))}</section>`;
      const table = `<section class="k-card" style="flex:3 1 620px"><div class="k-ch"><h2>사용자</h2><span class="k-pha k-push"><label class="k-search" style="flex:0 1 280px">${ki('search', 16, 1.75)}<input type="search" placeholder="이름 · 아이디 검색" aria-label="이름 · 아이디 검색" data-in="admUq" data-box="admusers" value="${esc(S.adm.uq)}"></label></span></div>
        <div class="k-x"><table class="k-t end adm-mid"><thead><tr><th scope="col">이름</th><th scope="col">아이디</th><th scope="col">역할</th><th scope="col">로그인</th><th scope="col"></th></tr></thead><tbody id="admusers">${admUserRows(d)}</tbody></table></div>
        <p class="k-cf">${d.users.length}명</p></section>`;
      return `${stats}<div class="k-cols">${table}<div class="k-v g24" style="flex:2 1 320px;min-width:0">${roles}</div></div>${kNext([['sys-auth', '인증 · 보안'], ['sys-audit', '감사 로그']])}`;
    });
  }

  // 사용자 추가 · 편집: applied at once, kept in the users file
  item('user', {
    word: '사용자', area: 'admin', list: 'sys-users', direct: true, may: () => isSysAdmin(), crumb: ['관리', '시스템 관리', '사용자 · 그룹'],
    load: async () => { admAgain('users'); S.adm.d.users = await api('admin/users'); },
    find: (id) => ((admGot('users') || {}).users || []).find((u) => u.id === id) || null,
    code: (x) => x.name, name: (x) => x.id,
    draft: (x) => ({ id: x ? x.id : '', name: x ? x.name : '', password: '', r_viewer: x ? x.roles.includes('viewer') : true, r_editor: !!x && x.roles.includes('editor'), r_approver: !!x && x.roles.includes('approver'), r_admin: !!x && x.roles.includes('admin') }),
    form: (d, x) => `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">이름<input class="k-in" type="text" data-in="itf" data-k="name" value="${esc(d.name)}" autocomplete="off"></label>
        <label class="k-f">아이디<input class="k-in" type="text" data-in="itf" data-k="id" value="${esc(d.id)}"${x ? ' readonly' : ''} autocomplete="off"><span class="k-hint">${x ? '변경 불가' : '영문 · 숫자 · . _ @ - 사용, 2자 이상'}</span></label>
        <label class="k-f">비밀번호<input class="k-in" type="password" data-in="itf" data-k="password" value="${esc(d.password)}" autocomplete="new-password"><span class="k-hint">${x ? '변경 시에만 입력' : `${(admGot('users') || {}).password_min || 10}자 이상`}</span></label>
        <div class="k-f">역할<div class="k-wrap g8">${['viewer', 'editor', 'approver', 'admin'].map((r) => `<label class="k-ck pill"><input type="checkbox" data-in="itf" data-k="r_${r}"${d[`r_${r}`] ? ' checked' : ''}>${WORK_ROLE[r]}</label>`).join('')}</div></div></div></div></section>`,
    checks: (d, x) => {
      const got = admGot('users') || { users: [], password_min: 10 };
      const roles = ['viewer', 'editor', 'approver', 'admin'].filter((r) => d[`r_${r}`]);
      const admins = got.users.filter((u) => u.roles.includes('admin') && (!x || u.id !== x.id)).length;
      const taken = !x && got.users.some((u) => u.id === d.id.trim());
      return [
        x ? null : { say: taken ? '이미 사용 중인 아이디' : '아이디 중복 없음', tone: !d.id.trim() ? 'note' : taken ? 'bad' : 'ok', word: !d.id.trim() ? '입력 대기' : '' },
        { say: `비밀번호 ${got.password_min}자 이상`, tone: !d.password ? (x ? 'note' : 'warn') : d.password.length < got.password_min ? 'bad' : 'ok', word: !d.password ? (x ? '변경 안 함' : '입력 대기') : '' },
        { say: '역할 1개 이상', tone: roles.length ? 'ok' : 'bad' },
        x && x.roles.includes('admin') ? { say: '관리자 1명 이상 유지', tone: d.r_admin || admins ? 'ok' : 'bad' } : null,
      ].filter(Boolean);
    },
    // what stops a save is said as the cause and what to do, the same sentence the server would answer with
    valid: (d, x) => {
      const got = admGot('users') || { users: [], password_min: 10 }, min = got.password_min;
      const admins = got.users.filter((u) => u.roles.includes('admin') && (!x || u.id !== x.id)).length;
      return !d.name.trim() ? '이름이 없어 저장하지 못했습니다. 이름을 입력해 주세요.' : !d.id.trim() ? '아이디가 없어 저장하지 못했습니다. 아이디를 입력해 주세요.'
        : !x && got.users.some((u) => u.id === d.id.trim()) ? `아이디 ${d.id.trim()}${josa(d.id.trim(), '이', '가')} 이미 있어 추가하지 못했습니다. 다른 아이디를 입력해 주세요.`
          : !x && !d.password ? '비밀번호가 없어 저장하지 못했습니다. 비밀번호를 입력해 주세요.'
            : d.password && d.password.length < min ? `비밀번호가 ${min}자보다 짧아 저장하지 못했습니다. ${min}자 이상 입력해 주세요.`
              : !['viewer', 'editor', 'approver', 'admin'].some((r) => d[`r_${r}`]) ? '역할이 없어 저장하지 못했습니다. 역할을 하나 이상 선택해 주세요.'
                : x && x.roles.includes('admin') && !d.r_admin && !admins ? '마지막 관리자의 관리자 역할은 해제할 수 없어 저장하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.' : '';
    },
    saves: () => [['적용', '저장 즉시'], ['기록', V2['sys-audit'] ? '<a href="#sys-audit">감사 로그</a>' : '감사 로그']],
    save: async (d, x) => {
      await api('admin/user/save', { id: d.id.trim(), name: d.name.trim(), password: d.password, roles: ['viewer', 'editor', 'approver', 'admin'].filter((r) => d[`r_${r}`]), new: !x });
      admAgain('users'); admAgain('members'); admAgain('audit'); admAgain('overview');
      return { said: x ? '사용자를 저장했습니다.' : '사용자를 추가했습니다.' };
    },
    side: (d, x) => (!x ? '' : `<section class="k-card"><div class="k-ch"><h2>계정 폐기</h2></div><div class="k-cb"><p class="k-s" style="margin:0">즉시 로그아웃 · 감사 로그 기록</p>
        <div class="k-wrap g8">${x.id === (admGot('users') || {}).me ? '<span class="k-s">본인 계정 폐기 불가</span>' : `<button class="k-btn dan" data-act="admUserDrop" data-id="${esc(x.id)}" data-name="${esc(x.name)}">폐기</button>`}${V2['sys-audit'] ? `<a class="k-lnk" href="#sys-audit">감사 로그${ki('chevR', 14, 1.75)}</a>` : ''}</div></div></section>`),
  });

  // ---- SYS-05 인증 · 보안 -------------------------------------------------------------------------------------------
  function admAuth() {
    const head = kHead('인증 · 보안', '로그인 방식, 보안 정책, 외부 통신 범위를 확인합니다.');
    return head + admBody('security', (d) => {
      const login = `<section class="k-card"><div class="k-ch"><h2>로그인 방식</h2><span class="k-pha k-push">${d.team ? kChip(d.users === null ? '로컬 계정' : `로컬 계정 · ${d.users}명`, 'ok') : kChip('팀 계정 사용 안 함')}</span></div>
        ${admFact('로컬 계정', '사용자 파일 기반 아이디 · 비밀번호', d.team ? 'ok' : '', d.team ? '사용' : '사용 안 함')}${admFact('LDAP · SSO', '', '', '사용 안 함')}${admFact('2단계 인증', '', '', '사용 안 함')}${admFact('로그인 없는 접속', '방문자별 개별 공간', d.team ? '' : 'ok', d.team ? '사용 안 함' : '사용')}
        ${V2['sys-users'] ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#sys-users">사용자 · 그룹${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      const policy = `<section class="k-card"><div class="k-ch"><h2>보안 정책</h2><span class="k-pha k-push">${kChip(d.team ? '적용 중' : '미적용', d.team ? 'ok' : '')}</span></div>
        ${kKv('세션 만료', `${d.session_hours}시간`)}${kKv('로컬 비밀번호 최소 길이', `${d.password_min}자`)}${kKv('비밀번호 보관', `<span class="k-code k-ink">${esc(d.hash)}</span> · ${Number(d.iterations).toLocaleString('ko-KR')}회`)}
        ${kKv('로그인 시도 제한', `IP당 분당 ${d.tries_per_minute}회`)}${kKv('로그인 쿠키', 'HttpOnly · SameSite=Strict · HTTPS Secure')}${kKv('요청 출처 확인', '타 사이트 요청 차단')}</section>`;
      const out = `<section class="k-card"><div class="k-ch"><h2>외부 통신</h2></div>
        ${admFact('외부 API', d.rest ? `REST /v1 · MCP · 토큰 ${d.clients.length}개` : '', d.rest ? 'ok' : '', d.rest ? '사용' : '사용 안 함')}
        ${admFact('언어 모델 호출', d.model ? '질문 · 초안 생성 시 모델 서버로 전송' : '', d.model ? 'ok' : '', d.model ? '사용' : '사용 안 함')}
        ${admFact('데이터 소스 직접 연결', '화면에서 DB 연결', d.connect ? 'ok' : '', d.connect ? '허용' : '차단')}
        ${admFact('웹 글꼴', 'cdn.jsdelivr.net', '', '외부')}
        <div class="k-cb" style="padding-top:12px">${V2['sys-ai'] ? `<a class="k-lnk flat" href="#sys-ai">AI 운영${ki('chevR', 14, 1.75)}</a>` : ''}${known('connect') ? `<a class="k-lnk flat" href="#connect">연동 · API${ki('chevR', 14, 1.75)}</a>` : ''}</div></section>`;
      const data = `<section class="k-card"><div class="k-ch"><h2>데이터 보호</h2></div>${kKv('사용자 비밀번호', '해시 보관')}${kKv('API 토큰', '환경 변수 · 파일 저장 안 함')}${kKv('DB 비밀번호', '저장 안 함')}
        ${kKv('변경 요청 · 감사 기록', d.kept ? kChip('저널 보관', 'ok') : '메모리 보관')}${V2['sys-audit'] ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#sys-audit">감사 로그${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      return `<div class="k-cols"><div class="k-c3 wide">${login}${policy}</div><div class="k-c2 wide">${out}${data}</div></div>`;
    });
  }

  // ---- SYS-03 도메인 팩 ---------------------------------------------------------------------------------------------
  const ADM_COUNT = [['areas', 'Object'], ['objects', 'Entity'], ['properties', 'Property'], ['links', 'Relation'], ['decisions', '결정표'], ['rule_cards', '규칙 카드'], ['parameters', '기준값'],
    ['terms', '용어'], ['questions', '검증 질문'], ['actions', 'Action'], ['queries', '질의'], ['roles', '접근 정책'], ['functions', '함수'], ['metrics', '지표'], ['identities', '식별 통합'],
    ['interfaces', '인터페이스'], ['conflicts', '출처 충돌'], ['extends', '확장'], ['gates', '통과 조건'], ['draft_rules', '구축 규칙'], ['messages', '문구']];
  const admHolds = (c, max = 4) => ADM_COUNT.filter(([k]) => c[k]).slice(0, max).map(([k, w]) => `${w} ${c[k]}`).join(' · ') || '-';
  function admPacks() {
    const st = S.st, rows = st.library || [];
    const kinds = [...new Set(rows.map((r) => r.kind_label))];
    const A = S.adm, shown = rows.filter((r) => A.pkind === 'all' || r.kind_label === A.pkind);
    const sel = rows.find((r) => r.name === A.psel) || shown[0] || rows[0];
    const head = kHead('도메인 팩', '분야별 표준 모듈 패키지를 확인합니다.',
      known('library') ? '<a class="k-btn" href="#library">모듈 라이브러리</a>' : '');
    if (!rows.length) return head + kEmpty('등록된 도메인 팩이 없습니다', '');
    const seg = `<div class="k-x"><div class="k-seg" role="group" aria-label="팩 종류"><button class="${A.pkind === 'all' ? 'on' : ''}" data-act="admPkind" data-k="all">전체 ${rows.length}</button>${kinds.map((k) => `<button class="${A.pkind === k ? 'on' : ''}" data-act="admPkind" data-k="${esc(k)}">${esc(k)} ${rows.filter((r) => r.kind_label === k).length}</button>`).join('')}</div></div>`;
    const state = (r) => (!r.on ? kChip('미적용') : r.version !== r.latest ? kChip(`새 버전 ${r.latest}`, 'b') : kChip('최신', 'ok'));
    const table = `<section class="k-card" style="flex:3 1 600px"><div class="k-ch"><h2>도메인 팩</h2></div><div class="k-x"><table class="k-t end adm-mid"><thead><tr><th scope="col">팩</th><th scope="col">종류</th><th scope="col">버전</th><th scope="col">포함</th><th scope="col">적용</th><th scope="col">상태</th></tr></thead>
      <tbody>${shown.map((r) => `<tr class="${sel && r.name === sel.name ? 'on' : ''}" data-act="admPsel" data-n="${esc(r.name)}"><td>${admPick('admPsel', r.name, r.label || r.name, sel && r.name === sel.name)}</td><td class="nw">${esc(r.kind_label)}</td><td><span class="k-code k-mut">${esc(r.version)}</span></td><td>${esc(admHolds(r.counts))}</td><td class="nw">${r.on ? '적용' : '<span class="k-mut">-</span>'}</td><td>${state(r)}</td></tr>`).join('')}</tbody></table></div>
      </section>`;
    const detail = !sel ? '' : `<div class="k-v g24" style="flex:2 1 360px;min-width:0"><section class="k-card"><div class="k-ch"><h2>${esc(sel.label || sel.name)} · 구성</h2></div>
      ${ADM_COUNT.filter(([k]) => sel.counts[k]).map(([k, w]) => kKv(w, `<span class="k-code k-ink">${sel.counts[k]}</span>`)).join('') || '<p class="k-cf line">포함된 정의가 없습니다.</p>'}
      ${sel.description ? `<div class="k-cb" style="padding-top:12px"><span class="k-s">${esc(sel.description)}</span></div>` : ''}</section>
      <section class="k-card"><div class="k-ch"><h2>${esc(sel.label || sel.name)} · 버전</h2></div>${kKv('적용한 버전', sel.on ? `<span class="k-code k-ink">${esc(sel.version)}</span>` : '<span class="k-mut">미적용</span>')}${kKv('라이브러리 버전', `<span class="k-code k-ink">${esc((sel.versions || [sel.latest]).join(' · '))}</span>`)}
        ${kKv('선행 팩', sel.requires && sel.requires.length ? esc(sel.requires.map((x) => modLabel(String(x).split('@')[0].split(/[<>=~ ]/)[0]) || x).join(' · ')) : '<span class="k-mut">없음</span>')}
        </section></div>`;
    return `${head}${seg}<div class="k-cols">${table}${detail}</div>${kNext([['sys-vocab', '기준 어휘'], ['sys-overview', '관리 현황'], ['ontologies', '온톨로지 선택']])}`;
  }

  // ---- SYS-10 기준 어휘 ---------------------------------------------------------------------------------------------
  function admVocab() {
    const head = kHead('기준 어휘', '온톨로지가 참조하는 표준 어휘를 확인합니다.');
    return head + admBody('vocab', (d) => {
      const sel = d.vocabularies.find((v) => v.name === S.adm.vsel) || d.vocabularies[0];
      const table = `<section class="k-card" style="flex:3 1 600px"><div class="k-ch"><h2>참조 어휘</h2></div>
        ${d.vocabularies.length ? `<div class="k-x"><table class="k-t end"><thead><tr><th scope="col">어휘</th><th scope="col">Object</th><th scope="col">Entity</th><th scope="col">Property</th><th scope="col">Relation</th></tr></thead>
        <tbody>${d.vocabularies.map((v) => `<tr class="${sel && v.name === sel.name ? 'on' : ''}" data-act="admVsel" data-n="${esc(v.name)}"><td>${admPick('admVsel', v.name, v.name, sel && v.name === sel.name)}</td>${['Object', 'Entity', 'Property', 'Relation'].map((k) => `<td>${v.counts[k] || '<span class="k-mut">-</span>'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        <p class="k-cf">전체 정의 Object ${d.defined.Object} · Entity ${d.defined.Entity} · Property ${d.defined.Property} · Relation ${d.defined.Relation}</p>` : '<p class="k-cf line">표준 어휘에 정렬된 개념이 없습니다.</p>'}</section>`;
      const rule = (word, n) => admFact(word, n.total ? `${n.follow} / ${n.total}` : '대상 없음', '', n.style || '-');
      const naming = `<section class="k-card"><div class="k-ch"><h2>명명 규칙</h2></div>${rule('Entity 영문', d.naming.entity)}${rule('Property 영문', d.naming.property)}${rule('Relation', d.naming.link)}
        ${kKv('자체 네임스페이스', `<span class="k-code k-ink" style="white-space:normal;word-break:break-all">${esc(d.namespace)}</span>`)}<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#settings">온톨로지 설정${ki('chevR', 14, 1.75)}</a></div></section>`;
      const terms = !sel ? '' : `<section class="k-card"><div class="k-ch"><h2>${esc(sel.name)}</h2><span class="k-s">${sel.terms.length}개</span></div><div class="k-x adm-terms"><table class="k-t s end"><thead><tr><th scope="col">종류</th><th scope="col">정의</th><th scope="col">어휘 이름</th></tr></thead>
        <tbody>${sel.terms.map((t) => `<tr><td>${kChip(t.kind)}</td><td>${esc(t.label)}</td><td><span class="k-code k-ink" title="${esc(t.iri)}">${esc(t.term)}</span></td></tr>`).join('')}</tbody></table></div></section>`;
      return `<div class="k-cols">${table}<div class="k-v g24" style="flex:2 1 360px;min-width:0">${naming}${terms}</div></div>${kNext([['sys-packs', '도메인 팩'], ['ontology-new', '온톨로지 만들기'], ['sys-overview', '관리 현황']])}`;
    });
  }

  // ---- SYS-06 AI 운영 -----------------------------------------------------------------------------------------------
  const ADM_LLM = { ok: ['ok', '연결됨'], bad: ['bad', '응답 없음'], idle: ['', '호출 전'], off: ['', '사용 안 함'] };
  function admAi() {
    const d0 = admGot('ai'), A = S.adm;
    const head = kHead('AI 운영', '초안 생성 · 답변 · 임베딩에 쓰는 모델의 상태를 확인합니다.',
      d0 && d0.llm.state !== 'off' ? `<button class="k-btn" data-act="admAiTest"${A.testing ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${A.testing ? '테스트 중' : '연결 테스트'}</button>` : '');
    return head + admBody('ai', (d) => {
      const llm = A.test && A.test.state ? A.test : d.llm, [tone, word] = ADM_LLM[llm.state] || ['', llm.state];
      const on = llm.state !== 'off';
      const server = `<section class="k-card"><div class="k-ch"><h2>모델 서버</h2><span class="k-pha k-push">${kChip(A.test && A.test.ms !== undefined && A.test.ok ? `${word} · 응답 ${(A.test.ms / 1000).toFixed(1)}초` : word, tone)}</span></div>
        ${kKv('연결 방식', on ? (LLM_KIND_WORD[llm.kind] || esc(llm.kind || '-')) : '사용 안 함')}${on ? kKv('주소 · 모델 이름', '서버 설정') : ''}${on ? kKv('마지막 호출', llm.at ? esc(String(llm.at).replace('T', ' ')) : '<span class="k-mut">-</span>') : ''}
        ${llm.error ? kKv('마지막 오류', `<span class="k-bad">${esc(llm.error)}</span>`) : ''}${d.ask_per_minute ? kKv('분당 질문 한도', `${d.ask_per_minute}회 · 전체 사용자`) : ''}
        </section>`;
      const uses = d.uses.filter((u) => known(u.screen));
      const table = `<section class="k-card"><div class="k-ch"><h2>모델 사용처</h2></div><div class="k-x"><table class="k-t end"><thead><tr><th scope="col">용도</th><th scope="col">화면</th><th scope="col">상태</th></tr></thead>
        <tbody>${uses.map((u) => `<tr><td>${esc(u.label)}</td><td><a href="#${u.screen}">${esc(groupOf(u.screen)[1])}</a></td><td>${!on ? kChip('사용 안 함') : llm.state === 'bad' ? kChip('응답 없음', 'bad') : kChip('사용 가능', 'ok')}</td></tr>`).join('')}</tbody></table></div>
        </section>`;
      const emb = `<section class="k-card"><div class="k-ch"><h2>임베딩 모델</h2></div>${kKv('종류', esc(d.embedder.kind || '-'))}${d.embedder.name ? kKv('이름', `<span class="k-code k-ink">${esc(d.embedder.name)}</span>`) : ''}${kKv('차원', d.embedder.dim ? String(d.embedder.dim) : '-')}
        ${known('adapters') ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#adapters">저장소 · 엔진${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      return `<div class="k-cols"><div class="k-c3 wide">${server}${table}</div><div class="k-c2 wide">${emb}${V2['sys-system'] ? `<a class="k-lnk flat" href="#sys-system" style="padding:0 16px">시스템 상태${ki('chevR', 14, 1.75)}</a>` : ''}</div></div>`;
    });
  }
  const LLM_KIND_WORD = { openai: 'OpenAI 호환 API' };

  // ---- SYS-07 감사 로그 ---------------------------------------------------------------------------------------------
  const ADM_KIND = { change: '정의 · 배포', action: '판정 · 처리', api: 'API', user: '사용자', setting: '설정', note: '활동' };
  const admAuditHit = (r) => (S.adm.akind === 'all' || r.kind === S.adm.akind) && (!S.adm.aq || `${r.by} ${r.text}`.toLowerCase().includes(S.adm.aq.toLowerCase()));
  const admAuditRows = (d) => d.rows.filter(admAuditHit).slice(0, 200).map((r) => `<tr><td><span class="k-code k-mut">${esc(admWhen(r.at))}</span></td><td>${r.by ? esc(r.by) : '<span class="k-mut">-</span>'}</td><td>${kChip(ADM_KIND[r.kind] || r.kind)}</td><td>${esc(r.text)}</td></tr>`).join('')
    || `<tr><td colspan="4" class="mut">${d.rows.length ? '검색 결과가 없습니다.' : '기록이 없습니다.'}</td></tr>`;
  const admAuditFoot = (d) => `${Math.min(d.rows.filter(admAuditHit).length, 200)} / ${d.total}건 · ${d.kept ? '저널 보관' : '메모리 보관'}`;
  function admAudit() {
    const d0 = admGot('audit'), A = S.adm;
    const head = kHead('감사 로그', '정의 변경, 배포, 판정, 외부 호출, 사용자 관리 기록을 조회합니다.', d0 && d0.rows.length ? '<button class="k-btn" data-act="admAuditCsv">CSV로 내보내기</button>' : '');
    return head + admBody('audit', (d) => {
      const bar = `<div class="k-pha"><div class="k-x"><div class="k-seg" role="group" aria-label="기록 종류"><button class="${A.akind === 'all' ? 'on' : ''}" data-act="admAkind" data-k="all">전체</button>${Object.entries(ADM_KIND).map(([k, w]) => `<button class="${A.akind === k ? 'on' : ''}" data-act="admAkind" data-k="${k}">${w}${d.counts[k] ? `&nbsp;<span class="k-m12">${d.counts[k]}</span>` : ''}</button>`).join('')}</div></div>
        <label class="k-search" style="flex:0 1 280px">${ki('search', 16, 1.75)}<input type="search" placeholder="사람 · 내용 검색" aria-label="사람 · 내용 검색" data-in="admAq" value="${esc(A.aq)}"></label></div>`;
      return `${bar}<section class="k-card"><div class="k-ch"><h2>기록</h2></div><div class="k-x"><table class="k-t end adm-wide"><thead><tr><th scope="col">시각</th><th scope="col">사람</th><th scope="col">종류</th><th scope="col">내용</th></tr></thead><tbody id="admaudit">${admAuditRows(d)}</tbody></table></div>
        <p class="k-cf" id="admauditfoot">${admAuditFoot(d)}</p></section>${kNext([['sys-users', '사용자 · 그룹'], ['sys-auth', '인증 · 보안'], ['sys-system', '시스템']])}`;
    });
  }

  // ---- SYS-08 시스템 ------------------------------------------------------------------------------------------------
  const ADM_STATE = { ok: ['ok', '정상'], bad: ['bad', '응답 없음'], idle: ['', '호출 전'], off: ['', '사용 안 함'] };
  function admSystem() {
    const d0 = admGot('system');
    const head = kHead('시스템', '설치 버전, 구성요소 상태, 한도, 기록 보관을 확인합니다.', d0 ? '<button class="k-btn" data-act="admDiag">진단 정보 내려받기</button>' : '');
    return head + admBody('system', (d) => {
      const live = d.parts.filter((p) => p.state !== 'off'), bad = live.filter((p) => p.state === 'bad').length, idle = live.filter((p) => p.state === 'idle').length;
      const up = d.uptime_minutes >= 60 ? `${Math.floor(d.uptime_minutes / 60)}시간 ${d.uptime_minutes % 60}분` : `${d.uptime_minutes}분`;
      const stats = `<section class="k-wrap" aria-label="현황">${admStat('설치 버전', d.version, `Python ${d.python}`)}${admStat('구성요소', `${live.length - bad - idle} / ${live.length} 정상`, bad ? `응답 없음 ${bad}` : idle ? `호출 전 ${idle}` : '모두 정상', bad ? 'warn' : '', true)}
        ${d.sessions ? admStat('방문자 공간', `${d.sessions.count} / ${d.sessions.limit}`, `미사용 ${d.sessions.idle_minutes}분 후 정리`) : d.team ? admStat('공간', '1', '팀 공용') : ''}${admStat('가동 시간', up, `${admWhen(d.started)} 시작`)}</section>`;
      const parts = `<section class="k-card"><div class="k-ch"><h2>구성요소 상태</h2><span class="k-pha k-push"><button class="k-lnk" data-act="admRetry" data-k="system">${ki('reload', 14, 1.75)}다시 측정</button></span></div>
        ${d.parts.map((p) => { const [tone, word] = ADM_STATE[p.state] || ['', p.state]; return admFact(p.name, p.error || p.detail, tone, word); }).join('')}
        ${V2['sys-ai'] || known('adapters') ? `<div class="k-cb" style="padding-top:12px"><div class="k-h g16">${known('adapters') ? `<a class="k-lnk flat" href="#adapters">저장소 · 엔진${ki('chevR', 14, 1.75)}</a>` : ''}${V2['sys-ai'] ? `<a class="k-lnk flat" href="#sys-ai">AI 운영${ki('chevR', 14, 1.75)}</a>` : ''}</div></div>` : ''}</section>`;
      const lim = d.limits, use = d.usage;
      const meter = (word, text, share) => `<div class="adm-use"><div class="k-14 k-h sb nw"><span>${word}</span><span class="k-code k-ink">${text}</span></div><span class="k-meter"><i style="width:${Math.min(100, Math.round(share * 100))}%"></i></span></div>`;
      const usage = `<section class="k-card"><div class="k-ch"><h2>자원 사용량</h2></div>${d.sessions ? meter('방문자 공간', `${d.sessions.count} / ${d.sessions.limit}`, d.sessions.count / d.sessions.limit) : ''}
        ${meter('업로드 자료', `${use.mb} / ${lim.total_mb} MB`, lim.total_mb ? use.mb / lim.total_mb : 0)}${meter('업로드 파일', `${use.files} / ${lim.files}`, lim.files ? use.files / lim.files : 0)}</section>`;
      const limits = `<section class="k-card"><div class="k-ch"><h2>한도</h2></div>${kKv('파일당 최대', `${Number(lim.file_kb).toLocaleString('ko-KR')} KB`)}
        ${kKv('표당 최대 행 · 열', `${Number(lim.rows).toLocaleString('ko-KR')}행 · ${lim.columns}열`)}${d.ask_per_minute ? kKv('분당 질문', `${d.ask_per_minute}회`) : ''}${kKv('온톨로지', `${d.libraries}개`)}</section>`;
      const k = d.keeps;
      const keeps = `<section class="k-card"><div class="k-ch"><h2>기록 보관</h2></div>${kKv('변경 요청 · 감사 기록', k.journal ? `<span class="k-code k-ink">${esc(k.journal_file)}</span> · ${Number(k.journal_kb).toLocaleString('ko-KR')} KB` : '메모리 보관')}
        ${kKv('승인된 변경', k.library_write ? '라이브러리 폴더 저장' : '현재 공간만 반영')}${kKv('업로드 자료', k.repositories ? '저장소 폴더 보관' : '공간 종료 시 삭제')}
        ${known('changes') ? `<div class="k-cb" style="padding-top:12px"><a class="k-lnk flat" href="#changes">변경 요청 · 버전${ki('chevR', 14, 1.75)}</a></div>` : ''}</section>`;
      return `${stats}<div class="k-cols"><div class="k-c3 wide">${parts}</div><div class="k-v g24" style="flex:2 1 360px;min-width:0">${usage}${limits}${keeps}</div></div>`;
    });
  }

  const ADM_SCREENS = [['settings', '온톨로지 설정', () => isOntoAdmin(), admSettings, (again, moved) => { admNeed('settings', 'admin/settings', again); admFlow(again, moved); }], ['members', '멤버 · 권한', () => isOntoAdmin(), admMembers, (again) => admNeed('members', 'admin/members', again)],
    ['sys-overview', '관리 현황', () => isSysAdmin(), admOverview, (again) => admNeed('overview', 'admin/overview', again)], ['sys-users', '사용자 · 그룹', () => isSysAdmin(), admUsers, (again) => admNeed('users', 'admin/users', again)],
    ['sys-auth', '인증 · 보안', () => isSysAdmin(), admAuth, (again) => admNeed('security', 'admin/security', again)], ['sys-packs', '도메인 팩', () => isSysAdmin(), admPacks, () => {}],
    ['sys-vocab', '기준 어휘', () => isSysAdmin(), admVocab, (again) => admNeed('vocab', 'admin/vocab', again)], ['sys-ai', 'AI 운영', () => isSysAdmin(), admAi, (again) => { if (again) S.adm.test = null; admNeed('ai', 'admin/ai', again); }],
    ['sys-audit', '감사 로그', () => isSysAdmin(), admAudit, (again) => admNeed('audit', 'admin/audit', again)], ['sys-system', '시스템', () => isSysAdmin(), admSystem, (again) => admNeed('system', 'admin/system', again)]];
  // a screen is read again when it is come to, and when the page read the space again (초기화, a file taken in):
  // what it showed was read from the space as it was
  ADM_SCREENS.forEach(([key, word, may, view, need]) => screen(key, { area: 'admin', word, may, view,
    after: () => { const moved = S.adm.st !== S.st, again = moved || S.adm.seen !== key; S.adm.seen = key; S.adm.st = S.st; admVersion(); need(again, moved); } }));

  Object.assign(INPUT, {
    admGate: (t) => {
      const A = S.adm, s = t.dataset.s, c = t.dataset.c, text = t.value.trim();
      if (!A.gates) return;
      A.gates[s] = A.gates[s] || {};
      const v = admRead(c, text);
      A.typed[`${s}.${c}`] = t.value;
      if (v === undefined) delete A.gates[s][c]; else A.gates[s][c] = v;
      A.dirty = true;
      const b = $('#admsave');
      if (b) b.disabled = false;
    },
    admUq: (t) => {  // 사용자 · 그룹 and 멤버 · 권한 each keep their own search
      const users = t.dataset.box === 'admusers';
      S.adm[users ? 'uq' : 'mq'] = t.value;
      const box = $(`#${t.dataset.box}`), d = admGot(users ? 'users' : 'members');
      if (box && d) box.innerHTML = users ? admUserRows(d) : admMemberRows(d);
    },
    admAq: (t) => {
      S.adm.aq = t.value;
      const d = admGot('audit');
      if (d && $('#admaudit')) { $('#admaudit').innerHTML = admAuditRows(d); $('#admauditfoot').innerHTML = admAuditFoot(d); }
    },
  });

  Object.assign(ACT, {
    admRetry: (t) => { admAgain(t.dataset.k); if (t.dataset.k === 'ai') S.adm.test = null; render(); },
    admSave: async () => {
      const A = S.adm;
      if (!A.flow || A.saving) return;
      const wrong = ADM_TARGETS.find(([s, c]) => Number.isNaN((A.gates[s] || {})[c]));
      if (wrong) { toast(`${wrong[2]} 값의 형식이 맞지 않아 저장하지 못했습니다. ${wrong[1].startsWith('min_') ? '0에서 100 사이의 숫자' : '0 이상의 정수'}를 입력해 주세요.`, true); return; }
      // only the targets changed here are sent, with what they were when read: another admin's change in the meantime
      // stays, and the same target changed by both is said back instead of overwritten
      const was = A.flow.settings.gates || {}, at = (g, s, c) => { const v = (g[s] || {})[c]; return v === undefined ? null : v; };
      const changes = ADM_TARGETS.map(([s, c]) => ({ stage: s, condition: c, was: at(was, s, c), value: at(A.gates, s, c) })).filter((x) => x.was !== x.value);
      if (!changes.length) { A.dirty = false; render(); return; }
      A.saving = true; render();
      try {
        const out = await api('admin/targets', { changes });
        A.flow.settings = out.settings;
        A.gates = JSON.parse(JSON.stringify(out.settings.gates || {}));
        A.typed = {}; A.dirty = false;
        S.flset = null; S.fl = null; S.home.ov = null;  // the screens that read the pass conditions read them again
        admAgain('audit'); admAgain('overview');
        toast(out.ok ? '품질 목표를 저장했습니다.' : out.error, !out.ok);
      } catch (e) { fail(e); }
      A.saving = false; render();
    },
    admOpen: async (t) => {  // an ontology's row on the overview: that ontology's admin screen
      if (t.dataset.id !== S.st.library_id) await libraryUse(t.dataset.id);
      location.hash = '#settings';
    },
    admPkind: (t) => { S.adm.pkind = t.dataset.k; S.adm.psel = ''; render(); },
    admPsel: (t) => { S.adm.psel = t.dataset.n; render(); if (t.tagName === 'BUTTON') admRefocus('admPsel', t.dataset.n); },
    admVsel: (t) => { S.adm.vsel = t.dataset.n; render(); if (t.tagName === 'BUTTON') admRefocus('admVsel', t.dataset.n); },
    admAkind: (t) => { S.adm.akind = t.dataset.k; render(); },
    admUsersCsv: () => { const d = admGot('users'); if (d) admCsv('ontlas-users.csv', ['아이디', '이름', '역할'], d.users.filter((u) => admUserHit(u, S.adm.uq)).map((u) => [u.id, u.name, u.roles.map((r) => WORK_ROLE[r] || r).join(' · ')])); },
    admAuditCsv: () => { const d = admGot('audit'); if (d) admCsv('ontlas-audit.csv', ['시각', '사람', '종류', '내용'], d.rows.filter(admAuditHit).map((r) => [r.at, r.by, ADM_KIND[r.kind] || r.kind, r.text])); },
    admDiag: () => {
      const d = admGot('system');
      if (!d) return;
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }));
      a.download = 'ontlas-system.json';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    },
    admAiTest: async () => {
      const A = S.adm;
      if (A.testing) return;
      A.testing = true; render();
      try { A.test = await api('admin/ai/test', {}); toast(A.test.ok ? '언어 모델 연결을 확인했습니다.' : '언어 모델이 응답하지 않아 연결을 확인하지 못했습니다. 모델 서버 상태를 확인해 주세요.', !A.test.ok); } catch (e) { fail(e); }
      A.testing = false; admAgain('ai'); render();
    },
    admUserDrop: async (t) => {
      if (!window.confirm(`사용자 ${t.dataset.name}${josa(t.dataset.name, '을', '를')} 폐기합니다.`)) return;
      try {
        await api('admin/user/drop', { id: t.dataset.id });
        ['users', 'members', 'audit', 'overview'].forEach(admAgain);
        S.it = { key: '' };
        toast('사용자를 폐기했습니다.');
        location.hash = '#sys-users';
      } catch (e) { fail(e); }
    },
  });
