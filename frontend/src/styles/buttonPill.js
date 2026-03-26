/** Pill outline: pure white fill, dark border — primary actions */
const base =
  "rounded-full border border-neutral-900 bg-white font-light leading-snug tracking-tight text-neutral-900 shadow-none transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900/20 disabled:cursor-not-allowed disabled:opacity-60";

export const btnPill = `${base} px-6 py-2.5 text-base`;

export const btnPillSm = `${base} px-4 py-2 text-sm`;

export const btnPillLg = `${base} px-10 py-3.5 text-lg`;

/** Softer outline for secondary actions (e.g. Download) */
const baseSecondary =
  "rounded-full border border-gray-500 bg-white font-light leading-snug tracking-tight text-gray-900 shadow-none transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400/25 disabled:cursor-not-allowed disabled:opacity-60";

export const btnPillSecondary = `${baseSecondary} px-6 py-2.5 text-base`;
