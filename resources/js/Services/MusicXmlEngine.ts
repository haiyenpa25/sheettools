/**
 * MusicXmlEngine — Bộ xử lý và thao tác DOM MusicXML nâng cao
 * Hỗ trợ: Live WYSIWYG, Transpose dịch giọng, Quản lý nhịp/tempo, Sửa nốt/lời/hợp âm, Undo/Redo, Sửa lỗi chính tả tiếng Việt.
 */

export interface ParsedLyric {
  id: string;
  partId: string;
  measureNumber: number;
  noteIndex: number;
  verseNumber: number;
  text: string;
  syllabic: string;
  rawOcr?: string;
  hasDiff?: boolean;
}

export interface ParsedHarmony {
  id: string;
  measureNumber: number;
  rootStep: string;
  rootAlter?: number;
  kindText: string;
  bassStep?: string;
  bassAlter?: number;
  displayText: string;
  beatOffset: number;
}

export interface ParsedNoteDetail {
  id: string;
  measureNumber: number;
  noteIndex: number;
  step: string;
  octave: number;
  accidental: string | null;
  duration: string;
  isRest: boolean;
  isDotted: boolean;
  tieType?: string | null;
  lyricText?: string;
  voice: number;
}

export class MusicXmlEngine {
  private doc: XMLDocument;
  private historyStack: string[] = [];
  private redoStack: string[] = [];
  private maxHistory: number = 40;

  constructor(xmlString: string) {
    this.doc = new DOMParser().parseFromString(xmlString, 'application/xml');
    this.autoFixVietnameseLyrics();
    this.saveState();
  }

  // ─── UNDO / REDO ───
  public saveState(): void {
    const current = this.getXmlString();
    if (this.historyStack.length > 0 && this.historyStack[this.historyStack.length - 1] === current) {
      return;
    }
    this.historyStack.push(current);
    if (this.historyStack.length > this.maxHistory) {
      this.historyStack.shift();
    }
    this.redoStack = [];
  }

  public undo(): boolean {
    if (this.historyStack.length <= 1) return false;
    const current = this.historyStack.pop()!;
    this.redoStack.push(current);
    const prev = this.historyStack[this.historyStack.length - 1];
    this.doc = new DOMParser().parseFromString(prev, 'application/xml');
    return true;
  }

  public redo(): boolean {
    if (this.redoStack.length === 0) return false;
    const next = this.redoStack.pop()!;
    this.historyStack.push(next);
    this.doc = new DOMParser().parseFromString(next, 'application/xml');
    return true;
  }

  public canUndo(): boolean {
    return this.historyStack.length > 1;
  }

  public canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  public getXmlString(): string {
    return new XMLSerializer().serializeToString(this.doc);
  }

  // ─── METADATA ───
  public extractMetadata(): { title: string; composer: string; lyricist: string; tempo: number; timeSig: string; keySig: string } {
    const title = this.doc.querySelector('work > work-title')?.textContent ||
                  this.doc.querySelector('movement-title')?.textContent || '001 Hỡi Thánh Vương, Kíp Ngự Lai';
    const composer = this.doc.querySelector('creator[type="composer"]')?.textContent || 'Felice de Giardini, 1769';
    const lyricist = this.doc.querySelector('creator[type="lyricist"]')?.textContent || 'Anon, 1757';

    // Tempo
    const tempoNode = this.doc.querySelector('sound[tempo]') || this.doc.querySelector('per-minute');
    const tempo = tempoNode ? parseInt(tempoNode.getAttribute('tempo') || tempoNode.textContent || '104', 10) : 104;

    // Time signature
    const beats = this.doc.querySelector('time > beats')?.textContent || '3';
    const beatType = this.doc.querySelector('time > beat-type')?.textContent || '4';

    // Key signature (fifths)
    const fifths = parseInt(this.doc.querySelector('key > fifths')?.textContent || '1', 10);
    const keyNames: Record<number, string> = {
      '-7': 'Cb Maj / Ab min', '-6': 'Gb Maj / Eb min', '-5': 'Db Maj / Bb min',
      '-4': 'Ab Maj / F min', '-3': 'Eb Maj / C min', '-2': 'Bb Maj / G min',
      '-1': 'F Maj / D min', '0': 'C Major', '1': 'G Major', '2': 'D Major',
      '3': 'A Major', '4': 'E Major', '5': 'B Major', '6': 'F# Major', '7': 'C# Major'
    };

    return {
      title,
      composer,
      lyricist,
      tempo,
      timeSig: `${beats}/${beatType}`,
      keySig: keyNames[fifths] || `${fifths} fifths`,
    };
  }

  public updateMetadata(title?: string, composer?: string, lyricist?: string, tempo?: number): void {
    if (title !== undefined) {
      let wt = this.doc.querySelector('work > work-title');
      if (!wt) {
        let work = this.doc.querySelector('work');
        if (!work) {
          work = this.doc.createElement('work');
          this.doc.documentElement.insertBefore(work, this.doc.documentElement.firstChild);
        }
        wt = this.doc.createElement('work-title');
        work.appendChild(wt);
      }
      wt.textContent = title;
    }

    if (composer !== undefined) {
      let comp = this.doc.querySelector('creator[type="composer"]');
      if (!comp) {
        let id = this.doc.querySelector('identification');
        if (!id) {
          id = this.doc.createElement('identification');
          this.doc.documentElement.insertBefore(id, this.doc.documentElement.firstChild);
        }
        comp = this.doc.createElement('creator');
        comp.setAttribute('type', 'composer');
        id.appendChild(comp);
      }
      comp.textContent = composer;
    }

    if (tempo !== undefined) {
      this.doc.querySelectorAll('sound').forEach(s => s.setAttribute('tempo', String(tempo)));
      const pm = this.doc.querySelector('per-minute');
      if (pm) pm.textContent = String(tempo);
    }

    this.saveState();
  }

  // ─── TRANSPOSE BY SEMITONES ───
  public transpose(semitones: number): void {
    if (semitones === 0) return;

    const notesCycle = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

    // Transpose all notes
    this.doc.querySelectorAll('note').forEach(note => {
      const pitch = note.querySelector('pitch');
      if (!pitch) return;

      const stepElem = pitch.querySelector('step');
      const alterElem = pitch.querySelector('alter');
      const octElem = pitch.querySelector('octave');

      if (!stepElem || !octElem) return;

      let step = stepElem.textContent || 'C';
      let alter = parseInt(alterElem?.textContent || '0', 10);
      let octave = parseInt(octElem.textContent || '4', 10);

      // Convert to midi note number
      let noteIndex = notesCycle.indexOf(step);
      if (alter === 1) noteIndex = (noteIndex + 1) % 12;
      else if (alter === -1) noteIndex = (noteIndex + 11) % 12;

      let midi = 12 * (octave + 1) + noteIndex + semitones;
      let newOctave = Math.floor(midi / 12) - 1;
      let newNoteIndex = ((midi % 12) + 12) % 12;

      let noteName = notesCycle[newNoteIndex];
      let newStep = noteName[0];
      let newAlter = noteName.length > 1 ? 1 : 0;

      stepElem.textContent = newStep;
      octElem.textContent = String(newOctave);

      if (newAlter !== 0) {
        if (!alterElem) {
          const a = this.doc.createElement('alter');
          a.textContent = String(newAlter);
          pitch.appendChild(a);
        } else {
          alterElem.textContent = String(newAlter);
        }
      } else if (alterElem) {
        alterElem.remove();
      }
    });

    // Transpose all harmony chords
    this.doc.querySelectorAll('harmony').forEach(h => {
      const rootStepElem = h.querySelector('root > root-step');
      const rootAlterElem = h.querySelector('root > root-alter');
      if (rootStepElem) {
        let step = rootStepElem.textContent || 'C';
        let alter = parseInt(rootAlterElem?.textContent || '0', 10);
        let noteIndex = notesCycle.indexOf(step);
        if (alter === 1) noteIndex = (noteIndex + 1) % 12;
        else if (alter === -1) noteIndex = (noteIndex + 11) % 12;

        let newNoteIndex = ((noteIndex + semitones) % 12 + 12) % 12;
        let noteName = notesCycle[newNoteIndex];
        rootStepElem.textContent = noteName[0];
        if (noteName.length > 1) {
          if (!rootAlterElem) {
            const a = this.doc.createElement('root-alter');
            a.textContent = '1';
            h.querySelector('root')?.appendChild(a);
          } else {
            rootAlterElem.textContent = '1';
          }
        } else if (rootAlterElem) {
          rootAlterElem.remove();
        }
      }

      // Transpose bass step if any
      const bassStepElem = h.querySelector('bass > bass-step');
      const bassAlterElem = h.querySelector('bass > bass-alter');
      if (bassStepElem) {
        let step = bassStepElem.textContent || 'C';
        let alter = parseInt(bassAlterElem?.textContent || '0', 10);
        let noteIndex = notesCycle.indexOf(step);
        if (alter === 1) noteIndex = (noteIndex + 1) % 12;
        else if (alter === -1) noteIndex = (noteIndex + 11) % 12;

        let newNoteIndex = ((noteIndex + semitones) % 12 + 12) % 12;
        let noteName = notesCycle[newNoteIndex];
        bassStepElem.textContent = noteName[0];
        if (noteName.length > 1) {
          if (!bassAlterElem) {
            const a = this.doc.createElement('bass-alter');
            a.textContent = '1';
            h.querySelector('bass')?.appendChild(a);
          } else {
            bassAlterElem.textContent = '1';
          }
        } else if (bassAlterElem) {
          bassAlterElem.remove();
        }
      }
    });

    this.saveState();
  }

  // ─── AUTO-FIX VIETNAMESE DIACRITICS ───
  public autoFixVietnameseLyrics(): number {
    let fixedCount = 0;
    const dictionary: Record<string, string> = {
      // 1. Tiêu đề và tác giả
      'TU cfil LbNG sAU': 'Từ Cõi Lòng Sâu Thẳm',
      'TU cﬁl LbNG sAU': 'Từ Cõi Lòng Sâu Thẳm',
      'TU COI LONG SAU THAM': 'Từ Cõi Lòng Sâu Thẳm',
      'Dinh Thén': 'Nguyễn Đình Tiến',
      'Nguyen Dinh Thon': 'Nguyễn Đình Tiến',
      'Ton Vinh Chua Hang Htu': 'Tôn Vinh Chúa Hằng Hữu',

      // 2. Các từ và cụm từ biến dạng do OCR
      'cfil': 'cõi', 'cﬁl': 'cõi', 'cﬁi': 'cõi', 'cﬂi': 'cõi', 'coi': 'cõi', 'Coi': 'Cõi',
      'LbNG': 'lòng', 'lbng': 'lòng', 'lc\'mg': 'lòng', 'lc’mg': 'lòng', 'lc‘mg': 'lòng',
      'Ic\'mg': 'lòng', 'Ic’mg': 'lòng', 'Ic‘mg': 'lòng', 'lﬂng': 'lòng', 'long': 'lòng', 'Long': 'Lòng',
      'sAU': 'sâu', 'sau': 'sâu', 'Sau': 'Sâu', 'sﬁu': 'sâu',
      'tham,': 'thẳm,', 'tham': 'thẳm', 'Tham': 'Thẳm', 'thﬁm': 'thẳm',
      'dé\'y': 'đầy', 'dé’y': 'đầy', 'day': 'đầy', 'Day': 'Đầy', 'day vinh': 'đầy vinh',
      'diên': 'diện', 'dien': 'diện', 'dién': 'diện', 'Dien': 'Diện',
      'hiê\'n': 'hiển', 'hiê’n': 'hiển', 'hié\'n': 'hiển', 'hié’n': 'hiển', 'hien': 'hiện', 'hién': 'hiện',
      'nay.': 'này.', 'nay': 'này',
      'LUi': 'Lời', 'Lui': 'Lời', 'loi': 'lời', 'Loi': 'Lời',
      'nguyén': 'nguyện', 'nguyen': 'nguyện', 'Nguyen': 'Nguyện',
      'cé‘u': 'cầu', 'cé\'u': 'cầu', 'cè‘u': 'cầu', 'cè\'u': 'cầu', 'cau': 'cầu', 'Cau': 'Cầu',
      'thié’t': 'thiết', 'thié\'t': 'thiết', 'thiê’t': 'thiết', 'thiê\'t': 'thiết', 'thiet': 'thiết',
      'vc\'ii': 'với', 'vc’ii': 'với', 'vc\'ll': 'với', 'vc’ll': 'với', 'vc’Ji': 'với', 'vc\'Ji': 'với', 'v6i': 'với', 'voi': 'với', 'tvoi': 'với',
      't‘mh': 'tình', 't’mh': 'tình', 't\'mh': 'tình', 'tinh': 'tình',
      'yéu.': 'yêu.', 'yêu.': 'yêu.', 'yéu': 'yêu', 'yeu.': 'yêu.', 'yeu': 'yêu',
      'Chﬂa!': 'Chúa!', 'ChL\'la': 'Chúa!', 'ChL’la': 'Chúa!', 'Ch!a!': 'Chúa!', 'Chua!': 'Chúa!', 'chua': 'Chúa', 'Chua': 'Chúa',
      'Chl’mg': 'Chúng', 'Chl\'mg': 'Chúng', 'Ch!\'mg': 'Chúng', 'Ch!’mg': 'Chúng', 'Chung': 'Chúng', 'chung': 'chúng',
      'khé’n': 'khiến', 'khé\'n': 'khiến', 'khê’n': 'khiến', 'khê\'n': 'khiến', 'khien': 'khiến',
      'khan': 'khẩn',
      'Ngéi': 'Ngài', 'Ngái': 'Ngài', 'Ngai': 'Ngài', 'ngai': 'ngài',
      'dé\'n': 'đến', 'dé’n': 'đến', 'de\'n': 'đến', 'de’n': 'đến', 'dn': 'đến', 'den': 'đến',
      'sb\'ng': 'sống', 'sb’ng': 'sống', 'song': 'sống',
      'nu\'c': 'nước', 'nu’c': 'nước', 'nuoc': 'nước', 'nuﬁc': 'nước', 'nuﬂc': 'nước',
      'tuon': 'tuôn', 'Tuon': 'Tuôn', 'moi': 'mới', 'Moi': 'Mới', 'moi.': 'mới.', 'tuoi': 'tươi', 'Tuoi': 'Tươi', 'tuéi': 'tươi',
      'Than': 'Thần', 'than': 'thần', 'Linh': 'Linh', 'linh': 'linh', 'Iinh': 'linh',
      'Lay': 'Lạy', 'lay': 'lạy', 'Cha': 'Cha', 'Cha.': 'Cha.',
      'dua': 'đưa', 'hon': 'hồn', 'h6n': 'hồn', 'cho': 'cho', 'hiep': 'hiệp', 'hiép': 'hiệp',
      'nhat,': 'nhất,', 'nhat': 'nhất', 'nhé’t,': 'nhất,', 'nhé\'t,': 'nhất,', 'nhé’t': 'nhất', 'nhé\'t': 'nhất',
      'tam': 'tấm', 'Tam': 'Tấm', 'té’m': 'tấm', 'té\'m': 'tấm',
      'vo': 'vô', 'Vo': 'Vô', 'v6': 'vô', 'H6i': 'Hỡi', 'h6i': 'hỡi', 'm6i': 'mọi',
      'tan,': 'tận,', 'tan': 'tận', 'biet': 'biết', 'on.': 'ơn.', 'on': 'ơn', 'On': 'Ơn',
      'métchﬂng': 'mát chúng', 'mét': 'mát',
      'Hơi': 'Hỡi', 'Hoi': 'Hỡi', 'hoi': 'hỡi', 'hơi': 'hỡi',
      'Thanh': 'Thánh', 'thanh': 'thánh', 'Vuong': 'Vương', 'vuong': 'vương',
      'ngu': 'ngự', 'ngư': 'ngự', 'kip': 'kíp', 'lai': 'lai',
      'Dâng': 'Đấng', 'Dang': 'Đấng', 'dang': 'đấng',
      'tron': 'trọn', 'Tron': 'Trọn', 'ca': 'cả', 'Ca': 'Cả',
      'ton': 'tôn', 'Ton': 'Tôn', 'Chan': 'Chân', 'chan': 'chân', 'nguon': 'nguồn', 'Nguon': 'Nguồn',
      'doi': 'đối', 'Doi': 'Đối', 'khap': 'khắp', 'Khap': 'Khắp', 'noi': 'nơi', 'Noi': 'Nơi',
      'chuc': 'chúc', 'Chuc': 'Chúc', 'tung': 'tụng', 'Tung': 'Tụng', 'cuu': 'cứu', 'Cuu': 'Cứu',
      'roi': 'rỗi', 'Roi': 'Rỗi', 'chua chan': 'chứa chan',
    };

    // Sửa Tiêu đề & Credit words
    this.doc.querySelectorAll('movement-title, work-title, credit-words').forEach(el => {
      const txt = el.textContent?.trim() || '';
      if (dictionary[txt]) {
        el.textContent = dictionary[txt];
        fixedCount++;
      }
    });

    // Sửa toàn bộ Lyrics text
    this.doc.querySelectorAll('lyric > text').forEach(textNode => {
      const original = textNode.textContent?.trim() || '';
      if (dictionary[original]) {
        textNode.textContent = dictionary[original];
        fixedCount++;
      } else {
        const cleaned = original.replace(/[|_]/g, '').trim();
        if (dictionary[cleaned]) {
          textNode.textContent = dictionary[cleaned];
          fixedCount++;
        } else {
          const lower = cleaned.toLowerCase();
          if (dictionary[lower]) {
            const match = dictionary[lower];
            textNode.textContent = (cleaned[0] === cleaned[0].toUpperCase()) ? (match[0].toUpperCase() + match.slice(1)) : match;
            fixedCount++;
          }
        }
      }
    });

    if (fixedCount > 0) this.saveState();
    return fixedCount;
  }

  // ─── LYRICS ───
  public extractLyrics(): Record<number, ParsedLyric[]> {
    const result: Record<number, ParsedLyric[]> = {};

    this.doc.querySelectorAll('part').forEach(part => {
      const partId = part.getAttribute('id') || 'P1';
      part.querySelectorAll('measure').forEach(measure => {
        const mNum = parseInt(measure.getAttribute('number') || '1', 10);
        let noteIndex = 0;

        measure.querySelectorAll('note').forEach(note => {
          if (note.querySelector('rest')) return;
          noteIndex++;

          note.querySelectorAll('lyric').forEach(lyric => {
            const verse = parseInt(lyric.getAttribute('number') || '1', 10);
            const text = lyric.querySelector('text')?.textContent || '';
            const syllabic = lyric.querySelector('syllabic')?.textContent || 'single';

            if (!result[verse]) result[verse] = [];

            result[verse].push({
              id: `lyr_${partId}_m${mNum}_n${noteIndex}_v${verse}`,
              partId,
              measureNumber: mNum,
              noteIndex,
              verseNumber: verse,
              text,
              syllabic,
              rawOcr: text,
              hasDiff: false,
            });
          });
        });
      });
    });

    return result;
  }

  public updateLyricText(verseNumber: number, measureNumber: number, noteIndex: number, newText: string): boolean {
    let found = false;
    this.doc.querySelectorAll('part').forEach(part => {
      part.querySelectorAll('measure').forEach(measure => {
        const mNum = parseInt(measure.getAttribute('number') || '1', 10);
        if (mNum !== measureNumber) return;

        let curNoteIdx = 0;
        measure.querySelectorAll('note').forEach(note => {
          if (note.querySelector('rest')) return;
          curNoteIdx++;
          if (curNoteIdx !== noteIndex) return;

          note.querySelectorAll('lyric').forEach(lyric => {
            const v = parseInt(lyric.getAttribute('number') || '1', 10);
            if (v === verseNumber) {
              const textNode = lyric.querySelector('text');
              if (textNode) {
                textNode.textContent = newText;
                found = true;
              }
            }
          });

          if (!found) {
            const lyricElem = this.doc.createElement('lyric');
            lyricElem.setAttribute('number', String(verseNumber));
            const syllabicElem = this.doc.createElement('syllabic');
            syllabicElem.textContent = 'single';
            const textElem = this.doc.createElement('text');
            textElem.textContent = newText;
            lyricElem.appendChild(syllabicElem);
            lyricElem.appendChild(textElem);
            note.appendChild(lyricElem);
            found = true;
          }
        });
      });
    });

    if (found) this.saveState();
    return found;
  }

  // ─── HARMONIES ───
  public extractHarmonies(): ParsedHarmony[] {
    const result: ParsedHarmony[] = [];
    let idx = 0;

    this.doc.querySelectorAll('measure').forEach(measure => {
      const mNum = parseInt(measure.getAttribute('number') || '1', 10);

      measure.querySelectorAll('harmony').forEach(h => {
        idx++;
        const rootStep = h.querySelector('root > root-step')?.textContent || 'C';
        const rootAlter = parseInt(h.querySelector('root > root-alter')?.textContent || '0', 10);
        const kindElem = h.querySelector('kind');
        const kindText = kindElem?.getAttribute('text') || kindElem?.textContent || '';
        const bassStep = h.querySelector('bass > bass-step')?.textContent || '';
        const bassAlter = parseInt(h.querySelector('bass > bass-alter')?.textContent || '0', 10);

        let display = rootStep;
        if (rootAlter === 1) display += '♯';
        if (rootAlter === -1) display += '♭';
        if (kindText && kindText !== 'major') display += kindText;
        if (bassStep) {
          display += '/' + bassStep;
          if (bassAlter === 1) display += '♯';
          if (bassAlter === -1) display += '♭';
        }

        result.push({
          id: `h_${idx}`,
          measureNumber: mNum,
          rootStep,
          rootAlter,
          kindText,
          bassStep: bassStep || undefined,
          bassAlter: bassAlter || undefined,
          displayText: display,
          beatOffset: 0,
        });
      });
    });

    return result;
  }

  public addOrUpdateHarmony(measureNumber: number, chordString: string): boolean {
    const measure = Array.from(this.doc.querySelectorAll('measure')).find(
      m => parseInt(m.getAttribute('number') || '1', 10) === measureNumber
    );
    if (!measure) return false;

    const match = chordString.trim().match(/^([A-Ga-g])([#♯b♭]?)(.*?)(?:\/([A-Ga-g])([#♯b♭]?))?$/);
    if (!match) return false;

    const rootStep = match[1].toUpperCase();
    const rootAcc = match[2] === '#' || match[2] === '♯' ? 1 : match[2] === 'b' || match[2] === '♭' ? -1 : 0;
    const kind = match[3] || 'major';
    const bassStep = match[4] ? match[4].toUpperCase() : null;
    const bassAcc = match[5] === '#' || match[5] === '♯' ? 1 : match[5] === 'b' || match[5] === '♭' ? -1 : 0;

    const harmElem = this.doc.createElement('harmony');

    const rootElem = this.doc.createElement('root');
    const rootStepElem = this.doc.createElement('root-step');
    rootStepElem.textContent = rootStep;
    rootElem.appendChild(rootStepElem);
    if (rootAcc !== 0) {
      const rootAlterElem = this.doc.createElement('root-alter');
      rootAlterElem.textContent = String(rootAcc);
      rootElem.appendChild(rootAlterElem);
    }
    harmElem.appendChild(rootElem);

    const kindElem = this.doc.createElement('kind');
    kindElem.textContent = kind === 'm' || kind.startsWith('min') ? 'minor' : kind.startsWith('7') ? 'dominant' : 'major';
    kindElem.setAttribute('text', kind);
    harmElem.appendChild(kindElem);

    if (bassStep) {
      const bassElem = this.doc.createElement('bass');
      const bassStepElem = this.doc.createElement('bass-step');
      bassStepElem.textContent = bassStep;
      bassElem.appendChild(bassStepElem);
      if (bassAcc !== 0) {
        const bassAlterElem = this.doc.createElement('bass-alter');
        bassAlterElem.textContent = String(bassAcc);
        bassElem.appendChild(bassAlterElem);
      }
      harmElem.appendChild(bassElem);
    }

    const firstNote = measure.querySelector('note');
    if (firstNote) {
      measure.insertBefore(harmElem, firstNote);
    } else {
      measure.appendChild(harmElem);
    }

    this.saveState();
    return true;
  }

  public removeHarmony(measureNumber: number, chordIndex: number): boolean {
    const measure = Array.from(this.doc.querySelectorAll('measure')).find(
      m => parseInt(m.getAttribute('number') || '1', 10) === measureNumber
    );
    if (!measure) return false;

    const harms = measure.querySelectorAll('harmony');
    if (harms[chordIndex]) {
      harms[chordIndex].remove();
      this.saveState();
      return true;
    }
    return false;
  }

  // ─── NOTES DETAIL & QUICK EDIT ───
  public getNotesInMeasure(measureNumber: number): ParsedNoteDetail[] {
    const measure = Array.from(this.doc.querySelectorAll('measure')).find(
      m => parseInt(m.getAttribute('number') || '1', 10) === measureNumber
    );
    if (!measure) return [];

    const result: ParsedNoteDetail[] = [];
    let noteIdx = 0;

    measure.querySelectorAll('note').forEach(n => {
      noteIdx++;
      const isRest = !!n.querySelector('rest');
      const step = n.querySelector('pitch > step')?.textContent || 'G';
      const octave = parseInt(n.querySelector('pitch > octave')?.textContent || '4', 10);
      const acc = n.querySelector('accidental')?.textContent || (n.querySelector('alter')?.textContent === '1' ? 'sharp' : (n.querySelector('alter')?.textContent === '-1' ? 'flat' : null));
      const duration = n.querySelector('type')?.textContent || 'quarter';
      const isDotted = !!n.querySelector('dot');
      const voice = parseInt(n.querySelector('voice')?.textContent || '1', 10);
      const lyricText = n.querySelector('lyric > text')?.textContent || undefined;

      result.push({
        id: `note_m${measureNumber}_n${noteIdx}`,
        measureNumber,
        noteIndex: noteIdx,
        step,
        octave,
        accidental: acc,
        duration,
        isRest,
        isDotted,
        voice,
        lyricText,
      });
    });

    return result;
  }

  public updateNoteDetail(
    measureNumber: number,
    noteIndex: number,
    step: string,
    octave: number,
    accidental: string | null,
    duration: string,
    isDotted: boolean = false,
    isRest: boolean = false
  ): boolean {
    const measure = Array.from(this.doc.querySelectorAll('measure')).find(
      m => parseInt(m.getAttribute('number') || '1', 10) === measureNumber
    );
    if (!measure) return false;

    const notes = Array.from(measure.querySelectorAll('note'));
    const targetNote = notes[noteIndex - 1] || notes[0];
    if (!targetNote) return false;

    if (isRest) {
      if (!targetNote.querySelector('rest')) {
        const restElem = this.doc.createElement('rest');
        targetNote.insertBefore(restElem, targetNote.firstChild);
      }
      const pitch = targetNote.querySelector('pitch');
      if (pitch) pitch.remove();
    } else {
      const rest = targetNote.querySelector('rest');
      if (rest) rest.remove();

      let pitchElem = targetNote.querySelector('pitch');
      if (!pitchElem) {
        pitchElem = this.doc.createElement('pitch');
        targetNote.insertBefore(pitchElem, targetNote.firstChild);
      }

      let stepElem = pitchElem.querySelector('step');
      if (!stepElem) { stepElem = this.doc.createElement('step'); pitchElem.appendChild(stepElem); }
      stepElem.textContent = step.toUpperCase();

      let octElem = pitchElem.querySelector('octave');
      if (!octElem) { octElem = this.doc.createElement('octave'); pitchElem.appendChild(octElem); }
      octElem.textContent = String(octave);

      let alterElem = pitchElem.querySelector('alter');
      let accElem = targetNote.querySelector('accidental');

      if (accidental === 'sharp') {
        if (!alterElem) { alterElem = this.doc.createElement('alter'); pitchElem.appendChild(alterElem); }
        alterElem.textContent = '1';
        if (!accElem) { accElem = this.doc.createElement('accidental'); targetNote.appendChild(accElem); }
        accElem.textContent = 'sharp';
      } else if (accidental === 'flat') {
        if (!alterElem) { alterElem = this.doc.createElement('alter'); pitchElem.appendChild(alterElem); }
        alterElem.textContent = '-1';
        if (!accElem) { accElem = this.doc.createElement('accidental'); targetNote.appendChild(accElem); }
        accElem.textContent = 'flat';
      } else {
        if (alterElem) alterElem.remove();
        if (accElem) accElem.remove();
      }
    }

    // Duration Type
    let typeElem = targetNote.querySelector('type');
    if (!typeElem) {
      typeElem = this.doc.createElement('type');
      targetNote.appendChild(typeElem);
    }
    typeElem.textContent = duration;

    // Dotted
    const dotElem = targetNote.querySelector('dot');
    if (isDotted && !dotElem) {
      targetNote.appendChild(this.doc.createElement('dot'));
    } else if (!isDotted && dotElem) {
      dotElem.remove();
    }

    this.saveState();
    return true;
  }

  // ─── BULK LYRIC DISTRIBUTOR ───
  public distributeBulkLyrics(verseNumber: number, fullText: string): boolean {
    if (!fullText || fullText.trim() === '') return false;

    // Tokenize text into words/syllables
    const syllables = fullText.trim().split(/\s+/);
    if (syllables.length === 0) return false;

    let sylIdx = 0;
    let modified = false;

    this.doc.querySelectorAll('part').forEach(part => {
      part.querySelectorAll('measure').forEach(measure => {
        measure.querySelectorAll('note').forEach(note => {
          if (note.querySelector('rest')) return;
          if (sylIdx >= syllables.length) return;

          const currentSyl = syllables[sylIdx];
          let lyricElem: Element | null = null;

          note.querySelectorAll('lyric').forEach(l => {
            if (parseInt(l.getAttribute('number') || '1', 10) === verseNumber) {
              lyricElem = l;
            }
          });

          if (!lyricElem) {
            lyricElem = this.doc.createElement('lyric');
            lyricElem.setAttribute('number', String(verseNumber));
            const syllabicElem = this.doc.createElement('syllabic');
            syllabicElem.textContent = 'single';
            const textElem = this.doc.createElement('text');
            textElem.textContent = currentSyl;
            lyricElem.appendChild(syllabicElem);
            lyricElem.appendChild(textElem);
            note.appendChild(lyricElem);
          } else {
            const textElem = lyricElem.querySelector('text');
            if (textElem) {
              textElem.textContent = currentSyl;
            }
          }

          sylIdx++;
          modified = true;
        });
      });
    });

    if (modified) this.saveState();
    return modified;
  }
}

