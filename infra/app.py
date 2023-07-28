#!/usr/bin/env python3

import aws_cdk as cdk

from infra.infra_stack import InfraStack
from infra.secret_stack import SecretStack
from infra.app_stack import AppStack


app = cdk.App()

application = AppStack(app, "app")
secret = SecretStack(app, "secret")
infra = InfraStack(
    app,
    "infra",
    secrets= secret.secret_data,
    lambda_code=application.lambda_code_data,
    lambda_layer_code=application.lambda_layer_code_data
    )

app.synth()
