// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import {IERC20} from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "openzeppelin-contracts/contracts/token/ERC20/utils/SafeERC20.sol";
import {EIP712} from "openzeppelin-contracts/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "openzeppelin-contracts/contracts/utils/cryptography/ECDSA.sol";
import {ReentrancyGuard} from "openzeppelin-contracts/contracts/utils/ReentrancyGuard.sol";
import {Ownable2Step, Ownable} from "openzeppelin-contracts/contracts/access/Ownable2Step.sol";

/*//////////////////////////////////////////////////////////////
                              EVENTS
//////////////////////////////////////////////////////////////*/

event IntentCreated(
    uint256 indexed intentId,
    address indexed customer,
    address indexed provider,
    address token,
    uint256 amount
);
event IntentFunded(uint256 indexed intentId, uint256 amount);
event DisputeRaised(uint256 indexed intentId, address indexed raisedBy);
event AIProposalSubmitted(
    uint256 indexed intentId,
    uint256 customerAmount,
    uint256 providerAmount
);
event AppealEscalated(uint256 indexed intentId, address indexed appellant, uint256 stake);
event IntentResolved(
    uint256 indexed intentId,
    uint256 customerAmount,
    uint256 providerAmount
);
event AbandonmentExecuted(uint256 indexed intentId, address indexed triggeredBy);

/*//////////////////////////////////////////////////////////////
                              ERRORS
//////////////////////////////////////////////////////////////*/

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

/**
 * @title IntentraEscrow
 * @author Intentra (ETHOnline 2026)
 * @notice Singleton escrow registry for the Intentra AI marketplace.
 *         Manages ERC-20 (USDC) escrows with a 2-of-3 multisig release,
 *         AI-arbitrated dispute resolution, appeal escalation, and
 *         abandonment timeouts.
 * @dev    Follows Cyfrin/solskill standards: strict pragma, named imports,
 *         custom errors, CEI pattern, ReentrancyGuard, Ownable2Step, EIP-712.
 * @custom:security-contact security@intentra.io
 */
contract IntentraEscrow is EIP712, ReentrancyGuard, Ownable2Step {
    using SafeERC20 for IERC20;

    /*//////////////////////////////////////////////////////////////
                            TYPE DECLARATIONS
    //////////////////////////////////////////////////////////////*/

    enum IntentState {
        AWAITING_FUNDS, // 0
        FUNDED,         // 1
        IN_DISPUTE,     // 2
        TIMELOCKED,     // 3
        APPEALED,       // 4
        RESOLVED        // 5
    }

    struct Proposal {
        uint256 customerAmount;
        uint256 providerAmount;
        uint256 proposedAt;
        address proposedBy;
    }

    struct Intent {
        uint256 id;
        address customer;
        address provider;
        address token;
        uint256 totalAmount;
        IntentState state;
        uint256 fundedAt;
        uint256 lastActivityAt;
        Proposal activeProposal;
    }

    /*//////////////////////////////////////////////////////////////
                            STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    /// @notice The backend-controlled AI Arbitrator wallet (one of the 3 multisig keys).
    address public immutable aiArbitrator;

    /// @notice Auto-incrementing intent counter.
    uint256 public nextIntentId;

    /// @notice Core intent registry. intentId => Intent
    mapping(uint256 => Intent) internal s_intents;

    /// @notice Appeal stakes held per intent. intentId => staked ETH amount
    mapping(uint256 => uint256) public appealStakes;

    /// @notice Who filed the appeal. intentId => appellant address
    mapping(uint256 => address) public appellants;

    /// @notice Configurable appeal fee (in native ETH/gas token). Default: 0.01 ether.
    uint256 public appealFee;

    /*//////////////////////////////////////////////////////////////
                              CONSTANTS
    //////////////////////////////////////////////////////////////*/

    uint256 public constant ABANDONMENT_TIMEOUT = 14 days;
    uint256 public constant APPEAL_TIMELOCK = 48 hours;

    /// @dev EIP-712 typehash for the ResolveIntent struct.
    bytes32 public constant RESOLVE_INTENT_TYPEHASH = keccak256(
        "ResolveIntent(uint256 intentId,uint256 customerAmount,uint256 providerAmount)"
    );

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /**
     * @param _aiArbitrator The address of the AI Arbitrator multisig key.
     * @param _owner        The Human Oracle / admin multisig (Ownable2Step).
     * @param _appealFee    Initial appeal stake requirement in native currency.
     */
    constructor(
        address _aiArbitrator,
        address _owner,
        uint256 _appealFee
    ) EIP712("IntentraEscrow", "1") Ownable(_owner) {
        if (_aiArbitrator == address(0)) revert IntentraEscrow__ZeroAddress();
        if (_owner == address(0)) revert IntentraEscrow__ZeroAddress();

        aiArbitrator = _aiArbitrator;
        appealFee = _appealFee;
    }

    /*//////////////////////////////////////////////////////////////
                    USER-FACING STATE-CHANGING FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Creates a new intent between a customer and a provider.
     * @param provider The address of the service provider.
     * @param token    The ERC-20 token address (USDC).
     * @param amount   The total escrow amount (6-decimal USDC).
     * @return intentId The newly created intent's ID.
     */
    function createIntent(
        address provider,
        address token,
        uint256 amount
    ) external returns (uint256 intentId) {
        if (provider == address(0) || token == address(0)) revert IntentraEscrow__ZeroAddress();
        if (amount == 0) revert IntentraEscrow__ZeroAmount();
        if (provider == msg.sender) revert IntentraEscrow__CustomerEqualsProvider();

        intentId = nextIntentId++;

        Intent storage intent = s_intents[intentId];
        intent.id = intentId;
        intent.customer = msg.sender;
        intent.provider = provider;
        intent.token = token;
        intent.totalAmount = amount;
        // state defaults to AWAITING_FUNDS (0)
        intent.lastActivityAt = block.timestamp;

        emit IntentCreated(intentId, msg.sender, provider, token, amount);
    }

    /**
     * @notice Deposits the full escrow amount. Must be called by the customer
     *         after approving this contract to spend their tokens.
     * @param intentId The intent to fund.
     */
    function fundIntent(uint256 intentId) external nonReentrant {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);
        _requireState(intent, IntentState.AWAITING_FUNDS);

        // Effects
        intent.state = IntentState.FUNDED;
        intent.fundedAt = block.timestamp;
        intent.lastActivityAt = block.timestamp;

        // Interactions
        IERC20(intent.token).safeTransferFrom(intent.customer, address(this), intent.totalAmount);

        emit IntentFunded(intentId, intent.totalAmount);
    }

    /**
     * @notice Raises a dispute. Only customer or provider, only when FUNDED.
     * @param intentId The intent to dispute.
     */
    function raiseDispute(uint256 intentId) external {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);
        _requireState(intent, IntentState.FUNDED);
        _requireParty(intent);

        intent.state = IntentState.IN_DISPUTE;
        intent.lastActivityAt = block.timestamp;

        emit DisputeRaised(intentId, msg.sender);
    }

    /**
     * @notice AI Arbitrator submits a proposed fund split. Moves to TIMELOCKED.
     * @param intentId        The disputed intent.
     * @param customerAmount  Amount to return to customer.
     * @param providerAmount  Amount to pay provider.
     */
    function submitAIProposal(
        uint256 intentId,
        uint256 customerAmount,
        uint256 providerAmount
    ) external {
        if (msg.sender != aiArbitrator) revert IntentraEscrow__Unauthorized();

        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);
        _requireState(intent, IntentState.IN_DISPUTE);
        _requireAmountMatch(customerAmount, providerAmount, intent.totalAmount);

        intent.activeProposal = Proposal({
            customerAmount: customerAmount,
            providerAmount: providerAmount,
            proposedAt: block.timestamp,
            proposedBy: msg.sender
        });
        intent.state = IntentState.TIMELOCKED;
        intent.lastActivityAt = block.timestamp;

        emit AIProposalSubmitted(intentId, customerAmount, providerAmount);
    }

    /**
     * @notice 2-of-3 EIP-712 off-chain multisig execution.
     *         Requires two distinct valid signatures from {customer, provider, aiArbitrator}.
     *         If TIMELOCKED, the 48-hour appeal window must have passed.
     * @param intentId        The intent to resolve.
     * @param customerAmount  Amount to the customer.
     * @param providerAmount  Amount to the provider.
     * @param sigA            First EIP-712 signature.
     * @param sigB            Second EIP-712 signature.
     */
    function executeWithSignatures(
        uint256 intentId,
        uint256 customerAmount,
        uint256 providerAmount,
        bytes calldata sigA,
        bytes calldata sigB
    ) external nonReentrant {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);

        // Must be in FUNDED (happy path) or TIMELOCKED (AI path, post-48h)
        IntentState currentState = intent.state;
        if (currentState != IntentState.FUNDED && currentState != IntentState.TIMELOCKED) {
            revert IntentraEscrow__InvalidState(uint8(currentState), uint8(IntentState.FUNDED));
        }

        // If TIMELOCKED, enforce the 48-hour appeal window
        if (currentState == IntentState.TIMELOCKED) {
            uint256 expiresAt = intent.activeProposal.proposedAt + APPEAL_TIMELOCK;
            if (block.timestamp < expiresAt) {
                revert IntentraEscrow__TimelockNotExpired(expiresAt);
            }
        }

        _requireAmountMatch(customerAmount, providerAmount, intent.totalAmount);

        // Recover signers from EIP-712 typed data
        bytes32 structHash = keccak256(
            abi.encode(RESOLVE_INTENT_TYPEHASH, intentId, customerAmount, providerAmount)
        );
        bytes32 digest = _hashTypedDataV4(structHash);

        address signerA = ECDSA.recover(digest, sigA);
        address signerB = ECDSA.recover(digest, sigB);

        if (signerA == signerB) revert IntentraEscrow__DuplicateSigners();
        if (!_isValidSigner(intent, signerA)) revert IntentraEscrow__InvalidSigner(signerA);
        if (!_isValidSigner(intent, signerB)) revert IntentraEscrow__InvalidSigner(signerB);

        _executeSplit(intent, intentId, customerAmount, providerAmount);
    }

    /**
     * @notice Escalates an AI proposal during the 48-hour appeal window.
     *         Freezes the intent indefinitely for Human Oracle review.
     *         Requires a stake (appealFee) to prevent griefing.
     * @param intentId The timelocked intent to appeal.
     */
    function escalateAppeal(uint256 intentId) external payable {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);
        _requireState(intent, IntentState.TIMELOCKED);
        _requireParty(intent);

        // Appeal must be within the 48-hour window
        uint256 windowEnd = intent.activeProposal.proposedAt + APPEAL_TIMELOCK;
        if (block.timestamp >= windowEnd) revert IntentraEscrow__AppealWindowClosed();

        // Validate appeal stake
        if (msg.value < appealFee) {
            revert IntentraEscrow__InsufficientAppealStake(msg.value, appealFee);
        }

        // Effects
        intent.state = IntentState.APPEALED;
        intent.lastActivityAt = block.timestamp;
        appealStakes[intentId] = msg.value;
        appellants[intentId] = msg.sender;

        emit AppealEscalated(intentId, msg.sender, msg.value);
    }

    /**
     * @notice Human Oracle (owner) resolves an appealed intent.
     *         Distributes the escrowed tokens and refunds the appeal stake
     *         to the winning party (whoever's share is larger or equal).
     * @param intentId        The appealed intent.
     * @param customerAmount  Final amount to the customer.
     * @param providerAmount  Final amount to the provider.
     */
    function resolveHumanAppeal(
        uint256 intentId,
        uint256 customerAmount,
        uint256 providerAmount
    ) external onlyOwner nonReentrant {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);
        _requireState(intent, IntentState.APPEALED);
        _requireAmountMatch(customerAmount, providerAmount, intent.totalAmount);

        // Determine who gets the appeal stake refund.
        // The appellant (who disagreed with AI) is "right" if the Human Oracle
        // gave them a better deal than the AI proposed.
        uint256 stake = appealStakes[intentId];
        address appellant = appellants[intentId];

        // Effects — set state first (CEI)
        intent.state = IntentState.RESOLVED;
        intent.lastActivityAt = block.timestamp;
        appealStakes[intentId] = 0;

        // Interactions — distribute escrowed tokens
        IERC20 token = IERC20(intent.token);
        if (customerAmount > 0) {
            token.safeTransfer(intent.customer, customerAmount);
        }
        if (providerAmount > 0) {
            token.safeTransfer(intent.provider, providerAmount);
        }

        // Refund the appeal stake to the appellant
        if (stake > 0 && appellant != address(0)) {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success,) = appellant.call{value: stake}("");
            // If refund fails, don't revert — the owner can withdraw later.
            // This prevents a malicious appellant from blocking resolution.
            if (!success) {
                // Re-store for later withdrawal rather than losing funds
                appealStakes[intentId] = stake;
            }
        }

        emit IntentResolved(intentId, customerAmount, providerAmount);
    }

    /**
     * @notice Triggers the 14-day abandonment safety valve.
     *         Callable by anyone. If an active AI proposal exists it is executed.
     *         Otherwise, full refund to customer.
     * @param intentId The abandoned intent.
     */
    function executeAbandonment(uint256 intentId) external nonReentrant {
        Intent storage intent = s_intents[intentId];
        _requireIntentExists(intent, intentId);

        IntentState currentState = intent.state;

        // Only FUNDED or IN_DISPUTE are eligible for abandonment
        if (currentState != IntentState.FUNDED && currentState != IntentState.IN_DISPUTE) {
            revert IntentraEscrow__InvalidState(uint8(currentState), uint8(IntentState.FUNDED));
        }

        uint256 readyAt = intent.lastActivityAt + ABANDONMENT_TIMEOUT;
        if (block.timestamp < readyAt) {
            revert IntentraEscrow__AbandonmentNotReady(readyAt);
        }

        // Check if there's an active proposal (possible if AI submitted but
        // state was manually IN_DISPUTE — defensive check)
        Proposal storage proposal = intent.activeProposal;
        if (proposal.proposedBy != address(0)) {
            // Execute the AI proposal as final
            _executeSplit(intent, intentId, proposal.customerAmount, proposal.providerAmount);
        } else {
            // No proposal — full refund to customer
            _executeSplit(intent, intentId, intent.totalAmount, 0);
        }

        emit AbandonmentExecuted(intentId, msg.sender);
    }

    /*//////////////////////////////////////////////////////////////
                        OWNER-ONLY ADMIN FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Updates the appeal fee. Only callable by Human Oracle (owner).
     * @param newFee The new appeal fee in native currency.
     */
    function setAppealFee(uint256 newFee) external onlyOwner {
        appealFee = newFee;
    }

    /**
     * @notice Emergency withdrawal of stuck appeal stakes.
     *         Only callable by owner for failed refunds.
     * @param intentId The intent with a stuck stake.
     */
    function withdrawStuckStake(uint256 intentId) external onlyOwner {
        uint256 stake = appealStakes[intentId];
        if (stake == 0) revert IntentraEscrow__ZeroAmount();

        appealStakes[intentId] = 0;

        // solhint-disable-next-line avoid-low-level-calls
        (bool success,) = msg.sender.call{value: stake}("");
        if (!success) revert IntentraEscrow__ZeroAmount();
    }

    /*//////////////////////////////////////////////////////////////
                        USER-FACING READ FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Returns the full Intent struct for a given ID.
     * @param intentId The intent to query.
     */
    function getIntent(uint256 intentId) external view returns (Intent memory) {
        return s_intents[intentId];
    }

    /**
     * @notice Returns the active proposal for an intent.
     * @param intentId The intent to query.
     */
    function getProposal(uint256 intentId) external view returns (Proposal memory) {
        return s_intents[intentId].activeProposal;
    }

    /**
     * @notice Returns the EIP-712 domain separator for frontend signing.
     */
    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }

    /*//////////////////////////////////////////////////////////////
                    INTERNAL STATE-CHANGING FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @dev Executes a fund split and transitions to RESOLVED.
     *      Follows CEI pattern: effects before interactions.
     */
    function _executeSplit(
        Intent storage intent,
        uint256 intentId,
        uint256 customerAmount,
        uint256 providerAmount
    ) internal {
        // Effects
        intent.state = IntentState.RESOLVED;
        intent.lastActivityAt = block.timestamp;

        // Interactions
        IERC20 token = IERC20(intent.token);
        if (customerAmount > 0) {
            token.safeTransfer(intent.customer, customerAmount);
        }
        if (providerAmount > 0) {
            token.safeTransfer(intent.provider, providerAmount);
        }

        emit IntentResolved(intentId, customerAmount, providerAmount);
    }

    /*//////////////////////////////////////////////////////////////
                        INTERNAL VIEW FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function _isValidSigner(Intent storage intent, address signer) internal view returns (bool) {
        return signer == intent.customer || signer == intent.provider || signer == aiArbitrator;
    }

    function _requireState(Intent storage intent, IntentState expected) internal view {
        if (intent.state != expected) {
            revert IntentraEscrow__InvalidState(uint8(intent.state), uint8(expected));
        }
    }

    function _requireParty(Intent storage intent) internal view {
        if (msg.sender != intent.customer && msg.sender != intent.provider) {
            revert IntentraEscrow__Unauthorized();
        }
    }

    function _requireAmountMatch(
        uint256 customerAmount,
        uint256 providerAmount,
        uint256 totalAmount
    ) internal pure {
        uint256 sum = customerAmount + providerAmount;
        if (sum != totalAmount) {
            revert IntentraEscrow__AmountMismatch(sum, totalAmount);
        }
    }

    function _requireIntentExists(Intent storage intent, uint256 intentId) internal view {
        // An intent that was never created has customer == address(0)
        if (intent.customer == address(0)) {
            revert IntentraEscrow__IntentNotFound(intentId);
        }
    }
}
