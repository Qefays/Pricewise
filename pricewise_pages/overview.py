import altair as alt
import pandas as pd
import streamlit as st
from pricewise_ui import *
from pricewise_map import coverage_map
from pricewise_analytics import coverage_views, geographic_prices
from pricewise_charts import draw,calendar,histogram,geographic_ranges,BLUE
from pricewise_business import render_ranking

data,items,shops,audit=context()
heading('PRICEWISE MALAYSIA / RETAIL INTELLIGENCE','Spend smarter. Start with the evidence.','Explore comparable prices, build your shopping list and understand the trade-offs before choosing an outlet.')
with st.container(horizontal=True):
    if st.button('Build my shopping basket',type='primary',icon=':material/shopping_basket:'):st.switch_page('pricewise_pages/basket.py')
    if st.button('Compare a product',icon=':material/compare_arrows:'):st.switch_page('pricewise_pages/compare.py')
    st.badge(f'Data through {data.date.max():%d %b %Y}',icon=':material/calendar_today:',color='gray')
view=st.segmented_control('Dashboard focus',['Price snapshot','Survey coverage'],default='Price snapshot',key='dashboard_focus') or 'Price snapshot'
with st.expander('Adjust location, product & date',expanded=False):
    state,district=location_controls()
    if view=='Price snapshot':
        code=product(items)
        reference,days=window(data)
if view=='Price snapshot':
    if code is None:product_empty();st.stop()
    selection_summary(items,code)
    sample=latest_prices(selected_history(data,code,state,district),reference,days).sort_values(['price','premise_code'])
    if sample.empty:
        st.info('No observations match these filters. Change the product, location or date window.');st.stop()
    scope_note(state,district,reference,days)
    metrics([('Lowest observed price',f'RM {sample.price.min():.2f}'),('Typical price · median',f'RM {sample.price.median():.2f}'),('Comparable outlets',f'{len(sample):,}'),('Observed price spread',f'RM {sample.price.max()-sample.price.min():.2f}')])
    left,right=st.columns([1.7,1])
    with left,st.container(border=True):
        st.subheader('Where this product costs less')
        st.caption('The eight lowest observed outlet prices · same product and listed unit')
        render_ranking(sample.head(8),value='price',key='dashboard_ranking')
    with right,st.container(border=True):
        st.badge('Lowest observed option',icon=':material/storefront:',color='green')
        winner=sample.iloc[0]
        st.subheader(str(winner['premise']))
        st.metric('Price per listed unit',f"RM {winner.price:.2f}")
        st.write(f"{winner['district']}, {winner['state']}")
        st.caption(f"Observed {winner.date:%d %b %Y} · {winner.age_days} day(s) before the reference date")
        if st.button('Add this product to my list',type='primary',width='stretch'):
            basket=st.session_state.setdefault('basket',{})
            basket[code]=basket.get(code,0)+1
            st.session_state[f'qty_{code}']=basket[code]
            st.toast('One purchase unit added to Smart shopping',icon=':material/check:')
        st.page_link('pricewise_pages/basket.py',label='Review my shopping list',icon=':material/arrow_forward:')
        st.caption('Prices are historical observations. Confirm availability and checkout prices with the outlet.')
    a,b=st.columns(2)
    with a,st.container(border=True):
        st.subheader('How prices are distributed')
        draw(histogram(sample))
        st.caption('One latest eligible price per outlet. Amber marks the median.')
    with b,st.container(border=True):
        st.subheader('How areas compare')
        by='state' if state=='All Malaysia' else 'district'
        draw(geographic_ranges(geographic_prices(sample,by),by))
        st.caption('Median and middle 50% of observed prices. Hover for sample sizes.')
    with st.container(horizontal=True):
        st.page_link('pricewise_pages/locations.py',label='Explore the retailer map',icon=':material/map:')
        st.page_link('pricewise_pages/trends.py',label='Analyze price history',icon=':material/monitoring:')
else:
    stats,daily,groups=coverage_views(data,st.session_state['pw_signature'],state,district)
    st.caption(f"FULL DATASET COVERAGE · {stats['start']:%d %b %Y} – {stats['end']:%d %b %Y}")
    metrics([('Eligible observations',f"{stats['observations']:,}"),('Products monitored',f"{stats['products']:,}"),('Surveyed outlets',f"{stats['premises']:,}"),('Observed days',f"{stats['days']:,}")])
    coverage_map(data,state,district,st.session_state['pw_signature'])
    with st.container(border=True):
        st.subheader('Survey coverage through the year')
        draw(calendar(daily))
        st.caption('Grey cells have no eligible observations. Missing dates are never filled with estimated prices.')
    with st.container(border=True):
        st.subheader('What is being monitored?')
        draw(alt.Chart(groups).mark_bar(color=BLUE,cornerRadiusEnd=4).encode(x=alt.X('observations:Q',title='Observations',axis=alt.Axis(format='~s')),y=alt.Y('item_group:N',title=None,sort='-x'),tooltip=['item_group:N','observations:Q','products:Q']).properties(height=220))
    st.page_link('pricewise_pages/methodology.py',label='Inspect source coverage and methodology',icon=':material/verified:')
footer()
