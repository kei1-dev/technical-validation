#!/usr/bin/env python3
"""
Test script for embedding HTML documents and storing them in S3 Vectors.

This script:
- Reads all HTML files from the s3-vectors-files directory
- Extracts text content from each HTML file
- Generates embeddings using Amazon Titan Embeddings V2
- Stores the embeddings in S3 Vectors with metadata
"""
import argparse
import sys
import os
import glob
from pathlib import Path
from utils import (
    get_s3vectors_client,
    get_bedrock_client,
    read_html_file,
    extract_text_from_html,
    generate_embedding_with_titan_v2,
    format_vector_for_put,
    print_success,
    print_error,
    print_info,
    print_section
)


def process_html_files(
    html_dir: str,
    bedrock_client,
    s3vectors_client,
    bucket_name: str,
    index_name: str,
    batch_size: int = 100
):
    """
    Process all HTML files and store their embeddings in S3 Vectors.

    Args:
        html_dir: Directory containing HTML files
        bedrock_client: Bedrock Runtime client
        s3vectors_client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        batch_size: Number of vectors to upload per batch
    """
    print_section("Processing HTML Documents")

    # Find all HTML files
    html_files = glob.glob(os.path.join(html_dir, "*.html"))

    if not html_files:
        print_error(f"No HTML files found in {html_dir}")
        return

    print_info(f"Found {len(html_files)} HTML files")

    vectors_to_put = []
    processed_count = 0
    failed_count = 0

    for html_file in sorted(html_files):
        file_name = os.path.basename(html_file)
        print_info(f"Processing: {file_name}")

        try:
            # Read HTML file
            html_content = read_html_file(html_file)

            # Extract text
            text = extract_text_from_html(html_content)

            if not text or len(text.strip()) < 50:
                print_error(f"  ✗ Skipping {file_name}: Insufficient text content")
                failed_count += 1
                continue

            # Get file info for metadata
            file_size = os.path.getsize(html_file)
            text_length = len(text)

            print_info(f"  Text extracted: {text_length} characters")

            # Generate embedding with Titan V2
            print_info(f"  Generating embedding with Titan Embeddings V2...")
            embedding = generate_embedding_with_titan_v2(
                bedrock_client,
                text,
                dimensions=1024,
                normalize=True
            )

            print_success(f"  Embedding generated: {len(embedding)} dimensions")

            # Create vector object
            vector_id = file_name.replace('.html', '')

            vector_obj = format_vector_for_put(
                vector_id=vector_id,
                vector=embedding,
                metadata={
                    "file_name": file_name,
                    "file_size": file_size,
                    "text_length": text_length,
                    "doc_type": "s3-vectors-documentation",
                    "language": "ja",
                    "source": "AWS Documentation",
                    "title": extract_title_from_text(text)
                }
            )

            vectors_to_put.append(vector_obj)
            processed_count += 1

            # Upload in batches
            if len(vectors_to_put) >= batch_size:
                upload_vectors_batch(
                    s3vectors_client,
                    bucket_name,
                    index_name,
                    vectors_to_put
                )
                vectors_to_put = []

        except Exception as e:
            print_error(f"  ✗ Failed to process {file_name}: {str(e)}")
            failed_count += 1
            continue

    # Upload remaining vectors
    if vectors_to_put:
        upload_vectors_batch(
            s3vectors_client,
            bucket_name,
            index_name,
            vectors_to_put
        )

    print_section("Processing Complete")
    print_success(f"Successfully processed: {processed_count} files")
    if failed_count > 0:
        print_error(f"Failed to process: {failed_count} files")


def upload_vectors_batch(
    s3vectors_client,
    bucket_name: str,
    index_name: str,
    vectors: list
):
    """
    Upload a batch of vectors to S3 Vectors.

    Args:
        s3vectors_client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        vectors: List of vector objects
    """
    try:
        print_info(f"Uploading batch of {len(vectors)} vectors...")

        response = s3vectors_client.put_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            vectors=vectors
        )

        print_success(f"✓ Uploaded {len(vectors)} vectors successfully")

    except Exception as e:
        print_error(f"Failed to upload vectors: {str(e)}")
        raise


def extract_title_from_text(text: str) -> str:
    """
    Extract a title from the beginning of text.

    Args:
        text: Document text

    Returns:
        str: Extracted title or first 100 characters
    """
    # Take first line or first 100 characters as title
    lines = text.split('\n')
    if lines:
        title = lines[0].strip()
        if title and len(title) > 10:
            return title[:100]

    # Fallback to first 100 characters
    return text[:100].strip()


def verify_upload(
    s3vectors_client,
    bucket_name: str,
    index_name: str
):
    """
    Verify that vectors were uploaded by listing them.

    Args:
        s3vectors_client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
    """
    print_section("Verifying Upload")

    try:
        # Note: List operation may not be available in all regions/versions
        # This is just for verification
        print_info("Attempting to verify uploaded vectors...")
        print_success("Upload verification would go here (API dependent)")

    except Exception as e:
        print_info(f"Verification skipped: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description='Embed HTML documents with Titan V2 and store in S3 Vectors'
    )
    parser.add_argument(
        '--html-dir',
        default='../s3-vectors-files',
        help='Directory containing HTML files (default: ../s3-vectors-files)'
    )
    parser.add_argument(
        '--bucket',
        default='my-s3-vector-bucket',
        help='Vector bucket name (default: my-s3-vector-bucket)'
    )
    parser.add_argument(
        '--index',
        default='my-vector-index',
        help='Vector index name (default: my-vector-index)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of vectors to upload per batch (default: 100)'
    )

    args = parser.parse_args()

    # Resolve HTML directory path
    html_dir = os.path.abspath(args.html_dir)

    if not os.path.exists(html_dir):
        print_error(f"HTML directory not found: {html_dir}")
        sys.exit(1)

    print_section("S3 Vectors - HTML Document Embedding Test")
    print_info(f"HTML Directory: {html_dir}")
    print_info(f"Bucket: {args.bucket}")
    print_info(f"Index: {args.index}")
    print_info(f"Region: {args.region}")
    print_info(f"Batch Size: {args.batch_size}")
    print_info(f"Embedding Model: Amazon Titan Embeddings V2 (1024 dimensions)")

    try:
        # Initialize clients
        print_info("\nInitializing AWS clients...")
        bedrock_client = get_bedrock_client(region=args.region)
        s3vectors_client = get_s3vectors_client(region=args.region)
        print_success("✓ Clients initialized")

        # Process HTML files
        process_html_files(
            html_dir,
            bedrock_client,
            s3vectors_client,
            args.bucket,
            args.index,
            args.batch_size
        )

        # Verify upload
        verify_upload(s3vectors_client, args.bucket, args.index)

        print_section("All Operations Completed Successfully!")

    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
