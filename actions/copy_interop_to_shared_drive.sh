#!/bin/bash

set -euo pipefail

SOURCEDIR=$1
TARGETDIR=$2

RUNFOLDER=$(basename $SOURCEDIR)

# declare -a FILES=("CopyComplete.txt" "RTAComplete.txt" "RTAExited.txt" "RunCompletionStatus.xml" "RunInfo.xml" "RunParameters.xml" "SampleSheet.csv")

rsync -azr $SOURCEDIR/InterOp $TARGETDIR/$RUNFOLDER/