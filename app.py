# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ALL
import dash_table
from dash_table.Format import Format, Scheme, Sign
from layout_helpers import *


# APP INITIALIZATION
app = dash.Dash(
    __name__,
    external_stylesheets=["https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"],
    external_scripts=[
        'https://code.jquery.com/jquery-3.4.1.slim.min.js',
        'https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js'
    ]
    )

server = app.server


# SIDEBAR ----
percent_marks = {i*20: {'label': f"{i*20}"} for i in range(6)}
sidebar = html.Div([
    html.Label('Forecast horizon (year)'),
    dcc.Slider(id='horizon', min=1, max=20, value=10, step=1,
        marks={i*5: {'label': f"{i*5}"} for i in range(5)}),
    html.Label('Revenue (base year)'),
    dcc.Input(id='base_revenue', type='number', value=623, className='form-control'),
    html.Label('Adjusted EBIT (base year)'),
    dcc.Input(id='base_ebit', type='number', value=61, className='form-control'),
    html.Label('Tax Rate (%)'),
    dcc.Slider(id='taxrate', min=0, max=100, value=25, step=1,
        marks=percent_marks),
    html.Label('Short-term revenue CAGR (%)'),
    dcc.Slider(id='st_cagr', min=0, max=100, value=50, step=1,
        marks=percent_marks),
    html.Label('Long-term revenue CAGR (%)'),
    dcc.Slider(id='lt_cagr', min=0, max=100, value=1, step=1,
        marks=percent_marks),
    html.Label('Long-term EBIT margin (%)'),
    dcc.Slider(id='lt_margin', min=0, max=100, value=22, step=1,
        marks=percent_marks),
    html.Label('Reinvestment sales to capital ratio'),
    dcc.Slider(id='reinvest_ratio', min=0, max=10, value=2.5, step=0.1,
        marks={i: {'label': f"{i}"} for i in range(11)}),

    html.Label('WACC (%)'),
    dcc.Slider(id='wacc', min=0, max=100, value=7.7, step=0.1,
        marks=percent_marks),
    html.Label('Net Debt and value adjustments'),
    dcc.Input(id='netdebt', type='number', value=738, className='form-control'),
    html.Label('Number of shares outstanding'),
    dcc.Input(id='numshares', type='number', value=276, className='form-control'),
])



# TABLE ----
table = dash_table.DataTable(id='forecast_table', data=[], columns=[],
    row_selectable='multi',
    style_as_list_view=True,
    style_header={'fontWeight': 'bold'},
    style_cell_conditional=[
        {'if': {'column_id':''}, 'textAlign':'left'}
    ])



# MAIN GRID ----
grid = gen_grid([
    [gen_card('', 'firm_value_card','Firm Value'),
     gen_card('', 'equity_value_card','Equity Value'),
     gen_card('', 'value_pershare_card','Value per Share')],
    [table],
    [dcc.Graph(id='table_plot')]
])


# LAYOUT ----
app.title = "DCF Valuation"
navbar = gen_navbar(app.title,
    {'Github': 'https://github.com/danielrmt/dash-dcf-valuation'})
hidden = html.Div(
    [html.Div([], id=s) for s in ['forecast_data']],
    style={'display': 'none'})
app.layout = html.Div([
    navbar,
    gen_sidebar_layout(sidebar, grid, 3, mainClass='container-fluid'),
    hidden])



# CALLBACKS ----
@app.callback(
    [Output('forecast_data', 'children')],
    [Input(id, 'value') for id in ['horizon', 'base_revenue', 'base_ebit',
                                   'taxrate', 'st_cagr', 'lt_cagr', 'lt_margin',
                                   'reinvest_ratio']])
def update_forecast(horizon, base_revenue, base_ebit, taxrate, st_cagr, lt_cagr,
        lt_margin, reinvest_ratio):
    n_per = horizon
    conv_per = int(horizon / 2)
    # Initialize dataframe
    per_id = np.arange(n_per)+1
    year = int(datetime.date.today().year) + per_id
    df = pd.DataFrame(columns=['Year'], data=year)
    # Calculate weights between long-term / short-term used for convergence
    cagr_weight = (conv_per - per_id) / (conv_per - n_per)
    cagr_weight = np.maximum(cagr_weight, 0)
    cagr_weight = np.minimum(cagr_weight, 1)
    # Calculate growth as weighted average between long term and short term
    growth =  cagr_weight * lt_cagr + (1 - cagr_weight) * st_cagr
    # Calculate revenue
    df['Revenue'] = base_revenue * np.cumprod(1 + growth/100)
    df['Growth'] = growth
    # Calculate margin as weighted average between long term and short term
    mg_weight = 1 - np.flip(cagr_weight)
    base_margin = base_ebit / base_revenue * 100
    margin = mg_weight * lt_margin + (1 - mg_weight) * base_margin
    # Calculate Opex and EBIT
    df['Opex'] = - (1 - margin / 100) * df['Revenue']
    df['EBIT'] = df['Revenue'] + df['Opex']
    df['Margin'] = margin
    # Calculate Taxes and NOPAT
    df['Taxes'] = -df['EBIT'] * taxrate / 100
    df['NOPAT'] = df['EBIT'] + df['Taxes']
    # Calculate reinvestment
    lag_revenue = df['Revenue'].shift(fill_value=base_revenue)
    revenue_diff = df['Revenue'] - lag_revenue
    df['Reinvestment'] = - revenue_diff / reinvest_ratio
    # Calculate free cash flow
    df['Free Cash Flow'] = df['NOPAT'] + df['Reinvestment']
    # Calculate invested capital and ROIC
    df['Invested Capital'] = df['Revenue'] / reinvest_ratio
    df['ROIC'] = df['NOPAT'] / df['Invested Capital'] * 100
    # Return as JSON
    return [df.to_json(date_format='iso', orient='split')]



@app.callback(
    [Output('firm_value_card', 'children'),
     Output('equity_value_card', 'children'),
     Output('value_pershare_card', 'children')],
    [Input('forecast_data', 'children'),
     Input('wacc', 'value'),
     Input('lt_cagr', 'value'),
     Input('netdebt', 'value'),
     Input('numshares', 'value')])
def update_cards(data, wacc, lt_cagr, netdebt, numshares):
    df = pd.read_json(data, orient='split')
    # Calculate discount factor $1 / (1 + r)^t$
    df['WACC'] = wacc
    df['DiscountFactor'] = np.cumprod(1 / (1 + df['WACC']/100))
    # Calculate discounted cash flow
    df['DCF'] = df['DiscountFactor'] * df['Free Cash Flow']
    # Calculate terminal value as $CF_T * (1+g_T) / (r - g_T)$
    terminal_value = df['Free Cash Flow'].tail(1) * (1 + lt_cagr/100) / ((wacc-lt_cagr)/100)
    # Calculate present value of terminal value
    pv_terminal_value = terminal_value * df['DiscountFactor'].tail(1)
    # Calculate firm value as sum of discounted cash flow + pv of terminal value
    firm_value = df['DCF'].sum() + pv_terminal_value
    # Calculate equity value as firm value minus net debt and adjustments
    equity_value = firm_value - netdebt
    # Calculate value per share
    value_pershare = equity_value / numshares
    # Return
    return round(firm_value, 0), round(equity_value, 0), \
        round(value_pershare, 2)


numeric_fmt = Format(precision=1, 
            scheme=Scheme.fixed,
            sign=Sign.parantheses,)
@app.callback(
    [Output('forecast_table', 'data'),
     Output('forecast_table', 'columns')],
    [Input('forecast_data', 'children')])
def update_table(data):
    df = pd.read_json(data, orient='split')
    # Transpose table
    df = df.set_index('Year').T.reset_index().rename(columns={'index':''})
    return df.to_dict('records'), \
        [{'name':str(s),'id':str(s),'type':'numeric',
         'format':numeric_fmt} for s in df.columns]


@app.callback(
    Output('table_plot', 'figure'),
    [Input('forecast_table', 'selected_rows'),
     Input('forecast_data', 'children')])
def update_plot(row_ids, data):
    # Sanitize input
    if row_ids is None or len(row_ids) == 0:
        row_ids = [3,8]
    # Read data
    df = pd.read_json(data, orient='split')
    # X axis is the same 
    x = pd.to_numeric(df['Year'])
    # Initialize plot array
    plot_data = []
    # For each selected row
    for row_id in row_ids:
        # Get variable name
        colname = df.columns[row_id+1]
        # Locate apropriate variable
        y = df.iloc[:,row_id+1]
        # Invert sign for expense columns
        if colname == 'Taxes' or colname == 'Opex' or colname == 'Reinvestment':
            y = - y
        # Use line for relative values and bars for absolute values
        if colname == 'Margin' or colname == 'Growth' or colname == 'ROIC':
            plot_type = 'lines+markers'
        else:
            plot_type = 'bar'
        # Append to plot data
        plot_data.append({'x': x, 'y': y, 'name': colname, 'type':plot_type})
    # Display variable name if only one selected
    title = 'Forecasts'
    if len(row_ids) == 1:
        title = colname + ' ' + title
    return {'data': plot_data, 'layout':{'title':title}}

# ----


# ----
if __name__ == '__main__':
    app.run_server(debug=True)



