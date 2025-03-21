import os
import urllib.parse
import uuid
from datetime import date, datetime
from typing import TypedDict
import requests
from langchain_core.tools import tool


# os.environ["PAYROLL_API_KEY"] = "<YOUR API KEY>"
API_KEY = os.environ.get("PAYROLL_API_KEY")

base_url = 'https://sandbox.api.sap.com/successfactors/odata/v2/'

#randomly chosen
user_id = '100257'

get_header = {
    'Accept': 'application/json',
    'APIKey': API_KEY,
    "DataServiceVersion": "2.0"
}

post_header = {
    'Content-Type': 'application/json',
    'APIKey': API_KEY,
    "DataServiceVersion": "2.0"
}


class ExternalTimeData(TypedDict):
    startDate: str
    startTime: str
    endTime: str

@tool
def get_records(top:int):
    """Retrieve ExternalTimeData entries from the API for the current user.
    top: Specifies the number of entries to retrieve.
    """
    params = {}
    if top is not None:
        params['$top'] = top
    params['$filter'] = f'userId eq {user_id}'
    query_text = urllib.parse.urlencode(params, safe='(),')

    table = 'ExternalTimeData'
    url = f'{base_url}{table}?{query_text}'
    response = requests.get(url, headers=get_header)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return f'Error: {response.content}'


@tool
def post_records(data: ExternalTimeData, confirmation_message : str):
    """Post work time records to the API.
    The user is first asked for confirmation.
    Changes by the user to the times to post are returned in the ToolMessage.

        Args:
            data:
                startDate: YYYY-mm-dd
                startTime/endTime: ISO 8601 e.g. 'PT09H00M00S'/'PT18H30M00S' (9:00-18:30). The time frame must only include work time.
            confirmation_message: Confirmation message of the action containing a detailed summary.
            Include the specific date and time e.g. Confirm work time from 11:00 to 14:00 on June 15th 2025.
        """
    # externalCode: Optional parameter. If set the entry with this Code is updated.

    payload = dict(data)
    payload['startDate'] = f"/Date({int(datetime.fromisoformat(data['startDate']).timestamp()) * 1000})/"
    payload['externalCode'] = str(uuid.uuid1())
    payload['userId'] = user_id
    payload["userIdNav"] = {
        "__metadata": {
            "uri": f"https://sandbox.api.sap.com/successfactors/odata/v2/User('{user_id}')"
        }
    }

    table = 'ExternalTimeData'
    url = f'{base_url}{table}'

    response = requests.post(url, headers=post_header, json=payload)

    if response.status_code in (200, 201):
        return f'Entity created successfully: {data}'
    else:
        return  f'Error creating entity ({data}):  {response.status_code}: {response.content}'


@tool
def get_today():
    """Returns todays date."""
    return date.today()