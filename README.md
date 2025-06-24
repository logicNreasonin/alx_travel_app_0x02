# ALX Travel App 0x02 - Chapa Payment Integration

This project integrates the Chapa payment gateway into the ALX Travel App for processing booking payments.

## Features

- Payment initiation via Chapa API.
- Payment verification and status updates.
- `Payment` model to store transaction details.
- Conceptual integration of Celery for sending payment confirmation emails.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url> alx_travel_app_0x02
    cd alx_travel_app_0x02
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    # Ensure requirements.txt includes: Django, requests, python-dotenv, celery, redis (or other broker)
    ```

4.  **Set Up Environment Variables:**
    *   Sign up for a Chapa developer account at [https://developer.chapa.co/](https://developer.chapa.co/) to get your API Secret Key.
    *   Create a `.env` file in the project root directory (next to `manage.py`):
        ```        CHAPA_SECRET_KEY=your_chapa_secret_key_here
        # For email (if using Django's SMTP backend)
        EMAIL_HOST_USER=your_email@example.com
        EMAIL_HOST_PASSWORD=your_email_password
        DEFAULT_FROM_EMAIL=your_email@example.com
        # Celery broker URL (example for Redis)
        CELERY_BROKER_URL=redis://localhost:6379/0
        CELERY_RESULT_BACKEND=redis://localhost:6379/0
        ```
    *   **Important:** Add `.env` to your `.gitignore` file.

5.  **Apply Database Migrations:**
    ```bash
    python manage.py makemigrations listings
    python manage.py migrate
    ```

6.  **Run Development Server:**
    ```bash
    python manage.py runserver
    ```

7.  **(Optional) Run Celery Worker (for email tasks):**
    Ensure your message broker (e.g., Redis) is running.
    ```bash
    celery -A alx_travel_app worker -l info 
    # Replace 'alx_travel_app' with your actual Django project name if different
    ```

## API Endpoints

-   **Initiate Payment:** `POST /api/listings/booking/<booking_id>/initiate-payment/`
    -   Requires an existing `Booking` instance.
    -   Returns a Chapa `checkout_url`.
-   **Payment Verification Callback:** `GET` or `POST /api/listings/payment/verify-callback/`
    -   This URL is used by Chapa to redirect the user and send payment status updates.
    -   It verifies the payment with Chapa's server-to-server API.

## Workflow

1.  A user creates a `Booking`.
2.  The system calls the "Initiate Payment" endpoint with the `booking_id`.
3.  The user is redirected to the Chapa `checkout_url` to complete the payment.
4.  After payment attempt, Chapa calls the "Payment Verification Callback" URL.
5.  The callback view verifies the transaction with Chapa's API.
6.  The `Payment` model status is updated (e.g., "COMPLETED", "FAILED").
7.  If successful, a confirmation email is (conceptually) sent via a Celery task.

## Testing

-   Use Chapa's sandbox/test environment and test API keys.
-   **Initiation:** Make a POST request to the initiate payment endpoint for a booking. Check if you receive a valid `checkout_url`.
    ```bash
    # Example using curl, assuming booking with ID 1 exists
    curl -X POST http://localhost:8000/api/listings/booking/1/initiate-payment/
    ```
-   **Verification:** Follow the `checkout_url`. Complete or fail a payment in Chapa's sandbox.
    -   You should be redirected to your callback URL.
    -   Check the server logs for verification process output.
    -   Check the `Payment` model instance in the Django admin or shell to see if the status and `chapa_transaction_id` (if applicable) are updated correctly.
-   **Email:** If Celery is set up, check if the confirmation email task is queued and processed successfully upon completed payment.

### Example Logs/Screenshots to Include for Project Submission:

1.  **Successful Payment Initiation:**
    *   Screenshot of the JSON response from your `/initiate-payment/` endpoint showing the `checkout_url`.
    *   Log output from your Django server showing the request to Chapa's initialize API and the payload.
2.  **Chapa Payment Page:**
    *   Screenshot of the Chapa sandbox payment page after being redirected.
3.  **Successful Payment Verification:**
    *   Log output from your Django server for the `/payment/verify-callback/` endpoint showing:
        *   The request received from Chapa (or user redirection).
        *   The server-to-server verification request sent to Chapa's verify API.
        *   The response received from Chapa's verify API.
        *   Confirmation that the `Payment` model status was updated to "COMPLETED".
    *   Screenshot of the `Payment` model instance (e.g., from Django Admin) showing the "COMPLETED" status and other details.
4.  **Failed Payment Scenario:**
    *   Similar logs and screenshots as above, but demonstrating a "FAILED" status update.
5.  **(Optional) Celery Task Log:**
    *   Log output from the Celery worker showing the email task being received and processed.