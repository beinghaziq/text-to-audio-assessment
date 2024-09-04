import boto3
from datetime import datetime
from django.conf import settings

class AwsS3:
    def __init__(self):
        self.aws_kwargs = {
            "aws_access_key_id": settings.AWS_ACCESSKEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY
        }
        self.s3_resource = boto3.resource("s3", **self.aws_kwargs)
        self.bucket_name = settings.AWS_BUCKET_NAME
        self.file_type = settings.AWS_FILE_TYPE

    def upload_file(self, audio_stream):
        file_name = self._generate_file_name()
        self.s3_resource.Bucket(self.bucket_name).put_object(
            Key=file_name,
            Body=audio_stream.read(),
            ContentType=self.file_type
        )
        return file_name, self._generate_presigned_url(file_name)

    def _generate_file_name(self):
        return f"{datetime.now().isoformat()}.{self.file_type}"

    def _generate_presigned_url(self, file_name):
        return self.s3_resource.meta.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": file_name}
        )
