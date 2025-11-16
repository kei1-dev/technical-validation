#!/usr/bin/env python3
"""
Test script for similarity search with S3 Vectors using HTML documents.

This script demonstrates:
- Querying with actual text from HTML documents
- Performing k-nearest neighbor (k-NN) similarity search
- Finding similar documentation pages
- Analyzing search results with real data
"""
import argparse
import sys
import os
from utils import (
    get_s3vectors_client,
    get_bedrock_client,
    read_html_file,
    extract_text_from_html,
    generate_embedding_with_titan_v2,
    print_query_results,
    print_success,
    print_error,
    print_info,
    print_section
)


def search_with_query_text(
    client,
    bedrock_client,
    bucket_name: str,
    index_name: str,
    query_text: str,
    top_k: int = 10
):
    """
    Perform similarity search using query text.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
        query_text: Query text to search for
        top_k: Number of top results to retrieve
    """
    print_section(f"Similarity Search with Query Text")

    try:
        print_info(f"Query: {query_text[:100]}...")
        print_info("Generating embedding for query...")

        # Generate embedding for query text
        query_vector = generate_embedding_with_titan_v2(
            bedrock_client,
            query_text,
            dimensions=1024,
            normalize=True
        )

        print_success(f"Query embedding generated: {len(query_vector)} dimensions")
        print_info("Performing similarity search...")

        response = client.query_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            queryVector={"float32": query_vector},
            topK=top_k,
            returnMetadata=True,
            returnDistance=True
        )

        print_success("Search completed!")
        print_query_results(response, top_k=top_k)

        return response

    except Exception as e:
        print_error(f"Similarity search failed: {str(e)}")
        raise


def search_with_html_file(
    client,
    bedrock_client,
    bucket_name: str,
    index_name: str,
    html_file: str,
    top_k: int = 10
):
    """
    Perform similarity search using an HTML file as query.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
        html_file: Path to HTML file to use as query
        top_k: Number of top results to retrieve
    """
    print_section(f"Similarity Search with HTML Document")

    try:
        print_info(f"Query document: {os.path.basename(html_file)}")

        # Read and extract text from HTML
        html_content = read_html_file(html_file)
        text = extract_text_from_html(html_content)

        print_info(f"Extracted {len(text)} characters")
        print_info("Generating embedding for query document...")

        # Generate embedding
        query_vector = generate_embedding_with_titan_v2(
            bedrock_client,
            text,
            dimensions=1024,
            normalize=True
        )

        print_success(f"Query embedding generated: {len(query_vector)} dimensions")
        print_info("Performing similarity search...")

        response = client.query_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            queryVector={"float32": query_vector},
            topK=top_k,
            returnMetadata=True,
            returnDistance=True
        )

        print_success("Search completed!")
        print_query_results(response, top_k=top_k)

        return response

    except Exception as e:
        print_error(f"Similarity search failed: {str(e)}")
        raise


def test_predefined_queries(
    client,
    bedrock_client,
    bucket_name: str,
    index_name: str,
    top_k: int = 5
):
    """
    Test multiple predefined queries related to S3 Vectors.

    Args:
        client: S3 Vectors client
        bedrock_client: Bedrock client
        bucket_name: Vector bucket name
        index_name: Vector index name
        top_k: Number of top results to retrieve
    """
    print_section("Testing Predefined Queries")

    queries = [
        "ベクトルバケットの作成方法",
        "類似度検索の実行方法",
        "メタデータフィルタリングの使い方",
        "S3 Vectorsのセキュリティとアクセス管理",
        "ベクトルインデックスの削除手順",
    ]

    for i, query in enumerate(queries, 1):
        print_info(f"\n--- Query {i}/{len(queries)} ---")
        print_info(f"Query: {query}")

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
                queryVector={"float32": query_vector},
                topK=top_k,
                returnMetadata=True,
                returnDistance=True
            )

            results = response.get('vectors', [])
            print_success(f"Found {len(results)} results")

            # Show top 3 results
            for j, result in enumerate(results[:3], 1):
                vector_id = result.get('key', 'N/A')
                distance = result.get('distance', 0.0)
                metadata = result.get('metadata', {})
                file_name = metadata.get('file_name', 'N/A')
                title = metadata.get('title', 'N/A')

                print(f"  {j}. {vector_id} (distance: {distance:.4f})")
                print(f"     File: {file_name}")
                print(f"     Title: {title[:80]}...")

        except Exception as e:
            print_error(f"Query {i} failed: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description='Test similarity search with S3 Vectors using HTML documents'
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
        '--top-k',
        type=int,
        default=10,
        help='Number of top results to retrieve (default: 10)'
    )
    parser.add_argument(
        '--query-text',
        help='Query text for similarity search'
    )
    parser.add_argument(
        '--query-html',
        help='Path to HTML file to use as query'
    )
    parser.add_argument(
        '--test-queries',
        action='store_true',
        help='Run predefined test queries'
    )

    args = parser.parse_args()

    print_section("S3 Vectors - Similarity Search Test (HTML Documents)")
    print_info(f"Bucket: {args.bucket}")
    print_info(f"Index: {args.index}")
    print_info(f"Region: {args.region}")
    print_info(f"Top-K: {args.top_k}")
    print_info(f"Embedding Model: Amazon Titan Embeddings V2 (1024 dimensions)")

    try:
        # Initialize clients
        print_info("\nInitializing AWS clients...")
        s3vectors_client = get_s3vectors_client(region=args.region)
        bedrock_client = get_bedrock_client(region=args.region)
        print_success("✓ Clients initialized")

        # Determine which test to run
        if args.query_text:
            # Search with query text
            search_with_query_text(
                s3vectors_client,
                bedrock_client,
                args.bucket,
                args.index,
                args.query_text,
                args.top_k
            )

        elif args.query_html:
            # Search with HTML file
            if not os.path.exists(args.query_html):
                print_error(f"HTML file not found: {args.query_html}")
                sys.exit(1)

            search_with_html_file(
                s3vectors_client,
                bedrock_client,
                args.bucket,
                args.index,
                args.query_html,
                args.top_k
            )

        elif args.test_queries:
            # Run predefined test queries
            test_predefined_queries(
                s3vectors_client,
                bedrock_client,
                args.bucket,
                args.index,
                top_k=5
            )

        else:
            # Default: run predefined test queries
            print_info("No query specified. Running predefined test queries...")
            test_predefined_queries(
                s3vectors_client,
                bedrock_client,
                args.bucket,
                args.index,
                top_k=5
            )

        print_section("All Similarity Search Tests Completed Successfully!")

    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
