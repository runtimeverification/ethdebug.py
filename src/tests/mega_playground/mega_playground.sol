// SPDX-License-Identifier: MIT
pragma solidity ^0.8.29;

/// @title MegaFeaturePlayground
/// @notice Demonstrates a broad spectrum of Solidity features.

/// User-defined value type
type UFixed256x18 is uint256;

/// Library example
library MathLib {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        return a + b;
    }
}

/// Interface example
interface IGreeter {
    function greet() external view returns (string memory);
}

/// Abstract contract example
abstract contract GreeterBase {
    function greet() public view virtual returns (string memory);
}

/// Enum example
enum Status { Pending, Active, Inactive }

/// Struct example
struct Profile {
    string name;
    uint age;
    Status status;
}

/// Base contract
contract Owned {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function transferOwnership(address newOwner) public onlyOwner {
        owner = newOwner;
    }
}

/// Main contract
contract MegaFeaturePlayground is Owned, GreeterBase, IGreeter {
    using MathLib for uint256;

    /// State variables
    uint256 public immutable creationTime;
    uint256 public constant VERSION = 1;
    uint256 public balance;
    mapping(address => Profile) public profiles;
    address[] public users;

    /// Events
    event ProfileCreated(address indexed user, string name, uint age);
    event EtherReceived(address indexed sender, uint amount);
    event CustomErrorRaised();

    /// Custom error
    error InvalidProfile(string reason);

    /// Constructor
    constructor() payable {
        creationTime = block.timestamp;
    }

    /// Receive Ether
    receive() external payable {
        emit EtherReceived(msg.sender, msg.value);
        balance += msg.value;
    }

    /// Fallback
    fallback() external payable {
        emit EtherReceived(msg.sender, msg.value);
    }

    /// External function
    function createProfile(string calldata name, uint age) external {
        if (age == 0) revert InvalidProfile("Age must be > 0");
        profiles[msg.sender] = Profile(name, age, Status.Active);
        users.push(msg.sender);
        emit ProfileCreated(msg.sender, name, age);
    }

    /// View function
    function getProfile(address user) public view returns (Profile memory) {
        return profiles[user];
    }

    /// Pure function
    function sum(uint256 a, uint256 b) public pure returns (uint256) {
        return a.add(b); // using library
    }

    /// Payable function
    function donate() external payable {
        balance += msg.value;
    }

    /// Internal function
    function internalHelper() internal view returns (bool) {
        return msg.sender == owner;
    }

    /// Private function
    function _privateLogic(uint256 x) private pure returns (uint256) {
        return x * 42;
    }

    /// Assembly example
    function getCodeSize(address _addr) public view returns (uint size) {
        assembly {
            size := extcodesize(_addr)
        }
    }

    /// Low-level call
    function callOther(address target, bytes calldata data) external payable {
        (bool success, ) = target.call{value: msg.value}(data);
        require(success, "Call failed");
    }

    /// Delegatecall
    function delegateTo(address target, bytes calldata data) external {
        (bool success, ) = target.delegatecall(data);
        require(success, "Delegatecall failed");
    }

    /// Try/catch
    function tryCreate(address addr) external {
        try this.createProfile("TryUser", 1) {
            // success
        } catch Error(string memory reason) {
            emit CustomErrorRaised();
        }
    }

    /// Overloaded functions
    function overload() public pure returns (string memory) {
        return "no args";
    }

    function overload(uint256 x) public pure returns (uint256) {
        return x + 1;
    }

    /// Overridden function
    function greet() public view override(GreeterBase, IGreeter) returns (string memory) {
        return "Hello from MegaFeaturePlayground";
    }

    /// Function selector
    function getSelector(string calldata sig) external pure returns (bytes4) {
        return bytes4(keccak256(bytes(sig)));
    }

    /// Storage vs memory vs calldata
    function echoMemory(string memory s) public pure returns (string memory) {
        return s;
    }

    function echoCalldata(string calldata s) public pure returns (string calldata) {
        return s;
    }

    function echoStorage(uint index) public view returns (string memory) {
        return profiles[users[index]].name;
    }
}
