  // ==== a QR code drawn as SVG: the sign-in key an authenticator app reads from the screen ==========================
  // Byte mode, error correction level M, the smallest version that holds the text, the mask with the lowest penalty
  // (ISO/IEC 18004). Drawn here with no outside script, so it works where the network reaches nothing outside.
  const qrSvg = (() => {
    // level M, by version: error correction codewords per block, and blocks
    const ECC = [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28];
    const BLOCKS = [0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49];
    const rawModules = (v) => {
      let n = (16 * v + 128) * v + 64;
      if (v >= 2) { const a = Math.floor(v / 7) + 2; n -= (25 * a - 10) * a - 55; if (v >= 7) n -= 36; }
      return n;
    };
    const dataCodewords = (v) => Math.floor(rawModules(v) / 8) - ECC[v] * BLOCKS[v];
    const gfMul = (x, y) => { let z = 0; for (let i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11d); z ^= ((y >>> i) & 1) * x; } return z; };
    function rsDivisor(degree) {
      const out = new Array(degree).fill(0);
      out[degree - 1] = 1;
      let root = 1;
      for (let i = 0; i < degree; i++) {
        for (let j = 0; j < degree; j++) { out[j] = gfMul(out[j], root); if (j + 1 < degree) out[j] ^= out[j + 1]; }
        root = gfMul(root, 2);
      }
      return out;
    }
    function rsRemainder(data, divisor) {
      const out = divisor.map(() => 0);
      data.forEach((b) => { const f = b ^ out.shift(); out.push(0); divisor.forEach((c, i) => { out[i] ^= gfMul(c, f); }); });
      return out;
    }
    const bit = (x, i) => ((x >>> i) & 1) !== 0;
    const alignAt = (v) => {
      if (v === 1) return [];
      const n = Math.floor(v / 7) + 2, step = Math.floor((v * 8 + n * 3 + 5) / (n * 4 - 4)) * 2, out = [6];
      for (let p = v * 4 + 10; out.length < n; p -= step) out.splice(1, 0, p);
      return out;
    };
    const MASK = [(x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
      (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
      (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0, (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0];

    function encode(text) {
      const bytes = [...new TextEncoder().encode(text)];
      let v = 1;
      for (; v <= 40; v++) if (4 + (v < 10 ? 8 : 16) + bytes.length * 8 <= dataCodewords(v) * 8) break;
      if (v > 40) throw new Error('QR text too long');
      const cap = dataCodewords(v) * 8, bits = [];
      const put = (val, len) => { for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
      put(4, 4); put(bytes.length, v < 10 ? 8 : 16); bytes.forEach((b) => put(b, 8));
      put(0, Math.min(4, cap - bits.length));
      put(0, (8 - (bits.length % 8)) % 8);
      for (let pad = 0xec; bits.length < cap; pad ^= 0xec ^ 0x11) put(pad, 8);
      const data = [];
      for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
      // the data cut into blocks, each with its error correction, then interleaved
      const nb = BLOCKS[v], ecl = ECC[v], raw = Math.floor(rawModules(v) / 8), short = nb - (raw % nb), shortLen = Math.floor(raw / nb);
      const div = rsDivisor(ecl), blocks = [];
      for (let i = 0, k = 0; i < nb; i++) {
        const d = data.slice(k, k + shortLen - ecl + (i < short ? 0 : 1));
        k += d.length;
        const e = rsRemainder(d, div);
        if (i < short) d.push(0);
        blocks.push(d.concat(e));
      }
      const words = [];
      for (let i = 0; i < blocks[0].length; i++) blocks.forEach((b, j) => { if (i !== shortLen - ecl || j >= short) words.push(b[i]); });

      const size = v * 4 + 17, dark = [], fixed = [];
      for (let y = 0; y < size; y++) { dark.push(new Array(size).fill(false)); fixed.push(new Array(size).fill(false)); }
      const set = (x, y, on) => { dark[y][x] = on; fixed[y][x] = true; };
      for (let i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
      const finder = (cx, cy) => { for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
        const d = Math.max(Math.abs(dx), Math.abs(dy)), x = cx + dx, y = cy + dy;
        if (x >= 0 && x < size && y >= 0 && y < size) set(x, y, d !== 2 && d !== 4);
      } };
      finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
      const al = alignAt(v), na = al.length;
      for (let i = 0; i < na; i++) for (let j = 0; j < na; j++) {
        if ((i === 0 && j === 0) || (i === 0 && j === na - 1) || (i === na - 1 && j === 0)) continue;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(al[i] + dx, al[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
      }
      const format = (mask) => {  // level M is 00
        let r = mask;
        for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537);
        const b = ((mask << 10) | r) ^ 0x5412;
        for (let i = 0; i <= 5; i++) set(8, i, bit(b, i));
        set(8, 7, bit(b, 6)); set(8, 8, bit(b, 7)); set(7, 8, bit(b, 8));
        for (let i = 9; i < 15; i++) set(14 - i, 8, bit(b, i));
        for (let i = 0; i < 8; i++) set(size - 1 - i, 8, bit(b, i));
        for (let i = 8; i < 15; i++) set(8, size - 15 + i, bit(b, i));
        set(8, size - 8, true);
      };
      format(0);
      if (v >= 7) {
        let r = v;
        for (let i = 0; i < 12; i++) r = (r << 1) ^ ((r >>> 11) * 0x1f25);
        const b = (v << 12) | r;
        for (let i = 0; i < 18; i++) { const a = size - 11 + (i % 3), c = Math.floor(i / 3); set(a, c, bit(b, i)); set(c, a, bit(b, i)); }
      }
      // the codewords in the zigzag, two columns at a time from the right
      let n = 0;
      for (let right = size - 1; right >= 1; right -= 2) {
        if (right === 6) right = 5;
        for (let vert = 0; vert < size; vert++) for (let j = 0; j < 2; j++) {
          const x = right - j, up = ((right + 1) & 2) === 0, y = up ? size - 1 - vert : vert;
          if (!fixed[y][x] && n < words.length * 8) { dark[y][x] = bit(words[n >>> 3], 7 - (n & 7)); n++; }
        }
      }
      const flip = (m) => { for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!fixed[y][x] && MASK[m](x, y)) dark[y][x] = !dark[y][x]; };
      let best = 0, low = Infinity;
      for (let m = 0; m < 8; m++) {
        flip(m); format(m);
        const p = penalty(dark, size);
        if (p < low) { low = p; best = m; }
        flip(m);
      }
      flip(best); format(best);
      return dark;
    }
    // runs of one color, 2x2 blocks, finder-like rows and columns, and how far dark is from half
    function penalty(dark, size) {
      let p = 0, black = 0;
      const lines = [];
      for (let i = 0; i < size; i++) {
        lines.push(dark[i].map((d) => (d ? 1 : 0)).join(''));
        lines.push(dark.map((r) => (r[i] ? 1 : 0)).join(''));
      }
      lines.forEach((s) => {
        (s.match(/0{5,}|1{5,}/g) || []).forEach((run) => { p += run.length - 2; });
        for (let i = s.indexOf('1011101'); i !== -1; i = s.indexOf('1011101', i + 1)) {
          if (s.slice(Math.max(0, i - 4), i) === '0000'.slice(0, Math.min(4, i)) || s.slice(i + 7, i + 11) === '0000'.slice(0, Math.min(4, s.length - i - 7))) p += 40;
        }
      });
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        if (dark[y][x]) black++;
        if (x < size - 1 && y < size - 1 && dark[y][x] === dark[y][x + 1] && dark[y][x] === dark[y + 1][x] && dark[y][x] === dark[y + 1][x + 1]) p += 3;
      }
      const total = size * size;
      return p + (Math.ceil(Math.abs(black * 20 - total * 10) / total) - 1) * 10;
    }

    // text, its drawn width in px, its accessible name
    return (text, px = 176, label = 'QR 코드') => {
      const dark = encode(text), size = dark.length, q = 4, all = size + q * 2;
      let d = '';
      dark.forEach((row, y) => row.forEach((on, x) => { if (on) d += `M${x + q} ${y + q}h1v1h-1z`; }));
      return `<svg class="k-qr" width="${px}" height="${px}" viewBox="0 0 ${all} ${all}" shape-rendering="crispEdges" role="img" aria-label="${esc(label)}"><rect width="${all}" height="${all}" fill="#fff"/><path d="${d}" fill="#171717"/></svg>`;
    };
  })();
