  // ---- 모듈 라이브러리 (ONT-06): how much it holds, its layers, the change waiting, its versions, the modules it is made of ----

  async function o2LoadSem() {
    const L = S.o2.lib;
    if (L.semBusy) return;
    L.semBusy = true;
    const at = S.st;
    try { L.sem = await api('semantic'); } catch (e) { L.sem = { error: e.message, layers: [], cards: [] }; }
    L.semFor = at; L.semBusy = false;
    if (S.tab === 'library') render();
  }

  // the kinds of element a change touches, counted: + Entity 2, ~ Property 1
  function o2DiffRows(diff, terms = 0) {
    const out = [];
    [['added', '+', 'ok'], ['changed', '~', 'warn'], ['removed', '−', 'bad']].forEach(([k, sign, tone]) => {
      const by = {};
      (diff[k] || []).forEach((e) => { const [kind, name] = o2Split(e); (by[kind] = by[kind] || []).push(name); });
      Object.entries(by).forEach(([kind, names]) => out.push([sign, tone, `${O2_KIND[kind] || kind} ${names.slice(0, 4).join(' · ')}${names.length > 4 ? ` 외 ${names.length - 4}` : ''}`, names.length]));
    });
    if (terms) out.push(['~', 'warn', '용어 · 표현 관계', terms]);
    return out.map(([sign, tone, say, n], i, all) => `<li style="display:flex;gap:8px;padding:8px 0${i < all.length - 1 ? ';border-bottom:1px solid var(--row)' : ''}"><span class="k-code k-b k-chip ${tone}">${sign}</span><span class="k-g0">${esc(say)}</span><span class="k-s">${n}</span></li>`).join('');
  }

  function o2Library() {
    const st = S.st, L = S.o2.lib;
    const exports = `<details class="o2-menu"><summary class="k-btn">내보내기 · YAML · OWL</summary><div class="k-pop right" style="width:280px">
      <a class="k-opt" href="/api/export/library" download>${ki('download')}<span>YAML · 스튜디오 · 적용 모듈 zip</span></a>
      <a class="k-opt" href="/api/export/owl" download>${ki('download')}<span>OWL · Turtle</span></a></div></details>`;
    const head = kHead('모듈 라이브러리', '계층 구조 · 규모 · 버전 · 모듈을 관리합니다.',
      `${exports}<a class="k-btn" href="#changes">변경 요청 · 버전</a>`);
    const v = S.ver && S.ver.current ? S.ver : null, all = S.changes && S.changes.changes;
    if (!v || !all || !S.mg.st) return head + (S.ver && S.ver.error ? kEmpty('불러오지 못했습니다', S.ver.error) : o2Wait());
    const cur = v.current, sem = L.sem && !L.sem.error ? L.sem : null;
    const ws = S.mg.st.error ? null : S.mg.st.workspace, draft = !!(ws && ws.dirty), dm = S.o2.ch.dm || {};
    const open = all.filter((x) => x.status === 'pending');
    const hist = Object.fromEntries([...v.pending, ...v.history].map((x) => [x.id, x]));
    const stat = (word, value) => `<div class="k-card" style="flex:1 1 130px;padding:16px"><p class="k-s" style="margin:0">${word}</p><p class="k-big">${value}</p></div>`;
    const stats = `<section class="k-wrap" aria-label="규모">${stat('Object', count(st.stats.areas))}${stat('Entity', count(st.stats.objects))}${stat('Relation', count(st.stats.links))}${stat('Property', count(st.stats.properties))}
      ${stat('규칙', sem ? count(sem.cards.length) : '-')}${stat('현재 버전', esc(cur.label))}</section>`;
    // the layers a rule is judged in, with the modules that make each one
    const LAYER_SAY = { axiom: '모든 고객사 공통', standard: '표준 + 업종 확장', custom: '고객사별' };
    const layers = sem ? ['axiom', 'standard', 'custom'].map((k) => sem.layers.find((l) => l.layer === k)).filter(Boolean).map((l, i, xs) => `<div class="k-v g4" style="padding:12px 0${i < xs.length - 1 ? ';border-bottom:1px solid var(--row)' : ''}">
        <span class="k-h">${kLayer(l.layer)}<span class="k-s">${LAYER_SAY[l.layer] || ''}</span><span class="k-s k-push">규칙 ${count(l.cards)} · 결정표 규칙 ${count(l.rules)}</span></span>
        ${l.modules.length ? `<span class="k-h g6">${l.modules.map((m) => `<button class="k-chip w" data-act="libshow" data-mod="${esc(m.name)}">${esc(m.label)} <span class="k-m12">${esc(m.version)}</span></button>`).join('')}</span>` : '<span class="k-s">모듈 없음</span>'}</div>`).join('')
      : '<p class="k-p s">불러오는 중</p>';
    const layerCard = `<section class="k-card pad k-v g12" aria-labelledby="o2ly" style="flex:1 1 380px"><h2 class="k-h2" id="o2ly">계층 구조</h2><div style="display:flex;flex-direction:column">${layers}</div>
      <div class="k-wrap g8" style="margin-top:4px"><div class="k-13" style="flex:1 1 160px;padding:12px;border-radius:8px;background:var(--ok-soft)"><b class="k-ok">고객사 계층 허용</b><br>Entity · Property · Relation · 규칙 추가, 표준 항목 확장과 제외, 별칭</div>
        <div class="k-13" style="flex:1 1 160px;padding:12px;border-radius:8px;background:var(--warn-soft)"><b class="k-warn">금지 · 등록 시 검사</b><br>AXIOM 규칙 삭제와 수정, AXIOM이 정한 범위 밖의 기준값, 참조가 끊기는 삭제</div></div></section>`;
    // the change that waits: the one under review, else the one being written
    const x = open[0];
    const reg = (r) => (r && r.measured ? `<span class="k-chip ${(r.newly_failing || []).length ? 'bad' : 'ok'}">신규 오답 ${(r.newly_failing || []).length}</span>${r.accuracy && r.accuracy.after !== null ? `<span class="k-chip b">정답률 ${r.accuracy.before === r.accuracy.after || r.accuracy.before === null ? pct(r.accuracy.after) : `${pct(r.accuracy.before)} → ${pct(r.accuracy.after)}`}</span>` : ''}${r.grounded && r.grounded.after !== null ? `<span class="k-chip ok">근거 제시율 ${pct(r.grounded.after)}</span>` : ''}` : '<span class="k-s">측정 전</span>');
    const cpCard = x ? `<section class="k-card" aria-labelledby="o2cp" style="flex:2 1 520px"><div style="padding:16px 20px;border-bottom:1px solid var(--row);display:flex;flex-direction:column;gap:6px">
          <div class="k-pha"><span class="k-code k-blue">${esc(x.id)}</span><span class="k-chip b">검토 대기</span><span class="k-s">${esc(cur.label)} → 버전 ${cur.number + 1}</span></div>
          <h2 id="o2cp" style="margin:0;font-size:20px;font-weight:600">${esc(o2Title(x))}</h2>
          <p class="k-s" style="margin:0">${hist[x.id] && hist[x.id].summary && hist[x.id].summary !== o2Title(x) ? `${esc(hist[x.id].summary)} · ` : ''}요청 ${esc(x.requested_by || '-')} · ${o2When(x.at)}</p></div>
        <ul class="k-14" style="margin:0;padding:8px 20px;list-style:none">${o2DiffRows(x.diff || {}) || '<li class="k-s" style="padding:8px 0">바뀐 항목이 없습니다</li>'}</ul>
        <div class="k-pha" style="padding:12px 20px;border-top:1px solid var(--row)"><span class="k-b k-14">회귀 테스트</span>${reg(x.regression)}${known('flow') ? '<a class="k-lnk k-push" href="#flow">결과 보기</a>' : ''}</div>
        <div style="padding:12px 20px;border-top:1px solid var(--row);display:flex;justify-content:flex-end;gap:8px"><a class="k-btn pri" href="#changes?id=${encodeURIComponent(x.id)}">변경 요청 검토${ki('arrow', 16, 1.75)}</a></div></section>`
      : draft ? `<section class="k-card" aria-labelledby="o2cp" style="flex:2 1 520px"><div style="padding:16px 20px;border-bottom:1px solid var(--row);display:flex;flex-direction:column;gap:6px">
          <div class="k-pha"><span class="k-chip">작성 중</span><span class="k-s">${esc(cur.label)} → 버전 ${cur.number + 1}</span></div>
          <h2 id="o2cp" style="margin:0;font-size:20px;font-weight:600">${esc(o2DraftTitle())}</h2><p class="k-s" style="margin:0">변경 ${ws.edits.length}건 · ${esc(st.who || '')}</p></div>
        <ul class="k-14" style="margin:0;padding:8px 20px;list-style:none">${o2DiffRows(ws.diff, ws.edits.filter((e) => /^terms?:/.test(e.target)).length)}</ul>
        <div class="k-pha" style="padding:12px 20px;border-top:1px solid var(--row)"><span class="k-b k-14">회귀 테스트</span>${S.md.trial && S.md.trial.gates ? reg(S.md.trial.regression) : '<span class="k-s">검토 요청 시 자동 실행</span>'}</div>
        <div style="padding:12px 20px;border-top:1px solid var(--row);display:flex;justify-content:flex-end;gap:8px"><a class="k-btn pri" href="#changes">변경 요청 등록${ki('arrow', 16, 1.75)}</a></div></section>`
        : `<section class="k-card pad k-v" aria-labelledby="o2cp" style="flex:2 1 520px"><h2 class="k-h2" id="o2cp">열린 변경 요청이 없습니다</h2><a class="k-lnk flat" href="#changes">변경 요청 · 버전${ki('chevR', 14, 1.75)}</a></section>`;
    const applied = v.history.filter((h) => h.applied).sort((a, b) => b.number - a.number);
    const vrow = (label, say, right) => `<div class="k-14" style="display:flex;justify-content:space-between;gap:12px"><span class="k-g0"><b>${esc(label)}</b> · ${esc(say)}</span>${right}</div>`;
    const verCard = `<section class="k-card pad k-v" aria-labelledby="o2ver" style="flex:1 1 300px"><div class="k-h"><h2 class="k-h2" id="o2ver">버전</h2><a class="k-lnk k-push" href="#changes">전체 이력${ki('chevR', 14, 1.75)}</a></div>
      ${draft || x ? vrow(`버전 ${cur.number + 1}`, x ? o2Title(x) : o2DraftTitle(), `<span class="k-chip b">${x ? '승인 시 배포' : '작성 중'}</span>`) : ''}
      ${applied.slice(0, 4).map((h) => vrow(`버전 ${h.number}`, `${o2Title(h)}${h.summary && h.summary !== o2Title(h) ? ` · ${h.summary}` : ''}`, h.number === cur.number ? `<span class="k-chip ok">${o2When(h.decided_at)} · 현재</span>` : `<span class="k-s">${o2When(h.decided_at)}</span>`)).join('')}
      ${applied.length <= 4 ? vrow('버전 1', '처음 구성', cur.number === 1 ? '<span class="k-chip ok">현재</span>' : '') : ''}</section>`;
    const envCard = `<section class="k-card" aria-labelledby="o2env" style="flex:2 1 420px"><div class="k-h" style="padding:16px 20px"><h2 class="k-h2" id="o2env">배포 환경</h2><a class="k-lnk k-push" href="#changes">변경 요청 · 버전${ki('chevR', 14, 1.75)}</a></div>
      <div class="o2-env"><div class="k-v g4" style="padding:16px 20px"><span class="k-s">운영</span><span class="k-b" style="font-size:20px;font-variant-numeric:tabular-nums">${esc(cur.label)}</span><span class="k-s">${cur.at ? `${o2When(cur.at)} 배포` : '처음 구성'} · API · MCP 응답 기준</span></div>
        <div class="k-v g4" style="padding:16px 20px"><span class="k-s">미리보기</span><span class="k-b${draft || x ? '' : ' k-mut'}" style="font-size:20px;font-variant-numeric:tabular-nums">${draft || x ? `버전 ${cur.number + 1} 초안` : '없음'}</span><span class="k-s">${x ? `${esc(open.map((o) => o.id).join(' · '))} 포함` : draft ? '작성 중인 변경 요청' : '변경 없음'}</span></div></div></section>`;
    // the modules the ontology is made of
    const kinds = [...new Map(st.library.map((r) => [r.kind, r.kind_label])).entries()];
    if (S.kind !== 'all' && !kinds.some(([k]) => k === S.kind)) S.kind = 'all';
    const rows = st.library.filter((r) => S.kind === 'all' || r.kind === S.kind).map((r) => {
      const waiting = all.filter((c) => c.module === r.name && c.status === 'pending');
      const first = (st.graph.nodes.find((n) => n.module === r.name) || {}).id;
      const on = (S.impact && S.impact.module === r.name) || S.libFocus === r.name || S.libFocus === r.label;
      const req = r.requires.length ? r.requires.map((q) => `<button class="k-chip w" data-act="libshow" data-mod="${esc(q)}">${esc(shortMod((st.library.find((y) => y.name === q) || {}).label || q))}</button>`).join(' ') : '<span class="k-mut">-</span>';
      return `<tr class="${on ? 'on' : ''}"><td><span class="k-b" title="${esc(r.name)}">${esc(r.label || r.name)}</span>${r.description ? `<div class="k-xs o2-desc" title="${esc(r.description)}">${esc(r.description)}</div>` : ''}
          <div class="k-h g4" style="margin-top:2px">${canEdit() ? `<button class="k-lnk flat" data-act="medit" data-mod="${esc(r.name)}" style="margin-right:12px">파일 편집</button>` : ''}${first && known('model') ? `<a class="k-lnk flat" href="#model?entity=${encodeURIComponent(first)}">그래프 탐색</a>` : ''}${waiting.map((c) => `<a class="k-chip warn" href="#changes?id=${encodeURIComponent(c.id)}" style="margin-left:8px">${esc(c.id)} 검토 중 → ${esc(c.version)}</a>`).join('')}</div></td>
        <td title="${esc(r.kind_label)}">${esc(r.kind)}</td><td class="k-code">${esc(r.version)}</td><td>${req}</td><td class="i3">${esc(counts(r.counts))}</td>
        <td><input type="checkbox"${r.on ? ' checked' : ''}${canEdit() ? '' : ' disabled'} data-act="toggle" data-mod="${esc(r.name)}" aria-label="${esc(r.label || r.name)} 적용"></td></tr>`;
    }).join('');
    const libCard = `<section class="k-card" aria-labelledby="o2lib"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="o2lib">모듈</h2><span class="k-chip">${st.library.length} · 적용 ${st.modules_on}</span>
        <div class="k-seg" role="group" aria-label="종류">${[['all', '전체'], ...kinds].map(([k, w]) => `<button class="${S.kind === k ? 'on' : ''}" data-act="kind" data-kind="${esc(k)}" aria-pressed="${S.kind === k}">${esc(w)}</button>`).join('')}</div>
        <div class="k-push k-h">${known('ruleagent') ? '<a class="k-btn" href="#ruleagent">규칙 초안</a>' : ''}${canEdit() ? `<button class="k-btn" data-act="mnew">${ki('plus', 16, 1.75)}모듈</button>` : ''}</div></div>
      ${S.impact ? `<div class="o2-impact"><div class="k-b k-14" style="margin-bottom:8px">해제 영향</div>${impactCard()}</div>` : ''}
      <div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">모듈</th><th scope="col">종류</th><th scope="col">버전</th><th scope="col">의존</th><th scope="col">포함 요소</th><th scope="col">적용</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    return `${head}${stats}<div class="k-cols">${layerCard}${cpCard}</div><div class="k-cols">${verCard}${envCard}</div>${libCard}${S.ed ? editorCard() : ''}${known('ontology-new') ? '' : librariesCard()}
      ${kNext([...(isSysAdmin() ? [['sys-packs', '도메인 팩']] : []), ['flow', '검증'], ['connect', '연동 · API'], ['ontologies', '온톨로지 선택']])}`;
  }

  screen('library', {
    area: 'work', word: '모듈 라이브러리', view: o2Library,
    after: () => {
      const L = S.o2.lib;
      o2NeedManage('library');
      if (!S.changes) loadChanges();
      if (!S.ver) o2LoadVersions();
      if (S.mg.st && o2DraftStale()) o2LoadDraft();
      if (!L.sem || L.semFor !== S.st) o2LoadSem();
      if (S.libScroll) { S.libScroll = false; const row = $('#main tr.on'); if (row) row.scrollIntoView({ block: 'center' }); }
      if (S.ed && S.o2.lib.edFor !== S.ed) { S.o2.lib.edFor = S.ed; const box = $('#editor'); if (box) box.scrollIntoView({ block: 'nearest' }); }
    },
  });

  document.addEventListener('click', (ev) => {  // the export list closes when something outside it is chosen
    document.querySelectorAll('details.o2-menu[open]').forEach((d) => { if (!d.contains(ev.target) || ev.target.closest('.k-pop a')) d.open = false; });
  });
  document.addEventListener('keydown', (ev) => {  // and with Escape, back to the button that opened it
    if (ev.key !== 'Escape') return;
    document.querySelectorAll('details.o2-menu[open]').forEach((d) => { d.open = false; if (d.contains(document.activeElement)) d.querySelector('summary').focus(); });
  });
