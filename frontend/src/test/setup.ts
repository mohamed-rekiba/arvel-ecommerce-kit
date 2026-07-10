// vitest setupFiles entry — registers PrimeVue + an in-memory vue-router globally so
// RouterLink/useRoute/useRouter resolve for every mounted component (K8). Real router over a
// global stub keeps router-dependent rendering faithful (architecture doc §1).
//
// ponytail: no top-level `await router.isReady()` here — the router's initial navigation only
// fires once it's installed on an app (mount() does that via config.global.plugins) or once a
// push()/replace() runs; awaiting isReady() before either happens never resolves (hangs forever).
import { config } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PrimeVue from 'primevue/config'

// Route names/paths mirror src/router.ts's shop routes — enough for RouterLink resolution and
// the named-route pushes the views themselves perform (e.g. ProductDetailView's goBack()).
export const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'home', component: { template: '<div />' } },
    { path: '/catalog', name: 'catalog', component: { template: '<div />' } },
    { path: '/products/:slug', name: 'product', component: { template: '<div />' } },
    { path: '/cart', name: 'cart', component: { template: '<div />' } },
    { path: '/checkout', name: 'checkout', component: { template: '<div />' } },
    { path: '/orders/:id', name: 'order', component: { template: '<div />' } },
    { path: '/account', name: 'account', component: { template: '<div />' } }
  ]
})

config.global.plugins.push(router)
config.global.plugins.push(PrimeVue)
