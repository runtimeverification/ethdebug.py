# EthDebug.py

EthDebug.py is a library offering debugging primitives that are commonly used by developer tools, such as breakpoint-style debuggers, testing frameworks, or static analyzers/linters. Notably, it includes a complete debugger-side implementation of the EthDebug format. The main function is reading Solidity runtime information (like local variables) from a running Ethereum Virtual Machine.

Things you can do with EthDebug.py:
- Read the value of a Solidity variable at a paused machine state
- See which variables are in scope at a specific source location
- Provide better log and error messages by replacing unreadable EVM details with their human-readable Solidity counterparts

This library is agnostic of any specific virtual machine implementation and compiler. The following diagram shows the relationship between the different components:

```mermaid
flowchart TD
    Solc
    subgraph EthDebug.py
        Validator
        Machine
        Dereference
        Trace@{ shape: stadium}
        DebugData@{ shape: stadium}
        View@{shape: stadium}
    end
    EVM
    Debugger
    SolcOutput@{ shape: stadium, label: "Std Output\n EthDebug Data\nSource Maps"}
    Solc --> SolcOutput-->Validator
    EVMOutput@{ shape: stadium, label: "Tx Data\nAccount Data\nStruct Logs"}
    EVM -->EVMOutput-->Machine
    Validator-->DebugData-->Dereference
    Machine-->Trace-->Dereference
    Dereference-->View-->Debugger
```

## Goals and Non-Goals

- Improve ecosystem-wide developer experience by providing a rich set of debugging primitives
- Provide feedback on the specification and implementation of the EthDebug format
- Assist compilers when implementing the counterpart of the EthDebug protocol
- It is explicitly beyond the scope of this project to develop a fully-featured stand-alone debugger. For a debugger that uses this library, see [Simbolik](https://simbolik.runtimeverification.com/). In fact, this library used to be a part of Simbolik but has since been extracted into its own project.

## API Docs

The [Project Structure](#project-structure) section provides a high-level overview of the provided modules. Inside each module, you'll find extensive pydoc comments detailing how the module is meant to be used.

For examples of how to use the library for a specific task, the tests generally offer a good starting point.

### Project Structure

- `src/ethdebug/format` \
  This module contains parsers and generators for all EthDebug schemas. The module structure closely follows the sub-schema hierarchy. These models are auto-generated directly from the spec and kept up to date as the spec evolves.
- `src/ethdebug/evaluate.py` \
   This module contains data structures and algorithms for evaluating pointers in the context of a paused machine state. Notice that "evaluating" here is not the same as "dereferencing."
- `src/ethdebug/dereference` \
   This module offers a complete pointer dereferencing algorithm. This algorithm is a rewrite of the TypeScript reference implementation in Python. It has support for all pointer regions, collections, expressions, and templates.
- `src/ethdebug/cursor.py` \
   This module defines the result of dereferencing a pointer.
- `src/ethdebug/data.py` \
   The data module defines low-level primitives to convert between different data representations, such as converting between raw bytes and unsigned integers.
- `src/ethdebug/machine.py` \
   This module defines abstract protocols `Machine`, `MachineTrace`, and `MachineState`. EthDebug.py aims to be agnostic of any specific EVM implementation. Users of the library must implement these protocols themselves.
- `tests` contains all sorts of automated tests. Some tests are ported from the reference implementation to ensure consistency. Other tests are specifically developed to test the integration with the Solidity compiler.

## For Contributors and Maintainers

### Regenerating the Validators

The data models used for parsing and validating the EthDebug format are generated from the JSON schema using the `generate_model.py` script. The files should be regenerated when the JSON schema files change or when the `datamodel-code-generator` library is updated.

~~~bash
uv run python ./generate_model.py 
~~~

The `datamodel-code-generator` library we use to generate the validators has some custom changes to make it work with the EthDebug JSON schema files. The library is therefore embedded as a subtree in the `datamodel-code-generator` directory. To update the library, you can run the following command:

~~~bash
git subtree pull --prefix=datamodel-code-generator git@github.com:koxudaxi/datamodel-code-generator.git main --squash
~~~

### Using solc to Generate Standard JSON Output Files

~~~bash
pushd tests && solc --standard-json mega_playground/input.json > mega_playground/output.json && popd
pushd tests && solc --standard-json abstract_and_interface/input.json --pretty-json > abstract_and_interface/output.json && popd
pushd tests && solc --standard-json standard_yul_debug_info_ethdebug_compatible_output/input.json > standard_yul_debug_info_ethdebug_compatible_output/output.json --allow-paths . && popd
~~~
