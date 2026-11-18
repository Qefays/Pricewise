import pandas as pd
import streamlit as st
from pricewise_ui import *
from pricewise_charts import draw, ranking, histogram
from pricewise_visual_insights import shop_insights
from pricewise_business import render_ranking

data, items, shops, audit = context()
heading('SHOP / PRICE COMPARISON', 'Find a better price.', 'Find the shops behind the numbers, compare their observed prices, and inspect the evidence.')
with st.expander('Adjust product, location & observation window',expanded=False):
    state,district=location_controls()
    code=product(items,key='shop_product')
    reference,days=window(data)
if code is None:
    product_empty(); st.stop()
selection_summary(items,code)
if st.button('Add one unit to my shopping list',icon=':material/add_shopping_cart:'):
    basket=st.session_state.setdefault('basket',{})
    basket[code]=basket.get(code,0)+1
    st.session_state[f'qty_{code}']=basket[code]
    st.toast('Added to Smart shopping',icon=':material/check:')
st.page_link('pricewise_pages/basket.py',label='Open my shopping list',icon=':material/shopping_basket:')
result=latest_prices(selected_history(data,code,state,district),reference,days).sort_values(['price','premise_code'])
retailer=st.selectbox('Retailer type · applies to the entire comparison',['All retailer types']+sorted(result.premise_type.dropna().astype(str).unique()),key='comparison_retailer')
if retailer!='All retailer types':result=result[result.premise_type.eq(retailer)]
if result.empty:
    st.info('No eligible observations for these filters. Try a different product, area or date window.'); st.stop()
scope_note(state,district,reference,days)
metrics([('Lowest observed price',f'RM {result.price.min():.2f}'),('Median price',f'RM {result.price.median():.2f}'),('Price range',f'RM {result.price.max()-result.price.min():.2f}'),('Comparable shops',f'{len(result):,}')])
winner=result.iloc[0]
with st.container(border=True):
    a,b=st.columns([3,1])
    with a:
        st.caption('LOWEST OBSERVED PRICE')
        st.subheader(str(winner['premise']))
        st.write(str(winner['address']))
        st.caption(f"{winner['district']}, {winner['state']} · Observed {winner['date']:%d %b %Y} · {winner['age_days']} day(s) before reference date")
    with b:
        st.metric('Per listed unit',f"RM {winner['price']:.2f}")
        st.link_button('View directions',maps_url(winner),icon=':material/directions:')
    ties=int(result.price.eq(winner.price).sum())
    if ties>1: st.caption(f'{ties} shops share this lowest observed price. The featured shop uses stable premise-code order.')
a,b=st.columns([1.4,1])
with a,st.container(border=True):
    st.subheader('The lowest observed prices')
    limit=st.select_slider('Shops to display',[5,10,15,20],value=10)
    render_ranking(result.head(limit),value='price',key='product_business_rank')
    st.caption('Every bar represents the same product and purchase unit.')
with b,st.container(border=True):
    st.subheader('The wider price picture')
    draw(histogram(result))
    st.caption(f'{result.age_days.gt(0).sum():,} of {len(result):,} prices predate the reference date. The amber line is the median.')
shop_insights(result)
st.subheader('Inspect the observations')
query=st.text_input('Search the outlet evidence',placeholder='Outlet name or address')
view=result
if query:view=result[result.premise.astype(str).str.contains(query,case=False,regex=False)|result.address.astype(str).str.contains(query,case=False,regex=False)]
st.caption('Search narrows the evidence table. The retailer-type filter above applies to KPIs, charts and export.')
table(view[['item','unit','price','date','age_days','premise','address','premise_type','state','district']])
export(result[['item_code','item','unit','premise_code','premise','price','date','age_days','address','premise_type','state','district']], 'pricewise_shop_comparison.csv',state,district,reference,days)
footer()
