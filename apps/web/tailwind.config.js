/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Colour carries meaning only (docs/01 §5): controllable, uncontrollable, residual, recovered.
      colors: {
        controllable: "#c2410c",
        uncontrollable: "#475569",
        residual: "#a16207",
        recovered: "#15803d",
      },
    },
  },
  plugins: [],
};
