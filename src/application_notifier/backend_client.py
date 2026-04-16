from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from .models import BackendConfig, DueItem, Location, Subject


@dataclass(slots=True)
class BackendClient:
    config: BackendConfig
    timeout_seconds: int = 30

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> Any:
        base_url = self.config.base_url.rstrip("/") + "/"
        url = urljoin(base_url, path.lstrip("/"))
        if params:
            query = urlencode([(key, str(value)) for key, value in params.items() if value is not None])
            url = f"{url}?{query}"
        request = Request(url, method=method.upper())
        request.add_header("X-API-Key", self.config.api_key)
        request.add_header("Accept", "application/json")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"backend request failed with HTTP {exc.code} for {path}: {raw}") from exc
        except URLError as exc:
            raise RuntimeError(f"backend request failed for {path}: {exc.reason}") from exc

    def list_due_items(self) -> list[DueItem]:
        payload = self._request("GET", "/episodes/due")
        items = payload.get("due", [])
        return [DueItem(**item) for item in items]

    def list_subjects(self) -> list[Subject]:
        payload = self._request("GET", "/subjects")
        items = payload.get("subjects", [])
        return [Subject(id=item["id"], display_name=item["display_name"]) for item in items]

    def list_locations(self) -> list[Location]:
        payload = self._request("GET", "/locations")
        items = payload.get("locations", [])
        return [
            Location(id=item["id"], code=item["code"], display_name=item["display_name"])
            for item in items
        ]

