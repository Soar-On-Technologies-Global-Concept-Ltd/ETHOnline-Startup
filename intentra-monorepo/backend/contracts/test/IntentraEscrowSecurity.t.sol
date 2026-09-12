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

/// @notice The attacks the escrow has to survive: a stolen resolver key, a hostile counterparty, a replayed
///         signature from another job, and anyone at all calling the money-moving functions.
contract IntentraEscrowSecurityTest is Test {
    IntentraEscrow escrow;
    MockUSDC usdc;

    uint256 customerKey = 0xA11CE;
    uint256 providerKey = 0xB0B;
    uint256 attackerKey = 0xBAD;
    address customer;
    address provider;
    address attacker;
    address resolver = address(0xE5);

    bytes32 txKey = keccak256("job-1");
    bytes32 otherKey = keccak256("job-2");
    uint256 amount = 100_000_000;

    function setUp() public {
        customer = vm.addr(customerKey);
        provider = vm.addr(providerKey);
        attacker = vm.addr(attackerKey);
        usdc = new MockUSDC();
        escrow = new IntentraEscrow(address(usdc), resolver);
        usdc.mint(customer, amount * 2);
        vm.prank(customer);
        escrow.fund(txKey, provider, amount, keccak256("auth"), 600, uint64(block.timestamp + 7200));
    }

    // ---------------------------------------------------------------- a stolen resolver key

    function test_resolver_cannot_settle_without_both_signatures() public {
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory onlyProvider = _sign(providerKey, _digest(txKey, 10000, outcome));
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadSignature.selector);
        escrow.resolve(txKey, 10000, outcome, onlyProvider, onlyProvider);
        assertEq(usdc.balanceOf(address(escrow)), amount, "the money must not move");
    }

    function test_resolver_cannot_forge_a_signature_with_its_own_key() public {
        _dispute();
        bytes32 outcome = keccak256("outcome");
        uint256 resolverKey = 0xE5E5;
        bytes memory forged = _sign(resolverKey, _digest(txKey, 10000, outcome));
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadSignature.selector);
        escrow.resolve(txKey, 10000, outcome, forged, forged);
    }

    function test_resolver_cannot_pay_a_third_party() public {
        // There is no argument for a recipient: the contract only ever pays this job's two parties.
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory customerSig = _sign(customerKey, _digest(txKey, 7000, outcome));
        bytes memory providerSig = _sign(providerKey, _digest(txKey, 7000, outcome));
        vm.prank(resolver);
        escrow.resolve(txKey, 7000, outcome, customerSig, providerSig);
        assertEq(usdc.balanceOf(attacker), 0, "a third party must never be paid");
        assertEq(usdc.balanceOf(address(escrow)), 0, "the escrow keeps nothing");
        // the customer was minted amount * 2 and funded one job, so the two parties hold everything between them
        assertEq(usdc.balanceOf(provider) + usdc.balanceOf(customer), amount * 2);
    }

    // ---------------------------------------------------------------- signature replay

    function test_a_resolution_signed_for_another_job_is_refused() public {
        vm.prank(customer);
        escrow.fund(otherKey, provider, amount, keccak256("auth-2"), 600, uint64(block.timestamp + 7200));
        _dispute();
        bytes32 outcome = keccak256("outcome");
        // Both parties signed a resolution for job 2; it must not settle job 1.
        bytes memory customerSig = _sign(customerKey, _digest(otherKey, 10000, outcome));
        bytes memory providerSig = _sign(providerKey, _digest(otherKey, 10000, outcome));
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadSignature.selector);
        escrow.resolve(txKey, 10000, outcome, customerSig, providerSig);
    }

    function test_a_resolution_for_a_different_split_is_refused() public {
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory customerSig = _sign(customerKey, _digest(txKey, 5000, outcome));
        bytes memory providerSig = _sign(providerKey, _digest(txKey, 5000, outcome));
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadSignature.selector);
        escrow.resolve(txKey, 10000, outcome, customerSig, providerSig);   // resolver tries to keep more
    }

    function test_settles_exactly_once() public {
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory c = _sign(customerKey, _digest(txKey, 7000, outcome));
        bytes memory p = _sign(providerKey, _digest(txKey, 7000, outcome));
        vm.prank(resolver);
        escrow.resolve(txKey, 7000, outcome, c, p);
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.resolve(txKey, 7000, outcome, c, p);
    }

    // ---------------------------------------------------------------- access control

    function test_only_the_provider_can_submit() public {
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.NotParty.selector);
        escrow.submit(txKey, keccak256("deliverable"));
    }

    function test_a_stranger_cannot_release_before_the_window_closes() public {
        vm.prank(provider);
        escrow.submit(txKey, keccak256("deliverable"));
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.TooEarly.selector);
        escrow.release(txKey);
    }

    function test_a_stranger_cannot_release_work_that_was_never_submitted() public {
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.NotParty.selector);
        escrow.release(txKey);
    }

    function test_only_the_customer_or_resolver_can_freeze_the_money() public {
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.NotParty.selector);
        escrow.openDispute(txKey, keccak256("complaint"));
    }

    function test_only_the_resolver_can_anchor_evidence() public {
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.NotResolver.selector);
        escrow.anchorEvidence(txKey, keccak256("photo"));
    }

    function test_release_stays_blocked_while_disputed() public {
        _dispute();
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.release(txKey);
        vm.warp(block.timestamp + 10_000);
        vm.prank(attacker);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.release(txKey);
    }

    // ---------------------------------------------------------------- funding and refunds

    function test_a_job_key_cannot_be_funded_twice() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.fund(txKey, provider, amount, keccak256("auth"), 600, uint64(block.timestamp + 7200));
    }

    function test_a_customer_cannot_be_their_own_provider() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow.BadInput.selector);
        escrow.fund(keccak256("self"), customer, amount, keccak256("auth"), 600, uint64(block.timestamp + 7200));
    }

    function test_refund_is_refused_before_the_deadline_and_after_delivery() public {
        vm.expectRevert(IntentraEscrow.TooEarly.selector);
        escrow.claimRefund(txKey);
        vm.prank(provider);
        escrow.submit(txKey, keccak256("deliverable"));
        vm.warp(block.timestamp + 7201);
        vm.expectRevert(IntentraEscrow.WrongStatus.selector);
        escrow.claimRefund(txKey);      // delivered work is not refundable by timeout
    }

    function test_a_refund_pays_the_customer_and_nobody_else() public {
        vm.warp(block.timestamp + 7201);
        vm.prank(attacker);
        escrow.claimRefund(txKey);      // anyone may trigger it
        assertEq(usdc.balanceOf(customer), amount * 2);
        assertEq(usdc.balanceOf(attacker), 0);
    }

    // ---------------------------------------------------------------- arithmetic

    function testFuzz_a_split_never_creates_or_destroys_money(uint16 bps) public {
        bps = uint16(bound(bps, 0, 10_000));
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory customerSig = _sign(customerKey, _digest(txKey, bps, outcome));
        bytes memory providerSig = _sign(providerKey, _digest(txKey, bps, outcome));
        vm.prank(resolver);
        escrow.resolve(txKey, bps, outcome, customerSig, providerSig);
        assertEq(usdc.balanceOf(provider) + usdc.balanceOf(customer), amount * 2);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(usdc.balanceOf(provider), (uint256(amount) * bps) / 10_000);
    }

    function test_a_split_over_one_hundred_percent_is_refused() public {
        _dispute();
        bytes32 outcome = keccak256("outcome");
        bytes memory customerSig = _sign(customerKey, _digest(txKey, 10_001, outcome));
        bytes memory providerSig = _sign(providerKey, _digest(txKey, 10_001, outcome));
        vm.prank(resolver);
        vm.expectRevert(IntentraEscrow.BadInput.selector);
        escrow.resolve(txKey, 10_001, outcome, customerSig, providerSig);
    }

    // ---------------------------------------------------------------- helpers

    function _dispute() private {
        vm.prank(customer);
        escrow.openDispute(txKey, keccak256("complaint"));
    }

    function _digest(bytes32 key, uint16 bps, bytes32 outcome) private view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", escrow.domainSeparator(),
            keccak256(abi.encode(keccak256("Resolution(bytes32 txKey,uint16 providerBps,bytes32 outcomeHash)"),
                                 key, bps, outcome))));
    }

    function _sign(uint256 key, bytes32 digest) private pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, digest);
        return abi.encodePacked(r, s, v);
    }
}
