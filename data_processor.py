import pandas as pd
import logging
from datetime import datetime, timedelta
import pytz
from google_sheets_service import GoogleSheetsService
from models import FollowUpRecord, SystemLog
from app import db

class DataProcessor:
    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.crm_names = ['HILDA', 'RANIA', 'ESTI']
    
    def process_daily_data(self):
        """Main function to process daily data from Google Sheets"""
        try:
            # Set timezone WIB (GMT+7)
            wib = pytz.timezone('Asia/Jakarta')
            current_time = datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"Starting daily data processing at {current_time}...")
            
            # Check if Google Sheets service is available
            if not self.sheets_service.service:
                logging.warning("Google Sheets service not available - authentication required")
                # Log system status
                log_entry = SystemLog()
                log_entry.action = "Data Processing Skipped"
                log_entry.details = "Google Sheets authentication failed. Please provide valid service account credentials."
                db.session.add(log_entry)
                db.session.commit()
                return
            
            # Read data from source sheet
            logging.info("Reading data from Google Sheets...")
            raw_data = self.sheets_service.read_sheet_data(self.sheets_service.source_sheet)
            
            if not raw_data or len(raw_data) < 2:
                logging.warning("No data found in source sheet")
                # Log system status
                log_entry = SystemLog()
                log_entry.action = "No Data Found"
                log_entry.details = "Google Sheets connection successful but no data found in source sheet"
                db.session.add(log_entry)
                db.session.commit()
                return
            
            # Debug: Log actual data structure
            headers = raw_data[0]
            data_rows = raw_data[1:]
            logging.info(f"Headers found: {headers}")
            logging.info(f"Number of headers: {len(headers)}")
            logging.info(f"First data row length: {len(data_rows[0]) if data_rows else 0}")
            
            # Pad rows to match header length if needed
            max_cols = len(headers)
            padded_rows = []
            for row in data_rows:
                if len(row) < max_cols:
                    row.extend([''] * (max_cols - len(row)))
                elif len(row) > max_cols:
                    row = row[:max_cols]
                padded_rows.append(row)
            
            df = pd.DataFrame(padded_rows, columns=headers)
            
            # Process and clean data
            cleaned_df = self.clean_and_filter_data(df)
            
            if cleaned_df.empty:
                logging.warning("No valid data after cleaning and filtering")
                return
            
            # Split and redistribute data
            redistributed_df = self.redistribute_crm_data(cleaned_df)
            
            # Update database
            self.update_database(redistributed_df)
            
            # Update follow-up statuses
            self.update_followup_statuses()
            
            # Write processed data back to target sheet
            self.write_processed_data(redistributed_df)
            
            # Log the operation
            log_entry = SystemLog()
            log_entry.action = "Daily Data Processing"
            log_entry.details = f"Processed {len(redistributed_df)} records"
            db.session.add(log_entry)
            db.session.commit()
            
            logging.info("Daily data processing completed successfully")
            
        except Exception as e:
            logging.error(f"Error in daily data processing: {e}")
            raise
    
    def clean_and_filter_data(self, df):
        """Clean and filter data according to specifications"""
        try:
            # Filter hanya produk propolis hepro (case insensitive)
            df = df[df['Produk'].str.contains('propolis hepro', case=False, na=False)].copy()
            logging.info(f"Filtered for propolis hepro products. Records found: {len(df)}")
            logging.info(f"Available products in data: {df['Produk'].unique() if 'Produk' in df.columns else 'No Produk column'}")
            
            # Clean customer names (uppercase, remove extra spaces)
            df.loc[:, 'Receiver Name'] = df['Receiver Name'].str.upper().str.strip()
            df.loc[:, 'Receiver Name'] = df['Receiver Name'].str.replace(r'\s+', ' ', regex=True)
            
            # Clean product names
            df.loc[:, 'Produk'] = df['Produk'].str.upper().str.strip()
            
            # Clean and standardize shipping status
            df.loc[:, 'Status Pengiriman'] = df['Status Pengiriman'].apply(self._standardize_shipping_status)
            
            # Parse and format dates
            df.loc[:, 'Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
            
            # For testing purposes, let's process all available data instead of filtering by yesterday
            # yesterday = datetime.now().date() - timedelta(days=1)
            # df = df[df['Created Date'].dt.date == yesterday]
            
            # Remove rows with missing critical data
            df = df.dropna(subset=['Order No.', 'Receiver Name', 'Created Date'])
            
            logging.info(f"Cleaned and filtered data: {len(df)} records")
            return df
            
        except Exception as e:
            logging.error(f"Error in data cleaning: {e}")
            return pd.DataFrame()
    
    def _standardize_shipping_status(self, status):
        """Standardize shipping status"""
        if pd.isna(status):
            return 'PENDING'
        
        status_lower = str(status).lower()
        if 'terkirim' in status_lower:
            return 'TERKIRIM'
        else:
            return 'PENDING'
    
    def redistribute_crm_data(self, df):
        """Redistribute CRM data evenly among HILDA, RANIA, ESTI"""
        try:
            # Split data into two groups
            assigned_crm = df[df['CRM'].isin(self.crm_names)].copy()
            unassigned_crm = df[~df['CRM'].isin(self.crm_names)].copy()
            
            # Redistribute unassigned data evenly
            if not unassigned_crm.empty:
                crm_cycle = self.crm_names * (len(unassigned_crm) // len(self.crm_names) + 1)
                unassigned_crm['CRM'] = crm_cycle[:len(unassigned_crm)]
            
            # Combine both groups
            result_df = pd.concat([assigned_crm, unassigned_crm], ignore_index=True)
            
            logging.info(f"Redistributed CRM data: {len(result_df)} records")
            return result_df
            
        except Exception as e:
            logging.error(f"Error in CRM redistribution: {e}")
            return df
    
    def update_database(self, df):
        """Update database with processed data"""
        try:
            # Set timezone WIB (GMT+7)
            wib = pytz.timezone('Asia/Jakarta')
            
            for _, row in df.iterrows():
                # Check if record already exists
                existing_record = FollowUpRecord.query.filter_by(order_id=row['Order No.']).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.customer_name = row['Receiver Name']
                    existing_record.receiver_phone = row.get('Receiver Phone', '')
                    existing_record.crm = row['CRM']
                    existing_record.status_pengiriman = row['Status Pengiriman']
                    existing_record.last_updated = datetime.now(wib).replace(tzinfo=None)
                    
                    # Update complete date if status changed to TERKIRIM
                    if row['Status Pengiriman'] == 'TERKIRIM' and not existing_record.complete_date:
                        existing_record.complete_date = datetime.now(wib).replace(tzinfo=None)
                        # Calculate FU PENAWARAN scheduled date: (qty x 7) - 2 days from complete_date
                        penawaran_days = (existing_record.qty * 7) - 2
                        existing_record.follow_up_3_scheduled_date = existing_record.complete_date + timedelta(days=penawaran_days)
                        
                else:
                    # Create new record
                    new_record = FollowUpRecord()
                    new_record.order_id = row['Order No.']
                    new_record.customer_id = row.get('CustomerID', '')
                    new_record.customer_name = row['Receiver Name']
                    new_record.receiver_phone = row.get('Receiver Phone', '')
                    new_record.crm = row['CRM']
                    new_record.no_resi = row.get('AWB No.', '')
                    new_record.qty = int(row.get('Qty', 1))
                    new_record.produk = row['Produk']
                    new_record.status_pengiriman = row['Status Pengiriman']
                    new_record.created_date = row['Created Date']
                    
                    # Set complete_date and calculate FU PENAWARAN if TERKIRIM
                    if row['Status Pengiriman'] == 'TERKIRIM':
                        new_record.complete_date = datetime.now(wib).replace(tzinfo=None)
                        # Calculate FU PENAWARAN scheduled date: (qty x 7) - 2 days from complete_date
                        penawaran_days = (new_record.qty * 7) - 2
                        new_record.follow_up_3_scheduled_date = new_record.complete_date + timedelta(days=penawaran_days)
                    else:
                        new_record.complete_date = None
                        
                    db.session.add(new_record)
            
            db.session.commit()
            logging.info("Database updated successfully")
            
        except Exception as e:
            logging.error(f"Error updating database: {e}")
            db.session.rollback()
            raise
    
    def update_followup_statuses(self):
        """Update follow-up statuses based on dates"""
        try:
            # Set timezone WIB (GMT+7)
            wib = pytz.timezone('Asia/Jakarta')
            records = FollowUpRecord.query.all()
            current_date = datetime.now(wib)
            
            for record in records:
                # Update Follow Up 1 status
                if record.follow_up_1_status == 'PENDING':
                    days_since_created = (current_date.date() - record.created_date.date()).days
                    if days_since_created > 1:
                        record.follow_up_1_status = 'OVERDUE'
                
                # Update Follow Up 2 status dengan logika baru: (quantity × 7) - 2
                if record.complete_date and record.follow_up_2_status == 'PENDING':
                    days_since_complete = (current_date.date() - record.complete_date.date()).days
                    # Hitung target follow up 2: (quantity × 7) - 2 hari
                    target_followup2_days = (record.qty * 7) - 2
                    
                    if days_since_complete >= target_followup2_days:
                        # Jika sudah mencapai target hari, set status OVERDUE jika lewat 1 hari dari target
                        if days_since_complete > target_followup2_days:
                            record.follow_up_2_status = 'OVERDUE'
                
                # Update overall status
                if (record.follow_up_1_status == 'COMPLETED' and 
                    (not record.complete_date or record.follow_up_2_status == 'COMPLETED')):
                    record.overall_status = 'SELESAI'
                elif (record.complete_date and record.follow_up_2_status == 'COMPLETED'):
                    record.overall_status = 'SELESAI'
            
            db.session.commit()
            logging.info("Follow-up statuses updated successfully")
            
        except Exception as e:
            logging.error(f"Error updating follow-up statuses: {e}")
            db.session.rollback()
    
    def write_processed_data(self, df):
        """Write processed data back to Google Sheets"""
        try:
            # Prepare data for writing
            headers = ['No', 'CRM', 'OrderID', 'No Resi', 'CustomerID', 'Customer Name', 
                      'QTY', 'Produk', 'Status pengiriman', 'Created Date', 'Follow up I', 
                      'Complete Date', 'Follow Up II', 'Status Follow Up']
            
            # Get all records from database
            records = FollowUpRecord.query.all()
            
            data_rows = []
            for i, record in enumerate(records, 1):
                row = [
                    i,
                    record.crm,
                    record.order_id,
                    record.no_resi or '',
                    record.customer_id,
                    record.customer_name,
                    record.qty,
                    record.produk,
                    record.status_pengiriman,
                    record.created_date.strftime('%Y-%m-%d') if record.created_date else '',
                    record.follow_up_1_status,
                    record.complete_date.strftime('%Y-%m-%d') if record.complete_date else '',
                    record.follow_up_2_status,
                    record.overall_status
                ]
                data_rows.append(row)
            
            # Clear target sheet and write new data
            self.sheets_service.clear_sheet(self.sheets_service.target_sheet)
            all_data = [headers] + data_rows
            self.sheets_service.write_sheet_data(self.sheets_service.target_sheet, all_data)
            
            logging.info("Processed data written to Google Sheets successfully")
            
        except Exception as e:
            logging.error(f"Error writing processed data: {e}")
