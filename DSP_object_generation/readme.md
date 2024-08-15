
# Remote table to View generation
Read blog https://community.sap.com/t5/technology-blogs-by-sap/sap-datasphere-view-generation-with-python-and-the-command-line-interface/ba-p/13558181

# Transformation Flow Partition generation
Read blog ...
The rest of the text below are some random comments I wrote down while writing the code

## Steps
- Read transformation flow CSN using space and object name into a file
- Define partitioning variables: field and partition arrays
- For each partition, create new transformation flow and number up
- Create task chain

## Knotted down some commands

### Read transformation flow and store as file
datasphere objects transformation-flows list --space SEFANGENERATESTUFF
datasphere objects transformation-flows read --space SEFANGENERATESTUFF --technical-name UC2_TF_NO_PART --output objects_import/UC2_TF_NO_PART.csn

### Read taskchain
datasphere objects task-chains read --space SEFANGENERATESTUFF --technical-name UC2_TF_PART_TC --output objects_import/UC2_TF_PART_TC.csn

### Other commands 
datasphere config host set <host>
datasphere objects views update --host https://xxxxx.hcs.cloud.sap/ --space SEFANGENERATESTUFF --file-path DSP_object_generation/objects_output/space_SEFANGENERATESTUFF_object_T0_ALL_V.csn --verbose