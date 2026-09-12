"""World RP signatures against the test vectors in World's RP-signature spec (docs.world.org, checked 11 Sep 2026)."""
from app.integrations.world import hash_to_field, rp_message, sign_request

KEY = "0x" + "ab" * 32
NONCE = bytes.fromhex("008ae1aa597fa146ebd3aa2ceddf360668dea5e526567e92b0321816a4e895bd")


def test_hash_to_field_vectors():
    assert hash_to_field(b"").hex() == "00c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a4"
    assert hash_to_field(b"test_signal").hex() == "00c1636e0a961a3045054c4d61374422c31a95846b8442f0927ad2ff1d6112ed"
    assert hash_to_field(bytes([1, 2, 3])).hex() == "00f1885eda54b7a053318cd41e2093220dab15d65381b1157a3633a83bfd5c92"
    assert hash_to_field(b"hello").hex() == "001c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36dea"


def test_message_vectors():
    assert rp_message(NONCE, 1700000000, 1700000300, None).hex() == (
        "01008ae1aa597fa146ebd3aa2ceddf360668dea5e526567e92b0321816a4e895bd000000006553f100000000006553f22c")
    assert rp_message(NONCE, 1700000000, 1700000300, "test-action").hex() == (
        "01008ae1aa597fa146ebd3aa2ceddf360668dea5e526567e92b0321816a4e895bd000000006553f100000000006553f22c"
        "00aa0ce59768ae5b1c52f07a9387f14f09f277422c0d2f8a268c7bad0c60a46a")


def test_sign_request_vectors():
    session = sign_request(KEY, None, ttl=300, now=1700000000, random_bytes=bytes(range(32)))
    assert session["nonce"] == "0x" + NONCE.hex()
    assert session["expires_at"] == 1700000300
    assert session["sig"] == ("0x14f693175773aed912852a601e9c0fd30f2afe2738d31388316232ce6f64ae9e"
                              "4edbfb19d81c4229ba9c9fca78ede4b28956b7ba4415f08d957cbc1b3bdaa4021b")
    uniqueness = sign_request(KEY, "test-action", ttl=300, now=1700000000, random_bytes=bytes(range(32)))
    assert uniqueness["sig"] == ("0x05594adb6c1495768a38d523d7d6ee6356b2c31231919198794ed022ade7d08f"
                                 "73753f83bd167067d99c9b969d28e9222315837c66af25867b041273a6d5056f1b")
