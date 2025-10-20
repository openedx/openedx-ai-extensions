"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor


class BaseOrchestrator:
    def __init__(self, workflow):
        self.workflow = workflow
        self.config = workflow.config
    
    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")


class MockResponse(BaseOrchestrator):
    def run(self, input_data):
        return {
            'response': f'Mock response for {self.workflow.action}',
            'status': 'completed'
        }


class DirectLLMResponse(BaseOrchestrator):
    def run(self, input_data):
        # Prepare context
        context = {
            'course_id': self.workflow.course_id,
            'extra_context': self.workflow.extra_context
        }
        
        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(context)
        
        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}
        
        # 2. Process with LLM processor
        llm_processor = LLMProcessor(self.config.processor_config)
        llm_result = llm_processor.process(str(content_result))
        
        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}
        
        # 3. Return result
        return {
            'response': llm_result.get('response', 'No response available'),
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }