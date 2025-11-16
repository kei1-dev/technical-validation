#!/usr/bin/env python3
"""
Test script for metadata filtering with S3 Vectors using HTML documents.

This script demonstrates:
- Filtering HTML documentation by metadata
- Combining similarity search with metadata filters
- Testing various filter conditions on real documentation data
"""
import argparse
import sys
from utils import (
    get_s3vectors_client,
    get_bedrock_client,
    generate_embedding_with_titan_v2,
    print_query_results,
    print_success,
    print_error,
    print_info,
    print_section
)


def test_search_with_filter(
    client,
    bedrock_client,
    bucket_name: str,
    index_name: str,
    query_text: str,
    filter_expression: dict = None,
    description: str = "Search"
):
    """
    Test similarity search with metadata filter.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
        query_text: Query text
        filter_expression: Metadata filter expression
        description: Description of the search
    """
    print_section(description)

    try:
        print_info(f"Query: {query_text}")
        if filter_expression:
            print_info(f"Filter: {filter_expression}")

        # Generate embedding for query
        print_info("Generating query embedding...")
        query_vector = generate_embedding_with_titan_v2(
            bedrock_client,
            query_text,
            dimensions=1024,
            normalize=True
        )

        params = {
            'vectorBucketName': bucket_name,
            'indexName': index_name,
            'queryVector': query_vector,
            'topK': 10
        }

        # Add filter if provided
        if filter_expression:
            params['metadataFilter'] = filter_expression

        response = client.query_vectors(**params)

        results = response.get('vectors', [])
        print_success(f"Found {len(results)} results")
        print_query_results(response, top_k=10)

        return response

    except Exception as e:
        print_error(f"Search failed: {str(e)}")
        raise


def test_various_filters(client, bedrock_client, bucket_name: str, index_name: str):
    """
    Test various metadata filter scenarios on HTML documentation.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
    """
    print_section("Testing Various Metadata Filters on HTML Documents")

    # Test 1: Filter by document type
    test_search_with_filter(
        client,
        bedrock_client,
        bucket_name,
        index_name,
        query_text="ベクトルの操作方法",
        filter_expression={"doc_type": {"$eq": "s3-vectors-documentation"}},
        description="Test 1: Filter by Document Type (s3-vectors-documentation)"
    )

    # Test 2: Filter by language
    test_search_with_filter(
        client,
        bedrock_client,
        bucket_name,
        index_name,
        query_text="セキュリティの設定",
        filter_expression={"language": {"$eq": "ja"}},
        description="Test 2: Filter by Language (Japanese)"
    )

    # Test 3: Filter by source
    test_search_with_filter(
        client,
        bedrock_client,
        bucket_name,
        index_name,
        query_text="バケットの作成",
        filter_expression={"source": {"$eq": "AWS Documentation"}},
        description="Test 3: Filter by Source (AWS Documentation)"
    )

    # Test 4: Search without filter (baseline)
    test_search_with_filter(
        client,
        bedrock_client,
        bucket_name,
        index_name,
        query_text="インデックスの管理",
        filter_expression=None,
        description="Test 4: Search without Filter (Baseline)"
    )


def test_specific_topics(client, bedrock_client, bucket_name: str, index_name: str):
    """
    Test searches for specific S3 Vectors topics.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
    """
    print_section("Testing Topic-Specific Searches")

    topics = [
        {
            "query": "ベクトルバケットの作成と削除",
            "description": "Bucket Operations"
        },
        {
            "query": "類似度検索とk-NN",
            "description": "Similarity Search"
        },
        {
            "query": "IAMポリシーとアクセス権限",
            "description": "Security & Access Management"
        },
        {
            "query": "データの暗号化",
            "description": "Data Encryption"
        },
        {
            "query": "制限事項とクォータ",
            "description": "Limitations & Quotas"
        },
    ]

    for i, topic in enumerate(topics, 1):
        print_info(f"\n--- Topic {i}/{len(topics)}: {topic['description']} ---")

        try:
            # Generate embedding
            query_vector = generate_embedding_with_titan_v2(
                bedrock_client,
                topic['query'],
                dimensions=1024,
                normalize=True
            )

            # Perform search
            response = client.query_vectors(
                vectorBucketName=bucket_name,
                indexName=index_name,
                queryVector=query_vector,
                topK=5
            )

            results = response.get('vectors', [])
            print_success(f"Query: {topic['query']}")
            print_success(f"Found {len(results)} results")

            # Show results
            for j, result in enumerate(results, 1):
                vector_id = result.get('vectorId', 'N/A')
                score = result.get('score', 0.0)
                metadata = result.get('metadata', {})
                file_name = metadata.get('file_name', 'N/A')

                print(f"  {j}. {vector_id} (score: {score:.4f}) - {file_name}")

        except Exception as e:
            print_error(f"Topic search {i} failed: {str(e)}")


def analyze_document_coverage(client, bedrock_client, bucket_name: str, index_name: str):
    """
    Analyze which documents are retrieved for different query types.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
    """
    print_section("Analyzing Document Coverage")

    query_categories = {
        "Getting Started": "S3 Vectorsの始め方",
        "Operations": "ベクトルの追加と削除",
        "Security": "セキュリティとアクセス制御",
        "Performance": "パフォーマンスの最適化",
        "Integration": "他のAWSサービスとの統合"
    }

    coverage_map = {}

    for category, query in query_categories.items():
        try:
            # Generate embedding
            query_vector = generate_embedding_with_titan_v2(
                bedrock_client,
                query,
                dimensions=1024,
                normalize=True
            )

            # Perform search
            response = client.query_vectors(
                vectorBucketName=bucket_name,
                indexName=index_name,
                queryVector=query_vector,
                topK=3
            )

            results = response.get('vectors', [])
            doc_files = [r.get('metadata', {}).get('file_name', 'unknown') for r in results]

            coverage_map[category] = doc_files

            print_info(f"{category}: {query}")
            for i, doc in enumerate(doc_files, 1):
                print(f"  {i}. {doc}")

        except Exception as e:
            print_error(f"Coverage analysis for {category} failed: {str(e)}")

    return coverage_map


def main():
    parser = argparse.ArgumentParser(
        description='Test metadata filtering with S3 Vectors using HTML documents'
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
        '--test-filters',
        action='store_true',
        help='Test various metadata filters'
    )
    parser.add_argument(
        '--test-topics',
        action='store_true',
        help='Test topic-specific searches'
    )
    parser.add_argument(
        '--analyze-coverage',
        action='store_true',
        help='Analyze document coverage'
    )

    args = parser.parse_args()

    print_section("S3 Vectors - Metadata Filtering Test (HTML Documents)")
    print_info(f"Bucket: {args.bucket}")
    print_info(f"Index: {args.index}")
    print_info(f"Region: {args.region}")
    print_info(f"Embedding Model: Amazon Titan Embeddings V2 (1024 dimensions)")

    try:
        # Initialize clients
        print_info("\nInitializing AWS clients...")
        s3vectors_client = get_s3vectors_client(region=args.region)
        bedrock_client = get_bedrock_client(region=args.region)
        print_success("✓ Clients initialized")

        # Run tests based on arguments
        if args.test_filters:
            test_various_filters(s3vectors_client, bedrock_client, args.bucket, args.index)

        if args.test_topics:
            test_specific_topics(s3vectors_client, bedrock_client, args.bucket, args.index)

        if args.analyze_coverage:
            analyze_document_coverage(s3vectors_client, bedrock_client, args.bucket, args.index)

        # If no specific test selected, run all
        if not (args.test_filters or args.test_topics or args.analyze_coverage):
            print_info("No specific test selected. Running all tests...")
            test_various_filters(s3vectors_client, bedrock_client, args.bucket, args.index)
            test_specific_topics(s3vectors_client, bedrock_client, args.bucket, args.index)
            analyze_document_coverage(s3vectors_client, bedrock_client, args.bucket, args.index)

        print_section("All Metadata Filtering Tests Completed Successfully!")

    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
