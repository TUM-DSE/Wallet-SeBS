from enum import Enum


class Platforms(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    CVM = "cvm"
    KATA_QEMU = "kata-qemu"
    KATA_FC = "kata-fc"
    GRAMINE = "gramine"
    GRAMINE_NATIVE = "gramine_native"
    WALLET = "wallet"
    GCP = "gcp"
    LOCAL = "local"
    OPENWHISK = "openwhisk"


class Storage(str, Enum):
    AWS_S3 = "aws-s3"
    AZURE_BLOB_STORAGE = "azure-blob-storage"
    GCP_STORAGE = "google-cloud-storage"
    MINIO = "minio"
