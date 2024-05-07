from dsp_utilities import dspUtilities as du
import copy
import json

class dspTF:
    @staticmethod
    def get_name_from_tf(tf_data):
        tf_name = str(next(iter(tf_data["transformationflows"])))
        return tf_name
    
    def get_name_from_tc(tc_data):
        tc_name = str(next(iter(tc_data["taskchains"])))
        return tc_name
    
    def read_tf(dsp_space, tf_name, objects_import_path):
        file_path = f'{objects_import_path}{tf_name}.json'
        command = f'datasphere objects transformation-flows read --space {dsp_space} --technical-name {tf_name} --output {file_path} --verbose'
        du.run_command(command)
        tf_json = du.read_json_file(file_path)
        return tf_json
    
    def push_tf(tf_data, objects_export_path, dsp_space):
        tf_name = dspTF.get_name_from_tf(tf_data)
        print("tf_name: " + tf_name)
        file_path = objects_export_path + tf_name + '.json'
        du.write_json_file(tf_data, file_path)
        command = f'datasphere objects transformation-flows create --space {dsp_space} --file-path {file_path} --verbose'
        du.run_command(command)

    def push_tc(tc_data, objects_export_path, dsp_space):
        tc_name = dspTF.get_name_from_tc(tc_data)
        print("tf_name: " + tc_name)
        file_path = objects_export_path + tc_name + '.json'
        du.write_json_file(tc_data, file_path)
        command = f'datasphere objects task-chains create --space {dsp_space} --file-path {file_path} --verbose'
        du.run_command(command)

    def create_tf_with_between_clause(tf_data, field_name, low, high):
        tf_data = copy.deepcopy(tf_data)
        # Add low and high value to transformation flow name
        tf_name_old = dspTF.get_name_from_tf(tf_data)
        print ("tf_name_old: " + tf_name_old)
        part_extension = '_' + low + '-' + high
        tf_name = tf_name_old + part_extension
        tf_data['transformationflows'][tf_name] = tf_data['transformationflows'].pop(tf_name_old)
        tf_data['transformationflows'][tf_name]["@EndUserText.label"] = tf_data['transformationflows'][tf_name]["@EndUserText.label"] + part_extension
        tf_data['transformationflows'][tf_name]["contents"]["description"] = tf_data['transformationflows'][tf_name]["contents"]["description"] + part_extension
        sql_transform_name_old = tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['name']
        sql_transform_name = sql_transform_name_old.split('$')[0] + part_extension + "$TRF_TV_sqltransform1"
        tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['name'] = sql_transform_name

        #Navigate to the plain SQL query string and add partition clause
        plain_query = tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['definition']['@DataWarehouse.sqlEditor.query']
        print("Plain query: " + plain_query)
        updated_plain_query = f"{plain_query}\nWHERE \"{field_name}\" >= '{low}' AND \"{field_name}\" < '{high}'"
        print("Updated plain query: " + updated_plain_query)
        tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['definition']['@DataWarehouse.sqlEditor.query'] = updated_plain_query

        # Navigate to the structured JSON query and modify it
        structured_query = tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['definition']['query']['SELECT']
        structured_query['where'] = [
            {"ref": [field_name]}, ">=", {"val": low}, "and", {"ref": [field_name]}, "<", {"val": high}
        ]
        tf_data['transformationflows'][tf_name]['contents']['processes']['sqltransform1']['metadata']['config']['definition']['query']['SELECT'] = structured_query

        return tf_data
    
    def create_tc_from_tfs(tc_name, l_tf_names: list):
        tc = {
            "taskchains": {
                tc_name: {
                    "kind": "sap.dwc.taskChain",
                    "@EndUserText.label": tc_name,
                    "nodes": [
                        {
                            "id": 0,
                            "type": "START"
                        }
                    ],
                    "links": [
                        {
                            "startNode": {
                                "nodeId": 0,
                                "statusRequired": "ANY"
                            },
                            "endNode": {
                                "nodeId": 1
                            },
                            "id": 0
                        }
                    ]
                }
            }
        }
        id=0
        for tf_name in l_tf_names:
            # Add node
            id+=1
            nodes = tc['taskchains'][tc_name]["nodes"]
            nodes.append({
                "id": id,
                "type": "TASK",
                "taskIdentifier": {
                    "applicationId": "TRANSFORMATION_FLOWS",
                    "activity": "EXECUTE",
                    "objectId": tf_name
                }
            })
            links = tc['taskchains'][tc_name]["links"]
            links.append(
                {
                    "startNode": {
                        "nodeId": id,
                        "statusRequired": "COMPLETED"
                    },
                    "endNode": {
                        "nodeId": id+1
                    },
                    "id": id
                }
            )
        return tc

    def partition_tf(tf_data, field_name, partitions, objects_export_path, dsp_space):
        l_tf_names = []
        tf_original_name = dspTF.get_name_from_tf(tf_data)
        for low, high in partitions:
            tf_data_partitioned = dspTF.create_tf_with_between_clause(tf_data, field_name,low,high)
            dspTF.push_tf(tf_data_partitioned, objects_export_path, dsp_space)
            # store all partitioned tfs in list
            tf_name = dspTF.get_name_from_tf(tf_data_partitioned)
            l_tf_names.append(tf_name)
            print (l_tf_names)
        # Create task chain with all objects
        tc_name = tf_original_name + '_TASKCHAIN'
        tc = dspTF.create_tc_from_tfs(tc_name, l_tf_names)
        print("TC: " + json.dumps(tc, indent=4))
        dspTF.push_tc(tc, objects_export_path, dsp_space)