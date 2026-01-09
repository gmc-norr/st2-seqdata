# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

The main config parameter that needs to be set is `notification_email`. This should contain an array of email addresses where notifications should be sent.

Example:

```yaml
notification_email:
  - me@email.com
```

## Actions

ref | description
--- | ---
copy_interop | Copy the InterOp folder of a Novaseq run to the shared drive
copy_indexmetrics | Copy the IndexMetricsOut.bin file of an analysis to the shared drive

## Rules

ref | description
--- | ---
copy_interop | Rule for copying the InterOp folder of a ready Novaseq run to the shared drive
copy_indexmetrics | Rule for copying the IndexMetricsOut.bin file when an analysis changes state to ready to the shared drive
copy_indexmetrics_new_directory | Rule for copying the IndexMetricsOut.bin file when a new, ready analysis directory is found to the shared drive

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues
