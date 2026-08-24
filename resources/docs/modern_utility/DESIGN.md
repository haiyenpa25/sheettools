---
name: Modern Utility
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434655'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fc'
  on-secondary-container: '#57657a'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#EF4444'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#d5e3fc'
  secondary-fixed-dim: '#b9c7df'
  on-secondary-fixed: '#0d1c2e'
  on-secondary-fixed-variant: '#3a485b'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
  success: '#10B981'
  warning: '#F59E0B'
  omr-issue-highlight: rgba(239, 68, 68, 0.1)
  sync-active-highlight: rgba(37, 99, 235, 0.08)
  workspace-bg: '#F1F5F9'
  border-subtle: '#E2E8F0'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  mono-label:
    fontFamily: monospace
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.2'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter-default: 16px
  margin-main: 24px
  panel-padding: 12px
  editor-gap: 2px
---

## Brand & Style
The design system is engineered for **Modern Utility**, prioritizing workflow efficiency, data integrity, and musical accuracy. It adopts a **Corporate / Modern** aesthetic that mimics the focused environment of a developer IDE or professional engraving software. 

The personality is technical and dependable, aimed at users who view the application as a high-precision instrument rather than a casual media player. The interface relies on a clean, structured hierarchy to reduce cognitive load during the meticulous process of correcting Optical Music Recognition (OMR) results. The UI avoids unnecessary decoration, using space and alignment to create a sense of professional reliability.

## Colors
This design system utilizes a structured palette built around a trusted **Primary Indigo (#2563EB)** to denote action and focus. The workspace is grounded in a range of cool greys and whites to ensure that musical notation and OCR highlights remain the primary focal points.

- **Primary**: Used for active states, primary buttons, and critical path interactions.
- **Secondary**: Reserved for auxiliary tools, secondary navigation, and meta-information.
- **Semantic Palette**: High-saturation greens, ambers, and reds are used strictly for status reporting (Success, Warning, Error) to ensure OMR issues are immediately identifiable.
- **Application Surfaces**: The main editor uses a slightly off-white background to reduce eye strain, while side panels and toolbars use subtle grey tonal shifts to define boundaries without heavy borders.

## Typography
The system uses **Inter** exclusively to provide a neutral, highly legible foundation with exceptional support for Vietnamese diacritics. 

The typographic scale is compact to accommodate data-heavy editor panels. 
- **Headlines**: Used sparingly for project titles and major section headers.
- **Body**: Optimized for reading lyrics and composer metadata.
- **Labels**: Used for technical attributes (Root, Accidental, Quality) in the chord and note editors.
- **Monospace (Fallback)**: Used for coordinate data or technical identifiers in the Issue Panel to distinguish raw data from user-editable text.

## Layout & Spacing
The layout philosophy is built on a **Split-View Workspace**. On desktop, a rigid 50/50 split divides the immutable Source Viewer from the editable Score Viewer. 

- **Desktop**: A persistent header contains global actions, while the main body uses a vertical divider that is draggable. Panels for Lyrics, Chords, and Issues are docked at the bottom or sides using a flexible grid.
- **Mobile/Tablet**: The layout reflows into a single-pane tabbed interface ([SOURCE] | [SCORE] | [EDIT]), allowing the user to focus on one aspect of the conversion at a time.
- **Spacing Rhythm**: A 4px baseline grid ensures alignment across dense input forms and toolbars. Padding is kept tight (12px) in editor panels to maximize visible notation area.

## Elevation & Depth
In line with the "Modern Utility" aesthetic, this design system uses **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows.

- **Level 0 (Base)**: The workspace background (`#F1F5F9`).
- **Level 1 (Panels)**: White surfaces (`#FFFFFF`) with 1px borders (`#E2E8F0`) to define the Source and Score containers.
- **Level 2 (Active Tool)**: Floating editor pop-ups (invoked when clicking a note) use a very soft, diffused ambient shadow (8px blur, 5% opacity) to provide context without obscuring the score.
- **Interactive Sync**: When a measure is selected, a subtle color tint (`sync-active-highlight`) is applied to the corresponding area in both viewers, creating a "connected" depth effect.

## Shapes
Shapes are functional and conservative. A **Soft (0.25rem)** roundedness is applied to standard UI elements like buttons, input fields, and chips. 

- **Standard (4px)**: Default for buttons, inputs, and panel corners.
- **Large (8px)**: Used for modal containers like the "ExportDialog" or "UploadDropzone."
- **Musical Symbols**: Notation remains standard, but interactive "hit-boxes" for notes and chords follow the system's roundedness to maintain visual harmony.

## Components
- **Buttons**: High-contrast, solid fills for primary actions (Export, Process). Ghost buttons for secondary tools (Zoom, Pan).
- **Progress Indicators**: Linear, detailed bars showing specific pipeline stages (e.g., "Detecting Staves...", "OCR Text Extraction...").
- **Split-Pane Layout**: A custom divider component with a hover-active handle for resizing the Source/Score view.
- **Editor Panels**: Dense, form-heavy drawers at the bottom of the viewport. Inputs use `label-sm` for field names to save vertical space.
- **Status Chips**: Small, pill-shaped indicators in the Project Dashboard using semantic background colors to show "READY" or "NEEDS_REVIEW."
- **Issue Highlighting**: A non-intrusive red underline or background tint within the Issue Panel that correlates to a red bounding box in the Source Viewer.
- **Input Fields**: Clean, 1px bordered boxes that highlight in Primary Blue when focused. For Vietnamese text input, ensure the height accounts for stacked diacritics.