import React, { useState, useEffect, useRef } from 'react';
import type { SwarmState, SwarmVehicleState, SafetyEvent } from '../../types/swarm';

export interface SwarmTactical3DMapProps {
  swarmState: SwarmState | null;
  selectedVehicleId?: string | null;
  onSelectVehicle?: (vehicleId: string) => void;
}

export const SwarmTactical3DMap: React.FC<SwarmTactical3DMapProps> = ({
  swarmState,
  selectedVehicleId,
  onSelectVehicle,
}) => {
  const [cameraMode, setCameraMode] = useState<'ORBIT' | 'TOP_DOWN' | 'FOLLOW_LEADER'>('ORBIT');
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const selectedState = selectedVehicleId && swarmState?.vehicle_states
    ? swarmState.vehicle_states[selectedVehicleId]
    : null;

  // 3D Canvas Rendering Engine for Swarm Tactical Viewport
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dark Tactical Background Grid
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    if (!swarmState || !swarmState.vehicle_states) {
      ctx.fillStyle = '#64748b';
      ctx.font = '14px monospace';
      ctx.fillText('NO ACTIVE SWARM TELEMETRY STREAM', centerX - 120, centerY);
      return;
    }

    const vehicles = Object.values(swarmState.vehicle_states);
    if (vehicles.length === 0) return;

    // Leader position for camera centering if in follow mode
    const leaderId = swarmState.leader_vehicle_id;
    const leaderVeh = leaderId ? swarmState.vehicle_states[leaderId] : vehicles[0];

    const refX = cameraMode === 'FOLLOW_LEADER' && leaderVeh ? leaderVeh.current_position_enu[0] : 0;
    const refY = cameraMode === 'FOLLOW_LEADER' && leaderVeh ? leaderVeh.current_position_enu[1] : 0;

    const scale = 5.0 * zoomLevel; // meters to canvas pixels

    // Render Formation Mesh & Target Slot Lines
    ctx.strokeStyle = '#334155';
    ctx.setLineDash([4, 4]);
    vehicles.forEach((v) => {
      if (v.role === 'FOLLOWER' && leaderVeh) {
        const lx = centerX + (leaderVeh.current_position_enu[0] - refX) * scale;
        const ly = centerY - (leaderVeh.current_position_enu[1] - refY) * scale;
        const vx = centerX + (v.current_position_enu[0] - refX) * scale;
        const vy = centerY - (v.current_position_enu[1] - refY) * scale;

        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(vx, vy);
        ctx.stroke();
      }
    });
    ctx.setLineDash([]);

    // Render Pairwise Proximity & Safety Breach Lines
    for (let i = 0; i < vehicles.length; i++) {
      for (let j = i + 1; j < vehicles.length; j++) {
        const v1 = vehicles[i];
        const v2 = vehicles[j];

        const dx = v1.current_position_enu[0] - v2.current_position_enu[0];
        const dy = v1.current_position_enu[1] - v2.current_position_enu[1];
        const dz = v1.current_position_enu[2] - v2.current_position_enu[2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < 8.0) {
          const x1 = centerX + (v1.current_position_enu[0] - refX) * scale;
          const y1 = centerY - (v1.current_position_enu[1] - refY) * scale;
          const x2 = centerX + (v2.current_position_enu[0] - refX) * scale;
          const y2 = centerY - (v2.current_position_enu[1] - refY) * scale;

          ctx.strokeStyle = dist < 5.0 ? '#ef4444' : '#f59e0b';
          ctx.lineWidth = dist < 5.0 ? 3 : 1.5;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
    }

    // Render Individual Vehicle Nodes
    vehicles.forEach((v) => {
      const px = centerX + (v.current_position_enu[0] - refX) * scale;
      const py = centerY - (v.current_position_enu[1] - refY) * scale;
      const isLeader = v.role === 'LEADER';
      const isSelected = v.vehicle_id === selectedVehicleId;

      ctx.save();
      ctx.translate(px, py);

      // Selection Halo
      if (isSelected) {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(0, 0, 18, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Vehicle Icon (Circle with Direction Pointer)
      ctx.fillStyle = isLeader ? '#38bdf8' : v.autopilot_type === 'PX4' ? '#a855f7' : '#22c55e';
      ctx.beginPath();
      ctx.arc(0, 0, isLeader ? 10 : 8, 0, Math.PI * 2);
      ctx.fill();

      // Heading Vector Line
      const headingRad = (v.current_heading_deg * Math.PI) / 180;
      const headX = Math.sin(headingRad) * 16;
      const headY = -Math.cos(headingRad) * 16;

      ctx.strokeStyle = '#f8fafc';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(headX, headY);
      ctx.stroke();

      ctx.restore();

      // Label Overlay
      ctx.fillStyle = '#f8fafc';
      ctx.font = '10px monospace';
      ctx.fillText(`${v.vehicle_id} (${v.role[0]})`, px + 12, py + 4);
    });

    // Viewport HUD Legend
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px sans-serif';
    ctx.fillText(`SWARM: ${swarmState.swarm_id} | HEALTH: ${swarmState.health}`, 12, 20);
    ctx.fillText(`CAMERA: ${cameraMode} | ZOOM: ${zoomLevel.toFixed(1)}x`, 12, 36);
  }, [swarmState, cameraMode, zoomLevel, selectedVehicleId]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '15px' }}>
      {/* 3D Map Viewport Canvas */}
      <div style={{ background: '#020617', padding: '12px', borderRadius: '8px', border: '1px solid #334155' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h4 style={{ margin: 0, color: '#38bdf8' }}>3D Tactical Swarm Viewport</h4>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setCameraMode('ORBIT')}
              style={{ background: cameraMode === 'ORBIT' ? '#0284c7' : '#1e293b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
            >
              ORBIT
            </button>
            <button
              onClick={() => setCameraMode('TOP_DOWN')}
              style={{ background: cameraMode === 'TOP_DOWN' ? '#0284c7' : '#1e293b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
            >
              TOP-DOWN
            </button>
            <button
              onClick={() => setCameraMode('FOLLOW_LEADER')}
              style={{ background: cameraMode === 'FOLLOW_LEADER' ? '#0284c7' : '#1e293b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
            >
              FOLLOW LEADER
            </button>
            <button
              onClick={() => setZoomLevel((z) => Math.min(3.0, z + 0.2))}
              style={{ background: '#1e293b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
            >
              +
            </button>
            <button
              onClick={() => setZoomLevel((z) => Math.max(0.4, z - 0.2))}
              style={{ background: '#1e293b', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
            >
              -
            </button>
          </div>
        </div>
        <canvas
          ref={canvasRef}
          width={580}
          height={320}
          onClick={(e) => {
            if (!swarmState?.vehicle_states) return;
            const canvas = canvasRef.current;
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const scale = 5.0 * zoomLevel;

            // Find closest vehicle to click
            let closestVid: string | null = null;
            let minDist = 30.0; // Click radius tolerance in pixels

            Object.values(swarmState.vehicle_states).forEach((v) => {
              const px = centerX + v.current_position_enu[0] * scale;
              const py = centerY - v.current_position_enu[1] * scale;
              const d = Math.sqrt((clickX - px) ** 2 + (clickY - py) ** 2);
              if (d < minDist) {
                minDist = d;
                closestVid = v.vehicle_id;
              }
            });

            if (closestVid && onSelectVehicle) {
              onSelectVehicle(closestVid);
            }
          }}
          style={{ width: '100%', background: '#090d16', borderRadius: '4px', cursor: 'pointer' }}
        />
      </div>

      {/* Vehicle Detailed Telemetry Inspector Panel */}
      <div style={{ background: '#1e293b', padding: '12px', borderRadius: '8px', fontSize: '12px', border: '1px solid #334155' }}>
        <h4 style={{ margin: '0 0 10px 0', color: '#eab308' }}>Vehicle Telemetry Inspector</h4>
        {selectedState ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>ID: <strong style={{ color: '#38bdf8' }}>{selectedState.vehicle_id}</strong></div>
            <div>Autopilot: <strong>{selectedState.autopilot_type}</strong></div>
            <div>Role: <strong>{selectedState.role}</strong> (Slot {selectedState.slot_index})</div>
            <hr style={{ borderColor: '#334155', margin: '4px 0' }} />
            <div>ENU Pos: [{selectedState.current_position_enu.map((n) => n.toFixed(1)).join(', ')}] m</div>
            <div>Heading: {selectedState.current_heading_deg.toFixed(1)}°</div>
            <div>Position Error: <span style={{ color: selectedState.position_error_m > 4.0 ? '#ef4444' : '#22c55e' }}>{selectedState.position_error_m.toFixed(2)} m</span></div>
            <div>Health: <strong style={{ color: selectedState.health_status === 'HEALTHY' ? '#22c55e' : '#f59e0b' }}>{selectedState.health_status}</strong></div>
          </div>
        ) : (
          <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>
            Click any vehicle in the 3D map viewport to inspect live telemetry.
          </div>
        )}
      </div>
    </div>
  );
};
