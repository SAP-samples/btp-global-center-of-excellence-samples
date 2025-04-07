# %%
address = "<YOUR HANA DATABASE ENDPOINT>"
user = "<YOUR HANA DATABASE USER>"
password = "<YOUR DATABASE USER PASSWORD>"

# %%
import pandas as pd
import numpy as np
from hdbcli import dbapi
import hana_ml
from hana_ml import ConnectionContext, DataFrame as hana_df
from hana_ml.dataframe import create_dataframe_from_pandas
import datetime

# %%
queries = [
    """CREATE TABLE products (
    product_id INT PRIMARY KEY,
    name VARCHAR(255),
    price DECIMAL(10,2) DEFAULT 1,
    category VARCHAR(255) DEFAULT 'Sonstige',
    expiry_date DATE,
    stock INT
    );""",
    
    """CREATE TABLE sales (
    sale_id INT PRIMARY KEY,
    date DATE,
    product_id INT,
    quantity INT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
    );""",
    
    """CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    product_id INT,
    quantity INT DEFAULT 1,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
    );""",
    
    """CREATE TABLE inventory (
    inv_id INT PRIMARY KEY,
    product_id INT,
    quantity INT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
    );"""
]

# %%
db_conn = dbapi.connect(address=address, port=443, user=user, password=password)
cursor = db_conn.cursor()

# %%
for query in queries:
    cursor.execute(query)
db_conn.close()

# %%
with ConnectionContext(address=address, port=443, user=user, password=password) as conn:
    sales_remote = conn.table('SALES')
    products_remote = conn.table('PRODUCTS')
    products = pd.DataFrame({
    'PRODUCT_ID': range(1, 51),
    'NAME': [
    'Milk', 'Bread', 'Apples', 'Cheese', 'Tomatoes',
    'Laundry Detergent', 'Toothpaste', 'Chocolate', 'Pasta', 'Rice',
    'Orange Juice', 'Coffee', 'Toilet Paper', 'Butter', 'Eggs',
    'Potatoes', 'Bananas', 'Chicken', 'Tuna', 'Mineral Water',
    'Yogurt', 'Cereal', 'Carrots', 'Soap', 'Shampoo',
    'Cookies', 'Olive Oil', 'Salmon', 'Spinach', 'Beef',
    'Beer', 'Wine', 'Chips', 'Ice Cream', 'Frozen Pizza',
    'Lettuce', 'Onions', 'Garlic', 'Pepper', 'Salt',
    'Ketchup', 'Mustard', 'Mayonnaise', 'Honey', 'Jam',
    'Soda', 'Tea', 'Flour', 'Sugar', 'Canned Beans'
    ],
    'PRICE': np.round(np.random.uniform(0.5, 20, 50), 2),
    'CATEGORY': [
    'Dairy', 'Bakery', 'Produce', 'Dairy', 'Produce',
    'Household', 'Personal Care', 'Snacks', 'Pasta & Rice', 'Pasta & Rice',
    'Beverages', 'Beverages', 'Household', 'Dairy', 'Eggs',
    'Produce', 'Produce', 'Meat', 'Canned Goods', 'Beverages',
    'Dairy', 'Breakfast', 'Produce', 'Personal Care', 'Personal Care',
    'Snacks', 'Cooking Oil', 'Seafood', 'Produce', 'Meat',
    'Alcoholic Beverages', 'Alcoholic Beverages', 'Snacks', 'Frozen Foods', 'Frozen Foods',
    'Produce', 'Produce', 'Produce', 'Spices', 'Spices',
    'Condiments', 'Condiments', 'Condiments', 'Spreads', 'Spreads',
    'Beverages', 'Beverages', 'Baking', 'Baking', 'Canned Goods'
    ],
    'STOCK': np.random.randint(0, 1000, 50),
    })
    products['EXPIRY_DATE'] = pd.date_range(start='2025-06-01', periods=50, freq='D')

    num_products = 50
    num_samples = 365 * 2 
    today = datetime.date.today()
    sales = pd.DataFrame({
        'SALE_ID': range(1, num_samples+1, 1),
        'DATE': pd.date_range(end=today, periods=num_samples, freq='D'),
        'QUANTITY': ((np.sin(np.linspace(0, 3.141 * 4, num_samples))+3) * 100).astype(int),
        'PRODUCT_ID': np.random.randint(1, num_products+1, num_samples)
    })
    create_dataframe_from_pandas(append=True, pandas_df=products, connection_context=conn, table_name="PRODUCTS", force=True) 
    create_dataframe_from_pandas(append=True, pandas_df=sales, connection_context=conn, table_name="SALES") 



