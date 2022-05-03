# bowerbird-contract

This codebase houses the smart contracts for Bowerbird.

## Description

BoweredUSDL keeps track of the underlying supply and loaned supply of USDL, the desired annualized APR, and conversions between USDL and bUSDL.

BowerbirdNest keeps track of collateralization and liquidation. It consults the Oracle to get the most recent price feed since many of its operations are based on asset value and not just asset quantity.
