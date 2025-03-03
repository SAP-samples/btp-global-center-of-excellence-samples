import os, json
from flask import Flask, request
from gen_ai_hub.proxy.native.openai import chat

app = Flask(__name__)
# Port number is required to fetch from env variable
# http://docs.cloudfoundry.org/devguide/deploy-apps/environment-variable.html#PORT
cf_port = os.getenv("PORT")

# Credentials for SAP AI Core need to be set as environment variables in the manifest.yml file
# AICORE_AUTH_URL
# AICORE_BASE_URL
# AICORE_CLIENT_ID
# AICORE_CLIENT_SECRET
# AICORE_RESOURCE_GROUP

# Credentials for SAP HANA Cloud, hardcoded for testing
SAP_HANA_CLOUD_ADDRESS  = ""
SAP_HANA_CLOUD_PORT     = 443
SAP_HANA_CLOUD_USER     = "MLUSER"
SAP_HANA_CLOUD_PASSWORD = ""
AI_CORE_MODEL_NAME      = "mistralai--mistral-large-instruct"

# Connect to SAP HANA Cloud
import hana_ml.dataframe as dataframe
conn = dataframe.ConnectionContext(
                                   address  = SAP_HANA_CLOUD_ADDRESS,
                                   port     = SAP_HANA_CLOUD_PORT,
                                   user     = SAP_HANA_CLOUD_USER,
                                   password = SAP_HANA_CLOUD_PASSWORD, 
                                  )
conn.connection.isconnected()

@app.route('/', methods=['GET'])
def processing():

    # Default task
    user_request = """What's the meaning of the letters SAP?"""
    
	# Get user request from the paylod
    payload = request.get_json()
    user_question = payload['user_request']
	
    # Create the embeddings for the new question, using SAP HANA Cloud's embedding engine
    user_question_sqlcompliant = user_question.replace("'", "''") # A single ' can lead to incorrect SQL syntax. Example: Who is SAP's boss?
    sql = f'''SELECT VECTOR_EMBEDDING('{user_question_sqlcompliant}', 'QUERY', 'SAP_NEB.20240715') EMBEDDEDQUESTION FROM DUMMY;'''
    user_question_embedding_str = conn.sql(sql).head(1).collect().iloc[0, 0]
	
    # Find the most similar questions, by comparing the new question's vector with the existing question's vectors, using SAP HANA Cloud's vector engine
    sql = f'''SELECT TOP 200 "AID", "QID", "QUESTION", COSINE_SIMILARITY("QUESTION_VECTOR", TO_REAL_VECTOR('{user_question_embedding_str}')) AS SIMILARITY
        FROM CHATBOT_FAQ_QUESTIONS ORDER BY "SIMILARITY" DESC, "AID", "QID" '''
    df_remote = conn.sql(sql)
	
    # Select at least the best n candidates, or more in case more have high similarity. 
    # TODO Test which values of n seems most suitable for the specific data
    top_n = max(df_remote.filter('SIMILARITY > 0.95').count(), 10)
	
    # Download the selected Questions as Pandas DataFrame for processing
    df_data = df_remote.head(top_n).select('AID', 'QID', 'QUESTION').collect()
	
    # Create a ROW-ID out of the AID and QID, which will simplify the identification of the selected Question and its corresponding Answer
    df_data['ROWID'] = df_data['AID'].astype(str) + '-' + df_data['QID'].astype(str) + ': '
    df_data = df_data[['ROWID', 'QUESTION']]
	
    # Turn the above Pandas dataframe with the candidate questions into block of text, for use with the Large Language Model
    candiates_str = df_data.to_string(header=False,
                                      index=False,
                                      index_names=False)
	
    # Prepare the prompt for the Large Language Model to select the best matching question from the candidates
    llm_prompt = f'''
    Task: which of the following candidate questions is closest to this one?
    {user_question}
    Only return the ID of the selected question, not the question itself. The ID are the first values in each row. 
    In case none of the candidate questions is a good match, return only: NONE

    -----------------------------------

    Candidate questions. Each question starts with the ID, followed by a :, followed by the question
    {candiates_str}
    '''

    # Send the prompt to the Large Language Model via the SAP Generative AI Hub
    messages = [{"role": "user", "content": llm_prompt}]
    kwargs = dict(model_name=AI_CORE_MODEL_NAME, messages=messages, temperature=0)
    response = chat.completions.create(**kwargs)

    # Extract the ROWID that was selected by the Large Language Model
    llm_response = response.choices[0].message.content.lstrip()  
	
    # Get the pre-defined Answer that belongs to the selected Question from the FAQ
    aid = qid = None
    matching_question = matching_answer = None
    if llm_response != 'NONE':
        aid, qid = llm_response.split('-')

        # From HANA Cloud get the question from the FAQ that matches the user request best
        df_remote = conn.table('CHATBOT_FAQ_QUESTIONS').filter(f''' "AID" = '{aid}' AND "QID" = '{qid}' ''').select('QUESTION')
        matching_question = df_remote.head(5).collect().iloc[0,0]
    
        # From HANA Cloud get the predefined answer of the above question from the FAQ
        df_remote = conn.table('CHATBOT_FAQ_ANSWERS').filter(f''' "AID" = '{aid}' ''').select('ANSWER')
        matching_answer = df_remote.head(5).collect().iloc[0,0]
    
    # Attempt to adjust the pre-defined response to a more natural answer, based on the user's specific phrase
    llm_prompt = f'''Task: Answer the following question. Only consider the context that is provided further below.
    {user_question}
    -----------------------------------
    Context to consider to answer the above question:
    {matching_answer}
    '''
    messages = [{"role": "user", "content": llm_prompt}]
    kwargs = dict(model_name=AI_CORE_MODEL_NAME, messages=messages, temperature=0)
    response = chat.completions.create(**kwargs)
    natural_answer = response.choices[0].message.content.lstrip()

    # Prepare the log
    answer_log = f"""The user question was:\n{user_question}
    \nThe selected question from the FAQ is:\n{matching_question}
    \nThe predefined answer to the selected question is:\n{matching_answer}
    \nThe natural answer is:\n{natural_answer}"""

	# Return the response and the log
    faq_response = natural_answer
    faq_response_log = answer_log
    return json.dumps({'faq_response': faq_response, 'faq_response_log': faq_response_log})
    #return {'faq_response': faq_response, 'faq_response_log': faq_response_log}

if __name__ == '__main__':
	if cf_port is None:
		app.run(host='0.0.0.0', port=5000, debug=True)
	else:
		app.run(host='0.0.0.0', port=int(cf_port), debug=True)