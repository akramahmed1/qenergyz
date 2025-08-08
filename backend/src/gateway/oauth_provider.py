"""
OAuth/SSO Provider Integration

Supports multiple OAuth providers:
- Google OAuth 2.0
- Microsoft Azure AD / Office 365
- GitHub OAuth
- Custom OIDC providers
"""

import asyncio
import secrets
import base64
import hashlib
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog
import httpx
import jwt
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class OAuthProvider(str, Enum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github" 
    LINKEDIN = "linkedin"
    OKTA = "okta"
    AUTH0 = "auth0"
    CUSTOM = "custom"


class TokenType(str, Enum):
    """OAuth token types"""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    ID_TOKEN = "id_token"


class OAuthConfig(BaseModel):
    """OAuth provider configuration"""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: HttpUrl
    
    # Provider URLs
    auth_url: HttpUrl
    token_url: HttpUrl
    userinfo_url: Optional[HttpUrl] = None
    jwks_url: Optional[HttpUrl] = None
    
    # Scopes and configuration
    scopes: List[str] = Field(default_factory=list)
    state_required: bool = True
    pkce_required: bool = True
    
    # Advanced settings
    token_endpoint_auth_method: str = "client_secret_post"
    response_type: str = "code"
    grant_type: str = "authorization_code"


class OAuthToken(BaseModel):
    """OAuth token information"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    
    # Metadata
    provider: OAuthProvider
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.expires_in and not self.expires_at:
            self.expires_at = self.created_at + timedelta(seconds=self.expires_in)


class OAuthUserInfo(BaseModel):
    """Standardized user information from OAuth providers"""
    id: str  # Provider user ID
    email: EmailStr
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    picture: Optional[HttpUrl] = None
    locale: Optional[str] = None
    
    # Provider-specific data
    provider: OAuthProvider
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class OAuthState(BaseModel):
    """OAuth state for CSRF protection"""
    state: str
    code_verifier: Optional[str] = None  # For PKCE
    redirect_uri: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=10))


class OAuthError(Exception):
    """OAuth-related errors"""
    
    def __init__(self, error: str, description: Optional[str] = None, provider: Optional[str] = None):
        self.error = error
        self.description = description
        self.provider = provider
        message = f"OAuth error: {error}"
        if description:
            message += f" - {description}"
        if provider:
            message += f" (Provider: {provider})"
        super().__init__(message)


class OAuthProviderHandler:
    """
    OAuth Provider Integration Handler
    
    Provides unified OAuth 2.0 / OpenID Connect integration with
    multiple providers and security best practices.
    """
    
    def __init__(self):
        self.providers: Dict[OAuthProvider, OAuthConfig] = {}
        self.states: Dict[str, OAuthState] = {}  # In production, use Redis
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Load provider configurations
        self._load_provider_configs()
    
    def _load_provider_configs(self):
        """Load OAuth provider configurations from settings"""
        
        # Google OAuth 2.0
        if settings.google_oauth_client_id:
            self.providers[OAuthProvider.GOOGLE] = OAuthConfig(
                provider=OAuthProvider.GOOGLE,
                client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret,
                redirect_uri=f"{settings.base_url}/auth/oauth/google/callback",
                auth_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
                jwks_url="https://www.googleapis.com/oauth2/v3/certs",
                scopes=["openid", "email", "profile"]
            )
        
        # Microsoft Azure AD
        if settings.microsoft_oauth_client_id:
            tenant = settings.microsoft_oauth_tenant or "common"
            self.providers[OAuthProvider.MICROSOFT] = OAuthConfig(
                provider=OAuthProvider.MICROSOFT,
                client_id=settings.microsoft_oauth_client_id,
                client_secret=settings.microsoft_oauth_client_secret,
                redirect_uri=f"{settings.base_url}/auth/oauth/microsoft/callback",
                auth_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
                token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                userinfo_url="https://graph.microsoft.com/v1.0/me",
                jwks_url=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
                scopes=["openid", "email", "profile", "User.Read"]
            )
        
        # GitHub OAuth
        if settings.github_oauth_client_id:
            self.providers[OAuthProvider.GITHUB] = OAuthConfig(
                provider=OAuthProvider.GITHUB,
                client_id=settings.github_oauth_client_id,
                client_secret=settings.github_oauth_client_secret,
                redirect_uri=f"{settings.base_url}/auth/oauth/github/callback",
                auth_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["user:email"],
                pkce_required=False  # GitHub doesn't support PKCE
            )
        
        # LinkedIn OAuth
        if settings.linkedin_oauth_client_id:
            self.providers[OAuthProvider.LINKEDIN] = OAuthConfig(
                provider=OAuthProvider.LINKEDIN,
                client_id=settings.linkedin_oauth_client_id,
                client_secret=settings.linkedin_oauth_client_secret,
                redirect_uri=f"{settings.base_url}/auth/oauth/linkedin/callback",
                auth_url="https://www.linkedin.com/oauth/v2/authorization",
                token_url="https://www.linkedin.com/oauth/v2/accessToken",
                userinfo_url="https://api.linkedin.com/v2/people/~",
                scopes=["r_liteprofile", "r_emailaddress"]
            )
    
    def get_authorization_url(
        self, 
        provider: OAuthProvider, 
        redirect_uri: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate OAuth authorization URL
        
        Args:
            provider: OAuth provider
            redirect_uri: Optional custom redirect URI
            
        Returns:
            Dictionary with authorization URL and state
        """
        if provider not in self.providers:
            raise OAuthError("unsupported_provider", f"Provider {provider} not configured")
        
        config = self.providers[provider]
        state = secrets.token_urlsafe(32)
        
        # Generate PKCE parameters if required
        code_verifier = None
        code_challenge = None
        if config.pkce_required:
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('utf-8')).digest()
            ).decode('utf-8').rstrip('=')
        
        # Store state for validation
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri or str(config.redirect_uri)
        )
        self.states[state] = oauth_state
        
        # Build authorization URL
        params = {
            "response_type": config.response_type,
            "client_id": config.client_id,
            "redirect_uri": redirect_uri or str(config.redirect_uri),
            "scope": " ".join(config.scopes),
            "state": state
        }
        
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        
        # Provider-specific parameters
        if provider == OAuthProvider.GOOGLE:
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        elif provider == OAuthProvider.MICROSOFT:
            params["response_mode"] = "query"
        
        auth_url = f"{config.auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        logger.info("Generated OAuth authorization URL", 
                   provider=provider, state=state)
        
        return {
            "authorization_url": auth_url,
            "state": state
        }
    
    async def handle_callback(
        self, 
        provider: OAuthProvider, 
        code: str, 
        state: str
    ) -> OAuthToken:
        """
        Handle OAuth callback and exchange code for token
        
        Args:
            provider: OAuth provider
            code: Authorization code
            state: CSRF state parameter
            
        Returns:
            OAuth token information
        """
        if provider not in self.providers:
            raise OAuthError("unsupported_provider", f"Provider {provider} not configured")
        
        # Validate state
        if state not in self.states:
            raise OAuthError("invalid_state", "State parameter is invalid or expired")
        
        oauth_state = self.states[state]
        if oauth_state.expires_at < datetime.utcnow():
            del self.states[state]
            raise OAuthError("expired_state", "State parameter has expired")
        
        config = self.providers[provider]
        
        # Prepare token request
        token_data = {
            "grant_type": config.grant_type,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": oauth_state.redirect_uri
        }
        
        # Add PKCE verifier if used
        if oauth_state.code_verifier:
            token_data["code_verifier"] = oauth_state.code_verifier
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # GitHub expects different headers
        if provider == OAuthProvider.GITHUB:
            headers["Accept"] = "application/vnd.github+json"
        
        try:
            response = await self.http_client.post(
                str(config.token_url),
                data=token_data,
                headers=headers
            )
            
            response.raise_for_status()
            token_response = response.json()
            
            # Handle error in token response
            if "error" in token_response:
                raise OAuthError(
                    token_response["error"],
                    token_response.get("error_description"),
                    provider.value
                )
            
            # Create OAuth token
            oauth_token = OAuthToken(
                access_token=token_response["access_token"],
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                refresh_token=token_response.get("refresh_token"),
                scope=token_response.get("scope"),
                id_token=token_response.get("id_token"),
                provider=provider
            )
            
            # Clean up state
            del self.states[state]
            
            logger.info("Successfully exchanged OAuth code for token", 
                       provider=provider, expires_in=oauth_token.expires_in)
            
            return oauth_token
            
        except httpx.HTTPStatusError as e:
            logger.error("OAuth token exchange failed", 
                        provider=provider, status_code=e.response.status_code,
                        response_text=e.response.text)
            raise OAuthError("token_exchange_failed", str(e), provider.value)
        except Exception as e:
            logger.error("OAuth token exchange error", provider=provider, error=str(e))
            raise OAuthError("token_exchange_error", str(e), provider.value)
    
    async def get_user_info(
        self, 
        provider: OAuthProvider, 
        oauth_token: OAuthToken
    ) -> OAuthUserInfo:
        """
        Get user information from OAuth provider
        
        Args:
            provider: OAuth provider
            oauth_token: OAuth token
            
        Returns:
            Standardized user information
        """
        if provider not in self.providers:
            raise OAuthError("unsupported_provider", f"Provider {provider} not configured")
        
        config = self.providers[provider]
        
        if not config.userinfo_url:
            raise OAuthError("no_userinfo_endpoint", f"Provider {provider} has no userinfo endpoint")
        
        headers = {
            "Authorization": f"Bearer {oauth_token.access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = await self.http_client.get(
                str(config.userinfo_url),
                headers=headers
            )
            
            response.raise_for_status()
            user_data = response.json()
            
            # Handle GitHub email separately (it might not be in the profile)
            if provider == OAuthProvider.GITHUB and not user_data.get("email"):
                user_data = await self._get_github_email(oauth_token, user_data)
            
            # Standardize user information based on provider
            return self._normalize_user_info(provider, user_data)
            
        except httpx.HTTPStatusError as e:
            logger.error("OAuth userinfo request failed",
                        provider=provider, status_code=e.response.status_code)
            raise OAuthError("userinfo_request_failed", str(e), provider.value)
        except Exception as e:
            logger.error("OAuth userinfo error", provider=provider, error=str(e))
            raise OAuthError("userinfo_error", str(e), provider.value)
    
    async def _get_github_email(self, oauth_token: OAuthToken, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get GitHub user email from emails endpoint"""
        try:
            response = await self.http_client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {oauth_token.access_token}",
                    "Accept": "application/vnd.github+json"
                }
            )
            
            response.raise_for_status()
            emails = response.json()
            
            # Find primary email
            primary_email = None
            for email_info in emails:
                if email_info.get("primary"):
                    primary_email = email_info["email"]
                    break
            
            if primary_email:
                user_data["email"] = primary_email
            
            return user_data
            
        except Exception as e:
            logger.warning("Failed to get GitHub user email", error=str(e))
            return user_data
    
    def _normalize_user_info(self, provider: OAuthProvider, user_data: Dict[str, Any]) -> OAuthUserInfo:
        """Normalize user info from different providers to standard format"""
        
        if provider == OAuthProvider.GOOGLE:
            return OAuthUserInfo(
                id=user_data["id"],
                email=user_data["email"],
                name=user_data["name"],
                first_name=user_data.get("given_name"),
                last_name=user_data.get("family_name"),
                picture=user_data.get("picture"),
                locale=user_data.get("locale"),
                provider=provider,
                raw_data=user_data
            )
        
        elif provider == OAuthProvider.MICROSOFT:
            return OAuthUserInfo(
                id=user_data["id"],
                email=user_data["mail"] or user_data.get("userPrincipalName"),
                name=user_data["displayName"],
                first_name=user_data.get("givenName"),
                last_name=user_data.get("surname"),
                locale=user_data.get("preferredLanguage"),
                provider=provider,
                raw_data=user_data
            )
        
        elif provider == OAuthProvider.GITHUB:
            return OAuthUserInfo(
                id=str(user_data["id"]),
                email=user_data.get("email", ""),
                name=user_data["name"] or user_data["login"],
                picture=user_data.get("avatar_url"),
                locale=user_data.get("location"),
                provider=provider,
                raw_data=user_data
            )
        
        elif provider == OAuthProvider.LINKEDIN:
            return OAuthUserInfo(
                id=user_data["id"],
                email=user_data.get("emailAddress", ""),  # Requires separate API call
                name=f"{user_data.get('firstName', {}).get('localized', {}).get('en_US', '')} "
                     f"{user_data.get('lastName', {}).get('localized', {}).get('en_US', '')}".strip(),
                first_name=user_data.get("firstName", {}).get("localized", {}).get("en_US"),
                last_name=user_data.get("lastName", {}).get("localized", {}).get("en_US"),
                picture=user_data.get("profilePicture", {}).get("displayImage~", {}).get("elements", [{}])[0].get("identifiers", [{}])[0].get("identifier"),
                provider=provider,
                raw_data=user_data
            )
        
        else:
            # Generic handling
            return OAuthUserInfo(
                id=str(user_data.get("id", user_data.get("sub", ""))),
                email=user_data.get("email", ""),
                name=user_data.get("name", user_data.get("preferred_username", "")),
                first_name=user_data.get("given_name", user_data.get("first_name")),
                last_name=user_data.get("family_name", user_data.get("last_name")),
                picture=user_data.get("picture", user_data.get("avatar_url")),
                locale=user_data.get("locale"),
                provider=provider,
                raw_data=user_data
            )
    
    async def refresh_token(
        self, 
        provider: OAuthProvider, 
        refresh_token: str
    ) -> OAuthToken:
        """
        Refresh OAuth access token
        
        Args:
            provider: OAuth provider
            refresh_token: Refresh token
            
        Returns:
            New OAuth token
        """
        if provider not in self.providers:
            raise OAuthError("unsupported_provider", f"Provider {provider} not configured")
        
        config = self.providers[provider]
        
        token_data = {
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": refresh_token
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = await self.http_client.post(
                str(config.token_url),
                data=token_data,
                headers=headers
            )
            
            response.raise_for_status()
            token_response = response.json()
            
            if "error" in token_response:
                raise OAuthError(
                    token_response["error"],
                    token_response.get("error_description"),
                    provider.value
                )
            
            oauth_token = OAuthToken(
                access_token=token_response["access_token"],
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                refresh_token=token_response.get("refresh_token", refresh_token),
                scope=token_response.get("scope"),
                id_token=token_response.get("id_token"),
                provider=provider
            )
            
            logger.info("Successfully refreshed OAuth token", provider=provider)
            
            return oauth_token
            
        except httpx.HTTPStatusError as e:
            logger.error("OAuth token refresh failed",
                        provider=provider, status_code=e.response.status_code)
            raise OAuthError("token_refresh_failed", str(e), provider.value)
        except Exception as e:
            logger.error("OAuth token refresh error", provider=provider, error=str(e))
            raise OAuthError("token_refresh_error", str(e), provider.value)
    
    async def revoke_token(
        self, 
        provider: OAuthProvider, 
        token: str, 
        token_type: TokenType = TokenType.ACCESS_TOKEN
    ) -> bool:
        """
        Revoke OAuth token
        
        Args:
            provider: OAuth provider
            token: Token to revoke
            token_type: Type of token
            
        Returns:
            True if successful
        """
        if provider not in self.providers:
            raise OAuthError("unsupported_provider", f"Provider {provider} not configured")
        
        # Not all providers support token revocation
        revoke_urls = {
            OAuthProvider.GOOGLE: "https://oauth2.googleapis.com/revoke",
            OAuthProvider.MICROSOFT: None,  # Microsoft doesn't have a standard revoke endpoint
            OAuthProvider.GITHUB: None,     # GitHub doesn't support revocation
        }
        
        revoke_url = revoke_urls.get(provider)
        if not revoke_url:
            logger.warning("Token revocation not supported", provider=provider)
            return False
        
        try:
            response = await self.http_client.post(
                revoke_url,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            response.raise_for_status()
            
            logger.info("Successfully revoked OAuth token", provider=provider)
            return True
            
        except Exception as e:
            logger.error("OAuth token revocation failed", provider=provider, error=str(e))
            return False
    
    def get_supported_providers(self) -> List[OAuthProvider]:
        """Get list of configured OAuth providers"""
        return list(self.providers.keys())
    
    async def cleanup_expired_states(self):
        """Clean up expired OAuth states"""
        now = datetime.utcnow()
        expired_states = [
            state for state, oauth_state in self.states.items()
            if oauth_state.expires_at < now
        ]
        
        for state in expired_states:
            del self.states[state]
        
        if expired_states:
            logger.info("Cleaned up expired OAuth states", count=len(expired_states))
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()