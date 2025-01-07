from ers.util.crypto.crypto import (
    SecureRandom,
    HashKDF,
    HMAC,
    Hash,
    SymmetricEncrypt,
    SymmetricDecrypt,
)

from typing import List, Dict, Set
from tqdm import tqdm

PURPOSE_HMAC = "hmac"
PURPOSE_ENCRYPT = "encryption"

DO_NOT_ENCRYPT = False


class EMMEngine:
    def __init__(self, dimension_bits: List[int], dimensions: int):
        self.DIMENSIONS_BITS = dimension_bits
        self.dimensions = dimensions

        if len(dimension_bits) != dimensions:
            raise ValueError("Specified dimensions bits do to not correspond to the number of dimensions")

    def setup(self, security_parameter: int) -> bytes:
        return SecureRandom(security_parameter)

    def build_index(self, key: bytes, plaintext_mm: Dict[bytes, List[bytes]]) -> Dict[bytes, bytes]:
        hmac_key = HashKDF(key, PURPOSE_HMAC)
        enc_key = HashKDF(key, PURPOSE_ENCRYPT)

        encrypted_db = {}
        for label, values in tqdm(plaintext_mm.items()):
            token = HMAC(hmac_key, label)
            for index, value in enumerate(values):
                ct_label = Hash(token + bytes(index))
                ct_value = SymmetricEncrypt(enc_key, value)
                encrypted_db[ct_label] = ct_value
        return encrypted_db

    def trapdoor(self, key: bytes, label: bytes) -> bytes:
        hmac_key = HashKDF(key, PURPOSE_HMAC)
        return HMAC(hmac_key, label)

    def search(self, search_token: bytes, encrypted_db: dict[bytes, bytes]) -> Set[bytes]:
        results = set()

        index = 0
        while True:
            ct_label = Hash(search_token + bytes(index))
            if ct_label in encrypted_db:
                data = encrypted_db[ct_label]
                results.add(data)
            else:
                break
            index += 1

        return results

    def resolve(self, key: bytes, results: Set[bytes]) -> Set[bytes]:
        enc_key = HashKDF(key, PURPOSE_ENCRYPT)
        pt_values = set()

        for ct_value in results:
            pt_values.add(SymmetricDecrypt(enc_key, ct_value))

        return pt_values
