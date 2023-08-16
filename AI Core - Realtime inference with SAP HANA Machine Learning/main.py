import os
import json
import pandas as pd
import hana_ml.dataframe as dataframe
from hana_ml.model_storage import ModelStorage
from flask import Flask
from flask import request as call_request 
import uuid

# Print external IP address
from requests import get
ip = get('https://api.ipify.org').text
print(f'My public IP address is: {ip}')

# Variable for connection to SAP HANA
conn = None

# Function to establish connection to SAP HANA
def get_hanaconnection():
    global conn
    conn = dataframe.ConnectionContext(address=os.getenv('HANA_ADDRESS'),
                                            port=int(os.getenv('HANA_PORT')),
                                            user=os.getenv('HANA_USER'),
                                            password=os.getenv('HANA_PASSWORD'))
    print('Connection to SAP HANA established: ' + str(conn.connection.isconnected()))

# Creates Flask serving engine
app = Flask(__name__)

# You may customize the endpoint, but must have the prefix `/v<number>`
@app.route("/v1/predict", methods=["POST"])
def predict():
    print("start serving ...")

    # Convert incoming payload to Pandas DataFrame
    payload = call_request.get_json()
    payloadString = json.dumps(payload)
    parsedPayload = json.loads(payloadString)
    df_data = pd.json_normalize(parsedPayload)
    # Ensure that the connection to SAP HANA is active
    if (conn.connection.isconnected() == False):
        get_hanaconnection()

    # Load the saved model
    model_storage = ModelStorage(connection_context=conn)
    ur_hgbt = model_storage.load_model('Car price regression')

    # Save received data as temporary table in SAP HANA
    temp_table_name = '#' + str(uuid.uuid1()).upper()
    df_remote_topredict = dataframe.create_dataframe_from_pandas(
        connection_context=conn,
        pandas_df=df_data,
        table_name=temp_table_name,
        force=True,
        drop_exist_tab=True,
        replace=False)
    
    # Create prediction based on the data in the temporary table
    df_predicted = ur_hgbt.predict(data=df_remote_topredict,
    key='CAR_ID').collect()
    prediction = df_predicted['SCORE'][0]

    # Delete the temporary table
    dbapi_cursor = conn.connection.cursor()
    dbapi_cursor.execute('DROP TABLE "' + temp_table_name + '"')

    # Send the prediction as response
    output = json.dumps({'price_estimate': round(prediction, 1)})
    return output

if __name__ == "__main__":
    # Establish initial connection to SAP HANA
    get_hanaconnection()

    print("Serving Started")
    app.run(host="0.0.0.0", debug=False, port=9001)
