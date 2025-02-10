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
    """
    An Encrypted Multi-Map (EMM) engine that allows secure indexing and searching
    while preserving confidentiality.

    This class provides mechanisms for securely constructing an encrypted index,
    generating trapdoors for queries, and resolving search results.
    """

    def __init__(self, dimension_bits: List[int], dimensions: int):
        """
        Initializes the EMM engine with the specified dimensionality.

        :param dimension_bits: A list representing the bit-length of each dimension.
        :param dimensions: The total number of dimensions.
        :raises ValueError: If the specified bit lengths do not match the number of dimensions.
        """
        self.DIMENSIONS_BITS = dimension_bits
        self.dimensions = dimensions

        if len(dimension_bits) != dimensions:
            raise ValueError("Specified dimensions bits do to not correspond to the number of dimensions")

    def setup(self, security_parameter: int) -> bytes:
        """
        Generates a cryptographic key with a specified security parameter.

        :param security_parameter: The bit length of the secure key.
        :return: A securely generated random key.
        """
        return SecureRandom(security_parameter)

    def build_index(self, key: bytes, plaintext_mm: Dict[bytes, List[bytes]]) -> Dict[bytes, bytes]:
        """
        Constructs an encrypted index from the given plaintext multi-map.

        :param key: The secret key for encryption and authentication.
        :param plaintext_mm: A dictionary mapping labels to lists of plaintext values.
        :return: A dictionary representing the encrypted index.
        """
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
        """
        Generates a trapdoor (secure search token) for a given label.

        :param key: The secret key used for generating the trapdoor.
        :param label: The plaintext label for which the trapdoor is generated.
        :return: A secure token that can be used for searching.
        """
        hmac_key = HashKDF(key, PURPOSE_HMAC)
        return HMAC(hmac_key, label)

    def search(self, search_token: bytes, encrypted_db: Dict[bytes, bytes]) -> Set[bytes]:
        """
        Searches for encrypted values corresponding to a given search token.

        :param search_token: The trapdoor token generated from a label.
        :param encrypted_db: The encrypted index to search in.
        :return: A set of encrypted values matching the search token.
        """
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
        """
        Decrypts search results using the provided key.

        :param key: The secret key used for decryption.
        :param results: A set of encrypted values retrieved from the index.
        :return: A set of decrypted plaintext values.
        """
        enc_key = HashKDF(key, PURPOSE_ENCRYPT)
        pt_values = set()
        for ct_value in results:
            pt_values.add(SymmetricDecrypt(enc_key, ct_value))
        return pt_values