import streamlit as st
from pricewise_ui import *
from pricewise_locations import render_location_map

data,items,shops,audit=context()
heading('EXPLORE / RETAILER MAP','Prices across places.','Compare state-level prices and inspect the outlets behind the observations.')
with st.expander('Adjust product, location & observation window',expanded=False):
    state,district=location_controls()
    code=product(items,key='map_product')
    reference,days=window(data)
if code is None:st.stop()
selection_summary(items,code)
latest=latest_prices(selected_history(data,code,state,district),reference,days)
retailers=st.multiselect('Retailer types',sorted(latest.premise_type.dropna().astype(str).unique()),key='map_retailers')
if retailers:latest=latest[latest.premise_type.isin(retailers)]
if latest.empty:st.info('No eligible prices for these filters. Change the product, location or date.');st.stop()
scope_note(state,district,reference,days)
metrics([('Compared outlets',f'{len(latest):,}'),('Median product price',f'RM {latest.price.median():.2f}'),('Latest observation',f'{latest.date.max():%d %b %Y}')])
render_location_map(latest,shops,state)
with st.container(border=True):
    st.subheader('Outlet directory')
    query=st.text_input('Find an outlet or address',placeholder='Type a shop, street or postcode')
    found=latest
    if query:found=found[found.premise.astype(str).str.contains(query,case=False,regex=False)|found.address.astype(str).str.contains(query,case=False,regex=False)]
    table(found.sort_values(['price','premise_code'])[['premise','address','district','state','price','date','age_days']])
    st.caption('Directory search narrows this table. Geographic, product, date and retailer filters control the map and metrics above.')
footer()

