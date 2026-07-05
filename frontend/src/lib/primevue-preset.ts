// Dark mode follows our own `[data-theme="dark"]` selector so the header toggle drives PrimeVue too.
import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

export const ArvelPreset = definePreset(Aura, {
  semantic: {
    // Amber #B45309 — a tonal amber scale (500 is the text-safe brand accent)
    primary: {
      50: '#FDF4E7',
      100: '#F9E3C4',
      200: '#F2C98D',
      300: '#EAAC55',
      400: '#D97A08',
      500: '#B45309',
      600: '#9A4708',
      700: '#8F4A05',
      800: '#6E3904',
      900: '#4C2803',
      950: '#2B1702'
    },
    focusRing: { width: '2px', style: 'solid', offset: '2px' },
    colorScheme: {
      light: {
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.400}',
          activeColor: '{primary.700}'
        },
        // warm paper neutrals
        surface: {
          0: '#ffffff',
          50: '#F7F6F3',
          100: '#F1EFEB',
          200: '#E8E6E0',
          300: '#D6D3CB',
          400: '#B3AFA6',
          500: '#8B887E',
          600: '#6E6B62',
          700: '#54524B',
          800: '#3A3833',
          900: '#232220',
          950: '#151412'
        },
        content: { background: '#ffffff', borderColor: '#E8E6E0' },
        text: { color: '#18181B', mutedColor: '#54555A' }
      },
      dark: {
        primary: {
          color: '#E8A33D',
          contrastColor: '#201503',
          hoverColor: '#F2B65A',
          activeColor: '#D18F26'
        },
        // warm graphite
        surface: {
          0: '#F0EEE8',
          50: '#D8D5CE',
          100: '#ACA79D',
          200: '#8B867C',
          300: '#5C584F',
          400: '#3B372F',
          500: '#2E2B26',
          600: '#262420',
          700: '#1D1C19',
          800: '#191815',
          900: '#151412',
          950: '#100F0E'
        },
        content: { background: '#1D1C19', borderColor: '#2E2B26' },
        text: { color: '#F0EEE8', mutedColor: '#ACA79D' }
      }
    }
  }
})
