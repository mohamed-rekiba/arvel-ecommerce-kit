"""Product reviews — verified purchasers rate + review; admins moderate; the storefront shows
APPROVED reviews and the denormalized aggregate."""

from arvel import DB, abort
from app.auth.require import require_user as _current_user
from app.i18n import trans
from arvel.activitylog import activity
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException

from app.controllers.serializers import iso as _iso
from app.enums import OrderStatus, Permission, ReviewStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.review import Review
from app.models.user import User
from app.schemas import AdminReviewOut, ReviewIn, ReviewListOut, ReviewOut

# Only a delivered purchase earns a review — the customer has actually received the product.
_REVIEWABLE_STATUSES = {OrderStatus.DELIVERED}


def _out(review: Review, author: str | None = None) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        rating=review.rating,
        title=review.title,
        body=review.body,
        status=review.status,
        author=author,
        created_at=_iso(review.created_at),
    )


async def _has_purchased(user: User, product: Product) -> bool:
    """A qualifying purchase: an order line for any of the product's variants on a **delivered**
    order owned by the user (received, not merely paid/shipped)."""
    variants = await ProductVariant.where("product_id", product.id).get()
    variant_ids = [v.id for v in variants]
    if not variant_ids:
        return False
    orders = await Order.where("user_id", user.id).get()
    eligible = {
        o.id
        for o in orders
        if o.status in _REVIEWABLE_STATUSES  # cast by Order.__casts__
    }
    if not eligible:
        return False
    lines = await OrderItem.where_in("order_id", list(eligible)).get()
    return any(line.product_variant_id in variant_ids for line in lines)


async def index(request: Request) -> ReviewListOut:
    """APPROVED reviews for the product (+ the caller's own review, whatever its status)."""
    product = await Product.where("slug", request.path_param("slug")).first_or_fail()
    reviews = (
        await Review.where("subject_type", "Product")
        .where("subject_id", product.id)
        .where("status", ReviewStatus.APPROVED.value)
        .order_by("id", "desc")
        .get()
    )
    authors = (
        {
            u.id: u.name
            for u in await User.where_in("id", [r.user_id for r in reviews]).get()
        }
        if reviews
        else {}
    )
    mine = None
    user: User | None = current_user.get()
    if user is not None:
        own = (
            await Review.where("subject_type", "Product")
            .where("subject_id", product.id)
            .where("user_id", user.id)
            .first()
        )
        if own is not None:
            mine = _out(own, author=user.name)
    return ReviewListOut(
        reviews=[_out(r, author=authors.get(r.user_id)) for r in reviews],
        mine=mine,
        rating_count=product.rating_count or 0,
        rating_avg=(
            round((product.rating_sum or 0) / product.rating_count, 1)
            if product.rating_count
            else None
        ),
    )


async def store(request: Request, data: ReviewIn) -> ReviewOut:
    """Submit a review — verified purchasers only, one per product; lands PENDING."""
    user = _current_user()
    product = await Product.where("slug", request.path_param("slug")).first_or_fail()
    if not (1 <= data.rating <= 5):
        raise ValidationException({"rating": [trans("shop.errors.rating_range")]})
    if not data.body.strip():
        raise ValidationException({"body": [trans("shop.errors.review_body_required")]})
    if not await _has_purchased(user, product):
        abort(403, trans("shop.errors.review_requires_purchase"))
    existing = (
        await Review.where("subject_type", "Product")
        .where("subject_id", product.id)
        .where("user_id", user.id)
        .first()
    )
    if existing is not None:
        raise ValidationException({"review": [trans("shop.errors.already_reviewed")]})
    review = await Review.create(
        subject_type="Product",
        subject_id=product.id,
        user_id=user.id,
        rating=data.rating,
        title=data.title,
        body=data.body,
        status=ReviewStatus.PENDING,
    )
    return _out(review, author=user.name)


async def admin_index(
    request: Request, status: str = "pending"
) -> list[AdminReviewOut]:
    user = _current_user()
    if not await user.can(Permission.REVIEWS_MODERATE.value):
        abort(403, trans("shop.errors.no_reviews_moderate"))
    try:
        wanted = ReviewStatus(status)
    except ValueError:
        raise ValidationException(
            {"status": [trans("shop.errors.unknown_review_status")]}
        ) from None
    reviews = await Review.where("status", wanted.value).order_by("id").get()
    products = (
        {
            p.id: p.slug
            for p in await Product.with_trashed()
            .where_in("id", [r.subject_id for r in reviews])
            .get()
        }
        if reviews
        else {}
    )
    authors = (
        {
            u.id: u.name
            for u in await User.where_in("id", [r.user_id for r in reviews]).get()
        }
        if reviews
        else {}
    )
    return [
        AdminReviewOut(
            id=r.id,
            product_slug=products.get(r.subject_id, "?"),
            author=authors.get(r.user_id, "?"),
            rating=r.rating,
            title=r.title,
            body=r.body,
            status=r.status,
        )
        for r in reviews
    ]


async def moderate(request: Request, id: Review) -> AdminReviewOut:
    """Approve or reject (the path decides); approval feeds the denormalized aggregate — all
    transitions keep it exact (approve adds, un-approve subtracts). reviews.moderate is enforced
    by the route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or
    not the review id exists."""
    user = _current_user()
    decision = request.path_param("decision")
    if decision not in ("approve", "reject"):
        abort(404, trans("shop.errors.unknown_decision"))
    review = id
    target = ReviewStatus.APPROVED if decision == "approve" else ReviewStatus.REJECTED
    previous = review.status
    if target is not previous:
        async with DB.transaction():
            product = (
                await Product.with_trashed()
                .where("id", review.subject_id)
                .lock_for_update()
                .first_or_fail()
            )
            if target is ReviewStatus.APPROVED:
                product.rating_sum = (product.rating_sum or 0) + review.rating
                product.rating_count = (product.rating_count or 0) + 1
            elif previous is ReviewStatus.APPROVED:
                product.rating_sum = (product.rating_sum or 0) - review.rating
                product.rating_count = max((product.rating_count or 0) - 1, 0)
            await product.save()
            review.status = target
            await review.save()
        await (
            activity()
            .caused_by(user)
            .performed_on(review)
            .with_properties({"decision": decision})
            .log("moderated review")
        )
    author = await User.find(review.user_id)
    subject = await Product.find(review.subject_id)
    return AdminReviewOut(
        id=review.id,
        product_slug=subject.slug if subject else "?",
        author=author.name if author else "?",
        rating=review.rating,
        title=review.title,
        body=review.body,
        status=review.status,
    )
