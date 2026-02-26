"""
Custom middleware for FastAPI.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.datastructures import Address
from starlette.responses import Response

__all__ = ["CloudflareIPMiddleware"]


class CloudflareIPMiddleware(BaseHTTPMiddleware):
    """Middleware to extract the client's real IP address from Cloudflare headers and
    attach it to the request state."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Cloudflare header
        cf_ip = request.headers.get("CF-Connecting-IP")

        if cf_ip:
            # Override the client address
            request.scope["client"] = Address(
                host=cf_ip,
                port=request.client.port if request.client else 0
            )
            request.state.client_ip = cf_ip
        else:
            # Fallback to the original client IP
            request.state.client_ip = (
                request.client.host if request.client else None
            )

        response = await call_next(request)
        return response
