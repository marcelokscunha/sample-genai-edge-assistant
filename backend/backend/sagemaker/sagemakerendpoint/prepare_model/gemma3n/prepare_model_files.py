import os 
import pathlib
import shutil

from dotenv import load_dotenv
from huggingface_hub import login

from test_utils import create_model_archive
from code.inference import NavigationPipeline

# Requirements:
# - Make sure you've installed the dependencies in requirements.txt with 'pip install -r core/requirements.txt'
# - Add .env file backend/backend/sagemaker/sagemakerendpoint/prepare_model/.env with HF_TOKEN=hf_abcdefGhijKlMnoPqrs

if __name__ == "__main__":

    load_dotenv()
    login(os.getenv("HF_TOKEN"))

    HERE = pathlib.Path(__file__).parent.absolute()
    code_dir = (HERE / "code").absolute()
    dst_dir = (HERE / "ARTIFACTS").absolute()
    dst_content_dir = (HERE / "ARTIFACTS" / "model").absolute()
    dst_content_code_dir = (dst_content_dir / "code").absolute()

    model_id = "google/gemma-3n-e2b-it"

    print("Downloading and saving model...")
    pipeline = NavigationPipeline(model_id)
    pipeline.processor.save_pretrained(dst_content_dir)
    pipeline.model.save_pretrained(dst_content_dir)

    print(f"Copying {code_dir.name} into {dst_content_code_dir}...")
    shutil.copytree(code_dir, dst_content_code_dir, dirs_exist_ok=True)

    print(f"Creating final '{dst_content_dir}/model.tar.gz' artifact with model and inference code...")
    create_model_archive(dst_content_dir, output_file_path = dst_dir/"package"/"model.tar.gz")
    print(f"\nArchive created successfully!")
    
    # Verify the size of the created archive
    archive_size = pathlib.Path(dst_dir/"package"/"model.tar.gz").stat().st_size / (1024 * 1024)  # Size in MB
    print(f"Archive size: {archive_size:.2f} MB")
