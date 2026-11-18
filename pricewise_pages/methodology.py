import streamlit as st
import pandas as pd
from pricewise_ui import context,heading,footer

data,items,shops,audit=context()
heading('TRUST / DATA & METHODOLOGY','Know what the numbers mean.','Trace the source, comparison rules and limits behind every recommendation.')
with st.container(border=True):
    st.subheader('Real observations. Explicit limits.')
    st.write('PriceWise uses the supplied Malaysian PriceCatcher CSVs and official item/premise lookups. All production charts use eligible source observations. Synthetic fixtures are isolated in automated tests.')
    st.caption(f'Loaded dates: {data.date.min():%d %b %Y} – {data.date.max():%d %b %Y}. The app does not claim live checkout prices, stock levels, discounts or real-time traffic.')
for title,text in [
    ('Comparable means the same item','Products match by exact item code and listed purchase unit. Prices are not pooled across brands, variants or pack sizes. Quantities multiply that unit.'),
    ('How the price window works','The latest eligible observation per item and outlet is chosen within the selected calendar-day window, including the reference date. Later observations are never used. Age is measured against the reference date.'),
    ('Savings need a reference','Gross savings = your explicitly selected complete reference basket − the lowest complete basket. Savings percentage divides that difference by the reference cost. The highest observed cost is descriptive, never silently used as your spending baseline.'),
    ('One outlet versus multiple outlets','A complete single-outlet basket requires every selected item. Multi-outlet optimization minimizes observed item costs, not travel distance or number of stops. Equal-price ties use premise-code order. Missing prices are never zero.'),
    ('Geography and travel','The original lookup contains addresses, not coordinates. State polygons are official DOSM geometry. Outlet markers require a separate provenance-bearing verified coordinate file. Directions search the supplied address in Google Maps. No driving distance, ETA or net travel savings are calculated.'),
    ('Reading the analytics','Percentile bands show observed spread, not confidence intervals. Pooled medians may change when surveyed shops change. Matched-shop comparisons require observations at both exact endpoints. CV is sample standard deviation divided by mean price. Expanded CV scales are labelled. These are not official inflation estimates.')]:
    with st.expander(title,expanded=False):st.write(text)
with st.expander('Source file coverage and validation audit',expanded=True):
    st.dataframe(pd.DataFrame(audit['File coverage']),hide_index=True)
    counts={k:v for k,v in audit.items() if k!='File coverage'}
    st.dataframe(pd.DataFrame({'Validation check':list(counts),'Result':[str(v) for v in counts.values()]}),hide_index=True)
    st.caption('Invalid prices/dates, unresolved lookups and all duplicate-key rows are excluded. Exclusion counts can overlap; do not sum them to infer the number excluded. Monthly filenames do not prove a full month of coverage.')
footer()
