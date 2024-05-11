###################################################################################
#
#    Copyright (c) 2021,2024 Cyril MORISSE (github: cmorisse)
#
#    This file is a part of 'inouk_attachments_storage' addon
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import boto3
import botocore
import logging
import random
import time
import os

from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError,AccessError

from odoo.addons.inouk_message_queue.api import processor_method

_logger = logging.getLogger("IKAttachmentStorage")


IK_IR_ATTACHMENT_S3_INFO = None
IK_IR_ATTACHMENT_S3_INFO_TTL = 90       # Cache is refreshed every 90s

INOUK_S3_ADD_DATABASE_TO_S3_OBJECT_KEY = False


class InoukIRAttachmentS3(models.Model):
    """ Get and Put attachment files into S3 bucket defined by ENV VARs above.
    To activate S3 storage, in Settings, Attachment Storage must be set to file and
    IK_IR_ATTACHMENT_S3_ENABLED must be 'set'. 
    When IK_IR_ATTACHMENT_S3_ENABLED is set, S3 has precedence over file system.
    Hence, Odoo will always try to read and write from/to S3.

    """
    _inherit = "ir.attachment"

    ikas_file_location = fields.Char(
        "File Storage. Location",
        help="Where is the file stored when not on disk. Don't modify this by hand."
    )

    @api.model
    def _get_ikas_s3_config(self):
        """ Get S3 config (and credentials) from ENV vars and cache them.
        :returns: None but update IK_IR_ATTACHMENT_S3_INFO
        """
        global IK_IR_ATTACHMENT_S3_INFO
        global INOUK_S3_ADD_DATABASE_TO_S3_OBJECT_KEY

        if IK_IR_ATTACHMENT_S3_INFO:  # TODO and age < 90s
            return

        #s3_enabled_raw       = os.environ.get("IK_IR_ATTACHMENT_S3_ENABLED", '')
        #s3_enabled           = s3_enabled_raw.lower() == 'true'

        s3_enabled_raw = self.env['ir.config_parameter'].sudo().get_param(
            'inouk.ir_attachment_s3_enabled', 
            'False'
        )
        s3_enabled           = s3_enabled_raw.lower() == 'true'

        s3_add_database_to_s3_object_key_raw = self.env['ir.config_parameter'].sudo().get_param(
            'inouk.ir_attachment_s3_use_database_as_object_key_prefix', 
            'False'
        )
        s3_add_database_to_s3_object_key = s3_add_database_to_s3_object_key_raw.lower() == 'true'
        INOUK_S3_ADD_DATABASE_TO_S3_OBJECT_KEY = s3_add_database_to_s3_object_key

        s3_bucket            = os.environ.get("IK_IR_ATTACHMENT_S3_BUCKET", None)
        s3_endpoint_url      = os.environ.get("IK_IR_ATTACHMENT_S3_ENDPOINT_URL", None)
        s3_access_key_id     = os.environ.get("IK_IR_ATTACHMENT_S3_ACCESS_KEY_ID", None)
        s3_secret_access_key = os.environ.get("IK_IR_ATTACHMENT_S3_SECRET_ACCESS_KEY", None)
        s3_region            = os.environ.get("IK_IR_ATTACHMENT_S3_REGION", None)

        IK_IR_ATTACHMENT_S3_INFO = {
            "S3_ENABLED": s3_enabled,
            "S3_BUCKET": s3_bucket,
            "S3_ENDPOINT_URL": s3_endpoint_url,
            "S3_ACCESS_KEY_ID": s3_access_key_id,
            "S3_SECRET_ACCESS_KEY": s3_secret_access_key,           
            "S3_REGION": s3_region,
            "ts": fields.Datetime.now()
        }
        
        # Check if the credentials are set
        if s3_enabled and not (s3_bucket and s3_access_key_id and s3_secret_access_key):
            raise ValidationError(
                "S3 credentials not configured correctly. Please set the environment variables."
            )
        _logger.info("ir.attachment::IK_IR_ATTACHMENT_S3_INFO: %s", IK_IR_ATTACHMENT_S3_INFO)
        return

    @api.model
    def _ikas_file_read_s3(self, fname):
        """ Read attachment from s3.

        _get_ikas_s3_config() must have been called before.

        :returns: 
            - file content if found
            - None if  key not found on bucket
            - 
        """
        # self._get_ikas_s3_config() must have been called before.
        #_logger.info("_ikas_file_read_s3(%s)", fname)
        s3 = boto3.client(
            service_name="s3",
            endpoint_url = IK_IR_ATTACHMENT_S3_INFO.get("S3_ENDPOINT_URL", None),
            aws_access_key_id=IK_IR_ATTACHMENT_S3_INFO['S3_ACCESS_KEY_ID'],
            aws_secret_access_key=IK_IR_ATTACHMENT_S3_INFO['S3_SECRET_ACCESS_KEY'],
            region_name=IK_IR_ATTACHMENT_S3_INFO['S3_REGION'],
        )

        nb_retries = 3
        initial_delay = 2   # in seconds
        max_delay = 10      # in seconds
        s3_bucket = IK_IR_ATTACHMENT_S3_INFO['S3_BUCKET']

        for attempt in range(nb_retries):
            try:
                if INOUK_S3_ADD_DATABASE_TO_S3_OBJECT_KEY:
                    key = "%s/%s" (self.env.cr.dbname, fname)
                else:
                    key = fname
                _logger.debug(f"Trying to get key={key} from s3 bucket:'{s3_bucket}'.")
                response = s3.get_object(
                    Bucket=s3_bucket, 
                    Key=key
                )
                return response["Body"].read()

            except botocore.exceptions.ClientError as err:
                error_code = err.response["Error"]["Code"]
                if error_code == "NoSuchKey":
                    return None
                _logger.error(f"Failed to get key '{fname}' with Error:'{error_code} - {err}'")

            except Exception as err:
                _logger.exception(f"Exception '{err}' while trying to get object with key '{fname}'")

            if attempt < nb_retries - 1:
                sleep_time = min(
                    max_delay,
                    (initial_delay * 2**attempt) * (1 + random.uniform(-0.1, 0.1)),
                )
                time.sleep(sleep_time)
            else:
                return None

    def _file_read(self, fname, bin_size):
        """ Read a file from S3 or fall back to the local file system."""
        self._get_ikas_s3_config()
        if IK_IR_ATTACHMENT_S3_INFO['S3_ENABLED']:
            file_content = self._ikas_file_read_s3(fname)
            if file_content:
                return file_content
            _logger.warning(f"Attachment with key='{fname}' unexpectedly not found on s3.")

        return super()._file_read(fname, bin_size)

    @api.model
    def _ikas_file_write_s3(self, fname, value):
        """Write attachment data an S3."
        :param value: this is attachment binary content

        :returns: None of fname if put was sucessful
        """
        _logger.info("_ikas_file_read_s3(%s)", fname)

        # self._get_ikas_s3_config() must have been called before.
        s3 = boto3.client(
            service_name="s3",
            endpoint_url = IK_IR_ATTACHMENT_S3_INFO.get("S3_ENDPOINT_URL", None),
            aws_access_key_id=IK_IR_ATTACHMENT_S3_INFO['S3_ACCESS_KEY_ID'],
            aws_secret_access_key=IK_IR_ATTACHMENT_S3_INFO['S3_SECRET_ACCESS_KEY'],
            region_name=IK_IR_ATTACHMENT_S3_INFO['S3_REGION'],
        )

        nb_retries = 3
        initial_delay = 2   # in seconds
        max_delay = 10      # in seconds
        s3_bucket = IK_IR_ATTACHMENT_S3_INFO['S3_BUCKET']
        for attempt in range(nb_retries):

            try:
                if INOUK_S3_ADD_DATABASE_TO_S3_OBJECT_KEY:
                    key = "%s/%s" (self.env.cr.dbname, fname)
                else:
                    key = fname
                _logger.debug(f"Trying to put key '{key}' in s3 bucket:'{s3_bucket}'.")
                response = s3.put_object(
                    Bucket=s3_bucket, 
                    Key=key, 
                    Body=value
                )
                _logger.info(f"Successfully uploaded file '{fname}' to S3 bucket '{s3_bucket}'.")
                if self:
                    self.ikas_file_location = 's3'
                return fname

            except botocore.exceptions.ClientError as err:
                error_code = err.response["Error"]["Code"]
                _logger.error(f"Failed to put object content for key '{fname}' with Error:'{error_code} - {err}'")

            except Exception as err:
                _logger.exception(f"Exception '{err}' while trying to put object with key='{fname}'")

            # If there are remaining retry attempts, sleep using exponential backoff with jitter
            if attempt < nb_retries - 1:
                sleep_time = min(
                    max_delay,
                    (initial_delay * 2**attempt) * (1 + random.uniform(-0.1, 0.1)),
                )
                time.sleep(sleep_time)
            else:  # Quand ca veut pas, ca veut pas !
                return None
        return None

    def _file_write(self, value, checksum):
        """ Write attachment to S3 (when configured), falling back to the local file system if the upload fails."""
        self._get_ikas_s3_config()
        if IK_IR_ATTACHMENT_S3_INFO['S3_ENABLED']:
            fname, full_path = self._get_path(value, checksum)
            res = self._ikas_file_write_s3(fname, value)
            if not res:
                fname = super()._file_write(value, checksum)
                _logger.warning(f"Attachment stored locally due to S3 upload failure.")

            return fname 
        fname = super()._file_write(value, checksum)
        return fname
