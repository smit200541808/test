import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from datetime import datetime
from pymongo import MongoClient
import re

def connect_to_mongodb():
    client = MongoClient('mongodb+srv://200541808:IqqPvMpTys2uLQWa@cluster1111.p6rdc1z.mongodb.net/')
    return client['sales_database']

def get_combined_data(db, min_date, max_date):
    collection_names = db.list_collection_names()
    
    date_objects = [datetime.strptime(re.search(r'\d{4}-\d{2}-\d{2}', name).group(0), '%Y-%m-%d') for name in collection_names]
    
    combined_data = []
    for name, date_object in zip(collection_names, date_objects):
        if min_date <= date_object <= max_date:
            collection = db[name]
            data = list(collection.find())
            combined_data.extend(data)
    
    df = pd.DataFrame(combined_data)
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Total Sales'] = df['Quantity'] * df['Price']
    
    return df

def get_top_n_items(data, column, n):
    return data.groupby(column)['Total Sales'].sum().nlargest(n)

def create_pie_chart(data, title, template):
    return px.pie(data, values='Total Sales', names=data.index, title=title, template=template)

def create_bar_chart(data, x, y, title, labels=None):
    return px.bar(data, x=x, y=y, title=title, labels=labels, template='plotly_dark')

def create_line_chart(data, x, y, color, title,template):
    return px.line(data, x=x, y=y, color=color, title=title, template=template)

def create_line_chart_test(data, x, y, title,template):
    return px.line(data, x=x, y=y, title=title, template=template)

def create_choropleth_map(data, locations, locationmode, color, title, color_continuous_scale):
    return px.choropleth(data, locations=locations, locationmode=locationmode, color=color,
                         title=title, color_continuous_scale=color_continuous_scale, template='plotly_dark')

def create_pie_chart_figure(df, selection,template):
    if selection == 'Country':
        top_10_data = get_top_n_items(df, 'Country', 10)
        #print(top_10_data)
        title = 'Top 10 Countries by Sales'

    elif selection == 'Product':
        top_10_data=get_top_n_items(df,'ProductName',10)
        #print(top_10_data)
        title = 'Top 10 Products by Sales'

    else:
        # If neither 'Country' nor 'Product' is selected, return country pie chart by default
        top_10_data = get_top_n_items(df, 'Country', 10)
        title = 'Top 10 Countries by Sales'
    return create_pie_chart(top_10_data, title,template=template)

def create_bar_chart_figure(df):
    df['Total Sales'] = df['Quantity'] * df['Price']
    total_sales_per_product = df.groupby('ProductName')['Total Sales'].sum().reset_index()
    top_10_products_bar = total_sales_per_product.sort_values(by='Total Sales', ascending=False).head(10)
    return create_bar_chart(top_10_products_bar, 'ProductName', 'Total Sales', 'Total Sales for Top 10 Products', {'Total Sales': 'Total Sales'})

def create_line_chart_figure(df):
    total_sales_per_product_over_time = df.groupby(['ProductName', 'Date'])['Quantity'].sum() * df.groupby(['ProductName', 'Date'])['Price'].sum()
    top_10_products_line = total_sales_per_product_over_time.groupby('ProductName').sum().nlargest(10).index
    filtered_data_line = total_sales_per_product_over_time[total_sales_per_product_over_time.index.get_level_values('ProductName').isin(top_10_products_line)]
    filtered_data_line = filtered_data_line.reset_index().rename(columns={0: 'Total Sales'})
    return create_line_chart(filtered_data_line, 'Date', 'Total Sales', 'ProductName', 'Total Sales Over Time for Top 10 Products',template='plotly_dark')

def create_choropleth_map_figure(df):
    total_sales_per_country = df.groupby('Country')['Total Sales'].sum().reset_index()
    return create_choropleth_map(total_sales_per_country, 'Country', 'country names', 'Total Sales', 'Total Sales by Country', 'Viridis')

def create_line_chart_quantity_over_time_figure(df):
    total_sales_per_product_over_time = df.groupby(['ProductName', 'Date'])['Quantity'].sum().reset_index()
    total_sales_per_product_over_time.rename(columns={0: 'Quantity'}, inplace=True)
    top_10_products_quantity = total_sales_per_product_over_time.groupby('ProductName')['Quantity'].sum().nlargest(10).index
    filtered_data_quantity = total_sales_per_product_over_time[total_sales_per_product_over_time['ProductName'].isin(top_10_products_quantity)]
    return create_line_chart(filtered_data_quantity, 'Date', 'Quantity', 'ProductName', 'Quantity Sold Over Time for Top 10 Products',template='plotly_dark')

def create_dash_app_layout(df):
    # Custom styling for charts
    chart_style = {
        'height': '400px',
        #'margin': {'t': 10, 'b': 10, 'r': 10, 'l': 10},
        'template': 'plotly_dark',
    }

    # Dark mode CSS for the entire layout
    dark_mode_css = {
        'backgroundColor': '#1E1E1E',
        'color': 'white',
    }

    # Set overall style for the app
    return html.Div([
        html.H1("Sales Dashboard", style={'color': 'white', 'text-align': 'center', 'margin-top': '20px'}),

        html.Div([
            html.H3(f"Grand Total Sales: ${df['Total Sales'].sum():,.2f}", style={'color': 'white'}),
        ], style={'text-align': 'right', 'margin-bottom': '20px'}),

        # Top row with World Map, Bar Chart, and Pie Chart
        html.Div([
            dcc.Graph(id='world-map', figure=create_choropleth_map_figure(df), className='four columns', style={**chart_style,'width': '40%', **dark_mode_css}),
            dcc.Graph(id='bar-chart', figure=create_bar_chart_figure(df), className='four columns', style={'backgroundColor': 'black','width': '50%'}),
        ], className='row'),

        # Second row with Pie Chart
        html.Div([
            dcc.Dropdown(
                id='pie-chart-dropdown',
                options=[
                    {'label': 'Top 10 Countries by Sales', 'value': 'Country'},
                    {'label': 'Top 10 Products by Sales', 'value': 'Product'},
                ],
                value='Country',
                style={'width': '50%', **dark_mode_css, 'color': 'black'},  # Change the text color for better visibility
            ),
            dcc.Graph(id='pie-chart', style={**chart_style, **dark_mode_css}),
        ], className='row'),

        # Third row with Quantity Line Chart and Top Sales Line Chart
        html.Div([
            dcc.Dropdown(
                id='product-dropdown',
                options=[{'label': product, 'value': product} for product in df['ProductName'].unique()],
                value=df['ProductName'].unique()[0],  # Set the default selected product
                style={'width': '50%', **dark_mode_css, 'color': 'black'},  # Change the text color for better visibility
            ),
            dcc.Graph(id='quantity-line-chart', figure=create_line_chart_quantity_over_time_figure(df), className='six columns', style={**chart_style, 'width': '40%',**dark_mode_css}),
            dcc.Graph(id='top-sales-line-chart', figure=create_line_chart_figure(df), className='six columns', style={**chart_style,'width': '40%', **dark_mode_css}),
        ], className='row'),

        # Bottom row with Quantity Over Time and Line Chart
        html.Div([
            dcc.Graph(id='quantity-over-time', figure=create_line_chart_quantity_over_time_figure(df), style={**chart_style, 'width': '100%', **dark_mode_css}),
            dcc.Graph(id='line-chart', figure=create_line_chart_figure(df), style={**chart_style, 'width': '100%', **dark_mode_css}),
        ], className='row'),

    ], style={**dark_mode_css, 'padding': '20px'})  # Set background color and text color for the entire app


def run_dash_app(app):
    app.run_server(debug=True)

def main():
    # MongoDB Connection
    db = connect_to_mongodb()
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    # Date Range
    min_date = datetime(2023, 12, 1)
    max_date = datetime.now()

    # Combined Data
    df = get_combined_data(db, min_date, max_date)

    # Initialize the Dash app
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    # Set layout
    app.layout = create_dash_app_layout(df)

    # Callback to update pie chart based on dropdown selection
    @app.callback(
        Output('pie-chart', 'figure'),
        [Input('pie-chart-dropdown', 'value')]
    )
    def update_pie_chart(selection):
        return create_pie_chart_figure(df, selection,template='plotly_dark')
    
    # Callback to update quantity-over-time line chart based on selected product
    @app.callback(
        Output('quantity-line-chart', 'figure'),
        [Input('product-dropdown', 'value')]
    )
    def update_quantity_line_chart(selected_product):
        filtered_data_quantity = df[df['ProductName'] == selected_product].groupby(['Date'])['Quantity'].sum().reset_index()
        #print(filtered_data_quantity)
        return create_line_chart_test(filtered_data_quantity, 'Date', 'Quantity', f'Quantity Sold Over Time for {selected_product}',template='plotly_dark')

    # Callback to update top sales line chart based on selected product
    @app.callback(
        Output('top-sales-line-chart', 'figure'),
        [Input('product-dropdown', 'value')]
    )
    def update_top_sales_line_chart(selected_product):
        filtered_data_top_sales = df[df['ProductName'] == selected_product].groupby(['Date'])['Total Sales'].sum().reset_index()
        #print(filtered_data_top_sales)
        return create_line_chart_test(filtered_data_top_sales, 'Date', 'Total Sales', f'Top Sales Over Time for {selected_product}',template='plotly_dark')

    # Run the app
    run_dash_app(app)

if __name__ == '__main__':
    main()
