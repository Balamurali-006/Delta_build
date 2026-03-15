async function main() {

  const Contract = await ethers.getContractFactory("ContractRegistry");

  const contract = await Contract.deploy();

  await contract.waitForDeployment();

  console.log("Contract deployed at:", contract.target);
}

main();
