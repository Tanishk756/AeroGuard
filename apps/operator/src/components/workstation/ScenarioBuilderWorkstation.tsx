import React, { useState, useEffect, useRef } from 'react';

export interface ScenarioValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface WorldObject {
  id?: string;
  object_type: string;
  position: { x: number; y: number; z: number };
  orientation: { roll: number; pitch: number; yaw: number };
  scale: { x: number; y: number; z: number };
  collision_enabled: boolean;
  visual_enabled: boolean;
}

export const ScenarioBuilderWorkstation: React.FC = () => {
  const [scenarioName, setScenarioName] = useState<string>('Evaluation Flight Alpha');
  const [selectedVehicle, setSelectedVehicle] = useState<string>('veh-default-q450');
  const [selectedWorldType, setSelectedWorldType] = useState<string>('FLAT_GROUND');
  const [windSpeed, setWindSpeed] = useState<number>(5.0);
  const [windDirection, setWindDirection] = useState<number>(90.0);
  const [turbulence, setTurbulence] = useState<string>('LOW');
  const [simRate, setSimRate] = useState<number>(250.0);
  const [stepSize, setStepSize] = useState<number>(0.004);
  const [spawnX, setSpawnX] = useState<number>(0.0);
  const [spawnY, setSpawnY] = useState<number>(0.0);
  const [spawnZ, setSpawnZ] = useState<number>(0.2);
  const [spawnHeading, setSpawnHeading] = useState<number>(0.0);
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [worldObjects, setWorldObjects] = useState<WorldObject[]>([
    { object_type: 'LANDING_PAD', position: { x: 0.0, y: 0.0, z: 0.01 }, orientation: { roll: 0, pitch: 0, yaw: 0 }, scale: { x: 2.0, y: 2.0, z: 0.02 }, collision_enabled: true, visual_enabled: true },
    { object_type: 'STATIC_BOX', position: { x: 5.0, y: 3.0, z: 1.5 }, orientation: { roll: 0, pitch: 0, yaw: 0 }, scale: { x: 2.0, y: 2.0, z: 3.0 }, collision_enabled: true, visual_enabled: true },
  ]);

  const [validation, setValidation] = useState<ScenarioValidation>({ valid: true, errors: [], warnings: [] });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Validate Scenario Parameters
  useEffect(() => {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (windSpeed < 0 || windSpeed > 50) {
      errors.push(`Wind speed (${windSpeed} m/s) out of valid range [0, 50]`);
    } else if (windSpeed > 15) {
      warnings.push(`High wind speed (${windSpeed} m/s) may destabilize multicopters`);
    }

    if (stepSize <= 0) errors.push('Physics step size must be positive');
    if (simRate <= 0) errors.push('Simulation update rate must be positive');

    setValidation({ valid: errors.length === 0, errors, warnings });
  }, [windSpeed, stepSize, simRate]);

  // 3D Live World Preview Canvas Renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Ground Grid Lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    // World Objects Preview Rendering
    worldObjects.forEach((obj) => {
      const px = cx + obj.position.x * 20;
      const py = cy - obj.position.y * 20;

      if (obj.object_type === 'LANDING_PAD') {
        ctx.fillStyle = '#eab308';
        ctx.fillRect(px - 20, py - 20, 40, 40);
        ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2;
        ctx.strokeRect(px - 20, py - 20, 40, 40);
        ctx.fillStyle = '#ffffff'; ctx.font = '12px sans-serif'; ctx.fillText('H', px - 4, py + 4);
      } else if (obj.object_type === 'STATIC_BOX') {
        ctx.fillStyle = '#64748b';
        ctx.fillRect(px - 15, py - 15, 30, 30);
        ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1;
        ctx.strokeRect(px - 15, py - 15, 30, 30);
      }
    });

    // Vehicle Spawn Position Marker
    const vx = cx + spawnX * 20;
    const vy = cy - spawnY * 20;
    ctx.fillStyle = '#38bdf8';
    ctx.beginPath(); ctx.arc(vx, vy, 8, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#0284c7'; ctx.lineWidth = 2; ctx.stroke();

    // Spawn Heading Arrow
    const headingRad = (spawnHeading * Math.PI) / 180;
    ctx.strokeStyle = '#f43f5e'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(vx, vy); ctx.lineTo(vx + Math.sin(headingRad) * 25, vy - Math.cos(headingRad) * 25); ctx.stroke();
  }, [worldObjects, spawnX, spawnY, spawnHeading]);

  const handleAddObject = (type: string) => {
    setWorldObjects([...worldObjects, {
      object_type: type,
      position: { x: (Math.random() - 0.5) * 10, y: (Math.random() - 0.5) * 10, z: 1.0 },
      orientation: { roll: 0, pitch: 0, yaw: 0 },
      scale: { x: 2.0, y: 2.0, z: 2.0 },
      collision_enabled: true,
      visual_enabled: true,
    }]);
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', color: '#f8fafc', fontFamily: 'sans-serif' }}>
      <h2>AeroGuard Scenario Builder (Stage S6)</h2>
      <p style={{ color: '#94a3b8' }}>Define reproducible simulation environments, weather, physics, and mission spawn parameters.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', marginTop: '20px' }}>
        {/* Section 1: Vehicle & World Selection */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Vehicle & World</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label>Scenario Name: <input type="text" value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} style={{ width: '100%' }} /></label>
            <label>Target Vehicle:
              <select value={selectedVehicle} onChange={(e) => setSelectedVehicle(e.target.value)} style={{ width: '100%' }}>
                <option value="veh-default-q450">Holybro S500 Quad-X (1158g)</option>
                <option value="veh-default-q650">Tarot 650 Sport (1620g)</option>
              </select>
            </label>
            <label>World Type:
              <select value={selectedWorldType} onChange={(e) => setSelectedWorldType(e.target.value)} style={{ width: '100%' }}>
                <option value="FLAT_GROUND">Flat Grassland Ground</option>
                <option value="EMPTY">Empty Free Space</option>
              </select>
            </label>
          </div>
        </div>

        {/* Section 2: Environment & Weather */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Environment & Weather</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label>Wind Speed (m/s): <input type="number" value={windSpeed} onChange={(e) => setWindSpeed(Number(e.target.value))} style={{ width: '100%' }} /></label>
            <label>Wind Direction (deg): <input type="number" value={windDirection} onChange={(e) => setWindDirection(Number(e.target.value))} style={{ width: '100%' }} /></label>
            <label>Turbulence:
              <select value={turbulence} onChange={(e) => setTurbulence(e.target.value)} style={{ width: '100%' }}>
                <option value="NONE">None</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </label>
          </div>
        </div>

        {/* Section 3: Physics & Validation Status */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Physics & Validation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label>Sim Rate (Hz): <input type="number" value={simRate} onChange={(e) => setSimRate(Number(e.target.value))} style={{ width: '100%' }} /></label>
            <label>Step Size (s): <input type="number" value={stepSize} onChange={(e) => setStepSize(Number(e.target.value))} style={{ width: '100%' }} /></label>
            <label>Random Seed: <input type="number" value={randomSeed} onChange={(e) => setRandomSeed(Number(e.target.value))} style={{ width: '100%' }} /></label>
            
            <div style={{ fontSize: '13px', marginTop: '10px' }}>
              Status: <strong style={{ color: validation.valid ? '#22c55e' : '#f43f5e' }}>{validation.valid ? '✓ VALID SCENARIO' : '❌ INVALID'}</strong>
              {validation.errors.map((err, i) => <div key={i} style={{ color: '#f43f5e', fontSize: '11px' }}>❌ {err}</div>)}
              {validation.warnings.map((warn, i) => <div key={i} style={{ color: '#f59e0b', fontSize: '11px' }}>⚠️ {warn}</div>)}
            </div>
          </div>
        </div>
      </div>

      {/* 3D Live World Preview Canvas */}
      <div style={{ marginTop: '20px', background: '#020617', padding: '15px', borderRadius: '8px', border: '1px solid #334155' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3>3D Live World Preview & Object Placement</h3>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={() => handleAddObject('STATIC_BOX')} style={{ background: '#475569', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>+ Add Box</button>
            <button onClick={() => handleAddObject('LANDING_PAD')} style={{ background: '#475569', color: '#fff', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>+ Add Landing Pad</button>
          </div>
        </div>
        <canvas ref={canvasRef} width={800} height={300} style={{ width: '100%', background: '#090d16', borderRadius: '4px' }} />
      </div>
    </div>
  );
};
