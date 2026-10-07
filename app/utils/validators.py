from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def format_validation_errors(exc: RequestValidationError) -> list[dict]:
    errors = []
    for err in exc.errors():
        if err["type"] == "json_invalid":
            errors.append({"field": "body", "message": "Request body is not valid JSON"})
            continue
        loc = [str(p) for p in err["loc"] if p != "body"]
        errors.append({"field": ".".join(loc) or "body", "message": err["msg"]})
    return errors


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": format_validation_errors(exc)},
    )