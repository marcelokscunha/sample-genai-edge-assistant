# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import shared_variables as shared_variables
from sagemaker import image_uris
from sagemaker.processing import ProcessingJob, ProcessingOutput, ProcessingInput
from sagemaker.pytorch.estimator import PyTorch
from sagemaker.processing import FrameworkProcessor
from sagemaker.workflow.execution_variables import ExecutionVariables
from sagemaker.workflow.functions import Join
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.lambda_step import LambdaStep
from sagemaker.lambda_helper import Lambda


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
        region,
        script_path,
        sagemaker_session,
        default_approval_status="PendingManualApproval",
    ):

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
            default_value="huggingface-token"
        )

        # Instance types - using same PyTorch environment as endpoint deployment
        training_instance_type = ParameterString(
            name="TrainingInstanceType", 
            default_value="ml.m5.xlarge"  # Suitable for model preparation (no GPU needed). If training is ran, must change to GPU
        )
        
        validation_instance_type = ParameterString(
            name="ValidationInstanceType",
            default_value="ml.g5.xlarge"  # GPU instance for model validation
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
            source_dir=f"{script_path}/src",
            role=execution_role,
            instance_type=training_instance_type,
            instance_count=1,
            framework_version=pytorch_version,
            py_version=py_version,
            output_path=final_model_output_s3_uri,
            base_job_name="navigation-model-preparation",
            sagemaker_session=pipeline_session,
            environment={
                "HF_TOKEN_SECRET_NAME": hf_token_secret_name
            },
            # Disable distributed training
            distribution=None,
        )

        training_step = TrainingStep(
            name="PrepareNavigationModel",
            display_name="Prepare Navigation Model",
            description="Download and prepare the Gemma3n navigation model using PyTorch training job",
            estimator=pytorch_estimator,
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
            source_dir=f"{script_path}/src",
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
        )

        # Step 3: Model Registration
        # Use the PyTorch estimator for model registration
        register_model_step = RegisterModel(
            estimator=pytorch_estimator,
            name="RegisterNavigationModel",
            display_name="Register Navigation Model",
            description="Register the validated navigation model in SageMaker Model Registry",
            model_data=model_artifact_s3_uri,
            content_types=["application/json"],
            response_types=["application/json"],
            inference_instances=["ml.g5.xlarge", "ml.g5.2xlarge"],
            model_package_group_name=package_group_name,
            approval_status=approval_status,
            depends_on=[validation_step],
        )

        # Step 4: Inference Recommendation (Optional/Non-blocking)
        # Lambda function for creating inference recommendation job
        inference_recommendation_lambda = Lambda(
            function_name="navigation-inference-recommendation",
            execution_role_arn=execution_role,
            script=f"{script_path}/../../../functions/setup/inference_recommendation/src/inference_recommendation_lambda.py",
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
                )
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