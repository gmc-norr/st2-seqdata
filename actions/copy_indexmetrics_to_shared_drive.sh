set -euo pipefail

SOURCEDIR=$1
TARGETDIR=$2

ANALYSISFOLDER=$(basename $SOURCEDIR)
RUNPATH=${SOURCEDIR%%Analysis/$ANALYSISFOLDER}
RUNFOLDER=$(basename $RUNPATH)

rsync -azr $SOURCEDIR/Data/Demux/IndexMetricsOut.bin $TARGETDIR/$RUNFOLDER/InterOp/