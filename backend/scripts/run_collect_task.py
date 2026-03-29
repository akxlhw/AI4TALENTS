#!/usr/bin/env python
"""
Standalone script to run a collection task.

Usage: python scripts/run_collect_task.py <task_id>

This script is designed to be run in a separate subprocess to avoid
issues with asyncio event loops and database connections on Windows.
"""
import asyncio
import sys
import os
import signal

# Add backend directory to Python path
# Script is at: backend/scripts/run_collect_task.py
# We need backend/ in path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
sys.path.insert(0, backend_dir)

# Change working directory to backend
os.chdir(backend_dir)

# Ensure UTF-8 encoding on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')


def signal_handler(sig, frame):
    """Handle interrupt signals gracefully."""
    print("\n[INFO] Received interrupt signal, shutting down...")
    sys.exit(1)


async def run_task(task_id: int):
    """Run the collection task."""
    # Import here to ensure clean environment
    from app.core.database import AsyncSessionLocal
    from app.services.collect.orchestrator import CollectionOrchestrator
    from app.services.data_fetchers import WorkFetcher, AuthorFetcher, InstitutionFetcher

    print(f"[INFO] Starting task {task_id}")
    sys.stdout.flush()

    async with AsyncSessionLocal() as session:
        # Initialize fetchers
        work_fetcher = WorkFetcher(session)
        author_fetcher = AuthorFetcher(session)
        institution_fetcher = InstitutionFetcher(session)

        # Create orchestrator
        orchestrator = CollectionOrchestrator(
            session,
            work_fetcher=work_fetcher,
            author_fetcher=author_fetcher,
            institution_fetcher=institution_fetcher
        )

        # Execute task
        progress = await orchestrator.execute_task(task_id)

        print(f"[INFO] Task {task_id} completed with status: {progress.status}")
        print(f"[INFO] Works: {progress.total_works:,}")
        print(f"[INFO] Authors: {progress.total_authors:,}")
        print(f"[INFO] Normalized: {progress.normalized_authors:,}")
        print(f"[INFO] Synced: {progress.synced_authors:,}")
        print(f"[INFO] Tech Tags: {progress.created_tech_tags:,}")

        if progress.errors:
            print(f"[WARN] Errors: {len(progress.errors)}")
            for err in progress.errors[:5]:
                print(f"  - {err}")

        sys.stdout.flush()
        return progress


def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get task ID from command line
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_collect_task.py <task_id>")
        sys.exit(1)

    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid task ID '{sys.argv[1]}'")
        sys.exit(1)

    print(f"[INFO] Run collect task script started for task {task_id}")
    print(f"[INFO] Working directory: {os.getcwd()}")
    sys.stdout.flush()

    # Run the async task
    try:
        # On Windows, use ProactorEventLoop for better compatibility
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        progress = asyncio.run(run_task(task_id))

        if progress.status == "completed":
            print(f"[INFO] Task {task_id} completed successfully!")
            sys.exit(0)
        else:
            print(f"[ERROR] Task {task_id} failed with status: {progress.status}")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Exception running task {task_id}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
