module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './**/*.py'
  ],
  theme: {
    extend: {
      colors: {
        'brand-green': '#56C02B',
        'brand-green-dark': '#4F8B3C',
        'brand-turquoise': '#2DD4BF',
        'brand-orange': '#FB923C',
        'brand-raspberry': '#EC4899',
        'brand-yellow': '#FBBF24',
      },
    },
  },
  plugins: [],
}
