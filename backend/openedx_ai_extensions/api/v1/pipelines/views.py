"""
AI Pipelines API Views
Simple logging and basic response functionality
"""
import json
import logging
import pprint
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

# Configure logger for this module
logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AIGenericPipelinesView(View):
    """
    AI Assistance Pipeline API endpoint
    Simple logging and hello world response
    """
    
    def post(self, request):
        """Handle POST request for AI assistance"""
        return self._handle_request(request, 'POST')
    
    def get(self, request):
        """Handle GET request for AI assistance"""
        return self._handle_request(request, 'GET')
    
    def _handle_request(self, request, method):
        """Common handler for GET and POST requests"""
        
        # Parse request body if present
        try:
            if request.body:
                body_data = json.loads(request.body.decode('utf-8'))
            else:
                body_data = {}
        except:
            body_data = {"error": "Could not parse request body"}
        
        # Create complete request info for logging
        request_info = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "user": str(request.user),
            "user_id": getattr(request.user, 'id', None),
            "query_params": dict(request.GET),
            "request_body": body_data,
        }
        
        # Single pretty log with all info
        logger.info("🤖 AI ASSISTANCE REQUEST:\n" + pprint.pformat(request_info, indent=2, width=100))
        
        # Generate simple response
        request_id = body_data.get('requestId', 'no-request-id')
        
        response_data = {
            'requestId': request_id,
            'response': f'¡Hola Mundo desde Python! 👋 Request recibido correctamente via {method}.',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
        }
        
        return JsonResponse(response_data, status=200)
