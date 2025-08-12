# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from sagemaker import image_uris
from sagemaker.processing import ProcessingJob, ProcessingOutput, ProcessingInput
from sagemaker.pytorch.estimator import PyTorch
from sagemaker.processing import FrameworkProcessor
from sagemaker.workflow.execution_variables import ExecutionVariables
from sagemaker.workflow.functions import Join
from sagemaker.workflow.parameters import ParameterString, ParameterInteger, ParameterFloat
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, CacheConfig
from sagemaker.workflow.lambda_step import LambdaStep
from sagemaker.lambda_helper import Lambda

import shared_variables as shared_variables

class NavigationModelTrainingPipeline:
    """
    Navigation Model Preparation Pipeline for Gemma3n model.
    
    This pipeline handles:
    1. Model preparation (downloading and packaging) and training via PyTorch training job
    2. Model validation via PyTorch processing job  
    3. Model registration in SageMaker Model Registry
    4. Inference recommendation job (optional)
    """

    def __init__(
        self,
        pipeline_name,
        input_bucket_name,  # use it for passing training data, etc.
        output_bucket_name,
        prefix_bucket_path,
        package_group_name_p,
        pipeline_session,
        execution_role,
        lambda_execution_role,
        region,
        script_path,
        sagemaker_session,
        default_approval_status="PendingManualApproval",
        default_hf_token_secret_name="huggingface-token",
        enable_step_cache=True,
    ):
        # Constants for sample payload
        SAMPLE_PAYLOAD_FILENAME = "navigation_sample_payload.tar.gz"

        # Pipeline parameters
        export_model_output_s3_uri = ParameterString(
            name="ModelOutputS3Uri",
            default_value=f"s3://{output_bucket_name}/{prefix_bucket_path}/output",
        )
        
        package_group_name = ParameterString(
            name="PackageGroupName", 
            default_value=package_group_name_p
        )
        
        approval_status = ParameterString(
            name="DefaultApprovalStatus", 
            default_value=default_approval_status
        )

        hf_token_secret_name = ParameterString(
            name="HuggingFaceTokenSecretName",
            default_value=default_hf_token_secret_name
        )

        # Instance types - using same PyTorch environment as endpoint deployment
        training_instance_type = ParameterString(
            name="TrainingInstanceType", 
            default_value="ml.m5.xlarge"  # Suitable for model preparation (no GPU needed). If training is ran, must change to GPU
        )
        
        validation_instance_type = ParameterString(
            name="ValidationInstanceType",
            default_value="ml.g6.xlarge"  # GPU instance for model validation
        )

        # PyTorch versions for training and endpoint deployment must match
        pytorch_version = "2.6.0"
        py_version = "py312"

        # S3 paths for pipeline execution
        final_model_output_s3_uri = Join(
            on="/",
            values=[
                export_model_output_s3_uri,
                ExecutionVariables.PIPELINE_EXECUTION_ID,
                ExecutionVariables.START_DATETIME,
            ],
        )

        # Step 1: Model Preparation using PyTorch Training Job
        pytorch_estimator = PyTorch(
            entry_point="train.py",
            source_dir=f"{script_path}",
            role=execution_role,
            instance_type=training_instance_type,
            instance_count=1,
            framework_version=pytorch_version,
            py_version=py_version,
            output_path=final_model_output_s3_uri,
            base_job_name="navigation-model-preparation",
            sagemaker_session=pipeline_session,
            environment={
                "HF_TOKEN_SECRET_NAME": hf_token_secret_name,
                "AWS_DEFAULT_REGION": shared_variables.CDK_OUT_KEY_REGION
            },
            # Disable distributed training
            distribution=None,
        )

        cache_config = None
        if enable_step_cache:
            cache_config = CacheConfig(enable_caching=True, expire_after="1d")

        training_step = TrainingStep(
            name="PrepareNavigationModel",
            display_name="Prepare Navigation Model",
            description="Download and prepare the Gemma3n navigation model using PyTorch training job",
            estimator=pytorch_estimator,
            cache_config=cache_config,
        )

        # Model artifacts S3 URI from training step
        model_artifact_s3_uri = training_step.properties.ModelArtifacts.S3ModelArtifacts

        # Step 2: Model Validation using PyTorch Processing Job with FrameworkProcessor pattern        
        pytorch_processor = FrameworkProcessor(
            estimator_cls=PyTorch,
            framework_version=pytorch_version,
            py_version=py_version,
            role=execution_role,
            instance_type=validation_instance_type,
            instance_count=1,
            base_job_name="navigation-model-validation",
            sagemaker_session=pipeline_session,
            env={
                "SAMPLE_PAYLOAD_FILENAME": SAMPLE_PAYLOAD_FILENAME
            },
        )

        validation_output_s3_uri = Join(
            on="/",
            values=[
                final_model_output_s3_uri,
                "validation"
            ],
        )

        # Use the run method to get step_args with proper source_dir
        step_args = pytorch_processor.run(
            code="validate_model.py",
            source_dir=f"{script_path}",
            inputs=[
                ProcessingInput(
                    source=training_step.properties.ModelArtifacts.S3ModelArtifacts,
                    destination="/opt/ml/processing/input/model",
                    input_name="model"
                )
            ],
            outputs=[
                ProcessingOutput(
                    source="/opt/ml/processing/output",
                    destination=validation_output_s3_uri,
                    output_name="validation_results"
                )
            ],
        )

        validation_step = ProcessingStep(
            name="ValidateNavigationModel",
            display_name="Validate Navigation Model", 
            description="Validate the prepared navigation model with test inference",
            step_args=step_args,
            depends_on=[training_step],
            cache_config=cache_config,
        )

        # Step 3: Model Registration
        # Sample payload S3 URI from validation step
        sample_payload_s3_uri = Join(
            on="/",
            values=[
                validation_output_s3_uri,
                SAMPLE_PAYLOAD_FILENAME
            ],
        )
        
        # Use the PyTorch estimator for model registration
        register_model_step = RegisterModel(
            estimator=pytorch_estimator,
            name="RegisterNavigationModel",
            display_name="Register Navigation Model",
            description="Register the validated navigation model in SageMaker Model Registry",
            model_data=model_artifact_s3_uri,
            content_types=["application/json"],
            response_types=["application/json"],
            inference_instances=["ml.g6.xlarge", "ml.g6.2xlarge"],
            model_package_group_name=package_group_name,
            approval_status=approval_status,
            sample_payload_url=sample_payload_s3_uri,
            domain="COMPUTER_VISION",
            task="TEXT_GENERATION",
            depends_on=[validation_step],
        )

        # Step 4: Inference Recommendation (Optional/Non-blocking)
        # Lambda function for creating inference recommendation job
        inference_recommendation_lambda = Lambda(
            function_name=shared_variables.LAMBDA_NAVIGATION_INFERENCE_RECOMMENDATION,
            execution_role_arn=lambda_execution_role,
            script=f"{shared_variables.BACKEND_DIR}/functions/setup/inference_recommendation/src/inference_recommendation_lambda.py",
            handler="inference_recommendation_lambda.handler",
            timeout=900,  # 15 minutes timeout
            memory_size=256,
        )

        # S3 URI for storing inference recommendation results
        inference_results_s3_uri = Join(
            on="/",
            values=[
                final_model_output_s3_uri,
                "inference-recommendations"
            ],
        )

        inference_recommendation_step = LambdaStep(
            name="InferenceRecommendation",
            display_name="Create Inference Recommendation Job",
            description="Create SageMaker Inference Recommender job for the registered model (non-blocking)",
            lambda_func=inference_recommendation_lambda,
            inputs={
                "model_package_arn": register_model_step.properties.ModelPackageArn,
                "job_name": Join(
                    on="-",
                    values=[
                        "navigation-inference-rec",
                        ExecutionVariables.PIPELINE_EXECUTION_ID
                    ]
                ),
                "results_s3_bucket": output_bucket_name,
                "results_s3_prefix": Join(
                    on="/",
                    values=[
                        prefix_bucket_path,
                        "inference-recommendations",
                        ExecutionVariables.PIPELINE_EXECUTION_ID
                    ]
                ),
                "execution_role_arn": execution_role
            },
            depends_on=[register_model_step],
        )

        # Define the pipeline
        self.pipeline = Pipeline(
            name=pipeline_name,
            parameters=[
                export_model_output_s3_uri,
                training_instance_type,
                validation_instance_type,
                package_group_name,
                approval_status,
                hf_token_secret_name,
            ],
            steps=[
                training_step,
                validation_step, 
                register_model_step,
                inference_recommendation_step
            ],
            sagemaker_session=sagemaker_session,
        )

    def get_pipeline(self):
        return self.pipeline


class NavigationModelDeploymentPipeline:
    """
    Navigation Model Deployment Pipeline for deploying approved Gemma3n models.
    
    This pipeline handles:
    1. Endpoint deployment using approved model package from registry
    2. Autoscaling configuration using Lambda function
    
    The pipeline is triggered by EventBridge when a model is approved in the registry.
    This is the second pipeline in the two-pipeline architecture as specified in the requirements.
    """

    def __init__(
        self,
        pipeline_name,
        output_bucket_name,
        prefix_bucket_path,
        pipeline_session,
        execution_role,
        lambda_execution_role,
        region,
        sagemaker_session,
    ):

        # Pipeline parameters - model package ARN provided by EventBridge trigger
        model_package_arn = ParameterString(
            name="ModelPackageArn",
            default_value=""  # Provided by EventBridge trigger
        )

        endpoint_name = ParameterString(
            name="EndpointName",
            default_value="vis-assis-navigation-endpoint"
        )

        # Instance configuration for deployment
        instance_type = ParameterString(
            name="InstanceType",
            default_value="ml.g6.xlarge"  # GPU instance suitable for Gemma3n model
        )

        initial_instance_count = ParameterInteger(
            name="InitialInstanceCount",
            default_value=1
        )

        # Autoscaling configuration parameters
        min_capacity = ParameterInteger(
            name="MinCapacity",
            default_value=1
        )

        max_capacity = ParameterInteger(
            name="MaxCapacity", 
            default_value=2
        )

        target_invocations_per_instance = ParameterFloat(
            name="TargetInvocationsPerInstance",
            default_value=10.0
        )

        # Step 1: Deploy endpoint using Lambda function
        # Lambda function for deploying the endpoint from model package
        # TODO: replace by built-in Step for endpoint deployment when SageMaker SDK supports it
        deploy_lambda = Lambda(
            function_name=shared_variables.LAMBDA_DEPLOY_NAVIGATION_ENDPOINT,
            execution_role_arn=lambda_execution_role,
            script=f"{shared_variables.BACKEND_DIR}/functions/setup/deploy_navigation_endpoint/src/endpoint_deployment_lambda.py",
            handler="endpoint_deployment_lambda.handler",
            timeout=900,  # 15 minutes timeout for endpoint deployment
            memory_size=512,
        )

        deploy_step = LambdaStep(
            name="DeployNavigationEndpoint",
            display_name="Deploy Navigation Endpoint",
            description="Deploy the navigation model as a SageMaker endpoint from approved model package",
            lambda_func=deploy_lambda,
            inputs={
                "model_package_arn": model_package_arn,
                "endpoint_name": endpoint_name,
                "instance_type": instance_type,
                "initial_instance_count": initial_instance_count,
                "execution_role": execution_role,
                "region": region,
            },
        )

        # Step 2: Configure autoscaling using Lambda function
        # Lambda function for configuring endpoint autoscaling
        autoscaling_lambda = Lambda(
            function_name=shared_variables.LAMBDA_SETUP_NAVIGATION_ENDPOINT_AUTOSCALING,
            execution_role_arn=lambda_execution_role,
            script=f"{shared_variables.BACKEND_DIR}/functions/setup/setup_navigation_endpoint_autoscaling/src/endpoint_autoscaling_lambda.py",
            handler="lambda.handler",
            timeout=300,  # 5 minutes timeout
            memory_size=256,
        )

        autoscaling_step = LambdaStep(
            name="ConfigureAutoscaling",
            display_name="Configure Endpoint Autoscaling",
            description="Configure autoscaling policies for the deployed navigation endpoint",
            lambda_func=autoscaling_lambda,
            inputs={
                "endpoint_name": endpoint_name,
                "min_capacity": min_capacity,
                "max_capacity": max_capacity,
                "target_value": target_invocations_per_instance,
            },
            depends_on=[deploy_step],
        )

        # Define the pipeline
        self.pipeline = Pipeline(
            name=pipeline_name,
            parameters=[
                model_package_arn,
                endpoint_name,
                instance_type,
                initial_instance_count,
                min_capacity,
                max_capacity,
                target_invocations_per_instance,
            ],
            steps=[
                deploy_step,
                autoscaling_step,
            ],
            sagemaker_session=sagemaker_session,
        )

    def get_pipeline(self):
        return self.pipeline