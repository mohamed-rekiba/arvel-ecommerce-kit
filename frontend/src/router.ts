import { createRouter, createWebHistory } from 'vue-router'
import { installViewTransitions } from './lib/transitions'
import ShopLayout from './shop/ShopLayout.vue'
import HomeView from './shop/views/HomeView.vue'

// The shell (ShopLayout) and the landing page (HomeView) load eagerly for a fast first paint;
// every other storefront view is lazy, so a home visitor downloads only those two and each route
// (catalog, product, cart, checkout, account, …) arrives on navigation.
const shop = {
  catalog: () => import('./shop/views/CatalogView.vue'),
  deals: () => import('./shop/views/DealsView.vue'),
  product: () => import('./shop/views/ProductDetailView.vue'),
  cart: () => import('./shop/views/CartView.vue'),
  checkout: () => import('./shop/views/CheckoutView.vue'),
  order: () => import('./shop/views/OrderDetailView.vue'),
  forgotPassword: () => import('./shop/views/ForgotPasswordView.vue'),
  resetPassword: () => import('./shop/views/ResetPasswordView.vue'),
  verifyEmail: () => import('./shop/views/VerifyEmailView.vue'),
  accountLayout: () => import('./shop/views/account/AccountLayout.vue'),
  profile: () => import('./shop/views/account/ProfilePane.vue'),
  accountOrders: () => import('./shop/views/account/OrdersPane.vue'),
  addresses: () => import('./shop/views/account/AddressesPane.vue'),
  wishlist: () => import('./shop/views/account/WishlistPane.vue'),
  security: () => import('./shop/views/account/SecurityPane.vue'),
  notifications: () => import('./shop/views/account/NotificationsPane.vue')
}

// Lazy-loaded so a storefront visitor never downloads the admin chunk (Keycloak/OIDC client included).
const admin = {
  layout: () => import('./admin/AdminLayout.vue'),
  login: () => import('./admin/views/LoginView.vue'),
  callback: () => import('./admin/views/CallbackView.vue'),
  dashboard: () => import('./admin/views/DashboardView.vue'),
  products: () => import('./admin/views/ProductsView.vue'),
  deals: () => import('./admin/views/DealsView.vue'),
  banners: () => import('./admin/views/BannersView.vue'),
  coupons: () => import('./admin/views/CouponsView.vue'),
  productEdit: () => import('./admin/views/ProductEditView.vue'),
  categories: () => import('./admin/views/CategoriesView.vue'),
  categoryEdit: () => import('./admin/views/CategoryEditView.vue'),
  couponEdit: () => import('./admin/views/CouponEditView.vue'),
  dealEdit: () => import('./admin/views/DealEditView.vue'),
  bannerEdit: () => import('./admin/views/BannerEditView.vue'),
  vendorEdit: () => import('./admin/views/VendorEditView.vue'),
  vendors: () => import('./admin/views/VendorsView.vue'),
  users: () => import('./admin/views/UsersView.vue'),
  orderDetail: () => import('./admin/views/OrderDetailView.vue'),
  reviews: () => import('./admin/views/ReviewsView.vue'),
  orders: () => import('./admin/views/OrdersView.vue'),
  roles: () => import('./admin/views/RolesView.vue'),
  audit: () => import('./admin/views/AuditView.vue'),
  media: () => import('./admin/views/MediaView.vue'),
  settings: () => import('./admin/views/SettingsView.vue'),
  newsletter: () => import('./admin/views/NewsletterView.vue')
}

const router = createRouter({
  history: createWebHistory(),
  // Restore scroll on back/forward, or every back-nav loses your place.
  scrollBehavior: (_to, _from, savedPosition) => savedPosition ?? { top: 0 },
  routes: [
    {
      path: '/',
      component: ShopLayout,
      children: [
        { path: '', name: 'home', component: HomeView },
        { path: 'catalog', name: 'catalog', component: shop.catalog },
        { path: 'deals', name: 'deals', component: shop.deals },
        {
          path: 'products/:slug',
          name: 'product',
          component: shop.product,
          meta: { detail: true }
        },
        { path: 'cart', name: 'cart', component: shop.cart },
        {
          path: 'checkout',
          name: 'checkout',
          component: shop.checkout,
          meta: { detail: true }
        },
        {
          path: 'orders/:id',
          name: 'order',
          component: shop.order,
          meta: { detail: true }
        },
        {
          path: 'account',
          component: shop.accountLayout,
          children: [
            {
              path: '',
              name: 'account',
              redirect: { path: '/account/profile' }
            },
            {
              path: 'profile',
              name: 'account-profile',
              component: shop.profile
            },
            { path: 'orders', name: 'account-orders', component: shop.accountOrders },
            {
              path: 'addresses',
              name: 'account-addresses',
              component: shop.addresses
            },
            {
              path: 'wishlist',
              name: 'account-wishlist',
              component: shop.wishlist
            },
            {
              path: 'security',
              name: 'account-security',
              component: shop.security
            },
            {
              path: 'notifications',
              name: 'account-notifications',
              component: shop.notifications
            }
          ]
        },
        {
          path: 'forgot-password',
          name: 'forgot-password',
          component: shop.forgotPassword,
          meta: { detail: true }
        },
        {
          path: 'reset-password',
          name: 'reset-password',
          component: shop.resetPassword,
          meta: { detail: true }
        },
        {
          path: 'verify-email',
          name: 'verify-email',
          component: shop.verifyEmail,
          meta: { detail: true }
        }
      ]
    },
    // pre-auth admin routes live outside the AdminLayout shell
    { path: '/admin/login', component: admin.login },
    { path: '/admin/callback', component: admin.callback },
    {
      path: '/admin',
      component: admin.layout,
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: admin.dashboard },
        { path: 'products', component: admin.products },
        { path: 'deals', component: admin.deals },
        { path: 'banners', component: admin.banners },
        { path: 'coupons', component: admin.coupons },
        { path: 'products/:id', component: admin.productEdit },
        { path: 'categories', component: admin.categories },
        { path: 'categories/:id', component: admin.categoryEdit },
        { path: 'coupons/:id', component: admin.couponEdit },
        { path: 'deals/:id', component: admin.dealEdit },
        { path: 'banners/:id', component: admin.bannerEdit },
        { path: 'vendors', component: admin.vendors },
        { path: 'vendors/:id', component: admin.vendorEdit },
        { path: 'users', component: admin.users },
        { path: 'reviews', component: admin.reviews },
        { path: 'orders', component: admin.orders },
        { path: 'orders/:id', component: admin.orderDetail },
        { path: 'media', component: admin.media },
        { path: 'settings', component: admin.settings },
        { path: 'newsletter', component: admin.newsletter },
        { path: 'roles', component: admin.roles },
        { path: 'audit', component: admin.audit }
      ]
    }
  ]
})

// Reads the token key directly (no admin import) so the admin bundle stays out of the main chunk.
router.beforeEach((to) => {
  const isAdminApp = to.path.startsWith('/admin')
  const isPublic = to.path === '/admin/login' || to.path === '/admin/callback'
  if (isAdminApp && !isPublic && !localStorage.getItem('arvel_admin_token')) {
    return { path: '/admin/login' }
  }
  return true
})

installViewTransitions(router)

export default router
