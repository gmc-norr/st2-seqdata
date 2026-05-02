# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

There are three items in the config that needs to be set:

- `notification_email`: an array of email addresses where notifications should be sent
- `interop_destinations`: platform specific paths where interop data should be copied when a run is ready
- `run_destinations`: platform specific paths where sequencing data should be moved when analysis is done

Example:

```yaml
notification_email:
  - me@email.com

interop_destinations:
  - platform: NovaSeq X Plus
    path: /path/to/interop/novaseq
  - platform: MiSeq i100
    path: /path/to/interop/miseq-i100

run_destinations:
  - platform: NovaSeq X Plus
    path: /path/to/seq/archive/novaseq
  - platform: MiSeq i100
    path: /path/to/seq/archive/miseq-i100
```

## Actions

ref | description
--- | ---
copy_interop | Copy the InterOp folder from a sequencing run
copy_indexmetrics | Copy the IndexMetricsOut.bin file
get_file_destination | Get the destination paths for runs and interop files (internal)

## Rules

ref | description
--- | ---
copy_interop | Rule for copying the InterOp folder from a sequencing run to a shared location
copy_indexmetrics | Rule for copying the IndexMetricsOut.bin file from a BCLConvert run to the InterOp folder in a shared location

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues
