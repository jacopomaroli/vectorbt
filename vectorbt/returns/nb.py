"""Numba-compiled functions.

Provides an arsenal of Numba-compiled functions that are used by accessors and for measuring
portfolio performance. These only accept NumPy arrays and other Numba-compatible types.

```python-repl
>>> import numpy as np
>>> import vectorbt as vbt

>>> price = np.array([1.1, 1.2, 1.3, 1.2, 1.1])
>>> returns = vbt.generic.nb.pct_change_1d_nb(price)

>>> # vectorbt.returns.nb.cum_returns_1d_nb
>>> vbt.returns.nb.cum_returns_1d_nb(returns, 0)
array([0., 0.09090909, 0.18181818, 0.09090909, 0.])
```

!!! note
    vectorbt treats matrices as first-class citizens and expects input arrays to be
    2-dim, unless function has suffix `_1d` or is meant to be input to another function.
    Data is processed along index (axis 0).

    All functions passed as argument should be Numba-compiled."""

import numpy as np
from numba import njit

from vectorbt.generic import nb as generic_nb


# ############# Financial risk and performance metrics ############# #


@njit(cache=True)
def total_return_apply_nb(idxs, col, returns):
    """Calculate total return from returns."""
    return generic_nb.product_1d_nb(returns + 1) - 1


@njit(cache=True)
def cum_returns_1d_nb(returns, start_value):
    """See `empyrical.cum_returns`."""
    out = np.empty_like(returns, dtype=np.float_)
    cumprod = 1
    for i in range(returns.shape[0]):
        if not np.isnan(returns[i]):
            cumprod *= returns[i] + 1
        out[i] = cumprod
    if start_value == 0.:
        return out - 1.
    return out * start_value


@njit(cache=True)
def cum_returns_nb(returns, start_value):
    """2-dim version of `cum_returns_1d_nb`."""
    out = np.empty_like(returns, dtype=np.float_)
    for col in range(returns.shape[1]):
        out[:, col] = cum_returns_1d_nb(returns[:, col], start_value)
    return out


@njit(cache=True)
def cum_returns_final_1d_nb(returns, start_value=0.):
    """See `empyrical.cum_returns_final`."""
    out = generic_nb.product_1d_nb(returns + 1.)
    if start_value == 0.:
        return out - 1.
    return out * start_value


@njit(cache=True)
def cum_returns_final_nb(returns, start_value=0.):
    """2-dim version of `cum_returns_final_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = cum_returns_final_1d_nb(returns[:, col], start_value)
    return out


@njit
def rolling_cum_returns_final_nb(returns, window, minp, start_value=0.):
    """Rolling version of `cum_returns_final_nb`."""

    def _apply_func_nb(i, col, _returns, _start_value):
        return cum_returns_final_1d_nb(_returns, _start_value)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, start_value)


@njit(cache=True)
def annualized_return_1d_nb(returns, ann_factor):
    """See `empyrical.annual_return`."""
    end_value = cum_returns_final_1d_nb(returns, 1.)
    return end_value ** (ann_factor / returns.shape[0]) - 1


@njit(cache=True)
def annualized_return_nb(returns, ann_factor):
    """2-dim version of `annualized_return_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = annualized_return_1d_nb(returns[:, col], ann_factor)
    return out


@njit
def rolling_annualized_return_nb(returns, window, minp, ann_factor):
    """Rolling version of `annualized_return_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor):
        return annualized_return_1d_nb(_returns, _ann_factor)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor)


@njit(cache=True)
def annualized_volatility_1d_nb(returns, ann_factor, levy_alpha=2.0, ddof=1):
    """See `empyrical.annual_volatility`."""
    if returns.shape[0] < 2:
        return np.nan

    return generic_nb.nanstd_1d_nb(returns, ddof) * ann_factor ** (1.0 / levy_alpha)


@njit(cache=True)
def annualized_volatility_nb(returns, ann_factor, levy_alpha=2.0, ddof=1):
    """2-dim version of `annualized_volatility_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = annualized_volatility_1d_nb(returns[:, col], ann_factor, levy_alpha, ddof)
    return out


@njit
def rolling_annualized_volatility_nb(returns, window, minp, ann_factor, levy_alpha=2.0, ddof=1):
    """Rolling version of `annualized_volatility_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor, _levy_alpha, _ddof):
        return annualized_volatility_1d_nb(_returns, _ann_factor, _levy_alpha, _ddof)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor, levy_alpha, ddof)


@njit(cache=True)
def drawdown_1d_nb(returns):
    """Drawdown of cumulative returns."""
    cum_returns = cum_returns_1d_nb(returns, start_value=100.)
    max_returns = generic_nb.expanding_max_1d_nb(cum_returns, minp=1)
    return cum_returns / max_returns - 1


@njit(cache=True)
def drawdown_nb(returns):
    """2-dim version of `drawdown_1d_nb`."""
    out = np.empty_like(returns, dtype=np.float_)
    for col in range(returns.shape[1]):
        out[:, col] = drawdown_1d_nb(returns[:, col])
    return out


@njit(cache=True)
def max_drawdown_1d_nb(returns):
    """See `empyrical.max_drawdown`."""
    return np.min(drawdown_1d_nb(returns))


@njit(cache=True)
def max_drawdown_nb(returns):
    """2-dim version of `max_drawdown_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = max_drawdown_1d_nb(returns[:, col])
    return out


@njit
def rolling_max_drawdown_nb(returns, window, minp):
    """Rolling version of `max_drawdown_nb`."""

    def _apply_func_nb(i, col, _returns):
        return max_drawdown_1d_nb(_returns)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb)


@njit(cache=True)
def calmar_ratio_1d_nb(returns, ann_factor):
    """See `empyrical.calmar_ratio`."""
    max_drawdown = max_drawdown_1d_nb(returns)
    if max_drawdown == 0.:
        return np.nan
    annualized_return = annualized_return_1d_nb(returns, ann_factor)
    if max_drawdown == 0.:
        return np.inf
    return annualized_return / np.abs(max_drawdown)


@njit(cache=True)
def calmar_ratio_nb(returns, ann_factor):
    """2-dim version of `calmar_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = calmar_ratio_1d_nb(returns[:, col], ann_factor)
    return out


@njit
def rolling_calmar_ratio_nb(returns, window, minp, ann_factor):
    """Rolling version of `calmar_ratio_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor):
        return calmar_ratio_1d_nb(_returns, _ann_factor)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor)


@njit(cache=True)
def omega_ratio_1d_nb(returns, ann_factor, risk_free=0., required_return=0.):
    """See `empyrical.omega_ratio`."""
    if ann_factor == 1:
        return_threshold = required_return
    elif ann_factor <= -1:
        return np.nan
    else:
        return_threshold = (1 + required_return) ** (1. / ann_factor) - 1
    returns_less_thresh = returns - risk_free - return_threshold
    numer = np.sum(returns_less_thresh[returns_less_thresh > 0.0])
    denom = -1.0 * np.sum(returns_less_thresh[returns_less_thresh < 0.0])
    if denom == 0.:
        return np.inf
    return numer / denom


@njit(cache=True)
def omega_ratio_nb(returns, ann_factor, risk_free=0., required_return=0.):
    """2-dim version of `omega_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = omega_ratio_1d_nb(
            returns[:, col], ann_factor, risk_free, required_return)
    return out


@njit
def rolling_omega_ratio_nb(returns, window, minp, ann_factor, risk_free=0., required_return=0.):
    """Rolling version of `omega_ratio_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor, _risk_free, _required_return):
        return omega_ratio_1d_nb(_returns, _ann_factor, _risk_free, _required_return)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor, risk_free, required_return)


@njit(cache=True)
def sharpe_ratio_1d_nb(returns, ann_factor, risk_free=0., ddof=1):
    """See `empyrical.sharpe_ratio`."""
    if returns.shape[0] < 2:
        return np.nan

    returns_risk_adj = returns - risk_free
    mean = np.nanmean(returns_risk_adj)
    std = generic_nb.nanstd_1d_nb(returns_risk_adj, ddof)
    if std == 0.:
        return np.inf
    return mean / std * np.sqrt(ann_factor)


@njit(cache=True)
def sharpe_ratio_nb(returns, ann_factor, risk_free=0., ddof=1):
    """2-dim version of `sharpe_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = sharpe_ratio_1d_nb(returns[:, col], ann_factor, risk_free, ddof)
    return out


@njit
def rolling_sharpe_ratio_nb(returns, window, minp, ann_factor, risk_free=0., ddof=1):
    """Rolling version of `sharpe_ratio_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor, _risk_free, _ddof):
        return sharpe_ratio_1d_nb(_returns, _ann_factor, _risk_free, _ddof)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor, risk_free, ddof)


@njit(cache=True)
def downside_risk_1d_nb(returns, ann_factor, required_return=0.):
    """See `empyrical.downside_risk`."""
    adj_returns = returns - required_return
    adj_returns[adj_returns > 0] = 0
    return np.sqrt(np.nanmean(adj_returns ** 2)) * np.sqrt(ann_factor)


@njit(cache=True)
def downside_risk_nb(returns, ann_factor, required_return=0.):
    """2-dim version of `downside_risk_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = downside_risk_1d_nb(returns[:, col], ann_factor, required_return)
    return out


@njit
def rolling_downside_risk_nb(returns, window, minp, ann_factor, required_return=0.):
    """Rolling version of `downside_risk_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor, _required_return):
        return downside_risk_1d_nb(_returns, _ann_factor, _required_return)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor, required_return)


@njit(cache=True)
def sortino_ratio_1d_nb(returns, ann_factor, required_return=0.):
    """See `empyrical.sortino_ratio`."""
    if returns.shape[0] < 2:
        return np.nan

    adj_returns = returns - required_return
    average_annualized_return = np.nanmean(adj_returns) * ann_factor
    downside_risk = downside_risk_1d_nb(returns, ann_factor, required_return)
    if downside_risk == 0.:
        return np.inf
    return average_annualized_return / downside_risk


@njit(cache=True)
def sortino_ratio_nb(returns, ann_factor, required_return=0.):
    """2-dim version of `sortino_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = sortino_ratio_1d_nb(returns[:, col], ann_factor, required_return)
    return out


@njit
def rolling_sortino_ratio_nb(returns, window, minp, ann_factor, required_return=0.):
    """Rolling version of `sortino_ratio_nb`."""

    def _apply_func_nb(i, col, _returns, _ann_factor, _required_return):
        return sortino_ratio_1d_nb(_returns, _ann_factor, _required_return)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, ann_factor, required_return)


@njit(cache=True)
def information_ratio_1d_nb(returns, benchmark_rets, ddof=1):
    """See `empyrical.excess_sharpe`."""
    if returns.shape[0] < 2:
        return np.nan

    active_return = returns - benchmark_rets
    mean = np.nanmean(active_return)
    std = generic_nb.nanstd_1d_nb(active_return, ddof)
    if std == 0.:
        return np.inf
    return mean / std


@njit(cache=True)
def information_ratio_nb(returns, benchmark_rets, ddof=1):
    """2-dim version of `information_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = information_ratio_1d_nb(returns[:, col], benchmark_rets[:, col], ddof)
    return out


@njit
def rolling_information_ratio_nb(returns, window, minp, benchmark_rets, ddof=1):
    """Rolling version of `information_ratio_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets, _ddof):
        return information_ratio_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col], _ddof)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets, ddof)


@njit(cache=True)
def beta_1d_nb(returns, benchmark_rets):
    """See `empyrical.beta`."""
    if benchmark_rets.shape[0] < 2:
        return np.nan

    independent = np.where(
        np.isnan(returns),
        np.nan,
        benchmark_rets,
    )
    ind_residual = independent - np.nanmean(independent)
    covariances = np.nanmean(ind_residual * returns)
    ind_residual = ind_residual ** 2
    ind_variances = np.nanmean(ind_residual)
    if ind_variances < 1.0e-30:
        ind_variances = np.nan
    if ind_variances == 0.:
        return np.inf
    return covariances / ind_variances


@njit(cache=True)
def beta_nb(returns, benchmark_rets):
    """2-dim version of `beta_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = beta_1d_nb(returns[:, col], benchmark_rets[:, col])
    return out


@njit
def rolling_beta_nb(returns, window, minp, benchmark_rets):
    """Rolling version of `beta_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets):
        return beta_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col])

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets)


@njit(cache=True)
def alpha_1d_nb(returns, benchmark_rets, ann_factor, risk_free=0.):
    """See `empyrical.alpha`."""
    if returns.shape[0] < 2:
        return np.nan

    adj_returns = returns - risk_free
    adj_benchmark_rets = benchmark_rets - risk_free
    beta = beta_1d_nb(returns, benchmark_rets)
    alpha_series = adj_returns - (beta * adj_benchmark_rets)
    return (np.nanmean(alpha_series) + 1) ** ann_factor - 1


@njit(cache=True)
def alpha_nb(returns, benchmark_rets, ann_factor, risk_free=0.):
    """2-dim version of `alpha_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = alpha_1d_nb(returns[:, col], benchmark_rets[:, col], ann_factor, risk_free)
    return out


@njit
def rolling_alpha_nb(returns, window, minp, benchmark_rets, ann_factor, risk_free=0.):
    """Rolling version of `alpha_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets, _ann_factor, _risk_free):
        return alpha_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col], _ann_factor, _risk_free)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets, ann_factor, risk_free)


@njit(cache=True)
def tail_ratio_1d_nb(returns):
    """See `empyrical.tail_ratio`."""
    returns = returns[~np.isnan(returns)]
    if len(returns) < 1:
        return np.nan
    perc_95 = np.abs(np.percentile(returns, 95))
    perc_5 = np.abs(np.percentile(returns, 5))
    if perc_5 == 0.:
        return np.inf
    return perc_95 / perc_5


@njit(cache=True)
def tail_ratio_nb(returns):
    """2-dim version of `tail_ratio_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = tail_ratio_1d_nb(returns[:, col])
    return out


@njit
def rolling_tail_ratio_nb(returns, window, minp):
    """Rolling version of `tail_ratio_nb`."""

    def _apply_func_nb(i, col, _returns):
        return tail_ratio_1d_nb(_returns)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb)


@njit(cache=True)
def value_at_risk_1d_nb(returns, cutoff=0.05):
    """See `empyrical.value_at_risk`."""
    returns = returns[~np.isnan(returns)]
    if len(returns) < 1:
        return np.nan
    return np.percentile(returns, 100 * cutoff)


@njit(cache=True)
def value_at_risk_nb(returns, cutoff=0.05):
    """2-dim version of `value_at_risk_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = value_at_risk_1d_nb(returns[:, col], cutoff)
    return out


@njit
def rolling_value_at_risk_nb(returns, window, minp, cutoff=0.05):
    """Rolling version of `value_at_risk_nb`."""

    def _apply_func_nb(i, col, _returns, _cutoff):
        return value_at_risk_1d_nb(_returns, _cutoff)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, cutoff)


@njit(cache=True)
def cond_value_at_risk_1d_nb(returns, cutoff=0.05):
    """See `empyrical.cond_value_at_risk`."""
    cutoff_index = int((len(returns) - 1) * cutoff)
    return np.mean(np.partition(returns, cutoff_index)[:cutoff_index + 1])


@njit(cache=True)
def cond_value_at_risk_nb(returns, cutoff=0.05):
    """2-dim version of `cond_value_at_risk_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = cond_value_at_risk_1d_nb(returns[:, col], cutoff)
    return out


@njit
def rolling_cond_value_at_risk_nb(returns, window, minp, cutoff=0.05):
    """Rolling version of `cond_value_at_risk_nb`."""

    def _apply_func_nb(i, col, _returns, _cutoff):
        return cond_value_at_risk_1d_nb(_returns, _cutoff)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, cutoff)


@njit(cache=True)
def capture_1d_nb(returns, benchmark_rets, ann_factor):
    """See `empyrical.capture`."""
    annualized_return1 = annualized_return_1d_nb(returns, ann_factor)
    annualized_return2 = annualized_return_1d_nb(benchmark_rets, ann_factor)
    if annualized_return2 == 0.:
        return np.inf
    return annualized_return1 / annualized_return2


@njit(cache=True)
def capture_nb(returns, benchmark_rets, ann_factor):
    """2-dim version of `capture_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = capture_1d_nb(returns[:, col], benchmark_rets[:, col], ann_factor)
    return out


@njit
def rolling_capture_nb(returns, window, minp, benchmark_rets, ann_factor):
    """Rolling version of `capture_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets, _ann_factor):
        return capture_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col], _ann_factor)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets, ann_factor)


@njit(cache=True)
def up_capture_1d_nb(returns, benchmark_rets, ann_factor):
    """See `empyrical.up_capture`."""
    returns = returns[benchmark_rets > 0]
    benchmark_rets = benchmark_rets[benchmark_rets > 0]
    if returns.shape[0] < 1:
        return np.nan
    annualized_return1 = annualized_return_1d_nb(returns, ann_factor)
    annualized_return2 = annualized_return_1d_nb(benchmark_rets, ann_factor)
    if annualized_return2 == 0.:
        return np.inf
    return annualized_return1 / annualized_return2


@njit(cache=True)
def up_capture_nb(returns, benchmark_rets, ann_factor):
    """2-dim version of `up_capture_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = up_capture_1d_nb(returns[:, col], benchmark_rets[:, col], ann_factor)
    return out


@njit
def rolling_up_capture_nb(returns, window, minp, benchmark_rets, ann_factor):
    """Rolling version of `up_capture_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets, _ann_factor):
        return up_capture_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col], _ann_factor)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets, ann_factor)


@njit(cache=True)
def down_capture_1d_nb(returns, benchmark_rets, ann_factor):
    """See `empyrical.down_capture`."""
    returns = returns[benchmark_rets < 0]
    benchmark_rets = benchmark_rets[benchmark_rets < 0]
    if returns.shape[0] < 1:
        return np.nan
    annualized_return1 = annualized_return_1d_nb(returns, ann_factor)
    annualized_return2 = annualized_return_1d_nb(benchmark_rets, ann_factor)
    if annualized_return2 == 0.:
        return np.inf
    return annualized_return1 / annualized_return2


@njit(cache=True)
def down_capture_nb(returns, benchmark_rets, ann_factor):
    """2-dim version of `down_capture_1d_nb`."""
    out = np.empty(returns.shape[1], dtype=np.float_)
    for col in range(returns.shape[1]):
        out[col] = down_capture_1d_nb(returns[:, col], benchmark_rets[:, col], ann_factor)
    return out


@njit
def rolling_down_capture_nb(returns, window, minp, benchmark_rets, ann_factor):
    """Rolling version of `down_capture_nb`."""

    def _apply_func_nb(i, col, _returns, _benchmark_rets, _ann_factor):
        return down_capture_1d_nb(_returns, _benchmark_rets[i + 1 - len(_returns):i + 1, col], _ann_factor)

    return generic_nb.rolling_apply_nb(
        returns, window, minp, _apply_func_nb, benchmark_rets, ann_factor)
