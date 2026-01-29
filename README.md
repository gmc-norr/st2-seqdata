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
copy_interop | Copy the InterOp folder from a sequencing run
copy_indexmetrics | Copy the IndexMetricsOut.bin file

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
