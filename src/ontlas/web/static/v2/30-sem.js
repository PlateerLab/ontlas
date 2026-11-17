  // ==== 시멘틱 매니저: 규칙(SEM-01), 규칙 초안(SEM-02), and the own screens of a rule and of a named value ============
  // 규칙 is one screen: the three layers, every rule (a card that states one, a row of a decision table that decides),
  // a test on values typed in, what the checks found, and the named values, metrics and functions the rules read.
  // The older tabs it stands for (결정표, 기준값 · 지표, 함수) stay open by their own links: tables are edited there.

  S.smr = { sig: '', ws: '', loading: false, err: '', sel: '', psel: '', area: '', layer: '', more: 40, pmore: 30, newKind: 'parameter',
    dec: '', vals: {}, key: '', res: null, busy: false, simErr: '', agree: null, edges: false,
    dr: null, drTab: 'waiting', drSel: '', drMore: 12, drEdit: null, drBusy: false, docs: [], text: '', target: '', gen: false, genNote: '' };
  const SMR_STATUS = { approved: 'ok', review: 'warn', draft: 'warn' };
  const smrMine = () => ['semrules', 'ruleagent'].includes(S.tab);
  const smrWs = (m) => (m && m.workspace ? `${m.workspace.edits.length}:${m.workspace.dirty}:${m.workspace.version}` : '');
  const smrLines = (s) => String(s || '').split(/[\n;]/).map((x) => x.trim()).filter(Boolean);

  function smrFresh() {  // another ontology, other data, or an edit made on another screen: what was read is read again
    const x = S.smr, sig = `${S.st.library_id}|${S.st.pipeline}`;
    if (x.sig !== sig) {
      Object.assign(x, { sig, ws: '', err: '', sel: '', psel: '', area: '', layer: '', more: 40, pmore: 30, dec: '', vals: {}, key: '', res: null, simErr: '', agree: null, dr: null, drSel: '', drEdit: null, drMore: 12, docs: [], genNote: '' });
      S.ru = null;
    }
    if (S.mg.st && !S.mg.st.error && x.ws && x.ws !== smrWs(S.mg.st)) { S.sem.st = null; S.ru = null; x.dr = null; x.res = null; x.agree = null; }
  }

  const smrReady = (drafts) => !!(S.sem.st && !S.sem.st.error && S.mg.st && !S.mg.st.error && S.ru && (!drafts || (S.smr.dr && S.files && !S.files.busy)));

  // one read at a time: whoever asks while it runs waits for the same answer
  function smrLoad(opt = {}) {
    const x = S.smr;
    smrFresh();
    if (!x.job) {
      x.loading = true;
      x.job = Promise.all([
        !S.sem.st || S.sem.st.error ? api('semantic').then((r) => { S.sem.st = r; }) : 0,
        !S.mg.st || S.mg.st.error ? api('manage').then((r) => { S.mg.st = r; }) : 0,
        !S.ru ? api('rules').then((r) => { S.ru = r; }) : 0,
        opt.drafts && !x.dr ? api('sem/drafts').then((r) => { x.dr = r; }) : 0,
        opt.drafts && (!S.files || S.files.error || S.files.busy) ? api('files').then((r) => { S.files = r; }) : 0,
      ]).then(() => { x.err = ''; x.ws = smrWs(S.mg.st); }, (e) => { x.err = e.message || String(e); })
        .then(() => { x.loading = false; x.job = null; });
    }
    return x.job.then(() => { if (!opt.quiet && smrMine()) render(); });
  }
  // an item's own screen reads the same data; what could not be read is said as that, not as an item that is gone
  async function smrLoadItem() {
    await smrLoad({ quiet: true });
    if (!smrReady()) await smrLoad({ quiet: true });
    if (S.smr.err || !smrReady()) throw new Error(S.smr.err || '정의를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
  }

  function smrEdited(r) {  // an edit went in: the definition the screens read has moved
    if (r && r.workspace) S.mg.st = r;
    S.sem.st = null; S.ru = null; S.qa = null;
    Object.assign(S.smr, { dr: null, res: null, agree: null, ws: '' });
  }

  const smrWait = (head) => `${head}<section class="k-card pad"><p class="k-p s">불러오는 중입니다.</p></section>`;
  const smrFail = (head) => `${head}${kEmpty('불러오지 못했습니다', S.smr.err || (S.sem.st || {}).error || (S.mg.st || {}).error || '', '<button class="k-btn" data-act="smrRetry">다시 불러오기</button>')}`;

  // the Objects a rule is about: the Object of each Entity it applies to
  function smrAreas(c) {
    const m = S.mg.st, out = [];
    (c.applies_to || []).forEach((ref) => {
      const [kind, ...rest] = String(ref).split(':');
      const name = kind === 'property' ? rest.join(':').split('.')[0] : rest.join(':');
      const o = kind === 'object' || kind === 'property' ? m.objects.find((t) => t.name === name) : null;
      const a = o && o.area ? o.area : kind === 'area' ? name : '';
      if (a && !out.includes(a)) out.push(a);
    });
    return out;
  }
  const smrAreaWord = (name) => { const a = (S.mg.st.areas || []).find((y) => y.name === name); return a ? a.label || a.name : name; };
  // what a rule applies to, in the words of the definition
  function smrApplies(c) {
    if (c.applies_to_labels && c.applies_to_labels.length) return c.applies_to_labels;
    const m = S.mg.st;
    return (c.applies_to || []).map((ref) => {
      const [kind, ...rest] = String(ref).split(':'), name = rest.join(':');
      if (kind === 'object') return mgLabel(name);
      if (kind === 'area') return `Object ${smrAreaWord(name)}`;
      if (kind === 'property') { const [t, p] = name.split('.'); const hit = m.properties.find((y) => y.object === t && y.name === p); return `${mgLabel(t)} · ${hit ? hit.label || p : p}`; }
      if (kind === 'parameter') { const hit = m.parameters.find((y) => y.name === name); return hit ? hit.label : `@${name}`; }
      return ref;
    });
  }
  // every rule card is edited here (an AXIOM card as a change request to its own module); an AXIOM rule of a decision table is not
  const smrEditable = (c) => (c.kind === 'executable' ? c.layer !== 'axiom' : true);
  const smrAxiomCard = (c) => !!c && c.kind !== 'executable' && c.layer === 'axiom';
  const SMR_AXIOM_SAID = 'AXIOM 모듈의 변경 요청으로 올렸습니다. 승인하면 반영됩니다.';
  const smrVer = (c) => `${c.version ? `v${c.version}` : '-'}${c.new || c.pending ? ' 초안' : ''}`;
  const smrCite = (s) => (s ? `<span class="k-m12 smr-cite"><span aria-hidden="true">§</span>${esc(s)}</span>` : '<span class="k-mut">-</span>');

  // ---- SEM-01 규칙 ----------------------------------------------------------------------------------------------

  function smrRulesView() {
    const x = S.smr, can = canEdit();
    smrFresh();
    const st = S.sem.st, m = S.mg.st;
    const waiting = st && st.cards ? st.cards.filter((c) => c.status !== 'approved').length : 0;
    const head = kHead('규칙', '규칙을 AXIOM과 Rules(Standard · Custom)로 나누고 AXIOM › Custom › Standard 순서로 판정합니다. 모든 규칙에 조건, 결과, 예외, 근거, 버전, 담당자를 남깁니다.',
      `<a class="k-btn" href="#ruleagent">${ki('doc', 16, 1.75)}규칙 초안${waiting ? ` ${waiting}` : ''}</a>${can ? `<a class="k-btn pri" href="#rule-form" data-act="smrNew" data-kind="rule">${ki('plus', 16, 1.75)}규칙 카드</a>` : ''}`);
    if (x.err || (st && st.error) || (m && m.error)) return smrFail(head);
    if (!smrReady()) return smrWait(head);
    const areasOf = new Map(st.cards.map((c) => [c.ref, smrAreas(c)]));
    const areas = [...new Set(st.cards.flatMap((c) => areasOf.get(c.ref)))];
    if (x.area && !areas.includes(x.area)) x.area = '';
    const cards = st.cards.filter((c) => (!x.layer || c.layer === x.layer) && (!x.area || areasOf.get(c.ref).includes(x.area)));
    if (!x.sel || !cards.some((c) => c.ref === x.sel)) x.sel = (cards[0] || {}).ref || '';
    const sel = cards.find((c) => c.ref === x.sel);
    if (sel && sel.kind === 'executable' && x.decFor !== sel.ref) { x.decFor = sel.ref; if (x.dec !== sel.decision) { Object.assign(x, { dec: sel.decision, vals: {}, key: '', res: null, simErr: '' }); } }
    if (!x.dec || !m.decisions.some((d) => d.name === x.dec)) Object.assign(x, { dec: (m.decisions[0] || {}).name || '', vals: {}, key: '', res: null });
    const bar = sel ? itemBar('rule', sel.ref, sel.id, sel.statement, { edit: smrEditable(sel), del: smrEditable(sel) }) : '';
    const violated = st.violations.length ? `<p class="k-note bad"><b>AXIOM 위반 ${st.violations.length}건</b> · ${st.violations.map((v) => esc(v.said)).join(' · ')}</p>` : '';
    const LY_SAY = { axiom: '항상 참 · 어떤 규칙도 덮어쓸 수 없음', custom: '고객사 규칙 · Standard보다 우선', standard: '표준 도메인 팩 기본값 · Custom이 없을 때' };
    const strip = `<section class="k-card smr-strip" aria-label="적용 우선순위">${st.layers.map((l) => `<button type="button" class="smr-ly${x.layer === l.layer ? ' on' : ''}" data-act="smrLayer" data-k="${esc(l.layer)}" aria-pressed="${x.layer === l.layer}" title="${esc(l.modules.map((y) => `${y.label} ${y.version}`).join(', ') || '규칙을 쓴 모듈 없음')}">
      <span class="k-code k-mut">${l.order}</span><span class="k-col">${kLayer(l.layer)}<span class="k-s">${LY_SAY[l.layer] || esc(l.description)}</span></span><span class="smr-n">${count(l.rules + l.cards)}</span></button>`).join('')}</section>`;
    const shown = cards.slice(0, x.more);
    const owner = (c) => (c.legal_review === 'pending' ? '<span class="k-chip warn">법무 검토 중</span>' : `${esc(c.owner || '-')}${c.status !== 'approved' ? ` <span class="k-chip ${SMR_STATUS[c.status] || ''}">${esc(c.status_label || c.status)}</span>` : ''}`);
    const tr = (c) => `<tr class="${c.ref === x.sel ? 'on' : ''}" data-act="smrPick" data-ref="${esc(c.ref)}"${c.ref === x.sel ? ' aria-selected="true"' : ''}><td class="k-code smr-id${c.ref === x.sel ? ' b' : ''}">${esc(c.id).replace('#', '#<wbr>')}</td><td class="${c.ref === x.sel ? 'b' : ''}">${esc(c.statement)}</td><td>${kLayer(c.layer)}</td><td>${smrCite(c.source)}</td><td class="k-code">${esc(smrVer(c))}</td><td>${owner(c)}</td></tr>`;
    const picks = `<select class="smr-pick${x.area ? ' on' : ''}" data-in="smrArea" aria-label="영역"><option value="">영역 · 전체</option>${areas.map((a) => `<option value="${esc(a)}"${a === x.area ? ' selected' : ''}>영역 · ${esc(smrAreaWord(a))}</option>`).join('')}</select>
      <select class="smr-pick${x.layer ? ' on' : ''}" data-in="smrLayerPick" aria-label="계층"><option value="">계층 · 전체</option>${st.layers.map((l) => `<option value="${esc(l.layer)}"${l.layer === x.layer ? ' selected' : ''}>계층 · ${esc(l.label)}</option>`).join('')}</select>`;
    const pending = st.cards.filter((c) => c.pending || c.new).length;
    const foot = `${count(shown.length)} / ${count(st.cards.length)}개 표시${pending ? ` · 작성 중인 변경 요청에 담긴 규칙 ${count(pending)}개는 버전에 ‘초안’으로 표시합니다` : ''}${(st.removed || []).length ? ` · 삭제를 요청한 규칙 ${count(st.removed.length)}개` : ''} · 결정표 규칙은 판정에 쓰이고 규칙 카드는 규칙을 글로 남깁니다`;
    const table = `<section class="k-card" aria-labelledby="smr-rl"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="smr-rl">규칙 카드</h2><span class="k-chip">${count(st.cards.length)}</span><div class="k-push smr-picks">${picks}</div></div>
      <div class="k-x"><table class="k-t s end smr-rules"><colgroup><col style="width:19%"><col><col style="width:14%"><col style="width:18%"><col style="width:10%"><col style="width:13%"></colgroup><thead><tr><th scope="col">ID</th><th scope="col">규칙</th><th scope="col">계층</th><th scope="col">근거</th><th scope="col">버전</th><th scope="col">담당자</th></tr></thead><tbody>${shown.map(tr).join('') || '<tr><td colspan="6" class="mut">조건에 맞는 규칙이 없습니다.</td></tr>'}</tbody></table></div>
      <p class="k-cf">${foot}${cards.length > shown.length ? ` <button class="k-lnk" data-act="smrMore" data-k="more">${count(Math.min(40, cards.length - shown.length))}개 더 보기</button>` : ''}</p></section>`;
    return `${head}${violated}${bar}${strip}<div class="k-cols"><div class="k-c3">${table}${sel ? smrDetail(sel) : ''}</div>${smrSim()}</div>
      <div class="smr-pair"><section class="k-card pad k-v" aria-labelledby="smr-chk" id="smr-checks">${smrChecks(sel)}</section><section class="k-card pad k-v" aria-labelledby="smr-tst" id="smr-tests">${smrTests()}</section></div>
      ${smrValues()}${kNext([['ruleagent', '규칙 초안에서 후보 승인'], ['changes', '변경 요청으로 묶어 배포'], ['flow', '이 규칙으로 검증'], ['actions', '규칙을 전제조건으로 쓰는 액션']])}`;
  }

  function smrDetail(c) {
    const box = (k, v) => `<div class="k-box"><p class="k-hint k-b" style="margin:0">${k}</p><p class="k-14" style="margin:4px 0 0">${v || '-'}</p></div>`;
    const lines = (xs) => (xs || []).map(esc).join('<br>');
    const ref = (r) => `<span class="k-chip${r.found === false ? ' warn' : ''}">${esc(r.label || r.ref)}</span>`;
    const fact = (k, v) => (v ? `<span class="k-s">${k}</span><span class="k-14">${v}</span>` : '');
    const params = Object.entries(c.params || {}).map(([k, v]) => `<span class="k-code">@${esc(k)}</span> ${esc(String(v))}`).join(' · ');
    const check = c.check ? `${esc(c.check.parameter ? `@${c.check.parameter}` : c.check.property)}${c.check.min !== undefined && c.check.min !== null ? ` ${esc(String(c.check.min))} 이상` : ''}${c.check.max !== undefined && c.check.max !== null ? ` ${esc(String(c.check.max))} 이하` : ''}` : '';
    const state = `${esc(c.type_label || c.type)} · <span class="k-chip ${SMR_STATUS[c.status] || ''}">${esc(c.status_label || c.status)}</span>${c.legal_review && c.legal_review !== 'none' ? ` <span class="k-chip">법무 검토 ${esc(c.legal_review_label || c.legal_review)}</span>` : ''}`;
    const where = `${esc(c.module_label || c.module || '-')}${(c.extended_by || []).length ? ` · 확장 ${c.extended_by.map(esc).join(', ')}` : ''}`;
    const facts = [fact('유형 · 상태', state), fact('적용 대상', smrApplies(c).map(esc).join(', ')), fact('기준값', params), fact('위반 시', esc(c.risk || '')), fact('근거 확인', esc(c.verification || '')),
      fact('실행 위치', (c.implements || []).map(ref).join(' ')), fact('사용처', (c.used_by || []).map(ref).join(' ')), fact(c.check && c.check.property ? '값 범위' : 'AXIOM 검사', check), fact('정의한 모듈', where)].join('');
    const open = c.kind === 'executable' ? `<a class="k-lnk flat" href="#mgrules?decision=${encodeURIComponent(c.decision)}">결정표 ${esc(c.decision_label || c.decision)} 편집${ki('chevR', 14, 1.75)}</a>` : '';
    const why = smrEditable(c) ? '' : `<p class="k-s" style="margin:0">${c.layer === 'axiom' ? '결정표의 AXIOM 규칙은 그 규칙을 정의한 모듈에서 바꿉니다. 온톨로지 화면의 모듈 파일 편집에서 고칩니다.' : 'Standard 규칙 카드는 도메인 팩의 모듈에서 정의합니다. 이 화면에서는 Custom 규칙 카드를 만들고 고칩니다.'}</p>`;
    return `<section class="k-card pad k-v g12" aria-labelledby="smr-rc"><div class="k-pha"><span class="k-code k-mut">${esc(c.id)}</span><h2 class="k-h2" id="smr-rc">${esc(c.statement)}</h2>${kLayer(c.layer)}</div>
      <div class="k-g2" style="gap:8px">${box('조건', lines(c.conditions))}${box('결과', esc(c.result || ''))}${box('예외', lines(c.exceptions))}${box('근거 · 버전 · 담당자', [c.source, smrVer(c), c.owner].filter(Boolean).map(esc).join(' · '))}</div>
      <div class="smr-facts">${facts}</div>${open}${why}</section>`;
  }

  // 판정 테스트: values typed in are decided by the table as the pending edits leave it; no source is read unless a record is picked
  function smrSim() {
    const x = S.smr, m = S.mg.st, d = m.decisions.find((t) => t.name === x.dec);
    const none = noSource();
    const top = `<div class="k-h sb nw"><h2 class="k-h2" id="smr-sim">판정 테스트</h2>${none ? '<span class="k-chip ok">연결 없이</span>' : ''}</div><p class="k-s" style="margin:-6px 0 0">값을 직접 넣어 판정합니다. 소스 데이터가 없어도 됩니다.</p>`;
    if (!d) return `<aside class="k-card pad k-v g12 smr-sim" aria-labelledby="smr-sim">${top}<p class="k-note">판정에 쓰는 결정표가 없습니다. 규칙 카드는 규칙을 글로 남기고, 판정은 결정표의 규칙이 합니다.</p>${canEdit() ? '<a class="k-btn" href="#mgrules" style="align-self:flex-start">결정표 만들기</a>' : ''}</aside>`;
    const r = x.res && x.res.name === d.name ? x.res : null;
    const got = Object.fromEntries((r ? r.inputs : []).map((i) => [i.name, i.value]));
    const field = (i) => {
      const cur = x.vals[i.name] ?? (got[i.name] === null || got[i.name] === undefined ? '' : String(got[i.name]));
      const at = `data-in="smrVal" data-k="${esc(i.name)}"`;
      if (i.type === 'boolean') return `<select class="k-in" ${at}><option value="">값 없음</option>${[['true', '예'], ['false', '아니요']].map(([k, l]) => `<option value="${k}"${cur === k ? ' selected' : ''}>${l}</option>`).join('')}</select>`;
      if ((i.values || []).length) return `<select class="k-in" ${at}><option value="">값 없음</option>${i.values.map((v) => `<option value="${esc(v)}"${cur === String(v) ? ' selected' : ''}>${esc((i.labels || {})[v] || v)}</option>`).join('')}</select>`;
      return `<input class="k-in" type="${['integer', 'decimal', 'number'].includes(i.type) ? 'number' : 'text'}" ${at} value="${esc(cur)}" placeholder="값 없음">`;
    };
    const keys = d.target && !none && !d.new ? (S.d.keys[d.target] || []).slice(0, 300) : [];
    const record = d.target && !none && !d.new ? `<label class="k-f">레코드 값 불러오기<select class="k-in" data-in="smrKey" aria-label="레코드"><option value="">직접 입력</option>${keys.map((k) => `<option value="${esc(k.key)}"${k.key === x.key ? ' selected' : ''}>${esc(k.key)}</option>`).join('')}</select></label>` : '';
    return `<aside class="k-card pad k-v g12 smr-sim" aria-labelledby="smr-sim">${top}
      <label class="k-f">결정표<select class="k-in" data-in="smrDec" aria-label="결정표">${m.decisions.map((t) => `<option value="${esc(t.name)}"${t.name === x.dec ? ' selected' : ''}>${esc(t.label)}</option>`).join('')}</select></label>${record}
      <div class="smr-ins">${d.inputs.map((i) => `<label class="k-f">${esc(i.label)}${i.unit ? ` (${esc(i.unit)})` : ''}${field(i)}</label>`).join('')}</div>
      <div id="smr-out" class="k-v g12" aria-live="polite">${smrOut()}</div>
      ${S.sem.st.layers.some((l) => l.layer === 'axiom' && l.rules + l.cards) ? '<p class="smr-reg"><b>등록 검사</b> · AXIOM이 정한 범위를 벗어난 기준값과 AXIOM 규칙을 바꾸는 변경은 저장되지 않습니다</p>' : ''}</aside>`;
  }

  function smrOut() {
    const x = S.smr, r = x.res && x.res.name === x.dec ? x.res : null;
    if (x.simErr) return `<p class="k-note warn">${esc(x.simErr)}</p>`;
    if (!r) return `<p class="k-s" style="margin:0">${x.busy ? '판정 중입니다.' : '값을 넣으면 계층마다 어떤 규칙이 적용되는지 보입니다.'}</p>`;
    const li = (l) => {
      const cls = l.state === 'fired' ? ' fired' : l.state === 'passed' ? ' passed' : ' off';
      const say = l.state === 'fired' ? esc(l.fired.join(', ')) : l.state === 'held' ? `${esc(l.held.join(', '))} · 앞선 규칙이 먼저 적용` : l.rules ? `규칙 ${count(l.rules)}개 · 해당 없음` : '규칙 없음';
      const word = l.state === 'fired' ? `<b class="${r.yes ? 'k-ok' : 'k-warn'}">${esc(r.verdict)}</b>` : l.state === 'passed' ? '<b class="k-ok">통과</b>' : '<span>적용 안 함</span>';
      return `<li class="smr-step${cls}">${kLayer(l.layer)}<span class="k-g">${say}</span>${word}</li>`;
    };
    const path = r.path ? `<ol class="smr-steps">${r.path.layers.map(li).join('')}</ol>` : '';
    const src = r.path && r.path.source;
    const passed = r.path && r.path.layers.some((l) => l.layer === 'axiom' && l.state === 'passed' && l.rules);
    const line = r.error ? esc(r.error) : src ? `§ ${esc(src.module_label || src.module || '')} 규칙 ${esc(src.rule)}${src.version ? ` v${esc(src.version)}` : ''}${src.cite ? ` · ${esc(src.cite)}` : ''}${passed ? ' · AXIOM 검사 통과' : ''}` : '적용된 규칙이 없습니다';
    const other = (r.other || []).length ? `<div class="k-v g4"><span class="k-s">다른 결과가 나오려면</span>${r.other.map((o) => `<span class="k-13">${esc(o.label)} ${typeof o.value === 'boolean' ? yesNo(o.value) : esc(String(o.value))} → <b>${esc(o.verdict)}</b> <span class="k-mut">${esc(o.matched.join(', ') || '적용 규칙 없음')}</span></span>`).join('')}</div>` : '';
    return `${path}<div class="k-v g4 smr-res"><p class="k-13">판정 결과${r.pending ? ' · 작성 중인 변경 반영' : ''}${r.key ? ` · 레코드 ${esc(r.key)}` : ''}</p><p class="smr-verdict"><i class="k-dot${r.yes ? '' : ' no'}" aria-hidden="true"></i>${esc(r.verdict)}</p><p class="smr-src">${line}</p></div>${other}`;
  }

  async function smrRun() {
    const x = S.smr, name = x.dec;
    if (!name) return;
    x.busy = true;
    try { x.res = await api('decide/simulate', { name, key: x.key || '', inputs: x.vals }); x.simErr = ''; } catch (e) { x.simErr = e.message || String(e); x.key = ''; }
    x.busy = false;
    if (S.tab !== 'semrules' || x.dec !== name) return;
    const out = $('#smr-out'), tests = $('#smr-tests');
    if (!out || (x.key && x.res && x.res.key === x.key && !Object.keys(x.vals).length)) { render(); return; }  // a record's values fill the fields
    out.innerHTML = smrOut();
    if (tests) tests.innerHTML = smrTests();
  }

  // 규칙 검사: what the checks of the table found, and which rules overlap the one chosen
  function smrChecks(sel) {
    const x = S.smr, st = S.sem.st, d = S.mg.st.decisions.find((t) => t.name === x.dec);
    const row = (k, chip) => `<div class="k-14 k-h sb nw"><span>${k}</span>${chip}</div>`;
    const axiom = st.checks.length ? row('AXIOM 값 검사', `<span class="k-chip ${st.violations.length ? 'bad' : 'ok'}" title="${esc(st.checks.map((c) => c.said).join(' / '))}">${st.checks.filter((c) => c.passed).length} / ${st.checks.length} 통과</span>`) : '';
    if (!d) return `<h2 class="k-h2" id="smr-chk">규칙 검사</h2>${axiom || '<p class="k-s" style="margin:0">검사할 결정표가 없습니다.</p>'}`;
    const fs = (S.ru.findings || []).filter((f) => f.decision === d.name);
    const n = (k) => fs.filter((f) => f.kind === k).length;
    const tone = (k, soft) => { const c = n(k); return `<span class="k-chip ${c ? (soft ? 'b' : 'warn') : 'ok'}">${c}${c && soft ? ` · ${esc(POLICY_WORD[d.hit_policy] || d.hit_policy)} 우선` : ''}</span>`; };
    const mine = sel && sel.kind === 'executable' && sel.decision === d.name ? [...new Set(fs.filter((f) => ['overlap', 'tie'].includes(f.kind) && f.rules.includes(sel.rule)).flatMap((f) => f.rules).filter((id) => id !== sel.rule))] : null;
    const say = mine === null ? '결정표의 규칙을 고르면 조건이 겹치는 규칙을 표시합니다' : mine.length ? `${sel.rule}와 조건이 겹치는 규칙 · ${mine.join(', ')}` : `${sel.rule}와 조건이 겹치는 규칙이 없습니다`;
    return `<div class="k-h sb"><h2 class="k-h2" id="smr-chk">규칙 검사 · ${esc(d.label)}</h2><a class="k-lnk flat" href="#mgrules?decision=${encodeURIComponent(d.name)}">결정표 편집${ki('chevR', 14, 1.75)}</a></div>
      ${row('중복 조건', tone('overlap', true))}${row('도달 불가 규칙', tone('unreachable'))}${row('빈 구간', tone('gap'))}${row('우선순위 동률', tone('tie'))}${axiom}<p class="k-s" style="margin:0">${esc(say)}</p>`;
  }

  // 테스트: the edges of what the rules compare, the questions asked of this table, the past cases decided again
  function smrTests() {
    const x = S.smr, d = S.mg.st.decisions.find((t) => t.name === x.dec);
    const row = (k, chip) => `<div class="k-14 k-h sb nw"><span>${k}</span>${chip}</div>`;
    const dash = (w) => `<span class="k-chip dash">${w}</span>`;
    if (!d) return '<h2 class="k-h2" id="smr-tst">테스트</h2><p class="k-s" style="margin:0">시험할 결정표가 없습니다.</p>';
    const r = x.res && x.res.name === d.name ? x.res : null;
    const flips = r ? r.edges.filter((e) => e.verdict !== r.verdict).length : 0;
    const qs = r ? r.questions.filter((q) => q.passed !== null) : [], okq = qs.filter((q) => q.passed).length, unasked = r ? r.questions.length - qs.length : 0;
    const a = x.agree && x.agree.ok && x.agree.decision === d.name ? x.agree : null;
    const past = a ? `<span class="k-chip ${a.rate === 1 ? 'ok' : 'warn'}">${count(a.agree)} / ${count(a.cases)} 일치</span>` : noSource() ? dash('연결 후') : dash('과거 기록 없음');
    const edges = r && x.edges ? `<div class="k-x"><table class="k-t s"><thead><tr><th scope="col">입력</th><th scope="col">값</th><th scope="col">결과</th><th scope="col">규칙</th></tr></thead><tbody>${r.edges.map((e) => `<tr><td>${esc(e.label)}</td><td class="k-code">${typeof e.value === 'boolean' ? yesNo(e.value) : esc(String(e.value))}</td><td><span class="k-chip ${e.yes ? 'ok' : 'warn'}">${esc(e.verdict)}</span></td><td class="k-code mut">${esc(e.matched.join(', '))}</td></tr>`).join('')}</tbody></table></div>` : '';
    const failing = qs.filter((q) => !q.passed).map((q) => `<p class="k-note warn" style="font-size:13px"><b>${esc(q.id)}</b> ${esc(q.text)} · 기대 ${esc(JSON.stringify(q.expect || {}))} → 결과 ${esc(q.error || JSON.stringify(q.got || {}))}</p>`).join('');
    return `<h2 class="k-h2" id="smr-tst">테스트</h2>
      ${row('경계값 자동 생성', r ? `<span class="k-h g6 nw"><span class="k-chip">${count(r.edges.length)}건 · 결과가 바뀌는 값 ${count(flips)}</span>${r.edges.length ? `<button class="k-lnk" data-act="smrEdges" aria-expanded="${x.edges}">${x.edges ? '접기' : '보기'}</button>` : ''}</span>` : dash(x.busy ? '실행 중' : '실행 전'))}${edges}
      ${row('이 규칙을 사용하는 검증 질문', r ? (r.questions.length ? `<span class="k-chip ${okq === qs.length ? 'ok' : 'bad'}">${okq} / ${qs.length} 통과${unasked ? ` · 연결 후 ${unasked}` : ''}</span>` : '<span class="k-chip">질문 없음</span>') : dash(x.busy ? '실행 중' : '실행 전'))}${failing}
      ${row('과거 처리 기록 재계산', past)}
      <button class="k-btn" type="button" data-act="smrRerun" style="align-self:flex-start;margin-top:4px"${x.busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}테스트 재실행</button>`;
  }

  // the named values, metrics and functions the rules read, as one list
  function smrValueRows() {
    const m = S.mg.st, of = (mod) => { const r = S.st.library.find((y) => y.name === mod); return r ? `v${r.version}` : ''; };
    const said = Object.fromEntries((S.ru.metrics || []).map((y) => [y.metric, y]));
    const range = (p) => (p.min !== null && p.min !== undefined && p.max !== null && p.max !== undefined ? ` · 범위 ${p.min}~${p.max}` : p.min !== null && p.min !== undefined ? ` · 범위 ${p.min} 이상` : p.max !== null && p.max !== undefined ? ` · 범위 ${p.max} 이하` : '');
    const uses = (xs) => (xs && xs.length ? `${xs.slice(0, 2).join(' · ')}${xs.length > 2 ? ` 외 ${xs.length - 2}` : ''}` : '-');
    const run = (k) => (RUNTIME.find((y) => y[0] === k) || [k, k])[1];
    return m.parameters.map((p) => ({ id: `parameter:${p.name}`, kind: '기준값', code: `@${p.name}`, label: p.label, say: `${show(p.value)}${esc(p.unit || '')}${esc(range(p))}`, uses: uses(p.readers), who: [p.module_label, of(p.module)].filter(Boolean).join(' · '), x: p }))
      .concat(m.metrics.map((y) => ({ id: `metric:${y.name}`, kind: '지표', code: y.name, label: y.label, say: esc(said[y.name] ? `${said[y.name].formula}${said[y.name].denominator ? ` · 분모 ${said[y.name].denominator}` : ''}` : y.description || '-'), uses: y.unit ? `단위 ${y.unit}` : '-', who: [y.owner || y.module_label, of(y.module)].filter(Boolean).join(' · '), x: y })))
      .concat(m.functions.map((f) => ({ id: `function:${f.name}`, kind: '함수', code: f.name, label: f.label, say: esc(`${run(f.runtime)} · ${f.expr || f.decision || f.query || f.entry || (f.call || {}).url || '-'}`), uses: f.target ? `대상 ${mgLabel(f.target)}` : '-', who: [f.owner || f.module_label, f.version ? `v${f.version}` : ''].filter(Boolean).join(' · '), x: f })));
  }

  function smrValues() {
    const x = S.smr, can = canEdit(), rows = smrValueRows();
    if (!x.psel || !rows.some((r) => r.id === x.psel)) x.psel = (rows[0] || {}).id || '';
    const sel = rows.find((r) => r.id === x.psel);
    const bar = sel ? kBar('선택한 기준값 · 지표 · 함수', sel.code, sel.label, itemActs('param', sel.id)) : '';
    const add = (type, word) => `<a class="k-btn" href="#param-form" data-act="smrNew" data-kind="param" data-type="${type}">${ki('plus', 16, 1.75)}${word}</a>`;
    const shown = rows.slice(0, x.pmore);
    const tr = (r) => `<tr class="${r.id === x.psel ? 'on' : ''}" data-act="smrPickValue" data-id="${esc(r.id)}"><td><span class="k-chip">${r.kind}</span>${r.x.new ? ' <span class="k-chip warn">새로 추가</span>' : r.x.pending ? ' <span class="k-chip warn">변경 대기</span>' : ''}</td><td>${esc(r.label)}<br><span class="k-code k-mut">${esc(r.code)}</span></td><td>${r.say}</td><td>${esc(r.uses)}</td><td>${esc(r.who || '-')}</td></tr>`;
    const more = [S.mg.st.metrics.length ? '<a class="k-lnk" href="#rules">지표 계산 · 출처 충돌 보기</a>' : '<a class="k-lnk" href="#rules">출처 충돌 · 기한 전이 보기</a>', S.mg.st.functions.length ? '<a class="k-lnk" href="#mgfuncs">함수 실행해 보기</a>' : ''].join('');
    return `${bar}<section class="k-card" aria-labelledby="smr-prm"><div class="k-pha" style="padding:16px 20px"><h2 class="k-h2" id="smr-prm">기준값 · 지표 · 함수</h2><span class="k-s">규칙이 참조하는 값과 계산</span>${can ? `<div class="k-push k-h">${add('parameter', '기준값')}${add('metric', '지표')}${add('function', '함수')}</div>` : ''}</div>
      <div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">종류</th><th scope="col">이름</th><th scope="col">값 · 산식</th><th scope="col">사용처</th><th scope="col">담당 · 버전</th></tr></thead><tbody>${shown.map(tr).join('') || '<tr><td colspan="5" class="mut">기준값, 지표, 함수가 없습니다.</td></tr>'}</tbody></table></div>
      <p class="k-cf">${count(shown.length)} / ${count(rows.length)}개 표시${rows.length > shown.length ? ` <button class="k-lnk" data-act="smrMore" data-k="pmore">${count(Math.min(30, rows.length - shown.length))}개 더 보기</button>` : ''}${more}</p></section>`;
  }

  function smrRulesAfter() {
    const x = S.smr;
    if (S.it.kind === 'rule' || S.it.kind === 'param') S.it = { key: '' };  // back on the list: a form left open starts again next time
    if (!x.err && !x.loading && !smrReady()) { smrLoad(); return; }
    if (!smrReady()) return;
    const d = S.mg.st.decisions.find((t) => t.name === x.dec);
    if (d && !x.busy && !x.simErr && !(x.res && x.res.name === d.name)) smrRun();
    if (d && !x.agree) { x.agree = { busy: true }; api('agreement?pending=1').then((a) => { x.agree = a; }).catch((e) => { x.agree = { ok: false, error: e.message }; }).finally(() => { const t = $('#smr-tests'); if (t && S.tab === 'semrules') t.innerHTML = smrTests(); }); }
    if (d && d.target && !d.new && !noSource() && !S.d.keys[d.target]) keysFor(d.target).then(() => { if (S.tab === 'semrules') render(); }).catch(() => { S.d.keys[d.target] = []; });
  }

  screen('semrules', { area: 'work', word: '규칙', view: smrRulesView, after: smrRulesAfter });

  // ---- SEM-02 규칙 초안 ---------------------------------------------------------------------------------------------

  const smrDocs = () => ((S.files || {}).definitions || []).flatMap((y) => y.document_list || []);
  // the rules the model drafted in this visit: rows of one table, filed together as one module
  const smrMade = () => (S.pol.res && S.pol.res.ok ? S.pol.res.rules.map((r) => ({ ref: `made:${r.id}`, made: true, id: r.id, state: 'waiting', layer: 'custom', statement: `${S.pol.res.label || S.pol.res.decision} · ${r.id}`,
    conditions: Object.entries(r.when || {}).map(([k, v]) => `${k} ${cellWord(v)}`), result: Object.entries(r.then || {}).map(([k, v]) => `${k === 'reason' ? '사유' : k} ${typeof v === 'boolean' ? yesNo(v) : v}`).join(' · '), exceptions: [], source: r.cite || '', areas: [], verification: '', decidable: false })) : []);

  function smrDraftsView() {
    const x = S.smr, can = canEdit();
    smrFresh();
    const lead = `정책서와 법령에서 만든 규칙 초안(조건 · 결과 · 예외 · 계층)을 검토합니다. 항목마다 근거와 근거 확인 수준이 붙고 반영은 영역 담당자 승인으로만 됩니다.${known('concepts') ? ' 같은 자료에서 나온 개념 후보는 개념 초안에 있습니다.' : ''}`;
    const head = kHead('규칙 초안', lead, `${known('ai') ? `<a class="k-btn" href="#ai">${ki('spark', 16, 1.75)}AI 초안 생성</a>` : ''}${known('concepts') ? `<a class="k-btn" href="#concepts">${ki('nodes', 16, 1.75)}개념 초안 보기</a>` : ''}`);
    if (x.err || (S.sem.st && S.sem.st.error) || (S.mg.st && S.mg.st.error)) return smrFail(head);
    if (!smrReady(true)) return smrWait(head);
    const dr = x.dr, made = smrMade(), n = dr.counts;
    const all = [...made, ...dr.drafts];
    const list = all.filter((r) => r.state === x.drTab);
    if (!x.drSel || !list.some((r) => r.ref === x.drSel)) { x.drSel = (list[0] || {}).ref || ''; x.drEdit = null; }
    const sel = list.find((r) => r.ref === x.drSel);
    const std = n.waiting - dr.axiom;
    const tone = (w) => (/확인$|확인됨|검증/.test(w) && !/필요/.test(w) ? 'ok' : /필요|대조|미확인/.test(w) ? 'warn' : '');
    const top = (xs, k) => {  // the largest few by name, the rest (and what belongs to no Object) as one
      const named = xs.filter((a) => a.word !== '그 밖'), rest = xs.filter((a) => a.word === '그 밖').concat(named.slice(k)).reduce((sum, a) => sum + a.count, 0);
      return `${named.slice(0, k).map((a) => `${esc(a.word)} ${count(a.count)}`).join(' · ')}${rest ? ` · 그 밖 ${count(rest)}` : ''}`;
    };
    const imported = n.waiting ? `<section class="k-card pad smr-imp" aria-labelledby="smr-imp"><div class="k-v g4" style="flex:1 1 420px;min-width:0"><h2 class="k-h2" id="smr-imp">가져온 규칙 초안${dr.modules.length ? ` · ${dr.modules.slice(0, 2).map(esc).join(' · ')}${dr.modules.length > 2 ? ` 외 ${dr.modules.length - 2}` : ''}` : ''}</h2>
        <p class="k-p">규칙 ${count(n.waiting)}건이 검토를 기다립니다.${dr.axiom && std ? ` AXIOM 후보 ${count(dr.axiom)}건은 법무 검토로만 확정하고 Standard · Custom 제안 ${count(std)}건은 영역 담당이 승인합니다.` : dr.axiom ? ` AXIOM 후보 ${count(dr.axiom)}건은 법무 검토로만 확정합니다.` : ` Standard · Custom 제안 ${count(std)}건은 영역 담당이 승인합니다.`}${dr.parameters ? ` 기준값 ${count(dr.parameters)}개가 함께 있습니다.` : ''}</p>
        ${dr.by_area.length ? `<p class="k-s" style="margin:0">${top(dr.by_area, 9)}</p>` : ''}</div>
      <div class="k-wrap g8">${dr.by_verification.slice(0, 4).map((v) => `<span class="k-chip ${tone(v.word)}">${esc(v.word)} ${count(v.count)}</span>`).join('')}<a class="k-btn" href="#semrules">승인된 규칙 보기</a></div></section>` : '';
    const stat = (k, big, sub, warn) => `<div class="k-stat${warn ? ' warn' : ''}" style="flex:1 1 180px"><p class="k-s" style="margin:0">${k}</p><p class="k-big${warn ? ' warn' : ''}">${big}</p><p class="${warn ? 'k-warn k-13' : 'k-s'}" style="margin:4px 0 0">${sub}</p></div>`;
    const total = n.waiting + n.approved + n.rejected + made.length;
    const stats = `<section class="k-wrap" aria-label="규칙 초안 현황">${stat('규칙 초안', count(total), `승인 ${count(n.approved)} · 대기 ${count(n.waiting + made.length)} · 거절 ${count(n.rejected)}`)}${stat('AXIOM 후보', count(dr.axiom), '법무 검토로만 확정')}
      ${stat('문서 간 차이', count(dr.conflicts.length), dr.conflicts.length ? esc(`${dr.conflicts[0].label} · ${dr.conflicts[0].sources.join(' ↔ ')}`) : '출처끼리 다른 값 없음', dr.conflicts.length > 0)}${stat('기존 규칙과 겹침', count(dr.overlaps.length), dr.overlaps.length ? esc(`${dr.overlaps[0].label} · ${dr.overlaps[0].rules.join(', ')}`) : '답이 갈리는 겹침 없음')}</section>`;
    const seg = [['waiting', '대기', n.waiting + made.length], ['approved', '승인', n.approved], ['rejected', '거절', n.rejected]].map(([k, w, c]) => `<button type="button" class="${x.drTab === k ? 'on' : ''}" data-act="smrDrTab" data-k="${k}" aria-pressed="${x.drTab === k}">${w} ${count(c)}</button>`).join('');
    const kindChip = (r) => (r.made ? '<span class="k-chip warn">LLM 초안</span>' : r.layer === 'axiom' ? '<span class="k-chip dk">AXIOM 후보</span>' : `<span class="k-chip b">${esc(r.layer_label || r.layer)} 제안</span>`);
    const mark = (r) => (r.made ? '' : r.layer === 'axiom' ? '<span class="k-chip bad">법무 검토</span>' : r.verification ? `<span class="k-chip ${tone(r.verification)}">${esc(r.verification)}</span>` : `<span class="k-chip">${esc(r.status_label || '')}</span>`);
    const shown = list.slice(0, x.drMore);
    const rows = shown.map((r) => `<button type="button" class="smr-drow${r.ref === x.drSel ? ' on' : ''}" data-act="smrDrPick" data-ref="${esc(r.ref)}"${r.ref === x.drSel ? ' aria-current="true"' : ''}><span class="k-h g6">${kindChip(r)}${mark(r)}</span><b class="k-b">${esc(r.statement)}</b><span class="k-s">${esc([r.source, r.made ? '' : r.module_label].filter(Boolean).join(' · ') || '근거 없음')}</span></button>`).join('')
      || `<p class="k-cf line">${x.drTab === 'waiting' ? '검토를 기다리는 규칙 초안이 없습니다.' : x.drTab === 'approved' ? '작성 중인 변경 요청에 승인한 초안이 없습니다.' : '작성 중인 변경 요청에서 거절한 초안이 없습니다.'}</p>`;
    const nav = `<nav class="k-card" aria-label="규칙 초안 목록" style="flex:1 1 320px;min-width:0"><div style="padding:12px"><div class="k-seg fill" role="group" aria-label="상태">${seg}</div></div>${rows}
      ${list.length > shown.length ? `<p class="k-cf line">${count(shown.length)} / ${count(list.length)}개 표시 <button class="k-lnk" data-act="smrMore" data-k="drMore">${count(Math.min(24, list.length - shown.length))}개 더 보기</button></p>` : ''}</nav>`;
    return `${head}${imported}${smrSources()}${stats}<div class="k-cols">${nav}${smrDraftDetail(sel)}</div>${S.ed && !S.ed.readonly ? editorCard() : ''}
      ${kNext([['ai', 'AI 초안 생성'], ['semrules', '승인한 규칙'], ['concepts', '개념 초안'], ['changes', '변경 요청으로 묶기'], [known('evidence') ? 'evidence' : 'docs', '자료 관리']])}`;
  }

  // 바탕 자료: the documents a draft is made from, or a clause typed in
  function smrSources() {
    const x = S.smr, docs = smrDocs(), can = canEdit(), ask = S.st.ask, res = S.pol.res;
    x.docs = x.docs.filter((d) => docs.some((y) => y.name === d));
    const ready = can && ask && !x.gen && (x.docs.length || x.text.trim());
    const pills = docs.map((d) => `<label class="k-ck pill mid"><input type="checkbox" data-in="smrDoc" value="${esc(d.name)}"${x.docs.includes(d.name) ? ' checked' : ''}>${esc(d.name)}</label>`).join('');
    const nodes = S.st.graph.nodes.filter((nd) => nd.table);
    const typed = `<details class="smr-typed"${x.text ? ' open' : ''}><summary class="k-lnk flat">조항을 직접 입력</summary><div class="k-v" style="padding-top:8px"><textarea class="k-in" rows="6" data-in="smrText" aria-label="정책서 조항" placeholder="제1조 (목적) ...">${esc(x.text)}</textarea>
      <div class="k-h"><label class="k-f" style="flex:0 1 260px">대상 Entity<select class="k-in" data-in="smrTarget"><option value="">자동</option>${nodes.map((nd) => `<option value="${esc(nd.id)}"${nd.id === x.target ? ' selected' : ''}>${esc(nd.label)}</option>`).join('')}</select></label>${S.st.data.policy_sample ? '<button class="k-btn" data-act="smrSample" style="align-self:flex-end">예시 정책서 불러오기</button>' : ''}</div></div></details>`;
    const last = res ? (res.ok ? `<span class="k-s">마지막 생성 · 결정표 ${esc(res.label || res.decision)} · 규칙 ${count(res.rules.length)} · 모델 시도 ${count(res.attempts)}회</span><span class="k-push k-h g6"><span class="k-chip ${res.issues.length ? 'warn' : 'ok'}">${res.issues.length ? `초안 검사 오류 ${res.issues.length}` : '초안 검사 통과'}</span><span class="k-chip warn">조항 LLM 초안</span></span>` : `<span class="k-bad k-13">${esc(res.error)}</span>`)
      : `<span class="k-s">${x.gen ? '초안을 만드는 중입니다. 최대 5분 걸립니다.' : x.genNote ? esc(x.genNote) : '아직 이 화면에서 만든 초안이 없습니다.'}</span>`;
    return `<section class="k-card" aria-labelledby="smr-src"><div class="k-h g12 smr-line"><span class="smr-tile">${ki('doc', 18, 1.75)}</span><div style="flex:1 1 320px;min-width:0"><h2 class="k-h2" id="smr-src">바탕 자료</h2><p class="k-s" style="margin:2px 0 0">규칙 초안은 올린 문서의 조항에서 만듭니다. 만든 초안은 아래 대기 목록에 쌓이고, 승인하면 변경 요청으로 등록됩니다.</p></div>
        ${can ? `<a class="k-btn" href="#catalog">${ki('plus', 16, 1.75)}자료 업로드</a><button class="k-btn" type="button" data-act="smrGen"${ready ? '' : ' disabled'}>${ki('play', 16, 1.75)}${x.gen ? '초안 생성 중' : '선택한 자료로 초안 생성'}</button>` : ''}</div>
      ${ask ? '' : '<p class="k-note" style="margin:12px 20px 0">언어 모델이 연결되어 있지 않아 초안을 새로 만들 수 없습니다. 가져온 초안의 검토와 승인은 그대로 할 수 있습니다. 규칙은 규칙 화면에서 직접 추가합니다.</p>'}
      <div class="k-wrap g8 smr-line" role="group" aria-label="추출할 자료">${pills || '<span class="k-s">올린 문서가 없습니다. 정책서나 규정 문서를 올리면 여기에 나옵니다.</span>'}<a class="k-lnk" href="#${known('evidence') ? 'evidence' : 'docs'}">전체 자료 ${count(docs.length)} · ${known('evidence') ? '근거 지도' : '문서'}에서 관리${ki('chevR', 14, 1.75)}</a></div>
      ${can && ask ? `<div class="smr-line">${typed}</div>` : ''}<div class="k-14 k-h g16" style="padding:12px 20px">${last}</div></section>`;
  }

  function smrDraftDetail(r) {
    const x = S.smr;
    if (!r) return '<section class="k-card pad" style="flex:2 1 520px;min-width:0"><p class="k-p s">왼쪽에서 초안을 고르면 조건, 결과, 예외와 근거가 보입니다.</p></section>';
    const e = x.drEdit && x.drEdit.ref === r.ref ? x.drEdit : null;
    const val = (k, cur) => (e ? e[k] : cur);
    const open = r.decidable && canApprove() && !x.drBusy;
    const lock = r.decidable && canApprove() ? '' : ' readonly';
    const chips = r.made ? `<span class="k-chip warn">LLM 초안</span>${S.pol.res.issues.length ? `<span class="k-chip warn">초안 검사 오류 ${S.pol.res.issues.length}</span>` : '<span class="k-chip ok">초안 검사 통과</span>'}`
      : `<span class="k-chip ${SMR_STATUS[r.status] || ''}">${esc(r.status_label || r.status)}</span>${r.verification ? `<span class="k-chip">${esc(r.verification)}</span>` : ''}${r.legal_review && r.legal_review !== 'none' ? `<span class="k-chip ${r.legal_review === 'pending' ? 'bad' : 'ok'}">법무 검토 ${esc(r.legal_review_label)}</span>` : ''}${r.type_label ? `<span class="k-chip">${esc(r.type_label)}</span>` : ''}`;
    const where = `규칙 초안${r.areas.length ? ` · ${r.areas.map(esc).join(', ')} 영역` : ''} · 계층 제안 ${esc(r.made ? 'Custom' : r.layer_label || r.layer)}`;
    const grounds = r.made ? `<div class="smr-ground"><span class="k-chip warn" style="align-self:flex-start">문서 · LLM</span><b>${esc(r.source || '출처 조항 없음')}</b><span class="k-i3 k-13">언어 모델이 정책서 조항에서 만든 결정표 규칙입니다. 엔진이 입력 속성, 규칙 형식, 출처 조항을 검사했습니다.</span></div>`
      : `<div class="smr-ground"><span class="k-chip${r.verification ? ` ${/필요/.test(r.verification) ? 'warn' : 'b'}` : ''}" style="align-self:flex-start">${esc(r.verification || '근거')}</span><b>${esc(r.source || '근거 없음')}</b><span class="k-i3 k-13">${esc([r.module_label, r.version ? `v${r.version}` : '', r.owner ? `담당 ${r.owner}` : ''].filter(Boolean).join(' · '))}</span>${r.kind === 'executable' ? `<a class="k-13" href="#mgrules?decision=${encodeURIComponent(r.decision)}">결정표에서 열기</a>` : ''}</div>${r.risk ? `<div class="smr-ground"><span class="k-chip" style="align-self:flex-start">위반 시</span><span class="k-i3 k-13">${esc(r.risk)}</span></div>` : ''}`;
    let foot;
    if (r.made) {
      foot = `<span class="k-s" style="flex:1 1 220px">승인하면 결정표 ${esc(S.pol.res.label || S.pol.res.decision)}(규칙 ${count(S.pol.res.rules.length)}개)가 모듈 하나로 변경 요청에 등록됩니다. 규칙 하나만 따로 승인하지 않습니다</span>
        <button class="k-btn" type="button" data-act="smrMadeDrop">거절</button><button class="k-btn" type="button" data-act="smrMadeEdit">수정 후 승인</button><button class="k-btn pri" type="button" data-act="smrMadeFile"${canEdit() && !x.drBusy ? '' : ' disabled'}>승인</button>`;
    } else if (r.state !== 'waiting') {
      foot = `<span class="k-s" style="flex:1 1 220px">${r.state === 'approved' ? '승인해 작성 중인 변경 요청에 담았습니다.' : '거절해 작성 중인 변경 요청에서 뺐습니다.'} 변경 요청을 올리기 전에는 <a href="#changes">변경 요청 · 버전</a>에서 되돌릴 수 있습니다</span>`;
    } else if (r.layer === 'axiom') {
      foot = '<span class="k-s" style="flex:1 1 220px">AXIOM 후보는 법무 검토로만 확정합니다. 검토가 끝나면 axiom 모듈의 새 버전으로 반영하며 이 화면에서는 승인하거나 거절하지 않습니다</span>';
    } else if (!canApprove()) {
      foot = '<span class="k-s" style="flex:1 1 220px">승인과 거절은 영역 담당 이상 역할이 합니다</span>';
    } else {
      foot = `<span class="k-s" style="flex:1 1 220px">승인하면 ${r.kind === 'executable' ? `결정표 규칙 ${esc(r.rule)}` : `규칙 카드 ${esc(r.id)}`}의 상태가 승인으로 바뀌고 다음 버전 변경 요청에 추가됩니다</span>
        <button class="k-btn" type="button" data-act="smrDrDecide" data-v="reject"${open ? '' : ' disabled'}>거절</button><button class="k-btn" type="button" data-act="smrDrDecide" data-v="edit"${open && e ? '' : ' disabled'}>수정 후 승인</button><button class="k-btn pri" type="button" data-act="smrDrDecide" data-v="approve"${open ? '' : ' disabled'}>승인</button>`;
    }
    const fixed = r.made || r.kind === 'executable' ? ' readonly' : lock;
    return `<section class="k-card" aria-labelledby="smr-ad" style="flex:2 1 520px;min-width:0"><div class="k-v smr-part"><p class="k-s" style="margin:0">${where}</p><h2 id="smr-ad" style="margin:0;font-size:20px;font-weight:600">${esc(r.statement)}</h2><div class="k-h g6">${chips}</div></div>
      <div class="smr-part k-g2" style="gap:8px"><label class="k-f">조건<input class="k-in" type="text" data-in="smrDrField" data-k="conditions" value="${esc(val('conditions', (r.conditions || []).join('; ')))}"${fixed}></label>
        <label class="k-f">결과<input class="k-in" type="text" data-in="smrDrField" data-k="result" value="${esc(val('result', r.result || ''))}"${fixed}></label>
        <label class="k-f">예외<input class="k-in" type="text" data-in="smrDrField" data-k="exceptions" value="${esc(val('exceptions', (r.exceptions || []).join('; ')))}"${fixed}></label>
        <label class="k-f">계층<select class="k-in" disabled aria-label="계층"><option>${esc(r.made ? 'Custom' : r.layer_label || r.layer)}</option></select></label></div>
      <div class="k-v smr-part"><p class="k-p b">근거 위치</p><div class="k-wrap">${grounds}</div></div>
      <div class="k-pha" style="padding:16px 20px">${foot}</div></section>`;
  }

  function smrDraftsAfter() {
    const x = S.smr;
    if (!x.err && !x.loading && !smrReady(true)) smrLoad({ drafts: true });
  }

  screen('ruleagent', { area: 'work', word: '규칙 초안', view: smrDraftsView, after: smrDraftsAfter });

  // ---- a rule's own screens ---------------------------------------------------------------------------------------

  const SMR_TYPES = () => ((S.sem.st || {}).types || []).map((t) => [t.type, t.label]);
  const smrTable = (name) => S.mg.st.decisions.find((t) => t.name === name);
  const smrOpt = (k, w, cur) => `<option value="${esc(k)}"${String(k) === String(cur ?? '') ? ' selected' : ''}>${esc(w)}</option>`;
  const smrIn = (k, v, more = '', cls = '') => `<input class="k-in${cls}" type="text" data-in="itf" data-k="${k}" value="${esc(v ?? '')}" ${more}>`;

  function smrRuleDraft(c) {
    if (!c) return { kind: 'stated', isNew: true, id: '', statement: '', type: 'decide', area: '', keep: [], conditions: '', result: '', exceptions: '', source: '', owner: '', params: [], decision: (S.mg.st.decisions[0] || {}).name || '', when: {}, then: {}, first: true, reason: '' };
    if (c.kind === 'executable') {
      const r = (smrTable(c.decision) || { rules: [] }).rules.find((y) => y.id === c.rule) || { when: {}, then: {} };
      return { kind: 'executable', id: c.rule, decision: c.decision, when: JSON.parse(JSON.stringify(r.when || {})), then: { ...(r.then || {}) }, source: r.cite || '', owner: r.owner || '', status: r.status || '', reason: '' };
    }
    const area = (c.applies_to || []).map(String).find((r) => r.startsWith('area:')) || '';
    return { kind: 'stated', id: c.id, statement: c.statement, type: c.type, area: area.slice(5), keep: (c.applies_to || []).filter((r) => !String(r).startsWith('area:')), conditions: (c.conditions || []).join('\n'), result: c.result || '',
      exceptions: (c.exceptions || []).join('; '), source: c.source || '', owner: c.owner || '', params: Object.entries(c.params || {}).map(([name, value]) => ({ name, value })), reason: '' };
  }

  function smrRuleForm(d, c) {
    const m = S.mg.st, fresh = !c;
    const kinds = fresh ? `<div class="k-full k-h g12"><div class="k-seg" role="group" aria-label="규칙의 종류"><button type="button" class="${d.kind === 'stated' ? 'on' : ''}" data-act="smrKind" data-k="stated">규칙 카드</button><button type="button" class="${d.kind === 'executable' ? 'on' : ''}" data-act="smrKind" data-k="executable"${m.decisions.length ? '' : ' disabled'}>결정표 규칙</button></div><span class="k-s">규칙 카드는 규칙을 글로 남깁니다. 결정표 규칙은 판정에 바로 쓰입니다</span></div>` : '';
    const locked = c && !smrEditable(c) ? `<p class="k-note warn k-full">${c.layer === 'axiom' ? '결정표의 AXIOM 규칙은 그 규칙을 정의한 모듈에서 바꿉니다. 온톨로지 화면의 모듈 파일 편집에서 고칩니다.' : 'Standard 규칙 카드는 도메인 팩의 모듈에서 정의합니다. 이 화면에서는 저장할 수 없습니다.'}</p>` : '';
    if (d.kind === 'executable') {
      const t = smrTable(d.decision);
      const conds = t ? t.inputs.map((i) => {
        const part = d.when[i.name] || { op: 'any', value: '' };
        const ops = part.op === 'raw' ? ['raw'] : opsOf(i.type);
        const at = `data-in="smrWhen" data-k="${esc(i.name)}" data-p="value"`;
        const value = ['any', 'null', 'notnull'].includes(part.op) ? '' : i.type === 'boolean' ? `<select class="k-in" ${at}>${[['true', '예'], ['false', '아니요']].map(([k, l]) => smrOpt(k, l, part.value)).join('')}</select>`
          : (i.values || []).length && ['eq', 'ne'].includes(part.op) ? `<select class="k-in" ${at}>${i.values.map((v) => smrOpt(v, (i.labels || {})[v] || v, part.value)).join('')}</select>`
            : `<input class="k-in" type="text" ${at} value="${esc(part.value ?? '')}" placeholder="${esc(cellHint(i, part.op))}">`;
        return `<div class="smr-cond"><span class="k-14">${esc(i.label)}</span><select class="k-in" data-in="smrWhen" data-k="${esc(i.name)}" data-p="op" data-re="1" aria-label="${esc(i.label)} 비교">${ops.map((o) => smrOpt(o, CELL_OPS[o], part.op)).join('')}</select>${value}</div>`;
      }).join('') : '';
      const outs = t ? t.outputs.map((o) => {
        const cur = d.then[o.name], word = outWord(t, o.name);
        return `<label class="k-f">${esc(word)}${o.type === 'boolean' ? `<select class="k-in" data-in="smrThen" data-k="${esc(o.name)}" data-t="boolean"><option value="">선택</option>${[['true', '예'], ['false', '아니요']].map(([k, l]) => smrOpt(k, l, cur === undefined ? '' : String(cur))).join('')}</select>` : `<input class="k-in" type="text" data-in="smrThen" data-k="${esc(o.name)}" data-t="${esc(o.type)}" value="${esc(cur ?? '')}">`}</label>`;
      }).join('') : '';
      return `<section class="k-card" aria-labelledby="smr-f1"><div class="k-ch"><h2 id="smr-f1">기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">${kinds}${locked}
          <label class="k-f">규칙 ID${smrIn('id', d.id, fresh ? 'placeholder="예: gold-window"' : 'disabled')}<span class="k-hint">영문자로 시작하고 영문자 · 숫자 · _ · - 를 씁니다</span></label>
          <label class="k-f">결정표<select class="k-in" data-in="itf" data-k="decision" data-re="1"${fresh ? '' : ' disabled'}>${m.decisions.map((y) => smrOpt(y.name, y.label, d.decision)).join('')}</select><span class="k-hint">규칙이 들어갈 결정표 · 계층은 Custom</span></label>
          <div class="k-full k-v"><span class="k-s">조건</span>${conds || '<span class="k-s">결정표를 고르면 입력마다 조건을 정합니다.</span>'}</div>
          <div class="k-full k-g2"><span class="k-s k-full">결과</span>${outs}</div>
          <label class="k-f">근거 자료 · 절${smrIn('source', d.source, 'placeholder="예: 반품 정책서 v1.2 3조" list="smr-docs"')}<span class="k-hint">근거 지도의 자료에서 선택</span></label>
          <label class="k-f">담당자${smrIn('owner', d.owner, 'list="smr-owners"')}</label>
          ${fresh ? `<label class="k-ck mid k-full"><input type="checkbox" data-in="itf" data-k="first"${d.first ? ' checked' : ''}>기존 규칙보다 먼저 적용</label>` : ''}</div></div>${smrLists()}</section>`;
    }
    // a value a card names is a named value of the definition (it follows that value) or a value written on the card itself
    const linked = d.params.map((y) => { const p = m.parameters.find((q) => q.name === y.name); return `<tr><td class="k-code">${p ? '@' : ''}${esc(y.name)}</td><td>${p ? `${show(p.value)}${esc(p.unit || '')}` : `${show(y.value)} <span class="k-s">카드에 적은 값</span>`}</td><td>${esc(p && p.readers.length ? p.readers.join(' · ') : '-')}</td><td class="r"><button class="k-lnk" type="button" data-act="smrParamDrop" data-name="${esc(y.name)}">삭제</button></td></tr>`; }).join('');
    const free = m.parameters.filter((p) => !d.params.some((y) => y.name === p.name));
    return `<section class="k-card" aria-labelledby="smr-f1"><div class="k-ch"><h2 id="smr-f1">기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">${kinds}${locked}
        <label class="k-f">규칙 ID${smrIn('id', d.id, fresh ? 'placeholder="예: CU-CL-001"' : 'disabled')}<span class="k-hint">영문자로 시작하고 영문자 · 숫자 · _ · - 를 씁니다</span></label>
        <label class="k-f">규칙 이름${smrIn('statement', d.statement)}</label>
        <label class="k-f">계층<select class="k-in" disabled aria-label="계층"><option>${esc(c ? c.layer_label || c.layer : 'Custom')}</option></select><span class="k-hint">이 화면에서 만든 규칙은 Custom 계층 · Standard와 AXIOM은 도메인 팩에서 정의</span></label>
        <label class="k-f">영역<select class="k-in" data-in="itf" data-k="area"><option value="">선택 안 함</option>${(m.areas || []).map((a) => smrOpt(a.name, a.label || a.name, d.area)).join('')}</select></label>
        <div class="k-full"><label class="k-f">조건<textarea class="k-in" rows="3" data-in="itf" data-k="conditions" placeholder="한 줄에 조건 하나">${esc(d.conditions)}</textarea></label></div>
        <div class="k-full"><label class="k-f">결과<textarea class="k-in" rows="3" data-in="itf" data-k="result">${esc(d.result)}</textarea></label></div>
        <label class="k-f">예외${smrIn('exceptions', d.exceptions, 'placeholder="여럿이면 ; 로 구분"')}</label>
        <label class="k-f">근거 자료 · 절${smrIn('source', d.source, 'list="smr-docs"')}<span class="k-hint">근거 지도의 자료에서 선택</span></label>
        <label class="k-f">담당자${smrIn('owner', d.owner, 'list="smr-owners"')}</label>
        <label class="k-f">유형<select class="k-in" data-in="itf" data-k="type">${SMR_TYPES().map(([k, w]) => smrOpt(k, w, d.type)).join('')}</select></label></div></div>${smrLists()}</section>
      <section class="k-card" aria-labelledby="smr-f2"><div class="k-ch"><h2 id="smr-f2">조건에 쓰는 기준값</h2>${free.length ? `<span class="k-push"><select class="smr-pick on" data-in="smrParamAdd" aria-label="기준값 연결"><option value="">+ 기준값 연결</option>${free.map((p) => smrOpt(p.name, `${p.label} @${p.name}`, '')).join('')}</select></span>` : ''}</div>
        <div class="k-x"><table class="k-t"><thead><tr><th scope="col">키</th><th scope="col">값</th><th scope="col">함께 쓰는 규칙</th><th scope="col"></th></tr></thead><tbody>${linked || '<tr><td colspan="4" class="mut">연결한 기준값이 없습니다. 조건의 숫자를 기준값으로 두면 한곳에서 관리합니다.</td></tr>'}</tbody></table></div></section>`;
  }
  // what a person may pick a source and an owner from: the documents of the space and the owners rules already name
  const smrLists = () => `<datalist id="smr-docs">${(S.mg.st.documents || []).map((n) => `<option value="${esc(n)}">`).join('')}</datalist><datalist id="smr-owners">${[...new Set(S.sem.st.cards.map((c) => c.owner).filter(Boolean))].map((n) => `<option value="${esc(n)}">`).join('')}</datalist>`;

  function smrRuleChecks(d, c) {
    const out = [], st = S.sem.st, fresh = !c;
    if (c && !smrEditable(c)) return [{ say: c.layer === 'axiom' ? 'AXIOM 규칙은 이 화면에서 바꿀 수 없음' : 'Standard 규칙 카드는 이 화면에서 바꿀 수 없음', tone: 'bad', word: '저장 불가' }];
    if (d.kind === 'executable') {
      const t = smrTable(d.decision);
      if (fresh) out.push(!d.id ? { say: '규칙 ID 입력 필요', tone: 'warn' } : !/^[A-Za-z_][A-Za-z0-9_-]*$/.test(d.id) ? { say: '규칙 ID는 영문자로 시작하고 영문자 · 숫자 · _ · - 만 사용', tone: 'bad' } : t && t.rules.some((r) => r.id === d.id) ? { say: `${t.label}에 같은 ID의 규칙이 있음`, tone: 'bad' } : { say: '규칙 ID 사용 가능', tone: 'ok' });
      const set = Object.values(d.when || {}).filter((p) => p && p.op && p.op !== 'any').length;
      out.push(set ? { say: `조건 ${set}개`, tone: 'ok' } : { say: '조건 없음 · 다른 규칙에 맞지 않는 모든 경우에 적용', tone: 'note' });
      if (t && !t.outputs.every((o) => d.then[o.name] !== undefined && d.then[o.name] !== '')) out.push({ say: '결과를 모두 입력해야 함', tone: 'warn' });
      const over = c ? [...new Set((S.ru.findings || []).filter((f) => f.decision === d.decision && ['overlap', 'tie'].includes(f.kind) && f.rules.includes(d.id)).flatMap((f) => f.rules).filter((id) => id !== d.id))] : [];
      if (over.length) out.push({ say: `${over.join(', ')}와 조건 겹침 · ${POLICY_WORD[(t || {}).hit_policy] || ''} 적용`, tone: 'note' });
      out.push(d.source ? { say: '근거 자료 입력됨', tone: 'ok' } : { say: '근거 자료 없음', tone: 'warn' });
      const qs = S.st.questions.filter((q) => q.decision === d.decision).length;
      if (qs) out.push({ say: `검증 질문 ${qs}개가 이 결정표를 사용`, tone: 'note' });
      return out;
    }
    if (fresh) out.push(!d.id ? { say: '규칙 ID 입력 필요', tone: 'warn' } : !/^[A-Za-z_][A-Za-z0-9_-]*$/.test(d.id) ? { say: '규칙 ID는 영문자로 시작하고 영문자 · 숫자 · _ · - 만 사용', tone: 'bad' } : st.cards.some((y) => y.kind === 'stated' && y.id === d.id) ? { say: '같은 ID의 규칙 카드가 있음', tone: 'bad' } : { say: '규칙 ID 사용 가능', tone: 'ok' });
    out.push(String(d.statement || '').trim() ? { say: '규칙 이름 입력됨', tone: 'ok' } : { say: '규칙 이름 입력 필요', tone: 'warn' });
    out.push(String(d.source || '').trim() ? { say: '근거 자료 입력됨', tone: 'ok' } : { say: '근거 자료 없음', tone: 'warn' });
    const named = d.params.filter((y) => S.mg.st.parameters.some((p) => p.name === y.name)).length;
    if (named) out.push({ say: `기준값 ${named}개 연결`, tone: 'ok' });
    if (d.params.length - named) out.push({ say: `카드에 적은 값 ${d.params.length - named}개 · 기준값으로 두면 한곳에서 관리`, tone: 'note' });
    return out;
  }

  function smrRuleValid(d, c) {
    if (c && !smrEditable(c)) return c.layer === 'axiom' ? 'AXIOM 규칙은 axiom 모듈에서만 바뀌어 저장하지 못했습니다.' : 'Standard 규칙 카드는 도메인 팩의 모듈에서 정의해 저장하지 못했습니다. Custom 규칙 카드를 새로 만들어 주세요.';
    if (!String(d.id || '').trim()) return '규칙 ID가 비어 있어 저장하지 못했습니다. 규칙 ID를 입력해 주세요.';
    if (d.kind === 'executable') {
      const t = smrTable(d.decision);
      if (!t) return '결정표를 고르지 않아 저장하지 못했습니다. 결정표를 선택해 주세요.';
      if (!t.outputs.every((o) => d.then[o.name] !== undefined && d.then[o.name] !== '')) return '결과가 비어 있어 저장하지 못했습니다. 결과를 모두 입력해 주세요.';
      return '';
    }
    return String(d.statement || '').trim() ? '' : '규칙 이름이 비어 있어 저장하지 못했습니다. 규칙 이름을 입력해 주세요.';
  }

  async function smrRuleSave(d, c) {
    let r, element;
    if (smrAxiomCard(c)) {  // an AXIOM card: its own module's change request, not the edits waiting in the workspace
      const fields = { type: d.type, statement: d.statement.trim(), applies_to: [...(d.area ? [`area:${d.area}`] : []), ...(d.keep || [])], conditions: smrLines(d.conditions), result: String(d.result || '').trim(),
        exceptions: smrLines(d.exceptions), source: String(d.source || '').trim(), owner: String(d.owner || '').trim() };
      r = await api('sem/axiom/card', { id: c.id, fields });
      S.sem.st = null; S.changes = null;
      return { element: `rule_card:${c.id}`, go: `changes?id=${encodeURIComponent(r.change.id)}`, said: SMR_AXIOM_SAID };
    }
    if (d.kind === 'executable') {
      const args = { decision: d.decision, id: d.id.trim(), when: d.when, then: d.then, cite: d.source || '', owner: d.owner || '', ...(d.status ? { status: d.status } : {}) };
      r = await api('manage/edit', c ? { op: 'update_rule', args } : { op: 'add_rule', args: { ...args, first: !!d.first } });
      element = `rule:${d.decision}.${args.id}`;
    } else {
      const params = Object.fromEntries(d.params.map((y) => { const p = S.mg.st.parameters.find((q) => q.name === y.name); return [y.name, p ? p.value : y.value]; }));
      const args = { id: d.id.trim(), type: d.type, statement: d.statement.trim(), applies_to: [...(d.area ? [`area:${d.area}`] : []), ...(d.keep || [])], conditions: smrLines(d.conditions), result: String(d.result || '').trim(),
        exceptions: smrLines(d.exceptions), params, source: String(d.source || '').trim(), owner: String(d.owner || '').trim() };
      r = await api('manage/edit', c ? { op: 'update_rule_card', args } : { op: 'add_rule_card', args: { ...args, status: 'approved' } });
      element = `rule_card:${args.id}`;
    }
    smrEdited(r);
    S.smr.sel = d.kind === 'executable' ? `decision:${d.decision}#${d.id.trim()}` : `card:${d.id.trim()}`;
    return { element };
  }

  async function smrRuleUses(c) {
    if (c.kind === 'executable') return itemUsesOf(ITEM.rule, c);
    const WORD = { decision: '결정표 규칙', function: '함수', action: '액션', object: 'Entity', property: 'Property', link: 'Relation', parameter: '기준값', query: '쿼리', metric: '지표', role: '접근 정책', states: '상태 전이' };
    const TAB = { decision: 'semrules', function: 'semrules', action: 'actions', object: 'objects', property: 'objects', link: 'model', parameter: 'semrules', query: 'query', metric: 'semrules', role: 'roles', states: 'objects' };
    const by = {};
    (c.implements || []).forEach((r) => { (by[r.kind] = by[r.kind] || []).push(r.label || r.ref); });
    const out = Object.entries(by).map(([k, names]) => ({ say: `${WORD[k] || k} ${names.length}개`, sub: `${names.slice(0, 3).join(', ')}${names.length > 3 ? ` 외 ${names.length - 3}` : ''} · 이 규칙의 기록이 사라집니다`, href: TAB[k] || '' }));
    if (c.check && c.check.parameter) out.push({ say: '기준값 1개', sub: `@${c.check.parameter}의 범위를 이 규칙이 정합니다`, href: 'semrules' });
    return out;
  }

  // the history of a card, a named value or a metric, as the item screens draw it
  async function smrHistory(kind, name, word) {
    const r = await api(`sem/history?kind=${kind}&name=${encodeURIComponent(name)}`);
    const WORD = { added: '추가', changed: '변경', removed: '삭제' };
    return r.entries.map((e) => ({ ver: e.version ? `v${e.version}` : '', mark: e.status_label, cp: e.change, at: e.at, who: e.by, deployed: e.deployed,
      say: (e.notes || []).map((n) => n.text).join(' · ') || e.reason || `${word} ${WORD[e.kind] || '변경'}`,
      rows: e.fields.map((f) => ({ label: f.label, before: f.before, after: f.after })), all: Object.entries(e.all || {}).map(([k, v]) => ({ label: k, value: v })) }));
  }

  item('rule', {
    word: '규칙', under: 'semrules', list: 'semrules',
    hint: '규칙에서 ‘+ 규칙 카드’를 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    load: smrLoadItem,
    find: (id) => (S.sem.st && S.sem.st.cards ? S.sem.st.cards.find((c) => c.ref === id) || null : null),
    code: (c) => c.id, name: (c) => c.statement,
    element: (c) => (c.kind === 'executable' ? `rule:${c.decision}.${c.rule}` : `rule_card:${c.id}`),
    draft: smrRuleDraft, form: smrRuleForm, checks: smrRuleChecks, valid: smrRuleValid, save: smrRuleSave,
    uses: smrRuleUses,
    history: (c) => (c.kind === 'executable' ? itemHistoryOf(ITEM.rule, c) : smrHistory('card', c.id, '규칙')),
    saves: (d, c) => (smrAxiomCard(c) ? [['저장 상태', 'AXIOM 모듈의 변경 요청으로 올림'], ['변경 요청', '<a href="#changes">변경 요청 · 버전</a>에 검토 대기로 등록'], ['검토', '승인해야 반영 · AXIOM은 어떤 규칙도 덮어쓸 수 없음'], ['회귀 테스트', '올릴 때 자동 실행']] : null),
    remove: async (c) => {
      if (smrAxiomCard(c)) { const r = await api('sem/axiom/card', { id: c.id, remove: true }); S.sem.st = null; S.changes = null; return { go: `changes?id=${encodeURIComponent(r.change.id)}`, said: SMR_AXIOM_SAID }; }
      if (!smrEditable(c)) throw new Error(c.layer === 'axiom' ? 'AXIOM 규칙은 axiom 모듈에서만 바뀌어 삭제를 요청하지 못했습니다.' : 'Standard 규칙 카드는 도메인 팩의 모듈에서 정의해 삭제를 요청하지 못했습니다.');
      smrEdited(await api('manage/edit', c.kind === 'executable' ? { op: 'delete_rule', args: { decision: c.decision, id: c.rule } } : { op: 'delete_rule_card', args: { id: c.id } }));
    },
  });

  // ---- a named value's, a metric's, a function's own screens -------------------------------------------------------

  const SMR_VALUE = { parameter: '기준값', metric: '지표', function: '함수' };
  const smrValueOf = (id) => { const [kind, ...rest] = String(id).split(':'), name = rest.join(':'), m = S.mg.st; const x = ({ parameter: m.parameters, metric: m.metrics, function: m.functions }[kind] || []).find((y) => y.name === name); return x ? { kind, name, x } : null; };

  function smrValueDraft(v) {
    const first = (S.mg.st.objects.find((o) => !o.concept) || {}).name || '';
    if (!v) {
      const kind = S.smr.newKind || 'parameter';
      if (kind === 'metric') return { kind, isNew: true, name: '', label: '', owner: '', object: first, fn: 'count', prop: '', where: [], den: [], ratio: false, den_label: '', unit: '', scale: 1, basis: '', time_prop: '', description: '', cite: '', reason: '' };
      if (kind === 'function') return { kind, isNew: true, name: '', label: '', runtime: 'expr', target: first, expr: '', decision: '', query: '', entry: '', url: '', method: 'POST', path: '', fin: [], fout: [{ name: 'value', type: 'decimal' }], version: '1.0.0', owner: '', status: 'draft', depends: '', description: '', cite: '', reason: '' };
      return { kind: 'parameter', isNew: true, name: '', label: '', type: 'integer', value: '', unit: '', min: '', max: '', description: '', cite: '', reason: '' };
    }
    const y = v.x;
    if (v.kind === 'metric') {
      const match = y.formula.match || {}, alias = Object.keys(match)[0], where = condRows(y.formula.where), den = condRows((y.denominator || {}).where), agg = aggOf(y.formula);
      const raw = Object.keys(match).length !== 1 || where === null || den === null || !!y.formula.edges;
      return { kind: 'metric', raw, name: y.name, label: y.label, owner: y.owner || '', object: match[alias] || '', fn: agg.fn, prop: agg.prop, where: where || [], den: den || [], ratio: !!Object.keys(y.denominator || {}).length, den_label: (y.denominator || {}).label || '',
        unit: y.unit || '', scale: y.scale, basis: (y.time || {}).basis || '', time_prop: String((y.time || {}).property || '').split('.').pop(), description: y.description || '', cite: y.cite || '', reason: '' };
    }
    if (v.kind === 'function') {
      return { kind: 'function', name: y.name, label: y.label, runtime: y.runtime, target: y.target || '', expr: y.expr || '', decision: y.decision || '', query: y.query || '', entry: y.entry || '', url: (y.call || {}).url || '', method: (y.call || {}).method || 'POST', path: (y.call || {}).path || '', call: y.call || {},
        fin: Object.entries(y.inputs || {}).map(([name, s]) => ({ name, label: (s || {}).label || '', type: (s || {}).type || 'string' })), fout: Object.entries(y.outputs || {}).map(([name, type]) => ({ name, type })),
        version: y.version || '', owner: y.owner || '', status: y.status || 'active', depends: (y.depends || []).join(', '), description: y.description || '', cite: y.cite || '', reason: '' };
    }
    return { kind: 'parameter', name: y.name, label: y.label, type: y.type, value: y.value ?? '', unit: y.unit || '', min: y.min ?? '', max: y.max ?? '', description: y.description || '', cite: y.cite || '', reason: '' };
  }

  const smrRowsOf = (list, rows, cols) => `<div class="k-v">${rows.map((r, i) => `<div class="smr-row">${cols(r, i)}<button class="k-lnk" type="button" data-act="smrRowDel" data-list="${list}" data-i="${i}" aria-label="행 삭제">삭제</button></div>`).join('')}<button class="k-lnk flat" type="button" data-act="smrRowAdd" data-list="${list}">${ki('plus', 16, 1.75)}행 추가</button></div>`;
  const smrRowIn = (list, i, f, v, hold) => `<input class="k-in" type="text" data-in="smrRow" data-list="${list}" data-i="${i}" data-f="${f}" value="${esc(v ?? '')}" placeholder="${esc(hold)}" aria-label="${esc(hold)}">`;
  const smrRowSel = (list, i, f, options, v, label) => `<select class="k-in" data-in="smrRow" data-list="${list}" data-i="${i}" data-f="${f}" aria-label="${esc(label)}">${options.map(([k, w]) => smrOpt(k, w, v)).join('')}</select>`;

  function smrValueForm(d, v) {
    const m = S.mg.st, fresh = !v;
    const kind = `<label class="k-f">종류<select class="k-in" data-in="smrNewKind" aria-label="종류"${fresh ? '' : ' disabled'}>${Object.entries(SMR_VALUE).map(([k, w]) => smrOpt(k, w, d.kind)).join('')}</select></label>`;
    const key = (hint) => `<label class="k-f">키${smrIn('name', fresh ? d.name : (d.kind === 'parameter' ? `@${d.name}` : d.name), fresh ? 'placeholder="영문 이름"' : 'disabled')}<span class="k-hint">${hint}</span></label>`;
    const name = `<label class="k-f">이름${smrIn('label', d.label)}</label>`;
    const tail = `<div class="k-full"><label class="k-f">설명<textarea class="k-in" rows="3" data-in="itf" data-k="description">${esc(d.description)}</textarea></label></div>`;
    const cite = `<label class="k-f">근거 자료 · 절${smrIn('cite', d.cite, 'list="smr-docs"')}</label>`;
    let body;
    if (d.kind === 'metric') {
      const props = [['', '대상 자체'], ...mgProps(d.object).map((p) => [p.name, p.label || p.name])];
      const conds = (list) => smrRowsOf(list, d[list], (r, i) => `${smrRowSel(list, i, 'property', props.slice(1), r.property, '속성')}${smrRowSel(list, i, 'op', WHERE_OPS, r.op, '비교')}${smrRowIn(list, i, 'value', r.value, '값')}`);
      const formula = d.raw ? '<p class="k-note k-full">산식이 여러 Entity를 잇고 있어 대상과 조건은 온톨로지 화면의 모듈 편집에서 고칩니다.</p>' : `
        <label class="k-f">대상 Entity<select class="k-in" data-in="itf" data-k="object" data-re="1">${m.objects.filter((o) => !o.concept).map((o) => smrOpt(o.name, o.label, d.object)).join('')}</select></label>
        <div class="k-g2"><label class="k-f">집계<select class="k-in" data-in="itf" data-k="fn">${AGG_WORD.map(([k, w]) => smrOpt(k, w, d.fn)).join('')}</select></label><label class="k-f">집계 속성<select class="k-in" data-in="itf" data-k="prop">${props.map(([k, w]) => smrOpt(k, w, d.prop)).join('')}</select></label></div>
        <div class="k-full k-v"><span class="k-s">값 · 산식의 조건</span>${conds('where')}</div>
        <label class="k-ck mid k-full"><input type="checkbox" data-in="itf" data-k="ratio" data-re="1"${d.ratio ? ' checked' : ''}>분모로 나누어 비율로 표시</label>
        ${d.ratio ? `<div class="k-full k-v"><span class="k-s">분모 조건</span>${conds('den')}</div><label class="k-f">분모 이름${smrIn('den_label', d.den_label)}</label>` : ''}`;
      body = `${kind}${key('검증 질문과 API에서 이 키로 참조')}${name}<label class="k-f">담당자${smrIn('owner', d.owner, 'list="smr-owners"')}</label>${formula}
        <label class="k-f">단위${smrIn('unit', d.unit, 'list="smr-units"')}</label><label class="k-f">배율${smrIn('scale', d.scale)}<span class="k-hint">백분율은 100</span></label>
        <label class="k-f">기준 시각${smrIn('basis', d.basis, 'placeholder="예: 주문 일시"')}</label>${d.raw ? '' : `<label class="k-f">기준 시각 속성<select class="k-in" data-in="itf" data-k="time_prop"><option value="">없음</option>${mgProps(d.object).filter((p) => ['date', 'datetime'].includes(p.type)).map((p) => smrOpt(p.name, p.label || p.name, d.time_prop)).join('')}</select></label>`}${tail}${cite}`;
    } else if (d.kind === 'function') {
      const types = TYPES.filter((t) => t !== 'enum').map((t) => [t, TYPE_WORD[t]]);
      const by = { expr: `<div class="k-full"><label class="k-f">값 · 산식${smrIn('expr', d.expr, 'placeholder="예: line_total * @rate"', ' mono')}<span class="k-hint">대상 Entity의 속성을 이름으로, 입력값을 @이름으로 참조합니다</span></label></div>`,
        decision: `<label class="k-f">결정표<select class="k-in" data-in="itf" data-k="decision"><option value="">선택</option>${m.decisions.map((y) => smrOpt(y.name, y.label, d.decision)).join('')}</select></label>`,
        query: `<label class="k-f">등록 쿼리<select class="k-in" data-in="itf" data-k="query"><option value="">선택</option>${m.queries.map((q) => smrOpt(q.name, q.label, d.query)).join('')}</select></label>`,
        python: `<label class="k-f">등록 이름${smrIn('entry', d.entry)}<span class="k-hint">설치 환경의 studio 파일 functions.python에 등록한 이름입니다</span></label>`,
        http: `<div class="k-full"><label class="k-f">호출 주소${smrIn('url', d.url, 'placeholder="https://service.example/score/$key"', ' mono')}<span class="k-hint">허용한 호스트만 호출합니다. $key, $row.속성, $입력값을 참조합니다</span></label></div>
          <label class="k-f">방식<select class="k-in" data-in="itf" data-k="method">${['POST', 'GET'].map((y) => smrOpt(y, y, d.method)).join('')}</select></label><label class="k-f">응답 경로${smrIn('path', d.path, 'placeholder="예: data"')}</label>` }[d.runtime] || '';
      body = `${kind}${key('액션과 API에서 이 키로 참조')}${name}<label class="k-f">담당자${smrIn('owner', d.owner, 'list="smr-owners"')}</label>
        <label class="k-f">실행 방식<select class="k-in" data-in="itf" data-k="runtime" data-re="1">${RUNTIME.map(([k, w]) => smrOpt(k, w, d.runtime)).join('')}</select></label>
        <label class="k-f">대상 Entity<select class="k-in" data-in="itf" data-k="target"><option value="">없음</option>${m.objects.filter((o) => !o.concept).map((o) => smrOpt(o.name, o.label, d.target)).join('')}</select></label>${by}
        <div class="k-full k-v"><span class="k-s">입력값</span>${smrRowsOf('fin', d.fin, (r, i) => `${smrRowIn('fin', i, 'name', r.name, '영문 이름')}${smrRowIn('fin', i, 'label', r.label, '이름')}${smrRowSel('fin', i, 'type', types, r.type, '자료형')}`)}</div>
        <div class="k-full k-v"><span class="k-s">출력값</span>${smrRowsOf('fout', d.fout, (r, i) => `${smrRowIn('fout', i, 'name', r.name, '영문 이름')}${smrRowSel('fout', i, 'type', types, r.type, '자료형')}`)}</div>
        <label class="k-f">버전${smrIn('version', d.version)}</label><label class="k-f">상태<select class="k-in" data-in="itf" data-k="status">${FN_STATUS.map(([k, w]) => smrOpt(k, w, d.status)).join('')}</select></label>
        <label class="k-f">외부 의존${smrIn('depends', d.depends, 'placeholder="쉼표로 구분"')}</label>${cite}${tail}`;
    } else {
      const ax = ((S.sem.st.parameters || []).find((p) => p.name === d.name) || {}).axiom;
      const bound = ax ? `AXIOM ${ax.min !== null && ax.min !== undefined ? `하한 ${ax.min}보다 작게` : ''}${ax.min !== null && ax.min !== undefined && ax.max !== null && ax.max !== undefined ? ', ' : ''}${ax.max !== null && ax.max !== undefined ? `상한 ${ax.max}보다 크게` : ''} 저장할 수 없음` : '';
      body = `${kind}${key('규칙 조건에서 이 키로 참조')}${name}
        <label class="k-f">값 · 산식${smrIn('value', d.value)}</label>
        ${fresh ? `<label class="k-f">자료형<select class="k-in" data-in="itf" data-k="type">${[['integer', '정수'], ['decimal', '소수'], ['string', '문자열'], ['boolean', '참 · 거짓']].map(([k, w]) => smrOpt(k, w, d.type)).join('')}</select></label>` : ''}
        <label class="k-f">단위${smrIn('unit', d.unit, 'list="smr-units"')}</label>
        <div class="k-f"><span>허용 범위</span><div class="k-h nw">${smrIn('min', d.min, 'placeholder="최솟값" aria-label="최솟값" inputmode="decimal"')}<span class="k-s">~</span>${smrIn('max', d.max, 'placeholder="최댓값" aria-label="최댓값" inputmode="decimal"')}</div>${bound ? `<span class="k-hint">${esc(bound)}</span>` : ''}</div>${tail}${cite}`;
    }
    return `<section class="k-card" aria-labelledby="smr-v1"><div class="k-ch"><h2 id="smr-v1">기본 정보</h2><span class="k-s">* 표시 없는 항목도 모두 저장 전 검사를 거칩니다</span></div><div class="k-cb"><div class="k-g2">${body}</div></div>
      ${smrLists()}<datalist id="smr-units">${['일', '원', '%', '건', '회', '개'].map((u) => `<option value="${u}">`).join('')}</datalist></section>`;
  }

  function smrValueChecks(d, v) {
    const out = [], m = S.mg.st;
    if (!v) {
      const taken = ({ parameter: m.parameters, metric: m.metrics, function: m.functions }[d.kind] || []).some((y) => y.name === d.name);
      out.push(!d.name ? { say: '키 입력 필요', tone: 'warn' } : !IDENT.test(d.name) ? { say: '키는 영문자로 시작하고 영문자 · 숫자 · _ 만 사용', tone: 'bad' } : taken ? { say: `같은 키의 ${SMR_VALUE[d.kind]}이 있음`, tone: 'bad' } : { say: '키 사용 가능', tone: 'ok' });
    }
    if (d.kind === 'parameter') {
      const num = ['integer', 'decimal', 'number'].includes(d.type), val = Number(d.value), has = (y) => y !== '' && y !== null && y !== undefined;
      const ax = ((S.sem.st.parameters || []).find((p) => p.name === d.name) || {}).axiom;
      if (!has(d.value)) out.push({ say: '값 입력 필요', tone: 'warn' });
      else if (num && Number.isNaN(val)) out.push({ say: '값은 숫자여야 함', tone: 'bad' });
      else if (num) {
        const low = has(d.min) && val < Number(d.min), high = has(d.max) && val > Number(d.max);
        out.push(low || high ? { say: `허용 범위 밖의 값 · ${low ? `${d.min} 이상` : `${d.max} 이하`}이어야 함`, tone: 'bad' } : { say: '허용 범위 안의 값', tone: 'ok' });
        if (ax) { const under = has(ax.min) && val < ax.min, over = has(ax.max) && val > ax.max; out.push(under || over ? { say: `AXIOM 규칙 ${ax.cards.join(', ')}의 ${under ? `하한 ${ax.min}` : `상한 ${ax.max}`}을 벗어남`, tone: 'bad' } : { say: `AXIOM 규칙 ${ax.cards.join(', ')}의 범위 안`, tone: 'ok' }); }
      }
      const readers = v ? v.x.readers || [] : [];
      if (readers.length) out.push({ say: `이 키를 쓰는 규칙 ${readers.length}개 · 값이 바뀌면 함께 다시 검증`, sub: readers.slice(0, 3).join(' · '), tone: 'note' });
    }
    if (d.kind === 'metric' && !d.raw) out.push(d.object ? { say: `대상 ${mgLabel(d.object)} · ${(AGG_WORD.find((a) => a[0] === d.fn) || [0, d.fn])[1]}`, tone: 'ok' } : { say: '대상 Entity 선택 필요', tone: 'warn' });
    if (d.kind === 'function') out.push({ expr: d.expr, decision: d.decision, query: d.query, python: d.entry, http: d.url }[d.runtime] ? { say: '실행 내용 입력됨', tone: 'ok' } : { say: '실행 내용 입력 필요', tone: 'warn' });
    out.push(String(d.label || '').trim() ? { say: '이름 입력됨', tone: 'ok' } : { say: '이름 입력 필요', tone: 'warn' });
    return out;
  }

  function smrValueValid(d) {
    if (!String(d.name || '').trim()) return '키가 비어 있어 저장하지 못했습니다. 키를 입력해 주세요.';
    if (!String(d.label || '').trim()) return '이름이 비어 있어 저장하지 못했습니다. 이름을 입력해 주세요.';
    if (d.kind === 'parameter' && (d.value === '' || d.value === null || d.value === undefined)) return '값이 비어 있어 저장하지 못했습니다. 값을 입력해 주세요.';
    return '';
  }

  async function smrValueSave(d, v) {
    const name = String(d.name).trim(), num = (y) => (y === '' || y === null || y === undefined ? null : Number(y));
    let op, args;
    if (d.kind === 'metric') {
      args = { name, label: d.label, owner: d.owner, unit: d.unit || '', scale: Number(d.scale) || 1, description: d.description || '', cite: d.cite || '' };
      if (d.raw) args.time = { ...((v && v.x.time) || {}), basis: d.basis };
      else {
        const al = 'x', ref = d.prop ? `${al}.${d.prop}` : al, where = condSpec(d.where, al), den = condSpec(d.den, al);
        args.formula = { match: { [al]: d.object }, ...(where ? { where } : {}), value: { [d.fn]: ref } };
        args.denominator = d.ratio ? { ...(den ? { where: den } : {}), value: { count: al }, ...(d.den_label ? { label: d.den_label } : {}) } : {};
        args.time = { basis: d.basis, ...(d.time_prop ? { property: `${al}.${d.time_prop}` } : {}) };
      }
      op = v ? 'update_metric' : 'add_metric';
    } else if (d.kind === 'function') {
      const inputs = Object.fromEntries(d.fin.filter((p) => p.name).map((p) => [p.name, { type: p.type || 'string', label: p.label || p.name }]));
      const outputs = Object.fromEntries(d.fout.filter((p) => p.name).map((p) => [p.name, p.type || 'string']));
      const by = { expr: { expr: d.expr }, decision: { decision: d.decision }, query: { query: d.query }, python: { entry: d.entry }, http: { call: { ...(d.call || {}), url: d.url, method: d.method, ...(d.path ? { path: d.path } : {}) } } }[d.runtime] || {};
      args = { name, label: d.label, runtime: d.runtime, target: d.target || '', inputs, outputs, version: d.version, owner: d.owner || '', status: d.status, description: d.description || '', cite: d.cite || '',
        depends: String(d.depends || '').split(',').map((y) => y.trim()).filter(Boolean), expr: '', decision: '', query: '', entry: '', call: {}, ...by };
      op = v ? 'update_function' : 'add_function';
    } else {
      const meta = { label: d.label || '', unit: d.unit || '', description: d.description || '', cite: d.cite || '', min: num(d.min), max: num(d.max) };
      args = v ? { name, value: d.value, ...meta } : { name, type: d.type, value: d.value, ...meta };
      op = v ? 'update_parameter' : 'add_parameter';
    }
    smrEdited(await api('manage/edit', { op, args }));
    S.smr.psel = `${d.kind}:${name}`;
    return { element: `${d.kind}:${name}` };
  }

  item('param', {
    word: '기준값 · 지표 · 함수', under: 'semrules', list: 'semrules',
    hint: '규칙에서 ‘+ 기준값’을 누르면 추가 화면이, 항목의 ‘편집’을 누르면 편집 화면이 열립니다',
    lead: { form: '기준값 · 지표 · 함수를 새로 만들거나 고칩니다. 저장한 내용은 변경 요청에 담기고 승인과 배포를 거쳐야 운영 버전에 반영됩니다.', history: '기준값 · 지표 · 함수 하나를 언제 누가 어떻게 바꿨는지 봅니다. 기록은 지워지지 않고 변경 요청 · 버전에서 이전 버전으로 되살릴 수 있습니다.' },
    load: smrLoadItem,
    find: smrValueOf,
    code: (v) => (v.kind === 'parameter' ? `@${v.name}` : v.name), name: (v) => v.x.label,
    element: (v) => `${v.kind}:${v.name}`,
    draft: smrValueDraft, form: smrValueForm, checks: smrValueChecks, valid: smrValueValid, save: smrValueSave,
    uses: async (v) => {
      if (v.kind === 'function') return itemUsesOf(ITEM.param, v);
      const readers = v.kind === 'parameter' ? v.x.readers || [] : [];
      return readers.length ? [{ say: `규칙 · 계산 ${readers.length}개`, sub: `${readers.slice(0, 3).join(', ')}${readers.length > 3 ? ` 외 ${readers.length - 3}` : ''} · 이 값을 읽는 조건을 먼저 바꿔야 삭제됩니다`, href: 'semrules' }] : [];
    },
    history: (v) => (v.kind === 'function' ? itemHistoryOf(ITEM.param, v) : smrHistory(v.kind, v.name, SMR_VALUE[v.kind])),
    remove: async (v) => { smrEdited(await api('manage/edit', { op: `delete_${v.kind}`, args: { name: v.name } })); },
  });

  // ---- what is pressed and typed ------------------------------------------------------------------------------------

  let smrTimer = 0;
  Object.assign(ACT, {
    smrRetry: () => { S.smr.err = ''; if (S.sem.st && S.sem.st.error) S.sem.st = null; if (S.mg.st && S.mg.st.error) S.mg.st = null; render(); },
    smrPick: (t) => { S.smr.sel = t.dataset.ref; render(); },
    smrPickValue: (t) => { S.smr.psel = t.dataset.id; render(); },
    smrLayer: (t) => { S.smr.layer = S.smr.layer === t.dataset.k ? '' : t.dataset.k; S.smr.more = 40; render(); },
    smrMore: (t) => { const k = t.dataset.k; S.smr[k] += { pmore: 30, drMore: 24 }[k] || 40; render(); },
    smrEdges: () => { S.smr.edges = !S.smr.edges; const b = $('#smr-tests'); if (b) b.innerHTML = smrTests(); },
    smrRerun: async () => {
      const x = S.smr;
      S.ru = null; x.agree = null; x.res = null; x.simErr = '';
      try { S.ru = await api('rules'); } catch (e) { fail(e); S.ru = { findings: [], metrics: [], conflicts: [] }; }
      render();
    },
    smrNew: (t) => {  // a new item starts from an empty form, whatever was typed into the last one
      S.it = { key: '' };
      if (t.dataset.type) S.smr.newKind = t.dataset.type;
      location.hash = `#${t.dataset.kind}-form`;
    },
    smrKind: (t) => { const d = S.it.d; if (!d) return; d.kind = t.dataset.k; render(); },
    smrParamDrop: (t) => { const d = S.it.d; if (!d) return; d.params = d.params.filter((y) => y.name !== t.dataset.name); render(); },
    smrRowAdd: (t) => { const d = S.it.d; if (!d) return; d[t.dataset.list].push(t.dataset.list === 'fin' ? { name: '', label: '', type: 'string' } : t.dataset.list === 'fout' ? { name: '', type: 'decimal' } : { property: (mgProps(d.object)[0] || {}).name || '', op: 'eq', value: '' }); render(); },
    smrRowDel: (t) => { const d = S.it.d; if (!d) return; d[t.dataset.list].splice(Number(t.dataset.i), 1); render(); },
    smrDrTab: (t) => { Object.assign(S.smr, { drTab: t.dataset.k, drSel: '', drEdit: null, drMore: 12 }); render(); },
    smrDrPick: (t) => { S.smr.drSel = t.dataset.ref; S.smr.drEdit = null; render(); },
    smrDrDecide: async (t) => {
      const x = S.smr, r = x.dr.drafts.find((y) => y.ref === x.drSel), how = t.dataset.v;
      if (!r || x.drBusy) return;
      const e = how === 'edit' && x.drEdit && x.drEdit.ref === r.ref ? x.drEdit : null;
      const fields = e ? { conditions: smrLines(e.conditions), result: e.result.trim(), exceptions: smrLines(e.exceptions) } : {};
      x.drBusy = true; render();
      try {
        x.dr = await api('sem/draft/decide', { ref: r.ref, verdict: how === 'reject' ? 'reject' : 'approve', fields });
        Object.assign(x, { drEdit: null, drSel: '', res: null, agree: null, ws: '' });
        S.sem.st = null; S.mg.st = null; S.ru = null;
        toast(how === 'reject' ? '거절했습니다. 작성 중인 변경 요청에서 이 규칙을 뺍니다.' : '승인했습니다. 작성 중인 변경 요청에 담겼습니다.');
      } catch (err) { fail(err); }
      x.drBusy = false; render();
    },
    smrSample: async () => {
      try { const r = await api('policy/sample', {}); if (!r.ok) throw new Error(r.error); S.smr.text = r.text; render(); } catch (e) { fail(e); }
    },
    smrGen: async () => {
      const x = S.smr;
      if (x.gen) return;
      x.gen = true; x.genNote = ''; S.pol.res = null; render();
      try {
        let text = x.text.trim(), cut = false;
        for (const name of x.docs) {
          const d = await api('policy/document', { name, section: '' });
          if (!d.ok) throw new Error(d.error);
          text += `${text ? '\n\n' : ''}[${name}]\n${d.text}`;
          cut = cut || d.cut;
        }
        let r = await api('policy/draft', { text, target: x.target });
        const { job } = r;
        while (job && (r.job || r.running)) {  // the model works on the server; the page collects the draft
          await new Promise((done) => setTimeout(done, 2000));
          r = await api('policy/draft/result', { job });
        }
        S.pol.res = r;
        if (r.ok) { Object.assign(x, { drTab: 'waiting', drSel: `made:${(r.rules[0] || {}).id || ''}`, drEdit: null }); if (cut) toast('문서가 길어 앞부분만 사용했습니다. 조항을 직접 입력하면 그 조항만 사용합니다.'); }
      } catch (e) { S.pol.res = { ok: false, error: e.message || String(e) }; }
      x.gen = false;
      if (S.tab === 'ruleagent') render();
    },
    smrMadeDrop: () => { S.pol.res = null; S.ed = null; S.smr.drSel = ''; S.smr.genNote = '만든 초안을 거절했습니다.'; render(); },
    smrMadeEdit: () => {
      const r = S.pol.res;
      S.ed = { name: '', label: r.label, applied: false, isNew: true, text: r.yaml, check: null, busy: false };
      S.change = null;
      render();
      requestAnimationFrame(() => { const e = $('#editor'); if (e) e.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    },
    smrMadeFile: async () => {
      const x = S.smr, r = S.pol.res;
      if (!r || x.drBusy) return;
      x.drBusy = true; render();
      try {
        const out = await api('module/propose', { text: r.yaml, apply: true });
        S.pol.res = null; S.ed = null; S.changes = null;
        S.st = await api('state');
        x.genNote = `결정표 ${r.label || r.decision}을 변경 요청 ${out.change.id}로 등록했습니다.`;
        toast(out.change.passed ? `변경 요청 ${out.change.id}로 등록했습니다. 변경 요청 · 버전에서 검토합니다.` : `변경 요청 ${out.change.id}로 등록했습니다. 통과하지 못한 조건이 있어 검토가 필요합니다.`, !out.change.passed);
      } catch (e) { fail(e); }
      x.drBusy = false; render();
    },
  });

  Object.assign(INPUT, {
    smrArea: (t) => { S.smr.area = t.value; S.smr.more = 40; render(); },
    smrLayerPick: (t) => { S.smr.layer = t.value; S.smr.more = 40; render(); },
    smrDec: (t) => { Object.assign(S.smr, { dec: t.value, vals: {}, key: '', res: null, simErr: '', agree: null, decFor: S.smr.sel }); render(); },
    smrKey: (t) => { Object.assign(S.smr, { key: t.value, vals: {}, simErr: '' }); smrRun(); },
    smrVal: (t) => {
      const x = S.smr;
      if (!Object.keys(x.vals).length && x.res) x.res.inputs.forEach((i) => { if (i.value !== null && i.value !== undefined) x.vals[i.name] = String(i.value); });  // a record's values stay as the start
      x.vals[t.dataset.k] = t.value;
      x.key = '';
      clearTimeout(smrTimer);
      smrTimer = setTimeout(smrRun, t.tagName === 'SELECT' ? 0 : 350);
    },
    smrDoc: (t) => { const x = S.smr; x.docs = t.checked ? [...new Set([...x.docs, t.value])] : x.docs.filter((d) => d !== t.value); render(); },
    smrText: (t) => { const was = !!S.smr.text.trim(); S.smr.text = t.value; if (was !== !!t.value.trim()) { const b = $('[data-act=smrGen]'); if (b) b.disabled = !(canEdit() && S.st.ask && !S.smr.gen && (S.smr.docs.length || t.value.trim())); } },
    smrTarget: (t) => { S.smr.target = t.value; },
    smrDrField: (t) => {
      const x = S.smr, r = x.dr.drafts.find((y) => y.ref === x.drSel);
      if (!r) return;
      const was = x.drEdit && x.drEdit.ref === r.ref;
      if (!was) x.drEdit = { ref: r.ref, conditions: (r.conditions || []).join('; '), result: r.result || '', exceptions: (r.exceptions || []).join('; ') };
      x.drEdit[t.dataset.k] = t.value;
      if (!was) { const b = $('[data-act=smrDrDecide][data-v=edit]'); if (b) b.disabled = false; }
    },
    smrNewKind: (t) => { S.smr.newKind = t.value; S.it.d = smrValueDraft(null); render(); },
    smrParamAdd: (t) => { const d = S.it.d, p = S.mg.st.parameters.find((q) => q.name === t.value); if (!d || !p) return; d.params.push({ name: p.name, value: p.value }); render(); },
    smrWhen: (t) => {
      const d = S.it.d;
      if (!d) return;
      const part = d.when[t.dataset.k] = d.when[t.dataset.k] || { op: 'any', value: '' };
      part[t.dataset.p] = t.value;
      if (t.dataset.p === 'op') {
        const i = (smrTable(d.decision) || { inputs: [] }).inputs.find((y) => y.name === t.dataset.k);
        if (['any', 'null', 'notnull'].includes(t.value)) part.value = '';
        else if (i && i.type === 'boolean' && !['true', 'false'].includes(String(part.value))) part.value = 'true';
        else if (i && (i.values || []).length && ['eq', 'ne'].includes(t.value) && !i.values.map(String).includes(String(part.value))) part.value = String(i.values[0]);
        render();
        return;
      }
      const box = $('#itchecks');
      if (box) box.innerHTML = itemChecks(ITEM.rule, S.it);
    },
    smrThen: (t) => {
      const d = S.it.d;
      if (!d) return;
      const v = t.value;
      d.then[t.dataset.k] = t.dataset.t === 'boolean' ? (v === '' ? '' : v === 'true') : ['integer', 'decimal', 'number'].includes(t.dataset.t) && v !== '' && !Number.isNaN(Number(v)) ? Number(v) : v;
      const box = $('#itchecks');
      if (box) box.innerHTML = itemChecks(ITEM.rule, S.it);
    },
    smrRow: (t) => { const d = S.it.d; if (d && d[t.dataset.list][Number(t.dataset.i)]) d[t.dataset.list][Number(t.dataset.i)][t.dataset.f] = t.value; },
  });
