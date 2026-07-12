import React, { useEffect, useRef } from "react";
import type { GantryVisualizerProps } from "../types/telemetry";

export const GantryVisualizer: React.FC<GantryVisualizerProps> = ({ telemetry, safeZ }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas dimensions based on container width
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    // Clear background
    ctx.fillStyle = "#04060b";
    ctx.fillRect(0, 0, width, height);

    // Grid details
    const drawGrid = (x: number, y: number, w: number, h: number) => {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.02)";
      ctx.lineWidth = 1;
      const step = 20;
      for (let i = x; i < x + w; i += step) {
        ctx.beginPath();
        ctx.moveTo(i, y);
        ctx.lineTo(i, y + h);
        ctx.stroke();
      }
      for (let j = y; j < y + h; j += step) {
        ctx.beginPath();
        ctx.moveTo(x, j);
        ctx.lineTo(x + w, j);
        ctx.stroke();
      }
    };

    // Bounds details
    const bounds = telemetry.workspace_bounds;
    const xRange = bounds.x.max - bounds.x.min;
    const yRange = bounds.y.max - bounds.y.min;
    const zRange = bounds.z.max - bounds.z.min;

    // View boundaries: split canvas into left (Top View X-Y) and right (Side View X-Z)
    const margin = 40;
    const halfW = width / 2;

    const view1 = {
      x: margin,
      y: margin + 20,
      w: halfW - margin * 1.5,
      h: height - margin * 2 - 20,
    };

    const view2 = {
      x: halfW + margin / 2,
      y: margin + 20,
      w: halfW - margin * 1.5,
      h: height - margin * 2 - 20,
    };

    // Draw Grids
    drawGrid(view1.x, view1.y, view1.w, view1.h);
    drawGrid(view2.x, view2.y, view2.w, view2.h);

    // Helpers to scale world coordinates to canvas coordinates
    const scaleX = (val: number, view: typeof view1) => {
      const pct = (val - bounds.x.min) / xRange;
      return view.x + pct * view.w;
    };

    const scaleY = (val: number, view: typeof view1) => {
      // Y is drawn downwards in 2D top view
      const pct = (val - bounds.y.min) / yRange;
      return view.y + (1 - pct) * view.h;
    };

    const scaleZ = (val: number, view: typeof view2) => {
      // Z vertical height: 0 (min) is at the bottom, safe_z is high up
      const pct = (val - bounds.z.min) / zRange;
      return view.y + (1 - pct) * view.h;
    };

    // Renders physical workspace borders
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 2;
    ctx.strokeRect(view1.x, view1.y, view1.w, view1.h);
    ctx.strokeRect(view2.x, view2.y, view2.w, view2.h);

    // Labels for the projection panels
    ctx.fillStyle = "#94a3b8";
    ctx.font = "bold 11px Inter, system-ui";
    ctx.fillText("HORIZONTAL TOP VIEW (X - Y)", view1.x + 4, view1.y - 8);
    ctx.fillText("VERTICAL SIDE VIEW (X - Z)", view2.x + 4, view2.y - 8);

    // Axis Labels
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.fillText("+X (Right)", view1.x + view1.w - 55, view1.y + view1.h - 8);
    ctx.fillText("+Y (Top)", view1.x + 8, view1.y + 16);
    ctx.fillText("+Z (Up)", view2.x + 8, view2.y + 16);

    // Renders coordinates under views
    const renderPos = telemetry.position;

    // Draw Source, Destination, and Target positions if sequence is running
    const drawMarkers = (view: typeof view1, isXZ: boolean) => {
      const source = telemetry.cube_position;
      const dest = telemetry.destination_position;

      // 1. Draw Source (Cube starting position)
      const srcX = scaleX(source.x, view);
      const srcYVal = isXZ ? scaleZ(source.z, view) : scaleY(source.y, view);

      ctx.strokeStyle = "rgba(167, 139, 250, 0.6)"; // purple
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(srcX, srcYVal, 8, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = "rgba(167, 139, 250, 0.15)";
      ctx.fill();

      // 2. Draw Destination Zone
      const dstX = scaleX(dest.x, view);
      const dstYVal = isXZ ? scaleZ(dest.z, view) : scaleY(dest.y, view);

      ctx.strokeStyle = "rgba(52, 211, 153, 0.6)"; // success emerald
      ctx.lineWidth = 1.5;
      ctx.strokeRect(dstX - 8, dstYVal - 8, 16, 16);
      ctx.fillStyle = "rgba(52, 211, 153, 0.1)";
      ctx.fillRect(dstX - 8, dstYVal - 8, 16, 16);

      // Label markers
      ctx.fillStyle = "rgba(255,255,255,0.3)";
      ctx.font = "9px monospace";
      ctx.fillText("SRC", srcX - 8, srcYVal - 12);
      ctx.fillText("DST", dstX - 8, dstYVal - 12);
    };

    drawMarkers(view1, false);
    drawMarkers(view2, true);

    // Draw Safe Z Line on X-Z view
    const safeZVal = safeZ !== undefined ? safeZ : (telemetry.target_position?.z ?? 300);
    const safeZCanvas = scaleZ(safeZVal > 0 ? safeZVal : 300, view2);
    ctx.strokeStyle = "rgba(251, 191, 36, 0.25)"; // amber dashed line
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(view2.x, safeZCanvas);
    ctx.lineTo(view2.x + view2.w, safeZCanvas);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(251, 191, 36, 0.4)";
    ctx.font = "9px Inter";
    ctx.fillText(`Safe Z: ${safeZVal}mm`, view2.x + view2.w - 85, safeZCanvas - 4);

    // Draw the simulated Cube (Object)
    const cubeStatus = telemetry.cube_status;
    const cubePos = telemetry.cube_current_position;
    const cubeColor = cubeStatus === "attached" ? "var(--color-primary)" : "var(--color-warning)";

    // Top view cube
    const cubeCanvasX1 = scaleX(cubePos.x, view1);
    const cubeCanvasY1 = scaleY(cubePos.y, view1);
    ctx.fillStyle = cubeColor;
    ctx.shadowColor = cubeColor;
    ctx.shadowBlur = cubeStatus === "attached" ? 8 : 0;
    ctx.fillRect(cubeCanvasX1 - 5, cubeCanvasY1 - 5, 10, 10);

    // Side view cube
    const cubeCanvasX2 = scaleX(cubePos.x, view2);
    const cubeCanvasZ2 = scaleZ(cubePos.z, view2);
    ctx.fillRect(cubeCanvasX2 - 5, cubeCanvasZ2 - 5, 10, 10);
    ctx.shadowBlur = 0; // reset glow

    // Draw Gantry Track System (Bridges & Carriage lines)
    const robX1 = scaleX(renderPos.x, view1);
    const robY1 = scaleY(renderPos.y, view1);
    const robX2 = scaleX(renderPos.x, view2);
    const robZ2 = scaleZ(renderPos.z, view2);

    // VIEW 1 (X-Y Top View): Draw X-bridge girder and Y-rail slider
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 6;
    // Y-Rails on sides
    ctx.beginPath();
    ctx.moveTo(view1.x + 6, view1.y);
    ctx.lineTo(view1.x + 6, view1.y + view1.h);
    ctx.moveTo(view1.x + view1.w - 6, view1.y);
    ctx.lineTo(view1.x + view1.w - 6, view1.y + view1.h);
    ctx.stroke();

    // X-Gantry Bridge (slides along Y)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(view1.x, robY1);
    ctx.lineTo(view1.x + view1.w, robY1);
    ctx.stroke();

    // Carriage slider on X-bridge
    ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
    ctx.beginPath();
    ctx.arc(robX1, robY1, 5, 0, Math.PI * 2);
    ctx.fill();

    // VIEW 2 (X-Z Side View): Draw X-bridge and Z-retracting spindle
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 6;
    // Overhead bridge track
    ctx.beginPath();
    ctx.moveTo(view2.x, view2.y + 15);
    ctx.lineTo(view2.x + view2.w, view2.y + 15);
    ctx.stroke();

    // Vertical Z-axis spindle line down to active carriage position
    ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(robX2, view2.y + 15);
    ctx.lineTo(robX2, robZ2);
    ctx.stroke();

    // Draw carriage block on overhead bridge
    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
    ctx.fillRect(robX2 - 8, view2.y + 11, 16, 8);

    // Draw Gripper Jaws
    const isClosed = telemetry.gripper_state === "CLOSED";
    const gripColor = isClosed ? "var(--color-primary)" : "#fff";
    ctx.strokeStyle = gripColor;
    ctx.lineWidth = 2;

    // Left jaw
    ctx.beginPath();
    ctx.moveTo(robX2 - (isClosed ? 3 : 6), robZ2);
    ctx.lineTo(robX2 - (isClosed ? 3 : 6), robZ2 + 8);
    ctx.lineTo(robX2 - 1, robZ2 + 8);
    ctx.stroke();

    // Right jaw
    ctx.beginPath();
    ctx.moveTo(robX2 + (isClosed ? 3 : 6), robZ2);
    ctx.lineTo(robX2 + (isClosed ? 3 : 6), robZ2 + 8);
    ctx.lineTo(robX2 + 1, robZ2 + 8);
    ctx.stroke();

    // Small carriage dot at Z head
    ctx.fillStyle = "var(--color-primary)";
    ctx.beginPath();
    ctx.arc(robX2, robZ2, 3, 0, Math.PI * 2);
    ctx.fill();
  }, [telemetry]);

  const p = telemetry.position;
  const v = telemetry.velocity;

  return (
    <div className="gantry-visualizer">
      <div className="gantry-status-strip" aria-label="Gantry status summary">
        <div className="gantry-status-card">
          <span>Current State</span>
          <strong>{telemetry.state}</strong>
        </div>
        <div className="gantry-status-card">
          <span>Gripper State</span>
          <strong>{telemetry.gripper_state}</strong>
        </div>
      </div>

      <div className="gantry-canvas-container">
        <canvas ref={canvasRef} className="gantry-canvas" />
      </div>

      <div className="gantry-metrics-strip" aria-label="Gantry position and velocity">
        <div>
          <span>Position</span>
          <strong>
            X:{p.x.toFixed(1)} Y:{p.y.toFixed(1)} Z:{p.z.toFixed(1)} mm
          </strong>
        </div>
        <div>
          <span>Velocity</span>
          <strong>
            vX:{v.x.toFixed(1)} vY:{v.y.toFixed(1)} vZ:{v.z.toFixed(1)} mm/s
          </strong>
        </div>
      </div>
    </div>
  );
};
export default GantryVisualizer;
