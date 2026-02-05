/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        golf: {
          50: '#F3F1EC',
          100: '#E8E4DA',
          200: '#F3F1EC',
          300: '#F3F1EC',
          400: '#E6C36A',
          500: '#E6C36A',
          600: '#C9A84E',
          700: '#C9A84E',
          800: '#0F3B2E',
          900: '#0A241C',
          950: '#0F3B2E'
        }
      },
      fontFamily: {
        sans: ['Bebas Neue', 'sans-serif']
      }
    }
  },
  plugins: []
}
