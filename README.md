# EthDebug.py

This is a Python library for debugging Ethereum smart contracts.
It provides a debugger-side implementation of the EthDebug format.


# For Devs

The data models used for parsing and validating the EthDebug format are generated from the JSON schema using the `generate_model.py` script.
The files should be regenerated when the JSON schema files change, or when the datamodel-code-generator library is updated.

~~~bash
uv run python ./generate_model.py 
~~~

The datamodel-code-generator library we use to generate the validators has some custom changes to make it work with the EthDebug JSON schema files.
The library is therefore embedded as a subtree in the `datamodel-code-generator` directory.
To update the library, you can run the following command:

~~~bash
git subtree pull --prefix=datamodel-code-generator git@github.com:koxudaxi/datamodel-code-generator.git main --squash
~~~


## Using solc to generate standard json output files

~~~bash
pushd tests && solc --standard-json mega_playground/input.json > mega_playground/output.json && popd
pushd tests && solc --standard-json abstract_and_interface/input.json --pretty-json > abstract_and_interface/output.json && popd
pushd tests && solc --standard-json standard_yul_debug_info_ethdebug_compatible_output/input.json > standard_yul_debug_info_ethdebug_compatible_output/output.json --allow-paths . && popd
~~~