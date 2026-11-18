import altair as alt
import pandas as pd
import streamlit as st
from pricewise_core import basket_results
from pricewise_ui import *
from pricewise_charts import draw,basket_stack,TEAL,AMBER,BLUE
from pricewise_visual_insights import basket_matrix
from pricewise_business import savings_summary,basket_business_views
from pricewise_locations import render_location_map

data,items,shops,audit=context()
heading('SHOP / SMART SHOPPING','Your list. Your best comparison.','01 Build your list · 02 Compare complete baskets · 03 Choose an outlet')
st.session_state.setdefault('basket',{})
if st.session_state.get('basket_undo'):
    with st.container(horizontal=True):
        st.caption('Shopping list updated.')
        if st.button('Undo last removal',icon=':material/undo:',key='undo_basket'):
            for undo_code,undo_quantity in st.session_state.pop('basket_undo').items():
                st.session_state.basket[undo_code]=st.session_state.basket.get(undo_code,0)+undo_quantity
                st.session_state[f'qty_{undo_code}']=st.session_state.basket[undo_code]
            st.rerun()

with st.expander('Shopping area & observation window',expanded=not bool(st.session_state.basket)):
    state,district=location_controls(required=True)
    reference,days=window(data)
labels=product_labels(items)
with st.expander('Add products · group → category → unit → variant',expanded=not bool(st.session_state.basket)):
    selected=product(items,key='basket_product')
    if selected is not None:
        a,b=st.columns([1,2],vertical_alignment='bottom')
        quantity=a.number_input('Purchase units to add',min_value=1,max_value=1000,value=1)
        if b.button('Add to my basket',type='primary',icon=':material/add_shopping_cart:',width='stretch'):
            new_quantity=st.session_state.basket.get(selected,0)+quantity
            st.session_state.basket[selected]=new_quantity
            st.session_state[f'qty_{selected}']=new_quantity
            st.toast('Product added to your basket',icon=':material/check_circle:')
if not st.session_state.basket:
    with st.container(border=True):
        st.subheader('Your shopping list starts here')
        st.write('Choose a product above, set the number of purchase units, and add it to your basket. Each comparison uses your own list.')
        a,b,c=st.columns(3)
        a.markdown('**01 · Choose**\n\nUse the official group, category and unit to identify a product.')
        b.markdown('**02 · Compare**\n\nOnly shops with every basket item enter the complete-shop ranking.')
        c.markdown('**03 · Inspect**\n\nExplore item costs, observation dates and the number of shops involved.')
    footer(); st.stop()
with st.container(border=True):
    a,b=st.columns([3,1],vertical_alignment='bottom')
    a.subheader(f"Your basket · {len(st.session_state.basket)} {'product' if len(st.session_state.basket)==1 else 'products'}")
    if b.button('Clear basket',icon=':material/delete_sweep:',width='stretch'):
        st.session_state['basket_undo']=dict(st.session_state.basket)
        for code in list(st.session_state.basket): st.session_state.pop(f'qty_{code}',None)
        st.session_state.basket={}
        st.rerun()
    for code,qty in list(st.session_state.basket.items()):
        a,b,c=st.columns([5,1,1],vertical_alignment='bottom')
        a.write(labels[code])
        if st.session_state.get(f'qty_{code}') is None:
            st.session_state[f'qty_{code}']=int(qty or 1)
        st.session_state.basket[code]=b.number_input('Units',min_value=1,max_value=1000000,key=f'qty_{code}')
        if c.button('Remove',key=f'remove_{code}',width='stretch'):
            st.session_state['basket_undo']={code:st.session_state.basket[code]}
            del st.session_state.basket[code]
            st.session_state.pop(f'qty_{code}',None)
            st.rerun()
    st.caption('Quantities are whole multiples of the listed purchase unit, for example 2 × a 1 kg pack.')
quantities=st.session_state.basket
if any(q is None for q in quantities.values()):
    st.info('Enter a positive quantity for each item.');st.stop()
history=pd.concat([selected_history(data,c,state,district) for c in quantities],ignore_index=True)
latest=latest_prices(history,reference,days)
eligible_shops=shops[shops.state.eq(state)]
if district!='All districts': eligible_shops=eligible_shops[eligible_shops.district.eq(district)]
rows,complete,incomplete,multi,absent=basket_results(latest,quantities,eligible_shops.premise_code)
single_total=complete.total.iloc[0] if not complete.empty else None
multi_total=multi.line_total.sum() if not absent else None
scope_note(state,district,reference,days)
metrics([('Complete single-shop baskets',str(len(complete))),('Best single-shop total',f'RM {single_total:.2f}' if single_total is not None else 'Unavailable'),('Multi-shop minimum',f'RM {multi_total:.2f}' if multi_total is not None else 'Unavailable'),('Multi-shop visits',str(multi.premise_code.nunique()) if multi_total is not None else '—')])
baseline=None
if not complete.empty:
    with st.container(border=True):
        st.subheader('Your savings, against your reference')
        shop_names=shops.set_index('premise_code').premise.to_dict()
        if st.session_state.get('reference_shop') not in complete.premise_code.values:
            st.session_state.pop('reference_shop',None)
        ref_code=st.selectbox('Reference outlet · choose where you would otherwise shop',complete.premise_code.tolist(),index=None,placeholder='Choose a complete outlet to calculate savings',format_func=lambda p:f'{shop_names[p]} · #{p}',key='reference_shop')
        summary=savings_summary(complete,ref_code)
        if summary:
            baseline=summary['reference']
            metrics([('Reference basket',f'RM {baseline:.2f}'),('Potential gross savings',f"RM {summary['gross']:.2f}"),('Savings vs reference',f"{summary['percent']:.1f}%"),('Highest complete basket',f"RM {summary['highest']:.2f}")])
            st.caption(f'Reference: {shop_names[ref_code]} · Same items, quantities, location and observation window. Gross savings exclude travel and time.')
        else:st.caption('Choose a reference to calculate potential savings. The highest-priced outlet is not assumed to be your usual shop.')
        winner_code=int(complete.premise_code.iloc[0])
        st.success(f'Lowest complete basket: {shop_names[winner_code]} · RM {single_total:.2f}')
        st.caption(f"Oldest price in this basket: {complete.oldest.iloc[0]:%d %b %Y}. Equal-cost ties use premise-code order.")
basket_business_views(rows,complete,shops,items)
if single_total is not None and multi_total is not None:
    difference=single_total-multi_total
    st.success(f'RM {difference:.2f} difference in historical item costs between the best complete single-shop basket and the multi-shop combination.')
st.caption('These totals exclude transport and time. Observations do not confirm stock availability or today’s checkout price. Shops in the same state or district may be far apart.')
if complete.empty:
    st.warning('No shop has eligible observations for every item. You can remove a low-coverage product, broaden the location or adjust the lookback. Your selection has not been changed.')
if absent:
    st.warning('A complete multi-shop total is unavailable. Missing observations for: '+ '; '.join(labels[c] for c in absent))
composition=st.expander('Basket composition · item-by-item cost breakdown',on_change='rerun')
if not complete.empty and composition.open:
    with composition:
        st.subheader('What makes up the complete basket cost?')
        top_codes=complete.head(5).premise_code.tolist()
        stacks=shop_labels(rows[rows.premise_code.isin(top_codes)])
        order=shop_labels(complete.head(5).merge(shops,on='premise_code')).shop_label.tolist()
        if not absent:
            extra=multi.copy();extra['shop_label']='Multi-shop minimum'
            stacks=pd.concat([stacks,extra],ignore_index=True)
            order=['Multi-shop minimum']+order
        draw(basket_stack(stacks,order))
        st.caption('Each coloured segment is one product’s quantity × observed unit price. Complete baskets only; up to five lowest-cost single shops.')
if single_total is not None and multi_total is not None:
    best=rows[rows.premise_code.eq(complete.premise_code.iloc[0])]
    differences=best[['item_code','item','line_total']].merge(multi[['item_code','line_total']],on='item_code',suffixes=('_single','_multi'))
    differences['difference']=differences.line_total_single-differences.line_total_multi
    if differences.difference.gt(.001).any():
        with st.container(border=True):
            st.subheader('Where does the price difference come from?')
            draw(alt.Chart(differences).mark_bar(color=AMBER,cornerRadiusEnd=4).encode(y=alt.Y('item:N',sort='-x',title=None,axis=alt.Axis(labelLimit=260)),x=alt.X('difference:Q',title='Item-cost reduction versus best single shop (RM)'),tooltip=[alt.Tooltip('item:N',title='Product'),alt.Tooltip('difference:Q',format='.2f',title='Difference (RM)')]).properties(height=max(160,len(differences)*30)))
mode=st.segmented_control('Inspect a shopping option',['Single shop','Multiple shops'],default='Single shop',key='basket_mode') or 'Single shop'
if mode=='Single shop' and not complete.empty:
    ranked=complete.merge(shops,on='premise_code')
    shop_names=shops.set_index('premise_code').premise.to_dict()
    chosen=st.selectbox('Choose a complete shop to inspect',ranked.premise_code.tolist(),format_func=lambda p:f'{shop_names[p]} · #{p}')
    detail=rows[rows.premise_code.eq(chosen)]
    table(detail[DETAILS])
    st.link_button('Directions to this shop',maps_url(detail.iloc[0]),icon=':material/directions:')
    evidence=rows[rows.premise_code.isin(complete.premise_code)].merge(complete[['premise_code','total']],on='premise_code')
    export(evidence[['item_code','item','unit','quantity','price','line_total','date','age_days','premise_code','premise','address','state','district','total']], 'pricewise_complete_baskets.csv',state,district,reference,days)
    ranking_panel=st.expander('All complete-shop totals',on_change='rerun')
    if ranking_panel.open:
        with ranking_panel: table(ranked)
elif mode=='Multiple shops' and not absent:
    st.subheader('Your shopping stops')
    for premise,stop in multi.groupby('premise_code',sort=True):
        with st.container(border=True):
            a,b=st.columns([3,1])
            a.markdown(f"**{stop.iloc[0]['premise']}**")
            a.caption(str(stop.iloc[0]['address']))
            b.metric('Items at this shop',f'RM {stop.line_total.sum():.2f}')
            table(stop[['item','unit','quantity','price','line_total','date','age_days']])
            st.link_button('View directions',maps_url(stop.iloc[0]),key=f'map_{premise}',icon=':material/directions:')
    export(multi[['item_code','item','unit','quantity','price','line_total','date','age_days','premise_code','premise','address','state','district']], 'pricewise_multi_shop.csv',state,district,reference,days)
    st.caption('Equal-price ties use the lowest premise code. The calculation minimizes observed item costs; it does not minimize shop visits or distance.')
with st.container(border=True):
    st.subheader('How well is your basket observed?')
    coverage=latest.groupby('item_code').premise_code.nunique().reindex(list(quantities),fill_value=0).rename('shops').reset_index()
    coverage['product']=coverage.item_code.map(labels)
    draw(alt.Chart(coverage).mark_bar(color=BLUE,cornerRadiusEnd=4).encode(y=alt.Y('product:N',title=None,sort='x',axis=alt.Axis(labelLimit=260)),x=alt.X('shops:Q',title='Shops with an eligible observation'),tooltip=['product:N','shops:Q']).properties(height=max(150,len(coverage)*30)))
    st.caption('Lower coverage can limit complete-basket options. Missing observations do not imply a stock shortage.')
basket_matrix(latest,quantities,eligible_shops,labels)
map_panel=st.expander('Locate complete shopping options',on_change='rerun')
if map_panel.open:
    with map_panel:render_location_map(latest,eligible_shops,state,key='basket_locations',basket=complete,baseline=baseline)
missing_panel=st.expander(f'Incomplete premises · {len(incomplete):,}',on_change='rerun')
if missing_panel.open:
    with missing_panel:
        missing=incomplete.copy()
        missing['Missing products']=missing.missing_codes.map(lambda codes:'; '.join(labels[c] for c in codes))
        st.dataframe(missing.drop(columns='missing_codes').merge(shops[['premise_code','premise','district']],on='premise_code').rename(columns={'premise':'Shop','district':'District'}),hide_index=True)
        st.caption('Includes scoped lookup premises with no basket observations. Partial basket totals are never ranked against complete totals.')
footer()
