import React, { useState, useEffect, useRef } from 'react';

export interface MissionItem {
  id?: string;
  sequence: number;
  command_type: 'TAKEOFF' | 'WAYPOINT' | 'LOITER' | 'LAND' | 'RETURN_TO_HOME';
  latitude?: number;
  longitude?: number;
  altitude_m: number;
  acceptance_radius_m: number;
  loiter_duration_s: number;
}

export interface MissionProgress {
  mission_id: string;
  mission_status: string;
  current_item_index: number;
  completed_items: number;
  total_items: number;
  progress_percentage: number;
  distance_to_target_m: number;
  mission_elapsed_time_s: number;
}

export const MissionPlannerWorkstation: React.FC = () => {
  const [missionName, setMissionName] = useState<string>('Quad-X Surveillance Flight');
  const [status, setStatus] = useState<string>('CREATED');
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [items, setItems] = useState<MissionItem[]>([
    { sequence: 1, command_type: 'TAKEOFF', altitude_m: 20.0, acceptance_radius_m: 2.0, loiter_duration_s: 0.0 },
    { sequence: 2, command_type: 'WAYPOINT', latitude: 37.7749, longitude: -122.4194, altitude_m: 25.0, acceptance_radius_m: 2.0, loiter_duration_s: 0.0 },
    { sequence: 3, command_type: 'WAYPOINT', latitude: 37.7755, longitude: -122.4180, altitude_m: 30.0, acceptance_radius_m: 2.0, loiter_duration_s: 0.0 },
    { sequence: 4, command_type: 'LOITER', latitude: 37.7755, longitude: -122.4180, altitude_m: 30.0, acceptance_radius_m: 5.0, loiter_duration_s: 30.0 },
    { sequence: 5, command_type: 'RETURN_TO_HOME', altitude_m: 25.0, acceptance_radius_m: 2.0, loiter_duration_s: 0.0 },
    { sequence: 6, command_type: 'LAND', altitude_m: 0.0, acceptance_radius_m: 1.0, loiter_duration_s: 0.0 },
  ]);

  const [progress, setProgress] = useState<MissionProgress>({
    mission_id: 'msn-demo-01',
    mission_status: 'READY',
    current_item_index: 2,
    completed_items: 1,
    total_items: 6,
    progress_percentage: 16.7,
    distance_to_target_m: 14.5,
    mission_elapsed_time_s: 18.2,
  });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Render 2D Route Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Grid Background
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    // Draw Mission Route Vectors
    if (items.length > 1) {
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      items.forEach((item, idx) => {
        const px = cx + (idx - 2) * 60;
        const py = cy - (idx % 2 === 0 ? 30 : -30);
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Render Waypoint Markers
    items.forEach((item, idx) => {
      const px = cx + (idx - 2) * 60;
      const py = cy - (idx % 2 === 0 ? 30 : -30);
      const isSelected = idx === selectedIndex;

      ctx.fillStyle = isSelected ? '#f43f5e' : '#0284c7';
      ctx.beginPath(); ctx.arc(px, py, isSelected ? 10 : 7, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ffffff'; ctx.font = '11px sans-serif'; ctx.fillText(`${item.sequence}`, px - 3, py + 4);
    });
  }, [items, selectedIndex]);

  const handleAddItem = () => {
    const nextSeq = items.length + 1;
    setItems([...items, {
      sequence: nextSeq,
      command_type: 'WAYPOINT',
      latitude: 37.7760,
      longitude: -122.4170,
      altitude_m: 25.0,
      acceptance_radius_m: 2.0,
      loiter_duration_s: 0.0,
    }]);
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', color: '#f8fafc', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>AeroGuard Mission Planner (Stage S7)</h2>
        <div style={{ background: '#1e293b', padding: '6px 12px', borderRadius: '6px' }}>
          Status: <strong style={{ color: '#38bdf8' }}>{status}</strong>
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px', marginTop: '15px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
          <span>Mission Progress: <strong>WAYPOINT {progress.current_item_index} / {progress.total_items}</strong></span>
          <span>{progress.progress_percentage}% COMPLETE | Target Dist: {progress.distance_to_target_m}m | Time: {progress.mission_elapsed_time_s}s</span>
        </div>
        <div style={{ width: '100%', height: '10px', background: '#334155', borderRadius: '5px', overflow: 'hidden' }}>
          <div style={{ width: `${progress.progress_percentage}%`, height: '100%', background: '#22c55e', transition: 'width 0.3s' }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr 1fr', gap: '15px', marginTop: '20px' }}>
        {/* Pane 1: Mission Item Sequence */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3>Mission Items</h3>
            <button onClick={handleAddItem} style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>+ Add</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {items.map((item, idx) => (
              <div key={idx} onClick={() => setSelectedIndex(idx)} style={{ padding: '8px 12px', background: idx === selectedIndex ? '#334155' : '#0f172a', borderRadius: '6px', cursor: 'pointer', borderLeft: idx === selectedIndex ? '4px solid #38bdf8' : 'none' }}>
                <strong>{item.sequence}. {item.command_type}</strong> ({item.altitude_m}m)
              </div>
            ))}
          </div>
        </div>

        {/* Pane 2: Route Map / Canvas */}
        <div style={{ background: '#020617', padding: '15px', borderRadius: '8px', border: '1px solid #334155' }}>
          <h3>Interactive Route Map</h3>
          <canvas ref={canvasRef} width={500} height={260} style={{ width: '100%', background: '#090d16', borderRadius: '4px', marginTop: '10px' }} />
        </div>

        {/* Pane 3: Item Inspector */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Item Inspector</h3>
          {items[selectedIndex] && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
              <label>Command Type:
                <select value={items[selectedIndex].command_type} onChange={(e) => {
                  const updated = [...items]; updated[selectedIndex].command_type = e.target.value as any; setItems(updated);
                }} style={{ width: '100%' }}>
                  <option value="TAKEOFF">TAKEOFF</option>
                  <option value="WAYPOINT">WAYPOINT</option>
                  <option value="LOITER">LOITER</option>
                  <option value="RETURN_TO_HOME">RETURN_TO_HOME</option>
                  <option value="LAND">LAND</option>
                </select>
              </label>
              <label>Altitude (m):
                <input type="number" value={items[selectedIndex].altitude_m} onChange={(e) => {
                  const updated = [...items]; updated[selectedIndex].altitude_m = Number(e.target.value); setItems(updated);
                }} style={{ width: '100%' }} />
              </label>
              <label>Acceptance Radius (m):
                <input type="number" value={items[selectedIndex].acceptance_radius_m} onChange={(e) => {
                  const updated = [...items]; updated[selectedIndex].acceptance_radius_m = Number(e.target.value); setItems(updated);
                }} style={{ width: '100%' }} />
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Control Action Bar */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '20px', background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
        <button onClick={() => setStatus('VALIDATED')} style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>VALIDATE</button>
        <button onClick={() => setStatus('UPLOADED')} style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>UPLOAD</button>
        <button onClick={() => setStatus('RUNNING')} style={{ background: '#22c55e', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>START</button>
        <button onClick={() => setStatus('PAUSED')} style={{ background: '#f59e0b', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>HOLD / PAUSE</button>
        <button onClick={() => setStatus('ABORTED')} style={{ background: '#f43f5e', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>ABORT</button>
      </div>
    </div>
  );
};
