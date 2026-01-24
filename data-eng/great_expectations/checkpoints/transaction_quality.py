"""
GraphGuard - Great Expectations Data Quality Suite
====================================================
File: data-eng/great_expectations/checkpoints/transaction_quality.py
Reference: Specification.md Lines 1227-1280

Goal: Define data quality expectations for transactions and features.

Expectations:
- expect_column_values_to_not_be_null - transaction_id
- expect_column_values_to_be_between - amount (0, 1M)
- expect_column_values_to_be_in_set - currency
- expect_column_max_to_be_below - txn_count_1h < 50
"""

import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.expectation_configuration import ExpectationConfiguration


def create_transaction_quality_suite() -> ExpectationSuite:
    """
    Create expectation suite for raw transaction data.
    Reference: Specification.md Lines 1243-1275
    """
    suite = ExpectationSuite(expectation_suite_name="transaction_quality")
    
    # 1. No null transaction IDs
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "transaction_id"}
    ))
    
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "user_id"}
    ))
    
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "merchant_id"}
    ))
    
    # 2. Amount should be positive and reasonable
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={"column": "amount", "min_value": 0.01, "max_value": 1000000}
    ))
    
    # 3. Currency should be valid ISO codes
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "currency", "value_set": ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"]}
    ))
    
    # 4. Unique transaction IDs
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_unique",
        kwargs={"column": "transaction_id"}
    ))
    
    # 5. Card last 4 should be 4 digits
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_value_lengths_to_equal",
        kwargs={"column": "card_last4", "value": 4}
    ))
    
    # 6. IP address should match pattern
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_match_regex",
        kwargs={
            "column": "ip_address",
            "regex": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        }
    ))
    
    return suite


def create_feature_quality_suite() -> ExpectationSuite:
    """
    Create expectation suite for computed features.
    """
    suite = ExpectationSuite(expectation_suite_name="feature_quality")
    
    # 1. Transaction counts should be non-negative
    for col in ["txn_count_1h", "txn_count_24h", "txn_count_7d"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={"column": col, "min_value": 0, "max_value": None}
        ))
    
    # 2. Rapid fire flag should indicate high velocity
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_max_to_be_between",
        kwargs={"column": "txn_count_1h", "min_value": 0, "max_value": 100}
    ))
    
    # 3. PageRank should be between 0 and 1
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={"column": "pagerank", "min_value": 0, "max_value": 1}
    ))
    
    # 4. No null features for ML
    for col in ["txn_count_1h", "amount_sum_1h", "device_age_days"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": col}
        ))
    
    return suite


def setup_data_context():
    """
    Initialize Great Expectations data context.
    """
    context = gx.get_context()
    
    # Add transaction quality suite
    context.add_or_update_expectation_suite(
        expectation_suite=create_transaction_quality_suite()
    )
    
    # Add feature quality suite
    context.add_or_update_expectation_suite(
        expectation_suite=create_feature_quality_suite()
    )
    
    print("Expectation suites created successfully")
    return context


if __name__ == "__main__":
    setup_data_context()
