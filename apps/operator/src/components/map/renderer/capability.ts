/**
 * WebGPU & Canvas 2D Capability Detection for AeroGuard MAP2
 */

import { RendererCapabilities, RendererType } from './types';

let cachedCapabilities: RendererCapabilities | null = null;

export async function detectRendererCapabilities(): Promise<RendererCapabilities> {
  if (cachedCapabilities) {
    return cachedCapabilities;
  }

  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
  let hasCanvas2D = false;
  let hasWebGPU = false;
  let preferredType: RendererType = 'LEGACY';
  let diagnosticsMessage = 'Initialized renderer capability detection.';
  let maxTextureDimension2D: number | undefined;
  let adapterInfo: RendererCapabilities['adapterInfo'];

  // 1. Check Canvas 2D support
  try {
    if (typeof document !== 'undefined') {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      hasCanvas2D = !!ctx;
      if (hasCanvas2D) {
        preferredType = 'CANVAS';
      }
    }
  } catch (err) {
    hasCanvas2D = false;
  }

  // 2. Check WebGPU support
  try {
    if (typeof navigator !== 'undefined' && 'gpu' in navigator && (navigator as any).gpu) {
      const gpu = (navigator as any).gpu;
      const adapter = await gpu.requestAdapter({
        powerPreference: 'high-performance',
      });

      if (adapter) {
        // Request device to confirm capability
        const device = await adapter.requestDevice();
        if (device) {
          hasWebGPU = true;
          preferredType = 'WEBGPU';
          maxTextureDimension2D = device.limits?.maxTextureDimension2D || 8192;

          if (adapter.info) {
            adapterInfo = {
              vendor: adapter.info.vendor,
              architecture: adapter.info.architecture,
              device: adapter.info.device,
              description: adapter.info.description,
            };
          }

          diagnosticsMessage = `WebGPU hardware acceleration active (${adapterInfo?.description || adapterInfo?.vendor || 'Standard GPU'}).`;
          device.destroy();
        }
      }
    }
  } catch (err: any) {
    hasWebGPU = false;
    diagnosticsMessage = `WebGPU unavailable (${err?.message || 'Unsupported'}). Falling back to Canvas 2D.`;
  }

  if (!hasWebGPU && hasCanvas2D) {
    diagnosticsMessage = 'Canvas 2D hardware-accelerated pipeline active.';
  } else if (!hasWebGPU && !hasCanvas2D) {
    diagnosticsMessage = 'Canvas 2D unavailable. Falling back to SVG DOM rendering.';
    preferredType = 'LEGACY';
  }

  cachedCapabilities = {
    preferredType,
    hasWebGPU,
    hasCanvas2D,
    adapterInfo,
    maxTextureDimension2D,
    devicePixelRatio: dpr,
    diagnosticsMessage,
  };

  return cachedCapabilities;
}

export function resetCapabilityCache(): void {
  cachedCapabilities = null;
}
