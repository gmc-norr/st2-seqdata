# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

The main config parameters that need to be set are `illumina_directories`, `notification_email` and `cleve`. These should contain an array of paths to watch for new runs in, an array of email addresses where notifications should be sent and the [cleve](https://github.com/gmc-norr/cleve) configuration, respectively.

Example:

```yaml
illumina_directories:
    - /data/seqdata/novaseq
    - /data/seqdata/nextseq

notification_email:
  - me@email.com

cleve:
  host: localhost
  port: 8080
  api_key: supersecretapikey
```

## Actions

ref | description
--- | ---
add_analysis       | Add an analysis associated with a sequencing run
add_run            | Add a sequencing run to the database
add_run_qc         | Add sequencing QC data to the database
run_state_workflow | Workflow for updating run state and setting properties
update_analysis    | Update an analysis associated with a NovaSeq sequencing run
update_run_path    | Update the path of a run
update_run_state   | Update the state of a run
update_samplesheet | Update the samplesheet for a run
copy_interop | Copy the InterOp folder of a Novaseq run to the shared drive
copy_indexmetrics | Copy the IndexMetricsOut.bin file of an analysis to the shared drive

## Rules

ref | description
--- | ---
add_analysis_directory | Rule for adding an analysis directory to an existing NovaSeq run
add_run_directory      | Rule for adding a new sequencing run directory
notify_duplicate_run   | Rule for sending an email when an duplicate run directory is found
notify_incomplete_run  | Rule for sending an email when an incomplete run directory is found
update_analysis        | Rule for updating the state and summary for an existing analysis
update_run_state       | Rule for when the state of a run directory is updated
update_samplesheet     | Rule for updating the samplesheet for a run
copy_interop | Rule for copying the InterOp folder of a ready Novaseq run to the shared drive
copy_indexmetrics | Rule for copying the IndexMetricsOut.bin file when an analysis changes state to ready to the shared drive
copy_indexmetrics_new_directory | Rule for copying the IndexMetricsOut.bin file when a new, ready analysis directory is found to the shared drive

## Sensors

ref | description
--- | ---
IlluminaDirectorySensor | Sensor that emits triggers for seqencing run directories that are direct children of a specific directory, as well as any analysis directories that are found in those run directories.

## Triggers

ref | description
--- | ---
duplicate_run        | Trigger that indicates a duplicated run was found.
incomplete_directory | Triggers when a new directory is found, but it is somehow incomplete and thus cannot be added to the database.
new_directory        | Triggers when a new directory is found
new_samplesheet      | Triggers when a new samplesheet is found for a run.
state_change         | Triggers when the state of a directory changes

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues
