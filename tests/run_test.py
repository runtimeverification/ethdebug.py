

import json
import os
from pathlib import Path
from ethdebug.format.info_schema import EthdebugFormatInfo
from ethdebug.format.program_schema import EthdebugFormatProgram

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

def test_output():

    for output in output_files:

        with open(output, 'r') as f:
            standard_json_output = json.load(f)

            ethdebug_data = standard_json_output.get('ethdebug', None)
            if ethdebug_data is None:
                print(f"Skipping {filename} as it does not contain ethdebug data")
            else:
                model = EthdebugFormatInfo.model_validate(ethdebug_data)

            for filename, file in standard_json_output.get('contracts', {}).items():

                for contract_name, contract in file.items():
                    bytecode_ethdebug_data = get_nested(contract, ('evm', 'bytecode', 'ethdebug'))
                    deployed_ethdebug_data = get_nested(contract, ('evm', 'deployedBytecode', 'ethdebug'))
                    for ethdebug_data in (bytecode_ethdebug_data, deployed_ethdebug_data):
                        if ethdebug_data is None:
                            continue
                        try:
                            model = EthdebugFormatProgram.model_validate(ethdebug_data)
                            assert model is not None, "Model validation returned None"
                            print("Model validation successful")
                            # Print the model in a human readable format
                            # print(model.model_dump_json(indent=4))
                        except Exception as e:
                            print(f"Error validating model for {filename}.{contract_name}: {e}")
                            raise AssertionError(f"Model validation failed: {e}")
    
test_output()