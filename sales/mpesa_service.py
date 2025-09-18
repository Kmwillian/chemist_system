import requests
import base64
from datetime import datetime
from django.conf import settings

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.business_short_code = settings.MPESA_BUSINESS_SHORT_CODE
        self.passkey = settings.MPESA_PASSKEY
        self.base_url = settings.MPESA_BASE_URL
        self.callback_url = settings.MPESA_CALLBACK_URL
    
    def get_access_token(self):
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        
        headers = {'Authorization': f'Basic {auth_b64}'}
        response = requests.get(url, headers=headers)
        return response.json().get('access_token') if response.status_code == 200 else None
    
    def initiate_stk_push(self, phone_number, amount, account_reference):
        token = self.get_access_token()
        if not token:
            return {'success': False, 'message': 'Failed to get token'}
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_short_code}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.business_short_code,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': f"Payment for {account_reference}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if result.get('ResponseCode') == '0':
            return {
                'success': True,
                'checkout_request_id': result.get('CheckoutRequestID')
            }
        return {'success': False, 'message': result.get('ResponseDescription', 'STK push failed')}