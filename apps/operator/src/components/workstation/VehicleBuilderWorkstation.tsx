import React, { useState, useEffect, useRef } from 'react';

export interface HardwareComponent {
  id: string;
  manufacturer: string;
  model: string;
  category: string;
  mass_g: number;
  datasheet_url?: string | null;
  electrical_specs?: Record<string, any> | null;
}

export interface VehicleCompatibility {
  compatible: boolean;
  errors: string[];
  warnings: string[];
  total_mass_g: number;
  estimated_hover_throttle: number;
  thrust_to_weight_ratio: number;
}

export const VehicleBuilderWorkstation: React.FC = () => {
  const [hardwareList, setHardwareList] = useState<HardwareComponent[]>([]);
  const [selectedFrame, setSelectedFrame] = useState<string>('');
  const [selectedMotor, setSelectedMotor] = useState<string>('');
  const [selectedEsc, setSelectedEsc] = useState<string>('');
  const [selectedProp, setSelectedProp] = useState<string>('');
  const [selectedBattery, setSelectedBattery] = useState<string>('');
  const [selectedFc, setSelectedFc] = useState<string>('');
  const [selectedGps, setSelectedGps] = useState<string>('');
  const [vehicleName, setVehicleName] = useState<string>('Quad-X Digital Twin');
  const [compatibility, setCompatibility] = useState<VehicleCompatibility | null>(null);
  const [createdVehicleId, setCreatedVehicleId] = useState<string | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Default Reference Hardware Catalog
  const defaultComponents: HardwareComponent[] = [
    { id: 'frame-q450', manufacturer: 'Holybro', model: 'S500 Quad-X Frame', category: 'frame', mass_g: 280.0 },
    { id: 'motor-mn2212', manufacturer: 'T-Motor', model: 'MN2212 920KV', category: 'motor', mass_g: 55.0, electrical_specs: { max_voltage_v: 16.8, max_current_a: 18.0, max_thrust_g: 1100.0 } },
    { id: 'esc-bl30a', manufacturer: 'Holybro', model: 'Tekko32 30A ESC', category: 'esc', mass_g: 12.0, electrical_specs: { current_rating_a: 30.0, min_cells: 2, max_cells: 6 } },
    { id: 'prop-1045', manufacturer: 'Gemfan', model: '1045 Carbon Propellers', category: 'propeller', mass_g: 15.0 },
    { id: 'bat-4s5000', manufacturer: 'Tattu', model: '4S 14.8V 5000mAh 45C LiPo', category: 'battery', mass_g: 450.0, electrical_specs: { cell_count_s: 4, nominal_voltage_v: 14.8, capacity_mah: 5000.0 } },
    { id: 'fc-pixhawk4', manufacturer: 'Holybro', model: 'Pixhawk 4 Flight Controller', category: 'flight_controller', mass_g: 68.0 },
    { id: 'gps-m8n', manufacturer: 'u-blox', model: 'NEO-M8N GPS Module', category: 'gps', mass_g: 32.0 },
  ];

  useEffect(() => {
    fetch('/api/v1/hardware')
      .then((res) => res.json())
      .then((data: HardwareComponent[]) => {
        if (data.length > 0) {
          setHardwareList(data);
        } else {
          setHardwareList(defaultComponents);
        }
      })
      .catch(() => setHardwareList(defaultComponents));
  }, []);

  // Auto-select defaults
  useEffect(() => {
    if (hardwareList.length > 0) {
      if (!selectedFrame) setSelectedFrame(hardwareList.find((c) => c.category === 'frame')?.id || '');
      if (!selectedMotor) setSelectedMotor(hardwareList.find((c) => c.category === 'motor')?.id || '');
      if (!selectedEsc) setSelectedEsc(hardwareList.find((c) => c.category === 'esc')?.id || '');
      if (!selectedProp) setSelectedProp(hardwareList.find((c) => c.category === 'propeller')?.id || '');
      if (!selectedBattery) setSelectedBattery(hardwareList.find((c) => c.category === 'battery')?.id || '');
      if (!selectedFc) setSelectedFc(hardwareList.find((c) => c.category === 'flight_controller')?.id || '');
      if (!selectedGps) setSelectedGps(hardwareList.find((c) => c.category === 'gps')?.id || '');
    }
  }, [hardwareList]);

  // Recalculate physical compatibility metrics locally
  useEffect(() => {
    const frame = hardwareList.find((c) => c.id === selectedFrame);
    const motor = hardwareList.find((c) => c.id === selectedMotor);
    const esc = hardwareList.find((c) => c.id === selectedEsc);
    const prop = hardwareList.find((c) => c.id === selectedProp);
    const bat = hardwareList.find((c) => c.id === selectedBattery);
    const fc = hardwareList.find((c) => c.id === selectedFc);
    const gps = hardwareList.find((c) => c.id === selectedGps);

    if (frame && motor && esc && prop && bat && fc) {
      const totalMass = frame.mass_g + (motor.mass_g * 4) + (esc.mass_g * 4) + (prop.mass_g * 4) + bat.mass_g + fc.mass_g + (gps ? gps.mass_g : 0);
      const motorThrust = motor.electrical_specs?.max_thrust_g || 1100.0;
      const totalThrust = motorThrust * 4;
      const twRatio = Number((totalThrust / Math.max(totalMass, 1.0)).toFixed(2));
      const hoverThrottle = Number(Math.min(1.0, Math.max(0.1, 1.0 / twRatio)).toFixed(2));

      const errors: string[] = [];
      const warnings: string[] = [];

      const motorMaxV = motor.electrical_specs?.max_voltage_v || 16.8;
      const batV = bat.electrical_specs?.nominal_voltage_v || 14.8;
      if (batV > motorMaxV) {
        errors.push(`Motor max voltage (${motorMaxV}V) exceeded by battery (${batV}V)`);
      }

      if (twRatio < 1.2) {
        errors.push(`Insufficient Thrust-to-Weight ratio (${twRatio}); minimum 1.2 required`);
      } else if (twRatio < 1.5) {
        warnings.push(`Marginal Thrust-to-Weight ratio (${twRatio}); recommended > 1.8`);
      }

      setCompatibility({
        compatible: errors.length === 0,
        errors,
        warnings,
        total_mass_g: totalMass,
        estimated_hover_throttle: hoverThrottle,
        thrust_to_weight_ratio: twRatio,
      });
    }
  }, [selectedFrame, selectedMotor, selectedEsc, selectedProp, selectedBattery, selectedFc, selectedGps, hardwareList]);

  // 3D Quad-X Hardware Canvas Visualizer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Outer Frame Arms
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(cx - 70, cy - 70); ctx.lineTo(cx + 70, cy + 70); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + 70, cy - 70); ctx.lineTo(cx - 70, cy + 70); ctx.stroke();

    // Flight Controller Center Hub
    ctx.fillStyle = '#22c55e';
    ctx.fillRect(cx - 20, cy - 20, 40, 40);
    ctx.fillStyle = '#ffffff';
    ctx.font = '10px sans-serif';
    ctx.fillText('PIXHAWK', cx - 18, cy + 3);

    // Motor & Propeller Rotors
    ctx.fillStyle = '#f43f5e';
    [[cx - 70, cy - 70], [cx + 70, cy - 70], [cx + 70, cy + 70], [cx - 70, cy + 70]].forEach(([mx, my]) => {
      ctx.beginPath(); ctx.arc(mx, my, 12, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(mx, my, 25, 0, Math.PI * 2); ctx.stroke();
    });
  }, [selectedFrame, selectedMotor, selectedProp]);

  const handleSimulateVehicle = async () => {
    if (!compatibility?.compatible) return;
    setIsSimulating(true);
    try {
      const res = await fetch('/api/v1/vehicles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-default-01',
          name: vehicleName,
          vehicle_type: 'quadcopter',
          frame_id: selectedFrame,
          motor_id: selectedMotor,
          esc_id: selectedEsc,
          propeller_id: selectedProp,
          battery_id: selectedBattery,
          flight_controller_id: selectedFc,
          gps_id: selectedGps || undefined,
        }),
      });
      const data = await res.json();
      setCreatedVehicleId(data.id);
      setIsSimulating(false);
      alert(`Vehicle '${vehicleName}' created successfully! (ID: ${data.id})`);
    } catch {
      setIsSimulating(false);
    }
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', color: '#f8fafc', fontFamily: 'sans-serif' }}>
      <h2>AeroGuard Hardware-Aware Vehicle Builder</h2>
      <p style={{ color: '#94a3b8' }}>Assemble real hardware components into a verified UAV Digital Twin.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr 1fr', gap: '20px', marginTop: '20px' }}>
        {/* Column 1: Hardware Component Selector */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Hardware Selection</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label>Vehicle Name: <input type="text" value={vehicleName} onChange={(e) => setVehicleName(e.target.value)} style={{ width: '100%' }} /></label>
            <label>Frame:
              <select value={selectedFrame} onChange={(e) => setSelectedFrame(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'frame').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
            <label>Motor:
              <select value={selectedMotor} onChange={(e) => setSelectedMotor(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'motor').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
            <label>ESC:
              <select value={selectedEsc} onChange={(e) => setSelectedEsc(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'esc').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
            <label>Propeller:
              <select value={selectedProp} onChange={(e) => setSelectedProp(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'propeller').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
            <label>Battery:
              <select value={selectedBattery} onChange={(e) => setSelectedBattery(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'battery').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
            <label>Flight Controller:
              <select value={selectedFc} onChange={(e) => setSelectedFc(e.target.value)} style={{ width: '100%' }}>
                {hardwareList.filter(c => c.category === 'flight_controller').map(c => <option key={c.id} value={c.id}>{c.manufacturer} {c.model} ({c.mass_g}g)</option>)}
              </select>
            </label>
          </div>
        </div>

        {/* Column 2: 3D Hardware Visualizer */}
        <div style={{ background: '#020617', padding: '15px', borderRadius: '8px', border: '1px solid #334155' }}>
          <h3>3D Digital Twin Visualizer</h3>
          <canvas ref={canvasRef} width={400} height={350} style={{ width: '100%', background: '#090d16', borderRadius: '4px' }} />
        </div>

        {/* Column 3: Real-Time Compatibility Panel */}
        <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px' }}>
          <h3>Compatibility Validation</h3>
          <div style={{ fontSize: '14px', marginBottom: '15px' }}>
            Status: <strong style={{ color: compatibility?.compatible ? '#22c55e' : '#f43f5e' }}>{compatibility?.compatible ? '✓ COMPATIBLE' : '❌ INCOMPATIBLE'}</strong>
          </div>
          <div>Total Mass: <strong>{compatibility?.total_mass_g || 0} g</strong></div>
          <div>Thrust-to-Weight: <strong>{compatibility?.thrust_to_weight_ratio || 0}:1</strong></div>
          <div>Est. Hover Throttle: <strong>{((compatibility?.estimated_hover_throttle || 0.5) * 100).toFixed(0)}%</strong></div>

          {compatibility?.errors && compatibility.errors.length > 0 && (
            <div style={{ color: '#f43f5e', fontSize: '12px', marginTop: '10px' }}>
              {compatibility.errors.map((e, idx) => <div key={idx}>❌ {e}</div>)}
            </div>
          )}

          <div style={{ marginTop: '20px' }}>
            <button onClick={handleSimulateVehicle} disabled={!compatibility?.compatible || isSimulating} style={{ width: '100%', padding: '10px', background: '#38bdf8', color: '#0f172a', fontWeight: 'bold', border: 'none', borderRadius: '4px' }}>
              {isSimulating ? 'Creating Digital Twin...' : 'Simulate This Vehicle'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
