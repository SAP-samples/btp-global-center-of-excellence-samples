import sys, os, json, requests, hana_ml
from jwcrypto import jwk, jwe
import hana_ml.dataframe as dataframe

outputstring = 'Connection to SAP HANA Cloud established from'

if os.getenv('VCAP_APPLICATION'):
	# File is executed in Cloud Foundry
	outputstring += ' Python deployment in Cloud Foundry'

    # The following steps to access the SAP Credential Store are based on this blog
    # https://community.sap.com/t5/technology-blogs-by-members/access-credential-storage-api-using-python/ba-p/13633301
    
    # Get bindings from SAP Credential Store
	vcap_services = os.getenv('VCAP_SERVICES')
	cred_headers = {"sapcp-credstore-namespace": 'dspdbuserpassword'}  # UPDATE WITH THE NAME OF YOUR NAMESPACE
	cred_params = {"name": 'dbuser_for_cf'}                            # UPDATE WITH THE NAME OF YOUR PASSWORD AS SAVED IN THE NAMESPACE
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
    # File is executed in development environment
    outputstring += '  Python development'

	# Establish connection
    os.environ["HDB_USE_IDENT"] = os.environ["WORKSPACE_ID"]
    conn = dataframe.ConnectionContext(userkey='HC_KEY')

# Test the connection to SAP HANA Cloud
outputstring += ': ' + str(conn.connection.isconnected()) + '\n'

# Print the output
sys.stdout.write(outputstring)