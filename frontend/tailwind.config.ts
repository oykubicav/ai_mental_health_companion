import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cbt: {
          // === LIGHT === (default)
          bg: "#FBFBFB",
          surface: "#FFFFFF",
          surfaceMuted: "#F5F5F7",
          border: "#E8E8ED",
          borderStrong: "#D2D2D7",
          text: "#1D1D1F",
          textSecondary: "#515154",
          textMuted: "#86868B",
          accent: "#0A7A6E",
          accentHover: "#095F55",
          accentSoft: "#E6F4F1",
          warning: "#B8611E",
          warningSoft: "#FBEBD9",
          danger: "#A02A2A",
          dangerSoft: "#FBE7E7",
          success: "#1E7A3D",
          successSoft: "#E5F4EA",
          userBubble: "#F0EDE6",
          userBubbleText: "#1D1D1F",
          assistantBubble: "#FFFFFF",

          // === DARK === (used with dark: variant)
          dark: {
            bg: "#000000",              // pure black (Apple OLED style)
            surface: "#1C1C1E",         // elevated cards
            surfaceMuted: "#2C2C2E",    // recessed input, hover
            border: "#38383A",
            borderStrong: "#48484A",
            text: "#F5F5F7",
            textSecondary: "#AEAEB2",
            textMuted: "#8E8E93",
            accent: "#30D5C8",          // brighter teal in dark
            accentHover: "#5EE1D5",
            accentSoft: "rgba(48, 213, 200, 0.15)",
            warning: "#FF9F0A",
            warningSoft: "rgba(255, 159, 10, 0.15)",
            danger: "#FF453A",
            dangerSoft: "rgba(255, 69, 58, 0.15)",
            success: "#30D158",
            successSoft: "rgba(48, 209, 88, 0.15)",
            userBubble: "#2C2C2E",
            userBubbleText: "#F5F5F7",
            assistantBubble: "#1C1C1E",
          },
        },
      },
      fontFamily: {
        sans: [
          "var(--font-inter)",
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        display: [
          "var(--font-display)",
          "Georgia",
          "Times New Roman",
          "serif",
        ],
      },
      fontSize: {
        xs: ["11px", { lineHeight: "16px", letterSpacing: "0.01em" }],
        sm: ["13px", { lineHeight: "18px", letterSpacing: "-0.005em" }],
        base: ["15px", { lineHeight: "22px", letterSpacing: "-0.011em" }],
        lg: ["17px", { lineHeight: "24px", letterSpacing: "-0.015em" }],
        xl: ["20px", { lineHeight: "26px", letterSpacing: "-0.02em" }],
        "2xl": ["24px", { lineHeight: "30px", letterSpacing: "-0.024em" }],
        "3xl": ["30px", { lineHeight: "36px", letterSpacing: "-0.028em" }],
        "4xl": ["40px", { lineHeight: "48px", letterSpacing: "-0.032em" }],
        "5xl": ["56px", { lineHeight: "60px", letterSpacing: "-0.036em" }],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 3px 0 rgba(0, 0, 0, 0.03)",
        soft: "0 2px 4px -1px rgba(0, 0, 0, 0.04), 0 4px 6px -1px rgba(0, 0, 0, 0.05)",
        elevated: "0 4px 12px -2px rgba(0, 0, 0, 0.06), 0 10px 20px -4px rgba(0, 0, 0, 0.05)",
        modal: "0 20px 60px -12px rgba(0, 0, 0, 0.18), 0 8px 20px -8px rgba(0, 0, 0, 0.10)",
        glow: "0 0 30px -8px rgba(10, 122, 110, 0.35)",
      },
      borderRadius: {
        DEFAULT: "8px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        "2xl": "22px",
        "3xl": "28px",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        modalIn: {
          "0%": { opacity: "0", transform: "scale(0.96) translateY(8px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        heroIn: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInLeft: {
          "0%": { opacity: "0", transform: "translateX(-12px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        stepIn: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        drift: {
          "0%, 100%": { transform: "translate3d(0, 0, 0) scale(1)" },
          "50%": { transform: "translate3d(4%, -6%, 0) scale(1.08)" },
        },
        driftAlt: {
          "0%, 100%": { transform: "translate3d(0, 0, 0) scale(1)" },
          "50%": { transform: "translate3d(-5%, 5%, 0) scale(0.94)" },
        },
        caret: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fadeIn 200ms ease-out",
        "slide-up": "slideUp 260ms cubic-bezier(0.16, 1, 0.3, 1)",
        "modal-in": "modalIn 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "hero-in": "heroIn 600ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-left": "slideInLeft 220ms cubic-bezier(0.16, 1, 0.3, 1)",
        "step-in": "stepIn 420ms cubic-bezier(0.16, 1, 0.3, 1) both",
        drift: "drift 18s ease-in-out infinite",
        "drift-alt": "driftAlt 22s ease-in-out infinite",
        caret: "caret 1s steps(1) infinite",
      },
      backdropBlur: {
        xs: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
