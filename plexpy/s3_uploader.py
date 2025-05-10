#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import plexpy
from plexpy import logger

# Check if boto3 is installed
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.error("Tautulli S3 Uploader :: Failed to import boto3. S3 backup functionality is not available.")


def check_s3_enabled():
    """Check if S3 backup is enabled and properly configured."""
    if not BOTO3_AVAILABLE:
        logger.error("Tautulli S3 Uploader :: S3 backup is unavailable as boto3 is not installed.")
        return False
    
    if not plexpy.CONFIG.S3_BACKUP_ENABLED:
        logger.debug("Tautulli S3 Uploader :: S3 backup is disabled.")
        return False
    
    required_config = {
        'S3_ENDPOINT': plexpy.CONFIG.S3_ENDPOINT,
        'S3_ACCESS_KEY': plexpy.CONFIG.S3_ACCESS_KEY,
        'S3_SECRET_KEY': plexpy.CONFIG.S3_SECRET_KEY,
        'S3_BUCKET_NAME': plexpy.CONFIG.S3_BUCKET_NAME
    }
    
    missing = [k for k, v in required_config.items() if not v]
    if missing:
        logger.error(f"Tautulli S3 Uploader :: S3 backup is missing required configuration: {', '.join(missing)}")
        return False
    
    return True


def get_s3_client():
    """Create and return an S3 client."""
    if not BOTO3_AVAILABLE:
        return None
    
    # Check for environment variables first
    access_key = os.environ.get('TAUTULLI_S3_ACCESS_KEY', plexpy.CONFIG.S3_ACCESS_KEY)
    secret_key = os.environ.get('TAUTULLI_S3_SECRET_KEY', plexpy.CONFIG.S3_SECRET_KEY)
    
    # Configure the S3 client
    session = boto3.session.Session()
    
    # Set custom endpoint (for MinIO, etc.)
    endpoint_url = plexpy.CONFIG.S3_ENDPOINT if plexpy.CONFIG.S3_ENDPOINT else None
    region = plexpy.CONFIG.S3_REGION if plexpy.CONFIG.S3_REGION else None
    
    try:
        s3_client = session.client(
            service_name='s3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region,
            use_ssl=bool(plexpy.CONFIG.S3_SECURE)
        )
        return s3_client
    except Exception as e:
        logger.error(f"Tautulli S3 Uploader :: Failed to create S3 client: {e}")
        return None


def upload_file_to_s3(file_path, object_name=None):
    """Upload a file to an S3 bucket.

    Args:
        file_path (str): The path to the file to upload
        object_name (str, optional): The S3 object name. If not specified, file_name is used

    Returns:
        bool: True if file was uploaded, False otherwise
    """
    # Check if S3 backup is enabled and configured
    if not check_s3_enabled():
        return False
    
    # If object_name was not specified, use file_path
    if not object_name:
        object_name = os.path.basename(file_path)
    
    # Add prefix if configured
    if plexpy.CONFIG.S3_PREFIX:
        prefix = plexpy.CONFIG.S3_PREFIX.strip('/')
        object_name = f"{prefix}/{object_name}"
    
    # Get S3 client
    s3_client = get_s3_client()
    if not s3_client:
        return False
    
    # Upload the file
    try:
        logger.debug(f"Tautulli S3 Uploader :: Uploading file {file_path} to S3 bucket {plexpy.CONFIG.S3_BUCKET_NAME}/{object_name}")
        with open(file_path, 'rb') as file_data:
            s3_client.upload_fileobj(
                file_data, 
                plexpy.CONFIG.S3_BUCKET_NAME, 
                object_name
            )
        logger.info(f"Tautulli S3 Uploader :: Successfully uploaded file to {plexpy.CONFIG.S3_BUCKET_NAME}/{object_name}")
        return True
    except FileNotFoundError:
        logger.error(f"Tautulli S3 Uploader :: File {file_path} not found for S3 upload")
        return False
    except NoCredentialsError:
        logger.error("Tautulli S3 Uploader :: Credentials not available for S3 upload")
        return False
    except EndpointConnectionError:
        logger.error(f"Tautulli S3 Uploader :: Could not connect to S3 endpoint: {plexpy.CONFIG.S3_ENDPOINT}")
        return False
    except ClientError as e:
        logger.error(f"Tautulli S3 Uploader :: S3 error: {e}")
        return False
    except Exception as e:
        logger.error(f"Tautulli S3 Uploader :: Unexpected error during S3 upload: {e}")
        return False