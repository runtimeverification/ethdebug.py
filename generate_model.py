from glob import glob
from pathlib import Path

from datamodel_code_generator import InputFileType, generate, DataModelType
from datamodel_code_generator.model import PythonVersion

SCHEMA_DIR = Path("format/schemas")
OUTPUT_DIR = Path("src/ethdebug/format")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

generate(
    input_=SCHEMA_DIR,
    input_file_type=InputFileType.JsonSchema,
    output=OUTPUT_DIR,
    output_model_type=DataModelType.PydanticV2BaseModel,
    target_python_version=PythonVersion.PY_312,
)
