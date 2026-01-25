# ============================================================================
# EFOPA API Routes - Enhanced Assessment Endpoints
# ============================================================================
# REST API endpoints for EFOPA enhancement results and analysis
# ============================================================================

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc
import logging
from datetime import datetime, timezone
import traceback

from models import db, Assessment
from models_efopa_extension import (
    EFOPALambdaAnalysis,
    EFOPADomainCosts,
    EFOPAElephantModule,
    EFOPAValidityMetrics,
    EFOPAAuthenticityMetrics,
    EFOPAAssessmentMetadata,
)
from scoring_integration import create_enhanced_scoring_integration

efopa_bp = Blueprint('efopa', __name__, url_prefix='/api/efopa')
logger = logging.getLogger(__name__)

enhanced_scoring_integration = None

def set_enhanced_scoring_integration(integration):
    """
    Set the enhanced scoring integration instance.
    Called from app.py after initialization.
    """
    global enhanced_scoring_integration
    enhanced_scoring_integration = integration
    logger.info("[EFOPA_API] Enhanced scoring integration configured")


# ============================================================================
# LAMBDA ANALYSIS ENDPOINTS
# ============================================================================

@efopa_bp.route('/lambda-analysis/<int:assessment_id>', methods=['GET'])
def get_lambda_analysis(assessment_id):
    """
    GET /api/efopa/lambda-analysis/<assessment_id>
    Retrieve Lambda (deception susceptibility) analysis for an assessment.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        lambda_analysis = EFOPALambdaAnalysis.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not lambda_analysis:
            return jsonify({
                'status': 'error',
                'message': 'Lambda analysis not found for this assessment',
                'code': 'LAMBDA_ANALYSIS_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': lambda_analysis.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving lambda analysis: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


# ============================================================================
# DOMAIN COSTS ENDPOINTS
# ============================================================================

@efopa_bp.route('/domain-costs/<int:assessment_id>', methods=['GET'])
def get_domain_costs(assessment_id):
    """
    GET /api/efopa/domain-costs/<assessment_id>
    Retrieve domain honesty costs and fitness impact analysis.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        domain_costs = EFOPADomainCosts.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not domain_costs:
            return jsonify({
                'status': 'error',
                'message': 'Domain costs analysis not found',
                'code': 'DOMAIN_COSTS_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': domain_costs.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving domain costs: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# ELEPHANT MODULE ENDPOINTS
# ============================================================================

@efopa_bp.route('/elephant-module/<int:assessment_id>', methods=['GET'])
def get_elephant_module(assessment_id):
    """
    GET /api/efopa/elephant-module/<assessment_id>
    Retrieve implicit cognition and credibility weighting analysis.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        elephant_module = EFOPAElephantModule.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not elephant_module:
            return jsonify({
                'status': 'error',
                'message': 'Elephant module analysis not found',
                'code': 'ELEPHANT_MODULE_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': elephant_module.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving elephant module: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# VALIDITY METRICS ENDPOINTS
# ============================================================================

@efopa_bp.route('/validity-metrics/<int:assessment_id>', methods=['GET'])
def get_validity_metrics(assessment_id):
    """
    GET /api/efopa/validity-metrics/<assessment_id>
    Retrieve response validity and quality metrics.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        validity_metrics = EFOPAValidityMetrics.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not validity_metrics:
            return jsonify({
                'status': 'error',
                'message': 'Validity metrics not found',
                'code': 'VALIDITY_METRICS_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': validity_metrics.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving validity metrics: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# AUTHENTICITY METRICS ENDPOINTS
# ============================================================================

@efopa_bp.route('/authenticity-metrics/<int:assessment_id>', methods=['GET'])
def get_authenticity_metrics(assessment_id):
    """
    GET /api/efopa/authenticity-metrics/<assessment_id>
    Retrieve authenticity and coherence analysis.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        authenticity_metrics = EFOPAAuthenticityMetrics.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not authenticity_metrics:
            return jsonify({
                'status': 'error',
                'message': 'Authenticity metrics not found',
                'code': 'AUTHENTICITY_METRICS_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': authenticity_metrics.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving authenticity metrics: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# ASSESSMENT METADATA ENDPOINTS
# ============================================================================

@efopa_bp.route('/assessment-metadata/<int:assessment_id>', methods=['GET'])
def get_assessment_metadata(assessment_id):
    """
    GET /api/efopa/assessment-metadata/<assessment_id>
    Retrieve aggregated EFOPA metadata, quality indicators, and recommendations.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        metadata = EFOPAAssessmentMetadata.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        if not metadata:
            return jsonify({
                'status': 'error',
                'message': 'Assessment metadata not found',
                'code': 'METADATA_NOT_FOUND'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': metadata.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving assessment metadata: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# COMPREHENSIVE RESULTS ENDPOINTS
# ============================================================================

@efopa_bp.route('/complete-analysis/<int:assessment_id>', methods=['GET'])
def get_complete_efopa_analysis(assessment_id):
    """
    GET /api/efopa/complete-analysis/<assessment_id>
    Retrieve complete EFOPA analysis with all components.
    """
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({
                'status': 'error',
                'message': 'Assessment not found',
                'code': 'ASSESSMENT_NOT_FOUND'
            }), 404
        
        # Retrieve all EFOPA components
        lambda_analysis = EFOPALambdaAnalysis.query.filter_by(
            assessment_id=assessment_id
        ).first()
        domain_costs = EFOPADomainCosts.query.filter_by(
            assessment_id=assessment_id
        ).first()
        elephant_module = EFOPAElephantModule.query.filter_by(
            assessment_id=assessment_id
        ).first()
        validity_metrics = EFOPAValidityMetrics.query.filter_by(
            assessment_id=assessment_id
        ).first()
        authenticity_metrics = EFOPAAuthenticityMetrics.query.filter_by(
            assessment_id=assessment_id
        ).first()
        metadata = EFOPAAssessmentMetadata.query.filter_by(
            assessment_id=assessment_id
        ).first()
        
        complete_analysis = {
            'assessment_id': assessment_id,
            'lambda_analysis': lambda_analysis.to_dict() if lambda_analysis else None,
            'domain_costs': domain_costs.to_dict() if domain_costs else None,
            'elephant_module': elephant_module.to_dict() if elephant_module else None,
            'validity_metrics': validity_metrics.to_dict() if validity_metrics else None,
            'authenticity_metrics': authenticity_metrics.to_dict() if authenticity_metrics else None,
            'assessment_metadata': metadata.to_dict() if metadata else None,
        }
        
        return jsonify({
            'status': 'success',
            'data': complete_analysis
        }), 200
    
    except Exception as e:
        logger.error(f'[EFOPA_API] Error retrieving complete analysis: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@efopa_bp.route('/health', methods=['GET'])
def efopa_health_check():
    """
    GET /api/efopa/health
    Health check for EFOPA enhancement services.
    """
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'efopa-enhancement-api',
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'integration_status': 'ready' if enhanced_scoring_integration else 'not_initialized',
        }), 200
    except Exception as e:
        logger.error(f'[EFOPA_API] Health check error: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
