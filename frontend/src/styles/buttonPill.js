/** Pill outline: pure white fill, dark border — primary actions */
const base =
  "rounded-full border border-border-default bg-surface-panel font-light leading-snug tracking-tight text-text-primary shadow-none transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40 disabled:cursor-not-allowed disabled:opacity-60";

export const btnPill = `${base} px-6 py-2.5 text-base`;

export const btnPillSm = `${base} px-4 py-2 text-sm`;

export const btnPillLg = `${base} px-10 py-3.5 text-lg`;

/** Softer outline for secondary actions (e.g. Download) */
const baseSecondary =
  "rounded-full border border-border-default bg-surface-panel font-light leading-snug tracking-tight text-text-primary shadow-none transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40 disabled:cursor-not-allowed disabled:opacity-60";

export const btnPillSecondary = `${baseSecondary} px-6 py-2.5 text-base`;
