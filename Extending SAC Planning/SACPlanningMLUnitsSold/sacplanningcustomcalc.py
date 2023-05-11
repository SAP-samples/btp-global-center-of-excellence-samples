from flask import Flask
from flask import Response
import os, json, IPython
from hana_ml import dataframe
from hana_ml.algorithms.pal.unified_regression import UnifiedRegression

app = Flask(__name__)
# Port number is required to fetch from env variable
# http://docs.cloudfoundry.org/devguide/deploy-apps/environment-variable.html#PORT

cf_port = os.getenv("PORT")

# Get SAP HANA logon credentials from user-provided variable in CloudFoundry
hana_credentials_env = os.getenv('HANACRED')
hana_credentials = json.loads(hana_credentials_env)
hana_address = hana_credentials['address']
hana_port = hana_credentials['port']
hana_user = hana_credentials['user']
hana_password = hana_credentials['password']

# POST method as required by SAC PLanning
@app.route('/', methods=['GET', 'POST'])
def processing():

	# Connect to SAP HANA Cloud
	conn = dataframe.ConnectionContext(address=hana_address,
                                   port=hana_port, 
                                   user=hana_user, 
                                   password=hana_password)
	
	# Bring the data into a temporary table
	df_remote = conn.table('V_FactData', schema='SAC_PLAN_EXT_API')
	df_remote = df_remote.filter(""" "Version" = 'public.Temporary'""")
	df_remote = df_remote.save('#PLANNINGDATA', table_type='LOCAL TEMPORARY', force=True)

	# Adding ID as predictor for regression
	df_remote = df_remote.add_id(ref_col='Date')

	# Data to train and to forecast
	df_rem_train = df_remote.sort('Date').head(6)
	df_rem_toforecast = df_remote.tail(n=6, ref_col='Date')

	# Train and apply regression
	ur_hgbt = UnifiedRegression(func='LinearRegression')
	ur_hgbt.fit(data=df_rem_train, features=['ID'], label='UnitPrice')
	df_rem_predicted = ur_hgbt.predict(data=df_rem_toforecast, features='ID', key='Date')

	# Prepare dataset to return to SAC Planning
	df_rem_predicted = df_rem_predicted.set_index('Date').join(df_rem_toforecast.set_index('Date'))
	df_rem_predicted = df_rem_predicted.select('Version', 'Date', ('ROUND(SCORE, 1)', 'UnitPrice'), 'UnitCost', 'SalesUnits', 'FixedCost')
	df_rem_toreturn = df_rem_train.drop('ID').union(df_rem_predicted).sort('Date')
	df_rem_toreturn = df_rem_toreturn.select(("'public.Temporary'", 'Version'), 'Date', 'UnitPrice', 'UnitCost', 'SalesUnits', 'FixedCost')

	# Remove any previous / old content from the target table
	dbapi_cursor = conn.connection.cursor()
	dbapi_cursor.execute("""DELETE FROM "SAC_PLAN_EXT_API#DATA"."FactData_2" WHERE "Version"='public.Temporary'""")

	# Save data into staging table
	df_rem_toreturn.save('FactData_2', append=True)

	# Process compelete
	return Response("{'message':'The data has been processed'}", status=200, mimetype='application/json')

if __name__ == '__main__':
	if cf_port is None:
		app.run(host='0.0.0.0', port=5000, debug=True)
	else:
		app.run(host='0.0.0.0', port=int(cf_port), debug=True)