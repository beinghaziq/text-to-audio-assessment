import boto3
from datetime import datetime
from django.conf import settings

class AwsPolly:
    VOICE_ID = "Joey"
    LANG_CODE = "en-US"

    def __init__(self):
        self.polly_client = boto3.client(
            'polly',
            aws_access_key_id=settings.AWS_ACCESSKEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
        
    def generate_speech(self, text, response_text):

        combined_text = f"{text} {response_text}"
        return self.polly_client.synthesize_speech(
            Text=combined_text,
            OutputFormat=settings.AWS_FILE_TYPE,
            VoiceId=self.VOICE_ID,
            LanguageCode=self.LANG_CODE
        )
