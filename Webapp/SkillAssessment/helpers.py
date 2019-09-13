from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
import pickle
import os


def getSheets():
    """
    Get Google Sheets Object for Sheets navigation and fetching operations.
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']      # Read Only

    if os.path.exists('SkillAssessment/authentication/token_sheets.pickle'):
        with open('SkillAssessment/authentication/token_sheets.pickle', 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'SkillAssessment/authentication/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

        with open('SkillAssessment/authentication/token_sheets.pickle', 'wb') as token:
            pickle.dump(creds, token, protocol=pickle.HIGHEST_PROTOCOL)

    service = build('sheets', 'v4', credentials=creds)
    return service


def getSheet(Sheets, sheet_id, sheet_name):
    """ 
    Fetches google sheet corresponding to `sheet_id` and `sheet_name`, and transfors
    the object into a pandas dataframe.

    Returns the dataframe
    """
    sheet  = Sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_name).execute()

    header = sheet.get('values', [])[0]   # Assumes first line is header!
    values = sheet.get('values', [])[1:]  # Everything else is data.
    values = [y for y in [x for x in values if x] if not all([i=='' for i in y])]   # Fetch only non-empty rows

    if not values:
        print('No data found.')
    else:
        try:
            df = pd.DataFrame(data=values, columns=header)
            if ('✓' in df.columns):
                df = df.drop(['✓', ''], axis=1).dropna(how='all')
                print (df.head())
            return df
        except Exception as e:
            print ("Exception occurred while parsing sheet to dataframe | Error: {}".format(e))
    return None
