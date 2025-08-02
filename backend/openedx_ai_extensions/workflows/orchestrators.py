"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""

from openedx_ai_extensions.processors import OpenEdXProcessor, LLMProcessor


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
    
        unit_id = self.workflow.unit_id
        if not unit_id:
            return {'error': 'Unit ID is required', 'status': 'error'}
        
        # 1. Get unit content
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_text = openedx_processor.get_unit_content(unit_id)
        
        if 'error' in content_text:
            return {'error': content_text['error'], 'status': 'error'}
        
        # 2. Summarize with LLM
        llm_processor = LLMProcessor(self.config.processor_config)
        llm_result = llm_processor.summarize_content(str(content_text))
        
        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'error'}
        
        # 3. Return result
        return {
            'response': llm_result.get('summary', 'No summary available'),
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }
