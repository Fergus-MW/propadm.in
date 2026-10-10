"""Write-only credential secrets, the domain lock and server-side TOTP.

Secret values ({password, totp_seed}) live in GCP Secret Manager in cloud mode and in a
0600 file beside the local data path otherwise -- never in the shared state JSON.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import struct
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from propadmin_core import ProviderNotConfigured

_lock = threading.Lock()


def _secret_id(credential_id):
    return "propadmin-credential-" + re.sub(r"[^A-Za-z0-9_-]", "-", credential_id)


def _local(settings):
    # A gs:// data path has no local directory to sit beside; use Secret Manager.
    return settings.mode != "cloud" and not settings.data_path.startswith("gs://")


def _local_path(settings):
    return Path(settings.data_path).with_name("credentials.secret.json")


def _local_read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def _local_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _secret_manager():
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
    if not project:
        raise ProviderNotConfigured("Secret Manager requires GOOGLE_CLOUD_PROJECT")
    try:
        from google.cloud import secretmanager
    except ImportError as exc:
        raise ProviderNotConfigured("Install the cloud extra for Secret Manager") from exc
    return secretmanager.SecretManagerServiceClient(), project


def put_secret(settings, credential_id, value):
    """Create or rotate. `value` is {password, totp_seed}; never log it."""
    if _local(settings):
        # ponytail: process lock only; the API is the sole writer of this file.
        with _lock:
            path = _local_path(settings)
            data = _local_read(path)
            data[credential_id] = value
            _local_write(path, data)
        return
    client, project = _secret_manager()
    from google.api_core.exceptions import AlreadyExists

    name = f"projects/{project}/secrets/{_secret_id(credential_id)}"
    try:
        client.create_secret(
            request={
                "parent": f"projects/{project}",
                "secret_id": _secret_id(credential_id),
                "secret": {"replication": {"automatic": {}}},
            }
        )
    except AlreadyExists:
        pass
    client.add_secret_version(
        request={"parent": name, "payload": {"data": json.dumps(value).encode()}}
    )


def get_secret(settings, credential_id):
    if _local(settings):
        return _local_read(_local_path(settings))[credential_id]
    client, project = _secret_manager()
    name = f"projects/{project}/secrets/{_secret_id(credential_id)}/versions/latest"
    return json.loads(client.access_secret_version(request={"name": name}).payload.data)


def delete_secret(settings, credential_id):
    if _local(settings):
        with _lock:
            path = _local_path(settings)
            data = _local_read(path)
            data.pop(credential_id, None)
            _local_write(path, data)
        return
    client, project = _secret_manager()
    from google.api_core.exceptions import NotFound

    try:
        client.delete_secret(
            request={"name": f"projects/{project}/secrets/{_secret_id(credential_id)}"}
        )
    except NotFound:
        pass


def normalise_domain(domain):
    domain = domain.strip().lower().rstrip(".")
    if domain.startswith("*."):
        domain = domain[2:]
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", domain):
        raise ValueError(f"Invalid allowed domain {domain!r}")
    return domain


def domain_allowed(url, allowed_domains):
    """Fill only on https pages whose hostname is an allowed domain or its subdomain."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    return parts.scheme == "https" and any(
        host == domain or host.endswith("." + domain) for domain in allowed_domains
    )


def totp(seed, at=None, digits=6, step=30):
    """RFC 6238 TOTP (HMAC-SHA1) from a base32 seed."""
    seed = seed.replace(" ", "").upper()
    key = base64.b32decode(seed + "=" * (-len(seed) % 8))
    counter = int((time.time() if at is None else at) // step)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 10**digits).zfill(digits)
