# ADR 003: Technical Indicator Calculation Strategy

**Status:** Accepted  
**Date:** 2026-01-21  
**Deciders:** Engineering Team

## Context

Sentinance needs to calculate technical indicators for 8 assets:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Moving Averages (SMA, EMA)
- ATR (Average True Range)

These calculations must be:
- Accurate (match industry-standard formulas)
- Fast (<50ms per calculation)
- Maintainable (clear, testable code)

## Decision

Implement indicators **in-house using NumPy** instead of:
- TA-Lib (C library with Python bindings)
- pandas-ta
- tulipy

## Rationale

### Why In-House?

1. **Full Control**: Understand every line of the algorithm
2. **No Dependencies**: Avoid C library compilation issues
3. **Educational Value**: Portfolio project demonstrates understanding
4. **Customization**: Easy to modify for specific use cases

### Key Implementation Details

#### MACD Signal Line (Critical Fix)

The signal line MUST be the 9-period EMA of MACD history, NOT a simplified approximation.

**Wrong (Bug Fixed):**
```python
signal_line = macd_line * 0.9  # ❌ WRONG
```

**Correct:**
```python
# Calculate MACD history
macd_history = []
for i in range(slow, len(prices) + 1):
    ema_fast = calculate_ema(prices[:i], fast)
    ema_slow = calculate_ema(prices[:i], slow)
    macd_history.append(ema_fast - ema_slow)

# Signal line is EMA of MACD history
signal_line = calculate_ema(macd_history, signal)  # ✅ CORRECT
```

#### RSI Calculation

```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss over N periods
```

The implementation uses a 14-period lookback by default.

## Consequences

### Positive
- Zero external dependencies for calculations
- 100% test coverage achievable
- Clear documentation of each formula
- Easy to add new indicators

### Negative
- More code to maintain than using a library
- Potential for bugs (mitigated by comprehensive tests)
- Less optimized than C-based TA-Lib

## Test Coverage

```python
class TestMACD:
    def test_macd_signal_is_not_simplified(self, prices):
        """Signal line should NOT be MACD * 0.9"""
        macd, signal, histogram = calculate_macd(prices)
        assert abs(signal - macd * 0.9) > 0.001  # ✅
```

## References

- [MACD Formula](https://www.investopedia.com/terms/m/macd.asp)
- [RSI Formula](https://www.investopedia.com/terms/r/rsi.asp)
- [Bollinger Bands](https://www.investopedia.com/terms/b/bollingerbands.asp)
