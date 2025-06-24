# listings/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment, Booking # User

@shared_task
def send_payment_confirmation_email(payment_id):
    try:
        payment = Payment.objects.get(pk=payment_id)
        if payment.status == Payment.PaymentStatus.COMPLETED:
            booking = payment.booking
            user = booking.user
            subject = f"Payment Confirmation for Booking {booking.booking_reference}"
            message_body = (
                f"Dear {user.first_name or user.username},\n\n"
                f"Your payment of {payment.amount} {payment.currency} for booking {booking.booking_reference} has been successfully processed.\n\n"
                f"Transaction Reference: {payment.transaction_reference}\n"
                f"Thank you for booking with us!\n\n"
                f"Regards,\nYour Travel App Team"
            )
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL, # Configure in settings.py
                [user.email],
                fail_silently=False,
            )
            print(f"Confirmation email sent for payment {payment_id}")
    except Payment.DoesNotExist:
        print(f"Payment with ID {payment_id} not found for email task.")
    except Exception as e:
        print(f"Error sending confirmation email for payment {payment_id}: {str(e)}")