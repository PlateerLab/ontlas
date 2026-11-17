  // ==== Quality (검증 질문 · 검증) and two screens of Operations (파이프라인 관제 · 근거 지도) ======================
  // The questions and what they measure come from the definition (S.mg.st.questions) and the check (S.qa, the same
  // answer the older 검증 tab kept); the pass conditions from the flow (S.fl, S.flset); the board from S.mon.st.

  S.qa2 = { set: 'dev', sel: '', pd: null, pdOf: '', imp: null, result: '', edit: false, ranAt: '', busy: false,
    ask: { text: '', busy: false, res: null, fb: '' }, attempt: { sig: '', busy: false, res: null, timer: 0 },
    scene: false, log: null, monTimer: 0, monBusy: false, steps: false, ev: null, evBusy: false, docWant: '', secWant: '', gapN: 0, hitOf: '' };

  const QA_TYPE = { definition: '정의형', decision: '판정형', value: '값 조회형' };
  const QA_GRADING = { match: '판정 일치', keywords: '키워드 포함', evidence: '근거 포함', llm: 'LLM 심사' };
  // a question on what a word means is held right by match when its answer says every word of the expected answer
  const qaGrades = (definition) => (definition ? { ...QA_GRADING, match: '정답 포함' } : QA_GRADING);
  // the grading a question has when none is chosen: by its keywords when it asks what a word means and has some
  const qaGradeOf = (d) => d.grading || (d.via === '' && csv(d.keywords).length ? 'keywords' : 'match');
  const QA_NONE = '값 없음';
  const qaWait = (say) => `<section class="k-card pad"><p class="k-p s">${esc(say)}</p></section>`;
  const qaUntil = (ok) => new Promise((done) => { const t = setInterval(() => { if (ok()) { clearInterval(t); done(); } }, 60); });
  const qaHm = (at) => (at ? String(at).slice(11, 16) : '');
  const qaWhen = (at) => (at ? `${String(at).slice(5, 10).replace('-', '/')} ${String(at).slice(11, 16)}` : '');
  const qaDash = (word, title = '') => `<span class="k-chip dash"${title ? ` title="${esc(title)}"` : ''}>${esc(word)}</span>`;
  // why a condition or an answer is not measured, by the reason the server names
  const QA_UNMEASURED = { no_source: '데이터 소스 미연결', needs_model: 'LLM 심사' };
  const qaNote = (g) => QA_UNMEASURED[g.unmeasured] || '';
  // a value as a row says it: a count of rows, a verdict's results, a list of words
  function qaSay(v) {
    if (v === null || v === undefined || v === '') return '-';
    if (typeof v === 'number') return `${count(v)}행`;
    if (typeof v === 'boolean') return v ? '예' : '아니요';
    if (Array.isArray(v)) return v.map((x) => (x && typeof x === 'object' ? JSON.stringify(x) : String(x))).join(', ') || '-';
    if (typeof v === 'object') {
      const ks = Object.keys(v);
      if (ks.length === 1 && ks[0] === 'rows') return `${count(v.rows)}행`;
      return ks.map((k) => `${k} ${v[k] === true ? '예' : v[k] === false ? '아니요' : v[k] === null ? QA_NONE : typeof v[k] === 'object' ? JSON.stringify(v[k]) : v[k]}`).join(' · ') || '-';
    }
    const s = String(v);
    return s.length > 90 ? `${s.slice(0, 90)}…` : s;
  }
  const qaQuestions = () => (S.mg.st && !S.mg.st.error ? S.mg.st.questions || [] : []);
  const qaFind = (id) => qaQuestions().find((q) => q.id === id) || null;
  // what a question asks, whatever type it is filed under: a decision table, a registered query, or what a word means
  const qaVia = (q) => (q.decision ? 'decision' : q.query ? 'query' : '');
  // whether it can be measured as things stand, and the word for it when it cannot
  function qaWaits(q) {
    if (q.grading === 'llm') return ['측정 제외', 'LLM 심사'];
    if (qaVia(q) === 'query' && noSource()) return ['연결 필요', '데이터 소스 미연결'];
    if (qaVia(q) === 'decision' && noSource() && !Object.keys(q.values || {}).length) return ['연결 필요', '데이터 소스 미연결 · 판정 값 없음'];
    return null;
  }
  // the Object a question is about: the one its decision's target Entity is filed under
  function qaObjectOf(q) {
    const m = S.mg.st, dec = q.decision && (S.st.decisions || []).find((d) => d.name === q.decision);
    const o = dec && m && m.objects ? m.objects.find((x) => x.name === dec.target) : null;
    return o ? (o.area_label || o.label) : '';
  }
  const qaVersion = () => { const l = (S.st.layers.find((x) => x.kind === 'domain') || S.st.layers[0] || { modules: [] }).modules[0]; return l ? `v${l.version}` : ''; };
  async function qaManage() {  // the definition, once: the menu may already be reading it
    if (S.mg.st && !S.mg.st.error) return;
    if (S.mg.busy) await qaUntil(() => !S.mg.busy);
    if (!S.mg.st || S.mg.st.error) await loadManage();
  }

  // ---- a question as a form holds it ------------------------------------------------------------------------------
  // One flat object: the engine of the item screens writes d[key] for an input with data-in="itf" data-k="key".
  // A decision's values are v:<input>, its expected results e:<output>.
  function qaDraft(q) {
    const d0 = (S.st.decisions || [])[0], q0 = (S.st.queries || [])[0];
    if (!q) {
      const type = itemParam('type') || (d0 ? 'decision' : 'definition');
      return { id: '', type, viaOf: type, via: type === 'decision' ? 'decision' : type === 'value' ? ((S.st.queries || []).length ? 'query' : 'decision') : '', text: itemParam('text'), decision: itemParam('decision') || (d0 ? d0.name : ''), key: itemParam('key'),
        query: q0 ? q0.name : '', params: '', rows: '', expectjson: '', answer: '', keywords: '', grading: '', holdout: '', owner: '', reason: '' };
    }
    const str = (v) => (v === null ? 'null' : String(v));
    const d = { id: q.id, type: q.type, viaOf: q.type, via: qaVia(q), text: q.text, decision: q.decision || (d0 ? d0.name : ''), key: q.key || '', query: q.query || (q0 ? q0.name : ''),
      params: q.params && Object.keys(q.params).length ? JSON.stringify(q.params) : '', rows: '', expectjson: '', answer: '',
      keywords: (q.keywords || []).join(', '), grading: q.grading || '', holdout: q.holdout ? '1' : '', owner: q.owner || '', reason: '' };
    const e = q.expect;
    if (q.decision) {
      Object.entries(q.values || {}).forEach(([k, v]) => { d[`v:${k}`] = str(v); });
      Object.entries(e && typeof e === 'object' && !Array.isArray(e) ? e : {}).forEach(([k, v]) => { d[`e:${k}`] = str(v); });
    } else if (q.query) {
      if (e && typeof e === 'object' && !Array.isArray(e) && Object.keys(e).length === 1 && 'rows' in e) d.rows = String(e.rows);
      else if (e && (Array.isArray(e) ? e.length : typeof e === 'object' ? Object.keys(e).length : true)) d.expectjson = JSON.stringify(e);
    } else d.answer = Array.isArray(e) ? e.join(', ') : typeof e === 'string' ? e : '';
    return d;
  }

  const qaDecision = (name) => (S.st.decisions || []).find((x) => x.name === name) || null;
  function qaTyped(raw, type) {  // '' is not given; 값 없음 is given as none
    const s = String(raw ?? '').trim();
    if (s === '') return undefined;
    if (s === 'null' || s === QA_NONE) return null;
    if (type === 'boolean') return s === 'true' || s === '예';
    if (['integer', 'decimal', 'number'].includes(type)) return Number(s.replace(/,/g, ''));
    return s;
  }
  // the draft as the server takes it, or what stops it: { args } | { error, kind, field } (kind: a field left empty or
  // one written in a form the server cannot read). A decision question may give some of its inputs and leave the rest
  // to its record or to the table's defaults, as the server takes it.
  function qaArgs(d) {
    const out = { id: (d.id || '').trim(), type: d.type, text: (d.text || '').trim(), grading: d.grading || '', holdout: d.holdout === '1' || d.holdout === true,
      keywords: csv(d.keywords), owner: (d.owner || '').trim() };
    const miss = (field, error) => ({ error, field, kind: '필수 항목 누락' }), malformed = (field, error) => ({ error, field, kind: '형식 오류' });
    if (!out.text) return miss('질문', '질문이 없어 저장하지 못했습니다. 질문을 입력해 주세요.');
    if (out.grading === 'keywords' && !out.keywords.length) return miss('키워드', '키워드가 없어 저장하지 못했습니다. 키워드를 하나 이상 입력해 주세요.');
    const byWords = out.keywords.length && ['keywords', 'evidence'].includes(out.grading);
    if (d.via === 'decision') {
      const dec = qaDecision(d.decision);
      if (!dec) return miss('결정표', '결정표가 선택되지 않아 저장하지 못했습니다. 결정표를 선택해 주세요.');
      const values = {}, expect = {}, fields = [];
      for (const i of dec.inputs || []) { const x = qaTyped(d[`v:${i.name}`], i.type); fields.push([i.label, x]); if (x !== undefined) values[i.name] = x; }
      for (const o of dec.outputs || []) { const x = qaTyped(d[`e:${o.name}`], o.type); fields.push([`정답 · ${o.name}`, x]); if (x !== undefined) expect[o.name] = x; }
      const nan = fields.find(([, x]) => typeof x === 'number' && Number.isNaN(x));
      if (nan) return malformed(nan[0], `${nan[0]} 값이 숫자가 아니어서 저장하지 못했습니다. 숫자를 입력해 주세요.`);
      const key = (d.key || '').trim();
      if (!key && !Object.keys(values).length) return miss('판정 값 · 레코드 키', '판정 값과 레코드 키가 모두 비어 있어 저장하지 못했습니다. 판정 값 또는 레코드 키를 입력해 주세요.');
      if (!Object.keys(expect).length && !byWords) return miss('정답', '정답이 없어 저장하지 못했습니다. 정답 판정 결과를 하나 이상 입력해 주세요.');
      return { args: { ...out, decision: dec.name, key, values, expect } };
    }
    if (d.via === 'query') {
      if (!d.query) return miss('질의', '질의가 선택되지 않아 저장하지 못했습니다. 등록된 질의를 선택해 주세요.');
      let params = {}, expect = {};
      const said = 'Parameter가 JSON 객체 형식이 아니어서 저장하지 못했습니다. {"이름": "값"} 형식으로 입력해 주세요.';
      try { params = (d.params || '').trim() ? JSON.parse(d.params) : {}; } catch (_) { return malformed('Parameter', said); }
      if (!params || typeof params !== 'object' || Array.isArray(params)) return malformed('Parameter', said);  // the server takes names and values only
      if ((d.expectjson || '').trim()) { try { expect = JSON.parse(d.expectjson); } catch (_) { return malformed('정답', '정답이 JSON 형식이 아니어서 저장하지 못했습니다. JSON 형식으로 입력해 주세요.'); } }
      else if ((d.rows || '').trim() !== '') {
        expect = { rows: Number(String(d.rows).replace(/,/g, '')) };
        if (!Number.isInteger(expect.rows) || expect.rows < 0) return malformed('기대 행 수', '기대 행 수가 0 이상의 정수가 아니어서 저장하지 못했습니다. 0 이상의 정수를 입력해 주세요.');
      } else if (!byWords) return miss('정답', '정답이 없어 저장하지 못했습니다. 기대 행 수를 입력해 주세요.');
      return { args: { ...out, query: d.query, params, expect } };
    }
    const words = csv(d.answer);
    if (!words.length && !out.keywords.length) return miss('정답', '정답이 없어 저장하지 못했습니다. 정답 또는 키워드를 입력해 주세요.');
    return { args: { ...out, type: 'definition', expect: words.length === 1 ? words[0] : words } };
  }

  // the fields of what is asked and what is expected: the same in the item form and (by `inp`) in the list's side
  // panel, which shows the expected answer only
  function qaAskFields(d, inp, only = false) {
    const sel = (k, options, cur, re = false) => `<select class="k-in" data-in="${inp}" data-k="${esc(k)}"${re ? ' data-re' : ''}>${options.map(([v, w]) => opt(v, w, cur)).join('')}</select>`;
    const control = (key, i, cur, expected) => {
      if (i.type === 'boolean') return sel(key, [['', expected ? '확인 안 함' : '입력 안 함'], ['true', '예'], ['false', '아니요'], ...(expected ? [] : [['null', QA_NONE]])], cur);
      if (i.values && i.values.length) return sel(key, [['', '입력 안 함'], ...i.values.map((x) => [String(x), (i.labels || {})[x] || String(x)]), ['null', QA_NONE]], cur);
      const num = ['integer', 'decimal', 'number'].includes(i.type);
      return `<input class="k-in" type="text" data-in="${inp}" data-k="${esc(key)}" value="${esc(cur ?? '')}"${num || i.days_since ? ' inputmode="decimal"' : ''} placeholder="${expected ? '확인 안 함' : i.days_since ? '일 수' : num ? '숫자' : ''}">`;
    };
    if (d.via === 'decision') {
      const dec = qaDecision(d.decision);
      const hint = (i) => (i.param ? '판정 Parameter' : '');
      const ins = dec ? dec.inputs.map((i) => `<label class="k-f">${esc(i.label)}${control(`v:${i.name}`, i, d[`v:${i.name}`], false)}${hint(i) ? `<span class="k-hint">${esc(hint(i))}</span>` : ''}</label>`).join('') : '';
      const outs = dec ? (dec.outputs || []).map((o) => `<label class="k-f"><span>정답 · <span class="k-code">${esc(o.name)}</span></span>${control(`e:${o.name}`, { ...o, values: [] }, d[`e:${o.name}`], true)}</label>`).join('') : '';
      if (only) return outs;
      return `<label class="k-f">결정표${sel('decision', (S.st.decisions || []).map((x) => [x.name, x.label]), d.decision, true)}</label>
        <label class="k-f">레코드 키<input class="k-in" type="text" data-in="${inp}" data-k="key" value="${esc(d.key)}" placeholder="예: I1001"></label>
        ${ins ? `<div class="k-full qa-group"><p class="k-s">판정 값</p><div class="k-g2">${ins}</div></div>` : ''}
        ${outs ? `<div class="k-full qa-group"><p class="k-s">정답</p><div class="k-g2">${outs}</div></div>` : ''}`;
    }
    if (d.via === 'query') {
      const answer = (d.expectjson || '').trim() ? `<div class="k-full"><label class="k-f">정답<textarea class="k-in mono" rows="3" data-in="${inp}" data-k="expectjson">${esc(d.expectjson)}</textarea><span class="k-hint">JSON 형식</span></label></div>`
        : `<label class="k-f">기대 행 수<input class="k-in" type="text" inputmode="numeric" data-in="${inp}" data-k="rows" value="${esc(d.rows)}" placeholder="예: 2"></label>`;
      if (only) return answer;
      return `<label class="k-f">질의${sel('query', (S.st.queries || []).map((x) => [x.name, x.label]), d.query)}</label>
        <label class="k-f">Parameter<input class="k-in mono" type="text" data-in="${inp}" data-k="params" value="${esc(d.params)}" placeholder='예: {"customer": "C001"}'></label>${answer}`;
    }
    return `<div class="k-full"><label class="k-f">정답<textarea class="k-in" rows="3" data-in="${inp}" data-k="answer">${esc(d.answer)}</textarea><span class="k-hint">쉼표로 구분</span></label></div>`;
  }

  function qaFormCard(d, x) {
    // what a question asks follows its type; a value question asks a registered query unless 조회 대상 says otherwise
    if (d.viaOf !== d.type) { d.via = d.type === 'decision' ? 'decision' : d.type === 'definition' ? '' : (S.st.queries || []).length ? 'query' : 'decision'; d.viaOf = d.type; }
    const o = (v, w, cur) => opt(v, w, cur), grades = qaGrades(d.via === '');
    const types = [['definition', '정의형'], ...((S.st.decisions || []).length ? [['decision', '판정형']] : []), ...((S.st.queries || []).length || (S.st.decisions || []).length ? [['value', noSource() ? '값 조회형 · 연결 필요' : '값 조회형']] : [])];
    const via = d.type === 'value' && (S.st.queries || []).length && (S.st.decisions || []).length
      ? `<label class="k-f">조회 대상<select class="k-in" data-in="itf" data-k="via" data-re>${o('query', '등록된 질의', d.via)}${o('decision', '결정표', d.via)}</select></label>` : '';
    const words = ['keywords', 'evidence'].includes(d.grading) || d.via === '' || (d.keywords || '').trim();
    return `<section class="k-card"><div class="k-ch"><h2>기본 정보</h2></div><div class="k-cb"><div class="k-g2">
        <label class="k-f">질문 ID<input class="k-in mono${x ? ' qa-ro' : ''}" type="text" data-in="itf" data-k="id" value="${esc(d.id)}"${x ? ' readonly' : ' placeholder="자동 부여"'}></label>
        <label class="k-f">유형<select class="k-in" data-in="itf" data-k="type" data-re>${types.map(([v, w]) => o(v, w, d.type)).join('')}</select></label>
        <div class="k-full"><label class="k-f">질문<textarea class="k-in" rows="3" data-in="itf" data-k="text">${esc(d.text)}</textarea></label></div>
        ${via}${qaAskFields(d, 'itf')}
        <label class="k-f">평가 방법<select class="k-in" data-in="itf" data-k="grading" data-re>${o('', `기본 · ${grades[qaGradeOf({ ...d, grading: '' })]}`, d.grading)}${Object.entries(grades).map(([k, w]) => o(k, w, d.grading)).join('')}</select></label>
        <label class="k-f">세트<select class="k-in" data-in="itf" data-k="holdout">${o('', '개발 세트', d.holdout)}${o('1', '보류 세트', d.holdout)}</select></label>
        ${words ? `<label class="k-f">키워드<input class="k-in" type="text" data-in="qaKw" data-k="keywords" value="${esc(d.keywords)}" placeholder="예: 14일, 고객센터"><span class="k-hint">쉼표로 구분</span></label>` : ''}
        <label class="k-f">담당<input class="k-in" type="text" data-in="itf" data-k="owner" value="${esc(d.owner)}" placeholder="예: 클레임 담당"></label>
      </div></div></section>`;
  }

  // the question tried on the definition as it stands, while the form is being filled: asked a moment after the last key
  function qaAttempt(d) {
    const t = S.qa2.attempt, a = qaArgs(d);
    if (a.error) return null;
    const sig = JSON.stringify({ ...a.args, id: '', owner: '', holdout: false });
    if (t.sig === sig) return t;
    clearTimeout(t.timer);
    Object.assign(t, { sig, busy: true, res: null });
    t.timer = setTimeout(async () => {
      let res;
      try { res = await api('qa/question/try', a.args); } catch (e) { res = { ok: false, error: e.message }; }
      if (t.sig !== sig) return;
      Object.assign(t, { busy: false, res });
      const box = $('#itchecks');
      if (box && S.it.kind === 'question' && S.it.d === d) box.innerHTML = itemChecks(ITEM.question, S.it);
    }, 500);
    return t;
  }

  // the grading a question has when none is chosen follows its keywords: its word in the list is said again as they are
  // typed, without drawing the field anew (that would end the typing)
  function qaGradeDefault(d) {
    const o = $('#main select[data-in="itf"][data-k="grading"] option[value=""]');
    if (o) o.textContent = `기본 · ${qaGrades(d.via === '')[qaGradeOf({ ...d, grading: '' })]}`;
  }

  function qaFormChecks(d, x) {
    const out = [], a = qaArgs(d);
    out.push(a.error ? { say: `${a.kind} · ${a.field}`, sub: a.error.split('. ').slice(-1)[0], tone: 'bad' } : { say: '필수 항목 입력됨', tone: 'ok' });
    const same = qaQuestions().find((q) => q.id !== (x ? x.id : '') && q.text.replace(/\s+/g, '') === (d.text || '').replace(/\s+/g, '') && (d.text || '').trim());
    out.push(same ? { say: `중복 질문 · ${same.id}`, tone: 'warn' } : { say: '중복 질문 없음', tone: 'ok' });
    if (!x && (d.id || '').trim() && qaFind(d.id.trim())) out.push({ say: `질문 ID 중복 · ${d.id.trim()}`, tone: 'bad' });
    if (a.error) return out;
    const t = qaAttempt(d);
    if (!t || t.busy || !t.res) out.push({ say: '현재 버전 답 확인 중', tone: 'note', word: '확인 중' });
    else if (!t.res.ok || t.res.error) out.push({ say: '현재 버전 답 확인 실패', sub: t.res.error, tone: 'warn' });
    else if (!t.res.measured) out.push({ say: '측정 제외', sub: qaNote(t.res), tone: 'note' });
    else if (t.res.passed) out.push({ say: '현재 버전 정답', sub: t.res.grounded ? '근거 · 출처 · 버전 포함' : `근거 부족 · ${(t.res.gaps || []).join(', ')}`, tone: t.res.grounded ? 'ok' : 'note' });
    else out.push({ say: `현재 버전 오답 · 기대 ${qaSay(t.res.expected)} · 실제 ${qaSay(t.res.got)}`, tone: 'warn', word: '확인 필요' });
    return out;
  }

  // a field of a question as the screens name it, and its value in the same words the form uses
  const QA_FIELD = { id: '질문 ID', text: '질문', expect: '정답', type: '유형', grading: '평가 방법', holdout: '세트', keywords: '키워드', owner: '담당', decision: '결정표', key: '레코드 키', query: '질의', params: 'Parameter', values: '판정 값' };
  const qaFieldWord = (f) => { const [head, ...rest] = String(f).split('.'); return `${QA_FIELD[head] || head}${rest.length ? ` · ${rest.join('.')}` : ''}`; };
  function qaFieldSay(f, v, definition = false) {
    const head = String(f).split('.')[0];
    if (head === 'holdout') return v ? '보류 세트' : '개발 세트';
    if (v === null || v === undefined || v === '') return v;
    if (head === 'type') return QA_TYPE[v] || v;
    if (head === 'grading') return qaGrades(definition)[v] || v;
    if (head === 'decision') return (qaDecision(v) || { label: v }).label;
    if (head === 'query') return ((S.st.queries || []).find((q) => q.name === v) || { label: v }).label;
    if (typeof v === 'boolean') return v ? '예' : '아니요';
    return Array.isArray(v) ? v.join(', ') : v;
  }
  async function qaHistory(x) {
    const r = await api('item/history?element=' + encodeURIComponent(`question:${x.id}`));
    const WORD = { added: '추가', changed: '변경', removed: '삭제' };
    const flat = (o, pre = '') => Object.entries(o || {}).flatMap(([k, v]) => (v && typeof v === 'object' && !Array.isArray(v) ? flat(v, `${pre}${k}.`) : [[`${pre}${k}`, v]]));
    const def = x.type === 'definition';
    return r.entries.map((e) => ({ ver: e.version ? `v${e.version}` : '', mark: e.status_label, cp: e.change, at: e.at, who: e.by, deployed: e.deployed, raw: e.after,
      say: (e.notes || []).map((n) => n.text).join(' · ') || e.reason || `검증 질문 ${WORD[e.kind] || '변경'}`,
      rows: e.fields.map((f) => ({ label: qaFieldWord(f.field), before: qaFieldSay(f.field, f.before, def), after: qaFieldSay(f.field, f.after, def) })),
      all: flat(e.after || e.before).filter(([k]) => k !== 'id').map(([k, v]) => ({ label: qaFieldWord(k), value: qaFieldSay(k, v, def) })) }));
  }

  item('question', {
    word: '검증 질문', under: 'check', list: 'check',
    load: qaManage,
    find: (id) => qaFind(id), code: (x) => x.id, name: (x) => x.text, element: (x) => `question:${x.id}`,
    draft: (x) => qaDraft(x),
    form: (d, x) => qaFormCard(d, x),
    checks: (d, x) => qaFormChecks(d, x),
    valid: (d) => qaArgs(d).error || '',
    save: async (d, x) => {
      const r = await api('qa/question/save', { ...qaArgs(d).args, new: !x });
      S.mg.st = r; S.qa2.sel = r.id; S.qa2.pdOf = '';
      const q = qaFind(r.id);
      if (q) S.qa2.set = q.holdout ? 'holdout' : 'dev';
      return { element: r.element };
    },
    uses: async (x) => {
      // the accuracy target it is measured against: as measured when the flow is at hand, else as set (a module may raise it)
      const n = qaQuestions().length, gate = qaGate('check', 'min_accuracy');
      let goal = gate ? gateValue(gate, gate.limit) : '';
      if (!gate) {
        try {
          const f = await api('flow/settings'), up = (f.raised || []).find((g) => g.stage === 'check' && g.condition === 'min_accuracy');
          const v = up ? up.value : ((f.settings.gates || {}).check || {}).min_accuracy;
          if (v !== undefined && v !== null) goal = pct(v);
        } catch (_) { /* the count alone */ }
      }
      return [{ say: '검증 결과', sub: '다음 실행부터 제외', href: 'flow' },
        { say: '통과 조건', sub: `질문 수 ${n} → ${n - 1}${goal ? ` · 정답률 목표 ${goal}` : ''}`, href: 'flow' }];
    },
    remove: async (x) => { S.mg.st = await api('manage/edit', { op: 'delete_question', args: { id: x.id } }); S.qa2.sel = ''; S.qa2.pdOf = ''; },
    history: qaHistory,
    revert: async (x, e) => {
      if (!e.raw) throw new Error('선택한 시점에 질문이 없어 되돌리지 못했습니다. 다른 시점을 선택해 주세요.');
      const was = qaDraft({ ...e.raw, type: e.raw.type || (e.raw.decision ? 'decision' : e.raw.query ? 'value' : 'definition'), values: e.raw.values || {}, keywords: e.raw.keywords || [], grading: e.raw.grading || '' });
      try { S.mg.st = await api('qa/question/save', { ...qaArgs(was).args, id: x.id }); } catch (err) {
        // the point picked reads as the question does now: the version in use, or a point it has been set back to
        if (/변경된 내용이 없어/.test(err.message)) throw new Error('선택한 시점의 값이 현재 값과 같아 되돌리지 못했습니다. 이전 시점을 선택해 주세요.');
        throw err;
      }
      S.qa2.pdOf = '';
    },
  });

  // ---- QA-01 검증 질문 -------------------------------------------------------------------------------------------

  function qaPanel(q) {
    if (S.qa2.pdOf !== q.id) { S.qa2.pd = qaDraft(q); S.qa2.pdOf = q.id; }
    const d = S.qa2.pd, edit = canEdit(), off = edit ? '' : ' disabled';
    const grades = qaGrades(d.via === '');
    const grade = (k) => `<label class="k-ck mid"><input type="radio" name="qagrade" value="${k}" data-in="qaPd" data-k="grading" data-re${qaGradeOf(d) === k ? ' checked' : ''}${off}>${esc(grades[k])}${k === 'keywords' && d.keywords.trim() ? ` · ‘${esc(csv(d.keywords).join(', '))}’` : ''}</label>`;
    const basis = d.via === 'decision' ? `결정표 · ${(qaDecision(d.decision) || { label: d.decision }).label}` : d.via === 'query' ? `등록된 질의 · ${((S.st.queries || []).find((x) => x.name === d.query) || { label: d.query }).label}` : '정의 · 용어 사전 · 문서';
    const body = edit ? qaAskFields(d, 'qaPd', true) : '';
    const answer = edit ? '' : `<label class="k-f">정답<input class="k-in qa-ro" type="text" value="${esc(qaSay(q.expect))}" disabled></label>`;
    const words = ['keywords', 'evidence'].includes(d.grading || (d.via === '' ? 'keywords' : '')) || d.keywords.trim();
    return `<section class="k-card pad k-v g12" aria-label="선택한 검증 질문" style="flex:2 1 360px">
      <p class="k-code k-mut k-b" style="margin:0">${esc(q.id)}</p>
      <label class="k-f">질문<input class="k-in${edit ? '' : ' qa-ro'}" type="text" data-in="qaPd" data-k="text" value="${esc(d.text)}"${off}></label>
      ${edit ? (body ? `<div class="k-g2 qa-pf">${body}</div>` : '') : answer}
      <label class="k-f">근거<input class="k-in qa-ro" type="text" value="${esc(basis)}" disabled></label>
      <fieldset class="k-v" style="margin:0;padding:0;border:0"><legend class="k-s" style="padding:0;margin-bottom:8px;float:left;width:100%">평가 방법</legend>
        ${Object.keys(grades).map(grade).join('')}</fieldset>
      ${words && edit ? `<label class="k-f">키워드<input class="k-in" type="text" data-in="qaPd" data-k="keywords" value="${esc(d.keywords)}" placeholder="예: 14일, 고객센터"></label>` : ''}
      <div class="k-wrap g8">${kChip(QA_TYPE[q.type] || q.type)}${kChip(q.holdout ? '보류 세트' : '개발 세트')}${q.owner ? kChip(`담당자 · ${q.owner}`) : ''}${q.module_label ? kChip(q.module_label) : ''}${q.pending ? kChip('작성 중인 변경', 'warn') : ''}</div>
      ${edit ? `<div class="k-h end" style="margin-top:4px"><button class="k-btn" data-act="qaHold" data-id="${esc(q.id)}"${S.qa2.busy ? ' disabled' : ''}>${q.holdout ? '개발 세트로 이동' : '보류 세트로 이동'}</button><button class="k-btn pri" data-act="qaPdSave"${S.qa2.busy ? ' disabled' : ''}>저장</button></div>` : ''}</section>`;
  }

  function qaImportCard() {
    const f = S.qa2.imp;
    if (!f) return '';
    // the rows the server refused, each with its reason, kept beside the list until it is loaded again
    const failed = (f.failed || []).map((x) => { const at = x.indexOf(': '); return at > 0 ? [x.slice(0, at), x.slice(at + 2)] : ['', x]; });
    const refused = failed.length ? `<div class="qa-group" role="alert"><p class="k-s">추가 실패 ${failed.length}건</p><ul class="qa-fails k-14">${failed.map(([id, why]) => `<li>${id ? `<span class="k-code">${esc(id)}</span>` : ''}<span class="k-bad">${esc(why)}</span></li>`).join('')}</ul></div>` : '';
    return `<section class="k-card"><div class="k-ch"><h2>목록 불러오기</h2><span class="k-s">YAML · JSON</span></div><div class="k-cb">
      <label class="k-f"><textarea class="k-in mono" rows="6" data-in="qaImpText" aria-label="검증 질문 목록" placeholder="- {id: G1, text: &quot;C001 고객 주문 건수&quot;, query: ordersOfCustomer, params: {customer: C001}, expect: {rows: 2}}">${esc(f.text)}</textarea></label>
      ${refused}<div class="k-h"><button class="k-btn pri" data-act="qaImpGo"${f.busy ? ' disabled' : ''}>${f.busy ? '불러오는 중' : '불러오기'}</button><button class="k-btn" data-act="qaImpX">닫기</button></div></div></section>`;
  }

  function qaSetView() {
    const m = S.mg.st, edit = canEdit();
    const lead = '정답이 정해진 검증 질문 세트를 관리합니다.';
    const acts = `${edit ? `<button class="k-btn" data-act="qaImp">목록 불러오기</button><a class="k-btn" href="${itemHref('question', 'form')}">${ki('plus', 16, 1.75)}질문</a>` : ''}<button class="k-btn" data-act="qaRunGo">${ki('play', 16, 1.75)}검증 실행</button>`;
    const next = kNext([['semrules', '규칙'], ['search', '검색 · 질문'], ['flow?edit=1', '통과 조건']]);
    if (!m) return kHead('검증 질문', lead, acts) + qaWait('검증 질문을 불러오는 중입니다.');
    if (m.error) return kHead('검증 질문', lead) + kEmpty('검증 질문을 불러오지 못했습니다', m.error, '<button class="k-btn" data-act="qaReload">다시 시도</button>');
    const qs = m.questions || [];
    if (!qs.length) return `${kHead('검증 질문', lead, acts)}${qaImportCard()}${kEmpty('등록된 검증 질문이 없습니다', '', edit ? `<a class="k-btn pri" href="${itemHref('question', 'form')}">질문 추가</a>${known('search') ? '<a class="k-btn" href="#search">검색 · 질문</a>' : ''}` : '')}${next}`;
    const dev = qs.filter((q) => !q.holdout), hold = qs.filter((q) => q.holdout);
    if (S.qa2.set === 'holdout' && !hold.length) S.qa2.set = 'dev';
    const list = S.qa2.set === 'holdout' ? hold : dev;
    if (!list.some((q) => q.id === S.qa2.sel)) S.qa2.sel = list.length ? list[0].id : '';
    const sel = list.find((q) => q.id === S.qa2.sel) || null;
    const n = (f) => qs.filter(f).length;
    const decs = qs.filter((q) => q.type === 'decision'), onValues = decs.filter((q) => Object.keys(q.values || {}).length).length;
    const tile = (label, value, sub, dashed) => `<div class="${dashed ? 'qa-dash' : 'k-stat'}"><p class="k-s" style="margin:0">${label}</p><p class="k-big">${value}</p>${sub ? `<p class="k-s" style="margin:4px 0 0">${sub}</p>` : ''}</div>`;
    const tiles = `<section class="k-wrap" aria-label="질문 세트 현황">${tile('질문', count(qs.length), '')}${tile('정의형', count(n((q) => q.type === 'definition')), '연결 불필요')}
      ${tile('판정형', count(decs.length), !decs.length || onValues === decs.length ? '연결 불필요' : noSource() ? `값 기준 ${onValues} · 연결 필요 ${decs.length - onValues}` : `값 기준 ${onValues} · 레코드 기준 ${decs.filter((q) => q.key).length}`)}
      ${tile('값 조회형', count(n((q) => q.type === 'value')), noSource() ? '연결 필요' : '데이터 소스 기준', noSource())}${tile('보류 세트', count(hold.length), '별도 측정')}</section>`;
    const row = (q) => { const on = sel && q.id === sel.id, w = qaWaits(q);
      return `<tr class="${on ? 'on' : ''}" data-act="qaPick" data-id="${esc(q.id)}"><td class="k-code${on ? ' k-b' : ''}"><button class="qa-id" data-act="qaPick" data-id="${esc(q.id)}"${on ? ' aria-current="true"' : ''}>${esc(q.id)}</button></td><td class="${on ? 'b' : ''}">${esc(q.text)}${q.pending ? ` ${kChip('신규', 'warn')}` : ''}</td>
        <td>${kChip(QA_TYPE[q.type] || q.type, q.type === 'decision' ? 'b' : '')}</td><td>${esc(qaObjectOf(q) || '-')}</td><td>${w ? qaDash(w[0], w[1]) : kChip('측정 가능', 'ok')}</td></tr>`; };
    const w = m.workspace || {}, mine = (w.edits || []).filter((e) => String(e.target).startsWith('question:')).length;
    const pending = mine ? `<p class="k-note b">작성 중인 변경 요청 · 검증 질문 ${mine}건 <a href="#changes">변경 요청 · 버전</a></p>` : '';
    return `${kHead('검증 질문', lead, acts)}${sel ? itemBar('question', sel.id, sel.id, sel.text) : ''}${pending}${qaImportCard()}${tiles}
      <div class="k-cols"><section class="k-card" aria-labelledby="qa-ql" style="flex:3 1 560px"><div class="k-ch"><h2 id="qa-ql">질문 세트</h2><div class="k-push"><div class="k-seg" role="group" aria-label="세트"><button class="${S.qa2.set === 'dev' ? 'on' : ''}" data-act="qaSetTab" data-v="dev">개발 ${dev.length}</button><button class="${S.qa2.set === 'holdout' ? 'on' : ''}" data-act="qaSetTab" data-v="holdout"${hold.length ? '' : ' disabled'}>보류 ${hold.length}</button></div></div></div>
        <div class="k-x"><table class="k-t s"><thead><tr><th scope="col">ID</th><th scope="col">질문</th><th scope="col">유형</th><th scope="col">Object</th><th scope="col">측정</th></tr></thead><tbody>${list.map(row).join('') || '<tr><td colspan="5" class="mut">질문이 없습니다.</td></tr>'}</tbody></table></div></section>
        ${sel ? qaPanel(sel) : ''}</div>${next}`;
  }

  screen('check', { area: 'work', word: '검증 질문', view: qaSetView,
    after: () => { if (!S.mg.st && !S.mg.busy) loadManage(); } });

  Object.assign(INPUT, {
    qaPd: (t) => {
      const d = S.qa2.pd;
      if (!d) return;
      d[t.dataset.k] = t.value;
      if ('re' in t.dataset) render();
    },
    qaImpText: (t) => { if (S.qa2.imp) S.qa2.imp.text = t.value; },
    qaAskText: (t) => { S.qa2.ask.text = t.value; },
    qaKw: (t) => { INPUT.itf(t); if (S.it.d) qaGradeDefault(S.it.d); },  // the form's keywords, as the engine keeps any field
  });

  Object.assign(ACT, {
    qaPick: (t) => { S.qa2.sel = t.dataset.id; render(); },
    qaSetTab: (t) => { S.qa2.set = t.dataset.v; S.qa2.sel = ''; render(); },
    qaReload: () => { S.mg.st = null; loadManage(); render(); },
    qaRunGo: () => { location.hash = '#flow'; qaRun(); },
    qaImp: () => { S.qa2.imp = S.qa2.imp ? null : { text: '', busy: false }; render(); },
    qaImpX: () => { S.qa2.imp = null; render(); },
    qaImpGo: async () => {
      const f = S.qa2.imp;
      if (!f || f.busy) return;
      if (!f.text.trim()) { toast('목록이 없어 불러오지 못했습니다. YAML 또는 JSON 목록을 입력해 주세요.', true); return; }
      f.busy = true; f.failed = []; render();
      try {
        const r = await api('manage/questions', { text: f.text });
        S.mg.st = r;
        if (!r.failed.length) { S.qa2.imp = null; toast(`검증 질문 ${r.added.length}건을 추가했습니다.`); } else {
          f.busy = false; f.failed = r.failed;  // the reasons stay in the card, one row each
          if (r.added.length) toast(`검증 질문 ${r.added.length}건을 추가했습니다.`);
          else toast(`목록의 검증 질문 ${r.failed.length}건에 오류가 있어 추가하지 못했습니다. 오류 내용을 확인해 주세요.`, true);
        }
      } catch (e) { f.busy = false; fail(e); }
      render();
    },
    qaHold: async (t) => {
      const q = qaFind(t.dataset.id);
      if (!q || S.qa2.busy) return;
      S.qa2.busy = true;
      try {
        S.mg.st = await api('manage/edit', { op: 'update_question', args: { id: q.id, holdout: !q.holdout } });
        S.qa2.set = q.holdout ? 'dev' : 'holdout'; S.qa2.pdOf = '';
        toast(`${q.id}${josa(q.id, '을', '를')} ${q.holdout ? '개발' : '보류'} 세트로 이동했습니다.`);
      } catch (e) { fail(e); }
      S.qa2.busy = false; render();
    },
    qaPdSave: async () => {
      const d = S.qa2.pd, a = d ? qaArgs(d) : { error: '' };
      if (!d || S.qa2.busy) return;
      if (a.error) { toast(a.error, true); return; }
      S.qa2.busy = true;
      try {
        const r = await api('qa/question/save', a.args);
        S.mg.st = r; S.qa2.pdOf = '';
        toast('작성 중인 변경 요청에 저장했습니다.');
      } catch (e) { fail(e); }
      S.qa2.busy = false; render();
    },
  });

  // ---- QA-02 검증 --------------------------------------------------------------------------------------------------

  async function qaLoadFlow() {  // the stages and their pass conditions, measured
    if (S.fl && S.fl.busy) return;
    S.fl = { busy: true };
    try { S.fl = await api('flow'); S.fl.at = new Date().toTimeString().slice(0, 5); } catch (e) { S.fl = { error: e.message }; }
    if (['flow', 'check', 'monitor'].includes(S.tab)) render();
  }

  async function qaRun() {  // every question asked again, then the conditions measured on the answers
    if (S.qa && S.qa.busy) return;
    S.qa = { busy: true };
    if (S.tab === 'flow') render();
    try { S.qa = await api('questions', {}); } catch (e) { S.qa = { error: e.message }; }
    try { S.val = await api('values'); } catch (e) { S.val = { ok: false, configured: true, error: e.message }; }
    S.qa2.ranAt = new Date().toTimeString().slice(0, 5);
    if (S.tab === 'flow') render();
    S.fl = null;
    await qaLoadFlow();
  }

  // the answer a wrong result would make right: the rows it counted, or the expected outputs as they came out
  const qaGotAsExpect = (r) => (typeof r.got === 'number' ? { rows: r.got } : Object.fromEntries(Object.keys(r.expected || {}).map((k) => [k, (r.got || {})[k]])));
  const qaCanon = (v) => JSON.stringify(v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => (a < b ? -1 : 1))) : v);
  // whether the question as it is being written already takes what came out as its answer
  const qaTaken = (r) => { const q = qaFind(r.id); return !!q && qaCanon(q.expect) === qaCanon(qaGotAsExpect(r)); };
  // what a row of the results expected: the value, or the words a question graded by words must say
  const qaExpected = (x) => { const q = qaFind(x.id); return x.expected === null || x.expected === undefined || x.expected === '' || (typeof x.expected === 'object' && !Object.keys(x.expected).length) ? (q && (q.keywords || []).length ? `키워드 ${q.keywords.join(', ')}` : '-') : qaSay(x.expected); };
  const qaGates = () => ((S.fl && S.fl.steps) || []).flatMap((s) => s.gates || []);
  // a pass condition as the screens say it: 정답률 ≥ 90%, DB 대조 오류 0
  const QA_GATE = { 'bind.max_errors': 'Binding 검사 오류', 'bind.max_warnings': 'Binding 검사 경고', 'index.min_found': '문서 검색 적중률', 'query.min_agree': '저장소 간 질의 결과 일치율',
    'decide.min_agreement': '판정 일치율', 'check.min_accuracy': '정답률', 'check.min_grounded': '근거 제시율', 'check.max_value_errors': '거래 값 오류' };
  const qaGateSay = (g) => `${QA_GATE[`${g.stage}.${g.condition}`] || g.label} ${g.condition.startsWith('min_') ? `≥ ${gateValue(g, g.limit)}` : Number(g.limit) === 0 ? '0' : `≤ ${gateValue(g, g.limit)}`}`;
  const qaGate = (stage, cond) => qaGates().find((g) => g.stage === stage && g.condition === cond) || null;
  // what the check found out about a wrong decision answer, under the question in the results
  const QA_DIAGNOSIS = { rule: '질문 값 기준 오답', mapping: '질문 값 기준 정답 · 레코드 기준 오답', data: '레코드 조회 실패' };
  // why an answer was wrong, and the screen that mends it: [word, hash]
  function qaCause(x) {
    if (x.diagnosis === 'mapping') return ['Mapping', 'sources'];
    if (x.diagnosis === 'data') return ['소스 값', 'db'];
    if (x.error && x.diagnosis !== 'rule') return ['실행 오류', ''];
    const q = qaFind(x.id) || {};
    if (q.decision || x.diagnosis === 'rule') return ['규칙', 'semrules'];
    return q.query ? ['질의', 'query'] : ['정의', 'objects'];
  }

  function qaAskCard() {
    const a = S.qa2.ask, res = a.res;
    const open = '<section class="k-card pad k-v g12" aria-labelledby="qa-try" style="flex:2 1 480px"><h2 class="k-h2" id="qa-try">질문 테스트</h2>';
    const box = `<label class="qa-ask">${ki('chat', 18, 1.75)}<span class="k-hide">질문</span><input class="k-g0 k-14" id="qaask" type="text" data-in="qaAskText" value="${esc(a.text)}" placeholder="${esc((S.st.questions || [])[0] ? `예: ${S.st.questions[0].text}` : '질문 입력')}"><button class="k-lnk" data-act="qaAskGo"${a.busy ? ' disabled' : ''}>${a.busy ? '확인 중' : '질문'}</button></label>`;
    if (!res) return `${open}${box}</section>`;
    if (res.error) return `${open}${box}<p class="k-note bad">${esc(res.error)}</p></section>`;
    const d = (res.decisions || [])[0] || null;
    const val = (e) => (e.value === null || e.value === undefined ? QA_NONE : typeof e.value === 'boolean' ? (e.value ? '예' : '아니요') : e.kind === 'days_since' ? `${e.value}일` : String(e.value));
    const chips = d ? [`레코드 · ${d.target_label} ${d.key}`, `판정 · ${d.label}`, ...d.evidence.slice(0, 4).map((e) => `${e.label} · ${val(e)}`)]
      : res.record ? [`레코드 · ${res.record.label} ${res.record.key}`] : res.query ? [`등록된 질의 · ${res.query.label}`] : [res.route === 'none' ? '찾을 대상 없음' : '문서 · 정의 검색'];
    const badge = answerBadge(res)[1];
    const uniq = (xs) => [...new Set(xs.filter(Boolean))].join(' · ');
    const rules = d ? uniq(d.rules.map((x) => x.id)) : '', cites = d ? uniq(d.rules.map((x) => x.cite)) : '', vers = d ? uniq(d.rules.map((x) => `${x.module_label} ${x.version}`)) : '';
    const main = d ? `${d.verdict}${d.reason ? ` · ${d.reason}` : ''}` : res.route === 'none' ? '답변 없음' : (res.answer || '');
    const basis = d ? [rules && `규칙 ${rules}`, cites && `근거 ${cites}`, vers, badge].filter(Boolean).join(' · ')
      : [badge, res.sources && res.sources.length ? `근거 ${res.sources.length}건` : '', res.route === 'none' ? (res.reason || '근거 없음') : ''].filter(Boolean).join(' · ');
    const saved = a.fb === 'saved' ? '<p class="k-note b">작성 중인 변경 요청에 검증 질문을 저장했습니다. <a href="#check">검증 질문</a></p>' : '';
    const bad = a.fb === 'bad' ? `<p class="k-note warn">확인 대상 · ${known('semrules') ? '<a href="#semrules">규칙</a>' : ''}${d ? ` · <a href="#record?type=${encodeURIComponent(d.target)}&key=${encodeURIComponent(d.key)}">${esc(d.target_label)} ${esc(d.key)}</a>` : ''}</p>` : '';
    return `${open}${box}
      <div class="k-h g6"><span class="k-s">질문 해석</span>${chips.map((c) => kChip(c)).join('')}</div>
      <div class="qa-answer"><p class="k-15" style="margin:0;font-weight:600">${esc(main)}</p><p class="k-i3 k-13" style="margin:0">${esc(basis)}</p>${d ? `<p class="k-s" style="margin:0">판단 과정 · ${policyStep(d)}</p>` : ''}</div>
      <div class="k-pha"><span class="k-s">답변 평가</span><button class="k-btn${a.fb === 'good' ? ' qa-on' : ''}" data-act="qaAskFb" data-v="good" aria-pressed="${a.fb === 'good'}">정답</button><button class="k-btn${a.fb === 'bad' ? ' qa-on' : ''}" data-act="qaAskFb" data-v="bad" aria-pressed="${a.fb === 'bad'}">오답</button>
        ${canEdit() && a.fb !== 'saved' && res.route !== 'none' ? '<button class="k-lnk k-push" data-act="qaAskSave">검증 질문으로 저장</button>' : ''}</div>${saved}${bad}</section>`;
  }

  // the stages a check runs through and the pass conditions, to change: the older form's handlers, drawn with the kit
  function qaSettingsCard() {
    const f = S.flset;
    if (!f || f.busy) return qaWait('통과 조건을 불러오는 중입니다.');
    if (f.error) return kEmpty('통과 조건을 불러오지 못했습니다', f.error);
    const s = f.settings;
    // the stages and conditions in the words the results and the board use
    const stages = f.stages.filter((x) => !['source', 'define'].includes(x.id)).map((x) => `<label class="k-ck pill"><input type="checkbox" data-in="fstage" data-k="${x.id}"${s.off.includes(x.id) ? '' : ' checked'}>${esc(STEP_WORD[x.id] || x.label)}</label>`).join('');
    const conds = Object.entries(f.conditions).map(([stage, cs]) => cs.map((c) => {
      const v = (s.gates[stage] || {})[c.id], share = c.id.startsWith('min_');
      const up = (f.raised || []).find((x) => x.stage === stage && x.condition === c.id);
      const word = QA_GATE[`${stage}.${c.id}`] ? `${QA_GATE[`${stage}.${c.id}`]} ${share ? '최소' : '최대'}` : c.label;
      return `<label class="k-f">${esc(word)}${share ? ' (%)' : ''}<input class="k-in" type="number" min="0"${share ? ' max="100"' : ''} step="1" data-in="fgate" data-s="${stage}" data-k="${c.id}" value="${v === undefined || v === null ? '' : (share ? Math.round(v * 100) : v)}" placeholder="조건 없음">${up ? `<span class="k-hint">${esc(up.module_label)} 적용 중 · ${share ? `${Math.round(up.value * 100)}%` : up.value}</span>` : ''}</label>`;
    }).join('')).join('');
    const a = s.agreement || {}, dec = f.decisions.find((d) => d.name === a.decision), q = f.queries.find((x) => x.name === a.query), cols = q ? q.columns : [];
    const colSel = (kind, k, cur) => `<select class="k-in sm" data-in="fagree" data-kind="${kind}" data-k="${esc(k)}" aria-label="${esc(k)} 컬럼"><option value="">-</option>${cols.map((c) => opt(c, c, cur)).join('')}</select>`;
    const maps = dec && q ? `<div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">결정표</th><th scope="col">처리 기록 컬럼</th></tr></thead><tbody>
      ${dec.inputs.map((i) => `<tr><td>입력 <span class="k-code">${esc(i)}</span></td><td>${colSel('inputs', i, (a.inputs || {})[i])}</td></tr>`).join('')}${dec.outputs.map((o) => `<tr><td>결과 <span class="k-code">${esc(o)}</span></td><td>${colSel('expect', o, (a.expect || {})[o])}</td></tr>`).join('')}</tbody></table></div>` : '';
    const list = s.values = s.values || [];
    const WORD = { query: '대조 질의', key: '대상 번호 컬럼', truth: '거래 시스템 값 컬럼', by: '온톨로지 값', output: '결과 이름' };
    const sel = (i, k, options, cur) => `<select class="k-in sm" data-in="fval" data-i="${i}" data-k="${k}" aria-label="${WORD[k]}" title="${WORD[k]}"><option value="">${WORD[k]}</option>${options.map(([x, y]) => opt(x, y, cur)).join('')}</select>`;
    const vrow = (v, i) => {
      const vq = f.queries.find((x) => x.name === v.query), vcols = ((vq || {}).columns || []).map((c) => [c, c]);
      const ans = v.answer || {}, outs = ans.decision ? ((f.decisions.find((d) => d.name === ans.decision) || {}).outputs || []) : ans.function ? (((f.functions || []).find((x) => x.name === ans.function) || {}).outputs || []) : [];
      return `<div class="qa-vrow"><input class="k-in sm" type="text" data-in="fval" data-i="${i}" data-k="label" value="${esc(v.label || '')}" placeholder="항목 이름" aria-label="항목 이름">${sel(i, 'query', f.queries.map((x) => [x.name, x.label || x.name]), v.query)}${sel(i, 'key', vcols, v.key)}${sel(i, 'truth', vcols, typeof v.truth === 'string' ? v.truth : '')}
        ${sel(i, 'by', [...f.decisions.map((d) => [`decision:${d.name}`, `결정 · ${d.label || d.name}`]), ...(f.functions || []).map((x) => [`function:${x.name}`, `함수 · ${x.label || x.name}`])], ans.decision ? `decision:${ans.decision}` : (ans.function ? `function:${ans.function}` : ''))}${sel(i, 'output', outs.map((o) => [o, o]), ans.output)}
        <button class="k-lnk bad" data-act="fvaldel" data-i="${i}" aria-label="${esc(v.label || '항목')} 삭제">삭제</button></div>`;
    };
    return `<section class="k-card" id="qa-edit" aria-labelledby="qa-edit-h"><div class="k-ch"><h2 id="qa-edit-h">통과 조건 편집</h2><div class="k-push"><button class="k-btn" data-act="qaEdit">닫기</button><button class="k-btn pri" data-act="flowsave">저장</button></div></div>
      <div class="k-cb"><div class="qa-group"><p class="k-s">측정 단계</p><div class="k-wrap g8">${stages}</div></div>
        <div class="qa-group"><p class="k-s">통과 조건</p><div class="qa-g3">${conds}</div></div>
        <div class="qa-group"><p class="k-s">판정 일치율</p><div class="k-g2">
          <label class="k-f">결정표<select class="k-in" data-in="fagree" data-kind="decision"><option value="">사용 안 함</option>${f.decisions.map((d) => opt(d.name, d.label, a.decision)).join('')}</select></label>
          <label class="k-f">처리 기록 질의<select class="k-in" data-in="fagree" data-kind="query"><option value="">-</option>${f.queries.map((x) => opt(x.name, x.label, a.query)).join('')}</select></label></div>${maps}</div>
        <div class="qa-group" data-row="values"><p class="k-s">거래 값 대조</p>${list.map(vrow).join('')}<div><button class="k-btn sm" data-act="fvaladd">${ki('plus', 14, 1.75)}항목 추가</button></div></div>
        </div></section>`;
  }

  function qaRunView() {
    const r = S.qa, fl = S.fl && !S.fl.busy && !S.fl.error ? S.fl : null;
    const lead = '검증 질문을 실행하고 결과와 통과 조건을 확인합니다.';
    const busy = !r || r.busy;
    const ver = qaVersion(), dirty = S.mg.st && S.mg.st.workspace && S.mg.st.workspace.dirty;
    const last = S.qa2.ranAt ? `<span class="k-s">마지막 실행 ${esc(S.qa2.ranAt)}${ver ? ` · 버전 ${esc(ver)}` : ''}${dirty ? ' · 작성 중인 변경 미반영' : ''}</span>` : '';
    const head = kHead('검증', lead, `${last}<button class="k-btn pri" data-act="qaRunNow"${busy ? ' disabled' : ''}>${ki('play', 16, 1.75)}${busy ? '검증 중' : '검증 실행'}</button>`);
    const next = kNext([['check', '검증 질문'], ['semrules', '규칙'], ['objects', 'Entity'], ['changes', '변경 요청 · 버전']]);
    if (busy) return head + qaWait('검증 질문을 실행하는 중입니다.') + next;
    if (r.error) return head + kEmpty('검증을 실행하지 못했습니다', r.error, '<button class="k-btn" data-act="qaRunNow">다시 시도</button>') + next;
    const res = r.results, asked = res.filter((x) => x.passed !== null), right = asked.filter((x) => x.passed), wrong = asked.filter((x) => !x.passed), waits = res.filter((x) => x.passed === null);
    if (!res.length) return head + kEmpty('등록된 검증 질문이 없습니다', '', '<a class="k-btn pri" href="#check">검증 질문</a>') + next;
    // the four measures against their targets
    const gAcc = qaGate('check', 'min_accuracy'), gGr = qaGate('check', 'min_grounded'), gAg = qaGate('decide', 'min_agreement'), gVal = qaGate('check', 'max_value_errors');
    const tile = (label, big, sub, tone) => `<div class="qa-tile${tone === 'warn' ? ' warn' : tone === 'wait' ? ' wait' : ''}"><p class="k-s" style="margin:0">${esc(label)}</p><p class="k-big${tone === 'warn' ? ' warn' : tone === 'wait' ? ' mut' : ''}">${esc(big)}</p><p class="${tone === 'warn' ? 'k-warn k-13' : tone === 'ok' ? 'k-ok k-13' : 'k-s'}" style="margin:4px 0 0">${esc(sub)}</p></div>`;
    const share = (v) => `${Math.round(v * 100)}%`;
    const goal = (g) => (g && !g.unmeasured ? gateValue(g, g.limit) : '');
    const accT = !asked.length ? tile('정답률', noSource() ? '연결 필요' : '-', '측정 질문 없음', 'wait')
      : tile('정답률', share(r.accuracy), `${right.length} / ${asked.length}${goal(gAcc) ? ` · 목표 ${goal(gAcc)}${gAcc.passed ? ' 충족' : ''}` : ''}`, gAcc && !gAcc.passed ? 'warn' : gAcc ? 'ok' : '');
    const grounded = asked.filter((x) => x.grounded).length;
    const grT = !asked.length ? tile('근거 제시율', noSource() ? '연결 필요' : '-', '측정 질문 없음', 'wait')
      : tile('근거 제시율', share(r.grounded), goal(gGr) ? `목표 ${goal(gGr)}${gGr.passed ? ' 충족' : ` · ${grounded} / ${asked.length}`}` : `근거 있는 답 ${grounded} / ${asked.length}`, gGr && !gGr.passed ? 'warn' : gGr ? 'ok' : '');
    const dstep = fl ? fl.steps.find((x) => x.id === 'decide') : null, ag = dstep && dstep.agreement;
    const agT = ag && ag.cases ? tile('판정 일치율 · 실제 처리 대비', pct(ag.rate), `${ag.agree} / ${ag.cases}${goal(gAg) ? ` · 목표 ${goal(gAg)}${gAg.passed ? ' 충족' : ''}` : ''}`, gAg && !gAg.passed ? 'warn' : gAg ? 'ok' : '')
      : tile('판정 일치율 · 실제 처리 대비', noSource() ? '연결 필요' : !fl ? '-' : '미설정', noSource() ? (gAg ? `목표 ${gateValue(gAg, gAg.limit)}` : '과거 처리 기록 대조') : !fl ? '측정 중' : '처리 기록 질의 미지정', 'wait');
    const v = S.val || {}, vLabel = v.ok && v.items && v.items.length ? `${v.items.slice(0, 3).map((x) => x.label).join(' · ')} 오류` : '거래 값 오류';
    const valT = v.ok && v.configured !== false ? tile(vLabel, `${count(v.errors)}건`, `${count(v.cases)}건 대조${gVal ? ` · 목표 ${gateValue(gVal, gVal.limit)}건` : ''}`, v.errors ? 'warn' : 'ok')
      : !noSource() && v.error && v.configured !== false ? tile(vLabel, '측정 실패', String(v.error).split('. ')[0], 'warn')
        : tile(vLabel, noSource() ? '연결 필요' : '미설정', noSource() ? (gVal ? `목표 ${gateValue(gVal, gVal.limit)}건` : '거래 시스템 값 대조') : '대조 항목 미지정', 'wait');
    // the answers, by how they came out
    const tabs = [['wrong', '오답', wrong], ['right', '정답', right], ['wait', waits.length && waits.every((x) => x.unmeasured === 'no_source') ? '연결 필요' : '측정 제외', waits]];
    // a link to one question's row (#flow?row=q:Q1) opens the tab that row is in: while the link is landing, and once
    // more when the results come in after it landed
    const land = S.land && S.land.row ? String(S.land.row) : '', want = land || String(S.hit || '');
    const hitTab = want.startsWith('q:') && (land || want !== S.qa2.hitOf) ? tabs.find(([, , l]) => l.some((x) => `q:${x.id}` === want)) : null;
    if (hitTab) { S.qa2.result = hitTab[0]; S.qa2.hitOf = want; }
    const on =tabs.some(([k, , l]) => k === S.qa2.result && l.length) ? S.qa2.result : (wrong.length ? 'wrong' : right.length ? 'right' : 'wait');
    const shown = tabs.find((t) => t[0] === on)[2];
    const idCell = (x) => `<td class="k-code">${canEdit() ? `<a class="k-ink" href="${itemHref('question', 'form', x.id)}" title="편집">${esc(x.id)}</a>` : esc(x.id)}</td>`;
    const row = (x) => {
      if (on === 'wait') return `<tr data-row="q:${esc(x.id)}">${idCell(x)}<td>${esc(x.text)}</td><td>${esc(qaExpected(x))}</td><td>${qaDash(x.unmeasured === 'no_source' ? '연결 필요' : '측정 제외', qaNote(x))}</td></tr>`;
      if (on === 'right') return `<tr data-row="q:${esc(x.id)}">${idCell(x)}<td>${esc(x.text)}</td><td>${esc(qaExpected(x))} · <span class="k-ok">${x.grading === 'keywords' || x.grading === 'evidence' || x.type === 'definition' ? '포함' : '일치'}</span></td><td>${x.grounded ? kChip('근거 있음', 'ok') : `<span class="k-s">근거 부족 · ${esc((x.gaps || []).join(', '))}</span>`}</td></tr>`;
      const [word, tab] = qaCause(x), d = QA_DIAGNOSIS[x.diagnosis] || '', q = qaFind(x.id) || {};
      const differs = (x.differs || []).map((m) => `${m.label || m.input} 질문 ${qaSay(m.given)} · 레코드 ${qaSay(m.read)}`).join(' / ');
      const why = [d, differs].filter(Boolean).join(' · ');
      return `<tr data-row="q:${esc(x.id)}">${idCell(x)}<td>${esc(x.text)}${why ? `<div class="k-s" style="margin-top:4px">${esc(why)}</div>` : ''}</td><td>${esc(qaExpected(x))} · <span class="k-bad">${esc(x.error || qaSay(x.got))}</span></td>
        <td><div class="k-h g6">${tab && known(tab) ? `<a class="k-chip warn" href="#${tab}">${esc(word)}</a>` : kChip(word, 'warn')}${q.decision || q.query ? `<button class="k-lnk" data-act="chkopen" data-id="${esc(x.id)}">열기</button>` : ''}${canEdit() && !x.error && x.got !== null && typeof x.got !== 'string' ? (qaTaken(x) ? kChip('정답 갱신됨', 'b') : `<button class="k-lnk" data-act="qaExpect" data-id="${esc(x.id)}">정답 갱신</button>`) : ''}</div></td></tr>`;
    };
    const results = `<section class="k-card" aria-labelledby="qa-res" style="flex:3 1 560px"><div class="k-ch"><h2 id="qa-res">결과</h2><div class="k-push"><div class="k-seg" role="group" aria-label="결과 필터">${tabs.map(([k, w, l]) => `<button class="${k === on ? 'on' : ''}" data-act="qaResTab" data-v="${k}"${l.length ? '' : ' disabled'}>${w} ${l.length}</button>`).join('')}</div></div></div>
      <div class="k-x"><table class="k-t s end"><thead><tr><th scope="col">ID</th><th scope="col" style="width:38%">질문</th><th scope="col">${on === 'wait' ? '기대' : '기대 · 실제'}</th><th scope="col">${on === 'right' ? '근거' : on === 'wait' ? '측정' : '원인'}</th></tr></thead><tbody>${shown.map(row).join('') || '<tr><td colspan="4" class="mut">질문이 없습니다.</td></tr>'}</tbody></table></div></section>`;
    // what the wrong answers point at
    const by = {};
    wrong.forEach((x) => { const w = qaCause(x)[0]; by[w] = (by[w] || 0) + 1; });
    const lack = right.filter((x) => !x.grounded).length;
    const line = (w, n, mut = false) => `<div class="k-14${mut ? ' k-mut' : ''}" style="display:flex;justify-content:space-between;gap:12px"><span>${w}</span>${typeof n === 'number' ? `<b>${n}</b>` : `<span>${n}</span>`}</div>`;
    const causes = `<section class="k-card pad k-v" aria-labelledby="qa-cause"><h2 class="k-h2" id="qa-cause">오답 원인</h2>${line('정의', by['정의'] || 0)}${line('규칙', by['규칙'] || 0)}${line('질의', by['질의'] || 0)}${by['실행 오류'] ? line('실행 오류', by['실행 오류']) : ''}
      ${noSource() ? line('Mapping · 소스 값', '연결 필요', true) : line('Mapping · 소스 값', (by['Mapping'] || 0) + (by['소스 값'] || 0))}${lack ? line('근거 부족 정답', lack) : ''}</section>`;
    const st = r.stages, c = r.conformance;
    const stageLine = (k, w) => { const x = st && st[k]; return !x || !x.questions ? '' : line(w, x.measured ? `${x.passed} / ${x.measured} 통과${x.measured < x.questions ? ` · 대기 ${x.questions - x.measured}` : ''}` : `연결 필요 · ${x.questions}문항`, !x.measured); };
    const sets = r.sets && r.sets.holdout && r.sets.holdout.questions ? line('개발 · 보류 세트 정답률', `${pct(r.sets.dev.accuracy)} · ${pct(r.sets.holdout.accuracy)}`) : '';
    const conf = c && c.queries ? line('저장소 간 질의 결과 일치', `${c.queries.filter((x) => x.agree).length} / ${c.queries.length}`) : '';
    const lines = `${stageLine('values', '값 기준')}${stageLine('record', '레코드 기준')}${sets}${conf}`;
    const stagesCard = lines ? `<section class="k-card pad k-v" aria-labelledby="qa-stage"><h2 class="k-h2" id="qa-stage">측정 단계</h2>${lines}</section>` : '';
    // where the stores disagree on a registered query, and where a value differs from the one the trade system recorded
    const apart = c && c.queries ? c.queries.filter((x) => !x.agree) : [];
    const apartCard = apart.length ? `<section class="k-card" aria-labelledby="qa-apart"><div class="k-ch"><h2 id="qa-apart">저장소 간 결과 불일치 질의</h2>${kChip(String(apart.length), 'warn')}</div>
      ${apart.slice(0, 8).map((x) => `<a class="k-row" data-row="conf:${esc(x.name)}" href="#query?query=${encodeURIComponent(x.name)}"><span class="k-col"><span class="k-ink k-14">${esc(x.label)}</span><span class="k-s">${Object.entries(x.rows).map(([b, n]) => `${esc(b)} ${n === null ? '오류' : `${n}행`}`).join(' · ')}</span></span>${ki('chevR', 16, 1.75)}</a>`).join('')}</section>` : '';
    const off = v.ok && v.items ? v.items.filter((x) => x.errors) : [];
    const offCard = off.length ? `<section class="k-card" aria-labelledby="qa-off" data-row="values"><div class="k-ch"><h2 id="qa-off">거래 값 불일치</h2>${kChip(`${v.errors}건`, 'warn')}</div>
      ${off.map((x) => `<div class="k-row"><span class="k-col"><span class="k-ink k-14">${esc(x.label)} · 오류 ${x.errors} / ${x.cases}건</span><span class="k-s">${x.mismatches.slice(0, 5).map((m) => `${esc(m.key)} 온톨로지 ${show(m.answer)} · 거래 시스템 ${show(m.truth)}`).join(' / ')}</span></span></div>`).join('')}</section>` : '';
    // the conditions a version must meet before it is deployed
    const gates = qaGates();
    const met = gates.filter((g) => g.passed && !g.unmeasured).length, due = gates.filter((g) => !g.unmeasured).length;
    const gline = (g) => `<li${g.unmeasured ? ' class="k-mut"' : ''}><span>${esc(qaGateSay(g))}${g.by ? ` <span class="k-s">· ${esc(g.by)}</span>` : ''}</span>${g.unmeasured ? qaDash('연결 필요', qaNote(g)) : g.passed ? kChip('충족', 'ok') : `<button class="k-chip warn" data-act="issopen" data-key="${esc(gateKey(g))}" title="조치 보기">${gateValue(g, g.value)} · 미달</button>`}</li>`;
    const pass = `<section class="k-card" aria-labelledby="qa-pass" style="flex:1 1 360px"><div class="k-ch" style="border-bottom:1px solid var(--row)"><h2 id="qa-pass">배포 통과 조건</h2>${due ? `<span class="k-chip ${met === due ? 'ok' : 'warn'} k-push">${met} / ${due}</span>` : gates.length ? `<span class="k-push">${qaDash('연결 필요', '데이터 소스 미연결')}</span>` : ''}</div>
      ${!fl ? `<p class="k-cf">${S.fl && S.fl.error ? esc(S.fl.error) : '통과 조건을 측정하는 중입니다.'}</p>` : gates.length ? `<ul class="qa-gates k-14">${gates.map(gline).join('')}</ul>` : '<p class="k-cf">설정된 통과 조건이 없습니다.</p>'}
      <div class="qa-passfoot">${isOntoAdmin() ? `<button class="k-btn" data-act="qaEdit" aria-expanded="${S.qa2.edit}">조건 편집</button>` : ''}</div></section>`;
    return `${head}<section class="k-wrap" aria-label="목표 대비">${accT}${grT}${agT}${valT}</section>
      <div class="k-cols">${results}<div class="k-c2">${causes}${stagesCard}${apartCard}${offCard}</div></div>
      <div class="k-cols">${pass}${qaAskCard()}</div>${S.qa2.edit && isOntoAdmin() ? qaSettingsCard() : ''}${next}`;
  }

  screen('flow', { area: 'work', word: '검증', view: qaRunView,
    after: () => {
      if (itemParam('edit') && !S.qa2.edit) { S.qa2.edit = true; S.qa2.editGo = true; history.replaceState(null, '', '#flow'); render(); return; }
      if (!S.qa) qaRun(); else if (!S.fl) qaLoadFlow();
      if (!S.flset) loadFlowSettings();
      if (!S.mg.st && !S.mg.busy) loadManage();
      if (S.qa2.edit && S.qa2.editGo) { const box = $('#qa-edit'); if (box) { S.qa2.editGo = false; box.scrollIntoView({ block: 'start' }); } }
    } });

  async function qaAsk() {
    const a = S.qa2.ask, text = a.text.trim();
    if (!text) { toast('질문이 없어 확인하지 못했습니다. 질문을 입력해 주세요.', true); return; }
    if (a.busy) return;
    Object.assign(a, { busy: true, fb: '' });
    render();
    let res;
    try { res = await api('space/ask', { text }); } catch (e) { res = { error: e.message }; }
    if (res && res.ok === false) res = { error: res.error };
    Object.assign(a, { busy: false, res });
    if (S.tab === 'flow') { render(); const box = $('#qaask'); if (box) box.focus(); }
  }

  Object.assign(ACT, {
    qaRunNow: () => qaRun(),
    qaExpect: async (t) => {  // a wrong answer taken as the right one: the result as it came out becomes the answer
      const r = S.qa && S.qa.results && S.qa.results.find((x) => x.id === t.dataset.id);
      if (!r) return;
      if (qaTaken(r)) { toast('변경된 내용이 없어 저장하지 못했습니다. 작성 중인 변경 요청을 확인해 주세요.', true); render(); return; }
      const expect = qaGotAsExpect(r);
      if (!window.confirm(`${r.id} 정답 변경 · ${qaSay(r.expected)} → ${qaSay(r.got)}`)) return;
      try {
        S.mg.st = await api('manage/edit', { op: 'update_question', args: { id: r.id, expect } });
        toast('작성 중인 변경 요청에 저장했습니다.');
        render();
      } catch (e) { fail(e); }
    },
    qaResTab: (t) => { S.qa2.result = t.dataset.v; render(); },
    qaEdit: () => { S.qa2.edit = !S.qa2.edit; S.qa2.editGo = S.qa2.edit; render(); },
    qaAskGo: () => qaAsk(),
    qaAskFb: (t) => { S.qa2.ask.fb = S.qa2.ask.fb === t.dataset.v ? '' : t.dataset.v; render(); },
    qaAskSave: async () => {
      const res = S.qa2.ask.res, d = res && (res.decisions || [])[0];
      if (!res) return;
      if (!d) { location.hash = `#question-form?type=definition&text=${encodeURIComponent(res.question || S.qa2.ask.text)}`; return; }  // a meaning or a value: its answer is written on the form
      try {
        const r = await api('qa/question/save', { new: true, type: 'decision', text: res.question, decision: d.name, key: d.key, expect: d.outputs });
        S.mg.st = r; S.qa2.ask.fb = 'saved'; S.qa2.sel = r.id;
        toast(`검증 질문 ${r.id}${josa(r.id, '을', '를')} 작성 중인 변경 요청에 저장했습니다.`);
        render();
      } catch (e) { fail(e); }
    },
  });
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' && ev.target.id === 'qaask') { ev.preventDefault(); qaAsk(); } });

  // ---- OPS-03 파이프라인 관제 --------------------------------------------------------------------------------------
  // The board the server measures (S.mon.st) is read again every few seconds while the screen is open; only the parts
  // that move are drawn again, so what a person is reading stays where it is.

  const QA_MON_EVERY = 5000;
  const QA_DOT = { ok: '', warn: ' warn', bad: ' bad', off: ' off' };
  const QA_FLOOR = { source: '자료 · 데이터 소스', convert: '변환', ontology: '온톨로지 구축', store: '저장소 · 엔진', use: '활용', verify: '검증' };

  function qaMonChip(m) {
    const n = m.alerts.length, tone = m.status === 'bad' ? 'bad' : m.status === 'warn' ? 'warn' : 'ok';
    return `<span class="k-chip ${tone}"><i class="k-dot${QA_DOT[m.status] || ''}" style="width:6px;height:6px" aria-hidden="true"></i>${esc(ST_WORD[m.status] || m.status)}${n ? ` · 알림 ${n}` : ''}</span>`;
  }

  function qaMonTiles(m) {
    const tile = (f) => `<li class="qa-step${f.status === 'warn' ? ' warn' : f.status === 'bad' ? ' bad' : ''}"><span class="qa-steph"><a class="k-b" href="#${esc(f.tab)}"${f.alerts ? ` data-act="issfloor" data-floor="${esc(f.id)}"` : ''}>${esc(QA_FLOOR[f.id] || f.label)}</a><i class="k-dot${QA_DOT[f.status] || ''}" role="img" aria-label="${esc(ST_WORD[f.status] || '')}"></i></span>
      <span class="${f.status === 'warn' ? 'k-warn k-13' : f.status === 'bad' ? 'k-bad k-13' : 'k-s'}">${f.alerts ? `알림 ${f.alerts} · ` : ''}${f.tags.filter((t) => t.value !== '0' && t.value !== '').slice(0, 2).map((t) => `${esc(t.label)} ${esc(t.value)}`).join(' · ') || esc((f.tags[0] || {}).label ? `${f.tags[0].label} ${f.tags[0].value}` : '')}</span></li>`;
    const waits = S.st.changes || 0, inbox = S.home.box ? S.home.box.counts.assigned : 0;
    const approve = `<li class="qa-step${waits ? ' warn' : ''}"><span class="qa-steph"><a class="k-b" href="#${known('changes') ? 'changes' : 'inbox'}">승인</a><i class="k-dot${waits ? ' warn' : ''}" role="img" aria-label="${waits ? '주의' : '정상'}"></i></span><span class="${waits ? 'k-warn k-13' : 'k-s'}">변경 요청 대기 ${waits}${inbox ? ` · 할 일 ${inbox}` : ''}</span></li>`;
    const ver = qaVersion();
    const deploy = `<li class="qa-step"><span class="qa-steph"><a class="k-b" href="#changes">배포</a><i class="k-dot" role="img" aria-label="정상"></i></span><span class="k-s">${esc(ver || '-')}${waits ? ` · 검토 중 ${waits}` : ''}</span></li>`;
    const source = noSource() ? `<li class="qa-step dash"><span class="qa-steph"><b class="k-b">소스 차이 검사</b>${kChip('선택 사항')}</span><span class="k-s">미연결</span></li>` : '';
    return m.floors.map(tile).join('') + approve + deploy + source;
  }

  function qaMonRules(m) {
    const gates = qaGates();
    const rule = (title, sub, chip, warn, act = '') => `<div class="qa-rule${warn ? ' warn' : ''}"><span class="qa-ruleh"><b class="k-b">${esc(title)}</b>${chip}</span><span class="k-s">${esc(sub)}</span>${act}</div>`;
    const fromGate = (g) => (g.unmeasured ? rule(qaGateSay(g), qaNote(g) || '데이터 소스 필요', qaDash('연결 필요'), false)
      : g.passed ? rule(qaGateSay(g), `현재 ${gateValue(g, g.value)}`, kChip('정상', 'ok'), false)
        : rule(qaGateSay(g), `현재 ${gateValue(g, g.value)}`, `<button class="k-chip warn" data-act="issopen" data-key="${esc(gateKey(g))}">알림 · 조치 보기</button>`, true));
    const gated = new Set(gates.filter((g) => !g.passed && !g.unmeasured).map((g) => gateKey(g)));
    const others = m.issues.filter((x) => !gated.has(x.id) && !String(x.id).startsWith('gate:')).map((x) => rule(x.title, x.detail || '', `<button class="k-chip ${x.level === 'bad' ? 'bad' : 'warn'}" data-act="issopen" data-id="${esc(x.id)}">알림${x.members && x.members.length ? ` ${x.members.length + 1}` : ''} · 조치 보기</button>`, true));
    const rows = others.join('') + gates.map(fromGate).join('');
    return rows || `<p class="k-cf">${S.fl && S.fl.busy ? '통과 조건을 측정하는 중입니다.' : '설정된 통과 조건과 알림이 없습니다.'}</p>`;
  }

  function qaMonLog() {
    const l = S.qa2.log;
    if (!l) return '<p class="k-cf">기록을 불러오는 중입니다.</p>';
    if (l.error) return `<p class="k-cf">${esc(l.error)}</p>`;
    if (!l.rows.length) return '<p class="k-cf">기록이 없습니다.</p>';
    const basis = (r) => [r.rules.length ? r.rules.join(' · ') : '', r.change || '', ...r.versions.slice(0, 1).map((v) => `${v.label} ${v.version}`), r.versions.length > 1 ? `외 ${r.versions.length - 1}` : ''].filter(Boolean).join(' · ');
    return `<div class="k-x"><table class="k-t s"><thead><tr><th scope="col">시각</th><th scope="col">종류</th><th scope="col">내용</th><th scope="col">근거 · 버전</th></tr></thead><tbody>
      ${l.rows.map((r) => `<tr><td class="k-code" title="${esc(r.at)}">${esc(String(r.at).slice(0, 10) === new Date().toISOString().slice(0, 10) ? qaHm(r.at) : qaWhen(r.at))}</td><td>${kChip(r.kind, r.tone)}</td><td>${esc(r.text)}</td><td class="i3">${esc(basis(r) || '-')}</td></tr>`).join('')}</tbody></table></div>
      ${l.total > l.rows.length ? `<p class="k-cf line">최근 ${l.rows.length}건 표시 · 전체 ${l.total}건</p>` : ''}`;
  }

  // each stage as the flow measured it: what it holds, its pass conditions, and the screen it is made on
  function qaMonSteps() {
    const fl = S.fl;
    if (!fl || fl.busy) return '<p class="k-cf">단계별 값을 측정하는 중입니다.</p>';
    if (fl.error) return `<p class="k-cf">${esc(fl.error)}</p>`;
    const say = (s) => {
      if (s.id === 'source') return noSource() ? '데이터 소스 미연결' : `${esc(BACKEND_KIND[(s.kind || s.dialect || '').toLowerCase()] || s.kind || '')} · 테이블 ${count(s.tables.length)} · ${count(s.rows)}행`;
      if (s.id === 'define') return `도메인 팩 ${s.modules.length} · Entity ${count(s.objects)} · Relation ${count(s.links)} · Property ${count(s.properties)}${s.computed ? ` · 계산 ${s.computed}` : ''}`;
      if (s.id === 'bind') { const c = s.checked || {}; return `테이블 ${count(c.tables || 0)} · 컬럼 ${count(c.columns || 0)} · 문제 ${s.findings}`; }
      if (s.id === 'project') return s.backends.length ? `${esc(s.backends.join(', '))} · Node ${count(s.nodes)} · Edge ${count(s.edges)}${s.sync && s.sync.at ? ` · 최근 동기화 ${esc(s.sync.at.replace('T', ' '))}` : ''}` : '그래프 저장소 없음';
      if (s.id === 'index') return `문서 ${s.documents} · 항목 ${s.sections} · 청크 ${s.chunks}${s.questions ? ` · 검색 적중 ${s.found} / ${s.questions}` : ''}`;
      if (s.id === 'query') return `등록된 질의 ${s.queries} · 질의 언어 ${s.targets}개${s.conformance && !s.conformance.error ? ` · 저장소 간 일치 ${s.conformance.agree} / ${s.conformance.queries}` : ''}`;
      if (s.id === 'decide') return `결정표 ${s.decisions} · 규칙 ${s.rules} · Action ${s.actions}${s.agreement && s.agreement.cases ? ` · 판정 일치율 ${pct(s.agreement.rate)}` : ''}`;
      return !s.questions ? '등록된 검증 질문 없음' : s.accuracy === null || s.accuracy === undefined ? `검증 질문 ${s.questions} · 측정 제외` : `검증 질문 ${s.questions} · 정답률 ${Math.round(s.accuracy * 100)}% · 근거 제시율 ${Math.round((s.grounded || 0) * 100)}%`;
    };
    const gate = (g) => (g.unmeasured ? qaDash(`${qaGateSay(g)} · 연결 필요`, qaNote(g)) : g.passed ? kChip(`${qaGateSay(g)} · 현재 ${gateValue(g, g.value)}`, 'ok') : `<button class="k-chip warn" data-act="issopen" data-key="${esc(gateKey(g))}">${esc(qaGateSay(g))} · 현재 ${gateValue(g, g.value)}</button>`);
    const rows = fl.steps.map((s, i) => { const tab = FLOW[i] ? FLOW[i][3] : '';
      return `<tr><td class="b nw">${i + 1}. ${esc(STEP_WORD[s.id] || s.id)}${s.on === false ? ` ${kChip('꺼짐')}` : ''}</td><td>${say(s)}${s.id === 'project' && s.backends.length && canEdit() ? ' <button class="k-lnk" data-act="sync">데이터 소스 동기화</button>' : ''}</td><td><div class="k-h g6">${(s.gates || []).map(gate).join('') || '<span class="k-s">-</span>'}</div></td><td class="nw">${tab && known(tab) ? `<a class="k-lnk" href="#${tab}">열기${ki('chevR', 14, 1.75)}</a>` : ''}</td></tr>`; }).join('');
    return `<div class="k-x"><table class="k-t s"><thead><tr><th scope="col">단계</th><th scope="col">측정 값</th><th scope="col">통과 조건</th><th scope="col"></th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  const STEP_WORD = { source: '데이터 소스', define: '온톨로지 정의', bind: 'Binding 검사', project: '그래프 저장소 반영', index: '문서 · 벡터 색인', query: '질의', decide: '판정 · 처리', check: '검증' };

  function qaMonScene(m) {
    const short = { source: '소스', convert: '변환', ontology: '구축', store: '저장소', use: '활용', verify: '검증' };
    const seg = [['', '전체'], ...m.floors.map((f) => [f.id, short[f.id] || f.label])].map(([k, l]) => `<button class="${S.mon.focus === k ? 'on' : ''}" data-act="mfocus" data-k="${k}">${esc(l)}</button>`).join('');
    const active = m.faults.find((f) => f.on);
    const fault = m.faults.length && isOntoAdmin() ? `<select class="k-in sm" style="width:auto;max-width:220px" data-in="mfault" aria-label="장애 테스트 항목"${active ? ' disabled' : ''}>${m.faults.map((f, i) => `<option value="${i}"${i === S.mon.fault ? ' selected' : ''}>${esc(f.label)}</option>`).join('')}</select>
      <button class="k-btn sm" data-act="qaMonFault"${S.mon.busy ? ' disabled' : ''}>${S.mon.busy ? '처리 중' : active ? '복구' : '장애 테스트'}</button>` : '';
    return `<div class="qa-scene"><div class="k-h g12" style="padding:0 0 12px"><div class="k-seg mseg" role="group" aria-label="보는 범위">${seg}</div><span class="k-push k-h">${fault}${S.st.pipeline === 'p1' || !canEdit() ? '' : '<button class="k-btn sm" data-act="mpipedel">파이프라인 삭제</button>'}</span></div>
      <div class="mstage"><div class="mlink"><i class="dot mlive"></i>${QA_MON_EVERY / 1000}초마다 갱신</div>${m.notice ? `<div class="mnote">${esc(m.notice)}</div>` : ''}<div id="mscene"></div>
        <div class="mlegend"><span><i style="background:#22a06b"></i>정상</span><span><i style="background:#e2a03f"></i>주의</span><span><i style="background:#e5484d"></i>장애</span></div><div class="mtick" id="mtick">${monitorTicker(m)}</div></div></div>`;
  }

  function qaMonView() {
    const m = S.mon.st;
    const lead = '파이프라인 처리 상태, 결정 로그, 알림 규칙을 확인합니다.';
    const next = kNext([['inbox', '할 일 · 알림'], ['connect', '연동 · API'], ['evidence', '근거 지도']]);
    if (!m) return kHead('파이프라인 관제', lead) + qaWait('파이프라인을 점검하는 중입니다.') + next;
    const head = kHead('파이프라인 관제', lead, `<span id="qa-monchip">${qaMonChip(m)}</span><button class="k-btn" data-act="qaMonCheck"${S.qa2.monBusy ? ' disabled' : ''}>${ki('reload', 16, 1.75)}${S.qa2.monBusy ? '점검 중' : '재점검'}</button>`);
    const audit = known('sys-audit') && isSysAdmin() ? '<a class="k-lnk k-push" href="#sys-audit">감사 로그</a>' : '';
    return `${head}<section class="k-card pad k-v g12" aria-labelledby="qa-pl"><div class="k-h sb"><h2 class="k-h2" id="qa-pl">처리 상태</h2><span class="k-h g12"><span class="k-s" id="qa-monat">마지막 점검 ${esc(hms(m.measured_at))}</span><button class="k-lnk" data-act="qaMonSceneGo" aria-expanded="${S.qa2.scene}">${S.qa2.scene ? '그림 접기' : '그림 보기'}</button></span></div>
        <ol class="qa-steps" id="qa-montiles">${qaMonTiles(m)}</ol>${S.qa2.scene ? qaMonScene(m) : ''}</section>
      <div class="k-cols"><section class="k-card" aria-labelledby="qa-log" style="flex:3 1 560px"><div class="k-ch"><h2 id="qa-log">결정 로그</h2>${audit}</div><div id="qa-monlog">${qaMonLog()}</div></section>
        <section class="k-card" aria-labelledby="qa-watch" style="flex:2 1 340px"><div class="k-ch" style="border-bottom:1px solid var(--row)"><h2 id="qa-watch">알림 규칙</h2>${isOntoAdmin() ? '<a class="k-lnk k-push" href="#flow?edit=1">알림 기준</a>' : ''}</div><div id="qa-monrules">${qaMonRules(m)}</div></section></div>
      <section class="k-card" aria-labelledby="qa-stg"><div class="k-ch"><h2 id="qa-stg">단계별 측정</h2><div class="k-push"><button class="k-lnk" data-act="qaMonSteps" aria-expanded="${S.qa2.steps}">${S.qa2.steps ? '접기' : '보기'}</button></div></div>${S.qa2.steps ? qaMonSteps() : ''}</section>${next}`;
  }

  async function qaMonLoadLog() {
    try { S.qa2.log = await api('qa/decisions'); } catch (e) { S.qa2.log = { error: e.message, rows: [], total: 0 }; }
    const box = $('#qa-monlog');
    if (box && S.tab === 'monitor') box.innerHTML = qaMonLog();
  }

  async function qaMonTick() {
    clearTimeout(S.qa2.monTimer);
    S.qa2.monTimer = 0;
    if (S.tab !== 'monitor') return;
    if (!document.hidden && !S.qa2.monBusy) {
      try {
        const m = await api('monitor');
        const first = !S.mon.st, moved = S.mon.st && m.shape !== S.mon.shape;
        S.mon.st = m;
        if (S.tab !== 'monitor') return;
        if (first || (S.qa2.scene && (moved || !$('#mscene svg')))) { S.qa2.monTimer = setTimeout(qaMonTick, QA_MON_EVERY); render(); return; }
        const put = (id, html) => { const box = $(id); if (box) box.innerHTML = html; };
        put('#qa-monchip', qaMonChip(m)); put('#qa-montiles', qaMonTiles(m)); put('#qa-monrules', qaMonRules(m));
        put('#qa-monat', `마지막 점검 ${esc(hms(m.measured_at))}`);
        if (S.qa2.scene && $('#mscene svg')) { window.SpaceScene.patch(m); if (m.measured) window.SpaceScene.sweep(); put('#mtick', monitorTicker(m)); }
        if (m.measured) qaMonLoadLog();
      } catch (e) { fail(e); }
    }
    S.qa2.monTimer = setTimeout(qaMonTick, QA_MON_EVERY);
  }

  screen('monitor', { area: 'work', word: '파이프라인 관제', view: qaMonView,
    after: () => {
      const m = S.mon.st;
      if (m && S.qa2.scene && $('#mscene')) { window.SpaceScene.mount($('#mscene'), m); S.mon.shape = m.shape; window.SpaceScene.focus(S.mon.focus); }
      if (!S.qa2.monTimer) qaMonTick();
      if (!S.qa2.log) qaMonLoadLog();
      if (!S.fl) qaLoadFlow();
      if (!S.home.box && !S.home.busy && !S.home.err) loadInbox();
    } });

  Object.assign(ACT, {
    qaMonCheck: async () => {  // measured again now: the stages, the conditions, then the board
      if (S.qa2.monBusy) return;
      S.qa2.monBusy = true; render();
      try { S.fl = await api('flow'); S.fl.at = new Date().toTimeString().slice(0, 5); S.mon.st = await api('monitor'); await qaMonLoadLog(); toast('파이프라인을 재점검했습니다.'); } catch (e) { fail(e); }
      S.qa2.monBusy = false; render();
    },
    qaMonSceneGo: () => { S.qa2.scene = !S.qa2.scene; render(); },
    qaMonSteps: () => { S.qa2.steps = !S.qa2.steps; render(); },
    qaMonFault: async () => {
      const m = S.mon.st, f = m.faults.find((x) => x.on) || m.faults[S.mon.fault];
      if (!f || S.mon.busy) return;
      S.mon.busy = true; render();
      try { await api(f.on ? 'detach' : 'attach', { name: f.module }); stale(); S.st = await api('state'); S.fl = null; S.mon.st = await api('monitor'); } catch (e) { fail(e); }
      S.mon.busy = false; render();
    },
  });

  // ---- OPS-04 근거 지도 --------------------------------------------------------------------------------------------

  const QA_EV_TABS = [['evidence', '근거 지도'], ['docs', '문서'], ['explorer', '자산 탐색기'], ['map', '자산 그래프']];
  const QA_GAPS = 8;  // the gaps shown at a time
  const qaEvTabs = () => `<nav class="k-seg self" aria-label="근거 지도">${QA_EV_TABS.map(([k, w]) => `<a href="#${k}" class="${S.tab === k ? 'on' : ''}"${S.tab === k ? ' aria-current="page"' : ''}>${w}</a>`).join('')}</nav>`;

  async function qaLoadEv() {
    if (S.qa2.evBusy) return;
    S.qa2.evBusy = true;
    try { S.qa2.ev = await api('qa/evidence'); } catch (e) { S.qa2.ev = { error: e.message }; }
    S.qa2.evBusy = false;
    if (S.tab === 'evidence') render();
  }

  function qaEvView() {
    const ev = S.qa2.ev;
    const lead = '정의와 규칙의 근거 자료를 Object별로 확인합니다.';
    const head = kHead('근거 지도', lead) + qaEvTabs();
    const next = kNext([['ruleagent', '규칙 초안'], ['concepts', '개념 초안'], ['objmgr', 'Object'], ['objects', 'Entity']]);
    if (!ev) return head + qaWait('근거 지도를 불러오는 중입니다.') + next;
    if (ev.error) return head + kEmpty('근거 지도를 불러오지 못했습니다', ev.error, '<button class="k-btn" data-act="qaEvReload">다시 시도</button>') + next;
    const docs = ev.documents;
    const upload = canEdit() ? `<a class="k-btn" href="#catalog">${ki('plus', 16, 1.75)}자료 업로드</a>` : '';
    if (!docs.length && !ev.objects.length) return head + kEmpty('등록된 자료가 없습니다', '', upload) + next;
    const CELL = { all: ['qa-c all', '있음'], some: ['qa-c some', '일부'], none: ['qa-c none', '없음'] };
    const cell = (o, d) => { const c = o.cells[d.name], [cls, w] = CELL[c.state];
      return `<td class="tight">${c.count ? `<button class="${cls}" data-act="qaEvDoc" data-doc="${esc(d.name)}" title="${esc(`${d.name} · ${c.entities.join(', ')}${c.count > c.entities.length ? ` 외 ${c.count - c.entities.length}` : ''}`)}">${w}${c.state === 'some' ? ` ${c.count}/${o.entities}` : ''}</button>` : `<span class="${cls}">${w}</span>`}</td>`; };
    const src = (o) => `<td class="tight qa-srccol">${!ev.connected ? '<span class="qa-c wait">연결 필요</span>' : `<a class="qa-c ${o.source === 'all' ? 'all' : o.source === 'some' ? 'some' : 'none'}" href="#sources" title="Binding Entity ${o.bound} / ${o.entities}">${o.source === 'all' ? '있음' : o.source === 'some' ? `일부 ${o.bound}/${o.entities}` : '없음'}</a>`}</td>`;
    const legend = [['all', '있음'], ['some', '일부'], ['none', '없음'], ...(ev.connected ? [] : [['wait', '연결 필요']])].map(([k, w]) => `<span class="qa-leg"><i class="qa-c ${k}"></i>${w}</span>`).join('');
    const matrix = `<section class="k-card" aria-labelledby="qa-map" style="flex:3 1 ${Math.max(640, 300 + docs.length * 92)}px"><div class="k-ch"><h2 id="qa-map">Object × 자료</h2><div class="k-wrap g8 k-push k-i3 k-13">${legend}</div></div>
      ${ev.objects.length ? `<div class="k-x"><table class="k-t"><thead><tr><th class="k-13" scope="col">Object</th>${docs.map((d) => `<th class="c" scope="col" title="${esc(d.kind_label)}">${esc(d.name)}</th>`).join('')}<th class="c qa-srccol" scope="col">소스 DB</th></tr></thead>
        <tbody>${ev.objects.map((o) => `<tr><td class="b nw" style="padding:8px 12px">${esc(o.label)}<span class="k-s">@${esc(o.name)}</span></td>${docs.map((d) => cell(o, d)).join('')}${src(o)}</tr>`).join('')}</tbody></table></div>
        <p class="k-cf">Object ${ev.objects.length}개 · 칸: 자료에 언급된 Entity 수</p>` : '<p class="k-cf">Object가 없습니다.</p>'}</section>`;
    const gapRow = (g) => `<a class="qa-gap" href="#${g.kind === 'rule' ? 'semrules' : 'objmgr'}"><span class="k-14"><b class="k-b">${esc(g.who)}</b> · ${esc(g.what)}</span><span class="k-s">${esc(g.sub)}</span></a>`;
    const gapN = Math.min(S.qa2.gapN || QA_GAPS, ev.gaps.length);
    const gaps = `<section class="k-card" aria-labelledby="qa-gap"><div class="k-ch" style="border-bottom:1px solid var(--row)"><h2 id="qa-gap">근거 누락</h2>${ev.gaps.length ? kChip(String(ev.gaps.length), 'warn') : kChip('없음', 'ok')}</div>
      ${ev.gaps.slice(0, gapN).map(gapRow).join('') || '<p class="k-cf">근거 누락이 없습니다.</p>'}${ev.gaps.length > QA_GAPS ? `<p class="k-cf line">${gapN} / ${ev.gaps.length}건 표시${gapN < ev.gaps.length ? ` · <button class="k-lnk flat" data-act="qaEvMore">${Math.min(QA_GAPS, ev.gaps.length - gapN)}건 더 보기</button>` : ` · <button class="k-lnk flat" data-act="qaEvMore" data-v="fold">접기</button>`}</p>` : ''}</section>`;
    const unbound = ev.unbound_total ? `<section class="k-v qa-orph" aria-labelledby="qa-orph"><h2 class="k-15" id="qa-orph" style="margin:0;font-weight:600">Mapping 미정 Entity</h2>
      ${ev.unbound.slice(0, 6).map((u) => `<div class="k-14" style="display:flex;justify-content:space-between;gap:12px"><span>${esc(u.label)}<span class="k-s">@${esc(u.name)}</span></span><span class="k-mut">${esc(u.why)}</span></div>`).join('')}${ev.unbound_total > 6 ? `<span class="k-s">외 ${ev.unbound_total - 6}개</span>` : ''}
      <a class="k-lnk flat" href="#objects">Entity 보기${ki('chevR', 14, 1.75)}</a></section>` : '';
    const STATE = { embedded: 'ok', pending: 'b', failed: 'bad', off: '', none: '' };
    const rows = docs.map((d) => `<tr><td><button class="qa-docname" data-act="qaEvDoc" data-doc="${esc(d.name)}"><b class="k-b">${esc(d.name)}</b></button><br><span class="k-s">${esc(d.kind_label)}${d.fixed ? ' · 기본 자료' : ' · 업로드'}</span></td><td>항목 ${count(d.sections)} · 청크 ${count(d.passages)}</td><td>Entity ${count(d.entities)} · 언급 ${count(d.mentions)}회</td><td>${kChip(d.state_label, STATE[d.state] || '')}</td></tr>`).join('');
    const materials = `<section class="k-card" aria-labelledby="qa-mat"><div class="k-ch"><h2 id="qa-mat">자료</h2>${kChip(String(docs.length))}<span class="k-push"></span>${upload}</div>
      ${docs.length ? `<div class="k-x"><table class="k-t"><thead><tr><th scope="col">자료</th><th scope="col">구성</th><th scope="col">정의 연결</th><th scope="col">상태</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="k-cf">등록된 자료가 없습니다.</p>'}</section>`;
    return `${head}<div class="k-cols">${matrix}<div class="qa-side" style="flex:2 1 320px;min-width:0">${gaps}${unbound}</div></div>${materials}${next}`;
  }

  screen('evidence', { area: 'work', word: '근거 지도', view: qaEvView, after: () => { if (!S.qa2.ev && !S.qa2.evBusy) qaLoadEv(); } });
  // the three older screens under 근거 지도, as they were, with the row that leads back to it
  screen('docs', { area: 'work', word: '문서', under: 'evidence', view: () => qaEvTabs() + viewDocs(),
    after: () => {
      mountDocs();
      const want = S.qa2.docWant, dg = S.dg;
      if (want && dg && !dg.busy && dg.nodes && S.dgx.of === dg) {  // came from a cell of the map: that document in the middle
        S.qa2.docWant = '';
        const n = dg.nodes.find((x) => x.module === 'document' && x.label === want);
        // a section named with it is picked inside that document
        const sec = n && S.qa2.secWant ? dg.nodes.find((x) => x.module === 'section' && x.label === S.qa2.secWant && dg.edges.some((e) => (e.source === n.id && e.target === x.id) || (e.target === n.id && e.source === x.id))) : null;
        S.qa2.secWant = '';
        const go = sec || n;
        if (go && S.dgx.sel !== go.id) dgxPick(go.id);
      }
    } });
  screen('explorer', { area: 'work', word: '자산 탐색기', under: 'evidence', view: () => qaEvTabs() + viewExplorer(),
    after: () => { if (!S.ex.tree && !S.ex.loading) { S.ex.loading = true; loadExplorer().finally(() => { S.ex.loading = false; }); } } });
  screen('map', { area: 'work', word: '자산 그래프', under: 'evidence', view: () => qaEvTabs() + viewMap(),
    after: () => {
      if (!S.amap) api('space/map').then((x) => { S.amap = x; render(); }).catch((e) => { S.amap = { error: e.message }; render(); });
      else if (!S.amap.error) mountGraph($('#mapgraph'), S.amap, { key: 'map', pos: S.mappos, sel: () => S.mapsel, tag: (n) => KIND[n.table] || n.table, clear: () => { S.mapsel = null; S.mapn = null; const box = $('#mapside'); if (box) box.innerHTML = mapSide(); },
        pick: async (id) => { S.mapsel = id; drawGraph(); try { S.mapn = await api('space/map/node?node=' + encodeURIComponent(id)); $('#mapside').innerHTML = mapSide(); } catch (e) { fail(e); } } });
    } });

  Object.assign(ACT, {
    qaEvReload: () => { S.qa2.ev = null; render(); },
    qaEvMore: (t) => { S.qa2.gapN = t.dataset.v === 'fold' ? QA_GAPS : (S.qa2.gapN || QA_GAPS) + QA_GAPS; render(); },
    qaEvDoc: (t) => { S.qa2.docWant = t.dataset.doc; location.hash = '#docs'; },
  });
