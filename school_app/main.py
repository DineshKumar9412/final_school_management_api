# api/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqladmin import Admin
from database.session import engine
from api.users import router as user_router
from admin.user_admin import UserAdmin
from middleware.cors import setup_cors
from middleware.decryption import DecryptionMiddleware
from middleware.encryption import EncryptionMiddleware
from middleware.monitoring import MonitoringMiddleware, metrics_endpoint, loki_logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="FastAPI Production App")

# Middleware Setup
# 1️⃣ CORS
setup_cors(app)

# 2️⃣ Decrypt incoming requests (only selected paths)
app.add_middleware(DecryptionMiddleware)

# 3️⃣ Logging middleware for request/response metadata
app.add_middleware(MonitoringMiddleware)

# 4️⃣ Encrypt outgoing responses (only selected paths)
app.add_middleware(EncryptionMiddleware)

# 5️⃣ Catch all unhandled exceptions and log
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        loki_logger.error(
            "Unhandled exception occurred",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            }
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

# API Routes
app.include_router(user_router, prefix="/api/users")

# Admin Panel
admin = Admin(app, engine)
admin.add_view(UserAdmin)

@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_endpoint()  
