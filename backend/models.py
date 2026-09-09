# ============================================================================
# SCRIPT 2: models.py - Database Schema & ORM Models
# ============================================================================

from datetime import datetime, timezone
from sqlalchemy import func, Index, CheckConstraint, UniqueConstraint, String
from sqlalchemy.types import TypeDecorator
import json
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer
import uuid

db = SQLAlchemy()


class JSONType(TypeDecorator):
    """JSON type - stores as string, compatible with SQLite and PostgreSQL"""
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            print(f"[JSONType] Error encoding to JSON: {e}, value: {value}")
            return None
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError) as e:
            print(f"[JSONType] Error decoding from JSON: {e}, value: {value}")
            return None


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = db.Column(db.String(255), unique=True, nullable=True)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(1), nullable=False)
    # Use func.now() for server-side defaults (PostgreSQL compatible)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    assessments = db.relationship('Assessment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('age >= 13 AND age <= 120', name='valid_age_range'),
        CheckConstraint("sex IN ('M', 'F', 'O')", name='valid_sex_value'),
        Index('idx_user_external_id', 'external_id'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'external_id': str(self.external_id) if self.external_id else None,
            'age': self.age,
            'sex': self.sex,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'assessment_count': self.assessments.count(),
        }
    
    def __repr__(self):
        return f'<User {self.id}: age={self.age}, sex={self.sex}>'


class Assessment(db.Model):
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    responses_json = db.Column(JSONType, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    completion_percentage = db.Column(db.Float, default=100.0)
    is_valid = db.Column(db.Boolean, default=True)
    validation_notes = db.Column(db.Text, nullable=True)
    # Use func.now() for server-side defaults (PostgreSQL compatible)
    created_at = db.Column(db.DateTime, default=func.now())
    completed_at = db.Column(db.DateTime, nullable=True)
    
    results = db.relationship('Result', uselist=False, backref='assessment', cascade='all, delete-orphan')
    model_outputs = db.relationship('ModelOutput', uselist=False, backref='assessment', cascade='all, delete-orphan')
    personality_classifications = db.relationship('PersonalityClassification', uselist=False, backref='assessment', cascade='all, delete-orphan')
    interpretations = db.relationship('Interpretation', uselist=False, backref='assessment', cascade='all, delete-orphan')
    
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
            'user_id': str(self.user_id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
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
    """Scoring output: the five trait scores before and after the correction."""
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)

    raw_trait_scores = db.Column(JSONType, nullable=False)        # O,C,E,A,N on 0-100
    corrected_trait_scores = db.Column(JSONType, nullable=False)  # after the lambda shift
    trait_biases = db.Column(JSONType, nullable=False)            # signed shift per trait

    lambda_score = db.Column(db.Float, nullable=False)            # 0-1
    lambda_band = db.Column(db.String(20), nullable=False)        # light | moderate | substantial
    lambda_analysis = db.Column(JSONType, nullable=True)          # contradictions, style flags

    validity_responses = db.Column(JSONType, nullable=True)       # V1-V5 as answered
    model_input_vector = db.Column(JSONType, nullable=False)      # the 50 raw responses

    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_result_assessment_id', 'assessment_id'),
        Index('idx_result_created_at', 'created_at'),
        Index('idx_result_lambda', 'lambda_score'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'raw_trait_scores': self.raw_trait_scores,
            'corrected_trait_scores': self.corrected_trait_scores,
            'trait_biases': self.trait_biases,
            'lambda_score': self.lambda_score,
            'lambda_band': self.lambda_band,
            'lambda_analysis': self.lambda_analysis,
            'validity_responses': self.validity_responses,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Result {self.id}: assessment_id={self.assessment_id}>'


class ModelOutput(db.Model):
    """Latent embedding and novelty from the trained VAE."""
    __tablename__ = 'model_outputs'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)

    weights_loaded = db.Column(db.Boolean, nullable=False, default=False)
    model_version = db.Column(db.String(64), nullable=True)

    latent_representation = db.Column(JSONType, nullable=True)
    reconstruction_error = db.Column(db.Float, nullable=True)
    latent_distance_from_mean = db.Column(db.Float, nullable=True)
    novelty_score = db.Column(db.Float, nullable=True)
    percentiles = db.Column(JSONType, nullable=True)

    created_at = db.Column(db.DateTime, default=func.now())

    __table_args__ = (
        Index('idx_model_output_assessment_id', 'assessment_id'),
        Index('idx_model_output_novelty', 'novelty_score'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'weights_loaded': self.weights_loaded,
            'model_version': self.model_version,
            'latent_representation': self.latent_representation,
            'reconstruction_error': self.reconstruction_error,
            'latent_distance_from_mean': self.latent_distance_from_mean,
            'novelty_score': self.novelty_score,
            'percentiles': self.percentiles,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ModelOutput {self.id}: trained={self.weights_loaded}>'


class PersonalityClassification(db.Model):
    """Which of the learned clusters this profile fell nearest to."""
    __tablename__ = 'personality_classifications'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)

    type_index = db.Column(db.Integer, nullable=False)
    type_name = db.Column(db.String(80), nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)   # null when untrained
    runner_up_name = db.Column(db.String(80), nullable=True)
    type_traits = db.Column(JSONType, nullable=True)        # centroid profile, 0-100
    type_probabilities = db.Column(JSONType, nullable=True)

    created_at = db.Column(db.DateTime, default=func.now())

    __table_args__ = (
        Index('idx_personality_assessment_id', 'assessment_id'),
        Index('idx_personality_type_index', 'type_index'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'type_index': self.type_index,
            'type_name': self.type_name,
            'confidence_score': self.confidence_score,
            'runner_up_name': self.runner_up_name,
            'type_traits': self.type_traits,
            'type_probabilities': self.type_probabilities,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<PersonalityClassification {self.id}: {self.type_name}>'


class Interpretation(db.Model):
    """The written reading. Generated locally; no third-party API is involved."""
    __tablename__ = 'interpretations'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False, unique=True)

    interpretation_text = db.Column(db.Text, nullable=False)
    backend = db.Column(db.String(20), nullable=False, default='template')
    model_name = db.Column(db.String(120), nullable=True)
    generation_time_ms = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=func.now())

    __table_args__ = (
        Index('idx_interpretation_assessment_id', 'assessment_id'),
        Index('idx_interpretation_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'interpretation_text': self.interpretation_text,
            'backend': self.backend,
            'model_name': self.model_name,
            'generation_time_ms': self.generation_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Interpretation {self.id}: backend={self.backend}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    details = db.Column(JSONType, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    # Use func.now() for server-side defaults (PostgreSQL compatible)
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action} on {self.resource_type}>'
