
import pytest
import json
from pathlib import Path
from ethdebug.format.info_schema import Info
from ethdebug.format.program_schema import Program

script_dir = Path(__file__).parent
output_files = [
    script_dir / "abstract_and_interface/output.json",
    script_dir / "mega_playground/output.json",
    script_dir / "standard_yul_debug_info_ethdebug_compatible_output/output.json",
]

def get_nested(d, keys, default=None):
    for key in keys:
        d = d.get(key) if isinstance(d, dict) else default
        if d is default:
            break
    return d

@pytest.xfail(reason="This test is expected to fail because the solc output does not adhere to the ethdebug format.")
@pytest.mark.parametrize("output_file", output_files)
def test_info(output_file: Path):
    with open(output_file, 'r') as f:
        standard_json_output = json.load(f)
        ethdebug_data = standard_json_output.get('ethdebug', None)
        model = Info.model_validate(ethdebug_data)
        assert model is not None, "Model validation returned None"

@pytest.xfail(reason="This test is expected to fail because the solc output does not adhere to the ethdebug format.")
@pytest.mark.parametrize("output_file", output_files)
def test_program(output_file: Path):
    with open(output_file, 'r') as f:
        standard_json_output = json.load(f)
        ethdebug_data = standard_json_output.get('ethdebug', None)
        for filename, file in standard_json_output.get('contracts', {}).items():
            for contract_name, contract in file.items():
                bytecode_ethdebug_data = get_nested(contract, ('evm', 'bytecode', 'ethdebug'))
                deployed_ethdebug_data = get_nested(contract, ('evm', 'deployedBytecode', 'ethdebug'))
                for ethdebug_data in (bytecode_ethdebug_data, deployed_ethdebug_data):
                    model = Program.model_validate(ethdebug_data)
                    assert model is not None, "Model validation returned None"