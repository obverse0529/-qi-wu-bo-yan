/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef7ee',
          100: '#fdedd3',
          200: '#fad7a5',
          300: '#f5b96d',
          400: '#f19233',
          500: '#ee7a12',
          600: '#dc5f0d',
          700: '#b74610',
          800: '#933414',
          900: '#782a12',
        },
        museum: {
          gold: '#C9A962',
          bronze: '#8B6914',
          jade: '#3D8B37',
          porcelain: '#87CEEB',
        },
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
