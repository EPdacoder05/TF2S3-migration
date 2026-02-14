"""
TF2S3 Migration Tool - Universal Terraform Cloud to S3 Backend Migration

A production-ready tool for migrating Terraform state backends from HCP Terraform Cloud
to AWS S3/DynamoDB across multiple repositories with parallel processing capabilities.
"""

__version__ = "1.0.0"
__author__ = "EPdacoder05"

# Export all submodules for convenient imports
from . import config
from . import tf_ops
from . import gh_ops
from . import state_ops
from . import utils
from . import validation

__all__ = [
    "config",
    "tf_ops",
    "gh_ops",
    "state_ops",
    "utils",
    "validation",
]
