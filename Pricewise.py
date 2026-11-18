from pathlib import Path
import streamlit as st
from pricewise_core import deployment_sources, load_data

st.set_page_config(page_title='PriceWise Malaysia', page_icon=':material/shopping_basket:', layout='wide')
st.logo(str(Path(__file__).parent / 'assets' / 'pricewise.svg'), size='large', icon_image=str(Path(__file__).parent / 'assets' / 'pricewise-icon.svg'))
st.sidebar.caption('RETAIL PRICE INTELLIGENCE')

@st.cache_resource(max_entries=1, show_spinner='Preparing validated PriceCatcher observations…')
def cached_data(signature):
    return load_data()

try:
    signature = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in deployment_sources())
    data, items, shops, audit = cached_data(signature)
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.info('Check that all files in the snapshot folder were committed to GitHub.')
    st.stop()
if data.empty:
    st.warning('No eligible observations remain after validation.')
    st.stop()
st.session_state['pw_data'] = (data, items, shops, audit)
st.session_state['pw_signature'] = signature
page = st.navigation([
    st.Page('pricewise_pages/overview.py', title='Dashboard', icon=':material/dashboard:', default=True),
    st.Page('pricewise_pages/compare.py', title='Price comparison', icon=':material/storefront:'),
    st.Page('pricewise_pages/basket.py', title='Smart shopping', icon=':material/shopping_basket:'),
    st.Page('pricewise_pages/locations.py', title='Retailer map', icon=':material/map:'),
    st.Page('pricewise_pages/trends.py', title='Price analytics', icon=':material/monitoring:'),
    st.Page('pricewise_pages/methodology.py', title='Data & methodology', icon=':material/verified:'),
])
st.sidebar.markdown('**Your data, at a glance**')
st.sidebar.caption(f"Available data: {data.date.min():%d %b %Y} – {data.date.max():%d %b %Y}")
st.sidebar.caption(f"{audit['Eligible observations']:,} eligible observations")
st.sidebar.caption('Historical observations · MYR')
st.sidebar.caption(f"Shopping list: {len(st.session_state.get('basket',{}))} products")
page.run()
