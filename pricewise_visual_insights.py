"""Focused visual analyses with explicit units, dates and coverage."""
import json
import altair as alt
import pandas as pd
import streamlit as st
from pricewise_analytics import price_reach, retailer_summary, shop_stability, basket_coverage_matrix
from pricewise_charts import draw, TEAL, AMBER, BLUE
from pricewise_map import BOUNDARIES

def shop_insights(latest):
    with st.container(border=True):
        st.subheader('Explore the market from another angle')
        mode=st.segmented_control('Visual analysis',['Retailer types','Budget reach','Price map'],default='Retailer types',key='shop_insight') or 'Retailer types'
        if mode=='Retailer types':
            summary=retailer_summary(latest)
            base=alt.Chart(summary).encode(y=alt.Y('retailer:N',title=None,sort=alt.SortField('median',order='ascending'),axis=alt.Axis(labelLimit=185)),tooltip=[alt.Tooltip('retailer:N',title='Retailer type'),alt.Tooltip('shops:Q',title='Shops'),alt.Tooltip('median:Q',title='Median (RM)',format='.2f'),alt.Tooltip('low:Q',title='Minimum',format='.2f'),alt.Tooltip('lower:Q',title='25th percentile',format='.2f'),alt.Tooltip('upper:Q',title='75th percentile',format='.2f'),alt.Tooltip('high:Q',title='Maximum',format='.2f')])
            whisker=base.mark_rule(color='#aebcb6',strokeWidth=2).encode(x=alt.X('low:Q',title='Observed price (RM / listed unit)',scale=alt.Scale(zero=False)),x2='high:Q')
            box=base.mark_rule(color=TEAL,strokeWidth=14,opacity=.65).encode(x='lower:Q',x2='upper:Q')
            middle=base.mark_tick(color='#173d37',thickness=3,size=22).encode(x='median:Q')
            draw((whisker+box+middle).properties(height=max(230,len(summary)*42)))
            st.caption('Thin range: minimum–maximum · thick range: middle 50% · dark mark: median. Each shop contributes one latest eligible price. Retailer groups can have different sample sizes and locations; this does not establish a causal retailer effect.')
        elif mode=='Budget reach':
            budget=st.number_input('Your price ceiling per listed unit (RM)',min_value=0.0,value=round(float(latest.price.median()),2),step=.50,key='price_ceiling')
            within=int(latest.price.le(budget).sum())
            st.metric('Surveyed shops at or below your ceiling',f'{within:,} / {len(latest):,}',help='Based on the latest eligible historical observation at each shop.')
            reach=price_reach(latest)
            # Extend the chart to zero shops below the minimum observed price.
            reach=pd.concat([pd.DataFrame({'price':[0.0],'share':[0.0],'cumulative_shops':[0]}),reach],ignore_index=True)
            curve=alt.Chart(reach).mark_line(color=TEAL,strokeWidth=3,interpolate='step-after').encode(x=alt.X('price:Q',title='Price ceiling (RM / listed unit)'),y=alt.Y('share:Q',title='Shops at or below ceiling (%)',scale=alt.Scale(domain=[0,100])),tooltip=[alt.Tooltip('price:Q',title='Price ceiling (RM)',format='.2f'),alt.Tooltip('share:Q',title='Share of shops (%)',format='.1f'),alt.Tooltip('cumulative_shops:Q',title='Shops')])
            threshold=alt.Chart(pd.DataFrame({'ceiling':[budget]})).mark_rule(color=AMBER,strokeDash=[5,4],strokeWidth=2).encode(x='ceiling:Q')
            dot=alt.Chart(pd.DataFrame({'ceiling':[budget],'share':[within/len(latest)*100]})).mark_circle(color=AMBER,size=100).encode(x='ceiling:Q',y='share:Q')
            draw((curve+threshold+dot).properties(height=300))
            st.caption('The step curve shows the cumulative share of surveyed shops within each price ceiling. Tied prices enter together. The amber marker shows your ceiling; this is historical price coverage, not a stock or savings guarantee.')
        else:
            summary=latest.groupby('state',observed=True).agg(median=('price','median'),shops=('premise_code','nunique')).to_dict('index')
            geometry=json.loads(BOUNDARIES.read_text(encoding='utf-8'))
            for feature in geometry['features']:
                record=summary.get(feature['properties']['state'])
                feature['properties']['median']=float(record['median']) if record else None
                feature['properties']['shops']=int(record['shops']) if record else 0
            chart=alt.Chart(alt.Data(values=geometry['features'])).mark_geoshape(stroke='white',strokeWidth=1).encode(color=alt.condition('isValid(datum.properties.median)',alt.Color('properties.median:Q',title='Median price (RM)',scale=alt.Scale(scheme='teals',zero=False)),alt.value('#e2e7e4')),tooltip=[alt.Tooltip('properties.state:N',title='State'),alt.Tooltip('properties.median:Q',title='Median price (RM)',format='.2f'),alt.Tooltip('properties.shops:Q',title='Eligible shops')]).project(type='mercator').properties(height=330)
            draw(chart)
            st.caption('Same product, unit and date-matching rule across states. Counts and medians respect your location filters; a district selection is displayed within its parent state. Grey areas have no eligible observations in this selection. Boundaries: DOSM.')

def stability_insights(history,shops):
    with st.container(border=True):
        st.subheader('Which shops have more stable observed prices?')
        minimum=st.select_slider('Minimum observed days per shop',[3,7,14,30],value=7,key='stability_days')
        summary=shop_stability(history,minimum).merge(shops[['premise_code','premise','state','district']],on='premise_code',validate='one_to_one')
        if summary.empty:
            st.info('No shops meet this coverage threshold. Reduce the minimum or widen the analysis period.');return
        scale_mode=st.segmented_control('Variation scale',['Expanded low values','Linear'],default='Expanded low values',key='variation_scale') or 'Expanded low values'
        variation_scale=alt.Scale(type='symlog',constant=1,zero=True) if scale_mode=='Expanded low values' else alt.Scale(zero=True)
        selection=alt.selection_point(fields=['state'],bind='legend',name='stability_state')
        chart=alt.Chart(summary).mark_circle(opacity=.65,stroke='white',strokeWidth=.5).encode(x=alt.X('median:Q',title='Typical observed price · median (RM)',scale=alt.Scale(zero=False)),y=alt.Y('variation_pct:Q',title='Within-shop price variation · CV (%)',scale=variation_scale),size=alt.Size('days:Q',title='Observed days',scale=alt.Scale(range=[35,350])),color=alt.Color('state:N',title='State',scale=alt.Scale(scheme='tableau20')),opacity=alt.condition(selection,alt.value(.75),alt.value(.08)),tooltip=[alt.Tooltip('premise:N',title='Shop'),alt.Tooltip('state:N',title='State'),alt.Tooltip('district:N',title='District'),alt.Tooltip('median:Q',format='.2f',title='Median (RM)'),alt.Tooltip('variation_pct:Q',format='.2f',title='Price variation (%)'),alt.Tooltip('days:Q',title='Observed days'),alt.Tooltip('low:Q',format='.2f',title='Minimum (RM)'),alt.Tooltip('high:Q',format='.2f',title='Maximum (RM)')]).add_params(selection).properties(height=340)
        draw(chart)
        if scale_mode=='Expanded low values':
            st.caption('Expanded low values uses a symmetric-logarithmic vertical scale: zero remains visible and large outliers stay on the chart. Equal vertical distances do not represent equal percentage-point differences.')
        st.caption(f'{len(summary):,} shops qualify. Each point is one shop; larger points have more observed days. Click a state in the legend to highlight it. Variation is the sample standard deviation divided by mean price × 100. Low measured variation does not guarantee future price stability, especially with sparse observations.')

def matched_price_plot(paired,shops):
    if paired.empty:return
    with st.container(border=True):
        st.subheader('Start price → end price, shop by shop')
        limit=st.select_slider('Largest absolute percentage changes to display',[5,10,15,20],value=10,key='matched_limit')
        view=paired.assign(magnitude=paired.change_pct.abs()).sort_values(['magnitude','premise_code'],ascending=[False,True]).head(limit).merge(shops[['premise_code','premise']],on='premise_code')
        view['shop']=view.premise.astype(str).str.slice(0,40)+' · #'+view.premise_code.astype(str)
        order=view.shop.tolist()
        base=alt.Chart(view).encode(y=alt.Y('shop:N',title=None,sort=order,axis=alt.Axis(labelLimit=230)),tooltip=[alt.Tooltip('premise:N',title='Shop'),alt.Tooltip('price_start:Q',format='.2f',title='Start (RM)'),alt.Tooltip('price_end:Q',format='.2f',title='End (RM)'),alt.Tooltip('change_pct:Q',format='+.2f',title='Change (%)')])
        connector=base.mark_rule(color='#bdcac4',strokeWidth=2).encode(x=alt.X('price_start:Q',title='Observed price (RM)',scale=alt.Scale(zero=False)),x2='price_end:Q')
        start=base.mark_circle(color=BLUE,size=80).encode(x='price_start:Q')
        end=base.mark_circle(color=TEAL,size=80).encode(x='price_end:Q')
        draw((connector+start+end).properties(height=max(190,len(view)*32)))
        st.caption('Blue: start date · teal: end date. Both prices are exact-date observations for the same item at the same shop. Displayed shops have the largest absolute percentage changes, not a representative sample of all shops.')

def basket_matrix(latest,quantities,shops,labels):
    panel=st.expander('Shop × product coverage matrix',on_change='rerun')
    if not panel.open:return
    with panel:
        count=st.select_slider('Premises to inspect',[10,20,30],value=20,key='matrix_limit')
        grid=basket_coverage_matrix(latest,quantities,shops,count)
        if grid.empty:
            st.info('No premises in this area.');return
        grid['product']=grid.item_code.map(labels)
        order=grid.shop_label.drop_duplicates().tolist()
        chart=alt.Chart(grid).mark_rect(cornerRadius=3,stroke='white',strokeWidth=2).encode(x=alt.X('product_code:N',title='Product code · hover for the full name',sort=['#'+str(c) for c in quantities],axis=alt.Axis(labelAngle=-45)),y=alt.Y('shop_label:N',sort=order,title=None,axis=alt.Axis(labelLimit=210)),color=alt.Color('status:N',title='Observation status',scale=alt.Scale(domain=['Observed','Missing'],range=[TEAL,'#e4e9e6'])),tooltip=[alt.Tooltip('premise:N',title='Shop'),alt.Tooltip('product:N',title='Product'),alt.Tooltip('status:N',title='Status'),alt.Tooltip('price:Q',format='.2f',title='Price (RM)'),alt.Tooltip('date:T',format='%d %b %Y',title='Observed on'),alt.Tooltip('age_days:Q',title='Age (days)')]).properties(height=max(200,len(order)*26))
        draw(chart)
        st.caption('Sorted by number of basket items with eligible observations, then premise code. Grey cells mean no eligible price record, not out of stock. This is a coverage view; partial basket prices are not ranked.')
        st.dataframe(pd.DataFrame({'Product code':['#'+str(c) for c in quantities],'Product':[labels[c] for c in quantities]}),hide_index=True)
