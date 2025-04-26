""" 
Detailed Description:
This module contains Django signals that are triggered when a review is saved or deleted.
These signals are used to update the average rating and total number of reviews for a product in the ProductRating model.

 """

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Review, ProductRating
from django.db.models import Avg


@receiver(post_save, sender=Review)
def update_product_rating_on_save(sender, instance, **kwargs):
    """
    Signal to update the product rating when a review is saved.
    """
    product = instance.product
    reviews = product.reviews.all()
    total_reviews = reviews.count()
    
    review_average = reviews.aggregate(Avg('rating')) or 0.0
    product_rating, created = ProductRating.objects.get_or_create(product=product)
    product_rating.average_rating = review_average['rating__avg'] if review_average['rating__avg'] is not None else 0.0
    product_rating.total_reviews = total_reviews
    product_rating.save()



@receiver(post_delete, sender=Review)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """
    Signal to update the product rating when a review is deleted.
    """
    product = instance.product
    reviews = product.reviews.all()
    total_reviews = reviews.count()
    
    if total_reviews > 0:
        review_average = reviews.aggregate(Avg('rating')) or 0.0
        product_rating, created = ProductRating.objects.get_or_create(product=product)
        product_rating.average_rating = review_average['rating__avg'] if review_average['rating__avg'] is not None else 0.0
        product_rating.total_reviews = total_reviews
        product_rating.save()
    else:
        # If no reviews left, set rating to 0 and total reviews to 0
        product_rating, created = ProductRating.objects.get_or_create(product=product)
        product_rating.average_rating = 0.0
        product_rating.total_reviews = 0
        product_rating.save()
    