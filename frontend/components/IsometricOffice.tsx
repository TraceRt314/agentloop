"use client";

import { useEffect, useRef, useCallback } from "react";
import { Application, Container, Graphics, Text, TextStyle } from "pixi.js";
import type { AgentState } from "@/lib/types";
import { ROLE_COLORS, ROLE_EMOJI } from "@/lib/types";

interface Props {
  agents: AgentState[];
  width?: number;
  height?: number;
}

const TILE_W = 64;
const TILE_H = 32;

function toIso(x: number, y: number): [number, number] {
  return [(x - y) * (TILE_W / 2), (x + y) * (TILE_H / 2)];
}
function hexToNum(hex: string): number {
  return parseInt(hex.replace("#", ""), 16);
}

// ─── Particles ───
interface Particle { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; size: number; color: number; alpha: number; }

function spawnParticles(pool: Particle[], count: number, bounds: { w: number; h: number }) {
  for (let i = 0; i < count; i++) {
    pool.push({
      x: (Math.random() - 0.5) * bounds.w,
      y: (Math.random() - 0.5) * bounds.h,
      vx: (Math.random() - 0.5) * 0.15,
      vy: -Math.random() * 0.2 - 0.05,
      life: Math.random() * 300,
      maxLife: 300 + Math.random() * 200,
      size: Math.random() * 2 + 0.5,
      color: [0x60a5fa, 0x4ade80, 0xa78bfa, 0xfbbf24, 0xffffff][Math.floor(Math.random() * 5)],
      alpha: 0,
    });
  }
}

function tickParticles(pool: Particle[], g: Graphics, bounds: { w: number; h: number }) {
  g.clear();
  for (let i = pool.length - 1; i >= 0; i--) {
    const p = pool[i];
    p.x += p.vx; p.y += p.vy; p.life++;
    const progress = p.life / p.maxLife;
    p.alpha = progress < 0.1 ? progress * 10 : progress > 0.8 ? (1 - progress) * 5 : 1;
    p.alpha *= 0.35;
    if (p.life > p.maxLife) {
      p.x = (Math.random() - 0.5) * bounds.w;
      p.y = (Math.random() - 0.5) * bounds.h + bounds.h * 0.3;
      p.life = 0;
    }
    g.circle(p.x, p.y, p.size);
    g.fill({ color: p.color, alpha: p.alpha });
  }
}

// ─── Floor ───
function drawFloor(g: Graphics, cols: number, rows: number) {
  for (let x = 0; x < cols; x++) {
    for (let y = 0; y < rows; y++) {
      const [ix, iy] = toIso(x, y);
      const isDark = (x + y) % 2 === 0;
      // Gradient-ish per tile
      const base = isDark ? 0x1a2538 : 0x1f2d42;
      const edgeDist = Math.min(x, y, cols - 1 - x, rows - 1 - y);
      const brighten = Math.max(0, 3 - edgeDist) * 0x050505;
      g.poly([
        { x: ix, y: iy }, { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H }, { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.fill({ color: base + brighten, alpha: 0.92 });
      g.poly([
        { x: ix, y: iy }, { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H }, { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.stroke({ color: 0x2e4060, width: 0.4, alpha: 0.25 });
    }
  }
  // Floor reflection shine
  const [cx, cy] = toIso(cols / 2, rows / 2);
  g.ellipse(cx, cy, 80, 40);
  g.fill({ color: 0xffffff, alpha: 0.018 });
}

// ─── Carpet/Rug ───
function drawRug(g: Graphics) {
  const [cx, cy] = toIso(4, 4);
  for (let r = 3; r > 0; r--) {
    const colors = [0x1e3a5f, 0x162d4d, 0x0f2240];
    g.ellipse(cx, cy, r * 28, r * 14);
    g.fill({ color: colors[3 - r], alpha: 0.5 });
  }
  // Rug border pattern
  for (let i = 0; i < 24; i++) {
    const angle = (i / 24) * Math.PI * 2;
    const dx = Math.cos(angle) * 78;
    const dy = Math.sin(angle) * 39;
    g.circle(cx + dx, cy + dy, 1.5);
    g.fill({ color: 0x3b82f6, alpha: 0.3 });
  }
}

// ─── Walls ───
function drawWalls(g: Graphics, cols: number) {
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const [brx, bry] = toIso(cols, cols);
  const H = 90;

  // Back wall
  g.poly([{ x: lx, y: ly - H }, { x: rx, y: ry - H }, { x: rx, y: ry }, { x: lx, y: ly }]);
  g.fill({ color: 0x243348 });
  g.stroke({ color: 0x2e4462, width: 1 });
  // Wall panel lines
  for (let i = 1; i < 4; i++) {
    const px = lx + (rx - lx) * (i / 4);
    const py = ly + (ry - ly) * (i / 4);
    g.moveTo(px, py - H); g.lineTo(px, py);
    g.stroke({ color: 0x2a3f5a, width: 0.5, alpha: 0.5 });
  }
  // Baseboard
  g.poly([{ x: lx, y: ly - 6 }, { x: rx, y: ry - 6 }, { x: rx, y: ry }, { x: lx, y: ly }]);
  g.fill({ color: 0x1a2840, alpha: 0.8 });

  // Right wall
  g.poly([{ x: rx, y: ry - H }, { x: brx, y: bry - H }, { x: brx, y: bry }, { x: rx, y: ry }]);
  g.fill({ color: 0x1c2b3e });
  g.stroke({ color: 0x253a52, width: 1 });
  for (let i = 1; i < 4; i++) {
    const px = rx + (brx - rx) * (i / 4);
    const py = ry + (bry - ry) * (i / 4);
    g.moveTo(px, py - H); g.lineTo(px, py);
    g.stroke({ color: 0x223550, width: 0.5, alpha: 0.5 });
  }
  g.poly([{ x: rx, y: ry - 6 }, { x: brx, y: bry - 6 }, { x: brx, y: bry }, { x: rx, y: ry }]);
  g.fill({ color: 0x152236, alpha: 0.8 });

  // Corner edge highlight
  g.moveTo(rx, ry - H); g.lineTo(rx, ry);
  g.stroke({ color: 0x3a5575, width: 1.5 });
}

// ─── Window ───
function drawWindow(container: Container, cols: number, t: number) {
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const H = 90;
  const wx = (lx + rx) / 2;
  const wy = (ly + ry) / 2 - H + 18;
  const g = new Graphics();
  // Frame
  g.roundRect(wx - 50, wy, 100, 50, 3);
  g.fill({ color: 0x0c1829 });
  g.stroke({ color: 0x4a6480, width: 2.5 });
  // Sky gradient (animated)
  const skyShift = Math.sin(t / 2000) * 0.1;
  g.roundRect(wx - 46, wy + 4, 92, 42, 2);
  g.fill({ color: 0x0f2557, alpha: 0.9 });
  // Stars through window
  for (let i = 0; i < 8; i++) {
    const sx = wx - 40 + Math.sin(i * 2.7 + t / 5000) * 36 + 36;
    const sy = wy + 8 + Math.cos(i * 1.9 + t / 4000) * 16 + 16;
    const twinkle = (Math.sin(t / 300 + i * 1.3) + 1) / 2;
    g.circle(sx, sy, 1 + twinkle * 0.5);
    g.fill({ color: 0xffffff, alpha: 0.3 + twinkle * 0.5 });
  }
  // Moon
  g.circle(wx + 25, wy + 14, 8);
  g.fill({ color: 0xe2e8f0, alpha: 0.6 + Math.sin(t / 3000) * 0.1 });
  g.circle(wx + 27, wy + 12, 6);
  g.fill({ color: 0x0f2557 }); // crescent cut
  // Window cross
  g.moveTo(wx, wy); g.lineTo(wx, wy + 50);
  g.stroke({ color: 0x4a6480, width: 1.5 });
  g.moveTo(wx - 50, wy + 25); g.lineTo(wx + 50, wy + 25);
  g.stroke({ color: 0x4a6480, width: 1.5 });
  // Window light cone on floor
  const fg = new Graphics();
  const [flx, fly] = toIso(2.5, 2.5);
  fg.ellipse(flx, fly, 50, 25);
  fg.fill({ color: 0x3b82f6, alpha: 0.025 + Math.sin(t / 4000) * 0.008 });
  container.addChild(fg);
  container.addChild(g);
}

// ─── Poster/Art on wall ───
function drawWallArt(container: Container, cols: number) {
  const [rx, ry] = toIso(cols, 0);
  const [brx, bry] = toIso(cols, cols);
  const g = new Graphics();
  // Poster on right wall
  const px = rx + (brx - rx) * 0.35;
  const py = ry + (bry - ry) * 0.35 - 60;
  g.roundRect(px - 14, py, 28, 22, 1);
  g.fill({ color: 0x1a1a2e });
  g.stroke({ color: 0x64748b, width: 1 });
  // Poster art (mini bar chart)
  for (let i = 0; i < 4; i++) {
    const bh = 4 + Math.random() * 10;
    g.rect(px - 10 + i * 6, py + 18 - bh, 4, bh);
    g.fill({ color: [0xe94560, 0x60a5fa, 0x4ade80, 0xfbbf24][i], alpha: 0.8 });
  }
  container.addChild(g);

  // Clock on back wall
  const [lx, ly] = toIso(0, 0);
  const cx = lx + (rx - lx) * 0.15;
  const cy = ly + (ry - ly) * 0.15 - 70;
  const cg = new Graphics();
  cg.circle(cx, cy, 12);
  cg.fill({ color: 0x1e293b });
  cg.stroke({ color: 0x64748b, width: 1.5 });
  cg.circle(cx, cy, 10);
  cg.fill({ color: 0xf0f0f0, alpha: 0.9 });
  // Clock hands
  const now = new Date();
  const hAngle = ((now.getHours() % 12) / 12) * Math.PI * 2 - Math.PI / 2;
  const mAngle = (now.getMinutes() / 60) * Math.PI * 2 - Math.PI / 2;
  cg.moveTo(cx, cy);
  cg.lineTo(cx + Math.cos(hAngle) * 5, cy + Math.sin(hAngle) * 5);
  cg.stroke({ color: 0x333333, width: 1.5 });
  cg.moveTo(cx, cy);
  cg.lineTo(cx + Math.cos(mAngle) * 7, cy + Math.sin(mAngle) * 7);
  cg.stroke({ color: 0x666666, width: 1 });
  cg.circle(cx, cy, 1.5);
  cg.fill({ color: 0xe94560 });
  container.addChild(cg);
}

// ─── Desk ───
function drawDesk(container: Container, gx: number, gy: number, color: number, label: string, t: number) {
  const [ix, iy] = toIso(gx, gy);
  const g = new Graphics();
  const dw = 52, dh = 26;

  // Desk shadow
  g.ellipse(ix, iy + 4, 28, 10);
  g.fill({ color: 0x000000, alpha: 0.15 });

  // Desk legs
  for (const [ox, oy] of [[-dw/2+4, dh/2-2], [dw/2-4, dh/2-2], [-dw/2+4, -dh/2+2], [dw/2-4, -dh/2+2]]) {
    g.rect(ix + ox - 1.5, iy - 16 + oy, 3, 16);
    g.fill({ color: 0x5a3e10, alpha: 0.7 });
  }

  // Desk top
  g.poly([
    { x: ix, y: iy - 18 }, { x: ix + dw / 2, y: iy - 18 + dh / 2 },
    { x: ix, y: iy - 18 + dh }, { x: ix - dw / 2, y: iy - 18 + dh / 2 },
  ]);
  g.fill({ color: 0xb8860b });
  g.stroke({ color: 0x8b6914, width: 1 });
  // Wood grain
  for (let i = 0; i < 3; i++) {
    const gy2 = iy - 18 + dh / 2 - 6 + i * 4;
    g.moveTo(ix - dw / 4, gy2); g.lineTo(ix + dw / 4, gy2);
    g.stroke({ color: 0xa67c00, width: 0.5, alpha: 0.3 });
  }

  // Front face
  g.poly([
    { x: ix - dw / 2, y: iy - 18 + dh / 2 }, { x: ix, y: iy - 18 + dh },
    { x: ix, y: iy - 4 }, { x: ix - dw / 2, y: iy - 4 - dh / 2 + dh / 2 },
  ]);
  g.fill({ color: 0x8b6914, alpha: 0.6 });

  // Monitor
  g.roundRect(ix - 10, iy - 40, 20, 16, 2);
  g.fill({ color: 0x0f172a });
  g.stroke({ color: 0x334155, width: 1.5 });
  // Screen content (animated)
  const screenFlicker = Math.sin(t / 200) * 0.05;
  g.roundRect(ix - 8, iy - 38, 16, 12, 1);
  g.fill({ color, alpha: 0.15 + screenFlicker });
  // Code lines on screen
  for (let i = 0; i < 4; i++) {
    const lw = 4 + Math.sin(t / 500 + i) * 3 + 3;
    g.rect(ix - 6, iy - 36 + i * 3, lw, 1.5);
    g.fill({ color, alpha: 0.5 + Math.sin(t / 300 + i) * 0.2 });
  }
  // Monitor stand
  g.rect(ix - 2, iy - 24, 4, 5);
  g.fill({ color: 0x334155 });
  g.rect(ix - 5, iy - 19, 10, 2);
  g.fill({ color: 0x334155 });

  // Keyboard
  g.roundRect(ix - 8, iy - 15, 16, 5, 1);
  g.fill({ color: 0x1e293b, alpha: 0.8 });
  g.stroke({ color: 0x334155, width: 0.5 });

  // Coffee mug
  g.roundRect(ix + 14, iy - 18, 6, 7, 1);
  g.fill({ color: 0xffffff, alpha: 0.8 });
  g.stroke({ color: 0xcccccc, width: 0.5 });
  // Mug handle
  g.arc(ix + 20, iy - 15, 3, -Math.PI / 2, Math.PI / 2, false);
  g.stroke({ color: 0xcccccc, width: 1 });
  // Steam from mug
  for (let i = 0; i < 2; i++) {
    const sy = iy - 22 - Math.sin(t / 400 + i * 2) * 4;
    g.circle(ix + 16 + i * 3, sy, 1.5);
    g.fill({ color: 0xffffff, alpha: 0.12 - i * 0.04 });
  }

  container.addChild(g);

  // Label
  const text = new Text({
    text: label,
    style: new TextStyle({ fontFamily: "monospace", fontSize: 7, fill: 0x6b7fa0 }),
  });
  text.anchor.set(0.5, 0); text.x = ix; text.y = iy + 6;
  container.addChild(text);

  // Desk lamp
  const lg = new Graphics();
  lg.rect(ix - dw / 2 - 2, iy - 28, 2, 12);
  lg.fill({ color: 0x475569 });
  lg.ellipse(ix - dw / 2 + 2, iy - 30, 6, 3);
  lg.fill({ color: 0xfbbf24, alpha: 0.7 });
  // Lamp light cone
  lg.ellipse(ix - dw / 2, iy - 18, 10, 4);
  lg.fill({ color: 0xfbbf24, alpha: 0.06 });
  container.addChild(lg);
}

// ─── Furniture ───
function drawFurniture(container: Container, t: number) {
  // Bookshelf on right wall
  const bg = new Graphics();
  const [bsx, bsy] = toIso(8, 2);
  bg.roundRect(bsx - 12, bsy - 40, 24, 40, 2);
  bg.fill({ color: 0x5a3e10 });
  bg.stroke({ color: 0x4a2e08, width: 1 });
  // Shelves
  for (let s = 0; s < 3; s++) {
    bg.rect(bsx - 10, bsy - 36 + s * 12, 20, 2);
    bg.fill({ color: 0x6b4f12 });
    // Books
    for (let b = 0; b < 4; b++) {
      const bw = 3 + Math.random() * 2;
      const bh = 6 + Math.random() * 4;
      const bc = [0xe94560, 0x3b82f6, 0x4ade80, 0xfbbf24, 0xa78bfa][Math.floor(Math.random() * 5)];
      bg.rect(bsx - 8 + b * 5, bsy - 34 + s * 12 - bh, bw, bh);
      bg.fill({ color: bc, alpha: 0.7 });
    }
  }
  container.addChild(bg);

  // Coffee machine
  const cg = new Graphics();
  const [cmx, cmy] = toIso(7.2, 0.8);
  // Counter
  cg.poly([
    { x: cmx - 16, y: cmy - 12 }, { x: cmx + 16, y: cmy - 12 },
    { x: cmx + 16, y: cmy + 4 }, { x: cmx - 16, y: cmy + 4 },
  ]);
  cg.fill({ color: 0x2a2a3e });
  cg.stroke({ color: 0x3a3a50, width: 1 });
  // Machine body
  cg.roundRect(cmx - 8, cmy - 28, 16, 18, 2);
  cg.fill({ color: 0x1e1e30 });
  cg.stroke({ color: 0x444466, width: 1 });
  // LED
  cg.circle(cmx, cmy - 22, 2);
  cg.fill({ color: 0x4ade80, alpha: 0.6 + Math.sin(t / 500) * 0.3 });
  // Steam
  for (let i = 0; i < 3; i++) {
    const sx = cmx - 2 + i * 2;
    const sy = cmy - 32 - Math.sin(t / 300 + i * 1.5) * 5;
    const sa = 0.15 - i * 0.04;
    cg.circle(sx, sy, 2 + Math.sin(t / 400 + i) * 0.5);
    cg.fill({ color: 0xffffff, alpha: sa > 0 ? sa : 0 });
  }
  container.addChild(cg);

  // Server rack
  const sg = new Graphics();
  const [srx, sry] = toIso(7.5, 7.2);
  // Rack body
  sg.roundRect(srx - 12, sry - 42, 24, 44, 2);
  sg.fill({ color: 0x0a0f1a });
  sg.stroke({ color: 0x1e2d42, width: 1.5 });
  // Server units
  for (let i = 0; i < 4; i++) {
    sg.roundRect(srx - 9, sry - 38 + i * 10, 18, 8, 1);
    sg.fill({ color: 0x111827 });
    sg.stroke({ color: 0x1f2937, width: 0.5 });
    // LED
    const ledState = Math.sin(t / 200 + i * 1.7) > 0;
    sg.circle(srx - 5, sry - 34 + i * 10, 2);
    sg.fill({ color: ledState ? 0x4ade80 : 0x1a2e1a });
    // Activity LED
    const actLed = Math.sin(t / 80 + i * 3) > 0.5;
    sg.circle(srx - 1, sry - 34 + i * 10, 1.5);
    sg.fill({ color: actLed ? 0xfbbf24 : 0x2a2a1a, alpha: actLed ? 0.8 : 0.3 });
    // Drive bays
    for (let d = 0; d < 3; d++) {
      sg.rect(srx + 2 + d * 4, sry - 36 + i * 10, 3, 4);
      sg.fill({ color: 0x1a2030 });
    }
  }
  // Server glow
  sg.ellipse(srx, sry + 4, 16, 6);
  sg.fill({ color: 0x4ade80, alpha: 0.03 });
  container.addChild(sg);

  // Plants (detailed)
  for (const [px, py, size] of [[0.3, 7.5, 1.2], [7.8, 0.3, 0.8], [0.3, 0.3, 1.0]] as [number, number, number][]) {
    const pg = new Graphics();
    const [plx, ply] = toIso(px, py);
    // Pot
    pg.poly([
      { x: plx - 6 * size, y: ply - 4 }, { x: plx + 6 * size, y: ply - 4 },
      { x: plx + 4 * size, y: ply + 6 }, { x: plx - 4 * size, y: ply + 6 },
    ]);
    pg.fill({ color: 0x8b4513 });
    pg.stroke({ color: 0x6b3410, width: 1 });
    // Soil
    pg.ellipse(plx, ply - 4, 6 * size, 2.5);
    pg.fill({ color: 0x3e2723 });
    // Leaves
    for (let l = 0; l < 5; l++) {
      const angle = (l / 5) * Math.PI * 2 + Math.sin(t / 1500 + l) * 0.15;
      const dist = 8 * size + Math.sin(t / 2000 + l * 2) * 1.5;
      const lx = plx + Math.cos(angle) * dist;
      const ly2 = ply - 10 * size + Math.sin(angle) * dist * 0.4;
      pg.ellipse(lx, ly2, 5 * size, 3 * size);
      pg.fill({ color: l % 2 === 0 ? 0x2d6a2d : 0x3a8a3a, alpha: 0.85 });
    }
    // Center stem
    pg.moveTo(plx, ply - 4);
    pg.lineTo(plx, ply - 14 * size);
    pg.stroke({ color: 0x2d5a2d, width: 1.5 });
    container.addChild(pg);
  }

  // Whiteboard
  const wg = new Graphics();
  const [wx, wy] = toIso(1.5, 0.3);
  // Frame
  wg.roundRect(wx - 36, wy - 42, 72, 44, 2);
  wg.fill({ color: 0xf8f8f8 });
  wg.stroke({ color: 0x94a3b8, width: 2.5 });
  // Shadow under frame
  wg.roundRect(wx - 34, wy - 40, 68, 40, 1);
  wg.fill({ color: 0xf0f0f0 });
  // Sticky notes
  const stickies = [
    { x: -24, y: -36, w: 14, h: 12, color: 0xfbbf24 },
    { x: -6, y: -38, w: 14, h: 14, color: 0xf87171 },
    { x: 12, y: -34, w: 14, h: 12, color: 0x4ade80 },
    { x: -18, y: -20, w: 14, h: 12, color: 0x60a5fa },
    { x: 2, y: -22, w: 14, h: 14, color: 0xa78bfa },
    { x: 22, y: -20, w: 14, h: 12, color: 0xfbbf24 },
  ];
  for (const s of stickies) {
    wg.roundRect(wx + s.x, wy + s.y, s.w, s.h, 1);
    wg.fill({ color: s.color, alpha: 0.85 });
    // Tiny text lines
    for (let i = 0; i < 2; i++) {
      wg.rect(wx + s.x + 2, wy + s.y + 3 + i * 3, s.w - 4, 1.5);
      wg.fill({ color: 0x000000, alpha: 0.15 });
    }
  }
  // Sprint title
  wg.rect(wx - 30, wy - 42, 60, 8);
  wg.fill({ color: 0xe2e8f0 });
  container.addChild(wg);
  const wbText = new Text({
    text: "SPRINT BOARD",
    style: new TextStyle({ fontFamily: "monospace", fontSize: 5, fill: 0x64748b, fontWeight: "bold" }),
  });
  wbText.anchor.set(0.5, 0.5); wbText.x = wx; wbText.y = wy - 38;
  container.addChild(wbText);

  // Meeting table (nicer)
  const mg = new Graphics();
  const [mx, my] = toIso(4, 4);
  // Table shadow
  mg.ellipse(mx, my + 2, 24, 10);
  mg.fill({ color: 0x000000, alpha: 0.12 });
  // Table top
  mg.ellipse(mx, my - 8, 22, 11);
  mg.fill({ color: 0xa67c00 });
  mg.stroke({ color: 0x8b6914, width: 1.5 });
  mg.ellipse(mx, my - 10, 16, 8);
  mg.fill({ color: 0xb8860b, alpha: 0.4 }); // highlight
  // Table leg
  mg.rect(mx - 2, my - 8, 4, 10);
  mg.fill({ color: 0x6b4f12 });
  container.addChild(mg);

  // Chairs around meeting table
  for (let i = 0; i < 4; i++) {
    const angle = (i / 4) * Math.PI * 2 + Math.PI / 4;
    const dist = 30;
    const chairX = mx + Math.cos(angle) * dist;
    const chairY = my - 4 + Math.sin(angle) * dist * 0.5;
    const chairG = new Graphics();
    chairG.circle(chairX, chairY, 5);
    chairG.fill({ color: 0x334155, alpha: 0.7 });
    chairG.circle(chairX, chairY - 6, 4);
    chairG.fill({ color: 0x3a4f6a });
    container.addChild(chairG);
  }
}

// ─── Agent ───
function drawAgent(container: Container, agent: AgentState, pos: { x: number; y: number }, t: number) {
  const [ix, iy] = toIso(pos.x / 60, pos.y / 60);
  const color = hexToNum(ROLE_COLORS[agent.role] ?? ROLE_COLORS.default);
  const emoji = ROLE_EMOJI[agent.role] ?? "🤖";
  const isWorking = agent.current_action === "working";
  const isWalking = agent.current_action === "walking";
  const isTalking = agent.current_action === "talking";
  const isThinking = agent.current_action === "thinking";

  const bounce = isWalking ? Math.sin(t / 120) * 4 : 0;
  const breathe = Math.sin(t / 800) * 0.8;
  const idleSway = Math.sin(t / 2000 + pos.x) * 1;

  const g = new Graphics();
  const by = iy - 14 + bounce + breathe;

  // Shadow
  const shadowScale = 1 + (isWorking ? Math.sin(t / 300) * 0.1 : 0);
  g.ellipse(ix, iy + 2, 14 * shadowScale, 6 * shadowScale);
  g.fill({ color: 0x000000, alpha: 0.25 });

  // Work aura
  if (isWorking) {
    const auraSize = 24 + Math.sin(t / 250) * 4;
    g.circle(ix, by - 4, auraSize);
    g.fill({ color, alpha: 0.04 });
    g.circle(ix, by - 4, auraSize * 0.7);
    g.fill({ color, alpha: 0.03 });
  }

  // Legs
  const legPhase = isWalking ? t / 150 : 0;
  g.roundRect(ix - 5 + idleSway, by + 6 + Math.sin(legPhase) * (isWalking ? 3 : 0), 4, 10, 2);
  g.fill({ color: 0x334155 });
  g.roundRect(ix + 1 + idleSway, by + 6 + Math.sin(legPhase + Math.PI) * (isWalking ? 3 : 0), 4, 10, 2);
  g.fill({ color: 0x2d3a4e });
  // Shoes
  g.roundRect(ix - 6 + idleSway, by + 14 + Math.sin(legPhase) * (isWalking ? 2 : 0), 6, 3, 1);
  g.fill({ color: 0x1a1a2e });
  g.roundRect(ix + idleSway, by + 14 + Math.sin(legPhase + Math.PI) * (isWalking ? 2 : 0), 6, 3, 1);
  g.fill({ color: 0x1a1a2e });

  // Body / torso
  g.roundRect(ix - 9 + idleSway, by - 8, 18, 16, 3);
  g.fill({ color });
  g.stroke({ color: 0x000000, width: 0.3, alpha: 0.15 });
  // Shirt detail
  g.moveTo(ix + idleSway, by - 6); g.lineTo(ix + idleSway, by + 6);
  g.stroke({ color: 0xffffff, width: 0.5, alpha: 0.15 });
  // Badge/pocket
  g.roundRect(ix + 3 + idleSway, by - 4, 4, 4, 1);
  g.fill({ color: 0xffffff, alpha: 0.2 });

  // Arms
  if (isWorking) {
    g.roundRect(ix - 14 + idleSway, by - 2 + Math.sin(t / 200) * 1, 6, 4, 2);
    g.fill({ color: 0xfcd5b0 });
    g.roundRect(ix + 8 + idleSway, by - 2 + Math.sin(t / 200 + 1) * 1, 6, 4, 2);
    g.fill({ color: 0xfcd5b0 });
  } else {
    g.roundRect(ix - 13 + idleSway, by + Math.sin(t / 1200) * 1, 5, 10, 2);
    g.fill({ color });
    g.roundRect(ix + 8 + idleSway, by + Math.sin(t / 1200 + 1) * 1, 5, 10, 2);
    g.fill({ color });
    // Hands
    g.circle(ix - 11 + idleSway, by + 10, 2.5);
    g.fill({ color: 0xfcd5b0 });
    g.circle(ix + 11 + idleSway, by + 10, 2.5);
    g.fill({ color: 0xfcd5b0 });
  }

  // Head
  g.circle(ix + idleSway, by - 16, 9);
  g.fill({ color: 0xfcd5b0 });
  g.stroke({ color: 0xe8b898, width: 0.8 });

  // Hair with role color
  g.arc(ix + idleSway, by - 18, 9, Math.PI + 0.3, -0.3, false);
  g.fill({ color, alpha: 0.85 });
  // Hair shine
  g.arc(ix - 3 + idleSway, by - 20, 4, Math.PI, 0, false);
  g.fill({ color: 0xffffff, alpha: 0.1 });

  // Eyes
  const blinkPhase = Math.sin(t / 3000 + pos.x * 0.1);
  const eyeH = blinkPhase > 0.95 ? 0.5 : 2;
  g.ellipse(ix - 3 + idleSway, by - 17, 1.8, eyeH);
  g.fill({ color: 0x1a1a2e });
  g.ellipse(ix + 3 + idleSway, by - 17, 1.8, eyeH);
  g.fill({ color: 0x1a1a2e });
  // Eye shine
  if (eyeH > 1) {
    g.circle(ix - 2.5 + idleSway, by - 17.5, 0.7);
    g.fill({ color: 0xffffff, alpha: 0.6 });
    g.circle(ix + 3.5 + idleSway, by - 17.5, 0.7);
    g.fill({ color: 0xffffff, alpha: 0.6 });
  }

  // Mouth
  if (isTalking) {
    const mouthOpen = Math.abs(Math.sin(t / 120)) * 2 + 1;
    g.ellipse(ix + idleSway, by - 12, 2.5, mouthOpen);
    g.fill({ color: 0xc97755 });
  } else if (isWorking) {
    g.arc(ix + idleSway, by - 13, 3, 0.2, Math.PI - 0.2, false);
    g.stroke({ color: 0xc97755, width: 1 });
  } else {
    g.rect(ix - 2 + idleSway, by - 12.5, 4, 1.5);
    g.fill({ color: 0xc97755 });
  }

  container.addChild(g);

  // Emoji badge (floating above)
  const badgeY = by - 34 + Math.sin(t / 600) * 2;
  const badge = new Text({
    text: emoji,
    style: new TextStyle({ fontSize: 14 }),
  });
  badge.anchor.set(0.5, 0.5); badge.x = ix; badge.y = badgeY;
  container.addChild(badge);

  // Action bubble
  if (agent.current_action !== "idle") {
    const bubbleG = new Graphics();
    const bx = ix + 18; const bby = by - 36;
    bubbleG.roundRect(bx - 4, bby - 2, 52, 16, 6);
    bubbleG.fill({ color: 0xffffff, alpha: 0.92 });
    bubbleG.stroke({ color, width: 1.5, alpha: 0.6 });
    bubbleG.poly([
      { x: bx + 2, y: bby + 14 }, { x: bx - 4, y: bby + 22 }, { x: bx + 12, y: bby + 14 },
    ]);
    bubbleG.fill({ color: 0xffffff, alpha: 0.92 });
    container.addChild(bubbleG);

    const icons: Record<string, string> = {
      working: "⚡", talking: "💬", reviewing: "🔍", thinking: "🤔", walking: "🚶",
    };
    const actionText = new Text({
      text: `${icons[agent.current_action] ?? "•"} ${agent.current_action}`,
      style: new TextStyle({ fontFamily: "monospace", fontSize: 8, fill: hexToNum(ROLE_COLORS[agent.role] ?? "#e94560") }),
    });
    actionText.x = bx; actionText.y = bby;
    container.addChild(actionText);
  }

  // Thinking dots
  if (isThinking) {
    for (let i = 0; i < 3; i++) {
      const dotAlpha = (Math.sin(t / 300 + i * 0.8) + 1) / 2;
      const dg = new Graphics();
      dg.circle(ix + 16 + i * 6, by - 38 + Math.sin(t / 500 + i) * 2, 2);
      dg.fill({ color, alpha: dotAlpha * 0.7 });
      container.addChild(dg);
    }
  }

  // Name
  const name = new Text({
    text: agent.name,
    style: new TextStyle({
      fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
      fontSize: 7,
      fill: 0xffffff,
      stroke: { color: 0x000000, width: 3 },
    }),
  });
  name.anchor.set(0.5, 0); name.x = ix; name.y = iy + 18;
  container.addChild(name);
}

// ─── Main Component ───
export default function IsometricOffice({ agents, width = 700, height = 620 }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const agentPositions = useRef<Map<string, { x: number; y: number }>>(new Map());
  const particles = useRef<Particle[]>([]);

  const updatePositions = useCallback(() => {
    for (const agent of agents) {
      const cur = agentPositions.current.get(agent.id) ?? { x: agent.position_x, y: agent.position_y };
      const tx = agent.target_x || agent.position_x;
      const ty = agent.target_y || agent.position_y;
      agentPositions.current.set(agent.id, {
        x: cur.x + (tx - cur.x) * 0.06,
        y: cur.y + (ty - cur.y) * 0.06,
      });
    }
  }, [agents]);

  useEffect(() => {
    if (!canvasRef.current) return;
    const app = new Application();
    let mounted = true;

    (async () => {
      await app.init({
        width, height,
        background: 0x0a0e17,
        antialias: true,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
      });
      if (!mounted || !canvasRef.current) return;
      canvasRef.current.innerHTML = "";
      canvasRef.current.appendChild(app.canvas);
      appRef.current = app;

      const world = new Container();
      world.x = width / 2;
      world.y = 80;
      app.stage.addChild(world);

      const GRID = 8;

      // Particle layer
      const particleG = new Graphics();
      world.addChild(particleG);
      spawnParticles(particles.current, 40, { w: 500, h: 400 });

      // Static layers (drawn once, updated for animations)
      const floorG = new Graphics();
      drawFloor(floorG, GRID, GRID);
      world.addChild(floorG);

      const rugG = new Graphics();
      drawRug(rugG);
      world.addChild(rugG);

      // Dynamic layers
      const wallLayer = new Container();
      world.addChild(wallLayer);

      const furnitureLayer = new Container();
      world.addChild(furnitureLayer);

      const deskLayer = new Container();
      world.addChild(deskLayer);

      const agentLayer = new Container();
      world.addChild(agentLayer);

      // Title
      const title = new Text({
        text: "🏢 AGENTLOOP HQ",
        style: new TextStyle({
          fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
          fontSize: 9,
          fill: 0x3a4f68,
          letterSpacing: 3,
        }),
      });
      title.anchor.set(0.5, 0);
      title.x = 0; title.y = GRID * TILE_H + 16;
      world.addChild(title);

      // Render loop
      app.ticker.add(() => {
        const t = Date.now();
        updatePositions();

        // Particles
        tickParticles(particles.current, particleG, { w: 500, h: 400 });

        // Redraw dynamic elements
        wallLayer.removeChildren();
        const wallG = new Graphics();
        drawWalls(wallG, GRID);
        wallLayer.addChild(wallG);
        drawWindow(wallLayer, GRID, t);
        drawWallArt(wallLayer, GRID);

        furnitureLayer.removeChildren();
        drawFurniture(furnitureLayer, t);

        deskLayer.removeChildren();
        drawDesk(deskLayer, 2, 3, hexToNum(ROLE_COLORS.product_manager), "PM", t);
        drawDesk(deskLayer, 6, 3, hexToNum(ROLE_COLORS.developer), "DEV", t);
        drawDesk(deskLayer, 2, 6, hexToNum(ROLE_COLORS.quality_assurance), "QA", t);
        drawDesk(deskLayer, 6, 6, hexToNum(ROLE_COLORS.deployer), "OPS", t);

        agentLayer.removeChildren();
        const sorted = [...agents].sort((a, b) => {
          const pa = agentPositions.current.get(a.id);
          const pb = agentPositions.current.get(b.id);
          return (pa?.y ?? 0) - (pb?.y ?? 0);
        });
        for (const agent of sorted) {
          const pos = agentPositions.current.get(agent.id) ?? { x: agent.position_x, y: agent.position_y };
          drawAgent(agentLayer, agent, pos, t);
        }
      });
    })();

    return () => { mounted = false; appRef.current?.destroy(true); appRef.current = null; };
  }, [width, height, agents, updatePositions]);

  return (
    <div
      ref={canvasRef}
      className="rounded-xl border border-slate-700/50 overflow-hidden"
      style={{
        width, height,
        background: "linear-gradient(180deg, #080c14 0%, #0d1420 50%, #0a0e17 100%)",
        boxShadow: "0 0 60px rgba(59, 130, 246, 0.08), 0 0 120px rgba(139, 92, 246, 0.04), inset 0 0 60px rgba(0,0,0,0.6)",
      }}
    />
  );
}
