import React, { useState, useEffect, useRef } from 'react';

export interface VehicleStateVector {
  timestamp_utc: string;
  sim_time_seconds: number;
  vehicle_id: string;
  flight_mode: string;
  armed: boolean;
  position: { latitude: number; longitude: number; altitude_msl: number; altitude_relative: number };
  velocity: { vx: number; vy: number; vz: number; ground_speed: number };
  attitude: { roll_deg: number; pitch_deg: number; yaw_deg: number };
  battery: { voltage_v: number; remaining_percent: number };
  gps: { fix_type: number; satellites_visible: number; hdop: number };
}

export interface CapabilityStatus {
  available: boolean;
  version?: string | null;
  reason?: string | null;
}

export interface CapabilityDiagnostic {
  gazebo: CapabilityStatus;
  ardupilot_sitl: CapabilityStatus;
  mavlink: CapabilityStatus;
}

export const SimulationWorkstation: React.FC = () => {
  const [capabilities, setCapabilities] = useState<CapabilityDiagnostic | null>(null);
  const [selectedEngine, setSelectedEngine] = useState<'MOCK' | 'GAZEBO'>('MOCK');
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>('CREATED');
  const [telemetry, setTelemetry] = useState<VehicleStateVector | null>(null);
  const [replaySamples, setReplaySamples] = useState<VehicleStateVector[]>([]);
  const [replayIndex, setReplayIndex] = useState<number>(0);
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Fetch capabilities diagnostic on mount
  useEffect(() => {
    fetch('/api/v1/simulation/capabilities')
      .then((res) => res.json())
      .then((data: CapabilityDiagnostic) => setCapabilities(data))
      .catch(() => {
        setCapabilities({
          gazebo: { available: false, reason: 'Endpoint unavailable' },
          ardupilot_sitl: { available: false, reason: 'Endpoint unavailable' },
          mavlink: { available: true, version: 'pymavlink' },
        });
      });
  }, []);

  // 2D Tactical 3D Viewport Simulation Renderer Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background Grid
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    const currentState = isReplaying && replaySamples.length > 0 ? replaySamples[replayIndex] : telemetry;

    if (currentState) {
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const heading = (currentState.attitude.yaw_deg * Math.PI) / 180;

      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(heading);

      // Render Quad-X Vehicle Body
      ctx.strokeStyle = currentState.armed ? '#22c55e' : '#eab308';
      ctx.lineWidth = 3;
      // Cross Arms
      ctx.beginPath(); ctx.moveTo(-25, -25); ctx.lineTo(25, 25); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(25, -25); ctx.lineTo(-25, 25); ctx.stroke();
      // Motor Rotors
      ctx.fillStyle = '#38bdf8';
      [[-25, -25], [25, -25], [25, 25], [-25, 25]].forEach(([mx, my]) => {
        ctx.beginPath(); ctx.arc(mx, my, 8, 0, Math.PI * 2); ctx.fill();
      });

      // Front Heading Indicator Arrow
      ctx.fillStyle = '#f43f5e';
      ctx.beginPath(); ctx.moveTo(0, -28); ctx.lineTo(-6, -18); ctx.lineTo(6, -18); ctx.closePath(); ctx.fill();

      ctx.restore();

      // Render Overlay Telemetry Text
      ctx.fillStyle = '#f8fafc';
      ctx.font = '12px monospace';
      ctx.fillText(`ALT: ${currentState.position.altitude_relative.toFixed(1)}m`, 15, 25);
      ctx.fillText(`SPD: ${currentState.velocity.ground_speed.toFixed(1)}m/s`, 15, 45);
      ctx.fillText(`YAW: ${currentState.attitude.yaw_deg.toFixed(1)}°`, 15, 65);
    }
  }, [telemetry, isReplaying, replayIndex, replaySamples]);

  const handleCreateAndStartScenario = async () => {
    try {
      // 1. Create Scenario
      const scenRes = await fetch('/api/v1/simulation/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'AeroGuard Quad-X Evaluation',
          simulator_type: selectedEngine,
          autopilot_type: 'ARDUPILOT',
          world_name: 'default_grassland',
        }),
      });
      const scenData = await scenRes.json();
      setScenarioId(scenData.id);

      // 2. Create Run
      const runRes = await fetch('/api/v1/simulation/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: scenData.id }),
      });
      const runData = await runRes.json();
      setRunId(runData.id);
      setRunStatus('CREATED');

      // 3. Start Run
      const startRes = await fetch(`/api/v1/simulation/runs/${runData.id}/start`, { method: 'POST' });
      const startData = await startRes.json();
      setRunStatus(startData.status);

      // 4. Open WebSocket Telemetry Stream
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/simulation/runs/${runData.id}/telemetry`;
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'VEHICLE_STATE' && payload.vehicle_state) {
            setTelemetry(payload.vehicle_state);
          }
        } catch {
          // Ignore parse errors
        }
      };
    } catch (err) {
      console.error('Failed to start simulation:', err);
    }
  };

  const handleStopSimulation = async () => {
    if (!runId) return;
    await fetch(`/api/v1/simulation/runs/${runId}/stop`, { method: 'POST' });
    setRunStatus('STOPPED');

    // Fetch Replay Samples
    const replayRes = await fetch(`/api/v1/simulation/runs/${runId}/replay`);
    const replayData = await replayRes.json();
    if (replayData.samples) {
      setReplaySamples(replayData.samples);
    }
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', color: '#f8fafc', fontFamily: 'sans-serif' }}>
      <h2>AeroGuard UAV Simulation Workstation v0.1</h2>
      
      {/* Capability Diagnostics Bar */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', background: '#1e293b', padding: '12px', borderRadius: '6px' }}>
        <div>Gazebo: <strong>{capabilities?.gazebo.available ? 'AVAILABLE' : 'NOT AVAILABLE'}</strong></div>
        <div>ArduPilot SITL: <strong>{capabilities?.ardupilot_sitl.available ? 'AVAILABLE' : 'NOT AVAILABLE'}</strong></div>
        <div>MAVLink Transport: <strong>{capabilities?.mavlink.available ? 'AVAILABLE' : 'NOT AVAILABLE'}</strong></div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* 3D Simulation Viewport Canvas */}
        <div style={{ background: '#020617', padding: '15px', borderRadius: '8px', border: '1px solid #334155' }}>
          <h3>3D Simulation Viewport (Quad-X Digital Twin)</h3>
          <canvas ref={canvasRef} width={600} height={350} style={{ width: '100%', background: '#090d16', borderRadius: '4px' }} />
        </div>

        {/* Telemetry Instruments & Controls */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Vehicle Telemetry & Diagnostics</h3>
          {/* Subsystem Status Indicators */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '15px', fontSize: '12px' }}>
            <div>Simulation: <strong style={{ color: runStatus === 'RUNNING' ? '#22c55e' : runStatus === 'FAILED' ? '#f43f5e' : '#eab308' }}>{runStatus}</strong></div>
            <div>Gazebo: <strong style={{ color: selectedEngine === 'GAZEBO' && runStatus === 'RUNNING' ? '#22c55e' : '#94a3b8' }}>{selectedEngine === 'GAZEBO' ? (capabilities?.gazebo.available ? (runStatus === 'RUNNING' ? 'RUNNING' : 'DISCONNECTED') : 'NOT AVAILABLE') : 'STANDBY'}</strong></div>
            <div>ArduPilot: <strong style={{ color: runStatus === 'RUNNING' ? '#22c55e' : '#94a3b8' }}>{capabilities?.ardupilot_sitl.available ? (runStatus === 'RUNNING' ? 'CONNECTED' : 'DISCONNECTED') : 'NOT AVAILABLE'}</strong></div>
            <div>MAVLink Stream: <strong style={{ color: telemetry ? '#22c55e' : '#f43f5e' }}>{telemetry ? 'ACTIVE' : 'DISCONNECTED'}</strong></div>
          </div>

          <div>Mode: <strong>{telemetry?.flight_mode || 'OFFLINE'}</strong></div>
          <div>Armed: <strong>{telemetry?.armed ? 'ARMED' : 'DISARMED'}</strong></div>
          <div>Latitude: {telemetry?.position.latitude || '0.000000'}</div>
          <div>Longitude: {telemetry?.position.longitude || '0.000000'}</div>
          <div>Altitude Rel: {telemetry?.position.altitude_relative || 0} m</div>
          <div>Ground Speed: {telemetry?.velocity.ground_speed || 0} m/s</div>
          <div>Battery: {telemetry?.battery.remaining_percent || 100}% ({telemetry?.battery.voltage_v || 14.8}V)</div>

          {/* Engine Selection & Control Bar */}
          <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label>
              Engine Adapter:
              <select value={selectedEngine} onChange={(e) => setSelectedEngine(e.target.value as 'MOCK' | 'GAZEBO')}>
                <option value="MOCK">Mock Simulation Engine (In-Memory)</option>
                <option value="GAZEBO">Gazebo Harmonic Physics Engine</option>
              </select>
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={handleCreateAndStartScenario} disabled={runStatus === 'RUNNING'}>Start Simulation</button>
              <button onClick={handleStopSimulation} disabled={runStatus !== 'RUNNING'}>Stop Simulation</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
