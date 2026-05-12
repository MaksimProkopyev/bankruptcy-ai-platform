import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: "#1B3A5C",
        gold: "#C9A84C",
        "warm-white": "#F8F7F4",
      },
      fontFamily: {
        heading: ["Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
export default config;
