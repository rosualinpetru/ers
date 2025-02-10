from .emm_engine import EMMEngine

from typing import Set


class EMM:
    """
    A wrapper class for the EMMEngine, providing a simplified interface for secure setup
    and search result resolution.
    """

    def __init__(self, emm_engine: EMMEngine):
        """
        Initializes the EMM instance with an underlying EMMEngine.

        :param emm_engine: An instance of EMMEngine that handles secure indexing and search.
        """
        self.emm_engine = emm_engine
        self.dimensions = emm_engine.dimensions

    def setup(self, security_parameter: int) -> bytes:
        """
        Generates a cryptographic key with a specified security parameter.

        :param security_parameter: The bit length of the secure key.
        :return: A securely generated random key.
        """
        return self.emm_engine.setup(security_parameter)

    def resolve(self, key: bytes, results: Set[bytes]) -> Set[bytes]:
        """
        Decrypts search results using the provided key.

        :param key: The secret key used for decryption.
        :param results: A set of encrypted values retrieved from the index.
        :return: A set of decrypted plaintext values.
        """
        return self.emm_engine.resolve(key, results)