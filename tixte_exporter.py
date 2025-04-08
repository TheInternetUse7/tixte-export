import argparse
import csv
import os
import random
import sys
import time
import json
import glob
import requests
from rich.progress import Progress, TaskID
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.align import Align

LOG_FILE = "downloaded.log"
DETAILED_LOG_FILE = "detailed.log"
CONFIG_FILE = "config.json"

def log_to_file(message):
    """Write to detailed log file"""
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    log_message = f"{timestamp} {message}"

    # Write to log file
    with open(DETAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

def parse_args():
    parser = argparse.ArgumentParser(description="Export all files from Tixte using uploads.csv")
    parser.add_argument("--csv", default="data/uploads.csv", help="Path to uploads CSV file")
    parser.add_argument("--output", default="exported_files", help="Directory to save downloaded files")
    parser.add_argument("--delay", type=float, default=1.0, help="Base delay between downloads (seconds)")
    parser.add_argument("--jitter", type=float, default=0.5, help="Max random jitter added to delay (seconds)")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum retries per file")
    parser.add_argument("--user-agent", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", help="Custom User-Agent string")
    parser.add_argument("--dry-run", action="store_true", help="List files without downloading")
    return parser.parse_args()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in config file.")
            return {}

def load_downloaded(output_dir):
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        # Convert all paths to use the current output directory
        downloaded_files = set()
        for line in f:
            if line.strip():
                # Extract just the filename from the path
                _, filename = os.path.split(line.strip())
                # Create a new path with the current output directory
                downloaded_files.add(os.path.join(output_dir, filename))
        return downloaded_files

def save_downloaded(file_path):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(file_path + "\n")

def construct_url(subdomain, filename, extension):
    return f"https://us-east-1.tixte.net/uploads/{subdomain}/{filename}.{extension}"

def file_exists_in_directory(directory, filename):
    # Recursively search for filename in directory
    pattern = os.path.join(directory, '**', filename)
    matches = glob.glob(pattern, recursive=True)
    return len(matches) > 0

def human_readable_speed(bytes_per_sec):
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.2f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.2f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

def download_file(url, save_path, headers, max_retries, base_delay, jitter, progress: Progress, task_id: TaskID, filename: str):
    attempt = 0
    final_speed = 0

    log_to_file(f"\nAttempting to download: {url}")
    log_to_file(f"Saving to: {save_path}")
    log_to_file(f"User-Agent: {headers.get('User-Agent', 'Not specified')}")

    while attempt <= max_retries:
        try:
            log_to_file(f"Download attempt {attempt+1}/{max_retries+1}...")

            response = requests.get(url, headers=headers, stream=True, timeout=30)
            if response.status_code == 200:
                content_length = int(response.headers.get('content-length', 0))
                log_to_file(f"Connection established. Content length: {content_length} bytes")

                start_time = time.time()
                bytes_downloaded = 0
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = bytes_downloaded / elapsed
                            final_speed = speed
                            speed_str = human_readable_speed(speed)
                            progress.update(task_id, description=f"Downloading {filename} @ {speed_str}")

                            if bytes_downloaded % (1024*1024) < 8192:  # Log approximately every 1MB
                                log_to_file(f"Progress: {bytes_downloaded} bytes @ {speed_str}")

                total_time = time.time() - start_time
                log_to_file(f"Downloaded: {save_path}")
                log_to_file(f"Total size: {bytes_downloaded} bytes")
                log_to_file(f"Time taken: {total_time:.2f} seconds")
                log_to_file(f"Average speed: {human_readable_speed(bytes_downloaded/total_time if total_time > 0 else 0)}")

                return True, final_speed
            else:
                log_to_file(f"Failed ({response.status_code}): {url}")
                log_to_file(f"Response headers: {dict(response.headers)}")
                log_to_file(f"Response content: {response.text[:500]}..." if len(response.text) > 500 else response.text)
        except requests.exceptions.RequestException as e:
            log_to_file(f"Request error downloading {url}: {e}")
        except Exception as e:
            log_to_file(f"Unexpected error downloading {url}: {e}")
            import traceback
            error_trace = traceback.format_exc()
            log_to_file(f"Traceback: {error_trace}")

        attempt += 1
        if attempt <= max_retries:
            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            log_to_file(f"Retrying in {sleep_time:.2f}s... (attempt {attempt+1}/{max_retries+1})")
            time.sleep(sleep_time)

    log_to_file(f"Failed to download after {max_retries+1} attempts: {url}")

    return False, 0

def main():
    args = parse_args()
    config = load_config()
    headers = {"User-Agent": args.user_agent}

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Load downloaded files with the current output directory
    downloaded = load_downloaded(args.output)

    console = Console()

    # Clear detailed log file at the start of each run
    if os.path.exists(DETAILED_LOG_FILE):
        os.remove(DETAILED_LOG_FILE)

    # Log command line arguments
    log_to_file("[Command line arguments]")
    for arg, value in vars(args).items():
        log_to_file(f"  {arg}: {value}")
    log_to_file("")

    # Log output directory
    log_to_file(f"Output directory: {os.path.abspath(args.output)}")
    console.print(f"[bold]Output directory:[/bold] {os.path.abspath(args.output)}")

    # Load CSV
    try:
        with open(args.csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
        console.print(f"[bold]Loaded CSV:[/bold] {args.csv} with {len(rows)} files")
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] CSV file not found: {args.csv}")
        console.print(f"Please check the path and try again.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error loading CSV:[/bold red] {e}")
        sys.exit(1)

    local_check_dir = config.get("local_check_dir")
    default_subdomain = config.get("subdomain")

    # Counters for summary
    total_files = len(rows)
    downloaded_count = 0
    skipped_logged = 0
    skipped_exists_output = 0
    skipped_exists_local = 0
    skipped_dry_run = 0

    # Log message buffer
    log_messages = []

    def add_log(message):
        timestamp = time.strftime("[%H:%M:%S]")
        log_entry = f"{timestamp} {message}"
        log_messages.append(log_entry)
        # Keep only last 20 logs
        if len(log_messages) > 20:
            log_messages.pop(0)

        # Also log to detailed log file
        log_to_file(message)

        return log_entry

    progress = Progress()
    task = progress.add_task("Processing files", total=total_files)

    try:
        # Use Live display for progress
        console.print("\n[bold]Starting download process...[/bold]")
        console.print(f"Total files to process: {total_files}")
        log_to_file(f"Starting download process with {total_files} files")

        # Initialize the live display
        live = Live(console=console, refresh_per_second=10)
        live.start()

        # Process each file
        for row in rows:
            filename = row['Filename']
            extension = row['Extension']
            subdomain = row.get('Subdomain') or default_subdomain or ''
            save_name = f"{filename}.{extension}"
            save_path = os.path.join(args.output, save_name)

            # Make sure the output directory exists (in case it's a nested path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Check if already logged as downloaded
            if save_path in downloaded:
                add_log(f"[yellow]⚠️ Skipped (already downloaded):[/yellow] {save_name}")
                skipped_logged += 1
                progress.update(task, advance=1)
                continue

            # Check if file exists in output directory
            if os.path.exists(save_path):
                add_log(f"[yellow]⚠️ Skipped (exists in output):[/yellow] {save_name}")
                skipped_exists_output += 1
                progress.update(task, advance=1)
                continue

            # Check if file exists in optional local directory recursively
            if local_check_dir and file_exists_in_directory(local_check_dir, save_name):
                add_log(f"[cyan]ℹ️ Skipped (found in local dir):[/cyan] {save_name}")
                skipped_exists_local += 1
                progress.update(task, advance=1)
                continue

            # Dry run mode
            if args.dry_run:
                add_log(f"[magenta]🚫 Dry run, skipping download:[/magenta] {save_name}")
                log_to_file(f"Dry run: Would download {construct_url(subdomain, filename, extension)} to {save_path}")
                skipped_dry_run += 1
                progress.update(task, advance=1)
                continue

            # Actually download the file
            file_task_id = progress.add_task(f"Downloading {save_name}", total=None)
            success, download_speed = download_file(
                construct_url(subdomain, filename, extension),
                save_path,
                headers,
                args.max_retries,
                args.delay,
                args.jitter,

                progress,
                file_task_id,
                save_name
            )
            progress.remove_task(file_task_id)
            if success:
                downloaded_count += 1
                save_downloaded(save_path)
                speed_str = human_readable_speed(download_speed)
                add_log(f"[green]✅ Downloaded successfully:[/green] {save_name} @ {speed_str}")
            else:
                add_log(f"[red]❌ Failed after retries:[/red] {save_name}")

            delay_time = args.delay + random.uniform(0, args.jitter)
            time.sleep(delay_time)
            progress.update(task, advance=1)

            # Update live display after each file
            log_table = Table.grid()
            for msg in log_messages:
                log_table.add_row(msg)

            live.update(
                Group(
                    Align.left(log_table),
                    Align.left(progress.get_renderable())
                )
            )

    except KeyboardInterrupt:
        console.print("\n[red]Download interrupted by user. Progress saved.[/red]")
        sys.exit(0)

    # Summary
    console.print("\n[bold green]Download Summary:[/bold green]")
    console.print(f"CSV file: {args.csv}")
    console.print(f"Output directory: {os.path.abspath(args.output)}")
    console.print(f"Dry run mode: {'Yes' if args.dry_run else 'No'}")
    console.print(f"\nTotal files processed: {total_files}")
    console.print(f"[green]✅ Downloaded successfully:[/green] {downloaded_count}")
    console.print(f"[yellow]⚠️ Skipped (already downloaded):[/yellow] {skipped_logged}")
    console.print(f"[yellow]⚠️ Skipped (exists in output):[/yellow] {skipped_exists_output}")
    console.print(f"[cyan]ℹ️ Skipped (found in local dir):[/cyan] {skipped_exists_local}")
    console.print(f"[magenta]🚫 Skipped (dry run):[/magenta] {skipped_dry_run}")

    # Print help message if no files were downloaded
    if downloaded_count == 0 and not args.dry_run:
        console.print("\n[yellow]No files were downloaded. Possible reasons:[/yellow]")
        console.print("  - All files were already downloaded")
        console.print("  - Files exist in the output directory")
        console.print("  - Files exist in the local check directory")
        console.print("  - There might be an issue with the CSV file or subdomain configuration")
        console.print("\nCheck the detailed log file for more information.")

    # Show detailed log file location
    console.print(f"\n[blue]Detailed log has been saved to:[/blue] {os.path.abspath(DETAILED_LOG_FILE)}")

if __name__ == "__main__":
    main()
