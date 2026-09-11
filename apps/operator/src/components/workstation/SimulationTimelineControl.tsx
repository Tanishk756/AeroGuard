import React from 'react';

export interface TimelineEventMarker {
  id: string;
  sim_time_seconds: number;
  type: 'SAFETY' | 'MISSION' | 'DISCONNECT';
  label: string;
  severity?: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface SimulationTimelineControlProps {
  currentSimTime: number;
  totalDuration: number;
  isPlaying: boolean;
  playbackSpeed: number;
  events?: TimelineEventMarker[];
  onPlayPause: () => void;
  onStep: (count: number) => void;
  onSeek: (timeSeconds: number) => void;
  onSpeedChange: (speed: number) => void;
  onReset?: () => void;
}

export const SimulationTimelineControl: React.FC<SimulationTimelineControlProps> = ({
  currentSimTime,
  totalDuration,
  isPlaying,
  playbackSpeed,
  events = [],
  onPlayPause,
  onStep,
  onSeek,
  onSpeedChange,
  onReset,
}) => {
  const maxDuration = Math.max(totalDuration, 60.0);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(4, '0')}`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-slate-200 shadow-lg space-y-2">
      {/* Control Buttons & Digital Clock Display */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button
            onClick={onPlayPause}
            className={`px-3 py-1.5 rounded font-semibold text-xs transition-colors ${
              isPlaying
                ? 'bg-amber-600 hover:bg-amber-500 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            {isPlaying ? 'PAUSE' : 'PLAY'}
          </button>
          <button
            onClick={() => onStep(1)}
            disabled={isPlaying}
            className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs rounded border border-slate-700"
          >
            STEP +1
          </button>
          {onReset && (
            <button
              onClick={onReset}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700"
            >
              RESET
            </button>
          )}
        </div>

        {/* Timestamp Readout */}
        <div className="font-mono text-sm tracking-wider text-cyan-400 font-bold">
          T+ {formatTime(currentSimTime)} / {formatTime(maxDuration)}
        </div>

        {/* Speed Controls */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded border border-slate-800 text-xs">
          <span className="text-slate-400 px-1 font-mono">SPEED:</span>
          {[0.5, 1.0, 2.0, 4.0].map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                playbackSpeed === s ? 'bg-cyan-600 text-white font-bold' : 'hover:bg-slate-800 text-slate-400'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Scrubber & Event Track */}
      <div className="relative pt-2 pb-1">
        <input
          type="range"
          min={0}
          max={maxDuration}
          step={0.1}
          value={currentSimTime}
          onChange={(e) => onSeek(parseFloat(e.target.value))}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
        />

        {/* Event Markers Overlay */}
        <div className="relative w-full h-3 mt-1">
          {events.map((ev) => {
            const leftPct = Math.min(100, Math.max(0, (ev.sim_time_seconds / maxDuration) * 100));
            const markerColor =
              ev.type === 'SAFETY'
                ? 'bg-rose-500'
                : ev.type === 'MISSION'
                ? 'bg-emerald-400'
                : 'bg-amber-400';
            return (
              <button
                key={ev.id}
                onClick={() => onSeek(ev.sim_time_seconds)}
                title={`[T+${ev.sim_time_seconds.toFixed(1)}s] ${ev.type}: ${ev.label}`}
                style={{ left: `${leftPct}%` }}
                className={`absolute top-0 transform -translate-x-1/2 w-2 h-2.5 rounded-full ${markerColor} hover:scale-150 transition-transform cursor-pointer`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};
