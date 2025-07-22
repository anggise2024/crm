import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from data_processor import DataProcessor

scheduler = None


def daily_update_job():
    """Job function that runs daily at 8 AM"""
    from app import app

    with app.app_context():
        try:
            logging.info("Starting scheduled daily update job...")
            processor = DataProcessor()
            processor.process_daily_data()
            logging.info("Scheduled daily update job completed successfully")
        except Exception as e:
            logging.error(f"Error in scheduled daily update job: {e}")


def start_scheduler():
    """Start the scheduler"""
    global scheduler

    if scheduler is None:
        scheduler = BackgroundScheduler()

        # Schedule job every 2 minutes for testing (change back to daily later)
        scheduler.add_job(
            func=daily_update_job,
            trigger=CronTrigger(minute='*/2'),  # Every 2 minutes
            id='daily_update_job',
            name='Daily Data Update Job',
            replace_existing=True)

        scheduler.start()
        logging.info("Scheduler started successfully")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler

    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logging.info("Scheduler stopped")
