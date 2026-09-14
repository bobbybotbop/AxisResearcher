export interface Toast {
  id: number;
  type: "success" | "error";
  message: string;
  detail?: string;
}
