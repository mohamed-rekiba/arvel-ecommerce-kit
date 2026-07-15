import type {
  ActivityOut,
  AddItemIn,
  AdminBannerOut,
  AdminCategoryOut,
  AdminCategoryPage,
  AdminCouponOut,
  AdminDealOut,
  AdminMeOut,
  AdminOrderDetailOut,
  AdminProductDetailOut,
  AdminProductOut,
  AdminProductPage,
  AdminReviewOut,
  AdminUserDetailOut,
  AdminUserPage,
  AdminVendorOut,
  AiMcpMetadata200,
  AnnouncementOut,
  ApiAccountAddressesDestroy200,
  ApiAccountAddressesDestroy400,
  ApiAccountAddressesUpdate400,
  ApiAdminBannersDestroy200,
  ApiAdminBannersDestroy400,
  ApiAdminBannersImage400,
  ApiAdminBannersUpdatePatch400,
  ApiAdminBannersUpdatePut400,
  ApiAdminCategoriesDestroy400,
  ApiAdminCategoriesIndex400,
  ApiAdminCategoriesIndexParams,
  ApiAdminCategoriesUpdatePatch400,
  ApiAdminCategoriesUpdatePut400,
  ApiAdminCouponsUpdatePatch400,
  ApiAdminCouponsUpdatePut400,
  ApiAdminDealsDestroy200,
  ApiAdminDealsDestroy400,
  ApiAdminDealsUpdatePatch400,
  ApiAdminDealsUpdatePut400,
  ApiAdminOrdersRefund400,
  ApiAdminOrdersShow400,
  ApiAdminOrdersStatus400,
  ApiAdminProductsCopyDraft400,
  ApiAdminProductsDestroy400,
  ApiAdminProductsImage400,
  ApiAdminProductsIndex400,
  ApiAdminProductsIndexParams,
  ApiAdminProductsMediaDestroy400,
  ApiAdminProductsRestore400,
  ApiAdminProductsShow400,
  ApiAdminProductsUpdatePatch400,
  ApiAdminProductsUpdatePut400,
  ApiAdminReviewsIndex400,
  ApiAdminReviewsIndexParams,
  ApiAdminReviewsModerate400,
  ApiAdminUsersIndex400,
  ApiAdminUsersIndexParams,
  ApiAdminUsersRoles400,
  ApiAdminUsersRolesAssign400,
  ApiAdminUsersRolesRevoke400,
  ApiAdminUsersShow400,
  ApiAdminVariantsDestroy400,
  ApiAdminVariantsIndex400,
  ApiAdminVariantsStock400,
  ApiAdminVariantsStore400,
  ApiAdminVariantsUpdate400,
  ApiAdminVendorsUpdatePatch400,
  ApiAdminVendorsUpdatePut400,
  ApiCartItemsRemove400,
  ApiCartItemsUpdate400,
  ApiMediaConversion400,
  ApiMediaShow400,
  ApiOrdersCancel400,
  ApiOrdersInvoice400,
  ApiOrdersPay400,
  ApiOrdersShow400,
  ApiProductsFeed400,
  ApiProductsFeedParams,
  ApiProductsIndex400,
  ApiProductsIndexParams,
  ApiProductsReviewsIndex400,
  ApiProductsReviewsStore400,
  ApiProductsShow400,
  ApiVariantsStockAlertSubscribe400,
  ApiVariantsStockAlertUnsubscribe400,
  ApiWishlistToggle400,
  ApplyCouponIn,
  AssignRoleIn,
  BannerIn,
  BannerOut,
  BannerUpdateIn,
  CartOut,
  CategoryIn,
  CategoryOut,
  CategoryUpdateIn,
  ChangePasswordIn,
  CheckoutIn,
  CopyDraft,
  CouponIn,
  CouponUpdateIn,
  CredentialsIn,
  DealIn,
  DealOut,
  DealUpdateIn,
  ForgotPasswordIn,
  ForgotPasswordOut,
  GalleryImageOut,
  HealthReport,
  LivenessStatus,
  MediaItemOut,
  MessageOut,
  MetricsOut,
  NewsletterIn,
  NewsletterSubscriberOut,
  NotificationOut,
  OrderOut,
  OrderStatusIn,
  PaymentOut,
  PermissionOut,
  ProductFeed,
  ProductIn,
  ProductOut,
  ProductPage,
  ProfileIn,
  RegisterIn,
  ResetPasswordIn,
  Response,
  ReviewIn,
  ReviewListOut,
  ReviewOut,
  RoleOut,
  SavedAddressIn,
  SavedAddressOut,
  SettingsIn,
  SettingsOut,
  ShippingMethodOut,
  StockAdjustIn,
  TokenOut,
  UpdateItemIn,
  UpdateProductIn,
  UserOut,
  UserRolesOut,
  VariantIn,
  VariantOut,
  VariantUpdateIn,
  VendorIn,
  VendorUpdateIn,
  VerifyEmailIn,
  WebhookIn,
  WebhookOut,
  WishlistToggleOut,
  _Public400
} from './models';

import { apiFetch } from '../http';
export type healthResponse200 = {
  data: HealthReport
  status: 200
}

export type healthResponseSuccess = (healthResponse200) & {
  headers: Headers;
};
;

export type healthResponse = (healthResponseSuccess)

export const getHealthUrl = () => {




  return `/health`
}

/**
 * Readiness: check every registered resource concurrently. ``200`` when nothing critical has
 * failed (degraded non-criticals included), ``503`` otherwise.
 * @summary Health
 */
export const health = async ( options?: RequestInit): Promise<healthResponse> => {

  return apiFetch<healthResponse>(getHealthUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type healthLiveResponse200 = {
  data: LivenessStatus
  status: 200
}

export type healthLiveResponseSuccess = (healthLiveResponse200) & {
  headers: Headers;
};
;

export type healthLiveResponse = (healthLiveResponseSuccess)

export const getHealthLiveUrl = () => {




  return `/livez`
}

/**
 * Process-is-alive. No dependency checks — always ``200`` while the worker can serve.
 * @summary HealthLive
 */
export const healthLive = async ( options?: RequestInit): Promise<healthLiveResponse> => {

  return apiFetch<healthLiveResponse>(getHealthLiveUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type broadcastingAuthResponse201 = {
  data: Response
  status: 201
}

export type broadcastingAuthResponseSuccess = (broadcastingAuthResponse201) & {
  headers: Headers;
};
;

export type broadcastingAuthResponse = (broadcastingAuthResponseSuccess)

export const getBroadcastingAuthUrl = () => {




  return `/broadcasting/auth`
}

/**
 * Resolve ``request``'s authenticated user + the requested channel, run its registered
 * authorization callback, and return the auth signature (private) or member data (presence).
 * 403 when the callback denies or no pattern matches.
 * @summary BroadcastingAuth
 */
export const broadcastingAuth = async ( options?: RequestInit): Promise<broadcastingAuthResponse> => {

  return apiFetch<broadcastingAuthResponse>(getBroadcastingAuthUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiLoginResponse200 = {
  data: TokenOut
  status: 200
}

export type apiLoginResponseSuccess = (apiLoginResponse200) & {
  headers: Headers;
};
;

export type apiLoginResponse = (apiLoginResponseSuccess)

export const getApiLoginUrl = () => {




  return `/api/login`
}

/**
 * Verify credentials and issue a personal access token (merging any guest cart the request
 * carries — build-a-cart-then-sign-in must never strand items).
 * @summary ApiLogin
 */
export const apiLogin = async (credentialsIn: CredentialsIn, options?: RequestInit): Promise<apiLoginResponse> => {

  return apiFetch<apiLoginResponse>(getApiLoginUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(credentialsIn)
  }
);}



export type apiUserResponse200 = {
  data: UserOut
  status: 200
}

export type apiUserResponseSuccess = (apiUserResponse200) & {
  headers: Headers;
};
;

export type apiUserResponse = (apiUserResponseSuccess)

export const getApiUserUrl = () => {




  return `/api/user`
}

/**
 * The authenticated user (requires a bearer token).
 * @summary ApiUser
 */
export const apiUser = async ( options?: RequestInit): Promise<apiUserResponse> => {

  return apiFetch<apiUserResponse>(getApiUserUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiUserUpdateResponse200 = {
  data: UserOut
  status: 200
}

export type apiUserUpdateResponseSuccess = (apiUserUpdateResponse200) & {
  headers: Headers;
};
;

export type apiUserUpdateResponse = (apiUserUpdateResponseSuccess)

export const getApiUserUpdateUrl = () => {




  return `/api/user`
}

/**
 * Update name/email/phone. Changing the email un-verifies the account and re-sends the
 * verification link to the NEW address.
 * @summary ApiUserUpdate
 */
export const apiUserUpdate = async (profileIn: ProfileIn, options?: RequestInit): Promise<apiUserUpdateResponse> => {

  return apiFetch<apiUserUpdateResponse>(getApiUserUpdateUrl(),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(profileIn)
  }
);}



export type apiRegisterResponse201 = {
  data: TokenOut
  status: 201
}

export type apiRegisterResponseSuccess = (apiRegisterResponse201) & {
  headers: Headers;
};
;

export type apiRegisterResponse = (apiRegisterResponseSuccess)

export const getApiRegisterUrl = () => {




  return `/api/register`
}

/**
 * Register a customer and issue a scoped API token.
 * @summary ApiRegister
 */
export const apiRegister = async (registerIn: RegisterIn, options?: RequestInit): Promise<apiRegisterResponse> => {

  return apiFetch<apiRegisterResponse>(getApiRegisterUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(registerIn)
  }
);}



export type apiLogoutResponse200 = {
  data: MessageOut
  status: 200
}

export type apiLogoutResponseSuccess = (apiLogoutResponse200) & {
  headers: Headers;
};
;

export type apiLogoutResponse = (apiLogoutResponseSuccess)

export const getApiLogoutUrl = () => {




  return `/api/logout`
}

/**
 * Revoke only the current token (Sanctum currentAccessToken()->delete()).
 * @summary ApiLogout
 */
export const apiLogout = async ( options?: RequestInit): Promise<apiLogoutResponse> => {

  return apiFetch<apiLogoutResponse>(getApiLogoutUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiPasswordForgotResponse200 = {
  data: ForgotPasswordOut
  status: 200
}

export type apiPasswordForgotResponseSuccess = (apiPasswordForgotResponse200) & {
  headers: Headers;
};
;

export type apiPasswordForgotResponse = (apiPasswordForgotResponseSuccess)

export const getApiPasswordForgotUrl = () => {




  return `/api/forgot-password`
}

/**
 * Store a single-use reset token and email its link. Always 200 (non-enumerating).
 * @summary ApiPasswordForgot
 */
export const apiPasswordForgot = async (forgotPasswordIn: ForgotPasswordIn, options?: RequestInit): Promise<apiPasswordForgotResponse> => {

  return apiFetch<apiPasswordForgotResponse>(getApiPasswordForgotUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(forgotPasswordIn)
  }
);}



export type apiPasswordResetResponse200 = {
  data: MessageOut
  status: 200
}

export type apiPasswordResetResponseSuccess = (apiPasswordResetResponse200) & {
  headers: Headers;
};
;

export type apiPasswordResetResponse = (apiPasswordResetResponseSuccess)

export const getApiPasswordResetUrl = () => {




  return `/api/reset-password`
}

/**
 * Consume the single-use reset token and set the new (hashed) password.
 * @summary ApiPasswordReset
 */
export const apiPasswordReset = async (resetPasswordIn: ResetPasswordIn, options?: RequestInit): Promise<apiPasswordResetResponse> => {

  return apiFetch<apiPasswordResetResponse>(getApiPasswordResetUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(resetPasswordIn)
  }
);}



export type apiEmailVerifyResponse200 = {
  data: MessageOut
  status: 200
}

export type apiEmailVerifyResponseSuccess = (apiEmailVerifyResponse200) & {
  headers: Headers;
};
;

export type apiEmailVerifyResponse = (apiEmailVerifyResponseSuccess)

export const getApiEmailVerifyUrl = () => {




  return `/api/email/verify`
}

/**
 * Mark the account verified from a signed token (purpose-bound: a reset token won't pass).
 * The token is bound to the email it was issued for, so it stops verifying once the address
 * changes — we load the user the link names, then check the token against their current email.
 * @summary ApiEmailVerify
 */
export const apiEmailVerify = async (verifyEmailIn: VerifyEmailIn, options?: RequestInit): Promise<apiEmailVerifyResponse> => {

  return apiFetch<apiEmailVerifyResponse>(getApiEmailVerifyUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(verifyEmailIn)
  }
);}



export type apiCategoriesIndexResponse200 = {
  data: CategoryOut[]
  status: 200
}

export type apiCategoriesIndexResponseSuccess = (apiCategoriesIndexResponse200) & {
  headers: Headers;
};
;

export type apiCategoriesIndexResponse = (apiCategoriesIndexResponseSuccess)

export const getApiCategoriesIndexUrl = () => {




  return `/api/categories`
}

/**
 * List **retrievable** categories — published, fully-published ancestor chain, and at least one
 * viewable product in the subtree (the retrievable_categories materialized view). Each carries a
 * derived ``image_url`` (a subtree product's thumb) for the storefront's category tiles.
 * @summary ApiCategoriesIndex
 */
export const apiCategoriesIndex = async ( options?: RequestInit): Promise<apiCategoriesIndexResponse> => {

  return apiFetch<apiCategoriesIndexResponse>(getApiCategoriesIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiProductsIndexResponse200 = {
  data: ProductPage
  status: 200
}

export type apiProductsIndexResponse400 = {
  data: ApiProductsIndex400
  status: 400
}

export type apiProductsIndexResponseSuccess = (apiProductsIndexResponse200) & {
  headers: Headers;
};
export type apiProductsIndexResponseError = (apiProductsIndexResponse400) & {
  headers: Headers;
};

export type apiProductsIndexResponse = (apiProductsIndexResponseSuccess | apiProductsIndexResponseError)

export const getApiProductsIndexUrl = (params?: ApiProductsIndexParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/products?${stringifiedParams}` : `/api/products`
}

/**
 * List **retrievable** products (the storefront view): published, with a published vendor, under a
 * fully-published category. Query params (documented in OpenAPI): `q` (name search), `category`
 * (slug — includes descendant categories), `sort` (featured|price_asc|price_desc|newest|name),
 * `per_page`, `page`.
 * @summary ApiProductsIndex
 */
export const apiProductsIndex = async (params?: ApiProductsIndexParams, options?: RequestInit): Promise<apiProductsIndexResponse> => {

  return apiFetch<apiProductsIndexResponse>(getApiProductsIndexUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiProductsFeedResponse200 = {
  data: ProductFeed
  status: 200
}

export type apiProductsFeedResponse400 = {
  data: ApiProductsFeed400
  status: 400
}

export type apiProductsFeedResponseSuccess = (apiProductsFeedResponse200) & {
  headers: Headers;
};
export type apiProductsFeedResponseError = (apiProductsFeedResponse400) & {
  headers: Headers;
};

export type apiProductsFeedResponse = (apiProductsFeedResponseSuccess | apiProductsFeedResponseError)

export const getApiProductsFeedUrl = (params?: ApiProductsFeedParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/products/feed?${stringifiedParams}` : `/api/products/feed`
}

/**
 * Infinite-scroll product feed — keyset (cursor) pagination. Unlike the offset listing, pages
 * stay correct even when products are published mid-scroll (no page drift / duplicate rows). Pass
 * the previous response's `next_cursor` back as `cursor` to fetch the next page; a null
 * `next_cursor` means the end of the feed. Same filters/sorts as the offset listing.
 * @summary ApiProductsFeed
 */
export const apiProductsFeed = async (params?: ApiProductsFeedParams, options?: RequestInit): Promise<apiProductsFeedResponse> => {

  return apiFetch<apiProductsFeedResponse>(getApiProductsFeedUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiProductsShowResponse200 = {
  data: ProductOut
  status: 200
}

export type apiProductsShowResponse400 = {
  data: ApiProductsShow400
  status: 400
}

export type apiProductsShowResponseSuccess = (apiProductsShowResponse200) & {
  headers: Headers;
};
export type apiProductsShowResponseError = (apiProductsShowResponse400) & {
  headers: Headers;
};

export type apiProductsShowResponse = (apiProductsShowResponseSuccess | apiProductsShowResponseError)

export const getApiProductsShowUrl = (slug: string,) => {




  return `/api/products/${slug}`
}

/**
 * Show one **retrievable** product by slug (a non-retrievable product 404s — it isn't public).
 * @summary ApiProductsShow
 */
export const apiProductsShow = async (slug: string, options?: RequestInit): Promise<apiProductsShowResponse> => {

  return apiFetch<apiProductsShowResponse>(getApiProductsShowUrl(slug),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiMediaShowResponse200 = {
  data: Response
  status: 200
}

export type apiMediaShowResponse400 = {
  data: ApiMediaShow400
  status: 400
}

export type apiMediaShowResponseSuccess = (apiMediaShowResponse200) & {
  headers: Headers;
};
export type apiMediaShowResponseError = (apiMediaShowResponse400) & {
  headers: Headers;
};

export type apiMediaShowResponse = (apiMediaShowResponseSuccess | apiMediaShowResponseError)

export const getApiMediaShowUrl = (id: number,) => {




  return `/api/media/${id}`
}

/**
 * Stream a media item — the original, or a named conversion (thumb/preview).
 * @summary ApiMediaShow
 */
export const apiMediaShow = async (id: number, options?: RequestInit): Promise<apiMediaShowResponse> => {

  return apiFetch<apiMediaShowResponse>(getApiMediaShowUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiMediaConversionResponse200 = {
  data: Response
  status: 200
}

export type apiMediaConversionResponse400 = {
  data: ApiMediaConversion400
  status: 400
}

export type apiMediaConversionResponseSuccess = (apiMediaConversionResponse200) & {
  headers: Headers;
};
export type apiMediaConversionResponseError = (apiMediaConversionResponse400) & {
  headers: Headers;
};

export type apiMediaConversionResponse = (apiMediaConversionResponseSuccess | apiMediaConversionResponseError)

export const getApiMediaConversionUrl = (id: number,
    conversion: string,) => {




  return `/api/media/${id}/${conversion}`
}

/**
 * Stream a media item — the original, or a named conversion (thumb/preview).
 * @summary ApiMediaConversion
 */
export const apiMediaConversion = async (id: number,
    conversion: string, options?: RequestInit): Promise<apiMediaConversionResponse> => {

  return apiFetch<apiMediaConversionResponse>(getApiMediaConversionUrl(id,conversion),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiProductsReviewsIndexResponse200 = {
  data: ReviewListOut
  status: 200
}

export type apiProductsReviewsIndexResponse400 = {
  data: ApiProductsReviewsIndex400
  status: 400
}

export type apiProductsReviewsIndexResponseSuccess = (apiProductsReviewsIndexResponse200) & {
  headers: Headers;
};
export type apiProductsReviewsIndexResponseError = (apiProductsReviewsIndexResponse400) & {
  headers: Headers;
};

export type apiProductsReviewsIndexResponse = (apiProductsReviewsIndexResponseSuccess | apiProductsReviewsIndexResponseError)

export const getApiProductsReviewsIndexUrl = (slug: string,) => {




  return `/api/products/${slug}/reviews`
}

/**
 * APPROVED reviews for the product (+ the caller's own review, whatever its status).
 * @summary ApiProductsReviewsIndex
 */
export const apiProductsReviewsIndex = async (slug: string, options?: RequestInit): Promise<apiProductsReviewsIndexResponse> => {

  return apiFetch<apiProductsReviewsIndexResponse>(getApiProductsReviewsIndexUrl(slug),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiProductsReviewsStoreResponse201 = {
  data: ReviewOut
  status: 201
}

export type apiProductsReviewsStoreResponse400 = {
  data: ApiProductsReviewsStore400
  status: 400
}

export type apiProductsReviewsStoreResponseSuccess = (apiProductsReviewsStoreResponse201) & {
  headers: Headers;
};
export type apiProductsReviewsStoreResponseError = (apiProductsReviewsStoreResponse400) & {
  headers: Headers;
};

export type apiProductsReviewsStoreResponse = (apiProductsReviewsStoreResponseSuccess | apiProductsReviewsStoreResponseError)

export const getApiProductsReviewsStoreUrl = (slug: string,) => {




  return `/api/products/${slug}/reviews`
}

/**
 * Submit a review — verified purchasers only, one per product; lands PENDING.
 * @summary ApiProductsReviewsStore
 */
export const apiProductsReviewsStore = async (slug: string,
    reviewIn: ReviewIn, options?: RequestInit): Promise<apiProductsReviewsStoreResponse> => {

  return apiFetch<apiProductsReviewsStoreResponse>(getApiProductsReviewsStoreUrl(slug),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(reviewIn)
  }
);}



export type apiCartShowResponse200 = {
  data: CartOut
  status: 200
}

export type apiCartShowResponseSuccess = (apiCartShowResponse200) & {
  headers: Headers;
};
;

export type apiCartShowResponse = (apiCartShowResponseSuccess)

export const getApiCartShowUrl = () => {




  return `/api/cart`
}

/**
 * Show the current cart (an empty shell if none exists yet).
 * @summary ApiCartShow
 */
export const apiCartShow = async ( options?: RequestInit): Promise<apiCartShowResponse> => {

  return apiFetch<apiCartShowResponse>(getApiCartShowUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiCartItemsAddResponse201 = {
  data: CartOut
  status: 201
}

export type apiCartItemsAddResponseSuccess = (apiCartItemsAddResponse201) & {
  headers: Headers;
};
;

export type apiCartItemsAddResponse = (apiCartItemsAddResponseSuccess)

export const getApiCartItemsAddUrl = () => {




  return `/api/cart/items`
}

/**
 * Add a variant to the cart (or bump its quantity if already present).
 * @summary ApiCartItemsAdd
 */
export const apiCartItemsAdd = async (addItemIn: AddItemIn, options?: RequestInit): Promise<apiCartItemsAddResponse> => {

  return apiFetch<apiCartItemsAddResponse>(getApiCartItemsAddUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(addItemIn)
  }
);}



export type apiCartItemsRemoveResponse200 = {
  data: CartOut
  status: 200
}

export type apiCartItemsRemoveResponse400 = {
  data: ApiCartItemsRemove400
  status: 400
}

export type apiCartItemsRemoveResponseSuccess = (apiCartItemsRemoveResponse200) & {
  headers: Headers;
};
export type apiCartItemsRemoveResponseError = (apiCartItemsRemoveResponse400) & {
  headers: Headers;
};

export type apiCartItemsRemoveResponse = (apiCartItemsRemoveResponseSuccess | apiCartItemsRemoveResponseError)

export const getApiCartItemsRemoveUrl = (id: number,) => {




  return `/api/cart/items/${id}`
}

/**
 * Remove a line from the cart.
 * @summary ApiCartItemsRemove
 */
export const apiCartItemsRemove = async (id: number, options?: RequestInit): Promise<apiCartItemsRemoveResponse> => {

  return apiFetch<apiCartItemsRemoveResponse>(getApiCartItemsRemoveUrl(id),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiCartItemsUpdateResponse200 = {
  data: CartOut
  status: 200
}

export type apiCartItemsUpdateResponse400 = {
  data: ApiCartItemsUpdate400
  status: 400
}

export type apiCartItemsUpdateResponseSuccess = (apiCartItemsUpdateResponse200) & {
  headers: Headers;
};
export type apiCartItemsUpdateResponseError = (apiCartItemsUpdateResponse400) & {
  headers: Headers;
};

export type apiCartItemsUpdateResponse = (apiCartItemsUpdateResponseSuccess | apiCartItemsUpdateResponseError)

export const getApiCartItemsUpdateUrl = (id: number,) => {




  return `/api/cart/items/${id}`
}

/**
 * Set a line's quantity (0 removes it).
 * @summary ApiCartItemsUpdate
 */
export const apiCartItemsUpdate = async (id: number,
    updateItemIn: UpdateItemIn, options?: RequestInit): Promise<apiCartItemsUpdateResponse> => {

  return apiFetch<apiCartItemsUpdateResponse>(getApiCartItemsUpdateUrl(id),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(updateItemIn)
  }
);}



export type apiCartCouponApplyResponse200 = {
  data: CartOut
  status: 200
}

export type apiCartCouponApplyResponseSuccess = (apiCartCouponApplyResponse200) & {
  headers: Headers;
};
;

export type apiCartCouponApplyResponse = (apiCartCouponApplyResponseSuccess)

export const getApiCartCouponApplyUrl = () => {




  return `/api/cart/coupon`
}

/**
 * Attach a coupon to the cart with immediate validation (checkout re-validates
 * authoritatively — a code can expire between apply and place-order).
 * @summary ApiCartCouponApply
 */
export const apiCartCouponApply = async (applyCouponIn: ApplyCouponIn, options?: RequestInit): Promise<apiCartCouponApplyResponse> => {

  return apiFetch<apiCartCouponApplyResponse>(getApiCartCouponApplyUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(applyCouponIn)
  }
);}



export type apiCartCouponRemoveResponse200 = {
  data: CartOut
  status: 200
}

export type apiCartCouponRemoveResponseSuccess = (apiCartCouponRemoveResponse200) & {
  headers: Headers;
};
;

export type apiCartCouponRemoveResponse = (apiCartCouponRemoveResponseSuccess)

export const getApiCartCouponRemoveUrl = () => {




  return `/api/cart/coupon`
}

/**
 * @summary ApiCartCouponRemove
 */
export const apiCartCouponRemove = async ( options?: RequestInit): Promise<apiCartCouponRemoveResponse> => {

  return apiFetch<apiCartCouponRemoveResponse>(getApiCartCouponRemoveUrl(),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiDealsIndexResponse200 = {
  data: DealOut[]
  status: 200
}

export type apiDealsIndexResponseSuccess = (apiDealsIndexResponse200) & {
  headers: Headers;
};
;

export type apiDealsIndexResponse = (apiDealsIndexResponseSuccess)

export const getApiDealsIndexUrl = () => {




  return `/api/deals`
}

/**
 * @summary ApiDealsIndex
 */
export const apiDealsIndex = async ( options?: RequestInit): Promise<apiDealsIndexResponse> => {

  return apiFetch<apiDealsIndexResponse>(getApiDealsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAnnouncementResponse200 = {
  data: AnnouncementOut
  status: 200
}

export type apiAnnouncementResponseSuccess = (apiAnnouncementResponse200) & {
  headers: Headers;
};
;

export type apiAnnouncementResponse = (apiAnnouncementResponseSuccess)

export const getApiAnnouncementUrl = () => {




  return `/api/announcement`
}

/**
 * @summary ApiAnnouncement
 */
export const apiAnnouncement = async ( options?: RequestInit): Promise<apiAnnouncementResponse> => {

  return apiFetch<apiAnnouncementResponse>(getApiAnnouncementUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiSettingsResponse200 = {
  data: SettingsOut
  status: 200
}

export type apiSettingsResponseSuccess = (apiSettingsResponse200) & {
  headers: Headers;
};
;

export type apiSettingsResponse = (apiSettingsResponseSuccess)

export const getApiSettingsUrl = () => {




  return `/api/settings`
}

/**
 * @summary ApiSettings
 */
export const apiSettings = async ( options?: RequestInit): Promise<apiSettingsResponse> => {

  return apiFetch<apiSettingsResponse>(getApiSettingsUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiNewsletterResponse200 = {
  data: MessageOut
  status: 200
}

export type apiNewsletterResponseSuccess = (apiNewsletterResponse200) & {
  headers: Headers;
};
;

export type apiNewsletterResponse = (apiNewsletterResponseSuccess)

export const getApiNewsletterUrl = () => {




  return `/api/newsletter`
}

/**
 * Idempotent newsletter signup — re-subscribing an existing email is a friendly 200.
 * @summary ApiNewsletter
 */
export const apiNewsletter = async (newsletterIn: NewsletterIn, options?: RequestInit): Promise<apiNewsletterResponse> => {

  return apiFetch<apiNewsletterResponse>(getApiNewsletterUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(newsletterIn)
  }
);}



export type apiShippingMethodsResponse200 = {
  data: ShippingMethodOut[]
  status: 200
}

export type apiShippingMethodsResponseSuccess = (apiShippingMethodsResponse200) & {
  headers: Headers;
};
;

export type apiShippingMethodsResponse = (apiShippingMethodsResponseSuccess)

export const getApiShippingMethodsUrl = () => {




  return `/api/shipping-methods`
}

/**
 * The active shipping methods + their server rate, for the checkout method selector.
 * @summary ApiShippingMethods
 */
export const apiShippingMethods = async ( options?: RequestInit): Promise<apiShippingMethodsResponse> => {

  return apiFetch<apiShippingMethodsResponse>(getApiShippingMethodsUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiBannersIndexResponse200 = {
  data: BannerOut[]
  status: 200
}

export type apiBannersIndexResponseSuccess = (apiBannersIndexResponse200) & {
  headers: Headers;
};
;

export type apiBannersIndexResponse = (apiBannersIndexResponseSuccess)

export const getApiBannersIndexUrl = () => {




  return `/api/banners`
}

/**
 * @summary ApiBannersIndex
 */
export const apiBannersIndex = async ( options?: RequestInit): Promise<apiBannersIndexResponse> => {

  return apiFetch<apiBannersIndexResponse>(getApiBannersIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiCheckoutResponse201 = {
  data: OrderOut
  status: 201
}

export type apiCheckoutResponseSuccess = (apiCheckoutResponse201) & {
  headers: Headers;
};
;

export type apiCheckoutResponse = (apiCheckoutResponseSuccess)

export const getApiCheckoutUrl = () => {




  return `/api/checkout`
}

/**
 * Convert the current cart into a PENDING order, atomically (stock locked, cart cleared),
 * capturing the contact email + shipping address and the server-computed money breakdown.
 * @summary ApiCheckout
 */
export const apiCheckout = async (checkoutIn: CheckoutIn, options?: RequestInit): Promise<apiCheckoutResponse> => {

  return apiFetch<apiCheckoutResponse>(getApiCheckoutUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(checkoutIn)
  }
);}



export type apiMetricsOrdersPlacedResponse200 = {
  data: MetricsOut
  status: 200
}

export type apiMetricsOrdersPlacedResponseSuccess = (apiMetricsOrdersPlacedResponse200) & {
  headers: Headers;
};
;

export type apiMetricsOrdersPlacedResponse = (apiMetricsOrdersPlacedResponseSuccess)

export const getApiMetricsOrdersPlacedUrl = () => {




  return `/api/metrics/orders-placed`
}

/**
 * Order metrics bumped by the order.placed listeners (proves event→listener + the queued job).
 * @summary ApiMetricsOrdersPlaced
 */
export const apiMetricsOrdersPlaced = async ( options?: RequestInit): Promise<apiMetricsOrdersPlacedResponse> => {

  return apiFetch<apiMetricsOrdersPlacedResponse>(getApiMetricsOrdersPlacedUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiOrdersShowResponse200 = {
  data: OrderOut
  status: 200
}

export type apiOrdersShowResponse400 = {
  data: ApiOrdersShow400
  status: 400
}

export type apiOrdersShowResponseSuccess = (apiOrdersShowResponse200) & {
  headers: Headers;
};
export type apiOrdersShowResponseError = (apiOrdersShowResponse400) & {
  headers: Headers;
};

export type apiOrdersShowResponse = (apiOrdersShowResponseSuccess | apiOrdersShowResponseError)

export const getApiOrdersShowUrl = (id: number,) => {




  return `/api/orders/${id}`
}

/**
 * One order, with lines + breakdown + the tracking timeline — for the signed-in owner or
 * the order-token holder.
 * @summary ApiOrdersShow
 */
export const apiOrdersShow = async (id: number, options?: RequestInit): Promise<apiOrdersShowResponse> => {

  return apiFetch<apiOrdersShowResponse>(getApiOrdersShowUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiOrdersInvoiceResponse200 = {
  data: Response
  status: 200
}

export type apiOrdersInvoiceResponse400 = {
  data: ApiOrdersInvoice400
  status: 400
}

export type apiOrdersInvoiceResponseSuccess = (apiOrdersInvoiceResponse200) & {
  headers: Headers;
};
export type apiOrdersInvoiceResponseError = (apiOrdersInvoiceResponse400) & {
  headers: Headers;
};

export type apiOrdersInvoiceResponse = (apiOrdersInvoiceResponseSuccess | apiOrdersInvoiceResponseError)

export const getApiOrdersInvoiceUrl = (id: number,) => {




  return `/api/orders/${id}/invoice`
}

/**
 * @summary ApiOrdersInvoice
 */
export const apiOrdersInvoice = async (id: number, options?: RequestInit): Promise<apiOrdersInvoiceResponse> => {

  return apiFetch<apiOrdersInvoiceResponse>(getApiOrdersInvoiceUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiOrdersCancelResponse200 = {
  data: OrderOut
  status: 200
}

export type apiOrdersCancelResponse400 = {
  data: ApiOrdersCancel400
  status: 400
}

export type apiOrdersCancelResponseSuccess = (apiOrdersCancelResponse200) & {
  headers: Headers;
};
export type apiOrdersCancelResponseError = (apiOrdersCancelResponse400) & {
  headers: Headers;
};

export type apiOrdersCancelResponse = (apiOrdersCancelResponseSuccess | apiOrdersCancelResponseError)

export const getApiOrdersCancelUrl = (id: number,) => {




  return `/api/orders/${id}/cancel`
}

/**
 * Cancel the order (owner or token holder) while the state machine allows it. A PENDING
 * (unpaid) cancel is a plain, synchronous CANCELLED + restock — unchanged. A PAID cancel is a
 * REFUND (K15, DR-0065): money was captured, so it must come back — the customer keeps ONE
 * action, routed to `refund_service.initiate_refund` (the same function the admin refund route
 * uses). This first read is unlocked and only picks which path to take; each path re-validates
 * the real state under its own `FOR UPDATE` before doing anything irreversible, so a race here
 * (e.g. the order ships between this read and the lock) is caught by that path's own guard, not
 * by this dispatch.
 * @summary ApiOrdersCancel
 */
export const apiOrdersCancel = async (id: number, options?: RequestInit): Promise<apiOrdersCancelResponse> => {

  return apiFetch<apiOrdersCancelResponse>(getApiOrdersCancelUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiOrdersPayResponse201 = {
  data: PaymentOut
  status: 201
}

export type apiOrdersPayResponse400 = {
  data: ApiOrdersPay400
  status: 400
}

export type apiOrdersPayResponseSuccess = (apiOrdersPayResponse201) & {
  headers: Headers;
};
export type apiOrdersPayResponseError = (apiOrdersPayResponse400) & {
  headers: Headers;
};

export type apiOrdersPayResponse = (apiOrdersPayResponseSuccess | apiOrdersPayResponseError)

export const getApiOrdersPayUrl = (id: number,) => {




  return `/api/orders/${id}/pay`
}

/**
 * Create a charge for the order via the gateway — the signed-in owner or the guest holding
 * the order's access token (guests must be able to pay; PENDING-only).
 * @summary ApiOrdersPay
 */
export const apiOrdersPay = async (id: number, options?: RequestInit): Promise<apiOrdersPayResponse> => {

  return apiFetch<apiOrdersPayResponse>(getApiOrdersPayUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiWebhooksPaymentResponse201 = {
  data: WebhookOut
  status: 201
}

export type apiWebhooksPaymentResponseSuccess = (apiWebhooksPaymentResponse201) & {
  headers: Headers;
};
;

export type apiWebhooksPaymentResponse = (apiWebhooksPaymentResponseSuccess)

export const getApiWebhooksPaymentUrl = () => {




  return `/api/webhooks/payment`
}

/**
 * Idempotently process a gateway webhook — a redelivery of the same event id is a no-op. The
 * request must carry a valid gateway signature (authenticity) before any side effects run.
 * @summary ApiWebhooksPayment
 */
export const apiWebhooksPayment = async (webhookIn: WebhookIn, options?: RequestInit): Promise<apiWebhooksPaymentResponse> => {

  return apiFetch<apiWebhooksPaymentResponse>(getApiWebhooksPaymentUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(webhookIn)
  }
);}



export type apiUserPasswordResponse200 = {
  data: MessageOut
  status: 200
}

export type apiUserPasswordResponseSuccess = (apiUserPasswordResponse200) & {
  headers: Headers;
};
;

export type apiUserPasswordResponse = (apiUserPasswordResponseSuccess)

export const getApiUserPasswordUrl = () => {




  return `/api/user/password`
}

/**
 * Set a new password — only with the current one in hand (credential-change confirmation).
 * @summary ApiUserPassword
 */
export const apiUserPassword = async (changePasswordIn: ChangePasswordIn, options?: RequestInit): Promise<apiUserPasswordResponse> => {

  return apiFetch<apiUserPasswordResponse>(getApiUserPasswordUrl(),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(changePasswordIn)
  }
);}



export type apiEmailVerificationSendResponse200 = {
  data: MessageOut
  status: 200
}

export type apiEmailVerificationSendResponseSuccess = (apiEmailVerificationSendResponse200) & {
  headers: Headers;
};
;

export type apiEmailVerificationSendResponse = (apiEmailVerificationSendResponseSuccess)

export const getApiEmailVerificationSendUrl = () => {




  return `/api/email/verification-notification`
}

/**
 * (Re-)send the verification link to the account email.
 * @summary ApiEmailVerificationSend
 */
export const apiEmailVerificationSend = async ( options?: RequestInit): Promise<apiEmailVerificationSendResponse> => {

  return apiFetch<apiEmailVerificationSendResponse>(getApiEmailVerificationSendUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiOrdersIndexResponse200 = {
  data: OrderOut[]
  status: 200
}

export type apiOrdersIndexResponseSuccess = (apiOrdersIndexResponse200) & {
  headers: Headers;
};
;

export type apiOrdersIndexResponse = (apiOrdersIndexResponseSuccess)

export const getApiOrdersIndexUrl = () => {




  return `/api/orders`
}

/**
 * The authenticated user's orders (newest first).
 * @summary ApiOrdersIndex
 */
export const apiOrdersIndex = async ( options?: RequestInit): Promise<apiOrdersIndexResponse> => {

  return apiFetch<apiOrdersIndexResponse>(getApiOrdersIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAccountAvatarResponse201 = {
  data: UserOut
  status: 201
}

export type apiAccountAvatarResponseSuccess = (apiAccountAvatarResponse201) & {
  headers: Headers;
};
;

export type apiAccountAvatarResponse = (apiAccountAvatarResponseSuccess)

export const getApiAccountAvatarUrl = () => {




  return `/api/account/avatar`
}

/**
 * Attach/replace the account avatar (one image; the previous one is removed).
 * @summary ApiAccountAvatar
 */
export const apiAccountAvatar = async ( options?: RequestInit): Promise<apiAccountAvatarResponse> => {

  return apiFetch<apiAccountAvatarResponse>(getApiAccountAvatarUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAccountAddressesIndexResponse200 = {
  data: SavedAddressOut[]
  status: 200
}

export type apiAccountAddressesIndexResponseSuccess = (apiAccountAddressesIndexResponse200) & {
  headers: Headers;
};
;

export type apiAccountAddressesIndexResponse = (apiAccountAddressesIndexResponseSuccess)

export const getApiAccountAddressesIndexUrl = () => {




  return `/api/account/addresses`
}

/**
 * @summary ApiAccountAddressesIndex
 */
export const apiAccountAddressesIndex = async ( options?: RequestInit): Promise<apiAccountAddressesIndexResponse> => {

  return apiFetch<apiAccountAddressesIndexResponse>(getApiAccountAddressesIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAccountAddressesStoreResponse201 = {
  data: SavedAddressOut
  status: 201
}

export type apiAccountAddressesStoreResponseSuccess = (apiAccountAddressesStoreResponse201) & {
  headers: Headers;
};
;

export type apiAccountAddressesStoreResponse = (apiAccountAddressesStoreResponseSuccess)

export const getApiAccountAddressesStoreUrl = () => {




  return `/api/account/addresses`
}

/**
 * @summary ApiAccountAddressesStore
 */
export const apiAccountAddressesStore = async (savedAddressIn: SavedAddressIn, options?: RequestInit): Promise<apiAccountAddressesStoreResponse> => {

  return apiFetch<apiAccountAddressesStoreResponse>(getApiAccountAddressesStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(savedAddressIn)
  }
);}



export type apiAccountAddressesDestroyResponse200 = {
  data: ApiAccountAddressesDestroy200
  status: 200
}

export type apiAccountAddressesDestroyResponse400 = {
  data: ApiAccountAddressesDestroy400
  status: 400
}

export type apiAccountAddressesDestroyResponseSuccess = (apiAccountAddressesDestroyResponse200) & {
  headers: Headers;
};
export type apiAccountAddressesDestroyResponseError = (apiAccountAddressesDestroyResponse400) & {
  headers: Headers;
};

export type apiAccountAddressesDestroyResponse = (apiAccountAddressesDestroyResponseSuccess | apiAccountAddressesDestroyResponseError)

export const getApiAccountAddressesDestroyUrl = (id: number,) => {




  return `/api/account/addresses/${id}`
}

/**
 * @summary ApiAccountAddressesDestroy
 */
export const apiAccountAddressesDestroy = async (id: number, options?: RequestInit): Promise<apiAccountAddressesDestroyResponse> => {

  return apiFetch<apiAccountAddressesDestroyResponse>(getApiAccountAddressesDestroyUrl(id),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAccountAddressesUpdateResponse200 = {
  data: SavedAddressOut
  status: 200
}

export type apiAccountAddressesUpdateResponse400 = {
  data: ApiAccountAddressesUpdate400
  status: 400
}

export type apiAccountAddressesUpdateResponseSuccess = (apiAccountAddressesUpdateResponse200) & {
  headers: Headers;
};
export type apiAccountAddressesUpdateResponseError = (apiAccountAddressesUpdateResponse400) & {
  headers: Headers;
};

export type apiAccountAddressesUpdateResponse = (apiAccountAddressesUpdateResponseSuccess | apiAccountAddressesUpdateResponseError)

export const getApiAccountAddressesUpdateUrl = (id: number,) => {




  return `/api/account/addresses/${id}`
}

/**
 * @summary ApiAccountAddressesUpdate
 */
export const apiAccountAddressesUpdate = async (id: number,
    savedAddressIn: SavedAddressIn, options?: RequestInit): Promise<apiAccountAddressesUpdateResponse> => {

  return apiFetch<apiAccountAddressesUpdateResponse>(getApiAccountAddressesUpdateUrl(id),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(savedAddressIn)
  }
);}



export type apiNotificationsIndexResponse200 = {
  data: NotificationOut[]
  status: 200
}

export type apiNotificationsIndexResponseSuccess = (apiNotificationsIndexResponse200) & {
  headers: Headers;
};
;

export type apiNotificationsIndexResponse = (apiNotificationsIndexResponseSuccess)

export const getApiNotificationsIndexUrl = () => {




  return `/api/notifications`
}

/**
 * The signed-in customer's notifications, newest first.
 * @summary ApiNotificationsIndex
 */
export const apiNotificationsIndex = async ( options?: RequestInit): Promise<apiNotificationsIndexResponse> => {

  return apiFetch<apiNotificationsIndexResponse>(getApiNotificationsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiNotificationsReadResponse200 = {
  data: MessageOut
  status: 200
}

export type apiNotificationsReadResponseSuccess = (apiNotificationsReadResponse200) & {
  headers: Headers;
};
;

export type apiNotificationsReadResponse = (apiNotificationsReadResponseSuccess)

export const getApiNotificationsReadUrl = () => {




  return `/api/notifications/read`
}

/**
 * Mark all of the customer's notifications as read.
 * @summary ApiNotificationsRead
 */
export const apiNotificationsRead = async ( options?: RequestInit): Promise<apiNotificationsReadResponse> => {

  return apiFetch<apiNotificationsReadResponse>(getApiNotificationsReadUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiWishlistIndexResponse200 = {
  data: ProductOut[]
  status: 200
}

export type apiWishlistIndexResponseSuccess = (apiWishlistIndexResponse200) & {
  headers: Headers;
};
;

export type apiWishlistIndexResponse = (apiWishlistIndexResponseSuccess)

export const getApiWishlistIndexUrl = () => {




  return `/api/wishlist`
}

/**
 * The signed-in customer's saved products (only ones still retrievable on the storefront).
 * @summary ApiWishlistIndex
 */
export const apiWishlistIndex = async ( options?: RequestInit): Promise<apiWishlistIndexResponse> => {

  return apiFetch<apiWishlistIndexResponse>(getApiWishlistIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiWishlistToggleResponse200 = {
  data: WishlistToggleOut
  status: 200
}

export type apiWishlistToggleResponse400 = {
  data: ApiWishlistToggle400
  status: 400
}

export type apiWishlistToggleResponseSuccess = (apiWishlistToggleResponse200) & {
  headers: Headers;
};
export type apiWishlistToggleResponseError = (apiWishlistToggleResponse400) & {
  headers: Headers;
};

export type apiWishlistToggleResponse = (apiWishlistToggleResponseSuccess | apiWishlistToggleResponseError)

export const getApiWishlistToggleUrl = (productId: number,) => {




  return `/api/wishlist/${productId}`
}

/**
 * Add the product to the wishlist, or remove it if already saved.
 * @summary ApiWishlistToggle
 */
export const apiWishlistToggle = async (productId: number, options?: RequestInit): Promise<apiWishlistToggleResponse> => {

  return apiFetch<apiWishlistToggleResponse>(getApiWishlistToggleUrl(productId),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiVariantsStockAlertSubscribeResponse200 = {
  data: MessageOut
  status: 200
}

export type apiVariantsStockAlertSubscribeResponse400 = {
  data: ApiVariantsStockAlertSubscribe400
  status: 400
}

export type apiVariantsStockAlertSubscribeResponseSuccess = (apiVariantsStockAlertSubscribeResponse200) & {
  headers: Headers;
};
export type apiVariantsStockAlertSubscribeResponseError = (apiVariantsStockAlertSubscribeResponse400) & {
  headers: Headers;
};

export type apiVariantsStockAlertSubscribeResponse = (apiVariantsStockAlertSubscribeResponseSuccess | apiVariantsStockAlertSubscribeResponseError)

export const getApiVariantsStockAlertSubscribeUrl = (id: number,) => {




  return `/api/variants/${id}/stock-alert`
}

/**
 * Watch a SOLD-OUT variant (in-stock → 422; duplicates are an idempotent no-op).
 * @summary ApiVariantsStockAlertSubscribe
 */
export const apiVariantsStockAlertSubscribe = async (id: number, options?: RequestInit): Promise<apiVariantsStockAlertSubscribeResponse> => {

  return apiFetch<apiVariantsStockAlertSubscribeResponse>(getApiVariantsStockAlertSubscribeUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiVariantsStockAlertUnsubscribeResponse200 = {
  data: MessageOut
  status: 200
}

export type apiVariantsStockAlertUnsubscribeResponse400 = {
  data: ApiVariantsStockAlertUnsubscribe400
  status: 400
}

export type apiVariantsStockAlertUnsubscribeResponseSuccess = (apiVariantsStockAlertUnsubscribeResponse200) & {
  headers: Headers;
};
export type apiVariantsStockAlertUnsubscribeResponseError = (apiVariantsStockAlertUnsubscribeResponse400) & {
  headers: Headers;
};

export type apiVariantsStockAlertUnsubscribeResponse = (apiVariantsStockAlertUnsubscribeResponseSuccess | apiVariantsStockAlertUnsubscribeResponseError)

export const getApiVariantsStockAlertUnsubscribeUrl = (id: number,) => {




  return `/api/variants/${id}/stock-alert`
}

/**
 * @summary ApiVariantsStockAlertUnsubscribe
 */
export const apiVariantsStockAlertUnsubscribe = async (id: number, options?: RequestInit): Promise<apiVariantsStockAlertUnsubscribeResponse> => {

  return apiFetch<apiVariantsStockAlertUnsubscribeResponse>(getApiVariantsStockAlertUnsubscribeUrl(id),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminMeResponse200 = {
  data: AdminMeOut
  status: 200
}

export type apiAdminMeResponseSuccess = (apiAdminMeResponse200) & {
  headers: Headers;
};
;

export type apiAdminMeResponse = (apiAdminMeResponseSuccess)

export const getApiAdminMeUrl = () => {




  return `/api/admin/me`
}

/**
 * The current admin's identity, resolved from the Keycloak OIDC token (401 without a valid
 * token, 403 without the admin realm role).
 * @summary ApiAdminMe
 */
export const apiAdminMe = async ( options?: RequestInit): Promise<apiAdminMeResponse> => {

  return apiFetch<apiAdminMeResponse>(getApiAdminMeUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminOidcTokenResponse200 = {
  data: TokenOut
  status: 200
}

export type apiAdminOidcTokenResponseSuccess = (apiAdminOidcTokenResponse200) & {
  headers: Headers;
};
;

export type apiAdminOidcTokenResponse = (apiAdminOidcTokenResponseSuccess)

export const getApiAdminOidcTokenUrl = () => {




  return `/api/admin/oidc/token`
}

/**
 * Exchange a validated Keycloak token for an arvel bearer PAT. JIT-provisions the admin and
 * persists the Keycloak-mapped RBAC roles so the issued bearer carries them into the
 * bearer-guarded admin APIs.
 * @summary ApiAdminOidcToken
 */
export const apiAdminOidcToken = async ( options?: RequestInit): Promise<apiAdminOidcTokenResponse> => {

  return apiFetch<apiAdminOidcTokenResponse>(getApiAdminOidcTokenUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminProductsImageResponse201 = {
  data: GalleryImageOut[]
  status: 201
}

export type apiAdminProductsImageResponse400 = {
  data: ApiAdminProductsImage400
  status: 400
}

export type apiAdminProductsImageResponseSuccess = (apiAdminProductsImageResponse201) & {
  headers: Headers;
};
export type apiAdminProductsImageResponseError = (apiAdminProductsImageResponse400) & {
  headers: Headers;
};

export type apiAdminProductsImageResponse = (apiAdminProductsImageResponseSuccess | apiAdminProductsImageResponseError)

export const getApiAdminProductsImageUrl = (id: number,) => {




  return `/api/admin/products/${id}/image`
}

/**
 * Attach an uploaded image to the product gallery. catalog.update is enforced by the route's
 * Authorize middleware (DR-0055) — it runs before binding, so a denied caller 403s uniformly
 * whether or not the product id exists; returns the updated gallery.
 * @summary ApiAdminProductsImage
 */
export const apiAdminProductsImage = async (id: number, options?: RequestInit): Promise<apiAdminProductsImageResponse> => {

  return apiFetch<apiAdminProductsImageResponse>(getApiAdminProductsImageUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminProductsCopyDraftResponse200 = {
  data: CopyDraft
  status: 200
}

export type apiAdminProductsCopyDraftResponse400 = {
  data: ApiAdminProductsCopyDraft400
  status: 400
}

export type apiAdminProductsCopyDraftResponseSuccess = (apiAdminProductsCopyDraftResponse200) & {
  headers: Headers;
};
export type apiAdminProductsCopyDraftResponseError = (apiAdminProductsCopyDraftResponse400) & {
  headers: Headers;
};

export type apiAdminProductsCopyDraftResponse = (apiAdminProductsCopyDraftResponseSuccess | apiAdminProductsCopyDraftResponseError)

export const getApiAdminProductsCopyDraftUrl = (slug: string,) => {




  return `/api/admin/products/${slug}/copy-draft`
}

/**
 * @summary ApiAdminProductsCopyDraft
 */
export const apiAdminProductsCopyDraft = async (slug: string, options?: RequestInit): Promise<apiAdminProductsCopyDraftResponse> => {

  return apiFetch<apiAdminProductsCopyDraftResponse>(getApiAdminProductsCopyDraftUrl(slug),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminProductsMediaDestroyResponse200 = {
  data: GalleryImageOut[]
  status: 200
}

export type apiAdminProductsMediaDestroyResponse400 = {
  data: ApiAdminProductsMediaDestroy400
  status: 400
}

export type apiAdminProductsMediaDestroyResponseSuccess = (apiAdminProductsMediaDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminProductsMediaDestroyResponseError = (apiAdminProductsMediaDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminProductsMediaDestroyResponse = (apiAdminProductsMediaDestroyResponseSuccess | apiAdminProductsMediaDestroyResponseError)

export const getApiAdminProductsMediaDestroyUrl = (id: number,
    mediaId: number,) => {




  return `/api/admin/products/${id}/media/${mediaId}`
}

/**
 * Remove ONE gallery image (row + stored files via HasMedia.delete_media); returns the
 * updated gallery. catalog.update is enforced by the route's Authorize middleware (DR-0055);
 * a foreign media id can't cross products.
 * @summary ApiAdminProductsMediaDestroy
 */
export const apiAdminProductsMediaDestroy = async (id: number,
    mediaId: number, options?: RequestInit): Promise<apiAdminProductsMediaDestroyResponse> => {

  return apiFetch<apiAdminProductsMediaDestroyResponse>(getApiAdminProductsMediaDestroyUrl(id,mediaId),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminProductsRestoreResponse200 = {
  data: AdminProductOut
  status: 200
}

export type apiAdminProductsRestoreResponse400 = {
  data: ApiAdminProductsRestore400
  status: 400
}

export type apiAdminProductsRestoreResponseSuccess = (apiAdminProductsRestoreResponse200) & {
  headers: Headers;
};
export type apiAdminProductsRestoreResponseError = (apiAdminProductsRestoreResponse400) & {
  headers: Headers;
};

export type apiAdminProductsRestoreResponse = (apiAdminProductsRestoreResponseSuccess | apiAdminProductsRestoreResponseError)

export const getApiAdminProductsRestoreUrl = (id: number,) => {




  return `/api/admin/products/${id}/restore`
}

/**
 * Bring an archived product back — visibility flags are untouched, so a hidden product
 * restores as hidden. Not a CRUD resource action (it targets a soft-deleted row `api_resource`'s
 * binding would 404 on), so it stays an explicit route with its own in-handler check.
 * @summary ApiAdminProductsRestore
 */
export const apiAdminProductsRestore = async (id: number, options?: RequestInit): Promise<apiAdminProductsRestoreResponse> => {

  return apiFetch<apiAdminProductsRestoreResponse>(getApiAdminProductsRestoreUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminProductsIndexResponse200 = {
  data: AdminProductPage
  status: 200
}

export type apiAdminProductsIndexResponse400 = {
  data: ApiAdminProductsIndex400
  status: 400
}

export type apiAdminProductsIndexResponseSuccess = (apiAdminProductsIndexResponse200) & {
  headers: Headers;
};
export type apiAdminProductsIndexResponseError = (apiAdminProductsIndexResponse400) & {
  headers: Headers;
};

export type apiAdminProductsIndexResponse = (apiAdminProductsIndexResponseSuccess | apiAdminProductsIndexResponseError)

export const getApiAdminProductsIndexUrl = (params?: ApiAdminProductsIndexParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/admin/products?${stringifiedParams}` : `/api/admin/products`
}

/**
 * List products (admin) — hidden ones included, each row carrying price/thumb/stock and
 * `is_visible`. Filterable by ``q`` (name), ``category_id`` and ``active`` (published yes/no),
 * sortable by ``sort``. ``archived=true`` lists the soft-deleted (recoverable) rows instead.
 * @summary ApiAdminProductsIndex
 */
export const apiAdminProductsIndex = async (params?: ApiAdminProductsIndexParams, options?: RequestInit): Promise<apiAdminProductsIndexResponse> => {

  return apiFetch<apiAdminProductsIndexResponse>(getApiAdminProductsIndexUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminProductsStoreResponse201 = {
  data: AdminProductOut
  status: 201
}

export type apiAdminProductsStoreResponseSuccess = (apiAdminProductsStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminProductsStoreResponse = (apiAdminProductsStoreResponseSuccess)

export const getApiAdminProductsStoreUrl = () => {




  return `/api/admin/products`
}

/**
 * Create a product (admins only) with per-locale content (en required).
 * @summary ApiAdminProductsStore
 */
export const apiAdminProductsStore = async (productIn: ProductIn, options?: RequestInit): Promise<apiAdminProductsStoreResponse> => {

  return apiFetch<apiAdminProductsStoreResponse>(getApiAdminProductsStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(productIn)
  }
);}



export type apiAdminProductsShowResponse200 = {
  data: AdminProductDetailOut
  status: 200
}

export type apiAdminProductsShowResponse400 = {
  data: ApiAdminProductsShow400
  status: 400
}

export type apiAdminProductsShowResponseSuccess = (apiAdminProductsShowResponse200) & {
  headers: Headers;
};
export type apiAdminProductsShowResponseError = (apiAdminProductsShowResponse400) & {
  headers: Headers;
};

export type apiAdminProductsShowResponse = (apiAdminProductsShowResponseSuccess | apiAdminProductsShowResponseError)

export const getApiAdminProductsShowUrl = (product: string,) => {




  return `/api/admin/products/${product}`
}

/**
 * One product with variants + gallery — the editor's read (hidden products included).
 * ``product`` is bound via the plain (non-visibility) query, so it's re-fetched through
 * ``with_visibility()`` here to get the computed `is_visible` flag for the response.
 * @summary ApiAdminProductsShow
 */
export const apiAdminProductsShow = async (product: string, options?: RequestInit): Promise<apiAdminProductsShowResponse> => {

  return apiFetch<apiAdminProductsShowResponse>(getApiAdminProductsShowUrl(product),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminProductsUpdatePutResponse200 = {
  data: AdminProductOut
  status: 200
}

export type apiAdminProductsUpdatePutResponse400 = {
  data: ApiAdminProductsUpdatePut400
  status: 400
}

export type apiAdminProductsUpdatePutResponseSuccess = (apiAdminProductsUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminProductsUpdatePutResponseError = (apiAdminProductsUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminProductsUpdatePutResponse = (apiAdminProductsUpdatePutResponseSuccess | apiAdminProductsUpdatePutResponseError)

export const getApiAdminProductsUpdatePutUrl = (product: string,) => {




  return `/api/admin/products/${product}`
}

/**
 * Update a product — per-locale content, price, category, status, visibility.
 * the class's ``__resource_policy__`` already 404'd a non-admin before this body runs (deny-as-404,
 * same policy as destroy).
 * @summary ApiAdminProductsUpdate
 */
export const apiAdminProductsUpdatePut = async (product: string,
    updateProductIn: UpdateProductIn, options?: RequestInit): Promise<apiAdminProductsUpdatePutResponse> => {

  return apiFetch<apiAdminProductsUpdatePutResponse>(getApiAdminProductsUpdatePutUrl(product),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(updateProductIn)
  }
);}



export type apiAdminProductsDestroyResponse200 = {
  data: MessageOut
  status: 200
}

export type apiAdminProductsDestroyResponse400 = {
  data: ApiAdminProductsDestroy400
  status: 400
}

export type apiAdminProductsDestroyResponseSuccess = (apiAdminProductsDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminProductsDestroyResponseError = (apiAdminProductsDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminProductsDestroyResponse = (apiAdminProductsDestroyResponseSuccess | apiAdminProductsDestroyResponseError)

export const getApiAdminProductsDestroyUrl = (product: string,) => {




  return `/api/admin/products/${product}`
}

/**
 * ARCHIVE a product (soft delete — order history intact, restorable;
 * the class's ``__resource_policy__`` already 404'd a non-admin before this body runs).
 * @summary ApiAdminProductsDestroy
 */
export const apiAdminProductsDestroy = async (product: string, options?: RequestInit): Promise<apiAdminProductsDestroyResponse> => {

  return apiFetch<apiAdminProductsDestroyResponse>(getApiAdminProductsDestroyUrl(product),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminProductsUpdatePatchResponse200 = {
  data: AdminProductOut
  status: 200
}

export type apiAdminProductsUpdatePatchResponse400 = {
  data: ApiAdminProductsUpdatePatch400
  status: 400
}

export type apiAdminProductsUpdatePatchResponseSuccess = (apiAdminProductsUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminProductsUpdatePatchResponseError = (apiAdminProductsUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminProductsUpdatePatchResponse = (apiAdminProductsUpdatePatchResponseSuccess | apiAdminProductsUpdatePatchResponseError)

export const getApiAdminProductsUpdatePatchUrl = (product: string,) => {




  return `/api/admin/products/${product}`
}

/**
 * Update a product — per-locale content, price, category, status, visibility.
 * the class's ``__resource_policy__`` already 404'd a non-admin before this body runs (deny-as-404,
 * same policy as destroy).
 * @summary ApiAdminProductsUpdate
 */
export const apiAdminProductsUpdatePatch = async (product: string,
    updateProductIn: UpdateProductIn, options?: RequestInit): Promise<apiAdminProductsUpdatePatchResponse> => {

  return apiFetch<apiAdminProductsUpdatePatchResponse>(getApiAdminProductsUpdatePatchUrl(product),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(updateProductIn)
  }
);}



export type apiAdminCategoriesIndexResponse200 = {
  data: AdminCategoryPage
  status: 200
}

export type apiAdminCategoriesIndexResponse400 = {
  data: ApiAdminCategoriesIndex400
  status: 400
}

export type apiAdminCategoriesIndexResponseSuccess = (apiAdminCategoriesIndexResponse200) & {
  headers: Headers;
};
export type apiAdminCategoriesIndexResponseError = (apiAdminCategoriesIndexResponse400) & {
  headers: Headers;
};

export type apiAdminCategoriesIndexResponse = (apiAdminCategoriesIndexResponseSuccess | apiAdminCategoriesIndexResponseError)

export const getApiAdminCategoriesIndexUrl = (params?: ApiAdminCategoriesIndexParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/admin/categories?${stringifiedParams}` : `/api/admin/categories`
}

/**
 * List **all** categories (admin) with `is_visible` (inline EXISTS column).
 * @summary ApiAdminCategoriesIndex
 */
export const apiAdminCategoriesIndex = async (params?: ApiAdminCategoriesIndexParams, options?: RequestInit): Promise<apiAdminCategoriesIndexResponse> => {

  return apiFetch<apiAdminCategoriesIndexResponse>(getApiAdminCategoriesIndexUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminCategoriesStoreResponse201 = {
  data: AdminCategoryOut
  status: 201
}

export type apiAdminCategoriesStoreResponseSuccess = (apiAdminCategoriesStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminCategoriesStoreResponse = (apiAdminCategoriesStoreResponseSuccess)

export const getApiAdminCategoriesStoreUrl = () => {




  return `/api/admin/categories`
}

/**
 * @summary ApiAdminCategoriesStore
 */
export const apiAdminCategoriesStore = async (categoryIn: CategoryIn, options?: RequestInit): Promise<apiAdminCategoriesStoreResponse> => {

  return apiFetch<apiAdminCategoriesStoreResponse>(getApiAdminCategoriesStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(categoryIn)
  }
);}



export type apiAdminCategoriesUpdatePutResponse200 = {
  data: AdminCategoryOut
  status: 200
}

export type apiAdminCategoriesUpdatePutResponse400 = {
  data: ApiAdminCategoriesUpdatePut400
  status: 400
}

export type apiAdminCategoriesUpdatePutResponseSuccess = (apiAdminCategoriesUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminCategoriesUpdatePutResponseError = (apiAdminCategoriesUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminCategoriesUpdatePutResponse = (apiAdminCategoriesUpdatePutResponseSuccess | apiAdminCategoriesUpdatePutResponseError)

export const getApiAdminCategoriesUpdatePutUrl = (category: string,) => {




  return `/api/admin/categories/${category}`
}

/**
 * @summary ApiAdminCategoriesUpdate
 */
export const apiAdminCategoriesUpdatePut = async (category: string,
    categoryUpdateIn: CategoryUpdateIn, options?: RequestInit): Promise<apiAdminCategoriesUpdatePutResponse> => {

  return apiFetch<apiAdminCategoriesUpdatePutResponse>(getApiAdminCategoriesUpdatePutUrl(category),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(categoryUpdateIn)
  }
);}



export type apiAdminCategoriesDestroyResponse200 = {
  data: MessageOut
  status: 200
}

export type apiAdminCategoriesDestroyResponse400 = {
  data: ApiAdminCategoriesDestroy400
  status: 400
}

export type apiAdminCategoriesDestroyResponseSuccess = (apiAdminCategoriesDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminCategoriesDestroyResponseError = (apiAdminCategoriesDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminCategoriesDestroyResponse = (apiAdminCategoriesDestroyResponseSuccess | apiAdminCategoriesDestroyResponseError)

export const getApiAdminCategoriesDestroyUrl = (category: string,) => {




  return `/api/admin/categories/${category}`
}

/**
 * @summary ApiAdminCategoriesDestroy
 */
export const apiAdminCategoriesDestroy = async (category: string, options?: RequestInit): Promise<apiAdminCategoriesDestroyResponse> => {

  return apiFetch<apiAdminCategoriesDestroyResponse>(getApiAdminCategoriesDestroyUrl(category),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminCategoriesUpdatePatchResponse200 = {
  data: AdminCategoryOut
  status: 200
}

export type apiAdminCategoriesUpdatePatchResponse400 = {
  data: ApiAdminCategoriesUpdatePatch400
  status: 400
}

export type apiAdminCategoriesUpdatePatchResponseSuccess = (apiAdminCategoriesUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminCategoriesUpdatePatchResponseError = (apiAdminCategoriesUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminCategoriesUpdatePatchResponse = (apiAdminCategoriesUpdatePatchResponseSuccess | apiAdminCategoriesUpdatePatchResponseError)

export const getApiAdminCategoriesUpdatePatchUrl = (category: string,) => {




  return `/api/admin/categories/${category}`
}

/**
 * @summary ApiAdminCategoriesUpdate
 */
export const apiAdminCategoriesUpdatePatch = async (category: string,
    categoryUpdateIn: CategoryUpdateIn, options?: RequestInit): Promise<apiAdminCategoriesUpdatePatchResponse> => {

  return apiFetch<apiAdminCategoriesUpdatePatchResponse>(getApiAdminCategoriesUpdatePatchUrl(category),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(categoryUpdateIn)
  }
);}



export type apiAdminVendorsIndexResponse200 = {
  data: AdminVendorOut[]
  status: 200
}

export type apiAdminVendorsIndexResponseSuccess = (apiAdminVendorsIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminVendorsIndexResponse = (apiAdminVendorsIndexResponseSuccess)

export const getApiAdminVendorsIndexUrl = () => {




  return `/api/admin/vendors`
}

/**
 * @summary ApiAdminVendorsIndex
 */
export const apiAdminVendorsIndex = async ( options?: RequestInit): Promise<apiAdminVendorsIndexResponse> => {

  return apiFetch<apiAdminVendorsIndexResponse>(getApiAdminVendorsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminVendorsStoreResponse201 = {
  data: AdminVendorOut
  status: 201
}

export type apiAdminVendorsStoreResponseSuccess = (apiAdminVendorsStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminVendorsStoreResponse = (apiAdminVendorsStoreResponseSuccess)

export const getApiAdminVendorsStoreUrl = () => {




  return `/api/admin/vendors`
}

/**
 * @summary ApiAdminVendorsStore
 */
export const apiAdminVendorsStore = async (vendorIn: VendorIn, options?: RequestInit): Promise<apiAdminVendorsStoreResponse> => {

  return apiFetch<apiAdminVendorsStoreResponse>(getApiAdminVendorsStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(vendorIn)
  }
);}



export type apiAdminVendorsUpdatePutResponse200 = {
  data: AdminVendorOut
  status: 200
}

export type apiAdminVendorsUpdatePutResponse400 = {
  data: ApiAdminVendorsUpdatePut400
  status: 400
}

export type apiAdminVendorsUpdatePutResponseSuccess = (apiAdminVendorsUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminVendorsUpdatePutResponseError = (apiAdminVendorsUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminVendorsUpdatePutResponse = (apiAdminVendorsUpdatePutResponseSuccess | apiAdminVendorsUpdatePutResponseError)

export const getApiAdminVendorsUpdatePutUrl = (vendor: string,) => {




  return `/api/admin/vendors/${vendor}`
}

/**
 * Rename or (un)publish a vendor — the publish flag gates the retrievability of every
 * product the vendor owns (recomputed by the debounced views refresh). catalog.update is
 * enforced by this controller's Authorize middleware (DR-0055).
 * @summary ApiAdminVendorsUpdate
 */
export const apiAdminVendorsUpdatePut = async (vendor: string,
    vendorUpdateIn: VendorUpdateIn, options?: RequestInit): Promise<apiAdminVendorsUpdatePutResponse> => {

  return apiFetch<apiAdminVendorsUpdatePutResponse>(getApiAdminVendorsUpdatePutUrl(vendor),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(vendorUpdateIn)
  }
);}



export type apiAdminVendorsUpdatePatchResponse200 = {
  data: AdminVendorOut
  status: 200
}

export type apiAdminVendorsUpdatePatchResponse400 = {
  data: ApiAdminVendorsUpdatePatch400
  status: 400
}

export type apiAdminVendorsUpdatePatchResponseSuccess = (apiAdminVendorsUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminVendorsUpdatePatchResponseError = (apiAdminVendorsUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminVendorsUpdatePatchResponse = (apiAdminVendorsUpdatePatchResponseSuccess | apiAdminVendorsUpdatePatchResponseError)

export const getApiAdminVendorsUpdatePatchUrl = (vendor: string,) => {




  return `/api/admin/vendors/${vendor}`
}

/**
 * Rename or (un)publish a vendor — the publish flag gates the retrievability of every
 * product the vendor owns (recomputed by the debounced views refresh). catalog.update is
 * enforced by this controller's Authorize middleware (DR-0055).
 * @summary ApiAdminVendorsUpdate
 */
export const apiAdminVendorsUpdatePatch = async (vendor: string,
    vendorUpdateIn: VendorUpdateIn, options?: RequestInit): Promise<apiAdminVendorsUpdatePatchResponse> => {

  return apiFetch<apiAdminVendorsUpdatePatchResponse>(getApiAdminVendorsUpdatePatchUrl(vendor),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(vendorUpdateIn)
  }
);}



export type apiAdminVariantsIndexResponse200 = {
  data: VariantOut[]
  status: 200
}

export type apiAdminVariantsIndexResponse400 = {
  data: ApiAdminVariantsIndex400
  status: 400
}

export type apiAdminVariantsIndexResponseSuccess = (apiAdminVariantsIndexResponse200) & {
  headers: Headers;
};
export type apiAdminVariantsIndexResponseError = (apiAdminVariantsIndexResponse400) & {
  headers: Headers;
};

export type apiAdminVariantsIndexResponse = (apiAdminVariantsIndexResponseSuccess | apiAdminVariantsIndexResponseError)

export const getApiAdminVariantsIndexUrl = (id: number,) => {




  return `/api/admin/products/${id}/variants`
}

/**
 * @summary ApiAdminVariantsIndex
 */
export const apiAdminVariantsIndex = async (id: number, options?: RequestInit): Promise<apiAdminVariantsIndexResponse> => {

  return apiFetch<apiAdminVariantsIndexResponse>(getApiAdminVariantsIndexUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminVariantsStoreResponse201 = {
  data: VariantOut
  status: 201
}

export type apiAdminVariantsStoreResponse400 = {
  data: ApiAdminVariantsStore400
  status: 400
}

export type apiAdminVariantsStoreResponseSuccess = (apiAdminVariantsStoreResponse201) & {
  headers: Headers;
};
export type apiAdminVariantsStoreResponseError = (apiAdminVariantsStoreResponse400) & {
  headers: Headers;
};

export type apiAdminVariantsStoreResponse = (apiAdminVariantsStoreResponseSuccess | apiAdminVariantsStoreResponseError)

export const getApiAdminVariantsStoreUrl = (id: number,) => {




  return `/api/admin/products/${id}/variants`
}

/**
 * @summary ApiAdminVariantsStore
 */
export const apiAdminVariantsStore = async (id: number,
    variantIn: VariantIn, options?: RequestInit): Promise<apiAdminVariantsStoreResponse> => {

  return apiFetch<apiAdminVariantsStoreResponse>(getApiAdminVariantsStoreUrl(id),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(variantIn)
  }
);}



export type apiAdminVariantsDestroyResponse200 = {
  data: MessageOut
  status: 200
}

export type apiAdminVariantsDestroyResponse400 = {
  data: ApiAdminVariantsDestroy400
  status: 400
}

export type apiAdminVariantsDestroyResponseSuccess = (apiAdminVariantsDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminVariantsDestroyResponseError = (apiAdminVariantsDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminVariantsDestroyResponse = (apiAdminVariantsDestroyResponseSuccess | apiAdminVariantsDestroyResponseError)

export const getApiAdminVariantsDestroyUrl = (id: number,
    variantId: number,) => {




  return `/api/admin/products/${id}/variants/${variantId}`
}

/**
 * Delete a variant. Order history can never dangle (422 when order lines reference it);
 * cart lines holding it are removed — the cart re-renders without the dead line.
 * @summary ApiAdminVariantsDestroy
 */
export const apiAdminVariantsDestroy = async (id: number,
    variantId: number, options?: RequestInit): Promise<apiAdminVariantsDestroyResponse> => {

  return apiFetch<apiAdminVariantsDestroyResponse>(getApiAdminVariantsDestroyUrl(id,variantId),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminVariantsUpdateResponse200 = {
  data: VariantOut
  status: 200
}

export type apiAdminVariantsUpdateResponse400 = {
  data: ApiAdminVariantsUpdate400
  status: 400
}

export type apiAdminVariantsUpdateResponseSuccess = (apiAdminVariantsUpdateResponse200) & {
  headers: Headers;
};
export type apiAdminVariantsUpdateResponseError = (apiAdminVariantsUpdateResponse400) & {
  headers: Headers;
};

export type apiAdminVariantsUpdateResponse = (apiAdminVariantsUpdateResponseSuccess | apiAdminVariantsUpdateResponseError)

export const getApiAdminVariantsUpdateUrl = (id: number,
    variantId: number,) => {




  return `/api/admin/products/${id}/variants/${variantId}`
}

/**
 * @summary ApiAdminVariantsUpdate
 */
export const apiAdminVariantsUpdate = async (id: number,
    variantId: number,
    variantUpdateIn: VariantUpdateIn, options?: RequestInit): Promise<apiAdminVariantsUpdateResponse> => {

  return apiFetch<apiAdminVariantsUpdateResponse>(getApiAdminVariantsUpdateUrl(id,variantId),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(variantUpdateIn)
  }
);}



export type apiAdminVariantsStockResponse200 = {
  data: VariantOut
  status: 200
}

export type apiAdminVariantsStockResponse400 = {
  data: ApiAdminVariantsStock400
  status: 400
}

export type apiAdminVariantsStockResponseSuccess = (apiAdminVariantsStockResponse200) & {
  headers: Headers;
};
export type apiAdminVariantsStockResponseError = (apiAdminVariantsStockResponse400) & {
  headers: Headers;
};

export type apiAdminVariantsStockResponse = (apiAdminVariantsStockResponseSuccess | apiAdminVariantsStockResponseError)

export const getApiAdminVariantsStockUrl = (id: number,
    variantId: number,) => {




  return `/api/admin/products/${id}/variants/${variantId}/stock`
}

/**
 * Set or shift a variant's stock — an explicit, audited operation, serialized under a row
 * lock so concurrent adjustments are deterministic.
 * @summary ApiAdminVariantsStock
 */
export const apiAdminVariantsStock = async (id: number,
    variantId: number,
    stockAdjustIn: StockAdjustIn, options?: RequestInit): Promise<apiAdminVariantsStockResponse> => {

  return apiFetch<apiAdminVariantsStockResponse>(getApiAdminVariantsStockUrl(id,variantId),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(stockAdjustIn)
  }
);}



export type apiAdminUsersIndexResponse200 = {
  data: AdminUserPage
  status: 200
}

export type apiAdminUsersIndexResponse400 = {
  data: ApiAdminUsersIndex400
  status: 400
}

export type apiAdminUsersIndexResponseSuccess = (apiAdminUsersIndexResponse200) & {
  headers: Headers;
};
export type apiAdminUsersIndexResponseError = (apiAdminUsersIndexResponse400) & {
  headers: Headers;
};

export type apiAdminUsersIndexResponse = (apiAdminUsersIndexResponseSuccess | apiAdminUsersIndexResponseError)

export const getApiAdminUsersIndexUrl = (params?: ApiAdminUsersIndexParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/admin/users?${stringifiedParams}` : `/api/admin/users`
}

/**
 * Search + paginate the user directory (name/email substring); users.view via the
 * route's Authorize.
 * @summary ApiAdminUsersIndex
 */
export const apiAdminUsersIndex = async (params?: ApiAdminUsersIndexParams, options?: RequestInit): Promise<apiAdminUsersIndexResponse> => {

  return apiFetch<apiAdminUsersIndexResponse>(getApiAdminUsersIndexUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminUsersShowResponse200 = {
  data: AdminUserDetailOut
  status: 200
}

export type apiAdminUsersShowResponse400 = {
  data: ApiAdminUsersShow400
  status: 400
}

export type apiAdminUsersShowResponseSuccess = (apiAdminUsersShowResponse200) & {
  headers: Headers;
};
export type apiAdminUsersShowResponseError = (apiAdminUsersShowResponse400) & {
  headers: Headers;
};

export type apiAdminUsersShowResponse = (apiAdminUsersShowResponseSuccess | apiAdminUsersShowResponseError)

export const getApiAdminUsersShowUrl = (id: number,) => {




  return `/api/admin/users/${id}`
}

/**
 * One user: profile basics, roles, and an order summary. users.view is enforced by the
 * route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or not the
 * user id exists.
 * @summary ApiAdminUsersShow
 */
export const apiAdminUsersShow = async (id: number, options?: RequestInit): Promise<apiAdminUsersShowResponse> => {

  return apiFetch<apiAdminUsersShowResponse>(getApiAdminUsersShowUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminRolesIndexResponse200 = {
  data: RoleOut[]
  status: 200
}

export type apiAdminRolesIndexResponseSuccess = (apiAdminRolesIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminRolesIndexResponse = (apiAdminRolesIndexResponseSuccess)

export const getApiAdminRolesIndexUrl = () => {




  return `/api/admin/roles`
}

/**
 * List every role with the permissions it grants (roles.manage via the route's Authorize).
 * @summary ApiAdminRolesIndex
 */
export const apiAdminRolesIndex = async ( options?: RequestInit): Promise<apiAdminRolesIndexResponse> => {

  return apiFetch<apiAdminRolesIndexResponse>(getApiAdminRolesIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminPermissionsIndexResponse200 = {
  data: PermissionOut[]
  status: 200
}

export type apiAdminPermissionsIndexResponseSuccess = (apiAdminPermissionsIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminPermissionsIndexResponse = (apiAdminPermissionsIndexResponseSuccess)

export const getApiAdminPermissionsIndexUrl = () => {




  return `/api/admin/permissions`
}

/**
 * List every permission in the system (roles.manage via the route's Authorize).
 * @summary ApiAdminPermissionsIndex
 */
export const apiAdminPermissionsIndex = async ( options?: RequestInit): Promise<apiAdminPermissionsIndexResponse> => {

  return apiFetch<apiAdminPermissionsIndexResponse>(getApiAdminPermissionsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminUsersRolesResponse200 = {
  data: UserRolesOut
  status: 200
}

export type apiAdminUsersRolesResponse400 = {
  data: ApiAdminUsersRoles400
  status: 400
}

export type apiAdminUsersRolesResponseSuccess = (apiAdminUsersRolesResponse200) & {
  headers: Headers;
};
export type apiAdminUsersRolesResponseError = (apiAdminUsersRolesResponse400) & {
  headers: Headers;
};

export type apiAdminUsersRolesResponse = (apiAdminUsersRolesResponseSuccess | apiAdminUsersRolesResponseError)

export const getApiAdminUsersRolesUrl = (id: number,) => {




  return `/api/admin/users/${id}/roles`
}

/**
 * The roles currently assigned to a user. roles.manage is enforced by the route's Authorize
 * middleware (DR-0055), so a denied caller 403s uniformly whether or not the user id exists.
 * @summary ApiAdminUsersRoles
 */
export const apiAdminUsersRoles = async (id: number, options?: RequestInit): Promise<apiAdminUsersRolesResponse> => {

  return apiFetch<apiAdminUsersRolesResponse>(getApiAdminUsersRolesUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminUsersRolesAssignResponse200 = {
  data: UserRolesOut
  status: 200
}

export type apiAdminUsersRolesAssignResponse400 = {
  data: ApiAdminUsersRolesAssign400
  status: 400
}

export type apiAdminUsersRolesAssignResponseSuccess = (apiAdminUsersRolesAssignResponse200) & {
  headers: Headers;
};
export type apiAdminUsersRolesAssignResponseError = (apiAdminUsersRolesAssignResponse400) & {
  headers: Headers;
};

export type apiAdminUsersRolesAssignResponse = (apiAdminUsersRolesAssignResponseSuccess | apiAdminUsersRolesAssignResponseError)

export const getApiAdminUsersRolesAssignUrl = (id: number,) => {




  return `/api/admin/users/${id}/roles`
}

/**
 * Assign a role to a user (roles.manage, enforced by the route's Authorize middleware —
 * DR-0055), recording it in the audit log.
 * @summary ApiAdminUsersRolesAssign
 */
export const apiAdminUsersRolesAssign = async (id: number,
    assignRoleIn: AssignRoleIn, options?: RequestInit): Promise<apiAdminUsersRolesAssignResponse> => {

  return apiFetch<apiAdminUsersRolesAssignResponse>(getApiAdminUsersRolesAssignUrl(id),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(assignRoleIn)
  }
);}



export type apiAdminUsersRolesRevokeResponse200 = {
  data: UserRolesOut
  status: 200
}

export type apiAdminUsersRolesRevokeResponse400 = {
  data: ApiAdminUsersRolesRevoke400
  status: 400
}

export type apiAdminUsersRolesRevokeResponseSuccess = (apiAdminUsersRolesRevokeResponse200) & {
  headers: Headers;
};
export type apiAdminUsersRolesRevokeResponseError = (apiAdminUsersRolesRevokeResponse400) & {
  headers: Headers;
};

export type apiAdminUsersRolesRevokeResponse = (apiAdminUsersRolesRevokeResponseSuccess | apiAdminUsersRolesRevokeResponseError)

export const getApiAdminUsersRolesRevokeUrl = (id: number,
    role: string,) => {




  return `/api/admin/users/${id}/roles/${role}`
}

/**
 * Revoke a role from a user (roles.manage, enforced by the route's Authorize middleware —
 * DR-0055), recording it in the audit log.
 * @summary ApiAdminUsersRolesRevoke
 */
export const apiAdminUsersRolesRevoke = async (id: number,
    role: string, options?: RequestInit): Promise<apiAdminUsersRolesRevokeResponse> => {

  return apiFetch<apiAdminUsersRolesRevokeResponse>(getApiAdminUsersRolesRevokeUrl(id,role),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminAuditIndexResponse200 = {
  data: ActivityOut[]
  status: 200
}

export type apiAdminAuditIndexResponseSuccess = (apiAdminAuditIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminAuditIndexResponse = (apiAdminAuditIndexResponseSuccess)

export const getApiAdminAuditIndexUrl = () => {




  return `/api/admin/audit`
}

/**
 * The most recent audit-log entries (audit.view via the route's Authorize).
 * @summary ApiAdminAuditIndex
 */
export const apiAdminAuditIndex = async ( options?: RequestInit): Promise<apiAdminAuditIndexResponse> => {

  return apiFetch<apiAdminAuditIndexResponse>(getApiAdminAuditIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminReviewsIndexResponse200 = {
  data: AdminReviewOut[]
  status: 200
}

export type apiAdminReviewsIndexResponse400 = {
  data: ApiAdminReviewsIndex400
  status: 400
}

export type apiAdminReviewsIndexResponseSuccess = (apiAdminReviewsIndexResponse200) & {
  headers: Headers;
};
export type apiAdminReviewsIndexResponseError = (apiAdminReviewsIndexResponse400) & {
  headers: Headers;
};

export type apiAdminReviewsIndexResponse = (apiAdminReviewsIndexResponseSuccess | apiAdminReviewsIndexResponseError)

export const getApiAdminReviewsIndexUrl = (params?: ApiAdminReviewsIndexParams,) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {

    if (value !== undefined) {
      normalizedParams.append(key, value === null ? 'null' : String(value))
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0 ? `/api/admin/reviews?${stringifiedParams}` : `/api/admin/reviews`
}

/**
 * @summary ApiAdminReviewsIndex
 */
export const apiAdminReviewsIndex = async (params?: ApiAdminReviewsIndexParams, options?: RequestInit): Promise<apiAdminReviewsIndexResponse> => {

  return apiFetch<apiAdminReviewsIndexResponse>(getApiAdminReviewsIndexUrl(params),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminReviewsModerateResponse200 = {
  data: AdminReviewOut
  status: 200
}

export type apiAdminReviewsModerateResponse400 = {
  data: ApiAdminReviewsModerate400
  status: 400
}

export type apiAdminReviewsModerateResponseSuccess = (apiAdminReviewsModerateResponse200) & {
  headers: Headers;
};
export type apiAdminReviewsModerateResponseError = (apiAdminReviewsModerateResponse400) & {
  headers: Headers;
};

export type apiAdminReviewsModerateResponse = (apiAdminReviewsModerateResponseSuccess | apiAdminReviewsModerateResponseError)

export const getApiAdminReviewsModerateUrl = (id: number,
    decision: string,) => {




  return `/api/admin/reviews/${id}/${decision}`
}

/**
 * Approve or reject (the path decides); approval feeds the denormalized aggregate — all
 * transitions keep it exact (approve adds, un-approve subtracts). reviews.moderate is enforced
 * by the route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or
 * not the review id exists.
 * @summary ApiAdminReviewsModerate
 */
export const apiAdminReviewsModerate = async (id: number,
    decision: string, options?: RequestInit): Promise<apiAdminReviewsModerateResponse> => {

  return apiFetch<apiAdminReviewsModerateResponse>(getApiAdminReviewsModerateUrl(id,decision),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminSettingsResponse200 = {
  data: SettingsOut
  status: 200
}

export type apiAdminSettingsResponseSuccess = (apiAdminSettingsResponse200) & {
  headers: Headers;
};
;

export type apiAdminSettingsResponse = (apiAdminSettingsResponseSuccess)

export const getApiAdminSettingsUrl = () => {




  return `/api/admin/settings`
}

/**
 * @summary ApiAdminSettings
 */
export const apiAdminSettings = async ( options?: RequestInit): Promise<apiAdminSettingsResponse> => {

  return apiFetch<apiAdminSettingsResponse>(getApiAdminSettingsUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminSettingsUpdateResponse200 = {
  data: SettingsOut
  status: 200
}

export type apiAdminSettingsUpdateResponseSuccess = (apiAdminSettingsUpdateResponse200) & {
  headers: Headers;
};
;

export type apiAdminSettingsUpdateResponse = (apiAdminSettingsUpdateResponseSuccess)

export const getApiAdminSettingsUpdateUrl = () => {




  return `/api/admin/settings`
}

/**
 * @summary ApiAdminSettingsUpdate
 */
export const apiAdminSettingsUpdate = async (settingsIn: SettingsIn, options?: RequestInit): Promise<apiAdminSettingsUpdateResponse> => {

  return apiFetch<apiAdminSettingsUpdateResponse>(getApiAdminSettingsUpdateUrl(),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(settingsIn)
  }
);}



export type apiAdminMediaResponse200 = {
  data: MediaItemOut[]
  status: 200
}

export type apiAdminMediaResponseSuccess = (apiAdminMediaResponse200) & {
  headers: Headers;
};
;

export type apiAdminMediaResponse = (apiAdminMediaResponseSuccess)

export const getApiAdminMediaUrl = () => {




  return `/api/admin/media`
}

/**
 * @summary ApiAdminMedia
 */
export const apiAdminMedia = async ( options?: RequestInit): Promise<apiAdminMediaResponse> => {

  return apiFetch<apiAdminMediaResponse>(getApiAdminMediaUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminNewsletterResponse200 = {
  data: NewsletterSubscriberOut[]
  status: 200
}

export type apiAdminNewsletterResponseSuccess = (apiAdminNewsletterResponse200) & {
  headers: Headers;
};
;

export type apiAdminNewsletterResponse = (apiAdminNewsletterResponseSuccess)

export const getApiAdminNewsletterUrl = () => {




  return `/api/admin/newsletter`
}

/**
 * @summary ApiAdminNewsletter
 */
export const apiAdminNewsletter = async ( options?: RequestInit): Promise<apiAdminNewsletterResponse> => {

  return apiFetch<apiAdminNewsletterResponse>(getApiAdminNewsletterUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminBannersImageResponse201 = {
  data: AdminBannerOut
  status: 201
}

export type apiAdminBannersImageResponse400 = {
  data: ApiAdminBannersImage400
  status: 400
}

export type apiAdminBannersImageResponseSuccess = (apiAdminBannersImageResponse201) & {
  headers: Headers;
};
export type apiAdminBannersImageResponseError = (apiAdminBannersImageResponse400) & {
  headers: Headers;
};

export type apiAdminBannersImageResponse = (apiAdminBannersImageResponseSuccess | apiAdminBannersImageResponseError)

export const getApiAdminBannersImageUrl = (id: number,) => {




  return `/api/admin/banners/${id}/image`
}

/**
 * Attach/replace the slide image (the previous one is removed — a slide has ONE image).
 * @summary ApiAdminBannersImage
 */
export const apiAdminBannersImage = async (id: number, options?: RequestInit): Promise<apiAdminBannersImageResponse> => {

  return apiFetch<apiAdminBannersImageResponse>(getApiAdminBannersImageUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type apiAdminBannersIndexResponse200 = {
  data: AdminBannerOut[]
  status: 200
}

export type apiAdminBannersIndexResponseSuccess = (apiAdminBannersIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminBannersIndexResponse = (apiAdminBannersIndexResponseSuccess)

export const getApiAdminBannersIndexUrl = () => {




  return `/api/admin/banners`
}

/**
 * @summary ApiAdminBannersIndex
 */
export const apiAdminBannersIndex = async ( options?: RequestInit): Promise<apiAdminBannersIndexResponse> => {

  return apiFetch<apiAdminBannersIndexResponse>(getApiAdminBannersIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminBannersStoreResponse201 = {
  data: AdminBannerOut
  status: 201
}

export type apiAdminBannersStoreResponseSuccess = (apiAdminBannersStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminBannersStoreResponse = (apiAdminBannersStoreResponseSuccess)

export const getApiAdminBannersStoreUrl = () => {




  return `/api/admin/banners`
}

/**
 * @summary ApiAdminBannersStore
 */
export const apiAdminBannersStore = async (bannerIn: BannerIn, options?: RequestInit): Promise<apiAdminBannersStoreResponse> => {

  return apiFetch<apiAdminBannersStoreResponse>(getApiAdminBannersStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(bannerIn)
  }
);}



export type apiAdminBannersUpdatePutResponse200 = {
  data: AdminBannerOut
  status: 200
}

export type apiAdminBannersUpdatePutResponse400 = {
  data: ApiAdminBannersUpdatePut400
  status: 400
}

export type apiAdminBannersUpdatePutResponseSuccess = (apiAdminBannersUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminBannersUpdatePutResponseError = (apiAdminBannersUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminBannersUpdatePutResponse = (apiAdminBannersUpdatePutResponseSuccess | apiAdminBannersUpdatePutResponseError)

export const getApiAdminBannersUpdatePutUrl = (banner: string,) => {




  return `/api/admin/banners/${banner}`
}

/**
 * @summary ApiAdminBannersUpdate
 */
export const apiAdminBannersUpdatePut = async (banner: string,
    bannerUpdateIn: BannerUpdateIn, options?: RequestInit): Promise<apiAdminBannersUpdatePutResponse> => {

  return apiFetch<apiAdminBannersUpdatePutResponse>(getApiAdminBannersUpdatePutUrl(banner),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(bannerUpdateIn)
  }
);}



export type apiAdminBannersDestroyResponse200 = {
  data: ApiAdminBannersDestroy200
  status: 200
}

export type apiAdminBannersDestroyResponse400 = {
  data: ApiAdminBannersDestroy400
  status: 400
}

export type apiAdminBannersDestroyResponseSuccess = (apiAdminBannersDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminBannersDestroyResponseError = (apiAdminBannersDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminBannersDestroyResponse = (apiAdminBannersDestroyResponseSuccess | apiAdminBannersDestroyResponseError)

export const getApiAdminBannersDestroyUrl = (banner: string,) => {




  return `/api/admin/banners/${banner}`
}

/**
 * @summary ApiAdminBannersDestroy
 */
export const apiAdminBannersDestroy = async (banner: string, options?: RequestInit): Promise<apiAdminBannersDestroyResponse> => {

  return apiFetch<apiAdminBannersDestroyResponse>(getApiAdminBannersDestroyUrl(banner),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminBannersUpdatePatchResponse200 = {
  data: AdminBannerOut
  status: 200
}

export type apiAdminBannersUpdatePatchResponse400 = {
  data: ApiAdminBannersUpdatePatch400
  status: 400
}

export type apiAdminBannersUpdatePatchResponseSuccess = (apiAdminBannersUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminBannersUpdatePatchResponseError = (apiAdminBannersUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminBannersUpdatePatchResponse = (apiAdminBannersUpdatePatchResponseSuccess | apiAdminBannersUpdatePatchResponseError)

export const getApiAdminBannersUpdatePatchUrl = (banner: string,) => {




  return `/api/admin/banners/${banner}`
}

/**
 * @summary ApiAdminBannersUpdate
 */
export const apiAdminBannersUpdatePatch = async (banner: string,
    bannerUpdateIn: BannerUpdateIn, options?: RequestInit): Promise<apiAdminBannersUpdatePatchResponse> => {

  return apiFetch<apiAdminBannersUpdatePatchResponse>(getApiAdminBannersUpdatePatchUrl(banner),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(bannerUpdateIn)
  }
);}



export type apiAdminDealsIndexResponse200 = {
  data: AdminDealOut[]
  status: 200
}

export type apiAdminDealsIndexResponseSuccess = (apiAdminDealsIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminDealsIndexResponse = (apiAdminDealsIndexResponseSuccess)

export const getApiAdminDealsIndexUrl = () => {




  return `/api/admin/deals`
}

/**
 * @summary ApiAdminDealsIndex
 */
export const apiAdminDealsIndex = async ( options?: RequestInit): Promise<apiAdminDealsIndexResponse> => {

  return apiFetch<apiAdminDealsIndexResponse>(getApiAdminDealsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminDealsStoreResponse201 = {
  data: AdminDealOut
  status: 201
}

export type apiAdminDealsStoreResponseSuccess = (apiAdminDealsStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminDealsStoreResponse = (apiAdminDealsStoreResponseSuccess)

export const getApiAdminDealsStoreUrl = () => {




  return `/api/admin/deals`
}

/**
 * @summary ApiAdminDealsStore
 */
export const apiAdminDealsStore = async (dealIn: DealIn, options?: RequestInit): Promise<apiAdminDealsStoreResponse> => {

  return apiFetch<apiAdminDealsStoreResponse>(getApiAdminDealsStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(dealIn)
  }
);}



export type apiAdminDealsUpdatePutResponse200 = {
  data: AdminDealOut
  status: 200
}

export type apiAdminDealsUpdatePutResponse400 = {
  data: ApiAdminDealsUpdatePut400
  status: 400
}

export type apiAdminDealsUpdatePutResponseSuccess = (apiAdminDealsUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminDealsUpdatePutResponseError = (apiAdminDealsUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminDealsUpdatePutResponse = (apiAdminDealsUpdatePutResponseSuccess | apiAdminDealsUpdatePutResponseError)

export const getApiAdminDealsUpdatePutUrl = (deal: string,) => {




  return `/api/admin/deals/${deal}`
}

/**
 * @summary ApiAdminDealsUpdate
 */
export const apiAdminDealsUpdatePut = async (deal: string,
    dealUpdateIn: DealUpdateIn, options?: RequestInit): Promise<apiAdminDealsUpdatePutResponse> => {

  return apiFetch<apiAdminDealsUpdatePutResponse>(getApiAdminDealsUpdatePutUrl(deal),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(dealUpdateIn)
  }
);}



export type apiAdminDealsDestroyResponse200 = {
  data: ApiAdminDealsDestroy200
  status: 200
}

export type apiAdminDealsDestroyResponse400 = {
  data: ApiAdminDealsDestroy400
  status: 400
}

export type apiAdminDealsDestroyResponseSuccess = (apiAdminDealsDestroyResponse200) & {
  headers: Headers;
};
export type apiAdminDealsDestroyResponseError = (apiAdminDealsDestroyResponse400) & {
  headers: Headers;
};

export type apiAdminDealsDestroyResponse = (apiAdminDealsDestroyResponseSuccess | apiAdminDealsDestroyResponseError)

export const getApiAdminDealsDestroyUrl = (deal: string,) => {




  return `/api/admin/deals/${deal}`
}

/**
 * @summary ApiAdminDealsDestroy
 */
export const apiAdminDealsDestroy = async (deal: string, options?: RequestInit): Promise<apiAdminDealsDestroyResponse> => {

  return apiFetch<apiAdminDealsDestroyResponse>(getApiAdminDealsDestroyUrl(deal),
  {
    ...options,
    method: 'DELETE'


  }
);}



export type apiAdminDealsUpdatePatchResponse200 = {
  data: AdminDealOut
  status: 200
}

export type apiAdminDealsUpdatePatchResponse400 = {
  data: ApiAdminDealsUpdatePatch400
  status: 400
}

export type apiAdminDealsUpdatePatchResponseSuccess = (apiAdminDealsUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminDealsUpdatePatchResponseError = (apiAdminDealsUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminDealsUpdatePatchResponse = (apiAdminDealsUpdatePatchResponseSuccess | apiAdminDealsUpdatePatchResponseError)

export const getApiAdminDealsUpdatePatchUrl = (deal: string,) => {




  return `/api/admin/deals/${deal}`
}

/**
 * @summary ApiAdminDealsUpdate
 */
export const apiAdminDealsUpdatePatch = async (deal: string,
    dealUpdateIn: DealUpdateIn, options?: RequestInit): Promise<apiAdminDealsUpdatePatchResponse> => {

  return apiFetch<apiAdminDealsUpdatePatchResponse>(getApiAdminDealsUpdatePatchUrl(deal),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(dealUpdateIn)
  }
);}



export type apiAdminCouponsIndexResponse200 = {
  data: AdminCouponOut[]
  status: 200
}

export type apiAdminCouponsIndexResponseSuccess = (apiAdminCouponsIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminCouponsIndexResponse = (apiAdminCouponsIndexResponseSuccess)

export const getApiAdminCouponsIndexUrl = () => {




  return `/api/admin/coupons`
}

/**
 * @summary ApiAdminCouponsIndex
 */
export const apiAdminCouponsIndex = async ( options?: RequestInit): Promise<apiAdminCouponsIndexResponse> => {

  return apiFetch<apiAdminCouponsIndexResponse>(getApiAdminCouponsIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminCouponsStoreResponse201 = {
  data: AdminCouponOut
  status: 201
}

export type apiAdminCouponsStoreResponseSuccess = (apiAdminCouponsStoreResponse201) & {
  headers: Headers;
};
;

export type apiAdminCouponsStoreResponse = (apiAdminCouponsStoreResponseSuccess)

export const getApiAdminCouponsStoreUrl = () => {




  return `/api/admin/coupons`
}

/**
 * @summary ApiAdminCouponsStore
 */
export const apiAdminCouponsStore = async (couponIn: CouponIn, options?: RequestInit): Promise<apiAdminCouponsStoreResponse> => {

  return apiFetch<apiAdminCouponsStoreResponse>(getApiAdminCouponsStoreUrl(),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(couponIn)
  }
);}



export type apiAdminCouponsUpdatePutResponse200 = {
  data: AdminCouponOut
  status: 200
}

export type apiAdminCouponsUpdatePutResponse400 = {
  data: ApiAdminCouponsUpdatePut400
  status: 400
}

export type apiAdminCouponsUpdatePutResponseSuccess = (apiAdminCouponsUpdatePutResponse200) & {
  headers: Headers;
};
export type apiAdminCouponsUpdatePutResponseError = (apiAdminCouponsUpdatePutResponse400) & {
  headers: Headers;
};

export type apiAdminCouponsUpdatePutResponse = (apiAdminCouponsUpdatePutResponseSuccess | apiAdminCouponsUpdatePutResponseError)

export const getApiAdminCouponsUpdatePutUrl = (coupon: string,) => {




  return `/api/admin/coupons/${coupon}`
}

/**
 * Activate/deactivate or adjust limits — deactivation takes effect immediately (checkout
 * re-validates every redemption). catalog.update is enforced by this controller's Authorize
 * middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists.
 * @summary ApiAdminCouponsUpdate
 */
export const apiAdminCouponsUpdatePut = async (coupon: string,
    couponUpdateIn: CouponUpdateIn, options?: RequestInit): Promise<apiAdminCouponsUpdatePutResponse> => {

  return apiFetch<apiAdminCouponsUpdatePutResponse>(getApiAdminCouponsUpdatePutUrl(coupon),
  {
    ...options,
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(couponUpdateIn)
  }
);}



export type apiAdminCouponsUpdatePatchResponse200 = {
  data: AdminCouponOut
  status: 200
}

export type apiAdminCouponsUpdatePatchResponse400 = {
  data: ApiAdminCouponsUpdatePatch400
  status: 400
}

export type apiAdminCouponsUpdatePatchResponseSuccess = (apiAdminCouponsUpdatePatchResponse200) & {
  headers: Headers;
};
export type apiAdminCouponsUpdatePatchResponseError = (apiAdminCouponsUpdatePatchResponse400) & {
  headers: Headers;
};

export type apiAdminCouponsUpdatePatchResponse = (apiAdminCouponsUpdatePatchResponseSuccess | apiAdminCouponsUpdatePatchResponseError)

export const getApiAdminCouponsUpdatePatchUrl = (coupon: string,) => {




  return `/api/admin/coupons/${coupon}`
}

/**
 * Activate/deactivate or adjust limits — deactivation takes effect immediately (checkout
 * re-validates every redemption). catalog.update is enforced by this controller's Authorize
 * middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists.
 * @summary ApiAdminCouponsUpdate
 */
export const apiAdminCouponsUpdatePatch = async (coupon: string,
    couponUpdateIn: CouponUpdateIn, options?: RequestInit): Promise<apiAdminCouponsUpdatePatchResponse> => {

  return apiFetch<apiAdminCouponsUpdatePatchResponse>(getApiAdminCouponsUpdatePatchUrl(coupon),
  {
    ...options,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(couponUpdateIn)
  }
);}



export type apiAdminOrdersIndexResponse200 = {
  data: OrderOut[]
  status: 200
}

export type apiAdminOrdersIndexResponseSuccess = (apiAdminOrdersIndexResponse200) & {
  headers: Headers;
};
;

export type apiAdminOrdersIndexResponse = (apiAdminOrdersIndexResponseSuccess)

export const getApiAdminOrdersIndexUrl = () => {




  return `/api/admin/orders`
}

/**
 * List orders (newest first) for the back office, narrowed by ``?status=`` and searched
 * by ``?q=`` (order id, or a case-insensitive contact-email fragment). Requires orders.view.
 * @summary ApiAdminOrdersIndex
 */
export const apiAdminOrdersIndex = async ( options?: RequestInit): Promise<apiAdminOrdersIndexResponse> => {

  return apiFetch<apiAdminOrdersIndexResponse>(getApiAdminOrdersIndexUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminOrdersShowResponse200 = {
  data: AdminOrderDetailOut
  status: 200
}

export type apiAdminOrdersShowResponse400 = {
  data: ApiAdminOrdersShow400
  status: 400
}

export type apiAdminOrdersShowResponseSuccess = (apiAdminOrdersShowResponse200) & {
  headers: Headers;
};
export type apiAdminOrdersShowResponseError = (apiAdminOrdersShowResponse400) & {
  headers: Headers;
};

export type apiAdminOrdersShowResponse = (apiAdminOrdersShowResponseSuccess | apiAdminOrdersShowResponseError)

export const getApiAdminOrdersShowUrl = (id: number,) => {




  return `/api/admin/orders/${id}`
}

/**
 * Everything a staff member needs on one order: lines (purchase snapshots), breakdown,
 * address + contact, the customer link (or guest label), payment + webhook-backed states, and
 * the transition history from the activity trail. Requires orders.view.
 * @summary ApiAdminOrdersShow
 */
export const apiAdminOrdersShow = async (id: number, options?: RequestInit): Promise<apiAdminOrdersShowResponse> => {

  return apiFetch<apiAdminOrdersShowResponse>(getApiAdminOrdersShowUrl(id),
  {
    ...options,
    method: 'GET'


  }
);}



export type apiAdminOrdersStatusResponse200 = {
  data: OrderOut
  status: 200
}

export type apiAdminOrdersStatusResponse400 = {
  data: ApiAdminOrdersStatus400
  status: 400
}

export type apiAdminOrdersStatusResponseSuccess = (apiAdminOrdersStatusResponse200) & {
  headers: Headers;
};
export type apiAdminOrdersStatusResponseError = (apiAdminOrdersStatusResponse400) & {
  headers: Headers;
};

export type apiAdminOrdersStatusResponse = (apiAdminOrdersStatusResponseSuccess | apiAdminOrdersStatusResponseError)

export const getApiAdminOrdersStatusUrl = (id: number,) => {




  return `/api/admin/orders/${id}/status`
}

/**
 * Transition an order, enforcing the state machine. orders.update is enforced by the route's
 * Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists.
 * @summary ApiAdminOrdersStatus
 */
export const apiAdminOrdersStatus = async (id: number,
    orderStatusIn: OrderStatusIn, options?: RequestInit): Promise<apiAdminOrdersStatusResponse> => {

  return apiFetch<apiAdminOrdersStatusResponse>(getApiAdminOrdersStatusUrl(id),
  {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: JSON.stringify(orderStatusIn)
  }
);}



export type apiAdminOrdersRefundResponse200 = {
  data: OrderOut
  status: 200
}

export type apiAdminOrdersRefundResponse400 = {
  data: ApiAdminOrdersRefund400
  status: 400
}

export type apiAdminOrdersRefundResponseSuccess = (apiAdminOrdersRefundResponse200) & {
  headers: Headers;
};
export type apiAdminOrdersRefundResponseError = (apiAdminOrdersRefundResponse400) & {
  headers: Headers;
};

export type apiAdminOrdersRefundResponse = (apiAdminOrdersRefundResponseSuccess | apiAdminOrdersRefundResponseError)

export const getApiAdminOrdersRefundUrl = (id: number,) => {




  return `/api/admin/orders/${id}/refund`
}

/**
 * Admin-issued refund/return (K15): PAID (a support cancel) or SHIPPED (the one documented
 * return case) -> REFUND_PENDING via the same `refund_service.initiate_refund` the customer
 * /cancel route uses — one money-moving code path, two entry points. orders.update is enforced
 * by the route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or
 * not the id exists.
 * @summary ApiAdminOrdersRefund
 */
export const apiAdminOrdersRefund = async (id: number, options?: RequestInit): Promise<apiAdminOrdersRefundResponse> => {

  return apiFetch<apiAdminOrdersRefundResponse>(getApiAdminOrdersRefundUrl(id),
  {
    ...options,
    method: 'POST'


  }
);}



export type aiMcpResponse201 = {
  data: Response
  status: 201
}

export type aiMcpResponseSuccess = (aiMcpResponse201) & {
  headers: Headers;
};
;

export type aiMcpResponse = (aiMcpResponseSuccess)

export const getAiMcpUrl = () => {




  return `/mcp`
}

/**
 * @summary AiMcp
 */
export const aiMcp = async ( options?: RequestInit): Promise<aiMcpResponse> => {

  return apiFetch<aiMcpResponse>(getAiMcpUrl(),
  {
    ...options,
    method: 'POST'


  }
);}



export type aiMcpMetadataResponse200 = {
  data: AiMcpMetadata200
  status: 200
}

export type aiMcpMetadataResponseSuccess = (aiMcpMetadataResponse200) & {
  headers: Headers;
};
;

export type aiMcpMetadataResponse = (aiMcpMetadataResponseSuccess)

export const getAiMcpMetadataUrl = () => {




  return `/.well-known/oauth-protected-resource`
}

/**
 * @summary AiMcpMetadata
 */
export const aiMcpMetadata = async ( options?: RequestInit): Promise<aiMcpMetadataResponse> => {

  return apiFetch<aiMcpMetadataResponse>(getAiMcpMetadataUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type publicRootResponse200 = {
  data: unknown
  status: 200
}

export type publicRootResponseSuccess = (publicRootResponse200) & {
  headers: Headers;
};
;

export type publicRootResponse = (publicRootResponseSuccess)

export const getPublicRootUrl = () => {




  return `/`
}

/**
 * @summary PublicRoot
 */
export const publicRoot = async ( options?: RequestInit): Promise<publicRootResponse> => {

  return apiFetch<publicRootResponse>(getPublicRootUrl(),
  {
    ...options,
    method: 'GET'


  }
);}



export type _publicResponse200 = {
  data: unknown
  status: 200
}

export type _publicResponse400 = {
  data: _Public400
  status: 400
}

export type _publicResponseSuccess = (_publicResponse200) & {
  headers: Headers;
};
export type _publicResponseError = (_publicResponse400) & {
  headers: Headers;
};

export type _publicResponse = (_publicResponseSuccess | _publicResponseError)

export const getPublicUrl = (path: string,) => {




  return `/${path}`
}

/**
 * @summary Public
 */
export const _public = async (path: string, options?: RequestInit): Promise<_publicResponse> => {

  return apiFetch<_publicResponse>(getPublicUrl(path),
  {
    ...options,
    method: 'GET'


  }
);}
