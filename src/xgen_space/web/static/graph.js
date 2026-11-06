/* The knowledge graph. WebGL through sigma, loaded the first time a graph opens. A layout runs once and stops, so nothing
   drifts after it settles. Colors come from the data: one per module, or one per community when a single module holds all. */
window.SpaceGraph = (function () {
  'use strict';

  const PALETTE = ['#4169E1', '#e3493b', '#00bfa0', '#cf6d17', '#bd7ebe', '#0f558a', '#2fb96b', '#4421af', '#f4b942',
    '#84a3e1', '#9b3a31', '#00a3c7', '#b300b3', '#0f705d', '#ff8fc0', '#5a2c6d'];
  const ALONE = 'c:alone';
  const FOCUS = '#F57F17', DIM = '#E2E2E2', RING = '#FFFFFF', EDGE = '#BEC6D1', SUBTYPE = '#8FA0B5', LABELS_ALL = 90;
  const LAYOUTS = [['circular', 'Circular'], ['circlepack', 'Circlepack'], ['random', 'Random'], ['noverlap', 'Noverlaps'],
    ['force', 'Force Directed'], ['forceatlas', 'Force Atlas']];
  const ICON = {
    play: '<path d="M7 5l12 7-12 7z"/>',
    layout: '<circle cx="6" cy="6" r="1.6"/><circle cx="12" cy="6" r="1.6"/><circle cx="18" cy="6" r="1.6"/><circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/><circle cx="6" cy="18" r="1.6"/><circle cx="12" cy="18" r="1.6"/><circle cx="18" cy="18" r="1.6"/>',
    left: '<path d="M4 12a8 8 0 1 0 2.6-5.9L4 8.6"/><path d="M4 3.6v5h5"/>',
    right: '<path d="M20 12a8 8 0 1 1-2.6-5.9L20 8.6"/><path d="M20 3.6v5h-5"/>',
    fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    plus: '<circle cx="11" cy="11" r="7"/><path d="M11 8v6M8 11h6M16.5 16.5L21 21"/>',
    minus: '<circle cx="11" cy="11" r="7"/><path d="M8 11h6M16.5 16.5L21 21"/>',
    full: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
  };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; };

  let kit = null, loading = null, cur = null, ticket = 0;
  const palettes = new Map();  // per graph: a group keeps its color while the page lives, so a module applied later moves nothing
  const prefs = { colorBy: 'auto', nodeLabels: false, edgeLabels: false };

  function load() {
    if (window.GraphKit) { kit = window.GraphKit; return Promise.resolve(); }
    if (!loading) {
      loading = new Promise((ok, no) => {
        const s = document.createElement('script');
        s.src = window.GRAPH_KIT_URL;
        s.onload = () => { kit = window.GraphKit; ok(); };
        s.onerror = () => { loading = null; no(new Error('kit')); };
        document.head.appendChild(s);
      });
    }
    return loading;
  }

  function colorOf(graph, group) {
    if (group === ALONE) return '#AEB7C2';
    if (!palettes.has(graph)) palettes.set(graph, new Map());
    const colors = palettes.get(graph);
    if (!colors.has(group)) colors.set(group, PALETTE[colors.size % PALETTE.length]);
    return colors.get(group);
  }

  const signature = (data) => JSON.stringify([data.nodes.map((n) => [n.id, n.module, n.abstract]),
    data.edges.map((e) => [e.source, e.target, e.label, e.subtype])]);

  // ---- model ---------------------------------------------------------------------------------------------------

  function communities(data) {
    const g = new kit.Graph({ type: 'undirected' });
    data.nodes.forEach((n) => g.addNode(n.id));
    data.edges.forEach((e) => { if (e.source !== e.target && g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target); });
    if (!g.size) return Object.fromEntries(data.nodes.map((n) => [n.id, 0]));
    return kit.louvain(g, { rng: () => 0.5 });
  }

  function groupsOf(data, graph) {
    const useModules = prefs.colorBy === 'module' || (prefs.colorBy === 'auto' && data.clusters.length > 1);
    const out = new Map();
    if (useModules) {
      const label = Object.fromEntries(data.clusters.map((c) => [c.id, c.label]));
      data.nodes.forEach((n) => { const k = 'm:' + n.module; if (!out.has(k)) out.set(k, { key: k, label: label[n.module] || n.module, nodes: [] }); out.get(k).nodes.push(n.id); });
    } else {
      const part = communities(data);
      data.nodes.forEach((n) => {
        const k = graph.degree(n.id) ? 'c:' + part[n.id] : ALONE;
        if (!out.has(k)) out.set(k, { key: k, label: '', nodes: [] });
        out.get(k).nodes.push(n.id);
      });
      const name = Object.fromEntries(data.nodes.map((n) => [n.id, n.label]));
      for (const g of out.values()) {  // a community is called after its best connected member
        const top = g.nodes.reduce((a, b) => (graph.degree(b) > graph.degree(a) ? b : a));
        g.label = g.key === ALONE ? '관계 없음' : (g.nodes.length > 1 ? `${name[top]} 외 ${g.nodes.length - 1}` : name[top]);
      }
    }
    return [...out.values()].sort((a, b) => b.nodes.length - a.nodes.length);
  }

  function build(data) {
    const graph = new kit.Graph({ multi: true, type: 'directed', allowSelfLoops: false });
    data.nodes.forEach((n) => graph.addNode(n.id, { raw: n, x: 0, y: 0, size: 8, label: n.label }));
    const loops = [];
    data.edges.forEach((e, i) => {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) return;
      if (e.source === e.target) { loops.push(e); return; }
      graph.addDirectedEdgeWithKey('e' + i, e.source, e.target, { raw: e, size: 1.3, color: e.subtype ? SUBTYPE : EDGE, label: e.label });
    });
    kit.indexParallelEdgesIndex(graph, { edgeIndexAttribute: 'pi', edgeMaxIndexAttribute: 'pm' });
    graph.forEachEdge((key, a) => {
      const spread = typeof a.pi === 'number' && a.pm ? (a.pi + 1) / (a.pm + 1) : 0;
      graph.mergeEdgeAttributes(key, { type: 'curved', curvature: 0.16 + spread * 0.5 });
    });
    const degrees = graph.nodes().map((n) => graph.degree(n));
    const lo = Math.min(...degrees, 0), span = Math.max(Math.max(...degrees, 1) - lo, 1);
    const big = data.nodes.length > 120;
    graph.forEachNode((n) => graph.setNodeAttribute(n, 'size', (big ? 4 : 7) + (big ? 12 : 13) * Math.sqrt((graph.degree(n) - lo) / span)));
    return { graph, loops };
  }

  function paint(st) {
    st.groups = groupsOf(st.data, st.graph);
    st.groupOf = {};
    st.groups.forEach((g) => { g.color = colorOf(st.key, g.key); g.nodes.forEach((id) => { st.groupOf[id] = g; }); });
    st.graph.forEachNode((id, a) => {
      const color = st.groupOf[id].color;
      st.graph.mergeNodeAttributes(id, a.raw.abstract ? { color: RING, borderColor: color, ring: 0.3 } : { color, borderColor: RING, ring: 0.14 });
    });
  }

  // ---- layouts: computed once, then still -------------------------------------------------------------------------

  function seed(st, pos) {
    const g = st.graph, centers = {}, keys = st.groups.map((x) => x.key);
    const ring = 60 + 26 * Math.sqrt(g.order);  // a group starts on its own part of the ring, so groups end up apart
    keys.forEach((k, i) => { const a = (2 * Math.PI * i) / Math.max(keys.length, 1); centers[k] = { x: Math.cos(a) * ring, y: Math.sin(a) * ring }; });
    let fresh = 0;
    g.forEachNode((id) => {
      const p = pos[id];
      if (p) { g.mergeNodeAttributes(id, { x: p.x, y: p.y, fixed: true }); return; }
      fresh += 1;
      const known = g.neighbors(id).map((k) => pos[k]).filter(Boolean);
      const c = known.length && Object.keys(pos).length ? { x: known.reduce((s, k) => s + k.x, 0) / known.length, y: known.reduce((s, k) => s + k.y, 0) / known.length } : centers[st.groupOf[id].key];
      const a = hash(id) * Math.PI * 2, r = 12 + hash(id + '.') * 30;
      g.mergeNodeAttributes(id, { x: c.x + Math.cos(a) * r, y: c.y + Math.sin(a) * r, fixed: false });
    });
    return fresh;
  }

  function atlas(g, iterations) {
    const inferred = kit.layouts.forceAtlas2.inferSettings(g);
    const big = g.order > 120;  // LinLog pulls a community together; a small graph reads better evenly spread
    return kit.layouts.forceAtlas2(g, { iterations, settings: { ...inferred, gravity: big ? 0.5 : 1.2, scalingRatio: big ? 6 : 14 + g.order / 2, slowDown: 2, linLogMode: big, adjustSizes: false, barnesHutOptimize: g.order > 250 } });
  }

  function spaced(g, positions) {
    if (positions) Object.entries(positions).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
    return kit.layouts.noverlap(g, { maxIterations: 160, settings: { margin: g.order > 40 ? 16 : 7, ratio: 1.15, gridSize: 24 } });
  }

  function settle(st, pos) {
    const g = st.graph, fresh = seed(st, pos);
    if (fresh) {
      const all = fresh === g.order;
      const placed = atlas(g, all ? 400 : 80);
      Object.entries(placed).forEach(([id, p]) => { if (!g.getNodeAttribute(id, 'fixed')) g.mergeNodeAttributes(id, p); });
      if (all) Object.entries(spaced(g)).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
    }
    g.forEachNode((id, a) => { g.removeNodeAttribute(id, 'fixed'); pos[id] = { x: a.x, y: a.y }; });
  }

  function targets(st, name) {
    const g = st.graph, L = kit.layouts, scale = 90 + g.order * 2;
    g.forEachNode((id) => g.setNodeAttribute(id, 'grp', st.groupOf[id].key));
    if (name === 'circular') return L.circular(g, { scale });
    if (name === 'circlepack') return L.circlepack(g, { hierarchyAttributes: ['grp'], scale });
    if (name === 'random') return L.random(g, { scale: scale * 2, center: 0, rng: (() => { let i = 0; const ids = g.nodes(); return () => hash(ids[Math.floor(i / 2) % ids.length] + (i++ % 2)); })() });
    if (name === 'noverlap') return spaced(g);
    if (name === 'force') return L.force(g, { maxIterations: 300, settings: { attraction: 0.0006, repulsion: 0.3, gravity: 0.0012, inertia: 0.6, maxMove: 60 } });
    return atlas(g, 300);
  }

  function arrange(st, name) {
    const to = targets(st, name);
    kit.animateNodes(st.graph, to, { duration: 380, easing: 'quadraticInOut' }, () => {
      st.graph.forEachNode((id, a) => { st.opt.pos[id] = { x: a.x, y: a.y }; });
      st.renderer.setCustomBBox(null);
      st.renderer.refresh();
      st.renderer.getCamera().animatedReset({ duration: 260 });
    });
    st.layout = name;
    paintTools(st);
  }

  // ---- what shows ---------------------------------------------------------------------------------------------------

  const selected = (st) => (st.opt.sel ? st.opt.sel() : null);
  const focusOf = (st) => {
    const id = st.hover || selected(st);
    return id && st.graph.hasNode(id) ? id : null;
  };

  function nodeShown(st, id, a) {
    if (st.off.has(st.groupOf[id].key)) return false;
    return !st.opt.shown || !!st.opt.shown('node', a.raw);
  }

  function reducers(st) {
    return {
      nodeReducer(id, a) {
        const o = { ...a, label: st.opt.label ? st.opt.label(a.raw) : a.raw.label };
        if (!nodeShown(st, id, a)) { o.hidden = true; return o; }
        if (prefs.nodeLabels) o.forceLabel = true;
        const f = focusOf(st);
        if (!f) return o;
        if (id === f || st.graph.areNeighbors(id, f)) {
          o.highlighted = true; o.forceLabel = true; o.zIndex = 2;
          if (id === selected(st)) o.borderColor = FOCUS;
        } else {
          o.color = DIM; o.borderColor = '#F1F2F4'; o.label = ''; o.forceLabel = false; o.zIndex = 0;
        }
        return o;
      },
      edgeReducer(key, a) {
        const o = { ...a, label: '' }, g = st.graph, s = g.source(key), t = g.target(key);
        const seen = nodeShown(st, s, g.getNodeAttributes(s)) && nodeShown(st, t, g.getNodeAttributes(t));
        if (!seen || (st.opt.shown && !st.opt.shown('edge', a.raw))) { o.hidden = true; return o; }
        if (prefs.edgeLabels) { o.label = a.raw.label; o.forceLabel = true; }
        const f = focusOf(st);
        if (!f) return o;
        if (s !== f && t !== f) { o.hidden = true; return o; }
        o.color = FOCUS; o.size = 1.8; o.label = a.raw.label; o.forceLabel = true; o.zIndex = 1;
        return o;
      },
    };
  }

  function drawLoops(st) {
    const c = st.loopCanvas, r = st.renderer;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1, w = st.stage.clientWidth, h = st.stage.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
    const x = c.getContext('2d');
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    x.clearRect(0, 0, w, h);
    const f = focusOf(st);
    for (const e of st.loops) {
      const d = r.getNodeDisplayData(e.source);
      if (!d || d.hidden || !nodeShown(st, e.source, st.graph.getNodeAttributes(e.source))) continue;
      if (f && f !== e.source) continue;
      const p = r.framedGraphToViewport(d), size = r.scaleSize(d.size), rad = Math.max(size * 0.8, 8), on = f === e.source;
      x.beginPath();
      x.arc(p.x + size * 0.8, p.y - size * 0.8, rad, 0, Math.PI * 2);
      x.lineWidth = on ? 1.8 : 1.2;
      x.strokeStyle = on ? FOCUS : EDGE;
      x.stroke();
      if (on || prefs.edgeLabels) {
        x.font = '500 10.5px Pretendard, "Malgun Gothic", sans-serif';
        x.fillStyle = '#5b6675';
        x.textAlign = 'left';
        x.fillText(e.label, p.x + size * 0.8 + rad + 4, p.y - size * 0.8 + 3);
      }
    }
  }

  // ---- the frame around it --------------------------------------------------------------------------------------------

  const tool = (act, icon, title) => `<button type="button" data-g="${act}" title="${title}" aria-label="${title}"><svg viewBox="0 0 24 24">${ICON[icon]}</svg></button>`;

  function frame(el) {
    el.innerHTML = `<div class="kg-stage"></div><canvas class="kg-loops"></canvas>
      <div class="kg-find"><input type="search" placeholder="Node 검색" aria-label="Node 검색" autocomplete="off"><div class="kg-hits" hidden></div></div>
      <div class="kg-tools">${tool('run', 'play', '레이아웃 다시 실행')}${tool('layouts', 'layout', '레이아웃 선택')}${tool('ccw', 'left', '왼쪽으로 회전')}${tool('cw', 'right', '오른쪽으로 회전')}${tool('fit', 'fit', '화면에 맞춤')}${tool('in', 'plus', '확대')}${tool('out', 'minus', '축소')}${tool('full', 'full', '전체 화면')}${tool('prefs', 'gear', '표시 설정')}</div>
      <div class="kg-pop" data-pop="layouts" hidden></div><div class="kg-pop" data-pop="prefs" hidden></div>
      <div class="kg-foot"><div class="kg-legend"></div><div class="kg-status"></div></div>`;
  }

  function paintTools(st) {
    const pop = st.el.querySelector('[data-pop=layouts]');
    pop.innerHTML = LAYOUTS.map(([k, l]) => `<button type="button" data-layout="${k}" class="${st.layout === k ? 'on' : ''}">${l}</button>`).join('');
  }

  function paintPrefs(st) {
    const pick = (v, l) => `<button type="button" data-color="${v}" class="${prefs.colorBy === v ? 'on' : ''}">${l}</button>`;
    const check = (k, l) => `<label><input type="checkbox" data-pref="${k}"${prefs[k] ? ' checked' : ''}>${l}</label>`;
    st.el.querySelector('[data-pop=prefs]').innerHTML = `<div class="kg-cap">색상 기준</div>${pick('auto', '자동')}${pick('module', '모듈')}${pick('community', 'Community')}
      <div class="kg-cap">라벨</div>${check('nodeLabels', 'Node 라벨 항상 표시')}${check('edgeLabels', 'Edge 라벨 항상 표시')}`;
  }

  function paintLegend(st) {
    const rows = st.groups.slice(0, 14).map((g) => `<button type="button" data-group="${esc(g.key)}" class="${st.off.has(g.key) ? 'off' : ''}"><i style="background:${g.color}"></i>${esc(g.label)}<span>${g.nodes.length}</span></button>`).join('');
    const rest = st.groups.length > 14 ? `<div class="kg-more">외 ${st.groups.length - 14}개 그룹</div>` : '';
    st.el.querySelector('.kg-legend').innerHTML = rows + rest;
  }

  function paintStatus(st) {
    const shown = st.graph.filterNodes((id, a) => nodeShown(st, id, a)).length;
    const edges = st.graph.filterEdges((k, a, s, t) => nodeShown(st, s, st.graph.getNodeAttributes(s)) && nodeShown(st, t, st.graph.getNodeAttributes(t)) && (!st.opt.shown || st.opt.shown('edge', a.raw))).length;
    st.el.querySelector('.kg-status').textContent = `Node ${shown} · Edge ${edges + st.loops.length}`;
  }

  function closePops(st, except) {
    st.el.querySelectorAll('.kg-pop').forEach((p) => { if (p.dataset.pop !== except) p.hidden = true; });
  }

  function find(st, text) {
    const box = st.el.querySelector('.kg-hits'), q = text.trim().toLowerCase();
    if (!q) { box.hidden = true; return; }
    const hits = st.data.nodes.filter((n) => [n.label, n.id, n.table].some((v) => String(v || '').toLowerCase().includes(q))).slice(0, 8);
    box.innerHTML = hits.length ? hits.map((n) => `<button type="button" data-hit="${esc(n.id)}"><i style="background:${st.groupOf[n.id].color}"></i>${esc(n.label)}<span>${esc(n.id)}</span></button>`).join('') : '<div class="kg-none">일치하는 Node가 없습니다</div>';
    box.hidden = false;
  }

  function goTo(st, id) {
    const d = st.renderer.getNodeDisplayData(id);
    if (d) st.renderer.getCamera().animate({ x: d.x, y: d.y, ratio: Math.min(st.renderer.getCamera().ratio, 0.6) }, { duration: 360 });
  }

  function wire(st) {
    const { el, renderer } = st, cam = renderer.getCamera();
    el.addEventListener('click', (ev) => {
      const b = ev.target.closest('button');
      if (!b || !el.contains(b)) return;
      const act = b.dataset.g;
      if (act === 'run') arrange(st, st.layout);
      else if (act === 'layouts' || act === 'prefs') { const p = el.querySelector(`[data-pop=${act}]`); closePops(st, act); p.hidden = !p.hidden; }
      else if (act === 'ccw') cam.animate({ angle: cam.angle - Math.PI / 8 }, { duration: 200 });
      else if (act === 'cw') cam.animate({ angle: cam.angle + Math.PI / 8 }, { duration: 200 });
      else if (act === 'fit') cam.animatedReset({ duration: 260 });
      else if (act === 'in') cam.animatedZoom({ duration: 200 });
      else if (act === 'out') cam.animatedUnzoom({ duration: 200 });
      else if (act === 'full') { if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen(); }
      if (b.dataset.layout) { closePops(st); arrange(st, b.dataset.layout); }
      if (b.dataset.color) {
        prefs.colorBy = b.dataset.color;
        st.off.clear();
        paint(st); paintLegend(st); paintPrefs(st); paintStatus(st); renderer.refresh();
      }
      if (b.dataset.group) {
        if (st.off.has(b.dataset.group)) st.off.delete(b.dataset.group); else st.off.add(b.dataset.group);
        paintLegend(st); paintStatus(st); renderer.refresh();
      }
      if (b.dataset.hit) {
        const box = el.querySelector('.kg-find input');
        box.value = '';
        el.querySelector('.kg-hits').hidden = true;
        if (st.opt.pick) st.opt.pick(b.dataset.hit);
        goTo(st, b.dataset.hit);
      }
    });
    el.addEventListener('change', (ev) => {
      if (!ev.target.dataset.pref) return;
      prefs[ev.target.dataset.pref] = ev.target.checked;
      renderer.setSetting('labelRenderedSizeThreshold', prefs.nodeLabels || st.graph.order <= LABELS_ALL ? 0 : 11);
      renderer.refresh();
    });
    const input = el.querySelector('.kg-find input');
    input.addEventListener('input', () => find(st, input.value));
    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') { input.value = ''; find(st, ''); }
      if (ev.key === 'Enter') { const b = el.querySelector('[data-hit]'); if (b) b.click(); }
    });

    renderer.on('enterNode', ({ node }) => { st.hover = node; st.stage.style.cursor = 'pointer'; renderer.refresh({ skipIndexation: true }); });
    renderer.on('leaveNode', () => { st.hover = null; st.stage.style.cursor = ''; renderer.refresh({ skipIndexation: true }); });
    const touch = (event) => String(event.original.type).startsWith('touch');
    renderer.on('clickNode', ({ node, event }) => { if (touch(event) && st.opt.pick) st.opt.pick(node); });
    renderer.on('downNode', ({ node, event }) => {
      if (touch(event)) return;
      st.drag = { node, moved: false };
      if (!renderer.getCustomBBox()) renderer.setCustomBBox(renderer.getBBox());
      event.preventSigmaDefault();
    });
    renderer.getMouseCaptor().on('mousemovebody', (ev) => {
      if (!st.drag) return;
      const p = renderer.viewportToGraph(ev);
      st.graph.mergeNodeAttributes(st.drag.node, { x: p.x, y: p.y });
      st.opt.pos[st.drag.node] = { x: p.x, y: p.y };
      st.drag.moved = true;
      ev.preventSigmaDefault();
      ev.original.preventDefault();
      ev.original.stopPropagation();
    });
    const drop = () => {
      const d = st.drag;
      st.drag = null;
      if (d && !d.moved && st.opt.pick) st.opt.pick(d.node);
    };
    renderer.getMouseCaptor().on('mouseup', drop);
    renderer.on('clickStage', () => { closePops(st); if (st.opt.clear) st.opt.clear(); refresh(); });
    renderer.on('afterRender', () => drawLoops(st));
    st.ro = new ResizeObserver(() => { renderer.resize(); renderer.refresh(); });
    st.ro.observe(st.stage);
  }

  function kill() {
    if (!cur) return;
    if (cur.ro) cur.ro.disconnect();
    // a browser keeps about sixteen WebGL contexts: give these back now rather than whenever it collects them
    const canvases = cur.stage ? [...cur.stage.querySelectorAll('canvas')] : [];
    const gls = canvases.map((c) => c.getContext('webgl2') || c.getContext('webgl')).filter(Boolean);
    if (cur.renderer) cur.renderer.kill();
    gls.forEach((gl) => { const lose = gl.getExtension('WEBGL_lose_context'); if (lose) lose.loseContext(); });
    cur = null;
  }

  function start(el, data, opt) {
    const camera = cur && cur.key === opt.key ? cur.renderer.getCamera().getState() : null;
    const off = cur && cur.key === opt.key ? cur.off : new Set();
    kill();
    frame(el);
    const { graph, loops } = build(data);
    const st = { el, data, opt, graph, loops, key: opt.key, off, sig: signature(data), hover: null, drag: null, layout: 'forceatlas',
      stage: el.querySelector('.kg-stage'), loopCanvas: el.querySelector('.kg-loops') };
    paint(st);
    settle(st, opt.pos);
    const Border = kit.createNodeBorderProgram({ borders: [
      { size: { attribute: 'ring', defaultValue: 0.14 }, color: { attribute: 'borderColor' } },
      { size: { fill: true }, color: { attribute: 'color' } }] });
    try {
      st.renderer = new kit.Sigma(graph, st.stage, {
        allowInvalidContainer: true, defaultNodeType: 'border', defaultEdgeType: 'curved', zIndex: true, stagePadding: 52,
        nodeProgramClasses: { border: Border }, edgeProgramClasses: { curved: kit.createEdgeCurveProgram({ arrowHead: { extremity: 'target', lengthToThicknessRatio: 6.5, widenessToThicknessRatio: 4.6 } }) },
        renderEdgeLabels: true, labelFont: 'Pretendard, "Malgun Gothic", sans-serif', labelSize: 12, labelWeight: '600',
        labelColor: { color: '#1b2330' }, edgeLabelFont: 'Pretendard, "Malgun Gothic", sans-serif', edgeLabelSize: 10.5, edgeLabelWeight: '500',
        edgeLabelColor: { color: '#5b6675' }, labelGridCellSize: 70, labelDensity: 1.4,
        labelRenderedSizeThreshold: prefs.nodeLabels || graph.order <= LABELS_ALL ? 0 : 11,
        minCameraRatio: 0.06, maxCameraRatio: 4, ...reducers(st),
      });
    } catch (e) {
      el.innerHTML = '<div class="kg-none big">이 브라우저에서 WebGL을 사용할 수 없어 그래프를 표시하지 못했습니다. 객체 관리 화면에서 같은 정의를 확인할 수 있습니다.</div>';
      return;
    }
    cur = st;
    wire(st);
    paintTools(st); paintPrefs(st); paintLegend(st); paintStatus(st);
    if (camera) st.renderer.getCamera().setState(camera);
    drawLoops(st);
  }

  function mount(el, data, opt) {
    if (!el) return;
    if (cur && cur.el === el && cur.sig === signature(data)) { cur.opt = opt; refresh(); return; }
    const mine = ++ticket;
    if (!el.firstChild) el.innerHTML = '<div class="kg-none big">그래프를 불러오는 중입니다.</div>';
    load().catch(() => {
      if (document.body.contains(el)) el.innerHTML = '<div class="kg-none big">그래프 모듈을 불러오지 못했습니다. 네트워크를 확인한 뒤 새로고침해 주세요.</div>';
      return false;
    }).then((ok) => {
      if (ok !== false && mine === ticket && document.body.contains(el)) start(el, data, opt);
    });
  }

  function refresh() {
    if (!cur || !document.body.contains(cur.el)) return;
    paintStatus(cur);
    cur.renderer.refresh({ skipIndexation: true });
  }

  function focus(id) {
    if (cur && cur.graph.hasNode(id)) { refresh(); goTo(cur, id); }
  }

  // where a node sits on screen right now, for a test driving the page
  function point(id) {
    if (!cur || !cur.graph.hasNode(id)) return null;
    const p = cur.renderer.framedGraphToViewport(cur.renderer.getNodeDisplayData(id));
    const r = cur.stage.getBoundingClientRect();
    return { x: r.left + p.x, y: r.top + p.y };
  }

  return { mount, refresh, focus, kill, point, state: () => (cur ? { nodes: cur.graph.order, edges: cur.graph.size + cur.loops.length, layout: cur.layout, groups: cur.groups.map((g) => g.label), colorBy: prefs.colorBy } : null) };
})();
