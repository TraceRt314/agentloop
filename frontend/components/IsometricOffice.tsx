"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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
const GRID = 10;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.5;
const FONT = "'Fira Code', 'SF Mono', monospace";

function toIso(x: number, y: number): [number, number] {
  return [(x - y) * (TILE_W / 2), (x + y) * (TILE_H / 2)];
}
function hexToNum(hex: string): number {
  return parseInt(hex.replace("#", ""), 16);
}

// Safely destroy all children of a container
function clearContainer(c: Container) {
  while (c.children.length > 0) {
    const child = c.children[0];
    c.removeChild(child);
    child.destroy({ children: true });
  }
}

// ─── Particles ───
interface Particle {
  x: number; y: number; vx: number; vy: number;
  life: number; maxLife: number; size: number; color: number; alpha: number;
}

function spawnParticles(pool: Particle[], count: number, bounds: { w: number; h: number }) {
  for (let i = 0; i < count; i++) {
    pool.push({
      x: (Math.random() - 0.5) * bounds.w,
      y: (Math.random() - 0.5) * bounds.h,
      vx: (Math.random() - 0.5) * 0.1,
      vy: -Math.random() * 0.15 - 0.03,
      life: Math.random() * 300,
      maxLife: 300 + Math.random() * 200,
      size: Math.random() * 1.5 + 0.3,
      color: [0x60a5fa, 0x4ade80, 0xa78bfa, 0xfbbf24, 0xffffff][Math.floor(Math.random() * 5)],
      alpha: 0,
    });
  }
}

function tickParticles(pool: Particle[], g: Graphics, bounds: { w: number; h: number }) {
  g.clear();
  for (const p of pool) {
    p.x += p.vx; p.y += p.vy; p.life++;
    const progress = p.life / p.maxLife;
    p.alpha = progress < 0.1 ? progress * 10 : progress > 0.8 ? (1 - progress) * 5 : 1;
    p.alpha *= 0.25;
    if (p.life > p.maxLife) {
      p.x = (Math.random() - 0.5) * bounds.w;
      p.y = (Math.random() - 0.5) * bounds.h + bounds.h * 0.3;
      p.life = 0;
    }
    g.circle(p.x, p.y, p.size);
    g.fill({ color: p.color, alpha: p.alpha });
  }
}

// ─── Floor (static — drawn once) ───
function drawFloor(g: Graphics, cols: number, rows: number) {
  for (let x = 0; x < cols; x++) {
    for (let y = 0; y < rows; y++) {
      const [ix, iy] = toIso(x, y);
      const isDark = (x + y) % 2 === 0;
      const base = isDark ? 0x1e2d42 : 0x243348;
      const edgeDist = Math.min(x, y, cols - 1 - x, rows - 1 - y);
      const darken = Math.max(0, 2 - edgeDist) * 0x030303;
      g.poly([
        { x: ix, y: iy }, { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H }, { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.fill({ color: Math.max(0, base - darken), alpha: 0.92 });
      g.poly([
        { x: ix, y: iy }, { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H }, { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.stroke({ color: 0x2e4060, width: 0.3, alpha: 0.2 });
    }
  }
  const [cx, cy] = toIso(cols / 2, rows / 2);
  g.ellipse(cx, cy, 100, 50);
  g.fill({ color: 0xffffff, alpha: 0.012 });
}

// ─── Rug (static) ───
function drawRug(g: Graphics) {
  const [cx, cy] = toIso(5, 5);
  for (let r = 3; r > 0; r--) {
    const colors = [0x1e3a5f, 0x162d4d, 0x0f2240];
    g.ellipse(cx, cy, r * 32, r * 16);
    g.fill({ color: colors[3 - r], alpha: 0.45 });
  }
  for (let i = 0; i < 32; i++) {
    const angle = (i / 32) * Math.PI * 2;
    g.circle(cx + Math.cos(angle) * 90, cy + Math.sin(angle) * 45, 1.2);
    g.fill({ color: 0x3b82f6, alpha: 0.25 });
  }
  for (let i = 0; i < 16; i++) {
    const angle = (i / 16) * Math.PI * 2;
    g.circle(cx + Math.cos(angle) * 50, cy + Math.sin(angle) * 25, 1);
    g.fill({ color: 0xa78bfa, alpha: 0.15 });
  }
}

// ─── Walls (static) ───
function drawWalls(g: Graphics, cols: number) {
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const [brx, bry] = toIso(cols, cols);
  const H = 110;

  // Back wall
  g.poly([{ x: lx, y: ly - H }, { x: rx, y: ry - H }, { x: rx, y: ry }, { x: lx, y: ly }]);
  g.fill({ color: 0x243348 });
  g.stroke({ color: 0x2e4462, width: 1 });
  // Wainscoting
  const panelH = 30;
  g.poly([{ x: lx, y: ly - panelH }, { x: rx, y: ry - panelH }, { x: rx, y: ry }, { x: lx, y: ly }]);
  g.fill({ color: 0x1e2d42, alpha: 0.6 });
  for (let i = 0; i <= 5; i++) {
    const px = lx + (rx - lx) * (i / 5);
    const py = ly + (ry - ly) * (i / 5);
    g.moveTo(px, py - panelH); g.lineTo(px, py);
    g.stroke({ color: 0x2a3f5a, width: 0.5, alpha: 0.4 });
  }
  // Crown molding
  g.poly([{ x: lx, y: ly - H }, { x: rx, y: ry - H }, { x: rx, y: ry - H + 4 }, { x: lx, y: ly - H + 4 }]);
  g.fill({ color: 0x2e4462, alpha: 0.8 });
  // Baseboard
  g.poly([{ x: lx, y: ly - 5 }, { x: rx, y: ry - 5 }, { x: rx, y: ry }, { x: lx, y: ly }]);
  g.fill({ color: 0x1a2840, alpha: 0.9 });

  // Right wall
  g.poly([{ x: rx, y: ry - H }, { x: brx, y: bry - H }, { x: brx, y: bry }, { x: rx, y: ry }]);
  g.fill({ color: 0x1c2b3e });
  g.stroke({ color: 0x253a52, width: 1 });
  g.poly([{ x: rx, y: ry - panelH }, { x: brx, y: bry - panelH }, { x: brx, y: bry }, { x: rx, y: ry }]);
  g.fill({ color: 0x182738, alpha: 0.6 });
  for (let i = 0; i <= 5; i++) {
    const px = rx + (brx - rx) * (i / 5);
    const py = ry + (bry - ry) * (i / 5);
    g.moveTo(px, py - panelH); g.lineTo(px, py);
    g.stroke({ color: 0x223550, width: 0.5, alpha: 0.4 });
  }
  g.poly([{ x: rx, y: ry - H }, { x: brx, y: bry - H }, { x: brx, y: bry - H + 4 }, { x: rx, y: ry - H + 4 }]);
  g.fill({ color: 0x253a52, alpha: 0.8 });
  g.poly([{ x: rx, y: ry - 5 }, { x: brx, y: bry - 5 }, { x: brx, y: bry }, { x: rx, y: ry }]);
  g.fill({ color: 0x152236, alpha: 0.9 });
  // Corner highlight
  g.moveTo(rx, ry - H); g.lineTo(rx, ry);
  g.stroke({ color: 0x3a5575, width: 2 });
}

// ─── Window (animated — reuses a single Graphics) ───
function drawWindow(g: Graphics, cols: number, t: number) {
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const H = 110;
  const wx = lx + (rx - lx) * 0.5;
  const wy = ly + (ry - ly) * 0.5 - H + 22;

  // Frame
  g.roundRect(wx - 60, wy, 120, 60, 3);
  g.fill({ color: 0x0c1829 });
  g.stroke({ color: 0x4a6480, width: 3 });
  // Sky
  g.roundRect(wx - 56, wy + 4, 112, 52, 2);
  g.fill({ color: 0x0f1d3a, alpha: 0.95 });
  g.roundRect(wx - 56, wy + 34, 112, 22, 2);
  g.fill({ color: 0x1a2d55, alpha: 0.4 });
  // Stars
  for (let i = 0; i < 12; i++) {
    const sx = wx - 48 + ((i * 37 + 13) % 96);
    const sy = wy + 8 + ((i * 23 + 7) % 40);
    const twinkle = (Math.sin(t / 400 + i * 1.7) + 1) / 2;
    g.circle(sx, sy, 0.8 + twinkle * 0.5);
    g.fill({ color: 0xffffff, alpha: 0.25 + twinkle * 0.55 });
  }
  // Moon
  g.circle(wx + 30, wy + 16, 10);
  g.fill({ color: 0xe2e8f0, alpha: 0.65 + Math.sin(t / 3000) * 0.1 });
  g.circle(wx + 33, wy + 14, 8);
  g.fill({ color: 0x0f1d3a });
  // Cityscape
  const buildings = [
    { x: -44, w: 12, h: 20 }, { x: -30, w: 8, h: 28 }, { x: -20, w: 14, h: 18 },
    { x: -4, w: 10, h: 32 }, { x: 8, w: 16, h: 22 }, { x: 26, w: 10, h: 26 },
    { x: 38, w: 12, h: 16 },
  ];
  for (const b of buildings) {
    g.rect(wx + b.x, wy + 56 - b.h, b.w, b.h);
    g.fill({ color: 0x0a1525, alpha: 0.9 });
    for (let wy2 = 0; wy2 < b.h - 6; wy2 += 5) {
      for (let wx2 = 2; wx2 < b.w - 3; wx2 += 4) {
        if (Math.sin(t / 2000 + b.x + wy2 + wx2) > 0.2) {
          g.rect(wx + b.x + wx2, wy + 56 - b.h + wy2 + 2, 2, 3);
          g.fill({ color: 0xfbbf24, alpha: 0.5 });
        }
      }
    }
  }
  // Cross bars
  g.moveTo(wx, wy); g.lineTo(wx, wy + 60);
  g.stroke({ color: 0x4a6480, width: 2 });
  g.moveTo(wx - 60, wy + 30); g.lineTo(wx + 60, wy + 30);
  g.stroke({ color: 0x4a6480, width: 2 });
  // Sill
  g.roundRect(wx - 64, wy + 58, 128, 6, 1);
  g.fill({ color: 0x2e4462 });
  // Light cone on floor
  const [flx, fly] = toIso(3, 3);
  g.ellipse(flx, fly, 60, 30);
  g.fill({ color: 0x3b82f6, alpha: 0.02 + Math.sin(t / 4000) * 0.006 });
}

// ─── Ceiling lights (animated) ───
function drawCeilingLights(g: Graphics, t: number) {
  const lightPositions: [number, number][] = [[3, 3], [7, 3], [3, 7], [7, 7]];
  for (const [lx, ly] of lightPositions) {
    const [ix, iy] = toIso(lx, ly);
    g.moveTo(ix, iy - 120); g.lineTo(ix, iy - 90);
    g.stroke({ color: 0x475569, width: 1 });
    g.poly([
      { x: ix - 12, y: iy - 90 }, { x: ix + 12, y: iy - 90 },
      { x: ix + 8, y: iy - 96 }, { x: ix - 8, y: iy - 96 },
    ]);
    g.fill({ color: 0x334155 });
    g.circle(ix, iy - 88, 3);
    g.fill({ color: 0xfef3c7, alpha: 0.9 });
    const flicker = Math.sin(t / 1500 + lx * 2) * 0.005;
    g.ellipse(ix, iy, 40, 20);
    g.fill({ color: 0xfef3c7, alpha: 0.025 + flicker });
    g.ellipse(ix, iy, 24, 12);
    g.fill({ color: 0xfef3c7, alpha: 0.02 + flicker });
  }
}

// ─── Wall art (animated clock) ───
function drawWallArt(g: Graphics, cols: number) {
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const [brx, bry] = toIso(cols, cols);

  // Clock
  const cx = lx + (rx - lx) * 0.15;
  const cy = ly + (ry - ly) * 0.15 - 80;
  g.circle(cx, cy, 14);
  g.fill({ color: 0x1e293b });
  g.stroke({ color: 0x64748b, width: 2 });
  g.circle(cx, cy, 12);
  g.fill({ color: 0xf0f0f0, alpha: 0.92 });
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
    const r1 = i % 3 === 0 ? 8 : 9.5;
    g.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
    g.lineTo(cx + Math.cos(a) * 11, cy + Math.sin(a) * 11);
    g.stroke({ color: 0x333333, width: i % 3 === 0 ? 1.5 : 0.5 });
  }
  const now = new Date();
  const hAngle = ((now.getHours() % 12 + now.getMinutes() / 60) / 12) * Math.PI * 2 - Math.PI / 2;
  const mAngle = (now.getMinutes() / 60) * Math.PI * 2 - Math.PI / 2;
  g.moveTo(cx, cy); g.lineTo(cx + Math.cos(hAngle) * 5, cy + Math.sin(hAngle) * 5);
  g.stroke({ color: 0x1a1a1a, width: 2 });
  g.moveTo(cx, cy); g.lineTo(cx + Math.cos(mAngle) * 8, cy + Math.sin(mAngle) * 8);
  g.stroke({ color: 0x333333, width: 1.2 });
  g.circle(cx, cy, 1.5);
  g.fill({ color: 0xe94560 });

  // Poster on right wall
  const px = rx + (brx - rx) * 0.35;
  const py = ry + (bry - ry) * 0.35 - 72;
  g.roundRect(px - 18, py, 36, 28, 2);
  g.fill({ color: 0x1a1a2e });
  g.stroke({ color: 0x64748b, width: 1.5 });
  for (let i = 0; i < 5; i++) {
    const bh = 5 + ((i * 7 + 3) % 10);
    g.rect(px - 14 + i * 6, py + 24 - bh, 4, bh);
    g.fill({ color: [0xe94560, 0x60a5fa, 0x4ade80, 0xfbbf24, 0xa78bfa][i], alpha: 0.75 });
  }

  // Logo on right wall
  const p2x = rx + (brx - rx) * 0.65;
  const p2y = ry + (bry - ry) * 0.65 - 72;
  g.roundRect(p2x - 16, p2y, 32, 24, 2);
  g.fill({ color: 0x0f172a });
  g.stroke({ color: 0x475569, width: 1 });
  g.circle(p2x, p2y + 12, 8);
  g.stroke({ color: 0x3b82f6, width: 1.5 });
  g.circle(p2x, p2y + 12, 4);
  g.fill({ color: 0x3b82f6, alpha: 0.3 });

  // Neon sign on back wall
  const atx = lx + (rx - lx) * 0.75;
  const aty = ly + (ry - ly) * 0.75 - 80;
  g.roundRect(atx - 30, aty, 60, 16, 2);
  g.fill({ color: 0x0f172a, alpha: 0.6 });
  g.stroke({ color: 0x3b82f6, width: 1, alpha: 0.4 });

  // Door on right wall
  const dx = rx + (brx - rx) * 0.88;
  const dy = ry + (bry - ry) * 0.88;
  g.roundRect(dx - 14, dy - 60, 28, 60, 1);
  g.fill({ color: 0x1a2840 });
  g.stroke({ color: 0x334155, width: 2 });
  g.roundRect(dx - 12, dy - 58, 24, 56, 1);
  g.fill({ color: 0x2a3f5a });
  g.circle(dx + 7, dy - 30, 2.5);
  g.fill({ color: 0xd4a45a });
  g.roundRect(dx - 9, dy - 54, 18, 22, 1);
  g.stroke({ color: 0x334155, width: 0.8 });
  g.roundRect(dx - 9, dy - 28, 18, 22, 1);
  g.stroke({ color: 0x334155, width: 0.8 });
  // EXIT sign
  g.roundRect(dx - 10, dy - 68, 20, 6, 1);
  g.fill({ color: 0x22c55e, alpha: 0.8 });
}

// ─── Desk (uses single Graphics, no Text per frame) ───
function drawDesk(g: Graphics, gx: number, gy: number, color: number, t: number) {
  const [ix, iy] = toIso(gx, gy);
  const dw = 56, dh = 28;

  // Shadow
  g.ellipse(ix, iy + 4, 30, 12);
  g.fill({ color: 0x000000, alpha: 0.18 });
  // Legs
  for (const [ox, oy] of [[-dw / 2 + 5, dh / 2 - 3], [dw / 2 - 5, dh / 2 - 3], [-dw / 2 + 5, -dh / 2 + 3], [dw / 2 - 5, -dh / 2 + 3]]) {
    g.rect(ix + ox - 1.5, iy - 16 + oy, 3, 16);
    g.fill({ color: 0x5a3e10, alpha: 0.7 });
  }
  // Top
  g.poly([
    { x: ix, y: iy - 18 }, { x: ix + dw / 2, y: iy - 18 + dh / 2 },
    { x: ix, y: iy - 18 + dh }, { x: ix - dw / 2, y: iy - 18 + dh / 2 },
  ]);
  g.fill({ color: 0xb8860b });
  g.stroke({ color: 0x8b6914, width: 1 });
  for (let i = 0; i < 3; i++) {
    const gy2 = iy - 18 + dh / 2 - 6 + i * 4;
    g.moveTo(ix - dw / 4, gy2); g.lineTo(ix + dw / 4, gy2);
    g.stroke({ color: 0xa67c00, width: 0.5, alpha: 0.25 });
  }
  // Front face
  g.poly([
    { x: ix - dw / 2, y: iy - 18 + dh / 2 }, { x: ix, y: iy - 18 + dh },
    { x: ix, y: iy - 4 }, { x: ix - dw / 2, y: iy + 10 },
  ]);
  g.fill({ color: 0x8b6914, alpha: 0.5 });
  // Monitor
  g.roundRect(ix - 12, iy - 42, 24, 18, 2);
  g.fill({ color: 0x0f172a });
  g.stroke({ color: 0x334155, width: 1.5 });
  const flicker = Math.sin(t / 200) * 0.04;
  g.roundRect(ix - 10, iy - 40, 20, 14, 1);
  g.fill({ color, alpha: 0.12 + flicker });
  for (let i = 0; i < 5; i++) {
    const lw = 3 + Math.sin(t / 600 + i * 1.3) * 3 + 4;
    g.rect(ix - 8, iy - 38 + i * 2.8, lw, 1.2);
    g.fill({ color, alpha: 0.45 + Math.sin(t / 400 + i) * 0.15 });
  }
  // Stand
  g.rect(ix - 2, iy - 24, 4, 5);
  g.fill({ color: 0x334155 });
  g.rect(ix - 6, iy - 19, 12, 2);
  g.fill({ color: 0x334155 });
  // Keyboard
  g.roundRect(ix - 9, iy - 15, 18, 6, 1);
  g.fill({ color: 0x1e293b, alpha: 0.85 });
  g.stroke({ color: 0x334155, width: 0.5 });
  // Mouse
  g.ellipse(ix + 14, iy - 14, 2.5, 3.5);
  g.fill({ color: 0x1e293b });
  // Coffee mug
  g.roundRect(ix - 18, iy - 20, 6, 7, 1);
  g.fill({ color: 0xffffff, alpha: 0.85 });
  g.arc(ix - 12, iy - 17, 3, -Math.PI / 2, Math.PI / 2, false);
  g.stroke({ color: 0xcccccc, width: 1 });
  // Steam
  for (let i = 0; i < 2; i++) {
    const sy = iy - 24 - Math.sin(t / 400 + i * 2) * 4;
    g.circle(ix - 16 + i * 3, sy, 1.5);
    g.fill({ color: 0xffffff, alpha: 0.1 - i * 0.03 });
  }
  // Desk lamp
  g.rect(ix + dw / 2 - 2, iy - 30, 2, 14);
  g.fill({ color: 0x475569 });
  g.ellipse(ix + dw / 2 + 2, iy - 32, 7, 3);
  g.fill({ color: 0xfbbf24, alpha: 0.65 });
  g.ellipse(ix + dw / 2, iy - 18, 12, 5);
  g.fill({ color: 0xfbbf24, alpha: 0.04 });
}

// ─── Furniture (static parts + animated LEDs) ───
function drawFurniture(g: Graphics, t: number) {
  // ── Bookshelf ──
  const [bsx, bsy] = toIso(9.5, 2);
  g.roundRect(bsx - 14, bsy - 48, 28, 48, 2);
  g.fill({ color: 0x5a3e10 });
  g.stroke({ color: 0x4a2e08, width: 1 });
  for (let s = 0; s < 4; s++) {
    g.rect(bsx - 12, bsy - 44 + s * 11, 24, 2);
    g.fill({ color: 0x6b4f12 });
    for (let b = 0; b < 5; b++) {
      const bw = 2.5 + (b * 7 + s * 3) % 3;
      const bh = 5 + (b * 11 + s * 5) % 5;
      const bc = [0xe94560, 0x3b82f6, 0x4ade80, 0xfbbf24, 0xa78bfa][(b + s) % 5];
      g.rect(bsx - 10 + b * 4.5, bsy - 42 + s * 11 - bh, bw, bh);
      g.fill({ color: bc, alpha: 0.65 });
    }
  }

  // ── Coffee machine ──
  const [cmx, cmy] = toIso(8.5, 0.8);
  g.poly([
    { x: cmx - 20, y: cmy - 14 }, { x: cmx + 20, y: cmy - 14 },
    { x: cmx + 20, y: cmy + 4 }, { x: cmx - 20, y: cmy + 4 },
  ]);
  g.fill({ color: 0x2a2a3e });
  g.roundRect(cmx - 10, cmy - 32, 20, 20, 2);
  g.fill({ color: 0x1e1e30 });
  g.stroke({ color: 0x444466, width: 1 });
  g.roundRect(cmx - 6, cmy - 28, 12, 8, 1);
  g.fill({ color: 0x0a0a1a });
  g.circle(cmx + 6, cmy - 14, 2);
  g.fill({ color: 0x4ade80, alpha: 0.6 + Math.sin(t / 500) * 0.3 });
  for (let i = 0; i < 3; i++) {
    const sx = cmx - 2 + i * 2;
    const sy = cmy - 36 - Math.sin(t / 300 + i * 1.5) * 5;
    g.circle(sx, sy, 2);
    g.fill({ color: 0xffffff, alpha: Math.max(0, 0.12 - i * 0.04) });
  }

  // ── Water cooler ──
  const [wcx, wcy] = toIso(9.2, 5);
  g.roundRect(wcx - 8, wcy - 6, 16, 6, 1);
  g.fill({ color: 0x475569 });
  g.roundRect(wcx - 6, wcy - 28, 12, 22, 2);
  g.fill({ color: 0xf0f0f0, alpha: 0.9 });
  g.stroke({ color: 0xd0d0d0, width: 1 });
  g.roundRect(wcx - 5, wcy - 44, 10, 18, 3);
  g.fill({ color: 0x93c5fd, alpha: 0.4 });
  g.circle(wcx + 3, wcy - 10, 1.5);
  g.fill({ color: 0x64748b });

  // ── Server rack ──
  const [srx, sry] = toIso(9, 8);
  g.roundRect(srx - 14, sry - 50, 28, 52, 2);
  g.fill({ color: 0x0a0f1a });
  g.stroke({ color: 0x1e2d42, width: 1.5 });
  for (let i = 0; i < 5; i++) {
    g.roundRect(srx - 11, sry - 46 + i * 10, 22, 8, 1);
    g.fill({ color: 0x111827 });
    g.stroke({ color: 0x1f2937, width: 0.5 });
    const led1 = Math.sin(t / 200 + i * 1.7) > 0;
    g.circle(srx - 7, sry - 42 + i * 10, 2);
    g.fill({ color: led1 ? 0x4ade80 : 0x1a2e1a });
    const led2 = Math.sin(t / 80 + i * 3) > 0.5;
    g.circle(srx - 3, sry - 42 + i * 10, 1.5);
    g.fill({ color: led2 ? 0xfbbf24 : 0x2a2a1a, alpha: led2 ? 0.8 : 0.3 });
    for (let d = 0; d < 4; d++) {
      g.rect(srx + 1 + d * 4, sry - 44 + i * 10, 3, 4);
      g.fill({ color: 0x1a2030 });
    }
  }
  g.ellipse(srx, sry + 4, 18, 8);
  g.fill({ color: 0x4ade80, alpha: 0.025 });

  // ── Filing cabinet ──
  const [fcx, fcy] = toIso(0.5, 5);
  g.roundRect(fcx - 10, fcy - 34, 20, 34, 2);
  g.fill({ color: 0x475569 });
  g.stroke({ color: 0x64748b, width: 1 });
  for (let d = 0; d < 3; d++) {
    g.roundRect(fcx - 8, fcy - 30 + d * 10, 16, 8, 1);
    g.fill({ color: 0x334155 });
    g.stroke({ color: 0x3f5168, width: 0.5 });
    g.roundRect(fcx - 3, fcy - 26 + d * 10, 6, 2, 0.5);
    g.fill({ color: 0x94a3b8 });
  }

  // ── Coat rack ──
  const [crx, cry] = toIso(0.3, 8.5);
  g.ellipse(crx, cry, 8, 4);
  g.fill({ color: 0x475569, alpha: 0.7 });
  g.rect(crx - 1.5, cry - 42, 3, 42);
  g.fill({ color: 0x5a3e10 });
  for (let h = 0; h < 3; h++) {
    const angle = (h / 3) * Math.PI * 2 + Math.PI / 6;
    g.moveTo(crx, cry - 38);
    g.lineTo(crx + Math.cos(angle) * 10, cry - 38 + Math.sin(angle) * 4);
    g.stroke({ color: 0x5a3e10, width: 2 });
  }
  g.ellipse(crx + 8, cry - 32, 6, 8);
  g.fill({ color: 0x334155, alpha: 0.8 });

  // ── Plants ──
  for (const [px, py, size] of [[0.3, 2, 1.1], [9.5, 0.3, 0.85], [0.3, 0.3, 1.0], [5, 9.2, 0.9]] as [number, number, number][]) {
    const [plx, ply] = toIso(px, py);
    g.poly([
      { x: plx - 6 * size, y: ply - 4 }, { x: plx + 6 * size, y: ply - 4 },
      { x: plx + 4 * size, y: ply + 6 }, { x: plx - 4 * size, y: ply + 6 },
    ]);
    g.fill({ color: 0x8b4513 });
    g.stroke({ color: 0x6b3410, width: 1 });
    g.ellipse(plx, ply - 4, 6 * size, 2.5);
    g.fill({ color: 0x3e2723 });
    for (let l = 0; l < 6; l++) {
      const angle = (l / 6) * Math.PI * 2 + Math.sin(t / 1500 + l) * 0.12;
      const dist = 8 * size + Math.sin(t / 2000 + l * 2) * 1.2;
      g.ellipse(plx + Math.cos(angle) * dist, ply - 10 * size + Math.sin(angle) * dist * 0.4, 5 * size, 3 * size);
      g.fill({ color: l % 2 === 0 ? 0x2d6a2d : 0x3a8a3a, alpha: 0.85 });
    }
    g.moveTo(plx, ply - 4); g.lineTo(plx, ply - 14 * size);
    g.stroke({ color: 0x2d5a2d, width: 1.5 });
  }

  // ── Whiteboard ──
  const [wx, wy] = toIso(2, 0.3);
  g.roundRect(wx - 42, wy - 50, 84, 52, 2);
  g.fill({ color: 0xf8f8f8 });
  g.stroke({ color: 0x94a3b8, width: 2.5 });
  g.roundRect(wx - 38, wy - 46, 76, 44, 1);
  g.fill({ color: 0xf5f5f5 });
  const stickies = [
    { x: -30, y: -42, w: 14, h: 12, color: 0xfbbf24 },
    { x: -12, y: -44, w: 14, h: 14, color: 0xf87171 },
    { x: 6, y: -40, w: 14, h: 12, color: 0x4ade80 },
    { x: 24, y: -42, w: 14, h: 12, color: 0x60a5fa },
    { x: -24, y: -26, w: 14, h: 12, color: 0xa78bfa },
    { x: -6, y: -28, w: 14, h: 14, color: 0xfbbf24 },
    { x: 12, y: -24, w: 14, h: 12, color: 0xf87171 },
    { x: 28, y: -26, w: 14, h: 12, color: 0x4ade80 },
  ];
  for (const s of stickies) {
    g.roundRect(wx + s.x, wy + s.y, s.w, s.h, 1);
    g.fill({ color: s.color, alpha: 0.85 });
    for (let i = 0; i < 2; i++) {
      g.rect(wx + s.x + 2, wy + s.y + 3 + i * 3, s.w - 4, 1.5);
      g.fill({ color: 0x000000, alpha: 0.12 });
    }
  }
  // Tray
  g.roundRect(wx - 36, wy + 2, 72, 4, 1);
  g.fill({ color: 0x94a3b8 });
  for (let i = 0; i < 3; i++) {
    g.roundRect(wx - 28 + i * 8, wy + 2, 5, 3, 0.5);
    g.fill({ color: [0xe94560, 0x3b82f6, 0x22c55e][i] });
  }

  // ── Meeting table ──
  const [mx, my] = toIso(5, 5);
  g.ellipse(mx, my + 2, 28, 12);
  g.fill({ color: 0x000000, alpha: 0.12 });
  g.ellipse(mx, my - 8, 26, 13);
  g.fill({ color: 0xa67c00 });
  g.stroke({ color: 0x8b6914, width: 1.5 });
  g.ellipse(mx, my - 10, 18, 9);
  g.fill({ color: 0xb8860b, alpha: 0.35 });
  g.rect(mx - 2, my - 8, 4, 10);
  g.fill({ color: 0x6b4f12 });
  // Chairs
  for (let i = 0; i < 5; i++) {
    const angle = (i / 5) * Math.PI * 2 + Math.PI / 5;
    const chairX = mx + Math.cos(angle) * 35;
    const chairY = my - 4 + Math.sin(angle) * 17;
    g.ellipse(chairX, chairY, 5, 3);
    g.fill({ color: 0x334155, alpha: 0.75 });
    g.arc(chairX, chairY - 2, 5, Math.PI + 0.5, -0.5, false);
    g.fill({ color: 0x3a4f6a, alpha: 0.8 });
  }
}

// ─── Agent drawing (to a shared Graphics + text container) ───
function drawAgent(g: Graphics, textContainer: Container, agent: AgentState, pos: { x: number; y: number }, t: number) {
  const [ix, iy] = toIso(pos.x / 60, pos.y / 60);
  const color = hexToNum(ROLE_COLORS[agent.role] ?? ROLE_COLORS.default);
  const isWorking = agent.current_action === "working";
  const isWalking = agent.current_action === "walking";
  const isTalking = agent.current_action === "talking";
  const isThinking = agent.current_action === "thinking";

  const bounce = isWalking ? Math.sin(t / 120) * 4 : 0;
  const breathe = Math.sin(t / 800) * 0.8;
  const idleSway = Math.sin(t / 2000 + pos.x) * 1;
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

  // Body
  g.roundRect(ix - 9 + idleSway, by - 8, 18, 16, 3);
  g.fill({ color });
  // Shirt line
  g.moveTo(ix + idleSway, by - 6); g.lineTo(ix + idleSway, by + 6);
  g.stroke({ color: 0xffffff, width: 0.5, alpha: 0.12 });
  // Badge
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
    g.circle(ix - 11 + idleSway, by + 10, 2.5);
    g.fill({ color: 0xfcd5b0 });
    g.circle(ix + 11 + idleSway, by + 10, 2.5);
    g.fill({ color: 0xfcd5b0 });
  }

  // Head
  g.circle(ix + idleSway, by - 16, 9);
  g.fill({ color: 0xfcd5b0 });
  g.stroke({ color: 0xe8b898, width: 0.8 });
  // Hair
  g.arc(ix + idleSway, by - 18, 9, Math.PI + 0.3, -0.3, false);
  g.fill({ color, alpha: 0.85 });

  // Eyes
  const blinkPhase = Math.sin(t / 3000 + pos.x * 0.1);
  const eyeH = blinkPhase > 0.95 ? 0.5 : 2;
  g.ellipse(ix - 3 + idleSway, by - 17, 1.8, eyeH);
  g.fill({ color: 0x1a1a2e });
  g.ellipse(ix + 3 + idleSway, by - 17, 1.8, eyeH);
  g.fill({ color: 0x1a1a2e });

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

  // Action bubble (Graphics only, no Text)
  if (agent.current_action !== "idle") {
    const bx = ix + 18; const bby = by - 36;
    g.roundRect(bx - 4, bby - 2, 46, 14, 6);
    g.fill({ color: 0xffffff, alpha: 0.92 });
    g.stroke({ color, width: 1.5, alpha: 0.6 });
    g.poly([
      { x: bx + 2, y: bby + 12 }, { x: bx - 4, y: bby + 20 }, { x: bx + 12, y: bby + 12 },
    ]);
    g.fill({ color: 0xffffff, alpha: 0.92 });
  }

  // Thinking dots
  if (isThinking) {
    for (let i = 0; i < 3; i++) {
      const dotAlpha = (Math.sin(t / 300 + i * 0.8) + 1) / 2;
      g.circle(ix + 16 + i * 6, by - 38 + Math.sin(t / 500 + i) * 2, 2);
      g.fill({ color, alpha: dotAlpha * 0.7 });
    }
  }

  // Text elements (created sparingly in textContainer)
  // Name label
  const nameText = new Text({
    text: agent.name,
    style: new TextStyle({
      fontFamily: FONT, fontSize: 7, fill: 0xffffff,
      stroke: { color: 0x000000, width: 3 },
    }),
  });
  nameText.anchor.set(0.5, 0); nameText.x = ix; nameText.y = iy + 18;
  textContainer.addChild(nameText);

  // Action label text
  if (agent.current_action !== "idle") {
    const icons: Record<string, string> = {
      working: ">>", talking: ">_", reviewing: "?!", thinking: "..", walking: "->",
    };
    const bx = ix + 18; const bby = by - 36;
    const actionText = new Text({
      text: `${icons[agent.current_action] ?? "-"} ${agent.current_action}`,
      style: new TextStyle({
        fontFamily: "monospace", fontSize: 8,
        fill: hexToNum(ROLE_COLORS[agent.role] ?? "#e94560"),
      }),
    });
    actionText.x = bx; actionText.y = bby - 1;
    textContainer.addChild(actionText);
  }
}

// ─── Main Component ───
export default function IsometricOffice({ agents, width = 700, height = 620 }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const worldRef = useRef<Container | null>(null);

  // Store agents in a ref so the render loop always reads current values
  // WITHOUT triggering a full app recreation
  const agentsRef = useRef<AgentState[]>(agents);
  agentsRef.current = agents;

  const agentPositions = useRef<Map<string, { x: number; y: number }>>(new Map());
  const particles = useRef<Particle[]>([]);
  const zoomRef = useRef(0.85);
  const panRef = useRef({ x: 0, y: 0 });
  const draggingRef = useRef(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(0.85);

  const resetView = useCallback(() => {
    zoomRef.current = 0.85;
    panRef.current = { x: 0, y: 0 };
    setZoom(0.85);
    if (worldRef.current) {
      worldRef.current.scale.set(0.85);
      worldRef.current.x = width / 2;
      worldRef.current.y = 100;
    }
  }, [width]);

  // PixiJS app — created ONCE on mount, NOT on every agents update
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
      world.x = width / 2 + panRef.current.x;
      world.y = 100 + panRef.current.y;
      world.scale.set(zoomRef.current);
      app.stage.addChild(world);
      worldRef.current = world;

      // ── Event listeners ──
      const canvas = app.canvas;

      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.08 : 0.08;
        const nz = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomRef.current + delta));
        zoomRef.current = nz;
        setZoom(nz);
        world.scale.set(nz);
      };

      const onMouseDown = (e: MouseEvent) => {
        if (e.button === 0) {
          draggingRef.current = true;
          lastMouseRef.current = { x: e.clientX, y: e.clientY };
          canvas.style.cursor = "grabbing";
        }
      };

      const onMouseMove = (e: MouseEvent) => {
        if (!draggingRef.current) return;
        const dx = e.clientX - lastMouseRef.current.x;
        const dy = e.clientY - lastMouseRef.current.y;
        panRef.current.x += dx;
        panRef.current.y += dy;
        world.x = width / 2 + panRef.current.x;
        world.y = 100 + panRef.current.y;
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
      };

      const onMouseUp = () => {
        draggingRef.current = false;
        canvas.style.cursor = "grab";
      };

      canvas.addEventListener("wheel", onWheel, { passive: false });
      canvas.addEventListener("mousedown", onMouseDown);
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      canvas.style.cursor = "grab";

      // ── Static layers (drawn ONCE) ──
      const particleG = new Graphics();
      world.addChild(particleG);
      if (particles.current.length === 0) {
        spawnParticles(particles.current, 50, { w: 600, h: 500 });
      }

      const floorG = new Graphics();
      drawFloor(floorG, GRID, GRID);
      world.addChild(floorG);

      const rugG = new Graphics();
      drawRug(rugG);
      world.addChild(rugG);

      const wallG = new Graphics();
      drawWalls(wallG, GRID);
      world.addChild(wallG);

      // ── Animated layers — single Graphics objects, cleared each frame ──
      const animatedWallG = new Graphics();
      world.addChild(animatedWallG);

      const furnitureG = new Graphics();
      world.addChild(furnitureG);

      const deskG = new Graphics();
      world.addChild(deskG);

      const agentG = new Graphics();
      world.addChild(agentG);

      // Text container for labels — cleared each frame
      const textLayer = new Container();
      world.addChild(textLayer);

      // Static text (drawn once)
      const staticTextLayer = new Container();
      world.addChild(staticTextLayer);

      const deskLabels = [
        { gx: 2.5, gy: 3, label: "PM" },
        { gx: 7, gy: 3, label: "DEV" },
        { gx: 2.5, gy: 7, label: "QA" },
        { gx: 7, gy: 7, label: "OPS" },
      ];
      for (const dl of deskLabels) {
        const [dix, diy] = toIso(dl.gx, dl.gy);
        const t = new Text({
          text: dl.label,
          style: new TextStyle({ fontFamily: "monospace", fontSize: 7, fill: 0x6b7fa0 }),
        });
        t.anchor.set(0.5, 0); t.x = dix; t.y = diy + 6;
        staticTextLayer.addChild(t);
      }

      // Wall text labels (static)
      const [lx2, ly2] = toIso(0, 0);
      const [rx2, ry2] = toIso(GRID, 0);
      const atx = lx2 + (rx2 - lx2) * 0.75;
      const aty = ly2 + (ry2 - ly2) * 0.75 - 80;
      const alText = new Text({
        text: "AGENTLOOP",
        style: new TextStyle({ fontFamily: "monospace", fontSize: 6, fill: 0x3b82f6, letterSpacing: 2, fontWeight: "bold" }),
      });
      alText.anchor.set(0.5, 0.5); alText.x = atx; alText.y = aty + 8;
      staticTextLayer.addChild(alText);

      // EXIT sign text
      const [brx2, bry2] = toIso(GRID, GRID);
      const dx = rx2 + (brx2 - rx2) * 0.88;
      const dy = ry2 + (bry2 - ry2) * 0.88;
      const exitT = new Text({
        text: "EXIT",
        style: new TextStyle({ fontFamily: "monospace", fontSize: 4, fill: 0xffffff, fontWeight: "bold" }),
      });
      exitT.anchor.set(0.5, 0.5); exitT.x = dx; exitT.y = dy - 65;
      staticTextLayer.addChild(exitT);

      // Title
      const title = new Text({
        text: "AGENTLOOP HQ",
        style: new TextStyle({
          fontFamily: FONT, fontSize: 9, fill: 0x3a4f68, letterSpacing: 4,
        }),
      });
      title.anchor.set(0.5, 0);
      title.x = 0; title.y = GRID * TILE_H + 20;
      staticTextLayer.addChild(title);

      // ── Render loop ──
      let frameCount = 0;
      app.ticker.add(() => {
        const t = Date.now();
        frameCount++;
        const currentAgents = agentsRef.current;

        // Update positions (interpolate toward targets)
        for (const agent of currentAgents) {
          const cur = agentPositions.current.get(agent.id) ?? { x: agent.position_x, y: agent.position_y };
          const tx = agent.target_x || agent.position_x;
          const ty = agent.target_y || agent.position_y;
          agentPositions.current.set(agent.id, {
            x: cur.x + (tx - cur.x) * 0.06,
            y: cur.y + (ty - cur.y) * 0.06,
          });
        }

        // Particles
        tickParticles(particles.current, particleG, { w: 600, h: 500 });

        // Animated wall elements (window, lights, clock, etc.) — redraw every 2 frames
        if (frameCount % 2 === 0) {
          animatedWallG.clear();
          drawWindow(animatedWallG, GRID, t);
          drawCeilingLights(animatedWallG, t);
          drawWallArt(animatedWallG, GRID);
        }

        // Furniture — redraw every 3 frames (LEDs don't need 60fps)
        if (frameCount % 3 === 0) {
          furnitureG.clear();
          drawFurniture(furnitureG, t);
        }

        // Desks — redraw every 2 frames
        if (frameCount % 2 === 0) {
          deskG.clear();
          drawDesk(deskG, 2.5, 3, hexToNum(ROLE_COLORS.product_manager), t);
          drawDesk(deskG, 7, 3, hexToNum(ROLE_COLORS.developer), t);
          drawDesk(deskG, 2.5, 7, hexToNum(ROLE_COLORS.quality_assurance), t);
          drawDesk(deskG, 7, 7, hexToNum(ROLE_COLORS.deployer), t);
        }

        // Agents — every frame for smooth animation
        agentG.clear();
        clearContainer(textLayer);

        const sorted = [...currentAgents].sort((a, b) => {
          const pa = agentPositions.current.get(a.id);
          const pb = agentPositions.current.get(b.id);
          return (pa?.y ?? 0) - (pb?.y ?? 0);
        });
        for (const agent of sorted) {
          const pos = agentPositions.current.get(agent.id) ?? { x: agent.position_x, y: agent.position_y };
          drawAgent(agentG, textLayer, agent, pos, t);
        }
      });

      // Cleanup
      return () => {
        canvas.removeEventListener("wheel", onWheel);
        canvas.removeEventListener("mousedown", onMouseDown);
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
      };
    })();

    return () => {
      mounted = false;
      appRef.current?.destroy(true);
      appRef.current = null;
      worldRef.current = null;
    };
    // Only recreate the app when width/height change — NOT when agents change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [width, height]);

  return (
    <div className="relative">
      <div
        ref={canvasRef}
        className="rounded-xl border border-slate-700/50 overflow-hidden"
        style={{
          width, height,
          background: "linear-gradient(180deg, #080c14 0%, #0d1420 50%, #0a0e17 100%)",
          boxShadow: "0 0 60px rgba(59, 130, 246, 0.08), 0 0 120px rgba(139, 92, 246, 0.04), inset 0 0 60px rgba(0,0,0,0.6)",
        }}
      />
      {/* Zoom controls */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1">
        <button
          onClick={() => {
            const nz = Math.min(MAX_ZOOM, zoomRef.current + 0.15);
            zoomRef.current = nz; setZoom(nz);
            if (worldRef.current) worldRef.current.scale.set(nz);
          }}
          className="w-7 h-7 rounded bg-slate-800/80 border border-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-700/80 transition text-xs font-bold flex items-center justify-center"
          title="Zoom in"
        >+</button>
        <button
          onClick={() => {
            const nz = Math.max(MIN_ZOOM, zoomRef.current - 0.15);
            zoomRef.current = nz; setZoom(nz);
            if (worldRef.current) worldRef.current.scale.set(nz);
          }}
          className="w-7 h-7 rounded bg-slate-800/80 border border-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-700/80 transition text-xs font-bold flex items-center justify-center"
          title="Zoom out"
        >-</button>
        <button
          onClick={resetView}
          className="w-7 h-7 rounded bg-slate-800/80 border border-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-700/80 transition text-[9px] font-bold flex items-center justify-center"
          title="Reset view"
        >R</button>
        <span className="text-[8px] text-slate-600 text-center mt-0.5 font-mono">
          {Math.round(zoom * 100)}%
        </span>
      </div>
      {/* Hint */}
      <div className="absolute top-2 right-3 text-[8px] text-slate-700 font-mono">
        scroll: zoom / drag: pan
      </div>
    </div>
  );
}
