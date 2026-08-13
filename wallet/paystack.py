"""
Paystack API integration for ISCOOA Facitech wallet top-up.
Handles transaction initialization and webhook verification.
"""
import hmac
import hashlib
import requests
from django.conf import settings


PAYSTACK_BASE_URL = 'https://api.paystack.co'


def get_headers():
    """Return Paystack API headers with secret key."""
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type':  'application/json',
    }


def initialize_transaction(email, amount_kobo, metadata=None, reference=None):
    """
    Initialize a Paystack transaction.

    Args:
        email:        Operator's email address
        amount_kobo:  Amount in kobo (Paystack uses kobo for NGN)
        metadata:     Optional dict of extra data to attach to the transaction
        reference:    Optional unique reference — Paystack generates one if not provided

    Returns:
        dict with keys:
            success:        bool
            authorization_url: URL to redirect user to for payment
            access_code:    Short code for embedded payment
            reference:      Unique transaction reference
            error:          Error message if success is False
    """
    payload = {
        'email':    email,
        'amount':   amount_kobo,
        'currency': 'NGN',
        'callback_url': settings.PAYSTACK_CALLBACK_URL,
        'metadata': metadata or {},
    }

    print(f"Callback URL being sent: {settings.PAYSTACK_CALLBACK_URL}")
    
    if reference:
        payload['reference'] = reference
    

    try:
        response = requests.post(
            f'{PAYSTACK_BASE_URL}/transaction/initialize',
            json    = payload,
            headers = get_headers(),
            timeout = 30,
        )
        data = response.json()

        if response.status_code == 200 and data.get('status'):
            return {
                'success':           True,
                'authorization_url': data['data']['authorization_url'],
                'access_code':       data['data']['access_code'],
                'reference':         data['data']['reference'],
            }
        else:
            return {
                'success': False,
                'error':   data.get('message', 'Paystack initialization failed.'),
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error':   'Paystack request timed out. Please try again.',
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error':   f'Network error: {str(e)}',
        }


def verify_transaction(reference):
    """
    Verify a Paystack transaction by reference.
    Call this from the callback URL or webhook to confirm payment.

    Returns:
        dict with keys:
            success:    bool
            status:     Transaction status (success, failed, abandoned)
            amount:     Amount in kobo
            email:      Customer email
            reference:  Transaction reference
            metadata:   Any metadata attached to the transaction
            error:      Error message if success is False
    """
    try:
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers = get_headers(),
            timeout = 30,
        )
        data = response.json()

        if response.status_code == 200 and data.get('status'):
            txn_data = data['data']
            return {
                'success':   True,
                'status':    txn_data['status'],
                # status is 'success', 'failed', or 'abandoned'
                'amount':    txn_data['amount'],
                'email':     txn_data['customer']['email'],
                'reference': txn_data['reference'],
                'metadata':  txn_data.get('metadata', {}),
                'channel':   txn_data.get('channel', ''),
                'paid_at':   txn_data.get('paid_at', ''),
            }
        else:
            return {
                'success': False,
                'error':   data.get('message', 'Transaction verification failed.'),
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error':   'Paystack verification request timed out.',
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error':   f'Network error: {str(e)}',
        }


def verify_webhook_signature(payload_bytes, signature_header):
    """
    Verify that a webhook request genuinely came from Paystack.
    Paystack signs every webhook with HMAC SHA512.

    Args:
        payload_bytes:     Raw request body as bytes
        signature_header:  Value of X-Paystack-Signature header

    Returns:
        bool — True if signature is valid
    """
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(
        secret,
        msg    = payload_bytes,
        digestmod = hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header)