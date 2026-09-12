// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import {Script, console} from "forge-std/Script.sol";
import {IntentraEscrow} from "src/IntentraEscrow.sol";
import {ERC20} from "openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockUSDC
 * @notice A simple ERC-20 mock with public mint for testnet deployments.
 */
contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }
}

/**
 * @title DeployIntentraEscrow
 * @notice Foundry deployment script for IntentraEscrow and MockUSDC.
 * @dev    Usage:
 *         forge script script/Deploy.s.sol --rpc-url $RPC_URL \
 *           --account $ACCOUNT --sender $SENDER --broadcast
 *
 *         Required env vars:
 *           AI_ARBITRATOR  — The AI arbitrator wallet address
 *           OWNER          — The Human Oracle / admin multisig address
 *         Optional:
 *           USDC_ADDRESS   — If set, uses existing USDC; otherwise deploys MockUSDC.
 *           APPEAL_FEE     — Appeal stake (default: 0.01 ether)
 */
contract DeployIntentraEscrow is Script {
    function run()
        external
        returns (IntentraEscrow escrow, address usdcAddr)
    {
        address aiArbitrator = vm.envOr("AI_ARBITRATOR", address(0xAA11));
        address owner = vm.envOr("OWNER", msg.sender);
        uint256 appealFee = vm.envOr("APPEAL_FEE", uint256(0.01 ether));
        usdcAddr = vm.envOr("USDC_ADDRESS", address(0));

        vm.startBroadcast();

        // Deploy MockUSDC if no address provided
        if (usdcAddr == address(0)) {
            MockUSDC mockUsdc = new MockUSDC();
            usdcAddr = address(mockUsdc);
            console.log("MockUSDC deployed at:", usdcAddr);

            // Mint test tokens to the deployer
            mockUsdc.mint(msg.sender, 1_000_000e6);
            console.log("Minted 1M USDC to deployer");
        }

        escrow = new IntentraEscrow(aiArbitrator, owner, appealFee);
        console.log("IntentraEscrow deployed at:", address(escrow));
        console.log("AI Arbitrator:", aiArbitrator);
        console.log("Owner (Human Oracle):", owner);

        vm.stopBroadcast();
    }
}
