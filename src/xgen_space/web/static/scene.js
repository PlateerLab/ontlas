'use strict';
// The pipeline as a building seen from the front right: five floors, data climbing them along one belt.
// Everything drawn comes from the board the server sends; nothing here knows a domain.
window.SpaceScene = (() => {
  const W = 840, D = 170, H = 102, SLAB = 9;
  const OX = 150, OY = 566, VIEW = [1180, 660];
  const BELT = 30;
  const NS = 'http://www.w3.org/2000/svg';
  const C = { floor: '#f5f6f8', slabF: '#dde1e7', slabR: '#cbd0d8', back: '#eef0f3', left: '#e2e5ea',
    blue: '#5b8def', teal: '#2fb5a5', violet: '#8b7cf6', amber: '#efb35c', rose: '#ec7c8e', slate: '#8f9bab', ink: '#16181d' };
  const STATE = { ok: '#22a06b', warn: '#e2a03f', bad: '#e5484d', off: '#b6bcc6' };
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const P = (x, y, z) => [OX + x + y * 0.70, OY + x * 0.075 - y * 0.33 - z];
  const pts = (list) => list.map((p) => P(...p).map((v) => v.toFixed(1)).join(',')).join(' ');
  const shade = (hex, f) => {
    const n = parseInt(hex.slice(1), 16);
    const ch = (s) => Math.max(0, Math.min(255, Math.round(((n >> s) & 255) * f))).toString(16).padStart(2, '0');
    return `#${ch(16)}${ch(8)}${ch(0)}`;
  };
  const poly = (list, fill, extra = '') => `<polygon points="${pts(list)}" fill="${fill}" ${extra}/>`;

  function box(x, y, z, w, d, h, c) {
    return poly([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]], shade(c, 1.12))
      + poly([[x, y, z], [x + w, y, z], [x + w, y, z + h], [x, y, z + h]], c)
      + poly([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, z + h], [x + w, y, z + h]], shade(c, 0.8));
  }

  function cyl(x, y, z, r, h, c) {
    const [cx, top] = P(x, y, z + h);
    const bottom = P(x, y, z)[1];
    const ry = r * 0.36;
    const id = `g${Math.round(x)}_${Math.round(y)}_${Math.round(z)}`;
    return `<linearGradient id="${id}"><stop offset="0" stop-color="${shade(c, 1.02)}"/><stop offset=".55" stop-color="${c}"/><stop offset="1" stop-color="${shade(c, 0.74)}"/></linearGradient>
      <path d="M${cx - r} ${top} V${bottom} A${r} ${ry} 0 0 0 ${cx + r} ${bottom} V${top} Z" fill="url(#${id})"/>
      <ellipse cx="${cx}" cy="${top}" rx="${r}" ry="${ry}" fill="${shade(c, 1.2)}"/>
      <ellipse cx="${cx}" cy="${top}" rx="${r * 0.62}" ry="${ry * 0.62}" fill="none" stroke="#fff" stroke-opacity=".5"/>`;
  }

  function sheets(x, y, z, c) {
    let s = '';
    for (let i = 0; i < 5; i += 1) s += box(x + (i % 2) * 3, y + ((i + 1) % 2) * 2, z + i * 6, 62, 44, 4.5, i % 2 ? shade(c, 1.1) : '#ffffff');
    return s + box(x + 2, y + 2, z + 30, 62, 44, 3, c);
  }

  function machine(x, y, z, c, h = 50) {
    const screen = [[x + 10, y, z + h - 30], [x + 44, y, z + h - 30], [x + 44, y, z + h - 10], [x + 10, y, z + h - 10]];
    const led = P(x + 54, y, z + h - 14);
    return box(x, y, z, 66, 46, h, c) + box(x + 14, y + 12, z + h, 38, 22, 7, shade(c, 0.9))
      + poly(screen, '#1c2230') + `<polyline points="${pts([[x + 13, y, z + h - 20], [x + 21, y, z + h - 15], [x + 29, y, z + h - 23], [x + 41, y, z + h - 17]])}" fill="none" stroke="#7fe0c3" stroke-width="1.4"/>`
      + `<circle class="led" cx="${led[0]}" cy="${led[1]}" r="2.6"/>`;
  }

  function arch(x, y, z, w, h, c) {
    return box(x, y, z, 9, 26, h, c) + box(x + w - 9, y, z, 9, 26, h, c) + box(x, y, z + h, w, 26, 9, shade(c, 1.05));
  }

  function jsonBlock(x, y, z) {
    const [tx, ty] = P(x + 46, y, z + 21);
    return box(x, y, z, 92, 56, 58, C.ink)
      + `<text x="${tx}" y="${ty}" class="jsonmark" text-anchor="middle">{ }</text>`;
  }

  function graph(x, y, z, w, d, parts) {
    const nodes = parts.nodes;
    const at = {}, foot = {};
    const step = (w - 56) / Math.max(nodes.length - 1, 1);
    nodes.forEach((n, i) => {
      const back = i % 2 === 0;
      const nx = x + 28 + i * step, ny = y + (back ? 54 : 20);
      at[n.id] = P(nx, ny, z + (back ? 26 : 12));
      foot[n.id] = P(nx, ny, z + 7);
    });
    const edges = parts.edges.map(([a, b]) => `<line x1="${at[a][0]}" y1="${at[a][1]}" x2="${at[b][0]}" y2="${at[b][1]}" class="gedge"/>`).join('');
    const dots = nodes.map((n, i) => {
      const [nx, ny] = at[n.id];
      const [fx, fy] = foot[n.id];
      return `<g class="gnode"><line x1="${fx}" y1="${fy}" x2="${nx}" y2="${ny}" class="gstem"/><ellipse cx="${fx}" cy="${fy}" rx="7" ry="2.6" fill="#16181d" opacity=".12"/>
        <circle cx="${nx}" cy="${ny}" r="8" fill="url(#ball)" style="animation-delay:${(i * 0.37).toFixed(2)}s"/><text x="${nx}" y="${ny - 12}" text-anchor="middle" class="glabel">${esc(n.label)}</text></g>`;
    }).join('');
    return box(x, y, z, w, d, 7, '#eceafc') + edges + dots;
  }

  function seal(x, y, z) {
    const [cx, top] = P(x, y, z + 58);
    return `<g class="seal">${cyl(x, y, z, 30, 58, '#22a06b')}<path class="sealok" d="M${cx - 11} ${top + 26} l8 8 l15 -17" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><path class="sealno" d="M${cx - 9} ${top + 19} l18 18 m0 -18 l-18 18" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/></g>`;
  }

  function floorShell(i, status) {
    const z = i * H;
    return `${poly([[0, D, z], [W, D, z], [W, D, z + H - SLAB], [0, D, z + H - SLAB]], 'url(#wall)')}
      ${poly([[0, 0, z], [0, D, z], [0, D, z + H - SLAB], [0, 0, z + H - SLAB]], C.left)}
      ${poly([[0, 0, z], [W, 0, z], [W, D, z], [0, D, z]], C.floor)}
      ${Array.from({ length: 13 }, (_, k) => `<polyline points="${pts([[60 * (k + 1), 0, z], [60 * (k + 1), D, z]])}" class="tile"/>`).join('')}
      <polyline points="${pts([[0, 84, z], [W, 84, z]])}" class="tile"/>
      ${poly([[0, 0, z], [W, 0, z], [W, 0, z - SLAB], [0, 0, z - SLAB]], C.slabF)}
      ${poly([[W, 0, z], [W, D, z], [W, D, z - SLAB], [W, 0, z - SLAB]], C.slabR)}
      <polyline class="edge" points="${pts([[0, 0, z], [W, 0, z]])}" stroke="${STATE[status] || STATE.ok}"/>`;
  }

  function belt(z) {
    const marks = [];
    for (let x = 70; x < W - 60; x += 46) marks.push(`<polyline points="${pts([[x, BELT - 7, z + 7], [x + 5, BELT, z + 7], [x, BELT + 7, z + 7]])}" fill="none" stroke="#fff" stroke-opacity=".28"/>`);
    return box(36, BELT - 12, z, W - 72, 24, 6, '#aab1bc') + poly([[36, BELT - 9, z + 6.2], [W - 36, BELT - 9, z + 6.2], [W - 36, BELT + 9, z + 6.2], [36, BELT + 9, z + 6.2]], '#59616e') + marks.join('');
  }

  const PLACE = {
    source: (m, z) => cyl(112, 96, z, 34, 54, C.blue) + cyl(112, 96, z + 56, 34, 3, C.blue)
      + sheets(300, 74, z, C.teal) + sheets(470, 74, z, C.blue) + sheets(640, 74, z, C.amber),
    convert: (m, z) => machine(650, 78, z, C.teal) + machine(500, 78, z, C.blue) + machine(350, 78, z, C.amber) + jsonBlock(120, 70, z),
    ontology: (m, z) => {
      const mods = m.parts.ontology.modules;
      let stack = '';
      mods.forEach((x, i) => { stack += box(44, 76, z + i * 7, 74, 54, 5.5, x.color); });
      return stack + graph(160, 52, z, 430, 104, m.parts.ontology) + arch(622, 70, z, 76, 52, C.violet)
        + cyl(770, 110, z, 24, 30, C.teal) + cyl(752, 72, z, 18, 22, shade(C.teal, 0.92));
    },
    use: (m, z) => {
      let cols = '';
      m.parts.use.targets.forEach((t, i) => {
        const x = 772 - i * 56;
        const h = 22 + (i % 3) * 6;
        const [lx, ly] = P(x, 88, z + h + 8);
        cols += cyl(x, 88, z, 13, h, [C.blue, C.teal, C.violet][i % 3]) + `<text x="${lx}" y="${ly}" text-anchor="middle" class="glabel">${esc(t)}</text>`;
      });
      let grid = '';
      for (let r = 0; r < 4; r += 1) for (let c = 0; c < 5; c += 1) grid += box(136 + c * 15, 74 + r * 13, z + 34, 13, 11, 2.5, (r + c) % 3 ? '#ffffff' : C.amber);
      return cols + box(130, 68, z, 86, 60, 34, C.slate) + grid + box(30, 76, z, 62, 44, 15, C.rose);
    },
    verify: (m, z) => {
      const gates = m.parts.verify.gates.slice(0, 6);
      let s = box(60, 72, z, 54, 46, 40, C.teal) + box(68, 78, z + 40, 38, 30, 9, shade(C.teal, 1.1));
      const gap = 480 / Math.max(gates.length, 1);
      gates.forEach((g, i) => { s += `<g class="gate" data-gate="${i}"><title>${esc(g.label)}</title>${arch(190 + i * gap, 74, z, 58, 50, g.passed ? '#7ccfa8' : '#f09aa0')}</g>`; });
      return s + seal(760, 92, z);
    },
  };

  // where each number stands on its floor
  const TAG_AT = {
    'source.tables': [112, 96, 76, -42], 'source.rows': [112, 96, 76, 40], 'source.data': [330, 96, 54], 'source.definition': [500, 96, 54], 'source.document': [670, 96, 54],
    'convert.sheet': [682, 100, 70], 'convert.schema': [532, 100, 70], 'convert.text': [382, 100, 70], 'convert.unread': [262, 96, 24], 'convert.json': [166, 96, 72],
    'ontology.modules': [80, 100, 72], 'ontology.objects': [222, 46, 9], 'ontology.links': [318, 46, 9], 'ontology.findings': [660, 86, 72], 'ontology.nodes': [770, 96, 50],
    'use.queries': [520, 48, 10], 'use.agree': [640, 48, 10], 'use.rules': [172, 96, 58, -50], 'use.agreement': [172, 96, 58, 56], 'use.waiting': [62, 96, 34],
    'verify.questions': [86, 96, 64], 'verify.accuracy': [300, 96, 72], 'verify.grounded': [486, 96, 72], 'verify.gates': [760, 92, 76],
  };

  function tag(t, i) {
    const a = TAG_AT[t.key] || [100 + (i * 150), 90, 60];
    const [x, sy] = P(a[0], a[1], a[2] + FLOOR_Z[t.key.split('.')[0]]);
    return `<a href="#${esc(t.tab)}" class="tag" data-key="${esc(t.key)}" data-dx="${a[3] || 0}" transform="translate(${(x + (a[3] || 0)).toFixed(1)} ${sy.toFixed(1)})">
      <rect rx="10" ry="10" height="20" class="tagbox"/><circle r="3" cy="10" class="tagdot" fill="${STATE[t.status]}"/>
      <text y="14" class="tagl">${esc(t.label)}</text><text y="14" class="tagv">${esc(t.value)}</text></a>`;
  }
  const FLOOR_Z = { source: 0, convert: H, ontology: 2 * H, use: 3 * H, verify: 4 * H };

  function fit(g) {
    const l = g.querySelector('.tagl'), v = g.querySelector('.tagv');
    const lw = l.getComputedTextLength(), vw = v.getComputedTextLength();
    const w = 16 + lw + 6 + vw + 10;
    g.querySelector('.tagbox').setAttribute('width', w.toFixed(1));
    g.querySelector('.tagbox').setAttribute('x', (-w / 2).toFixed(1));
    g.querySelector('.tagdot').setAttribute('cx', (-w / 2 + 9).toFixed(1));
    l.setAttribute('x', (-w / 2 + 16).toFixed(1));
    v.setAttribute('x', (-w / 2 + 22 + lw).toFixed(1));
  }

  function route(i) {
    const z = i * H + 11, up = (i + 1) * H + 11;
    const leftToRight = i % 2 === 0;
    const from = leftToRight ? 44 : W - 44, to = leftToRight ? W - 44 : 44;
    const a = P(from, BELT, z), b = P(to, BELT, z), c = P(to, BELT, up);
    return i === 4 ? `M${a} L${b}` : `M${a} L${b} L${c}`;
  }

  function packets(i) {
    let s = '';
    const n = 6;
    for (let k = 0; k < n; k += 1) {
      s += `<use href="#pk"><animateMotion dur="11s" begin="${(-k * 11 / n - i * 1.3).toFixed(2)}s" repeatCount="indefinite" path="${route(i)}"/></use>`;
    }
    return `<g class="flow" data-flow="${i}">${s}</g>`;
  }

  function lift(i) {
    const x = i % 2 === 0 ? W - 44 : 44;
    const z = i * H;
    return poly([[x - 11, BELT - 11, z + 4], [x + 11, BELT - 11, z + 4], [x + 11, BELT - 11, z + H + 14], [x - 11, BELT - 11, z + H + 14]], 'rgba(91,141,239,.13)', 'stroke="rgba(91,141,239,.45)"');
  }

  function draw(m) {
    const floors = m.floors.map((f, i) => {
      const z = i * H;
      return `<g class="floor" data-floor="${f.id}">${floorShell(i, f.status)}${(PLACE[f.id] || (() => ''))(m, z)}${belt(z)}</g>`;
    }).join('');
    const top = 5 * H;
    const roof = poly([[-8, -6, top], [W + 8, -6, top], [W + 8, D + 6, top], [-8, D + 6, top]], '#fafbfc')
      + poly([[-8, -6, top], [W + 8, -6, top], [W + 8, -6, top - SLAB], [-8, -6, top - SLAB]], C.slabF)
      + poly([[W + 8, -6, top], [W + 8, D + 6, top], [W + 8, D + 6, top - SLAB], [W + 8, -6, top - SLAB]], C.slabR);
    const badges = m.floors.map((f, i) => {
      const [x, y] = P(0, 0, i * H + 46);
      const text = `${f.no} ${f.label}`;
      const w = 20 + text.length * 11.4;
      return `<a href="#${esc(f.tab)}" class="badge" data-badge="${f.id}"><rect x="${x - w - 10}" y="${y - 13}" width="${w}" height="26" rx="13"/><text x="${x - 10 - w / 2}" y="${y + 4.5}" text-anchor="middle">${esc(text)}</text></a>`;
    }).join('');
    const ground = `<ellipse cx="${OX + 470}" cy="${OY + 44}" rx="600" ry="46" fill="url(#ground)"/>`;
    const lifts = [0, 1, 2, 3].map(lift).join('');
    const flows = m.floors.map((f, i) => packets(i)).join('');
    const tags = m.floors.flatMap((f) => f.tags.map(tag)).join('');
    return `<svg viewBox="0 0 ${VIEW[0]} ${VIEW[1]}" role="img" aria-label="온톨로지 파이프라인 관제 그림" class="spacesvg" xmlns="${NS}">
      <defs>
        <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6f7f9"/><stop offset="1" stop-color="${C.back}"/></linearGradient>
        <radialGradient id="ball" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#c9c0ff"/><stop offset="1" stop-color="#6b5ce0"/></radialGradient>
        <radialGradient id="ground"><stop offset="0" stop-color="#16181d" stop-opacity=".14"/><stop offset="1" stop-color="#16181d" stop-opacity="0"/></radialGradient>
        <g id="pk"><polygon points="-8,-3 0,-7 8,-3 0,1" fill="currentColor"/><polygon points="-8,-3 0,1 0,8 -8,4" fill="currentColor" opacity=".78"/><polygon points="8,-3 0,1 0,8 8,4" fill="currentColor" opacity=".58"/></g>
      </defs>
      ${ground}${floors}${roof}${lifts}${flows}${badges}${tags}</svg>`;
  }

  let root = null;
  let shown = {};

  function state(m) {
    const firstBad = m.floors.findIndex((f) => f.status === 'bad');
    m.floors.forEach((f, i) => {
      const g = root.querySelector(`[data-floor="${f.id}"]`);
      if (g) g.querySelector('.edge').setAttribute('stroke', STATE[f.status] || STATE.ok);
      const flow = root.querySelector(`[data-flow="${i}"]`);
      if (flow) {
        flow.style.color = firstBad >= 0 && i === firstBad ? STATE.bad : (f.status === 'warn' ? STATE.warn : ['#2563eb', '#0f9d8a', '#6b5ce0', '#2563eb', '#16a34a'][i]);
        flow.style.display = firstBad >= 0 && i > firstBad ? 'none' : '';
      }
      const b = root.querySelector(`[data-badge="${f.id}"]`);
      if (b) b.dataset.st = f.status;
    });
    m.parts.verify.gates.slice(0, 6).forEach((x, i) => {
      const g = root.querySelector(`[data-gate="${i}"]`);
      if (g) g.dataset.pass = x.passed ? '1' : '0';
    });
    const end = root.querySelector('.seal');
    if (end) end.dataset.pass = m.passed ? '1' : '0';
  }

  function patch(m) {
    if (!root) return;
    m.floors.forEach((f) => f.tags.forEach((t) => {
      const g = root.querySelector(`.tag[data-key="${t.key}"]`);
      if (!g) return;
      const v = g.querySelector('.tagv');
      if (shown[t.key] !== t.value) {
        v.textContent = t.value;
        fit(g);
        if (shown[t.key] !== undefined) { g.classList.remove('ping'); g.getBoundingClientRect(); g.classList.add('ping'); }
        shown[t.key] = t.value;
      }
      g.querySelector('.tagdot').setAttribute('fill', STATE[t.status]);
    }));
    state(m);
  }

  function mount(el, m) {
    el.innerHTML = draw(m);
    root = el;
    shown = {};
    root.querySelectorAll('.tag').forEach(fit);
    m.floors.forEach((f) => f.tags.forEach((t) => { shown[t.key] = t.value; }));
    state(m);
  }

  function focus(id) {
    if (!root) return;
    root.querySelector('svg').classList.toggle('focused', !!id);
    root.querySelectorAll('.floor').forEach((g) => g.classList.toggle('sel', g.dataset.floor === id));
    root.querySelectorAll('.tag').forEach((g) => g.classList.toggle('sel', g.dataset.key.startsWith(`${id}.`)));
    root.querySelectorAll('.badge').forEach((g) => g.classList.toggle('sel', g.dataset.badge === id));
  }

  // a measurement passes through the floors from the bottom up
  function sweep() {
    if (!root) return;
    root.querySelectorAll('.floor').forEach((g, i) => {
      setTimeout(() => { g.classList.add('scan'); setTimeout(() => g.classList.remove('scan'), 620); }, i * 170);
    });
  }

  return { mount, patch, focus, sweep };
})();
