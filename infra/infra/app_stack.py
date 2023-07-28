from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct


class AppStack(Stack):
    
    @property
    def lambda_code_data(self):
        return self.lambda_code
    
    @property
    def lambda_layer_code_data(self):
        return self.lambda_layer_code

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_code = _lambda.Code.from_cfn_parameters()
        lambda_layer_code = _lambda.Code.from_cfn_parameters()

        app_function = _lambda.Function(
            self, 'MiAppFuncion',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=lambda_code,
            handler='funcion.handler',
            environment={
                "API_URL": "https://api.coindesk.com/v1/bpi/currentprice.json"
            }
        )

        app_layer = _lambda.LayerVersion(
            self, 'MiAppLayer',
            code=lambda_layer_code,
            layer_version_name="Juan",
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
            description='Mi Capa de App'
            )
        
        app_function.add_layers(app_layer)
        app_version = app_function.current_version

        app_alias_dev = _lambda.Alias(
            self, 'MiAppAlias',
            alias_name='dev',
            version=app_version
        )

        self.alias = app_alias_dev
        self.lambda_code = lambda_code
        self.lambda_layer_code = lambda_layer_code

        apigw.LambdaRestApi(
            self, 'Endpoint',
            handler=app_function,
        )
