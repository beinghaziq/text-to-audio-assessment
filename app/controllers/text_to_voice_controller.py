import logging
from datetime import datetime
from app.services.aws_s3 import AwsS3

import boto3
import requests
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import views
from rest_framework.decorators import api_view

from core.serializers import ResponceSerializer, RequestSerializer, BadRequestSerializer

logger = logging.getLogger(__name__)

USER_RESPONSE = openapi.Response('Text successfully generated', ResponceSerializer)
BAD_RESPONSE = openapi.Response('Out of quota for generation', BadRequestSerializer)

def get_inferkit_response(text):
    payload = {"length": 500}
    if text:
        payload["prompt"] = {"text": text}
    headers = {"Authorization": f"Bearer {settings.INFERKIT_API_KEY}"}

    response = requests.post(settings.INFERKIT_URL, headers=headers, json=payload)
    
    if response.status_code == 400 and "Out of generation credits" in response.text:
        return None, "Out of generation credits"
    
    if not response.ok:
        logger.error(f"Status code {response.status_code} from Inferkit with {response.text}.")
        raise views.exceptions.ParseError("Text generation API failed. Please, try again.")
    
    return response.json().get("data", {}).get("text", ""), None

def generate_speech(text, response_text):
    aws_kwargs = {
        "aws_access_key_id": settings.AWS_ACCESSKEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY
    }
    
    polly_client = boto3.Session(region_name=settings.AWS_REGION_NAME, **aws_kwargs).client('polly')
    
    combined_text = f"{text} {response_text}"
    return polly_client.synthesize_speech(
        Text=combined_text,
        OutputFormat=settings.AWS_FILE_TYPE,
        VoiceId="Joey",
        LanguageCode="en-US"
    )

@swagger_auto_schema(method='post', request_body=RequestSerializer, responses={200: USER_RESPONSE, 400: BAD_RESPONSE})
@api_view(["POST"])
def text_to_voice(request):
    text = request.data.get("text")
    
    if not text:
        return views.Response({"error_message": "Text input is required"}, status=400)
    
    response_text, error_message = get_inferkit_response(text)
    
    if error_message:
        return views.Response({"error_message": error_message}, status=400)
    
    generated_audio = generate_speech(text, response_text)

    s3_uploader = AwsS3()
    file_name, file_url = s3_uploader.upload_file(generated_audio.get('AudioStream'))
    
    return views.Response({"message": response_text, "file_url": file_url, 'file_name': file_name})
