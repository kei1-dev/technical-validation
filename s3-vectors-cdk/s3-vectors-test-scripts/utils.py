"""
Common utilities for S3 Vectors testing scripts.
"""
import boto3
import numpy as np
from typing import List, Dict, Any, Optional
import json


def get_s3vectors_client(region: str = 'us-east-1'):
    """
    Create and return an S3 Vectors boto3 client.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        boto3.client: S3 Vectors client
    """
    return boto3.client('s3vectors', region_name=region)


def generate_random_vector(dimensions: int = 1024) -> List[float]:
    """
    Generate a random vector with specified dimensions.

    Args:
        dimensions: Number of dimensions (default: 1024)

    Returns:
        List[float]: Random normalized vector
    """
    # Generate random vector
    vector = np.random.randn(dimensions).astype(np.float32)

    # Normalize to unit length (common for similarity search)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def generate_random_vectors(count: int, dimensions: int = 1024) -> List[List[float]]:
    """
    Generate multiple random vectors.

    Args:
        count: Number of vectors to generate
        dimensions: Number of dimensions (default: 1024)

    Returns:
        List[List[float]]: List of random normalized vectors
    """
    return [generate_random_vector(dimensions) for _ in range(count)]


def format_vector_for_put(
    vector_id: str,
    vector: List[float],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a vector for PutVectors API call.

    Args:
        vector_id: Unique identifier for the vector
        vector: The vector data (list of floats)
        metadata: Optional metadata dictionary

    Returns:
        Dict: Formatted vector object
    """
    vector_obj = {
        "key": vector_id,
        "data": {
            "float32": vector
        }
    }

    if metadata:
        vector_obj["metadata"] = metadata

    return vector_obj


def print_query_results(results: Dict[str, Any], top_k: int = 5):
    """
    Pretty print query results.

    Args:
        results: Query results from QueryVectors API
        top_k: Number of top results to display
    """
    if 'vectors' not in results or not results['vectors']:
        print("No results found.")
        return

    print(f"\nFound {len(results['vectors'])} results:")
    print("-" * 80)

    for i, result in enumerate(results['vectors'][:top_k], 1):
        vector_id = result.get('key', 'N/A')
        distance = result.get('distance', 0.0)
        metadata = result.get('metadata', {})

        print(f"\n{i}. Vector ID: {vector_id}")
        print(f"   Distance: {distance:.4f}")

        if metadata:
            print(f"   Metadata: {json.dumps(metadata, indent=6, ensure_ascii=False)}")


def print_success(message: str):
    """Print success message."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"✗ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"ℹ {message}")


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}\n")


def get_bedrock_client(region: str = 'us-east-1'):
    """
    Create and return a Bedrock Runtime boto3 client.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        boto3.client: Bedrock Runtime client
    """
    return boto3.client('bedrock-runtime', region_name=region)


def extract_text_from_html(html_content: str) -> str:
    """
    Extract clean text from HTML content.

    Args:
        html_content: HTML string

    Returns:
        str: Extracted text
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'lxml')

    # Remove script and style elements
    for script in soup(['script', 'style', 'meta', 'link']):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)

    return text


def generate_embedding_with_titan_v2(
    bedrock_client,
    text: str,
    dimensions: int = 1024,
    normalize: bool = True
) -> List[float]:
    """
    Generate vector embedding using Amazon Titan Embeddings V2.

    Args:
        bedrock_client: Bedrock Runtime client
        text: Input text to embed
        dimensions: Output dimensions (256, 512, or 1024)
        normalize: Whether to normalize the vector

    Returns:
        List[float]: Vector embedding
    """
    import json

    # Truncate text if too long (Titan V2 max is ~8192 tokens, ~30000 chars as rough estimate)
    max_chars = 25000
    if len(text) > max_chars:
        text = text[:max_chars]

    # Prepare request
    request_body = {
        "inputText": text,
        "dimensions": dimensions,
        "normalize": normalize
    }

    # Call Bedrock
    response = bedrock_client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps(request_body),
        contentType="application/json",
        accept="application/json"
    )

    # Parse response
    response_body = json.loads(response['body'].read())
    embedding = response_body['embedding']

    return embedding


def read_html_file(file_path: str) -> str:
    """
    Read HTML file and return its content.

    Args:
        file_path: Path to HTML file

    Returns:
        str: HTML content
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
