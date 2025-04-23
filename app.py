import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
from datetime import datetime

# Initialize the Dash app with a modern theme
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Custom CSS for enhanced styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>SwiftShop Analytics</title>
        {%favicon%}
        {%css%}
        <style>
            /* Custom CSS */
            body {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
            }
            .dashboard-header {
                background: linear-gradient(135deg, #3a7bd5, #00d2ff);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .header-title {
                color: white;
                font-weight: 600;
                margin: 0;
            }
            .header-subtitle {
                color: rgba(255, 255, 255, 0.85);
                font-size: 1rem;
                margin-top: 5px;
            }
            .card {
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
                transition: transform 0.3s ease;
                margin-bottom: 20px;
            }
            # .card:hover {
            #     transform: translateY(-5px);
            #     box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12);
            # }
            .kpi-card {
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                height: 100%;
            }
            .kpi-title {
                font-size: 0.9rem;
                font-weight: 500;
                color: #6c757d;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }
            .kpi-value {
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 5px;
            }
            .filters-card {
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            }
            .export-btn {
                width: 100%;
                margin-top: 15px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .export-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            .dash-graph {
                border-radius: 8px;
                overflow: hidden;
            }
            .section-title {
                color: #495057;
                font-weight: 600;
                margin-bottom: 15px;
                padding-bottom: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            .card-content {
                padding: 20px;
            }
            /* Enhance table styling */
            .dash-table-container {
                margin-top: 10px;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            }
            .dash-spreadsheet-container {
                box-shadow: none !important;
            }
            .dash-spreadsheet-menu {
                background-color: #f8f9fa !important;
            }
            .dash-header {
                background-color: #f1f3f5 !important;
                font-weight: 600 !important;
                color: #495057 !important;
            }
            .dash-cell {
                padding: 10px 12px !important;
                color: #495057 !important;
            }
            /* Date picker customization */
            .DateInput_input {
                font-size: 0.9rem !important;
                padding: 7px 10px !important;
            }
            .DateRangePickerInput {
                border-radius: 6px !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Load and process data
def load_data():
    try:
        df = pd.read_csv('swiftshop_sales_data.csv')
        
        # Convert order_date to datetime
        df['order_date'] = pd.to_datetime(df['order_date'])
        
        # Extract year and month for time-based analysis
        df['year'] = df['order_date'].dt.year
        df['month'] = df['order_date'].dt.month
        df['month_year'] = df['order_date'].dt.strftime('%Y-%m')
        
        # Handle missing ratings
        df['payment_method'] = df['payment_method'].fillna("Unknown")
        
        median_rating_by_product = df.groupby('product_id')['customer_rating'].median().apply(np.round)
        for idx in df[df['customer_rating'].isna()].index:
            product = df.loc[idx, 'product_id']
            if product in median_rating_by_product and pd.notna(median_rating_by_product[product]):
                df.loc[idx, 'customer_rating'] = median_rating_by_product[product]
            else:
                # If no median for product, use overall median
                df.loc[idx, 'customer_rating'] = np.round(df['customer_rating'].median())

        # This block fills missing 'customer_region' values based on the most common region (mode) used by the same 'customer_id'. If the customer's region cannot be determined, it sets it as 'Unknown'.

        region_by_customer = df.groupby('customer_id')['customer_region'].agg(lambda x: x.mode()[0] if not x.mode().empty and pd.notna(x.mode()[0]) else np.nan)
        for idx in df[df['customer_region'].isna()].index:
            customer = df.loc[idx, 'customer_id']
            if customer in region_by_customer and pd.notna(region_by_customer[customer]):
                df.loc[idx, 'customer_region'] = region_by_customer[customer]
            else:
                df.loc[idx, 'customer_region'] = 'Unknown'        
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# Define unique values for filters
regions = sorted(df['customer_region'].unique())
categories = sorted(df['category'].unique())
date_range = [df['order_date'].min(), df['order_date'].max()]

# Create a custom graph template for consistency
custom_template = go.layout.Template()
custom_template.layout.colorway = ['#3a7bd5', '#00d2ff', '#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c', '#34495e', '#f1c40f']
custom_template.layout.font = dict(family="Segoe UI, Roboto, sans-serif", size=12, color="#495057")
custom_template.layout.paper_bgcolor = "white"
custom_template.layout.plot_bgcolor = "white"
custom_template.layout.xaxis = dict(gridcolor="#f5f5f5", zerolinecolor="#f5f5f5")
custom_template.layout.yaxis = dict(gridcolor="#f5f5f5", zerolinecolor="#f5f5f5")
custom_template.layout.legend = dict(orientation="h", y=-0.2)
custom_template.layout.margin = dict(l=40, r=40, t=50, b=50)

# Dashboard layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("SwiftShop Sales Dashboard", className="header-title"),
                html.P("Interactive sales performance monitoring system", className="header-subtitle"),
            ], className="dashboard-header")
        ])
    ]),
    
    # KPIs Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.P("TOTAL REVENUE", className="kpi-title"),
                    html.H2(id="total-sales", className="kpi-value"),
                    html.P("Across all selected filters", className="text-muted")
                ], className="kpi-card")
            ], className="card")
        ], width=4),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.P("AVERAGE ORDER VALUE", className="kpi-title"),
                    html.H2(id="avg-order-value", className="kpi-value"),
                    html.P("Customer spend per transaction", className="text-muted")
                ], className="kpi-card")
            ], className="card")
        ], width=4),
        
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.P("CUSTOMER SATISFACTION", className="kpi-title"),
                    html.H2(id="avg-rating", className="kpi-value"),
                    html.P("Average rating (1-5 scale)", className="text-muted")
                ], className="kpi-card")
            ], className="card")
        ], width=4)
    ]),
    
    # Main content area
    dbc.Row([
        # Filters sidebar
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("DATA FILTERS", className="section-title"),
                    
                    html.Label("Date Range:", className="font-weight-bold mt-3 mb-2"),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=date_range[0],
                        max_date_allowed=date_range[1],
                        start_date=date_range[0],
                        end_date=date_range[1],
                        calendar_orientation='horizontal',
                        clearable=True,
                        with_portal=True,
                        updatemode='bothdates',  
                        style={'width': '100%'},
                        className="mb-3"
                    ),
                    
                    html.Label("Region:", className="font-weight-bold mt-3 mb-2"),
                    dcc.Dropdown(
                        id='region-dropdown',
                        options=[
                            *[{'label': region, 'value': region} for region in regions if region != 'Unknown'],
                            {'label': 'Unknown', 'value': 'Unknown'}],
                        value=None,
                        placeholder="All Regions",
                        multi=True,
                        clearable=True,
                        className="mb-3"
                    ),
                    
                    html.Label("Product Category:", className="font-weight-bold mt-3 mb-2"),
                    dcc.Dropdown(
                        id='category-dropdown',
                        options=[{'label': category, 'value': category} for category in categories],
                        value=None,
                        placeholder="All Categories",
                        multi=True,
                        clearable=True,
                        className="mb-3"
                    ),
                    
                    dbc.Button(
                        [html.I(className="fas fa-download me-2"), "Export Filtered Data"],
                        id="export-button",
                        color="primary",
                        className="export-btn mt-4"
                    ),
                ])
            ], className="card")
        ], width=3),
        
        # Main charts area
        dbc.Col([
            # Sales Over Time Chart
            dbc.Card([
                dbc.CardBody([
                    html.H5("Sales Performance Trend", className="section-title"),
                    dcc.Graph(id='sales-time-graph', className="dash-graph")
                ])
            ], className="card"),
            
            # Category and Rating Row
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Category Performance", className="section-title"),
                            dcc.Graph(id='category-performance', className="dash-graph")
                        ])
                    ], className="card")
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Rating Distribution", className="section-title"),
                            dcc.Graph(id='rating-distribution', className="dash-graph")
                        ])
                    ], className="card")
                ], width=6)
            ]),
            
            # Top Products Chart
            dbc.Card([
                dbc.CardBody([
                    html.H5("Top 10 Revenue Generating Products", className="section-title"),
                    dcc.Graph(id='top-products', className="dash-graph")
                ])
            ], className="card"),
            
            # Data Table
            dbc.Card([
                dbc.CardBody([
                    html.H5("Data Preview", className="section-title d-flex justify-content-between align-items-center"),
                    html.Div([
                        dash_table.DataTable(
                            id='data-table',
                            columns=[{"name": i.replace('_', ' ').title(), "id": i} for i in df.columns 
                                    if i not in ['year', 'month', 'month_year']],
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '12px 15px',
                                'font-family': 'Segoe UI, sans-serif',
                                'font-size': '13px'
                            },
                            style_header={
                                'backgroundColor': '#f1f3f5',
                                'fontWeight': 'bold',
                                'border': '1px solid #e9ecef'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f8f9fa'
                                }
                            ],
                            style_as_list_view=True,
                            filter_action="native",
                            sort_action="native",
                            sort_mode="multi",
                            page_action="native",
                        )
                    ], className="dash-table-container")
                ])
            ], className="card mt-4")
            
        ], width=9)
    ]),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("SwiftShop Sales Dashboard • by Faisal Alkhunain", 
                   className="text-muted text-center")
        ])
    ], className="mt-5"),
    
    # Hidden download component
    dcc.Download(id="download-dataframe-csv"),
    
    # Font Awesome for icons
    html.Link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
    )
], fluid=True, className="px-4 py-3")

# Define callback to filter data
@app.callback(
    [Output('sales-time-graph', 'figure'),
     Output('category-performance', 'figure'),
     Output('rating-distribution', 'figure'),
     Output('top-products', 'figure'),
     Output('total-sales', 'children'),
     Output('avg-order-value', 'children'),
     Output('avg-rating', 'children'),
     Output('data-table', 'data')],
    [Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('region-dropdown', 'value'),
     Input('category-dropdown', 'value')]
)
def update_dashboard(start_date, end_date, selected_regions, selected_categories):
    # Filter data based on inputs
    filtered_df = df.copy()
    
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df['order_date'] >= start_date) & 
                                  (filtered_df['order_date'] <= end_date)]
    
    if selected_regions and len(selected_regions) > 0:
        filtered_df = filtered_df[filtered_df['customer_region'].isin(selected_regions)]
    
    if selected_categories and len(selected_categories) > 0:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    
    # Check if filtered dataframe is empty
    if filtered_df.empty:
        # Create empty figures with "No data" messages
        fig_time = go.Figure()
        fig_time.add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig_time.update_layout(height=350)
        
        fig_category = go.Figure()
        fig_category.add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig_category.update_layout(height=300)
        
        fig_rating = go.Figure()
        fig_rating.add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig_rating.update_layout(height=300)
        
        fig_top_products = go.Figure()
        fig_top_products.add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig_top_products.update_layout(height=450)
        
        total_sales = "$0.00"
        avg_order_value = "$0.00"
        avg_rating = "N/A"
        table_data = []
        
        return fig_time, fig_category, fig_rating, fig_top_products, total_sales, avg_order_value, avg_rating, table_data
    
    # If we have data, proceed as normal

    # Calculate KPIs
    total_sales = f"${filtered_df['total_amount'].sum():,.2f}"
    avg_order_value = f"${filtered_df.groupby('order_id')['total_amount'].sum().mean():,.2f}"
    
    # For average rating, exclude orders with no rating (value 0)
    rating_df = filtered_df[filtered_df['customer_rating'] > 0]
    avg_rating = f"{rating_df['customer_rating'].mean():.1f}/5.0" if not rating_df.empty else "N/A"
    
    # Sales Over Time graph
    sales_by_month = filtered_df.groupby('month_year')['total_amount'].sum().reset_index()
    sales_by_month = sales_by_month.sort_values('month_year')
    
    fig_time = px.line(sales_by_month, x='month_year', y='total_amount',
                      labels={'month_year': 'Month', 'total_amount': 'Revenue ($)'},
                      template=custom_template)
    
    fig_time.update_traces(mode='lines+markers', 
                          line=dict(width=3, color='#3a7bd5'),
                          marker=dict(size=8, color='#00d2ff'))
    # Force the x-axis to be categorical when there's only one data point
    if len(sales_by_month) <= 1:
        fig_time.update_layout(
            xaxis=dict(type='category', tickangle=-45),
            yaxis=dict(automargin=True),
            title=None,
            hovermode="x unified",
            height=350,
        )
    else:
        fig_time.update_layout(
            xaxis_tickangle=-45,
            yaxis=dict(automargin=True),
            title=None,
            hovermode="x unified",
            height=350,
        )

    fig_time.update_yaxes(tickprefix="$", gridwidth=0.5)
    
    # Category Performance graph
    category_performance = filtered_df.groupby('category')['total_amount'].sum().reset_index()
    fig_category = px.pie(category_performance, values='total_amount', names='category',
                         template=custom_template, hole=0.4)
    fig_category.update_traces(textposition='inside', textinfo='percent+label')
    fig_category.update_layout(
        showlegend=True,
        title=None,
        uniformtext_minsize=10,
        uniformtext_mode='hide',
        height=300
    )
    
    # Rating Distribution graph
    rating_counts = filtered_df[filtered_df['customer_rating'] > 0]['customer_rating'].value_counts().sort_index()
    fig_rating = px.bar(x=rating_counts.index, y=rating_counts.values,
                       labels={'x': 'Rating', 'y': 'Number of Reviews'},
                       template=custom_template)
    fig_rating.update_traces(marker_color='#3498db', opacity=0.8)
    fig_rating.update_layout(
        title=None,
        xaxis=dict(tickmode='linear', tickvals=[1, 2, 3, 4, 5]),
        height=300
    )
    
    # Top 10 Products graph
    top_products = filtered_df.groupby('product_name')['total_amount'].sum().sort_values(ascending=False).head(10).reset_index()
    fig_top_products = px.bar(top_products, x='total_amount', y='product_name', 
                             orientation='h',
                             labels={'total_amount': 'Revenue ($)', 'product_name': 'Product'},
                             template=custom_template)
    fig_top_products.update_traces(marker_color='#2ecc71', opacity=0.85)
    fig_top_products.update_layout(
        title=None,
        yaxis={'categoryorder': 'total ascending',
               'automargin': True },
        xaxis=dict(tickprefix="$"),
        height=450,
    )
    
    # Update data table
    table_data = filtered_df.to_dict('records')
    
    return fig_time, fig_category, fig_rating, fig_top_products, total_sales, avg_order_value, avg_rating, table_data

# Callback for exporting data
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-button", "n_clicks"),
    [State('date-range', 'start_date'),
     State('date-range', 'end_date'),
     State('region-dropdown', 'value'),
     State('category-dropdown', 'value')],
    prevent_initial_call=True
)
def export_data(n_clicks, start_date, end_date, selected_regions, selected_categories):
    if n_clicks is None:
        return None
    
    # Filter data based on inputs (same as above)
    filtered_df = df.copy()
    
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df['order_date'] >= start_date) & 
                                  (filtered_df['order_date'] <= end_date)]
    
    if selected_regions and len(selected_regions) > 0:
        filtered_df = filtered_df[filtered_df['customer_region'].isin(selected_regions)]
    
    if selected_categories and len(selected_categories) > 0:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    
    # Export filtered data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dcc.send_data_frame(filtered_df.to_csv, f"swiftshop_data_{timestamp}.csv", index=False)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)