"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Application, Container, Graphics, Text, TextStyle, FillGradient, BlurFilter } from "pixi.js";
import type { AgentState } from "@/lib/types";
import { ROLE_COLORS, ROLE_EMOJI, DESK_POSITIONS, MEETING_POINT } from "@/lib/types";

interface Props {
  agents: AgentState[];
  width?: number;
  height?: number;
}

// Isometric projection helpers
const ISO_ANGLE = Math.PI / 6; // 30 degrees
const TILE_W = 64;
const TILE_H = 32;

function toIso(x: number, y: number): [number, number] {
  return [
    (x - y) * (TILE_W / 2),
    (x + y) * (TILE_H / 2),
  ];
}

function hexToNum(hex: string): number {
  return parseInt(hex.replace("#", ""), 16);
}

function drawIsometricFloor(g: Graphics, cols: number, rows: number) {
  for (let x = 0; x < cols; x++) {
    for (let y = 0; y < rows; y++) {
      const [ix, iy] = toIso(x, y);
      const isDark = (x + y) % 2 === 0;
      const color = isDark ? 0x1e2a3a : 0x243448;
      g.poly([
        { x: ix, y: iy },
        { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H },
        { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.fill({ color, alpha: 0.9 });
      // Subtle grid line
      g.poly([
        { x: ix, y: iy },
        { x: ix + TILE_W / 2, y: iy + TILE_H / 2 },
        { x: ix, y: iy + TILE_H },
        { x: ix - TILE_W / 2, y: iy + TILE_H / 2 },
      ]);
      g.stroke({ color: 0x2a3f5f, width: 0.5, alpha: 0.3 });
    }
  }
}

function drawWall(g: Graphics, cols: number) {
  // Back wall
  const [lx, ly] = toIso(0, 0);
  const [rx, ry] = toIso(cols, 0);
  const wallHeight = 80;
  
  // Wall face
  g.poly([
    { x: lx, y: ly - wallHeight },
    { x: rx, y: ry - wallHeight },
    { x: rx, y: ry },
    { x: lx, y: ly },
  ]);
  g.fill({ color: 0x2a3a50, alpha: 0.95 });
  g.stroke({ color: 0x3a5070, width: 1 });

  // Right wall
  const [brx, bry] = toIso(cols, cols);
  g.poly([
    { x: rx, y: ry - wallHeight },
    { x: brx, y: bry - wallHeight },
    { x: brx, y: bry },
    { x: rx, y: ry },
  ]);
  g.fill({ color: 0x1e2d42, alpha: 0.95 });
  g.stroke({ color: 0x2a4060, width: 1 });

  // Window on back wall
  const wx = (lx + rx) / 2;
  const wy = (ly + ry) / 2 - wallHeight + 15;
  g.roundRect(wx - 40, wy, 80, 40, 3);
  g.fill({ color: 0x1e40af, alpha: 0.7 });
  g.stroke({ color: 0x64748b, width: 2 });
  
  // Window glow
  g.roundRect(wx - 36, wy + 4, 72, 32, 2);
  g.fill({ color: 0x3b82f6, alpha: 0.4 });
  
  // Window cross
  g.moveTo(wx, wy);
  g.lineTo(wx, wy + 40);
  g.stroke({ color: 0x64748b, width: 1.5 });
  g.moveTo(wx - 40, wy + 20);
  g.lineTo(wx + 40, wy + 20);
  g.stroke({ color: 0x64748b, width: 1.5 });
}

function drawDesk(container: Container, x: number, y: number, color: number, label: string) {
  const [ix, iy] = toIso(x / 60, y / 60);
  const g = new Graphics();
  
  // Desk top (isometric diamond)
  const dw = 48, dh = 24;
  g.poly([
    { x: ix, y: iy - 20 },
    { x: ix + dw / 2, y: iy - 20 + dh / 2 },
    { x: ix, y: iy - 20 + dh },
    { x: ix - dw / 2, y: iy - 20 + dh / 2 },
  ]);
  g.fill({ color: 0xa67c00, alpha: 0.9 });
  g.stroke({ color: 0x8b6914, width: 1.5 });
  
  // Desk front face
  g.poly([
    { x: ix - dw / 2, y: iy - 20 + dh / 2 },
    { x: ix, y: iy - 20 + dh },
    { x: ix, y: iy - 8 },
    { x: ix - dw / 2, y: iy - 8 - dh / 2 + dh / 2 },
  ]);
  g.fill({ color: 0x8b6914, alpha: 0.8 });
  
  // Desk right face
  g.poly([
    { x: ix, y: iy - 20 + dh },
    { x: ix + dw / 2, y: iy - 20 + dh / 2 },
    { x: ix + dw / 2, y: iy - 8 + dh / 2 - dh / 2 },
    { x: ix, y: iy - 8 },
  ]);
  g.fill({ color: 0x6b4f12, alpha: 0.8 });
  
  // Monitor
  g.roundRect(ix - 8, iy - 38, 16, 12, 1);
  g.fill({ color: 0x1e293b });
  g.stroke({ color: 0x475569, width: 1 });
  // Screen glow
  g.roundRect(ix - 6, iy - 36, 12, 8, 1);
  g.fill({ color, alpha: 0.6 });
  // Monitor stand
  g.rect(ix - 2, iy - 26, 4, 4);
  g.fill({ color: 0x475569 });

  container.addChild(g);
  
  // Label
  const text = new Text({
    text: label,
    style: new TextStyle({
      fontFamily: "monospace",
      fontSize: 7,
      fill: 0x8892b0,
      align: "center",
    }),
  });
  text.anchor.set(0.5, 0);
  text.x = ix;
  text.y = iy + 4;
  container.addChild(text);
}

function drawAgent(
  container: Container,
  agent: AgentState,
  interpolatedPos: { x: number; y: number }
) {
  const [ix, iy] = toIso(interpolatedPos.x / 60, interpolatedPos.y / 60);
  const color = hexToNum(ROLE_COLORS[agent.role] ?? ROLE_COLORS.default);
  const emoji = ROLE_EMOJI[agent.role] ?? "🤖";
  const isWorking = agent.current_action === "working";
  const isWalking = agent.current_action === "walking";
  const bounce = isWalking ? Math.sin(Date.now() / 150) * 3 : 0;
  const pulse = isWorking ? Math.sin(Date.now() / 300) * 2 : 0;

  const g = new Graphics();
  
  // Shadow
  g.ellipse(ix, iy + 2, 12, 5);
  g.fill({ color: 0x000000, alpha: 0.3 });
  
  // Body (isometric cube-like)
  const by = iy - 12 + bounce;
  
  // Torso front
  g.roundRect(ix - 8, by - 10, 16, 14, 2);
  g.fill({ color, alpha: 0.9 });
  g.stroke({ color: 0x000000, width: 0.5, alpha: 0.2 });
  
  // Head
  g.circle(ix, by - 16, 8);
  g.fill({ color: 0xfcd5b0 });
  g.stroke({ color: 0xe8b898, width: 1 });
  
  // Eyes
  g.circle(ix - 3, by - 17, 1.5);
  g.fill({ color: 0x333333 });
  g.circle(ix + 3, by - 17, 1.5);
  g.fill({ color: 0x333333 });
  
  // Mouth (smile if working)
  if (isWorking) {
    g.arc(ix, by - 13, 3, 0, Math.PI, false);
    g.stroke({ color: 0xc97755, width: 1 });
  } else {
    g.rect(ix - 2, by - 13, 4, 1.5);
    g.fill({ color: 0xc97755 });
  }
  
  // Hair/hat with role color
  g.arc(ix, by - 18, 8, Math.PI, 0, false);
  g.fill({ color, alpha: 0.8 });
  
  // Legs
  const legOffset = isWalking ? Math.sin(Date.now() / 200) * 3 : 0;
  g.roundRect(ix - 5, by + 2, 4, 8, 1);
  g.fill({ color: 0x445566 });
  g.roundRect(ix + 1, by + 2 + legOffset, 4, 8, 1);
  g.fill({ color: 0x445566 });
  
  // Arms
  if (isWorking) {
    // Arms forward (typing)
    g.roundRect(ix - 12, by - 6, 5, 3, 1);
    g.fill({ color: 0xfcd5b0 });
    g.roundRect(ix + 7, by - 6, 5, 3, 1);
    g.fill({ color: 0xfcd5b0 });
  }
  
  // Work glow
  if (isWorking) {
    g.circle(ix, by - 10, 20 + pulse);
    g.fill({ color, alpha: 0.05 });
  }

  container.addChild(g);
  
  // Name label
  const name = new Text({
    text: agent.name,
    style: new TextStyle({
      fontFamily: "'Press Start 2P', monospace",
      fontSize: 7,
      fill: 0xffffff,
      stroke: { color: 0x000000, width: 2 },
      align: "center",
    }),
  });
  name.anchor.set(0.5, 0);
  name.x = ix;
  name.y = iy + 14;
  container.addChild(name);
  
  // Action bubble
  if (agent.current_action !== "idle") {
    const bubbleG = new Graphics();
    const bx = ix + 14;
    const bby = by - 30;
    bubbleG.roundRect(bx - 2, bby, 42, 12, 4);
    bubbleG.fill({ color: 0xffffff, alpha: 0.9 });
    bubbleG.stroke({ color, width: 1 });
    // Bubble tail
    bubbleG.poly([
      { x: bx + 4, y: bby + 12 },
      { x: bx, y: bby + 18 },
      { x: bx + 10, y: bby + 12 },
    ]);
    bubbleG.fill({ color: 0xffffff, alpha: 0.9 });
    container.addChild(bubbleG);
    
    const actionText = new Text({
      text: `⚡ ${agent.current_action}`,
      style: new TextStyle({
        fontFamily: "monospace",
        fontSize: 7,
        fill: hexToNum(ROLE_COLORS[agent.role] ?? "#e94560"),
      }),
    });
    actionText.x = bx + 2;
    actionText.y = bby + 2;
    container.addChild(actionText);
  }
  
  // Emoji badge
  const emojiBadge = new Text({
    text: emoji,
    style: new TextStyle({ fontSize: 14 }),
  });
  emojiBadge.anchor.set(0.5, 0.5);
  emojiBadge.x = ix;
  emojiBadge.y = by - 32;
  container.addChild(emojiBadge);
}

function drawFurniture(container: Container, gridCols: number) {
  const g = new Graphics();
  
  // Coffee machine area
  const [cx, cy] = toIso(7, 1);
  g.roundRect(cx - 8, cy - 20, 16, 20, 2);
  g.fill({ color: 0x8b4513, alpha: 0.8 });
  g.stroke({ color: 0x654321, width: 1 });
  // Steam
  for (let i = 0; i < 3; i++) {
    const sx = cx - 4 + i * 4;
    const sy = cy - 24 - Math.sin(Date.now() / 400 + i) * 3;
    g.circle(sx, sy, 2);
    g.fill({ color: 0xffffff, alpha: 0.2 });
  }
  container.addChild(g);
  
  const coffeeText = new Text({
    text: "☕",
    style: new TextStyle({ fontSize: 16 }),
  });
  coffeeText.anchor.set(0.5, 0.5);
  coffeeText.x = cx;
  coffeeText.y = cy - 28;
  container.addChild(coffeeText);
  
  // Server rack
  const sg = new Graphics();
  const [srx, sry] = toIso(7.5, 7);
  sg.roundRect(srx - 10, sry - 30, 20, 35, 2);
  sg.fill({ color: 0x0f172a });
  sg.stroke({ color: 0x334155, width: 1 });
  // LEDs
  for (let i = 0; i < 5; i++) {
    const ledOn = Math.random() > 0.3;
    sg.circle(srx - 4, sry - 24 + i * 6, 2);
    sg.fill({ color: ledOn ? 0x4ade80 : 0x334155 });
  }
  container.addChild(sg);
  
  // Plants
  for (const [px, py] of [[0.5, 7.5], [7.5, 0.5]] as [number, number][]) {
    const [plx, ply] = toIso(px, py);
    const plantText = new Text({
      text: "🌿",
      style: new TextStyle({ fontSize: 18 }),
    });
    plantText.anchor.set(0.5, 0.5);
    plantText.x = plx;
    plantText.y = ply - 8;
    container.addChild(plantText);
  }
  
  // Whiteboard
  const wg = new Graphics();
  const [wx, wy] = toIso(1, 0.5);
  wg.roundRect(wx - 30, wy - 35, 60, 35, 2);
  wg.fill({ color: 0xf0f0f0 });
  wg.stroke({ color: 0x94a3b8, width: 2 });
  // Board content lines
  for (let i = 0; i < 4; i++) {
    const lw = 20 + Math.random() * 25;
    const colors = [0xe94560, 0x60a5fa, 0x4ade80, 0xfbbf24];
    wg.roundRect(wx - 24, wy - 30 + i * 8, lw, 3, 1);
    wg.fill({ color: colors[i] });
  }
  container.addChild(wg);
  
  // Meeting table (center)
  const mg = new Graphics();
  const [mx, my] = toIso(4, 4);
  mg.ellipse(mx, my - 8, 20, 10);
  mg.fill({ color: 0x8b6914, alpha: 0.9 });
  mg.stroke({ color: 0x6b4f12, width: 1.5 });
  // Table highlight
  mg.ellipse(mx, my - 10, 14, 7);
  mg.fill({ color: 0xa67c00, alpha: 0.3 });
  container.addChild(mg);
}

export default function IsometricOffice({ agents, width = 700, height = 600 }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const agentPositions = useRef<Map<string, { x: number; y: number }>>(new Map());

  // Interpolate agent positions
  const updatePositions = useCallback(() => {
    for (const agent of agents) {
      const current = agentPositions.current.get(agent.id) ?? {
        x: agent.position_x,
        y: agent.position_y,
      };
      const tx = agent.target_x || agent.position_x;
      const ty = agent.target_y || agent.position_y;
      agentPositions.current.set(agent.id, {
        x: current.x + (tx - current.x) * 0.06,
        y: current.y + (ty - current.y) * 0.06,
      });
    }
  }, [agents]);

  useEffect(() => {
    if (!canvasRef.current) return;
    
    const app = new Application();
    let mounted = true;
    
    (async () => {
      await app.init({
        width,
        height,
        background: 0x0d1117,
        antialias: true,
        resolution: window.devicePixelRatio || 1,
        autoDensity: true,
      });
      
      if (!mounted || !canvasRef.current) return;
      canvasRef.current.innerHTML = "";
      canvasRef.current.appendChild(app.canvas);
      appRef.current = app;
      
      // Main container (centered)
      const world = new Container();
      world.x = width / 2;
      world.y = 100;
      app.stage.addChild(world);
      
      const GRID = 8;
      
      // Ambient glow
      const ambientG = new Graphics();
      ambientG.ellipse(0, GRID * TILE_H / 2, 200, 100);
      ambientG.fill({ color: 0x3b82f6, alpha: 0.03 });
      world.addChild(ambientG);
      
      // Floor
      const floor = new Graphics();
      drawIsometricFloor(floor, GRID, GRID);
      world.addChild(floor);
      
      // Walls
      const walls = new Graphics();
      drawWall(walls, GRID);
      world.addChild(walls);
      
      // Static furniture
      const furnitureLayer = new Container();
      drawFurniture(furnitureLayer, GRID);
      world.addChild(furnitureLayer);
      
      // Desks
      const deskLayer = new Container();
      drawDesk(deskLayer, 120, 180, hexToNum(ROLE_COLORS.product_manager), "PM");
      drawDesk(deskLayer, 380, 180, hexToNum(ROLE_COLORS.developer), "DEV");
      drawDesk(deskLayer, 120, 380, hexToNum(ROLE_COLORS.quality_assurance), "QA");
      drawDesk(deskLayer, 380, 380, hexToNum(ROLE_COLORS.deployer), "OPS");
      world.addChild(deskLayer);
      
      // Dynamic layer (agents)
      const agentLayer = new Container();
      world.addChild(agentLayer);
      
      // Title
      const title = new Text({
        text: "🏢 AGENTLOOP HQ",
        style: new TextStyle({
          fontFamily: "'Press Start 2P', monospace",
          fontSize: 9,
          fill: 0x4a5568,
          letterSpacing: 3,
        }),
      });
      title.anchor.set(0.5, 0);
      title.x = 0;
      title.y = GRID * TILE_H + 10;
      world.addChild(title);
      
      // Render loop
      app.ticker.add(() => {
        updatePositions();
        
        // Clear and redraw agents
        agentLayer.removeChildren();
        
        // Sort agents by Y for correct depth
        const sorted = [...agents].sort((a, b) => {
          const pa = agentPositions.current.get(a.id);
          const pb = agentPositions.current.get(b.id);
          return (pa?.y ?? 0) - (pb?.y ?? 0);
        });
        
        for (const agent of sorted) {
          const pos = agentPositions.current.get(agent.id) ?? {
            x: agent.position_x,
            y: agent.position_y,
          };
          drawAgent(agentLayer, agent, pos);
        }
      });
    })();
    
    return () => {
      mounted = false;
      appRef.current?.destroy(true);
      appRef.current = null;
    };
  }, [width, height, agents, updatePositions]);

  return (
    <div
      ref={canvasRef}
      className="rounded-xl border-2 border-slate-700 overflow-hidden"
      style={{
        width,
        height,
        background: "linear-gradient(180deg, #0d1117 0%, #161b22 100%)",
        boxShadow: "0 0 40px rgba(59, 130, 246, 0.1), inset 0 0 60px rgba(0,0,0,0.5)",
      }}
    />
  );
}
