# EFOPA Enhancement - Technical Specifications

**Version:** 1.0.0  
**Release Date:** January 25, 2026  
**Architecture:** Microservice Integration Layer  
**Status:** Production Release

---

## 🏑 1. Architecture Overview

### System Components

```
┌────────────────────────────────────────────┐
│                   NeuroPersona EFOPA Integration                  │
└──────┬───────────────────────────────────┘
             │
    ┌────────────────────────────────────────┌
    │ Layer 1: API Gateway (api_routes_efopa.py)              │
    │ ├─ /api/efopa/lambda-analysis/<id>                  │
    │ ├─ /api/efopa/domain-costs/<id>                      │
    │ ├─ /api/efopa/elephant-module/<id>                  │
    │ ├─ /api/efopa/validity-metrics/<id>                 │
    │ ├─ /api/efopa/authenticity-metrics/<id>             │
    │ ├─ /api/efopa/assessment-metadata/<id>              │
    │ ├─ /api/efopa/complete-analysis/<id>                │
    │ └─ /api/efopa/health                                 │
    └──────┬──────────────────────────────────┘
             │
    ┌────────────────────────────────────────┌
    │ Layer 2: Integration Layer (scoring_integration.py)   │
    │ ├─ EnhancedScoringIntegration                       │
    │ └─ EFOPA Enhancement Pipeline                        │
    └──────┬──────────────────────────────────┘
             │
    ┌────────────────────────────────────────┌
    │ Layer 3: Data Persistence (efopa_data_persistence.py) │
    │ ├─ Database Operations                               │
    │ ├─ Transaction Management                           │
    │ └─ Error Handling & Rollback                        │
    └──────┬──────────────────────────────────┘
             │
    ┌────────────────────────────────────────┌
    │ Layer 4: Database (models_efopa_extension.py)         │
    │ ├─ EFOPALambdaAnalysis                               │
    │ ├─ EFOPADomainCosts                                 │
    │ ├─ EFOPAElephantModule                              │
    │ ├─ EFOPAValidityMetrics                             │
    │ ├─ EFOPAAuthenticityMetrics                        │
    │ └─ EFOPAAssessmentMetadata                          │
    └──────┬──────────────────────────────────┘
             │
    ┌────────────────────────────────────────┌
    │ Layer 5: Configuration (efopa_config.py)              │
    │ ├─ Domain Configuration                             │
    │ ├─ Deception Thresholds                             │
    │ ├─ Feature Flags                                     │
    │ └─ Scale Conversions                                │
    └────────────────────────────────────────┘
```

---

## 💯 2. Module Specifications

### 2.1 scoring_integration.py

**Purpose:** Integration layer coordinating existing ScoringEngine with EFOPA enhancements

**Key Classes:**

#### EnhancedScoringIntegration
```python
class EnhancedScoringIntegration:
    """
    Integration layer between ScoringEngine and EFOPA enhancement modules.
    """
    def __init__(self, scoring_engine: ScoringEngine)
    def process_with_efopa_enhancement(responses: List[int], age: int) -> Dict
    def calculate_comparative_scores(responses: List[int], age: int) -> Dict
    def get_domain_insights(integrated_result: Dict, domain: str) -> Dict
```

**Dependencies:**
- `efopa_engine` - EFOPA calculation engine
- `ScoringEngine` - Existing scoring engine instance

**Processing Pipeline:**
1. Base scoring using ScoringEngine
2. EFOPA enhancement application
3. Result integration
4. Metadata calculation

---

### 2.2 models_efopa_extension.py

**Purpose:** SQLAlchemy ORM models for EFOPA result persistence

**Database Models:**

| Model | Columns | Relationships | Indices |
|-------|---------|---------------|----------|
| EFOPALambdaAnalysis | 9 | assessment(1:1) | 3 |
| EFOPADomainCosts | 4 | assessment(1:1) | 2 |
| EFOPAElephantModule | 4 | assessment(1:1) | 2 |
| EFOPAValidityMetrics | 11 | assessment(1:1) | 3 |
| EFOPAAuthenticityMetrics | 6 | assessment(1:1) | 3 |
| EFOPAAssessmentMetadata | 8 | assessment(1:1) | 4 |

**Data Types:**
- Primary Keys: Integer auto-increment
- Foreign Keys: assessment_id (references assessments.id)
- JSON Fields: SQLAlchemy JSONType for complex data
- Timestamps: Automatic UTC timestamps

---

### 2.3 api_routes_efopa.py

**Purpose:** REST API endpoints for EFOPA data access

**Blueprint:** `efopa_bp` with prefix `/api/efopa`

**Endpoints:**

| Route | Method | Query Params | Response | Status Codes |
|-------|--------|--------------|----------|---------------|
| `/lambda-analysis/<id>` | GET | - | 200 (success), 404 (not found), 500 (error) | ✓ |
| `/domain-costs/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/elephant-module/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/validity-metrics/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/authenticity-metrics/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/assessment-metadata/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/complete-analysis/<id>` | GET | - | 200, 404, 500 | ✓ |
| `/health` | GET | - | 200, 500 | ✓ |

**Response Format:**
```json
{
  "status": "success|error",
  "data": { /* component-specific data */ },
  "message": "Optional message",
  "code": "Error code if applicable"
}
```

---

### 2.4 efopa_data_persistence.py

**Purpose:** Data persistence operations for EFOPA results

**Key Class:** EFOPADataPersistence

**Methods:**

| Method | Input | Output | Exceptions |
|--------|-------|--------|------------|
| save_complete_efopa_results | assessment_id, result | Dict with record IDs | Logs and raises on error |
| save_lambda_analysis | assessment_id, data | EFOPALambdaAnalysis | Database errors |
| save_domain_costs | assessment_id, data | EFOPADomainCosts | Database errors |
| save_elephant_module | assessment_id, data | EFOPAElephantModule | Database errors |
| save_validity_metrics | assessment_id, data | EFOPAValidityMetrics | Database errors |
| save_authenticity_metrics | assessment_id, data | EFOPAAuthenticityMetrics | Database errors |
| save_assessment_metadata | assessment_id, data | EFOPAAssessmentMetadata | Database errors |
| get_efopa_results | assessment_id | Dict with all results | Query errors |

**Transaction Handling:**
- Atomic saves with rollback on error
- Cascade delete on assessment deletion
- Unique constraint on assessment_id per table

---

### 2.5 efopa_config.py

**Purpose:** Centralized configuration and constants

**Configuration Objects:**

```python
EFOPA_QUESTIONNAIRE_CONFIG
EFOPA_DOMAIN_CONFIG  # 6 domains with weights
EFOPA_VALIDITY_ITEMS  # 5 validity checks
EFOPA_LAMBDA_CONFIG  # Deception calculation parameters
EFOPA_DOMAIN_COST_CONFIG  # Honesty costs per domain
EFOPA_ELEPHANT_CONFIG  # Implicit bias factors
EFOPA_VALIDITY_CONFIG  # Quality thresholds
EFOPA_AUTHENTICITY_CONFIG  # Authenticity thresholds
EFOPA_VAE_CONFIG  # VAE input settings
EFOPA_FEATURE_FLAGS  # Feature toggle switches
```

**Validation:**
```python
validate_efopa_configuration() -> bool
```

---

## 📚 3. Data Models

### 3.1 Lambda Analysis Data Structure

```python
{
    'lambda_score': float,  # 0.0-1.0
    'deception_level': str,  # 'Low', 'Moderate', 'High'
    'contradiction_count': int,
    'contradictions_detected': list,
    'extreme_consistency_score': float,
    'response_variability_penalty': float,
}
```

### 3.2 Domain Costs Data Structure

```python
{
    'domain_costs': {
        'R': {...},  # Per-domain cost breakdown
        'S': {...},
        'C': {...},
        'A': {...},
        'O': {...},
        'E': {...},
    },
    'average_honesty_cost': float,
    'total_fitness_impact': float,
}
```

### 3.3 Elephant Module Data Structure

```python
{
    'elephant_analysis': {
        'R': {...},  # Domain-specific analysis
        'S': {...},
        # ...
    },
    'weighted_credibility_scores': {
        'R': float,
        'S': float,
        # ...
    },
    'average_weighted_credibility': float,
}
```

### 3.4 Validity Metrics Data Structure

```python
{
    'validity_metrics': {...},
    'validity_scores': {
        'V31': int,  # 0-10 scale
        'V32': int,
        'V33': int,
        'V34': int,
        'V35': int,
    },
    'overall_validity_score': float,  # 0-1
    'quality_level': str,  # 'high', 'moderate', 'low', 'very_low'
}
```

### 3.5 Assessment Metadata Data Structure

```python
{
    'assessment_quality': {
        'lambda_score': float,
        'deception_level': str,
        'validity_quality': str,
        'authenticity_score': float,
        'average_credibility': float,
    },
    'risk_flags': list,  # ['flag1', 'flag2', ...]
    'recommendations': list,  # ['recommendation1', ...]
    'assessment_status': str,  # 'reliable', 'acceptable', 'flagged', 'failed'
}
```

---

## 🔄 4. Processing Pipeline

### 4.1 Assessment Processing Flow

```
Input: responses[] (0-10 scale), age: int
        │
        ▼
    ScoringEngine.process_assessment()
        │
        ▶ raw_domain_scores
        ▶ corrected_domain_scores
        ▶ deception_susceptibility
        ▶ domain_biases
        │
        ▼
    EnhancedScoringIntegration.process_with_efopa_enhancement()
        │
        ├─▶ Lambda Analysis
        ├─▶ Domain Costs Calculation
        ├─▶ Elephant Module Analysis
        ├─▶ Validity Metrics Computation
        ├─▶ Authenticity Metrics Calculation
        └─▶ Metadata Generation
        │
        ▼
    EFOPADataPersistence.save_complete_efopa_results()
        │
        ├─▶ Save to efopa_lambda_analysis
        ├─▶ Save to efopa_domain_costs
        ├─▶ Save to efopa_elephant_module
        ├─▶ Save to efopa_validity_metrics
        ├─▶ Save to efopa_authenticity_metrics
        └─▶ Save to efopa_assessment_metadata
        │
        ▼
Database persisted, API ready
```

### 4.2 Scale Conversion

**Input Scale:** 0-10 (user-facing)
**Internal Scale:** 1-5 (VAE processing)
**Conversion Formula:** `vae_score = 1 + (user_score / 10) * 4`

**Examples:**
- 0 (Strongly Disagree) → 1.0
- 5 (Neutral) → 3.0
- 10 (Strongly Agree) → 5.0

---

## 🔐 5. Error Handling

### 5.1 Error Codes

| Code | HTTP | Meaning | Recovery |
|------|------|---------|----------|
| ASSESSMENT_NOT_FOUND | 404 | Assessment ID not in database | Check assessment_id |
| LAMBDA_ANALYSIS_NOT_FOUND | 404 | EFOPA results not computed | Re-run assessment |
| INTERNAL_ERROR | 500 | Unexpected server error | Retry, check logs |
| DATABASE_ERROR | 500 | Database operation failed | Check DB connection |

### 5.2 Graceful Degradation

- If EFOPA fails, base scores returned
- If persistence fails, results still available in memory
- If API endpoint fails, health check still works
- If one EFOPA component fails, others continue

---

## 📊 6. Performance Specifications

### 6.1 Time Complexity

| Operation | Time | Notes |
|-----------|------|-------|
| Base scoring | O(1) | Direct calculation |
| Lambda analysis | O(n) | n = number of items |
| Domain costs | O(k) | k = number of domains (6) |
| Elephant module | O(k) | Per-domain weighting |
| Validity metrics | O(5) | 5 validity items fixed |
| Database save | O(k) | k = 6 tables |
| Database retrieve | O(k) | k = 6 tables |

**Total per assessment:** O(n) ~ 50-100ms

### 6.2 Space Complexity

| Component | Storage | Notes |
|-----------|---------|-------|
| Lambda data | 500 bytes | Relatively small |
| Domain costs | 800 bytes | JSON per domain |
| Elephant module | 600 bytes | Credibility scores |
| Validity metrics | 400 bytes | 5 items + metadata |
| Authenticity | 700 bytes | Coherence data |
| Metadata | 1.2 KB | Recommendations + flags |
| **Total** | ~4.2 KB | Per assessment |

---

## 📽 7. Database Specifications

### 7.1 Table Constraints

```sql
-- Foreign Key Constraints
ALTER TABLE efopa_lambda_analysis 
ADD CONSTRAINT fk_efopa_lambda_assessment 
FOREIGN KEY (assessment_id) 
REFERENCES assessments(id) ON DELETE CASCADE;

-- Unique Constraints
ALTER TABLE efopa_lambda_analysis 
ADD CONSTRAINT uk_efopa_lambda_assessment_id 
UNIQUE (assessment_id);

-- Indices for Performance
CREATE INDEX idx_efopa_lambda_assessment_id ON efopa_lambda_analysis(assessment_id);
CREATE INDEX idx_efopa_lambda_score ON efopa_lambda_analysis(lambda_score);
CREATE INDEX idx_efopa_deception_level ON efopa_lambda_analysis(deception_level);
```

### 7.2 Query Patterns

**Most Common Queries:**

```sql
-- Get Lambda analysis (indexed on assessment_id)
SELECT * FROM efopa_lambda_analysis WHERE assessment_id = ?

-- Filter by deception level (indexed)
SELECT * FROM efopa_lambda_analysis WHERE deception_level = 'High'

-- Get all EFOPA data for assessment
SELECT * FROM efopa_lambda_analysis WHERE assessment_id = ?
SELECT * FROM efopa_domain_costs WHERE assessment_id = ?
-- ... (6 queries, all indexed)
```

---

## 🔍 8. Logging Specifications

### 8.1 Log Levels

```
[EFOPA_API] - API endpoint operations
[EFOPA_PERSISTENCE] - Database operations
[EFOPA_INTEGRATION] - Integration processing
[EFOPA_CONFIG] - Configuration validation
```

### 8.2 Log Format

```
[COMPONENT] [LEVEL] [TIMESTAMP] Message details

Example:
[EFOPA_PERSISTENCE] INFO [2026-01-25 08:10:05] Saved Lambda analysis for assessment 123
[EFOPA_PERSISTENCE] ERROR [2026-01-25 08:10:06] Error saving domain costs: Database connection timeout
```

---

## 🔓 9. Security Specifications

### 9.1 Input Validation

- Assessment ID: Integer validation
- Response scores: Range validation (0-10)
- Age: Positive integer validation
- JSON payloads: Type checking

### 9.2 SQL Injection Prevention

- SQLAlchemy ORM (parameterized queries)
- No raw SQL queries
- Prepared statements throughout

### 9.3 Data Privacy

- HTTPS only (production)
- No sensitive data in error messages (debug mode control)
- Database encryption at rest (Render managed)

---

## 🔌 10. Compatibility Matrix

### 10.1 Python Version
- **Minimum:** Python 3.8
- **Tested:** Python 3.9, 3.10, 3.11
- **Recommended:** Python 3.11+

### 10.2 Framework Versions
- **Flask:** 2.0+
- **SQLAlchemy:** 1.4+
- **NumPy:** 1.20+

### 10.3 Database Support
- **PostgreSQL:** 12+ (recommended for production)
- **SQLite:** 3.30+ (for development)
- **MySQL:** 8.0+

---

## 📦 11. Deployment Specifications

### 11.1 Environment Variables

```bash
EFOPA_LOG_LEVEL=INFO  # DEBUG for verbose logging
EFOPA_DEBUG=False      # True for debug error messages
```

### 11.2 Requirements

**New Dependencies:** None (uses existing Flask, SQLAlchemy)

**System Requirements:**
- Disk: 100 MB minimum (for code + database growth)
- Memory: 512 MB minimum (recommended 1 GB+)
- CPU: Any modern processor

---

## 🌐 12. API Response Examples

### Lambda Analysis Response

```json
{
  "status": "success",
  "data": {
    "assessment_id": 123,
    "lambda_score": 0.48,
    "deception_level": "Moderate",
    "contradiction_count": 2,
    "contradictions_detected": [
      {"domain": "A", "reason": "High A but low V31"},
      {"domain": "C", "reason": "High C but low V33"}
    ]
  }
}
```

### Complete Analysis Response

```json
{
  "status": "success",
  "data": {
    "assessment_id": 123,
    "lambda_analysis": {...},
    "domain_costs": {...},
    "elephant_module": {...},
    "validity_metrics": {...},
    "authenticity_metrics": {...},
    "assessment_metadata": {...}
  }
}
```

---

## 🚘 13. Future Extensions

### Potential Enhancements
1. Machine learning model for adaptive thresholds
2. Longitudinal analysis (comparing assessments over time)
3. Cohort comparison (versus population norms)
4. Advanced visualization dashboard
5. Predictive indicators for relationship compatibility

---

**Document Version:** 1.0.0  
**Last Updated:** January 25, 2026  
**Status:** Complete
