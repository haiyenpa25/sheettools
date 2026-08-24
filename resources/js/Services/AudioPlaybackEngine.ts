/**
 * AudioPlaybackEngine — Web Audio API Synthesizer đa âm sắc & Metronome
 * Hỗ trợ Piano, Strings Choir, Church Organ, Máy đếm nhịp Metronome và Seek theo ô nhịp.
 */

export interface NoteEvent {
  measureNumber: number;
  pitch: string;
  durationBeats: number;
  frequency: number;
}

export interface HarmonyEvent {
  measureNumber: number;
  chordName: string;
  frequencies: number[];
}

export class AudioPlaybackEngine {
  private ctx: AudioContext | null = null;
  private isPlaying: boolean = false;
  private isLooping: boolean = false;
  private isMetronomeActive: boolean = false;
  private soundType: 'piano' | 'choir' | 'organ' = 'piano';
  private tempoBpm: number = 84;
  private currentMeasure: number = 1;
  private timerId: any = null;
  private onMeasureChangeCallback?: (measure: number) => void;
  private onStateChangeCallback?: (isPlaying: boolean) => void;

  private noteSequence: NoteEvent[] = [];
  private harmonySequence: HarmonyEvent[] = [];
  private currentStepIndex: number = 0;

  constructor() {
    this.initDefaultSequence();
  }

  public setTempo(bpm: number): void {
    this.tempoBpm = Math.max(40, Math.min(240, bpm));
  }

  public getTempo(): number {
    return this.tempoBpm;
  }

  public setLoop(loop: boolean): void {
    this.isLooping = loop;
  }

  public getIsLooping(): boolean {
    return this.isLooping;
  }

  public setMetronome(active: boolean): void {
    this.isMetronomeActive = active;
  }

  public getIsMetronomeActive(): boolean {
    return this.isMetronomeActive;
  }

  public setSoundType(type: 'piano' | 'choir' | 'organ'): void {
    this.soundType = type;
  }

  public getSoundType(): string {
    return this.soundType;
  }

  public onMeasureChange(cb: (measure: number) => void): void {
    this.onMeasureChangeCallback = cb;
  }

  public onStateChange(cb: (isPlaying: boolean) => void): void {
    this.onStateChangeCallback = cb;
  }

  public pitchToFreq(step: string, octave: number, alter: number = 0): number {
    const baseFreqs: Record<string, number> = {
      'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23,
      'G': 392.00, 'A': 440.00, 'B': 493.88
    };
    let freq = baseFreqs[step.toUpperCase()] || 440.0;
    freq = freq * Math.pow(2, octave - 4);
    if (alter !== 0) {
      freq = freq * Math.pow(2, alter / 12);
    }
    return freq;
  }

  public chordToFreqs(root: string, kind: string = 'major', bass?: string): number[] {
    const rootFreq = this.pitchToFreq(root, 4);
    const semitone = Math.pow(2, 1 / 12);
    const freqs: number[] = [rootFreq];

    if (kind.includes('minor') || kind === 'm' || kind.startsWith('min')) {
      freqs.push(rootFreq * Math.pow(semitone, 3));
      freqs.push(rootFreq * Math.pow(semitone, 7));
    } else if (kind.includes('dim')) {
      freqs.push(rootFreq * Math.pow(semitone, 3));
      freqs.push(rootFreq * Math.pow(semitone, 6));
    } else {
      freqs.push(rootFreq * Math.pow(semitone, 4));
      freqs.push(rootFreq * Math.pow(semitone, 7));
    }

    if (kind.includes('7')) {
      freqs.push(rootFreq * Math.pow(semitone, 10));
    }

    if (bass) {
      freqs.push(this.pitchToFreq(bass, 3));
    } else {
      freqs.push(this.pitchToFreq(root, 3));
    }

    return freqs;
  }

  public loadFromNotes(notes: { measure: number; step: string; octave: number; alter?: number; duration: string }[]): void {
    if (!notes || notes.length === 0) return;
    this.noteSequence = notes.map(n => {
      let beats = 1;
      if (n.duration === 'half') beats = 2;
      else if (n.duration === 'whole') beats = 4;
      else if (n.duration === 'eighth') beats = 0.5;
      else if (n.duration === '16th') beats = 0.25;

      return {
        measureNumber: n.measure,
        pitch: `${n.step}${n.alter ? (n.alter > 0 ? '#' : 'b') : ''}${n.octave}`,
        durationBeats: beats,
        frequency: this.pitchToFreq(n.step, n.octave, n.alter || 0),
      };
    });
  }

  private initDefaultSequence(): void {
    // Default sequence for "Từ cõi lòng sâu thẳm" (2/4 time)
    const melody = [
      { m: 1, step: 'B', oct: 4, alt: 0, beats: 0.5 }, { m: 1, step: 'B', oct: 4, alt: 0, beats: 0.5 },
      { m: 2, step: 'A', oct: 4, alt: 0, beats: 0.5 }, { m: 2, step: 'B', oct: 4, alt: 0, beats: 0.5 },
      { m: 3, step: 'G', oct: 4, alt: 0, beats: 1.0 },
      { m: 4, step: 'F', oct: 4, alt: 1, beats: 0.5 }, { m: 4, step: 'G', oct: 4, alt: 0, beats: 0.5 },
      { m: 5, step: 'A', oct: 4, alt: 0, beats: 0.5 }, { m: 5, step: 'A', oct: 4, alt: 0, beats: 0.5 },
      { m: 6, step: 'B', oct: 4, alt: 0, beats: 1.0 },
      { m: 7, step: 'G', oct: 4, alt: 0, beats: 0.5 }, { m: 7, step: 'A', oct: 4, alt: 0, beats: 0.5 },
      { m: 8, step: 'B', oct: 4, alt: 0, beats: 0.5 }, { m: 8, step: 'B', oct: 4, alt: 0, beats: 0.5 },
      { m: 9, step: 'B', oct: 4, alt: 0, beats: 0.5 }, { m: 9, step: 'A', oct: 4, alt: 0, beats: 0.5 },
      { m: 10, step: 'G', oct: 4, alt: 0, beats: 1.0 },
      { m: 11, step: 'E', oct: 4, alt: 0, beats: 2.0 },
    ];

    this.noteSequence = melody.map(item => ({
      measureNumber: item.m,
      pitch: `${item.step}${item.alt ? '#' : ''}${item.oct}`,
      durationBeats: item.beats,
      frequency: this.pitchToFreq(item.step, item.oct, item.alt),
    }));

    this.harmonySequence = [
      { measureNumber: 1, chordName: 'Em', frequencies: this.chordToFreqs('E', 'minor') },
      { measureNumber: 2, chordName: 'D', frequencies: this.chordToFreqs('D', 'major') },
      { measureNumber: 7, chordName: 'C', frequencies: this.chordToFreqs('C', 'major') },
      { measureNumber: 9, chordName: 'G', frequencies: this.chordToFreqs('G', 'major') },
      { measureNumber: 11, chordName: 'F#m7', frequencies: this.chordToFreqs('F', 'minor') },
    ];
  }

  public play(): void {
    if (this.isPlaying) return;
    this.isPlaying = true;
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    this.onStateChangeCallback?.(true);
    this.step();
  }

  public pause(): void {
    this.isPlaying = false;
    clearTimeout(this.timerId);
    this.onStateChangeCallback?.(false);
  }

  public stop(): void {
    this.pause();
    this.currentStepIndex = 0;
    this.currentMeasure = 1;
    this.onMeasureChangeCallback?.(1);
  }

  public toggle(): void {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  public seekToMeasure(measure: number): void {
    const idx = this.noteSequence.findIndex(n => n.measureNumber >= measure);
    if (idx !== -1) {
      this.currentStepIndex = idx;
      this.currentMeasure = this.noteSequence[idx].measureNumber;
      this.onMeasureChangeCallback?.(this.currentMeasure);
    }
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }

  private step(): void {
    if (!this.isPlaying || !this.ctx) return;

    if (this.currentStepIndex >= this.noteSequence.length) {
      if (this.isLooping) {
        this.currentStepIndex = 0;
      } else {
        this.stop();
        return;
      }
    }

    const note = this.noteSequence[this.currentStepIndex];
    const prevMeasure = this.currentMeasure;
    this.currentMeasure = note.measureNumber;

    // Trigger measure change
    if (this.currentMeasure !== prevMeasure || this.currentStepIndex === 0) {
      this.onMeasureChangeCallback?.(this.currentMeasure);

      if (this.isMetronomeActive) {
        this.playMetronomeClick(true);
      }

      // Play harmony chord pad on measure boundary
      const harm = this.harmonySequence.find(h => h.measureNumber === this.currentMeasure);
      if (harm) {
        this.playChord(harm.frequencies, (60 / this.tempoBpm) * 2.0);
      }
    }

    // Play melody note with selected sound type
    const durationSeconds = (note.durationBeats * 60) / this.tempoBpm;
    this.playTone(note.frequency, durationSeconds * 0.95);

    this.currentStepIndex++;
    this.timerId = setTimeout(() => {
      this.step();
    }, durationSeconds * 1000);
  }

  public playTone(freq: number, duration: number): void {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    if (this.soundType === 'organ') {
      osc.type = 'sawtooth';
      gain.gain.setValueAtTime(0.001, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.18, this.ctx.currentTime + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
    } else if (this.soundType === 'choir') {
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.001, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.22, this.ctx.currentTime + 0.08);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
    } else {
      // Grand Piano
      osc.type = 'triangle';
      gain.gain.setValueAtTime(0.001, this.ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.28, this.ctx.currentTime + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
    }

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start();
    osc.stop(this.ctx.currentTime + duration);
  }

  public playMetronomeClick(isDownbeat: boolean = true): void {
    if (!this.ctx) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(isDownbeat ? 1200 : 800, this.ctx.currentTime);

    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 0.04);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start();
    osc.stop(this.ctx.currentTime + 0.04);
  }

  public playChord(frequencies: number[], duration: number): void {
    if (!this.ctx) return;

    frequencies.forEach(freq => {
      const osc = this.ctx!.createOscillator();
      const gain = this.ctx!.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, this.ctx!.currentTime);

      gain.gain.setValueAtTime(0.001, this.ctx!.currentTime);
      gain.gain.linearRampToValueAtTime(0.06, this.ctx!.currentTime + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx!.currentTime + duration);

      osc.connect(gain);
      gain.connect(this.ctx!.destination);

      osc.start();
      osc.stop(this.ctx!.currentTime + duration);
    });
  }
}
