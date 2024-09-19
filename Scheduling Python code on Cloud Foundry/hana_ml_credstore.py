# This code is part of the blog https://community.sap.com/t5/technology-blogs-by-sap/scheduling-python-code-on-cloud-foundry/ba-p/13503697

import sys, os, json, requests, hana_ml
from jwcrypto import jwk, jwe
import hana_ml.dataframe as dataframe

if os.getenv('VCAP_APPLICATION'):	# File is executed in Cloud Foundry
    sys.stdout.write('Python executing in Cloud Foundry')

    # The following steps to access the SAP Credential Store are based on this blog
    # https://community.sap.com/t5/technology-blogs-by-members/access-credential-storage-api-using-python/ba-p/13633301

    # Get bindings from SAP Credential Store
    vcap_services = os.getenv('VCAP_SERVICES')
    cred_headers = {"sapcp-credstore-namespace": 'HANACLOUD_CREDS'}
    cred_params = {"name": 'DBUSER_CREDS'}
    binding = json.loads(vcap_services)['credstore'][0]['credentials']
 
    # With the binding details, obtain the content from the SAP Credential Store, which contains host, port, user and password
    response = requests.get(url=f"{binding['url']}/password",headers=cred_headers, params=cred_params,
                            auth=(binding['username'], binding['password']))
    
    # Decrypt the content
    private_key_pem =f"-----BEGIN PRIVATE KEY-----\n{binding['encryption']['client_private_key']}\n-----END PRIVATE KEY-----"
    private_key = jwk.JWK.from_pem(private_key_pem.encode('utf-8'))
    jwetoken = jwe.JWE()
    jwetoken.deserialize(response.text, key=private_key)
    resp = jwetoken.payload.decode('utf-8')
    json_payload = json.loads(resp)

	# Get the SAP HANA Cloud logon credentials and instantiate a connection object
    hana_cred_retrieved = json.loads(json_payload['value'])
    conn = dataframe.ConnectionContext(address = hana_cred_retrieved['address'],
                                       port = hana_cred_retrieved['port'],
                                       user = hana_cred_retrieved['user'],
                                       password = hana_cred_retrieved['password']
                                       )

else:
    # File is executed locally
    sys.stdout.write('Python executing locally')

    # Get SAP HANA logon credentials from the local client's secure user store
    conn = dataframe.ConnectionContext(userkey='MYHANACLOUD')

# Test the connection to SAP HANA Cloud and 
df_remote = conn.sql("SELECT 2 * 3 * 7 FROM DUMMY")
response = df_remote.collect().iloc[0, 0]
conn.close()
sys.stdout.write('\nThe answer is ' + str(response) + '\n')