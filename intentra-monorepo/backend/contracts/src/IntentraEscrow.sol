// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IntentraEscrow
/// @notice Holds USDC for one job and pays out only as the two parties agreed. The resolver key can move the workflow
///         along (anchor evidence, open a dispute, relay a signed resolution) but can never redirect funds, change the
///         amount, or settle a dispute without both signatures.
/// @dev Amounts are the 6-decimal USDC ERC-20 interface on Arc (0x3600...0000). Never native balances.
interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

contract IntentraEscrow {
    enum Status { None, Funded, Submitted, Disputed, Released, Resolved, Refunded }

    struct Job {
        address customer;
        address provider;
        uint256 amount;
        bytes32 authorizationHash;
        uint64 disputeWindow;
        uint64 expiresAt;
        uint64 releaseAfter;
        Status status;
    }

    uint16 internal constant BPS = 10_000;
    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 internal constant RESOLUTION_TYPEHASH =
        keccak256("Resolution(bytes32 txKey,uint16 providerBps,bytes32 outcomeHash)");

    IERC20 public immutable usdc;
    address public immutable resolver;
    bytes32 public immutable domainSeparator;

    mapping(bytes32 => Job) public jobs;
    uint256 private entered = 1;

    event JobFunded(bytes32 indexed txKey, address indexed customer, address indexed provider, uint256 amount,
                    bytes32 authorizationHash, uint64 disputeWindow, uint64 expiresAt);
    event EvidenceAnchored(bytes32 indexed txKey, bytes32 evidenceHash);
    event Submitted(bytes32 indexed txKey, bytes32 deliverableHash, uint64 releaseAfter);
    event DisputeOpened(bytes32 indexed txKey, bytes32 complaintHash);
    event Released(bytes32 indexed txKey, uint256 amount);
    event Resolved(bytes32 indexed txKey, uint256 toProvider, uint256 toCustomer, bytes32 outcomeHash);
    event Refunded(bytes32 indexed txKey, uint256 amount);

    error NotResolver();
    error NotParty();
    error WrongStatus();
    error BadInput();
    error BadSignature();
    error TooEarly();
    error TransferFailed();
    error Reentrancy();

    modifier onlyResolver() {
        if (msg.sender != resolver) revert NotResolver();
        _;
    }

    modifier nonReentrant() {
        if (entered != 1) revert Reentrancy();
        entered = 2;
        _;
        entered = 1;
    }

    constructor(address usdc_, address resolver_) {
        if (usdc_ == address(0) || resolver_ == address(0)) revert BadInput();
        usdc = IERC20(usdc_);
        resolver = resolver_;
        domainSeparator = keccak256(
            abi.encode(DOMAIN_TYPEHASH, keccak256("Intentra"), keccak256("1"), block.chainid, address(this))
        );
    }

    /// @notice The customer funds the job. The escrow keys on txKey, which the backend generates from 32 random bytes.
    function fund(bytes32 txKey, address provider, uint256 amount, bytes32 authorizationHash, uint64 disputeWindow,
                  uint64 expiresAt) external nonReentrant {
        Job storage job = jobs[txKey];
        if (job.status != Status.None) revert WrongStatus();
        if (txKey == bytes32(0) || provider == address(0) || provider == msg.sender || amount == 0) revert BadInput();
        if (expiresAt <= block.timestamp || disputeWindow == 0) revert BadInput();
        job.customer = msg.sender;
        job.provider = provider;
        job.amount = amount;
        job.authorizationHash = authorizationHash;
        job.disputeWindow = disputeWindow;
        job.expiresAt = expiresAt;
        job.status = Status.Funded;
        _pull(msg.sender, amount);
        emit JobFunded(txKey, msg.sender, provider, amount, authorizationHash, disputeWindow, expiresAt);
    }

    /// @notice Publishes an evidence hash. It proves when a photo existed; it never moves money.
    function anchorEvidence(bytes32 txKey, bytes32 evidenceHash) external onlyResolver {
        Status status = jobs[txKey].status;
        if (status != Status.Funded && status != Status.Submitted && status != Status.Disputed) revert WrongStatus();
        emit EvidenceAnchored(txKey, evidenceHash);
    }

    /// @notice The provider marks the work delivered. This is what starts the dispute window.
    function submit(bytes32 txKey, bytes32 deliverableHash) external {
        Job storage job = jobs[txKey];
        if (job.status != Status.Funded) revert WrongStatus();
        if (msg.sender != job.provider) revert NotParty();
        // casting to 'uint64' is safe: block.timestamp does not exceed uint64 until the year 2106
        // forge-lint: disable-next-line(unsafe-typecast)
        job.releaseAfter = uint64(block.timestamp) + job.disputeWindow;
        job.status = Status.Submitted;
        emit Submitted(txKey, deliverableHash, job.releaseAfter);
    }

    /// @notice The customer may release at any time; anyone may release once the window has closed.
    function release(bytes32 txKey) external nonReentrant {
        Job storage job = jobs[txKey];
        if (job.status != Status.Funded && job.status != Status.Submitted) revert WrongStatus();
        if (msg.sender != job.customer) {
            if (job.status != Status.Submitted) revert NotParty();
            if (block.timestamp < job.releaseAfter) revert TooEarly();
        }
        uint256 amount = job.amount;
        job.status = Status.Released;
        _pay(job.provider, amount);
        emit Released(txKey, amount);
    }

    /// @notice Freezes the money. While a job is disputed, release() reverts.
    function openDispute(bytes32 txKey, bytes32 complaintHash) external {
        Job storage job = jobs[txKey];
        if (job.status != Status.Funded && job.status != Status.Submitted) revert WrongStatus();
        if (msg.sender != job.customer && msg.sender != resolver) revert NotParty();
        job.status = Status.Disputed;
        emit DisputeOpened(txKey, complaintHash);
    }

    /// @notice Settles a dispute. The resolver only relays: the contract checks both parties' EIP-712 signatures,
    ///         so a leaked resolver key still cannot settle alone.
    function resolve(bytes32 txKey, uint16 providerBps, bytes32 outcomeHash, bytes calldata sigCustomer,
                     bytes calldata sigProvider) external nonReentrant onlyResolver {
        Job storage job = jobs[txKey];
        if (job.status != Status.Disputed) revert WrongStatus();
        if (providerBps > BPS) revert BadInput();
        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01", domainSeparator, keccak256(abi.encode(RESOLUTION_TYPEHASH, txKey, providerBps, outcomeHash))
        ));
        if (_recover(digest, sigCustomer) != job.customer) revert BadSignature();
        if (_recover(digest, sigProvider) != job.provider) revert BadSignature();
        uint256 toProvider = (job.amount * providerBps) / BPS;
        uint256 toCustomer = job.amount - toProvider;
        job.status = Status.Resolved;
        if (toProvider > 0) _pay(job.provider, toProvider);
        if (toCustomer > 0) _pay(job.customer, toCustomer);
        emit Resolved(txKey, toProvider, toCustomer, outcomeHash);
    }

    /// @notice No-show path: if nothing was ever submitted by the deadline, anyone can return the money to the customer.
    function claimRefund(bytes32 txKey) external nonReentrant {
        Job storage job = jobs[txKey];
        if (job.status != Status.Funded) revert WrongStatus();
        if (block.timestamp < job.expiresAt) revert TooEarly();
        uint256 amount = job.amount;
        job.status = Status.Refunded;
        _pay(job.customer, amount);
        emit Refunded(txKey, amount);
    }

    function getJob(bytes32 txKey) external view returns (Job memory) {
        return jobs[txKey];
    }

    function _pull(address from, uint256 amount) private {
        (bool ok, bytes memory data) = address(usdc).call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, address(this), amount));
        if (!ok || (data.length != 0 && !abi.decode(data, (bool)))) revert TransferFailed();
    }

    function _pay(address to, uint256 amount) private {
        (bool ok, bytes memory data) = address(usdc).call(abi.encodeWithSelector(IERC20.transfer.selector, to, amount));
        if (!ok || (data.length != 0 && !abi.decode(data, (bool)))) revert TransferFailed();
    }

    function _recover(bytes32 digest, bytes calldata signature) private pure returns (address) {
        if (signature.length != 65) revert BadSignature();
        bytes32 r = bytes32(signature[0:32]);
        bytes32 s = bytes32(signature[32:64]);
        uint8 v = uint8(signature[64]);
        if (uint256(s) > 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0) revert BadSignature();
        if (v < 27) v += 27;
        if (v != 27 && v != 28) revert BadSignature();
        address signer = ecrecover(digest, v, r, s);
        if (signer == address(0)) revert BadSignature();
        return signer;
    }
}
