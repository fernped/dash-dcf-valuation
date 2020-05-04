import numpy as np



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


