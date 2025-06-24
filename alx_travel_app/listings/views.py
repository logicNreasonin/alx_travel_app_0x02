# listings/views.py
from django.shortcuts import get_object_or_404, redirect # redirect might be useful for callback
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt # For simplicity in API callbacks, consider proper auth for production
from django.urls import reverse # To build callback URLs

import requests
import json
import uuid # For generating unique transaction references

from .models import Booking, Payment # Assuming Booking model is also in listings.models

# --- Helper Function for Chapa API Interaction ---
CHAPA_API_BASE_URL = "https://api.chapa.co/v1" # Use Chapa's sandbox URL for testing if available

def get_chapa_headers():
    return {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

# --- Initiate Payment View ---
@csrf_exempt # Ensure you understand CSRF implications for production APIs
def initiate_payment_view(request, booking_id):
    if request.method == "POST":
        try:
            booking = get_object_or_404(Booking, pk=booking_id)
            # Check if payment already initiated or completed for this booking
            if hasattr(booking, 'payment_details') and booking.payment_details.status == Payment.PaymentStatus.COMPLETED:
                return JsonResponse({"error": "Payment for this booking is already completed."}, status=400)
            if hasattr(booking, 'payment_details') and booking.payment_details.status == Payment.PaymentStatus.PENDING:
                # Potentially re-use existing pending payment or regenerate
                # For now, let's assume we create a new one or error if one is pending for too long
                # Here, we'll try to find an existing pending payment and use its tx_ref,
                # or create a new Payment record.
                payment, created = Payment.objects.get_or_create(
                    booking=booking,
                    defaults={
                        'amount': booking.amount_due,
                        'currency': "ETB", # Or get from booking/settings
                        'status': Payment.PaymentStatus.PENDING,
                        # transaction_reference will be set on save if not provided
                    }
                )
                if not created and payment.status != Payment.PaymentStatus.PENDING:
                    # If an existing payment is not PENDING (e.g. FAILED, COMPLETED) create new
                     payment = Payment.objects.create(
                        booking=booking,
                        amount=booking.amount_due,
                        currency="ETB",
                        status=Payment.PaymentStatus.PENDING
                    )
                elif not created and payment.status == Payment.PaymentStatus.PENDING:
                    # If reusing a PENDING payment, ensure its tx_ref is up-to-date or re-initialize if needed
                    # For simplicity, we assume its tx_ref is valid for re-initiation.
                    pass


            # User details - you might get this from the booking.user or request
            user = booking.user
            email = user.email if hasattr(user, 'email') else "customer@example.com"
            first_name = user.first_name if hasattr(user, 'first_name') and user.first_name else "Test"
            last_name = user.last_name if hasattr(user, 'last_name') and user.last_name else "User"
            phone_number = "0900000000" # Get from user profile if available

            # Construct callback URL dynamically
            # This URL will be where Chapa sends a notification (often a POST request)
            # It's also often where the user is redirected.
            # Make sure this endpoint is defined in your urls.py
            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()
            callback_url = f"{protocol}://{domain}{reverse('payment_verification_callback')}" # Name this URL pattern 'payment_verification_callback'
            # return_url is where the user is redirected. Could be same as callback or a success/failure page.
            # Chapa might use 'return_url' for user redirection after payment.
            return_url = callback_url # For simplicity, or a dedicated "thank you" page

            payload = {
                "amount": str(payment.amount),
                "currency": payment.currency,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "tx_ref": payment.transaction_reference, # Unique reference from your Payment model
                "callback_url": callback_url,
                "return_url": return_url, # Often same as callback or a thank you page
                "customization[title]": f"Payment for Booking {booking.booking_reference}",
                "customization[description]": f"Travel app booking payment for {booking.amount_due} {payment.currency}"
            }

            response = requests.post(
                f"{CHAPA_API_BASE_URL}/transaction/initialize",
                headers=get_chapa_headers(),
                json=payload
            )
            response_data = response.json()

            if response.status_code == 200 and response_data.get("status") == "success":
                checkout_url = response_data.get("data", {}).get("checkout_url")
                # Store chapa's internal reference if available (though tx_ref is our primary key for verification)
                # payment.chapa_transaction_id = response_data.get("data", {}).get("chapa_tx_id_if_any") # Check Chapa's response structure
                payment.save() # Ensure tx_ref is saved
                
                # The task asks to "provide them with a link".
                # In a real app, this might be part of a larger booking creation flow.
                # Here, we return the checkout URL.
                return JsonResponse({
                    "message": "Payment initiated successfully.",
                    "checkout_url": checkout_url,
                    "transaction_reference": payment.transaction_reference
                })
            else:
                payment.status = Payment.PaymentStatus.FAILED
                payment.save()
                error_message = response_data.get("message", "Failed to initiate payment with Chapa.")
                if response_data.get("errors"):
                     error_message += f" Details: {response_data.get('errors')}"
                return JsonResponse({"error": error_message, "chapa_response": response_data}, status=400)

        except Booking.DoesNotExist:
            return JsonResponse({"error": "Booking not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed."}, status=405)


# --- Payment Verification View (Callback from Chapa) ---
@csrf_exempt # Chapa will POST to this URL without a CSRF token from your site
def payment_verification_callback_view(request):
    # Chapa typically sends query parameters for GET or form data for POST on callback
    # The primary identifier is usually the 'tx_ref' we sent.
    # It might also include 'status' or other Chapa-specific params.
    # Consult Chapa documentation for the exact callback request structure.
    # For a server-to-server verification, we use the tx_ref to query Chapa's verify endpoint.

    # Example: If Chapa sends tx_ref as a query parameter on redirection
    tx_ref = request.GET.get('tx_ref') # Or request.POST.get('tx_ref')
    chapa_status = request.GET.get('status') # Chapa might send its own status in callback

    if not tx_ref:
        return JsonResponse({"error": "Transaction reference (tx_ref) not found in callback."}, status=400)

    try:
        payment = get_object_or_404(Payment, transaction_reference=tx_ref)
        
        # If payment is already completed or failed, don't re-process unless necessary
        if payment.status in [Payment.PaymentStatus.COMPLETED, Payment.PaymentStatus.FAILED]:
             # Redirect to a frontend page indicating the status
            return redirect(f"/booking/{payment.booking.id}/payment_status?status={payment.status.lower()}&tx_ref={tx_ref}")


        # Verify with Chapa API (server-to-server) - THIS IS THE CRUCIAL STEP
        verify_url = f"{CHAPA_API_BASE_URL}/transaction/verify/{tx_ref}"
        response = requests.get(verify_url, headers=get_chapa_headers())
        chapa_response_data = response.json()

        if response.status_code == 200 and chapa_response_data.get("status") == "success":
            # Chapa's data object contains the verified transaction details
            verified_data = chapa_response_data.get("data", {})
            verified_status = verified_data.get("status") # e.g., "success", "failed", "pending"

            if verified_status == "success":
                payment.status = Payment.PaymentStatus.COMPLETED
                from .tasks import send_payment_confirmation_email
                send_payment_confirmation_email.delay(payment.id)
                payment.chapa_transaction_id = verified_data.get("tx_ref") # Or other ID Chapa provides as their main ref
                payment.save()
                
                # TODO: Trigger Celery task for confirmation email
                # send_payment_confirmation_email.delay(payment.id)
                
                # Redirect user to a success page or provide JSON response
                # For a redirect based flow:
                return redirect(f"/booking/{payment.booking.id}/payment_success?tx_ref={tx_ref}")
                # For an API client:
                # return JsonResponse({"message": "Payment verified and completed.", "transaction_reference": tx_ref, "status": payment.status})

            elif verified_status in ["failed", "cancelled", "expired"]: # Check Chapa's status terms
                payment.status = Payment.PaymentStatus.FAILED # Or CANCELLED based on verified_status
                payment.save()
                # Redirect user to a failure page
                return redirect(f"/booking/{payment.booking.id}/payment_failed?tx_ref={tx_ref}&reason={verified_status}")
            else: # Still pending or other status
                payment.status = Payment.PaymentStatus.PENDING # Or map Chapa's status
                payment.save()
                # Redirect to a pending page or provide info
                return redirect(f"/booking/{payment.booking.id}/payment_pending?tx_ref={tx_ref}")
        else:
            # Verification API call failed
            payment.status = Payment.PaymentStatus.FAILED # Or keep PENDING and retry verification later
            payment.save()
            error_msg = chapa_response_data.get("message", "Failed to verify payment with Chapa.")
            # For a redirect based flow:
            return redirect(f"/booking/{payment.booking.id}/payment_error?tx_ref={tx_ref}&error={error_msg}")
            # For an API client:
            # return JsonResponse({"error": error_msg, "chapa_response": chapa_response_data}, status=400)

    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment record not found for this transaction reference."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred during payment verification: {str(e)}"}, status=500)
    
# You'll also need to create dummy views for these redirects or handle them in your frontend.
# e.g., /booking/<booking_id>/payment_success, /booking/<booking_id>/payment_failed etc.