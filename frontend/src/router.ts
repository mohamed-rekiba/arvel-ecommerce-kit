import { createRouter, createWebHistory } from "vue-router";
import ShopLayout from "./shop/ShopLayout.vue";
import DealsView from "./shop/views/DealsView.vue";
import HomeView from "./shop/views/HomeView.vue";
import CatalogView from "./shop/views/CatalogView.vue";
import ProductDetailView from "./shop/views/ProductDetailView.vue";
import CartView from "./shop/views/CartView.vue";
import CheckoutView from "./shop/views/CheckoutView.vue";
import OrderDetailView from "./shop/views/OrderDetailView.vue";
import ForgotPasswordView from "./shop/views/ForgotPasswordView.vue";
import ResetPasswordView from "./shop/views/ResetPasswordView.vue";
import VerifyEmailView from "./shop/views/VerifyEmailView.vue";
import AccountLayout from "./shop/views/account/AccountLayout.vue";
import ProfilePane from "./shop/views/account/ProfilePane.vue";
import OrdersPane from "./shop/views/account/OrdersPane.vue";
import AddressesPane from "./shop/views/account/AddressesPane.vue";
import WishlistPane from "./shop/views/account/WishlistPane.vue";
import SecurityPane from "./shop/views/account/SecurityPane.vue";
import NotificationsPane from "./shop/views/account/NotificationsPane.vue";

// The admin section is lazy-loaded — a separate chunk (with its Keycloak/OIDC client) that a storefront
// visitor never downloads. `manualChunks` in vite.config groups all of src/admin/* into one `admin` chunk.
const admin = {
  layout: () => import("./admin/AdminLayout.vue"),
  login: () => import("./admin/views/LoginView.vue"),
  callback: () => import("./admin/views/CallbackView.vue"),
  dashboard: () => import("./admin/views/DashboardView.vue"),
  products: () => import("./admin/views/ProductsView.vue"),
  deals: () => import("./admin/views/DealsView.vue"),
  banners: () => import("./admin/views/BannersView.vue"),
  coupons: () => import("./admin/views/CouponsView.vue"),
  productEdit: () => import("./admin/views/ProductEditView.vue"),
  categories: () => import("./admin/views/CategoriesView.vue"),
  vendors: () => import("./admin/views/VendorsView.vue"),
  users: () => import("./admin/views/UsersView.vue"),
  orderDetail: () => import("./admin/views/OrderDetailView.vue"),
  reviews: () => import("./admin/views/ReviewsView.vue"),
  orders: () => import("./admin/views/OrdersView.vue"),
  roles: () => import("./admin/views/RolesView.vue"),
  audit: () => import("./admin/views/AuditView.vue"),
  media: () => import("./admin/views/MediaView.vue"),
  settings: () => import("./admin/views/SettingsView.vue"),
  newsletter: () => import("./admin/views/NewsletterView.vue"),
};

// Real continuity is "I drilled into a product, hit back, land where I was" — that holds
// no matter which page you drilled in from (home's featured/deals rail, catalog, the
// wishlist table). It's keyed on the page you're LEAVING, not the one you're landing on:
// a lateral nav (tab bar, footer link) away from any page never touches the PDP, so it
// still resets to top — restoring an unrelated saved scroll there reads as breakage.
const RESTORE_SCROLL_FROM = new Set(["product"]);

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (_to, from, savedPosition) =>
    savedPosition && RESTORE_SCROLL_FROM.has(String(from.name)) ? savedPosition : { top: 0 },
  routes: [
    {
      path: "/",
      component: ShopLayout,
      children: [
        { path: "", name: "home", component: HomeView },
        { path: "catalog", name: "catalog", component: CatalogView },
        { path: "deals", name: "deals", component: DealsView },
        { path: "products/:slug", name: "product", component: ProductDetailView },
        { path: "cart", name: "cart", component: CartView },
        { path: "checkout", name: "checkout", component: CheckoutView },
        { path: "orders/:id", name: "order", component: OrderDetailView },
        {
          path: "account",
          component: AccountLayout,
          children: [
            { path: "", name: "account", redirect: { path: "/account/profile" } },
            { path: "profile", name: "account-profile", component: ProfilePane },
            { path: "orders", name: "account-orders", component: OrdersPane },
            { path: "addresses", name: "account-addresses", component: AddressesPane },
            { path: "wishlist", name: "account-wishlist", component: WishlistPane },
            { path: "security", name: "account-security", component: SecurityPane },
            { path: "notifications", name: "account-notifications", component: NotificationsPane },
          ],
        },
        { path: "forgot-password", name: "forgot-password", component: ForgotPasswordView },
        { path: "reset-password", name: "reset-password", component: ResetPasswordView },
        { path: "verify-email", name: "verify-email", component: VerifyEmailView },
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
      { path: "deals", component: admin.deals },
      { path: "banners", component: admin.banners },
      { path: "coupons", component: admin.coupons },
        { path: "products/:id", component: admin.productEdit },
        { path: "categories", component: admin.categories },
        { path: "vendors", component: admin.vendors },
        { path: "users", component: admin.users },
        { path: "reviews", component: admin.reviews },
        { path: "orders", component: admin.orders },
        { path: "orders/:id", component: admin.orderDetail },
        { path: "media", component: admin.media },
        { path: "settings", component: admin.settings },
        { path: "newsletter", component: admin.newsletter },
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

export default router;
