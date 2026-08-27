# AeroGuard MAP2 — Advanced Tactical Visualization & GPU Acceleration Architecture

**Stage MAP2** upgrades AeroGuard's tactical visualization engine from DOM/SVG-oriented rendering to a high-density, low-latency, hardware-accelerated rendering architecture supporting live tracks, historical trails, geofences, sensor coverage, forward trajectory predictions, spatial uncertainty envelopes, and perimeter ingress hazard markers.

---

## 1. Tactical Renderer Architecture

```
                  ┌─────────────────────────────────────┐
                  │    Authoritative Operational State   │
                  │   (Tracks, Sensors, Geofences, AI)   │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │         buildRenderScene()          │
                  │   (Equirectangular Math + Culling)  │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │        Tactical Map Canvas        │
                   │        (IMapRenderer API)         │
                   └─────────┬───────────────┬─────────┘
                             │               │
                 WebGPU Active?              Fallback
                             ▼               ▼
                   ┌──────────────────┐ ┌──────────────────┐
                   │  WebGPURenderer  │ │  CanvasRenderer  │
                   │  (WGSL Shaders)  │ │  (Batch 2D Path) │
                   └──────────────────┘ └──────────────────┘
```

### Renderer Abstraction (`IMapRenderer`)
All tactical renderers implement the unified contract defined in `apps/operator/src/components/map/renderer/types.ts`:
```typescript
export interface IMapRenderer {
  readonly type: RendererType; // 'WEBGPU' | 'CANVAS' | 'LEGACY'
  readonly isInitialized: boolean;
  initialize(canvas: HTMLCanvasElement): Promise<boolean>;
  render(scene: RenderScene): void;
  resize(width: number, height: number): void;
  hitTest(screenX: number, screenY: number, scene: RenderScene): HitTestResult | null;
  destroy(): void;
}
```

---

## 2. Hardware Capability Detection & Fallback Cascade

1. **WebGPU Hardware Accelerated (`WEBGPU`)**:
   - Safely queries `navigator.gpu.requestAdapter({ powerPreference: 'high-performance' })` and `adapter.requestDevice()`.
   - Uses WGSL vertex/fragment shaders and instanced GPU buffers for high-density chevrons and vector fields.
2. **High-Performance Canvas 2D (`CANVAS`)**:
   - Automatic fallback when WebGPU is unavailable (e.g. Windows Tauri webview environments without experimental WebGPU flags enabled).
   - Utilizes batch path drawing, high-DPI `devicePixelRatio` scaling, and spatial culling.
3. **Legacy SVG DOM (`LEGACY`)**:
   - Preserved for interactive authoring overlays (`draftGeometry` in Defense Zone Studio).

---

## 3. Normalized Scene Model & Render Layers

The normalized `RenderScene` isolates presentation concerns from backend/UI state and renders in strict tactical z-order:

| Layer Index | Visual Element | Rendering Strategy |
| :---: | :--- | :--- |
| **1** | Coordinate Grid | Equirectangular grid lines ($80\text{px}$) with geographic lat/lon labels. |
| **2** | Concentric Range Rings | Tactical distances ($500\text{m}$, $1000\text{m}$, $2000\text{m}$, $5000\text{m}$) and center reticle. |
| **3** | Defense Geofences | Alpha-filled polygons and bounding boxes with distinct borders for `ENABLED`, `DISABLED`, `SELECTED`, `WARNING`. |
| **4** | Sensor Coverage | Range radius circles and active status center nodes with callouts. |
| **5** | Track History Trails | Bounded historical trajectory nodes with temporal alpha falloff ($0.3 \to 1.0$). |
| **6** | AI1 Trajectory & Uncertainty | Cyan dashed forward vector, expanding spatial uncertainty discs ($\sigma_r(t)$), $+30\text{s}$ & $+60\text{s}$ time tags, and perimeter ingress hazard reticles. |
| **7** | Track Markers | Directional chevrons rotated to track heading, color-coded by threat/anomaly state, with anomaly halo discs. |
| **8** | Monospace Callouts | Callsigns, altitude, and ground speed (density-throttled under high load). |

---

## 4. High-Density Optimization & Culling

- **Viewport Spatial Culling**: Tracks outside the viewport bounds plus a $60\text{px}$ safety margin are culled before rendering, reducing drawing overhead to $O(\text{visible})$.
- **Density-Aware Label Throttling**: When total track count exceeds 80, labels for nominal unselected tracks are suppressed, keeping the display clutter-free and maintaining consistent 60 FPS.
- **Bounded Trail Buffers**: History is capped at $N=30$ points per track, preventing memory runaway during long-duration operations.

---

## 5. Performance Benchmarks

Measured on local test suite (`apps/operator/src/test/map_benchmarks.test.ts`):

| Track Density | Scene Projection & Culling Latency | Per-Track Time | 60 FPS Budget Utilization |
| :---: | :---: | :---: | :---: |
| **10 Tracks** | **0.009 ms** | 0.88 µs | 0.05% |
| **50 Tracks** | **0.038 ms** | 0.77 µs | 0.23% |
| **100 Tracks** | **0.076 ms** | 0.76 µs | 0.46% |
| **500 Tracks** | **0.407 ms** | 0.81 µs | 2.45% |
| **1,000 Tracks** | **0.840 ms** | 0.84 µs | **5.06%** |
| **Hit-Test Lookup** | **0.0085 ms** (1,000 tracks) | — | Sub-microsecond |

---

## 6. Accessibility & Keyboard Navigation

- **Keyboard Pan**: `ArrowUp`/`W`, `ArrowDown`/`S`, `ArrowLeft`/`A`, `ArrowRight`/`D`.
- **Keyboard Zoom & Reset**: `+`/`=` to zoom in, `-`/`_` to zoom out, `0`/`R` to reset view, `Escape` to clear selection.
- **Screen Reader Support**: Semantic `role="region"` with `aria-live="polite"` live status announcements summarizing active tracks, selected entity state, and anomaly severity.

---

## 7. Tauri Desktop & Browser Compatibility

The rendering system runs identically inside standard modern browsers (Chrome, Edge, Firefox) and the Tauri 2 desktop shell (`src-tauri` WebView2). If hardware WebGPU is disabled or unsupported by the local graphics driver, the canvas seamlessly transitions to the 2D hardware-accelerated pipeline with zero visual interruption.
