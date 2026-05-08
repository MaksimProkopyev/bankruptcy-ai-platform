import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Primary colors using CSS variables
        primary: "var(--color-primary)",
        "primary-dark": "var(--color-primary-dark)",
        "primary-light": "var(--color-primary-light)",
        surface: "var(--color-surface)",
        "surface-muted": "var(--color-surface-muted)",
        neutral: "var(--color-neutral)",
        // Accent (gold)
        accent: "var(--color-accent)",
        "accent-hover": "var(--color-accent-hover)",
        "accent-light": "var(--color-accent-light)",
        // Text
        text: "var(--color-text)",
        "text-body": "var(--color-text-body)",
        "text-muted": "var(--color-text-muted)",
        "text-on-dark": "var(--color-text-on-dark)",
        "text-on-dark-muted": "var(--color-text-on-dark-muted)",
        // Borders
        border: "var(--color-border)",
        "border-strong": "var(--color-border-strong)",
        "border-dark": "var(--color-border-dark)",
        // Semantic
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
        info: "var(--color-info)",
      },
      fontFamily: {
        heading: "var(--font-heading)",
        body: "var(--font-body)",
      },
      fontSize: {
        "h1": "var(--text-h1)",
        "h2": "var(--text-h2)",
        "h3": "var(--text-h3)",
        "body": "var(--text-body)",
        "small": "var(--text-small)",
        "caption": "var(--text-caption)",
      },
      borderRadius: {
        "sm": "var(--radius-sm)",
        "md": "var(--radius-md)",
        "lg": "var(--radius-lg)",
        "full": "var(--radius-full)",
      },
      boxShadow: {
        "card": "var(--shadow-card)",
        "hover": "var(--shadow-hover)",
      },
    },
  },
  plugins: [],
};
export default config;
