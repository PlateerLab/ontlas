  // ==== 운영 › 저장소 · 엔진 (adapters), 연동 · API (connect), 접근 정책 (roles), and the items they hold ==========
  // Each screen reads what the server measures now: the stores that answer, the callers of /v1 the server was started
  // with, the roles of the definition. Nothing here is a sample.

  S.ops = { key: '', tg: null, cn: null, busy: {}, sec: 'cfg', fold: {}, sel: '', landed: '', shown: '', tryPol: '', reidx: false };
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
    if (S.ops.key) S.conn = null;  // the decisions and Entities a call is tried on are another ontology's now
    Object.assign(S.ops, { key: k, tg: null, cn: null, sel: '' });
  }
  const opsGood = (x) => (x && !x.error && !x.busy ? x : null);
  const opsWait = (say = '불러오는 중입니다.') => `<section class="k-card pad"><p class="k-p s">${esc(say)}</p></section>`;
  const opsFailed = (say) => kEmpty('불러오지 못했습니다', say, '<button class="k-btn" data-act="opsRetry">다시 시도</button>');
  // the screens this one leads to; a screen of the admin area is marked and shown to those who may open it
  const opsNext = (links) => `<nav class="k-next" aria-label="이어지는 화면"><span>이어지는 화면</span>${links.filter(([h, , admin]) => known(h.split('?')[0]) && (!admin || (admin === 'onto' ? isOntoAdmin() : isSysAdmin())))
    .map(([h, w, admin]) => `<a class="k-lnk" href="#${h}">${esc(w)}${admin ? '<span class="k-chip w">관리</span>' : ''}${ki('chevR', 14, 1.75)}</a>`).join('')}</nav>`;
  const opsCopy = (text, say) => `<button class="k-lnk ops-copy" data-act="copycode" data-v="${esc(text)}" aria-label="${esc(say)}" title="${esc(say)}">${ki('copy', 16, 1.75)}</button>`;
  const opsTake = (text, word) => `<button class="k-btn sm" data-act="copycode" data-v="${esc(text)}">${esc(word)}</button>`;
  const opsPre = (text, say) => `<div class="ops-pre"><pre class="k-pre">${esc(text)}</pre>${opsCopy(text, say)}</div>`;
  // a text a person may want whole (a command, a settings file): folded until asked for, and it stays as left
  const opsMore = (key, title, text) => `<details class="ops-more" data-cn="${key}"${S.cn[key] ? ' open' : ''}><summary>${ki('chevR', 14, 1.75)}${esc(title)}</summary>${opsPre(text, `${title} 복사`)}</details>`;
  const opsFold = (key, word, body) => `<div class="ops-fold"><button class="k-lnk flat" data-act="opsFold" data-k="${key}" aria-expanded="${!!S.ops.fold[key]}">${ki(S.ops.fold[key] ? 'chevD' : 'chevR', 14, 1.75)}${word}</button>${S.ops.fold[key] ? body : ''}</div>`;
  const opsTargets = () => { const t = opsGood(S.ops.tg); return t ? t.targets : []; };

  // ---- OPS-01 저장소 · 엔진 ----------------------------------------------------------------------------------------

  const OPS_LOGIC = { rules: '규칙 판정 · AXIOM › Custom › Standard', owl2rl: 'OWL 2 RL · 계층 · 관계 추론', shapes: 'Restriction · 제약 검사' };
  const OPS_LLM = { off: '연결 안 됨', idle: '연결됨 · 호출 전', ok: '응답', bad: '응답 없음' };

  async function opsCheck(say) {  // every store asked the same questions, the reasoners run: the page runs it once on opening
    S.adbusy = true; render();
    try { S.adrep = await api('adapters/check', {}); S.adrs = null; S.ops.cn = null; if (say) toast('저장소 점검을 마쳤습니다.'); } catch (e) { fail(e); }
    S.adbusy = false; render();
  }

  function opsStorage() {
    const a = S.ad, rep = S.adrep, cn = opsGood(S.ops.cn), sp = opsGood(S.sp), tg = opsGood(S.ops.tg);
    const canAdd = !!(a && a.can_connect) && isSysAdmin();
    const head = kHead('저장소 · 엔진', '저장소, 쿼리 언어, 추론 엔진, 임베딩의 구성과 상태를 봅니다. 정의 원본과 그래프 · 벡터 저장소는 공간에 둡니다. 소스 DB는 데이터 바인더로 연결하면 함께 비교합니다.',
      `<button class="k-btn" data-act="opsCheck"${S.adbusy || !a || a.error ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.adbusy ? '점검 중' : '저장소 점검'}</button>${canAdd && ITEM.store ? `<a class="k-btn pri" href="${itemHref('store', 'form')}">${ki('plus', 16, 1.75)}저장소 추가</a>` : ''}`);
    if (!a) return head + opsWait('구성을 읽는 중입니다.');
    if (a.error) return head + opsFailed(a.error);
    const st = S.st;
    const seg = `<nav class="k-seg self" aria-label="이 화면의 구역">${[['cfg', '구성'], ['vec', '벡터 · 임베딩'], ['ext', '쓰는 곳']].map(([k, w]) => `<button class="${S.ops.sec === k ? 'on' : ''}" data-act="opsGo" data-to="ops${k}" data-k="${k}">${w}</button>`).join('')}</nav>`;
    // the tiles: what is set up, counted from the same rows as the tables under them
    const several = a.backends.length > 1;
    const rowsAll = 1 + a.backends.length + a.vectors.length + (a.source.connected ? 0 : 1);
    const down = (cn ? cn.stores.filter((x) => x.state === 'bad').length : 0) + a.vectors.filter((v) => v.error).length;
    const langsOk = a.languages.filter((l) => l.compiled === a.queries).length;
    const tile = (label, big, sub) => `<div class="k-stat ops-tile"><p>${label}</p><p class="k-big">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const dash = (label, big, sub) => `<div class="ops-dash ops-tile"><p class="k-s">${label}</p><p class="k-big mut">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const agree = !several ? dash('저장소 간 결과 일치', '연결 후', '소스 DB가 비교 기준')
      : tile('저장소 간 결과 일치', rep && rep.graph ? `${rep.graph.agree} / ${rep.graph.queries}` : S.adbusy ? '<span class="k-mut k-14">점검 중</span>' : '-', rep ? `점검 ${esc(String(rep.graph_ms))}ms` : '소스 DB가 비교 기준');
    const tiles = `<section class="k-wrap" aria-label="구성 요약">
      ${tile('저장소', `${rowsAll - (a.source.connected ? 0 : 1) - down} <span class="k-mut k-14" style="font-weight:400">/ ${rowsAll}</span>`, a.source.connected ? (down ? `응답 없음 ${down}` : '모두 응답') : '소스 DB는 연결 후')}
      ${tile('쿼리 변환 언어', `${langsOk} / ${a.languages.length}`, `등록 쿼리 ${count(a.queries)} 기준`)}
      ${tile('추론 엔진', count(a.reasoners.length), esc(a.reasoners.map((r) => r.name).join(' · ')) || '-')}
      ${tile('임베딩', a.embedder.dim ? `${count(a.embedder.dim)} <span class="k-mut k-14" style="font-weight:400">차원</span>` : '-', esc(a.embedder.kind))}
      ${agree}</section>`;
    // the stores: the definition's own files, where the rows are, where the graph is, where the passages are
    const dom = (st.layers.find((l) => l.kind === 'domain') || st.layers[0] || { modules: [] }).modules[0];
    const seen = (name) => (cn ? cn.stores.find((x) => x.name === name) : null);
    const said = (x) => (!x ? '' : x.state === 'bad' ? `<span class="k-chip bad" title="${esc(x.error)}">응답 없음</span>` : x.state === 'idle' ? '<span class="k-chip">호출 전</span>' : `<span class="k-chip ok">응답 ${esc(String(x.ms))}ms</span>`);
    const graphAgree = rep && rep.graph ? `<span class="k-chip ${rep.graph.agree === rep.graph.queries ? 'ok' : 'bad'}">${rep.graph.agree === rep.graph.queries ? '소스와 일치' : '소스와 다름'} ${rep.graph.agree} / ${rep.graph.queries}</span>` : '';
    const check = sp && sp.check;
    const dropCol = canAdd && a.vectors.length > 1;
    const storeRows = [`<tr><td class="k-code b">library</td><td>정의 원본</td><td>YAML 모듈 ${count(st.modules_on)}개</td><td>Object · Entity · 규칙 · 버전</td><td><span class="k-chip ok">기준${dom ? ` · v${esc(dom.version)}` : ''}</span></td>${dropCol ? '<td></td>' : ''}</tr>`]
      .concat(a.backends.map((b) => { const x = seen(b.name);
        return `<tr><td class="k-code b">${esc(b.name)}</td><td>${b.source ? '소스 저장소' : '그래프 저장소'}</td><td>${x ? `${esc(BACKEND_KIND[String(x.kind).toLowerCase()] || x.kind)} · ${esc(x.language)}` : `${esc(b.language)} ${esc(b.dialect || '')}`}</td>
          <td>${b.source ? `소스 값${b.write ? ' · 액션 반영' : ''} · 비교 기준` : `판정 · 쿼리 · 그래프 탐색${b.load ? ' · 소스 변경분 반영' : ''}`}</td><td><span class="k-h g6">${said(x)}${b.source ? '' : graphAgree}</span></td>${dropCol ? '<td></td>' : ''}</tr>`; }))
      .concat(a.vectors.map((v) => { const r = rep && rep.vectors[v.name];
        const state = v.error ? `<span class="k-chip bad">${esc(v.error)}</span>` : `${check ? `<span class="k-chip ${check.found === check.questions ? 'ok' : 'warn'}">검색 적중 ${check.found} / ${check.questions}</span>` : '<span class="k-chip ok">색인됨</span>'}${r && !r.error ? `<span class="k-chip ${r.agree ? 'ok' : 'bad'}">검색 결과 일치 ${Math.round(r.overlap * 100)}%</span>` : r && r.error ? `<span class="k-chip bad">${esc(r.error)}</span>` : ''}`;
        return `<tr><td class="k-code b">${esc(v.name)}</td><td>벡터 저장소</td><td>${esc(v.kind)} · ${esc(v.metric)}<br><span class="k-s">지원 ${esc(a.vector_kinds.join(' · '))}</span></td><td>문서 청크 ${count(v.count)}개 · 정의 검색</td><td><span class="k-h g6">${state}</span></td>
          ${dropCol ? `<td class="r">${v.primary ? '' : `<button class="k-lnk bad" data-act="opsStoreDrop" data-name="${esc(v.name)}">폐기</button>`}</td>` : ''}</tr>`; }))
      .concat(a.source.connected ? [] : [`<tr class="ops-off"><td class="k-code b">source</td><td>소스 저장소</td><td>-</td><td>소스 값 · 액션 반영 · 비교 기준</td><td>${known('db') ? '<a class="k-chip dash" href="#db">미연결 · 데이터 바인더</a>' : '<span class="k-chip dash">미연결</span>'}</td>${dropCol ? '<td></td>' : ''}</tr>`]).join('');
    const stores = `<section class="k-card" id="opscfg" aria-labelledby="ops-st-h"><div class="k-ch"><h2 id="ops-st-h">저장소</h2><span class="k-s k-push">정의 원본이 기준 · 그래프와 벡터는 버전마다 원본에서 다시 만듦</span></div>
      <div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">구분</th><th scope="col">종류</th><th scope="col">역할</th><th scope="col">상태</th>${dropCol ? '<th scope="col"></th>' : ''}</tr></thead><tbody>${storeRows}</tbody></table></div>
      ${a.can_connect ? '' : '<p class="k-cf line">Qdrant, pgvector 같은 외부 저장소는 연결을 허용한 설치에서 추가합니다. 이 서버는 메모리 저장소만 사용합니다.</p>'}</section>`;
    // the languages: every registered query compiled now; a language a store reads also runs there
    const langRows = a.languages.filter((l) => l.backends.length).concat(a.languages.filter((l) => !l.backends.length)).map((l) => {
      const why = l.refused.length ? `<br><span class="k-s">${l.refused.slice(0, 3).map((x) => `${esc(x.query)}: ${esc(x.error)}`).join('<br>')}</span>` : '';
      const ran = l.backends.length ? l.backends.map((n) => `<span class="k-chip ok">${esc(n)} · 실행</span>`).join(' ') : '<span class="k-chip">변환만</span>';
      return `<tr><td${l.backends.length ? ' class="b"' : ''}>${esc(l.label)}</td><td>${l.compiled === a.queries ? `${l.compiled} / ${a.queries}` : `<span class="k-warn">${l.compiled} / ${a.queries}</span>`}${why}</td><td>${ran}</td></tr>`;
    }).join('');
    const langs = `<section class="k-card" aria-labelledby="ops-ql-h" style="flex:3 1 520px"><div class="k-ch"><h2 id="ops-ql-h">쿼리 언어</h2><span class="k-s k-push">등록 쿼리 ${count(a.queries)}개를 각 언어로 변환</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">언어</th><th scope="col">변환</th><th scope="col">실행 저장소</th></tr></thead><tbody>${langRows}</tbody></table></div></section>`;
    // the reasoners: each run on the projected graph, when asked or by the check
    const reasRows = a.reasoners.map((r) => {
      const x = (S.adrs || {})[r.name] || (rep && rep.runs && rep.runs[r.name]);
      const found = x && (x.found !== undefined ? x.found : (x.findings || []).length);
      const g = rep && rep.reasoners && rep.reasoners[r.logic], twin = g && Object.keys(g.engines).length > 1;
      const mark = r.missing ? `<span class="k-chip warn">${esc(r.missing)}</span>` : !x ? (S.adbusy ? '<span class="k-chip">점검 중</span>' : '') : x.error ? `<span class="k-chip bad" title="${esc(x.error)}">실행 실패</span>` : `<span class="k-chip ${found ? 'warn' : 'ok'}">${found ? `발견 ${count(found)}건` : '발견 없음'}</span>`;
      const last = x && !x.error ? `<br><span class="k-s">유도한 사실 ${count(x.count)}건 · ${esc(String(x.ms))}ms${twin ? ` · 같은 논리 엔진과 결과 ${g.same ? '일치' : '다름'}` : ''}</span>` : x && x.error ? `<br><span class="k-s k-bad">${esc(x.error)}</span>` : '';
      return `<div class="ops-reas"><span class="k-g0"><span class="k-code k-b">${esc(r.name)}</span><br><span class="k-s">${esc(OPS_LOGIC[r.logic] || r.logic)}</span>${last}</span>${mark}${r.missing ? '' : `<button class="k-lnk" data-act="adreason" data-name="${esc(r.name)}">실행</button>`}</div>`;
    }).join('');
    const reas = `<section class="k-card" aria-labelledby="ops-rz-h" style="flex:2 1 340px"><div class="k-ch ops-line"><h2 id="ops-rz-h">추론 엔진</h2></div>${reasRows || '<p class="k-cf">추론 엔진이 없습니다.</p>'}</section>`;
    return `${head}${seg}${tiles}${stores}<div class="k-cols">${langs}${reas}</div>${opsVectors(a, sp, cn)}${opsUsedBy(a, tg)}
      ${opsNext([['query', '쿼리'], ['sys-ai', 'AI 운영', 'sys'], ['monitor', '파이프라인 모니터링'], ['sys-system', '시스템 상태', 'sys']])}`;
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
    if (!S.sp || S.sp.busy) more = '<p class="k-cf line">색인 상태를 읽는 중입니다.</p>';
    else if (S.sp.error) more = `<div class="k-cb"><p class="k-note bad">${esc(S.sp.error)}</p></div>`;
    else {
      const v = S.vemb, choices = (sp.embedders || []).filter((c) => !(c.kind === e.kind && (c.name || '') === e.name));
      const plan = v && v.plan ? `<div class="k-v"><div class="k-h g6"><span class="k-chip">문서 ${count(v.plan.files.length)}개</span><span class="k-chip">청크 ${count(v.plan.chunks)}개</span><span class="k-chip">${count(v.plan.chars)}자</span><span class="k-chip warn">예상 ${v.plan.seconds < 1 ? '1초 미만' : `약 ${Math.ceil(v.plan.seconds)}초`}</span></div>
          <p class="k-p s">임베딩 모델이 다르면 벡터를 비교할 수 없어 벡터 저장소를 비우고 모든 청크를 다시 임베딩합니다. 예상 시간은 새 모델로 청크 ${Math.min(6, v.plan.chunks)}개를 임베딩해 측정했습니다.</p>
          <div class="k-h"><button class="k-btn pri sm" data-act="vembuse"${v.busy ? ' disabled' : ''}>${v.busy ? '임베딩 중' : '변경하고 다시 임베딩'}</button><button class="k-btn sm" data-act="vembcancel">취소</button></div></div>` : '';
      const change = choices.length && isSysAdmin() ? opsFold('model', '임베딩 모델 변경', `<div class="k-v ops-in"><div class="k-h"><select class="k-in ops-pick" data-in="vemb" aria-label="임베딩 모델"><option value="">모델 선택</option>${choices.map((c) => { const at = (sp.embedders || []).indexOf(c); return `<option value="${at}"${v && String(v.pick) === String(at) ? ' selected' : ''}>${esc(c.name || c.kind)}${c.dim ? ` · ${c.dim}차원` : ''}</option>`; }).join('')}</select>
          <button class="k-btn" data-act="vembplan"${!v || v.pick === '' || v.busy ? ' disabled' : ''}>${v && v.busy && !v.plan ? '측정 중' : '영향 확인'}</button></div>${plan}</div>`) : '';
      const docs = opsFold('docs', `문서별 임베딩 ${count(sp.items.length)}`, `<div class="k-x ops-in"><table class="k-t s end"><thead><tr><th scope="col">문서</th><th scope="col">경로</th><th scope="col" class="r">항목</th><th scope="col" class="r">색인 청크</th><th scope="col">상태</th></tr></thead><tbody>${sp.items.map((d) => { const [tone, word] = EMBED_STATE[d.state] || ['', d.state === 'none' ? '내용 없음' : d.state];
        return `<tr><td class="b">${esc(d.name)}</td><td class="k-code mut">${esc(d.path || '기본 문서')}</td><td class="r">${d.sections}</td><td class="r">${d.chunks} / ${d.passages}</td><td><span class="k-chip${tone ? ` ${tone}` : ''}">${word}</span></td></tr>`; }).join('')}</tbody></table>
        <p class="k-p s" style="margin-top:8px">임베딩을 끈 문서는 검색에서 빠지고 문서 온톨로지에는 남습니다. ${known('catalog') ? '<a href="#catalog">자료 업로드</a>에서 파일이나 폴더 단위로 켜고 끕니다.' : ''}</p></div>`);
      const c = sp.check;
      const hits = c ? opsFold('check', `문서 검색 검증 ${c.found} / ${c.questions}`, `<div class="k-x ops-in"><table class="k-t s end"><thead><tr><th scope="col">질문</th><th scope="col">정답 문서</th><th scope="col">순위</th></tr></thead><tbody>${c.results.map((x) => `<tr><td>${esc(x.text)}</td><td>${esc(x.document)}</td><td>${x.rank ? `${x.rank}위` : '<span class="k-chip bad">미포함</span>'}</td></tr>`).join('')}</tbody></table>
        <p class="k-p s" style="margin-top:8px">질문마다 정답 문서가 상위 ${c.k}건에 들어 있는지 봅니다.</p></div>`) : '';
      more = `${sp.embed_error ? `<div class="k-cb"><p class="k-note bad">임베딩하지 못한 문서가 있습니다. ${esc(sp.embed_error)} 임베딩 모델 연결을 확인하면 다음 색인에서 다시 임베딩합니다.</p></div>` : ''}<div class="ops-folds">${change}${docs}${hits}</div>`;
    }
    return `<section class="k-card" id="opsvec" aria-labelledby="ops-vec-h"><div class="k-ch"><h2 id="ops-vec-h">벡터 · 임베딩</h2>${canEdit() ? `<div class="k-push"><button class="k-btn" data-act="opsReindex"${S.ops.reidx ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.ops.reidx ? '색인 중' : '재색인'}</button></div>` : ''}</div>
      <div class="k-wrap g16" style="padding:0 20px 20px">${table}${held}</div>${more}</section>`;
  }

  // who takes this ontology from outside, and whether rows come in from a source
  function opsUsedBy(a, tg) {
    const mark = (icon, cls) => `<span class="ops-mark${cls}">${ki(icon, 20, 1.75)}</span>`;
    const names = tg ? tg.targets.map((t) => t.name) : [];
    const callers = `<div class="k-card pad k-v" style="flex:1 1 320px"><div class="k-h nw">${mark('plug', ' b')}<div class="k-g0"><b>연동 대상${tg && tg.listed ? ` ${count(names.length)}` : ''}</b><p class="k-s" style="margin:0">${tg ? esc(!tg.rest ? '이 서버는 REST API 꺼짐' : names.length ? names.join(' · ') : 'REST API 켜짐') : ''}</p></div></div>
      <p class="k-13" style="margin:0;line-height:1.55">에이전트는 XGEN 등 외부에서 만들고 저장소의 온톨로지를 MCP, REST, 파일로 가져다 씁니다. 연동 대상과 키는 연동 · API에서, 범위는 접근 정책에서 정합니다.</p>
      <div class="k-wrap g8"><a class="k-btn" href="#connect">연동 · API</a><a class="k-lnk" href="#roles">접근 정책</a></div></div>`;
    const on = a.source.connected, kind = BACKEND_KIND[String(a.source.kind || '').toLowerCase()] || a.source.kind || a.source.name || '';
    const source = `<div class="k-v ${on ? 'k-card pad' : 'ops-dash'}" style="flex:1 1 320px;min-width:0${on ? '' : ';padding:20px'}"><div class="k-h nw">${mark('db', '')}<div class="k-g0"><b>데이터 소스</b><p class="k-s" style="margin:0">${on ? `${esc(kind)} · 연결됨` : '미연결 · 읽기 전용으로 연결'}</p></div></div>
      <p class="k-13" style="margin:0;line-height:1.55">비밀번호는 공간에 저장하지 않습니다. 읽기 전용 계정으로 연결하고 고른 테이블만 읽습니다.</p>
      ${known('db') ? `<a class="k-btn" href="#db" style="align-self:flex-start">${on ? '데이터 바인더에서 보기' : '데이터 바인더에서 연결'}</a>` : ''}</div>`;
    return `<section class="k-v g12" id="opsext" aria-labelledby="ops-ext-h"><h2 class="k-h2" id="ops-ext-h">이 온톨로지를 쓰는 곳</h2><div class="k-wrap g16" style="align-items:stretch">${callers}${source}</div></section>`;
  }

  function opsStorageAfter() {
    opsFresh();
    opsRead('tg', 'ops/targets');
    opsRead('cn', 'connections');
    opsRead('ad', 'adapters', () => S.ad, (x) => { S.ad = x; if (!x.error && !S.adrep && !S.adbusy) setTimeout(() => { if (S.tab === 'adapters' || S.tab === 'vectors') opsCheck(false); }, 0); });
    opsRead('sp', 'space', () => S.sp, (x) => { S.sp = x; });
  }
  screen('adapters', { area: 'work', word: '저장소 · 엔진', view: opsStorage, after: opsStorageAfter });
  // the older address of the vector screen opens the same screen at its section
  screen('vectors', {
    area: 'work', word: '저장소 · 엔진', under: 'adapters', find: false, crumb: () => ['운영', '저장소 · 엔진'],
    view: () => { S.ops.sec = 'vec'; return opsStorage(); },
    after: () => { opsStorageAfter(); const el = $('#opsvec'); if (el && S.ops.shown !== location.hash + ':' + !!S.ad) { S.ops.shown = location.hash + ':' + !!S.ad; el.scrollIntoView({ block: 'start' }); } },
  });

  Object.assign(ACT, {
    opsRetry: () => { ['tg', 'cn'].forEach((k) => { if (S.ops[k] && S.ops[k].error) S.ops[k] = null; }); if (S.ad && S.ad.error) S.ad = null; if (S.sp && S.sp.error) S.sp = null; if (S.conn && S.conn.error) S.conn = null; if (S.mg.st && S.mg.st.error) S.mg.st = null; render(); },
    opsCheck: () => opsCheck(true),
    opsGo: (t) => { S.ops.sec = t.dataset.k; t.parentNode.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b === t)); const el = document.getElementById(t.dataset.to); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); },
    opsFold: (t) => { S.ops.fold[t.dataset.k] = !S.ops.fold[t.dataset.k]; render(); },
    opsReindex: async () => {
      if (S.ops.reidx) return;
      S.ops.reidx = true; render();
      try { const r = await api('ops/reindex', {}); S.sp = r.space; S.ad = null; S.adrep = null; toast(`청크 ${count(r.chunks)}개를 다시 색인했습니다.`); } catch (e) { fail(e); }
      S.ops.reidx = false; render();
    },
    opsStoreDrop: async (t) => {
      if (!window.confirm(`벡터 저장소 ${t.dataset.name}을(를) 폐기합니다. 저장소의 색인은 이 공간에서 더 쓰지 않습니다.`)) return;
      try { S.sp = await api('space/store', { op: 'remove', name: t.dataset.name }); S.ad = null; S.adrep = null; toast('벡터 저장소를 폐기했습니다.'); } catch (e) { fail(e); }
      render();
    },
  });

  // ---- OPS-02 연동 · API ---------------------------------------------------------------------------------------------
  // The callers the server was started with, the ways an agent takes the ontology, the addresses, and one call tried
  // here as a platform makes it. The try panel keeps the names the older screen gave its controls (ctry…): the state
  // (S.ctry) and most handlers are the same ones.

  const OPS_NEEDS_SOURCE = new Set(['run_query', 'run_sparql', 'run_cypher', 'get_record', 'request_action']);

  function opsApi() {
    const i = S.conn, tg = opsGood(S.ops.tg), base = location.origin;
    const head = kHead('연동 · API', '이 온톨로지를 XGEN과 다른 에이전트 플랫폼이 가져다 쓰는 통로입니다. 에이전트는 여기서 만들지 않습니다. 연동 대상마다 키와 접근 정책을 연결합니다. 응답은 그 정책과 배포한 버전을 따릅니다.',
      '<a class="k-btn" href="/v1/openapi.json" download="ontlas-openapi.json">OpenAPI 내려받기</a>');
    if (!i) return head + opsWait();
    if (i.error) return head + opsFailed(i.error);
    const list = tg ? tg.targets : [];
    const tile = (label, big, sub, warn) => `<div class="k-stat${warn ? ' warn' : ''}"><p>${label}</p><p class="k-big${warn ? ' warn' : ''}">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const tiles = `<section class="k-wrap" aria-label="현황">
      ${tile('연동 대상', tg && tg.listed ? count(list.length) : i.rest ? '-' : '0', esc(!i.rest ? '이 서버는 REST API 꺼짐' : list.length ? list.map((t) => t.name).join(' · ') : 'REST API 켜짐'), !i.rest)}
      ${tg && tg.listed ? tile('이번 달 호출', count(tg.calls_month), '판정 · 답변 · 함수 · 액션 요청 기록 기준') : ''}
      ${tile('REST 도구', count(i.tools.length), 'OpenAPI 문서로 등록')}
      ${i.libraries > 1 ? tile('라이브러리', count(i.libraries), '요청에 library로 지정') : ''}</section>`;
    // who may call: named by the server, each with the policy it runs as
    const roles = new Set((S.st.roles || []).map((r) => r.name));
    const policy = (t) => (!t.policy ? '<span class="k-chip warn">정책 없음 · 전체 조회</span>' : roles.has(t.policy) ? `<a class="k-code" href="#roles?policy=${encodeURIComponent(t.policy)}">${esc(t.policy)}</a>` : `<span class="k-code k-ink">${esc(t.policy)}</span> <span class="k-chip warn">이 온톨로지에 없음</span>`);
    const rows = list.map((t) => `<tr><td><b class="k-b">${esc(t.name)}</b></td><td>REST</td><td>${policy(t)}</td><td>조회 · 판정 · 검색${t.write ? ' · 액션 요청' : ''}</td><td class="r">${count(t.calls)}</td><td>${t.last ? esc(String(t.last).slice(0, 16).replace('T', ' ')) : '<span class="k-mut">-</span>'}</td></tr>`).join('');
    const serveRest = 'export ONTLAS_API_TOKEN=...\nontlas serve studio.yaml --api-token-env ONTLAS_API_TOKEN --api-role support_agent';
    const agents = '# agents.yaml\nagents:\n  - {name: 고객 응대 Agent, token_env: ONTLAS_CS_TOKEN, role: customer_agent, principal: {customer_id: C001}, write: true}\n\nontlas serve studio.yaml --api-agents agents.yaml';
    const targets = `<section class="k-card" aria-labelledby="ops-tg-h"><div class="k-ch"><h2 id="ops-tg-h">연동 대상</h2><span class="k-s">플랫폼은 에이전트를 만드는 곳입니다</span><div class="k-push"><span class="k-chip ${i.rest ? 'ok' : 'warn'}">${i.rest ? 'REST API 켜짐' : 'REST API 꺼짐'}</span></div></div>
      ${rows ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">이름</th><th scope="col">연결</th><th scope="col">접근 정책</th><th scope="col">허용 도구</th><th scope="col" class="r">기록된 호출</th><th scope="col">마지막 사용</th></tr></thead><tbody>${rows}</tbody></table></div>`
    : `<p class="k-cf line">${i.rest ? '연동 대상 이름은 서버 설정에서 확인합니다.' : '이 서버는 REST API가 꺼져 있습니다. 서버를 띄울 때 토큰을 지정하면 켜집니다.'}</p>`}
      <div class="k-cb" style="padding-top:12px;gap:4px">${opsMore('serve', '서버에서 REST API 켜기', serveRest)}${opsMore('agents', 'Agent별 토큰과 역할', agents)}</div>
      <p class="k-cf line">연동 대상과 키는 서버를 띄울 때 정합니다 · 키 값은 화면에 나오지 않습니다 · 볼 수 있는 정의, 데이터, 액션은 <a href="#roles">접근 정책</a>에서 정합니다</p></section>`;
    // the ways an agent takes it, each with what a person copies to do so
    const mcpCmd = 'ontlas mcp studio.yaml --role customer_agent --principal customer_id=C001 --read-only';
    const mcpConf = JSON.stringify({ mcpServers: { ontlas: { command: 'ontlas', args: ['mcp', 'studio.yaml', '--role', 'customer_agent', '--read-only'] } } }, null, 2);
    const curl = `curl ${base}/v1/search -H "Authorization: Bearer $ONTLAS_API_TOKEN" \\\n  -H "Content-Type: application/json" -d '{"text": "반품 기간", "k": 3}'`;
    const gateway = 'backends:\n  source:\n    kind: gateway\n    url: https://platform.example/query\n    connection: 12\n    dialect: postgres\n    token_env: PLATFORM_TOKEN\n    source: true';
    const way = (name, say, acts) => `<div class="ops-way"><p><b>${name}</b><br>${say}</p><div class="k-h g6">${acts}</div></div>`;
    const ways = `<section class="k-card" aria-labelledby="ops-way-h"><div class="k-ch"><h2 id="ops-way-h">에이전트에 적용하는 방법</h2><span class="k-s">에이전트는 XGEN 등 외부에서 만들고 여기서는 온톨로지를 내어 줍니다</span></div><div class="ops-ways">
      ${way('MCP 서버로 연결', 'MCP를 지원하는 에이전트에 도구로 등록합니다. 정의 조회, 규칙 판정, 검색 도구를 그대로 씁니다.', `${opsTake(mcpCmd, '명령 복사')}${opsTake(mcpConf, '클라이언트 설정 복사')}`)}
      ${way('REST API 호출', '워크플로우와 에이전트 코드에서 판정, 답변, 정의 조회를 호출합니다. 판정 응답에 버전과 근거, 판정 경로가 들어갑니다.', `${opsTake('Authorization: Bearer <API 토큰>', '인증 헤더 복사')}${opsTake(curl, 'cURL 예시 복사')}<button class="k-btn sm" data-act="cngo" data-to="trypanel">API 실행</button>`)}
      ${way('온톨로지 파일로 받기', 'YAML, OWL로 내보내 에이전트 플랫폼에 올립니다. 규칙 판정은 API를 써야 배포한 버전이 적용됩니다.', known('library') ? '<a class="k-btn sm" href="#library">내보내기</a>' : '')}
      ${way('플랫폼 DB 연결', '플랫폼이 관리하는 DB 연결을 소스로 읽습니다. 비밀번호는 저장하지 않고, 읽기 전용과 허용 테이블은 플랫폼 정책을 따릅니다.', `${opsTake(gateway, '스튜디오 파일 설정 복사')}${S.st.data.connect && known('db') ? '<a class="k-btn sm" href="#db">플랫폼 연결 입력</a>' : ''}`)}
      </div></section>`;
    // the addresses: every tool /v1 serves, each with its own address to copy
    const toolRows = i.tools.map((t) => `<tr><td><span class="k-code k-ink">${esc(t.method)} ${esc(t.path)}</span><br><span class="k-m12">${esc(t.name)}</span></td><td>${esc(TOOL_WORD[t.name] || t.description)}</td>
      <td>${!i.rest ? '<span class="k-chip">꺼짐</span>' : !i.source && OPS_NEEDS_SOURCE.has(t.name) ? '<span class="k-chip">소스 연결 후</span>' : '<span class="k-chip ok">사용 중</span>'}</td><td class="r">${opsCopy(`${base}${t.path}`, `${t.name} 주소 복사`)}</td></tr>`).join('');
    const endpoints = `<section class="k-card" id="cntools" aria-labelledby="ops-ep-h"><div class="k-ch"><h2 id="ops-ep-h">엔드포인트</h2><span class="k-s">REST · v1 · 도구 ${count(i.tools.length)}개</span>
        <div class="k-push"><a class="k-lnk" href="/v1/openapi.json" target="_blank" rel="noopener">문서 열기</a><a class="k-lnk" href="/v1/tools" target="_blank" rel="noopener">도구 정의 열기</a></div></div>
      <div class="k-cb">${opsPre(`${base}/v1`, '주소 복사')}<div class="k-h g6">${opsTake(`${base}/v1/openapi.json`, 'OpenAPI 주소 복사')}${i.libraries > 1 ? `<span class="k-s">라이브러리가 여럿이면 요청에 library를 지정합니다. 목록은 /v1/libraries</span>` : ''}</div></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">메서드 · 경로</th><th scope="col">하는 일</th><th scope="col">상태</th><th scope="col"></th></tr></thead><tbody>${toolRows}</tbody></table></div>
      <p class="k-cf line">판정 응답에 정의 버전과 근거, 판정 경로가 들어갑니다</p></section>`;
    const mcp = `<section class="k-card" aria-labelledby="ops-mcp-h"><div class="k-ch"><h2 id="ops-mcp-h">MCP</h2></div><div class="k-cb">${opsPre(mcpCmd, 'MCP 명령 복사')}
      <span class="k-s">스튜디오 파일이 있는 위치에서 실행합니다 · 접근 정책을 지정하면 정의 · 데이터 범위와 마스킹이 그대로 적용됩니다</span>${opsMore('mcp', '클라이언트 설정', mcpConf)}</div></section>`;
    // how XGEN takes it, step by step, with what each step copies
    const chip = (text, word) => `<button class="k-chip b" data-act="copycode" data-v="${esc(text)}">${word}</button>`;
    const xgen = `<section class="k-card" aria-labelledby="ops-xg-h"><div class="k-ch"><h2 id="ops-xg-h">XGEN 연동</h2><span class="k-s">워크플로우와 Geny에서 쓰는 순서</span></div><ol class="ops-steps">
      <li><b>판정 노드</b><span>HTTP 요청 노드로 <span class="k-code">POST ${esc(base)}/v1/decide</span>를 호출합니다. 소스가 없어도 워크플로우가 가진 값을 values로 보내면 규칙대로 판정합니다. 값이 빠지면 422와 빠진 값 목록을 반환합니다. <button class="k-chip b" data-act="cnnode">노드 설정 보기</button></span></li>
      <li><b>용어 해석 · 값 검증</b><span><span class="k-code">/v1/terms</span>는 질문의 용어를 대표어, 뜻, 검색 표기로 바꿔 검색 질의 확장에 사용합니다. <span class="k-code">/v1/validate</span>는 값이 정의와 규칙 카드의 범위 안에 있는지 확인합니다. <button class="k-chip b" data-act="cngo" data-to="trypanel">API 실행</button></span></li>
      <li><b>Agent 도구</b><span>호출할 API를 API 도구로 등록하고 Geny의 도구 포트에 연결합니다. 판정, 규칙 카드, 용어, 검증 도구를 그대로 사용합니다. ${chip(`${base}/v1/openapi.json`, 'OpenAPI 주소 복사')}</span></li>
      <li><b>Agent 컨텍스트</b><span><span class="k-code">/v1/context</span>의 text를 Geny 시스템 프롬프트에 넣습니다. 질문과 관련된 정의와 규칙이 들어갑니다. ${chip(`${base}/v1/context`, '주소 복사')}</span></li>
      <li><b>검증</b><span><span class="k-code">/v1/questions</span>로 소스 연결 전에는 값 기준, 연결 후에는 레코드 기준으로 같은 검증 질문을 측정합니다. ${chip(`${base}/v1/questions`, '주소 복사')}</span></li></ol></section>`;
    return `${head}${tiles}${targets}${ways}<div class="ops-halves"><div class="ops-half">${endpoints}${mcp}</div><div class="ops-half">${opsTry(i)}</div></div>${xgen}
      ${opsNext([['actions', '액션'], ['changes', '배포 버전'], ['members', '멤버 · 권한', 'onto']])}`;
  }

  // one /v1 call made from the page: what is sent is what a platform sends, as the access policy picked would make it
  function opsTry(i) {
    const c = tryState(i), api = tryApi(c), NONE = '값 없음';
    const d = i.decisions.find((x) => x.name === c.decision), o = (i.objects || []).find((x) => x.name === c.object);
    const control = (x, cur, on) => {
      const attr = `class="k-in" data-in="${on}" data-k="${esc(x.name)}"`;
      if (x.type === 'boolean') return `<select ${attr}>${opt('', '입력 안 함', cur)}${opt('true', '예', cur)}${opt('false', '아니요', cur)}${opt('null', NONE, cur)}</select>`;
      if (x.values && x.values.length) return `<select ${attr}>${opt('', '입력 안 함', cur)}${x.values.map((v) => opt(String(v), String(v), cur)).join('')}${opt('null', NONE, cur)}</select>`;
      const num = ['integer', 'decimal', 'number'].includes(x.type);
      return `<input type="text" ${attr} value="${esc(cur ?? '')}"${num ? ' inputmode="decimal"' : ''} placeholder="${num ? `숫자 · 없으면 ${NONE}` : `없으면 ${NONE}`}">`;
    };
    const named = (x) => `<span>${esc(x.label)} <span class="k-m12">${esc(x.name)}</span></span>`;
    const pickObject = `<label class="k-f">Entity<select class="k-in" data-in="ctryo">${(i.objects || []).map((x) => opt(x.name, `${x.label} (${x.name})`, c.object)).join('')}</select></label>`;
    const help = (x) => (x.days_since ? `${x.property_label || x.property}에서 지난 일수. 일시(${x.property})로 보내도 됩니다.` : x.param ? '판정 Parameter' : x.property ? '' : '연결된 Entity에서 읽는 값');
    let fields, ready = true;
    if (c.api === 'terms') {
      fields = `<label class="k-f">문장<input class="k-in" type="text" data-in="ctryt" value="${esc(c.text)}" placeholder="질문 또는 문장"><span class="k-hint">용어사전의 동의어, 약어, 채널 표기를 대표어로 바꾸고 정의에 있는 이름을 찾습니다.</span></label>`;
    } else if (c.api === 'object') {
      ready = !!o;
      fields = o ? pickObject : '<p class="k-note">이 온톨로지에 Entity가 없습니다.</p>';
    } else if (c.api === 'validate') {
      ready = !!o;
      fields = !o ? '<p class="k-note">이 온톨로지에 Entity가 없습니다.</p>'
        : `<div class="k-g2">${pickObject}<label class="k-f">범위<select class="k-in" data-in="ctryc">${opt('', '입력한 값만', c.complete ? '1' : '')}${opt('1', '필수 속성 누락 포함', c.complete ? '1' : '')}</select></label>
          ${o.properties.map((x) => `<label class="k-f">${named(x)}${control(x, (c.ovalues || {})[x.name], 'ctryov')}</label>`).join('')}</div>`;
    } else if (!d) {
      ready = false;
      fields = '<p class="k-note">이 온톨로지에 결정표가 없습니다. 규칙에서 결정표를 추가하면 판정 API를 실행할 수 있습니다.</p>';
    } else {
      const mode = `<div class="k-f">기준<div class="k-seg self">${[['values', '판정 값'], ['record', '레코드 키']].map(([k, w]) => `<button class="${c.mode === k ? 'on' : ''}" data-act="ctrymode" data-k="${k}" aria-pressed="${c.mode === k}">${w}</button>`).join('')}</div></div>`;
      fields = `<div class="k-g2"><label class="k-f">판정<select class="k-in" data-in="ctryd">${i.decisions.map((x) => opt(x.name, `${x.label} (${x.name})`, c.decision)).join('')}</select></label>${mode}
        ${c.mode === 'record'
    ? `<label class="k-f k-full">레코드 키<input class="k-in" type="text" data-in="ctryk" value="${esc(c.key)}" placeholder="예: ${esc(d.target ? `${d.target_label} 키` : '레코드 키')}"><span class="k-hint">${i.source ? '소스에서 레코드를 읽어 판정합니다.' : '소스가 연결되어 있지 않아 409 응답을 반환합니다. 소스 없이 판정하려면 판정 값 기준을 사용합니다.'}</span></label>`
    : `${d.inputs.map((x) => `<label class="k-f">${named(x)}${control(x, (c.values || {})[x.name], 'ctryv')}${help(x) ? `<span class="k-hint">${esc(help(x))}</span>` : ''}</label>`).join('')}
        ${d.inputs.some((x) => x.days_since) ? `<label class="k-f">기준 시각 (선택)<input class="k-in" type="text" data-in="ctryat" value="${esc(c.at)}" placeholder="예: 2026-11-12T09:00:00"><span class="k-hint">일시로 보낸 값의 경과일을 이 시각 기준으로 계산합니다. 비우면 지금 기준입니다.</span></label>` : ''}`}</div>`;
    }
    const fill = c.api === 'decide' && d && c.mode === 'values' && d.example ? `<button class="k-btn" data-act="ctryfill" title="${esc(`${d.example.question} ${d.example.text}`)}">예시 값 채우기</button>` : '';
    const pols = S.st.roles || [];
    return `<section class="k-card" id="trypanel" aria-labelledby="ops-try-h"><div class="k-ch"><h2 id="ops-try-h">플레이그라운드</h2><div class="k-push"><span class="k-s">POST ${esc(api[2])}${i.library ? ` · ${esc(i.library.label)}` : ''}</span></div></div>
      <div class="k-cb ops-try"><p class="k-p s">워크플로우와 에이전트가 호출하는 API를 화면에서 실행합니다. 화면 결과는 같은 요청을 보낸 플랫폼이 받는 응답과 같습니다.</p>
        <div class="k-g2"><label class="k-f">엔드포인트<select class="k-in" data-in="opsTryApi">${TRY_API.map(([k, w, path]) => opt(k, `POST ${path} · ${w}`, c.api)).join('')}</select></label>
          <label class="k-f">접근 정책<select class="k-in" data-in="opsTryPol">${opt('', '정책 없음 · 전체', S.ops.tryPol)}${pols.map((r) => opt(r.name, r.label && r.label !== r.name ? `${r.name} · ${r.label}` : r.name, S.ops.tryPol)).join('')}</select></label></div>
        ${fields}
        ${ready ? `${opsTryCode(c, i)}<div class="k-h"><button class="k-btn pri" data-act="ctryrun"${c.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}${c.busy ? '보내는 중' : '보내기'}</button>${fill}${c.api === 'object' ? '' : '<button class="k-btn" data-act="ctryclear">값 지우기</button>'}</div>` : ''}
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
        <p class="k-p s">${template ? `앞 노드의 값은 body에 템플릿으로 넣습니다. 예: <span class="k-code" style="white-space:normal">${esc(template)}</span>. ` : ''}출력의 result에 응답이 들어 있고, 실패하면 success가 false입니다.</p>` : `<pre class="k-pre">${esc(text)}</pre>`}</div>`;
  }

  function opsTryResult(c) {
    const r = c.res, api = tryApi(c);
    if (c.busy) return '<p class="k-p s">실행 중입니다.</p>';
    if (!r) return `<p class="k-note">${esc(api[5].replace(/판정 실행|검증 실행|해석 실행|조회 실행/, '보내기'))}</p>`;
    const [tone, word] = r.status === 200 ? ['ok', api[4]] : TRY_STATUS[r.status] || ['bad', '오류'];
    const b = r.body || {};
    const as = r.policy ? `<span class="k-s">접근 정책 <span class="k-code">${esc(r.policy)}</span></span>` : '';
    const head = `<div class="k-h"><span class="k-chip ${tone}">${r.status} · ${word}</span>${c.api === 'decide' && b.mode ? `<span class="k-s">${b.mode === 'values' ? '판정 값 기준' : '레코드 기준'}</span>` : ''}${as}</div>`;
    const raw = `<pre class="k-pre">${esc(JSON.stringify(b, null, 2))}</pre>`;
    const table = (heads, rows) => `<div class="k-x"><table class="k-t s end"><thead><tr>${heads.map((h) => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
    if (r.status === 422) {
      const missing = (b.missing || []).length ? `<p class="k-note">판정에 필요한 값이 빠져 있어 판정하지 않았습니다. 빠진 값은 추정하지 않고 응답의 missing 목록으로 돌려줍니다. 에이전트는 이 목록으로 사용자에게 되물을 수 있습니다.</p>
        ${table(['빠진 값', '이름', '형식'], b.missing.map((m) => `<tr><td class="b">${esc(m.label)}</td><td class="k-code">${esc(m.input)}${m.property && m.property !== m.input ? ` <span class="k-mut">또는 ${esc(m.property)}</span>` : ''}</td><td>${esc(m.type)}${(m.values || []).length ? `<br><span class="k-s">허용 코드 ${esc(m.values.join(', '))}</span>` : ''}</td></tr>`).join(''))}` : '';
      const invalid = (b.invalid || []).length ? `<p class="k-note">허용 코드가 아닌 값이 있어 판정하지 않았습니다. 응답의 invalid 목록에 보낸 값과 허용 코드를 돌려줍니다.</p>
        ${table(['항목', '보낸 값', '허용 코드'], b.invalid.map((m) => `<tr><td class="b">${esc(m.label)}<br><span class="k-m12">${esc(m.input)}</span></td><td>${show(m.value)}</td><td>${esc((m.values || []).join(', '))}</td></tr>`).join(''))}` : '';
      return `${head}${invalid}${missing}${raw}`;
    }
    if (r.status !== 200) return `${head}${b.error ? `<p class="k-note warn">${esc(b.error)}</p>` : ''}${raw}`;
    const ver = b.definition ? `<p class="k-m12">정의 버전 ${esc(b.definition.version)} · 모듈 ${b.definition.modules.length}개</p>` : '';
    if (c.api === 'validate') {
      const bound = (v) => [v.min !== null && v.min !== undefined ? `${v.min} 이상` : '', v.max !== null && v.max !== undefined ? `${v.max} 이하` : ''].filter(Boolean).join(' · ');
      const why = (v) => (v.kind === 'rule' ? `<br><span class="k-s">${esc(v.statement)}</span><br><span class="k-s"><span class="k-code">${esc(v.rule)}</span> · ${esc(v.layer_label)} · ${esc(v.module)} ${esc(v.version)}${v.source ? ` · ${esc(v.source)}` : ''}</span>`
        : v.kind === 'code' ? `<br><span class="k-s">허용 코드 ${esc((v.allowed || []).map((a) => a.code).join(', '))}</span>` : v.kind === 'type' ? `<br><span class="k-s">${esc(TYPE_WORD[v.expected] || v.expected || '')} 형식</span>` : '');
      const rows = (b.violations || []).map((v) => `<tr><td class="b">${esc(v.label)}<br><span class="k-m12">${esc(v.property)}</span></td><td>${v.value === null || v.value === undefined ? '<span class="k-mut">-</span>' : show(v.value)}</td><td>${esc(TRY_KIND[v.kind] || v.kind)}${v.kind === 'rule' && bound(v) ? ` · ${esc(bound(v))}` : ''}${why(v)}</td></tr>`).join('');
      return `${head}<p class="ops-verdict">${b.valid ? '기준 충족' : `위반 ${(b.violations || []).length}건`}</p>${rows ? table(['속성', '값', '사유'], rows) : `<p class="k-p s">확인한 속성 ${(b.checked || []).length}개가 정의와 규칙 카드의 범위 안에 있습니다.</p>`}
        ${(b.rules || []).length ? `<p class="k-p s">적용한 규칙 카드 <span class="k-code" style="white-space:normal">${esc(b.rules.join(', '))}</span></p>` : ''}${ver}${raw}`;
    }
    if (c.api === 'terms') {
      const m = b.matched || [], d = b.defined || [];
      const exp = Object.fromEntries((b.expansions || []).map((x) => [x.term, x.labels]));
      if (!m.length && !d.length) return `${head}<p class="k-note">문장에서 용어사전의 용어와 정의의 이름을 찾지 못했습니다.</p>${raw}`;
      return `${head}<p class="k-p s">대표어 문장</p><p class="ops-verdict" style="font-size:16px">${esc(b.text)}</p>
        ${m.length ? table(['입력 표기', '대표어', '뜻'], m.map((x) => `<tr><td>${esc(x.label)}<br><span class="k-s">${esc(x.as_label)}</span></td><td class="b">${esc(x.term)}</td><td>${esc(x.meaning || '-')}${x.definition ? `<br><span class="k-s">${esc(x.definition)}</span>` : ''}${(exp[x.term] || []).length > 1 ? `<br><span class="k-s">검색 표기 ${esc(exp[x.term].join(', '))}</span>` : ''}</td></tr>`).join('')) : ''}
        ${(b.confusables || []).length ? `<p class="k-p s">혼동 주의 · ${b.confusables.map((x) => `<b>${esc(x.term)}</b> ≠ ${esc(x.confusable)}${x.note ? ` (${esc(x.note)})` : ''}`).join(' · ')}</p>` : ''}
        ${d.length ? table(['정의에서 찾은 이름', '뜻'], d.map((x) => `<tr><td class="b">${esc(x.label)}</td><td>${x.concepts.map((k) => `<span class="k-mut">${esc(k.concept_kind)}</span> ${esc(k.meaning)}`).join('<br>')}</td></tr>`).join('')) : ''}${ver}${raw}`;
    }
    if (c.api === 'object') {
      const o = b.object || {}, at = [b.area && b.area.label, b.parent && b.parent.label, o.label].filter(Boolean), props = Object.entries(o.properties || {});
      const label = (n) => (((S.conn || {}).objects || []).find((x) => x.name === n) || {}).label || n;
      return `${head}<p class="ops-verdict">${esc(at.join(' › '))}</p>${(b.children || []).length ? `<p class="k-p s">하위 Entity ${esc(b.children.map((x) => x.label).join(', '))}</p>` : ''}
        ${table([`Property ${props.length}개`, '라벨', '형식'], props.map(([k, p]) => `<tr><td class="k-code">${esc(k)}</td><td>${esc(p.label || '')}</td><td class="mut">${esc(TYPE_WORD[p.type] || p.type)}${(p.values || []).length ? ` · ${esc(p.values.join(', '))}` : ''}</td></tr>`).join(''))}
        ${(b.links || []).length ? table([`Relation ${b.links.length}개`, '연결'], b.links.map((x) => `<tr><td class="k-code">${esc(x.name)}</td><td>${esc(label(x.from))} → ${esc(label(x.to))}</td></tr>`).join('')) : ''}
        ${(b.decisions || []).length ? `<p class="k-p s">판정 <span class="k-code" style="white-space:normal">${esc(b.decisions.join(', '))}</span></p>` : ''}${ver}${raw}`;
    }
    const outs = b.outputs && typeof b.outputs === 'object' ? b.outputs : { result: b.outputs };
    const layers = ((b.path || {}).layers || []).map((x) => `<span class="k-chip${x.state === 'fired' ? ' ok' : ''}" title="${esc(x.said)}">${esc(x.label)} ${esc(x.fired.join(', ') || x.said)}</span>`).join('<span class="k-mut">›</span>');
    const src = (b.path || {}).source;
    const keep = b.mode === 'values' && canEdit() ? `<div class="k-v g4"><button class="k-btn" style="align-self:flex-start" data-act="ctrysave"${c.saved ? ' disabled' : ''}>${c.saved ? '검증 질문에 추가함' : '검증 질문으로 저장'}</button><span class="k-s">이 값과 결과를 검증 질문으로 저장합니다. 작성 중인 변경 요청에 담기고, 승인되면 검증에 포함됩니다.</span></div>` : '';
    return `${head}<p class="ops-verdict">${esc(b.verdict || '')}</p>
      ${Object.entries(outs).map(([k, v]) => `<div class="ops-pair"><span class="k-code">${esc(k)}</span><span>${show(v)}</span></div>`).join('')}
      <div class="k-h g6"><span class="k-s">판정 경로</span>${layers || '<span class="k-mut">-</span>'}</div>
      ${src ? `<p class="k-p s">판정을 정한 규칙 <span class="k-code">${esc(src.rule)}</span> · ${esc(src.layer_label)} · ${esc(src.module_label)} ${esc(src.version)}${src.cite ? ` · ${esc(src.cite)}` : ''}</p>` : ''}
      ${(b.evidence || []).length ? table(['근거 값', '값', '출처'], b.evidence.map((e) => `<tr><td class="k-code">${esc(e.input)}</td><td>${show(e.value)}</td><td class="mut">${e.source === 'given' ? '요청 값' : esc(e.source || '')}</td></tr>`).join('')) : ''}
      ${(b.not_needed || []).length ? `<p class="k-p s">판정에 쓰지 않은 값 · ${esc(b.not_needed.map((m) => m.label).join(', '))} (요청에 없음)</p>` : ''}${ver}${keep}${raw}`;
  }

  const opsTryRepaint = () => { const box = $('#opstrycode'); if (box && S.conn && !S.conn.error) box.outerHTML = opsTryCode(S.ctry, S.conn); };

  screen('connect', {
    area: 'work', word: '연동 · API',
    view: opsApi,
    after: () => {
      opsFresh();
      opsRead('tg', 'ops/targets');
      opsRead('conn', 'integrations', () => S.conn, (x) => { S.conn = x; });
    },
  });

  Object.assign(INPUT, {
    opsTryApi: (t) => { Object.assign(S.ctry, { api: t.value, res: null, saved: false }); render(); },
    opsTryPol: (t) => { S.ops.tryPol = t.value; if (S.ctry) { S.ctry.res = null; S.ctry.saved = false; } render(); },
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
      try { c.res = await api('ops/try', { path: tryApi(c)[2], policy: S.ops.tryPol, body: tryBody(c, S.conn) }); } catch (e) { c.res = { status: 400, body: { error: e.message } }; }
      c.busy = false; render();
    },
  });

  // ---- OPS-05 접근 정책 ----------------------------------------------------------------------------------------------
  // A policy is a role of the definition: what a caller of /v1 may read, which rows, what is hidden, what it may ask
  // to be done. The server says which caller runs as which policy.

  const OPS_MASK = { partial: '일부 가림', full: '전체 가림' };
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
    if (x.raw) return `${mgLabel(x.type)} · 모듈에서 정의한 조건`;
    const via = (x.via || []).filter(Boolean), end = via.length ? hopEnd(x.type, via[0]) : x.type;
    const p = m.properties.find((q) => q.object === end && q.name === x.property);
    return `${mgLabel(x.type)}${via.length ? ` › ${mgLabel(end)}` : ''}의 ${p ? p.label || x.property : x.property} = ${x.principal ? `호출자의 ${x.principal}` : show(x.value)}`;
  }
  const opsPolicy = () => { const m = S.mg.st; return m && !m.error ? m.roles.find((r) => r.name === S.ops.sel) || m.roles[0] || null : null; };
  const opsCallers = (name) => opsTargets().filter((t) => t.policy === name);

  function opsPolicies() {
    const m = S.mg.st, tg = opsGood(S.ops.tg);
    const head = kHead('접근 정책', 'XGEN이나 다른 플랫폼의 에이전트가 이 온톨로지를 가져다 쓸 때 적용하는 정책입니다. 연동 대상마다 볼 수 있는 정의, 데이터의 행 범위와 마스킹, 할 수 있는 액션을 정책 하나에 담습니다. 사람의 권한은 멤버 · 권한의 작업 역할로 정합니다.',
      `<a class="k-btn" href="#connect">${ki('plug', 16, 1.75)}연동 대상</a>${canEdit() ? `<a class="k-btn pri" href="${itemHref('policy', 'form')}">${ki('plus', 16, 1.75)}정책</a>` : ''}`);
    if (!m) return head + opsWait();
    if (m.error) return head + opsFailed(m.error);
    const src = !noSource(), list = tg ? tg.targets : [], roles = m.roles, sel = opsPolicy();
    const loose = list.filter((t) => !t.policy || !roles.some((r) => r.name === t.policy));
    const linked = (r) => list.filter((t) => t.policy === r.name);
    const bar = sel ? itemBar('policy', sel.name, sel.name, `${sel.label}${linked(sel).length ? ` · ${linked(sel).map((t) => t.name).join(', ')}에 연결` : ''}`) : '';
    const tile = (label, big, sub) => `<div class="k-stat ops-tile" style="flex-basis:170px"><p>${label}</p><p class="k-big">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const dash = (label, big, sub) => `<div class="ops-dash ops-tile" style="flex-basis:170px"><p class="k-s">${label}</p><p class="k-big mut">${big}</p><p class="k-s ops-sub">${sub}</p></div>`;
    const tiles = `<section class="k-wrap" aria-label="접근 정책 현황">
      ${tile('연동 대상', tg && tg.listed ? count(list.length) : tg && !tg.rest ? '0' : '-', esc(!tg ? '' : !tg.rest ? '이 서버는 REST API 꺼짐' : list.map((t) => t.name).join(' · ') || 'REST API 켜짐'))}
      ${tile('정책', count(roles.length), `정책이 없는 연동 대상 ${count(loose.length)}`)}
      ${tile('지금 적용', '정의 범위', 'Object · 규칙 조회와 판정')}
      ${src ? tile('지금 적용', '데이터 범위', '행 범위 · 마스킹') : dash('연결 후 적용', '데이터 범위', '행 범위 · 마스킹 · 데이터 소스 연결 후')}
      ${src && m.actions.length ? tile('지금 적용', '액션', '요청 · 승인 기준') : dash('연결 후 적용', '액션', m.actions.length ? '실행 · 요청 · 데이터 소스 연결 후' : '실행 · 요청 · 액션 정의 후')}</section>`;
    const say = `<section class="ops-say" role="note"><span class="ops-mark">${ki('plug', 20, 1.75)}</span><div><p class="k-b">에이전트는 밖에서 만들고 여기서는 범위만 정합니다</p>
      <p class="k-i3 k-14" style="margin-top:2px">XGEN 같은 에이전트 플랫폼은 서버에 연동 대상으로 등록하고 정책을 연결합니다. 정책을 연결하지 않은 연동 대상은 전체를 조회하므로 정책으로 범위를 정합니다.</p></div><a class="k-btn" href="#connect">연동 · API</a></section>`;
    if (!roles.length) return `${head}${tiles}${say}${kEmpty('아직 접근 정책이 없습니다', '정책을 만들면 연동 대상이 볼 수 있는 정의와 데이터, 요청할 수 있는 액션을 정할 수 있습니다.', canEdit() ? `<a class="k-btn pri" href="${itemHref('policy', 'form')}">${ki('plus', 16, 1.75)}정책</a>` : '')}`;
    // one row for each caller a policy is given to (a policy no caller runs as has one row of its own)
    const objs = opsObjects(m);
    const scope = (r) => (r.read.includes('*') ? '전체' : `Object ${count(objs.filter((o) => o.ents.some((e) => r.read.includes(e.name))).length)} · Entity ${count(r.read.length)}`);
    const acts = (r) => [r.request.length ? (r.request.includes('*') ? '요청 전체' : `요청 ${count(r.request.length)}`) : '', r.execute.length ? (r.execute.includes('*') ? '실행 전체' : `실행 ${count(r.execute.length)}`) : ''].filter(Boolean).join(' · ') || '<span class="k-mut">-</span>';
    const polCell = (r) => `<span class="k-code">${esc(r.name)}</span>${r.pending || r.new ? ' <span class="k-chip warn">변경 대기</span>' : ''}<br><span class="k-s">${esc(r.label)}</span>`;
    const row = (r, t) => `<tr class="${sel && r.name === sel.name ? 'on' : ''}" data-act="opsPolPick" data-name="${esc(r.name)}"><td class="b">${t ? `${esc(t.name)}<br><span class="k-s" style="font-weight:400">REST${t.write ? ' · 액션 요청' : ''}</span>` : '<span class="k-mut" style="font-weight:400">연결한 연동 대상 없음</span>'}</td>
      <td>${polCell(r)}</td><td>${scope(r)}</td><td>${r.rows.length ? esc(r.rows.map((x) => mgLabel(x.type)).join(' · ')) : '전체'}</td><td class="r">${count(Object.keys(r.mask).length)}</td><td>${acts(r)}</td></tr>`;
    const rows = roles.flatMap((r) => (linked(r).length ? linked(r).map((t) => row(r, t)) : [row(r, null)])).join('')
      + loose.map((t) => `<tr><td class="b">${esc(t.name)}<br><span class="k-s" style="font-weight:400">REST${t.write ? ' · 액션 요청' : ''}</span></td><td>${t.policy ? `<span class="k-code">${esc(t.policy)}</span> <span class="k-chip warn">이 온톨로지에 없음</span>` : '<span class="k-chip warn">정책 없음</span>'}</td><td>전체</td><td>전체</td><td class="r">0</td><td>${t.write ? '요청 전체' : '<span class="k-mut">-</span>'}</td></tr>`).join('');
    const table = `<section class="k-card" aria-labelledby="ops-tgp-h" style="flex:3 1 600px"><div class="k-ch"><h2 id="ops-tgp-h">연동 대상별 정책</h2><span class="k-chip">${count(roles.length)}</span><span class="k-s">연동 대상은 연동 · API에서 확인합니다</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">연동 대상</th><th scope="col">정책</th><th scope="col">정의 범위</th><th scope="col">데이터 행 범위</th><th scope="col" class="r">마스킹</th><th scope="col">액션</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="k-cf line">정책 하나를 여러 연동 대상에 연결할 수 있습니다 · 정책이 없는 연동 대상은 전체를 조회합니다${known('members') && isOntoAdmin() ? ' · 사람은 <a href="#members">멤버 · 권한</a>의 작업 역할을 따릅니다' : ''}</p></section>`;
    return `${head}${bar}${tiles}${say}<div class="k-cols">${table}${opsPolicyAside(m, sel, src)}</div>${opsPolicyScope(m, sel, src)}
      ${opsNext([['changes', '정책 변경을 변경 요청으로'], ['query', '정책으로 쿼리 테스트'], ['connect', '연동 대상 · API 키'], ['members', '멤버 · 권한', 'onto']])}`;
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
    const def = `<div class="k-h g6">${readable.map((o) => { const some = !r.read.includes('*') && !o.ents.every((e) => r.read.includes(e.name)); return `<span class="k-chip"${some ? ` title="${esc(o.ents.filter((e) => r.read.includes(e.name)).map((e) => e.label).join(', '))}"` : ''}>${esc(o.label)}${some ? ` ${o.ents.filter((e) => r.read.includes(e.name)).length}/${o.ents.length}` : ''}</span>`; }).join('') || '<span class="k-s">조회할 수 있는 Object가 없습니다</span>'}</div>
      <p class="k-s" style="margin:0">Object · Entity · 규칙 조회, 규칙 판정, 검색</p>${r.run.length ? pair('실행', esc(named(r.run, runs))) : ''}${m.documents.length ? pair('열람 문서', docs) : ''}`;
    const scoped = (r.scope || {}).attribute ? pair('조직 범위', `호출자의 ${esc(r.scope.attribute)} · Entity ${count(Object.keys(r.scope.types || {}).length)}`) : '';
    const data = `${pair('행 범위', r.rows.length ? r.rows.map((x) => esc(opsRowSay(m, x))).join('<br>') : '전체')}${scoped}${Object.entries(r.mask).map(([k, v]) => pair(esc(opsProp(m, k)), OPS_MASK[v] || esc(v))).join('')}${r.unmask.length ? pair('마스킹 해제', r.unmask.includes('*') ? '전체' : esc(r.unmask.map((k) => (k.endsWith('.*') ? `${mgLabel(k.slice(0, -2))} 전체` : opsProp(m, k))).join(' · '))) : ''}`;
    const act = (n, word) => { const a = m.actions.find((x) => x.name === n); return pair(esc(a ? a.label : n), a && word === '요청' && a.approval ? '요청 · 승인 필요' : word); };
    const actions = [...(r.request.includes('*') ? [pair('모든 액션', '요청')] : r.request.map((n) => act(n, '요청'))), ...(r.execute.includes('*') ? [pair('모든 액션', '실행')] : r.execute.map((n) => act(n, '실행')))].join('') || '<p class="k-s" style="margin:0">요청하거나 실행할 수 있는 액션이 없습니다</p>';
    const waiting = r.pending || r.new;
    return `<aside class="k-card ops-pol" aria-labelledby="ops-pd-h"><div class="ops-polh"><p class="k-s" style="margin:0">접근 정책${callers.length ? ` · ${esc(callers.map((t) => t.name).join(', '))}에 연결` : ''}</p><h2 id="ops-pd-h">${esc(r.name)}</h2><p class="k-i3 k-14" style="margin:0">${esc(r.label)}${r.module_label ? ` · ${esc(r.module_label)}` : ''}</p></div>
      ${part(1, '정의 범위', '<span class="k-chip ok">적용 중</span>', def)}
      ${part(2, '데이터 범위', src ? '<span class="k-chip ok">적용 중</span>' : '<span class="k-chip">데이터 소스 연결 후</span>', data)}
      ${part(3, '액션', src && m.actions.length ? '<span class="k-chip ok">적용 중</span>' : `<span class="k-chip">${m.actions.length ? '데이터 소스 연결 후' : '액션 정의 후'}</span>`, actions)}
      <div class="ops-polf"><a class="k-btn" href="#connect" data-act="opsPolTry" data-name="${esc(r.name)}">${ki('play', 16, 1.75)}이 정책으로 테스트</a>${waiting && known('changes') ? '<a class="k-btn pri" href="#changes">변경 요청에서 올리기</a>' : ''}</div></aside>`;
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
    return `<section class="k-card" aria-labelledby="ops-ob-h"><div class="k-ch"><h2 id="ops-ob-h">Object별 범위</h2><span class="k-code">${esc(r.name)}</span><span class="k-s">정의와 데이터를 한 표에서 정합니다${edit ? ' · 체크를 바꾸면 변경 요청에 담깁니다' : ''}</span></div>
      <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">Object</th><th scope="col" class="c">조회</th><th scope="col">행 범위</th><th scope="col">마스킹 속성</th><th scope="col">액션</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="k-cf line">${src ? '조회 범위, 행 범위, 마스킹이 지금 적용됩니다.' : `조회 범위는 지금 적용됩니다. 행 범위 · 마스킹은 데이터 소스를 연결하면, 액션은 액션을 연결하면 적용됩니다${known('db') ? ' · <a href="#db">데이터 소스 연결</a>' : ''}`}</p></section>`;
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
      try { S.mg.st = await api('manage/edit', { op: 'update_role', args: { name: r.name, read } }); toast('조회 범위를 바꿨습니다. 작성 중인 변경 요청에 담겼습니다.'); } catch (e) { fail(e); }
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
      if (t.tagName === 'SELECT') render();
    },
  });

  // ---- the policy's own screens ---------------------------------------------------------------------------------------

  const OPS_ROLE_FIELD = { read: '조회 Entity', run: '실행 쿼리 · 결정 · 함수', request: '요청 액션', execute: '실행 액션', mask: '마스킹', 가림: '마스킹', unmask: '마스킹 해제', row_filters: '행 범위', scope: '조직 범위', documents: '열람 문서', label: '이름', 라벨: '이름' };
  // a role's field as the policy screens name it: read -> 조회 Entity, mask.Customer.phone -> 마스킹 · Customer.phone
  const opsRoleWord = (label) => { const s = String(label), sep = s.includes(' · ') ? ' · ' : '.', head = s.split(sep)[0], rest = s.slice(head.length + sep.length); return OPS_ROLE_FIELD[head] ? `${OPS_ROLE_FIELD[head]}${rest ? ` · ${rest}` : ''}` : s; };

  function opsPolicyForm(d, x) {
    const m = S.mg.st, src = !noSource();
    const tick = (list, v, word, on, extra = '') => `<label class="k-ck pill"><input type="checkbox" data-in="opsPolTick" data-list="${list}" data-v="${esc(v)}"${extra}${on ? ' checked' : ''}>${esc(word)}</label>`;
    const all = (list) => tick(list, '*', '전체', d[list].includes('*'));
    const ticks = (list, items) => `<div class="ops-ticks">${all(list)}${d[list].includes('*') ? '' : items.map(([k, w]) => tick(list, k, w, d[list].includes(k))).join('')}</div>`;
    const read = d.read.includes('*') ? `<div class="ops-ticks">${all('read')}</div>` : `<div class="ops-ticks">${all('read')}</div><div>${opsObjects(m).map((o) => { const names = o.ents.map((e) => e.name), n = names.filter((x) => d.read.includes(x)).length;
      return `<div class="ops-group"><label class="k-ck mid k-b"><input type="checkbox" data-in="opsPolTick" data-list="read" data-ents="${esc(names.join(' '))}" data-v=""${n === names.length ? ' checked' : ''}><span class="k-cut">${esc(o.label)}</span>${n && n < names.length ? `<span class="k-xs" style="font-weight:400">${n}/${names.length}</span>` : ''}</label><div class="ops-ticks">${o.ents.map((e) => tick('read', e.name, e.label, d.read.includes(e.name))).join('')}</div></div>`; }).join('')}</div>`;
    const sel = (list, i, f, options, v) => `<select class="k-in" data-in="opsPolRow" data-list="${list}" data-i="${i}" data-f="${f}">${options.map(([k, w]) => opt(k, w, v)).join('')}</select>`;
    const del = (list, i) => `<button class="k-lnk bad" data-act="opsPolRowDel" data-list="${list}" data-i="${i}">삭제</button>`;
    const add = (list, word) => `<button class="k-lnk flat" data-act="opsPolRowAdd" data-list="${list}">${ki('plus', 16, 1.75)}${word}</button>`;
    const rule = (r, i) => {
      if (r.raw) return `<div class="ops-rule"><span class="k-s k-g0">${esc(mgLabel(r.type))} · 모듈에서 정의한 조건</span>${del('rows', i)}</div>`;
      const prop = mgProps(r.via ? hopEnd(r.type, r.via) : r.type).find((p) => p.name === r.property);
      const fixed = r.mode === 'value' && prop && (prop.values || []).length;
      const value = fixed ? sel('rows', i, 'value', [['', '값 선택'], ...prop.values.map((v) => [v, (prop.labels || {})[v] ? `${prop.labels[v]} · ${v}` : v])], r.value)
        : `<input class="k-in" type="text" data-in="opsPolRow" data-list="rows" data-i="${i}" data-f="value" value="${esc(r.value ?? '')}" placeholder="${r.mode === 'value' ? '값' : '호출자 속성 이름'}">`;
      return `<div class="ops-rule">${sel('rows', i, 'type', [['', 'Entity 선택'], ...roleObjects()], r.type)}${sel('rows', i, 'via', hopsOf(r.type), r.via)}${sel('rows', i, 'property', hopProps(r), r.property)}${sel('rows', i, 'mode', [['principal', '호출자 속성'], ['value', '고정 값']], r.mode)}${value}${del('rows', i)}</div>`;
    };
    const props = m.properties.map((p) => [`${p.object}.${p.name}`, `${mgLabel(p.object)} · ${p.label || p.name}`]);
    const mask = (r, i) => `<div class="ops-rule">${sel('mask', i, 'prop', [['', 'Property 선택'], ...props], r.prop)}${sel('mask', i, 'style', [['partial', '일부 가림'], ['full', '전체 가림']], r.style)}${del('mask', i)}</div>`;
    const scope = (r, i) => `<div class="ops-rule">${sel('scopes', i, 'type', [['', 'Entity 선택'], ...roleObjects()], r.type)}${sel('scopes', i, 'via', hopsOf(r.type), r.via)}${sel('scopes', i, 'property', hopProps(r), r.property)}${del('scopes', i)}</div>`;
    const callers = x ? opsCallers(x.name) : [];
    const field = (word, body, hint = '') => `<div class="k-f k-full">${word}${body}${hint ? `<span class="k-hint">${hint}</span>` : ''}</div>`;
    const later = src ? '' : '데이터 소스 연결 후 적용';
    return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">정책 키<input class="k-in mono" type="text" data-in="itf" data-k="name" value="${esc(d.name)}"${x ? ' disabled' : ''} placeholder="예: support_agent"><span class="k-hint">서버 설정에서 연동 대상에 이 키로 연결</span></label>
        <label class="k-f">이름<input class="k-in" type="text" data-in="itf" data-k="label" value="${esc(d.label)}"></label>
        <label class="k-f k-full">연결한 연동 대상<input class="k-in" type="text" value="${esc(callers.length ? callers.map((t) => `${t.name} · REST`).join(', ') : '없음')}" disabled><span class="k-hint">연동 · API에서 확인</span></label>
        ${field('정의 범위 · 조회할 수 있는 Object', read, '지금 적용')}
        ${field('데이터 행 범위', `${d.rows.map(rule).join('')}${add('rows', '행 범위 추가')}`, later || '조회하는 행을 호출자의 속성이나 고정 값으로 제한')}
        ${field('마스킹 속성', `${d.mask.map(mask).join('')}${add('mask', '마스킹 속성 추가')}`, later)}
        ${m.actions.length ? field('액션', ticks('request', m.actions.map((a) => [a.name, a.label])), `요청할 수 있는 액션${src ? '' : ' · 데이터 소스 연결 후 적용'}`) : ''}
      </div></div></section>
      <section class="k-card"><div class="k-ch"><h2>실행 · 문서 · 조직 범위</h2></div><div class="k-cb"><div class="k-g2">
        ${field('실행할 수 있는 쿼리 · 결정 · 함수', ticks('run', [...m.decisions.map((q) => [q.name, q.label]), ...m.functions.map((q) => [q.name, q.label]), ...m.queries.map((q) => [q.name, q.label])]))}
        ${m.documents.length ? field('열람 문서', ticks('docs', [...(m.folders || []).map((f) => [`${f}/*`, `${f} 폴더`]), ...m.documents.map((q) => [q, q])]), '이 정책으로 검색하고 답할 때 고른 폴더와 문서만 근거로 씁니다. 폴더를 고르면 하위 폴더의 문서도 들어갑니다') : ''}
        <label class="k-f k-full">조직 범위 · 호출자 속성<input class="k-in mono" type="text" data-in="itf" data-k="scope_attr" value="${esc(d.scope_attr)}" placeholder="예: seller_id"><span class="k-hint">지정하면 아래 Entity의 조회와 요청을 호출자가 속한 조직의 행으로 제한</span></label>
        ${field('조직 범위 · Entity', `${d.scopes.map(scope).join('')}${add('scopes', 'Entity 추가')}`, '호출자 속성을 지정했을 때 적용')}
      </div></div></section>`;
  }

  item('policy', {
    word: '접근 정책', under: 'roles', list: 'roles',
    hint: '접근 정책에서 ‘+ 정책’을 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    load: async () => { opsFresh(); if (!S.mg.st || S.mg.st.error) await loadManage(); if (!S.ops.tg) { try { S.ops.tg = await api('ops/targets'); } catch (e) { S.ops.tg = { error: e.message }; } } },
    find: (id) => (S.mg.st && !S.mg.st.error ? S.mg.st.roles.find((r) => r.name === id) || null : null),
    code: (x) => x.name, name: (x) => x.label, element: (x) => `role:${x.name}`,
    draft: (r) => (!r ? { name: '', label: '', read: [], run: [], request: [], mask: [], rows: [], scope_attr: '', scopes: [], docs: ['*'], reason: '' } : {
      name: r.name, label: r.label, read: [...r.read], run: [...r.run], request: [...r.request], mask: Object.entries(r.mask).map(([prop, style]) => ({ prop, style })),
      rows: r.rows.map((x) => (x.raw ? { ...x } : { type: x.type, via: (x.via || [])[0] || '', property: x.property, mode: x.principal ? 'principal' : 'value', value: x.principal || String(x.value ?? '') })),
      scope_attr: (r.scope || {}).attribute || '', scopes: Object.entries((r.scope || {}).types || {}).map(([type, w]) => (typeof w === 'string' ? { type, via: '', property: w } : { type, via: (w.via || [])[0] || '', property: w.property })),
      docs: r.documents === null || r.documents === undefined ? ['*'] : [...r.documents], reason: '' }),
    form: opsPolicyForm,
    checks: (d, x) => {
      const m = S.mg.st, out = [];
      if (!x) {
        const shaped = /^[A-Za-z][A-Za-z0-9_]*$/.test(d.name), taken = m.roles.some((r) => r.name === d.name);
        out.push(!d.name ? { say: '정책 키를 입력', tone: 'warn' } : !shaped ? { say: '정책 키는 영문자로 시작하고 영문자, 숫자, _ 만 사용', tone: 'bad' } : taken ? { say: '같은 키의 정책이 이미 있음', tone: 'bad' } : { say: '같은 키의 정책 없음', tone: 'ok' });
      }
      const gone = d.mask.filter((r) => r.prop && !m.properties.some((p) => `${p.object}.${p.name}` === r.prop));
      out.push(gone.length ? { say: '정의에 없는 마스킹 대상 속성이 있음', sub: gone.map((r) => r.prop).join(', '), tone: 'bad' } : { say: '마스킹 대상 속성이 모두 정의에 있음', tone: 'ok' });
      const outside = d.rows.filter((r) => r.type && !opsCan(d.read, r.type));
      if (outside.length) out.push({ say: '조회 범위 밖의 Entity에 행 범위가 있음', sub: outside.map((r) => mgLabel(r.type)).join(', '), tone: 'warn' });
      const half = d.rows.filter((r) => !r.raw && (r.type || r.property || r.value) && !(r.type && r.property && String(r.value).trim()));
      if (half.length) out.push({ say: '행 범위에 Entity, 속성, 값을 모두 채움', tone: 'bad', word: '수정 필요' });
      out.push({ say: `연결한 연동 대상 ${x ? opsCallers(x.name).length : 0}개`, tone: 'note' });
      if (noSource()) out.push({ say: '데이터 행 범위 · 마스킹은 데이터 소스 연결 후 적용', tone: 'note' });
      return out;
    },
    valid: (d, x) => (!x && !d.name.trim() ? '정책 키를 입력해 주세요.' : !d.label.trim() ? '이름을 입력해 주세요.' : ''),
    save: async (d, x) => {
      const asValue = (v) => (v === 'true' ? true : v === 'false' ? false : (v !== '' && !Number.isNaN(Number(v)) ? Number(v) : v));
      const mask = Object.fromEntries(d.mask.filter((r) => r.prop).map((r) => [r.prop, r.style]));
      const rows = d.rows.filter((r) => r.raw || (r.type && r.property)).map((r) => (r.raw ? { type: r.type, raw: r.raw } : { type: r.type, via: r.via ? [r.via] : [], property: r.property, ...(r.mode === 'value' ? { value: asValue(r.value) } : { principal: r.value }) }));
      const scope = d.scope_attr ? { attribute: d.scope_attr, types: d.scopes.filter((r) => r.type && r.property).map((r) => ({ type: r.type, via: r.via ? [r.via] : [], property: r.property })) } : {};
      const name = x ? x.name : d.name.trim();
      S.mg.st = await api('manage/edit', { op: x ? 'update_role' : 'add_role', args: { name, label: d.label.trim(), read: d.read, run: d.run, request: d.request, mask, rows, scope, documents: d.docs.includes('*') ? null : d.docs } });
      S.ops.sel = name;
      return { go: 'roles', element: `role:${name}` };
    },
    uses: async (x) => opsCallers(x.name).map((t) => ({ say: `연동 대상 ${t.name}`, sub: `이 정책으로 호출합니다 · 기록된 호출 ${count(t.calls)}건`, href: 'connect' })),
    remove: async (x) => { S.mg.st = await api('manage/edit', { op: 'delete_role', args: { name: x.name } }); S.ops.sel = ''; return { go: 'roles' }; },
    history: async (x) => (await itemHistoryOf({ word: '접근 정책', element: (y) => `role:${y.name}` }, x)).map((e) => ({ ...e, rows: e.rows.map((r) => ({ ...r, label: opsRoleWord(r.label) })), all: e.all.map((r) => ({ ...r, label: opsRoleWord(r.label) })) })),
  });

  // ---- a vector store added beside the one in use (an install that allows connections) -----------------------------

  item('store', {
    word: '저장소', under: 'adapters', list: 'adapters', direct: true, may: () => isSysAdmin(),
    hint: '저장소 · 엔진에서 ‘+ 저장소 추가’를 누르면 추가 화면이 열립니다',
    lead: { form: '벡터 저장소를 더합니다. 저장하면 바로 연결하고 공간의 문서를 그 저장소에 색인합니다.' },
    load: async () => { if (!opsGood(S.sp)) { try { S.sp = await api('space'); } catch (e) { S.sp = { error: e.message }; } } },
    find: () => null,
    name: (x) => x.name,
    draft: () => ({ name: '', kind: ((opsGood(S.sp) || { kinds: [] }).kinds.filter((k) => k !== 'memory')[0]) || '', url: '' }),
    form: (d) => {
      const sp = opsGood(S.sp);
      if (!sp || !sp.can_connect) return `<section class="k-card pad"><p class="k-note">이 서버는 외부 저장소 연결을 허용하지 않아 저장소를 더할 수 없습니다. 연결을 허용한 설치에서 Qdrant, pgvector 저장소를 더합니다.</p></section>`;
      return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">이름<input class="k-in mono" type="text" data-in="itf" data-k="name" value="${esc(d.name)}" placeholder="${esc(d.kind)}" maxlength="32"><span class="k-hint">비우면 종류 이름을 씁니다</span></label>
        <label class="k-f">구분<select class="k-in" disabled><option>벡터 저장소</option></select><span class="k-hint">그래프 · 소스 저장소는 데이터 바인더와 스튜디오 파일에서 정합니다</span></label>
        <label class="k-f">종류<select class="k-in" data-in="itf" data-k="kind" data-re>${sp.kinds.filter((k) => k !== 'memory').map((k) => opt(k, k, d.kind)).join('')}</select></label>
        <label class="k-f">주소<input class="k-in mono" type="text" data-in="itf" data-k="url" value="${esc(d.url)}" placeholder="${d.kind === 'pgvector' ? 'postgresql://...' : 'http://localhost:6333'}"><span class="k-hint">사내망 주소</span></label>
      </div></div></section>`;
    },
    checks: (d) => {
      const sp = opsGood(S.sp), name = (d.name || d.kind).trim();
      if (!sp || !sp.can_connect) return [{ say: '이 서버는 외부 저장소 연결을 허용하지 않음', tone: 'bad', word: '추가 불가' }];
      const shaped = d.kind === 'pgvector' ? /^postgres(ql)?:\/\/\S+/.test(d.url.trim()) : /^https?:\/\/\S+/.test(d.url.trim());
      return [sp.stores.some((s) => s.name === name) ? { say: '같은 이름의 저장소가 이미 있음', tone: 'bad' } : { say: '같은 이름의 저장소 없음', tone: 'ok' },
        !d.url.trim() ? { say: '주소를 입력', tone: 'warn' } : shaped ? { say: '주소 형식', tone: 'ok' } : { say: d.kind === 'pgvector' ? '주소는 postgresql:// 로 시작' : '주소는 http:// 또는 https:// 로 시작', tone: 'bad' },
        { say: `저장하면 연결을 확인하고 청크 ${count(sp.chunks)}개를 색인`, tone: 'note' }];
    },
    saves: () => [['적용', '저장 즉시'], ['기록', '공간 기록에 남음'], ['되돌리기', '저장소 표에서 폐기']],
    valid: (d) => (!d.url.trim() ? '주소를 입력해 주세요.' : ''),
    save: async (d) => { S.sp = await api('space/store', { op: 'add', kind: d.kind, name: (d.name || d.kind).trim(), url: d.url.trim() }); S.ad = null; S.adrep = null; return { go: 'adapters' }; },
  });
