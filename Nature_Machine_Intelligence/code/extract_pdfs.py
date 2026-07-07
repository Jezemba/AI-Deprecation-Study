#!/usr/bin/env python3
"""
PDF Text Extraction using Docling

Extracts text from PDFs using IBM's Docling library with parallel processing.
Handles tables better than GROBID and outputs clean ASCII-readable text.

Usage:
    python extract_pdfs.py [input_dir] [output_dir] [--workers N] [--device cpu|cuda]

Default paths:
    input:  ./pdfs
    output: ./markdown
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional
import multiprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global converter (initialized once per process)
_converter = None
_worker_id = None


def get_default_paths():
    """Return default input/output paths."""
    return {
        'input': os.path.join(os.getcwd(), 'pdfs'),
        'output': os.path.join(os.getcwd(), 'markdown')
    }


def init_worker_cpu():
    """Initialize the converter once per worker process (CPU mode)."""
    global _converter

    import time
    import random

    # Stagger worker initialization to avoid all workers loading models at once
    # This prevents memory spikes that can crash the process pool
    time.sleep(random.uniform(0, 5))

    # Force CPU usage
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

    # Import here to avoid issues with multiprocessing
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions

    # Create pipeline options for academic papers - CPU mode
    pipeline_options = PdfPipelineOptions(
        do_ocr=False,  # Assume text PDFs, faster processing
        do_table_structure=True,  # Enable table extraction
        accelerator_options=AcceleratorOptions(
            num_threads=4,  # Threads per worker
            device="cpu"
        )
    )

    # Create converter with optimized settings
    _converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )


def init_worker_gpu(gpu_id: int, num_gpus: int):
    """Initialize the converter once per worker process (GPU mode)."""
    global _converter, _worker_id

    # Get worker ID from process name or use provided gpu_id
    worker_pid = os.getpid()
    _worker_id = worker_pid % num_gpus

    # Set which GPU this worker should use
    os.environ['CUDA_VISIBLE_DEVICES'] = str(_worker_id)

    # Import here to avoid issues with multiprocessing
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions

    # Create pipeline options for academic papers - GPU mode
    pipeline_options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        accelerator_options=AcceleratorOptions(
            num_threads=4,
            device="cuda"
        )
    )

    # Create converter with optimized settings
    _converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )


def find_pdf_files(
    input_dir: str,
    output_dir: str = None,
    exclude_pattern: str = 'IDETC',
    resume: bool = False
) -> tuple:
    """
    Recursively find all PDF files in directory, excluding specified pattern.
    Optionally skip files that have already been processed (resume mode).

    Args:
        input_dir: Directory to search
        output_dir: Output directory (needed for resume mode)
        exclude_pattern: Pattern to exclude (default: 'IDETC' to ignore IDETC papers)
        resume: If True, skip PDFs that already have output files

    Returns:
        Tuple of (list of PDF file paths to process, count of skipped files)
    """
    pdf_files = []
    skipped = 0
    input_path = Path(input_dir)

    for pdf_file in input_path.rglob('*.pdf'):
        # Skip files containing exclude pattern in path
        if exclude_pattern and exclude_pattern.lower() in str(pdf_file).lower():
            continue

        # Check if output already exists (resume mode)
        if resume and output_dir:
            rel_path = os.path.relpath(str(pdf_file), input_dir)
            output_path = os.path.join(output_dir, rel_path.replace('.pdf', '.md'))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                skipped += 1
                continue

        pdf_files.append(str(pdf_file))

    return sorted(pdf_files), skipped


def extract_single_pdf(args: tuple) -> dict:
    """
    Extract text from a single PDF file.

    Args:
        args: Tuple of (pdf_path, output_dir, input_base_dir)

    Returns:
        Dictionary with extraction results
    """
    global _converter
    pdf_path, output_dir, input_base_dir = args

    result = {
        'input_file': pdf_path,
        'output_file': None,
        'success': False,
        'error': None,
        'text_length': 0,
        'num_tables': 0
    }

    try:
        # Convert PDF using the pre-initialized converter
        doc_result = _converter.convert(pdf_path)

        # Export to markdown (preserves tables nicely in ASCII)
        markdown_text = doc_result.document.export_to_markdown()

        # Create output path preserving directory structure
        rel_path = os.path.relpath(pdf_path, input_base_dir)
        output_path = os.path.join(output_dir, rel_path.replace('.pdf', '.md'))

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        # Count tables in document
        num_tables = len(list(doc_result.document.tables)) if hasattr(doc_result.document, 'tables') else 0

        result['output_file'] = output_path
        result['success'] = True
        result['text_length'] = len(markdown_text)
        result['num_tables'] = num_tables

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error processing {pdf_path}: {e}")

    return result


def extract_pdfs_parallel(
    input_dir: str,
    output_dir: str,
    num_workers: int = None,
    exclude_pattern: str = 'IDETC',
    device: str = 'cpu',
    resume: bool = False
) -> dict:
    """
    Extract text from all PDFs in directory using parallel processing.

    Args:
        input_dir: Directory containing PDFs
        output_dir: Directory for output files
        num_workers: Number of parallel workers (default: CPU count for cpu, 4 for gpu)
        exclude_pattern: Pattern to exclude from processing
        device: 'cpu' or 'cuda' for processing
        resume: If True, skip files that have already been processed

    Returns:
        Dictionary with processing statistics
    """
    # Set default workers based on device and available memory
    # Each worker uses ~1-2GB RAM, so limit to avoid OOM
    if num_workers is None:
        if device == 'cpu':
            # Conservative default: 8 workers (~8-16GB RAM)
            # Prevents crashes from simultaneous model loading
            # User can override with --workers flag
            num_workers = min(8, multiprocessing.cpu_count())
        else:
            # For GPU, limit workers to avoid OOM (2 workers per GPU typical)
            num_workers = 4  # 2 workers per GPU for 2 GPUs

    # Find all PDFs (with resume support)
    logger.info(f"Searching for PDFs in: {input_dir}")
    pdf_files, skipped = find_pdf_files(input_dir, output_dir, exclude_pattern, resume)
    total_files = len(pdf_files)

    if skipped > 0:
        logger.info(f"Resume mode: Skipping {skipped} already-processed files")

    if total_files == 0:
        logger.warning("No PDF files found!")
        return {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'total_text_length': 0,
            'total_tables': 0,
            'errors': [],
            'start_time': datetime.now().isoformat(),
            'end_time': datetime.now().isoformat(),
            'files': []
        }

    logger.info(f"Found {total_files} PDF files (excluding {exclude_pattern})")
    logger.info(f"Using {num_workers} workers on {device.upper()}")
    logger.info(f"Output directory: {output_dir}")

    # Prepare arguments for parallel processing
    args_list = [(pdf, output_dir, input_dir) for pdf in pdf_files]

    # Track results
    results = {
        'total_files': total_files,
        'successful': 0,
        'failed': 0,
        'total_text_length': 0,
        'total_tables': 0,
        'errors': [],
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'files': []
    }

    # Select initializer based on device
    if device == 'cpu':
        initializer = init_worker_cpu
        initargs = ()
    else:
        # Count available GPUs
        try:
            import torch
            num_gpus = torch.cuda.device_count()
        except:
            num_gpus = 2  # Default assumption
        initializer = lambda: init_worker_gpu(0, num_gpus)
        initargs = ()

    # Process in parallel with worker initialization
    # Use a timeout per PDF to prevent hung workers
    PDF_TIMEOUT = 300  # 5 minutes max per PDF

    with ProcessPoolExecutor(
        max_workers=num_workers,
        initializer=initializer,
        initargs=initargs
    ) as executor:
        futures = {executor.submit(extract_single_pdf, args): args[0] for args in args_list}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            pdf_path = futures[future]

            try:
                result = future.result(timeout=PDF_TIMEOUT)
                results['files'].append(result)

                if result['success']:
                    results['successful'] += 1
                    results['total_text_length'] += result['text_length']
                    results['total_tables'] += result['num_tables']
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': pdf_path,
                        'error': result['error']
                    })

                # Progress update every 100 files or at completion
                if completed % 100 == 0 or completed == total_files:
                    pct = 100 * completed / total_files
                    logger.info(f"Progress: {completed}/{total_files} ({pct:.1f}%) - Success: {results['successful']}, Failed: {results['failed']}")

            except TimeoutError:
                results['failed'] += 1
                results['errors'].append({
                    'file': pdf_path,
                    'error': f'Timeout after {PDF_TIMEOUT} seconds'
                })
                logger.error(f"Timeout processing {pdf_path}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'file': pdf_path,
                    'error': str(e)
                })
                logger.error(f"Failed to get result for {pdf_path}: {e}")

    results['end_time'] = datetime.now().isoformat()

    return results


def save_report(results: dict, output_dir: str):
    """Save extraction report to JSON and text files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save detailed JSON report (without individual file details to save space)
    json_path = os.path.join(output_dir, f'extraction_report_{timestamp}.json')

    # Create a summary version for JSON (full file list can be huge)
    summary_results = {k: v for k, v in results.items() if k != 'files'}
    summary_results['sample_files'] = results['files'][:100] if results['files'] else []

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_results, f, indent=2)
    logger.info(f"JSON report saved to: {json_path}")

    # Save summary text report
    txt_path = os.path.join(output_dir, f'extraction_summary_{timestamp}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("DOCLING PDF EXTRACTION SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Start time: {results['start_time']}\n")
        f.write(f"End time: {results['end_time']}\n\n")
        f.write(f"Total files: {results['total_files']}\n")
        f.write(f"Successful: {results['successful']}\n")
        f.write(f"Failed: {results['failed']}\n")

        if results['total_files'] > 0:
            f.write(f"Success rate: {100*results['successful']/results['total_files']:.1f}%\n\n")

        f.write(f"Total text extracted: {results['total_text_length']:,} characters\n")
        f.write(f"Total tables found: {results['total_tables']}\n\n")

        if results['errors']:
            f.write("=" * 60 + "\n")
            f.write(f"ERRORS ({len(results['errors'])})\n")
            f.write("=" * 60 + "\n\n")
            for err in results['errors'][:50]:  # Limit to first 50 errors
                f.write(f"File: {err['file']}\n")
                f.write(f"Error: {err['error']}\n\n")
            if len(results['errors']) > 50:
                f.write(f"... and {len(results['errors']) - 50} more errors\n")

    logger.info(f"Summary report saved to: {txt_path}")

    # Save full file list to separate file
    files_path = os.path.join(output_dir, f'extraction_files_{timestamp}.json')
    with open(files_path, 'w', encoding='utf-8') as f:
        json.dump(results['files'], f)
    logger.info(f"Full file list saved to: {files_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract text from PDFs using Docling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    defaults = get_default_paths()

    parser.add_argument(
        'input_dir',
        nargs='?',
        default=defaults['input'],
        help=f"Input directory containing PDFs (default: {defaults['input']})"
    )
    parser.add_argument(
        'output_dir',
        nargs='?',
        default=defaults['output'],
        help=f"Output directory for extracted text (default: {defaults['output']})"
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help="Number of parallel workers (default: 8 for CPU, 4 for GPU). Each worker uses ~1-2GB RAM."
    )
    parser.add_argument(
        '--exclude', '-e',
        type=str,
        default='IDETC',
        help="Pattern to exclude from processing (default: IDETC)"
    )
    parser.add_argument(
        '--no-exclude',
        action='store_true',
        help="Process all files without exclusion"
    )
    parser.add_argument(
        '--device', '-d',
        type=str,
        choices=['cpu', 'cuda'],
        default='cpu',
        help="Device to use: 'cpu' (default, recommended for large batches) or 'cuda'"
    )
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help="Resume from previous run, skipping already-processed files"
    )

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Set exclusion pattern
    exclude_pattern = None if args.no_exclude else args.exclude

    # Determine workers
    if args.workers is None:
        workers = min(8, multiprocessing.cpu_count()) if args.device == 'cpu' else 4
    else:
        workers = args.workers

    print("=" * 60)
    print("DOCLING PDF TEXT EXTRACTION")
    print("=" * 60)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Device: {args.device.upper()}")
    print(f"Workers: {workers}")
    print(f"Excluding: {exclude_pattern or 'None'}")
    print(f"Resume mode: {'Yes' if args.resume else 'No'}")
    print("=" * 60)

    # Run extraction
    results = extract_pdfs_parallel(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        num_workers=workers,
        exclude_pattern=exclude_pattern,
        device=args.device,
        resume=args.resume
    )

    # Save reports
    save_report(results, args.output_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Successful: {results['successful']}/{results['total_files']}")
    print(f"Failed: {results['failed']}")
    print(f"Total text: {results['total_text_length']:,} characters")
    print(f"Tables found: {results['total_tables']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
