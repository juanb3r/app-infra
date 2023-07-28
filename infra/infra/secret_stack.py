from constructs import Construct
from aws_cdk import (
    Stack,
    aws_secretsmanager as secretsmanager,
)


class SecretStack(Stack):

    @property
    def secret_data(self):
        return self.secret

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        secret = secretsmanager.Secret(
            self, "my-github-token",
            description="Secret for the github token",
            generate_secret_string=secretsmanager.SecretStringGenerator()
        )

        self.secret = secret
