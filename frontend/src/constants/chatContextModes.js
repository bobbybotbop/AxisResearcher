import { Heading, AlignLeft, Images, Tags } from "lucide-react";

export const CHAT_CONTEXT_MODES = [
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

export function getChatContextInputPlaceholder(contextId = DEFAULT_CHAT_CONTEXT) {
  const mode =
    CHAT_CONTEXT_MODES.find((m) => m.id === contextId) ?? CHAT_CONTEXT_MODES[0];
  return mode.inputPlaceholder;
}
