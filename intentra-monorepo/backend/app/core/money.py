"""Money is always an integer in minor units: kobo for naira, micro-USDC (6 decimals, Arc's ERC-20 interface) for escrow amounts."""
MICRO_USDC = 10**6
BPS = 10_000


def naira_to_kobo(naira: int) -> int:
    return int(naira) * 100


def kobo_to_micro_usdc(kobo: int, rate_ngn_per_usdc: int) -> int:
    if rate_ngn_per_usdc <= 0:
        raise ValueError("rate must be positive")
    return int(kobo) * MICRO_USDC // (int(rate_ngn_per_usdc) * 100)


def micro_usdc_to_kobo(micro: int, rate_ngn_per_usdc: int) -> int:
    return int(micro) * int(rate_ngn_per_usdc) * 100 // MICRO_USDC


def split(amount_minor: int, provider_bps: int) -> tuple[int, int]:
    """Same arithmetic as the escrow: provider gets the floor, customer gets the rest, so the two always add up."""
    if not 0 <= provider_bps <= BPS:
        raise ValueError("provider_bps must be between 0 and 10,000")
    to_provider = amount_minor * provider_bps // BPS
    return to_provider, amount_minor - to_provider


def within_tolerance(requested: int, authorized: int, tolerance_bps: int) -> bool:
    """The band is inclusive: an amount exactly 10% over an authorised maximum asks for a signature, it does not block."""
    allowance = -(-int(authorized) * int(tolerance_bps) // BPS)      # ceiling, so rounding never turns ASK into BLOCK
    return requested <= authorized + allowance
