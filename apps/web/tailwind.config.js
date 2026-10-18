/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // Industrial light theme: cool steel neutrals, one control-room blue, reserved status colours.
        plane: "#f3f5f8",
        surface: "#ffffff",
        line: "#e2e6ec",
        "line-strong": "#c9d0da",
        ink: { DEFAULT: "#101826", 2: "#3b4656", 3: "#6b7686", 4: "#98a1ae" },
        steel: { 50: "#f6f8fb", 100: "#eef1f5", 200: "#dfe4eb", 300: "#c5cdd8", 600: "#4a5668", 800: "#1e2836", 900: "#121a26" },
        brand: { 50: "#eef5fd", 100: "#cde2fb", 500: "#2a78d6", 600: "#1c5cab", 700: "#184f95", 800: "#0d366b" },
        good: { DEFAULT: "#0ca30c", ink: "#006300", bg: "#eaf6ea" },
        warning: { DEFAULT: "#fab219", ink: "#8a5a00", bg: "#fff6e0" },
        serious: { DEFAULT: "#ec835a", ink: "#9a3d14", bg: "#fdeee7" },
        critical: { DEFAULT: "#d03b3b", ink: "#9f1f1f", bg: "#fcebeb" },
        // Chart roles (validated categorical slots 1–3, dataviz reference palette)
        series: { 1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a" },
        // Loss colours carry meaning only (docs/01 §5)
        controllable: "#eb6834",
        uncontrollable: "#6250d6",
        residual: "#898781",
        recovered: "#1baf7a",
      },
      boxShadow: {
        card: "0 1px 0 rgba(16,24,38,0.04), 0 1px 2px rgba(16,24,38,0.06)",
        pop: "0 8px 24px rgba(16,24,38,0.12)",
      },
      borderRadius: { xl: "10px" },
    },
  },
  plugins: [],
};
