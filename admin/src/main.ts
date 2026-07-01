import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import "./tokens.css";
import App from "./App.vue";
import { token } from "./api";
import AuditView from "./views/AuditView.vue";
import CallbackView from "./views/CallbackView.vue";
import DashboardView from "./views/DashboardView.vue";
import LoginView from "./views/LoginView.vue";
import OrdersView from "./views/OrdersView.vue";
import ProductsView from "./views/ProductsView.vue";
import RolesView from "./views/RolesView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/callback", name: "callback", component: CallbackView, meta: { public: true } },
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", name: "dashboard", component: DashboardView },
    { path: "/products", name: "products", component: ProductsView },
    { path: "/orders", name: "orders", component: OrdersView },
    { path: "/roles", name: "roles", component: RolesView },
    { path: "/audit", name: "audit", component: AuditView },
  ],
});

// Auth guard: unauthenticated users go to /login; authenticated users skip the login page.
router.beforeEach((to) => {
  const authed = !!token.get();
  if (!to.meta.public && !authed) return { name: "login" };
  if (to.name === "login" && authed) return { name: "products" };
  return true;
});

createApp(App).use(router).mount("#app");
