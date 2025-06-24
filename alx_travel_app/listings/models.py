import uuid
from django.db import models
from django.conf import settings # If you link to the User model

class Listing(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    # owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    listing = models.ForeignKey(Listing, related_name='bookings', on_delete=models.CASCADE)
    # guest = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='bookings', on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100) # Simplified if not using User model for guests
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_guests = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking for {self.listing.name} by {self.guest_name}"
    
class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment_details')
    # Use the booking's reference or generate a new one specifically for Chapa's tx_ref
    # For simplicity, let's use a new one for tx_ref to keep it distinct if needed.
    transaction_reference = models.CharField(max_length=100, unique=True, editable=False) # Chapa's tx_ref
    chapa_transaction_id = models.CharField(max_length=255, blank=True, null=True) # ID from Chapa if they provide one beyond tx_ref
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="ETB") # Assuming Ethiopian Birr
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.transaction_reference:
            # Generate a unique transaction reference for Chapa
            self.transaction_reference = f"tx_{self.booking.booking_reference}_{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.transaction_reference} for Booking {self.booking.booking_reference} - {self.status}"