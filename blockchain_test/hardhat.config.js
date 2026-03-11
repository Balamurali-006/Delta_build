require("@nomiclabs/hardhat-ethers");
require("dotenv").config();

const { TENDERLY_RPC_URL, LOCAL_RPC_URL, PRIVATE_KEY } = process.env;

module.exports = {
  solidity: "0.8.20",
  networks: {
    localhost: { url: LOCAL_RPC_URL || "http://127.0.0.1:8545" },
    tenderly: {
      url: TENDERLY_RPC_URL,
      accounts: PRIVATE_KEY ? [PRIVATE_KEY] : []
    }
    // add others if needed
  }
};