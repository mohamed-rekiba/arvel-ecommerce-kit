import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import "./tokens.css";
import App from "./App.vue";
import AccountView from "./views/AccountView.vue";
import CartView from "./views/CartView.vue";
import CatalogView from "./views/CatalogView.vue";
import CheckoutView from "./views/CheckoutView.vue";
import ProductDetailView from "./views/ProductDetailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "catalog", component: CatalogView },
    { path: "/products/:slug", name: "product", component: ProductDetailView },
    { path: "/cart", name: "cart", component: CartView },
    { path: "/checkout", name: "checkout", component: CheckoutView },
    { path: "/account", name: "account", component: AccountView },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

createApp(App).use(router).mount("#app");
