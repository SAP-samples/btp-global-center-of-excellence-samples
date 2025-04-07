import uuid
import pandas as pd
import datetime
from datetime import datetime, date
from hana_ml.algorithms.pal.tsa.additive_model_forecast import AdditiveModelForecast
from hana_ml.dataframe import create_dataframe_from_pandas
from langchain_core.messages import ToolMessage
from typing import Literal, Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command



@tool
def get_temp_tables():
    """List temporary tables of the database."""
    return conn.get_temporary_tables(schema='DEMO')

@tool
def get_today():
    """Returns todays date."""
    return date.today()

@tool
def visualize_as_chart(sql_query: str, tool_call_id: Annotated[str, InjectedToolCallId], chart_type : Literal['bar_chart', 'line_chart', 'area_chart', 'scatter_chart']):
    """Visualizes the result of an SQL SELECT query as a chart.
    sql_query must be a SELECT query. The first column relates to the x-axis.
    The second column and all following columns represent one categorical variable each and must contain numerical values.
    Always cast the numerical columns to int or float.
    Example of allowed queries:
    1. SELECT CATEGORY, CAST(AVG(PRICE) AS INT) AS AVG_PRICE FROM PRODUCTS GROUP BY CATEGORY
    2. SELECT DATE, CAST(TEA_SALES AS INT), CAST(CHOCOLATE_SALES AS INT) FROM #TEMP_SALES GROUP BY DATE
    Do not provide more than one column containing categorical data.
    """
    from frontend import charts
    table = conn.sql(sql_query).collect()
    identifier = str(uuid.uuid1())
    charts[identifier] = table
    return Command(update={
        'messages': [ToolMessage(f'Successfully created visualization. Sample from the SQL Query: {str(table)}', tool_call_id=tool_call_id)],
        'charts': [{'id': identifier, 'chart_type': chart_type}]
    })



@tool
def fit_amf(table_name : str) -> str:
    """Fit data for Additive Model Forecast. Always create a new temporary table to fit data.
    table_name: The name of a remote hana table. This remote table must have two columns.
    The first column has to be of type date and the second column has to be a quantity.
    """
    table = conn.table(table=table_name.upper())
    amf.fit(data=table)
    return 'Successfully fit the data.'

@tool
def predict_amf(tool_call_id: Annotated[str, InjectedToolCallId], start_date: str, end_date: str, allow_negative: bool):
    """Predict data using Additive Model Forecast. First data has to be fit. A visualisation is displayed to the user automatically."""
    from frontend import charts

    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    dates = pd.date_range(start_date, end_date, freq='7D')
    prediction = pd.DataFrame({'DATE': dates, 'TARGET': 0})
    prediction_remote = create_dataframe_from_pandas(pandas_df=prediction, connection_context=conn,
                                                     table_name='tmp_amf', force=True,
                                                     table_structure={'DATE': 'DATE'}
                                                     )
    predictions = amf.predict(data=prediction_remote).collect()
    predictions['DATE'] = prediction['DATE']

    conn.drop_table(table='tmp_amf')
    identifier = str(uuid.uuid1())
    charts[identifier] = predictions
    return Command(update={
        'messages': [ToolMessage(f'Successfully created visualization.', tool_call_id=tool_call_id)],
        'charts': [{'id': identifier, 'chart_type': 'line_chart'}]
    })


@tool
def create_temp_table(sql_str: str) -> str:
    """Create a temporary table with the provided SQL String. The database is a SAP HANA database. Returns sample data of the temporary table.
    Example for the sql_str: CREATE LOCAL TEMPORARY COLUMN TABLE #TEMP_TABLE AS (...)"""
    cursor = conn.connection.cursor()
    if cursor.execute(sql_str):
        return 'Created table.'
    else:
        return "Couldn't create table."

@tool
def fetch_data(sql_str: str):
    """Fetches the result of the sql query. readonly access. Result cannot be longer than 20 rows."""
    cursor = conn.connection.cursor()
    if cursor.execute(sql_str):
        return cursor.fetchmany(20)
    else:
        return "Couldn't execute query"

@tool
def get_distinct_values(table_name : str, column_name : str):
    """Retrieves the distinct values of a column of a table."""
    table = conn.table(table=table_name)
    return str(table.distinct(cols=column_name).collect())

@tool
def get_column_names(table_name: str):
    """Retrieves the column names of a table."""
    table = conn.table(table=table_name)
    return str(table.columns)

@tool
def get_table_shape(table_name: str):
    "Retrieves the table shape given a table name."
    table = conn.table(table=table_name)
    return str(table.columns)


@tool
def get_temp_tables() -> str:
    """Lists the temporary tables of the database.
    """
    return conn.get_temporary_tables(schema='DEMO')

@tool
def get_tables() -> str:
    """Lists the tables of the database.
    """
    return conn.get_tables(schema='DEMO')


import streamlit as st
import hana_ml.dataframe as df

address = "<YOUR HANA DATABASE ENDPOINT>"
user = "<YOUR HANA DATABASE USER>"
password = "<YOUR DATABASE USER PASSWORD>"

def init_remote():
    if 'init_remote' not in st.session_state:
        st.session_state.amf = AdditiveModelForecast(daily_seasonality='false', weekly_seasonality='false', yearly_seasonality='true')
        st.session_state.conn = df.ConnectionContext(
            address=address, port=443, user=user,
            password=password)
        st.session_state.init_remote = True
    return [st.session_state[el] for el in ['amf', 'conn']]

amf, conn = init_remote()


