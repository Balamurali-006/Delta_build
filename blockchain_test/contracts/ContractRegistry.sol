// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ContractRegistry {

    string public contractData;

    function storeContract(string memory _data) public {
        contractData = _data;
    }

    function getContract() public view returns(string memory) {
        return contractData;
    }
}