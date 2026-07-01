// PrimeVue theme preset mapped to the arvel-ecommerce-kit "Boutique" palette (see styles/tokens.css /
// DESIGN.md): plum (Royal Scepter) primary, warm-greige surfaces in light, Blue Noir in dark. Dark mode
// follows our own `[data-theme="dark"]` selector so the header toggle drives PrimeVue too.
import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

export const ArvelPreset = definePreset(Aura, {
  semantic: {
    // Royal Scepter #795663 — a tonal plum scale
    primary: {
      50: "#F5EEF1",
      100: "#E7D9DF",
      200: "#D3BAC5",
      300: "#BC9AAB",
      400: "#9E7285",
      500: "#795663",
      600: "#674654",
      700: "#543A46",
      800: "#412D37",
      900: "#2E2027",
      950: "#1B1318",
    },
    focusRing: { width: "2px", style: "solid", offset: "2px" },
    colorScheme: {
      light: {
        primary: {
          color: "{primary.500}",
          contrastColor: "#ffffff",
          hoverColor: "{primary.400}",
          activeColor: "{primary.600}",
        },
        // warm greige neutrals
        surface: {
          0: "#ffffff",
          50: "#FBF8F5",
          100: "#F3EDE7",
          200: "#E7DFD7",
          300: "#D8CEC4",
          400: "#B7ABA0",
          500: "#8C8177",
          600: "#6E645B",
          700: "#554D46",
          800: "#3A342F",
          900: "#241F1B",
          950: "#17130F",
        },
        content: { background: "#ffffff", borderColor: "#E7DFD7" },
        text: { color: "#12212E", mutedColor: "#55625D" },
      },
      dark: {
        primary: {
          color: "{primary.300}",
          contrastColor: "#160E13",
          hoverColor: "{primary.200}",
          activeColor: "{primary.400}",
        },
        // Blue Noir base
        surface: {
          0: "#EDE4DE",
          50: "#CBD2D8",
          100: "#A6B0BF",
          200: "#79857D",
          300: "#4A5A66",
          400: "#33465A",
          500: "#22415A",
          600: "#173247",
          700: "#132B3D",
          800: "#0B2030",
          900: "#06192A",
          950: "#011627",
        },
        content: { background: "#0B2030", borderColor: "#173247" },
        text: { color: "#EDE4DE", mutedColor: "#9DA8A0" },
      },
    },
  },
});
