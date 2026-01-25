#!/usr/bin/env python
# ============================================================================
# migrations_reset.py - Force database schema recreation
# Run this once when schema changes to ensure clean database
# ============================================================================

import os
import logging
from app import app, db
from models import User, Assessment, Result, VAEOutput, PersonalityClassification, GeminiInterpretation, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """Drop all tables and recreate with new schema"""
    with app.app_context():
        try:
            logger.info("[MIGRATION] Starting database reset...")
            logger.info(f"[MIGRATION] Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
            
            # Drop all tables
            logger.info("[MIGRATION] Dropping all existing tables...")
            db.drop_all()
            logger.info("[MIGRATION] ✓ All tables dropped")
            
            # Recreate all tables with new schema
            logger.info("[MIGRATION] Creating new tables with updated schema...")
            db.create_all()
            logger.info("[MIGRATION] ✓ All tables recreated")
            
            # Verify tables exist
            logger.info("[MIGRATION] Verifying tables...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"[MIGRATION] ✓ Tables created: {', '.join(tables)}")
            
            # Test creating a user
            logger.info("[MIGRATION] Testing user creation...")
            test_user = User(age=25, sex='M')
            db.session.add(test_user)
            db.session.commit()
            logger.info(f"[MIGRATION] ✓ Test user created: {test_user.id}")
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()
            logger.info("[MIGRATION] ✓ Test user deleted")
            
            logger.info("[MIGRATION] ✅ Database reset complete!")
            return True
            
        except Exception as e:
            logger.error(f"[MIGRATION] ✗ Error during reset: {str(e)}")
            logger.error(f"[MIGRATION] Traceback: {__import__('traceback').format_exc()}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = reset_database()
    exit(0 if success else 1)
