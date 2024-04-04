# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

The main config parameters that need to be set are `illumina_directories` and `cleve`. These should contain an array of paths to watch for new runs in and the [cleve](https://github.com/gmc-norr/cleve) configuration, respectively.

Example:

```yaml
illumina_directories:
    - /data/seqdata/novaseq
    - /data/seqdata/nextseq

cleve:
  host: localhost
  port: 8080
  api_key: supersecretapikey
```

## Actions

ref | description
--- | ---
add_analysis     | Add an analysis associated with a sequencing run
add_run          | Add a sequencing run to the database
update_analysis  | Update an analysis associated with a NovaSeq sequencing run
update_run_state | Update the state of a run

## Rules

ref | description
--- | ---
add_analysis_directory | Rule for adding an analysis directory to an exising NovaSeq run
add_run_directory      | Rule for adding a new sequencing run directory
notify_incomplete      | Rule for sending an email when an incomplete run directory is found
update_analysis        | Rule for updating the state and summary for an existing analysis
update_run_state       | Rule for updating the state of an existing sequencing run

## Sensors

ref | description
--- | ---
IlluminaDirectorySensor | Sensor that emits triggers for seqencing run directories that are direct children of a specific directory, as well as any analysis directories that are found in those run directories.

## Triggers

ref | description
--- | ---
incomplete_directory | Triggers when a new directory is found, but it is somehow incomplete and thus cannot be added to the database
new_directory        | Triggers when a new directory is found
state_change         | Triggers when the state of a directory changes

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues

