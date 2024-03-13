# StackStorm pack for handling sequencing data

## Installation

```bash
st2 pack install https://github.com/gmc-norr/st2-seqdata.git
st2 pack config gmc_norr_seqdata
```

## Config

The main config parameter that needs to be set is `illumina_directories`. This is an array of objects representing the directories in which to watch for sequencing run directories. Each entry should have the absolute path to the directory in question, and the name of the host where this directory is located. If the host name is missing or `null` it will default to `localhost`.

Example:

```yaml
illumina_directories:
    - path: /data/seqdata
      host: null # will look on localhost
    - directory: /data/seqdata
      host: vsXXX.vll.se
```

If the illumina directory sensor will run on any remote hosts, then the `user` and `ssh_key` parameters in the config need to be defined. These default to:

```yaml
user: stanley
ssh_key: /home/stanley/.ssh/stanley_rsa
```

The user `sensor_service` needs to be able to read and write to the key-value store, more specifically the following keys:

- `gmc_norr_seqdata.IlluminaDirectorySensor:illumina_directories`

## Actions


## Rules


## Sensors

ref | description
--- | ---
IlluminaDirectorySensor | Sensor that emits triggers for seqencing run directories that are direct children of a specific directory, as well as any analysis directories that are found in those run directories.

## Triggers

ref | description
--- | ---
copy_complete | Triggers when CopyComplete.txt is found in a directory
new_directory | Triggers when a new directory is found

> [!TIP]
> Note that the triggers that are connected to analysis directories will not be emitted unless `CopyComplete.txt` is found in its parent run diretory.

## Running tests

```
git clone https://github.com/gmc-norr/st2-seqdata
st2-run-pack-tests -p st2-seqdata
```

## Known issues

