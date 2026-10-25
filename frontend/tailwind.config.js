/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Professional corporate brand palette
        brand: {
          50: '#f4f7fa',
          100: '#e6edf5',
          200: '#ccdbe9',
          300: '#99b8d6',
          400: '#6694c3',
          500: '#3371b0', // Primary Accent
          600: '#2b6cb0',
          700: '#23538c',
          800: '#1a3c68',
          900: '#112544',
        },
        slate: {
          950: '#070a13', // Deep slate for dark mode background
        }
      },
      fontFamily: {
        sans: ['Inter', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
