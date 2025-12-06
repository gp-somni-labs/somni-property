"""
WebSocket Authentication
Generates temporary session tokens for WebSocket connections
"""

import secrets
import time
import json
from typing import Optional, Dict
from dataclasses import dataclass, asdict
import logging
import redis
from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebSocketSession:
    """WebSocket session token"""
    token: str
    user_id: str
    username: str
    email: Optional[str]
    groups: list[str]
    created_at: float
    expires_at: float

    def is_expired(self) -> bool:
        """Check if session token has expired"""
        return time.time() > self.expires_at

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return "admins" in self.groups or "admin" in self.groups

    def is_manager(self) -> bool:
        """Check if user is manager"""
        return self.is_admin() or "managers" in self.groups or "manager" in self.groups


class WebSocketAuthManager:
    """
    Manages WebSocket session tokens

    Generates short-lived tokens that can be used for WebSocket authentication
    after user is authenticated via Authelia SSO.

    Workflow:
    1. User authenticates via Authelia (gets X-Forwarded-User header)
    2. Frontend calls /api/v1/ws/token to get WebSocket token
    3. Frontend connects to /ws?token={token}
    4. Backend validates token and establishes WebSocket connection
    """

    def __init__(self, token_lifetime: int = 300):
        """
        Initialize auth manager

        Args:
            token_lifetime: Token lifetime in seconds (default: 300 = 5 minutes)
        """
        self.token_lifetime = token_lifetime

        # Connect to Redis for shared token storage across pods
        try:
            redis_host = getattr(settings, 'REDIS_HOST', 'redis.core.svc.cluster.local')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.use_redis = True
            logger.info(f"WebSocket auth using Redis at {redis_host}:{redis_port} (token lifetime: {token_lifetime}s)")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory storage (multi-pod auth will fail!)")
            self.redis_client = None
            self.use_redis = False
            self.sessions: Dict[str, WebSocketSession] = {}
            logger.info(f"WebSocket auth using in-memory storage (token lifetime: {token_lifetime}s)")

    def create_token(
        self,
        username: str,
        email: Optional[str] = None,
        groups: Optional[list[str]] = None
    ) -> str:
        """
        Create WebSocket session token for authenticated user

        Args:
            username: Username from X-Forwarded-User
            email: Email from X-Forwarded-Email (optional)
            groups: Groups from X-Forwarded-Groups (optional)

        Returns:
            Session token string
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)

        # Create session
        now = time.time()
        session = WebSocketSession(
            token=token,
            user_id=username,  # Use username as user_id
            username=username,
            email=email,
            groups=groups or [],
            created_at=now,
            expires_at=now + self.token_lifetime
        )

        # Store session in Redis or in-memory
        if self.use_redis:
            try:
                # Store as JSON in Redis with TTL
                session_data = asdict(session)
                self.redis_client.setex(
                    f"ws_token:{token}",
                    self.token_lifetime,
                    json.dumps(session_data)
                )
                logger.info(f"Created WebSocket token for user {username} in Redis (expires in {self.token_lifetime}s)")
            except Exception as e:
                logger.error(f"Failed to store token in Redis: {e}. Token will not work!")
                raise
        else:
            # Fallback to in-memory
            self.sessions[token] = session
            logger.info(f"Created WebSocket token for user {username} in memory (expires in {self.token_lifetime}s)")

        return token

    def validate_token(self, token: Optional[str]) -> Optional[WebSocketSession]:
        """
        Validate WebSocket session token

        Args:
            token: Session token to validate

        Returns:
            WebSocketSession if valid, None otherwise
        """
        if not token:
            logger.debug("WebSocket auth failed: No token provided")
            return None

        # Get session from Redis or in-memory
        session = None

        if self.use_redis:
            try:
                session_data = self.redis_client.get(f"ws_token:{token}")
                if session_data:
                    # Deserialize from JSON
                    data = json.loads(session_data)
                    session = WebSocketSession(**data)
                else:
                    logger.debug(f"WebSocket auth failed: Token not found in Redis")
                    return None
            except Exception as e:
                logger.error(f"Failed to validate token from Redis: {e}")
                return None
        else:
            # Fallback to in-memory
            session = self.sessions.get(token)

        if not session:
            logger.debug(f"WebSocket auth failed: Invalid token")
            return None

        # Check expiration (Redis TTL handles this, but double-check)
        if session.is_expired():
            logger.info(f"WebSocket auth failed: Token expired for user {session.username}")
            # Clean up expired token
            if self.use_redis:
                try:
                    self.redis_client.delete(f"ws_token:{token}")
                except:
                    pass
            else:
                del self.sessions[token]
            return None

        logger.debug(f"WebSocket auth successful for user {session.username}")
        return session

    def revoke_token(self, token: str) -> bool:
        """
        Revoke WebSocket session token

        Args:
            token: Token to revoke

        Returns:
            True if token was revoked, False if not found
        """
        if self.use_redis:
            try:
                result = self.redis_client.delete(f"ws_token:{token}")
                if result > 0:
                    logger.info(f"Revoked WebSocket token from Redis")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to revoke token from Redis: {e}")
                return False
        else:
            if token in self.sessions:
                username = self.sessions[token].username
                del self.sessions[token]
                logger.info(f"Revoked WebSocket token for user {username}")
                return True
            return False

    def revoke_user_tokens(self, username: str) -> int:
        """
        Revoke all WebSocket tokens for a user

        Args:
            username: Username to revoke tokens for

        Returns:
            Number of tokens revoked

        Note: For Redis storage, this scans all ws_token keys (expensive).
        Consider token expiration (5 min) as alternative.
        """
        if self.use_redis:
            try:
                # Scan for all WebSocket tokens
                count = 0
                for key in self.redis_client.scan_iter(match="ws_token:*"):
                    try:
                        session_data = self.redis_client.get(key)
                        if session_data:
                            data = json.loads(session_data)
                            if data.get('username') == username:
                                self.redis_client.delete(key)
                                count += 1
                    except:
                        pass

                if count > 0:
                    logger.info(f"Revoked {count} WebSocket tokens for user {username} from Redis")
                return count
            except Exception as e:
                logger.error(f"Failed to revoke user tokens from Redis: {e}")
                return 0
        else:
            tokens_to_revoke = [
                token for token, session in self.sessions.items()
                if session.username == username
            ]

            for token in tokens_to_revoke:
                del self.sessions[token]

            if tokens_to_revoke:
                logger.info(f"Revoked {len(tokens_to_revoke)} WebSocket tokens for user {username}")

            return len(tokens_to_revoke)

    def cleanup_expired(self) -> int:
        """
        Remove expired tokens from memory

        Returns:
            Number of tokens cleaned up
        """
        now = time.time()
        expired_tokens = [
            token for token, session in self.sessions.items()
            if session.expires_at < now
        ]

        for token in expired_tokens:
            del self.sessions[token]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired WebSocket tokens")

        return len(expired_tokens)

    def get_stats(self) -> dict:
        """
        Get statistics about active sessions

        Returns:
            Dictionary with session statistics
        """
        now = time.time()
        active_sessions = [s for s in self.sessions.values() if not s.is_expired()]

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(self.sessions) - len(active_sessions),
            "unique_users": len(set(s.username for s in active_sessions)),
            "token_lifetime": self.token_lifetime
        }


# Global WebSocket auth manager instance
ws_auth_manager = WebSocketAuthManager(token_lifetime=300)  # 5 minute tokens


def get_ws_auth_manager() -> WebSocketAuthManager:
    """Dependency to get WebSocket auth manager"""
    return ws_auth_manager
