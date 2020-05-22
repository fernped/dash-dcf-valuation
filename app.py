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
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

from layout_helpers import *
from finance_helpers import *


#
pio.templates["custom"] = go.layout.Template(
    layout=go.Layout(
        margin=dict(l=50, r=20, t=40, b=20),
        legend=dict(orientation='h'),
        colorway=["#E69F00", "#56B4E9", "#009E73", "#F0E442", 
                  "#0072B2", "#D55E00", "#CC79A7", "#999999"]
    )
)
pio.templates.default = 'plotly_white+custom'

slider_tooptip = { 'always_visible': True, 'placement': 'right' }


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
        marks={i*5: {'label': f"{i*5}"} for i in range(5)},
        tooltip=slider_tooptip),
    html.Label('Revenue (base year)'),
    dcc.Input(id='base_revenue', type='number', value=623, className='form-control'),
    html.Label('Adjusted EBIT (base year)'),
    dcc.Input(id='base_ebit', type='number', value=61, className='form-control'),
    html.Label('Tax Rate (%)'),
    dcc.Slider(id='taxrate', min=0, max=100, value=25, step=1,
        marks=percent_marks,
        tooltip=slider_tooptip),
    html.Label('Short-term revenue CAGR (%)'),
    dcc.Slider(id='st_cagr', min=0, max=100, value=50, step=1,
        marks=percent_marks,
        tooltip=slider_tooptip),
    html.Label('Long-term revenue CAGR (%)'),
    dcc.Slider(id='lt_cagr', min=0, max=100, value=1, step=1,
        marks=percent_marks,
        tooltip=slider_tooptip),
    html.Label('Long-term EBIT margin (%)'),
    dcc.Slider(id='lt_margin', min=0, max=100, value=22, step=1,
        marks=percent_marks,
        tooltip=slider_tooptip),
    html.Label('Reinvestment sales to capital ratio'),
    dcc.Slider(id='reinvest_ratio', min=0, max=10, value=2.5, step=0.1,
        marks={i: {'label': f"{i}"} for i in range(11)},
        tooltip=slider_tooptip),

    html.Label('WACC (%)'),
    dcc.Slider(id='wacc', min=0, max=100, value=7.7, step=0.1,
        marks=percent_marks,
        tooltip=slider_tooptip),
    html.Label('Net Debt and value adjustments'),
    dcc.Input(id='netdebt', type='number', value=738, className='form-control'),
    html.Label('Number of shares outstanding'),
    dcc.Input(id='numshares', type='number', value=276, className='form-control'),
    html.Label('Current share price'),
    dcc.Input(id='current_price', type='number', value=113.75, className='form-control')
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
     gen_card('', 'value_pershare_card','Value per Share'),
     gen_card('', 'implicit_irr', 'Implicit IRR')],
    [table],
    [dcc.Graph(id='table_plot'),
     dcc.Graph(id='npv_plot')]
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
     Output('value_pershare_card', 'children'),
     Output('implicit_irr', 'children')],
    [Input('forecast_data', 'children'),
     Input('wacc', 'value'),
     Input('lt_cagr', 'value'),
     Input('netdebt', 'value'),
     Input('numshares', 'value'),
     Input('current_price', 'value')])
def update_cards(data, wacc, lt_cagr, netdebt, numshares, current_price):
    df = pd.read_json(data, orient='split')
    cashflows = df['Free Cash Flow']
    firm_value = npv(wacc, cashflows, lt_cagr)
    # Calculate equity value as firm value minus net debt and adjustments
    equity_value = firm_value - netdebt
    # Calculate value per share
    value_pershare = equity_value / numshares
    # Calculate implicit IRR
    mkt_cap = numshares * current_price
    implicit_irr = irr(cashflows, mkt_cap + netdebt, lt_cagr)
    # Return
    return round(firm_value, 0), round(equity_value, 0), \
        round(value_pershare, 2), round(implicit_irr, 2)


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

    #
    colnames = df.columns[np.array(row_ids) + 1]
    #
    df = df.set_index('Year')[colnames].reset_index().melt('Year')

    # Display variable name if only one selected
    title = 'Forecasts'
    if len(row_ids) == 1:
        title = colnames[0] + ' ' + title
    return px.bar(df, barmode='group', title=title,
        x='Year', y='value', color='variable',
        labels={'Year':'','value':'', 'variable':''})

# ----
@app.callback(
    Output('npv_plot', 'figure'),
    [Input('forecast_data', 'children'),
     Input('wacc', 'value'),
     Input('lt_cagr', 'value'),
     Input('netdebt', 'value'),
     Input('numshares', 'value'),
     Input('current_price', 'value')])
def update_npv_plot(data, wacc, lt_cagr, netdebt, numshares, current_price):
    df = pd.read_json(data, orient='split')
    cfs = df['Free Cash Flow']
    # Create WACC vector
    waccs = np.arange(lt_cagr+1, wacc*2+1, .1)
    # Calculate firm value for each WACC
    firm_values = np.array([npv(r, cfs, lt_cagr) for r in waccs])
    # Calculate share price
    share_prices = (firm_values - netdebt) / numshares
    # Build plot
    line_style = dict(color='#999999', dash='dot')
    fig = px.line(title='Share Price x WACC', x=waccs, y=share_prices,
        labels={'x':'WACC','y':'Share Price'})
    fig.add_shape(type='line', line=line_style,
        x0=wacc, y0=share_prices.min(),
        x1=wacc, y1=share_prices.max())
    fig.add_shape(type='line', line=line_style,
        x0=waccs.min(), y0=current_price,
        x1=waccs.max(), y1=current_price)
    # Return Plot data
    return fig


# ----
if __name__ == '__main__':
    app.run_server(debug=True)



