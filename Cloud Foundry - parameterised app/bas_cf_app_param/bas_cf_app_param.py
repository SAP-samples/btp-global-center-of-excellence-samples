# Start with /bin/python3 /home/user/projects/hanaml/bas_cf_app_param/bas_cf_app_param.py FR

import sys, os
outputstring = 'Hello world from'

if len(sys.argv) > 1:
	param1 = sys.argv[1]
	match param1:
		case "FR":
			outputstring = "Salut le monde de"
		case "DE":
			outputstring = "Hallo Welt von"

if os.getenv('VCAP_APPLICATION'):
	# File is executed in Cloud Foundry
	outputstring += ' Python deployment in Cloud Foundry\n'

else:
    # File is executed in development environment
    outputstring += ' Python development\n'

# Print the output
sys.stdout.write(outputstring)