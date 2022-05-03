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
    ORACLE_SCRIPT_HASH = UInt160(b'X\x87\x17\x11~\n\xa8\x10r\xaf\xabq\xd2\xdd\x89\xfe|K\x92\xfe')


    def get_path(self):
        return self.get_contract_path(ROOT_DIR, 'src', 'BowerbirdNest.py')


    def get_bneo_path(self):
        return self.get_contract_path(ROOT_DIR, 'testsrc', 'BurgerNeoToken.py')


    def get_busdl_path(self):
        return self.get_contract_path(ROOT_DIR, 'src', 'BoweredUSDLToken.py')


    def get_usdl_path(self):
        return self.get_contract_path(ROOT_DIR, 'testsrc', 'LyrebirdUSDToken.py')


    def test_nest_compile(self):
        path = self.get_path()
        Boa3.compile(path)


    def test_nest_deploy(self):
        path = self.get_path()
        engine = TestEngine()

        result = self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertIsVoid(result)


    def test_nest_get_owner(self):
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


    def test_nest_deposit_collateral(self):
        path = self.get_path()
        bneo_path = self.get_bneo_path()
        busdl_path = self.get_busdl_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        nest_address = hash160(output)

        output, manifest = self.get_output(bneo_path)
        bneo_address = hash160(output)

        output, manifest = self.get_output(busdl_path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, bneo_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, busdl_path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(0, result)

        # Collateral deposit fails if the asset isn't whitelisted
        with self.assertRaises(TestExecutionException, msg=self.ABORTED_CONTRACT_MSG):
            self.run_smart_contract(engine, bneo_path, 'transfer', self.OWNER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT, [ 'ACTION_COLLATERALIZE' ],
                                             signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, path, 'setBNEOScriptHash', bneo_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, bneo_path, 'transfer', self.OWNER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT, [ 'ACTION_COLLATERALIZE' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        collateral_deposit_events = engine.get_events('CollateralDeposit', origin=nest_address)
        self.assertEqual(1, len(collateral_deposit_events))
        args = collateral_deposit_events[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual('bNEO', args[1])
        self.assertEqual(1000 * TOKEN_MULT, args[2])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(1000 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, bneo_path, 'balanceOf', nest_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual(1000 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, bneo_path, 'balanceOf', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.assertEqual((10_000_000 - 1000) * TOKEN_MULT, result)


    def test_nest_withdraw_collateral(self):
        path = self.get_path()
        bneo_path = self.get_bneo_path()
        busdl_path = self.get_busdl_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        nest_address = hash160(output)

        output, manifest = self.get_output(bneo_path)
        bneo_address = hash160(output)

        output, manifest = self.get_output(busdl_path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, bneo_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, busdl_path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(0, result)

        self.run_smart_contract(engine, path, 'setBNEOScriptHash', bneo_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setBUSDLScriptHash', busdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, bneo_path, 'transfer', self.OWNER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT, [ 'ACTION_COLLATERALIZE' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)

        withdraw_collateral_data = {
            'account': self.OWNER_SCRIPT_HASH,
            'collateral_token': bneo_address,
            'withdraw_quantity': 1100 * TOKEN_MULT,
        }
        oracle_result = b'{"USDL":1000000,"bNEO":1000000}'
        self.run_smart_contract(engine, path, 'withdrawCollateralCallback', 'url', withdraw_collateral_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])

        withdraw_collateral_data = {
            'account': self.OWNER_SCRIPT_HASH,
            'collateral_token': bneo_address,
            'withdraw_quantity': 700 * TOKEN_MULT,
        }
        self.run_smart_contract(engine, path, 'withdrawCollateralCallback', 'url', withdraw_collateral_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])
        
        collateral_withdraw_events = engine.get_events('CollateralWithdraw', origin=nest_address)
        self.assertEqual(1, len(collateral_withdraw_events))
        args = collateral_withdraw_events[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual('bNEO', args[1])
        self.assertEqual(700 * TOKEN_MULT, args[2])


    def test_nest_loan(self):
        path = self.get_path()
        bneo_path = self.get_bneo_path()
        busdl_path = self.get_busdl_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        nest_address = hash160(output)

        output, manifest = self.get_output(bneo_path)
        bneo_address = hash160(output)

        output, manifest = self.get_output(busdl_path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, bneo_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, busdl_path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address,
                                         1000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(0, result)

        self.run_smart_contract(engine, path, 'setBNEOScriptHash', bneo_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setBUSDLScriptHash', busdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, bneo_path, 'transfer', self.OWNER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT, [ 'ACTION_COLLATERALIZE' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(1000 * TOKEN_MULT, result)

        loan_data = {
            'account': self.OWNER_SCRIPT_HASH,
            'loan_quantity': 500 * TOKEN_MULT,
            'loan_token': busdl_address,
        }
        oracle_result = b'{"USDL":1000000,"bNEO":100000}'
        self.run_smart_contract(engine, path, 'loanCallback', 'url', loan_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])

        loan_failure_events = engine.get_events('LoanFailure', origin=nest_address)
        self.assertEqual(1, len(loan_failure_events))
        args = loan_failure_events[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual('USDL', args[1])
        self.assertEqual(500 * TOKEN_MULT, args[2])

        loan_data = {
            'account': self.OWNER_SCRIPT_HASH,
            'loan_quantity': 500 * TOKEN_MULT,
            'loan_token': busdl_address,
        }
        oracle_result = b'{"USDL":1000000,"bNEO":1000000}'
        self.run_smart_contract(engine, path, 'loanCallback', 'url', loan_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])

        loan_failure_events = engine.get_events('Loan', origin=nest_address)
        self.assertEqual(1, len(loan_failure_events))
        args = loan_failure_events[0].arguments
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[0])
        self.assertEqual('USDL', args[1])
        self.assertEqual(500 * TOKEN_MULT, args[2])

    def test_nest_liquidate(self):
        path = self.get_path()
        bneo_path = self.get_bneo_path()
        busdl_path = self.get_busdl_path()
        usdl_path = self.get_usdl_path()
        engine = TestEngine()

        output, manifest = self.get_output(path)
        nest_address = hash160(output)

        output, manifest = self.get_output(bneo_path)
        bneo_address = hash160(output)

        output, manifest = self.get_output(busdl_path)
        busdl_address = hash160(output)

        output, manifest = self.get_output(usdl_path)
        usdl_address = hash160(output)

        self.run_smart_contract(engine, path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, bneo_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, '_deploy', None, False,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        # For testing, we set the Nest script hash to the owner script hash
        self.run_smart_contract(engine, busdl_path, 'setNestScriptHash', self.OWNER_SCRIPT_HASH,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, busdl_path, 'setUnderlyingScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual(0, result)

        self.run_smart_contract(engine, path, 'setBNEOScriptHash', bneo_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setBUSDLScriptHash', busdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, path, 'setUSDLScriptHash', usdl_address,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, busdl_address,
                                         1000 * TOKEN_MULT, [ 'ACTION_DEPOSIT' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        self.run_smart_contract(engine, bneo_path, 'transfer', self.OWNER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT, [ 'ACTION_COLLATERALIZE' ],
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])
        self.run_smart_contract(engine, usdl_path, 'transfer', self.OWNER_SCRIPT_HASH, self.OTHER_SCRIPT_HASH, 1000 * TOKEN_MULT, None,
                                         signer_accounts=[self.OWNER_SCRIPT_HASH])

        loan_data = {
            'account': self.OWNER_SCRIPT_HASH,
            'loan_quantity': 700 * TOKEN_MULT,
            'loan_token': busdl_address,
        }
        oracle_result = b'{"USDL":1000000,"bNEO":1000000}'
        self.run_smart_contract(engine, path, 'loanCallback', 'url', loan_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])

        liquidate_data = {
            'liquidator': self.OTHER_SCRIPT_HASH,
            'account': self.OWNER_SCRIPT_HASH,
            'collateral_token': bneo_address,
            'usdl_quantity': 100 * TOKEN_MULT,
        }
        self.run_smart_contract(engine, usdl_path, 'transfer', self.OTHER_SCRIPT_HASH, nest_address, 1000 * TOKEN_MULT,
                                         [ 'ACTION_LIQUIDATE', self.OTHER_SCRIPT_HASH ],
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        result = self.run_smart_contract(engine, usdl_path, 'balanceOf', nest_address,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])

        # Not eligible for liquidation at these prices
        oracle_result = b'{"USDL":1000000,"bNEO":1000000}'
        self.run_smart_contract(engine, path, 'liquidateCallback', 'url', liquidate_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])
        liquidate_events = engine.get_events('LiquidateFailure', origin=nest_address)
        self.assertEqual(1, len(liquidate_events))
        args = liquidate_events[0].arguments
        self.assertEqual(self.OTHER_SCRIPT_HASH, args[0])
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[1])
        self.assertEqual('bNEO', args[2])
        self.assertEqual(100 * TOKEN_MULT, args[3])

        # 50% is eligible for liquidation once collateral value below required margin
        oracle_result = b'{"USDL":1000000,"bNEO":500000}'
        self.run_smart_contract(engine, path, 'liquidateCallback', 'url', liquidate_data, 0, oracle_result,
                                         signer_accounts=[self.ORACLE_SCRIPT_HASH])

        result = self.run_smart_contract(engine, bneo_path, 'balanceOf', self.OTHER_SCRIPT_HASH,
                                         signer_accounts=[self.OTHER_SCRIPT_HASH])
        self.assertEqual(210 * TOKEN_MULT, result)

        result = self.run_smart_contract(engine, path, 'getCollateralBalance', bneo_address, self.OWNER_SCRIPT_HASH)
        self.assertEqual((1000 - 210) * TOKEN_MULT, result)

        liquidate_events = engine.get_events('Liquidate', origin=nest_address)
        self.assertEqual(1, len(liquidate_events))
        args = liquidate_events[0].arguments
        self.assertEqual(self.OTHER_SCRIPT_HASH, args[0])
        self.assertEqual(self.OWNER_SCRIPT_HASH, args[1])
        self.assertEqual('bNEO', args[2])
        self.assertEqual(100 * TOKEN_MULT, args[3])
        self.assertEqual(210 * TOKEN_MULT, args[4])
