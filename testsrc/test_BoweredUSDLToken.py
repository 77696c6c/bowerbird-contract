from boa3.boa3 import Boa3
from boa3.builtin.type import UInt160
from boa3.neo.cryptography import hash160
from boa3_test.tests.boa_test import BoaTest
from boa3_test.tests.test_classes.TestExecutionException import TestExecutionException
from boa3_test.tests.test_classes.testengine import TestEngine

ROOT_DIR = '/Users/william/Neo/src/lyrebird-contract'

TOKEN_MULT = int(1e8)

class TestTemplate(BoaTest):
    # Typically, we will set the owner to be the address that deploys the contract. However, the test suite uses a different script hash for the caller.
    OWNER_SCRIPT_HASH = UInt160(b'\x9c\xa5/\x04"{\xf6Z\xe2\xe5\xd1\xffe\x03\xd1\x9dd\xc2\x9cF')
    OTHER_SCRIPT_HASH = UInt160(b'\xf7\x82<X\xb5:\xcf\xe8\xb4e\xa67C\xcb}2;..b')


    def get_path(self):
        return self.get_contract_path(ROOT_DIR, 'src', 'BoweredUSDLToken.py')


    def get_usdl_path(self):
        return self.get_contract_path(ROOT_DIR, 'testsrc', 'LyrebirdUSDToken.py')


    def test_busdl_compile(self):
        path = self.get_path()
        Boa3.compile(path)


    def test_busdl_deploy(self):
        path = self.get_path()
        engine = TestEngine()

        result = self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertIsVoid(result)


    def test_busdl_get_owner(self):
        path = self.get_path()
        engine = TestEngine()
        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getOwner')
        self.assertEqual(self.OWNER_SCRIPT_HASH, result)

        self.run_smart_contract(engine, path, 'setOwner', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getOwner')
        self.assertEqual(self.OTHER_SCRIPT_HASH, result)

        with self.assertRaises(TestExecutionException, msg=self.ABORTED_CONTRACT_MSG):
            self.run_smart_contract(engine, path, 'setOwner', self.OWNER_SCRIPT_HASH,
                                             signer_accounts=[self.OWNER_SCRIPT_HASH])


    def test_busdl_get_symbol(self):
        path = self.get_path()
        engine = TestEngine()
        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'symbol')
        self.assertEqual('bUSDL', result)


    def test_busdl_get_decimals(self):
        path = self.get_path()
        engine = TestEngine()
        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'decimals')
        self.assertEqual(8, result)


    def test_busdl_deposit(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 1000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        deposit_events = engine.get_events('Deposit', origin=busdl_address)
        self.assertEqual(1, len(deposit_events))
        args = deposit_events[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual(1000 * TOKEN_MULT, args[1])
        self.assertEqual(1000 * TOKEN_MULT, args[2])

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', busdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual((10_000_000 - 1000) * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)


    def test_busdl_redeem(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 1000, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual((10_000_000 * TOKEN_MULT) - 1000, result)

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(1000, result)

        # NVM overflows at 2^256, but it seems that the Python test suite caps out at 2^64.
        self.run_smart_contract(engine, path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 500, [ 'ACTION_REDEEM' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        redeemevents = engine.get_events('Redeem', origin=busdl_address)
        self.assertEqual(1, len(redeemevents))
        args = redeemevents[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual(500, args[1])
        self.assertEqual(500, args[2])

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(500, result)

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual((10_000_000 * TOKEN_MULT) - 500, result)


    def test_busdl_loan(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # Lending fails if we don't have enough supply
        with self.assertRaises(TestExecutionException, msg=self.ABORTED_CONTRACT_MSG):
            self.run_smart_contract(engine, path, 'loan', self.OTHER_SCRIPT_HASH, 1000 * TOKEN_MULT,
                                             signer_accounts=[self.OTHER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address,
                                         1000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)
        
        self.run_smart_contract(engine, path, 'loan', self.OTHER_SCRIPT_HASH, 700 * TOKEN_MULT,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        loan_events = engine.get_events('Loan', origin=busdl_address)
        self.assertEqual(1, len(loan_events))
        args = loan_events[0].arguments
        self.assertEqual(self.OTHER_SCRIPT_HASH, args[0])
        self.assertEqual(700 * TOKEN_MULT, args[1])

        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(69999999999, result)
        
        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(700 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(300 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(69999999999, result)

        result = self.run_smart_contract(engine, path, 'getInterestMultiplier')
        self.assertEqual(1000000475646879756, result)

        # Lending fails if we don't have enough supply
        with self.assertRaises(TestExecutionException, msg=self.ABORTED_CONTRACT_MSG):
            self.run_smart_contract(engine, path, 'loan', self.OTHER_SCRIPT_HASH, 301 * TOKEN_MULT,
                                             signer_accounts=[self.OTHER_SCRIPT_HASH])

        # Loan again after one hour
        engine.increase_block(engine.height + (4 * 60))
        self.run_smart_contract(engine, path, 'loan', self.OWNER_SCRIPT_HASH, 300 * TOKEN_MULT,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # Another person loaned, but the original loan has now accrued interest
        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(70007990867, result)
        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(29999999999, result)
        
        # The balance remains the same
        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(700 * TOKEN_MULT, result)

        # We have no more reserves since the protocol is at 100% utilization
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        # original loaned balance + interest: 70007990867
        # new loaned balance: 29999999999
        # underlying balance: 0
        # and then rounding error
        self.assertEqual(100007990867, result)


    def test_busdl_repayment(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 1000 * TOKEN_MULT,
                                        [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)
        
        self.run_smart_contract(engine, path, 'loan', self.OTHER_SCRIPT_HASH, 700 * TOKEN_MULT,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 200 * TOKEN_MULT,
                                        [ 'ACTION_REPAYMENT', self.OTHER_SCRIPT_HASH ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(700 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(500 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(49999999999, result)

        # Repay again after one hour
        engine.increase_block(engine.height + (4 * 60))
        self.run_smart_contract(engine, usdl_path, 'transfer', self.OTHER_SCRIPT_HASH, busdl_address, 500 * TOKEN_MULT,
                                        [ 'ACTION_REPAYMENT', self.OTHER_SCRIPT_HASH ],
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])

        # The original loan has now accrued interest
        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(5707762, result)
        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(200 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)
        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(5707762, result)

        # Give the OTHER account more tokens to test overpayment
        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, self.OTHER_SCRIPT_HASH, 1000 * TOKEN_MULT, None,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OTHER_SCRIPT_HASH, busdl_address, 1000 * TOKEN_MULT,
                                        [ 'ACTION_REPAYMENT', self.OTHER_SCRIPT_HASH ],
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])

        # Overpayment gets refunded
        result = self.run_smart_contract(engine, path, 'loanedBalanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)
        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(1200 * TOKEN_MULT - 5707762, result)
        result = self.run_smart_contract(engine, path, 'getUnderlyingSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT + 5707762, result)
        result = self.run_smart_contract(engine, path, 'getLoanedSupply',
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)


    def test_busdl_get_balances(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(0, result)

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(0, result)

        result = self.run_smart_contract(engine, path, 'getBalances', 0, 1)
        self.assertEqual([], result)

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 10_000_000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, path, 'transfer', self.OWNER_SCRIPT_HASH, self.OTHER_SCRIPT_HASH, 2000, None,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(10_000_000 * TOKEN_MULT - 2000, result)
        
        result = self.run_smart_contract(engine, path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(2000, result)
        
        result = self.run_smart_contract(engine, path, 'getBalances', 0, 2)
        self.assertEqual([[self.OTHER_SCRIPT_HASH, 2000], [self.OWNER_SCRIPT_HASH, 10_000_000 * TOKEN_MULT - 2000]], result)
        result = self.run_smart_contract(engine, path, 'getBalances', 0, 1)
        self.assertEqual([[self.OTHER_SCRIPT_HASH, 2000]], result)
        result = self.run_smart_contract(engine, path, 'getBalances', 1, 1)
        self.assertEqual([[self.OWNER_SCRIPT_HASH, 10_000_000 * TOKEN_MULT - 2000]], result)

        # Page size too large fails
        with self.assertRaises(TestExecutionException, msg=self.ASSERT_RESULTED_FALSE_MSG):
            self.run_smart_contract(engine, path, 'getBalances', 0, 2048,
                                             signer_accounts=[self.OWNER_SCRIPT_HASH])


    def test_busdl_num_accounts(self):
        path = self.get_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'numAccounts')
        self.assertEqual(0, result)

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address, 1000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, path, 'transfer', self.OWNER_SCRIPT_HASH, self.OTHER_SCRIPT_HASH, 2000, None,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'numAccounts')
        self.assertEqual(1, result)

        self.run_smart_contract(engine, path, 'transfer', self.OTHER_SCRIPT_HASH, self.OWNER_SCRIPT_HASH, 2000, None,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'numAccounts')
        self.assertEqual(0, result)
