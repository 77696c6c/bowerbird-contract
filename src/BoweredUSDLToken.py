from typing import Any, List, Union

from boa3.builtin import CreateNewEvent, NeoMetadata, metadata, public
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop.blockchain import current_index, get_contract, Transaction
from boa3.builtin.interop.contract import call_contract, destroy_contract, update_contract
from boa3.builtin.interop.runtime import calling_script_hash, check_witness, script_container, executing_script_hash
from boa3.builtin.interop.stdlib import base64_encode, base64_decode, itoa
from boa3.builtin.interop.storage import find, get, put, get_context, get_read_only_context
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
    meta.description = "Bowered USDL"
    meta.email = "hello@bowerbird.finance"
    return meta


# -------------------------------------------
# SAFETY SETTINGS
# -------------------------------------------

NEST_SCRIPT_HASH_KEY = 'nest'

# -------------------------------------------
# TOKEN SETTINGS
# -------------------------------------------

OWNER_KEY = 'or'
SUPPLY_KEY = 'ts'
BALANCE_KEY = 'bl/'
LOAN_KEY = 'ln/'
MINTED_KEY = 'mt'
BURNED_KEY = 'bn'
NUM_ACCOUNTS_KEY = 'na'
UNDERLYING_SCRIPT_HASH_KEY = 'uh'
UNDERLYING_SUPPLY_KEY = 'us'
LOANED_SUPPLY_KEY = 'ls'

# Symbol of the Token
TOKEN_SYMBOL = 'bUSDL'

# Number of decimal places
TOKEN_DECIMALS = 8
TOKEN_MULT = 100_000_000
# The multiplier applied to the BUSDL_USDL exchange rate
# 100_000_000 means that 1 BUSDL == 1 USDL
EXCHANGE_RATE_MULT = 100_000_000
# For high-precision operations, 
# we apply the following multiplier
# For example, 2_500_000_000_000_000_000 means 2.5
FLOAT_MULTIPLIER = 1_000_000_000_000_000_000
# Interest rate is expressed in basis points
BASIS_POINTS = 10000

# 4 blocks per minute
BLOCKS_PER_YEAR = 4 * 60 * 24 * 365

# Initial Supply
TOKEN_INITIAL_SUPPLY = 0 * TOKEN_MULT

# Actions
ACTION_MINT = 'ACTION_MINT'
ACTION_DEPOSIT = 'ACTION_DEPOSIT'
ACTION_REDEEM = 'ACTION_REDEEM'
ACTION_REPAYMENT = 'ACTION_REPAYMENT'

# The exchange rate between lended assets and their
# yield-earning counterparts
# (1 UNDERLYING_ASSET) = EXCHANGE_RATE * (1 B_ASSET)
EXCHANGE_RATE_KEY = 'er'
# Initially, 1 BUSDL == 1 USDL
INITIAL_EXCHANGE_RATE = EXCHANGE_RATE_MULT
# Current loaned supply increases by increasing this multplier
# scaled down by FLOAT_MULTIPLIER
INTEREST_MULTIPLIER_KEY = 'im'
INITIAL_INTEREST_MULTIPLIER = FLOAT_MULTIPLIER

# The last height at which point the exchange rate
# for a B-asset was updated
LAST_HEIGHT_KEY = 'lh'


# -------------------------------------------
# Events
# -------------------------------------------

on_transfer = Nep17TransferEvent

on_deposit = CreateNewEvent(
    [
        ('account', UInt160),
        ('underlying_quantity', int),
        ('b_asset_quantity', int),
    ],
    'Deposit'
)

on_deposit_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('underlying_quantity', int),
        ('b_asset_quantity', int),
        ('failure_reason', str),
    ],
    'DepositFailure'
)

on_redeem = CreateNewEvent(
    [
        ('account', UInt160),
        ('underlying_quantity', int),
        ('b_asset_quantity', int),
    ],
    'Redeem'
)

on_redeem_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('underlying_quantity', int),
        ('b_asset_quantity', int),
        ('failure_reason', str),
    ],
    'RedeemFailure'
)

on_loan = CreateNewEvent(
    [
        ('account', UInt160),
        ('loan_quantity', int),
    ],
    'Loan'
)

on_loan_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('loan_quantity', int),
        ('failure_reason', str),
    ],
    'LoanFailure'
)

on_repayment = CreateNewEvent(
    [
        ('account', UInt160),
        ('repayment_quantity', int),
    ],
    'Repayment'
)

on_repayment_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('repayment_quantity', int),
        ('failure_reason', str),
    ],
    'RepaymentFailure'
)
    

# -------------------------------------------
# Methods
# -------------------------------------------


def validate_address(address: UInt160) -> bool:
    if not isinstance(address, UInt160):
        return False
    if address == 0:
        return False
    return True


# This takes a FLOAT quantity and returns an INT quantity
def getScaledQuantity(quantity: int) -> int:
    interest_multiplier = getInterestMultiplier()
    return (quantity * interest_multiplier) // (FLOAT_MULTIPLIER * FLOAT_MULTIPLIER)


# This takes an INT quantity and returns FLOAT quantity
def getUnscaledQuantity(quantity: int) -> int:
    interest_multiplier = getInterestMultiplier()
    return (quantity * FLOAT_MULTIPLIER * FLOAT_MULTIPLIER) // interest_multiplier


@public
def getUnderlyingScriptHash() -> UInt160:
    return UInt160(get(UNDERLYING_SCRIPT_HASH_KEY))


@public
def setUnderlyingScriptHash(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(UNDERLYING_SCRIPT_HASH_KEY, hash)


@public
def getNestScriptHash() -> UInt160:
    return UInt160(get(NEST_SCRIPT_HASH_KEY))


@public
def setNestScriptHash(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(NEST_SCRIPT_HASH_KEY, hash)


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
def getUnderlyingSupply() -> int:
    return get(UNDERLYING_SUPPLY_KEY).to_int()


def updateUnderlyingSupply(quantity: int):
    put(UNDERLYING_SUPPLY_KEY, getUnderlyingSupply() + quantity)


@public
def getInterestMultiplier() -> int:
    unscaled_interest_multiplier = get(INTEREST_MULTIPLIER_KEY).to_int()
    last_height = getLastHeight()
    new_height = current_index
    diff_height = new_height - last_height
    annual_rate = getR0()
    interest_accrued = (FLOAT_MULTIPLIER * diff_height * annual_rate) // (BLOCKS_PER_YEAR * BASIS_POINTS)
    return ((FLOAT_MULTIPLIER + interest_accrued) * unscaled_interest_multiplier) // FLOAT_MULTIPLIER


def setInterestMultiplier(interest_multiplier: int):
    put(INTEREST_MULTIPLIER_KEY, interest_multiplier)


@public
def getLoanedSupply() -> int:
    return getScaledQuantity(get(LOANED_SUPPLY_KEY).to_int())


# LOANED_SUPPLY_KEY keeps track of the
# FLOAT_MULTIPLIER scaled value
def updateLoanedSupply(quantity: int):
    put(LOANED_SUPPLY_KEY, get(LOANED_SUPPLY_KEY).to_int() + quantity)


@public
def totalMinted() -> int:
    return get(MINTED_KEY).to_int()


@public
def totalBurned() -> int:
    return get(BURNED_KEY).to_int()


@public
def numAccounts() -> int:
    return get(NUM_ACCOUNTS_KEY).to_int()


@public
def getLastHeight() -> int:
    return get(LAST_HEIGHT_KEY).to_int()


def setLastHeight(last_height: int):
    put(LAST_HEIGHT_KEY, last_height)


# TODO: make this settable
# 100% APR!
@public
def getR0() -> int:
    return 10_000


@public
def balanceOf(account: UInt160) -> int:
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    account64 = base64_encode(account)
    return get_read_only_context().create_map(BALANCE_KEY).get(account64).to_int()


@public
def loanedBalanceOf(account: UInt160) -> int:
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    account64 = base64_encode(account)
    unscaled_quantity = get_read_only_context().create_map(LOAN_KEY).get(account64).to_int()
    return getScaledQuantity(unscaled_quantity)


def updateLoanedBalanceOf(account: UInt160, quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'

    loan_context = get_context().create_map(LOAN_KEY)
    account64 = base64_encode(account)
    existing_loan = loan_context.get(account64).to_int()
    new_loan = existing_loan + quantity

    assert new_loan >= 0, 'update must not make loan quantity negative'

    loan_context.put(account64, new_loan)


@public
def getBalances(page_num: int, page_size: int) -> List[UInt160, int]:
    """
    Get all pairs of [account, balance] of currently held BUSDL tokens
    Due to a limit on the number of elements of the returned list,
    we need to support pagination through page_num and page_size

    :return: the [account, balance] of all held tokens for the page
    """
    assert page_num >= 0, 'page_num must be a non-negative integer'
    assert page_size > 0 and page_size <= 512, 'page_size must be a positive integer <= 512'
    offset = page_num * page_size
    balances = find(BALANCE_KEY)
    ret = []
    while balances.next():
        if offset > 0:
            offset -= 1
        else:
            account64 = cast(str, balances.value[0])[len(BALANCE_KEY):]
            account = UInt160(base64_decode(account64))
            quantity = cast(bytes, balances.value[1]).to_int()
            if quantity > 0:
                ret.append((UInt160(account), quantity))
            if len(ret) >= page_size:
                return ret
    return ret


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
    diff_num_accounts = 0
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
            diff_num_accounts -= 1
        else:
            balance_map.put(from_address64, from_balance - amount)

        to_address64 = base64_encode(to_address)
        to_balance = balance_map.get(to_address64).to_int()
        balance_map.put(to_address64, to_balance + amount)
        if to_balance == 0:
            diff_num_accounts += 1

    # if the method succeeds, it must fire the transfer event
    on_transfer(from_address, to_address, amount)
    # if the to_address is a smart contract, it must call the contracts onPayment
    post_transfer(from_address, to_address, amount, data)

    # Update the total number of accounts
    num_accounts = numAccounts()
    put(NUM_ACCOUNTS_KEY, num_accounts + diff_num_accounts)

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
# Lending Methods
# -------------------------------------------


def mint(account: UInt160, amount: int):
    """
    Mints new tokens
    Aborts if check_witness on the LyrebirdAviary contract fails

    :param account: the address of the account that is sending cryptocurrency to this contract
    :type account: UInt160
    :param amount: the amount to be minted
    :type amount: int
    :raise AssertionError: raised if `account` is invalid or if `amount` is less than zero.
    """

    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert amount >= 0, 'mint amount cannot be negative'

    if amount != 0:
        current_total_supply = totalSupply()
        minted = totalMinted()
        account_balance = balanceOf(account)
        account64 = base64_encode(account)

        put(SUPPLY_KEY, current_total_supply + amount)
        put(MINTED_KEY, minted + amount)
        get_context().create_map(BALANCE_KEY).put(account64, account_balance + amount)

        on_transfer(None, account, amount)
        post_transfer(None, account, amount, [ ACTION_MINT ])


def burn(account: UInt160, amount: int):
    """
    Burns tokens
    Unlike mint, this method can be called by anyone if they wish to burn their tokens

    :param account: the address of the account that is sending cryptocurrency to this contract
    :type account: UInt160
    :param amount: the amount to be burned
    :type amount: int
    :raise AssertionError: raised if `account` is invalid or if `amount` is less than zero.
    """

    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert amount >= 0, 'burn amount cannot be negative'

    if not callByNest() and not check_witness(account):
        abort()

    if amount != 0:
        current_total_supply = totalSupply()
        burned = totalBurned()
        account_balance = balanceOf(account)
        account64 = base64_encode(account)

        put(SUPPLY_KEY, current_total_supply - amount)
        put(BURNED_KEY, burned + amount)
        get_context().create_map(BALANCE_KEY).put(account64, account_balance - amount)

        on_transfer(None, account, amount)


# 1 BUSDL = (exchange_rate / EXCHANGE_RATE_MULT) USDL
# For example, start at USDL = 1e8 BUSDL
# If BUSDL supply stays the same and USDL supply + loans doubles, then USDl = 5e7 BUSDL
@public
def getExchangeRate() -> int:
    # Initially, exchange rate is 1:1 but with differing decimal places
    busdl_supply = totalSupply()
    if busdl_supply == 0:
        return INITIAL_EXCHANGE_RATE

    # If supply already exists, the rate is (USDL supply + USDL loans) / (BUSDL supply)
    usdl_supply = getUnderlyingSupply()
    usdl_loans = getLoanedSupply()
    
    return (EXCHANGE_RATE_MULT * (usdl_supply + usdl_loans)) // busdl_supply


# TODO: update interest rate
def accrueInterest():
    """
    We accrue interest whenever the underlying supply or loaned supply changes, so on:
        1. Deposit
        2. Redeem
        3. Loan
        4. Repayment
    On any of these operations, we accrue interest by:
        1. Computing the height difference since the last update
        2. Computing the interest charged during the height difference
        3. Computing the new interest_factor based on the previous interest_factor
        4. Updating the last height
    This function naturally has the effect of updating the exchange rate
    """
    last_height = getLastHeight()
    new_height = current_index
    diff_height = new_height - last_height
    annual_rate = getR0()
    interest_accrued = (FLOAT_MULTIPLIER * diff_height * annual_rate) // (BLOCKS_PER_YEAR * BASIS_POINTS)
    # Note that this is the stored value, not the one that scales with the interest accrued
    # since getInterestMultiplier() returns with unaccumulated interest.
    unscaled_interest_multiplier = get(INTEREST_MULTIPLIER_KEY).to_int()
    new_interest_multiplier = ((FLOAT_MULTIPLIER + interest_accrued) * unscaled_interest_multiplier) // FLOAT_MULTIPLIER

    setInterestMultiplier(new_interest_multiplier)
    setLastHeight(new_height)
    pass


def deposit(account: UInt160, deposit_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert deposit_quantity >= 0, 'deposit_quantity must be a non-negative integer'

    exchange_rate = getExchangeRate()
    mint_quantity = (EXCHANGE_RATE_MULT * deposit_quantity) // exchange_rate

    if deposit_quantity != 0:
        updateUnderlyingSupply(deposit_quantity)
        accrueInterest()
        mint(executing_script_hash, mint_quantity)
        # transfer BUSDL to depositor
        transfer_success = cast(bool, call_contract(executing_script_hash, 'transfer', [executing_script_hash, account, mint_quantity, None]))
        if not transfer_success:
            on_deposit_failure(account, deposit_quantity, mint_quantity, 'Failed to transfer BUSDL to depositor')
            abort()

    on_deposit(account, deposit_quantity, mint_quantity)


def redeem(account: UInt160, redeem_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert redeem_quantity >= 0, 'redeem_quantity must be a non-negative integer'

    exchange_rate = getExchangeRate()
    burn_quantity = redeem_quantity
    underlying_redeem_quantity = (redeem_quantity * exchange_rate) // EXCHANGE_RATE_MULT

    if redeem_quantity != 0:
        underlying_supply = getUnderlyingSupply()
        if underlying_supply < underlying_redeem_quantity:
            on_redeem_failure(account, underlying_redeem_quantity, redeem_quantity, 'Failed to redeem USDL because supply=' + itoa(underlying_supply) + ' < underlying_redeem_quantity=' + itoa(underlying_redeem_quantity))
            abort()

        updateUnderlyingSupply(-underlying_redeem_quantity)
        accrueInterest()
        burn(executing_script_hash, burn_quantity)
        # transfer USDL to redeemer
        transfer_success = cast(bool, call_contract(getUnderlyingScriptHash(), 'transfer', [executing_script_hash, account, underlying_redeem_quantity, None]))
        if not transfer_success:
            on_redeem_failure(account, underlying_redeem_quantity, redeem_quantity, 'Failed to transfer USDL to redeemer')
            abort()

    on_redeem(account, underlying_redeem_quantity, redeem_quantity)


@public
def loan(account: UInt160, loan_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert loan_quantity >= 0, 'loan_quantity must be a non-negative integer'

    if not callByNest():
        abort()

    accrueInterest()
    if loan_quantity != 0:
        underlying_supply = getUnderlyingSupply()
        if underlying_supply < loan_quantity:
            on_loan_failure(account, loan_quantity, 'Failed to loan USDL because supply=' + itoa(underlying_supply) + ' < loan_quantity=' + itoa(loan_quantity))
            abort()

        updateUnderlyingSupply(-loan_quantity)

        unscaled_loan_quantity = getUnscaledQuantity(loan_quantity)
        updateLoanedSupply(unscaled_loan_quantity)
        updateLoanedBalanceOf(account, unscaled_loan_quantity)

        transfer_success = cast(bool, call_contract(getUnderlyingScriptHash(), 'transfer', [executing_script_hash, account, loan_quantity, None]))
        if not transfer_success:
            on_loan_failure(account, loan_quantity, 'Failed to transfer USDL to loan')
            abort()

    on_loan(account, loan_quantity)


def repayment(payer: UInt160, account: UInt160, repayment_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert repayment_quantity >= 0, 'repayment_quantity must be a non-negative integer'

    max_repayment_quantity = loanedBalanceOf(account)
    clipped_repayment_quantity = min(max_repayment_quantity, repayment_quantity)

    accrueInterest()
    if repayment_quantity != 0:
        loaned_supply = getLoanedSupply()
        if loaned_supply < clipped_repayment_quantity:
            on_repayment_failure(account, clipped_repayment_quantity, 'Failed to repay USDL because loaned supply=' + itoa(loaned_supply) + ' < clipped repayment quantity=' + itoa(clipped_repayment_quantity))
            abort()

        unscaled_repayment_quantity = getUnscaledQuantity(clipped_repayment_quantity)
        updateLoanedSupply(-unscaled_repayment_quantity)
        updateUnderlyingSupply(clipped_repayment_quantity)
        updateLoanedBalanceOf(account, -unscaled_repayment_quantity)

    # Refund any overpayment
    overpayment_quantity = repayment_quantity - clipped_repayment_quantity
    if overpayment_quantity > 0:
        transfer_success = cast(bool, call_contract(getUnderlyingScriptHash(), 'transfer', [ executing_script_hash, payer, overpayment_quantity, None ]))
        if not transfer_success:
            on_repayment_failure(account, clipped_repayment_quantity, 'Failed to repay overpayment quantity=' + itoa(overpayment_quantity))
            abort()

    on_repayment(account, repayment_quantity)


@public
def onNEP17Payment(from_address: UInt160, amount: int, data: Any):
    """
    This is the entry point for the swap.

    The user transfers the original tokens while specifying the intent in the data attribute
    data = [ action_type: string, [repayment_address: UInt160] ]
    """
    assert amount >= 0, 'amount must be non-negative'

    transfer_data = cast(list, data)
    origin_token = calling_script_hash
    action_type = cast(str, transfer_data[0])

    # If receiving tokens due to a mint, we need to receive and stop processing
    if action_type == ACTION_MINT:
        return

    # from_address may be invalid on ACTION_MINT so we check here instead
    assert validate_address(from_address), 'from_address must be a valid 20 byte UInt160'

    # We can redeem the B-asset by burning it
    # and receive the underlying in return
    if origin_token == executing_script_hash:
        if action_type == ACTION_REDEEM:
            redeem(from_address, amount)
            return
    # We can deposit or repay the underlying 
    elif origin_token == getUnderlyingScriptHash():
        if action_type == ACTION_DEPOSIT:
            deposit(from_address, amount)
            return
        elif action_type == ACTION_REPAYMENT:
            repayment_address = cast(UInt160, transfer_data[1])
            repayment(from_address, repayment_address, amount)
            return
    abort()


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


def callByNest() -> bool:
    """
    Check whether the call to a method was by the Nest contract
    :return: whether the call was made by the Nest contract 
    """
    nest_script_hash = getNestScriptHash()
    return calling_script_hash == nest_script_hash or check_witness(nest_script_hash)


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
    put(MINTED_KEY, TOKEN_INITIAL_SUPPLY)
    put(BURNED_KEY, 0)
    put(NEST_SCRIPT_HASH_KEY, UInt160())
    owner64 = base64_encode(tx.sender)
    get_context().create_map(BALANCE_KEY).put(owner64, TOKEN_INITIAL_SUPPLY)
    put(NUM_ACCOUNTS_KEY, 0)
    put(INTEREST_MULTIPLIER_KEY, INITIAL_INTEREST_MULTIPLIER)
    put(UNDERLYING_SUPPLY_KEY, 0)
    put(LOANED_SUPPLY_KEY, 0)
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
