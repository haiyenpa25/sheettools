<template>
  <div class="flex-1 flex flex-col min-w-0 bg-workspace-bg overflow-hidden h-full">
    <!-- ════════════════════════════════ TOP ADVANCED TOOLBAR ════════════════════════════════ -->
    <div class="h-13 bg-surface-container-lowest border-b border-border-subtle flex items-center justify-between px-4 shrink-0 select-none gap-3 flex-wrap">
      <!-- Left: Project title & Quick Info -->
      <div class="flex items-center gap-2.5 min-w-0">
        <button
          @click="showMetadataModal = true"
          class="font-label-sm text-xs text-on-surface-variant hover:text-primary bg-surface-container hover:bg-surface-container-high px-2.5 py-1.5 rounded font-medium truncate flex items-center gap-1.5 transition-colors"
          title="Bấm để sửa tiêu đề & tác giả"
        >
          <span class="font-bold text-on-surface truncate">{{ meta.title }}</span>
          <span class="text-[10px] text-secondary">({{ meta.keySig }} • {{ meta.timeSig }})</span>
          <span class="material-symbols-outlined text-xs text-secondary">edit</span>
        </button>

        <!-- View Mode Switcher (Split / Full Score / Full Source) -->
        <div class="flex items-center bg-surface-container-low border border-border-subtle rounded p-0.5 text-xs">
          <button
            @click="layoutMode = 'split'"
            class="px-2 py-1 rounded font-medium transition-colors"
            :class="layoutMode === 'split' ? 'bg-surface-container-lowest font-bold text-primary shadow-xs' : 'text-secondary hover:text-on-surface'"
            title="Xem song song 50/50"
          >
            Split 50/50
          </button>
          <button
            @click="layoutMode = 'score'"
            class="px-2 py-1 rounded font-medium transition-colors"
            :class="layoutMode === 'score' ? 'bg-surface-container-lowest font-bold text-primary shadow-xs' : 'text-secondary hover:text-on-surface'"
            title="Mở rộng 100% Bản nhạc"
          >
            Full Score
          </button>
          <button
            @click="layoutMode = 'source'"
            class="px-2 py-1 rounded font-medium transition-colors"
            :class="layoutMode === 'source' ? 'bg-surface-container-lowest font-bold text-primary shadow-xs' : 'text-secondary hover:text-on-surface'"
            title="Mở rộng 100% Bản gốc"
          >
            Full Source
          </button>
        </div>

        <!-- Structure Wizard & Undo / Redo Buttons -->
        <div class="flex items-center gap-1">
          <button
            @click="showStructureModal = true"
            class="px-2 py-1 bg-surface-container hover:bg-surface-container-high border border-border-subtle rounded text-xs text-primary font-semibold flex items-center gap-1 transition-colors"
            title="Thiết lập nhịp điệu (2/4, 3/4, 4/4), khóa biểu và số ô nhịp"
          >
            <span class="material-symbols-outlined text-sm">tune</span>
            <span>Cấu trúc</span>
          </button>

          <div class="flex items-center gap-0.5 border border-border-subtle rounded bg-surface-container-low p-0.5">
            <button
              @click="triggerUndo"
              :disabled="!canUndo"
              class="p-1 text-secondary hover:text-primary rounded disabled:opacity-30 disabled:hover:text-secondary transition-colors"
              title="Hoàn tác (Ctrl+Z)"
            >
              <span class="material-symbols-outlined text-base">undo</span>
            </button>
            <button
              @click="triggerRedo"
              :disabled="!canRedo"
              class="p-1 text-secondary hover:text-primary rounded disabled:opacity-30 disabled:hover:text-secondary transition-colors"
              title="Làm lại (Ctrl+Y)"
            >
              <span class="material-symbols-outlined text-base">redo</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Center: Transposition (Dịch giọng) & Tempo -->
      <div class="flex items-center gap-2">
        <!-- Transpose Pill Group -->
        <div class="flex items-center gap-1 bg-surface-container-low border border-border-subtle px-2 py-1 rounded text-xs">
          <span class="text-secondary font-medium text-[11px]">Dịch giọng:</span>
          <button
            @click="transpose(-1)"
            class="px-1.5 py-0.5 hover:bg-surface-container-high rounded text-primary font-bold text-xs"
            title="Giảm 1/2 cung (-1 semitone)"
          >
            ♭ -1
          </button>
          <button
            @click="transpose(1)"
            class="px-1.5 py-0.5 hover:bg-surface-container-high rounded text-primary font-bold text-xs"
            title="Tăng 1/2 cung (+1 semitone)"
          >
            ♯ +1
          </button>
        </div>

        <!-- Tempo / BPM Controller -->
        <div class="flex items-center gap-1.5 bg-surface-container-low border border-border-subtle px-2 py-1 rounded text-xs">
          <span class="material-symbols-outlined text-secondary text-sm">speed</span>
          <span class="font-mono-label font-bold text-on-surface">{{ currentBpm }}</span>
          <span class="text-[10px] text-secondary">BPM</span>
          <input
            type="range"
            min="60"
            max="180"
            step="4"
            v-model.number="currentBpm"
            @input="onBpmChange"
            class="w-16 h-1 bg-surface-container-high rounded-lg appearance-none cursor-pointer accent-primary ml-1"
          />
        </div>

        <!-- Autosave Indicator -->
        <div class="flex items-center gap-1 text-[11px] font-medium" :class="isSaving ? 'text-primary' : 'text-success'">
          <span class="material-symbols-outlined text-xs" :class="{ 'animate-spin': isSaving }">
            {{ isSaving ? 'sync' : 'cloud_done' }}
          </span>
          <span class="hidden lg:inline">{{ isSaving ? 'Đang lưu...' : 'Tự động lưu ✓' }}</span>
        </div>
      </div>

      <!-- Right: Playback, Metronome, Zoom & Export Actions -->
      <div class="flex items-center gap-2">
        <!-- Audio Synthesizer Controls -->
        <div class="flex items-center gap-1 bg-primary/10 border border-primary/20 p-0.5 rounded">
          <button
            @click="toggleAudio"
            class="flex items-center gap-1 px-2.5 py-1 bg-primary text-on-primary hover:bg-primary-container text-xs font-semibold rounded transition-colors shadow-xs"
            :title="isPlaying ? 'Tạm dừng phát nhạc' : 'Phát bản nhạc tổng thể'"
          >
            <span class="material-symbols-outlined text-sm">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
            <span>{{ isPlaying ? 'Dừng' : 'Phát' }}</span>
          </button>

          <!-- Metronome Toggle -->
          <button
            @click="toggleMetronome"
            class="p-1 rounded text-xs transition-colors flex items-center gap-0.5 px-1.5"
            :class="isMetronomeActive ? 'bg-primary text-on-primary font-bold' : 'text-secondary hover:bg-primary/20'"
            title="Bật/Tắt máy đếm nhịp Metronome"
          >
            <span class="material-symbols-outlined text-sm">schedule</span>
            <span class="text-[10px]">Gõ nhịp</span>
          </button>

          <!-- Sound Type Selector -->
          <select
            v-model="soundType"
            @change="onSoundTypeChange"
            class="text-[11px] bg-surface-container-lowest border border-border-subtle rounded px-1.5 py-0.5 text-on-surface font-medium"
            title="Chọn âm sắc phát nhạc"
          >
            <option value="piano">🎹 Piano</option>
            <option value="choir">🎻 Strings Choir</option>
            <option value="organ">⛪ Organ</option>
          </select>

          <button
            @click="isLooping = !isLooping; audioPlayer.setLoop(isLooping)"
            class="p-1 text-secondary hover:text-primary rounded transition-colors"
            :class="{ 'text-primary font-bold': isLooping }"
            title="Lặp lại bài hát"
          >
            <span class="material-symbols-outlined text-sm">repeat</span>
          </button>
          <button
            @click="stopAudio"
            class="p-1 text-secondary hover:text-error rounded transition-colors"
            title="Dừng và về đầu bài"
          >
            <span class="material-symbols-outlined text-sm">stop</span>
          </button>
        </div>

        <div class="w-px h-4 bg-border-subtle mx-0.5"></div>

        <!-- Zoom Controls -->
        <button
          @click="changeZoom(-0.1)"
          class="p-1 text-on-surface-variant hover:text-primary hover:bg-surface-container-low rounded transition-colors"
          title="Thu nhỏ"
        >
          <span class="material-symbols-outlined text-sm">zoom_out</span>
        </button>
        <span class="text-xs font-mono-label text-on-surface-variant w-9 text-center font-medium">
          {{ Math.round(zoomLevel * 100) }}%
        </span>
        <button
          @click="changeZoom(0.1)"
          class="p-1 text-on-surface-variant hover:text-primary hover:bg-surface-container-low rounded transition-colors"
          title="Phóng to"
        >
          <span class="material-symbols-outlined text-sm">zoom_in</span>
        </button>
        <button
          @click="changeZoom(0)"
          class="p-1 text-on-surface-variant hover:text-primary hover:bg-surface-container-low rounded transition-colors"
          title="100%"
        >
          <span class="material-symbols-outlined text-sm">fit_screen</span>
        </button>

        <div class="w-px h-4 bg-border-subtle mx-0.5"></div>

        <!-- Quick Import button -->
        <label
          class="cursor-pointer border border-border-subtle hover:border-primary text-secondary hover:text-primary px-2.5 py-1 rounded text-xs font-semibold transition-colors flex items-center gap-1"
          title="Mở file MusicXML / XML từ máy"
        >
          <span class="material-symbols-outlined text-sm">file_open</span>
          <span class="hidden sm:inline">Mở XML</span>
          <input type="file" accept=".xml,.musicxml" class="hidden" @change="onImportLocalXml" />
        </label>

        <!-- Export button -->
        <button
          @click="$emit('open-export')"
          class="bg-primary text-on-primary px-3 py-1.5 rounded-lg text-xs font-bold hover:brightness-110 active:scale-98 transition-all flex items-center gap-1.5 shadow-sm"
          title="Xuất bản 3 Phiên bản: Bản Đầy Đủ, Bản Không Lời và Bản Hợp Âm Chuẩn"
        >
          <span class="material-symbols-outlined text-sm">ios_share</span>
          <span>Xuất Bản (3 Version)</span>
        </button>
      </div>
    </div>

    <!-- ════════════════════════════════ SPLIT VIEW WORKSPACE ════════════════════════════════ -->
    <div class="flex-1 flex min-h-0 relative overflow-hidden select-none" ref="splitContainerRef">
      <!-- ── Left Pane: Source Viewer (PDF / Scan) ── -->
      <div
        v-show="layoutMode !== 'score'"
        class="bg-surface-container-lowest flex flex-col overflow-hidden min-w-[260px]"
        :style="{ width: layoutMode === 'source' ? '100%' : leftPaneWidth + '%' }"
      >
        <div class="h-8 bg-surface-container-low border-b border-border-subtle flex items-center px-3 justify-between shrink-0">
          <span class="font-label-sm text-xs text-on-surface font-semibold uppercase tracking-wider">Source (Bản PDF / Ảnh Scan Gốc)</span>
          <div class="flex items-center gap-2">
            <span class="text-[11px] text-secondary">Trang 1 / 1</span>
          </div>
        </div>

        <div class="flex-1 p-panel-padding overflow-auto bg-workspace-bg flex justify-center items-start">
          <div class="bg-white shadow-sm border border-border-subtle max-w-2xl w-full p-6 relative rounded-sm">
            <!-- If user provided an actual uploaded PDF -->
            <div v-if="sourcePdfUrl" class="w-full h-full min-h-[550px] flex flex-col">
              <iframe
                :src="sourcePdfUrl + '#toolbar=0&navpanes=0'"
                class="w-full h-[600px] rounded border border-border-subtle shadow-sm bg-white"
                title="Bản PDF Gốc"
              ></iframe>
            </div>

            <!-- If user provided an actual uploaded image -->
            <div v-else-if="sourceImageUrl" class="relative">
              <img :src="sourceImageUrl" alt="Source Sheet" class="w-full h-auto object-contain rounded-xs shadow-sm border border-border-subtle" />
              <!-- Highlight Overlay on active measure -->
              <div
                class="absolute border-2 border-primary bg-sync-active-highlight transition-all pointer-events-none rounded"
                :style="activeMeasureBoxStyle"
              ></div>
            </div>

            <!-- Default Interactive Paper Mock if no uploaded image -->
            <template v-else>
              <div class="text-center mb-4 border-b border-slate-200 pb-2">
                <h4 class="font-bold text-sm text-slate-900">{{ meta.title }}</h4>
                <p class="text-[11px] text-slate-500">{{ meta.composer }} • Bản Scan Gốc</p>
              </div>

              <!-- Simulated Staves with interactive Measure bounding boxes -->
              <div class="space-y-4">
                <div v-for="system in 4" :key="system" class="space-y-1">
                  <div class="grid grid-cols-4 gap-1 relative">
                    <div
                      v-for="m in 4"
                      :key="m"
                      class="h-14 border border-slate-300 rounded-xs relative p-1 cursor-pointer transition-all hover:bg-sky-50 flex flex-col justify-between"
                      :class="[
                        activeMeasure === (system - 1) * 4 + m ? 'border-2 border-primary bg-sync-active-highlight ring-2 ring-primary/20' : '',
                        hasIssue((system - 1) * 4 + m) ? 'border-2 border-error bg-omr-issue-highlight' : ''
                      ]"
                      @click="selectMeasure((system - 1) * 4 + m)"
                    >
                      <!-- Staff lines -->
                      <div class="space-y-1 my-auto pointer-events-none opacity-40">
                        <div v-for="l in 4" :key="l" class="h-px bg-slate-800 w-full"></div>
                      </div>
                      <!-- Measure Number -->
                      <span class="text-[9px] font-mono-label font-bold text-slate-500 absolute top-0.5 left-1">
                        {{ (system - 1) * 4 + m }}
                      </span>

                      <!-- Issue warning icon if any -->
                      <span
                        v-if="hasIssue((system - 1) * 4 + m)"
                        class="material-symbols-outlined text-xs text-error absolute top-0.5 right-1"
                        title="Có cảnh báo OCR tại ô nhịp này"
                      >error</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- ── Resizer Handle ── -->
      <div
        v-if="layoutMode === 'split'"
        class="pane-resizer flex flex-col justify-center items-center group relative z-10"
        :class="{ 'is-dragging': isDraggingResizer }"
        @mousedown="startResize"
      >
        <div class="w-1 h-8 bg-outline-variant group-hover:bg-primary rounded-full transition-colors"></div>
      </div>

      <!-- ── Right Pane: Recognized Score (OSMD) WITH DIRECT SCORE IN-PLACE EDITING ── -->
      <div
        v-show="layoutMode !== 'source'"
        class="flex-1 bg-surface-container-lowest flex flex-col border-l border-border-subtle overflow-hidden min-w-[260px] relative"
      >
        <div class="h-8 bg-surface-container-low border-b border-border-subtle flex items-center px-3 justify-between shrink-0">
          <div class="flex items-center gap-2">
            <span class="font-label-sm text-xs text-on-surface font-semibold uppercase tracking-wider">Recognized Score (OSMD MusicXML)</span>
            <span class="text-[10px] bg-primary/10 text-primary font-bold px-2 py-0.2 rounded-full flex items-center gap-1 border border-primary/20">
              <span class="material-symbols-outlined text-xs">edit</span>
              Click vào chữ/nốt trên bản nhạc để sửa trực tiếp
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] text-primary font-semibold">Ô nhịp đang chọn: M.{{ activeMeasure }}</span>
          </div>
        </div>

        <div
          ref="scoreContainerParentRef"
          class="flex-1 p-panel-padding overflow-auto bg-white flex justify-center items-start relative select-text"
          @click="onScoreContainerClick"
        >
          <!-- OSMD Render Container -->
          <div
            id="osmd-editor-container"
            ref="osmdContainerRef"
            class="w-full max-w-4xl relative"
          ></div>

          <!-- ════════ FLOATING DIRECT INLINE LYRIC INPUT ON SCORE ════════ -->
          <div
            v-if="inlineLyric.visible"
            class="absolute z-50 transition-all flex items-center"
            :style="{
              left: inlineLyric.x + 'px',
              top: inlineLyric.y + 'px',
            }"
            @click.stop
          >
            <div class="relative flex items-center shadow-xl rounded">
              <input
                ref="inlineLyricInputRef"
                v-model="inlineLyric.text"
                type="text"
                class="bg-white border-2 border-primary text-primary font-bold text-xs text-center px-2 py-1 rounded shadow-md outline-none ring-4 ring-primary/25 min-w-[60px]"
                :style="{ width: inlineLyric.width + 'px', height: inlineLyric.height + 'px' }"
                @keydown.space.prevent="commitInlineLyricAndNext(1)"
                @keydown.tab.prevent="commitInlineLyricAndNext(1)"
                @keydown.shift.tab.prevent="commitInlineLyricAndNext(-1)"
                @keydown.enter.prevent="commitInlineLyric"
                @keydown.esc.prevent="closeInlineLyric"
                @blur="onInlineLyricBlur"
              />

              <!-- Floating Hint Tooltip -->
              <div class="absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] font-medium px-2 py-0.5 rounded shadow-lg whitespace-nowrap pointer-events-none flex items-center gap-1">
                <span>Nhấn <strong>Space / Tab</strong> để sang chữ tiếp ➔</span>
                <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-slate-900 rotate-45"></div>
              </div>
            </div>
          </div>

          <!-- ════════ FLOATING DIRECT INLINE CHORD INPUT ON SCORE ════════ -->
          <div
            v-if="inlineChord.visible"
            class="absolute z-50 transition-all flex items-center"
            :style="{
              left: inlineChord.x + 'px',
              top: inlineChord.y + 'px',
            }"
            @click.stop
          >
            <div class="relative flex items-center shadow-xl rounded">
              <input
                ref="inlineChordInputRef"
                v-model="inlineChord.text"
                type="text"
                placeholder="Hợp âm..."
                class="bg-white border-2 border-primary text-primary font-mono-label font-bold text-xs text-center px-2 py-1 rounded shadow-md outline-none ring-4 ring-primary/25 min-w-[70px]"
                @keydown.enter.prevent="commitInlineChord"
                @keydown.esc.prevent="closeInlineChord"
                @blur="onInlineChordBlur"
              />
              <div class="absolute -top-7 left-1/2 -translate-x-1/2 bg-primary text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-lg whitespace-nowrap pointer-events-none">
                Sửa hợp âm (Enter để lưu)
                <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-primary rotate-45"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════ BOTTOM EDITOR DRAWER ════════════════════════════════ -->
    <div
      class="bg-surface-container-lowest border-t border-border-subtle flex flex-col shrink-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-20 transition-all duration-200"
      :style="{ height: drawerCollapsed ? '40px' : drawerHeight + 'px' }"
    >
      <!-- Panel Tabs Header -->
      <div class="h-10 border-b border-border-subtle flex items-center justify-between bg-surface-container-low px-4 select-none shrink-0">
        <div class="flex gap-1 h-full items-end">
          <!-- Lyrics Tab -->
          <button
            @click="activeTab = 'lyrics'; drawerCollapsed = false"
            class="px-4 py-2 font-label-sm text-xs font-semibold flex items-center gap-1.5 transition-colors rounded-t-sm"
            :class="activeTab === 'lyrics' && !drawerCollapsed
              ? 'border-b-2 border-primary text-primary bg-surface-container-lowest'
              : 'text-on-surface-variant hover:text-on-surface border-b-2 border-transparent'"
          >
            <span class="material-symbols-outlined text-base">text_fields</span>
            <span>Lời nhạc (Lyrics)</span>
            <span class="text-[10px] bg-surface-container-high text-secondary px-1.5 py-0.2 rounded-full font-mono-label">
              {{ versesCount }}V
            </span>
          </button>

          <!-- Chords Tab -->
          <button
            @click="activeTab = 'chords'; drawerCollapsed = false"
            class="px-4 py-2 font-label-sm text-xs font-semibold flex items-center gap-1.5 transition-colors rounded-t-sm"
            :class="activeTab === 'chords' && !drawerCollapsed
              ? 'border-b-2 border-primary text-primary bg-surface-container-lowest'
              : 'text-on-surface-variant hover:text-on-surface border-b-2 border-transparent'"
          >
            <span class="material-symbols-outlined text-base">music_note</span>
            <span>Hợp âm (Chords)</span>
            <span class="text-[10px] bg-surface-container-high text-secondary px-1.5 py-0.2 rounded-full font-mono-label">
              {{ harmonies.length }}
            </span>
          </button>

          <!-- Note Editor Tab -->
          <button
            @click="activeTab = 'note'; drawerCollapsed = false; loadMeasureNotes(activeMeasure)"
            class="px-4 py-2 font-label-sm text-xs font-semibold flex items-center gap-1.5 transition-colors rounded-t-sm"
            :class="activeTab === 'note' && !drawerCollapsed
              ? 'border-b-2 border-primary text-primary bg-surface-container-lowest'
              : 'text-on-surface-variant hover:text-on-surface border-b-2 border-transparent'"
          >
            <span class="material-symbols-outlined text-base">edit_note</span>
            <span>Sửa nốt chi tiết (M.{{ activeMeasure }})</span>
          </button>

          <!-- Issues Tab -->
          <button
            @click="activeTab = 'issues'; drawerCollapsed = false"
            class="px-4 py-2 font-label-sm text-xs font-semibold flex items-center gap-1.5 transition-colors rounded-t-sm relative"
            :class="activeTab === 'issues' && !drawerCollapsed
              ? 'border-b-2 border-primary text-primary bg-surface-container-lowest'
              : 'text-on-surface-variant hover:text-on-surface border-b-2 border-transparent'"
          >
            <span class="material-symbols-outlined text-base">error_outline</span>
            <span>Vấn đề (Issues)</span>
            <span v-if="issues.length > 0" class="w-2 h-2 bg-error rounded-full"></span>
          </button>
        </div>

        <!-- Drawer Toggle -->
        <button
          @click="drawerCollapsed = !drawerCollapsed"
          class="p-1 text-secondary hover:text-on-surface rounded transition-colors"
          :title="drawerCollapsed ? 'Mở rộng bảng chỉnh sửa' : 'Thu nhỏ bảng'"
        >
          <span class="material-symbols-outlined text-base">
            {{ drawerCollapsed ? 'expand_less' : 'expand_more' }}
          </span>
        </button>
      </div>

      <!-- Panel Body Area -->
      <div v-show="!drawerCollapsed" class="flex-1 p-panel-padding overflow-y-auto bg-surface-container-lowest">
        <!-- ── TAB: LYRICS ── -->
        <div v-if="activeTab === 'lyrics'" class="grid grid-cols-[120px_1fr] gap-4 h-full">
          <!-- Verse Selector & Auto-fix Tools -->
          <div class="border-r border-border-subtle pr-3 flex flex-col gap-1.5 select-none">
            <button
              v-for="v in [1, 2, 3, 4]"
              :key="v"
              @click="activeVerse = v"
              class="w-full text-left px-3 py-1.5 text-xs rounded font-medium transition-colors"
              :class="activeVerse === v
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'text-on-surface-variant hover:bg-surface-container-low'"
            >
              Verse {{ v }}
            </button>

            <button
              @click="autoFixVietnamese"
              class="mt-2 border border-primary/30 text-primary hover:bg-primary/10 text-[11px] py-1 px-1.5 rounded text-center transition-colors font-semibold flex items-center justify-center gap-1"
              title="Tự động sửa các lỗi OCR dấu tiếng Việt phổ biến"
            >
              ✨ Sửa dấu TV
            </button>

            <button
              @click="showBulkLyrics = !showBulkLyrics"
              class="border border-border-subtle text-secondary hover:text-primary hover:bg-surface-container-low text-[11px] py-1 px-1.5 rounded text-center transition-colors"
            >
              📝 Sửa hàng loạt
            </button>
          </div>

          <!-- Lyrics Grid Content -->
          <div class="flex flex-col gap-3 overflow-y-auto pr-1">
            <!-- Bulk Edit Overlay if toggled -->
            <div v-if="showBulkLyrics" class="bg-surface-container-low p-3 rounded border border-border-subtle space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-xs font-semibold text-on-surface">Dán toàn bộ câu lời Verse {{ activeVerse }} (cách nhau bởi khoảng trắng):</span>
                <button @click="showBulkLyrics = false" class="text-xs text-secondary hover:text-on-surface">✕ Đóng</button>
              </div>
              <textarea
                v-model="bulkLyricText"
                rows="2"
                placeholder="Hỡi Thánh Vương kíp ngự lai giúp chúng tôi..."
                class="w-full p-2 bg-surface-container-lowest border border-border-subtle rounded text-xs text-on-surface focus:outline-none focus:border-primary font-body-md"
              ></textarea>
              <button
                @click="applyBulkLyrics"
                class="bg-primary text-on-primary px-3 py-1 rounded text-xs font-semibold hover:bg-primary-container transition-colors shadow-xs"
              >
                Áp dụng vào các nốt ↵
              </button>
            </div>

            <!-- Syllable inputs matching active verse -->
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="font-label-sm text-xs text-on-surface-variant font-medium">Danh sách âm tiết Verse {{ activeVerse }}</span>
                <span class="text-[11px] text-primary font-semibold">💡 Bạn có thể click trực tiếp vào chữ trên bản nhạc ở trên để gõ liên tục!</span>
              </div>

              <div class="flex flex-wrap gap-2.5">
                <div
                  v-for="(lyric, idx) in currentVerseLyrics"
                  :key="lyric.id"
                  class="flex flex-col gap-1 w-22"
                  :class="{ 'ring-2 ring-primary/50 rounded': activeMeasure === lyric.measureNumber }"
                >
                  <div class="flex justify-between items-center px-0.5">
                    <span class="text-[10px] text-on-surface-variant font-mono-label">M{{ lyric.measureNumber }}:N{{ lyric.noteIndex }}</span>
                    <div class="flex gap-0.5">
                      <button @click="shiftLyric(idx, -1)" class="text-[9px] text-secondary hover:text-primary leading-none" title="Chuyển sang nốt trước">◀</button>
                      <button @click="shiftLyric(idx, 1)" class="text-[9px] text-secondary hover:text-primary leading-none" title="Chuyển sang nốt sau">▶</button>
                    </div>
                  </div>

                  <div class="relative group">
                    <input
                      v-model="lyric.text"
                      @input="onLyricChange(lyric)"
                      @focus="selectMeasure(lyric.measureNumber)"
                      type="text"
                      class="w-full text-center text-xs py-1 px-1.5 border rounded focus:border-primary focus:ring-1 focus:ring-primary h-8 font-medium transition-all"
                      :class="[
                        lyric.hasDiff
                          ? 'border-2 border-primary bg-primary-fixed-dim/20'
                          : 'border-border-subtle bg-surface-container-lowest'
                      ]"
                    />

                    <!-- Tooltip showing OCR Read vs edited text -->
                    <div
                      v-if="lyric.rawOcr && lyric.rawOcr !== lyric.text"
                      class="absolute -top-9 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface text-[10px] px-2 py-0.5 rounded shadow-lg whitespace-nowrap z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <span>OCR: <strong>{{ lyric.rawOcr }}</strong></span>
                      <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-inverse-surface rotate-45"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── TAB: CHORDS ── -->
        <div v-else-if="activeTab === 'chords'" class="space-y-4">
          <div class="flex flex-wrap items-center gap-3 bg-surface-container-low p-2.5 rounded border border-border-subtle">
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold text-on-surface">Thêm hợp âm:</span>
              <input
                v-model="newChordText"
                @keyup.enter="addChord"
                type="text"
                placeholder="VD: G, Am7, D/F#, Cmaj7..."
                class="px-2.5 py-1 text-xs border border-border-subtle rounded bg-surface-container-lowest focus:border-primary focus:ring-1 focus:ring-primary font-mono-label font-bold w-36"
              />
            </div>

            <div class="flex items-center gap-2">
              <span class="text-xs text-secondary">Tại ô nhịp:</span>
              <select
                v-model="newChordMeasure"
                class="px-2 py-1 text-xs border border-border-subtle rounded bg-surface-container-lowest focus:border-primary"
              >
                <option v-for="m in 16" :key="m" :value="m">Ô nhịp {{ m }}</option>
              </select>
            </div>

            <button
              @click="addChord"
              class="bg-primary text-on-primary px-3 py-1 rounded text-xs font-semibold hover:bg-primary-container transition-colors shadow-xs"
            >
              + Thêm
            </button>

            <!-- Quick Presets Palette -->
            <div class="space-y-2 w-full pt-1 border-t border-border-subtle">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[11px] font-semibold text-secondary w-16">Hợp âm chính:</span>
                <button
                  v-for="p in ['Em', 'D', 'C', 'G', 'Am', 'B7', 'F#m7', 'Bsus4']"
                  :key="p"
                  @click="quickInsertChord(p)"
                  class="px-2 py-1 text-xs bg-primary/10 hover:bg-primary text-primary hover:text-on-primary rounded font-mono-label font-bold transition-all shadow-xs"
                  :title="'1-Click thêm ' + p + ' vào ô nhịp ' + activeMeasure"
                >
                  {{ p }}
                </button>
              </div>

              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[11px] font-semibold text-secondary w-16">Slash Chord:</span>
                <button
                  v-for="p in ['D/F#', 'G/B', 'C/E', 'Am/G', 'B7/D#', 'Em/D']"
                  :key="p"
                  @click="quickInsertChord(p)"
                  class="px-2 py-1 text-xs bg-surface-container-high hover:bg-primary hover:text-on-primary text-on-surface rounded font-mono-label font-semibold transition-all"
                  :title="'1-Click thêm Slash Chord ' + p"
                >
                  {{ p }}
                </button>
              </div>
            </div>
          </div>

          <!-- Chord list pills -->
          <div class="flex flex-wrap gap-2">
            <div
              v-for="(chord, cIdx) in harmonies"
              :key="chord.id"
              class="flex items-center gap-2 px-3 py-1.5 bg-surface-container-low border border-border-subtle rounded-full text-xs hover:border-primary transition-colors cursor-pointer"
              :class="{ 'border-primary bg-primary/10': activeMeasure === chord.measureNumber }"
              @click="selectMeasure(chord.measureNumber)"
            >
              <span class="font-mono-label font-bold text-primary">{{ chord.displayText }}</span>
              <span class="text-[10px] text-secondary">M.{{ chord.measureNumber }}</span>
              <button @click.stop="removeChord(chord.measureNumber, cIdx)" class="text-secondary hover:text-error text-xs leading-none" title="Xóa hợp âm">✕</button>
            </div>
          </div>
        </div>

        <!-- ── TAB: NOTE EDITOR (Chi tiết từng nốt trong Measure) ── -->
        <div v-else-if="activeTab === 'note'" class="space-y-4">
          <div class="flex items-center justify-between bg-surface-container-low px-3 py-2 rounded border border-border-subtle">
            <div class="flex items-center gap-3">
              <span class="text-xs font-semibold text-on-surface">Đang sửa nốt tại:</span>
              <span class="bg-primary text-on-primary text-xs px-2.5 py-0.5 rounded font-bold">Measure {{ activeMeasure }}</span>
            </div>
            <div class="flex gap-1 overflow-x-auto py-0.5">
              <button
                v-for="m in 16"
                :key="m"
                @click="selectMeasure(m)"
                class="w-6 h-6 rounded text-[11px] font-mono-label font-semibold flex items-center justify-center transition-colors shrink-0"
                :class="activeMeasure === m ? 'bg-primary text-on-primary' : 'bg-surface-container-highest text-secondary hover:text-on-surface'"
              >
                {{ m }}
              </button>
            </div>
          </div>

          <!-- Interactive Virtual Piano Bar -->
          <div class="bg-surface-container-low p-3 rounded-lg border border-border-subtle space-y-2">
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-base">piano</span>
                <span class="text-xs font-bold text-on-surface">Bàn phím Piano Ảo (Interactive Piano Roll)</span>
              </div>
              <span class="text-[11px] text-secondary">Click phím đàn để nghe và gán cao độ nốt đang chọn</span>
            </div>

            <div class="flex justify-center py-2 select-none overflow-x-auto">
              <div class="flex relative bg-neutral-900 p-2 rounded-lg shadow-inner">
                <!-- Octave 4 & 5 White and Black Keys -->
                <button
                  v-for="k in pianoKeys"
                  :key="k.s + (k.a ? '#' : '') + k.o"
                  @mousedown="playPianoKey(k.s, k.o, k.a)"
                  :class="[
                    k.b
                      ? 'w-5.5 h-16 bg-neutral-800 text-neutral-300 hover:bg-neutral-700 active:bg-primary z-10 -mx-2.75 rounded-b shadow-md flex items-end justify-center pb-1 text-[8px] font-bold cursor-pointer'
                      : 'w-8 h-26 bg-white text-neutral-800 hover:bg-neutral-100 active:bg-primary-fixed border border-neutral-300 rounded-b shadow-sm flex items-end justify-center pb-1 text-[10px] font-bold cursor-pointer'
                  ]"
                >
                  {{ k.s }}{{ k.a ? '♯' : '' }}{{ k.o }}
                </button>
              </div>
            </div>
          </div>

          <!-- Notes in active measure -->
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div
              v-for="note in activeMeasureNotes"
              :key="note.id"
              class="p-3 bg-surface-container-low border rounded space-y-2.5 transition-all"
              :class="selectedNoteId === note.id ? 'border-primary ring-2 ring-primary/30' : 'border-border-subtle'"
              @click="selectedNoteId = note.id"
            >
              <div class="flex justify-between items-center">
                <span class="text-xs font-bold text-primary font-mono-label">Nốt {{ note.noteIndex }}</span>
                <button
                  @click.stop="auditionNote(note.step, note.octave, note.accidental)"
                  class="text-xs text-primary hover:underline flex items-center gap-0.5"
                  title="Nghe thử cao độ nốt"
                >
                  <span class="material-symbols-outlined text-sm">volume_up</span> Nghe
                </button>
              </div>

              <!-- Pitch Step -->
              <div class="space-y-1">
                <label class="text-[10px] text-secondary font-semibold uppercase">Cao độ</label>
                <div class="flex gap-1">
                  <button
                    v-for="p in ['C','D','E','F','G','A','B']"
                    :key="p"
                    @click="note.step = p; applyNoteItem(note)"
                    class="px-1.5 py-0.5 text-xs font-bold rounded border transition-colors"
                    :class="note.step === p ? 'bg-primary text-on-primary border-primary' : 'border-border-subtle bg-surface-container-lowest'"
                  >
                    {{ p }}
                  </button>
                </div>
              </div>

              <!-- Octave & Accidental -->
              <div class="flex gap-2">
                <div class="flex-1">
                  <label class="text-[10px] text-secondary font-semibold uppercase">Quãng</label>
                  <select
                    v-model.number="note.octave"
                    @change="applyNoteItem(note)"
                    class="w-full text-xs p-1 border border-border-subtle rounded bg-surface-container-lowest font-bold"
                  >
                    <option :value="3">3 (Trầm)</option>
                    <option :value="4">4 (Chuẩn)</option>
                    <option :value="5">5 (Cao)</option>
                  </select>
                </div>

                <div class="flex-1">
                  <label class="text-[10px] text-secondary font-semibold uppercase">Dấu hóa</label>
                  <select
                    v-model="note.accidental"
                    @change="applyNoteItem(note)"
                    class="w-full text-xs p-1 border border-border-subtle rounded bg-surface-container-lowest font-medium"
                  >
                    <option :value="null">♮ Bình</option>
                    <option value="sharp">♯ Thăng</option>
                    <option value="flat">♭ Giáng</option>
                  </select>
                </div>
              </div>

              <!-- Duration -->
              <div class="space-y-1">
                <label class="text-[10px] text-secondary font-semibold uppercase">Trường độ</label>
                <select
                  v-model="note.duration"
                  @change="applyNoteItem(note)"
                  class="w-full text-xs p-1 border border-border-subtle rounded bg-surface-container-lowest"
                >
                  <option value="whole">○ Tròn (Whole)</option>
                  <option value="half">◔ Trắng (Half)</option>
                  <option value="quarter">● Đen (Quarter)</option>
                  <option value="eighth">♪ Móc đơn (8th)</option>
                  <option value="16th">♬ Móc kép (16th)</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- ── TAB: ISSUES ── -->
        <div v-else-if="activeTab === 'issues'" class="space-y-3">
          <div class="flex justify-between items-center bg-surface-container-low p-2.5 rounded border border-border-subtle">
            <span class="text-xs font-semibold text-on-surface">Kiểm tra tính tương thích MusicXML:</span>
            <button
              @click="runFullValidationAndRepair"
              class="px-3 py-1 bg-primary text-on-primary rounded text-xs font-semibold hover:bg-primary-container transition-colors flex items-center gap-1 shadow-xs"
            >
              <span class="material-symbols-outlined text-sm">auto_fix_high</span>
              <span>Quét & Tự động sửa lỗi toàn bài</span>
            </button>
          </div>

          <div v-if="issues.length === 0" class="flex items-center gap-2 text-success text-xs font-semibold p-4 bg-success/5 border border-success/20 rounded-lg">
            <span class="material-symbols-outlined text-base">verified</span>
            <span>Không phát hiện lỗi cấu trúc XML hay cảnh báo OMR nào! Bản nhạc đã sẵn sàng xuất bản.</span>
          </div>

          <div v-else class="space-y-1.5">
            <div
              v-for="issue in issues"
              :key="issue.id"
              @click="selectMeasure(issue.measureNumber)"
              class="flex items-center justify-between p-2.5 bg-surface-container-low hover:bg-sync-active-highlight border border-border-subtle hover:border-primary rounded cursor-pointer transition-all"
            >
              <div class="flex items-center gap-3">
                <span
                  class="text-[10px] font-bold font-mono-label px-2 py-0.5 rounded uppercase"
                  :class="[
                    issue.severity === 'error' ? 'bg-error text-on-primary' : '',
                    issue.severity === 'warning' ? 'bg-warning text-on-background' : '',
                    issue.severity === 'info' ? 'bg-primary-fixed text-on-primary-fixed' : ''
                  ]"
                >
                  {{ issue.severity }}
                </span>
                <div>
                  <p class="text-xs font-semibold text-on-surface">{{ issue.message }}</p>
                  <p class="text-[11px] text-secondary font-mono-label">Ô nhịp: Measure {{ issue.measureNumber }} • Đối tượng: {{ issue.entityType }}</p>
                </div>
              </div>

              <span class="text-xs text-primary font-semibold flex items-center gap-1">
                Xem vị trí →
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════ METADATA & TEMPO MODAL ════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="showMetadataModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4" @click.self="showMetadataModal = false">
        <div class="bg-surface-container-lowest border border-border-subtle rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
          <div class="flex justify-between items-center pb-2 border-b border-border-subtle">
            <h3 class="font-headline-sm text-base font-bold text-on-surface">Chỉnh sửa Thông tin Bản nhạc</h3>
            <button @click="showMetadataModal = false" class="p-1 text-secondary hover:text-on-surface">✕</button>
          </div>

          <div class="space-y-3 text-xs">
            <div>
              <label class="block font-semibold text-on-surface mb-1">Tiêu đề bài hát (Title)</label>
              <input v-model="editMetaTitle" type="text" class="w-full p-2 border border-border-subtle rounded bg-surface-container-lowest" />
            </div>

            <div>
              <label class="block font-semibold text-on-surface mb-1">Nhạc sĩ / Tác giả (Composer)</label>
              <input v-model="editMetaComposer" type="text" class="w-full p-2 border border-border-subtle rounded bg-surface-container-lowest" />
            </div>

            <div>
              <label class="block font-semibold text-on-surface mb-1">Lời bài hát (Lyricist)</label>
              <input v-model="editMetaLyricist" type="text" class="w-full p-2 border border-border-subtle rounded bg-surface-container-lowest" />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t border-border-subtle">
            <button @click="showMetadataModal = false" class="px-3 py-1.5 border border-border-subtle text-secondary rounded text-xs">Hủy</button>
            <button @click="saveMetadata" class="px-4 py-1.5 bg-primary text-on-primary rounded text-xs font-semibold hover:bg-primary-container">Lưu thông tin</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ════════════════════════════════ SCORE STRUCTURE WIZARD MODAL ════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="showStructureModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4" @click.self="showStructureModal = false">
        <div class="bg-surface-container-lowest border border-border-subtle rounded-xl max-w-md w-full p-6 shadow-xl space-y-5">
          <div class="flex justify-between items-center pb-2 border-b border-border-subtle">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">tune</span>
              <h3 class="font-headline-sm text-base font-bold text-on-surface">Thiết lập Cấu trúc Khuông nhạc</h3>
            </div>
            <button @click="showStructureModal = false" class="p-1 text-secondary hover:text-on-surface">✕</button>
          </div>

          <div class="space-y-3.5 text-xs">
            <div>
              <label class="block font-semibold text-on-surface mb-1">Nhịp điệu (Time Signature)</label>
              <div class="grid grid-cols-4 gap-2">
                <button
                  v-for="ts in [{ b: 2, t: 4, l: '2/4' }, { b: 3, t: 4, l: '3/4' }, { b: 4, t: 4, l: '4/4' }, { b: 6, t: 8, l: '6/8' }]"
                  :key="ts.l"
                  @click="structTimeBeats = ts.b; structTimeBeatType = ts.t"
                  class="py-2 border rounded font-mono-label font-bold text-center transition-all"
                  :class="structTimeBeats === ts.b && structTimeBeatType === ts.t ? 'bg-primary text-on-primary border-primary shadow-xs' : 'bg-surface-container-low border-border-subtle hover:bg-surface-container-high'"
                >
                  {{ ts.l }}
                </button>
              </div>
            </div>

            <div>
              <label class="block font-semibold text-on-surface mb-1">Khóa biểu / Giọng (Key Signature)</label>
              <select v-model.number="structFifths" class="w-full p-2 border border-border-subtle rounded bg-surface-container-lowest font-medium text-xs">
                <option :value="0">C Major / A minor (0 dấu hóa)</option>
                <option :value="1">G Major / E minor (1 dấu thăng - F#)</option>
                <option :value="2">D Major / B minor (2 dấu thăng - F#, C#)</option>
                <option :value="3">A Major / F# minor (3 dấu thăng)</option>
                <option :value="-1">F Major / D minor (1 dấu giáng - Bb)</option>
                <option :value="-2">Bb Major / G minor (2 dấu giáng - Bb, Eb)</option>
              </select>
            </div>

            <div>
              <label class="block font-semibold text-on-surface mb-1">Số lượng ô nhịp (Total Measures)</label>
              <div class="grid grid-cols-3 gap-2">
                <button
                  v-for="m in [8, 12, 16, 20, 24, 30]"
                  :key="m"
                  @click="structMeasuresCount = m"
                  class="py-1.5 border rounded font-mono-label font-bold text-center transition-all"
                  :class="structMeasuresCount === m ? 'bg-primary text-on-primary border-primary shadow-xs' : 'bg-surface-container-low border-border-subtle hover:bg-surface-container-high'"
                >
                  {{ m }} ô nhịp
                </button>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-3 border-t border-border-subtle">
            <button @click="showStructureModal = false" class="px-3 py-1.5 border border-border-subtle text-secondary rounded text-xs">Hủy</button>
            <button @click="applyScoreStructure" class="px-4 py-1.5 bg-primary text-on-primary rounded text-xs font-semibold hover:bg-primary-container shadow-xs">
              Áp dụng & Tái tạo Khuông
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, reactive, watch } from 'vue';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import { MusicXmlEngine, type ParsedLyric, type ParsedHarmony, type ParsedNoteDetail } from '../Services/MusicXmlEngine';
import { AudioPlaybackEngine } from '../Services/AudioPlaybackEngine';
import { OmrTranscriptionService } from '../Services/OmrTranscriptionService';

const props = defineProps<{
  projectTitle: string;
  xmlContent: string;
  sourceImageUrl?: string;
  sourcePdfUrl?: string;
}>();

const emit = defineEmits<{
  (e: 'open-export'): void;
  (e: 'update:xmlContent', newXml: string): void;
}>();

// Structure Wizard State
const showStructureModal = ref(false);
const structTimeBeats = ref(4);
const structTimeBeatType = ref(4);
const structFifths = ref(1);
const structMeasuresCount = ref(16);

function applyScoreStructure() {
  const newXml = OmrTranscriptionService.generateDynamicHymnStructure(
    meta.value.title || props.projectTitle,
    structTimeBeats.value,
    structTimeBeatType.value,
    structFifths.value,
    structMeasuresCount.value
  );
  showStructureModal.value = false;
  initXml(newXml);
}

// Engine instances
let xmlEngine: MusicXmlEngine | null = null;
const audioPlayer = new AudioPlaybackEngine();

// Playback state
const isPlaying = ref(false);
const isLooping = ref(false);
const isMetronomeActive = ref(false);
const soundType = ref<'piano' | 'choir' | 'organ'>('piano');
const currentBpm = ref(84);

const pianoKeys = [
  { s: 'C', o: 4, a: 0, b: false },
  { s: 'C', o: 4, a: 1, b: true },
  { s: 'D', o: 4, a: 0, b: false },
  { s: 'D', o: 4, a: 1, b: true },
  { s: 'E', o: 4, a: 0, b: false },
  { s: 'F', o: 4, a: 0, b: false },
  { s: 'F', o: 4, a: 1, b: true },
  { s: 'G', o: 4, a: 0, b: false },
  { s: 'G', o: 4, a: 1, b: true },
  { s: 'A', o: 4, a: 0, b: false },
  { s: 'A', o: 4, a: 1, b: true },
  { s: 'B', o: 4, a: 0, b: false },
  { s: 'C', o: 5, a: 0, b: false },
  { s: 'C', o: 5, a: 1, b: true },
  { s: 'D', o: 5, a: 0, b: false },
  { s: 'D', o: 5, a: 1, b: true },
  { s: 'E', o: 5, a: 0, b: false },
  { s: 'F', o: 5, a: 0, b: false },
  { s: 'F', o: 5, a: 1, b: true },
  { s: 'G', o: 5, a: 0, b: false },
  { s: 'G', o: 5, a: 1, b: true },
  { s: 'A', o: 5, a: 0, b: false },
  { s: 'A', o: 5, a: 1, b: true },
  { s: 'B', o: 5, a: 0, b: false },
];

function toggleMetronome() {
  isMetronomeActive.value = !isMetronomeActive.value;
  audioPlayer.setMetronome(isMetronomeActive.value);
}

function onSoundTypeChange() {
  audioPlayer.setSoundType(soundType.value);
}

function quickInsertChord(chordText: string) {
  if (!xmlEngine) return;
  xmlEngine.addOrUpdateHarmony(activeMeasure.value, chordText);
  refreshAfterXmlMutation();
}

function playPianoKey(step: string, octave: number, alter: number = 0) {
  const freq = audioPlayer.pitchToFreq(step, octave, alter);
  audioPlayer.playTone(freq, 0.4);

  if (selectedNoteId.value) {
    const note = activeMeasureNotes.value.find(n => n.id === selectedNoteId.value);
    if (note) {
      note.step = step;
      note.octave = octave;
      note.accidental = alter === 1 ? 'sharp' : alter === -1 ? 'flat' : null;
      applyNoteItem(note);
    }
  }
}

// Layout Modes
const layoutMode = ref<'split' | 'score' | 'source'>('split');

// Sizing
const leftPaneWidth = ref(48);
const isDraggingResizer = ref(false);
const splitContainerRef = ref<HTMLElement | null>(null);
const scoreContainerParentRef = ref<HTMLElement | null>(null);
const osmdContainerRef = ref<HTMLElement | null>(null);

function startResize() {
  isDraggingResizer.value = true;
  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!splitContainerRef.value) return;
    const rect = splitContainerRef.value.getBoundingClientRect();
    const newWidth = ((moveEvent.clientX - rect.left) / rect.width) * 100;
    if (newWidth > 20 && newWidth < 80) {
      leftPaneWidth.value = newWidth;
    }
  };
  const onMouseUp = () => {
    isDraggingResizer.value = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  };
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
}

// Zoom & OSMD
const zoomLevel = ref(0.9);
let osmd: OpenSheetMusicDisplay | null = null;

function changeZoom(delta: number) {
  if (delta === 0) {
    zoomLevel.value = 0.9;
  } else {
    zoomLevel.value = Math.min(Math.max(zoomLevel.value + delta, 0.4), 1.8);
  }
  if (osmd) {
    osmd.zoom = zoomLevel.value;
    osmd.render();
    setTimeout(attachDirectScoreClickListeners, 150);
  }
}

// Active Selection
const activeMeasure = ref(1);
function selectMeasure(mNum: number) {
  activeMeasure.value = mNum;
  loadMeasureNotes(mNum);
}

const activeMeasureBoxStyle = computed(() => {
  const m = activeMeasure.value;
  const row = Math.floor((m - 1) / 4);
  const col = (m - 1) % 4;
  return {
    top: `${20 + row * 22}%`,
    left: `${4 + col * 24}%`,
    width: '22%',
    height: '18%',
  };
});

// Drawer state
const drawerHeight = ref(250);
const drawerCollapsed = ref(false);
const activeTab = ref<'lyrics' | 'chords' | 'note' | 'issues'>('lyrics');
const activeVerse = ref(1);

// Metadata state
const meta = ref({
  title: '001 Hỡi Thánh Vương, Kíp Ngự Lai',
  composer: 'Felice de Giardini, 1769',
  lyricist: 'Anon, 1757',
  tempo: 104,
  timeSig: '3/4',
  keySig: 'G Major',
});
const showMetadataModal = ref(false);
const editMetaTitle = ref('');
const editMetaComposer = ref('');
const editMetaLyricist = ref('');

// Undo / Redo
const canUndo = ref(false);
const canRedo = ref(false);

function updateUndoRedoState() {
  canUndo.value = xmlEngine?.canUndo() || false;
  canRedo.value = xmlEngine?.canRedo() || false;
}

function triggerUndo() {
  if (!xmlEngine) return;
  if (xmlEngine.undo()) {
    refreshAfterXmlMutation();
  }
}

function triggerRedo() {
  if (!xmlEngine) return;
  if (xmlEngine.redo()) {
    refreshAfterXmlMutation();
  }
}

// ════════════════ DIRECT IN-PLACE SCORE EDITING OVERLAYS ════════════════
const inlineLyric = reactive({
  visible: false,
  x: 0,
  y: 0,
  width: 60,
  height: 24,
  text: '',
  verseNumber: 1,
  measureNumber: 1,
  noteIndex: 1,
  svgElement: null as SVGTextElement | null,
});

const inlineLyricInputRef = ref<HTMLInputElement | null>(null);

const inlineChord = reactive({
  visible: false,
  x: 0,
  y: 0,
  text: '',
  measureNumber: 1,
  chordIndex: 0,
  svgElement: null as SVGTextElement | null,
});

const inlineChordInputRef = ref<HTMLInputElement | null>(null);

// Interactive SVG Element Inspector
function attachDirectScoreClickListeners() {
  const container = document.getElementById('osmd-editor-container');
  if (!container) return;

  const svg = container.querySelector('svg');
  if (!svg) return;

  const textNodes = svg.querySelectorAll('text');
  const allLyrics = xmlEngine?.extractLyrics() || {};

  textNodes.forEach(tNode => {
    const rawText = tNode.textContent?.trim() || '';
    if (!rawText) return;

    // Skip title and metadata headers
    if (rawText.includes('HỠI THÁNH VƯƠNG') || rawText.includes('Giardini') || rawText.includes('Charles') || rawText.includes('3/4')) {
      return;
    }

    // Check if this text node is a chord (e.g. G, D, D7, Em, Am, D/F#)
    const isChord = /^[A-Ga-g][#b♭♯]?(m|min|maj|dim|aug|sus|7|9|add)?(\/[A-Ga-g][#b♭♯]?)?$/.test(rawText);

    // Style as interactive clickable hotspot
    tNode.style.pointerEvents = 'all';
    tNode.style.cursor = 'text';
    tNode.style.transition = 'all 0.15s ease';
    tNode.setAttribute('pointer-events', 'all');

    // Tooltip & hover
    tNode.onmouseenter = () => {
      tNode.style.fill = '#004ac6';
      tNode.style.fontWeight = 'bold';
    };
    tNode.onmouseleave = () => {
      tNode.style.fill = '';
      tNode.style.fontWeight = '';
    };

    // Direct Click on SVG Text
    tNode.onclick = (e: MouseEvent) => {
      e.stopPropagation();
      const parentRect = scoreContainerParentRef.value?.getBoundingClientRect();
      const textRect = tNode.getBoundingClientRect();

      if (!parentRect) return;

      const x = textRect.left - parentRect.left + (scoreContainerParentRef.value?.scrollLeft || 0);
      const y = textRect.top - parentRect.top + (scoreContainerParentRef.value?.scrollTop || 0);

      if (isChord) {
        // Open Inline Chord Editor directly over the chord symbol
        inlineChord.visible = true;
        inlineChord.x = Math.max(0, x - 10);
        inlineChord.y = Math.max(0, y - 4);
        inlineChord.text = rawText;
        inlineChord.measureNumber = activeMeasure.value;
        inlineChord.svgElement = tNode;
        inlineLyric.visible = false;

        nextTick(() => {
          inlineChordInputRef.value?.focus();
          inlineChordInputRef.value?.select();
        });
      } else {
        // Find matching syllable in active verse
        let matchedVerse = activeVerse.value;
        let matchedMeasure = activeMeasure.value;
        let matchedNoteIdx = 1;

        // Auto-match syllable
        for (let v = 1; v <= 4; v++) {
          const list = allLyrics[v] || [];
          const found = list.find(item => item.text === rawText || item.text.startsWith(rawText) || rawText.startsWith(item.text));
          if (found) {
            matchedVerse = found.verseNumber;
            matchedMeasure = found.measureNumber;
            matchedNoteIdx = found.noteIndex;
            break;
          }
        }

        activeVerse.value = matchedVerse;
        activeMeasure.value = matchedMeasure;

        // Open Inline Lyric Editor directly over the word
        inlineLyric.visible = true;
        inlineLyric.x = Math.max(0, x - 6);
        inlineLyric.y = Math.max(0, y - 4);
        inlineLyric.width = Math.max(textRect.width + 20, 60);
        inlineLyric.height = Math.max(textRect.height + 8, 26);
        inlineLyric.text = rawText;
        inlineLyric.verseNumber = matchedVerse;
        inlineLyric.measureNumber = matchedMeasure;
        inlineLyric.noteIndex = matchedNoteIdx;
        inlineLyric.svgElement = tNode;
        inlineChord.visible = false;

        nextTick(() => {
          inlineLyricInputRef.value?.focus();
          inlineLyricInputRef.value?.select();
        });
      }
    };
  });

  // Attach interactive click to noteheads
  const noteheads = svg.querySelectorAll('.vf-notehead, g.vf-stavenote, .vf-note');
  noteheads.forEach((nh, idx) => {
    const el = nh as SVGElement;
    el.style.cursor = 'pointer';
    el.onclick = (e: MouseEvent) => {
      e.stopPropagation();
      activeTab.value = 'note';
      drawerCollapsed.value = false;
      if (activeMeasureNotes.value.length > 0) {
        const targetNote = activeMeasureNotes.value[idx % activeMeasureNotes.value.length];
        if (targetNote) {
          selectedNoteId.value = targetNote.id;
          auditionNote(targetNote.step, targetNote.octave, targetNote.accidental);
        }
      }
    };
  });
}

function onScoreContainerClick() {
  if (inlineLyric.visible) commitInlineLyric();
  if (inlineChord.visible) commitInlineChord();
}

function commitInlineLyric() {
  if (!inlineLyric.visible || !xmlEngine) return;
  const newText = inlineLyric.text.trim();
  if (newText) {
    xmlEngine.updateLyricText(inlineLyric.verseNumber, inlineLyric.measureNumber, inlineLyric.noteIndex, newText);
    refreshAfterXmlMutation();
  }
  inlineLyric.visible = false;
}

function onInlineLyricBlur() {
  setTimeout(() => {
    commitInlineLyric();
  }, 120);
}

function commitInlineLyricAndNext(direction: number) {
  if (!xmlEngine) return;
  const currentVerse = inlineLyric.verseNumber;
  const currentMeasureNum = inlineLyric.measureNumber;
  const currentNoteIdx = inlineLyric.noteIndex;
  const newText = inlineLyric.text.trim();

  if (newText) {
    xmlEngine.updateLyricText(currentVerse, currentMeasureNum, currentNoteIdx, newText);
  }

  // Find next syllable in current verse
  const list = lyricsMap.value[currentVerse] || [];
  const currentIdx = list.findIndex(
    item => item.measureNumber === currentMeasureNum && item.noteIndex === currentNoteIdx
  );

  const nextIdx = currentIdx + direction;
  if (nextIdx >= 0 && nextIdx < list.length) {
    const nextItem = list[nextIdx];
    activeMeasure.value = nextItem.measureNumber;

    refreshAfterXmlMutation();

    setTimeout(() => {
      // Find SVG text node for next syllable and click it
      const container = document.getElementById('osmd-editor-container');
      const textNodes = Array.from(container?.querySelectorAll('svg text') || []);
      const nextNode = textNodes.find(n => n.textContent?.trim() === nextItem.text);
      if (nextNode) {
        (nextNode as HTMLElement).click();
      }
    }, 180);
  } else {
    inlineLyric.visible = false;
    refreshAfterXmlMutation();
  }
}

function closeInlineLyric() {
  inlineLyric.visible = false;
}

function commitInlineChord() {
  if (!inlineChord.visible || !xmlEngine) return;
  const newChord = inlineChord.text.trim();
  if (newChord) {
    xmlEngine.addOrUpdateHarmony(inlineChord.measureNumber, newChord);
    refreshAfterXmlMutation();
  }
  inlineChord.visible = false;
}

function onInlineChordBlur() {
  setTimeout(() => {
    commitInlineChord();
  }, 120);
}

function closeInlineChord() {
  inlineChord.visible = false;
}

// ════════════════ BOTTOM PANEL HANDLERS ════════════════
// Lyrics data
const lyricsMap = ref<Record<number, ParsedLyric[]>>({});
const versesCount = computed(() => Object.keys(lyricsMap.value).length || 4);
const currentVerseLyrics = computed(() => lyricsMap.value[activeVerse.value] || []);
const showBulkLyrics = ref(false);
const bulkLyricText = ref('');

function onLyricChange(lyric: ParsedLyric) {
  if (!xmlEngine) return;
  lyric.hasDiff = true;
  xmlEngine.updateLyricText(lyric.verseNumber, lyric.measureNumber, lyric.noteIndex, lyric.text);
  reRenderScore();
}

function autoFixVietnamese() {
  if (!xmlEngine) return;
  const count = xmlEngine.autoFixVietnameseLyrics();
  if (count > 0) {
    refreshAfterXmlMutation();
    alert(`✨ Đã tự động chuẩn hóa ${count} âm tiết có dấu tiếng Việt!`);
  } else {
    alert('Lời bài hát đã chuẩn dấu tiếng Việt!');
  }
}

function applyBulkLyrics() {
  if (!xmlEngine) return;
  const raw = bulkLyricText.value.trim();
  if (raw) {
    xmlEngine.distributeBulkLyrics(activeVerse.value, raw);
  }
  showBulkLyrics.value = false;
  bulkLyricText.value = '';
  refreshAfterXmlMutation();
}

function shiftLyric(idx: number, dir: number) {
  if (!xmlEngine) return;
  const list = lyricsMap.value[activeVerse.value];
  const target = idx + dir;
  if (target < 0 || target >= list.length) return;
  const temp = list[idx].text;
  list[idx].text = list[target].text;
  list[target].text = temp;
  list[idx].hasDiff = true;
  list[target].hasDiff = true;

  xmlEngine.updateLyricText(list[idx].verseNumber, list[idx].measureNumber, list[idx].noteIndex, list[idx].text);
  xmlEngine.updateLyricText(list[target].verseNumber, list[target].measureNumber, list[target].noteIndex, list[target].text);
  refreshAfterXmlMutation();
}

// Chords
const harmonies = ref<ParsedHarmony[]>([]);
const newChordText = ref('');
const newChordMeasure = ref(1);

function addChord() {
  if (!newChordText.value.trim() || !xmlEngine) return;
  const ok = xmlEngine.addOrUpdateHarmony(newChordMeasure.value, newChordText.value.trim());
  if (ok) {
    newChordText.value = '';
    refreshAfterXmlMutation();
  }
}

function removeChord(measureNumber: number, chordIndex: number) {
  if (!xmlEngine) return;
  xmlEngine.removeHarmony(measureNumber, chordIndex);
  refreshAfterXmlMutation();
}

// Transpose
function transpose(semitones: number) {
  if (!xmlEngine) return;
  xmlEngine.transpose(semitones);
  refreshAfterXmlMutation();
}

// Note detail editing
const activeMeasureNotes = ref<ParsedNoteDetail[]>([]);
const selectedNoteId = ref('');

function loadMeasureNotes(mNum: number) {
  if (!xmlEngine) return;
  activeMeasureNotes.value = xmlEngine.getNotesInMeasure(mNum);
  if (activeMeasureNotes.value.length > 0 && !selectedNoteId.value) {
    selectedNoteId.value = activeMeasureNotes.value[0].id;
  }
}

function applyNoteItem(note: ParsedNoteDetail) {
  if (!xmlEngine) return;
  xmlEngine.updateNoteDetail(
    note.measureNumber,
    note.noteIndex,
    note.step,
    note.octave,
    note.accidental,
    note.duration,
    note.isDotted,
    note.isRest
  );
  refreshAfterXmlMutation();
}

function auditionNote(step: string, octave: number, accidental: string | null) {
  const alter = accidental === 'sharp' ? 1 : accidental === 'flat' ? -1 : 0;
  const freq = audioPlayer.pitchToFreq(step, octave, alter);
  audioPlayer.playTone(freq, 0.4);
}

// Issues & Validation
const issues = ref([
  { id: 'iss_1', measureNumber: 2, entityType: 'lyric', message: 'Syllable "Vương," được chỉnh sửa so với OCR ("Vương")', severity: 'info' },
  { id: 'iss_2', measureNumber: 2, entityType: 'harmony', message: 'Hợp âm chuyển vị Slash chord D/F# — cần kiểm tra nốt bass F#', severity: 'warning' },
]);

function hasIssue(mNum: number) {
  return issues.value.some(i => i.measureNumber === mNum);
}

function runFullValidationAndRepair() {
  if (!xmlEngine) return;
  isSaving.value = true;
  xmlEngine.autoFixVietnameseLyrics();
  issues.value = [];
  setTimeout(() => {
    isSaving.value = false;
    refreshAfterXmlMutation();
  }, 300);
}

// Metadata saving
function saveMetadata() {
  if (!xmlEngine) return;
  xmlEngine.updateMetadata(editMetaTitle.value, editMetaComposer.value, editMetaLyricist.value);
  showMetadataModal.value = false;
  refreshAfterXmlMutation();
}

// Audio Playback
function toggleAudio() {
  audioPlayer.toggle();
}

function stopAudio() {
  audioPlayer.stop();
}

function onBpmChange() {
  audioPlayer.setTempo(currentBpm.value);
  xmlEngine?.updateMetadata(undefined, undefined, undefined, currentBpm.value);
}

// Import local XML
function onImportLocalXml(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    const xml = ev.target?.result as string;
    if (xml) {
      initXml(xml);
    }
  };
  reader.readAsText(file);
}

// Re-render OSMD with debounce
const isSaving = ref(false);
let renderDebounceTimer: any = null;
async function reRenderScore() {
  if (!xmlEngine || !osmd) return;
  isSaving.value = true;
  const newXml = xmlEngine.getXmlString();
  emit('update:xmlContent', newXml);
  updateUndoRedoState();

  clearTimeout(renderDebounceTimer);
  renderDebounceTimer = setTimeout(async () => {
    try {
      await osmd?.load(newXml);
      osmd?.render();
      setTimeout(attachDirectScoreClickListeners, 150);
      isSaving.value = false;
    } catch (e) {
      console.warn('Re-render OSMD notice:', e);
      isSaving.value = false;
    }
  }, 120);
}

function refreshAfterXmlMutation() {
  if (!xmlEngine) return;
  lyricsMap.value = xmlEngine.extractLyrics();
  harmonies.value = xmlEngine.extractHarmonies();
  meta.value = xmlEngine.extractMetadata();
  loadMeasureNotes(activeMeasure.value);
  reRenderScore();
}

// OSMD Setup & Initialization
async function initXml(xmlString: string) {
  xmlEngine = new MusicXmlEngine(xmlString);
  lyricsMap.value = xmlEngine.extractLyrics();
  harmonies.value = xmlEngine.extractHarmonies();
  meta.value = xmlEngine.extractMetadata();
  editMetaTitle.value = meta.value.title;
  editMetaComposer.value = meta.value.composer;
  editMetaLyricist.value = meta.value.lyricist;
  currentBpm.value = meta.value.tempo;
  audioPlayer.setTempo(currentBpm.value);
  loadMeasureNotes(activeMeasure.value);
  updateUndoRedoState();

  const container = document.getElementById('osmd-editor-container');
  if (!container) return;

  if (!osmd) {
    osmd = new OpenSheetMusicDisplay(container, {
      autoResize: true,
      backend: 'svg',
      drawTitle: true,
      drawComposer: true,
      drawLyricist: false,
      drawPartNames: false,
      drawMeasureNumbers: true,
      drawingParameters: 'compact',
    });
  }

  osmd.zoom = zoomLevel.value;
  await osmd.load(xmlString);
  osmd.render();

  setTimeout(attachDirectScoreClickListeners, 200);
}

// Global Keyboard Shortcuts (Ctrl+Z, Ctrl+Y, Space for play, Arrows for measures & note pitches)
function handleKeydown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') {
    return;
  }

  const stepsOrder = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    if (e.shiftKey) triggerRedo();
    else triggerUndo();
    e.preventDefault();
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
    triggerRedo();
    e.preventDefault();
  } else if (e.code === 'Space') {
    toggleAudio();
    e.preventDefault();
  } else if (e.key === 'ArrowRight' && !e.altKey) {
    selectMeasure(Math.min(activeMeasure.value + 1, 30));
  } else if (e.key === 'ArrowLeft' && !e.altKey) {
    selectMeasure(Math.max(activeMeasure.value - 1, 1));
  } else if (e.key === 'ArrowUp' && (e.altKey || activeTab.value === 'note')) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      const targetNote = measureNotes.value[0];
      const curIdx = stepsOrder.indexOf(targetNote.step);
      if (curIdx === 6) {
        targetNote.step = 'C';
        targetNote.octave = Math.min(targetNote.octave + 1, 7);
      } else {
        targetNote.step = stepsOrder[curIdx + 1];
      }
      applyNoteItem(targetNote);
      auditionNote(targetNote.step, targetNote.octave, targetNote.accidental);
    }
  } else if (e.key === 'ArrowDown' && (e.altKey || activeTab.value === 'note')) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      const targetNote = measureNotes.value[0];
      const curIdx = stepsOrder.indexOf(targetNote.step);
      if (curIdx === 0) {
        targetNote.step = 'B';
        targetNote.octave = Math.max(targetNote.octave - 1, 2);
      } else {
        targetNote.step = stepsOrder[curIdx - 1];
      }
      applyNoteItem(targetNote);
      auditionNote(targetNote.step, targetNote.octave, targetNote.accidental);
    }
  } else if (e.key === '4' && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].duration = 'quarter';
      applyNoteItem(measureNotes.value[0]);
    }
  } else if (e.key === '8' && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].duration = 'eighth';
      applyNoteItem(measureNotes.value[0]);
    }
  } else if (e.key === '2' && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].duration = 'half';
      applyNoteItem(measureNotes.value[0]);
    }
  } else if (e.key === '1' && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].duration = 'whole';
      applyNoteItem(measureNotes.value[0]);
    }
  } else if (e.key === '.' && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].isDotted = !measureNotes.value[0].isDotted;
      applyNoteItem(measureNotes.value[0]);
    }
  } else if ((e.key === '#' || e.key === '+') && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].accidental = measureNotes.value[0].accidental === 'sharp' ? null : 'sharp';
      applyNoteItem(measureNotes.value[0]);
      auditionNote(measureNotes.value[0].step, measureNotes.value[0].octave, measureNotes.value[0].accidental);
    }
  } else if ((e.key === 'b' || e.key === '-') && (activeTab.value === 'note' || e.altKey)) {
    e.preventDefault();
    if (measureNotes.value.length > 0) {
      measureNotes.value[0].accidental = measureNotes.value[0].accidental === 'flat' ? null : 'flat';
      applyNoteItem(measureNotes.value[0]);
      auditionNote(measureNotes.value[0].step, measureNotes.value[0].octave, measureNotes.value[0].accidental);
    }
  } else if (e.key === 'Escape') {
    inlineLyric.visible = false;
    inlineChord.visible = false;
    showMetadataModal.value = false;
    showBulkLyrics.value = false;
  }
}

// Watch for dynamic XML changes when opening different projects or converting new files
watch(
  () => props.xmlContent,
  async (newXml) => {
    if (newXml && newXml.trim() !== '') {
      await nextTick();
      await initXml(newXml);
    }
  },
  { immediate: false }
);

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown);

  // Connect Audio Player callbacks
  audioPlayer.onMeasureChange((m) => {
    activeMeasure.value = m;
  });
  audioPlayer.onStateChange((playing) => {
    isPlaying.value = playing;
  });

  await nextTick();
  let xml = props.xmlContent;
  if (!xml || xml.trim() === '') {
    xml = await fetch('/golden.xml').then(r => r.text()).catch(() => '');
  }
  if (xml) {
    await initXml(xml);
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
  audioPlayer.stop();
});
</script>
