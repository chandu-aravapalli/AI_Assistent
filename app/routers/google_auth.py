from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import requests
from .. import models
from ..database import get_db
from ..services.google_drive import GoogleDriveService
from ..tasks.document_sync import sync_user_documents
from ..config import settings
from ..crud import get_user_by_email, create_user, update_user_credentials
import secrets
import httpx

router = APIRouter(prefix="/auth/google", tags=["google"])

@router.get("/login")
async def google_login():
    """Start the Google OAuth flow."""
    try:
        flow = GoogleDriveService.get_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=secrets.token_urlsafe(16)
        )
        return RedirectResponse(authorization_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to initialize Google OAuth flow: {str(e)}"
        )

@router.get("/files")
async def list_files(
    mime_types: str = Query(None),
    db: Session = Depends(get_db)
):
    """List files from Google Drive with optional MIME type filter."""
    try:
        # Get the latest user with Google credentials
        user = db.query(models.User).filter(models.User.google_credentials.isnot(None)).order_by(models.User.id.desc()).first()
        if not user or not user.google_credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authenticated Google user found"
            )

        # Initialize Google Drive service
        drive_service = GoogleDriveService(user.google_credentials)

        # Parse MIME types if provided
        mime_type_list = mime_types.split(',') if mime_types else None

        # List files
        files = drive_service.list_files(mime_type_list)
        return {"files": files}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list files: {str(e)}"
        )

@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    try:
        flow = GoogleDriveService.get_oauth_flow()
        flow.fetch_token(
            authorization_response=str(request.url),
            code=code
        )

        # Print the tokens for testing purposes
        print("\n=== Google OAuth Tokens ===")
        print(f"Access Token: {flow.credentials.token}")
        print(f"Refresh Token: {flow.credentials.refresh_token}")
        print("=========================\n")

        credentials = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }

        # Get user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {'Authorization': f'Bearer {credentials["token"]}'}
        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info from Google")
            userinfo = response.json()
            email = userinfo.get('email')

        if not email:
            raise HTTPException(status_code=400, detail="Failed to get email from Google")

        # Create or update user
        user = get_user_by_email(db, email=email)
        if not user:
            user = create_user(db, email=email)

        # Store Google credentials
        update_user_credentials(db, user.id, credentials)

        # Start document sync
        sync_user_documents.delay(user.id)

        return RedirectResponse(url="/docs")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to authenticate with Google: {str(e)}") 