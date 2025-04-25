from django.shortcuts import render
from rest_framework.decorators import api_view
from django.db.models import Q
from rest_framework.response import Response
from .models import Cart, CartItem, Order, OrderItem, Product, Category, Review, Wishlist
from django.contrib.auth import get_user_model
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from .serializers import CartItemSerializer, CartSerializer, ProductListSerializer, ProductDetailSerializer, CategoryListSerializer, CategoryDetailSerializer, ReviewSerializer, WishlistSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.WEBHOOK_SECRET


# Create your views here.
@api_view(['GET'])
def products_list(request):
    products = Product.objects.filter(featured=True)
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)
    serializer = ProductDetailSerializer(product)
    return Response(serializer.data)


@api_view(['GET'])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategoryListSerializer(categories, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def category_detail(request, slug):
    try:
        category = Category.objects.get(slug=slug)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=404)
    serializer = CategoryDetailSerializer(category)
    return Response(serializer.data)

@api_view(['POST'])
def add_to_cart(request):
    # Logic to add a product to the cart
    cart_code = request.data.get("cart_code")
    product_id = request.data.get("product_id")

    cart, created = Cart.objects.get_or_create(cart_code=cart_code)
    product = Product.objects.get(id=product_id)

    cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
    cartitem.quantity = 1
    cartitem.save()

    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PUT'])
def update_cartitem_quantity(request):
    # Logic to update the quantity of a cart item
    cartitem_id = request.query_params.get("item_id")
    quantity = request.query_params.get("quantity")

    quantity = int(quantity)
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.quantity = quantity
    cartitem.save()

    serializer = CartItemSerializer(cartitem)
    return Response({"data": serializer.data, "message": "Cart item quantity updated successfully"})
    

@api_view(['DELETE'])
def delete_cartitem(request, pk):
    # Logic to delete a cart item
    cartitem = CartItem.objects.get(id=pk)
    cartitem.delete()
    return Response({"message": "Cart item deleted successfully"}, status=204)

User = get_user_model()

@api_view(['POST'])
def add_review(request):
   
    product_id = request.data.get("product_id") 
    email = request.data.get("email")
    rating = request.data.get("rating")
    review_text = request.data.get("review")

    user = User.objects.get(email=email)
    product = Product.objects.get(id=product_id)

    # Check if a review already exists for this user and product
    existing_review = Review.objects.filter(user=user, product=product).first()
    if existing_review:
        return Response(
            {"error": "You have already reviewed this product."},
            status=400
        )

    review = Review.objects.create(user=user, product=product, rating=rating, review=review_text)
    serializer = ReviewSerializer(review)
    return Response(serializer.data)

@api_view(['PUT'])
def update_review(request, pk):
    try:
        review = Review.objects.get(id=pk)
    except Review.DoesNotExist:
        return Response({"error": "Review not found"}, status=404)

    rating = request.data.get("rating")
    review_text = request.data.get("review")

    review.rating = rating
    review.review = review_text
    review.save()

    serializer = ReviewSerializer(review)
    return Response(serializer.data)


@api_view(['DELETE'])
def delete_review(request, pk):
    try:
        review = Review.objects.get(id=pk)
        review.delete()
        return Response({"message": "Review deleted successfully"}, status=204)
    except Review.DoesNotExist:
        return Response({"error": "Review not found"}, status=404)
    



@api_view(['POST'])
def add_to_wishlist(request):
    email = request.data.get("email")
    product_id = request.data.get("product_id")
    
    user = User.objects.get(email=email)
    product = Product.objects.get(id=product_id)

    wishlist = Wishlist.objects.filter(user=user, product=product)
    if wishlist:
        wishlist.delete()
        return Response({"message": "Product removed from wishlist"}, status=204)
    
    new_wishlist = Wishlist.objects.create(user=user, product=product)
    serializer = WishlistSerializer(new_wishlist)
    return Response(serializer.data, status=201)

@api_view(['GET'])
def product_search(request):
    query = request.query_params.get("query")
    if not query:
        return Response({"error": "Query parameter is required"}, status=400)
    
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query ) | Q(category__name__icontains=query)
    )
    
    serializer = ProductListSerializer(products, many=True)

    return Response(serializer.data)



@api_view(['POST'])
def create_checkout_session(request):
    email = request.data.get("email")
    #YOUR_DOMAIN = "https://nextshoppit.vercel.app"
    cart_code = request.data.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code)
    line_items_list = []
    for item in cart.cartitems.all():
        line_items_list.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item.product.name,
                },
                'unit_amount': int(item.product.price * 100),
            },
            'quantity': item.quantity,
        })
    
    try:
        checkout_session = stripe.checkout.Session.create(
            
            line_items=line_items_list,
            mode='payment',
            customer_email=email,
            payment_method_types=['card'],    
            success_url=f"https://nextshoppit.vercel.app/success",
            cancel_url=f"https://nextshoppit.vercel.app/cancel",
            metadata={"cart_code": cart_code},
        )   
        return Response({'data':checkout_session}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    
    
    

# Use the secret provided by Stripe CLI for local testing
# or your webhook endpoint's secret.


@csrf_exempt
def my_webhook_view(request):
  payload = request.body
  sig_header = request.META['HTTP_STRIPE_SIGNATURE']
  event = None

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, endpoint_secret
    )
  except ValueError as e:
    # Invalid payload
    return HttpResponse(status=400)
  except stripe.error.SignatureVerificationError as e:
    # Invalid signature
    return HttpResponse(status=400)

  if (
    event['type'] == 'checkout.session.completed'
    or event['type'] == 'checkout.session.async_payment_succeeded'
  ):
    session = event['data']['object']
    cart_code = session.get("metadata", {}).get("cart_code")
    fulfill_checkout(session, cart_code)

  return HttpResponse(status=200)

def fulfill_checkout(session, cart_code):
    order = Order.objects.create(stripe_checkout_id=session["id"],
        amount=session['amount_total'] / 100,
        currency=session['currency'],
        customer_email=session['customer_email'],
        status = 'Paid',)

    cart = Cart.objects.get(cart_code=cart_code)
    cartitem = cart.cartitems.all()
    for item in cartitem:
        orderitem = OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
        )
        
    cart.delete()