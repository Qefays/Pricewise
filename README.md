# PriceWise Malaysia

A Streamlit dashboard using 17,247,302 validated PriceCatcher observations dated 1 January to 7 November 2026. The deployment reads the fixed historical snapshot in `snapshot/` and its source audit.

## Deploy on Streamlit Community Cloud

Push the contents of this folder to the root of a GitHub repository. Upload all four Parquet parts, both lookup tables, and the audit JSON with the application. Use the repository's branch, `Pricewise.py` as the entry point, and Python 3.11. Streamlit installs the pinned packages from `requirements.txt`. The bundled snapshot requires no external data credentials.

## Data sources

PriceCatcher observations and lookup data are published by KPDN and DOSM on Malaysia's open data portal under Creative Commons Attribution 4.0. This snapshot converts the source CSVs to Parquet, joins lookup metadata, and excludes invalid, duplicate-key, or unmatched observations as recorded in `snapshot/audit.json`.

- [PriceCatcher observations](https://data.gov.my/data-catalogue/pricecatcher)
- [Item lookup](https://data.gov.my/data-catalogue/lookup_item)
- [Premise lookup](https://data.gov.my/data-catalogue/lookup_premise)
- [DOSM state boundaries](https://github.com/dosm-malaysia/data-open/blob/main/datasets/geodata/administrative_1_state.geojson)
