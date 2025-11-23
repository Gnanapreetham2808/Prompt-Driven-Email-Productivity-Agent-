import os
import base64
import json
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import email as email_lib
from email.parser import BytesParser
from email import policy

# Gmail OAuth2 configuration
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

class GmailSync:
    def __init__(self):
        self.client_id = os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GMAIL_REDIRECT_URIS", "http://localhost:8000/auth/gmail/callback").split(',')[0]
        
    def create_oauth_flow(self):
        """Create OAuth2 flow for Gmail authentication"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )
        return flow
    
    def get_authorization_url(self, state: str = None) -> tuple[str, str]:
        """Generate OAuth2 authorization URL"""
        flow = self.create_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        return authorization_url, state
    
    def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        flow = self.create_oauth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
    
    def build_service(self, token_data: Dict[str, Any]):
        """Build Gmail API service from stored token"""
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes")
        )
        
        service = build('gmail', 'v1', credentials=credentials)
        return service
    
    def parse_email_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """Extract key headers from email"""
        header_dict = {}
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            if name in ['from', 'to', 'subject', 'date']:
                header_dict[name] = value
        return header_dict
    
    def decode_body(self, part: Dict) -> str:
        """Decode email body from base64"""
        if 'data' in part.get('body', {}):
            data = part['body']['data']
            # URL-safe base64 decode
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            return decoded
        return ""
    
    def extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        # If single part
        if 'body' in payload and 'data' in payload['body']:
            body = self.decode_body(payload)
        
        # If multipart
        elif 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                
                # Prefer text/plain
                if mime_type == 'text/plain':
                    body = self.decode_body(part)
                    break
                # Fallback to text/html
                elif mime_type == 'text/html' and not body:
                    body = self.decode_body(part)
                # Recursive for nested parts
                elif mime_type.startswith('multipart/'):
                    body = self.extract_body(part)
                    if body:
                        break
        
        return body.strip()
    
    def extract_attachments(self, payload: Dict) -> List[Dict[str, str]]:
        """Extract attachment metadata from email"""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                filename = part.get('filename', '')
                if filename:
                    attachment = {
                        "name": filename,
                        "mimeType": part.get('mimeType', ''),
                        "size": str(part.get('body', {}).get('size', 0))
                    }
                    attachments.append(attachment)
                
                # Recursive for nested parts
                if 'parts' in part:
                    attachments.extend(self.extract_attachments(part))
        
        return attachments
    
    def fetch_emails(self, token_data: Dict[str, Any], max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail"""
        try:
            service = self.build_service(token_data)
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg_ref in messages:
                msg_id = msg_ref['id']
                
                # Get full message
                message = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Parse headers
                headers = self.parse_email_headers(message['payload']['headers'])
                
                # Extract body
                body = self.extract_body(message['payload'])
                
                # Extract attachments
                attachments = self.extract_attachments(message['payload'])
                
                # Parse timestamp
                internal_date = message.get('internalDate', '0')
                timestamp_ms = int(internal_date)
                
                email_data = {
                    "gmail_id": msg_id,
                    "sender": headers.get('from', ''),
                    "subject": headers.get('subject', ''),
                    "body": body,
                    "timestamp": timestamp_ms / 1000,  # Convert to seconds
                    "attachments": attachments,
                    "labels": message.get('labelIds', [])
                }
                
                emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            raise
        except Exception as e:
            print(f"Error fetching emails: {e}")
            raise
    
    def get_user_email(self, token_data: Dict[str, Any]) -> str:
        """Get the authenticated user's email address"""
        try:
            service = self.build_service(token_data)
            profile = service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', '')
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return ""
