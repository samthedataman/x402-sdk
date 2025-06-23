"""FastAPI middleware for x402 payments"""

from typing import Dict, Union, Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json

from .provider import X402Provider
from .models import X402Config, PaymentData, RouteConfig
from .exceptions import X402Error, PaymentRequiredError


class X402Middleware(BaseHTTPMiddleware):
    """Middleware for automatic x402 payment handling"""
    
    def __init__(
        self,
        app,
        provider: X402Provider,
        routes: Dict[str, Union[str, RouteConfig]],
        on_payment: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        super().__init__(app)
        self.provider = provider
        self.routes = self._normalize_routes(routes)
        self.on_payment = on_payment
        self.on_error = on_error
    
    def _normalize_routes(self, routes: Dict[str, Union[str, RouteConfig]]) -> Dict[str, RouteConfig]:
        """Normalize route configurations"""
        normalized = {}
        for path, config in routes.items():
            if isinstance(config, str):
                # Simple string amount
                normalized[path] = RouteConfig(amount=config)
            elif isinstance(config, dict):
                # Dict configuration
                normalized[path] = RouteConfig(**config)
            else:
                normalized[path] = config
        return normalized
    
    async def dispatch(self, request: Request, call_next):
        """Process requests and handle x402 payments"""
        
        # Check if this route requires payment
        path = request.url.path
        route_config = self._match_route(path)
        
        if not route_config:
            # No payment required for this route
            return await call_next(request)
        
        # Check for payment header
        payment_header = request.headers.get("X-Payment")
        
        if not payment_header:
            # No payment provided, return 402
            return await self._payment_required_response(route_config, path)
        
        try:
            # Parse payment data
            payment_data = PaymentData.model_validate_json(payment_header)
            
            # Create requirement based on route config
            requirement = self.provider.create_payment_requirement(
                amount=route_config.amount,
                endpoint=path,
                token=route_config.token,
                scheme=route_config.scheme,
            )
            
            # Verify payment
            verification = await self.provider.verify_payment(
                payment_data,
                requirement,
                endpoint=path,
            )
            
            if not verification.valid:
                raise PaymentRequiredError("Invalid payment")
            
            # Call custom handler if provided
            if self.on_payment:
                await self._call_handler(self.on_payment, payment_data)
            
            # Add payment info to request state
            request.state.x402_payment = payment_data
            request.state.x402_verification = verification
            
            # Process the request
            response = await call_next(request)
            
            # Add payment confirmation header
            response.headers["X-Payment-Confirmation"] = verification.transaction_hash
            
            return response
            
        except X402Error as e:
            if self.on_error:
                await self._call_handler(self.on_error, e)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "code": e.code,
                },
            )
        except Exception as e:
            if self.on_error:
                await self._call_handler(self.on_error, e)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                },
            )
    
    def _match_route(self, path: str) -> Optional[RouteConfig]:
        """Match request path to route configuration"""
        # Exact match
        if path in self.routes:
            return self.routes[path]
        
        # Prefix match (e.g., /api/* matches /api/users)
        for route_path, config in self.routes.items():
            if route_path.endswith("*") and path.startswith(route_path[:-1]):
                return config
        
        return None
    
    async def _payment_required_response(self, route_config: RouteConfig, path: str) -> Response:
        """Create 402 Payment Required response"""
        requirement = self.provider.create_payment_requirement(
            amount=route_config.amount,
            endpoint=path,
            token=route_config.token,
            scheme=route_config.scheme,
        )
        
        return JSONResponse(
            status_code=402,
            content=requirement.model_dump(),
            headers={
                "X-Payment-Required": "true",
                "Cache-Control": "no-cache",
            },
        )
    
    async def _call_handler(self, handler: Callable, *args):
        """Call handler function (async or sync)"""
        import asyncio
        if asyncio.iscoroutinefunction(handler):
            await handler(*args)
        else:
            handler(*args)


def x402_middleware(
    wallet_address: str,
    routes: Dict[str, Union[str, RouteConfig]],
    **kwargs,
) -> Callable:
    """Factory function to create x402 middleware"""
    
    def middleware_wrapper(app):
        config = X402Config(wallet_address=wallet_address, **kwargs)
        provider = X402Provider(config)
        
        return X402Middleware(
            app,
            provider=provider,
            routes=routes,
            on_payment=kwargs.get("on_payment"),
            on_error=kwargs.get("on_error"),
        )
    
    return middleware_wrapper