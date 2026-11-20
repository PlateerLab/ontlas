  // ==== 운영 › 저장소 · 엔진 (adapters), 연동 · API (connect), 접근 정책 (roles), and the items they hold ==========
  // Each screen reads what the server measures now: the stores that answer, the callers of /v1 the server was started
  // with, the roles of the definition. Nothing here is a sample.

  S.ops = { key: '', tg: null, cn: null, busy: {}, sec: 'cfg', fold: {}, sel: '', landed: '', shown: '', top: 0, tryPol: '', who: {}, reidx: false };
  const OPS_TABS = ['adapters', 'connect', 'roles'];
  const opsMine = () => OPS_TABS.includes(S.tab) || S.tab === 'vectors' || S.tab.startsWith('policy-') || S.tab.startsWith('store-');

  // read once, kept until the ontology or its data is another one; an error is kept as { error } so it is not asked again
  function opsRead(slot, path, get = () => S.ops[slot], set = (x) => { S.ops[slot] = x; }) {
    if (get() || S.ops.busy[slot]) return;
    S.ops.busy[slot] = true;
    api(path).then(set).catch((e) => set({ error: e.message || String(e) })).finally(() => { S.ops.busy[slot] = false; if (opsMine()) render(); });
  }
  function opsFresh() {
    const k = `${S.st.library_id}:${S.st.pipeline}`;
    if (S.ops.key === k) return;
    if (S.ops.key) S.conn = null;  // the decisions, Entities and policies a call is tried on are another ontology's now
    Object.assign(S.ops, { key: k, tg: null, cn: null, sel: '', tryPol: '', who: {} });
  }
  const opsGood = (x) => (x && !x.error && !x.busy ? x : null);
  const opsWait = (say = '불러오는 중입니다.') => `<section class="k-card pad"><p class="k-p s">${esc(say)}</p></section>`;
  const opsFailed = (say) => kEmpty('불러오지 못했습니다', say, '<button class="k-btn" data-act="opsRetry">다시 시도</button>');
  const opsCopy = (text, say) => `<button class="k-lnk ops-copy" data-act="copycode" data-v="${esc(text)}" aria-label="${esc(say)}" title="${esc(say)}">${ki('copy', 16, 1.75)}</button>`;
  const opsTake = (text, word) => `<button class="k-btn sm" data-act="copycode" data-v="${esc(text)}">${esc(word)}</button>`;
  const opsPre = (text, say) => `<div class="ops-pre"><pre class="k-pre">${esc(text)}</pre>${opsCopy(text, say)}</div>`;
  // a text a person may want whole (a command, a settings file): folded until asked for, and it stays as left
  const opsMore = (key, title, text) => `<details class="ops-more" data-cn="${key}"${S.cn[key] ? ' open' : ''}><summary>${ki('chevR', 14, 1.75)}${esc(title)}</summary>${opsPre(text, `${title} 복사`)}</details>`;
  const opsFold = (key, word, body) => `<div class="ops-fold"><button class="k-lnk flat" data-act="opsFold" data-k="${key}" aria-expanded="${!!S.ops.fold[key]}">${ki(S.ops.fold[key] ? 'chevD' : 'chevR', 14, 1.75)}${word}</button>${S.ops.fold[key] ? body : ''}</div>`;
  const opsTargets = () => { const t = opsGood(S.ops.tg); return t ? t.targets : []; };

  // ---- OPS-01 저장소 · 엔진 ----------------------------------------------------------------------------------------

  const OPS_LOGIC = { rules: '규칙 판정 · AXIOM › Custom › Standard', owl2rl: 'OWL 2 RL · 계층 · 관계 추론', shapes: 'Restriction · 제약 검사' };
  const OPS_LLM = { off: '미연결', idle: '연결됨 · 호출 전', ok: '연결됨', bad: '응답 없음' };

  async function opsCheck() {  // every store asked the same questions, the reasoners run: the page runs it once on opening
    S.adbusy = true; render();
    try { S.adrep = await api('adapters/check', {}); S.adrs = null; S.ops.cn = null; } catch (e) { fail(e); }
    S.adbusy = false; render();
  }
  // what the stores hold changed: read them again and check again, the screen left as it is (and where it is) meanwhile
  async function opsReload() {
    try { S.ad = await api('adapters'); } catch (e) { S.ad = { error: e.message || String(e) }; render(); return; }
    opsCheck();
  }

  function opsStorage() {
    const a = S.ad, rep = S.adrep, cn = opsGood(S.ops.cn), sp = opsGood(S.sp), tg = opsGood(S.ops.tg);
    const canAdd = !!(a && a.can_connect) && isSysAdmin();
    const head = kHead('저장소 · 엔진', '저장소, 질의 언어, 추론 엔진, 임베딩의 구성과 상태를 확인합니다.',
      `<button class="k-btn" data-act="opsCheck"${S.adbusy || !a || a.error ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.adbusy ? '점검 중' : '저장소 점검'}</button>${canAdd && ITEM.store ? `<a class="k-btn pri" href="${itemHref('store', 'form')}">${ki('plus', 16, 1.75)}저장소 추가</a>` : ''}`);
    if (!a) return head + opsWait('구성을 불러오는 중입니다.');
    if (a.error) return head + opsFailed(a.error);
    const st = S.st;
    const seg = `<nav class="k-seg self" aria-label="화면 구역">${[['cfg', '구성'], ['vec', '벡터 · 임베딩'], ['ext', '사용처']].map(([k, w]) => `<button class="${S.ops.sec === k ? 'on' : ''}" data-act="opsGo" data-to="ops${k}" data-k="${k}">${w}</button>`).join('')}</nav>`;
    // the tiles: what is set up, counted from the same rows as the tables under them
    const several = a.backends.length > 1;
    const rowsAll = 1 + a.backends.length + a.vectors.length + (a.source.connected ? 0 : 1);
    const down = (cn ? cn.stores.filter((x) => x.state === 'bad').length : 0) + a.vectors.filter((v) => v.error).length;
    const langsOk = a.languages.filter((l) => l.compiled === a.queries).length;
    const tile = (label, big, sub) => `<div class="k-stat ops-tile"><p>${label}</p><p class="k-big">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const dash = (label, big, sub) => `<div class="ops-dash ops-tile"><p class="k-s">${label}</p><p class="k-big mut">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const agree = !several ? dash('저장소 간 결과 일치', '미연결', '비교 기준 · 데이터 소스')
      : tile('저장소 간 결과 일치', rep && rep.graph ? `${rep.graph.agree} / ${rep.graph.queries}` : S.adbusy ? '<span class="k-mut k-14">점검 중</span>' : '-', rep ? `점검 ${esc(String(rep.graph_ms))}ms` : '비교 기준 · 데이터 소스');
    const tiles = `<section class="k-wrap" aria-label="구성 요약">
      ${tile('저장소', `${rowsAll - (a.source.connected ? 0 : 1) - down} <span class="k-mut k-14" style="font-weight:400">/ ${rowsAll}</span>`, a.source.connected ? (down ? `응답 없음 ${down}` : '모두 정상') : '데이터 소스 미연결')}
      ${tile('질의 변환 언어', `${langsOk} / ${a.languages.length}`, `등록 질의 ${count(a.queries)}개 기준`)}
      ${tile('추론 엔진', count(a.reasoners.length), esc(a.reasoners.map((r) => r.name).join(' · ')) || '-')}
      ${tile('임베딩', a.embedder.dim ? `${count(a.embedder.dim)} <span class="k-mut k-14" style="font-weight:400">차원</span>` : '-', esc(a.embedder.kind))}
      ${agree}</section>`;
    // the stores: the definition's own files, where the rows are, where the graph is, where the passages are
    const dom = (st.layers.find((l) => l.kind === 'domain') || st.layers[0] || { modules: [] }).modules[0];
    const seen = (name) => (cn ? cn.stores.find((x) => x.name === name) : null);
    const said = (x) => (!x ? '' : x.state === 'bad' ? `<span class="k-chip bad" title="${esc(x.error)}">응답 없음</span>` : x.state === 'idle' ? '<span class="k-chip">호출 전</span>' : `<span class="k-chip ok">응답 ${esc(String(x.ms))}ms</span>`);
    const graphAgree = rep && rep.graph ? `<span class="k-chip ${rep.graph.agree === rep.graph.queries ? 'ok' : 'bad'}">${rep.graph.agree === rep.graph.queries ? '데이터 소스와 일치' : '데이터 소스와 다름'} ${rep.graph.agree} / ${rep.graph.queries}</span>` : '';
    const check = sp && sp.check;
    const dropCol = canAdd && a.vectors.length > 1;
    const storeRows = [`<tr><td class="k-code b">library</td><td>정의 원본</td><td>YAML 모듈 ${count(st.modules_on)}개</td><td>Object · Entity · 규칙 · 버전</td><td><span class="k-chip ok">기준${dom ? ` · v${esc(dom.version)}` : ''}</span></td>${dropCol ? '<td></td>' : ''}</tr>`]
      .concat(a.backends.map((b) => { const x = seen(b.name);
        return `<tr><td class="k-code b">${esc(b.name)}</td><td>${b.source ? '데이터 소스' : '그래프 저장소'}</td><td>${x ? `${esc(BACKEND_KIND[String(x.kind).toLowerCase()] || x.kind)} · ${esc(x.language)}` : `${esc(b.language)} ${esc(b.dialect || '')}`}</td>
          <td>${b.source ? `레코드 값${b.write ? ' · Action 반영' : ''} · 비교 기준` : `판정 · 질의 · 그래프 탐색${b.load ? ' · 데이터 소스 변경분 반영' : ''}`}</td><td><span class="k-h g6">${said(x)}${b.source ? '' : graphAgree}</span></td>${dropCol ? '<td></td>' : ''}</tr>`; }))
      .concat(a.vectors.map((v) => { const r = rep && rep.vectors[v.name];
        const state = v.error ? `<span class="k-chip bad">${esc(v.error)}</span>` : `${check ? `<span class="k-chip ${check.found === check.questions ? 'ok' : 'warn'}">검색 적중 ${check.found} / ${check.questions}</span>` : '<span class="k-chip ok">색인됨</span>'}${r && !r.error ? `<span class="k-chip ${r.agree ? 'ok' : 'bad'}">검색 결과 일치 ${Math.round(r.overlap * 100)}%</span>` : r && r.error ? `<span class="k-chip bad">${esc(r.error)}</span>` : ''}`;
        return `<tr><td class="k-code b">${esc(v.name)}</td><td>벡터 저장소</td><td>${esc(v.kind)} · ${esc(v.metric)}<br><span class="k-s">지원 ${esc(a.vector_kinds.join(' · '))}</span></td><td>문서 청크 ${count(v.count)}개 · 정의 검색</td><td><span class="k-h g6">${state}</span></td>
          ${dropCol ? `<td class="r">${v.primary ? '' : `<button class="k-lnk bad" data-act="opsStoreDrop" data-name="${esc(v.name)}">삭제</button>`}</td>` : ''}</tr>`; }))
      .concat(a.source.connected ? [] : [`<tr class="ops-off"><td class="k-code b">source</td><td>데이터 소스</td><td>-</td><td>레코드 값 · Action 반영 · 비교 기준</td><td>${known('db') ? '<a class="k-chip dash" href="#db">미연결 · 데이터 소스</a>' : '<span class="k-chip dash">미연결</span>'}</td>${dropCol ? '<td></td>' : ''}</tr>`]).join('');
    const stores = `<section class="k-card" id="opscfg" aria-labelledby="ops-st-h"><div class="k-ch"><h2 id="ops-st-h">저장소</h2></div>
      <div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">구분</th><th scope="col">종류</th><th scope="col">역할</th><th scope="col">상태</th>${dropCol ? '<th scope="col"></th>' : ''}</tr></thead><tbody>${storeRows}</tbody></table></div></section>`;
    // the languages: every registered query compiled now; a language a store reads also runs there
    const langRows = a.languages.filter((l) => l.backends.length).concat(a.languages.filter((l) => !l.backends.length)).map((l) => {
      const why = l.refused.length ? `<br><span class="k-s">${l.refused.slice(0, 3).map((x) => `${esc(x.query)}: ${esc(x.error)}`).join('<br>')}</span>` : '';
      const ran = l.backends.length ? l.backends.map((n) => `<span class="k-chip ok">${esc(n)} · 실행</span>`).join(' ') : '<span class="k-chip">변환만</span>';
      return `<tr><td${l.backends.length ? ' class="b"' : ''}>${esc(l.label)}</td><td>${l.compiled === a.queries ? `${l.compiled} / ${a.queries}` : `<span class="k-warn">${l.compiled} / ${a.queries}</span>`}${why}</td><td>${ran}</td></tr>`;
    }).join('');
    const langs = `<section class="k-card" aria-labelledby="ops-ql-h" style="flex:3 1 520px"><div class="k-ch"><h2 id="ops-ql-h">질의 언어</h2><span class="k-s k-push">등록 질의 ${count(a.queries)}개 기준</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">언어</th><th scope="col">변환</th><th scope="col">실행 저장소</th></tr></thead><tbody>${langRows}</tbody></table></div></section>`;
    // the reasoners: each run on the projected graph, when asked or by the check. The check runs every reasoner it can
    // whenever the graph store holds the projected rows, so one it did not run has no graph to run on
    const reasRows = a.reasoners.map((r) => {
      const x = (S.adrs || {})[r.name] || (rep && rep.runs && rep.runs[r.name]);
      const bare = !r.missing && !x && rep && !S.adbusy;
      const found = x && (x.found !== undefined ? x.found : (x.findings || []).length);
      const g = rep && rep.reasoners && rep.reasoners[r.logic], twin = g && Object.keys(g.engines).length > 1;
      const mark = r.missing ? `<span class="k-chip warn">${esc(r.missing)}</span>` : bare ? '<span class="k-chip">그래프 데이터 없음</span>' : !x ? (S.adbusy ? '<span class="k-chip">점검 중</span>' : '') : x.error ? `<span class="k-chip bad" title="${esc(x.error)}">실행 실패</span>` : `<span class="k-chip ${found ? 'warn' : 'ok'}">${found ? `발견 ${count(found)}건` : '발견 없음'}</span>`;
      const last = x && !x.error ? `<br><span class="k-s">추론 결과 ${count(x.count)}건 · ${esc(String(x.ms))}ms${twin ? ` · 동일 논리 엔진 대비 ${g.same ? '일치' : '불일치'}` : ''}</span>` : x && x.error ? `<br><span class="k-s k-bad">${esc(x.error)}</span>` : '';
      return `<div class="ops-reas"><span class="k-g0"><span class="k-code k-b">${esc(r.name)}</span><br><span class="k-s">${esc(OPS_LOGIC[r.logic] || r.logic)}</span>${last}</span>${mark}${r.missing ? '' : `<button class="k-lnk" data-act="adreason" data-name="${esc(r.name)}"${bare ? ' disabled' : ''}>실행</button>`}</div>`;
    }).join('');
    const reas = `<section class="k-card" aria-labelledby="ops-rz-h" style="flex:2 1 340px"><div class="k-ch ops-line"><h2 id="ops-rz-h">추론 엔진</h2></div>${reasRows || '<p class="k-cf">등록된 추론 엔진이 없습니다.</p>'}</section>`;
    return `${head}${seg}${tiles}${stores}<div class="k-cols">${langs}${reas}</div>${opsVectors(a, sp, cn)}${opsUsedBy(a, tg)}
      ${kNext([['query', '질의'], ['sys-ai', 'AI 운영'], ['monitor', '파이프라인 관제'], ['sys-system', '시스템']])}`;
  }

  // the embedding model, the engine that finds things for a question, and what is indexed
  function opsVectors(a, sp, cn) {
    const e = a.embedder, ret = a.retriever, none = '<span class="k-mut">-</span>';
    const llm = cn ? cn.llm : null;
    const llmRow = llm ? `<tr><td class="b">언어 모델</td><td class="ops-mono">${llm.state === 'off' ? none : esc(llm.kind === 'openai' ? 'OpenAI 호환 API' : llm.kind || '-')}<br><span class="${llm.state === 'bad' ? 'k-bad' : 'k-mut'}">${esc(llm.state === 'bad' ? llm.error || OPS_LLM.bad : llm.state === 'ok' && llm.at ? `마지막 호출 ${String(llm.at).replace('T', ' ')}` : OPS_LLM[llm.state] || '')}</span></td><td>초안 · 설명 · 질문 답변</td></tr>` : '';
    const table = `<div class="k-x" style="flex:2 1 420px;min-width:0"><table class="k-t s end"><thead><tr><th scope="col">구분</th><th scope="col">이름</th><th scope="col">지원 종류</th></tr></thead><tbody>
      <tr><td class="b">임베딩 모델</td><td class="ops-mono">${esc(e.name)}<br><span class="k-mut">${e.dim ? `${count(e.dim)}차원 · ` : ''}${e.semantic ? '의미 비교' : '글자 비교'}</span></td><td>${esc(a.embedder_kinds.join(' · '))}</td></tr>
      <tr><td class="b">검색 엔진</td><td class="k-code">${esc(ret.kind)}</td><td>${esc(ret.kinds.join(' · '))}</td></tr>${llmRow}</tbody></table></div>`;
    const held = `<div class="k-v ops-held"><p class="k-s k-b" style="margin:0">색인 대상</p>${Object.entries(ret.by_kind).map(([k, n]) => `<div class="k-h sb k-14"><span>${esc(k)}</span><b>${count(n)}</b></div>`).join('')}<div class="k-h sb k-14"><span>연결</span><b>${count(ret.links)}</b></div></div>`;
    let more = '';
    if (!S.sp || S.sp.busy) more = '<p class="k-cf line">색인 상태를 불러오는 중입니다.</p>';
    else if (S.sp.error) more = `<div class="k-cb"><p class="k-note bad">${esc(S.sp.error)}</p></div>`;
    else {
      const v = S.vemb, choices = (sp.embedders || []).filter((c) => !(c.kind === e.kind && (c.name || '') === e.name));
      const plan = v && v.plan ? `<div class="k-v"><div class="k-h g6"><span class="k-chip">문서 ${count(v.plan.files.length)}개</span><span class="k-chip">청크 ${count(v.plan.chunks)}개</span><span class="k-chip">${count(v.plan.chars)}자</span><span class="k-chip warn">예상 ${v.plan.seconds < 1 ? '1초 미만' : `약 ${Math.ceil(v.plan.seconds)}초`}</span></div>
          <p class="k-note warn">벡터 저장소 초기화 · 전체 청크 재임베딩</p>
          <div class="k-h"><button class="k-btn pri sm" data-act="vembuse"${v.busy ? ' disabled' : ''}>${v.busy ? '임베딩 중' : '변경 후 재임베딩'}</button><button class="k-btn sm" data-act="vembcancel">취소</button></div></div>` : '';
      const change = choices.length && isSysAdmin() ? opsFold('model', '임베딩 모델 변경', `<div class="k-v ops-in"><div class="k-h"><select class="k-in ops-pick" data-in="vemb" aria-label="임베딩 모델"><option value="">모델 선택</option>${choices.map((c) => { const at = (sp.embedders || []).indexOf(c); return `<option value="${at}"${v && String(v.pick) === String(at) ? ' selected' : ''}>${esc(c.name || c.kind)}${c.dim ? ` · ${c.dim}차원` : ''}</option>`; }).join('')}</select>
          <button class="k-btn" data-act="vembplan"${!v || v.pick === '' || v.busy ? ' disabled' : ''}>${v && v.busy && !v.plan ? '측정 중' : '영향 확인'}</button></div>${plan}</div>`) : '';
      const docs = opsFold('docs', `문서별 임베딩 ${count(sp.items.length)}`, `<div class="k-x ops-in"><table class="k-t s end"><thead><tr><th scope="col">문서</th><th scope="col">경로</th><th scope="col" class="r">항목</th><th scope="col" class="r">색인 청크</th><th scope="col">상태</th></tr></thead><tbody>${sp.items.map((d) => { const [tone, word] = EMBED_STATE[d.state] || ['', d.state === 'none' ? '내용 없음' : d.state];
        return `<tr><td class="b">${esc(d.name)}</td><td class="k-code mut">${esc(d.path || '기본 문서')}</td><td class="r">${d.sections}</td><td class="r">${d.chunks} / ${d.passages}</td><td><span class="k-chip${tone ? ` ${tone}` : ''}">${word}</span></td></tr>`; }).join('')}</tbody></table></div>`);
      const c = sp.check;
      const hits = c ? opsFold('check', `문서 검색 검증 ${c.found} / ${c.questions}`, `<div class="k-x ops-in"><table class="k-t s end"><thead><tr><th scope="col">질문</th><th scope="col">정답 문서</th><th scope="col">순위</th></tr></thead><tbody>${c.results.map((x) => `<tr><td>${esc(x.text)}</td><td>${esc(x.document)}</td><td>${x.rank ? `${x.rank}위` : '<span class="k-chip bad">미포함</span>'}</td></tr>`).join('')}</tbody></table>
        <p class="k-p s" style="margin-top:8px">기준 · 상위 ${c.k}건</p></div>`) : '';
      more = `${sp.embed_error ? `<div class="k-cb"><p class="k-note bad">임베딩 모델 오류로 일부 문서를 임베딩하지 못했습니다. ${esc(sp.embed_error)} 임베딩 모델 연결을 확인해 주세요.</p></div>` : ''}<div class="ops-folds">${change}${docs}${hits}</div>`;
    }
    return `<section class="k-card" id="opsvec" aria-labelledby="ops-vec-h"><div class="k-ch"><h2 id="ops-vec-h">벡터 · 임베딩</h2>${canEdit() ? `<div class="k-push"><button class="k-btn" data-act="opsReindex"${S.ops.reidx ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.ops.reidx ? '색인 중' : '재색인'}</button></div>` : ''}</div>
      <div class="k-wrap g16" style="padding:0 20px 20px">${table}${held}</div>${more}</section>`;
  }

  // who takes this ontology from outside, and whether rows come in from a source
  function opsUsedBy(a, tg) {
    const mark = (icon, cls) => `<span class="ops-mark${cls}">${ki(icon, 20, 1.75)}</span>`;
    const names = tg ? tg.targets.map((t) => t.name) : [];
    const callers = `<div class="k-card pad k-v" style="flex:1 1 320px"><div class="k-h nw">${mark('plug', ' b')}<div class="k-g0"><b>연동 대상${tg && tg.listed ? ` ${count(names.length)}` : ''}</b><p class="k-s" style="margin:0">${tg ? esc(!tg.rest ? 'REST API 꺼짐' : names.length ? names.join(' · ') : 'REST API 켜짐') : ''}</p></div></div>
      <div class="k-wrap g8"><a class="k-btn" href="#connect">연동 · API</a><a class="k-lnk" href="#roles">접근 정책</a></div></div>`;
    const on = a.source.connected, kind = BACKEND_KIND[String(a.source.kind || '').toLowerCase()] || a.source.kind || a.source.name || '';
    const source = `<div class="k-v ${on ? 'k-card pad' : 'ops-dash'}" style="flex:1 1 320px;min-width:0${on ? '' : ';padding:20px'}"><div class="k-h nw">${mark('db', '')}<div class="k-g0"><b>데이터 소스</b><p class="k-s" style="margin:0">${on ? `${esc(kind)} · 연결됨` : '미연결'}</p></div></div>
      ${known('db') ? `<a class="k-btn" href="#db" style="align-self:flex-start">${on ? '데이터 소스' : '데이터 소스 연결'}</a>` : ''}</div>`;
    return `<section class="k-v g12" id="opsext" aria-labelledby="ops-ext-h"><h2 class="k-h2" id="ops-ext-h">사용처</h2><div class="k-wrap g16" style="align-items:stretch">${callers}${source}</div></section>`;
  }

  function opsStorageAfter() {
    opsFresh();
    opsRead('tg', 'ops/targets');
    opsRead('cn', 'connections');
    opsRead('ad', 'adapters', () => S.ad, (x) => { S.ad = x; if (!x.error && !S.adrep && !S.adbusy) setTimeout(() => { if (S.tab === 'adapters' || S.tab === 'vectors') opsCheck(); }, 0); });
    opsRead('sp', 'space', () => S.sp, (x) => { S.sp = x; });
  }
  screen('adapters', { area: 'work', word: '저장소 · 엔진', view: opsStorage, after: opsStorageAfter });
  // the older address of the vector screen opens the same screen at its section: when first drawn, and once more when
  // the check has filled the rows above it, unless the person has scrolled since
  screen('vectors', {
    area: 'work', word: '저장소 · 엔진', under: 'adapters', find: false,
    view: () => { S.ops.sec = 'vec'; return opsStorage(); },
    after: () => {
      opsStorageAfter();
      const el = $('#opsvec'), main = $('#main'), key = String(!!S.adrep);
      if (!el || S.ops.shown === key) return;
      if (!S.ops.shown || main.scrollTop === S.ops.top) { el.scrollIntoView({ block: 'start' }); S.ops.top = main.scrollTop; }
      S.ops.shown = key;
    },
  });
  // each arrival at #vectors scrolls to its section; at #adapters the screen opens at its top, its first section lit
  window.addEventListener('hashchange', () => { S.ops.shown = ''; S.ops.sec = 'cfg'; });

  Object.assign(ACT, {
    opsRetry: () => { ['tg', 'cn'].forEach((k) => { if (S.ops[k] && S.ops[k].error) S.ops[k] = null; }); if (S.ad && S.ad.error) S.ad = null; if (S.sp && S.sp.error) S.sp = null; if (S.conn && S.conn.error) S.conn = null; if (S.mg.st && S.mg.st.error) S.mg.st = null; render(); },
    opsCheck: () => opsCheck(),
    opsGo: (t) => { S.ops.sec = t.dataset.k; t.parentNode.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b === t)); const el = document.getElementById(t.dataset.to); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); },
    opsFold: (t) => { S.ops.fold[t.dataset.k] = !S.ops.fold[t.dataset.k]; render(); },
    opsReindex: async () => {
      if (S.ops.reidx) return;
      S.ops.reidx = true; render();
      let done = false;
      try { const r = await api('ops/reindex', {}); S.sp = r.space; toast(`청크 ${count(r.chunks)}개의 색인을 생성했습니다.`); done = true; } catch (e) { fail(e); }
      S.ops.reidx = false;
      if (done) opsReload(); else render();
    },
    opsStoreDrop: async (t) => {
      if (!window.confirm(`벡터 저장소 ${t.dataset.name}${josa(t.dataset.name, '을', '를')} 삭제합니다.`)) return;
      try { S.sp = await api('space/store', { op: 'remove', name: t.dataset.name }); toast(`벡터 저장소 ${t.dataset.name}${josa(t.dataset.name, '을', '를')} 삭제했습니다.`); opsReload(); } catch (e) { fail(e); }
    },
  });

  // ---- OPS-02 연동 · API ---------------------------------------------------------------------------------------------
  // The callers the server was started with, the ways an agent takes the ontology, the addresses, and one call tried
  // here as a platform makes it. The try panel keeps the names the older screen gave its controls (ctry…): the state
  // (S.ctry) and most handlers are the same ones.

  const OPS_NEEDS_SOURCE = new Set(['run_query', 'run_sparql', 'run_cypher', 'get_record', 'request_action']);

  function opsApi() {
    opsFresh();
    const i = S.conn, tg = opsGood(S.ops.tg), base = location.origin;
    const head = kHead('연동 · API', '외부 Agent · 플랫폼의 연동 방법과 API를 관리합니다.',
      '<a class="k-btn" href="/v1/openapi.json" download="ontlas-openapi.json">OpenAPI 내려받기</a>');
    if (!i) return head + opsWait();
    if (i.error) return head + opsFailed(i.error);
    const list = tg ? tg.targets : [];
    const tile = (label, big, sub, warn) => `<div class="k-stat${warn ? ' warn' : ''}"><p>${label}</p><p class="k-big${warn ? ' warn' : ''}">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const tiles = `<section class="k-wrap" aria-label="현황">
      ${tile('연동 대상', tg && tg.listed ? count(list.length) : i.rest ? '-' : '0', esc(!i.rest ? 'REST API 꺼짐' : list.length ? list.map((t) => t.name).join(' · ') : 'REST API 켜짐'), !i.rest)}
      ${tg && tg.listed ? tile('이번 달 호출', count(tg.calls_month), `하루 평균 ${count(Math.round((tg.calls_month / (tg.days || 1)) * 10) / 10)}`) : ''}
      ${tile('REST 도구', count(i.tools.length), 'OpenAPI 문서 포함')}
      ${i.libraries > 1 ? tile('온톨로지', count(i.libraries), '요청의 library 값으로 지정') : ''}</section>`;
    // who may call: named by the server, each with the policy it runs as
    const roles = new Set((S.st.roles || []).map((r) => r.name));
    // a caller with no policy is refused unless the server opens /v1 to it (ontlas serve --api-open)
    const policy = (t) => (!t.policy ? (tg.unscoped ? '<span class="k-chip warn">정책 없음 · 전체 조회</span>' : '<span class="k-chip bad">정책 없음 · 거부</span>') : roles.has(t.policy) ? `<a class="k-code" href="#roles?policy=${encodeURIComponent(t.policy)}">${esc(t.policy)}</a>` : `<span class="k-code k-ink">${esc(t.policy)}</span> <span class="k-chip warn">이 온톨로지에 없음</span>`);
    const rows = list.map((t) => `<tr><td><b class="k-b">${esc(t.name)}</b></td><td>REST</td><td>${policy(t)}</td><td>${!t.policy && !tg.unscoped ? '<span class="k-mut">-</span>' : `조회 · 판정 · 검색${t.write ? ' · Action 요청' : ''}`}</td><td class="r">${count(t.calls)}</td><td>${t.last ? esc(String(t.last).slice(0, 16).replace('T', ' ')) : '<span class="k-mut">-</span>'}</td></tr>`).join('');
    // the examples name a policy of this ontology (its first), with the caller attributes its row rules compare with
    const pol = (S.st.roles || [])[0], keys = pol ? pol.principal || [] : [];
    const serveRest = `export ONTLAS_API_TOKEN=...\nontlas serve studio.yaml --api-token-env ONTLAS_API_TOKEN${pol ? ` --api-role ${pol.name}${keys.map((k) => ` --api-principal ${k}=...`).join('')}` : ' --api-open'}`;
    const agents = `# agents.yaml\nagents:\n  - {name: ${JSON.stringify(pol ? pol.label : 'Agent')}, token_env: ONTLAS_AGENT_TOKEN${pol ? `, role: ${pol.name}` : ''}${keys.length ? `, principal: {${keys.map((k) => `${k}: ...`).join(', ')}}` : ''}, write: true}\n\nontlas serve studio.yaml --api-agents agents.yaml`;
    const targets = `<section class="k-card" aria-labelledby="ops-tg-h"><div class="k-ch"><h2 id="ops-tg-h">연동 대상</h2><div class="k-push k-h g6">${tg ? `<span class="k-chip${tg.action_write ? '' : ' warn'}">${tg.action_write ? 'Action 쓰기 켜짐' : 'Action 쓰기 꺼짐'}</span>` : ''}<span class="k-chip ${i.rest ? 'ok' : 'warn'}">${i.rest ? 'REST API 켜짐' : 'REST API 꺼짐'}</span></div></div>
      ${rows ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">연결</th><th scope="col">접근 정책</th><th scope="col">허용 도구</th><th scope="col" class="r">호출 수</th><th scope="col">마지막 사용</th></tr></thead><tbody>${rows}</tbody></table></div>`
    : '<p class="k-cf line">등록된 연동 대상이 없습니다.</p>'}
      <div class="k-cb" style="padding-top:12px;gap:4px">${opsMore('serve', 'REST API 활성화 명령', serveRest)}${opsMore('agents', 'Agent별 토큰 · 역할 설정', agents)}</div></section>`;
    // the ways an agent takes it, each with what a person copies to do so
    const mcpArgs = ['mcp', 'studio.yaml', ...(pol ? ['--role', pol.name, ...keys.flatMap((k) => ['--principal', `${k}=...`])] : []), '--read-only'];
    const mcpCmd = `ontlas ${mcpArgs.join(' ')}`;
    const mcpConf = JSON.stringify({ mcpServers: { ontlas: { command: 'ontlas', args: mcpArgs } } }, null, 2);
    const curl = `curl ${base}/v1/search -H "Authorization: Bearer $ONTLAS_API_TOKEN" \\\n  -H "Content-Type: application/json" -d '{"text": "반품 기간", "k": 3}'`;
    const gateway = 'backends:\n  source:\n    kind: gateway\n    url: https://platform.example/query\n    connection: 12\n    dialect: postgres\n    token_env: PLATFORM_TOKEN\n    source: true';
    const way = (name, say, acts) => `<div class="ops-way"><p><b>${name}</b><br><span class="k-s">${say}</span></p><div class="k-h g6">${acts}</div></div>`;
    const ways = `<section class="k-card" aria-labelledby="ops-way-h"><div class="k-ch"><h2 id="ops-way-h">Agent 연동 방법</h2></div><div class="ops-ways">
      ${way('MCP 서버', '정의 조회 · 규칙 판정 · 검색 도구', `${opsTake(mcpCmd, '명령 복사')}${opsTake(mcpConf, '클라이언트 설정 복사')}`)}
      ${way('REST API', '판정 · 답변 · 정의 조회 API', `${opsTake('Authorization: Bearer <API 토큰>', '인증 헤더 복사')}${opsTake(curl, 'cURL 예시 복사')}<button class="k-btn sm" data-act="cngo" data-to="trypanel">API 실행</button>`)}
      ${way('온톨로지 파일', 'YAML · OWL 내보내기', known('library') ? '<a class="k-btn sm" href="#library">내보내기</a>' : '')}
      ${way('플랫폼 DB 연결', '플랫폼 관리 DB 연결 · 읽기 전용 데이터 소스', `${opsTake(gateway, '스튜디오 파일 설정 복사')}${S.st.data.connect && known('db') ? '<a class="k-btn sm" href="#db">플랫폼 연결 입력</a>' : ''}`)}
      </div></section>`;
    // the addresses: every tool /v1 serves, each with its own address to copy
    const toolRows = i.tools.map((t) => `<tr><td><span class="k-code k-ink">${esc(t.method)} ${esc(t.path)}</span><br><span class="k-m12">${esc(t.name)}</span></td><td>${esc(TOOL_WORD[t.name] || t.description)}</td>
      <td>${!i.rest ? '<span class="k-chip">꺼짐</span>' : !i.source && OPS_NEEDS_SOURCE.has(t.name) ? '<span class="k-chip">데이터 소스 필요</span>' : '<span class="k-chip ok">사용 가능</span>'}</td><td class="r">${opsCopy(`${base}${t.path}`, `${t.name} 주소 복사`)}</td></tr>`).join('');
    const endpoints = `<section class="k-card" id="cntools" aria-labelledby="ops-ep-h"><div class="k-ch"><h2 id="ops-ep-h">엔드포인트</h2><span class="k-s">REST · v1 · 도구 ${count(i.tools.length)}개</span>
        <div class="k-push"><a class="k-lnk" href="/v1/openapi.json" target="_blank" rel="noopener">문서 열기</a><a class="k-lnk" href="/v1/tools" target="_blank" rel="noopener">도구 정의 열기</a></div></div>
      <div class="k-cb">${opsPre(`${base}/v1`, '주소 복사')}<div class="k-h g6">${opsTake(`${base}/v1/openapi.json`, 'OpenAPI 주소 복사')}${i.libraries > 1 ? '<span class="k-s">library 지정 · /v1/libraries</span>' : ''}</div></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">메서드 · 경로</th><th scope="col">설명</th><th scope="col">상태</th><th scope="col"></th></tr></thead><tbody>${toolRows}</tbody></table></div></section>`;
    const mcp = `<section class="k-card" aria-labelledby="ops-mcp-h"><div class="k-ch"><h2 id="ops-mcp-h">MCP</h2></div><div class="k-cb">${opsPre(mcpCmd, 'MCP 명령 복사')}${opsMore('mcp', '클라이언트 설정', mcpConf)}</div></section>`;
    // how XGEN takes it, step by step, with what each step copies
    const chip = (text, word) => `<button class="k-chip b" data-act="copycode" data-v="${esc(text)}">${word}</button>`;
    const xgen = `<section class="k-card" aria-labelledby="ops-xg-h"><div class="k-ch"><h2 id="ops-xg-h">XGEN 연동</h2></div><ol class="ops-steps">
      <li><b>판정 노드</b><span>HTTP 요청 노드 · <span class="k-code">POST ${esc(base)}/v1/decide</span> <button class="k-chip b" data-act="cnnode">노드 설정 보기</button></span></li>
      <li><b>용어 해석 · 값 검증</b><span><span class="k-code">/v1/terms</span> · <span class="k-code">/v1/validate</span> <button class="k-chip b" data-act="cngo" data-to="trypanel">API 실행</button></span></li>
      <li><b>Agent 도구</b><span>OpenAPI 도구 등록 · Geny 도구 포트 ${chip(`${base}/v1/openapi.json`, 'OpenAPI 주소 복사')}</span></li>
      <li><b>Agent 컨텍스트</b><span><span class="k-code">/v1/context</span> · Geny 시스템 프롬프트 ${chip(`${base}/v1/context`, '주소 복사')}</span></li>
      <li><b>검증</b><span><span class="k-code">/v1/questions</span> ${chip(`${base}/v1/questions`, '주소 복사')}</span></li></ol></section>`;
    return `${head}${tiles}${targets}${ways}<div class="ops-halves"><div class="ops-half">${endpoints}${mcp}</div><div class="ops-half">${opsTry(i)}</div></div>${xgen}
      ${kNext([['actions', 'Action'], ['changes', '변경 요청 · 버전'], ['members', '멤버 · 권한']])}`;
  }

  // the policies a call is tried as: those of the definition being written, where a policy added or changed and not
  // yet deployed is marked and tried on that definition; the deployed ones while it is read, or where it cannot be
  const opsTryPols = () => { const m = S.mg.st; return m && !m.error ? m.roles : S.st.roles || []; };
  const opsTryPolicy = () => opsTryPols().find((r) => r.name === S.ops.tryPol) || null;
  // the caller attributes a policy's row rules and scope compare with (customer_id, seller_id): what a token carries
  function opsWho(r) {
    if (!r) return [];
    if (!r.rows) return r.principal || [];
    const out = [];
    const walk = (x) => { if (Array.isArray(x)) x.forEach(walk); else if (x && typeof x === 'object') { if (typeof x.principal === 'string') out.push(x.principal); Object.values(x).forEach(walk); } };
    walk(r.rows);
    if ((r.scope || {}).attribute) out.push(r.scope.attribute);
    return [...new Set(out)];
  }
  // one /v1 call made from the page: what is sent is what a platform sends, as the access policy picked would make it
  function opsTry(i) {
    const c = tryState(i), api = tryApi(c), NONE = '값 없음';
    const pols = opsTryPols();
    // a policy no longer there (deleted, or of another ontology) is not tried in secret: the pick goes back to none
    if (S.ops.tryPol && S.mg.st && !S.mg.busy && !pols.some((r) => r.name === S.ops.tryPol)) S.ops.tryPol = '';
    const pol = opsTryPolicy(), keys = opsWho(pol);
    // the Entities the policy reads, as /v1 shows them to its caller
    const objects = (i.objects || []).filter((x) => !pol || !pol.read || opsCan(pol.read, x.name));
    if (!objects.some((x) => x.name === c.object)) { c.object = (objects[0] || {}).name || ''; c.ovalues = {}; if (c.api === 'validate' || c.api === 'object') c.res = null; }
    const d = i.decisions.find((x) => x.name === c.decision), o = objects.find((x) => x.name === c.object);
    const noObject = `<p class="k-note">${(i.objects || []).length ? '조회 가능한 Entity가 없습니다.' : '등록된 Entity가 없습니다.'}</p>`;
    const control = (x, cur, on) => {
      const attr = `class="k-in" data-in="${on}" data-k="${esc(x.name)}"`;
      if (x.type === 'boolean') return `<select ${attr}>${opt('', '입력 안 함', cur)}${opt('true', '예', cur)}${opt('false', '아니요', cur)}${opt('null', NONE, cur)}</select>`;
      if (x.values && x.values.length) return `<select ${attr}>${opt('', '입력 안 함', cur)}${x.values.map((v) => opt(String(v), String(v), cur)).join('')}${opt('null', NONE, cur)}</select>`;
      const num = ['integer', 'decimal', 'number'].includes(x.type) && !x.days_since;
      return `<input type="text" ${attr} value="${esc(cur ?? '')}"${num ? ' inputmode="decimal"' : ''} placeholder="${num ? '숫자' : ''}">`;
    };
    const named = (x) => `<span>${esc(x.label)} <span class="k-m12">${esc(x.name)}</span></span>`;
    const pickObject = `<label class="k-f">Entity<select class="k-in" data-in="ctryo">${objects.map((x) => opt(x.name, `${x.label} (${x.name})`, c.object)).join('')}</select></label>`;
    const help = (x) => (x.days_since ? '일수 또는 일시 · 예: 2026-10-20T09:00:00' : x.param ? '판정 Parameter' : x.property ? '' : '연결 Entity 값');
    let fields, ready = true;
    if (c.api === 'terms') {
      fields = `<label class="k-f">문장<input class="k-in" type="text" data-in="ctryt" value="${esc(c.text)}" placeholder="질문 또는 문장"></label>`;
    } else if (c.api === 'object') {
      ready = !!o;
      fields = o ? pickObject : noObject;
    } else if (c.api === 'validate') {
      ready = !!o;
      fields = !o ? noObject
        : `<div class="k-g2">${pickObject}<label class="k-f">범위<select class="k-in" data-in="ctryc">${opt('', '입력 값만', c.complete ? '1' : '')}${opt('1', '필수 Property 누락 포함', c.complete ? '1' : '')}</select></label>
          ${o.properties.map((x) => `<label class="k-f">${named(x)}${control(x, (c.ovalues || {})[x.name], 'ctryov')}</label>`).join('')}</div>`;
    } else if (!d) {
      ready = false;
      fields = '<p class="k-note">등록된 결정표가 없습니다.</p>';
    } else {
      if (!d.target && c.mode === 'record') c.mode = 'values';  // a decision on no Entity has no record to read
      const mode = !d.target ? '' : `<div class="k-f">기준<div class="k-seg self">${[['values', '판정 값'], ['record', '레코드 키']].map(([k, w]) => `<button class="${c.mode === k ? 'on' : ''}" data-act="ctrymode" data-k="${k}" aria-pressed="${c.mode === k}">${w}</button>`).join('')}</div></div>`;
      fields = `<div class="k-g2"><label class="k-f">판정<select class="k-in" data-in="ctryd">${i.decisions.map((x) => opt(x.name, `${x.label} (${x.name})`, c.decision)).join('')}</select></label>${mode}
        ${c.mode === 'record'
    ? `<label class="k-f k-full">레코드 키<input class="k-in" type="text" data-in="ctryk" value="${esc(c.key)}" placeholder="예: ${esc(`${d.target_label} 키`)}">${i.source ? '' : '<span class="k-hint">데이터 소스 미연결</span>'}</label>`
    : `${d.inputs.map((x) => `<label class="k-f">${named(x)}${control(x, (c.values || {})[x.name], 'ctryv')}${help(x) ? `<span class="k-hint">${esc(help(x))}</span>` : ''}</label>`).join('')}
        ${d.inputs.some((x) => x.days_since) ? `<label class="k-f">기준 시각<input class="k-in" type="text" data-in="ctryat" value="${esc(c.at)}" placeholder="예: 2026-11-12T09:00:00"><span class="k-hint">경과일 계산 기준 · 미입력 시 현재 시각</span></label>` : ''}`}</div>`;
    }
    const fill = c.api === 'decide' && d && c.mode === 'values' && d.example ? `<button class="k-btn" data-act="ctryfill" title="${esc(`${d.example.question} ${d.example.text}`)}">예시 값 채우기</button>` : '';
    // while the policies are still being read, the one picked stays shown as it is the one sent
    const listed = S.ops.tryPol && !pol ? [...pols, { name: S.ops.tryPol }] : pols;
    const polWord = (r) => `${r.label && r.label !== r.name ? `${r.name} · ${r.label}` : r.name}${r.pending || r.new ? ' · 변경 대기' : ''}`;
    const who = keys.length ? `<div class="k-g2">${keys.map((k) => `<label class="k-f">호출자 속성 · ${esc(k)}<input class="k-in mono" type="text" data-in="opsTryWho" data-k="${esc(k)}" value="${esc(S.ops.who[k] || '')}"></label>`).join('')}</div>` : '';
    return `<section class="k-card" id="trypanel" aria-labelledby="ops-try-h"><div class="k-ch"><h2 id="ops-try-h">실행 패널</h2><div class="k-push"><span class="k-s">POST ${esc(api[2])}${i.library ? ` · ${esc(i.library.label)}` : ''}</span></div></div>
      <div class="k-cb ops-try">
        <div class="k-g2"><label class="k-f">엔드포인트<select class="k-in" data-in="opsTryApi">${TRY_API.map(([k, w, path]) => opt(k, `POST ${path} · ${w}`, c.api)).join('')}</select></label>
          <label class="k-f">접근 정책<select class="k-in" data-in="opsTryPol">${opt('', '정책 없음', S.ops.tryPol)}${listed.map((r) => opt(r.name, polWord(r), S.ops.tryPol)).join('')}</select></label></div>
        ${who}${fields}
        ${ready ? `${opsTryCode(c, i)}<div class="k-h"><button class="k-btn pri" data-act="ctryrun"${c.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}${c.busy ? '실행 중' : '실행'}</button>${fill}${c.api === 'object' ? '' : '<button class="k-btn" data-act="ctryclear">값 초기화</button>'}</div>` : ''}
        <div class="ops-res" id="opstryres">${opsTryResult(c)}</div></div></section>`;
  }

  // the request as it goes out: its body, the same as a cURL line, the same as the settings of an XGEN HTTP request node
  function opsTryCode(c, i) {
    const base = location.origin, body = tryBody(c, i), path = tryApi(c)[2];
    const lib = i.library && i.libraries > 1 ? { library: i.library.id } : {};
    const flat = JSON.stringify({ ...lib, ...body });
    const curl = `curl -X POST ${base}${path} \\\n  -H "Authorization: Bearer $ONTLAS_API_TOKEN" \\\n  -H "Content-Type: application/json" \\\n  -d '${flat}'`;
    const node = [['method', 'POST'], ['url', `${base}${path}`], ['auth_type', 'bearer'], ['auth_token', 'API 토큰'], ['body_type', 'json'], ['body', flat], ['passthrough_input', 'false'], ['failure_mode', 'emit']];
    const text = { body: JSON.stringify({ ...lib, ...body }, null, 2), curl, node: node.map(([k, v]) => `${k}: ${v}`).join('\n') }[c.view];
    const tab = (k, w) => `<button class="${c.view === k ? 'on' : ''}" data-act="ctryview" data-k="${k}" aria-pressed="${c.view === k}">${w}</button>`;
    // how the node takes what the step before it sends: `input` is that step's whole value
    const template = { decide: `{"decision": "${c.decision}", "values": {{ input | tojson }}}`, validate: `{"object": "${c.object}", "values": {{ input | tojson }}}`, terms: '{"text": {{ input | tojson }}}' }[c.api];
    return `<div class="k-v" id="opstrycode"><div class="k-h sb"><div class="k-seg">${tab('body', '요청 본문')}${tab('curl', 'cURL')}${tab('node', 'XGEN HTTP 요청 노드')}</div>${opsTake(text, '복사')}</div>
      ${c.view === 'node' ? `<div class="k-x"><table class="k-t s end ops-node"><tbody>${node.map(([k, v]) => `<tr><td class="k-code">${esc(k)}</td><td class="k-code" style="white-space:normal">${esc(v)}</td></tr>`).join('')}</tbody></table></div>
        ${template ? `<p class="k-p s">body 템플릿 예: <span class="k-code" style="white-space:normal">${esc(template)}</span></p>` : ''}` : `<pre class="k-pre">${esc(text)}</pre>`}</div>`;
  }

  function opsTryResult(c) {
    const r = c.res, api = tryApi(c);
    if (c.busy) return '<p class="k-p s">실행 중입니다.</p>';
    if (!r) return '';
    const [tone, word] = r.status === 200 ? ['ok', api[4]] : TRY_STATUS[r.status] || ['bad', '오류'];
    const b = r.body || {};
    const as = r.policy ? `<span class="k-s">접근 정책 <span class="k-code">${esc(r.policy)}</span>${r.draft ? ' · 변경 대기 정의' : ''}</span>` : '';
    const head = `<div class="k-h"><span class="k-chip ${tone}">${r.status} · ${word}</span>${c.api === 'decide' && b.mode ? `<span class="k-s">${b.mode === 'values' ? '판정 값 기준' : '레코드 기준'}</span>` : ''}${as}</div>`;
    const raw = `<pre class="k-pre">${esc(JSON.stringify(b, null, 2))}</pre>`;
    const table = (heads, rows) => `<div class="k-x"><table class="k-t s end"><thead><tr>${heads.map((h) => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
    if (r.status === 422) {
      const missing = (b.missing || []).length ? `<p class="k-note">판정에 필요한 값이 없어 판정하지 못했습니다. 누락 값을 입력해 주세요.</p>
        ${table(['누락 값', '이름', '형식'], b.missing.map((m) => `<tr><td class="b">${esc(m.label)}</td><td class="k-code">${esc(m.input)}${m.property && m.property !== m.input ? ` <span class="k-mut">또는 ${esc(m.property)}</span>` : ''}</td><td>${esc(m.type)}${(m.values || []).length ? `<br><span class="k-s">허용 코드 ${esc(m.values.join(', '))}</span>` : ''}</td></tr>`).join(''))}` : '';
      const invalid = (b.invalid || []).length ? `<p class="k-note">허용 코드가 아닌 값이 있어 판정하지 못했습니다. 허용 코드로 입력해 주세요.</p>
        ${table(['항목', '입력 값', '허용 코드'], b.invalid.map((m) => `<tr><td class="b">${esc(m.label)}<br><span class="k-m12">${esc(m.input)}</span></td><td>${show(m.value)}</td><td>${esc((m.values || []).join(', '))}</td></tr>`).join(''))}` : '';
      return `${head}${invalid}${missing}${raw}`;
    }
    if (r.status !== 200) return `${head}${b.error ? `<p class="k-note warn">${esc(opsTrySaid(r))}</p>` : ''}${raw}`;
    const ver = b.definition ? `<p class="k-m12">정의 버전 ${esc(b.definition.version)} · 모듈 ${b.definition.modules.length}개</p>` : '';
    if (c.api === 'validate') {
      const bound = (v) => [v.min !== null && v.min !== undefined ? `${v.min} 이상` : '', v.max !== null && v.max !== undefined ? `${v.max} 이하` : ''].filter(Boolean).join(' · ');
      const why = (v) => (v.kind === 'rule' ? `<br><span class="k-s">${esc(v.statement)}</span><br><span class="k-s"><span class="k-code">${esc(v.rule)}</span> · ${esc(v.layer_label)} · ${esc(v.module)} ${esc(v.version)}${v.source ? ` · ${esc(v.source)}` : ''}</span>`
        : v.kind === 'code' ? `<br><span class="k-s">허용 코드 ${esc((v.allowed || []).map((a) => a.code).join(', '))}</span>` : v.kind === 'type' ? `<br><span class="k-s">${esc(TYPE_WORD[v.expected] || v.expected || '')} 형식</span>` : '');
      const rows = (b.violations || []).map((v) => `<tr><td class="b">${esc(v.label)}<br><span class="k-m12">${esc(v.property)}</span></td><td>${v.value === null || v.value === undefined ? '<span class="k-mut">-</span>' : show(v.value)}</td><td>${esc(TRY_KIND[v.kind] || v.kind)}${v.kind === 'rule' && bound(v) ? ` · ${esc(bound(v))}` : ''}${why(v)}</td></tr>`).join('');
      return `${head}<p class="ops-verdict">${b.valid ? '기준 충족' : `위반 ${(b.violations || []).length}건`}</p>${rows ? table(['Property', '값', '사유'], rows) : `<p class="k-p s">검사한 Property ${(b.checked || []).length}개 · 위반 없음</p>`}
        ${(b.rules || []).length ? `<p class="k-p s">적용 규칙 카드 <span class="k-code" style="white-space:normal">${esc(b.rules.join(', '))}</span></p>` : ''}${ver}${raw}`;
    }
    if (c.api === 'terms') {
      const m = b.matched || [], d = b.defined || [];
      const exp = Object.fromEntries((b.expansions || []).map((x) => [x.term, x.labels]));
      if (!m.length && !d.length) return `${head}<p class="k-note">일치하는 용어가 없습니다.</p>${raw}`;
      return `${head}<p class="k-p s">대표어 변환 결과</p><p class="ops-verdict" style="font-size:16px">${esc(b.text)}</p>
        ${m.length ? table(['입력 표기', '대표어', '뜻'], m.map((x) => `<tr><td>${esc(x.label)}<br><span class="k-s">${esc(x.as_label)}</span></td><td class="b">${esc(x.term)}</td><td>${esc(x.meaning || '-')}${x.definition ? `<br><span class="k-s">${esc(x.definition)}</span>` : ''}${(exp[x.term] || []).length > 1 ? `<br><span class="k-s">검색 표기 ${esc(exp[x.term].join(', '))}</span>` : ''}</td></tr>`).join('')) : ''}
        ${(b.confusables || []).length ? `<p class="k-p s">혼동 주의 · ${b.confusables.map((x) => `<b>${esc(x.term)}</b> ≠ ${esc(x.confusable)}${x.note ? ` (${esc(x.note)})` : ''}`).join(' · ')}</p>` : ''}
        ${d.length ? table(['정의 일치 이름', '뜻'], d.map((x) => `<tr><td class="b">${esc(x.label)}</td><td>${x.concepts.map((k) => `<span class="k-mut">${esc(k.concept_kind)}</span> ${esc(k.meaning)}`).join('<br>')}</td></tr>`).join('')) : ''}${ver}${raw}`;
    }
    if (c.api === 'object') {
      const o = b.object || {}, at = [b.area && b.area.label, b.parent && b.parent.label, o.label].filter(Boolean), props = Object.entries(o.properties || {});
      const label = (n) => (((S.conn || {}).objects || []).find((x) => x.name === n) || {}).label || n;
      return `${head}<p class="ops-verdict">${esc(at.join(' › '))}</p>${(b.children || []).length ? `<p class="k-p s">하위 Entity ${esc(b.children.map((x) => x.label).join(', '))}</p>` : ''}
        ${table([`Property ${props.length}개`, '이름', '형식'], props.map(([k, p]) => `<tr><td class="k-code">${esc(k)}</td><td>${esc(p.label || '')}</td><td class="mut">${esc(TYPE_WORD[p.type] || p.type)}${(p.values || []).length ? ` · ${esc(p.values.join(', '))}` : ''}</td></tr>`).join(''))}
        ${(b.links || []).length ? table([`Relation ${b.links.length}개`, '연결'], b.links.map((x) => `<tr><td class="k-code">${esc(x.name)}</td><td>${esc(label(x.from))} → ${esc(label(x.to))}</td></tr>`).join('')) : ''}
        ${(b.decisions || []).length ? `<p class="k-p s">판정 <span class="k-code" style="white-space:normal">${esc(b.decisions.join(', '))}</span></p>` : ''}${ver}${raw}`;
    }
    const outs = b.outputs && typeof b.outputs === 'object' ? b.outputs : { result: b.outputs };
    const layers = ((b.path || {}).layers || []).map((x) => `<span class="k-chip${x.state === 'fired' ? ' ok' : ''}" title="${esc(x.said)}">${esc(x.label)} ${esc(x.fired.join(', ') || x.said)}</span>`).join('<span class="k-mut">›</span>');
    const src = (b.path || {}).source;
    const keep = b.mode === 'values' && canEdit() ? `<div class="k-v g4"><button class="k-btn" style="align-self:flex-start" data-act="ctrysave"${c.saved ? ' disabled' : ''}>${c.saved ? '검증 질문 저장됨' : '검증 질문으로 저장'}</button></div>` : '';
    return `${head}<p class="ops-verdict">${esc(b.verdict || '')}</p>
      ${Object.entries(outs).map(([k, v]) => `<div class="ops-pair"><span class="k-code">${esc(k)}</span><span>${show(v)}</span></div>`).join('')}
      <div class="k-h g6"><span class="k-s">판정 경로</span>${layers || '<span class="k-mut">-</span>'}</div>
      ${src ? `<p class="k-p s">판정 규칙 <span class="k-code">${esc(src.rule)}</span> · ${esc(src.layer_label)} · ${esc(src.module_label)} ${esc(src.version)}${src.cite ? ` · ${esc(src.cite)}` : ''}</p>` : ''}
      ${(b.evidence || []).length ? table(['근거 값', '값', '출처'], b.evidence.map((e) => `<tr><td class="k-code">${esc(e.input)}</td><td>${show(e.value)}</td><td class="mut">${e.source === 'given' ? '요청 값' : esc(e.source || '')}</td></tr>`).join('')) : ''}
      ${(b.not_needed || []).length ? `<p class="k-p s">미사용 값 · ${esc(b.not_needed.map((m) => m.label).join(', '))}</p>` : ''}${ver}${keep}${raw}`;
  }

  // what /v1 refused, in the page's words; the body under it stays as the platform gets it
  function opsTrySaid(r) {
    const e = String((r.body || {}).error || ''), m = e.match(/needs principal attributes \[(.*)\]/);
    if (/[가-힣]/.test(e)) return e;  // the page's own refusal, already in its words
    if ((r.body || {}).no_policy) return '접근 정책이 없는 호출이라 실행하지 못했습니다. 접근 정책을 선택해 주세요.';
    if (m) return `호출자 속성 ${m[1].replace(/'/g, '')} 값이 없어 실행하지 못했습니다. 호출자 속성을 입력해 주세요.`;
    if (/outside (this role's rows|the scope of role)/.test(e)) return '접근 정책의 행 범위 밖 레코드라 판정하지 못했습니다. 레코드 키와 호출자 속성을 확인해 주세요.';
    if (/may not read/.test(e) || (r.policy && /unknown object/.test(e))) return '접근 정책의 조회 범위 밖 Entity라 실행하지 못했습니다. 조회 범위 안의 Entity를 선택해 주세요.';
    if (/may not run/.test(e)) return '접근 정책의 실행 허용 범위 밖이라 실행하지 못했습니다. 접근 정책의 실행 허용 항목을 확인해 주세요.';
    if (r.status === 409) return '연결된 데이터 소스가 없어 레코드를 조회하지 못했습니다. 데이터 소스를 연결해 주세요.';
    if (/not found/.test(e)) return '레코드를 찾을 수 없어 판정하지 못했습니다. 레코드 키를 확인해 주세요.';
    return r.status === 403 ? '접근 정책의 허용 범위 밖이라 실행하지 못했습니다. 접근 정책을 확인해 주세요.' : '요청 값 오류로 실행하지 못했습니다. 요청 본문을 확인해 주세요.';
  }

  const opsTryRepaint = () => { const box = $('#opstrycode'); if (box && S.conn && !S.conn.error) box.outerHTML = opsTryCode(S.ctry, S.conn); };

  screen('connect', {
    area: 'work', word: '연동 · API',
    view: opsApi,
    after: () => {
      opsFresh();
      opsRead('tg', 'ops/targets');
      opsRead('conn', 'integrations', () => S.conn, (x) => { S.conn = x; });
      if (!S.mg.st && !S.mg.busy) loadManage().then(() => { if (S.tab === 'connect') render(); });  // the policies with their pending ones
    },
  });

  Object.assign(INPUT, {
    opsTryApi: (t) => { Object.assign(S.ctry, { api: t.value, res: null, saved: false }); render(); },
    opsTryPol: (t) => { S.ops.tryPol = t.value; if (S.ctry) { S.ctry.res = null; S.ctry.saved = false; } render(); },
    opsTryWho: (t) => { S.ops.who = { ...S.ops.who, [t.dataset.k]: t.value }; },
    // the values of a request being written: the request shown under them follows, the fields keep their place
    ctryv: (t) => { const c = S.ctry; c.values = { ...(c.values || {}), [t.dataset.k]: t.value }; opsTryRepaint(); },
    ctryk: (t) => { S.ctry.key = t.value; opsTryRepaint(); },
    ctryt: (t) => { S.ctry.text = t.value; opsTryRepaint(); },
    ctryov: (t) => { const c = S.ctry; c.ovalues = { ...(c.ovalues || {}), [t.dataset.k]: t.value }; opsTryRepaint(); },
    ctryc: (t) => { S.ctry.complete = t.value === '1'; opsTryRepaint(); },
    ctryat: (t) => { S.ctry.at = t.value; opsTryRepaint(); },
  });
  Object.assign(ACT, {
    cngo: (t) => { const el = document.getElementById(t.dataset.to); if (el) { el.scrollIntoView({ block: 'start', behavior: 'smooth' }); el.classList.add('ops-here'); setTimeout(() => el.classList.remove('ops-here'), 1400); } },
    cnnode: () => {  // the decision call as the settings of an XGEN HTTP request node
      Object.assign(S.ctry, S.ctry.api === 'decide' ? { view: 'node' } : { api: 'decide', view: 'node', res: null, saved: false });
      render();
      const el = $('#opstrycode');
      if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    },
    ctryrun: async () => {  // as the policy picked would call it: what that policy may not run answers 403 here as it does there
      const c = S.ctry;
      if (c.api === 'terms' && !c.text.trim()) { toast('문장을 입력해 주세요.', true); return; }
      c.busy = true; c.saved = false; render();
      const principal = Object.fromEntries(opsWho(opsTryPolicy()).map((k) => [k, String(S.ops.who[k] || '').trim()]).filter(([, v]) => v));
      try { c.res = await api('ops/try', { path: tryApi(c)[2], policy: S.ops.tryPol, principal, body: tryBody(c, S.conn) }); } catch (e) { c.res = { status: 400, body: { error: e.message } }; }
      c.busy = false; render();
    },
  });

  // ---- OPS-05 접근 정책 ----------------------------------------------------------------------------------------------
  // A policy is a role of the definition: what a caller of /v1 may read, which rows, what is hidden, what it may ask
  // to be done. The server says which caller runs as which policy.

  const OPS_MASK = { partial: '부분 마스킹', full: '전체 마스킹' };
  const opsEntities = (m) => m.objects.filter((o) => !o.concept);
  // the Objects with the Entities filed under each; Entities under no Object come last
  function opsObjects(m) {
    const rows = m.areas.map((a) => ({ name: a.name, label: a.label || a.name, ents: opsEntities(m).filter((o) => o.area === a.name) }));
    const loose = opsEntities(m).filter((o) => !o.area || !m.areas.some((a) => a.name === o.area));
    if (loose.length) rows.push({ name: '', label: AREA_NONE, ents: loose });
    return rows.filter((r) => r.ents.length);
  }
  const opsCan = (list, name) => list.includes('*') || list.includes(name);
  const opsProp = (m, key) => { const [o, p] = String(key).split('.'); const x = m.properties.find((q) => q.object === o && q.name === p); return `${mgLabel(o)}.${x ? x.label || p : p}`; };
  function opsRowSay(m, x) {  // a row rule in words: 주문의 고객 = 호출자의 customer_id
    if (x.raw) return `${mgLabel(x.type)} · 모듈 정의 조건`;
    const via = (x.via || []).filter(Boolean), end = via.reduce((t, step) => hopEnd(t, step), x.type);
    const p = m.properties.find((q) => q.object === end && q.name === x.property);
    return `${mgLabel(x.type)}${via.length ? ` › ${mgLabel(end)}` : ''}의 ${p ? p.label || x.property : x.property} = ${x.principal ? `호출자의 ${x.principal}` : show(x.value)}`;
  }
  const opsPolicy = () => { const m = S.mg.st; return m && !m.error ? m.roles.find((r) => r.name === S.ops.sel) || m.roles[0] || null : null; };
  const opsCallers = (name) => opsTargets().filter((t) => t.policy === name);

  function opsPolicies() {
    const m = S.mg.st, tg = opsGood(S.ops.tg);
    const head = kHead('접근 정책', '연동 대상별 정의 · 데이터 · Action 범위를 관리합니다.',
      `<a class="k-btn" href="#connect">${ki('plug', 16, 1.75)}연동 대상</a>${canEdit() ? `<a class="k-btn pri" href="${itemHref('policy', 'form')}">${ki('plus', 16, 1.75)}정책</a>` : ''}`);
    if (!m) return head + opsWait();
    if (m.error) return head + opsFailed(m.error);
    const src = !noSource(), list = tg ? tg.targets : [], roles = m.roles, sel = opsPolicy();
    const loose = list.filter((t) => !t.policy || !roles.some((r) => r.name === t.policy));
    const linked = (r) => list.filter((t) => t.policy === r.name);
    const bar = sel ? itemBar('policy', sel.name, sel.name, `${sel.label}${linked(sel).length ? ` · 연결 ${linked(sel).map((t) => t.name).join(', ')}` : ''}`) : '';
    const tile = (label, big, sub) => `<div class="k-stat ops-tile" style="flex-basis:170px"><p>${label}</p><p class="k-big">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const dash = (label, big, sub) => `<div class="ops-dash ops-tile" style="flex-basis:170px"><p class="k-s">${label}</p><p class="k-big mut">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const tiles = `<section class="k-wrap" aria-label="접근 정책 현황">
      ${tile('연동 대상', tg && tg.listed ? count(list.length) : tg && !tg.rest ? '0' : '-', esc(!tg ? '' : !tg.rest ? 'REST API 꺼짐' : list.map((t) => t.name).join(' · ') || 'REST API 켜짐'))}
      ${tile('정책', count(roles.length), `정책 미지정 연동 대상 ${count(loose.length)}`)}
      ${tile('적용 중', '정의 범위', 'Object · 규칙 조회 · 판정')}
      ${src ? tile('적용 중', '데이터 범위', '행 범위 · 마스킹') : dash('미적용', '데이터 범위', '행 범위 · 마스킹 · 데이터 소스 미연결')}
      ${src && m.actions.length ? tile('적용 중', 'Action', '요청 · 승인 기준') : dash('미적용', 'Action', m.actions.length ? '데이터 소스 미연결' : '등록된 Action 없음')}</section>`;
    if (!roles.length) return `${head}${tiles}${kEmpty('등록된 접근 정책이 없습니다', '', canEdit() ? `<a class="k-btn pri" href="${itemHref('policy', 'form')}">${ki('plus', 16, 1.75)}정책</a>` : '')}`;
    // one row for each caller a policy is given to (a policy no caller runs as has one row of its own)
    const objs = opsObjects(m);
    const scope = (r) => (r.read.includes('*') ? '전체' : `Object ${count(objs.filter((o) => o.ents.some((e) => r.read.includes(e.name))).length)} · Entity ${count(r.read.length)}`);
    const acts = (r) => [r.request.length ? (r.request.includes('*') ? '요청 전체' : `요청 ${count(r.request.length)}`) : '', r.execute.length ? (r.execute.includes('*') ? '실행 전체' : `실행 ${count(r.execute.length)}`) : ''].filter(Boolean).join(' · ') || '<span class="k-mut">-</span>';
    const polCell = (r) => `<span class="k-code">${esc(r.name)}</span>${r.pending || r.new ? ' <span class="k-chip warn">변경 대기</span>' : ''}<br><span class="k-s">${esc(r.label)}</span>`;
    const row = (r, t) => `<tr class="${sel && r.name === sel.name ? 'on' : ''}" data-act="opsPolPick" data-name="${esc(r.name)}" tabindex="0"${sel && r.name === sel.name ? ' aria-current="true"' : ''}><td class="b">${t ? `${esc(t.name)}<br><span class="k-s" style="font-weight:400">REST${t.write ? ' · Action 요청' : ''}</span>` : '<span class="k-mut" style="font-weight:400">연동 대상 없음</span>'}</td>
      <td>${polCell(r)}</td><td>${scope(r)}</td><td>${r.rows.length ? esc(r.rows.map((x) => mgLabel(x.type)).join(' · ')) : '전체'}</td><td class="r">${count(Object.keys(r.mask).length)}</td><td>${acts(r)}</td></tr>`;
    const rows = roles.flatMap((r) => (linked(r).length ? linked(r).map((t) => row(r, t)) : [row(r, null)])).join('')
      + loose.map((t) => { const shut = !t.policy && !(tg && tg.unscoped), none = '<span class="k-mut">-</span>';  // refused: it reads nothing
        return `<tr><td class="b">${esc(t.name)}<br><span class="k-s" style="font-weight:400">REST${t.write ? ' · Action 요청' : ''}</span></td><td>${t.policy ? `<span class="k-code">${esc(t.policy)}</span> <span class="k-chip warn">이 온톨로지에 없음</span>` : shut ? '<span class="k-chip bad">정책 없음 · 거부</span>' : '<span class="k-chip warn">정책 없음 · 전체 조회</span>'}</td><td>${shut ? none : '전체'}</td><td>${shut ? none : '전체'}</td><td class="r">0</td><td>${t.write && !shut ? '요청 전체' : none}</td></tr>`; }).join('');
    const table = `<section class="k-card" aria-labelledby="ops-tgp-h" style="flex:3 1 600px"><div class="k-ch"><h2 id="ops-tgp-h">연동 대상별 정책</h2><span class="k-chip">${count(roles.length)}</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">연동 대상</th><th scope="col">정책</th><th scope="col">정의 범위</th><th scope="col">데이터 행 범위</th><th scope="col" class="r">마스킹</th><th scope="col">Action</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    return `${head}${bar}${tiles}<div class="k-cols">${table}${opsPolicyAside(m, sel, src)}</div>${opsPolicyScope(m, sel, src)}
      ${kNext([['changes', '변경 요청 · 버전'], ['query', '질의'], ['connect', '연동 · API'], ['members', '멤버 · 권한']])}`;
  }

  // the policy picked, in three parts: what it reads of the definition, of the data, and what it may ask to be done
  function opsPolicyAside(m, r, src) {
    if (!r) return '';
    const callers = opsCallers(r.name), objs = opsObjects(m);
    const part = (n, title, mark, body) => `<div class="ops-part"><div class="k-pha"><span class="k-num">${n}</span><h3>${title}</h3><span class="k-push">${mark}</span></div>${body}</div>`;
    const pair = (k, v) => `<div class="ops-pair"><span>${k}</span><span>${v}</span></div>`;
    const readable = r.read.includes('*') ? objs : objs.filter((o) => o.ents.some((e) => r.read.includes(e.name)));
    const named = (list, of) => (list.includes('*') ? '전체' : list.map((n) => { const x = of.find((y) => y.name === n); return x ? x.label || n : n; }).join(' · '));
    const runs = [...m.decisions, ...m.functions, ...m.queries];
    const docs = r.documents === null || r.documents === undefined ? '전체' : r.documents.length ? `${count(r.documents.length)}개` : '없음';
    const def = `<div class="k-h g6">${readable.map((o) => { const some = !r.read.includes('*') && !o.ents.every((e) => r.read.includes(e.name)); return `<span class="k-chip"${some ? ` title="${esc(o.ents.filter((e) => r.read.includes(e.name)).map((e) => e.label).join(', '))}"` : ''}>${esc(o.label)}${some ? ` ${o.ents.filter((e) => r.read.includes(e.name)).length}/${o.ents.length}` : ''}</span>`; }).join('') || '<span class="k-s">조회 가능 Object 없음</span>'}</div>
      <p class="k-s" style="margin:0">Object · Entity · 규칙 조회 · 판정 · 검색</p>${r.run.length ? pair('실행', esc(named(r.run, runs))) : ''}${m.documents.length ? pair('열람 문서', docs) : ''}`;
    const scoped = (r.scope || {}).attribute ? pair('조직 범위', `호출자의 ${esc(r.scope.attribute)} · Entity ${count(Object.keys(r.scope.types || {}).length)}`) : '';
    const data = `${pair('행 범위', r.rows.length ? r.rows.map((x) => esc(opsRowSay(m, x))).join('<br>') : '전체')}${scoped}${Object.entries(r.mask).map(([k, v]) => pair(esc(opsProp(m, k)), OPS_MASK[v] || esc(v))).join('')}${r.unmask.length ? pair('마스킹 해제', r.unmask.includes('*') ? '전체' : esc(r.unmask.map((k) => (k.endsWith('.*') ? `${mgLabel(k.slice(0, -2))} 전체` : opsProp(m, k))).join(' · '))) : ''}`;
    const act = (n, word) => { const a = m.actions.find((x) => x.name === n); return pair(esc(a ? a.label : n), a && word === '요청' && a.approval ? '요청 · 승인 필요' : word); };
    const actions = [...(r.request.includes('*') ? [pair('전체 Action', '요청')] : r.request.map((n) => act(n, '요청'))), ...(r.execute.includes('*') ? [pair('전체 Action', '실행')] : r.execute.map((n) => act(n, '실행')))].join('') || '<p class="k-s" style="margin:0">허용 Action 없음</p>';
    const waiting = r.pending || r.new;
    return `<aside class="k-card ops-pol" aria-labelledby="ops-pd-h"><div class="ops-polh"><p class="k-s" style="margin:0">접근 정책${callers.length ? ` · 연결 ${esc(callers.map((t) => t.name).join(', '))}` : ''}</p><h2 id="ops-pd-h">${esc(r.name)}</h2><p class="k-i3 k-14" style="margin:0">${esc(r.label)}${r.module_label ? ` · ${esc(r.module_label)}` : ''}</p></div>
      ${part(1, '정의 범위', '<span class="k-chip ok">적용 중</span>', def)}
      ${part(2, '데이터 범위', src ? '<span class="k-chip ok">적용 중</span>' : '<span class="k-chip">데이터 소스 미연결</span>', data)}
      ${part(3, 'Action', src && m.actions.length ? '<span class="k-chip ok">적용 중</span>' : `<span class="k-chip">${m.actions.length ? '데이터 소스 미연결' : 'Action 없음'}</span>`, actions)}
      <div class="ops-polf"><a class="k-btn" href="#connect" data-act="opsPolTry" data-name="${esc(r.name)}">${ki('play', 16, 1.75)}정책 테스트</a>${waiting && known('changes') ? '<a class="k-btn pri" href="#changes">변경 요청 등록</a>' : ''}</div></aside>`;
  }

  // the same policy Object by Object; ticking what it reads goes into the change request being written
  function opsPolicyScope(m, r, src) {
    if (!r) return '';
    const edit = canEdit();
    const rows = opsObjects(m).map((o) => {
      const names = o.ents.map((e) => e.name), on = names.filter((n) => opsCan(r.read, n));
      const rules = r.rows.filter((x) => names.includes(x.type)).map((x) => esc(opsRowSay(m, x))).join('<br>');
      const masks = Object.keys(r.mask).filter((k) => names.includes(k.split('.')[0])).map((k) => opsProp(m, k).split('.').slice(1).join('.')).join(' · ');
      const acts = m.actions.filter((a) => names.includes(a.target)).map((a) => (opsCan(r.execute, a.name) ? `${a.label} · 실행` : opsCan(r.request, a.name) ? `${a.label} · 요청` : '')).filter(Boolean).join('<br>');
      return `<tr><td class="b">${esc(o.label)}<br><span class="k-s" style="font-weight:400">${esc(o.ents.map((e) => e.label).join(' · '))}</span></td>
        <td class="c"><input type="checkbox" data-in="opsPolRead" data-ents="${esc(names.join(' '))}"${on.length === names.length ? ' checked' : ''}${on.length && on.length < names.length ? ' data-some="1"' : ''}${edit ? '' : ' disabled'} aria-label="${esc(o.label)} 조회"></td>
        <td>${on.length ? rules || '전체' : '<span class="k-mut">-</span>'}</td><td>${esc(masks) || '<span class="k-mut">-</span>'}</td><td>${acts || '<span class="k-mut">-</span>'}</td></tr>`;
    }).join('');
    return `<section class="k-card" aria-labelledby="ops-ob-h"><div class="k-ch"><h2 id="ops-ob-h">Object별 범위</h2><span class="k-code">${esc(r.name)}</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">Object</th><th scope="col" class="c">조회</th><th scope="col">행 범위</th><th scope="col">마스킹 Property</th><th scope="col">Action</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  screen('roles', {
    area: 'work', word: '접근 정책',
    view: opsPolicies,
    after: () => {
      opsFresh();
      opsRead('tg', 'ops/targets');
      if (!S.mg.st && !S.mg.busy) loadManage();
      const want = itemParam('policy');
      if (want && S.mg.st && !S.mg.st.error && S.ops.sel !== want && S.mg.st.roles.some((r) => r.name === want) && S.ops.landed !== location.hash) { S.ops.landed = location.hash; S.ops.sel = want; render(); return; }
      document.querySelectorAll('#main input[data-some]').forEach((x) => { x.indeterminate = true; });  // some of an Object's Entities, not all
    },
  });

  // a policy row is picked with Enter or Space as with a click, and keeps the focus through the repaint
  document.addEventListener('keydown', (ev) => {
    const t = ev.target;
    if (!t || !t.dataset || t.dataset.act !== 'opsPolPick' || (ev.key !== 'Enter' && ev.key !== ' ')) return;
    ev.preventDefault();
    ACT.opsPolPick(t);
    const again = [...document.querySelectorAll('#main tr[data-act=opsPolPick]')].find((x) => x.dataset.name === t.dataset.name);
    if (again) again.focus();
  });
  Object.assign(ACT, {
    opsPolPick: (t) => { S.ops.sel = t.dataset.name; render(); },
    opsPolTry: (t) => { S.ops.tryPol = t.dataset.name; if (S.ctry) S.ctry.res = null; location.hash = '#connect'; setTimeout(() => { const el = $('#trypanel'); if (el) el.scrollIntoView({ block: 'start' }); }, 400); },
    opsPolRowAdd: (t) => { const d = S.it.d, k = t.dataset.list; d[k].push(k === 'mask' ? { prop: '', style: 'partial' } : k === 'rows' ? { type: '', via: '', property: '', mode: 'principal', value: '' } : { type: '', via: '', property: '' }); render(); },
    opsPolRowDel: (t) => { S.it.d[t.dataset.list].splice(Number(t.dataset.i), 1); render(); },
  });
  Object.assign(INPUT, {
    opsPolRead: async (t) => {  // an Object ticked or cleared: all of its Entities join or leave what the policy reads
      const m = S.mg.st, r = opsPolicy(), ents = t.dataset.ents.split(' ').filter(Boolean);
      if (!r) return;
      const all = r.read.includes('*') ? opsEntities(m).map((o) => o.name) : [...r.read];
      const read = t.checked ? [...new Set([...all, ...ents])] : all.filter((n) => !ents.includes(n));
      t.disabled = true;
      try { S.mg.st = await api('manage/edit', { op: 'update_role', args: { name: r.name, read } }); toast('조회 범위를 작성 중인 변경 요청에 저장했습니다.'); } catch (e) { fail(e); }
      render();
    },
    opsPolTick: (t) => {
      const d = S.it.d, k = t.dataset.list;
      if (!d) return;
      if (t.dataset.v === '*') d[k] = t.checked ? ['*'] : [];
      else { const vs = (t.dataset.ents || t.dataset.v).split(' ').filter(Boolean); d[k] = t.checked ? [...new Set([...d[k].filter((x) => x !== '*'), ...vs])] : d[k].filter((x) => !vs.includes(x)); }
      render();
    },
    opsPolRow: (t) => {
      const row = S.it.d[t.dataset.list][Number(t.dataset.i)], f = t.dataset.f;
      row[f] = t.value;
      if (f === 'type') { row.via = ''; row.property = ''; }
      if (f === 'via') row.property = '';
      if (t.tagName === 'SELECT') { render(); return; }
      const box = $('#itchecks');
      if (box) box.innerHTML = itemChecks(ITEM.policy, S.it);
    },
  });

  // ---- the policy's own screens ---------------------------------------------------------------------------------------

  const OPS_ROLE_FIELD = { read: '조회 Entity', run: '실행 질의 · 결정 · 함수', request: '요청 Action', execute: '실행 Action', mask: '마스킹', 가림: '마스킹', unmask: '마스킹 해제', row_filters: '행 범위', scope: '조직 범위', documents: '열람 문서', label: '이름', 라벨: '이름' };
  const OPS_ROLE_PART = { attribute: '호출자 속성', types: 'Entity' };
  const opsRoleHead = (label) => { const s = String(label), sep = s.includes(' · ') ? ' · ' : '.', head = s.split(sep)[0]; return [head, s.slice(head.length + sep.length)]; };
  // a role's field as the policy screens name it: read -> 조회 Entity, mask.Customer.phone -> 마스킹 · 고객.전화번호
  const opsRoleWord = (label) => {
    const [head, rest] = opsRoleHead(label), m = S.mg.st, [first, ...more] = rest.split('.');
    if (!OPS_ROLE_FIELD[head]) return String(label);
    const part = !rest ? '' : ['mask', '가림', 'unmask'].includes(head) && m && !m.error ? opsProp(m, rest)
      : head === 'row_filters' ? mgLabel(first) : head === 'scope' ? [OPS_ROLE_PART[first] || first, ...more.map(mgLabel)].join(' · ') : rest;
    return `${OPS_ROLE_FIELD[head]}${part ? ` · ${part}` : ''}`;
  };
  // a role's value in the same words: names for the lists, the masking style, a row rule, where the scope is held
  function opsRoleSaid(label, v) {
    const [head, rest] = opsRoleHead(label), m = S.mg.st;
    if (v === null || v === undefined || v === '' || !m || m.error) return v;
    const of = (list) => (n) => (list.find((x) => x.name === n) || {}).label || n;
    const lists = { read: mgLabel, run: of([...m.decisions, ...m.functions, ...m.queries]), request: of(m.actions), execute: of(m.actions), documents: String, unmask: String };
    const names = Array.isArray(v) ? v : typeof v === 'string' && lists[head] ? v.split(', ') : null;  // a list comes said as "a, b"
    if (names && lists[head]) return names.map((n) => (n === '*' ? '전체' : lists[head](n))).join(' · ') || '없음';
    if (['mask', '가림'].includes(head)) return OPS_MASK[v] || v;
    if (head === 'row_filters' && v && typeof v === 'object' && !Array.isArray(v)) return opsRowSay(m, opsRowRule(rest.split('.')[0], v));
    if (head === 'scope' && typeof v === 'object' && !Array.isArray(v)) return Object.entries(v).map(([t, w]) => `${mgLabel(t)} · ${typeof w === 'string' ? w : [...(w.via || []), w.property].join(' › ')}`).join(', ');
    return v;
  }
  // a row filter as the policy form reads it, the way the server reads it: one compare on the Entity's own Property, or
  // one through Relations to the Entity it ends at; any other stays as the module wrote it
  function opsRowRule(type, spec) {
    const side = (who) => (who && typeof who === 'object' ? (Object.keys(who).join() === 'principal' ? { principal: who.principal } : null) : { value: who });
    const keys = Object.keys(spec).join();
    if (keys === 'eq' && String(spec.eq[0]).startsWith('$self.') && side(spec.eq[1])) return { type, via: [], property: String(spec.eq[0]).split('.').slice(1).join('.'), ...side(spec.eq[1]) };
    const body = keys === 'exists' ? spec.exists : null;
    if (body && Object.keys(body.where || {}).join() === 'eq') {
      const [ref, who] = body.where.eq, via = [];
      let here = '$self';
      for (const e of body.edges || []) {
        if (e.length !== 3 || e[0] !== here) return { type, raw: spec };
        via.push(e[1]);
        [, , here] = e;
      }
      if (String(ref).startsWith(`${here}.`) && side(who)) return { type, via, property: String(ref).split('.').slice(1).join('.'), ...side(who) };
    }
    return { type, raw: spec };
  }

  function opsPolicyForm(d, x) {
    const m = S.mg.st, src = !noSource();
    const tick = (list, v, word, on, extra = '') => `<label class="k-ck pill"><input type="checkbox" data-in="opsPolTick" data-list="${list}" data-v="${esc(v)}"${extra}${on ? ' checked' : ''}>${esc(word)}</label>`;
    const all = (list) => tick(list, '*', '전체', d[list].includes('*'));
    const ticks = (list, items) => `<div class="ops-ticks">${all(list)}${d[list].includes('*') ? '' : items.map(([k, w]) => tick(list, k, w, d[list].includes(k))).join('')}</div>`;
    const read = d.read.includes('*') ? `<div class="ops-ticks">${all('read')}</div>` : `<div class="ops-ticks">${all('read')}</div><div>${opsObjects(m).map((o) => { const names = o.ents.map((e) => e.name), n = names.filter((x) => d.read.includes(x)).length;
      return `<div class="ops-group"><label class="k-ck mid k-b"><input type="checkbox" data-in="opsPolTick" data-list="read" data-ents="${esc(names.join(' '))}" data-v=""${n === names.length ? ' checked' : ''}><span class="k-cut">${esc(o.label)}</span>${n && n < names.length ? `<span class="k-xs" style="font-weight:400">${n}/${names.length}</span>` : ''}</label><div class="ops-ticks">${o.ents.map((e) => tick('read', e.name, e.label, d.read.includes(e.name))).join('')}</div></div>`; }).join('') || '<span class="k-s">Entity 없음</span>'}</div>`;
    const sel = (list, i, f, options, v) => `<select class="k-in" data-in="opsPolRow" data-list="${list}" data-i="${i}" data-f="${f}">${options.map(([k, w]) => opt(k, w, v)).join('')}</select>`;
    const del = (list, i) => `<button class="k-lnk bad" data-act="opsPolRowDel" data-list="${list}" data-i="${i}">삭제</button>`;
    const add = (list, word) => `<button class="k-lnk flat" data-act="opsPolRowAdd" data-list="${list}">${ki('plus', 16, 1.75)}${word}</button>`;
    const rule = (r, i) => {
      if (r.raw) return `<div class="ops-rule"><span class="k-s k-g0">${esc(mgLabel(r.type))} · 모듈 정의 조건</span>${del('rows', i)}</div>`;
      const prop = mgProps(r.via ? hopEnd(r.type, r.via) : r.type).find((p) => p.name === r.property);
      const fixed = r.mode === 'value' && prop && (prop.values || []).length;
      const value = fixed ? sel('rows', i, 'value', [['', '값 선택'], ...prop.values.map((v) => [v, (prop.labels || {})[v] ? `${prop.labels[v]} · ${v}` : v])], r.value)
        : `<input class="k-in" type="text" data-in="opsPolRow" data-list="rows" data-i="${i}" data-f="value" value="${esc(r.value ?? '')}" placeholder="${r.mode === 'value' ? '값' : '호출자 속성'}">`;
      return `<div class="ops-rule">${sel('rows', i, 'type', [['', 'Entity 선택'], ...roleObjects()], r.type)}${sel('rows', i, 'via', hopsOf(r.type), r.via)}${sel('rows', i, 'property', hopProps(r), r.property)}${sel('rows', i, 'mode', [['principal', '호출자 속성'], ['value', '고정 값']], r.mode)}${value}${del('rows', i)}</div>`;
    };
    const props = m.properties.map((p) => [`${p.object}.${p.name}`, `${mgLabel(p.object)} · ${p.label || p.name}`]);
    const mask = (r, i) => `<div class="ops-rule">${sel('mask', i, 'prop', [['', 'Property 선택'], ...props], r.prop)}${sel('mask', i, 'style', [['partial', '부분 마스킹'], ['full', '전체 마스킹']], r.style)}${del('mask', i)}</div>`;
    const scope = (r, i) => `<div class="ops-rule">${sel('scopes', i, 'type', [['', 'Entity 선택'], ...roleObjects()], r.type)}${sel('scopes', i, 'via', hopsOf(r.type), r.via)}${sel('scopes', i, 'property', hopProps(r), r.property)}${del('scopes', i)}</div>`;
    const callers = x ? opsCallers(x.name) : [];
    const field = (word, body, hint = '') => `<div class="k-f k-full">${word}${body}${hint ? `<span class="k-hint">${hint}</span>` : ''}</div>`;
    const later = src ? '' : '데이터 소스 연결 시 적용';
    return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">정책 키<input class="k-in mono" type="text" data-in="itf" data-k="name" value="${esc(d.name)}"${x ? ' disabled' : ''} placeholder="예: support_agent"><span class="k-hint">영문자로 시작, 영문자 · 숫자 · _ 사용</span></label>
        <label class="k-f">이름<input class="k-in" type="text" data-in="itf" data-k="label" value="${esc(d.label)}"></label>
        <label class="k-f k-full">연결 연동 대상<input class="k-in" type="text" value="${esc(callers.length ? callers.map((t) => `${t.name} · REST`).join(', ') : '없음')}" disabled></label>
        ${field('정의 범위 · 조회 Object', read)}
        ${field('데이터 행 범위', `${d.rows.map(rule).join('')}${add('rows', '행 범위 추가')}`, later)}
        ${field('마스킹 Property', `${d.mask.map(mask).join('')}${add('mask', '마스킹 Property 추가')}`, later)}
        ${m.actions.length ? field('요청 허용 Action', ticks('request', m.actions.map((a) => [a.name, a.label])), later) : ''}
        ${m.actions.length ? field('실행 허용 Action', ticks('execute', m.actions.map((a) => [a.name, a.label])), later) : ''}
      </div></div></section>
      <section class="k-card"><div class="k-ch"><h2>실행 · 문서 · 조직 범위</h2></div><div class="k-cb"><div class="k-g2">
        ${field('실행 허용 질의 · 결정 · 함수', ticks('run', [...m.decisions.map((q) => [q.name, q.label]), ...m.functions.map((q) => [q.name, q.label]), ...m.queries.map((q) => [q.name, q.label])]))}
        ${m.documents.length ? field('열람 문서', ticks('docs', [...(m.folders || []).map((f) => [`${f}/*`, `${f} 폴더`]), ...m.documents.map((q) => [q, q])]), '하위 폴더 포함') : ''}
        <label class="k-f k-full">조직 범위 · 호출자 속성<input class="k-in mono" type="text" data-in="itf" data-k="scope_attr" value="${esc(d.scope_attr)}" placeholder="예: seller_id"></label>
        ${field('조직 범위 · Entity', `${d.scopes.map(scope).join('')}${add('scopes', 'Entity 추가')}`)}
      </div></div></section>`;
  }

  item('policy', {
    word: '접근 정책', under: 'roles', list: 'roles',
    load: async () => { opsFresh(); if (!S.mg.st || S.mg.st.error) await loadManage(); if (!S.ops.tg) { try { S.ops.tg = await api('ops/targets'); } catch (e) { S.ops.tg = { error: e.message }; } } },
    find: (id) => (S.mg.st && !S.mg.st.error ? S.mg.st.roles.find((r) => r.name === id) || null : null),
    code: (x) => x.name, name: (x) => x.label, element: (x) => `role:${x.name}`,
    draft: (r) => (!r ? { name: '', label: '', read: [], run: [], request: [], execute: [], mask: [], rows: [], scope_attr: '', scopes: [], docs: ['*'], reason: '' } : {
      name: r.name, label: r.label, read: [...r.read], run: [...r.run], request: [...r.request], execute: [...r.execute], mask:Object.entries(r.mask).map(([prop, style]) => ({ prop, style })),
      rows: r.rows.map((x) => (x.raw ? { ...x } : { type: x.type, via: (x.via || [])[0] || '', property: x.property, mode: x.principal ? 'principal' : 'value', value: x.principal || String(x.value ?? '') })),
      scope_attr: (r.scope || {}).attribute || '', scopes: Object.entries((r.scope || {}).types || {}).map(([type, w]) => (typeof w === 'string' ? { type, via: '', property: w } : { type, via: (w.via || [])[0] || '', property: w.property })),
      docs: r.documents === null || r.documents === undefined ? ['*'] : [...r.documents], reason: '' }),
    form: opsPolicyForm,
    checks: (d, x) => {
      const m = S.mg.st, out = [];
      if (!x) {
        const shaped = /^[A-Za-z][A-Za-z0-9_]*$/.test(d.name), taken = m.roles.some((r) => r.name === d.name);
        out.push(!d.name ? { say: '정책 키 미입력', tone: 'warn' } : !shaped ? { say: '정책 키 형식 오류', sub: '영문자로 시작, 영문자 · 숫자 · _ 사용', tone: 'bad' } : taken ? { say: '중복된 정책 키', tone: 'bad' } : { say: '정책 키 중복 없음', tone: 'ok' });
      }
      const gone = d.mask.filter((r) => r.prop && !m.properties.some((p) => `${p.object}.${p.name}` === r.prop));
      out.push(gone.length ? { say: '정의에 없는 마스킹 Property', sub: gone.map((r) => r.prop).join(', '), tone: 'bad' } : { say: '마스킹 Property 정의 일치', tone: 'ok' });
      if (d.mask.some((r) => !r.prop)) out.push({ say: '마스킹 Property 미선택', tone: 'bad' });
      // the server keeps one masking style per Property: a second line would replace the first
      const masked = d.mask.map((r) => r.prop).filter((k, i, all) => k && all.indexOf(k) !== i);
      if (masked.length) out.push({ say: '마스킹 Property 중복', sub: [...new Set(masked)].map((k) => opsProp(m, k)).join(', '), tone: 'bad' });
      const outside = d.rows.filter((r) => r.type && !opsCan(d.read, r.type));
      if (outside.length) out.push({ say: '조회 범위 밖 Entity의 행 범위', sub: outside.map((r) => mgLabel(r.type)).join(', '), tone: 'warn' });
      const half = d.rows.filter((r) => !r.raw && !(r.type && r.property && String(r.value).trim()));
      if (half.length) out.push({ say: '행 범위 입력 누락', sub: 'Entity · Property · 값', tone: 'bad' });
      // the server keeps one rule per Entity, for rows and for the organisation's scope: a second would replace the first
      const twice = (list) => [...new Set(list.map((r) => r.type).filter((t, i, all) => t && all.indexOf(t) !== i))].map(mgLabel).join(', ');
      if (twice(d.rows)) out.push({ say: '행 범위 Entity 중복', sub: twice(d.rows), tone: 'bad' });
      if (d.scopes.some((r) => !(r.type && r.property))) out.push({ say: '조직 범위 입력 누락', sub: 'Entity · Property', tone: 'bad' });
      if (twice(d.scopes)) out.push({ say: '조직 범위 Entity 중복', sub: twice(d.scopes), tone: 'bad' });
      if (d.scopes.some((r) => r.type) && !String(d.scope_attr || '').trim()) out.push({ say: '조직 범위 호출자 속성 미입력', tone: 'bad' });
      out.push({ say: `연결 연동 대상 ${x ? opsCallers(x.name).length : 0}개`, tone: 'note' });
      if (noSource()) out.push({ say: '행 범위 · 마스킹 · 데이터 소스 연결 시 적용', tone: 'note' });
      return out;
    },
    valid: (d, x) => (!x && !d.name.trim() ? '정책 키를 입력해 주세요.' : !d.label.trim() ? '이름을 입력해 주세요.' : ''),
    save: async (d, x) => {
      const asValue = (v) => (v === 'true' ? true : v === 'false' ? false : (v !== '' && !Number.isNaN(Number(v)) ? Number(v) : v));
      const mask = Object.fromEntries(d.mask.map((r) => [r.prop, r.style]));
      const rows = d.rows.map((r) => (r.raw ? { type: r.type, raw: r.raw } : { type: r.type, via: r.via ? [r.via] : [], property: r.property, ...(r.mode === 'value' ? { value: asValue(r.value) } : { principal: r.value }) }));
      const scope = d.scope_attr ? { attribute: d.scope_attr, types: d.scopes.map((r) => ({ type: r.type, via: r.via ? [r.via] : [], property: r.property })) } : {};
      const name = x ? x.name : d.name.trim();
      S.mg.st = await api('manage/edit', { op: x ? 'update_role' : 'add_role', args: { name, label: d.label.trim(), read: d.read, run: d.run, request: d.request, execute: d.execute, mask, rows, scope, documents: d.docs.includes('*') ? null : d.docs } });
      S.ops.sel = name;
      return { go: 'roles', element: `role:${name}` };
    },
    // the callers that run as it, and the Actions it lets a caller request or execute
    uses: async (x) => {
      const acts = S.mg.st.actions.filter((a) => opsCan(x.request, a.name) || opsCan(x.execute, a.name)), names = acts.map((a) => a.label || a.name);
      return [...opsCallers(x.name).map((t) => ({ say: `연동 대상 ${t.name}`, sub: `호출 ${count(t.calls)}건`, href: 'connect' })),
        ...(acts.length ? [{ say: `Action ${count(acts.length)}개`, sub: `${names.slice(0, 3).join(', ')}${names.length > 3 ? ` 외 ${names.length - 3}` : ''}`, href: known('actions') ? 'actions' : '' }] : [])];
    },
    drops: (x) => [['delete_role', { name: x.name }]],
    remove: async (x) => { const [[op, args]] = ITEM.policy.drops(x); S.mg.st = await api('manage/edit', { op, args }); S.ops.sel = ''; if (S.ops.tryPol === x.name) S.ops.tryPol = ''; },
    history: async (x) => (await itemHistoryOf({ word: '접근 정책', element: (y) => `role:${y.name}` }, x)).map((e) => ({ ...e,
      rows: e.rows.map((r) => ({ ...r, label: opsRoleWord(r.label), before: opsRoleSaid(r.label, r.before), after: opsRoleSaid(r.label, r.after) })),
      all: e.all.map((r) => ({ ...r, label: opsRoleWord(r.label), value: opsRoleSaid(r.label, r.value) })) })),
    revert: async (x, e) => {  // the policy as that change left it, as an edit of the change request being written
      const r = await api('item/history?element=' + encodeURIComponent(`role:${x.name}`));
      const was = (r.entries.find((h) => h.change === e.cp) || {}).after, draft = r.entries[0] && r.entries[0].status === 'draft' ? r.entries[0] : null;
      if (!was) throw new Error('선택한 시점에 접근 정책이 없어 되돌리지 못했습니다. 다른 시점을 선택해 주세요.');
      if (JSON.stringify(was) === JSON.stringify(draft ? draft.after : r.now)) throw new Error('선택한 시점의 값이 현재 값과 같아 되돌리지 못했습니다. 이전 시점을 선택해 주세요.');
      const types = Object.entries((was.scope || {}).types || {}).map(([type, w]) => (typeof w === 'string' ? { type, via: [], property: w } : { type, via: w.via || [], property: w.property }));
      S.mg.st = await api('manage/edit', { op: 'update_role', args: { name: x.name, label: was.label || '', read: was.read || [], run: was.run || [], request: was.request || [],
        execute: was.execute || [], mask: was.mask || {}, rows: Object.entries(was.row_filters || {}).map(([type, raw]) => ({ type, raw })),
        scope: (was.scope || {}).attribute ? { attribute: was.scope.attribute, types } : {}, documents: was.documents === undefined ? null : was.documents } });
      return { go: 'changes' };
    },
  });

  // ---- a vector store added beside the one in use (an install that allows connections) -----------------------------

  item('store', {
    word: '저장소', under: 'adapters', list: 'adapters', direct: true, adds: true, may: () => isSysAdmin(),
    lead: { form: '벡터 저장소를 추가합니다.' },
    load: async () => { if (!opsGood(S.sp)) S.sp = await api('space'); },
    // a server that does not connect to stores outside shows that state alone, with no form and no save
    can: () => (opsGood(S.sp) && !S.sp.can_connect ? '외부 저장소 연결 허용 안 됨' : ''),
    find: () => null,
    name: (x) => x.name,
    draft: () => ({ name: '', kind: ((opsGood(S.sp) || { kinds: [] }).kinds.filter((k) => k !== 'memory')[0]) || '', url: '' }),
    form: (d) => `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">이름<input class="k-in mono" type="text" data-in="itf" data-k="name" value="${esc(d.name)}" placeholder="${esc(d.kind)}" maxlength="32"><span class="k-hint">미입력 시 종류 이름 사용</span></label>
        <label class="k-f">구분<select class="k-in" disabled><option>벡터 저장소</option></select></label>
        <label class="k-f">종류<select class="k-in" data-in="itf" data-k="kind" data-re>${S.sp.kinds.filter((k) => k !== 'memory').map((k) => opt(k, k, d.kind)).join('')}</select></label>
        <label class="k-f">주소<input class="k-in mono" type="text" data-in="itf" data-k="url" value="${esc(d.url)}" placeholder="${d.kind === 'pgvector' ? 'postgresql://...' : 'http://localhost:6333'}"></label>
      </div></div></section>`,
    checks: (d) => {
      const name = (d.name || d.kind).trim();
      const shaped = d.kind === 'pgvector' ? /^postgres(ql)?:\/\/\S+/.test(d.url.trim()) : /^https?:\/\/\S+/.test(d.url.trim());
      return [S.sp.stores.some((s) => s.name === name) ? { say: '중복된 저장소 이름', tone: 'bad' } : { say: '저장소 이름 중복 없음', tone: 'ok' },
        !d.url.trim() ? { say: '주소 미입력', tone: 'warn' } : shaped ? { say: '주소 형식 일치', tone: 'ok' } : { say: d.kind === 'pgvector' ? '주소는 postgresql:// 로 시작' : '주소는 http:// 또는 https:// 로 시작', tone: 'bad' }];
    },
    saves: () => [['반영', '즉시 적용']],
    valid: (d) => (!d.url.trim() ? '주소를 입력해 주세요.' : ''),
    save: async (d) => { S.sp = await api('space/store', { op: 'add', kind: d.kind, name: (d.name || d.kind).trim(), url: d.url.trim() }); S.ad = null; S.adrep = null; return { go: 'adapters', said: '벡터 저장소를 추가했습니다.' }; },
  });
