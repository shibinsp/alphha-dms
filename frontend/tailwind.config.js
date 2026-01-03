/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1E3A5F',
          50: '#E8EDF3',
          100: '#C5D3E3',
          200: '#9FB8D0',
          300: '#799DBD',
          400: '#5382AA',
          500: '#1E3A5F',
          600: '#1A3354',
          700: '#152B47',
          800: '#11233A',
          900: '#0D1B2D',
        },
        secondary: {
          DEFAULT: '#2E7D32',
          50: '#E8F5E9',
          100: '#C8E6C9',
          200: '#A5D6A7',
          300: '#81C784',
          400: '#66BB6A',
          500: '#2E7D32',
          600: '#27692A',
          700: '#1F5522',
          800: '#17411A',
          900: '#0F2D12',
        },
        accent: {
          DEFAULT: '#B8860B',
          50: '#FDF5E1',
          100: '#F9E6B3',
          200: '#F5D685',
          300: '#F1C757',
          400: '#EDB729',
          500: '#B8860B',
          600: '#9A7009',
          700: '#7C5A07',
          800: '#5E4405',
          900: '#402E03',
        },
        surface: '#FFFFFF',
        background: '#F5F7FA',
        error: '#D32F2F',
        warning: '#FFA000',
        success: '#388E3C',
      },
      fontFamily: {
        sans: ['Inter', 'Roboto', 'sans-serif'],
        heading: ['Poppins', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false, // Disable to avoid conflicts with Ant Design
  },
}
