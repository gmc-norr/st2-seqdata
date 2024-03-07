# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

The main config parameter that needs to be set is `run_directories`. This is an array of objects representing the directories in which to watch for sequencing run directories. Each entry should have the absolute path to the directory in question, and the name of the host where this directory is located. If the host name is missing or `null` it will default to `localhost`.

Example:

```yaml
run_directories:
    - path: /data/seqdata
      host: null # will look on localhost
    - directory: /data/seqdata
      host: vsXXX.vll.se
```

The pack needs to be able to read and write to the key-value store, more specifically the following keys:

- `gmc_norr_seqdata.RunDirectorySensor:run_directories`

Furthermore, the following keys must be defined in the key-value store:

- `service_user`: username that the pack should act as when accessing data
- `service_keyfile`: the path to the private ssh key that should be used for authentication

## Actions


## Rules


## Sensors

ref | description
--- | ---
RunDirectorySensor | Sensor that emits triggers for seqencing run directories that are direct children of a specific directory

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues

