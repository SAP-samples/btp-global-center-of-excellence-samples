# -----------------------------------------------------------
# Package import
# -----------------------------------------------------------
import json # For handling the CSN files which are in JSON format
from hdbcli import dbapi # To connect to SAP HANA Database underneath SAP Datasphere to fetch Remote Table metadata
from dsp_utilities import dspUtilities as du

# settings
view_suffix = '_V'

class r2v:

    def __init__(self, dsp_logon_data_file, dsp_space, export_folder_path):
        # -----------------------------------------------------------
        # Read host and credentials
        # -----------------------------------------------------------
        self.dsp_space = dsp_space
        self.dsp_host=du.read_var_from_file(dsp_logon_data_file,'dsp_host')
        self.hdb_address=du.read_var_from_file(dsp_logon_data_file,'hdb_address')
        self.hdb_port=du.read_var_from_file(dsp_logon_data_file,'hdb_port')
        self.hdb_user=du.read_var_from_file(dsp_logon_data_file,'hdb_user')
        self.hdb_password=du.read_var_from_file(dsp_logon_data_file,'hdb_password')

        self.export_folder_path = export_folder_path

    # -----------------------------------------------------------
    # This function takes a Remote Table (RT) CSN as input and transforms it to a SQL View CSN
    # -----------------------------------------------------------
    def remote_table_to_view(rt_csn):
        rt_name = list(rt_csn['definitions'].keys())[0]
        view_name = rt_name + view_suffix

        elements = rt_csn["definitions"][rt_name]["elements"]
        elements_string = ', '.join(f'"{element}"' for element in elements)

        view_csn = {
            "definitions": {
                view_name: {
                    "kind": "entity",
                    "elements": elements,
                    "query": {
                        "SELECT": {
                            "from": {"ref": [rt_name]},
                            "columns": [{"ref": [element]} for element in elements]
                        }
                    },
                    "@EndUserText.label": view_name,
                    "@ObjectModel.modelingPattern": {"#": "DATA_STRUCTURE"},
                    "@ObjectModel.supportedCapabilities": [{"#": "DATA_STRUCTURE"}],
                    "@DataWarehouse.consumption.external": True,
                    "@DataWarehouse.sqlEditor.query": f"SELECT {elements_string}\nFROM \"{rt_name}\""
                }
            }
        }
        
        return view_csn

    # -----------------------------------------------------------
    # Write space definition to csn file and return file name
    # -----------------------------------------------------------
    def write_space_csn(self, space_csn):
        space_csn_pretty = json.dumps(space_csn, indent=4)
        view_name = next(iter(space_csn[next(iter(space_csn.keys()))]["definitions"].keys()))
        space_csn_file = f'{self.export_folder_path}space_{self.dsp_space}_object_{view_name}.csn'
        with open(space_csn_file, 'w') as f:
            f.write(space_csn_pretty)
        return space_csn_file

    def write_view_csn(self, view_csn: dict):
        view_name = str(next(iter(view_csn["definitions"])))
        print ('view_name: ' + view_name)
        view_csn_file_name = f'{self.export_folder_path}space_{self.dsp_space}_object_{view_name}.csn'
        view_csn_pretty = json.dumps(view_csn, indent=4)
        with open(view_csn_file_name, 'w') as f:
            f.write(view_csn_pretty)
        return view_csn_file_name, view_name

    # -----------------------------------------------------------
    # Push view csn to DSP with space definition csn as input
    # -----------------------------------------------------------
    def push_space_csn_to_DSP(self, space_csn_file):
        command = f'datasphere spaces create --host {self.dsp_host} --space {self.dsp_space} --file-path {space_csn_file} --force-definition-deployment --verbose'
        du.run_command(command)

    def push_view_to_DSP(self, view_csn_file, view_name):
        #command = f'datasphere objects views update --host {dsp_host} --space {dsp_space} --file-path {view_csn_file} --technical-name {view_name} --force-definition-deployment --verbose'
        command = f'datasphere objects views create --host {self.dsp_host} --space {self.dsp_space} --file-path {view_csn_file} --force-definition-deployment --verbose'
        du.run_command(command)

    def loopAndGo(self):
        
        # Connect to HDB
        conn = dbapi.connect(
            address=self.hdb_address,
            port=self.hdb_port,
            user=self.hdb_user,
            password=self.hdb_password
        )
        cursor = conn.cursor()

        # -----------------------------------------------------------
        # Fetch RT metadata from HANA DB, and for each RT create a view and push this to DSP
        # -----------------------------------------------------------

        # select statement to fetch remote table csn's. Selection on highest ARTIFACT_VERSION for each object.
        st = f'''
            SELECT A.ARTIFACT_NAME, A.CSN, A.ARTIFACT_VERSION
            FROM "{self.dsp_space}$TEC"."$$DeployArtifacts$$" A
            INNER JOIN (
            SELECT ARTIFACT_NAME, MAX(ARTIFACT_VERSION) AS MAX_ARTIFACT_VERSION
            FROM "{self.dsp_space}$TEC"."$$DeployArtifacts$$"
            WHERE PLUGIN_NAME='remoteTable'
            GROUP BY ARTIFACT_NAME
            ) B
            ON A.ARTIFACT_NAME = B.ARTIFACT_NAME
            AND A.ARTIFACT_VERSION = B.MAX_ARTIFACT_VERSION
        ;
        '''
        print('>>> SELECT statement to fetch remote table definitions')
        print(st)
        cursor.execute(st)

        # Loop over the remote tables, create a view definition, and push its csn to DSP
        rows = cursor.fetchall()
        conn.close()
        total_rows = len(rows)
        print ('Total rows: ' + str(total_rows))

        for i, row in enumerate(rows):
            rt_name = row[0]
            csn = row[1]
            
            # Load remote table csn and print it
            rt_csn = json.loads(csn)
            rt_csn_pretty = json.dumps(rt_csn, indent=4)
            print('>>> Remote table csn of: ' + rt_name)
            print(rt_csn_pretty)
            
            # Get view definition based on remote table and print it
            view_csn = r2v.remote_table_to_view(rt_csn)
            #view_csn_pretty = json.dumps(view_csn, indent=4)
            print('>>> Generated view csn of: ' + rt_name)
            print(view_csn)
            
            # Write space csn to file
            file, view_name = self.write_view_csn(view_csn)
                
            # Push space csn to DSP
            self.push_view_to_DSP(file, view_name)