from .base import Platform
from .host_based import HostBasedHandler

handler = HostBasedHandler(Platform.FACEBOOK, ("facebook.com", "fb.com", "fb.watch"))
