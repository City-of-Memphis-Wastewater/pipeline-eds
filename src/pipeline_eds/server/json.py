# pipeline_eds/server/json.py
import msgspec
from starlette.responses import Response

def msgspec_json(data, status=200):
    return Response(
        content=msgspec.json.encode(data),
        media_type="application/json",
        status_code=status,
    )
