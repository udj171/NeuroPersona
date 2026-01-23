# ============================================================================
# SCRIPT 2: models.py - Database Schema & ORM Models
# ============================================================================

from datetime import datetime, timezone
from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID, JSONB
from sqlalchemy.types import TypeDecorator
import json
import uuid

class GUID(TypeDecorator):
    impl = str
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)

class JSONType(TypeDecorator):
    impl = str
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(GUID, default=uuid.uuid4, unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(1), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    assessments = db.relationship('Assessment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('age >= 13 AND age <= 120', name='valid_age_range'),
        CheckConstraint("sex IN ('M', 'F', 'O')", name='valid_sex_value'),
        Index('idx_user_external_id', 'external_id'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'external_id': str(self.external_id),
            'age': self.age,
            'sex': self.sex,
            'created_at': self.created_at.isoformat(),
            'assessment_count': self.assessments.count(),
        }
    
    def __repr__(self):
        return f'<User {self.id}: age={self.age}, sex={self.sex}>'

class Assessment(db.Model):
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(GUID, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    responses_json = db.Column(JSONType, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    completion_percentage = db.Column(db.Float, default=100.0)
    is_valid = db.Column(db.Boolean, default=True)
    validation_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    results = db.relationship('Result', uselist=False, backref='assessment', cascade='all, delete-orphan')
    vae_outputs = db.relationship('VAEOutput', uselist=False, backref='assessment', cascade='all, delete-orphan')
    personality_classifications = db.relationship('PersonalityClassification', uselist=False, backref='assessment', cascade='all, delete-orphan')
    gemini_interpretations = db.relationship('GeminiInterpretation', uselist=False, backref='assessment', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_assessment_user_id', 'user_id'),
        Index('idx_assessment_external_id', 'external_id'),
        Index('idx_assessment_created_at', 'created_at'),
        Index('idx_assessment_is_valid', 'is_valid'),
    )
    
    def to_dict(self, include_responses=False):
        data = {
            'id': self.id,
            'external_id': str(self.external_id),
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'completion_percentage': self.completion_percentage,
            'is_valid': self.is_valid,
        }
        if include_responses:
            data['responses'] = self.responses_json
        return data
    
    def __repr__(self):
        return f'<Assessment {self.id}: user_id={self.user_id}, valid={self.is_valid}>'

class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    raw_domain_scores = db.Column(JSONType, nullable=False)
    deception_susceptibility = db.Column(db.Float, nullable=False)
    corrected_domain_scores = db.Column(JSONType, nullable=False)
    domain_biases = db.Column(JSONType, nullable=False)
    validity_scores = db.Column(JSONType, nullable=True)
    
    vae_input_vector = db.Column(JSONType, nullable=False)
    scaling_factors = db.Column(JSONType, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_result_assessment_id', 'assessment_id'),
        Index('idx_result_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'raw_domain_scores': self.raw_domain_scores,
            'deception_susceptibility': self.deception_susceptibility,
            'corrected_domain_scores': self.corrected_domain_scores,
            'domain_biases': self.domain_biases,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<Result {self.id}: assessment_id={self.assessment_id}>'

class VAEOutput(db.Model):
    __tablename__ = 'vae_outputs'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    latent_representation = db.Column(JSONType, nullable=False)
    reconstruction_error = db.Column(db.Float, nullable=False)
    latent_distance_from_mean = db.Column(db.Float, nullable=False)
    local_density = db.Column(db.Float, nullable=False)
    novelty_score = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_vae_output_assessment_id', 'assessment_id'),
        Index('idx_vae_output_novelty_score', 'novelty_score'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'latent_representation': self.latent_representation,
            'reconstruction_error': self.reconstruction_error,
            'latent_distance_from_mean': self.latent_distance_from_mean,
            'local_density': self.local_density,
            'novelty_score': self.novelty_score,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<VAEOutput {self.id}: novelty={self.novelty_score:.4f}>'

class PersonalityClassification(db.Model):
    __tablename__ = 'personality_classifications'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    personality_type = db.Column(db.String(1), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    
    personality_details = db.Column(JSONType, nullable=True)
    type_description = db.Column(db.Text, nullable=True)
    key_traits = db.Column(JSONType, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint("personality_type IN ('A', 'B', 'C', 'D', 'E', 'F')", name='valid_personality_type'),
        Index('idx_personality_assessment_id', 'assessment_id'),
        Index('idx_personality_type', 'personality_type'),
        Index('idx_personality_confidence', 'confidence_score'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'personality_type': self.personality_type,
            'confidence_score': self.confidence_score,
            'personality_details': self.personality_details,
            'type_description': self.type_description,
            'key_traits': self.key_traits,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<PersonalityClassification {self.id}: type={self.personality_type}, confidence={self.confidence_score:.2f}>'

class GeminiInterpretation(db.Model):
    __tablename__ = 'gemini_interpretations'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    prompt_text = db.Column(db.Text, nullable=False)
    interpretation_text = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    api_status = db.Column(db.String(50), default='success')
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_gemini_assessment_id', 'assessment_id'),
        Index('idx_gemini_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'interpretation_text': self.interpretation_text,
            'response_time_ms': self.response_time_ms,
            'api_status': self.api_status,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<GeminiInterpretation {self.id}: status={self.api_status}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    details = db.Column(JSONType, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action} on {self.resource_type}>'
