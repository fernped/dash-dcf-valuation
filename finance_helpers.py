import numpy as np
from scipy import optimize


def npv(wacc, cashflows, perp_growth=0):
    N = len(cashflows)
    # Repeat WACC as a series
    wacc_series = np.repeat(wacc, N)
    # Calculate discount factor
    discount_factor = np.cumprod(1 / (1+wacc_series/100))
    # Calculate PV of cash flows
    pv_cf = np.sum(np.array(cashflows) * discount_factor)
    # Calculate terminal value
    terminal_cashflow = cashflows[N - 1] * (1 + perp_growth/100)
    terminal_value = terminal_cashflow / ((wacc-perp_growth) / 100)
    # PV of Terminal Value
    pv_terminal_value = terminal_value * discount_factor[N - 1]
    # Return PV of Cash Flows + PV of Terminal Value
    return pv_cf + pv_terminal_value


def irr(cashflows, investment=0, perp_growth=0):
    x = optimize.fsolve(
        lambda x: (npv(x, cashflows, perp_growth) - investment), perp_growth+1)[0]
    return x
