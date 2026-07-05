import { ref } from 'vue'

// The title shown in the slim mobile header on drill-down pages (product, order, …). A detail page
// sets it in setup and clears it on unmount; ShopLayout's header reads it. Empty → the bar is just
// back + cart.
export const pageTitle = ref('')
