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
	
	# Move planning data to staging table (for performance)
	df_remote = conn.table('ExtSACP01_FactData_View', schema='EXTEND_SAC_PLANNING')
	df_remote = df_remote.save('#PLANNINGDATA', table_type='LOCAL TEMPORARY', force=True)

	# Prepare the actuals data to train the model
	df_remote_act = df_remote.filter(""" "Version" = 'public.Actual'""")
	df_remote_act = df_remote_act.filter('''"Account" = 'UnitPrice' ''').rename_columns({'Value': 'UnitPrice'}).select('Date', 'UnitPrice').set_index('Date').join(
    df_remote_act.filter('''"Account" = 'UnitsSold' ''').rename_columns({'Value': 'UnitsSold'}).select('Date', 'UnitsSold').set_index('Date'), how='left'
)
	# Prepare the planning data to predict the future (months without actuals)
	df_remote_plan = df_remote.filter(""" "Version" = 'public.Plan'""")
	df_remote_plan = df_remote_plan.filter('''"Account" = 'UnitPrice' ''').rename_columns({'Value': 'UnitPrice'}).select('Date', 'UnitPrice').set_index('Date').join(
		df_remote_plan.filter('''"Account" = 'UnitsSold' ''').rename_columns({'Value': 'UnitsSold'}).select('Date', 'UnitsSold').set_index('Date'), how='left'
	)
	month_last_actual = df_remote_act.select('Date').max()
	df_remote_plan = df_remote_plan.filter(f'''"Date" > '{month_last_actual}' ''')
	
	# Train and apply the Machine Learning model
	ur_hgbt = UnifiedRegression(func='LinearRegression')
	ur_hgbt.fit(data=df_remote_act, features=['UnitPrice'], label='UnitsSold')
	df_rem_predicted = ur_hgbt.predict(data=df_remote_plan, features='UnitPrice', key='Date')

	# Prepare dataset for returning to SAC Planning
	df_rem_predicted = df_rem_predicted.drop(['LOWER_BOUND', 'UPPER_BOUND', 'REASON'])
	df_rem_predicted = df_rem_predicted.rename_columns({'SCORE': 'Value'})
	df_rem_predicted = df_rem_predicted.add_constant('Version', 'public.Plan')
	df_rem_predicted = df_rem_predicted.add_constant('Category', 'Planning')
	df_rem_predicted = df_rem_predicted.add_constant('Account', 'UnitsSold')
	df_rem_predicted = df_rem_predicted.select('Version', 'Date', 'Account', 'Value', 'Category')

	# Save the data into staging table
	df_rem_predicted.save('CUSTOM_CALCULATIONS', force=True)

	# Process compelete
	return Response("{'message':'The data has been processed'}", status=200, mimetype='application/json')

if __name__ == '__main__':
	if cf_port is None:
		app.run(host='0.0.0.0', port=5000, debug=True)
	else:
		app.run(host='0.0.0.0', port=int(cf_port), debug=True)