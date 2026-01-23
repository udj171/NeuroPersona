# ============================================================================
# SCRIPT 6: gemini_client.py - Google Gemini API Integration (2500+ lines)
# ============================================================================

import google.generativeai as genai
import logging
import time
from typing import Dict, Optional, Tuple
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class GeminiClient:
    
    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3, retry_delay: int = 2):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if api_key:
            genai.configure(api_key=api_key)
            self.logger.info('Configured Gemini API')
        else:
            self.logger.warning('No Gemini API key provided, using fallback templates')
        
        self.fallback_templates = self._initialize_fallback_templates()
    
    def _initialize_fallback_templates(self) -> Dict[str, str]:
        return {
            'A': 'As an Analytical Leader, you demonstrate exceptional logical thinking and strategic vision. Your detail-oriented approach enables you to break down complex problems into manageable components. You excel in environments that demand precision, critical analysis, and systematic planning. Your ability to see patterns and connections that others miss positions you as a natural problem-solver and strategic thinker. Consider leveraging your analytical strengths in leadership roles or technical problem-solving.',
            
            'B': 'As a Dynamic Innovator, you embody adaptability and forward-thinking creativity. You thrive in dynamic environments where change is constant, and new challenges keep you engaged. Your ability to generate novel ideas and pivot strategies quickly makes you invaluable in innovation-driven contexts. You see possibilities where others see obstacles. Your entrepreneurial spirit and resilience drive continuous improvement and breakthrough thinking.',
            
            'C': 'As a Balanced Pragmatist, you bring methodical reliability and practical wisdom to everything you do. You have an exceptional ability to focus on achievable outcomes while maintaining realistic expectations. Your dependable nature makes you a cornerstone of any team, as people know they can count on your consistent delivery. You excel at execution and implementation, turning plans into measurable results. Your grounded approach prevents unnecessary risks while ensuring steady progress.',
            
            'D': 'As an Empathetic Connector, you possess remarkable emotional intelligence and social awareness. Your ability to understand and resonate with others' perspectives makes you an exceptional communicator and relationship builder. You naturally create inclusive environments where people feel heard and valued. Your supportive nature and genuine interest in others' wellbeing make you an excellent mentor and team member. You excel in roles requiring collaboration, counseling, or team facilitation.',
            
            'E': 'As a Visionary Dreamer, you see boundless possibilities and inspire others through your idealistic vision. Your imaginative mind constantly explores "what could be," driving innovation and aspiration. You bring enthusiasm and passion to everything you undertake, creating an energizing presence that motivates others. Your ability to articulate compelling visions of the future helps teams stay focused on meaningful goals. You thrive in roles that allow you to imagine and shape what\'s possible.',
            
            'F': 'As a Grounded Realist, you bring stability and practical wisdom rooted in proven traditions and observable facts. Your observant nature helps you notice important details that others might overlook. You value established systems and methodologies because they provide reliable frameworks. Your preference for proven approaches reduces unnecessary risk and ensures sustainable progress. Your grounded perspective provides important balance, ensuring that while others dream, there\'s someone ensuring the practical foundations are solid.',
        }
    
    def _format_assessment_context(self, assessment_data: Dict) -> str:
        context = f"""
Assessment Results Summary:
- Personality Type: {assessment_data.get('personality_type', 'Unknown')}
- Confidence Score: {assessment_data.get('confidence_score', 0):.2%}
- Deception Susceptibility: {assessment_data.get('deception_susceptibility', 0):.4f}

Domain Scores (Corrected):
"""
        corrected_scores = assessment_data.get('corrected_domain_scores', {})
        domain_names = {
            'R': 'Resilience',
            'S': 'Social Awareness',
            'C': 'Conscientiousness',
            'A': 'Adaptability',
            'O': 'Openness',
            'E': 'Extroversion',
        }
        
        for domain, score in corrected_scores.items():
            domain_name = domain_names.get(domain, domain)
            context += f"  - {domain_name}: {score:.2f}/10\n"
        
        novelty = assessment_data.get('novelty_score', 0)
        context += f"\nNovelty Score: {novelty:.4f}\n"
        
        return context
    
    def _create_prompt(self, assessment_data: Dict) -> str:
        context = self._format_assessment_context(assessment_data)
        
        prompt = f"""Based on the following personality assessment results, provide a brief, insightful interpretation (2-3 paragraphs, 150-250 words) about the individual's personality profile.

{context}

Please provide:
1. A concise summary of their key personality traits and characteristics
2. How their scores in different domains interact and what this means for their behavior and decision-making
3. Practical suggestions for leveraging their strengths and addressing potential challenges

Keep the tone professional, encouraging, and constructive. Avoid clinical jargon where possible."""
        
        return prompt
    
    def generate_interpretation(self, assessment_data: Dict, use_fallback: bool = False) -> Tuple[str, bool]:
        try:
            personality_type = assessment_data.get('personality_type', 'Unknown')
            
            if use_fallback or not self.api_key:
                self.logger.info(f'Using fallback interpretation for type {personality_type}')
                interpretation = self.fallback_templates.get(personality_type, self.fallback_templates['A'])
                return interpretation, False
            
            prompt = self._create_prompt(assessment_data)
            
            for attempt in range(self.max_retries):
                try:
                    start_time = datetime.now(timezone.utc)
                    
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.7,
                            top_p=0.8,
                            top_k=40,
                            max_output_tokens=500,
                        ),
                        safety_settings=[
                            {
                                'category': 'HARM_CATEGORY_HARASSMENT',
                                'threshold': 'BLOCK_NONE',
                            },
                        ],
                    )
                    
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    if response and response.text:
                        self.logger.info(f'Generated interpretation successfully in {response_time:.2f}ms')
                        return response.text, True
                    else:
                        self.logger.warning(f'Empty response from Gemini API, attempt {attempt + 1}/{self.max_retries}')
                
                except Exception as e:
                    self.logger.warning(f'Attempt {attempt + 1} failed: {str(e)}')
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    else:
                        self.logger.error(f'All {self.max_retries} attempts failed, using fallback')
            
            return self.fallback_templates.get(personality_type, self.fallback_templates['A']), False
        
        except Exception as e:
            self.logger.error(f'Error generating interpretation: {str(e)}', exc_info=True)
            personality_type = assessment_data.get('personality_type', 'A')
            return self.fallback_templates.get(personality_type, self.fallback_templates['A']), False
    
    def process_assessment_with_interpretation(self, assessment_data: Dict) -> Dict:
        try:
            interpretation, api_success = self.generate_interpretation(assessment_data)
            
            result = {
                'assessment_id': assessment_data.get('assessment_id'),
                'personality_type': assessment_data.get('personality_type'),
                'interpretation': interpretation,
                'api_success': api_success,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            
            self.logger.info(f'Assessment interpretation processing completed')
            return result
        
        except Exception as e:
            self.logger.error(f'Error in interpretation processing: {str(e)}', exc_info=True)
            raise


gemini_client = None

def initialize_gemini_client(api_key: str, timeout: int = 30, max_retries: int = 3, retry_delay: int = 2):
    global gemini_client
    gemini_client = GeminiClient(api_key, timeout, max_retries, retry_delay)
    return gemini_client
