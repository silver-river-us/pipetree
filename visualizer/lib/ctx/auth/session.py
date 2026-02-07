from dataclasses import dataclass, field

from lib.ctx.identity.user import User
from lib.security import encode_token


@dataclass
class Session:
    user: User
    token: str = field(init=False)

    @property
    def tenant(self):
        return self.user.tenant

    def __post_init__(self) -> None:
        self.token = encode_token(self.user.id, self.user.email, self.tenant.id)
