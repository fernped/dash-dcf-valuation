# DCF Valuation in Python and Dash

This project is a proof-of-concept of how Python can replace Excel spreadsheets
for valuation and forecasting financial statements.

The app has inspiration in `fcffsimpleginzu.xlsx` spreadsheet by
Aswath Damodaran, with simplified features. This file is available at
[his website](http://pages.stern.nyu.edu/~adamodar/New_Home_Page/spreadsh.htm).

The forecast methods for each of the main lines of the cashflow are:

- **Revenue**: constant growth (input) on the short term, converges 
to long term growth during medium term

- **EBIT**: during short term, the margin converges to medium term margin, and
stays constant for medium and long term

- **Taxes**: constant rate for all the forecast horizone

- **Reinvestment**: constant sales to capital ratio for all forecast horizon

Based on those drivers, the app can forecast the Free Cash Flow.

The app is very simple, and may seem overkill compared to a spreadsheet.
This is just a proof-of-concept, but using Python would allow us to:

- Use advanced forecasting methods for revenue or expenses (time series methods
or recurrent neural networks)

- Automate different possible inputs for sensivity monte carlo analysis

- Embrace the uncertainty instead of deterministic point forecasts
(input being priors distributions of hyperparameters and output being
a posterior distribution of cashflows and share price)

- Automate forecasts for multiple companies

- Integrate the forecast in a pipeline that uses external data on 
  macroeconomics (new GDP and inflation forecasts are released every week on
  Brazil) or sentiments from social networks for forecasting




