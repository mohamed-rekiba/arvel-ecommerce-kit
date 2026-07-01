import { createRouter, createWebHistory } from "vue-router";
import { installViewTransitions } from "./lib/transitions";
import ShopLayout from "./shop/ShopLayout.vue";
import HomeView from "./shop/views/HomeView.vue";
import CatalogView from "./shop/views/CatalogView.vue";
import ProductDetailView from "./shop/views/ProductDetailView.vue";
import CartView from "./shop/views/CartView.vue";
import CheckoutView from "./shop/views/CheckoutView.vue";
import AccountView from "./shop/views/AccountView.vue";

// The admin section is lazy-loaded — a separate chunk (with its Keycloak/OIDC client) that a storefront
// visitor never downloads. `manualChunks` in vite.config groups all of src/admin/* into one `admin` chunk.
const admin = {
  layout: () => import("./admin/AdminLayout.vue"),
  login: () => import("./admin/views/LoginView.vue"),
  callback: () => import("./admin/views/CallbackView.vue"),
  dashboard: () => import("./admin/views/DashboardView.vue"),
  products: () => import("./admin/views/ProductsView.vue"),
  orders: () => import("./admin/views/OrdersView.vue"),
  roles: () => import("./admin/views/RolesView.vue"),
  audit: () => import("./admin/views/AuditView.vue"),
};

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: "/",
      component: ShopLayout,
      children: [
        { path: "", name: "home", component: HomeView },
        { path: "catalog", name: "catalog", component: CatalogView },
        { path: "products/:slug", name: "product", component: ProductDetailView },
        { path: "cart", name: "cart", component: CartView },
        { path: "checkout", name: "checkout", component: CheckoutView },
        { path: "account", name: "account", component: AccountView },
      ],
    },
    // pre-auth admin routes live outside the AdminLayout shell
    { path: "/admin/login", component: admin.login },
    { path: "/admin/callback", component: admin.callback },
    {
      path: "/admin",
      component: admin.layout,
      children: [
        { path: "", redirect: "/admin/dashboard" },
        { path: "dashboard", component: admin.dashboard },
        { path: "products", component: admin.products },
        { path: "orders", component: admin.orders },
        { path: "roles", component: admin.roles },
        { path: "audit", component: admin.audit },
      ],
    },
  ],
});

// Bearer guard for the console. Read the token key directly (no admin import) so the admin bundle stays
// out of the main chunk; the server still enforces RBAC on every /api/admin call.
router.beforeEach((to) => {
  const isAdminApp = to.path.startsWith("/admin");
  const isPublic = to.path === "/admin/login" || to.path === "/admin/callback";
  if (isAdminApp && !isPublic && !localStorage.getItem("arvel_admin_token")) {
    return { path: "/admin/login" };
  }
  return true;
});

installViewTransitions(router); // cross-fade + shared-element morphs between routes

export default router;
