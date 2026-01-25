# ============================================================================
# EFOPA Extension Models - Extended Assessment Data Storage
# ============================================================================
# Additional database models for storing EFOPA enhancement results
# These extend the existing models without modifying them directly
# ============================================================================

from datetime import datetime, timezone
from sqlalchemy import func, Index, ForeignKey, UniqueConstraint, String, Integer, Float, Text, Boolean, DateTime
from sqlalchemy.types import TypeDecorator
import json
from flask_sqlalchemy import SQLAlchemy

# Import db from existing models to ensure consistency
from models import db, JSONType

class EFOPALambdaAnalysis(db.Model):
    """
    Stores Lambda (deception susceptibility) analysis results.
    """
    __tablename__ = 'efopa_lambda_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    lambda_score = db.Column(db.Float, nullable=False)
    deception_level = db.Column(db.String(20), nullable=False)  # Low, Moderate, High
    
    contradictions_detected = db.Column(JSONType, nullable=False)
    contradiction_count = db.Column(db.Integer, nullable=False)
    extreme_consistency_score = db.Column(db.Float, nullable=False)
    response_variability_penalty = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_lambda_assessment_id', 'assessment_id'),
        Index('idx_efopa_lambda_score', 'lambda_score'),
        Index('idx_efopa_deception_level', 'deception_level'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'lambda_score': self.lambda_score,
            'deception_level': self.deception_level,
            'contradiction_count': self.contradiction_count,
            'contradictions_detected': self.contradictions_detected,
            'extreme_consistency_score': self.extreme_consistency_score,
            'response_variability_penalty': self.response_variability_penalty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPALambdaAnalysis {self.id}: lambda={self.lambda_score:.4f}, level={self.deception_level}>'


class EFOPADomainCosts(db.Model):
    """
    Stores honesty cost analysis for each domain.
    """
    __tablename__ = 'efopa_domain_costs'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    domain_costs_data = db.Column(JSONType, nullable=False)
    average_honesty_cost = db.Column(db.Float, nullable=False)
    total_fitness_impact = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_domain_costs_assessment_id', 'assessment_id'),
        Index('idx_efopa_avg_honesty_cost', 'average_honesty_cost'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'domain_costs': self.domain_costs_data,
            'average_honesty_cost': self.average_honesty_cost,
            'total_fitness_impact': self.total_fitness_impact,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPADomainCosts {self.id}: avg_cost={self.average_honesty_cost:.4f}>'


class EFOPAElephantModule(db.Model):
    """
    Stores Elephant Module (implicit cognition) analysis.
    """
    __tablename__ = 'efopa_elephant_module'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    elephant_analysis_data = db.Column(JSONType, nullable=False)
    weighted_credibility_scores = db.Column(JSONType, nullable=False)
    average_weighted_credibility = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_elephant_assessment_id', 'assessment_id'),
        Index('idx_efopa_avg_credibility', 'average_weighted_credibility'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'elephant_analysis': self.elephant_analysis_data,
            'weighted_credibility_scores': self.weighted_credibility_scores,
            'average_weighted_credibility': self.average_weighted_credibility,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPAElephantModule {self.id}: credibility={self.average_weighted_credibility:.4f}>'


class EFOPAValidityMetrics(db.Model):
    """
    Stores comprehensive validity metrics for response quality.
    """
    __tablename__ = 'efopa_validity_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    validity_metrics_data = db.Column(JSONType, nullable=False)
    validity_scores_data = db.Column(JSONType, nullable=False)
    overall_validity_score = db.Column(db.Float, nullable=False)
    quality_level = db.Column(db.String(20), nullable=False)  # high, moderate, low, very_low
    
    admits_mistakes = db.Column(db.Boolean, nullable=False)
    genuinely_humble = db.Column(db.Boolean, nullable=False)
    consistent_across_contexts = db.Column(db.Boolean, nullable=False)
    understands_motivations = db.Column(db.Boolean, nullable=False)
    remembers_selfishness = db.Column(db.Boolean, nullable=False)
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_validity_assessment_id', 'assessment_id'),
        Index('idx_efopa_quality_level', 'quality_level'),
        Index('idx_efopa_overall_validity', 'overall_validity_score'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'validity_metrics': self.validity_metrics_data,
            'validity_scores': self.validity_scores_data,
            'overall_validity_score': self.overall_validity_score,
            'quality_level': self.quality_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPAValidityMetrics {self.id}: quality={self.quality_level}, validity={self.overall_validity_score:.4f}>'


class EFOPAAuthenticityMetrics(db.Model):
    """
    Stores authenticity and coherence metrics.
    """
    __tablename__ = 'efopa_authenticity_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    coherence_by_domain = db.Column(JSONType, nullable=False)
    overall_coherence = db.Column(db.Float, nullable=False)
    authenticity_index = db.Column(db.Float, nullable=False)
    authenticity_level = db.Column(db.String(20), nullable=False)  # high, moderate, low
    corrected_domain_scores = db.Column(JSONType, nullable=False)
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_authenticity_assessment_id', 'assessment_id'),
        Index('idx_efopa_authenticity_index', 'authenticity_index'),
        Index('idx_efopa_authenticity_level', 'authenticity_level'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'coherence_by_domain': self.coherence_by_domain,
            'overall_coherence': self.overall_coherence,
            'authenticity_index': self.authenticity_index,
            'authenticity_level': self.authenticity_level,
            'corrected_domain_scores': self.corrected_domain_scores,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPAAuthenticityMetrics {self.id}: authenticity={self.authenticity_index:.4f}, level={self.authenticity_level}>'


class EFOPAAssessmentMetadata(db.Model):
    """
    Stores aggregated EFOPA assessment metadata, quality indicators, and recommendations.
    """
    __tablename__ = 'efopa_assessment_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id', ondelete='CASCADE'), 
                              nullable=False, unique=True)
    
    # Quality Assessment
    assessment_quality = db.Column(JSONType, nullable=False)
    
    # Risk Flags
    risk_flags = db.Column(JSONType, nullable=False)
    risk_flag_count = db.Column(db.Integer, nullable=False, default=0)
    has_risk = db.Column(db.Boolean, nullable=False, default=False)
    
    # Recommendations
    recommendations = db.Column(JSONType, nullable=False)
    
    # Overall Assessment Status
    overall_quality_score = db.Column(db.Float, nullable=False)
    assessment_status = db.Column(db.String(50), nullable=False)  # reliable, acceptable, flagged, failed
    
    created_at = db.Column(db.DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_efopa_metadata_assessment_id', 'assessment_id'),
        Index('idx_efopa_assessment_status', 'assessment_status'),
        Index('idx_efopa_has_risk', 'has_risk'),
        Index('idx_efopa_quality_score', 'overall_quality_score'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'assessment_quality': self.assessment_quality,
            'risk_flags': self.risk_flags,
            'risk_flag_count': self.risk_flag_count,
            'has_risk': self.has_risk,
            'recommendations': self.recommendations,
            'overall_quality_score': self.overall_quality_score,
            'assessment_status': self.assessment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<EFOPAAssessmentMetadata {self.id}: status={self.assessment_status}, quality={self.overall_quality_score:.4f}>'
