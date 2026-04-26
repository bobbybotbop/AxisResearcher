# Global Styling Tokens

This project uses global semantic color variables for light/dark mode.  
Set theme by applying `data-theme="light"` or `data-theme="dark"` on the root HTML element.

## Theme Variables

Defined in `frontend/src/styles/App.css`:

- `--surface-app`: overall app/page background.
- `--surface-panel`: cards, sidebars, modals, and elevated containers.
- `--surface-muted`: secondary sections inside panels.
- `--surface-hover`: hover state for neutral interactive surfaces.
- `--border-default`: default neutral borders and separators.
- `--text-primary`: primary text color for headings and body copy.
- `--text-muted`: secondary/supporting text color.
- `--text-inverse`: inverse text color for high-contrast surfaces (reserved).
- `--ring-contrast`: ring/accent contrast helper for badges and status dots.

## Tailwind Utility Tokens

These semantic variables are exposed in Tailwind via `@theme`:

- `bg-surface-app`
- `bg-surface-panel`
- `bg-surface-muted`
- `bg-surface-hover`
- `border-border-default`
- `text-text-primary`
- `text-text-muted`
- `ring-ring-contrast`

## Usage Rules

- Use `bg-surface-app` for page-level wrappers and app backgrounds.
- Use `bg-surface-panel` for primary content containers.
- Use `bg-surface-muted` for nested utility blocks (settings sections, readouts, helper panels).
- Use `border-border-default` for neutral borders and dividers.
- Use `text-text-primary` for titles and default text.
- Use `text-text-muted` for helper labels and secondary descriptions.
- Use `bg-surface-hover` for neutral button/row hover states.
- Keep status colors (`primary`, `success`, `warning`, `danger`) for semantic feedback only, not for general layout surfaces.

## Dark Mode Behavior

- `:root` defines light theme defaults and `color-scheme: light`.
- `[data-theme="dark"]` overrides the same semantic variables and sets `color-scheme: dark`.
- Components should consume semantic utilities so no component-level dark-mode branching is needed for standard surfaces/text.
