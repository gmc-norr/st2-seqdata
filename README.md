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


## Rules


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

