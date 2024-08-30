# -----------------
# Introduction
# -----------------
# 
# This Python script generate objects for SAP Datasphere. Two use cases:
# - Datasphere (DSP) View generation based on Remote Tables
#   design time SQL views in DSP for each Remote Table (RT) that 
#   resides in a given space and then pushes the view definition to DSP via the DSP Command Line Interface.
#   The view is "exposed" so that it can be accessed from the Open SQL schema
#
# - DSP Transformation Flow generation, based on partition criteria. You choose an existing Transformation flow,
#   choose a field, and supply the partitioning criteria, then based on that it generates multiple TFs with
#   the proper WHERE statement in the SQL part of the flow. It also generates a TaskChain to run all 
#   transformation flows.
#
# Author: Sefan Linders
# Changelog: 
# - 16/5/2023: Initial version
# - 19/7/2023: Changed from dwc to datasphere commands
# - 6/11/2023: Adapted to DSP CLI command changes, wait function set to 0
# - 6/5/2024: Moved credentials to file, added transformation flow partitioning feature

# Prereqs
# - Install Datasphere CLI (npm install -g @sap/datasphere-cli)
# - Create Database Analysis User (with Space Schema access) on Datasphere for connection to HDB. https://help.sap.com/docs/SAP_DATASPHERE/9f804b8efa8043539289f42f372c4862/c28145bcb76c4415a1ec6265dd2a4c11.html?locale=en-US
# - Prepare DSP CLI secrets file according to https://help.sap.com/docs/SAP_DATASPHERE/d0ecd6f297ac40249072a44df0549c1a/eb7228a171a842fa84e48c899d48c970.html?locale=en-US#log-in-by-passing-oauth-client-information-in-a-secrets-file
# - If you want to avoid a login process, use the following instructions and adapt code under "Logon procedure": https://help.sap.com/docs/SAP_DATASPHERE/d0ecd6f297ac40249072a44df0549c1a/eb7228a171a842fa84e48c899d48c970.html?locale=en-US#avoid-running-a-login-command-by-extracting-access-and-refresh-tokens
# - To use the hdbcli package, install using pip: pip3 install hdbcli

# -----------------------------------------------------------
# Static variables, these you have to adjust
# -----------------------------------------------------------

# dsp host and credentials file path
dsp_logon_data_file = 'DSP_object_generation/dsp_logon_data.json'

# File paths
objects_export_path = 'DSP_object_generation/objects_export/'
objects_import_path = 'DSP_object_generation/objects_import/'

# -----------------------------------------------------------
# Package import
# -----------------------------------------------------------
from dsp_utilities import dspUtilities as du
from dsp_tf import dspTF as dtf
from dsp_rt_to_view_generation import r2v

# -----------------------------------------------------------
# Logout and login (optional, if not already logged in correctly)
# -----------------------------------------------------------
du.logoutlogin(dsp_logon_data_file)

# -----------------------------------------------------------
# Run RT 2 View generation
# -----------------------------------------------------------

# Datasphere (DSP) View generation based on Remote Tables
# Dsp_logon_data_file: File containing login data for accessing the system
# <SCHEMA_NAME>: Schema to read the existing remote tables from and write the generated view to
# Objects_export_path: Path where the generated objects will be exported
r2v = r2v(dsp_logon_data_file, 'SEFANGENERATESTUFF', objects_export_path)
r2v.loopAndGo()

# -----------------------------------------------------------
# Partition a transformation flow
# -----------------------------------------------------------

# -----------------------------------------------------------
# Read transformation flow
# <SCHEMA_NAME>: Space to read the existing transformation 
#   flow from
# <Transformation flow name>: Technical name of the existing transformation flow
# Objects_export_path: Path where the existing transformation flow will be written to before partitioning
# -----------------------------------------------------------

# tf_data = dtf.read_tf('SEFANGENERATESTUFF', 'UC2_TF', objects_import_path)

# -----------------------------------------------------------
# Generate partitioned transformation flows and task chain
# -----------------------------------------------------------
# tf_data: the previously read JSON data of the original transformation flow
# <COLUMN_NAME>: the column to partition on
# partitions: the partition definition with lower and upper bounds 
# <SCHEMA_NAME>: Space to write the partitioned transformation flows 
#   and write the generated task chain to
# <Transformation flow name>: Technical name of the existing transformation flow
# Objects_export_path: Path where the existing transformation flow will be written to before partitioning

partitions = [
    ('1','5'),
    ('5','10'),
    ('10','15'),
    ('15','20'),
    ('20','25'),
    ('25','30'),
    ('30','35')
]
# dtf.partition_tf(tf_data, 'SOMESTRING', partitions, objects_export_path, 'SEFANGENERATESTUFF')