"""
Test proxy and no_proxy functionality.

Usage:
    # Test without proxy (direct connection)
    python scripts/test_proxy.py

    # Test with proxy configuration
    python scripts/test_proxy.py --proxy http://proxy.company.com:8080

    # Test with no_proxy configuration
    python scripts/test_proxy.py --proxy http://proxy:8080 --no-proxy "localhost,*.internal.com,10.*"
"""
import argparse
import asyncio
import sys

# Add backend to path
sys.path.insert(0, '.')

from app.services.common.http_client import HttpClientFactory
from app.services.data_fetchers import OpenAlexClient


def test_no_proxy_matching():
    """Test no_proxy pattern matching logic."""
    print("\n" + "=" * 60)
    print("Testing no_proxy Pattern Matching")
    print("=" * 60)

    test_cases = [
        ('localhost,127.0.0.1', 'http://localhost:8080', False),
        ('localhost,127.0.0.1', 'https://api.openalex.org', True),
        ('*.internal.com', 'http://llm.internal.com', False),
        ('*.internal.com', 'https://api.openai.com', True),
        ('10.*,192.168.*', 'http://10.0.0.1', False),
        ('10.*,192.168.*', 'http://192.168.1.1', False),
        ('10.*,192.168.*', 'https://external.com', True),
    ]

    all_passed = True
    for no_proxy, url, expected_use_proxy in test_cases:
        HttpClientFactory.reset()
        HttpClientFactory.configure(proxy_url='http://proxy:8080', no_proxy=no_proxy)
        result = HttpClientFactory.should_use_proxy(url)
        status = 'PASS' if result == expected_use_proxy else 'FAIL'
        if result != expected_use_proxy:
            all_passed = False
        print(f'  [{status}] no_proxy={no_proxy}, url={url}')
        print(f'        Expected: {"Use Proxy" if expected_use_proxy else "Direct"}')
        print(f'        Actual:   {"Use Proxy" if result else "Direct"}')

    return all_passed


def test_openalex_client():
    """Test OpenAlexClient proxy decision logic."""
    print("\n" + "=" * 60)
    print("Testing OpenAlexClient Proxy Decision")
    print("=" * 60)

    client = OpenAlexClient(
        proxy_url='http://proxy:8080',
        no_proxy='*.internal.com,10.*'
    )

    test_urls = [
        ('https://api.openalex.org/works', 'http://proxy:8080', 'External API - should use proxy'),
        ('http://llm.internal.com/v1/chat', None, 'Internal LLM - should bypass proxy'),
        ('http://10.0.0.1:8003/api', None, 'Internal IP - should bypass proxy'),
    ]

    all_passed = True
    for url, expected_proxy, desc in test_urls:
        result = client.get_proxy_for_request(url)
        status = 'PASS' if result == expected_proxy else 'FAIL'
        if result != expected_proxy:
            all_passed = False
        print(f'  [{status}] {desc}')
        print(f'        URL: {url}')
        print(f'        Expected: {expected_proxy or "Direct"}')
        print(f'        Actual:   {result or "Direct"}')

    return all_passed


async def test_actual_connection(proxy_url: str = None, no_proxy: str = None):
    """Test actual HTTP connection (requires network access)."""
    print("\n" + "=" * 60)
    print("Testing Actual Network Connection")
    print("=" * 60)

    import httpx

    test_urls = [
        ('https://api.openalex.org/works?per_page=1', 'OpenAlex API'),
    ]

    for url, desc in test_urls:
        print(f'\n  Testing: {desc}')
        print(f'  URL: {url}')

        # Determine if should use proxy
        HttpClientFactory.reset()
        HttpClientFactory.configure(proxy_url=proxy_url, no_proxy=no_proxy)

        use_proxy = HttpClientFactory.should_use_proxy(url)
        print(f'  Proxy decision: {"Use Proxy" if use_proxy else "Direct"}')

        try:
            if use_proxy and proxy_url:
                async with httpx.AsyncClient(proxy=proxy_url, timeout=30.0) as client:
                    response = await client.get(url)
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url)

            print(f'  Status: {response.status_code}')
            print(f'  Result: {"SUCCESS" if response.status_code == 200 else "FAILED"}')
        except Exception as e:
            print(f'  Result: FAILED - {e}')


def main():
    parser = argparse.ArgumentParser(description='Test proxy configuration')
    parser.add_argument('--proxy', type=str, help='Proxy URL (e.g., http://proxy:8080)')
    parser.add_argument('--no-proxy', type=str, help='No proxy patterns (e.g., localhost,*.internal.com)')
    parser.add_argument('--live', action='store_true', help='Run live network tests')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Proxy Configuration Test Suite")
    print("=" * 60)

    if args.proxy:
        print(f"\nProxy URL: {args.proxy}")
    if args.no_proxy:
        print(f"No Proxy: {args.no_proxy}")

    # Run unit tests
    results = []
    results.append(('no_proxy matching', test_no_proxy_matching()))
    results.append(('OpenAlex client', test_openalex_client()))

    # Run live tests if requested
    if args.live:
        asyncio.run(test_actual_connection(args.proxy, args.no_proxy))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, passed in results:
        status = 'PASS' if passed else 'FAIL'
        print(f'  [{status}] {name}')

    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'All tests passed!' if all_passed else 'Some tests failed.'}")
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
