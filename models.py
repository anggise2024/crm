from app import db
from datetime import datetime

class FollowUpRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False, unique=True)
    customer_id = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    receiver_phone = db.Column(db.String(20))
    crm = db.Column(db.String(50), nullable=False)
    no_resi = db.Column(db.String(100))
    qty = db.Column(db.Integer, default=1)
    produk = db.Column(db.String(200), nullable=False)
    status_pengiriman = db.Column(db.String(50), default='PENDING')
    created_date = db.Column(db.DateTime, nullable=False)
    complete_date = db.Column(db.DateTime)
    # FU DIKIRIM - after order created  
    follow_up_1_status = db.Column(db.String(20), default='PENDING')  # PENDING, COMPLETED, OVERDUE
    follow_up_1_date = db.Column(db.DateTime)
    # FU TERKIRIM - after delivery (only available when FU DIKIRIM completed and status TERKIRIM)
    follow_up_2_status = db.Column(db.String(20), default='PENDING')  # PENDING, COMPLETED, OVERDUE
    follow_up_2_date = db.Column(db.DateTime)
    # FU PENAWARAN - (qty x 7) - 2 days after complete_date
    follow_up_3_status = db.Column(db.String(20), default='PENDING')  # PENDING, COMPLETED, OVERDUE
    follow_up_3_date = db.Column(db.DateTime)
    follow_up_3_scheduled_date = db.Column(db.DateTime)  # When FU PENAWARAN should be done
    overall_status = db.Column(db.String(20), default='BELUM')  # BELUM, SELESAI
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FollowUpRecord {self.order_id}>'

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemLog {self.action}>'
