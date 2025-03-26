from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
from ..config import settings

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

class GoogleDriveService:
    def __init__(self, credentials_dict: Dict[str, Any]):
        """Initialize the Google Drive service with credentials."""
        try:
            credentials = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri'),
                client_id=credentials_dict.get('client_id'),
                client_secret=credentials_dict.get('client_secret'),
                scopes=credentials_dict.get('scopes')
            )
            self.service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Google Drive service: {str(e)}")
            self.service = None

    @staticmethod
    def get_oauth_flow():
        client_config = {
            "installed": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8002/api/v1/auth/google/callback"],
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri="http://localhost:8002/api/v1/auth/google/callback"
        )
        return flow

    def list_files(self, mime_types: List[str] = None) -> List[Dict[str, Any]]:
        """List files from Google Drive with optional MIME type filtering."""
        if not self.service:
            raise ValueError("Service not initialized. Please authenticate first.")

        try:
            # Prepare the query for MIME types
            query_parts = ["trashed = false"]  # Only include non-trashed files
            if mime_types:
                mime_conditions = [f"mimeType='{mime}'" for mime in mime_types]
                query_parts.append(f"({' or '.join(mime_conditions)})")
            
            query = " and ".join(query_parts)
            
            # List files in Google Drive
            results = []
            page_token = None
            
            while True:
                # Prepare the query parameters
                params = {
                    'q': query,
                    'spaces': 'drive',
                    'fields': 'nextPageToken, files(id, name, mimeType, createdTime, modifiedTime)',
                    'pageToken': page_token
                }
                
                # Execute the query
                response = self.service.files().list(**params).execute()
                results.extend(response.get('files', []))
                
                # Get the next page token
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results

        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []

    def download_file(self, file_id: str) -> Tuple[str, Dict[str, Any]]:
        """Download a file's content from Google Drive."""
        if not self.service:
            raise ValueError("Service not initialized. Please authenticate first.")

        try:
            # Get file metadata
            print(f"Getting metadata for file {file_id}...")
            file = self.service.files().get(fileId=file_id, fields='id, name, mimeType').execute()
            mime_type = file.get('mimeType', '')
            print(f"File mime type: {mime_type}")

            # Handle Google Docs files
            if mime_type == 'application/vnd.google-apps.document':
                print("Detected Google Doc, exporting as plain text...")
                try:
                    response = self.service.files().export(
                        fileId=file_id,
                        mimeType='text/plain'
                    ).execute()
                    print("Successfully exported Google Doc")
                    content = response.decode('utf-8') if isinstance(response, bytes) else response
                    return content, file
                except Exception as e:
                    print(f"Error exporting Google Doc: {str(e)}")
                    return None, None

            # Handle regular files
            print("Downloading regular file...")
            try:
                request = self.service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                
                while not done:
                    status, done = downloader.next_chunk()
                    print(f"Download progress: {int(status.progress() * 100)}%")
                
                content = file_content.getvalue()
                if isinstance(content, bytes) and mime_type.startswith('text/'):
                    content = content.decode('utf-8')
                print("File download completed")
                return content, file
            except Exception as e:
                print(f"Error downloading file: {str(e)}")
                return None, None

        except Exception as e:
            print(f"An error occurred during file download: {str(e)}")
            return None, None

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata from Google Drive."""
        if not self.service:
            raise ValueError("Service not initialized. Please authenticate first.")

        try:
            return self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, modifiedTime, createdTime, owners'
            ).execute()
        except Exception as e:
            print(f"An error occurred: {e}")
            return None 