# Golden Files

This directory contains "golden" reference files for integration tests. These files represent the expected output of the full pipeline when run with a fixed random seed (42).

## Purpose

The integration test (`test_full_pipeline.py`) runs the complete pipeline:
1. `init-sample` - Generate sample notes
2. `ingest` - Ingest notes into the database
3. `preprocess` - Preprocess notes into segments
4. `analyze` - Analyze themes using KMeans clustering
5. `extract` - Extract structured information
6. `generate` - Generate modules from templates
7. `export` - Export knowledge base

The test compares generated Markdown files against these golden files to ensure:
- The pipeline produces consistent, reproducible results
- Changes to the codebase don't break expected outputs
- Random seeds are properly set (KMeans uses `random_state=42`)

## First Run

On the first run, if golden files don't exist, the test will:
1. Generate the files
2. Save them to this directory
3. Skip the comparison (with a message)

Run the test again to verify the generated files match the golden files.

## Updating Golden Files

If you intentionally change the pipeline behavior and need to update golden files:
1. Delete the relevant golden files (or the entire directory)
2. Run the test again to regenerate them
3. Review the changes to ensure they're expected
4. Commit the updated golden files

## Structure

Golden files mirror the structure of generated modules:
```
golden/
  <project>/
    <role>/
      <theme_slug>/
        <module-title>.md
```

