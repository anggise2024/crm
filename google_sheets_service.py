import os
import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSheetsService:
    def __init__(self):
        self.service = None
        self.spreadsheet_id = "14cEoyQaYIgtnz1W0UlhY0j38f1_2AnwfDshL1Gv_Kk8"
        self.source_sheet = "order-update"
        self.target_sheet = "followed-up"
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account"""
        try:
            # Check if service account file exists
            if not os.path.exists('service_account.json'):
                logging.error("service_account.json file not found")
                raise FileNotFoundError("service_account.json file not found")
            
            # Load service account credentials from file
            with open('service_account.json', 'r') as f:
                service_account_info = json.load(f)
            
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            self.service = build('sheets', 'v4', credentials=creds)
            logging.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logging.error(f"Failed to authenticate with Google Sheets API: {e}")
            # Set service to None to prevent further errors
            self.service = None
    
    def read_sheet_data(self, sheet_name, range_name="A:Z"):
        """Read data from a specific sheet"""
        try:
            if not self.service:
                logging.error("Google Sheets service not authenticated")
                return []
                
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range_name}"
            ).execute()
            
            values = result.get('values', [])
            logging.info(f"Successfully read {len(values)} rows from {sheet_name}")
            return values
            
        except HttpError as e:
            logging.error(f"Failed to read sheet data: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error reading sheet data: {e}")
            return []
    
    def write_sheet_data(self, sheet_name, data, range_name="A1"):
        """Write data to a specific sheet"""
        try:
            if not self.service:
                logging.error("Google Sheets service not authenticated")
                return None
                
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range_name}",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logging.info(f"Successfully wrote {len(data)} rows to {sheet_name}")
            return result
            
        except HttpError as e:
            logging.error(f"Failed to write sheet data: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error writing sheet data: {e}")
            return None
    
    def append_sheet_data(self, sheet_name, data):
        """Append data to a specific sheet"""
        try:
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:Z",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logging.info(f"Successfully appended {len(data)} rows to {sheet_name}")
            return result
            
        except HttpError as e:
            logging.error(f"Failed to append sheet data: {e}")
            return None
    
    def clear_sheet(self, sheet_name, range_name="A:Z"):
        """Clear data from a specific sheet"""
        try:
            if not self.service:
                logging.error("Google Sheets service not authenticated")
                return None
                
            result = self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range_name}"
            ).execute()
            
            logging.info(f"Successfully cleared {sheet_name}")
            return result
            
        except HttpError as e:
            logging.error(f"Failed to clear sheet: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error clearing sheet: {e}")
            return None
