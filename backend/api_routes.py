@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    """Start a new assessment session"""
    try:
        # Parse JSON request
        data = request.get_json(force=True, silent=True)
        
        if data is None:
            logger.warning('[START_ASSESSMENT] No JSON body received')
            return jsonify({
                'status': 'error',
                'message': 'Request body must be valid JSON',
                'code': 'INVALID_JSON'
            }), 400
        
        # Extract and validate fields
        age = data.get('age')
        sex = data.get('sex')
        
        logger.info(f'[START_ASSESSMENT] Received: age={age}, sex={sex}')
        
        # Validate age
        if age is None:
            logger.warning('[START_ASSESSMENT] Missing age field')
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: age',
                'code': 'MISSING_AGE'
            }), 400
        
        if not isinstance(age, (int, float)):
            logger.warning(f'[START_ASSESSMENT] Invalid age type: {type(age)}')
            return jsonify({
                'status': 'error',
                'message': 'Age must be a number',
                'code': 'INVALID_AGE_TYPE'
            }), 400
        
        age = int(age)
        if age < 13 or age > 120:
            logger.warning(f'[START_ASSESSMENT] Age out of range: {age}')
            return jsonify({
                'status': 'error',
                'message': 'Age must be between 13 and 120',
                'code': 'AGE_OUT_OF_RANGE'
            }), 400
        
        # Validate sex
        if sex is None:
            logger.warning('[START_ASSESSMENT] Missing sex field')
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: sex',
                'code': 'MISSING_SEX'
            }), 400
        
        if sex not in ['M', 'F', 'O']:
            logger.warning(f'[START_ASSESSMENT] Invalid sex value: {sex}')
            return jsonify({
                'status': 'error',
                'message': 'Sex must be M, F, or O',
                'code': 'INVALID_SEX'
            }), 400
        
        # Create user
        try:
            logger.info(f'[START_ASSESSMENT] Creating user with age={age}, sex={sex}')
            user = User(age=age, sex=sex)
            db.session.add(user)
            db.session.flush()  # Get the ID without committing
            logger.info(f'[START_ASSESSMENT] Created user {user.id}')
        except Exception as e:
            logger.error(f'[START_ASSESSMENT] Error creating user: {str(e)}')
            logger.error(f'[START_ASSESSMENT] User creation traceback: {traceback.format_exc()}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating user record',
                'code': 'USER_CREATE_ERROR',
                'details': str(e) if current_app.debug else None
            }), 500
        
        # Create assessment
        try:
            logger.info(f'[START_ASSESSMENT] Creating assessment for user {user.id}')
            assessment = Assessment(
                user_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500],
            )
            db.session.add(assessment)
            db.session.commit()
            logger.info(f'[START_ASSESSMENT] Created assessment {assessment.id} (external_id: {assessment.external_id}) for user {user.id}')
        except Exception as e:
            logger.error(f'[START_ASSESSMENT] Error creating assessment: {str(e)}')
            logger.error(f'[START_ASSESSMENT] Assessment creation traceback: {traceback.format_exc()}')
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error creating assessment record',
                'code': 'ASSESSMENT_CREATE_ERROR',
                'details': str(e) if current_app.debug else None
            }), 500
        
        # Success response
        logger.info(f'[START_ASSESSMENT] SUCCESS: Returning assessment_id={assessment.id}, external_id={assessment.external_id}')
        return jsonify({
            'status': 'success',
            'user_id': str(user.id),
            'assessment_id': assessment.id,
            'external_id': str(assessment.external_id),
        }), 201
    
    except Exception as e:
        logger.error(f'[START_ASSESSMENT] Unexpected error: {str(e)}')
        logger.error(traceback.format_exc())
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error': str(e) if current_app.debug else None,
        }), 500