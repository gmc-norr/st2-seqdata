#!/bin/bash

set -euo pipefail

SOURCEDIR=$1
TARGETDIR=$2

RUNFOLDER=$(basename $SOURCEDIR)

rsync -azr $SOURCEDIR/InterOp $SOURCEDIR/RunParameters.xml $SOURCEDIR/RunInfo.xml $TARGETDIR/$RUNFOLDER/