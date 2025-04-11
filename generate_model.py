from glob import glob
from pathlib import Path

from datamodel_code_generator import InputFileType, generate, DataModelType
from datamodel_code_generator.model import PythonVersion

SCHEMA_DIR = Path("format/schemas")
OUTPUT_DIR = Path("src/ethdebug/format")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_FILES = glob(str(SCHEMA_DIR / "**/*.schema.yaml"), recursive=True)

for schema_file in SCHEMA_FILES:
    schema_file = Path(schema_file)
    relative_path = schema_file.relative_to(SCHEMA_DIR)
    # Remove the `.schema` part from the file stem
    relative_path = relative_path.with_name(relative_path.stem.replace(".schema", "")).with_suffix(".py")
    output_file = OUTPUT_DIR / relative_path

    # Ensure the output directory structure matches the input structure
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating Pydantic model for {schema_file.stem} -> {output_file}")

    generate(
        input_=schema_file,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        target_python_version=PythonVersion.PY_312,
    )
