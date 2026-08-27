/**
 * Hardware-Accelerated WebGPU Tactical Renderer for AeroGuard MAP2
 */

import { CanvasRenderer } from './CanvasRenderer';
import { BaseMapRenderer } from './MapRenderer';
import { RenderScene, RendererType } from './types';

const WGSL_SHADERS = `
struct Uniforms {
  resolution: vec2<f32>,
  time: f32,
  padding: f32,
};

@group(0) @binding(0) var<uniform> uniforms: Uniforms;

struct VertexInput {
  @location(0) position: vec2<f32>,
  @location(1) instancePos: vec2<f32>,
  @location(2) instanceColor: vec4<f32>,
  @location(3) instanceHeading: f32,
  @location(4) instanceSize: f32,
};

struct VertexOutput {
  @builtin(position) position: vec4<f32>,
  @location(0) color: vec4<f32>,
};

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
  var out: VertexOutput;
  let rad = in.instanceHeading * 3.14159265 / 180.0;
  let cosH = cos(rad);
  let sinH = sin(rad);

  // Rotate local vertex
  let rotated = vec2<f32>(
    in.position.x * cosH - in.position.y * sinH,
    in.position.x * sinH + in.position.y * cosH
  ) * in.instanceSize;

  let screenPos = in.instancePos + rotated;
  let clipX = (screenPos.x / uniforms.resolution.x) * 2.0 - 1.0;
  let clipY = 1.0 - (screenPos.y / uniforms.resolution.y) * 2.0;

  out.position = vec4<f32>(clipX, clipY, 0.0, 1.0);
  out.color = in.instanceColor;
  return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
  return in.color;
}
`;

export class WebGPURenderer extends BaseMapRenderer {
  readonly type: RendererType = 'WEBGPU';
  private device: any = null;
  private context: any = null;
  private pipeline: any = null;
  private uniformBuffer: any = null;
  private uniformBindGroup: any = null;
  private vertexBuffer: any = null;
  private instanceBuffer: any = null;
  private fallbackRenderer: CanvasRenderer | null = null;
  private isUsingFallback = false;

  async initialize(canvas: HTMLCanvasElement): Promise<boolean> {
    this.canvas = canvas;

    try {
      if (typeof navigator === 'undefined' || !('gpu' in navigator)) {
        throw new Error('WebGPU not supported in this runtime');
      }

      const gpu = (navigator as any).gpu;
      const adapter = await gpu.requestAdapter({ powerPreference: 'high-performance' });
      if (!adapter) throw new Error('Failed to acquire WebGPU adapter');

      this.device = await adapter.requestDevice();
      this.context = canvas.getContext('webgpu');
      if (!this.context) throw new Error('Failed to create WebGPU context');

      const format = gpu.getPreferredCanvasFormat();
      this.context.configure({
        device: this.device,
        format,
        alphaMode: 'premultiplied',
      });

      // Compile WGSL Shader Module
      const shaderModule = this.device.createShaderModule({
        code: WGSL_SHADERS,
      });

      // Create Chevron Geometry Vertex Buffer (Triangle fan)
      // [-6, 6], [0, -8], [6, 6], [0, 3]
      const chevronVertices = new Float32Array([
        0.0, -1.0,
        0.8, 0.8,
        0.0, 0.4,
        0.0, -1.0,
        0.0, 0.4,
        -0.8, 0.8,
      ]);

      this.vertexBuffer = this.device.createBuffer({
        size: chevronVertices.byteLength,
        usage: (window as any).GPUBufferUsage?.VERTEX || 0x20,
        mappedAtCreation: true,
      });
      new Float32Array(this.vertexBuffer.getMappedRange()).set(chevronVertices);
      this.vertexBuffer.unmap();

      // Create Uniform Buffer
      this.uniformBuffer = this.device.createBuffer({
        size: 16, // 4 floats: resolution.xy, time, padding
        usage: ((window as any).GPUBufferUsage?.UNIFORM || 0x40) | ((window as any).GPUBufferUsage?.COPY_DST || 0x08),
      });

      // Create Render Pipeline
      const bindGroupLayout = this.device.createBindGroupLayout({
        entries: [
          {
            binding: 0,
            visibility: 0x1, // GPUShaderStage.VERTEX
            buffer: { type: 'uniform' },
          },
        ],
      });

      this.uniformBindGroup = this.device.createBindGroup({
        layout: bindGroupLayout,
        entries: [
          {
            binding: 0,
            resource: { buffer: this.uniformBuffer },
          },
        ],
      });

      const pipelineLayout = this.device.createPipelineLayout({
        bindGroupLayouts: [bindGroupLayout],
      });

      this.pipeline = this.device.createRenderPipeline({
        layout: pipelineLayout,
        vertex: {
          module: shaderModule,
          entryPoint: 'vs_main',
          buffers: [
            {
              arrayStride: 8, // 2 * 4 bytes
              attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x2' }],
            },
            {
              arrayStride: 36, // instance: pos(8) + color(16) + heading(4) + size(4) + pad(4)
              stepMode: 'instance',
              attributes: [
                { shaderLocation: 1, offset: 0, format: 'float32x2' },
                { shaderLocation: 2, offset: 8, format: 'float32x4' },
                { shaderLocation: 3, offset: 24, format: 'float32' },
                { shaderLocation: 4, offset: 28, format: 'float32' },
              ],
            },
          ],
        },
        fragment: {
          module: shaderModule,
          entryPoint: 'fs_main',
          targets: [
            {
              format,
              blend: {
                color: {
                  srcFactor: 'src-alpha',
                  dstFactor: 'one-minus-src-alpha',
                  operation: 'add',
                },
                alpha: {
                  srcFactor: 'one',
                  dstFactor: 'one-minus-src-alpha',
                  operation: 'add',
                },
              },
            },
          ],
        },
        primitive: {
          topology: 'triangle-list',
        },
      });

      this._isInitialized = true;
      this.isUsingFallback = false;
      return true;
    } catch (err) {
      // Graceful fallback to Canvas 2D
      this.fallbackRenderer = new CanvasRenderer();
      const ok = await this.fallbackRenderer.initialize(canvas);
      this._isInitialized = ok;
      this.isUsingFallback = true;
      return ok;
    }
  }

  render(scene: RenderScene): void {
    if (this.isUsingFallback && this.fallbackRenderer) {
      this.fallbackRenderer.render(scene);
      return;
    }

    if (!this._isInitialized || !this.device || !this.context || !this.pipeline) {
      if (this.fallbackRenderer) {
        this.fallbackRenderer.render(scene);
      }
      return;
    }

    try {
      const { width, height } = scene.viewport;

      // Update uniforms
      const uniformData = new Float32Array([width, height, performance.now() / 1000.0, 0.0]);
      this.device.queue.writeBuffer(this.uniformBuffer, 0, uniformData);

      // Pack instance buffer for visible tracks
      const trackCount = scene.tracks.length;
      if (trackCount > 0) {
        const instanceData = new Float32Array(trackCount * 9);
        for (let i = 0; i < trackCount; i++) {
          const t = scene.tracks[i];
          const offset = i * 9;
          instanceData[offset] = t.screenX;
          instanceData[offset + 1] = t.screenY;

          // Color RGBA
          if (t.isThreatElevated) {
            instanceData[offset + 2] = 0.94; // R
            instanceData[offset + 3] = 0.27; // G
            instanceData[offset + 4] = 0.27; // B
          } else if (t.anomalyScore && t.anomalyScore >= 60) {
            instanceData[offset + 2] = 0.98;
            instanceData[offset + 3] = 0.57;
            instanceData[offset + 4] = 0.24;
          } else if (t.isSelected) {
            instanceData[offset + 2] = 0.22;
            instanceData[offset + 3] = 0.74;
            instanceData[offset + 4] = 0.97;
          } else {
            instanceData[offset + 2] = 0.13;
            instanceData[offset + 3] = 0.77;
            instanceData[offset + 4] = 0.37;
          }
          instanceData[offset + 5] = 1.0; // Alpha
          instanceData[offset + 6] = t.heading ?? 0.0;
          instanceData[offset + 7] = t.isSelected ? 10.0 : 7.0;
          instanceData[offset + 8] = 0.0;
        }

        if (this.instanceBuffer) {
          this.instanceBuffer.destroy();
        }
        this.instanceBuffer = this.device.createBuffer({
          size: instanceData.byteLength,
          usage: ((window as any).GPUBufferUsage?.VERTEX || 0x20) | ((window as any).GPUBufferUsage?.COPY_DST || 0x08),
          mappedAtCreation: true,
        });
        new Float32Array(this.instanceBuffer.getMappedRange()).set(instanceData);
        this.instanceBuffer.unmap();
      }

      const commandEncoder = this.device.createCommandEncoder();
      const textureView = this.context.getCurrentTexture().createView();

      const renderPassDescriptor = {
        colorAttachments: [
          {
            view: textureView,
            clearValue: { r: 0.04, g: 0.07, b: 0.12, a: 1.0 },
            loadOp: 'clear',
            storeOp: 'store',
          },
        ],
      };

      const passEncoder = commandEncoder.beginRenderPass(renderPassDescriptor);
      passEncoder.setPipeline(this.pipeline);
      passEncoder.setBindGroup(0, this.uniformBindGroup);
      passEncoder.setVertexBuffer(0, this.vertexBuffer);

      if (trackCount > 0 && this.instanceBuffer) {
        passEncoder.setVertexBuffer(1, this.instanceBuffer);
        passEncoder.draw(6, trackCount, 0, 0);
      }

      passEncoder.end();
      this.device.queue.submit([commandEncoder.finish()]);
    } catch (err) {
      // On WebGPU draw failure, switch to Canvas fallback
      if (!this.fallbackRenderer && this.canvas) {
        this.fallbackRenderer = new CanvasRenderer();
        this.fallbackRenderer.initialize(this.canvas).then(() => {
          this.isUsingFallback = true;
          this.fallbackRenderer?.render(scene);
        });
      }
    }
  }

  destroy(): void {
    if (this.instanceBuffer) {
      this.instanceBuffer.destroy();
      this.instanceBuffer = null;
    }
    if (this.vertexBuffer) {
      this.vertexBuffer.destroy();
      this.vertexBuffer = null;
    }
    if (this.uniformBuffer) {
      this.uniformBuffer.destroy();
      this.uniformBuffer = null;
    }
    if (this.device) {
      this.device.destroy?.();
      this.device = null;
    }
    if (this.fallbackRenderer) {
      this.fallbackRenderer.destroy();
      this.fallbackRenderer = null;
    }
    super.destroy();
  }
}
