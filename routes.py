import json
import logging
from flask import render_template, request, jsonify, send_file
from datetime import datetime, timedelta
from app import app, db
from models import FollowUpRecord, SystemLog
from data_processor import DataProcessor
import pandas as pd
import io

@app.route('/')
def dashboard():
    """Dashboard route with statistics"""
    try:
        # Get filters from request
        date_filter = request.args.get('date', '')
        crm_filter = request.args.get('crm', '')
        
        # Base query
        query = FollowUpRecord.query
        
        # Apply date filter if provided
        if date_filter:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(FollowUpRecord.created_date >= filter_date)
            query = query.filter(FollowUpRecord.created_date < filter_date + timedelta(days=1))
        
        # Apply CRM filter
        if crm_filter:
            query = query.filter(FollowUpRecord.crm == crm_filter)
        
        records = query.all()
        
        # Calculate statistics
        stats = {
            'total_orders': len(records),
            'total_customers': len(set(record.customer_id for record in records)),
            'total_complete': len([r for r in records if r.status_pengiriman == 'TERKIRIM']),
            'total_pending': len([r for r in records if r.status_pengiriman == 'PENDING']),
            'followup1_completed': len([r for r in records if r.follow_up_1_status == 'COMPLETED']),
            'followup2_completed': len([r for r in records if r.follow_up_2_status == 'COMPLETED']),
            'followup1_pending': len([r for r in records if r.follow_up_1_status in ['PENDING', 'OVERDUE']]),
            'followup2_pending': len([r for r in records if r.follow_up_2_status in ['PENDING', 'OVERDUE']])
        }
        
        # Get recent system logs for status display
        recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(5).all()
        
        # Check Google Sheets authentication status
        from google_sheets_service import GoogleSheetsService
        sheets_service = GoogleSheetsService()
        sheets_status = "Connected" if sheets_service.service else "Authentication Failed"
        
        return render_template('dashboard.html', stats=stats, 
                             date_filter=date_filter, crm_filter=crm_filter,
                             recent_logs=recent_logs, sheets_status=sheets_status)
        
    except Exception as e:
        logging.error(f"Error in dashboard route: {e}")
        return render_template('dashboard.html', stats={}, error=str(e))

@app.route('/data-view')
def data_view():
    """Data view route showing all records"""
    try:
        # Get filters from request
        crm_filter = request.args.get('crm', '')
        status_filter = request.args.get('status', '')
        search_query = request.args.get('search', '')
        
        # Base query
        query = FollowUpRecord.query
        
        # Apply filters
        if crm_filter:
            query = query.filter(FollowUpRecord.crm == crm_filter)
        
        if status_filter:
            query = query.filter(FollowUpRecord.status_pengiriman == status_filter)
        
        if search_query:
            query = query.filter(
                db.or_(
                    FollowUpRecord.customer_name.contains(search_query),
                    FollowUpRecord.order_id.contains(search_query),
                    FollowUpRecord.no_resi.contains(search_query)
                )
            )
        
        records = query.order_by(FollowUpRecord.created_date.desc()).all()
        
        return render_template('data_view.html', records=records, 
                             crm_filter=crm_filter, status_filter=status_filter, search_query=search_query)
        
    except Exception as e:
        logging.error(f"Error in data view route: {e}")
        return render_template('data_view.html', records=[], error=str(e))

@app.route('/crm-followup')
def crm_followup():
    """CRM follow-up route for yesterday's data"""
    try:
        # Get filters from request
        crm_filter = request.args.get('crm', '')
        today_followup = request.args.get('today_followup', '')
        date_filter = request.args.get('date', '')
        search_query = request.args.get('search', '')
        pending_followup = request.args.get('pending_followup', '')
        
        # Base query untuk tanggal
        query = FollowUpRecord.query
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(FollowUpRecord.created_date >= filter_date)
                query = query.filter(FollowUpRecord.created_date < filter_date + timedelta(days=1))
            except ValueError:
                # Jika format tanggal salah, tampilkan data kemarin
                yesterday = datetime.now().date() - timedelta(days=1)
                query = query.filter(FollowUpRecord.created_date >= yesterday)
                query = query.filter(FollowUpRecord.created_date < yesterday + timedelta(days=1))
        else:
            # Default: tampilkan data kemarin
            yesterday = datetime.now().date() - timedelta(days=1)
            query = query.filter(FollowUpRecord.created_date >= yesterday)
            query = query.filter(FollowUpRecord.created_date < yesterday + timedelta(days=1))
            date_filter = yesterday.strftime('%Y-%m-%d')
        
        # Apply additional filters
        if crm_filter:
            query = query.filter(FollowUpRecord.crm == crm_filter)
        
        # Filter untuk follow up hari ini
        if today_followup == 'true':
            today = datetime.now().date()
            
            # Subquery untuk Follow Up I yang perlu dilakukan hari ini
            followup1_today = query.filter(
                FollowUpRecord.follow_up_1_status.in_(['PENDING', 'OVERDUE']),
                FollowUpRecord.created_date <= today
            )
            
            # Subquery untuk Follow Up II yang perlu dilakukan hari ini
            followup2_today = query.filter(
                FollowUpRecord.follow_up_1_status == 'COMPLETED',
                FollowUpRecord.follow_up_2_status.in_(['PENDING', 'OVERDUE']),
                FollowUpRecord.status_pengiriman == 'TERKIRIM',
                FollowUpRecord.complete_date.isnot(None)
            )
            
            # Gabungkan kedua kondisi
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    FollowUpRecord.id.in_([r.id for r in followup1_today]),
                    FollowUpRecord.id.in_([r.id for r in followup2_today])
                )
            )
        
        # Filter untuk belum follow up
        if pending_followup == 'true':
            from sqlalchemy import and_, or_
            query = query.filter(
                or_(
                    # FU DIKIRIM belum selesai
                    FollowUpRecord.follow_up_1_status != 'COMPLETED',
                    # FU TERKIRIM belum selesai (hanya jika syarat terpenuhi)
                    and_(
                        FollowUpRecord.follow_up_1_status == 'COMPLETED',
                        FollowUpRecord.status_pengiriman == 'TERKIRIM',
                        FollowUpRecord.follow_up_2_status != 'COMPLETED'
                    ),
                    # FU PENAWARAN belum selesai (hanya jika sudah terjadwal dan waktunya sudah tiba)
                    and_(
                        FollowUpRecord.follow_up_3_scheduled_date.isnot(None),
                        FollowUpRecord.follow_up_3_scheduled_date <= datetime.now().date(),
                        FollowUpRecord.follow_up_3_status != 'COMPLETED'
                    )
                )
            )
        
        if search_query:
            query = query.filter(
                db.or_(
                    FollowUpRecord.customer_name.contains(search_query),
                    FollowUpRecord.order_id.contains(search_query)
                )
            )
        
        records = query.order_by(FollowUpRecord.created_date.desc()).all()
        
        import pytz
        wib = pytz.timezone('Asia/Jakarta')
        current_time_wib = datetime.now(wib)
        current_date = current_time_wib.date()
        
        return render_template('crm_followup.html', records=records, 
                             crm_filter=crm_filter, search_query=search_query,
                             date_filter=date_filter, today_followup=today_followup,
                             pending_followup=pending_followup, now=current_time_wib,
                             current_date=current_date)
        
    except Exception as e:
        logging.error(f"Error in CRM follow-up route: {e}")
        return render_template('crm_followup.html', records=[], error=str(e))

@app.route('/update-followup', methods=['POST'])
def update_followup():
    """Update follow-up status"""
    try:
        import pytz
        
        data = request.get_json()
        record_id = data.get('record_id')
        followup_type = data.get('type')  # 'followup1', 'followup2', or 'followup3'
        
        record = FollowUpRecord.query.get(record_id)
        if not record:
            return jsonify({'success': False, 'message': 'Record not found'})
        
        # Set timezone WIB (GMT+7)
        wib = pytz.timezone('Asia/Jakarta')
        current_time_wib = datetime.now(wib)
        # Store as WIB time without timezone info (naive datetime)
        current_time_wib_naive = current_time_wib.replace(tzinfo=None)
        
        if followup_type == 'followup1':  # FU DIKIRIM
            record.follow_up_1_status = 'COMPLETED'
            record.follow_up_1_date = current_time_wib_naive
        elif followup_type == 'followup2':  # FU TERKIRIM
            # Only allow if FU DIKIRIM is completed and status is TERKIRIM
            if record.follow_up_1_status != 'COMPLETED':
                return jsonify({'success': False, 'message': 'FU DIKIRIM harus diselesaikan terlebih dahulu'})
            if record.status_pengiriman != 'TERKIRIM':
                return jsonify({'success': False, 'message': 'Status pengiriman harus TERKIRIM'})
            record.follow_up_2_status = 'COMPLETED'
            record.follow_up_2_date = current_time_wib_naive
        elif followup_type == 'followup3':  # FU PENAWARAN
            # Only allow if scheduled date has passed
            if not record.follow_up_3_scheduled_date:
                return jsonify({'success': False, 'message': 'FU PENAWARAN belum terjadwal'})
            # Compare with WIB date
            if current_time_wib.date() < record.follow_up_3_scheduled_date:
                return jsonify({'success': False, 'message': 'FU PENAWARAN belum waktunya'})
            record.follow_up_3_status = 'COMPLETED'
            record.follow_up_3_date = current_time_wib_naive
        
        # Update overall status - SELESAI ketika semua follow up sudah COMPLETED
        if (record.follow_up_1_status == 'COMPLETED' and 
            record.follow_up_2_status == 'COMPLETED' and 
            record.follow_up_3_status == 'COMPLETED'):
            record.overall_status = 'SELESAI'
        
        db.session.commit()
        
        # Generate WhatsApp URL
        phone = record.receiver_phone
        if phone:
            # Clean phone number (remove non-digits)
            phone_clean = ''.join(filter(str.isdigit, phone))
            if phone_clean.startswith('0'):
                phone_clean = '62' + phone_clean[1:]  # Convert to international format
            elif not phone_clean.startswith('62'):
                phone_clean = '62' + phone_clean
            
            whatsapp_url = f"https://wa.me/{phone_clean}"
        else:
            whatsapp_url = None
        
        return jsonify({
            'success': True, 
            'message': 'Follow-up updated successfully',
            'timestamp_wib': current_time_wib.strftime('%Y-%m-%d %H:%M:%S WIB'),
            'whatsapp_url': whatsapp_url
        })
        
    except Exception as e:
        logging.error(f"Error updating follow-up: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/manual-update', methods=['POST'])
def manual_update():
    """Manually trigger data update"""
    try:
        processor = DataProcessor()
        processor.process_daily_data()
        
        return jsonify({'success': True, 'message': 'Data updated successfully'})
        
    except Exception as e:
        logging.error(f"Error in manual update: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<data_type>')
def download_data(data_type):
    """Download data in Excel format"""
    try:
        if data_type == 'all':
            records = FollowUpRecord.query.all()
        elif data_type == 'pending':
            records = FollowUpRecord.query.filter_by(status_pengiriman='PENDING').all()
        elif data_type == 'completed':
            records = FollowUpRecord.query.filter_by(status_pengiriman='TERKIRIM').all()
        else:
            return jsonify({'error': 'Invalid data type'})
        
        # Convert to DataFrame
        data = []
        for record in records:
            data.append({
                'CRM': record.crm,
                'Order ID': record.order_id,
                'No Resi': record.no_resi,
                'Customer ID': record.customer_id,
                'Customer Name': record.customer_name,
                'QTY': record.qty,
                'Produk': record.produk,
                'Status Pengiriman': record.status_pengiriman,
                'Created Date': record.created_date.strftime('%Y-%m-%d') if record.created_date else '',
                'Complete Date': record.complete_date.strftime('%Y-%m-%d') if record.complete_date else '',
                'Follow Up 1': record.follow_up_1_status,
                'Follow Up 2': record.follow_up_2_status,
                'Overall Status': record.overall_status
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel file in memory using ExcelWriter
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'crm_data_{data_type}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
        
    except Exception as e:
        logging.error(f"Error downloading data: {e}")
        return jsonify({'error': str(e)})

@app.route('/recreate-database', methods=['POST'])
def recreate_database():
    """Recreate database tables with new schema"""
    try:
        # Drop all tables
        db.drop_all()
        # Create all tables with new schema
        db.create_all()
        
        # Run data processing to populate with fresh data
        processor = DataProcessor()
        processor.process_daily_data()
        
        return jsonify({"success": True, "message": "Database recreated and populated successfully"})
    except Exception as e:
        logging.error(f"Error recreating database: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete-all-records', methods=['POST'])
def delete_all_records():
    """Delete all follow-up records"""
    try:
        # Delete all records
        deleted_count = FollowUpRecord.query.count()
        FollowUpRecord.query.delete()
        
        # Delete all system logs
        SystemLog.query.delete()
        
        db.session.commit()
        
        # Log the operation
        log_entry = SystemLog()
        log_entry.action = "Delete All Records"
        log_entry.details = f"Deleted {deleted_count} records"
        db.session.add(log_entry)
        db.session.commit()
        
        logging.info(f"Successfully deleted all {deleted_count} records")
        return jsonify({'success': True, 'message': f'Successfully deleted {deleted_count} records'})
        
    except Exception as e:
        logging.error(f"Error deleting all records: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
