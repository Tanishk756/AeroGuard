import React from 'react';

export interface BarChartItem {
  label: string;
  value: number;
}

interface BarChartProps {
  title: string;
  data: BarChartItem[];
  color?: string;
  height?: number;
}

/**
 * Accessible SVG horizontal bar chart.
 *
 * Accessibility requirements:
 *  - role="img" on the <svg> with aria-label matching the title prop.
 *  - <title> element with the chart title.
 *  - <desc> element listing all data points so screen readers can convey content.
 *  - Numeric value labels on every bar (non-color-only information).
 */
export const BarChart: React.FC<BarChartProps> = ({
  title,
  data,
  color = 'var(--color-accent)',
  height = 180,
}) => {
  if (!data || data.length === 0) {
    return (
      <p className="text-muted text-xs" style={{ padding: '8px 0' }}>
        No data available.
      </p>
    );
  }

  const max = Math.max(...data.map((d) => d.value), 1);
  const barHeight = Math.max(12, Math.floor((height - data.length * 6) / data.length));
  const labelWidth = 100;
  const valueWidth = 48;
  const svgWidth = 480;
  const barAreaWidth = svgWidth - labelWidth - valueWidth - 16;
  const svgHeight = data.length * (barHeight + 6) + 12;

  // Build accessible description string for screen readers.
  const descText = data.map((d) => `${d.label}: ${d.value}`).join(', ');

  return (
    <svg
      role="img"
      aria-label={title}
      width="100%"
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      style={{ display: 'block', overflow: 'visible' }}
    >
      <title>{title}</title>
      <desc>{descText}</desc>

      {data.map((item, i) => {
        const y = i * (barHeight + 6) + 6;
        const barWidth = max > 0 ? Math.round((item.value / max) * barAreaWidth) : 0;

        return (
          <g key={item.label}>
            {/* Label */}
            <text
              x={labelWidth - 8}
              y={y + barHeight / 2 + 4}
              textAnchor="end"
              fontSize="11"
              fill="var(--text-secondary)"
              style={{ fontFamily: 'var(--font-mono, monospace)', textTransform: 'uppercase' }}
            >
              {item.label}
            </text>

            {/* Bar background */}
            <rect
              x={labelWidth}
              y={y}
              width={barAreaWidth}
              height={barHeight}
              rx={3}
              fill="var(--bg-canvas, #0d1117)"
            />

            {/* Bar fill */}
            <rect
              x={labelWidth}
              y={y}
              width={barWidth}
              height={barHeight}
              rx={3}
              fill={color}
              opacity={0.85}
            />

            {/* Numeric value label (non-color-only information) */}
            <text
              x={labelWidth + barAreaWidth + 6}
              y={y + barHeight / 2 + 4}
              textAnchor="start"
              fontSize="11"
              fill="var(--text-muted)"
              style={{ fontFamily: 'var(--font-mono, monospace)' }}
            >
              {item.value.toLocaleString()}
            </text>
          </g>
        );
      })}
    </svg>
  );
};
