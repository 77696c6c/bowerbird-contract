from typing import Any

from boa3.builtin import CreateNewEvent, NeoMetadata, metadata, public
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop.blockchain import current_index, Transaction
from boa3.builtin.interop.contract import call_contract, destroy_contract, update_contract, CallFlags
from boa3.builtin.interop.json import json_deserialize
from boa3.builtin.interop.oracle import Oracle
from boa3.builtin.interop.runtime import calling_script_hash, check_witness, script_container, executing_script_hash
from boa3.builtin.interop.stdlib import base64_decode, base64_encode, itoa
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
    meta.author = "Bowerbird Finance"
    meta.description = "Bowerbird Nest - the deposit/borrow module for Bowerbird"
    meta.email = "hello@bowerbird.finance"
    return meta


# -------------------------------------------
# ADDRESS SETTINGS
# -------------------------------------------

USDL_SCRIPT_HASH_KEY = 'usdl'
BUSDL_SCRIPT_HASH_KEY = 'busdl'
BNEO_SCRIPT_HASH_KEY = 'bneo'
COLLATERAL_SCRIPT_HASH_KEY = 'col/'
ORACLE_SCRIPT_HASH_KEY = 'oracle'
ORACLE_SCRIPT_HASH = UInt160(b'X\x87\x17\x11~\n\xa8\x10r\xaf\xabq\xd2\xdd\x89\xfe|K\x92\xfe')

OWNER_KEY = 'owner'

# -------------------------------------------
# LEND SETTINGS
# -------------------------------------------

# Number of decimal places
PRICE_MULT = 1_000_000

USDL = 'USDL'

PRICE_URL = 'https://bowerbird.finance/prices'
ORACLE_FEE_KEY = 'of'
# Initial fee = 0.10 GAS
INITIAL_ORACLE_FEE = 10_000_000

# Expressed in basis points
MAX_LIQUIDATION_RATIO_KEY = 'ml/'
INITIAL_MAX_LIQUIDATION_RATIO = 5000
# Expressed in basis points
LIQUIDATION_PENALTY_KEY = 'lp/'
INITIAL_LIQUIDATION_PENALTY = 500

# The minimum loan-to-value, expressed in basis points
# COLLATERAL_VALUE / LOAN_VALUE
LOAN_TO_VALUE_KEY = 'lv/'
INITIAL_LOAN_TO_VALUE = 7500
BASIS_POINTS = 10000

# The quantity of a given collateral for a wallet
COLLATERAL_KEY = 'cl/'

TOTAL_COLLATERAL_KEY = 'tc/'

# Actions
ACTION_COLLATERALIZE = 'ACTION_COLLATERALIZE'
ACTION_LIQUIDATE = 'ACTION_LIQUIDATE'

# -------------------------------------------
# Events
# -------------------------------------------

on_transfer = Nep17TransferEvent

on_collateral_deposit = CreateNewEvent(
    [
        ('account', UInt160),
        ('collateral_symbol', str),
        ('collateral_quantity', int)
    ],
    'CollateralDeposit'
)

on_collateral_withdraw = CreateNewEvent(
    [
        ('account', UInt160),
        ('collateral_symbol', str),
        ('collateral_quantity', int),
    ],
    'CollateralWithdraw'
)

on_collateral_withdraw_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('collateral_symbol', str),
        ('collateral_quantity', int),
        ('failure_reason', str),
    ],
    'CollateralWithdrawFailure'
)

on_loan = CreateNewEvent(
    [
        ('account', UInt160),
        ('loan_symbol', str),
        ('loan_quantity', int),
    ],
    'Loan'
)

on_loan_failure = CreateNewEvent(
    [
        ('account', UInt160),
        ('loan_symbol', str),
        ('loan_quantity', int),
        ('failure_reason', str),
    ],
    'LoanFailure'
)

on_liquidate = CreateNewEvent(
    [
        ('liquidator', UInt160),
        ('account', UInt160),
        ('collateral_symbol', str),
        ('usdl_quantity', int),
        ('collateral_quantity', int),
    ],
    'Liquidate'
)

on_liquidate_failure = CreateNewEvent(
    [
        ('liquidator', UInt160),
        ('account', UInt160),
        ('collateral_symbol', str),
        ('usdl_quantity', int),
        ('failure_reason', str),
    ],
    'LiquidateFailure'
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


@public
def getUSDLScriptHash() -> UInt160:
    return UInt160(get(USDL_SCRIPT_HASH_KEY))


@public
def setUSDLScriptHash(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(USDL_SCRIPT_HASH_KEY, hash)


@public
def getBUSDLScriptHash() -> UInt160:
    return UInt160(get(BUSDL_SCRIPT_HASH_KEY))


@public
def setBUSDLScriptHash(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(BUSDL_SCRIPT_HASH_KEY, hash)


@public
def getBNEOScriptHash() -> UInt160:
    return UInt160(get(BNEO_SCRIPT_HASH_KEY))


@public
def setBNEOScriptHash(hash: UInt160) -> bool:
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(BNEO_SCRIPT_HASH_KEY, hash)
    return supportCollateral(hash)


@public
def getOracleScriptHash() -> UInt160:
    return UInt160(get(ORACLE_SCRIPT_HASH_KEY))


@public
def setOracleScriptHash(hash: UInt160) -> bool:
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(ORACLE_SCRIPT_HASH_KEY, hash)
    return True


@public
def isCollateralSupported(token: UInt160) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    token64 = base64_encode(token)
    return get_read_only_context().create_map(COLLATERAL_SCRIPT_HASH_KEY).get(token64).to_bool()


@public
def supportCollateral(token: UInt160) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    if not verify():
        abort()
    token64 = base64_encode(token)
    get_context().create_map(COLLATERAL_SCRIPT_HASH_KEY).put(token64, True)
    setLoanToValue(token, INITIAL_LOAN_TO_VALUE)
    setMaxLiquiationRatio(token, INITIAL_MAX_LIQUIDATION_RATIO)
    setLiquidationPenalty(token, INITIAL_LIQUIDATION_PENALTY)
    return True


@public
def invalidateCollateral(token: UInt160) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    if not verify():
        abort()
    token64 = base64_encode(token)
    get_context().create_map(COLLATERAL_SCRIPT_HASH_KEY).delete(token64)
    return True


@public
def getMaxLiquidationRatio(token: UInt160) -> int:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    token64 = base64_encode(token)
    return get_read_only_context().create_map(MAX_LIQUIDATION_RATIO_KEY).get(token64).to_int()


@public
def setMaxLiquiationRatio(token: UInt160, max_liquidation_ratio: int) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    assert max_liquidation_ratio >= 0, 'max_liquidation_ratio must be a non-negative integer'
    if not verify():
        abort()
    token64 = base64_encode(token)
    get_context().create_map(MAX_LIQUIDATION_RATIO_KEY).put(token64, max_liquidation_ratio)
    return True


@public
def getLiquidationPenalty(token: UInt160) -> int:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    token64 = base64_encode(token)
    return get_read_only_context().create_map(LIQUIDATION_PENALTY_KEY).get(token64).to_int()


@public
def setLiquidationPenalty(token: UInt160, liquidation_penalty: int) -> bool:
    assert liquidation_penalty >= 0, 'liquidation_penalty must be a non-negative integer'
    if not verify():
        abort()
    token64 = base64_encode(token)
    get_context().create_map(LIQUIDATION_PENALTY_KEY).put(token64, liquidation_penalty)
    return True


@public
def getOracleFee() -> int:
    return get(ORACLE_FEE_KEY).to_int()


# TODO: set per transaction type
@public
def setOracleFee(oracle_fee: int) -> bool:
    assert oracle_fee >= 0, 'oracle_fee must be a non-negative integer'
    if not verify():
        abort()
    put(ORACLE_FEE_KEY, oracle_fee)
    return True


@public
def getLoanToValue(token: UInt160) -> int:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    token64 = base64_encode(token)
    return get_read_only_context().create_map(LOAN_TO_VALUE_KEY).get(token64).to_int()


@public
def setLoanToValue(token: UInt160, collateralization_ratio: int) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    assert collateralization_ratio > 0, 'collateralization_ratio must be greater than zero'
    if not verify():
        abort()
    token64 = base64_encode(token)
    get_context().create_map(LOAN_TO_VALUE_KEY).put(token64, collateralization_ratio)
    return True


@public
def getTotalCollateral(token: UInt160) -> int:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    token64 = base64_encode(token)
    return get_read_only_context().create_map(TOTAL_COLLATERAL_KEY).get(token64).to_int()


def updateTotalCollateral(token: UInt160, collateral_quantity: int) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    assert collateral_quantity >= 0, 'collateral_quantity must be non-negative'
    token64 = base64_encode(token)
    get_context().create_map(TOTAL_COLLATERAL_KEY).put(token64, collateral_quantity)
    return True


@public
def getCollateralBalance(token: UInt160, account: UInt160) -> int:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    assert validate_address(account), 'account must be a valid 20 byte UInt160'

    token64 = base64_encode(token)
    account64 = base64_encode(account)
    return get_read_only_context().create_map(COLLATERAL_KEY + account64 + '/').get(token64).to_int()


def updateCollateralBalance(token: UInt160, account: UInt160, collateral_quantity: int) -> bool:
    assert validate_address(token), 'token must be a valid 20 byte UInt160'
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert collateral_quantity >= 0, 'collateral_quantity must be non-negative'

    token64 = base64_encode(token)
    account64 = base64_encode(account)
    get_context().create_map(COLLATERAL_KEY + account64 + '/').put(token64, collateral_quantity)
    return True


@public
def setOwner(hash: UInt160):
    assert validate_address(hash), 'hash must be a valid 20 byte UInt160'
    if not verify():
        abort()
    put(OWNER_KEY, hash)


@public
def getOwner() -> UInt160:
    return UInt160(get(OWNER_KEY))


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


def callByOracle() -> bool:
    """
    Check whether the call to a method was by the Oracle contract
    :return: whether the call was made by the Oracle contract 
    """
    oracle_script_hash = getOracleScriptHash()
    return calling_script_hash == oracle_script_hash or check_witness(oracle_script_hash)


# -------------------------------------------
# Lending Methods
# -------------------------------------------

# The total collateral value with LTV applied
def computeCollateralLTV(account: UInt160, price_map: dict) -> int:
    account64 = base64_encode(account)
    account_collateral_key = COLLATERAL_KEY + account64 + '/'
    balances = find(account_collateral_key)

    collateral_value = 0
    while balances.next():
        token64 = cast(str, balances.value[0])[len(account_collateral_key):]
        token = UInt160(base64_decode(token64))
        quantity = cast(bytes, balances.value[1]).to_int()
        if quantity > 0:
            token_symbol = cast(str, call_contract(token, 'symbol', [], CallFlags.READ_ONLY))
            token_price = cast(int, price_map[token_symbol])
            loan_to_value = getLoanToValue(token)
            token_value = (quantity * token_price * loan_to_value) // BASIS_POINTS
            collateral_value += token_value

    return collateral_value


@public
def loanCallback(url: str, user_data: Any, code: int, result: bytes):
    if not callByOracle():
        abort()

    loan_data = cast(dict, user_data)
    account = cast(UInt160, loan_data['account'])
    loan_quantity = cast(int, loan_data['loan_quantity'])
    loan_token = cast(UInt160, loan_data['loan_token'])

    underlying_token = cast(UInt160, call_contract(loan_token, 'getUnderlyingScriptHash', [], CallFlags.READ_ONLY))
    loan_symbol = cast(str, call_contract(underlying_token, 'symbol', [], CallFlags.READ_ONLY))
    current_loan = cast(int, call_contract(loan_token, 'loanedBalanceOf', [account], CallFlags.READ_ONLY))

    if code != 0:
        on_loan_failure(account, loan_symbol, loan_quantity, 'Oracle invocation failed')
        pass


    json_result = cast(dict, json_deserialize(cast(str, result)))

    # Compute the total loan value
    total_loan = current_loan + loan_quantity
    loan_price = cast(int, json_result[loan_symbol])
    loan_value = total_loan * loan_price
    collateral_ltv = computeCollateralLTV(account, json_result)
            
    if loan_value > collateral_ltv:
        on_loan_failure(account, loan_symbol, loan_quantity, 'The total loan value=' + itoa(loan_value) +
            ' > total collateral loan to value=' + itoa(collateral_ltv))
        return

    call_contract(loan_token, 'loan', [account, loan_quantity])
    on_loan(account, loan_symbol, loan_quantity)

    
@public
def loan(account: UInt160, loan_token: UInt160, loan_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert validate_address(loan_token), 'loan_token must be a valid 20 byte UInt160'
    assert loan_quantity >= 0, 'loan_quantity must be a non-negative integer'

    # Keep in mind that loan_token is the wrapped token
    # 1. Make a call to the oracle to see if this is valid
    # If not valid, cut down to valid quantity
    loan_data = {
        'account': account,
        'loan_token': loan_token,
        'loan_quantity': loan_quantity,
    }
    Oracle.request(PRICE_URL, None, 'loanCallback', loan_data, getOracleFee())


def depositCollateral(account: UInt160, collateral_token: UInt160, quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert quantity >= 0, 'quantity must be a non-negative integer'

    collateral_symbol = cast(str, call_contract(collateral_token, 'symbol', [], CallFlags.READ_ONLY))
    current_collateral = getCollateralBalance(collateral_token, account)
    new_collateral = current_collateral + quantity
    updateCollateralBalance(collateral_token, account, new_collateral)
    on_collateral_deposit(account, collateral_symbol, quantity)


@public
def withdrawCollateralCallback(url: str, user_data: Any, code: int, result: bytes):
    if not callByOracle():
        abort()

    withdraw_collateral_data = cast(dict, user_data)
    account = cast(UInt160, withdraw_collateral_data['account'])
    collateral_token = cast(UInt160, withdraw_collateral_data['collateral_token'])
    withdraw_quantity = cast(int, withdraw_collateral_data['withdraw_quantity'])

    collateral_symbol = cast(str, call_contract(collateral_token, 'symbol', [], CallFlags.READ_ONLY))

    if code != 0:
        on_collateral_withdraw_failure(account, collateral_symbol, withdraw_quantity, 'Oracle invocation failed')
        pass

    loan_quantity = cast(int, call_contract(getBUSDLScriptHash(), 'loanedBalanceOf', [account], CallFlags.READ_ONLY))
    current_collateral = getCollateralBalance(collateral_token, account)
    if current_collateral < withdraw_quantity:
        on_collateral_withdraw_failure(account, collateral_symbol, withdraw_quantity, 'Withdraw quantity=' + itoa(withdraw_quantity) + ' < current collateral=' + itoa(current_collateral))
        return

    json_result = cast(dict, json_deserialize(cast(str, result)))
    usdl_price = cast(int, json_result[USDL])
    collateral_price = cast(int, json_result[collateral_symbol])

    loan_value = usdl_price * loan_quantity
    collateral_ltv = computeCollateralLTV(account, json_result)
    loan_to_value = getLoanToValue(collateral_token)
    withdraw_collateral_ltv = (withdraw_quantity * collateral_price * loan_to_value) // BASIS_POINTS
    remaining_collateral_ltv = collateral_ltv - withdraw_collateral_ltv


    if loan_value > 0:
        if loan_value > remaining_collateral_ltv:
            on_collateral_withdraw_failure(account, collateral_symbol, withdraw_quantity, 'Withdrawal causes loan value=' + itoa(loan_value) + ' < remaining collateral loan to value=' + itoa(remaining_collateral_ltv))
            return
    
    updateCollateralBalance(collateral_token, account, current_collateral - withdraw_quantity)
    transfer_success = cast(bool, call_contract(collateral_token, 'transfer', [executing_script_hash, account, withdraw_quantity, None]))
    if not transfer_success:
        on_collateral_withdraw_failure(account, collateral_symbol, withdraw_quantity, 'Failed to transfer collateral to withdrawer')
        return
    on_collateral_withdraw(account, collateral_symbol, withdraw_quantity)


@public
def withdrawCollateral(account: UInt160, collateral_token: UInt160, withdraw_quantity: int):
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert validate_address(collateral_token), 'collateral_token must be a valid 20 byte UInt160'
    assert withdraw_quantity >= 0, 'withdraw_quantity must be a non-negative integer'

    # Currently, we don't have any plans to support any loans other than USDL
    withdraw_collateral_data = {
        'account': account,
        'collateral_token': collateral_token,
        'withdraw_quantity': withdraw_quantity,
    }
    Oracle.request(PRICE_URL, None, 'withdrawCollateralCallback', withdraw_collateral_data, getOracleFee())


@public
def liquidateCallback(url: str, user_data: Any, code: int, result: bytes):
    if not callByOracle():
        abort()

    liquidate_data = cast(dict, user_data)
    liquidator = cast(UInt160, liquidate_data['liquidator'])
    account = cast(UInt160, liquidate_data['account'])
    collateral_token = cast(UInt160, liquidate_data['collateral_token'])
    # liquidate_quantity is the amount of USDL
    usdl_quantity = cast(int, liquidate_data['usdl_quantity'])

    loan_quantity = cast(int, call_contract(getBUSDLScriptHash(), 'loanedBalanceOf', [account], CallFlags.READ_ONLY))
    collateral_symbol = cast(str, call_contract(collateral_token, 'symbol', [], CallFlags.READ_ONLY))
    current_collateral = getCollateralBalance(collateral_token, account)

    if code != 0:
        on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'Oracle invocation failed')
        pass

    json_result = cast(dict, json_deserialize(cast(str, result)))
    usdl_price = cast(int, json_result[USDL])
    collateral_price = cast(int, json_result[collateral_symbol])

    loan_value = usdl_price * loan_quantity
    collateral_ltv = computeCollateralLTV(account, json_result)
    usdl_script_hash = getUSDLScriptHash()
    
    # The account isn't eligible for liquidation, so refund the liquidator
    if collateral_ltv > loan_value:
        on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'collateral loan to value=' + itoa(collateral_ltv) + ' > loan value=' + itoa(loan_value))
        # Refund the liquidator
        transfer_success = cast(bool, call_contract(usdl_script_hash, 'transfer', [executing_script_hash, liquidator, usdl_quantity, None]))
        if not transfer_success:
            on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'failed to refund usdl quantity=' + itoa(usdl_quantity))
        return

    # The desired quantity of the collateral to be liquidated
    desired_liquidate_quantity = (usdl_quantity * usdl_price) // collateral_price
    # The maxiumum quantity of the collateral allowed to be liquidated
    max_liquidate_quantity = (current_collateral * getMaxLiquidationRatio(collateral_token)) // BASIS_POINTS
    clipped_liquidate_quantity = min(desired_liquidate_quantity, max_liquidate_quantity)
    total_liquidate_quantity = ((getLiquidationPenalty(collateral_token) + BASIS_POINTS) * clipped_liquidate_quantity) // BASIS_POINTS
    clipped_usdl_quantity = (clipped_liquidate_quantity * collateral_price) // usdl_price
    unused_usdl_quantity = usdl_quantity - clipped_usdl_quantity

    if total_liquidate_quantity > 0:
        # Update the collateral balance
        updateCollateralBalance(collateral_token, account, current_collateral - total_liquidate_quantity)
        # Make a repayment with the incoming USDL
        transfer_success = cast(bool, call_contract(usdl_script_hash, 'transfer', [executing_script_hash, getBUSDLScriptHash(), clipped_usdl_quantity, ['ACTION_REPAYMENT', account]]))
        if not transfer_success:
            on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'failed to repay usdl quantity=' + itoa(clipped_usdl_quantity))
            updateCollateralBalance(collateral_token, account, current_collateral)
            return
        # Pay out the liquidated collateral
        transfer_success = cast(bool, call_contract(collateral_token, 'transfer', [executing_script_hash, liquidator, total_liquidate_quantity, None]))
        if not transfer_success:
            on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'failed to transfer liquidated collateral=' + itoa(total_liquidate_quantity))
            updateCollateralBalance(collateral_token, account, current_collateral)
            return
        # Refund the unused usdl_quantity
        if unused_usdl_quantity > 0:
            transfer_success = cast(bool, call_contract(usdl_script_hash, 'transfer', [executing_script_hash, liquidator, unused_usdl_quantity, None]))
            if not transfer_success:
                on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'failed to repay unused usdl quantity=' + itoa(unused_usdl_quantity))
        on_liquidate(liquidator, account, collateral_symbol, clipped_usdl_quantity, total_liquidate_quantity)
    else:
        on_liquidate_failure(liquidator, account, collateral_symbol, usdl_quantity, 'total liquidate quantity = 0')
        


def liquidate(liquidator: UInt160, account: UInt160, collateral_token: UInt160, usdl_quantity: int):
    assert validate_address(liquidator), 'account must be a valid 20 byte UInt160'
    assert validate_address(account), 'account must be a valid 20 byte UInt160'
    assert validate_address(collateral_token), 'collateral_token must be a valid 20 byte UInt160'
    assert usdl_quantity >= 0, 'quantity must be a non-negative integer'

    # Currently, we don't have any plans to support any loans other than USDL
    # For Polaris, we also don't have any plans to support any other collateral asset
    liquidate_data = {
        'liquidator': liquidator,
        'account': account,
        'collateral_token': collateral_token,
        'usdl_quantity': usdl_quantity,
    }
    Oracle.request(PRICE_URL, None, 'liquidateCallback', liquidate_data, getOracleFee())


@public
def onNEP17Payment(from_address: UInt160, amount: int, data: Any):
    """
    This is the entry point for the swap.

    The user transfers the original tokens while specifying the intent in the data attribute
    data = [ action_type: string, target_token: UInt160, max_spread: int ]
    """
    assert amount >= 0, 'amount must be non-negative'

    transfer_data = cast(list, data)
    action_type = cast(str, transfer_data[0])

    assert validate_address(from_address), 'from_address must be a valid 20 byte UInt160'
    if action_type == ACTION_COLLATERALIZE:
        collateral_token = calling_script_hash
        if not isCollateralSupported(collateral_token):
            abort()
        depositCollateral(from_address, collateral_token, amount)
    elif action_type == ACTION_LIQUIDATE:
        if calling_script_hash != getUSDLScriptHash():
            abort()
        liquidate_address = cast(UInt160, transfer_data[1])
        collateral_token = cast(UInt160, transfer_data[2])
        liquidate(from_address, liquidate_address, collateral_token, amount)
    else:
        abort()


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
    put(ORACLE_FEE_KEY, INITIAL_ORACLE_FEE)
    put(ORACLE_SCRIPT_HASH_KEY, ORACLE_SCRIPT_HASH)
    

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
        
