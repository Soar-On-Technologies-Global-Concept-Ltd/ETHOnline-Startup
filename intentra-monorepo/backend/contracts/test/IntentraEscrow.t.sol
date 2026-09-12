// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IntentraEscrow} from "../src/IntentraEscrow.sol";

contract MockUSDC {
    mapping(address => uint256) public balanceOf;
    function mint(address to, uint256 amount) external { balanceOf[to] += amount; }
    function transfer(address to, uint256 v) external returns (bool) {
        balanceOf[msg.sender] -= v; balanceOf[to] += v; return true;
    }
    function transferFrom(address f, address t, uint256 v) external returns (bool) {
        balanceOf[f] -= v; balanceOf[t] += v; return true;
    }
}

contract IntentraEscrowTest is Test {
    IntentraEscrow escrow;
    MockUSDC usdc;
    uint256 customerKey = 0xA11CE;
    uint256 providerKey = 0xB0B;
    address customer;
    address provider;
    address resolver = address(0xE5);
    bytes32 txKey = keccak256("tx-1");
    uint256 amount = 100_000_000;      // 100 USDC at 6 decimals

    function setUp() public {
        customer = vm.addr(customerKey);
        provider = vm.addr(providerKey);
        usdc = new MockUSDC();
        escrow = new IntentraEscrow(address(usdc), resolver);
        usdc.mint(customer, amount);
        vm.prank(customer);
        escrow.fund(txKey, provider, amount, keccak256("auth"), 600, uint64(block.timestamp + 7200));
    }

    function test_fund_holds_the_money() public view {
        assertEq(usdc.balanceOf(address(escrow)), amount);
    }

    function test_release_after_window_pays_provider_in_full() public {
        vm.prank(provider);
        escrow.submit(txKey, keccak256("deliverable"));
        vm.warp(block.timestamp + 601);
        escrow.release(txKey);
        assertEq(usdc.balanceOf(provider), amount);
    }

    function test_release_reverts_while_disputed() public {
        vm.prank(provider);
        escrow.submit(txKey, keccak256("deliverable"));
        vm.prank(customer);
        escrow.openDispute(txKey, keccak256("complaint"));
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.release(txKey);
    }

    function test_resolve_needs_both_signatures_and_conserves_the_amount() public {
        vm.prank(provider);
        escrow.submit(txKey, keccak256("deliverable"));
        vm.prank(customer);
        escrow.openDispute(txKey, keccak256("complaint"));
        bytes32 outcome = keccak256("outcome");
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", escrow.domainSeparator(),
            keccak256(abi.encode(keccak256("Resolution(bytes32 txKey,uint16 providerBps,bytes32 outcomeHash)"),
                                 txKey, uint16(7000), outcome))));
        bytes memory sigCustomer = _sign(customerKey, digest);
        bytes memory sigProvider = _sign(providerKey, digest);

        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadSignature.selector);
        escrow.resolve(txKey, 7000, outcome, sigProvider, sigProvider);   // customer signature missing

        vm.prank(resolver);
        escrow.resolve(txKey, 7000, outcome, sigCustomer, sigProvider);
        assertEq(usdc.balanceOf(provider), 70_000_000);
        assertEq(usdc.balanceOf(customer), 30_000_000);
        assertEq(usdc.balanceOf(address(escrow)), 0);
    }

    function test_claim_refund_after_expiry() public {
        vm.warp(block.timestamp + 7201);
        escrow.claimRefund(txKey);
        assertEq(usdc.balanceOf(customer), amount);
    }

    function test_settles_once() public {
        vm.warp(block.timestamp + 7201);
        escrow.claimRefund(txKey);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.claimRefund(txKey);
    }

    function _sign(uint256 key, bytes32 digest) private pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }
}
