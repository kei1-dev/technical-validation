#!/usr/bin/env python3
"""
Terakoya Invoice Automation Script.

This script automates monthly invoice submission for Terakoya lessons.

Usage:
    python run_terakoya.py --month 2025-10 --password PASSWORD [--dry-run] [--headless]

Examples:
    # Submit invoice for October 2025
    python run_terakoya.py --month 2025-10 --password "your_password"

    # Dry run (no actual submission)
    python run_terakoya.py --month 2025-10 --password "your_password" --dry-run

    # Run in headless mode
    python run_terakoya.py --month 2025-10 --password "your_password" --headless

    # Use password from environment variable
    export TERAKOYA_PASSWORD="your_password"
    python run_terakoya.py --month 2025-10
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from src.automation.browser import Browser
from src.automation.browser_config import BrowserConfig
from src.automation.terakoya.client import TerakoyaClient
from src.models.lesson import LessonData
from src.models.invoice import InvoiceResult, InvoiceSummary
from src.utils.config import config, SecureString
from src.utils.logger import setup_logger
from src.utils.file_utils import save_json, save_csv


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Automate Terakoya invoice submission",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--month",
        required=True,
        help="Target month in YYYY-MM format (e.g., 2025-10)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actual submission"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    parser.add_argument(
        "--password",
        help="Terakoya login password (overrides TERAKOYA_PASSWORD env var)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    return parser.parse_args()


def parse_target_month(month_str: str) -> tuple:
    """
    Parse month string to (year, month).

    Args:
        month_str: Month string in YYYY-MM format

    Returns:
        Tuple of (year, month)

    Raises:
        ValueError: If format is invalid
    """
    try:
        year, month = month_str.split("-")
        year = int(year)
        month = int(month)

        if not (1 <= month <= 12):
            raise ValueError("Month must be between 1 and 12")

        if year < 2020 or year > 2100:
            raise ValueError("Year must be between 2020 and 2100")

        return year, month

    except Exception as e:
        raise ValueError(f"Invalid month format '{month_str}': {e}")


def display_summary(
    lessons: List[LessonData],
    existing_invoices: List[dict],
    to_add: List[LessonData]
):
    """
    Display summary of lessons and invoices.

    Args:
        lessons: All lessons retrieved
        existing_invoices: Existing invoices
        to_add: Lessons to be added as invoices
    """
    print("\n" + "=" * 60)
    print("INVOICE SUMMARY")
    print("=" * 60)
    print(f"Total lessons found:      {len(lessons)}")
    print(f"Already invoiced:         {len(existing_invoices)}")
    print(f"To be added:              {len(to_add)}")
    print(f"Duplicate/skipped:        {len(lessons) - len(to_add) - len(existing_invoices)}")
    print("=" * 60)

    if to_add:
        print("\nLessons to be invoiced:")
        print("-" * 60)
        for idx, lesson in enumerate(to_add, 1):
            print(
                f"{idx:2d}. {lesson['date']} | {lesson['student_name']:20s} | "
                f"{lesson['duration']:3d}min | {lesson['category']}"
            )
        print("-" * 60)


def confirm_submission() -> bool:
    """
    Ask user to confirm invoice submission.

    Returns:
        True if user confirms
    """
    print("\n" + "=" * 60)
    response = input("Submit invoice? (y/n): ").strip().lower()
    return response in ['y', 'yes']


def save_execution_report(
    year: int,
    month: int,
    lessons: List[LessonData],
    existing_invoices: List[dict],
    added: List[LessonData],
    failed: List[tuple],
    submitted: bool,
    dry_run: bool
):
    """
    Save execution report.

    Args:
        year: Target year
        month: Target month
        lessons: All lessons
        existing_invoices: Existing invoices
        added: Successfully added lessons
        failed: Failed lessons with error messages
        submitted: Whether invoice was submitted
        dry_run: Whether this was a dry run
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output/terakoya_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create report data
    report = {
        "timestamp": timestamp,
        "target_month": f"{year}-{month:02d}",
        "dry_run": dry_run,
        "summary": {
            "total_lessons": len(lessons),
            "existing_invoices": len(existing_invoices),
            "added": len(added),
            "failed": len(failed),
            "submitted": submitted
        },
        "added_lessons": added,
        "failed_lessons": [
            {"lesson": lesson, "error": error}
            for lesson, error in failed
        ]
    }

    # Save JSON report
    json_path = output_dir / f"invoice_report_{year}{month:02d}_{timestamp}.json"
    save_json(report, json_path)
    print(f"\nReport saved to: {json_path}")

    # Save CSV for added lessons
    if added:
        import pandas as pd
        csv_path = output_dir / f"invoice_items_{year}{month:02d}_{timestamp}.csv"
        save_csv(pd.DataFrame(added), csv_path)
        print(f"Invoice items saved to: {csv_path}")


def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logger = setup_logger(
        "terakoya_automation",
        level=getattr(logging, args.log_level)
    )

    try:
        # Parse target month
        year, month = parse_target_month(args.month)
        logger.info(f"Target month: {year}-{month:02d}")

        if args.dry_run:
            logger.info("DRY RUN MODE - No actual submission will occur")
            print("\n*** DRY RUN MODE ***\n")

        # Validate configuration
        logger.info("Validating configuration")
        config.validate()

        # Create browser configuration
        browser_config = BrowserConfig(
            headless=args.headless or config.browser_headless,
            timeout=config.browser_timeout
        )

        # Initialize browser
        logger.info("Initializing browser")
        browser = Browser(config=browser_config)

        try:
            # Initialize Terakoya client
            logger.info("Initializing Terakoya client")
            client = TerakoyaClient(
                browser=browser,
                base_url=config.terakoya_url
            )

            # Determine password (command-line arg takes precedence)
            if args.password:
                password = SecureString(args.password)
                logger.info("Using password from command-line argument")
            elif config._terakoya_password:
                password = config.terakoya_password
                logger.info("Using password from environment variable")
            else:
                logger.error("Password not provided")
                print("ERROR: Password is required. Use --password or set TERAKOYA_PASSWORD")
                return 1

            # Step 1: Login
            print("\n[1/6] Logging in to Terakoya...")
            login_result = client.login(
                email=config.terakoya_email,
                password=password
            )

            if login_result.is_failure:
                logger.error(f"Login failed: {login_result.message}")
                print(f"ERROR: Login failed - {login_result.message}")
                return 1

            print("✓ Login successful")

            # Step 2: Get lessons for month
            print(f"\n[2/6] Retrieving lessons for {year}-{month:02d}...")
            lessons_result = client.get_lessons_for_month(year, month)

            if lessons_result.is_failure:
                logger.error(f"Failed to get lessons: {lessons_result.message}")
                print(f"ERROR: Failed to get lessons - {lessons_result.message}")
                return 1

            lessons = lessons_result.value
            print(f"✓ Retrieved {len(lessons)} lessons")

            if not lessons:
                print("\nNo lessons found for this month.")
                logger.info("No lessons found, exiting")
                return 0

            # Step 3: Navigate to invoice page
            print(f"\n[3/6] Navigating to invoice page...")
            nav_result = client.navigate_to_invoice_page(year, month)

            if nav_result.is_failure:
                logger.error(f"Navigation failed: {nav_result.message}")
                print(f"ERROR: Navigation failed - {nav_result.message}")
                return 1

            print("✓ Navigation successful")

            # Step 4: Get existing invoices
            print(f"\n[4/6] Checking for existing invoices...")
            existing_result = client.get_existing_invoices()

            existing_invoices = []
            if existing_result.is_success:
                existing_invoices = existing_result.value
                print(f"✓ Found {len(existing_invoices)} existing invoices")
            else:
                print("✓ No existing invoices found")

            # Filter out duplicates
            to_add = [
                lesson for lesson in lessons
                if not client.is_duplicate(lesson, existing_invoices)
            ]

            # Display summary
            display_summary(lessons, existing_invoices, to_add)

            if not to_add:
                print("\nAll lessons are already invoiced. Nothing to add.")
                logger.info("No new lessons to invoice")
                return 0

            # Step 5: Add invoice items
            added_lessons = []
            failed_lessons = []

            # Add items (dry run mode fills forms but doesn't save)
            mode_label = "DRY RUN - Testing" if args.dry_run else "Adding"
            print(f"\n[5/6] {mode_label} {len(to_add)} invoice items...")

            for idx, lesson in enumerate(to_add, 1):
                action = "Testing" if args.dry_run else "Adding"
                print(f"  [{idx}/{len(to_add)}] {action}: {lesson['date']} - {lesson['student_name']}")

                add_result = client.add_invoice_item_with_retry(
                    lesson=lesson,
                    unit_price=config.lesson_unit_price,
                    max_retries=3,
                    dry_run=args.dry_run
                )

                if add_result.is_success:
                    added_lessons.append(lesson)
                    status = "✓ Form filled (not saved)" if args.dry_run else "✓ Added successfully"
                    print(f"      {status}")
                else:
                    failed_lessons.append((lesson, add_result.message))
                    print(f"      ✗ Failed: {add_result.message}")
                    logger.error(f"Failed to add lesson: {add_result.message}")

            summary = f"✓ Tested {len(added_lessons)} items (dry run)" if args.dry_run else f"✓ Added {len(added_lessons)} items"
            print(f"\n{summary}")
            if failed_lessons:
                print(f"✗ Failed to process {len(failed_lessons)} items")

            # Step 6: Submission
            submitted = False
            if args.dry_run:
                print("\n[6/6] DRY RUN - Skipping submission")
                logger.info("Dry run mode, skipping submission")

            # Save execution report
            save_execution_report(
                year=year,
                month=month,
                lessons=lessons,
                existing_invoices=existing_invoices,
                added=added_lessons,
                failed=failed_lessons,
                submitted=submitted,
                dry_run=args.dry_run
            )

            print("\n" + "=" * 60)
            print("EXECUTION COMPLETE")
            print("=" * 60)

            return 0 if not failed_lessons else 1

        finally:
            # Close browser
            logger.info("Closing browser")
            browser.close()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        logger.info("Interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
