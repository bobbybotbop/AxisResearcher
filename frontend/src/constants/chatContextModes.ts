import { Heading, AlignLeft, Images, Tags } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ChatContextMode {
  id: string;
  label: string;
  Icon: LucideIcon;
  inputPlaceholder: string;
}

export const CHAT_CONTEXT_MODES: ChatContextMode[] = [
  { id: "title", label: "Title", Icon: Heading, inputPlaceholder: "Edit the title" },
  {
    id: "description",
    label: "Description",
    Icon: AlignLeft,
    inputPlaceholder: "Edit the description",
  },
  { id: "photos", label: "Photos", Icon: Images, inputPlaceholder: "Edit the photos" },
  {
    id: "metadata",
    label: "Metadata",
    Icon: Tags,
    inputPlaceholder: "Edit the metadata",
  },
];

export const DEFAULT_CHAT_CONTEXT = "title";

export function getChatContextInputPlaceholder(contextId: string = DEFAULT_CHAT_CONTEXT): string {
  const mode =
    CHAT_CONTEXT_MODES.find((m) => m.id === contextId) ?? CHAT_CONTEXT_MODES[0];
  return mode.inputPlaceholder;
}
