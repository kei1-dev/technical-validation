#!/usr/bin/env python3
"""
Test script for basic CRUD operations with S3 Vectors.

This script demonstrates:
- Creating vectors (PutVectors)
- Listing vectors
- Deleting vectors (DeleteVectors)
- Managing HTML document vectors
"""
import argparse
import sys
import os
import glob
from utils import (
    get_s3vectors_client,
    generate_random_vectors,
    format_vector_for_put,
    print_success,
    print_error,
    print_info,
    print_section
)


def test_put_vectors(client, bucket_name: str, index_name: str, num_vectors: int = 10):
    """
    Test adding vectors to the index.

    Args:
        client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        num_vectors: Number of vectors to create
    """
    print_section("Testing PutVectors Operation")

    try:
        # Generate random vectors
        print_info(f"Generating {num_vectors} random vectors (1024 dimensions)...")
        vectors_data = generate_random_vectors(count=num_vectors, dimensions=1024)

        # Format vectors for PutVectors API
        vectors_to_put = []
        for i, vector in enumerate(vectors_data, 1):
            vector_obj = format_vector_for_put(
                vector_id=f"test-vector-{i:03d}",
                vector=vector,
                metadata={
                    "category": "test",
                    "index": i,
                    "description": f"Test vector number {i}"
                }
            )
            vectors_to_put.append(vector_obj)

        # Put vectors (S3 Vectors supports up to 500 vectors per call)
        print_info(f"Uploading {len(vectors_to_put)} vectors to bucket '{bucket_name}', index '{index_name}'...")

        response = client.put_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            vectors=vectors_to_put
        )

        print_success(f"Successfully uploaded {len(vectors_to_put)} vectors!")
        print_info(f"Response: {response}")

        return vectors_to_put

    except Exception as e:
        print_error(f"Failed to put vectors: {str(e)}")
        raise


def test_delete_vectors(client, bucket_name: str, index_name: str, vector_ids: list):
    """
    Test deleting vectors from the index.

    Args:
        client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        vector_ids: List of vector IDs to delete
    """
    print_section("Testing DeleteVectors Operation")

    try:
        # Delete only the first 3 vectors
        ids_to_delete = vector_ids[:3]

        print_info(f"Deleting {len(ids_to_delete)} vectors: {ids_to_delete}")

        response = client.delete_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            keys=ids_to_delete
        )

        print_success(f"Successfully deleted {len(ids_to_delete)} vectors!")
        print_info(f"Response: {response}")

    except Exception as e:
        print_error(f"Failed to delete vectors: {str(e)}")
        raise


def test_list_indexes(client, bucket_name: str):
    """
    Test listing indexes in the bucket.

    Args:
        client: S3 Vectors client
        bucket_name: Vector bucket name
    """
    print_section("Testing ListIndexes Operation")

    try:
        print_info(f"Listing indexes in bucket '{bucket_name}'...")

        response = client.list_indexes(
            vectorBucketName=bucket_name
        )

        indexes = response.get('indexes', [])
        print_success(f"Found {len(indexes)} index(es):")

        for idx in indexes:
            index_name = idx.get('indexName', 'N/A')
            dimensions = idx.get('dimensions', 'N/A')
            status = idx.get('status', 'N/A')
            print(f"  - {index_name} (dimensions: {dimensions}, status: {status})")

    except Exception as e:
        print_error(f"Failed to list indexes: {str(e)}")
        raise


def delete_html_documents(client, bucket_name: str, index_name: str, html_dir: str):
    """
    Delete HTML document vectors from the index.

    Args:
        client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        html_dir: Directory containing HTML files
    """
    print_section("Deleting HTML Document Vectors")

    try:
        # Find all HTML files
        html_files = glob.glob(os.path.join(html_dir, "*.html"))

        if not html_files:
            print_error(f"No HTML files found in {html_dir}")
            return

        # Generate vector IDs from filenames
        vector_ids = []
        for html_file in html_files:
            file_name = os.path.basename(html_file)
            vector_id = file_name.replace('.html', '')
            vector_ids.append(vector_id)

        print_info(f"Found {len(vector_ids)} HTML document vectors to delete")
        print_info(f"First 5 IDs: {vector_ids[:5]}")

        # Confirm deletion
        print_info("Deleting vectors...")

        response = client.delete_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            keys=vector_ids
        )

        print_success(f"Successfully deleted {len(vector_ids)} HTML document vectors!")
        print_info(f"Response: {response}")

    except Exception as e:
        print_error(f"Failed to delete HTML document vectors: {str(e)}")
        raise


def delete_specific_documents(client, bucket_name: str, index_name: str, vector_ids: list):
    """
    Delete specific document vectors by their IDs.

    Args:
        client: S3 Vectors client
        bucket_name: Vector bucket name
        index_name: Vector index name
        vector_ids: List of vector IDs to delete
    """
    print_section("Deleting Specific Document Vectors")

    try:
        print_info(f"Deleting {len(vector_ids)} vectors...")
        print_info(f"Vector IDs: {vector_ids}")

        response = client.delete_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            keys=vector_ids
        )

        print_success(f"Successfully deleted {len(vector_ids)} vectors!")
        print_info(f"Response: {response}")

    except Exception as e:
        print_error(f"Failed to delete vectors: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Test basic CRUD operations with S3 Vectors'
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
        '--num-vectors',
        type=int,
        default=10,
        help='Number of vectors to create (default: 10)'
    )
    parser.add_argument(
        '--delete-html-docs',
        action='store_true',
        help='Delete all HTML document vectors'
    )
    parser.add_argument(
        '--html-dir',
        default='../s3-vectors-files',
        help='Directory containing HTML files (default: ../s3-vectors-files)'
    )
    parser.add_argument(
        '--delete-ids',
        nargs='+',
        help='Delete specific vector IDs (space-separated list)'
    )

    args = parser.parse_args()

    print_section("S3 Vectors - Basic CRUD Operations Test")
    print_info(f"Bucket: {args.bucket}")
    print_info(f"Index: {args.index}")
    print_info(f"Region: {args.region}")

    try:
        # Initialize S3 Vectors client
        client = get_s3vectors_client(region=args.region)

        # Test 1: List existing indexes
        test_list_indexes(client, args.bucket)

        # Handle delete operations
        if args.delete_html_docs:
            # Delete all HTML document vectors
            html_dir = os.path.abspath(args.html_dir)
            if not os.path.exists(html_dir):
                print_error(f"HTML directory not found: {html_dir}")
                sys.exit(1)

            delete_html_documents(client, args.bucket, args.index, html_dir)

        elif args.delete_ids:
            # Delete specific vector IDs
            delete_specific_documents(client, args.bucket, args.index, args.delete_ids)

        else:
            # Default: Run standard tests
            print_info(f"Number of vectors: {args.num_vectors}")

            # Test 2: Put vectors
            vectors = test_put_vectors(
                client,
                args.bucket,
                args.index,
                args.num_vectors
            )

            # Extract vector IDs
            vector_ids = [v['key'] for v in vectors]

            # Test 3: Delete some vectors
            test_delete_vectors(client, args.bucket, args.index, vector_ids)

        print_section("All Tests Completed Successfully!")

    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
