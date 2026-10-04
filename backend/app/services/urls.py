import ipaddress
import socket
from urllib.parse import urlparse


class InvalidUrl(ValueError):
    pass


def validate_url(raw: str, allow_private: bool = False) -> str:
    url = (raw or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise InvalidUrl("El enlace debe empezar con http:// o https://")
    if allow_private:
        return url

    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror:
        raise InvalidUrl("No se pudo resolver el dominio del enlace")

    for address in addresses:
        if not ipaddress.ip_address(address.split("%")[0]).is_global:
            raise InvalidUrl("No se permiten enlaces a direcciones privadas o locales")
    return url
