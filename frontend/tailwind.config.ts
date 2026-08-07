import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        border: "hsl(var(--border))",
        ring: "hsl(var(--ring))",
        /* Remapped for light burgundy theme — class names kept for existing UI */
        charcoal: {
          50: "#141010",
          100: "#1f1818",
          200: "#3d3232",
          300: "#5c4f4f",
          400: "#7a6b6b",
          500: "#9a8a8a",
          600: "#c4b8b8",
          700: "#ddd4d4",
          800: "#eee9e9",
          900: "#f7f4f4",
          950: "#ffffff",
        },
        citrus: {
          50: "#fef2f2",
          100: "#fde3e3",
          200: "#fbb6b6",
          300: "#c51414",
          400: "#b01212",
          500: "#9a1010",
          600: "#7f0e0e",
          700: "#680c0c",
          800: "#520a0a",
          900: "#3d0808",
        },
        burgundy: {
          DEFAULT: "#c51414",
          50: "#fef2f2",
          100: "#fde3e3",
          200: "#fbb6b6",
          300: "#e85a5a",
          400: "#d42b2b",
          500: "#c51414",
          600: "#b01212",
          700: "#9a1010",
          800: "#7f0e0e",
          900: "#520a0a",
        },
      },
      fontFamily: {
        display: ["var(--font-crimson)", "Georgia", "serif"],
        sans: ["var(--font-oswald)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 1px)",
        sm: "calc(var(--radius) - 2px)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s ease-out forwards",
        "fade-in": "fade-in 0.4s ease-out forwards",
        shimmer: "shimmer 2s linear infinite",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
      boxShadow: {
        deal: "0 4px 8px 0 rgba(0, 0, 0, 0.12), 0 6px 20px 0 rgba(0, 0, 0, 0.1)",
      },
    },
  },
  plugins: [],
};

export default config;
