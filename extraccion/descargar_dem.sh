#!/usr/bin/env bash
# Modelos de elevación usados en el estudio (reproducible).
# FABDEM V1-2 (DTM sin edificios/vegetación, 1", CC BY-NC-SA 4.0): https://data.bris.ac.uk/data/dataset/s5hqmjcdj8yo2ibzi9b4ew3sn
#   teselas S34W071 (y vecinas) — en este equipo: ~/Proyectos/dem/fabdem/S34W071_FABDEM_V1-2.tif
# Copernicus GLO-30 DSM (ESA, 1"): bucket público de AWS
set -euo pipefail; mkdir -p dem
curl -s -o dem/cop_dsm_S34W071.tif "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S34_00_W071_00_DEM/Copernicus_DSM_COG_10_S34_00_W071_00_DEM.tif"
sha256sum dem/cop_dsm_S34W071.tif ~/Proyectos/dem/fabdem/S34W071_FABDEM_V1-2.tif
