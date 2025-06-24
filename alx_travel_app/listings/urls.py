from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet
from alx_travel_app.listings import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('booking/<int:booking_id>/initiate-payment/', views.initiate_payment_view, name='initiate_payment'),
    path('payment/verify-callback/', views.payment_verification_callback_view, name='payment_verification_callback'),
    # Add paths for success/failure/pending/error pages if you are redirecting
    # path('booking/<int:booking_id>/payment_success/', your_success_view, name='payment_success'),
    # path('booking/<int:booking_id>/payment_failed/', your_failure_view, name='payment_failure'),
]