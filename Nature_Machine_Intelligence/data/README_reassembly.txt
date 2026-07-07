NMI supplementary materials, 2022-2025

Contents
- manifest.csv / manifest.json: one row per downloaded supplementary asset. Use is_code and category to distinguish code/software from other supplementary material.
- article_inventory.csv: one row per Nature Machine Intelligence article page checked.
- code_inventory.csv: subset of manifest.csv where is_code is True.
- chunk_manifest.csv: one row per uploaded archive chunk, including chunk size and SHA-256 checksums.
- NMI_code_only_2022_2025.zip parts: ZIP containing only the 13 code/software supplementary assets.
- NMI_supplementary_materials_YYYY.zip parts: ZIP containing all downloaded supplementary assets for that year.

Why split archives
The Drive connector used for this upload has a 100 MiB per-file limit, so each ZIP was split into 95 MiB parts.

Reassembly
Download all parts for an archive folder, keep their filenames unchanged, then concatenate them in filename order.

macOS/Linux example:
  cat NMI_supplementary_materials_2025.zip.part* > NMI_supplementary_materials_2025.zip

Windows PowerShell example:
  Get-Content -Encoding Byte NMI_supplementary_materials_2025.zip.part* -ReadCount 0 | Set-Content -Encoding Byte NMI_supplementary_materials_2025.zip

Verification
Compare the SHA-256 of the rebuilt ZIP with archive_sha256 in chunk_manifest.csv.

Scope
- Journal: Nature Machine Intelligence
- Years covered: 2022, 2023, 2024, 2025
- Article pages checked: 727
- Supplementary assets downloaded: 1,727
- Assets classified as code/software: 13
