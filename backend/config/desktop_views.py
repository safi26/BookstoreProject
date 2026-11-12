import os
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    return HttpResponse(
        os.environ.get("BOOKSTORE_HEALTH_TOKEN", "ok"),
        content_type="text/plain",
    )


@require_GET
def frontend(request, path=""):
    from django.conf import settings

    if path.startswith(("api/", "admin/", "healthz/", "static/")):
        raise Http404

    frontend_root = settings.FRONTEND_DIR.resolve()
    requested_file = (frontend_root / path).resolve()
    try:
        requested_file.relative_to(frontend_root)
    except ValueError as exc:
        raise Http404 from exc

    if requested_file.is_file():
        return FileResponse(requested_file.open("rb"))

    if path and Path(path).suffix:
        raise Http404

    index_file = frontend_root / "index.html"
    if not index_file.is_file():
        raise Http404("The packaged frontend build is missing.")
    response = FileResponse(index_file.open("rb"))
    response["Cache-Control"] = "no-cache"
    return response
