from dataclasses import dataclass, field

from lib.ctx.identity.tenant import Tenant
from lib.ctx.identity.user import User
from lib.security import encode_token


@dataclass
class Session:
    user: User
    tenant: Tenant
    token: str = field(init=False)

    def __post_init__(self) -> None:
        self.token = encode_token(self.user.id, self.user.email, self.tenant.id)
