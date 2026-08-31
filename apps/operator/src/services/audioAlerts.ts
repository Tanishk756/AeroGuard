/**
 * AeroGuard Tactical Acoustic Alert Synthesizer Engine.
 *
 * Uses Web Audio API to generate deterministic, low-latency alert tone patterns for
 * CRITICAL threat escalation events. Supports operator mute, volume control, and event deduplication.
 */

class AcousticAlertEngine {
  private audioCtx: AudioContext | null = null;
  private muted: boolean = false;
  private acknowledgedAlerts: Set<str> = new Set();
  private lastAlertTime: number = 0;

  private getContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  public isMuted(): boolean {
    return this.muted;
  }

  public mute(): void {
    this.muted = true;
  }

  public unmute(): void {
    this.muted = false;
  }

  public acknowledgeAlert(alertId: string): void {
    this.acknowledgedAlerts.add(alertId);
  }

  public isAcknowledged(alertId: string): boolean {
    return this.acknowledgedAlerts.has(alertId);
  }

  public playCriticalAlert(alertId?: string): boolean {
    if (this.muted) return false;
    if (alertId && this.acknowledgedAlerts.has(alertId)) return false;

    const now = Date.now();
    // Deduplicate event storms within 500ms
    if (now - this.lastAlertTime < 500) return false;
    this.lastAlertTime = now;

    const ctx = this.getContext();
    if (!ctx) return false;

    try {
      // Synthesize dual-tone tactical alert beep (880Hz / 1760Hz pulse)
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.setValueAtTime(1760, ctx.currentTime + 0.1);

      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.25);
      return true;
    } catch {
      return false;
    }
  }
}

type str = string;

export const audioAlertEngine = new AcousticAlertEngine();
