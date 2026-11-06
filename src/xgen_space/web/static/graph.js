/* The knowledge graph. WebGL through sigma, loaded the first time a graph opens. A layout runs once and stops, so nothing
   drifts after it settles. Colors come from the data: one per module, or one per community when a single module holds all.
   A large graph opens with its groups folded into one node each; names sit on their own canvas, clear of the nodes. */
window.SpaceGraph = (function () {
  'use strict';

  const PALETTE = ['#4169E1', '#e3493b', '#00bfa0', '#cf6d17', '#bd7ebe', '#0f558a', '#2fb96b', '#4421af', '#f4b942',
    '#84a3e1', '#9b3a31', '#00a3c7', '#b300b3', '#0f705d', '#ff8fc0', '#5a2c6d'];
  const ALONE = 'c:alone', BUNDLE = 'bundle\u0000';
  const FOCUS = '#F57F17', DIM = '#E2E2E2', RING = '#FFFFFF', EDGE = '#BEC6D1', SUBTYPE = '#8FA0B5', LABELS_ALL = 90;
  const FOLD_AT = 120, LABEL_CELL = 110, EDGE_NAMES = 40, FONT = 'Pretendard, "Malgun Gothic", sans-serif';
  const LAYOUTS =[['circular', 'Circular'], ['circlepack', 'Circlepack'], ['random', 'Random'], ['noverlap', 'Noverlaps'],
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
    fold: '<path d="M7 4l5 5 5-5M7 20l5-5 5 5"/>',
    unfold: '<path d="M7 9l5-5 5 5M7 15l5 5 5-5"/>',
  };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; };
  const short = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

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
    const held = {};  // a module too large to read once open says little: communities divide it further
    data.nodes.forEach((n) => { held[n.module] = (held[n.module] || 0) + 1; });
    const coarse = Math.max(0, ...Object.values(held)) > FOLD_AT;
    const useModules = prefs.colorBy === 'module' || (prefs.colorBy === 'auto' && data.clusters.length > 1 && !coarse);
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
        g.label = g.key === ALONE ? '관계 없음' : name[top];
      }
    }
    return [...out.values()].sort((a, b) => b.nodes.length - a.nodes.length);
  }

  function build(data, width) {
    const graph = new kit.Graph({ multi: true, type: 'directed', allowSelfLoops: false });
    data.nodes.forEach((n) => graph.addNode(n.id, { raw: n, x: 0, y: 0, size: 8, label: n.label }));
    const loops = [], big = data.nodes.length > FOLD_AT;
    data.edges.forEach((e, i) => {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) return;
      if (e.source === e.target) { loops.push(e); return; }
      graph.addDirectedEdgeWithKey('e' + i, e.source, e.target, { raw: e, size: big ? 0.8 : 1.3, color: e.subtype ? SUBTYPE : EDGE, label: e.label });
    });
    kit.indexParallelEdgesIndex(graph, { edgeIndexAttribute: 'pi', edgeMaxIndexAttribute: 'pm' });
    graph.forEachEdge((key, a) => {
      const spread = typeof a.pi === 'number' && a.pm ? (a.pi + 1) / (a.pm + 1) : 0;
      graph.mergeEdgeAttributes(key, { type: 'curved', curvature: 0.16 + spread * 0.5 });
    });
    const degrees = graph.nodes().map((n) => graph.degree(n));
    const lo = Math.min(...degrees, 0), span = Math.max(Math.max(...degrees, 1) - lo, 1);
    const fit = Math.max(0.45, Math.min(1, width / 760));  // a narrow stage holds the same nodes in less room
    graph.forEachNode((n) => graph.setNodeAttribute(n, 'size', fit * ((big ? 3.5 : 7) + (big ? 9 : 13) * Math.sqrt((graph.degree(n) - lo) / span))));
    return { graph, loops, fit, big };
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

  function disc(g, step) {  // the best connected in the middle, links pulling the rest into place, nothing on top of another
    const pull = (id) => g.reduceEdges(id, (s, k, a) => s + (a.weight || 1), 0);
    g.nodes().sort((a, b) => pull(b) - pull(a) || hash(a) - hash(b)).forEach((id, i) => {
      const r = step * Math.sqrt(i + 0.5), a = i * 2.399963;
      g.mergeNodeAttributes(id, { x: Math.cos(a) * r, y: Math.sin(a) * r });
    });
    if (g.size) {
      const placed = kit.layouts.forceAtlas2(g, { iterations: 120, settings: { ...kit.layouts.forceAtlas2.inferSettings(g), gravity: 1, strongGravityMode: true, scalingRatio: 12, slowDown: 3 } });
      Object.entries(placed).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
    }
    Object.entries(spaced(g)).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
    const ids = g.nodes(), cx = ids.reduce((s, id) => s + g.getNodeAttribute(id, 'x'), 0) / ids.length, cy = ids.reduce((s, id) => s + g.getNodeAttribute(id, 'y'), 0) / ids.length;
    let far = 0;
    g.forEachNode((id, a) => { g.mergeNodeAttributes(id, { x: a.x - cx, y: a.y - cy }); far = Math.max(far, Math.hypot(a.x - cx, a.y - cy) + a.size); });
    return far;
  }

  // a large graph settles in two steps, each group in a disc of its own and then the discs by what links them, so groups never
  // mix, a bundle sits where its members will appear, and opening one moves nothing
  function clustered(st) {
    const g = st.graph, inner = new Map(), ties = new Map(), out = {};
    st.groups.forEach((x) => {
      const sub = new kit.Graph({ type: 'undirected' });
      x.nodes.forEach((id) => sub.addNode(id, { size: g.getNodeAttribute(id, 'size') * 1.6 }));
      inner.set(x.key, sub);
    });
    g.forEachEdge((k, a, s, t) => {
      if (!a.raw) return;
      const p = st.groupOf[s].key, q = st.groupOf[t].key;
      if (p === q) { if (!inner.get(p).hasEdge(s, t)) inner.get(p).addEdge(s, t); return; }
      const pair = [p, q].sort().join(BUNDLE);
      ties.set(pair, (ties.get(pair) || 0) + 1);
    });
    const map = new kit.Graph({ type: 'undirected' }), radii = st.groups.map((x) => disc(inner.get(x.key), 24));
    st.groups.forEach((x, i) => map.addNode(x.key, { size: radii[i] + 34 }));
    ties.forEach((n, pair) => { const [p, q] = pair.split(BUNDLE); map.addEdge(p, q, { weight: n }); });
    disc(map, 2.4 * radii.reduce((s, r) => s + r + 34, 0) / Math.max(radii.length, 1));
    st.groups.forEach((x) => {
      const c = map.getNodeAttributes(x.key);
      inner.get(x.key).forEachNode((id, a) => { out[id] = { x: c.x + a.x, y: c.y + a.y }; });
    });
    return out;
  }

  function settle(st, pos) {
    const g = st.graph, fresh = seed(st, pos);
    if (fresh) {
      const all = fresh === g.order;
      if (all && st.big) Object.entries(clustered(st)).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
      else {
        const placed = atlas(g, all ? 400 : 80);
        Object.entries(placed).forEach(([id, p]) => { if (!g.getNodeAttribute(id, 'fixed')) g.mergeNodeAttributes(id, p); });
        if (all) Object.entries(spaced(g)).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
      }
    }
    g.forEachNode((id, a) => { g.removeNodeAttribute(id, 'fixed'); pos[id] = { x: a.x, y: a.y }; });
  }

  function targets(st, name) {
    if (st.big && name === 'forceatlas') return clustered(st);
    const g = st.graph.copy(), L = kit.layouts;
    st.bundles.forEach((x, id) => g.dropNode(id));
    const scale = 90 + g.order * 2;
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
    Object.assign(to, spots(st, (id) => to[id]));
    kit.animateNodes(st.graph, to, { duration: 380, easing: 'quadraticInOut' }, () => {
      st.graph.forEachNode((id, a) => { if (!st.bundles.has(id)) st.opt.pos[id] = { x: a.x, y: a.y }; });
      st.renderer.setCustomBBox(null);
      st.renderer.refresh();
      st.renderer.getCamera().animatedReset({ duration: 260 });
    });
    st.layout = name;
    paintTools(st);
  }

  // ---- folding: a group drawn as one node, what crosses groups drawn once per pair ---------------------------------------

  const foldable = (st) => st.groups.filter((x) => x.nodes.length > 1);
  const folded = (st, id) => { const x = st.groupOf[id]; return !!x.bundle && st.fold.has(x.key); };

  function spots(st, at) {  // a bundle sits among its members and clear of the other bundles
    const q = new kit.Graph();
    st.bundles.forEach((x, id) => {
      const sum = x.nodes.reduce((s, n) => { const p = at(n); return { x: s.x + p.x, y: s.y + p.y }; }, { x: 0, y: 0 });
      q.addNode(id, { x: sum.x / x.nodes.length, y: sum.y / x.nodes.length, size: st.graph.getNodeAttribute(id, 'size') });
    });
    if (q.order < 2) return Object.fromEntries(q.mapNodes((id, a) => [id, { x: a.x, y: a.y }]));
    return kit.layouts.noverlap(q, { maxIterations: 120, settings: { margin: 18, ratio: 1.1, gridSize: 12 } });
  }

  function links(st) {
    const g = st.graph, pairs = new Map();
    st.links.forEach((k) => g.dropEdge(k));
    st.links = [];
    const stand = (id) => (folded(st, id) ? st.groupOf[id].bundle : id);
    g.forEachEdge((k, a, s, t) => {
      const p = stand(s), q = stand(t);
      if (p === q || (p === s && q === t)) return;
      const [u, v] = p < q ? [p, q] : [q, p], pair = u + BUNDLE + v;
      if (!pairs.has(pair)) pairs.set(pair, { u, v, n: 0, of: a.raw });
      pairs.get(pair).n += 1;
    });
    pairs.forEach(({ u, v, n, of }, pair) => {
      g.addDirectedEdgeWithKey(pair, u, v, { of, size: Math.min(0.7 + Math.log2(n) * 0.35, 2.4), color: EDGE, type: 'line', label: n > 1 ? `Edge ${n}` : '' });
      st.links.push(pair);
    });
  }

  function addBundles(st) {
    const g = st.graph, most = Math.max(...st.groups.map((x) => x.nodes.length), 1), fit = Math.max(st.fit, 0.62);
    foldable(st).forEach((x) => {
      x.bundle = BUNDLE + x.key;
      st.bundles.set(x.bundle, x);
      g.addNode(x.bundle, { x: 0, y: 0, size: fit * (11 + 15 * Math.sqrt(x.nodes.length / most)), color: x.color, borderColor: RING, ring: 0.1, label: x.label });
    });
    Object.entries(spots(st, (id) => g.getNodeAttributes(id))).forEach(([id, p]) => g.mergeNodeAttributes(id, p));
    links(st);
  }

  function dropBundles(st) {
    st.bundles.forEach((x, id) => st.graph.dropNode(id));
    st.bundles.clear();
    st.links = [];
  }

  function setFold(st, keys) {
    st.fold = new Set(keys);
    links(st);
    paintFold(st);
    paintStatus(st);
    st.renderer.refresh();
  }

  function unfold(st, x) {
    setFold(st, [...st.fold].filter((k) => k !== x.key));
    look(st, x.nodes, 130);
  }

  function recolor(st) {
    if (st.opt.clear) st.opt.clear();
    dropBundles(st);
    paint(st);
    st.fold = new Set(st.big || st.fold.size ? foldable(st).map((x) => x.key) : []);
    addBundles(st);
    if (st.big) arrange(st, st.layout);
    paintLegend(st); paintPrefs(st); paintFold(st);
    refresh();
  }

  // ---- what is left on screen: the neighbors of a node, or the way between two ----------------------------------------------

  function ties(st, id) {
    const g = st.graph, out = [];
    g.forEachEdge(id, (k, a, s, t) => {
      const other = s === id ? t : s;
      if (a.raw && (!st.opt.shown || st.opt.shown('edge', a.raw)) && nodeShown(st, other, g.getNodeAttributes(other))) out.push(other);
    });
    return out;
  }

  function around(st, id, hops) {
    const out = new Set([id]);
    let ring = [id];
    for (let i = 0; i < hops; i += 1) {
      const next = [];
      ring.forEach((n) => ties(st, n).forEach((m) => { if (!out.has(m)) { out.add(m); next.push(m); } }));
      ring = next;
    }
    return out;
  }

  function shortest(st, from, to) {  // breadth first, and either way along an edge: a relation connects both its ends
    const back = new Map([[from, null]]), todo = [from];
    for (let i = 0; i < todo.length && !back.has(to); i += 1) {
      ties(st, todo[i]).forEach((m) => { if (!back.has(m)) { back.set(m, todo[i]); todo.push(m); } });
    }
    if (!back.has(to)) return null;
    const way = [to];
    while (back.get(way[0]) !== null) way.unshift(back.get(way[0]));
    return way;
  }

  function endRoute(st, id) {
    if (id === st.route.from) return;
    const { from } = st.route, nodes = shortest(st, from, id), keys = new Set();
    if (nodes) nodes.slice(1).forEach((n, i) => st.graph.forEachEdge(n, (k, a, s, t) => { if (a.raw && (s === nodes[i] || t === nodes[i])) keys.add(k); }));
    st.route = nodes ? { from, to: id, nodes, keys } : { from, none: true };
    refresh();
  }

  function tap(st, id) {
    if (st.bundles.has(id)) unfold(st, st.bundles.get(id));
    else if (st.route && !st.route.nodes) endRoute(st, id);
    else if (st.opt.pick) st.opt.pick(id);
  }

  function look(st, ids, pad = 70) {  // the camera takes these in; how far it moves is read off the screen, so a rotated stage needs no care
    const r = st.renderer, cam = r.getCamera(), pts = ids.map((id) => r.getNodeDisplayData(id)).filter(Boolean);
    if (!pts.length) return;
    const on = pts.map((d) => r.framedGraphToViewport(d)), span = (k) => Math.max(...on.map((p) => p[k])) - Math.min(...on.map((p) => p[k]));
    const mid = (k) => (Math.max(...pts.map((d) => d[k])) + Math.min(...pts.map((d) => d[k]))) / 2;
    const room = Math.max(span('x') / Math.max(st.stage.clientWidth - pad * 2, 1), span('y') / Math.max(st.stage.clientHeight - pad * 2, 1));
    cam.animate({ x: mid('x'), y: mid('y'), ratio: clamp(cam.ratio * room, 0.12, 1) }, { duration: 320 });
  }

  // reads the selection and works out what follows from it; everything that draws runs after this
  function sync(st) {
    const s = selected(st), id = s && st.graph.hasNode(s) ? s : null;
    if (id !== st.center) {
      st.center = id;
      st.route = null;
      if (!id) st.hops = 0;
      else if (folded(st, id)) setFold(st, [...st.fold].filter((k) => k !== st.groupOf[id].key));
    }
    st.only = st.route && st.route.nodes ? new Set(st.route.nodes) : (id && st.hops ? around(st, id, st.hops) : null);
    const left = st.only ? [...st.only].sort().join(BUNDLE) : '';
    if (left !== st.left) {
      st.left = left;
      const cam = st.renderer.getCamera();
      if (st.only) { if (!st.back) st.back = cam.getState(); look(st, [...st.only]); }
      else if (st.back) { cam.animate(st.back, { duration: 280 }); st.back = null; }
    }
    paintNear(st);
  }

  // ---- what shows ---------------------------------------------------------------------------------------------------

  const selected = (st) => (st.opt.sel ? st.opt.sel() : null);
  const focusOf = (st) => {
    const id = st.hover || selected(st);
    return id && st.graph.hasNode(id) && seen(st, id, st.graph.getNodeAttributes(id)) ? id : null;
  };

  function nodeShown(st, id, a) {
    if (st.off.has(st.groupOf[id].key)) return false;
    return !st.opt.shown || !!st.opt.shown('node', a.raw);
  }

  function seen(st, id, a) {
    const x = st.bundles.get(id);
    if (x) return !st.only && st.fold.has(x.key) && !st.off.has(x.key) && (!st.opt.shown || x.nodes.some((n) => st.opt.shown('node', st.graph.getNodeAttribute(n, 'raw'))));
    if (!nodeShown(st, id, a)) return false;
    return st.only ? st.only.has(id) : !folded(st, id);
  }

  function reducers(st) {
    return {
      nodeReducer(id, a) {
        const o = { ...a, label: !a.raw ? a.label : (st.opt.label ? st.opt.label(a.raw) : a.raw.label) };
        if (!seen(st, id, a)) { o.hidden = true; return o; }
        if (prefs.nodeLabels) o.forceLabel = true;
        if (st.only) {
          const mine = id === selected(st) || (st.route && st.route.nodes);
          if (mine) { o.highlighted = true; o.forceLabel = true; o.zIndex = 2; }
          if (id === selected(st)) o.borderColor = FOCUS;
          return o;
        }
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
        const o = { ...a, label: '' }, g = st.graph, s = g.source(key), t = g.target(key), raw = a.raw || a.of;
        const both = seen(st, s, g.getNodeAttributes(s)) && seen(st, t, g.getNodeAttributes(t));
        if (!both || (st.opt.shown && !st.opt.shown('edge', raw))) { o.hidden = true; return o; }
        const word = a.raw ? a.raw.label : a.label;
        if (prefs.edgeLabels) { o.label = word; o.forceLabel = true; }
        const way = st.route && st.route.keys;
        if (way && !way.has(key)) { o.hidden = true; return o; }
        const f = st.only ? selected(st) : focusOf(st);
        if (!f) return o;
        if (!way && s !== f && t !== f) { if (!st.only) o.hidden = true; return o; }
        o.color = FOCUS; o.size = Math.max(a.size, 1.8); o.zIndex = 1;
        if (way || g.degree(f) <= EDGE_NAMES) { o.label = word; o.forceLabel = true; }
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
    drawNames(st, x, w, h);
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
        x.textAlign = 'center';  // over the loop, where no name is placed first
        x.fillText(e.label, p.x + size * 0.8, p.y - size * 0.8 - rad - 7);
      }
    }
  }

  // ---- names: the most connected first, each where it touches no node and no other name -----------------------------------
  // At most one name per cell of the stage while the stage is crowded; closing in leaves fewer nodes on it, so more get a name.

  function drawNames(st, x, w, h) {
    const r = st.renderer, rows = [], cells = new Map(), size = 48, names = [], placed = [];
    const cell = (v) => Math.floor(v / size) + 8, key = (cx, cy) => cx * 4096 + cy;
    const find = st.el.querySelector('.kg-find');
    placed.push({ x: -60, y: 0, w: find.offsetLeft + find.offsetWidth - st.stage.offsetLeft + 66, h: find.offsetTop + 40 });
    st.graph.forEachNode((id) => {
      const d = r.getNodeDisplayData(id);
      if (!d || d.hidden) return;
      const p = r.framedGraphToViewport(d), s = r.scaleSize(d.size);
      if (p.x < -s || p.y < -s || p.x > w + s || p.y > h + s) return;
      const n = { id, d, s, x: p.x, y: p.y };
      rows.push(n);
      for (let cx = cell(p.x - s); cx <= cell(p.x + s); cx += 1) {
        for (let cy = cell(p.y - s); cy <= cell(p.y + s); cy += 1) {
          if (!cells.has(key(cx, cy))) cells.set(key(cx, cy), []);
          cells.get(key(cx, cy)).push(n);
        }
      }
    });
    const hitsNode = (b, self) => {
      for (let cx = cell(b.x); cx <= cell(b.x + b.w); cx += 1) {
        for (let cy = cell(b.y); cy <= cell(b.y + b.h); cy += 1) {
          for (const n of cells.get(key(cx, cy)) || []) {
            if (n !== self && Math.hypot(n.x - clamp(n.x, b.x, b.x + b.w), n.y - clamp(n.y, b.y, b.y + b.h)) < n.s + 1.5) return true;
          }
        }
      }
      return false;
    };
    const free = (b, self) => b.x >= 2 && b.y >= 2 && b.x + b.w <= w - 2 && b.y + b.h <= h - 2
      && !placed.some((q) => b.x < q.x + q.w && q.x < b.x + b.w && b.y < q.y + q.h && q.y < b.y + b.h) && !hitsNode(b, self);
    const span = (text) => { if (!st.widths.has(text)) st.widths.set(text, x.measureText(text).width); return st.widths.get(text); };

    x.font = `600 12px ${FONT}`;
    x.textBaseline = 'middle';
    x.textAlign = 'left';
    x.lineJoin = 'round';

    st.titles = [];  // a group open beside bundles keeps its name above it, and pressing the name folds it again
    if (!st.only && (st.big || st.fold.size)) {
      const box = new Map();
      rows.forEach((n) => {
        const g = st.groupOf[n.id];
        if (!g || !g.bundle) return;
        const b = box.get(g) || { x0: n.x - n.s, x1: n.x + n.s, y0: n.y - n.s, y1: n.y + n.s };
        box.set(g, { x0: Math.min(b.x0, n.x - n.s), x1: Math.max(b.x1, n.x + n.s), y0: Math.min(b.y0, n.y - n.s), y1: Math.max(b.y1, n.y + n.s) });
      });
      box.forEach((b, g) => {
        const text = `${short(g.label, 18)} ${g.nodes.length}`, bw = span(text) + 26, bh = 22, mid = (b.x0 + b.x1 - bw) / 2, side = (b.y0 + b.y1 - bh) / 2;
        const at = [[mid, b.y0 - bh - 5], [mid, b.y1 + 5], [b.x1 + 6, side], [b.x0 - bw - 6, side], [b.x1 + 6, b.y0 - bh], [b.x0 - bw - 6, b.y0 - bh],
          [b.x1 + 6, b.y1], [b.x0 - bw - 6, b.y1]].map(([tx, ty]) => ({ x: tx, y: ty, w: bw, h: bh, g, text }));
        const t = at.find((c) => free(c)) || { ...at[0], x: clamp(at[0].x, 2, w - bw - 2), y: clamp(at[0].y, 2, h - bh - 2) };
        placed.push(t);
        st.titles.push(t);
      });
    }

    const f = focusOf(st), rank = (n) => (n.id === f ? 3e4 : 0) + (n.d.highlighted ? 2e4 : 0) + (st.bundles.has(n.id) ? 1e4 : 0) + n.s;
    rows.sort((a, b) => rank(b) - rank(a));
    let room = prefs.nodeLabels || rows.length <= LABELS_ALL ? Infinity : Math.ceil((w * h) / (LABEL_CELL * LABEL_CELL)) - st.titles.length;
    rows.forEach((n) => {
      const pinned = n.id === f, first = pinned || n.d.highlighted || st.bundles.has(n.id);
      if (!n.d.label || (!first && room <= 0)) return;
      const inside = st.bundles.has(n.id) && n.s >= 9, count = st.bundles.has(n.id) ? st.bundles.get(n.id).nodes.length : 0;
      const text = short(n.d.label, n.d.highlighted ? 40 : 16) + (count && !inside ? ` ${count}` : ''), tw = span(text), th = 15, g = n.s + 5, c = n.s * 0.72 + 4;
      const at = [[n.x + g, n.y - th / 2], [n.x - g - tw, n.y - th / 2], [n.x - tw / 2, n.y + n.s + 3], [n.x - tw / 2, n.y - n.s - th - 3],
        [n.x + c, n.y + c - 2], [n.x + c, n.y - c - th + 2], [n.x - c - tw, n.y + c - 2], [n.x - c - tw, n.y - c - th + 2]].map(([bx, by]) => ({ x: bx, y: by, w: tw, h: th }));
      const spot = at.find((b) => free(b, n)) || (pinned || prefs.nodeLabels ? at[0] : null);
      if (!spot) return;
      placed.push(spot);
      names.push({ text, spot });
      if (!first) room -= 1;
    });

    rows.forEach((n) => {
      const b = st.bundles.get(n.id);
      if (!b) return;
      x.beginPath();  // a second ring tells a bundle from a node
      x.arc(n.x, n.y, n.s + 3.5, 0, Math.PI * 2);
      x.lineWidth = 1.6;
      x.strokeStyle = n.d.color;
      x.globalAlpha = 0.4;
      x.stroke();
      x.globalAlpha = 1;
      if (n.s < 9) return;
      x.fillStyle = n.d.color === DIM ? '#8a96a5' : '#fff';
      x.textAlign = 'center';
      x.fillText(String(b.nodes.length), n.x, n.y + 0.5);
      x.textAlign = 'left';
    });
    names.forEach(({ text, spot }) => {
      x.lineWidth = 3.5;
      x.strokeStyle = 'rgba(255,255,255,.92)';
      x.strokeText(text, spot.x, spot.y + spot.h / 2);
      x.fillStyle = '#1b2330';
      x.fillText(text, spot.x, spot.y + spot.h / 2);
    });
    st.titles.forEach((t) => {
      x.beginPath();
      x.roundRect(t.x, t.y, t.w, t.h, 7);
      x.fillStyle = 'rgba(255,255,255,.95)';
      x.fill();
      x.lineWidth = 1;
      x.strokeStyle = '#dfe3e9';
      x.stroke();
      x.beginPath();
      x.arc(t.x + 11, t.y + t.h / 2, 4, 0, Math.PI * 2);
      x.fillStyle = t.g.color;
      x.fill();
      x.fillStyle = '#2b3644';
      x.fillText(t.text, t.x + 20, t.y + t.h / 2 + 0.5);
    });
  }

  const titleAt = (st, p) => st.titles.find((t) => p.x >= t.x && p.x <= t.x + t.w && p.y >= t.y && p.y <= t.y + t.h);

  // ---- the frame around it --------------------------------------------------------------------------------------------

  const tool = (act, icon, title) => `<button type="button" data-g="${act}" title="${title}" aria-label="${title}"><svg viewBox="0 0 24 24">${ICON[icon]}</svg></button>`;

  function frame(el) {
    el.innerHTML = `<div class="kg-stage"></div><canvas class="kg-loops"></canvas>
      <div class="kg-find"><input type="search" placeholder="Node 검색" aria-label="Node 검색" autocomplete="off"><div class="kg-hits" hidden></div></div>
      <div class="kg-near" hidden></div>
      <div class="kg-tools">${tool('run', 'play', '레이아웃 다시 실행')}${tool('layouts', 'layout', '레이아웃 선택')}${tool('fold', 'fold', '전체 접기')}${tool('ccw', 'left', '왼쪽으로 회전')}${tool('cw', 'right', '오른쪽으로 회전')}${tool('fit', 'fit', '화면에 맞춤')}${tool('in', 'plus', '확대')}${tool('out', 'minus', '축소')}${tool('full', 'full', '전체 화면')}${tool('prefs', 'gear', '표시 설정')}</div>
      <div class="kg-pop" data-pop="layouts" hidden></div><div class="kg-pop" data-pop="prefs" hidden></div><div class="kg-pop" data-pop="groups" hidden></div>
      <div class="kg-foot"><div class="kg-legend"></div><button type="button" class="kg-more" data-g="groups" hidden></button><div class="kg-status"></div></div>`;
  }

  function paintFold(st) {
    const b = st.el.querySelector('[data-g=fold]'), all = foldable(st).length, shut = st.fold.size >= all, title = shut ? '전체 펼치기' : '전체 접기';
    b.hidden = !all;
    b.title = title;
    b.setAttribute('aria-label', title);
    b.querySelector('svg').innerHTML = ICON[shut ? 'unfold' : 'fold'];
  }

  function paintNear(st) {
    const box = st.el.querySelector('.kg-near'), r = st.route, name = (id) => esc(short(String(st.graph.getNodeAttribute(id, 'label')), 14));
    box.hidden = !st.center;
    if (!st.center) return;
    const hop = (n) => `<button type="button" data-hops="${n}" class="${st.hops === n ? 'on' : ''}">${n}단계</button>`;
    if (!r) box.innerHTML = `<span>이웃 보기</span>${hop(1)}${hop(2)}<i></i><button type="button" data-g="route">경로 보기</button>`;
    else if (r.nodes) box.innerHTML = `<span>${name(r.from)} → ${name(r.to)}</span><b>${r.nodes.length - 1}단계</b>`;
    else box.innerHTML = `<span>${r.none ? '연결된 경로가 없습니다. 다른 Node를 선택해 주세요' : '도착 Node를 선택해 주세요'}</span>`;
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
    const rows = st.groups.map((g) => `<button type="button" data-group="${esc(g.key)}" class="${st.off.has(g.key) ? 'off' : ''}"><i style="background:${g.color}"></i>${esc(g.label)}<span>${g.nodes.length}</span></button>`).join('');
    st.el.querySelector('.kg-legend').innerHTML = rows;
    st.el.querySelector('[data-pop=groups]').innerHTML = `<div class="kg-cap">그룹 ${st.groups.length}</div>${rows}`;
    fitLegend(st);
  }

  function fitLegend(st) {  // what does not fit waits behind one button, never cut through a word
    const box = st.el.querySelector('.kg-legend'), more = st.el.querySelector('.kg-more'), rows = [...box.children];
    const over = () => rows.findIndex((b) => b.offsetLeft + b.offsetWidth - box.offsetLeft > box.clientWidth);
    rows.forEach((b) => { b.hidden = false; });
    more.hidden = true;
    if (over() < 0) return;
    more.textContent = `그룹 ${rows.length}개`;
    more.hidden = false;
    const cut = Math.max(over(), 0);
    rows.slice(cut).forEach((b) => { b.hidden = true; });
    if (cut) more.textContent = `외 ${rows.length - cut}개`;
  }

  function paintStatus(st) {
    const g = st.graph, edge = (a) => a.raw && (!st.opt.shown || st.opt.shown('edge', a.raw));
    const nodes = g.filterNodes((id, a) => !st.bundles.has(id) && nodeShown(st, id, a));
    const edges = g.filterEdges((k, a, s, t) => edge(a) && nodeShown(st, s, g.getNodeAttributes(s)) && nodeShown(st, t, g.getNodeAttributes(t)));
    const count = edges.length + st.loops.length, kept = () => (st.route && st.route.keys ? st.route.keys.size
      : edges.filter((k) => st.only.has(g.source(k)) && st.only.has(g.target(k))).length + st.loops.filter((e) => st.only.has(e.source)).length);
    st.el.querySelector('.kg-status').textContent = st.only ? `Node ${st.only.size} / ${nodes.length} · Edge ${kept()} / ${count}`
      : `${st.fold.size ? `묶음 ${st.fold.size} · ` : ''}Node ${nodes.length} · Edge ${count}`;
    fitLegend(st);  // the status takes its width from the legend
  }

  function closePops(st, except) {
    st.el.querySelectorAll('.kg-pop').forEach((p) => { if (p.dataset.pop !== except) p.hidden = true; });
  }

  function find(st, text) {
    const box = st.el.querySelector('.kg-hits'), q = text.trim().toLowerCase();
    if (!q) { box.hidden = true; return; }
    const hits = st.data.nodes.filter((n) => [n.label, n.id, n.table].some((v) => String(v || '').toLowerCase().includes(q))).slice(0, 8);
    box.innerHTML = hits.length ? hits.map((n) => `<button type="button" data-hit="${esc(n.id)}"><i style="background:${st.groupOf[n.id].color}"></i>${esc(n.label)}<span>${esc(st.opt.tag ? st.opt.tag(n) : n.id)}</span></button>`).join('') : '<div class="kg-none">일치하는 Node가 없습니다</div>';
    box.hidden = false;
  }

  function goTo(st, id) {
    const d = st.renderer.getNodeDisplayData(id);
    if (d) st.renderer.getCamera().animate({ x: d.x, y: d.y, ratio: Math.min(st.renderer.getCamera().ratio, 0.6) }, { duration: 360 });
  }

  function wire(st) {
    const { el, renderer } = st, cam = renderer.getCamera();
    st.wires = new AbortController();  // the box outlives a graph when new data comes in: the old one must stop listening
    const { signal } = st.wires;
    el.addEventListener('click', (ev) => {
      const b = ev.target.closest('button');
      if (!b || !el.contains(b)) return;
      const act = b.dataset.g;
      if (act === 'run') arrange(st, st.layout);
      else if (act === 'layouts' || act === 'prefs' || act === 'groups') { const p = el.querySelector(`[data-pop=${act}]`); closePops(st, act); p.hidden = !p.hidden; }
      else if (act === 'fold') {
        const keys = foldable(st).map((x) => x.key);
        if (st.opt.clear) st.opt.clear();
        setFold(st, st.fold.size < keys.length ? keys : []);
        refresh();
        cam.animatedReset({ duration: 260 });
      }
      else if (act === 'route') { st.hops = 0; st.route = { from: st.center }; refresh(); }
      else if (b.dataset.hops) { st.hops = Number(b.dataset.hops); refresh(); }
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
        recolor(st);
      }
      if (b.dataset.group) {
        if (st.off.has(b.dataset.group)) st.off.delete(b.dataset.group); else st.off.add(b.dataset.group);
        paintLegend(st);
        refresh();
      }
      if (b.dataset.hit) {
        const box = el.querySelector('.kg-find input'), routing = st.route && !st.route.nodes;
        box.value = '';
        el.querySelector('.kg-hits').hidden = true;
        tap(st, b.dataset.hit);
        if (!routing) goTo(st, b.dataset.hit);
      }
    }, { signal });
    el.addEventListener('change', (ev) => {
      if (!ev.target.dataset.pref) return;
      prefs[ev.target.dataset.pref] = ev.target.checked;
      renderer.refresh();
    }, { signal });
    const input = el.querySelector('.kg-find input');
    input.addEventListener('input', () => find(st, input.value));
    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') { input.value = ''; find(st, ''); }
      if (ev.key === 'Enter') { const b = el.querySelector('[data-hit]'); if (b) b.click(); }
    });

    renderer.on('enterNode', ({ node }) => { st.hover = node; st.stage.style.cursor = 'pointer'; renderer.refresh({ skipIndexation: true }); });
    renderer.on('leaveNode', () => { st.hover = null; st.stage.style.cursor = ''; renderer.refresh({ skipIndexation: true }); });
    const touch = (event) => String(event.original.type).startsWith('touch');
    renderer.on('clickNode', ({ node, event }) => { st.opened = false; if (touch(event)) tap(st, node); });
    renderer.on('downNode', ({ node, event }) => {
      if (touch(event)) return;
      st.drag = { node, moved: false };
      if (!renderer.getCustomBBox()) renderer.setCustomBBox(renderer.getBBox());
      event.preventSigmaDefault();
    });
    renderer.getMouseCaptor().on('mousemovebody', (ev) => {
      if (!st.drag) {
        if (!st.hover) st.stage.style.cursor = titleAt(st, ev) ? 'pointer' : '';
        return;
      }
      const p = renderer.viewportToGraph(ev), { node } = st.drag, x = st.bundles.get(node);
      if (x) {  // a bundle carries its members with it
        const a = st.graph.getNodeAttributes(node), dx = p.x - a.x, dy = p.y - a.y;
        x.nodes.forEach((id) => {
          const m = st.graph.getNodeAttributes(id), to = { x: m.x + dx, y: m.y + dy };
          st.graph.mergeNodeAttributes(id, to);
          st.opt.pos[id] = to;
        });
      } else st.opt.pos[node] = { x: p.x, y: p.y };
      st.graph.mergeNodeAttributes(node, { x: p.x, y: p.y });
      st.drag.moved = true;
      ev.preventSigmaDefault();
      ev.original.preventDefault();
      ev.original.stopPropagation();
    });
    const drop = () => {
      const d = st.drag;
      st.drag = null;
      if (!d || d.moved) return;
      st.opened = st.bundles.has(d.node);  // the click that follows lands where the bundle no longer is: that is not the empty stage
      tap(st, d.node);
    };
    renderer.getMouseCaptor().on('mouseup', drop);
    renderer.on('clickStage', ({ event }) => {
      if (st.opened) { st.opened = false; return; }
      const t = titleAt(st, event);
      if (t) {
        if (st.center && st.groupOf[st.center] === t.g && st.opt.clear) st.opt.clear();
        setFold(st, [...st.fold, t.g.key]);
        refresh();
        return;
      }
      closePops(st);
      if (st.opt.clear) st.opt.clear();
      refresh();
    });
    renderer.on('afterRender', () => drawLoops(st));
    st.ro = new ResizeObserver(() => { renderer.resize(); renderer.refresh(); fitLegend(st); });
    st.ro.observe(st.stage);
  }

  function kill() {
    if (!cur) return;
    if (cur.ro) cur.ro.disconnect();
    if (cur.wires) cur.wires.abort();
    // a browser keeps about sixteen WebGL contexts: give these back now rather than whenever it collects them
    const canvases = cur.stage ? [...cur.stage.querySelectorAll('canvas')] : [];
    const gls = canvases.map((c) => c.getContext('webgl2') || c.getContext('webgl')).filter(Boolean);
    if (cur.renderer) cur.renderer.kill();
    gls.forEach((gl) => { const lose = gl.getExtension('WEBGL_lose_context'); if (lose) lose.loseContext(); });
    cur = null;
  }

  function halo(x, d) {  // what sigma lays under a highlighted node; its name comes with the others
    x.beginPath();
    x.arc(d.x, d.y, d.size + 3, 0, Math.PI * 2);
    x.fillStyle = '#fff';
    x.shadowColor = 'rgba(20,30,50,.28)';
    x.shadowBlur = 8;
    x.fill();
    x.shadowBlur = 0;
  }

  function start(el, data, opt) {
    const keep = cur && cur.key === opt.key ? cur : null, sig = signature(data), same = keep && keep.sig === sig ? keep : null;
    const camera = keep ? keep.renderer.getCamera().getState() : null;
    const off = keep ? keep.off : new Set();
    kill();
    frame(el);
    const main = el.closest('.main');  // the foot of the graph stays in the window, whatever sits above it
    el.style.setProperty('--kg-top', `${Math.round(el.getBoundingClientRect().top + (main ? main.scrollTop : 0)) + 16}px`);
    const { graph, loops, fit, big } = build(data, el.clientWidth || 760);
    const st = { el, data, opt, graph, loops, fit, big, key: opt.key, off, sig, hover: null, drag: null, layout: 'forceatlas',
      stage: el.querySelector('.kg-stage'), loopCanvas: el.querySelector('.kg-loops'), bundles: new Map(), links: [], fold: new Set(),
      widths: new Map(), titles: [], only: null, center: same ? same.center : null, hops: same ? same.hops : 0, route: same ? same.route : null,
      left: same ? same.left : '', back: same ? same.back : null };
    paint(st);
    settle(st, opt.pos);
    const keys = foldable(st).map((x) => x.key);
    st.fold = new Set(keep ? keys.filter((k) => keep.fold.has(k)) : (big ? keys : []));
    addBundles(st);
    const Border = kit.createNodeBorderProgram({ borders: [
      { size: { attribute: 'ring', defaultValue: 0.14 }, color: { attribute: 'borderColor' } },
      { size: { fill: true }, color: { attribute: 'color' } }] });
    try {
      st.renderer = new kit.Sigma(graph, st.stage, {
        allowInvalidContainer: true, defaultNodeType: 'border', defaultEdgeType: 'curved', zIndex: true, stagePadding: fit < 0.7 ? 22 : 52,
        nodeProgramClasses: { border: Border }, edgeProgramClasses: { curved: kit.createEdgeCurveProgram({ arrowHead: { extremity: 'target', lengthToThicknessRatio: 6.5, widenessToThicknessRatio: 4.6 } }) },
        renderLabels: false, renderEdgeLabels: true, edgeLabelFont: FONT, edgeLabelSize: 10.5, edgeLabelWeight: '500',
        edgeLabelColor: { color: '#5b6675' }, defaultDrawNodeHover: halo,
        zoomToSizeRatioFunction: (ratio) => ratio ** 0.25,  // closing in opens room between nodes instead of filling it with them
        minCameraRatio: 0.06, maxCameraRatio: 4, ...reducers(st),
      });
    } catch (e) {
      el.innerHTML = '<div class="kg-none big">이 브라우저에서 WebGL을 사용할 수 없어 그래프를 표시하지 못했습니다. 객체 관리 화면에서 같은 정의를 확인할 수 있습니다.</div>';
      return;
    }
    cur = st;
    wire(st);
    if (camera) st.renderer.getCamera().setState(camera);
    sync(st);
    paintTools(st); paintPrefs(st); paintLegend(st); paintFold(st); paintStatus(st);
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
    sync(cur);
    paintStatus(cur);
    cur.renderer.refresh({ skipIndexation: true });
  }

  function focus(id) {
    if (cur && cur.graph.hasNode(id)) { refresh(); goTo(cur, id); }
  }

  // where a node sits on screen right now, for a test driving the page; inside a folded group that is its bundle
  function point(id) {
    if (!cur || !cur.graph.hasNode(id)) return null;
    const at = !cur.bundles.has(id) && folded(cur, id) ? cur.groupOf[id].bundle : id;
    const p = cur.renderer.framedGraphToViewport(cur.renderer.getNodeDisplayData(at));
    const r = cur.stage.getBoundingClientRect();
    return { x: r.left + p.x, y: r.top + p.y };
  }

  function state() {
    if (!cur) return null;
    const g = cur.graph, shown = g.filterNodes((id) => !cur.bundles.has(id) && !cur.renderer.getNodeDisplayData(id).hidden).length;
    return { nodes: g.order - cur.bundles.size, edges: g.size - cur.links.length + cur.loops.length, layout: cur.layout, groups: cur.groups.map((x) => x.label), colorBy: prefs.colorBy,
      shown, bundles: [...cur.bundles].filter(([, x]) => cur.fold.has(x.key)).map(([id, x]) => ({ id, label: x.label, nodes: x.nodes.length })),
      hops: cur.hops, route: cur.route && cur.route.nodes ? cur.route.nodes : null };
  }

  return { mount, refresh, focus, kill, point, state };
})();
