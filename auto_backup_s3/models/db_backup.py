
import boto3
import os
import datetime
import glob
import time
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError
from odoo.exceptions import UserError, AccessDenied
from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)

class DbBackup(models.Model):
    _inherit = 'db.backup'

    s3_write = fields.Boolean('Write to S3',
                              help="If checked, backups will be uploaded to an AWS S3 bucket.")
    s3_bucket_name = fields.Char('S3 Bucket Name', help='The name of the AWS S3 bucket to store backups.')
    s3_access_key = fields.Char('S3 Access Key', help='AWS Access Key for S3 access.')
    s3_secret_key = fields.Char('S3 Secret Key', help='AWS Secret Key for S3 access.')
    s3_region = fields.Char('S3 Region', help='Region of the S3 bucket.')
    s3_folder_name = fields.Char("S3 Folder Name", required=True)

    def upload_to_s3(self, file_path, bucket_name, s3_key, access_key, secret_key, region):
        """
        Upload a file to S3 bucket.
        :param file_path: Path to the file to upload.
        :param bucket_name: S3 bucket name.
        :param s3_key: S3 object key (filename in S3).
        :param access_key: AWS access key.
        :param secret_key: AWS secret key.
        :param region: AWS region.
        :return: None
        """
        try:
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
            # Upload file
            s3_client.upload_file(file_path, bucket_name, s3_key)
            _logger.info('Successfully uploaded %s to S3 bucket %s', file_path, bucket_name)
        except (BotoCoreError, NoCredentialsError) as e:
            _logger.error('Failed to upload backup to S3: %s', str(e))
            raise UserError(_('Failed to upload backup to S3: %s') % str(e))

    def get_s3_client(self, access_key, secret_key, region):
        import boto3
        return boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def list_s3_objects(self, s3_client, bucket_name, folder_prefix):
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{folder_prefix}/")
        return response.get('Contents', [])  # Return list of objects or an empty list

    def action_test_s3_connection(self):
        """
        Test the connection to S3 and display the result as a notification.
        """
        self.ensure_one()  # Ensure the action is performed on a single record
        try:
            # Initialize S3 client with credentials
            s3_client = self.get_s3_client(
                access_key=self.s3_access_key,
                secret_key=self.s3_secret_key,
                region=self.s3_region,
            )

            # Attempt to list objects in the bucket to test connection
            s3_client.list_objects_v2(Bucket=self.s3_bucket_name)

            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            msg_type = "success"
        except Exception as err:
            title = _("Connection Test Failed!")
            message = str(err)
            msg_type = "danger"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": msg_type,
                "sticky": False,
            },
        }

    @api.model
    def schedule_backup(self):
        # Call the original method first to preserve existing functionality
        super(DbBackup, self).schedule_backup()

        conf_ids = self.search([])
        for rec in conf_ids:
            # Skip if S3 write is not enabled
            if not rec.s3_write:
                continue

            folder_path = rec.folder
            s3_folder = rec.s3_folder_name.strip()  # Use the folder name from the field

            try:
                local_files = {os.path.basename(f) for f in os.listdir(folder_path) if
                               os.path.isfile(os.path.join(folder_path, f))}
            except FileNotFoundError:
                _logger.error("Folder not found: %s", folder_path)
                continue
            except Exception as e:
                _logger.error("Error accessing folder %s: %s", folder_path, str(e))
                continue

            # Get the list of files currently in S3
            try:
                s3_client = self.get_s3_client(
                    access_key=rec.s3_access_key,
                    secret_key=rec.s3_secret_key,
                    region=rec.s3_region,
                )
                s3_objects = self.list_s3_objects(s3_client, rec.s3_bucket_name, s3_folder)
            except Exception as e:
                _logger.error("Error accessing S3 bucket %s: %s", rec.s3_bucket_name, str(e))
                continue

            s3_files = {obj['Key'].split('/')[-1] for obj in s3_objects}
            files_to_upload = local_files - s3_files
            files_to_delete = s3_files - local_files

            # Upload missing files
            for file_name in files_to_upload:
                file_path = os.path.join(folder_path, file_name)
                s3_key = f"{s3_folder}/{file_name}"  # Include the folder name in the key
                try:
                    self.upload_to_s3(
                        file_path=file_path,
                        bucket_name=rec.s3_bucket_name,
                        s3_key=s3_key,
                        access_key=rec.s3_access_key,
                        secret_key=rec.s3_secret_key,
                        region=rec.s3_region,
                    )
                    _logger.info("Uploaded file to S3: %s", s3_key)
                except UserError as e:
                    _logger.error("Failed to upload file %s to S3: %s", file_name, str(e))

            # Delete extra files from S3
            for file_name in files_to_delete:
                s3_key = f"{s3_folder}/{file_name}"  # Include the folder name in the key
                try:
                    s3_client.delete_object(Bucket=rec.s3_bucket_name, Key=s3_key)
                    _logger.info("Deleted file from S3: %s", s3_key)
                except ClientError as e:
                    _logger.error("Failed to delete file %s from S3: %s", s3_key, str(e))
