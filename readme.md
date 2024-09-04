# Task

## Refactor this code
``` Python
import logging
from datetime import datetime

import boto3
import requests
from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import views
from rest_framework.decorators import api_view

from core.serializers import ResponceSerializer, RequestSerializer, BadRequestSerializer

logger = logging.getLogger(__name__)

USER_RESPONSE = openapi.Response('text successfully generated', ResponceSerializer)
BAD_RESPONSE = openapi.Response('out of quota for generaton', BadRequestSerializer)


@swagger_auto_schema(method='post', request_body=RequestSerializer, responses={200: USER_RESPONSE, 400: BAD_RESPONSE})
@api_view(["POST"])
def text_to_voice(request):
    text = request.data.get("text")
    payload = {"length": 500}
    if text:
        payload["prompt"] = {"text": text}
    headers = {"Authorization": f"Bearer {settings.INFERKIT_API_KEY}"}
    response = requests.post(settings.INFERKIT_URL, headers=headers, json=payload)
    if response.status_code == 400 and "Out of generation credits" in response.text:
        return views.Response({"error_message": "Out of generation credits"}, status=400)
    if not response.ok:
        logger.error(f"Status code {response.status_code} from inferkit with {response.text}.")
        raise views.exceptions.ParseError("Text generation API failed. Please, try again.")
    response_text = response.json().get("data", {}).get("text") if response.ok else ""
    aws_kwargs = {
        "aws_access_key_id": settings.AWS_ACCESSKEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY
    }
    polly_client = boto3.Session(region_name=settings.AWS_REGION_NAME, **aws_kwargs).client('polly')
    generated_audio = polly_client.synthesize_speech(Text=f"{text} {response_text}",
                                                     OutputFormat=settings.AWS_FILE_TYPE,
                                                     VoiceId="Joey",
                                                     LanguageCode="en-US")
    s3_connection = boto3.resource("s3", **aws_kwargs)
    file_name = f"{datetime.now().isoformat()}.{settings.AWS_FILE_TYPE}"
    s3_connection.Bucket(settings.AWS_BUCKET_NAME).put_object(
        Key=file_name,
        Body=generated_audio.get('AudioStream').read(),
        ContentType=settings.AWS_FILE_TYPE
    )
    file_url = s3_connection.meta.client.generate_presigned_url(ClientMethod="get_object", Params={
        "Bucket": settings.AWS_BUCKET_NAME,
        "Key": file_name
    })
    return views.Response({"message": response_text, "file_url": file_url})
