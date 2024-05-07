import json
import subprocess # For OS commands on DSP CLI

class dspUtilities:
    # function to pretty print json
    def print_json(json_object, indent=2, sort_keys=False, encoding='utf-8' ):
        try:
            # Convert the JSON object to a string with specified indentation and sorting
            json_string = json.dumps(json_object, indent=indent, sort_keys=sort_keys, ensure_ascii=False).encode(encoding).decode(encoding)
            print(json_string)

        except (TypeError, ValueError) as e:
            # Error handling if the input is not a valid JSON object
            print(f"Error: Unable to print the JSON object. {str(e)}")

    def read_var_from_file(file_path, var_name):
        with open(file_path, 'r') as file:
            data = json.load(file)
            if var_name in data:
                return data[var_name]
            else:
                return None
    
    def run_command(command):
        print(command)
        subprocess.run(command, shell=True)

    def read_json_file(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("The file was not found.")
        except json.JSONDecodeError:
            print("Error decoding JSON.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def write_json_file(data, file_path):
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"Data successfully written to {file_path}.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def logoutlogin(dsp_logon_data_file):
        # -----------------------------------------------------------
        # Read host
        # -----------------------------------------------------------
        dsp_host=dspUtilities.read_var_from_file(dsp_logon_data_file,'dsp_host')

        # -----------------
        # print versions of relevant components
        # -----------------
        dspUtilities.run_command('node --version')
        dspUtilities.run_command('npm --version')
        dspUtilities.run_command('datasphere -version')

        # -----------------------------------------------------------
        # CLI logon procedure with oAuth authentication to DSP CLI
        # -----------------------------------------------------------

        # logout is needed to have the login consider new creds file, e.g., in case it is replaced with new client id/secret
        dspUtilities.run_command('datasphere logout')

        # login
        dspUtilities.run_command(f'datasphere login --host {dsp_host} --secrets-file {dsp_logon_data_file}')

        # set global host
        dspUtilities.run_command(f'datasphere config host set {dsp_host}')

        # Optional command to debug or to get the access and refresh token to avoid login command (see header comments)
        dspUtilities.run_command('datasphere config secrets show')