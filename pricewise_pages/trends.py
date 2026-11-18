import altair as alt
import pandas as pd
import streamlit as st
from pricewise_ui import *
from pricewise_analytics import period_summary,matched_change
from pricewise_charts import draw,trend_ribbon,state_heatmap,TEAL,AMBER
from pricewise_visual_insights import stability_insights, matched_price_plot

data,items,shops,audit=context()
heading('EXPLORE / PRICE ANALYTICS','Understand the price movement.','Trace a product’s median price, the spread between shops, and the strength of its observation coverage.')
with st.expander('Adjust product, location & analysis period',expanded=False):
    state,district=location_controls()
    code=product(items,key='trend_product')
    a,b=st.columns([2,1])
    with a:
        dates=st.date_input('Analysis period',(data.date.min().date(),data.date.max().date()),min_value=data.date.min().date(),max_value=data.date.max().date())
    with b:
        frequency=st.segmented_control('Time resolution',['Daily','Weekly','Monthly'],default='Weekly') or 'Weekly'
if code is None:
    product_empty();st.stop()
if not dates or len(dates)!=2:
    st.info('Select both a start date and an end date in the analysis filters.');st.stop()
selection_summary(items,code)
scope_note(state,district)
st.caption(f'{dates[0]:%d %b %Y} – {dates[1]:%d %b %Y} · {frequency} summary')
history=selected_history(data,code,state,district)
sample=history[history.date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1]))]
if sample.empty:
    st.info('No observations for this selection. Adjust the product, location or date range.'); st.stop()
trend=period_summary(sample,frequency)
observed=trend.dropna(subset=['median'])
change=(observed['median'].iloc[-1]/observed['median'].iloc[0]-1)*100
metrics([('Median observed price',f'RM {sample.price.median():.2f}'),('First → last period median',f'{change:+.1f}%'),('Surveyed shops',f'{sample.premise_code.nunique():,}'),('Days with observations',str(sample.date.nunique()))])
view=st.segmented_control('Explore the data',['Price trends','Geographic patterns','Shop changes'],default='Price trends',key='analytics_view') or 'Price trends'
if view=='Price trends':
    with st.container(border=True):
        st.subheader('Price trajectory & the middle 50%')
        st.caption('Teal line: median price · shaded band: 25th–75th percentile · blue strip: observation volume')
        draw(trend_ribbon(trend))
        st.caption('Drag across the lower strip to zoom; double-click it to reset. Hover the line for values and sample sizes. Summary periods at either end may be partial.')
    st.caption('Median changes can reflect different shops being observed. They are descriptive price movements, not an official inflation measure. Weekly/monthly summaries pool observations within each period.')
    with st.container(border=True):
        st.subheader('Follow individual outlets over time')
        available=sample[['premise_code','premise']].drop_duplicates().sort_values('premise_code')
        names=available.set_index('premise_code').premise.to_dict()
        if 'history_outlets' in st.session_state:
            st.session_state['history_outlets']=[c for c in st.session_state['history_outlets'] if c in names]
        selected_outlets=st.multiselect('Outlets to track · up to five',available.premise_code.tolist(),default=available.head(3).premise_code.tolist(),max_selections=5,format_func=lambda p:f'{names[p]} · #{p}',key='history_outlets')
        if selected_outlets:
            tracked=sample[sample.premise_code.isin(selected_outlets)][['date','premise_code','price']].copy()
            # Reindex every day: missing observations break lines instead of implying continuity.
            index=pd.MultiIndex.from_product([pd.date_range(dates[0],dates[1]),selected_outlets],names=['date','premise_code'])
            tracked=tracked.set_index(['date','premise_code']).reindex(index).reset_index()
            tracked['Outlet']=tracked.premise_code.map(lambda p:f'{names[p]} · #{p}')
            highlight=alt.selection_point(fields=['Outlet'],bind='legend')
            chart=alt.Chart(tracked).mark_line(point=True).encode(x=alt.X('date:T',title='Observation date'),y=alt.Y('price:Q',title='Observed price (RM / listed unit)',scale=alt.Scale(zero=False)),color=alt.Color('Outlet:N'),opacity=alt.condition(highlight,alt.value(1),alt.value(.15)),tooltip=[alt.Tooltip('date:T',format='%d %b %Y'),alt.Tooltip('Outlet:N'),alt.Tooltip('price:Q',format='.2f',title='Price (RM)')]).add_params(highlight).properties(height=300)
            draw(chart)
            st.caption('Daily observed prices for the exact selected item. Missing days break the line; prices are not carried forward. Click the legend to highlight an outlet. This view retains daily detail regardless of the summary resolution above.')
        else:st.info('Select an outlet to trace its observed prices.')
elif view=='Geographic patterns':
    with st.container(border=True):
        st.subheader('A geographic view through time')
        draw(state_heatmap(sample))
        st.caption('Each cell is this product’s monthly median in a state. Hover for record counts. Blank cells have no observations. Colours compare prices across all visible cells.')
else:
    st.subheader('Did prices change at the same shops?')
    st.caption(f'Exact observations on {dates[0]:%d %b %Y} and {dates[1]:%d %b %Y}. Both endpoints must exist at the same premise.')
    paired=matched_change(sample,*dates)
    if paired.empty:
        st.info('No shops were observed at both endpoints. Choose different dates to make a matched-shop comparison.')
    else:
        a,b=st.columns([1,2])
        with a:
            st.metric('Matched shops',f'{len(paired):,}',border=True)
            st.metric('Median same-shop change',f'{paired.change_pct.median():+.2f}%',border=True)
            st.caption('Each shop contributes one percentage change. This controls for changes in which shops were surveyed.')
        with b:
            paired['movement']=paired.change_pct.map(lambda p:'Lower' if p<0 else ('Higher' if p>0 else 'Unchanged'))
            summary=paired.groupby('movement').size().rename('shops').reset_index()
            draw(alt.Chart(summary).mark_bar(cornerRadiusEnd=4).encode(y=alt.Y('movement:N',title=None,sort=['Lower','Unchanged','Higher']),x=alt.X('shops:Q',title='Matched shops'),color=alt.Color('movement:N',scale=alt.Scale(domain=['Lower','Unchanged','Higher'],range=[TEAL,'#9aa8a2',AMBER]),legend=None),tooltip=['movement:N','shops:Q']).properties(height=210))
        details=st.expander('Matched-shop evidence',on_change='rerun')
        if details.open:
            with details:
                st.dataframe(paired.merge(shops[['premise_code','premise']],on='premise_code').rename(columns={'premise':'Shop','price_start':'Start price (RM)','price_end':'End price (RM)','change_pct':'Change (%)','movement':'Movement'}),hide_index=True,column_config={'Start price (RM)':st.column_config.NumberColumn(format='RM %.2f'),'End price (RM)':st.column_config.NumberColumn(format='RM %.2f'),'Change (%)':st.column_config.NumberColumn(format='%.2f%%')})
    st.header('Explore individual shops')
    analysis=st.segmented_control('Shop-level visual analysis',['Price stability','Matched movements'],default='Price stability',key='shop_level_view') or 'Price stability'
    if analysis=='Price stability':
        stability_insights(sample,shops)
    elif not paired.empty:
        matched_price_plot(paired,shops)
    else:
        st.info('No exact-endpoint shop pairs are available. Adjust the analysis dates to use this view.')
export_data=trend.assign(item_code=code,item=items.set_index('item_code').loc[code,'item'],unit=items.set_index('item_code').loc[code,'unit'],state=state,district=district,analysis_start=str(dates[0]),analysis_end=str(dates[1]),frequency=frequency)
st.download_button('Export trend data',export_data.to_csv(index=False).encode('utf-8-sig'),'pricewise_trends.csv','text/csv',icon=':material/download:')
footer()
