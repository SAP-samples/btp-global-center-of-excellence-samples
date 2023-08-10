import os, datetime
import hana_ml.dataframe as dataframe
from hana_ml.algorithms.pal.unified_regression import UnifiedRegression
from hana_ml.algorithms.pal.model_selection import GridSearchCV
from hana_ml.model_storage import ModelStorage
from ai_core_sdk.tracking import Tracking
from ai_core_sdk.models import Metric

# Print external IP address
from requests import get
ip = get('https://api.ipify.org').text
print(f'My public IP address is: {ip}')

if os.getenv('KUBERNETES_SERVICE_HOST'):
	# Code is executed in AI Core
	print('Hello from Python in Kubernetes')
	hana_address = os.getenv('HANA_ADDRESS')
	print('The SAP HANA address is: ' + hana_address)
	conn = dataframe.ConnectionContext(address=os.getenv('HANA_ADDRESS'),
                                           port=int(os.getenv('HANA_PORT')),
                                           user=os.getenv('HANA_USER'),
                                           password=os.getenv('HANA_PASSWORD'))
  
else:
	# File is executed locally
	print('Hello from Python that is NOT in Kubernetes')
	conn = dataframe.ConnectionContext(userkey='MYHC')

print('Connection to SAP HANA established: ' + str(conn.connection.isconnected()))

# Point to the training data in SAP HANA
df_remote = conn.table('V_USEDCARS')

# Train the Regression model
ur_hgbt = UnifiedRegression(func='HybridGradientBoostingTree')
gscv = GridSearchCV(estimator=ur_hgbt, 
                    param_grid={'learning_rate': [0.001, 0.01, 0.1],
                                'n_estimators': [5, 10, 20, 50],
                                'split_threshold': [0.1, 0.5, 1]},
                    train_control=dict(fold_num=3,
                                       resampling_method='cv',
                                       random_state=1,
                                       ref_metric=['rmse']),
                    scoring='rmse')
gscv.fit(data=df_remote, 
         key= 'CAR_ID',
         label='PRICE',
         partition_method='random',
         partition_random_state=42,
         output_partition_result=True,
         build_report=False)

r2 = ur_hgbt.statistics_.filter("STAT_NAME = 'TEST_R2'").select('STAT_VALUE').collect().iloc[0, 0]
print('The model has been trained. R2: ' + str(r2))

# If executed on AI Core, store model metrics with the execution
aic_connection = Tracking()
aic_connection.log_metrics(
    metrics = [
        Metric(
            name= "R2", value= float(r2), timestamp=datetime.datetime.now(datetime.timezone.utc)),
    ]
)

# Save the model
model_storage = ModelStorage(connection_context=conn)
ur_hgbt.name = 'Car price regression'
model_storage.save_model(model=ur_hgbt)

print('The model has been saved')