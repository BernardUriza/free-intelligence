/* synapse-field — the living backdrop for Activist OS.
 *
 *  A flow field of particles drifting through Perlin noise, leaving curved
 *  trails that read as nerve fibres / mycelium — biology meeting coordination.
 *  Six invisible attractors sit in a hexagon (the six agents); the field
 *  curves toward them, so the motion organises around the same structure the
 *  emblem draws. Amber pulses travel the fibres now and then (the cause).
 *
 *  Deliberately NOT the rancho-studio blueprint mesh: that field triangulates
 *  straight lines; this one flows in curves. Opposite topology on purpose.
 *
 *  The animation doubles as a client-side vital sign: a sliding-window FPS
 *  meter steps the field through quality tiers. Dense and silky = healthy
 *  GPU/CPU; the field thins itself out under load instead of stuttering.
 *
 *  Vanilla Canvas 2D, no dependencies. Honours prefers-reduced-motion.
 *  Engine owns the simulation; init() owns the canvas, rAF and lifecycle —
 *  same split as rancho's blueprint-engine, opposite aesthetic.
 */

(() => {
  "use strict";

  // ── Perlin noise (Ken Perlin's improved permutation gradient noise) ──────
  class Perlin {
    constructor(seed = 1337) {
      const p = new Uint8Array(512);
      const perm = Array.from({ length: 256 }, (_, i) => i);
      // deterministic shuffle (LCG) so the field is identical across reloads
      let s = seed >>> 0;
      for (let i = 255; i > 0; i--) {
        s = (s * 1664525 + 1013904223) >>> 0;
        const j = s % (i + 1);
        [perm[i], perm[j]] = [perm[j], perm[i]];
      }
      for (let i = 0; i < 512; i++) p[i] = perm[i & 255];
      this.p = p;
    }
    static fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }
    static lerp(a, b, t) { return a + t * (b - a); }
    static grad(hash, x, y) {
      const h = hash & 7;
      const u = h < 4 ? x : y;
      const v = h < 4 ? y : x;
      return ((h & 1) ? -u : u) + ((h & 2) ? -2 * v : 2 * v);
    }
    noise(x, y) {
      const p = this.p;
      const X = Math.floor(x) & 255, Y = Math.floor(y) & 255;
      x -= Math.floor(x); y -= Math.floor(y);
      const u = Perlin.fade(x), v = Perlin.fade(y);
      const a = p[X] + Y, b = p[X + 1] + Y;
      return Perlin.lerp(
        Perlin.lerp(Perlin.grad(p[a], x, y), Perlin.grad(p[b], x - 1, y), u),
        Perlin.lerp(Perlin.grad(p[a + 1], x, y - 1), Perlin.grad(p[b + 1], x - 1, y - 1), u),
        v,
      );
    }
  }

  // ── Quality tiers — the vital sign. Higher index = healthier client. ────
  const TIERS = [
    { particles: 34,  trail: 16, lineW: 0.7 },   // 0 — struggling
    { particles: 80,  trail: 26, lineW: 0.8 },   // 1
    { particles: 130, trail: 36, lineW: 0.9 },   // 2
    { particles: 190, trail: 46, lineW: 1.0 },   // 3 — silky
  ];

  // palette — Activist OS tokens: accent purple, evidence blue, safety amber
  const PURPLE = [139, 92, 246];
  const BLUE = [56, 189, 248];
  const AMBER = [245, 158, 11];

  const mix = (a, b, t) => [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];

  class SynapseField {
    constructor(ctx) {
      this.ctx = ctx;
      this.perlin = new Perlin();
      this.w = 0; this.h = 0; this.dpr = 1;
      this.t = 0;
      this.particles = [];
      this.attractors = [];
      // start at a mid tier; the FPS meter moves us up or down from here
      this.tier = 2;
      this.targetCount = TIERS[this.tier].particles;
      // FPS sliding window
      this.frames = [];
      this.lastTierChange = 0;
    }

    resize(w, h, dpr) {
      this.w = w; this.h = h; this.dpr = dpr;
      // six attractors on a hexagon centred on the viewport (the six agents)
      const cx = w / 2, cy = h / 2;
      const r = Math.min(w, h) * 0.34;
      this.attractors = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 3) * i - Math.PI / 2;
        return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
      });
      this._fill();
    }

    _spawn() {
      // bias spawns toward edges so particles flow inward across the field
      const edge = Math.random();
      let x, y;
      if (edge < 0.5) { x = Math.random() * this.w; y = Math.random() < 0.5 ? -20 : this.h + 20; }
      else { x = Math.random() < 0.5 ? -20 : this.w + 20; y = Math.random() * this.h; }
      return {
        x, y,
        trail: [],
        life: 0,
        maxLife: 260 + Math.random() * 320,
        tone: Math.random(),            // 0 purple … 1 blue, lerped along the trail
        amber: Math.random() < 0.05,    // ~1 in 20 carries an amber pulse (the cause)
        speed: 0.6 + Math.random() * 0.7,
      };
    }

    _fill() {
      while (this.particles.length < this.targetCount) this.particles.push(this._spawn());
      if (this.particles.length > this.targetCount) this.particles.length = this.targetCount;
    }

    _flowAngle(x, y) {
      // base flow from Perlin, then bent toward the nearest attractor so the
      // field organises around the hexagon without ever drawing it
      // low spatial frequency + slow drift → long, languid, organic meanders
      const n = this.perlin.noise(x * 0.0011 + this.t * 0.03, y * 0.0011);
      let angle = n * Math.PI * 2.6;
      let best = null, bestD = Infinity;
      for (const a of this.attractors) {
        const dx = a.x - x, dy = a.y - y, d = dx * dx + dy * dy;
        if (d < bestD) { bestD = d; best = a; }
      }
      if (best) {
        const pull = Math.min(0.4, 9000 / (bestD + 9000));
        const toA = Math.atan2(best.y - y, best.x - x);
        // shortest-arc blend toward the attractor
        let diff = toA - angle;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        angle += diff * pull;
      }
      return angle;
    }

    _measure(dt) {
      this.frames.push(dt);
      if (this.frames.length > 90) this.frames.shift();
      if (this.frames.length < 60 || this.t - this.lastTierChange < 1.2) return;
      const avg = this.frames.reduce((s, v) => s + v, 0) / this.frames.length;
      const fps = 1000 / avg;
      let next = this.tier;
      if (fps < 45 && this.tier > 0) next = this.tier - 1;
      else if (fps > 57 && this.tier < TIERS.length - 1) next = this.tier + 1;
      if (next !== this.tier) {
        this.tier = next;
        this.targetCount = TIERS[next].particles;
        this.lastTierChange = this.t;
        this._fill();
        this.frames.length = 0;
      }
    }

    step(dt) {
      this.t += dt / 1000;
      this._measure(dt);
      const { trail, lineW } = TIERS[this.tier];

      for (const pt of this.particles) {
        const angle = this._flowAngle(pt.x, pt.y);
        pt.x += Math.cos(angle) * pt.speed * 1.4;
        pt.y += Math.sin(angle) * pt.speed * 1.4;
        pt.life++;
        pt.trail.push(pt.x, pt.y);
        if (pt.trail.length > trail * 2) pt.trail.splice(0, 2);
        const out = pt.x < -40 || pt.x > this.w + 40 || pt.y < -40 || pt.y > this.h + 40;
        if (pt.life > pt.maxLife || out) Object.assign(pt, this._spawn());
      }

      this._draw(lineW);
    }

    _draw(lineW) {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.w, this.h);
      ctx.globalCompositeOperation = "lighter";   // fibres glow where they cross
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      for (const pt of this.particles) {
        const tr = pt.trail;
        if (tr.length < 6) continue;
        const base = pt.amber ? AMBER : mix(PURPLE, BLUE, pt.tone);
        const fade = Math.min(1, (pt.maxLife - pt.life) / 80, pt.life / 40);
        const headA = (pt.amber ? 0.5 : 0.32) * fade;

        ctx.beginPath();
        ctx.moveTo(tr[0], tr[1]);
        for (let i = 2; i < tr.length - 2; i += 2) {
          const mx = (tr[i] + tr[i + 2]) / 2, my = (tr[i + 1] + tr[i + 3]) / 2;
          ctx.quadraticCurveTo(tr[i], tr[i + 1], mx, my);   // smooth curved fibre
        }
        ctx.strokeStyle = `rgba(${base[0]},${base[1]},${base[2]},${headA})`;
        ctx.lineWidth = lineW * (pt.amber ? 1.6 : 1) * this.dpr;
        ctx.stroke();

        // bright node at the head
        const hx = tr[tr.length - 2], hy = tr[tr.length - 1];
        ctx.beginPath();
        ctx.arc(hx, hy, (pt.amber ? 1.8 : 1.1) * this.dpr, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${base[0]},${base[1]},${base[2]},${Math.min(1, headA * 2.4)})`;
        ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
    }

    // a single still frame for reduced-motion: faint fibres, no animation
    drawStatic() {
      for (let i = 0; i < 60; i++) {
        const pt = this._spawn();
        for (let s = 0; s < 30; s++) {
          const angle = this._flowAngle(pt.x, pt.y);
          pt.trail.push(pt.x, pt.y);
          pt.x += Math.cos(angle) * 1.4;
          pt.y += Math.sin(angle) * 1.4;
        }
        this.particles = [pt];
        this._draw(0.7);
      }
    }
  }

  // ── init: owns the <canvas>, sizing, rAF loop, visibility, lifecycle ─────
  function init(canvas) {
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    const field = new SynapseField(ctx);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function size() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = window.innerWidth, h = window.innerHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + "px"; canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      field.resize(w, h, dpr);
    }
    size();

    if (reduce) { field.drawStatic(); return; }

    let last = performance.now(), running = true, raf = 0;
    function frame(now) {
      if (!running) return;
      const dt = Math.min(now - last, 50);   // clamp tab-switch jumps
      last = now;
      field.step(dt);
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    // pause off-screen — don't burn cycles on a hidden tab
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) { running = false; cancelAnimationFrame(raf); }
      else if (!running) { running = true; last = performance.now(); raf = requestAnimationFrame(frame); }
    });

    let rt;
    window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(size, 150); });
  }

  // auto-mount on #synapse if present
  const mount = () => {
    const c = document.getElementById("synapse");
    if (c) init(c);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
