# Automatically setting Client parameter for HDI users to access Calculation Views

**Simpler version**: this approach works with both SAP HANA Cloud databases as well as with HANA databases embedded in SAP Datasphere.

This project shows how to implement a dynamic configuration of the `sap-client` in calculation views which are accessed via an HDI runtime user (RT user).

The client value is set during application startup for the entire database connection, regardless of the RT user used.

## 1. Deploying this project

You can deploy this project as-is by running the following console/terminal commands:
```bash
npm install
mbt build
cf deploy ./mta_archives/calcview_client_1.0.0.mtar
```

## 2. Testing

### Empty response
You just deployed the application without any client configuration and will see the default empty response of the calculation view. The following line is displayed in the startup logs of the SRV application:

`Project is not configured to set client [client: null, db: hana].`

And when loading the calculation view via the APP (https://xxxxx.hana.ondemand.com/odata/v4/calcviews/SAPDATA), there will be no data `[]` returned.

### Deploying with client
You will need to specify the correct extension file to correctly set the client. Note that below commands only refresh/deploy the SRV layer of the MTA since that is the only components that gets reconfigured.

```bash
# for client 100
cf deploy ./mta_archives/calcview_client_1.0.0.mtar -m calcview_client-srv -e mta_client100.mtaext

# for client 200
cf deploy ./mta_archives/calcview_client_1.0.0.mtar -m calcview_client-srv -e mta_client200.mtaext

# for client 300
cf deploy ./mta_archives/calcview_client_1.0.0.mtar -m calcview_client-srv -e mta_client300.mtaext
```

This will display the following line in the startup logs of the SRV application:

`Set client 200 for successfully.`

And when loading the calculation view via the APP (https://xxxxx.hana.ondemand.com/odata/v4/calcviews/SAPDATA), the correct data will be returned.
