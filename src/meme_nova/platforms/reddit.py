from .base import Platform
from .host_based import HostBasedHandler

handler = HostBasedHandler(Platform.REDDIT, ("reddit.com", "redd.it"))
