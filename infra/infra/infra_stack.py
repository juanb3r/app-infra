from constructs import Construct
from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    SecretValue,
)


class InfraStack(Stack):

    def __init__(
            self,
            scope: Construct,
            id: str,
            secrets,
            lambda_code,
            lambda_layer_code,
            **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        pipeline = codepipeline.Pipeline(
            self, "CICD_Pipeline",
            cross_account_keys=False,
        )

        cdk_source_output = codepipeline.Artifact()
        lambda_source_output = codepipeline.Artifact()
        cdk_build_output = codepipeline.Artifact()
        lambda_build_output = codepipeline.Artifact()
        lambda_layer_build_output = codepipeline.Artifact()
        
        cdk_source_action = codepipeline_actions.GitHubSourceAction(
            action_name="CDK_GitHub_Source",
            owner="juanb3r",
            repo="app-infra",
            oauth_token=SecretValue.secrets_manager(secrets.secret_name),
            output=cdk_source_output,
            branch="master"
        )
        lambda_source_action = codepipeline_actions.GitHubSourceAction(
            action_name="AppCode_GitHub_Source",
            owner="juanb3r",
            repo="app-code",
            oauth_token=SecretValue.secrets_manager(secrets.secret_name),
            output=lambda_source_output,
            branch="master"
        )
        pipeline.add_stage(
            stage_name="Fuente",
            actions=[cdk_source_action, lambda_source_action]
        ) 
        cdk_build_project = codebuild.Project(self, "CdkBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": "npm install -g aws-cdk"
                    },
                    "build": {
                        "commands": [
                            "pip install -r requirements.txt",
                            "cd infra && cdk synth app -- -o .",
                            "cdk synth app > ./app.template.yaml",
                            "ls"
                        ]
                    }
                },
                "artifacts": {
                    "files": "./infra/app.template.yaml"
                }
            })
        )

        cdk_build_action = codepipeline_actions.CodeBuildAction(
            action_name="Construccion_CDK",
            project=cdk_build_project,
            input=cdk_source_output,
            outputs=[cdk_build_output]
        )

        lambda_build_project = codebuild.Project(self, "LambdaBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": "pip install -r requirements.txt"
                    },
                    "build": {
                        "commands": "pip install -r requirements.txt"
                    }
                },
                "artifacts": {
                    "files": ["funcion.py"]
                }
            })
        )
        lambda_build_action = codepipeline_actions.CodeBuildAction(
            action_name="Lambda_Build",
            project=lambda_build_project,
            input=lambda_source_output,
            outputs=[lambda_build_output]
        )
        lambda_layer_build_project = codebuild.Project(self, "LambdaLayerBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4
            ),
            environment_variables={
                "FILENAME": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    value="LambdaLayer.zip"
                ),
            },
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": [
                            "echo \"Creando entorno y activandolo\"",
                            "python3 -m venv venv",
                            ". venv/bin/activate",
                            "echo \"Actualizando pip\"",
                            "pip install --upgrade pip",
                            "echo \"Instalando librerías\"",
                            "pip install -r requirements.txt",
                        ]
                    },
                    "build": {
                        "commands": [
                            "export PYTHON_VERSION=$(python3 --version | egrep -o \"([0-9]{1,}\.)+[0-9]{1,}\" | cut -c1-3)",
                            "echo \"Version de python $PYTHON_VERSION\"",
                            "echo \"building layer deployable\"",
                            "mkdir -p build/python",
                            "piphome=../venv/lib/python$PYTHON_VERSION/site-packages/",
                            "cd build && cp -r $piphome python && cd ..",
                        ]
                    },
                },
                "artifacts": {
                    "files": [
                        "**/*"
                    ],
                    "base-directory": "build",
                    "name": "$FILENAME"
                }
            })
        )
        lambda_layer_build_action = codepipeline_actions.CodeBuildAction(
            action_name="Lambda_Layer_Build",
            project=lambda_layer_build_project,
            input=lambda_source_output,
            outputs=[lambda_layer_build_output]
        )
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                cdk_build_action,
                lambda_build_action,
                lambda_layer_build_action
            ]
        )
        pipeline.add_stage(
            stage_name="Despliegue",
            actions=[
                codepipeline_actions.CloudFormationCreateUpdateStackAction(
                    action_name="Lambda_CFN_Deploy",
                    template_path=cdk_build_output.at_path("infra/app.template.yaml"),
                    stack_name="ApplicationStackDeployed",
                    admin_permissions=True,
                    parameter_overrides={
                        **lambda_code.assign(
                            bucket_name=lambda_build_output.bucket_name,
                            object_key=lambda_build_output.object_key
                        ),
                        **lambda_layer_code.assign(
                            bucket_name=lambda_layer_build_output.bucket_name,
                            object_key=lambda_layer_build_output.object_key
                        )
                    },
                    extra_inputs=[
                        lambda_build_output,
                        lambda_layer_build_output
                    ]
                ),
            ]
        )
