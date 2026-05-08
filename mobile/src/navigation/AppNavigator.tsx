/**
 * Three-mode navigation: Anticollector (free) → Qualification → Full LK
 * Shield tab always visible — it's the hook.
 */
export const TAB_CONFIG = {
  unauthenticated: [
    { name: "Shield", icon: "shield", label: "Защита" },
    { name: "Evaluate", icon: "calculator", label: "Оценка" },
    { name: "Tips", icon: "book-open", label: "Советы" },
    { name: "Auth", icon: "user", label: "Войти" },
  ],
  authenticated_with_case: [
    { name: "Shield", icon: "shield", label: "Защита" },
    { name: "Case", icon: "briefcase", label: "Дело" },
    { name: "Docs", icon: "file-text", label: "Документы" },
    { name: "Chat", icon: "message-circle", label: "Чат" },
    { name: "Profile", icon: "user", label: "Профиль" },
  ],
};
