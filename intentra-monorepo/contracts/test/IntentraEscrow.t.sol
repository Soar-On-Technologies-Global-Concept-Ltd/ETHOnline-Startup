// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import {Test} from "forge-std/Test.sol";
import {IntentraEscrow} from "src/IntentraEscrow.sol";
import {
    IntentCreated,
    IntentFunded,
    DisputeRaised,
    AIProposalSubmitted,
    AppealEscalated,
    IntentResolved,
    AbandonmentExecuted
} from "src/IntentraEscrow.sol";
import {ERC20} from "openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import {MessageHashUtils} from "openzeppelin-contracts/contracts/utils/cryptography/MessageHashUtils.sol";

/*//////////////////////////////////////////////////////////////
                            MOCK CONTRACTS
//////////////////////////////////////////////////////////////*/

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }
}

/*//////////////////////////////////////////////////////////////
                            BASE TEST SETUP
//////////////////////////////////////////////////////////////*/

abstract contract IntentraEscrowBaseTest is Test {
    IntentraEscrow public escrow;
    MockUSDC public usdc;

    // Private keys for EIP-712 signing
    uint256 internal constant CUSTOMER_PK = 0xA11CE;
    uint256 internal constant PROVIDER_PK = 0xB0B;
    uint256 internal constant AI_PK = 0xA1;

    address internal customer;
    address internal provider;
    address internal aiArbitrator;
    address internal owner;

    uint256 internal constant AMOUNT = 1000e6; // 1000 USDC
    uint256 internal constant APPEAL_FEE = 0.01 ether;

    function setUp() public virtual {
        customer = vm.addr(CUSTOMER_PK);
        provider = vm.addr(PROVIDER_PK);
        aiArbitrator = vm.addr(AI_PK);
        owner = address(this);

        usdc = new MockUSDC();
        escrow = new IntentraEscrow(aiArbitrator, owner, APPEAL_FEE);

        usdc.mint(customer, 100_000e6);
        vm.prank(customer);
        usdc.approve(address(escrow), type(uint256).max);
    }

    /*//////////////////////////////////////////////////////////////
                            HELPER FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function _createAndFundIntent() internal returns (uint256 intentId) {
        vm.prank(customer);
        intentId = escrow.createIntent(provider, address(usdc), AMOUNT);

        vm.prank(customer);
        escrow.fundIntent(intentId);
    }

    function _createFundAndDispute() internal returns (uint256 intentId) {
        intentId = _createAndFundIntent();

        vm.prank(customer);
        escrow.raiseDispute(intentId);
    }

    function _createFundDisputeAndPropose(
        uint256 custAmt,
        uint256 provAmt
    ) internal returns (uint256 intentId) {
        intentId = _createFundAndDispute();

        vm.prank(aiArbitrator);
        escrow.submitAIProposal(intentId, custAmt, provAmt);
    }

    function _signResolveIntent(
        uint256 pk,
        uint256 intentId,
        uint256 customerAmount,
        uint256 providerAmount
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(
            abi.encode(
                escrow.RESOLVE_INTENT_TYPEHASH(),
                intentId,
                customerAmount,
                providerAmount
            )
        );
        bytes32 digest = MessageHashUtils.toTypedDataHash(
            escrow.domainSeparator(),
            structHash
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }
}

/*//////////////////////////////////////////////////////////////
                        CREATION TESTS
//////////////////////////////////////////////////////////////*/

contract CreateIntentTest is IntentraEscrowBaseTest {
    function test_CreateIntent_Success(uint256 amount) public {
        vm.assume(amount > 0 && amount < 100_000e6);
        vm.prank(customer);
        uint256 intentId = escrow.createIntent(provider, address(usdc), amount);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(intent.customer, customer);
        assertEq(intent.provider, provider);
        assertEq(intent.token, address(usdc));
        assertEq(intent.totalAmount, amount);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.AWAITING_FUNDS));
    }

    function test_CreateIntent_RevertZeroProvider() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__ZeroAddress.selector);
        escrow.createIntent(address(0), address(usdc), AMOUNT);
    }

    function test_CreateIntent_RevertZeroToken() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__ZeroAddress.selector);
        escrow.createIntent(provider, address(0), AMOUNT);
    }

    function test_CreateIntent_RevertZeroAmount() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__ZeroAmount.selector);
        escrow.createIntent(provider, address(usdc), 0);
    }

    function test_CreateIntent_RevertCustomerEqualsProvider() public {
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__CustomerEqualsProvider.selector);
        escrow.createIntent(customer, address(usdc), AMOUNT);
    }

    function test_CreateIntent_IncrementsId() public {
        vm.startPrank(customer);
        uint256 id0 = escrow.createIntent(provider, address(usdc), AMOUNT);
        uint256 id1 = escrow.createIntent(provider, address(usdc), AMOUNT);
        vm.stopPrank();

        assertEq(id0, 0);
        assertEq(id1, 1);
        assertEq(escrow.nextIntentId(), 2);
    }
}

/*//////////////////////////////////////////////////////////////
                        FUNDING TESTS
//////////////////////////////////////////////////////////////*/

contract FundIntentTest is IntentraEscrowBaseTest {
    function test_FundIntent_Success() public {
        vm.prank(customer);
        uint256 intentId = escrow.createIntent(provider, address(usdc), AMOUNT);

        uint256 balBefore = usdc.balanceOf(customer);

        vm.prank(customer);
        escrow.fundIntent(intentId);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.FUNDED));
        assertEq(usdc.balanceOf(address(escrow)), AMOUNT);
        assertEq(usdc.balanceOf(customer), balBefore - AMOUNT);
        assertGt(intent.fundedAt, 0);
    }

    function test_FundIntent_RevertDoubleDeposit() public {
        uint256 intentId = _createAndFundIntent();

        vm.prank(customer);
        vm.expectRevert();
        escrow.fundIntent(intentId);
    }

    function test_FundIntent_RevertNonexistentIntent() public {
        vm.expectRevert(abi.encodeWithSelector(IntentraEscrow__IntentNotFound.selector, uint256(999)));
        escrow.fundIntent(999);
    }
}

/*//////////////////////////////////////////////////////////////
                        DISPUTE TESTS
//////////////////////////////////////////////////////////////*/

contract RaiseDisputeTest is IntentraEscrowBaseTest {
    function test_RaiseDispute_ByCustomer() public {
        uint256 intentId = _createAndFundIntent();

        vm.prank(customer);
        escrow.raiseDispute(intentId);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.IN_DISPUTE));
    }

    function test_RaiseDispute_ByProvider() public {
        uint256 intentId = _createAndFundIntent();

        vm.prank(provider);
        escrow.raiseDispute(intentId);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.IN_DISPUTE));
    }

    function test_RaiseDispute_RevertUnauthorized() public {
        uint256 intentId = _createAndFundIntent();

        address stranger = makeAddr("stranger");
        vm.prank(stranger);
        vm.expectRevert(IntentraEscrow__Unauthorized.selector);
        escrow.raiseDispute(intentId);
    }

    function test_RaiseDispute_RevertWrongState() public {
        vm.prank(customer);
        uint256 intentId = escrow.createIntent(provider, address(usdc), AMOUNT);

        vm.prank(customer);
        vm.expectRevert();
        escrow.raiseDispute(intentId);
    }
}

/*//////////////////////////////////////////////////////////////
                    AI PROPOSAL TESTS
//////////////////////////////////////////////////////////////*/

contract SubmitAIProposalTest is IntentraEscrowBaseTest {
    function test_SubmitAIProposal_Success() public {
        uint256 intentId = _createFundAndDispute();

        vm.prank(aiArbitrator);
        escrow.submitAIProposal(intentId, 300e6, 700e6);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.TIMELOCKED));

        IntentraEscrow.Proposal memory prop = escrow.getProposal(intentId);
        assertEq(prop.customerAmount, 300e6);
        assertEq(prop.providerAmount, 700e6);
        assertEq(prop.proposedBy, aiArbitrator);
    }

    function test_SubmitAIProposal_RevertNotAI() public {
        uint256 intentId = _createFundAndDispute();

        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__Unauthorized.selector);
        escrow.submitAIProposal(intentId, 500e6, 500e6);
    }

    function test_SubmitAIProposal_RevertAmountMismatch() public {
        uint256 intentId = _createFundAndDispute();

        vm.prank(aiArbitrator);
        vm.expectRevert(abi.encodeWithSelector(
            IntentraEscrow__AmountMismatch.selector,
            uint256(600e6),
            AMOUNT
        ));
        escrow.submitAIProposal(intentId, 200e6, 400e6);
    }
}

/*//////////////////////////////////////////////////////////////
                2-OF-3 EIP-712 SIGNATURE EXECUTION TESTS
//////////////////////////////////////////////////////////////*/

contract ExecuteWithSignaturesTest is IntentraEscrowBaseTest {
    function test_HappyPath_CustomerAndProvider() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 0, AMOUNT);

        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigProvider);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.RESOLVED));
        assertEq(usdc.balanceOf(provider), AMOUNT);
    }

    function test_HappyPath_CustomerAndAI() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigAI = _signResolveIntent(AI_PK, intentId, 0, AMOUNT);

        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigAI);

        assertEq(usdc.balanceOf(provider), AMOUNT);
    }

    function test_DisputePath_AIAndProviderAfterTimelock() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        // Warp past the 48-hour appeal window
        vm.warp(block.timestamp + 48 hours + 1);

        bytes memory sigAI = _signResolveIntent(AI_PK, intentId, 300e6, 700e6);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 300e6, 700e6);

        escrow.executeWithSignatures(intentId, 300e6, 700e6, sigAI, sigProvider);

        assertEq(usdc.balanceOf(customer), 100_000e6 - AMOUNT + 300e6);
        assertEq(usdc.balanceOf(provider), 700e6);
    }

    function test_Revert_TimelockNotExpired() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        bytes memory sigAI = _signResolveIntent(AI_PK, intentId, 300e6, 700e6);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 300e6, 700e6);

        // Don't warp — still within 48h window
        vm.expectRevert();
        escrow.executeWithSignatures(intentId, 300e6, 700e6, sigAI, sigProvider);
    }

    function test_Revert_DuplicateSigners() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sig1 = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sig2 = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);

        vm.expectRevert(IntentraEscrow__DuplicateSigners.selector);
        escrow.executeWithSignatures(intentId, 0, AMOUNT, sig1, sig2);
    }

    function test_Revert_InvalidSigner() public {
        uint256 intentId = _createAndFundIntent();
        uint256 strangePk = 0xDEAD;

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigStranger = _signResolveIntent(strangePk, intentId, 0, AMOUNT);

        vm.expectRevert(abi.encodeWithSelector(IntentraEscrow__InvalidSigner.selector, vm.addr(strangePk)));
        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigStranger);
    }

    function test_Revert_AmountMismatch() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 100e6, 100e6);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 100e6, 100e6);

        vm.expectRevert();
        escrow.executeWithSignatures(intentId, 100e6, 100e6, sigCustomer, sigProvider);
    }

    function test_Revert_WrongState_AwaitingFunds() public {
        vm.prank(customer);
        uint256 intentId = escrow.createIntent(provider, address(usdc), AMOUNT);

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 0, AMOUNT);

        vm.expectRevert();
        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigProvider);
    }

    function test_Revert_WrongState_Resolved() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sigCustomer = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigProvider = _signResolveIntent(PROVIDER_PK, intentId, 0, AMOUNT);

        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigProvider);

        // Try again on resolved
        vm.expectRevert();
        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigCustomer, sigProvider);
    }
}

/*//////////////////////////////////////////////////////////////
                    APPEAL ESCALATION TESTS
//////////////////////////////////////////////////////////////*/

contract EscalateAppealTest is IntentraEscrowBaseTest {
    function test_EscalateAppeal_Success() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.APPEALED));
        assertEq(escrow.appealStakes(intentId), APPEAL_FEE);
        assertEq(escrow.appellants(intentId), customer);
    }

    function test_EscalateAppeal_ByProvider() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(provider, 1 ether);
        vm.prank(provider);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        assertEq(escrow.appellants(intentId), provider);
    }

    function test_EscalateAppeal_RevertInsufficientStake() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        vm.expectRevert(abi.encodeWithSelector(
            IntentraEscrow__InsufficientAppealStake.selector,
            0.005 ether,
            APPEAL_FEE
        ));
        escrow.escalateAppeal{value: 0.005 ether}(intentId);
    }

    function test_EscalateAppeal_RevertWindowClosed() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        // Warp past the window
        vm.warp(block.timestamp + 48 hours);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        vm.expectRevert(IntentraEscrow__AppealWindowClosed.selector);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);
    }

    function test_EscalateAppeal_RevertUnauthorized() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);
        address stranger = makeAddr("stranger");

        vm.deal(stranger, 1 ether);
        vm.prank(stranger);
        vm.expectRevert(IntentraEscrow__Unauthorized.selector);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);
    }
}

/*//////////////////////////////////////////////////////////////
                HUMAN ORACLE RESOLUTION TESTS
//////////////////////////////////////////////////////////////*/

contract ResolveHumanAppealTest is IntentraEscrowBaseTest {
    function test_ResolveHumanAppeal_FullRefundToCustomer() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        // Customer appeals
        vm.deal(customer, 1 ether);
        vm.prank(customer);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        uint256 custBalBefore = usdc.balanceOf(customer);
        uint256 custEthBefore = customer.balance;

        // Human oracle decides: full refund to customer (customer was right)
        escrow.resolveHumanAppeal(intentId, AMOUNT, 0);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.RESOLVED));
        assertEq(usdc.balanceOf(customer), custBalBefore + AMOUNT);
        assertEq(customer.balance, custEthBefore + APPEAL_FEE); // Stake refunded
    }

    function test_ResolveHumanAppeal_PartialSplit() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(provider, 1 ether);
        vm.prank(provider);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        // Human oracle decides: 50/50 split
        escrow.resolveHumanAppeal(intentId, 500e6, 500e6);

        assertEq(usdc.balanceOf(customer), 100_000e6 - AMOUNT + 500e6);
        assertEq(usdc.balanceOf(provider), 500e6);
    }

    function test_ResolveHumanAppeal_RevertNotOwner() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        vm.prank(customer);
        vm.expectRevert();
        escrow.resolveHumanAppeal(intentId, AMOUNT, 0);
    }

    function test_ResolveHumanAppeal_RevertAmountMismatch() public {
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        vm.expectRevert();
        escrow.resolveHumanAppeal(intentId, 400e6, 400e6);
    }
}

/*//////////////////////////////////////////////////////////////
                    ABANDONMENT TIMEOUT TESTS
//////////////////////////////////////////////////////////////*/

contract ExecuteAbandonmentTest is IntentraEscrowBaseTest {
    function test_Abandonment_FundedNoProposal_RefundsCustomer() public {
        uint256 intentId = _createAndFundIntent();
        uint256 balBefore = usdc.balanceOf(customer);

        // Warp past 14 days
        vm.warp(block.timestamp + 14 days + 1);

        address anyone = makeAddr("anyone");
        vm.prank(anyone);
        escrow.executeAbandonment(intentId);

        IntentraEscrow.Intent memory intent = escrow.getIntent(intentId);
        assertEq(uint8(intent.state), uint8(IntentraEscrow.IntentState.RESOLVED));
        assertEq(usdc.balanceOf(customer), balBefore + AMOUNT);
    }

    function test_Abandonment_InDisputeNoProposal_RefundsCustomer() public {
        uint256 intentId = _createFundAndDispute();

        vm.warp(block.timestamp + 14 days + 1);

        escrow.executeAbandonment(intentId);

        assertEq(usdc.balanceOf(customer), 100_000e6);
    }

    function test_Abandonment_RevertTooEarly() public {
        uint256 intentId = _createAndFundIntent();

        vm.expectRevert();
        escrow.executeAbandonment(intentId);
    }

    function test_Abandonment_RevertWrongState_Resolved() public {
        uint256 intentId = _createAndFundIntent();

        bytes memory sigC = _signResolveIntent(CUSTOMER_PK, intentId, 0, AMOUNT);
        bytes memory sigP = _signResolveIntent(PROVIDER_PK, intentId, 0, AMOUNT);
        escrow.executeWithSignatures(intentId, 0, AMOUNT, sigC, sigP);

        vm.warp(block.timestamp + 14 days + 1);
        vm.expectRevert();
        escrow.executeAbandonment(intentId);
    }

    function test_Abandonment_RevertWrongState_AwaitingFunds() public {
        vm.prank(customer);
        uint256 intentId = escrow.createIntent(provider, address(usdc), AMOUNT);

        vm.warp(block.timestamp + 14 days + 1);
        vm.expectRevert();
        escrow.executeAbandonment(intentId);
    }
}

/*//////////////////////////////////////////////////////////////
                    INVARIANT / FUZZ TESTS
//////////////////////////////////////////////////////////////*/

contract InvariantTests is IntentraEscrowBaseTest {
    /// @notice Fuzz test: for any split amounts, customerAmount + providerAmount must equal totalAmount
    function test_Fuzz_SplitConservation(uint256 custAmt) public {
        vm.assume(custAmt <= AMOUNT);
        uint256 provAmt = AMOUNT - custAmt;

        uint256 intentId = _createAndFundIntent();

        bytes memory sigC = _signResolveIntent(CUSTOMER_PK, intentId, custAmt, provAmt);
        bytes memory sigP = _signResolveIntent(PROVIDER_PK, intentId, custAmt, provAmt);

        uint256 totalBefore = usdc.balanceOf(customer) + usdc.balanceOf(provider) + usdc.balanceOf(address(escrow));

        escrow.executeWithSignatures(intentId, custAmt, provAmt, sigC, sigP);

        uint256 totalAfter = usdc.balanceOf(customer) + usdc.balanceOf(provider) + usdc.balanceOf(address(escrow));
        assertEq(totalAfter, totalBefore, "Token conservation violated");
    }

    /// @notice Verify that resolved intents cannot be re-resolved
    function test_Fuzz_NoDoubleResolution(uint256 custAmt) public {
        vm.assume(custAmt <= AMOUNT);
        uint256 provAmt = AMOUNT - custAmt;

        uint256 intentId = _createAndFundIntent();

        bytes memory sigC = _signResolveIntent(CUSTOMER_PK, intentId, custAmt, provAmt);
        bytes memory sigP = _signResolveIntent(PROVIDER_PK, intentId, custAmt, provAmt);

        escrow.executeWithSignatures(intentId, custAmt, provAmt, sigC, sigP);

        // Second resolution must revert
        vm.expectRevert();
        escrow.executeWithSignatures(intentId, custAmt, provAmt, sigC, sigP);
    }
}

/*//////////////////////////////////////////////////////////////
                    ACCESS CONTROL TESTS
//////////////////////////////////////////////////////////////*/

contract AccessControlTest is IntentraEscrowBaseTest {
    function test_OnlyOwner_SetAppealFee() public {
        escrow.setAppealFee(0.05 ether);
        assertEq(escrow.appealFee(), 0.05 ether);

        vm.prank(customer);
        vm.expectRevert();
        escrow.setAppealFee(1 ether);
    }

    function test_OnlyOwner_WithdrawStuckStake() public {
        // Create a stuck stake scenario
        uint256 intentId = _createFundDisputeAndPropose(300e6, 700e6);

        vm.deal(customer, 1 ether);
        vm.prank(customer);
        escrow.escalateAppeal{value: APPEAL_FEE}(intentId);

        // Non-owner cannot withdraw
        vm.prank(customer);
        vm.expectRevert();
        escrow.withdrawStuckStake(intentId);
    }

    function test_Ownable2Step_TransferOwnership() public {
        address newOwner = makeAddr("newOwner");

        escrow.transferOwnership(newOwner);
        // Pending — not yet effective
        assertEq(escrow.owner(), address(this));

        vm.prank(newOwner);
        escrow.acceptOwnership();
        assertEq(escrow.owner(), newOwner);
    }
}

/*//////////////////////////////////////////////////////////////
                    CONSTRUCTOR VALIDATION TESTS
//////////////////////////////////////////////////////////////*/

contract ConstructorTest is Test {
    function test_Revert_ZeroAIArbitrator() public {
        vm.expectRevert(IntentraEscrow__ZeroAddress.selector);
        new IntentraEscrow(address(0), address(this), 0.01 ether);
    }

    function test_Revert_ZeroOwner() public {
        // OZ's Ownable reverts with OwnableInvalidOwner before our check
        vm.expectRevert(abi.encodeWithSignature("OwnableInvalidOwner(address)", address(0)));
        new IntentraEscrow(address(1), address(0), 0.01 ether);
    }
}

/*//////////////////////////////////////////////////////////////
                    EVENT EMISSION TESTS
//////////////////////////////////////////////////////////////*/

contract EventEmissionTest is IntentraEscrowBaseTest {
    function test_Emit_IntentCreated() public {
        vm.prank(customer);
        vm.expectEmit(true, true, true, true);
        emit IntentCreated(0, customer, provider, address(usdc), AMOUNT);
        escrow.createIntent(provider, address(usdc), AMOUNT);
    }

    function test_Emit_IntentFunded() public {
        vm.prank(customer);
        uint256 id = escrow.createIntent(provider, address(usdc), AMOUNT);

        vm.prank(customer);
        vm.expectEmit(true, false, false, true);
        emit IntentFunded(id, AMOUNT);
        escrow.fundIntent(id);
    }

    function test_Emit_DisputeRaised() public {
        uint256 id = _createAndFundIntent();

        vm.prank(customer);
        vm.expectEmit(true, true, false, false);
        emit DisputeRaised(id, customer);
        escrow.raiseDispute(id);
    }

    function test_Emit_AIProposalSubmitted() public {
        uint256 id = _createFundAndDispute();

        vm.prank(aiArbitrator);
        vm.expectEmit(true, false, false, true);
        emit AIProposalSubmitted(id, 300e6, 700e6);
        escrow.submitAIProposal(id, 300e6, 700e6);
    }
}

/*//////////////////////////////////////////////////////////////
            ERROR SELECTOR IMPORTS (for vm.expectRevert)
//////////////////////////////////////////////////////////////*/

// Importing file-level errors for test reverts
error IntentraEscrow__ZeroAddress();
error IntentraEscrow__ZeroAmount();
error IntentraEscrow__InvalidState(uint8 current, uint8 expected);
error IntentraEscrow__Unauthorized();
error IntentraEscrow__AmountMismatch(uint256 summed, uint256 expected);
error IntentraEscrow__DuplicateSigners();
error IntentraEscrow__InvalidSigner(address signer);
error IntentraEscrow__TimelockNotExpired(uint256 expiresAt);
error IntentraEscrow__AbandonmentNotReady(uint256 readyAt);
error IntentraEscrow__AppealWindowClosed();
error IntentraEscrow__InsufficientAppealStake(uint256 sent, uint256 required);
error IntentraEscrow__IntentNotFound(uint256 intentId);
error IntentraEscrow__CustomerEqualsProvider();
