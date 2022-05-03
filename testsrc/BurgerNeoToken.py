from typing import Any, Union

from boa3.builtin import NeoMetadata, metadata, public
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop.blockchain import get_contract, Transaction
from boa3.builtin.interop.contract import call_contract, destroy_contract, update_contract
from boa3.builtin.interop.runtime import check_witness, script_container
from boa3.builtin.interop.stdlib import base64_encode
from boa3.builtin.interop.storage import get, put, get_context, get_read_only_context
from boa3.builtin.type import UInt160
from typing import cast


# -------------------------------------------
# METADATA
# -------------------------------------------

@metadata
def manifest_metadata() -> NeoMetadata:
    """
    Defines this smart contract's metadata information
    """
    meta = NeoMetadata()
    meta.supported_standards = ["NEP-17"]
    meta.author = "Bowerbird Finance"
    meta.description = "BurgerNEO Token"
    meta.email = "hello@bowerbird.finance"
    return meta

# -------------------------------------------
# SAFETY SETTINGS
# -------------------------------------------

AVIARY_SCRIPT_HASH_KEY = 'aviary'

# -------------------------------------------
# TOKEN SETTINGS
# -------------------------------------------

OWNER_KEY = 'owner'
SUPPLY_KEY = 'totalSupply'
BALANCE_KEY = 'balance/'
NUM_ACCOUNTS_KEY = 'numAccounts'

# Symbol of the Token
TOKEN_SYMBOL = 'bNEO'

# Number of decimal places
TOKEN_DECIMALS = 8
TOKEN_MULT = 100_000_000

# Initial Supply
TOKEN_INITIAL_SUPPLY = 10_000_000 * TOKEN_MULT


# -------------------------------------------
# Events
# -------------------------------------------

on_transfer = Nep17TransferEvent

# -------------------------------------------
# Methods
# -------------------------------------------


def validate_address(address: UInt160) -> bool:
    if not isinstance(address, UInt160):
        return False
    if address == 0:
        return False
    return True


@public
def symbol() -> str:
    return TOKEN_SYMBOL


@public
def decimals() -> int:
    return TOKEN_DECIMALS


@public
def setOwner(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(OWNER_KEY, hash)


@public
def getOwner() -> UInt160:
    return UInt160(get(OWNER_KEY))


@public
def totalSupply() -> int:
    return get(SUPPLY_KEY).to_int()


@public
def balanceOf(account: UInt160) -> int:
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    account64 = base64_encode(account)
    return get_read_only_context().create_map(BALANCE_KEY).get(account64).to_int()


@public
def transfer(from_address: UInt160, to_address: UInt160, amount: int, data: Any) -> bool:
    """
    Transfers an amount of NEP17 tokens from one account to another
    If the method succeeds, it must fire the `Transfer` event and must return true, even if the amount is 0,
    or from and to are the same address.

    :param from_address: the address to transfer from
    :type from_address: UInt160
    :param to_address: the address to transfer to
    :type to_address: UInt160
    :param amount: the amount of NEP17 tokens to transfer
    :type amount: int
    :param data: whatever data is pertinent to the onPayment method
    :type data: Any
    :return: whether the transfer was successful
    :raise AssertionError: raised if `from_address` or `to_address` is invalid or if `amount` is less than zero.
    """

    assert validate_address(from_address), 'from_address must be a valid 20 byte UInt160'
    assert validate_address(to_address), 'to_address must be a valid 20 byte UInt160'
    assert amount >= 0, 'transfer amount cannot be negative'

    # Keep track of any changes in the number of active accounts
    balance_map = get_context().create_map(BALANCE_KEY)

    # The function MUST return false if the from account balance does not have enough tokens to spend.
    from_address64 = base64_encode(from_address)
    from_balance = balance_map.get(from_address64).to_int()
    if from_balance < amount:
        return False

    # The function should use the check_witness to verify the transfer.
    if not check_witness(from_address):
        return False

    # skip balance changes if transferring to yourself or transferring 0 cryptocurrency
    if from_address != to_address and amount != 0:
        if from_balance == amount:
            balance_map.delete(from_address64)
        else:
            balance_map.put(from_address64, from_balance - amount)

        to_address64 = base64_encode(to_address)
        to_balance = balance_map.get(to_address64).to_int()
        balance_map.put(to_address64, to_balance + amount)

    # if the method succeeds, it must fire the transfer event
    on_transfer(from_address, to_address, amount)
    # if the to_address is a smart contract, it must call the contracts onPayment
    post_transfer(from_address, to_address, amount, data)

    return True


def post_transfer(from_address: Union[UInt160, None], to_address: Union[UInt160, None], amount: int, data: Any):
    """
    Checks if the one receiving NEP17 tokens is a smart contract and if it's one the onPayment method will be called
    :param from_address: the address of the sender
    :type from_address: UInt160
    :param to_address: the address of the receiver
    :type to_address: UInt160
    :param amount: the amount of cryptocurrency that is being sent
    :type amount: int
    :param data: any pertinent data that might validate the transaction
    :type data: Any
    """
    if not isinstance(to_address, None):    # TODO: change to 'is not None' when `is` semantic is implemented
        contract = get_contract(to_address)
        if not isinstance(contract, None):      # TODO: change to 'is not None' when `is` semantic is implemented
            call_contract(to_address, 'onNEP17Payment', [from_address, amount, data])


# -------------------------------------------
# Verification Methods
# -------------------------------------------

@public
def verify() -> bool:
    """
    When this contract address is included in the transaction signature,
    this method will be triggered as a VerificationTrigger to verify that the signature is correct.
    For example, this method needs to be called when withdrawing token from the contract.
    :return: whether the transaction signature is correct
    """
    return check_witness(getOwner())


# -------------------------------------------
# Lifecycle Methods
# -------------------------------------------

@public
def _deploy(data: Any, update: bool):
    """
    Initializes the storage when the smart contract is deployed.
    :return: whether the deploy was successful. This method must return True only during the smart contract's deploy.
    """
    if update:
        return

    tx = cast(Transaction, script_container)
    put(OWNER_KEY, tx.sender)
    put(SUPPLY_KEY, TOKEN_INITIAL_SUPPLY)
    owner64 = base64_encode(tx.sender)
    get_context().create_map(BALANCE_KEY).put(owner64, TOKEN_INITIAL_SUPPLY)
    put(NUM_ACCOUNTS_KEY, 1)
    on_transfer(None, tx.sender, TOKEN_INITIAL_SUPPLY)


@public
def update(nef_file: bytes, manifest: bytes):
    if not verify():
        abort()
    update_contract(nef_file, manifest)


@public
def destroy():
    if not verify():
        abort()
    destroy_contract()
