# Automatically setting Client parameter for HDI users to access Calculation Views

This project shows how to implement a dynamic configuration of the `sap-client` in calculation views which are accessed via an HDI runtime user (RT user).

Link to SAP Blog: 

## 1. Prerequisites (HANA Cloud Setup)

Use the SAP HANA Database Explorer to log in to your HANA Cloud database using the `DBADMIN` user.

Prepare the required user and role via the below SQL commands.

**Note:** If you change `YourSecretPassword` then you also have to update the configuration details of the User Provided Service via the [HDI_GRANTS_Client.json](./HDI_GRANTS_Client.json) file.

```sql
-- Allow DBADMIN to grant Usergroup Operater privileges to a user:
CALL "SYSTEM".GRANT_USERGROUP_OPERATOR('BROKER_UG_HDISHARED');


-- Create a role which will contain the privilege to alter users:
CREATE ROLE UG_GRANTOR_ROLE NO GRANT TO CREATOR;
GRANT USERGROUP OPERATOR ON USERGROUP BROKER_UG_HDISHARED TO UG_GRANTOR_ROLE WITH GRANT OPTION;


-- Create user UG_GRANTOR_USER who will be allowed to grant the new role to other users:
CREATE USER UG_GRANTOR_USER PASSWORD "YourSecretPassword" SET USERGROUP DEFAULT;
ALTER USER UG_GRANTOR_USER disable PASSWORD lifetime;


-- Grant new role to UG_GRANTOR_USER with option to grant to others (which will be #OO users):
GRANT UG_GRANTOR_ROLE TO UG_GRANTOR_USER WITH ADMIN option;
```

## 2. Deploying this project

You can deploy this project as-is by running the following console/terminal commands:
```bash
npm install
mbt build
cf deploy ./mta_archives/calcview_client_1.0.0.mtar
```

## 3. Testing

### Empty response
You just deployed the application without any client configuration and will see the default empty response of the calculation view. The following line is displayed in the startup logs of the SRV application:

`Project is not configured to set client [user: your_user, client: null, db: hana].`

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

`Set client 200 for user xxxxxx_RT successfully.`

And when loading the calculation view via the APP (https://xxxxx.hana.ondemand.com/odata/v4/calcviews/SAPDATA), the correct data will be returned.

## 4. Revoke

The `DBADMIN` at all points in time retains control over the privilege of altering users.
**Only if you want to undo this deployment** you can run a few SQL statements as well to revoke all permissions:

```sql
-- Disable the granting and revoke privileges of the UG_GRANTOR_USER and all #OO users:
CALL "SYSTEM".REVOKE_USERGROUP_OPERATOR('BROKER_UG_HDISHARED');

-- Delete the role/user (clean-up)
DROP ROLE UG_GRANTOR_ROLE;
DROP USER UG_GRANTOR_USER;
```

After this, you can test to deploy the project with a different client setting and you will notice this no longer changes the client for the RT user.